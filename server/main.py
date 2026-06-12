# main.py — Yapper entry point

import sys
import time
from datetime import datetime

from server.config.settings import SESSION_MAX_MINUTES, VOCAB_HOTKEY
from server.core.audio import start_hotkey_listener, record_until_silence, play_audio, is_paused, pop_vocab_flag
from server.core.stt import transcribe, ping as whisper_ping
from server.core.tts import speak
from server.core.llm import chat, ping as ollama_ping
from server.pedagogy.student_profile import load as load_profile, create_interactive, exists as profile_exists, update_after_session, set_level
from server.pedagogy.assessment import run_assessment
from server.pedagogy.error_tracker import SessionTracker
from server.pedagogy.lesson_planner import run_post_session_analysis, generate_lesson_plan, load_current_plan, format_plan_for_prompt
from server.pedagogy.topics import suggest_topics, get_vocabulary, get_random_question
from server.pedagogy.progress import get_progress_report, print_quick_stats
from server.pedagogy.prompts import build_tutor_prompt


def check_services() -> bool:
    """Check that Whisper and Ollama are reachable."""
    print("[Yapper] Checking services...")
    ok = True
    if not whisper_ping():
        print("[Yapper] ERROR: Whisper server not reachable. Check WHISPER_URL in .env")
        ok = False
    else:
        print("[Yapper] Whisper ✓")
    if not ollama_ping():
        print("[Yapper] ERROR: Ollama not reachable. Check OLLAMA_URL in .env")
        ok = False
    else:
        print("[Yapper] Ollama ✓")
    return ok


def speak_and_print(text: str) -> None:
    """Print and speak text."""
    print(f"\n[Yapper]: {text}")
    audio = speak(text)
    play_audio(audio, format="mp3")


def listen() -> str | None:
    """Record mic and transcribe."""
    audio = record_until_silence()
    if not audio:
        return None
    text = transcribe(audio)
    if text:
        print(f"[You]: {text}")
    return text or None


def run_session(profile: dict) -> None:
    """Run a single conversation session."""
    name = profile["name"]

    # Pick topic
    suggested = suggest_topics(profile)
    topic = suggested[0] if suggested else "daily life"
    vocabulary = get_vocabulary(topic)

    # Load lesson plan
    plan = load_current_plan(name)
    plan_text = format_plan_for_prompt(plan)

    # Load context from previous sessions
    from server.pedagogy.error_tracker import get_recurring_errors, load_discovered_topics
    weak_points = get_recurring_errors(name)
    discovered_topics = load_discovered_topics(name)

    # Build system prompt
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
    last_user_text = ""

    print(f"\n[Yapper] Session started. Topic: {topic}")
    print(f"[Yapper] Press Right Ctrl to pause/resume. Press {VOCAB_HOTKEY} to flag a vocabulary gap.")
    print("[Yapper] Press Ctrl+C to end session.\n")

    # Opening message from tutor
    opening = get_random_question(topic) if not plan else plan.get("opening_question", get_random_question(topic))
    if opening:
        messages.append({"role": "assistant", "content": opening})
        speak_and_print(opening)

    try:
        while True:
            # Check session time limit
            elapsed = (time.time() - session_start) / 60
            if elapsed >= SESSION_MAX_MINUTES:
                speak_and_print("We've reached the end of our session time. Great work today!")
                break

            if is_paused():
                time.sleep(0.5)
                continue

            # Check vocab gap flag
            if pop_vocab_flag():
                tracker.flag_vocab_gap(context=last_user_text)

            # Listen
            user_text = listen()
            if not user_text:
                continue

            last_user_text = user_text

            # Check for commands
            lower = user_text.lower().strip()
            if any(cmd in lower for cmd in ["stop session", "end session", "goodbye yapper", "stop lesson"]):
                speak_and_print("Great session! Let me prepare your summary.")
                break
            if any(cmd in lower for cmd in ["my progress", "show progress", "how am i doing"]):
                print_quick_stats(name)
                speak_and_print("I've shown your stats on screen.")
                continue

            messages.append({"role": "user", "content": user_text})

            # Get tutor response
            response_chunks = []
            for chunk in chat(messages, stream=True):
                response_chunks.append(chunk)
                print(chunk, end="", flush=True)
            print()
            raw_response = "".join(response_chunks)

            # Parse and clean response (strip error tags)
            clean_response = tracker.parse_response(raw_response)
            messages.append({"role": "assistant", "content": clean_response})

            # Speak clean response
            audio = speak(clean_response)
            play_audio(audio, format="mp3")

    except KeyboardInterrupt:
        print("\n[Yapper] Session interrupted.")

    # Post-session
    duration = int((time.time() - session_start) / 60)
    log_path = tracker.save()
    update_after_session(duration)

    print(f"\n[Yapper] Session ended. Duration: {duration} min.")
    print("[Yapper] Running post-session analysis...")

    analysis = run_post_session_analysis(
        profile=profile,
        topic=topic,
        duration=duration,
        error_log=tracker.get_error_summary(),
        vocab_gaps=tracker.get_vocab_summary(),
        discovered_topics=tracker.discovered_topics,
    )

    plan = generate_lesson_plan(profile)
    next_topic = plan.get("topic", "TBD")
    speak_and_print(f"Great work today! We practised {topic}. Next time we'll focus on {next_topic}. See you soon!")


def main() -> None:
    print("\n" + "="*50)
    print("  Yapper — Your Personal English Tutor")
    print("="*50 + "\n")

    # Check services
    if not check_services():
        sys.exit(1)

    # Start hotkey listener
    listener = start_hotkey_listener()

    # Load or create profile
    if not profile_exists():
        profile = create_interactive()
    else:
        profile = load_profile()
        print(f"[Yapper] Welcome back, {profile['name']}!")

    # Run assessment on first session
    if not profile.get("assessment_done"):
        print("\n[Yapper] Let's start with a quick level assessment.")
        result = run_assessment(
            profile=profile,
            speak_fn=speak_and_print,
            listen_fn=listen,
        )
        set_level(result.get("level", "B1"))
        profile = load_profile()
        generate_lesson_plan(profile)

    # Main menu
    while True:
        print("\nWhat would you like to do?")
        print("  1. Start a session")
        print("  2. View progress")
        print("  3. Exit")
        choice = input("> ").strip()

        if choice == "1":
            run_session(load_profile())
        elif choice == "2":
            print(get_progress_report(profile["name"]))
        elif choice == "3":
            print("[Yapper] Goodbye!")
            break
        else:
            print("Please enter 1, 2, or 3.")


if __name__ == "__main__":
    main()
