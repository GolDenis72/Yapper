# core/tts.py — Text-to-Speech via edge-tts

import asyncio
import tempfile
import os
import edge_tts
from server.config.settings import TTS_VOICE, TTS_RATE, TTS_VOLUME


async def _synthesize(text: str, output_path: str) -> None:
    text = strip_emojis(text)
    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate=TTS_RATE,
        volume=TTS_VOLUME,
    )
    await communicate.save(output_path)


def strip_emojis(text: str) -> str:
    """Remove emoji characters from text before TTS."""
    import re
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002700-\U000027BF"
        u"\U0001F900-\U0001F9FF"
        u"\u2600-\u26FF"
        u"\u2700-\u27BF"
        "]+", flags=re.UNICODE
    )
    return emoji_pattern.sub("", text).strip()


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
