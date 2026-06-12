# core/llm.py — Ollama interface

import httpx
import json
from typing import Generator
from server.config.settings import OLLAMA_URL, OLLAMA_MODEL, OLLAMA_MAX_TOKENS


def chat(messages: list[dict], stream: bool = True) -> Generator[str, None, None] | str:
    """
    Send messages to Ollama and get a response.
    messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
    stream=True: yields text chunks as they arrive (lower latency for TTS)
    stream=False: returns full response string
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": stream,
        "options": {
            "num_predict": OLLAMA_MAX_TOKENS,
            "temperature": 0.7,
        }
    }

    if stream:
        return _stream_response(payload)
    else:
        return _full_response(payload)


def _stream_response(payload: dict) -> Generator[str, None, None]:
    with httpx.Client(timeout=60.0) as client:
        with client.stream("POST", f"{OLLAMA_URL}/api/chat", json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if token := chunk.get("message", {}).get("content", ""):
                        yield token
                    if chunk.get("done"):
                        break


def _full_response(payload: dict) -> str:
    payload["stream"] = False
    with httpx.Client(timeout=60.0) as client:
        response = client.post(f"{OLLAMA_URL}/api/chat", json=payload)
        response.raise_for_status()
        return response.json()["message"]["content"]


def ping() -> bool:
    """Check if Ollama is reachable."""
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{OLLAMA_URL}/api/tags")
            return r.status_code == 200
    except Exception:
        return False
