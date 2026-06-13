# pedagogy/lesson_planner.py — Post-session analysis and lesson plan generation

import json
from datetime import datetime
from pathlib import Path
from core.llm import chat
from config.settings import PLANS_DIR
from pedagogy.prompts import build_analysis_prompt, build_lesson_plan_prompt
from pedagogy.error_tracker import (
    load_recent_errors, get_recurring_errors,
    load_vocab_gaps, load_discovered_topics
)


def run_post_session_analysis(
    profile: dict,
    topic: str,
    duration: int,
    error_log: str,
    vocab_gaps: list,
    discovered_topics: list,
) -> dict:
    """
    Run post-session analysis via LLM.
    Returns analysis dict.
    """
    print("\n[Yapper] Analysing session...")

    prompt = build_analysis_prompt(
        profile=profile,
        topic=topic,
        duration=duration,
        error_log=error_log,
        vocab_gaps=vocab_gaps,
        discovered_topics=discovered_topics,
    )

    messages = [
        {"role": "system", "content": "You are an expert English language analyst. Always respond with valid JSON only."},
        {"role": "user", "content": prompt},
    ]

    response = chat(messages, stream=False)
    analysis = _extract_json(response)

    if not analysis:
        print("[Yapper] Warning: could not parse analysis JSON, saving raw response.")
        analysis = {"raw": response}

    # Save analysis
    _save_analysis(profile["name"], topic, analysis)
    return analysis


def generate_lesson_plan(profile: dict) -> dict:
    """
    Generate lesson plan for next session based on history.
    Returns lesson plan dict.
    """
    print("\n[Yapper] Generating lesson plan for next session...")

    name = profile["name"]
    last_analysis = _load_last_analysis(name)
    recurring_errors = get_recurring_errors(name)
    vocab_gaps = load_vocab_gaps(name)
    discovered_topics = load_discovered_topics(name)

    prompt = build_lesson_plan_prompt(
        profile=profile,
        last_analysis=json.dumps(last_analysis, ensure_ascii=False) if last_analysis else "",
        recurring_errors=recurring_errors,
        vocab_gaps=vocab_gaps,
        discovered_topics=discovered_topics,
    )

    messages = [
        {"role": "system", "content": "You are an expert English language teacher. Always respond with valid JSON only."},
        {"role": "user", "content": prompt},
    ]

    response = chat(messages, stream=False)
    plan = _extract_json(response)

    if not plan:
        print("[Yapper] Warning: could not parse lesson plan JSON.")
        plan = {"raw": response}

    # Save plan
    _save_plan(name, plan)
    print(f"[Yapper] Lesson plan ready. Next topic: {plan.get('topic', 'TBD')}")
    return plan


def load_current_plan(student_name: str) -> dict | None:
    """Load the most recent lesson plan for a student."""
    if not PLANS_DIR.exists():
        return None

    files = sorted(
        [f for f in PLANS_DIR.glob(f"*_{student_name}.json")],
        reverse=True
    )
    if not files:
        return None

    with open(files[0], encoding="utf-8") as f:
        return json.load(f)


def format_plan_for_prompt(plan: dict) -> str:
    """Format lesson plan as readable text for system prompt."""
    if not plan:
        return "No plan yet — free conversation."

    lines = []
    if plan.get("grammar_focus"):
        lines.append(f"Grammar focus: {plan['grammar_focus']}")
    if plan.get("vocabulary_focus"):
        lines.append(f"Vocabulary to introduce: {', '.join(plan['vocabulary_focus'][:8])}")
    if plan.get("opening_question"):
        lines.append(f"Start with: {plan['opening_question']}")
    if plan.get("callback_question"):
        lines.append(f"Reference from last session: {plan['callback_question']}")
    return "\n".join(lines) if lines else "Free conversation."


def _save_analysis(student_name: str, topic: str, analysis: dict) -> Path:
    from config.settings import ERRORS_DIR
    analysis_dir = ERRORS_DIR.parent / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M')}_{student_name}.json"
    path = analysis_dir / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"topic": topic, "date": datetime.now().isoformat(), "analysis": analysis},
                  f, indent=2, ensure_ascii=False)
    return path


def _save_plan(student_name: str, plan: dict) -> Path:
    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M')}_{student_name}.json"
    path = PLANS_DIR / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, ensure_ascii=False)
    return path


def _load_last_analysis(student_name: str) -> dict | None:
    from config.settings import ERRORS_DIR
    analysis_dir = ERRORS_DIR.parent / "analysis"
    if not analysis_dir.exists():
        return None
    files = sorted(
        [f for f in analysis_dir.glob(f"*_{student_name}.json")],
        reverse=True
    )
    if not files:
        return None
    with open(files[0], encoding="utf-8") as f:
        data = json.load(f)
        return data.get("analysis")


def _extract_json(text: str) -> dict | None:
    try:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except Exception:
        pass
    return None
