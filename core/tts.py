# core/tts.py — Text-to-Speech via edge-tts

import asyncio
import tempfile
import os
import edge_tts
from config.settings import TTS_VOICE, TTS_RATE, TTS_VOLUME


async def _synthesize(text: str, output_path: str) -> None:
    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate=TTS_RATE,
        volume=TTS_VOLUME,
    )
    await communicate.save(output_path)


async def speak_async(text: str) -> bytes:
    """Async version — use inside FastAPI/WebSocket handlers."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    try:
        await _synthesize(text, tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


def speak(text: str) -> bytes:
    """Sync version — use in console/main.py context only."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name
    try:
        asyncio.run(_synthesize(text, tmp_path))
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


def speak_to_file(text: str, output_path: str) -> None:
    asyncio.run(_synthesize(text, output_path))


async def list_voices() -> list[dict]:
    voices = await edge_tts.list_voices()
    return [v for v in voices if v["Locale"].startswith("en-")]


def get_english_voices() -> list[str]:
    voices = asyncio.run(list_voices())
    return [v["ShortName"] for v in voices]
