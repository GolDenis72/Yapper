# core/tts.py — Text-to-Speech via edge-tts

import asyncio
import tempfile
import os
import edge_tts
from config.settings import TTS_VOICE, TTS_RATE, TTS_VOLUME


async def _synthesize(text: str, output_path: str) -> None:
    """Synthesize text to audio file using edge-tts."""
    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate=TTS_RATE,
        volume=TTS_VOLUME,
    )
    await communicate.save(output_path)


def speak(text: str) -> bytes:
    """
    Convert text to speech and return audio bytes (MP3).
    Blocking wrapper around async edge-tts.
    """
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    try:
        asyncio.run(_synthesize(text, tmp_path))
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


def speak_to_file(text: str, output_path: str) -> None:
    """Save synthesized speech to a file."""
    asyncio.run(_synthesize(text, output_path))


async def list_voices() -> list[dict]:
    """List all available edge-tts voices."""
    voices = await edge_tts.list_voices()
    return [v for v in voices if v["Locale"].startswith("en-")]


def get_english_voices() -> list[str]:
    """Return list of English voice names."""
    voices = asyncio.run(list_voices())
    return [v["ShortName"] for v in voices]
