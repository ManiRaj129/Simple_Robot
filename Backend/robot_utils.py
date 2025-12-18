"""
robot_utils.py - Essential Async Robot Utilities
=================================================

REQUIRED FUNCTIONS (per teammate spec):
---------------------------------------
1. async def speak(text: str, face=None) -> bool
   - TTS using Piper (local) or OpenAI (cloud)
   - Controlled by TTS_BACKEND env var

2. async def ask_llm(user_text: str) -> Dict
   - Returns: {"find", "follow", "emotion", "response", "command"}

3. async def get_objects_at() -> List[Dict]
   - YOLO detection, returns: [{"name", "direction", "area", "confidence"}]

"""

from ultralytics import YOLO
from Camera import camera
import time as t

import asyncio
import shutil
import subprocess
import time
from pathlib import Path
import os
from typing import Any, Dict, List
import requests

from config import (
    PIPER_EXE as CONFIG_PIPER_EXE,
    PIPER_MODEL as CONFIG_PIPER_MODEL,
    TTS_BACKEND as CONFIG_TTS_BACKEND,
)

# ================== Paths ==================
ROOT = Path.home() / "Simple_Robot"
PIPER_EXE = Path(os.environ.get("PIPER_EXE", str(CONFIG_PIPER_EXE)))
VOICE_ONNX = Path(os.environ.get("PIPER_MODEL", str(CONFIG_PIPER_MODEL)))

# ================== Config ==================
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_TTS_STYLE_PROMPT = os.environ.get("OPENAI_TTS_STYLE_PROMPT", "")
TTS_BACKEND = os.environ.get("TTS_BACKEND", str(CONFIG_TTS_BACKEND))



# ================== TTS Helpers ==================
def _have_piper() -> bool:
    return (
        PIPER_EXE.exists()
        and VOICE_ONNX.exists()
        and VOICE_ONNX.with_suffix(VOICE_ONNX.suffix + ".json").exists()
    )


def _safe_run(cmd, **kwargs) -> tuple[bool, str]:
    try:
        subprocess.run(cmd, check=True, **kwargs)
        return True, ""
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _speak_piper(text: str, face=None) -> bool:
    """Local TTS using Piper."""
    if not _have_piper():
        print(f"[TTS] Piper not available: {text}")
        return False

    out_wav = Path.cwd() / f"piper_{int(time.time() * 1000)}.wav"
    try:
        cmd = [str(PIPER_EXE), "--model", str(VOICE_ONNX), "--output_file", str(out_wav)]
        ok, err = _safe_run(cmd, input=text.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not ok:
            print(f"[TTS] Piper failed: {err}")
            return False

        return _play_audio(out_wav, face)
    finally:
        try:
            out_wav.unlink(missing_ok=True)
        except Exception:
            pass


def _speak_openai(text: str, face=None) -> bool:
    """Cloud TTS using OpenAI."""
    if not OPENAI_API_KEY:
        return _speak_piper(text, face)  # Fallback

    out_wav = Path.cwd() / f"openai_tts_{int(time.time() * 1000)}.wav"
    try:
        t = f"{OPENAI_TTS_STYLE_PROMPT} {text}" if OPENAI_TTS_STYLE_PROMPT else text
        payload = {
            "model": os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
            "input": t,
            "voice": os.environ.get("OPENAI_TTS_VOICE", "alloy"),
            "response_format": "wav",
        }
        resp = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"[TTS] OpenAI failed: {resp.status_code}")
            return False

        with open(out_wav, "wb") as f:
            f.write(resp.content)

        return _play_audio(out_wav, face)
    except Exception as e:
        print(f"[TTS] OpenAI error: {e}")
        return False
    finally:
        try:
            out_wav.unlink(missing_ok=True)
        except Exception:
            pass


def _play_audio(wav_path: Path, face=None) -> bool:
    """Play audio file with face animation."""
    ffplay = shutil.which("ffplay")
    aplay = shutil.which("aplay")
    player = ffplay or aplay

    if not player:
        print("[TTS] No audio player found")
        return False

    if face:
        try:
            face.set_talking(True)
        except Exception:
            pass

    try:
        if player == ffplay:
            ok, _ = _safe_run([player, "-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_path)])
        else:
            ok, _ = _safe_run([player, str(wav_path)])
        return ok
    finally:
        if face:
            try:
                face.set_talking(False)
            except Exception:
                pass


# ================== TTS (async) ==================
async def speak(text: str, face) -> bool:
    """
    Speak text using TTS (async).
    
    Backend controlled by TTS_BACKEND: "piper" (local) or "openai" (cloud)
    """
    # Mute listener while speaking to avoid hearing ourselves
    from voice_listener import set_muted
    set_muted(True)
    
    loop = asyncio.get_running_loop()
    
    try:
        if TTS_BACKEND == "openai":
            ok = await loop.run_in_executor(None, _speak_openai, text, face)
            if not ok:
                return await loop.run_in_executor(None, _speak_piper, text, face)
            return ok
        else:
            return await loop.run_in_executor(None, _speak_piper, text, face)
    finally:
        # Small delay to let audio finish, then unmute
        await asyncio.sleep(0.3)
        set_muted(False)


# ================== LLM (async) ==================
try:
    from groq_utils import ask_groq, VALID_OBJECTS
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    VALID_OBJECTS = []

    def ask_groq(query: str) -> dict:
        return {"find": "", "follow": "", "emotion": "sad", "response": "LLM unavailable", "command": ""}


async def ask_llm(user_text: str) -> Dict[str, Any]:
    """
    Query LLM (Groq) and return structured JSON response.

    Returns: {
        "find": str,      # Object to find (COCO class) or ""
        "follow": str,    # "true" or ""
        "emotion": str,   # happy|sad|angry|neutral|surprised
        "response": str,  # Spoken response
        "command": str    # right|left|back|front or ""
    }
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, ask_groq, user_text)


# ================== Object Detection (async) ==================
_detector_initialized = False
_yolo_model = None
model = camera.get_yolo()

def _init_detector():
    global _detector_initialized, _yolo_model
    if _detector_initialized:
        return True
    try:
        _yolo_model = YOLO(str(ROOT / "yolov8n.pt"))
        t.sleep(1)
        _detector_initialized = True
        print("[Detection] YOLO initialized")
        return True
    except Exception as e:
        print(f"[Detection] Init failed: {e}")
        return False


def _get_objects_blocking() -> List[Dict[str, Any]]:
    """Detect objects in camera frame (blocking)."""
    if not _init_detector():
        return []

    try:
        frame = camera.get_frame()
        results = model(frame)
         
        detected = []
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                name = _yolo_model.names[cls]
                conf = float(box.conf[0])

                x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
                area = (x2 - x1) * (y2 - y1)
                x_center = (x1 + x2) / 2

                if x_center < 640 * 0.33:
                    direction = "left"
                elif x_center > 640 * 0.66:
                    direction = "right"
                else:
                    direction = "center"

                detected.append({
                    "name": name,
                    "direction": direction,
                    "area": area,
                    "confidence": conf,
                })

        return detected
    except Exception as e:
        print(f"[Detection] Error: {e}")
        return []


async def get_objects_at() -> List[Dict[str, Any]]:
    """
    Detect objects in camera view (async).

    Returns: [{"name", "direction", "area", "confidence"}, ...]
    - direction: "left" | "center" | "right"
    - area: larger = closer
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _get_objects_blocking)


def cleanup_detector():
    """Release camera resources."""
    global _detector_initialized
    if camera is not None:
        try:
            camera.stop()
        except Exception:
            pass
        _detector_initialized = False
