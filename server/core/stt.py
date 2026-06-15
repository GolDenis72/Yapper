# core/stt.py — Speech-to-Text via Whisper server

import httpx
import tempfile
import os
import asyncio
from config.settings import WHISPER_URL, WHISPER_LANGUAGE


def transcribe(audio_bytes: bytes, language: str = WHISPER_LANGUAGE) -> str:
    """
    Send raw audio bytes to Whisper server and get transcribed text.
    Sync version — use in non-async context only.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir="/tmp") as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        with httpx.Client(timeout=120.0) as client:  # 120s for long audio
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


async def transcribe_async(audio_bytes: bytes, language: str = WHISPER_LANGUAGE) -> str:
    """
    Async version — use inside FastAPI/WebSocket handlers.
    Runs transcribe() in thread pool so it doesn't block the event loop.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, transcribe, audio_bytes, language)


def ping() -> bool:
    """Check if Whisper server is reachable."""
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{WHISPER_URL}/docs", follow_redirects=True)
            return r.status_code == 200
    except Exception:
        return False
