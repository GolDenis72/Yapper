# pedagogy/progress.py — Progress tracking and statistics display

import json
from datetime import datetime
from pathlib import Path
from config.settings import ERRORS_DIR, BASE_DIR

PROGRESS_PATH = BASE_DIR / "logs" / "progress.json"

CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def record_monthly_test(student_name: str, result: dict) -> None:
    """Save monthly test result to progress log."""
    log = _load_progress_log(student_name)
    log["tests"].append({
        "date": datetime.now().isoformat(),
        "result": result,
    })
    _save_progress_log(student_name, log)
    print(f"[Yapper] Monthly test recorded. Level: {result.get('assessed_level')}")


def get_progress_report(student_name: str) -> str:
    """Return a human-readable progress report."""
    from pedagogy.student_profile import load as load_profile
    profile = load_profile()
    log = _load_progress_log(student_name)

    lines = [
        "=" * 50,
        f"  Progress Report — {student_name}",
        "=" * 50,
        "",
        f"Started at:       {profile.get('cefr_level', 'unknown')} (assessed on first session)",
        f"Current level:    {profile.get('cefr_level', 'unknown')}",
        f"Target level:     {profile.get('target_level', 'B2')}",
        f"Sessions done:    {profile.get('total_sessions', 0)}",
        f"Total time:       {profile.get('total_minutes', 0)} minutes",
        "",
    ]

    # Error trends
    error_stats = _get_error_stats(student_name)
    if error_stats:
        lines.append("Top recurring errors:")
        for error_type, count in sorted(error_stats.items(), key=lambda x: -x[1])[:5]:
            lines.append(f"  {error_type}: {count} times")
        lines.append("")

    # Monthly test history
    tests = log.get("tests", [])
    if tests:
        lines.append("Monthly test history:")
        for t in tests[-6:]:  # last 6 tests
            date = t["date"][:10]
            level = t["result"].get("assessed_level", "?")
            score = t["result"].get("overall_score", "?")
            progress = t["result"].get("progress", "")
            lines.append(f"  {date}: {level} (score {score}/10) — {progress}")
        lines.append("")

    # Level progress visualization
    current = profile.get("cefr_level", "B1")
    target = profile.get("target_level", "B2")
    lines.append(_level_progress_bar(current, target))
    lines.append("")
    lines.append("=" * 50)

    return "\n".join(lines)


def get_session_streak(student_name: str) -> int:
    """Count consecutive days with at least one session."""
    if not ERRORS_DIR.exists():
        return 0

    files = sorted(
        [f for f in ERRORS_DIR.glob(f"*_{student_name}.json")],
        reverse=True
    )
    if not files:
        return 0

    streak = 0
    prev_date = None
    for f in files:
        date_str = f.name[:8]  # YYYYMMDD
        try:
            date = datetime.strptime(date_str, "%Y%m%d").date()
        except ValueError:
            continue

        if prev_date is None:
            prev_date = date
            streak = 1
        elif (prev_date - date).days == 1:
            streak += 1
            prev_date = date
        else:
            break

    return streak


def print_quick_stats(student_name: str) -> None:
    """Print a short stats summary to terminal."""
    from pedagogy.student_profile import load as load_profile
    profile = load_profile()
    streak = get_session_streak(student_name)

    print("\n[Yapper] Your stats:")
    print(f"  Level:    {profile.get('cefr_level', 'not assessed')}")
    print(f"  Sessions: {profile.get('total_sessions', 0)}")
    print(f"  Time:     {profile.get('total_minutes', 0)} min total")
    print(f"  Streak:   {streak} day(s) in a row")


def _level_progress_bar(current: str, target: str) -> str:
    """Visual progress bar between current and target CEFR level."""
    if current not in CEFR_ORDER or target not in CEFR_ORDER:
        return f"Level: {current} → {target}"

    curr_idx = CEFR_ORDER.index(current)
    tgt_idx = CEFR_ORDER.index(target)

    bar = ""
    for i, level in enumerate(CEFR_ORDER):
        if i < curr_idx:
            bar += f"[{level}✓] "
        elif i == curr_idx:
            bar += f"[{level}★] "
        elif i <= tgt_idx:
            bar += f"[{level}  ] "
        else:
            break

    return f"Progress: {bar.strip()}"


def _get_error_stats(student_name: str) -> dict[str, int]:
    """Count error types across all sessions."""
    if not ERRORS_DIR.exists():
        return {}

    files = ERRORS_DIR.glob(f"*_{student_name}.json")
    counts: dict[str, int] = {}
    for f in files:
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            for e in data.get("errors", []):
                t = e.get("type", "unknown")
                counts[t] = counts.get(t, 0) + 1
    return counts


def _load_progress_log(student_name: str) -> dict:
    path = _progress_path(student_name)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"student": student_name, "tests": []}


def _save_progress_log(student_name: str, log: dict) -> None:
    path = _progress_path(student_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False)


def _progress_path(student_name: str) -> Path:
    return BASE_DIR / "logs" / f"progress_{student_name}.json"
