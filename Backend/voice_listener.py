#!/usr/bin/env python3
"""
voice_listener.py - Voice Command Listener
==========================================

Listens for "hey robot" wake word and transcribes commands.
Outputs to asyncio queue for processing by robot_assistant.py.

EXPORTS:
--------
- start_listener(ready, test_mode, queue) -> Main async loop
- get_voice_queue() -> asyncio.Queue for commands
- set_muted(bool) / is_muted() -> Pause during TTS
- set_last_bot_response(text, t_end) -> For follow-up detection
- FOLLOWUP_WINDOW -> Seconds to accept follow-ups without wake word

Usage:
    from voice_listener import start_listener, get_voice_queue
    queue = get_voice_queue()
    asyncio.create_task(start_listener())
    cmd, t_end, is_followup = await queue.get()
"""

import asyncio
import os
import sys
import tempfile
import time
import warnings
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import sounddevice as sd
import soundfile as sf
from openai import OpenAI

from config import (
    STT_OFFLOAD,
    STT_OFFLOAD_PROVIDER,
    STT_LOCAL_BACKEND,
    STT_LOCAL_MODEL,
    STT_SAMPLE_RATE,
    STT_VAD_SILENCE_MS,
    STT_MIN_UTTERANCE_SEC,
)

warnings.filterwarnings("ignore")

# ================== Config ==================
ROOT = Path.home() / "Simple_Robot"
OUTPUT_FILE = ROOT / "logs" / "voice_commands.txt"
WAKE_PHRASE = "hey robot"

SAMPLE_RATE = STT_SAMPLE_RATE
BLOCK_DURATION = 0.03
SILENCE_MS = STT_VAD_SILENCE_MS
MIN_UTTERANCE_SEC = STT_MIN_UTTERANCE_SEC
MAX_UTTERANCE_SEC = 10
SILENCE_THRESH = 0.012
FOLLOWUP_WINDOW = 10.0  # Seconds to accept follow-ups without wake word

# Whisper hallucinations to filter
HALLUCINATIONS = [
    "thank you for watching", "thanks for watching", "please subscribe",
    "like and subscribe", "mbc 뉴스", "구독과 좋아요", "subs by", "subtitles by",
]

# OpenAI client
API_KEY = os.environ.get("OPENAI_API_KEY", "")
client = OpenAI(api_key=API_KEY) if API_KEY else None

# ================== Shared State ==================
voice_queue: asyncio.Queue | None = None
_executor = ThreadPoolExecutor(max_workers=2)
_muted = False
_last_bot_response: str | None = None
_last_bot_t_end: float = 0.0


def set_muted(muted: bool):
    """Mute listener during TTS."""
    global _muted
    _muted = muted


def is_muted() -> bool:
    return _muted


def set_last_bot_response(text: str | None, t_end: float):
    """Store last response for follow-up detection."""
    global _last_bot_response, _last_bot_t_end
    _last_bot_response = text
    _last_bot_t_end = float(t_end) if t_end else time.time()


# ================== Transcription ==================
def _transcribe_blocking(wav_path: Path) -> str:
    """Transcribe audio via OpenAI Whisper API (blocking)."""
    try:
        if STT_OFFLOAD and STT_OFFLOAD_PROVIDER == "openai" and client:
            with wav_path.open("rb") as f:
                resp = client.audio.transcriptions.create(model="whisper-1", file=f)
            return resp.text.strip()
        # Local fallback
        if not STT_OFFLOAD and STT_LOCAL_BACKEND in ("faster_whisper", "whisper"):
            try:
                from faster_whisper import WhisperModel
                model = WhisperModel(STT_LOCAL_MODEL)
                segments, _ = model.transcribe(str(wav_path))
                return " ".join([s.text for s in segments]).strip()
            except Exception:
                pass
        # Default: OpenAI
        if client:
            with wav_path.open("rb") as f:
                resp = client.audio.transcriptions.create(model="whisper-1", file=f)
            return resp.text.strip()
        return ""
    except Exception as e:
        print(f"[Listener] Transcribe error: {e}")
        return ""
    finally:
        try:
            wav_path.unlink(missing_ok=True)
        except Exception:
            pass


async def transcribe(wav_path: Path) -> str:
    """Transcribe audio (async)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _transcribe_blocking, wav_path)


# ================== Recording ==================
def _record_utterance_blocking() -> Path | None:
    """Record until silence detected (blocking)."""
    # Find working sample rate
    sr = SAMPLE_RATE
    for test_sr in [16000, 48000, 44100]:
        try:
            s = sd.InputStream(samplerate=test_sr, channels=1, dtype="float32")
            s.close()
            sr = test_sr
            break
        except Exception:
            continue

    nblock = int(sr * BLOCK_DURATION)

    # Calibrate silence threshold
    try:
        with sd.InputStream(samplerate=sr, channels=1, dtype="float32") as stream:
            amb = [stream.read(nblock)[0].copy() for _ in range(4)]
            amb_rms = float(np.sqrt(np.mean(np.concatenate(amb) ** 2)) + 1e-9)
            thresh = max(SILENCE_THRESH * 0.5, min(SILENCE_THRESH, amb_rms * 3.0))
    except Exception:
        thresh = SILENCE_THRESH

    # Record
    audio_chunks = []
    last_voice_t = 0
    start_t = time.time()
    speech_detected = False

    try:
        with sd.InputStream(samplerate=sr, channels=1, dtype="float32") as stream:
            while True:
                if _muted:
                    return None
                frames, _ = stream.read(nblock)
                audio_chunks.append(frames.copy())
                rms = float(np.sqrt(np.mean(frames ** 2)) + 1e-9)
                now = time.time()

                if rms > thresh:
                    last_voice_t = now
                    speech_detected = True

                elapsed = now - start_t
                if speech_detected:
                    silence_ms = (now - last_voice_t) * 1000
                    if elapsed >= MIN_UTTERANCE_SEC and silence_ms >= SILENCE_MS:
                        break
                if elapsed >= MAX_UTTERANCE_SEC:
                    break
    except Exception as e:
        print(f"[Listener] Recording error: {e}")
        return None

    if not audio_chunks or not speech_detected:
        return None

    data = np.concatenate(audio_chunks)
    if float(np.sqrt(np.mean(data ** 2))) < thresh * 0.3:
        return None

    out = Path(tempfile.gettempdir()) / f"utt_{int(time.time() * 1000)}.wav"
    sf.write(out, data.flatten(), sr)
    return out


async def record_utterance() -> Path | None:
    """Record audio (async)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _record_utterance_blocking)


# ================== Helpers ==================
def is_hallucination(text: str) -> bool:
    """Filter Whisper hallucinations."""
    text_lower = text.lower()
    for h in HALLUCINATIONS:
        if h in text_lower:
            return True
    # Check repeated words
    words = text_lower.split()
    if len(words) >= 4:
        from collections import Counter
        for word, count in Counter(words).items():
            if count >= 4 and len(word) > 1:
                return True
    return False


def check_wake_word(text: str) -> tuple[bool, str]:
    """Check for wake word, return (found, command_after_wake)."""
    text_clean = text.lower().replace(",", "").replace(".", "").replace("!", "").replace("?", "")
    
    wake_patterns = [
        "hey robot", "hey robut", "hey robat", "hey roba", "hey robo",
        "hey rowbot", "hey robert", "yo robot", "hi robot", "hay robot",
    ]
    
    for pattern in wake_patterns:
        if pattern in text_clean:
            idx = text_clean.find(pattern)
            after = text_clean[idx + len(pattern):].strip()
            return True, after

    # Fuzzy: "rob" in first 3 words
    words = text_clean.split()
    for i, word in enumerate(words[:3]):
        if "rob" in word or "rub" in word:
            return True, " ".join(words[i + 1:]).strip()

    return False, ""


def _is_followup(text: str) -> bool:
    """Check if this is a follow-up (any speech within FOLLOWUP_WINDOW after bot response)."""
    if not _last_bot_response:
        return False
    elapsed = time.time() - _last_bot_t_end
    if elapsed > FOLLOWUP_WINDOW:
        return False
    # Any speech within the window is a follow-up
    print(f"[Listener] Follow-up detected ({elapsed:.1f}s since last response)")
    return True


# ================== Output ==================
async def output_command(text: str, t_utterance_end: float, test_mode: bool = False, followup: bool = False):
    """Save command to file and queue."""
    global voice_queue

    # Write to file
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "a") as f:
        f.write(text + "\n")

    if not test_mode and voice_queue:
        await voice_queue.put((text, t_utterance_end, followup))
        print(f"[Listener] Queued: {text}")


# ================== Main Loop ==================
async def start_listener(
    ready: asyncio.Event | None = None,
    test_mode: bool = False,
    queue: asyncio.Queue | None = None,
):
    """
    Main listener loop - listens for wake word and transcribes commands.
    
    Output format: (command_text, utterance_end_time, is_followup)
    """
    global voice_queue

    if queue is not None:
        voice_queue = queue
    elif voice_queue is None:
        voice_queue = asyncio.Queue()

    # Session separator
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "a") as f:
        f.write("-\n")

    print(f"[Listener] Started. Wake: \"{WAKE_PHRASE}\"")
    if ready:
        ready.set()

    pending_transcription: asyncio.Task | None = None
    utterance_end_time: float = 0

    try:
        while True:
            if _muted:
                await asyncio.sleep(0.1)
                continue

            # Start recording
            recording_task = asyncio.create_task(record_utterance())

            # Process previous transcription while recording
            if pending_transcription:
                text = await pending_transcription
                pending_transcription = None

                if _muted:
                    continue

                if text and not is_hallucination(text):
                    print(f"[Heard] \"{text}\"")
                    is_wake, command = check_wake_word(text)

                    if is_wake and command and len(command) > 2:
                        # Wake word + command
                        print(f"[Command] \"{command}\"")
                        await output_command(command, utterance_end_time, test_mode, followup=False)
                    elif is_wake:
                        # Just wake word, no command
                        print("[Listener] Wake word heard, waiting for command...")
                    elif _is_followup(text):
                        # Follow-up without wake word
                        print(f"[FollowUp] \"{text}\"")
                        await output_command(text, utterance_end_time, test_mode, followup=True)

            # Wait for recording
            wav_path = await recording_task
            utterance_end_time = time.perf_counter()

            if wav_path is None or _muted:
                if wav_path:
                    try:
                        wav_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                continue

            # Start transcription (don't wait)
            pending_transcription = asyncio.create_task(transcribe(wav_path))

    except asyncio.CancelledError:
        print("[Listener] Cancelled")
    except KeyboardInterrupt:
        print("[Listener] Stopped")


def get_voice_queue() -> asyncio.Queue:
    """Get the shared command queue."""
    global voice_queue
    if voice_queue is None:
        voice_queue = asyncio.Queue()
    return voice_queue


# ================== Standalone ==================
if __name__ == "__main__":
    test_mode = "--test" in sys.argv
    asyncio.run(start_listener(test_mode=test_mode))
