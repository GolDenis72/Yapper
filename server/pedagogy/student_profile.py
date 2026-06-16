# pedagogy/student_profile.py — Student profile management

import json
from pathlib import Path
from datetime import datetime
from server.config.settings import BASE_DIR

PROFILE_PATH = BASE_DIR / "student_profile.json"

DEFAULT_PROFILE = {
    "name": "",
    "native_language": "Russian",
    "cefr_level": None,
    "target_level": "B2",
    "session_duration_minutes": 20,
    "preferred_topics": [],
    "professional_topics": [],       # e.g. ["accounting", "finance", "fishing"]
    "strictness": "balanced",        # "relaxed" / "balanced" / "strict"
    "created_at": None,
    "last_session_at": None,
    "total_sessions": 0,
    "total_minutes": 0,
    "assessment_done": False,
}


def load() -> dict:
    if PROFILE_PATH.exists():
        with open(PROFILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_PROFILE.copy()


def save(profile: dict) -> None:
    PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)


def exists() -> bool:
    if not PROFILE_PATH.exists():
        return False
    p = load()
    return bool(p.get("name"))


def create_interactive() -> dict:
    """
    Interactive profile creation. Called on first run.
    Returns the created profile.
    """
    print("\n" + "="*50)
    print("  Welcome to Yapper! Let's set up your profile.")
    print("="*50 + "\n")

    profile = DEFAULT_PROFILE.copy()
    profile["created_at"] = datetime.now().isoformat()

    profile["name"] = input("Your name: ").strip() or "Student"

    print("\nHow long would you like each session to be?")
    print("  1. 15 minutes")
    print("  2. 20 minutes (recommended)")
    print("  3. 30 minutes")
    print("  4. 45 minutes")
    choice = input("Choose (1-4) [2]: ").strip() or "2"
    durations = {"1": 15, "2": 20, "3": 30, "4": 45}
    profile["session_duration_minutes"] = durations.get(choice, 20)

    print("\nWhat topics interest you for conversation? (select all that apply)")
    available_topics = [
        "travel", "food & cooking", "work & career",
        "technology", "sports", "music & arts",
        "nature & environment", "daily life", "news & current events"
    ]
    for i, topic in enumerate(available_topics, 1):
        print(f"  {i}. {topic}")
    choices = input("Enter numbers separated by comma (e.g. 1,3,5) or press Enter for all: ").strip()
    if choices:
        indices = [int(x.strip()) - 1 for x in choices.split(",") if x.strip().isdigit()]
        profile["preferred_topics"] = [available_topics[i] for i in indices if 0 <= i < len(available_topics)]
    else:
        profile["preferred_topics"] = available_topics

    print("\nDo you have any professional or special topics you want to focus on?")
    print("  Examples: accounting, finance, medicine, fishing, cooking, IT, law")
    print("  Enter topics separated by comma, or press Enter to skip:")
    prof_input = input("> ").strip()
    if prof_input:
        profile["professional_topics"] = [t.strip() for t in prof_input.split(",") if t.strip()]
    else:
        profile["professional_topics"] = []

    save(profile)
    print(f"\nProfile created! Welcome, {profile['name']}!")
    print("We'll start with a short level assessment to personalize your lessons.\n")
    return profile


def update_after_session(duration_minutes: int) -> None:
    profile = load()
    profile["last_session_at"] = datetime.now().isoformat()
    profile["total_sessions"] = profile.get("total_sessions", 0) + 1
    profile["total_minutes"] = profile.get("total_minutes", 0) + duration_minutes
    save(profile)


def set_level(cefr_level: str) -> None:
    profile = load()
    profile["cefr_level"] = cefr_level
    profile["assessment_done"] = True
    save(profile)
    print(f"\n[Yapper] Level set to {cefr_level}")


def summary() -> str:
    p = load()
    lines = [
        f"Name: {p['name']}",
        f"Current level: {p.get('cefr_level') or 'not assessed yet'}",
        f"Target level: {p['target_level']}",
        f"Sessions completed: {p['total_sessions']}",
        f"Total practice time: {p['total_minutes']} minutes",
        f"Favourite topics: {', '.join(p['preferred_topics'][:3]) or 'not set'}",
        f"Professional topics: {', '.join(p['professional_topics']) or 'not set'}",
    ]
    return "\n".join(lines)
