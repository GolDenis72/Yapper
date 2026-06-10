# pedagogy/assessment.py — CEFR level assessment on first run

import json
from datetime import datetime
from pathlib import Path
from core.llm import chat
from config.settings import BASE_DIR

ASSESSMENT_LOG_PATH = BASE_DIR / "logs" / "assessment.json"

ASSESSMENT_PROMPT = """You are an expert English language assessor using the CEFR framework.
Your task is to assess a student's spoken English level through a natural conversation.

Rules:
- Ask 6-8 questions of gradually increasing complexity
- Start simple (A1-A2): greetings, daily routine, simple descriptions
- Move to intermediate (B1): opinions, past experiences, future plans
- Try advanced (B2): abstract topics, hypothetical situations, complex ideas
- After each answer, internally note: grammar accuracy, vocabulary range, fluency, complexity
- Keep the conversation natural — do NOT tell the student you are assessing them
- Do NOT correct any mistakes during assessment — just listen and observe
- Never interrupt or comment on errors — silently note them for the assessment result
- At the end, output ONLY a JSON block like this:
  {"level": "B1", "reasoning": "...", "strong_points": [...], "weak_points": [...]}

Student profile:
- Native language: {native_language}
- Preferred topics: {topics}
- Professional/special topics: {professional_topics}

Start with a warm, friendly greeting and first question."""


def run_assessment(profile: dict, speak_fn, listen_fn) -> dict:
    """
    Run interactive CEFR assessment.
    speak_fn: function(text) -> plays audio
    listen_fn: function() -> returns transcribed text
    Returns assessment result dict.
    """
    print("\n[Yapper] Starting level assessment...\n")

    topics = ", ".join(profile.get("preferred_topics", [])[:3]) or "general topics"
    professional = ", ".join(profile.get("professional_topics", [])) or "none"

    system_prompt = ASSESSMENT_PROMPT.format(
        native_language=profile.get("native_language", "Russian"),
        topics=topics,
        professional_topics=professional,
    )

    messages = [{"role": "system", "content": system_prompt}]
    conversation_log = []
    result = None

    for turn in range(10):  # max 10 turns
        # Get model response
        response_chunks = []
        for chunk in chat(messages, stream=True):
            response_chunks.append(chunk)
            print(chunk, end="", flush=True)
        response = "".join(response_chunks)
        print()

        # Check if assessment is complete (JSON block present)
        if '{"level":' in response or '"level":' in response:
            result = _extract_json(response)
            break

        messages.append({"role": "assistant", "content": response})
        conversation_log.append({"role": "assistant", "content": response})

        # Speak the question
        speak_fn(response)

        # Listen for student answer
        print(f"\n[Yapper] Your turn (question {turn + 1})...")
        user_input = listen_fn()
        if not user_input:
            continue

        print(f"[You]: {user_input}")
        messages.append({"role": "user", "content": user_input})
        conversation_log.append({"role": "user", "content": user_input})

    if not result:
        # Fallback — ask model to evaluate now
        messages.append({
            "role": "user",
            "content": "Please provide your CEFR assessment now as a JSON block."
        })
        response_chunks = []
        for chunk in chat(messages, stream=False):
            response_chunks.append(chunk)
        result = _extract_json("".join(response_chunks)) or {"level": "B1"}

    # Save assessment log
    log = {
        "date": datetime.now().isoformat(),
        "student": profile.get("name"),
        "result": result,
        "conversation": conversation_log,
    }
    _save_log(log)

    level = result.get("level", "B1")
    print(f"\n[Yapper] Assessment complete! Your level: {level}")
    if result.get("strong_points"):
        print(f"Strong points: {', '.join(result['strong_points'])}")
    if result.get("weak_points"):
        print(f"Areas to work on: {', '.join(result['weak_points'])}")

    return result


def _extract_json(text: str) -> dict | None:
    """Extract JSON block from model response."""
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return None


def _save_log(log: dict) -> None:
    ASSESSMENT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ASSESSMENT_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)
