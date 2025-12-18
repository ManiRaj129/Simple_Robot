from pathlib import Path
import sys, subprocess, tempfile, time, warnings, os
import yaml
import sounddevice as sd
import soundfile as sf
import numpy as np

warnings.filterwarnings("ignore")
os.environ.setdefault("CT2_FORCE_CPU", "1")
os.environ.setdefault("CT2_VERBOSE", "0")
os.environ.setdefault("KMP_WARNINGS", "0")

DEFAULT_SR = 48000
CANDIDATE_SRS = lambda cfg_sr: [
    int(cfg_sr), 48000, 44100, 32000, 24000, 16000
]

MENU = (
    "[1] Robot repeat what you say (STT → TTS)\n"
    "[2] Robot print what you say   (STT only)\n"
    "[3] Say a line (TTS only)\n"
    "[4] Mic check (record 3s → play)\n"
    "[5] Exit\n> "
)

def load_cfg():
    cfg = {
        "exec": {
            "piper_path": "tools/piper/piper.exe",
            "ffmpeg_path": "tools/ffmpeg/ffmpeg.exe",
        },
        "tts": {"voice_model": "tools/piper/models/en_US-lessac-medium.onnx"},
        "stt": {"model_size": "base.en", "compute_type": "int8", "device": "cpu"},
        "audio": {
            "input_device": "default",
            "output_device": "default",
            "samplerate": DEFAULT_SR,
            # silence/VAD tuning
            "max_record_seconds": 30.0,
            "min_record_seconds": 2.0,
            "silence_ms": 800,
            "vad_rms_threshold": 0.015,
        },
    }
    p = Path("config.yaml")
    if p.exists():
        try:
            user = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            for k, v in user.items():
                if isinstance(v, dict) and k in cfg:
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception:
            pass
    return cfg

def must(path, label) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{label} not found at {p.resolve()}")
    return p.resolve()

def ffplay_from(ffmpeg_path: Path) -> Path | None:
    if not ffmpeg_path.exists():
        return None
    p = ffmpeg_path.with_name("ffplay.exe")
    return p if p.exists() else None

def piper_tts_to_file(piper_exe: Path, voice_model: Path, text: str) -> Path:
    sidecar = voice_model.with_suffix(voice_model.suffix + ".json")
    if not sidecar.exists():
        raise FileNotFoundError(f"Missing voice metadata next to {voice_model.name}: {sidecar.name}")
    out = Path(tempfile.gettempdir()) / f"piper_{int(time.time()*1000)}.wav"
    cmd = [str(piper_exe), "--model", str(voice_model), "--output_file", str(out)]
    subprocess.run(cmd, input=text.encode("utf-8"),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    return out

def play_wav(path: Path, cfg, ffplay: Path | None):
    if ffplay:
        subprocess.run([str(ffplay), "-nodisp", "-autoexit", "-loglevel", "quiet", str(path)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return
    out = cfg["audio"].get("output_device", "default")
    if out != "default":
        try:
            out = int(out)
            cur = sd.default.device or (None, None)
            sd.default.device = (cur[0], out)
        except Exception:
            pass
    data, sr = sf.read(path, dtype="float32")
    sd.default.samplerate = sr
    sd.play(data, sr); sd.wait()

def _set_input_device(cfg):
    inp = cfg["audio"].get("input_device", "default")
    if inp != "default":
        try:
            inp = int(inp)
            cur = sd.default.device or (None, None)
            sd.default.device = (inp, cur[1])
        except Exception:
            pass

def _open_input_stream_or_none(sr: int):
    try:
        return sd.InputStream(samplerate=sr, channels=1, dtype="float32")
    except Exception:
        return None

def _pick_working_samplerate(cfg) -> int:
    cfg_sr = int(cfg["audio"].get("samplerate", DEFAULT_SR))
    tried = set()
    for sr in CANDIDATE_SRS(cfg_sr):
        if sr in tried:
            continue
        tried.add(sr)
        stream = _open_input_stream_or_none(sr)
        if stream:
            stream.close()
            return sr
    # As a last resort, ask PortAudio what the default input supports
    try:
        info = sd.query_devices(kind='input')
        # Some drivers report default samplerate here:
        sr = int(info.get('default_samplerate') or 16000)
        stream = _open_input_stream_or_none(sr)
        if stream:
            stream.close()
            return sr
    except Exception:
        pass
    # Fallback
    return 16000

def record_fixed(seconds: float, cfg) -> Path:
    """Used for the mic check menu option with samplerate fallback."""
    _set_input_device(cfg)
    sr = _pick_working_samplerate(cfg)
    block_frames = int(sr * 0.05)
    audio = []
    try:
        with sd.InputStream(samplerate=sr, channels=1, dtype="float32") as stream:
            remaining = int(seconds / 0.05)
            for _ in range(remaining):
                frames, _ = stream.read(block_frames)
                audio.append(frames.copy())
    except Exception as e:
        raise RuntimeError(f"Could not open input stream at {sr} Hz: {e}")
    audio = np.concatenate(audio, axis=0)
    out = Path(tempfile.gettempdir()) / f"mic_{int(time.time()*1000)}.wav"
    sf.write(out, audio, sr)
    return out

def record_until_silence(cfg) -> Path:
    """Record audio and stop after a pause (silence), with samplerate fallback."""
    _set_input_device(cfg)
    sr = _pick_working_samplerate(cfg)

    max_sec = float(cfg["audio"].get("max_record_seconds", 30.0))
    min_sec = float(cfg["audio"].get("min_record_seconds", 2.0))
    silence_ms = int(cfg["audio"].get("silence_ms", 800))
    thresh = float(cfg["audio"].get("vad_rms_threshold", 0.015))

    block_dur = 0.05  # 50ms
    nblock = int(sr * block_dur)

    # Warm-up & ambient threshold adapt
    try:
        with sd.InputStream(samplerate=sr, channels=1, dtype="float32") as stream:
            amb_buf = []
            warm_blocks = max(1, int(0.2 / block_dur))
            for _ in range(warm_blocks):
                frames, _ = stream.read(nblock)
                amb_buf.append(frames.copy())
            amb = np.concatenate(amb_buf, axis=0)
            amb_rms = float(np.sqrt(np.mean(amb**2)) + 1e-9)
            dynamic_thresh = max(thresh * 0.7, min(thresh, amb_rms * 4.0))
            thresh_use = dynamic_thresh
    except Exception as e:
        raise RuntimeError(f"Could not open input stream at {sr} Hz: {e}")

    audio_chunks = []
    last_voice_t = time.time()
    start_t = time.time()
    with sd.InputStream(samplerate=sr, channels=1, dtype="float32") as stream:
        while True:
            frames, _ = stream.read(nblock)
            audio_chunks.append(frames.copy())

            rms = float(np.sqrt(np.mean(frames**2)) + 1e-9)
            now = time.time()
            if rms > thresh_use:
                last_voice_t = now

            elapsed = now - start_t
            silent_for_ms = (now - last_voice_t) * 1000.0

            if elapsed >= min_sec and silent_for_ms >= silence_ms:
                break
            if elapsed >= max_sec:
                break

    audio = np.concatenate(audio_chunks, axis=0)
    out = Path(tempfile.gettempdir()) / f"mic_{int(time.time()*1000)}.wav"
    sf.write(out, audio, sr)
    return out

_MODEL = None
def whisper_transcribe(wav: Path, cfg) -> str:
    global _MODEL
    from faster_whisper import WhisperModel
    if _MODEL is None:
        _MODEL = WhisperModel(
            cfg["stt"]["model_size"],
            device=cfg["stt"].get("device", "cpu"),
            compute_type=cfg["stt"]["compute_type"],
        )
    segs, _info = _MODEL.transcribe(str(wav), vad_filter=True, beam_size=1,
                                    temperature=0.0, language="en")
    return "".join(s.text for s in segs).strip()

def _beep():
    try:
        import winsound; winsound.Beep(880, 140)
    except Exception:
        pass

def act_repeat(cfg, piper, voice, ffplay):
    print("Speak after the beep…")
    _beep()
    rec = record_until_silence(cfg)
    text = whisper_transcribe(rec, cfg)
    if not text:
        print("(heard nothing)")
        return
    print(f"You said: {text}")
    say = piper_tts_to_file(piper, voice, f"You said: {text}")
    play_wav(say, cfg, ffplay)

def act_print(cfg, piper, voice, ffplay):
    print("Speak after the beep…")
    _beep()
    rec = record_until_silence(cfg)
    text = whisper_transcribe(rec, cfg)
    print(f"Transcript: {text or '(empty)'}")

def act_tts_only(cfg, piper, voice, ffplay):
    try:
        line = input("Type what the robot should say: ").strip()
    except EOFError:
        line = ""
    if not line:
        line = "Hello from your robot."
    say = piper_tts_to_file(piper, voice, line)
    play_wav(say, cfg, ffplay)

def act_mic_check(cfg, piper, voice, ffplay):
    print("Recording 3 seconds…")
    rec = record_fixed(3.0, cfg)
    play_wav(rec, cfg, ffplay)
    print("(played back)")

def main():
    cfg = load_cfg()
    piper = must(cfg["exec"]["piper_path"], "Piper executable")
    voice = must(cfg["tts"]["voice_model"], "Piper voice (.onnx)")
    ffmpeg = Path(cfg["exec"]["ffmpeg_path"])
    ffplay = ffplay_from(ffmpeg)

    actions = {
        "1": act_repeat,
        "2": act_print,
        "3": act_tts_only,
        "4": act_mic_check,
        "5": lambda *_: sys.exit(0),
    }

    while True:
        try:
            choice = input(MENU).strip()
        except EOFError:
            choice = "5"
        fn = actions.get(choice)
        if not fn:
            print("Choose 1–5.")
            continue
        try:
            fn(cfg, piper, voice, ffplay)
        except FileNotFoundError as e:
            print(f"[missing] {e}")
        except subprocess.CalledProcessError as e:
            print(f"[tool error] {e}")
        except Exception as e:
            print(f"[error] {e}")

if __name__ == "__main__":
    main()
