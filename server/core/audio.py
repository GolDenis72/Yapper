# core/audio.py — microphone capture, playback, hotkeys

import io
import wave
import threading
import numpy as np
import sounddevice as sd
import soundfile as sf
from pynput import keyboard
from config.settings import (
    AUDIO_SAMPLE_RATE,
    AUDIO_CHANNELS,
    SILENCE_THRESHOLD,
    VOCAB_HOTKEY,
)

# --- State ---
_paused = False
_vocab_flag = False
_pause_lock = threading.Lock()


# --- Hotkey listener ---
def _on_press(key):
    global _paused, _vocab_flag
    try:
        # Right Ctrl — pause/resume
        if key == keyboard.Key.ctrl_r:
            with _pause_lock:
                _paused = not _paused
            state = "PAUSED" if _paused else "RESUMED"
            print(f"\n[Yapper] {state} (Right Ctrl)")

        # F9 (default) — vocabulary gap flag
        if hasattr(key, 'name') and key.name == VOCAB_HOTKEY.lower().replace("f", "f"):
            _vocab_flag = True
            print("\n[Yapper] Vocabulary gap flagged (F9)")
        elif hasattr(key, '_name_') and key._name_ == VOCAB_HOTKEY:
            _vocab_flag = True

    except Exception:
        pass


def start_hotkey_listener() -> keyboard.Listener:
    """Start background hotkey listener. Call once at startup."""
    listener = keyboard.Listener(on_press=_on_press)
    listener.daemon = True
    listener.start()
    return listener


def is_paused() -> bool:
    with _pause_lock:
        return _paused


def pop_vocab_flag() -> bool:
    """Returns True and resets flag if vocabulary gap was flagged."""
    global _vocab_flag
    if _vocab_flag:
        _vocab_flag = False
        return True
    return False


# --- Recording ---
def record_until_silence(
    silence_duration: float = SILENCE_THRESHOLD,
    max_duration: float = 30.0,
    rms_threshold: float = 0.01,
) -> bytes | None:
    """
    Record from microphone until silence or max_duration.
    Respects pause state — returns None if paused.
    Returns WAV bytes.
    """
    if is_paused():
        return None

    sample_rate = AUDIO_SAMPLE_RATE
    chunk_size = int(sample_rate * 0.1)  # 100ms chunks
    max_chunks = int(max_duration / 0.1)
    silence_chunks = int(silence_duration / 0.1)

    frames = []
    silent_count = 0
    recording_started = False

    print("[Yapper] Listening...", end="", flush=True)

    with sd.InputStream(samplerate=sample_rate, channels=AUDIO_CHANNELS, dtype="float32") as stream:
        for _ in range(max_chunks):
            if is_paused():
                print("\n[Yapper] Paused mid-recording")
                break

            chunk, _ = stream.read(chunk_size)
            rms = float(np.sqrt(np.mean(chunk ** 2)))

            if rms > rms_threshold:
                recording_started = True
                silent_count = 0
                frames.append(chunk)
                print(".", end="", flush=True)
            elif recording_started:
                frames.append(chunk)
                silent_count += 1
                if silent_count >= silence_chunks:
                    break

    print()  # newline after dots

    if not frames or not recording_started:
        return None

    audio_data = np.concatenate(frames, axis=0)
    return _numpy_to_wav(audio_data, sample_rate)


def _numpy_to_wav(audio: np.ndarray, sample_rate: int) -> bytes:
    """Convert numpy float32 array to WAV bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(AUDIO_CHANNELS)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        pcm = (audio * 32767).astype(np.int16)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()


# --- Playback ---
def play_audio(audio_bytes: bytes, format: str = "mp3") -> None:
    """
    Play audio bytes (MP3 or WAV) through speakers.
    Blocks until playback is complete.
    """
    buf = io.BytesIO(audio_bytes)
    data, sample_rate = sf.read(buf, dtype="float32")
    sd.play(data, sample_rate)
    sd.wait()
