# Yapper — configuration
# Copy .env.example to .env and fill in your values

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / "logs"
ERRORS_DIR = LOGS_DIR / "errors"
VOCAB_DIR = LOGS_DIR / "vocabulary"
PLANS_DIR = BASE_DIR / "lessons" / "plans"

# --- STT (Whisper) ---
WHISPER_URL = os.getenv("WHISPER_URL", "http://localhost:9001")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "en")

# --- LLM (Ollama) ---
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral:7b")
OLLAMA_MAX_TOKENS = int(os.getenv("OLLAMA_MAX_TOKENS", "150"))  # short answers for conversation

# --- TTS (edge-tts) ---
TTS_VOICE = os.getenv("TTS_VOICE", "en-GB-RyanNeural")  # British male, clear accent
TTS_RATE = os.getenv("TTS_RATE", "+0%")
TTS_VOLUME = os.getenv("TTS_VOLUME", "+0%")

# --- Audio ---
AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1
SILENCE_THRESHOLD = float(os.getenv("SILENCE_THRESHOLD", "0.5"))  # seconds of silence to stop recording
VAD_SENSITIVITY = int(os.getenv("VAD_SENSITIVITY", "2"))  # 1-3, higher = more sensitive

# --- Pedagogy ---
CEFR_LEVEL = os.getenv("CEFR_LEVEL", "B1")  # starting level, updated after assessment
VOCAB_HOTKEY = os.getenv("VOCAB_HOTKEY", "F9")  # press when you used a Russian word

# --- Session ---
SESSION_MAX_MINUTES = int(os.getenv("SESSION_MAX_MINUTES", "30"))
