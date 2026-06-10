# core/stt.py — Speech-to-Text via Whisper server

import httpx
import tempfile
import os
from config.settings import WHISPER_URL, WHISPER_LANGUAGE


def transcribe(audio_bytes: bytes, language: str = WHISPER_LANGUAGE) -> str:
    """
    Send raw audio bytes to Whisper server and get transcribed text.
    audio_bytes: WAV audio data
    Returns: transcribed text string
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        with httpx.Client(timeout=30.0) as client:
            with open(tmp_path, "rb") as audio_file:
                response = client.post(
                    f"{WHISPER_URL}/asr",
                    params={
                        "language": language,
                        "task": "transcribe",
                        "output": "txt",
                    },
                    files={"audio_file": ("audio.wav", audio_file, "audio/wav")},
                )
                response.raise_for_status()
                return response.text.strip()
    finally:
        os.unlink(tmp_path)


def ping() -> bool:
    """Check if Whisper server is reachable."""
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{WHISPER_URL}/docs")
            return r.status_code == 200
    except Exception:
        return False
