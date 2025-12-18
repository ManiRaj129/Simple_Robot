
from pathlib import Path
import os

# TTS
ROOT = Path.home() / "Simple_Robot"
# The local ONNX model used by Piper. Change this if you download another model.
# Example override: export PIPER_MODEL=/home/pi/Simple_Robot/tools/piper/models/en_US-xyz.onnx
PIPER_MODEL = Path(os.environ.get("PIPER_MODEL", str(ROOT / "tools" / "piper" / "models" / "en_US-lessac-medium.onnx")))
PIPER_EXE = Path(os.environ.get("PIPER_EXE", str(ROOT / "tools" / "piper" / ("piper.exe" if os.name == "nt" else "piper"))))

# TTS backend preference
# - "piper" = local TTS using the ONNX model above
# - "openai" = offload to OpenAI TTS (faster for smaller devices) – ensure OPENAI_API_KEY is set
# Example to use OpenAI TTS (and be sure to set OPENAI_API_KEY):
#   export TTS_BACKEND=openai
#   export OPENAI_API_KEY="sk-..."
#
# NOTE: The openai TTS model will be more realistic + a bit faster
TTS_BACKEND = os.environ.get("TTS_BACKEND", os.environ.get("TTS_PROVIDER", "openai"))

# -------------------- STT (Speech to Text) --------------------
# Whether STT should be offloaded (cloud) or run locally
# - True: offload STT (e.g., OpenAI Whisper). Example:
#     export STT_OFFLOAD=true
#     export STT_OFFLOAD_PROVIDER=openai
#     export OPENAI_API_KEY="sk-..."
# - False: use local backend (whisper/faster_whisper)
# NOTE: The openai STT model will be more accurate + a bit faster
STT_OFFLOAD = os.environ.get("STT_OFFLOAD", "true").lower() in ("1", "true", "yes")

# Extra stuff you likely won't need to change.
STT_OFFLOAD_PROVIDER = os.environ.get("STT_OFFLOAD_PROVIDER", "openai")
STT_LOCAL_BACKEND = os.environ.get("STT_LOCAL_BACKEND", "faster_whisper")
STT_LOCAL_MODEL = os.environ.get("STT_LOCAL_MODEL", "base.en") 
STT_SAMPLE_RATE = int(os.environ.get("STT_SAMPLE_RATE", "16000"))
STT_VAD_SILENCE_MS = int(os.environ.get("STT_VAD_SILENCE_MS", "1200"))
STT_MIN_UTTERANCE_SEC = float(os.environ.get("STT_MIN_UTTERANCE_SEC", "1.0"))

def validate():
    msgs = []
    if TTS_BACKEND == "piper":
        if not PIPER_EXE.exists():
            msgs.append(f"PIPER_EXE not found at {PIPER_EXE}. If you use a different path, set PIPER_EXE env var or download Piper to this location.")
        if not PIPER_MODEL.exists():
            msgs.append(f"PIPER_MODEL not found at {PIPER_MODEL}. Download a Piper ONNX model and set PIPER_MODEL to that path.")
    if STT_OFFLOAD and STT_OFFLOAD_PROVIDER == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            msgs.append("STT is configured to offload to OpenAI, but OPENAI_API_KEY is not set. Example: export OPENAI_API_KEY='sk-...' and retry.")
    if TTS_BACKEND == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            msgs.append("TTS_BACKEND=openai selected, but OPENAI_API_KEY is not set. Set it with: export OPENAI_API_KEY='sk-...' ")
    return msgs


if __name__ == "__main__":
    for m in validate():
        print("[config] WARNING:", m)
