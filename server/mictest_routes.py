# server/mictest_routes.py — Microphone test endpoints

import base64
import io
import numpy as np
from fastapi import APIRouter, Request, HTTPException
from server.core.stt import transcribe_async as transcribe

router = APIRouter(prefix="/api/mictest")


@router.post("/noise")
async def measure_noise(request: Request):
    """Measure background noise level from 3 seconds of silence."""
    data = await request.json()
    audio_base64 = data.get("audio_base64")

    if not audio_base64:
        raise HTTPException(status_code=400, detail="No audio data")

    audio_bytes = base64.b64decode(audio_base64)

    try:
        import av
        buf = io.BytesIO(audio_bytes)
        container = av.open(buf)
        samples = []
        for frame in container.decode(audio=0):
            arr = frame.to_ndarray().flatten().astype(np.float32)
            samples.append(arr)
        if not samples:
            raise ValueError("No audio frames decoded")
        audio_array = np.concatenate(samples)
        if audio_array.max() > 1.0:
            audio_array /= 32768.0
    except Exception as e:
        try:
            import soundfile as sf
            buf = io.BytesIO(audio_bytes)
            audio_array, _ = sf.read(buf, dtype="float32")
        except Exception as e2:
            return {
                "noise_db": -99,
                "level": "unknown",
                "advice": f"Could not decode audio: {e2}"
            }

    rms = np.sqrt(np.mean(audio_array ** 2))
    rms_db = float(20 * np.log10(rms + 1e-10))

    if rms_db < -50:
        level = "low"
        advice = "Отлично! Фоновый шум очень низкий."
    elif rms_db < -35:
        level = "medium"
        advice = "Приемлемо. Шумодав поможет улучшить распознавание."
    else:
        level = "high"
        advice = "Высокий уровень шума. Выключите вентилятор, закройте окно."

    return {
        "noise_db": round(rms_db, 1),
        "level": level,
        "advice": advice
    }


@router.post("/test_phrase")
async def test_phrase(request: Request):
    """Transcribe a test phrase and compare with expected."""
    data = await request.json()
    audio_base64 = data.get("audio_base64")
    expected_text = data.get("expected_text", "")

    if not audio_base64:
        raise HTTPException(status_code=400, detail="No audio data")

    audio_bytes = base64.b64decode(audio_base64)

    try:
        transcribed = await transcribe_async(audio_bytes) or ""
    except Exception as e:
        return {
            "transcribed": "",
            "expected": expected_text,
            "wer": 1.0,
            "accuracy": 0,
            "error": str(e)
        }

    # Calculate word error rate
    wer, accuracy = _calculate_wer(expected_text, transcribed)

    return {
        "transcribed": transcribed,
        "expected": expected_text,
        "wer": round(wer, 2),
        "accuracy": round(accuracy, 1),
    }


def _calculate_wer(expected: str, transcribed: str) -> tuple[float, float]:
    """Simple word error rate calculation."""
    expected_words = expected.lower().split()
    transcribed_words = transcribed.lower().split()

    if not expected_words:
        return 0.0, 100.0

    # Count matching words
    matches = sum(1 for w in transcribed_words if w in expected_words)
    accuracy = (matches / len(expected_words)) * 100
    wer = 1.0 - (matches / len(expected_words))

    return wer, accuracy
