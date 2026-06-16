# server.py — FastAPI + WebSocket server for Yapper web interface

import asyncio
import json
import time
import tempfile
import os
import base64
import numpy as np
import wave
import io

from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager

from server.config.settings import SESSION_MAX_MINUTES, VOCAB_HOTKEY, BASE_DIR
from server.core.stt import transcribe, transcribe_async, ping as whisper_ping
from server.core.tts import speak_async
from server.core.llm import chat, ping as ollama_ping
from server.pedagogy.student_profile import load as load_profile, exists as profile_exists
from server.pedagogy.assessment import run_assessment
from server.pedagogy.error_tracker import SessionTracker
from server.pedagogy.lesson_planner import (
    run_post_session_analysis, generate_lesson_plan,
    load_current_plan, format_plan_for_prompt
)
from server.pedagogy.topics import suggest_topics, get_vocabulary, get_random_question, all_topic_names
from server.pedagogy.progress import get_progress_report, print_quick_stats
from server.pedagogy.prompts import build_tutor_prompt
from server.pedagogy.student_profile import update_after_session, set_level, create_interactive
from server.mictest_routes import router as mictest_router


app = FastAPI(title="Yapper")
app.include_router(mictest_router)

# Mount static files
STATIC_DIR = BASE_DIR / "client" / "main"
STATIC_DIR.mkdir(exist_ok=True)
#app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
# Основная статика (главное приложение)
app.mount("/static", StaticFiles(directory="client/main"), name="static")

# Статика для mictest (новая строка)
app.mount("/static/mictest", StaticFiles(directory="client/mictest"), name="mictest")

# --- Health endpoint ---
@app.get("/health")
async def health():
    return {
        "whisper": whisper_ping(),
        "ollama": ollama_ping(),
    }


@app.get("/profile")
async def get_profile():
    if not profile_exists():
        return {"exists": False}
    p = load_profile()
    return {"exists": True, "profile": p}


@app.get("/topics")
async def get_topics():
    return {"topics": all_topic_names()}


@app.get("/progress")
async def get_progress():
    if not profile_exists():
        return {"error": "No profile"}
    p = load_profile()
    report = get_progress_report(p["name"])
    return {"report": report}


@app.get("/")
async def root():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text())
    return HTMLResponse("<h1>Yapper starting...</h1>")

@app.get("/mictest")
async def mictest():
    path = BASE_DIR / "client" / "mictest" / "index.html"
    if path.exists():
        return HTMLResponse(path.read_text())
    return HTMLResponse("<h1>Mictest not found</h1>", status_code=404)

@app.get("/api/profile")
async def api_profile():
    if not profile_exists():
        return {"name": "Student"}
    p = load_profile()
    return {"name": p.get("name", "Student")}

@app.websocket("/ws")
async def websocket_session(ws: WebSocket):
    await ws.accept()

    async def send(msg_type: str, data: dict):
        await ws.send_text(json.dumps({"type": msg_type, **data}))

    try:
        # Send initial status
        await send("status", {
            "whisper": whisper_ping(),
            "ollama": ollama_ping(),
            "profile": load_profile() if profile_exists() else None,
        })

        # Wait for session start command
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            if msg["type"] == "start_session":
                topic = msg.get("topic")
                await run_session(ws, send, topic)

            elif msg["type"] == "save_profile":
                data = msg["data"]
                from server.pedagogy.student_profile import save, DEFAULT_PROFILE
                from datetime import datetime
                profile = DEFAULT_PROFILE.copy()
                profile.update(data)
                profile["created_at"] = datetime.now().isoformat()
                save(profile)
                await send("profile_saved", {"profile": profile})

            elif msg["type"] == "get_progress":
                p = load_profile()
                await send("progress", {"report": get_progress_report(p["name"])})

            elif msg["type"] == "reset_profile":
                from server.pedagogy.student_profile import reset
                reset()
                await send("profile_reset", {})

            elif msg["type"] == "set_level":
                from server.pedagogy.student_profile import set_level_manually
                try:
                    set_level_manually(msg["level"])
                    await send("level_updated", {"level": msg["level"]})
                except ValueError as e:
                    await send("error", {"message": str(e)})

            elif msg["type"] == "set_strictness":
                from server.pedagogy.student_profile import update_strictness
                try:
                    update_strictness(msg["level"])
                    await send("strictness_updated", {"level": msg["level"]})
                except ValueError as e:
                    await send("error", {"message": str(e)})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await send("error", {"message": str(e)})


async def run_session(ws: WebSocket, send, topic_override: str = None):
    """Run a full conversation session over WebSocket."""
    profile = load_profile()
    name = profile["name"]

    # Run assessment if needed
    if not profile.get("assessment_done"):
        await send("status_text", {"text": "Running initial assessment..."})
        await run_ws_assessment(ws, send, profile)
        profile = load_profile()
        generate_lesson_plan(profile)

    # Pick topic
    if topic_override:
        topic = topic_override
    else:
        suggested = suggest_topics(profile)
        topic = suggested[0] if suggested else "daily life"

    vocabulary = get_vocabulary(topic)
    plan = load_current_plan(name)
    plan_text = format_plan_for_prompt(plan)

    from server.pedagogy.error_tracker import get_recurring_errors, load_discovered_topics
    weak_points = get_recurring_errors(name)
    discovered_topics = load_discovered_topics(name)

    system_prompt = build_tutor_prompt(
        profile=profile,
        topic=topic,
        vocabulary=vocabulary,
        weak_points=weak_points,
        discovered_topics=discovered_topics,
        lesson_plan=plan_text,
    )

    messages = [{"role": "system", "content": system_prompt}]
    tracker = SessionTracker(student_name=name, topic=topic)
    session_start = time.time()
    active = True

    await send("session_started", {
        "topic": topic,
        "vocabulary": vocabulary[:10],
        "duration": profile.get("session_duration_minutes", 20),
    })

    # Opening question
    opening = (plan.get("opening_question") if plan else None) or get_random_question(topic)
    if opening:
        messages.append({"role": "assistant", "content": opening})
        audio = await speak_async(opening)
        import base64 as b64
        await send("assistant_message", {"text": opening, "audio": b64.b64encode(audio).decode()})

    # Main loop
    while active:
        elapsed = (time.time() - session_start) / 60
        if elapsed >= SESSION_MAX_MINUTES:
            await send("status_text", {"text": "Session time limit reached."})
            break

        # Wait for audio from client
        try:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=120.0)
        except asyncio.TimeoutError:
            break

        msg = json.loads(raw)

        if msg["type"] == "stop_session":
            active = False
            break

        elif msg["type"] == "change_topic":
            topic = msg.get("topic", topic)
            vocabulary = get_vocabulary(topic)
            tracker.topic = topic
            await send("topic_changed", {"topic": topic})
            continue

        elif msg["type"] == "vocab_flag":
            last_text = msg.get("context", "")
            tracker.flag_vocab_gap(context=last_text)
            await send("vocab_flagged", {"context": last_text})
            continue

        elif msg["type"] == "audio_chunk":
            # Receive audio bytes from browser
            import base64
            audio_bytes = base64.b64decode(msg["data"])

            await send("status_text", {"text": "Transcribing..."})
            user_text = await transcribe_async(audio_bytes)

            if not user_text:
                await send("status_text", {"text": "Could not understand. Try again."})
                continue

            await send("user_message", {"text": user_text})
            messages.append({"role": "user", "content": user_text})

            # Get LLM response
            await send("status_text", {"text": "Thinking..."})
            response_chunks = []
            for chunk in chat(messages, stream=True):
                response_chunks.append(chunk)

            raw_response = "".join(response_chunks)
            clean_response = tracker.parse_response(raw_response)
            messages.append({"role": "assistant", "content": clean_response})

            # TTS
            await send("status_text", {"text": "Speaking..."})
            audio = await speak_async(clean_response)
            import base64 as b64
            await send("assistant_message", {
                "text": clean_response,
                "audio": b64.b64encode(audio).decode()
            })

    # Post-session
    duration = int((time.time() - session_start) / 60)
    tracker.save()
    update_after_session(duration)

    await send("status_text", {"text": "Analysing session..."})
    analysis = run_post_session_analysis(
        profile=profile,
        topic=topic,
        duration=duration,
        error_log=tracker.get_error_summary(),
        vocab_gaps=tracker.get_vocab_summary(),
        discovered_topics=tracker.discovered_topics,
    )
    plan = generate_lesson_plan(profile)
    await send("session_ended", {
        "duration": duration,
        "errors": len(tracker.errors),
        "vocab_gaps": len(tracker.vocab_gaps),
        "next_topic": plan.get("topic", "TBD"),
    })


async def run_ws_assessment(ws: WebSocket, send, profile: dict):
    """Run assessment over WebSocket."""
    from server.pedagogy.assessment import ASSESSMENT_PROMPT
    topics = ", ".join(profile.get("preferred_topics", [])[:3]) or "general topics"
    professional = ", ".join(profile.get("professional_topics", [])) or "none"

    system_prompt = ASSESSMENT_PROMPT.format(
        native_language=profile.get("native_language", "Russian"),
        topics=topics,
        professional_topics=professional,
    )
    messages = [{"role": "system", "content": system_prompt}]
    result = None

    await send("assessment_started", {})

    for turn in range(10):
        response_chunks = []
        for chunk in chat(messages, stream=True):
            response_chunks.append(chunk)
        response = "".join(response_chunks)

        if '"level":' in response:
            import re, json as js
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    result = js.loads(match.group())
                    break
                except Exception:
                    pass

        messages.append({"role": "assistant", "content": response})
        audio = await speak_async(response)
        import base64 as b64
        await send("assistant_message", {
            "text": response,
            "audio": b64.b64encode(audio).decode()
        })

        try:
            raw = await asyncio.wait_for(ws.receive_text(), timeout=60.0)
            msg = json.loads(raw)
            if msg["type"] == "audio_chunk":
                import base64
                audio_bytes = base64.b64decode(msg["data"])
                user_text = await transcribe_async(audio_bytes)
                if user_text:
                    await send("user_message", {"text": user_text})
                    messages.append({"role": "user", "content": user_text})
        except asyncio.TimeoutError:
            break

    level = (result or {}).get("level", "B1")
    set_level(level)
    await send("assessment_done", {"level": level, "result": result})


if __name__ == "__main__":
    import uvicorn
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--ssl-certfile", default=None)
    parser.add_argument("--ssl-keyfile", default=None)
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()

    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=args.port,
        reload=False,
        ssl_certfile=args.ssl_certfile,
        ssl_keyfile=args.ssl_keyfile,
    )

# ========== MICROPHONE TEST ENDPOINTS ==========

@app.post("/api/mictest/noise")
async def measure_noise(request: Request):
    import soundfile as sf
    import io as _io

    data = await request.json()
    audio_base64 = data.get("audio_base64")

    if not audio_base64:
        raise HTTPException(status_code=400, detail="No audio data")

    audio_bytes = base64.b64decode(audio_base64)

    try:
        buf = _io.BytesIO(audio_bytes)
        audio_array, _ = sf.read(buf, dtype="float32")
    except Exception as e:
        # fallback: try av (for webm/opus)
        try:
            import av
            buf = _io.BytesIO(audio_bytes)
            container = av.open(buf)
            samples = []
            for frame in container.decode(audio=0):
                samples.append(frame.to_ndarray().flatten())
            audio_array = np.concatenate(samples).astype(np.float32)
            if audio_array.max() > 1.0:
                audio_array /= 32768.0
        except Exception as e2:
            return {"noise_db": -99, "level": "unknown", "advice": f"Could not decode audio: {e2}"}

    rms = np.sqrt(np.mean(audio_array**2))
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


@app.post("/api/mictest/test_phrase")
async def test_phrase(request: Request):
    import base64
    
    data = await request.json()
    audio_base64 = data.get("audio_base64")
    expected_text = data.get("expected_text")
    
    if not audio_base64 or not expected_text:
        raise HTTPException(status_code=400, detail="Missing audio or expected text")
    
    # Декодируем
    audio_bytes = base64.b64decode(audio_base64)
    
    # Real Whisper transcription
    try:
        transcribed = await transcribe_async(audio_bytes) or ""
    except Exception as e:
        transcribed = ""
    
    # Вычисляем WER
    expected_words = expected_text.lower().split()
    transcribed_words = transcribed.lower().split()
    
    matches = 0
    i = 0
    j = 0
    while i < len(expected_words) and j < len(transcribed_words):
        if expected_words[i] == transcribed_words[j]:
            matches += 1
            i += 1
            j += 1
        else:
            i += 1
            j += 1
    
    wer = (1 - matches / max(len(expected_words), 1)) * 100
    
    if wer == 0:
        advice = "Отлично! Распознавание работает идеально."
    elif wer < 20:
        advice = "Хорошо. Можно улучшить, говоря чуть чётче."
    elif wer < 50:
        advice = "Средний результат. Проверьте уровень громкости и фоновый шум."
    else:
        advice = "Низкая точность. Настройте микрофон заново."
    
    return {
        "transcribed": transcribed,
        "wer": round(wer, 1),
        "advice": advice
    }


@app.post("/api/mictest/save")
async def save_calibration(request: Request):
    import json
    import os
    
    data = await request.json()
    profile_name = data.get("profile_name")
    calibration = data.get("calibration")
    
    if not profile_name or not calibration:
        raise HTTPException(status_code=400, detail="Missing profile or calibration data")
    
    # Путь к файлу профиля
    profile_path = f"student_profile.json"
    
    # Загружаем существующий профиль или создаём новый
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            profile = json.load(f)
    else:
        profile = {"name": profile_name}
    
    # Добавляем калибровку
    profile["microphone_calibration"] = calibration
    
    # Сохраняем
    with open(profile_path, 'w') as f:
        json.dump(profile, f, indent=2)
    
    return {"status": "saved"}


@app.post("/api/mictest/reset")
async def reset_calibration(request: Request):
    import json
    import os
    
    data = await request.json()
    profile_name = data.get("profile_name")
    
    if not profile_name:
        raise HTTPException(status_code=400, detail="Missing profile name")
    
    profile_path = f"student_profile.json"
    
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            profile = json.load(f)
        
        if "microphone_calibration" in profile:
            del profile["microphone_calibration"]
        
        with open(profile_path, 'w') as f:
            json.dump(profile, f, indent=2)
    
    return {"status": "reset"}

