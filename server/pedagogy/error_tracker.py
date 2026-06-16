# pedagogy/error_tracker.py — Real-time error and vocabulary gap tracking

import json
import re
from datetime import datetime
from pathlib import Path
from server.config.settings import ERRORS_DIR, VOCAB_DIR

# --- Regex patterns to extract tags from model responses ---
# Tolerant patterns: LLM sometimes escapes underscores as markdown (\_)
ERROR_PATTERN = re.compile(
    r'\[ERROR:\s*type=(\w+),\s*original="([^"]+)",\s*correct="([^"]+)"(?:,\s*explained=(\w+))?\]'
)
TOPIC_PATTERN = re.compile(
    r'\[TOPIC\\?_DISCOVERED:\s*([^\]]+)\]'
)


class SessionTracker:
    """Tracks errors and vocabulary gaps during a single session."""

    def __init__(self, student_name: str, topic: str):
        self.student_name = student_name
        self.topic = topic
        self.session_start = datetime.now()
        self.errors: list[dict] = []
        self.vocab_gaps: list[dict] = []
        self.discovered_topics: list[str] = []

    def parse_response(self, response: str) -> str:
        """
        Parse model response for error/topic tags.
        Strips tags from response before speaking — student never hears them.
        Returns clean response text.
        """
        # Extract errors
        for match in ERROR_PATTERN.finditer(response):
            try:
                groups = match.groups()
                if len(groups) >= 3:
                    error_type, original, correct = groups[0], groups[1], groups[2]
                    self.errors.append({
                        "ts": datetime.now().isoformat(),
                        "type": error_type,
                        "original": original,
                        "correct": correct,
                        "topic": self.topic,
                    })
            except Exception:
                pass

        # Extract discovered topics
        for match in TOPIC_PATTERN.finditer(response):
            topic = match.group(1).strip()
            if topic not in self.discovered_topics:
                self.discovered_topics.append(topic)

        # Strip all tags from response
        clean = re.sub(r'\[ERROR:.*?\]', '', response)
        clean = re.sub(r'\[TOPIC\\?_DISCOVERED:.*?\]', '', clean)
        return clean.strip()

    def flag_vocab_gap(self, context: str, russian_word: str = "") -> None:
        """
        Called when student presses vocab hotkey.
        Logs the last spoken context as a vocabulary gap.
        """
        self.vocab_gaps.append({
            "ts": datetime.now().isoformat(),
            "context": context,
            "russian_word": russian_word,
            "topic": self.topic,
        })
        print(f"[Yapper] Vocabulary gap logged: '{context}'")

    def get_error_summary(self) -> str:
        """Return formatted error log for analysis prompt."""
        if not self.errors:
            return "No errors recorded."
        lines = []
        for e in self.errors:
            lines.append(
                f"[{e['type']}] Said: \"{e['original']}\" → Correct: \"{e['correct']}\""
            )
        return "\n".join(lines)

    def get_vocab_summary(self) -> list[str]:
        """Return list of vocabulary gap contexts."""
        return [v["context"] for v in self.vocab_gaps]

    def save(self) -> Path:
        """Save session log to disk. Returns path to saved file."""
        session_end = datetime.now()
        duration = int((session_end - self.session_start).total_seconds() / 60)

        log = {
            "student": self.student_name,
            "topic": self.topic,
            "date": self.session_start.isoformat(),
            "duration_minutes": duration,
            "errors": self.errors,
            "vocab_gaps": self.vocab_gaps,
            "discovered_topics": self.discovered_topics,
        }

        # Save error log
        ERRORS_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{self.session_start.strftime('%Y%m%d_%H%M')}_{self.student_name}.json"
        path = ERRORS_DIR / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=2, ensure_ascii=False)

        # Save vocab gaps separately
        if self.vocab_gaps:
            VOCAB_DIR.mkdir(parents=True, exist_ok=True)
            vocab_path = VOCAB_DIR / filename
            with open(vocab_path, "w", encoding="utf-8") as f:
                json.dump(self.vocab_gaps, f, indent=2, ensure_ascii=False)

        print(f"[Yapper] Session saved: {path}")
        return path


def load_recent_errors(student_name: str, last_n: int = 5) -> list[dict]:
    """Load errors from the last N sessions for a student."""
    if not ERRORS_DIR.exists():
        return []

    files = sorted(
        [f for f in ERRORS_DIR.glob(f"*_{student_name}.json")],
        reverse=True
    )[:last_n]

    all_errors = []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            all_errors.extend(data.get("errors", []))
    return all_errors


def get_recurring_errors(student_name: str, min_count: int = 3) -> list[str]:
    """
    Find error types that repeat across sessions.
    Returns list of error type strings that occurred >= min_count times.
    """
    errors = load_recent_errors(student_name, last_n=10)
    counts: dict[str, int] = {}
    for e in errors:
        t = e.get("type", "unknown")
        counts[t] = counts.get(t, 0) + 1

    return [t for t, c in counts.items() if c >= min_count]


def load_vocab_gaps(student_name: str, last_n: int = 3) -> list[str]:
    """Load vocabulary gaps from last N sessions."""
    if not VOCAB_DIR.exists():
        return []

    files = sorted(
        [f for f in VOCAB_DIR.glob(f"*_{student_name}.json")],
        reverse=True
    )[:last_n]

    gaps = []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            gaps.extend([v.get("context", "") for v in data])
    return gaps


def load_discovered_topics(student_name: str, last_n: int = 5) -> list[str]:
    """Load topics discovered in recent sessions."""
    if not ERRORS_DIR.exists():
        return []

    files = sorted(
        [f for f in ERRORS_DIR.glob(f"*_{student_name}.json")],
        reverse=True
    )[:last_n]

    topics = []
    for f in files:
        with open(f, encoding="utf-8") as fp:
            data = json.load(fp)
            for t in data.get("discovered_topics", []):
                if t not in topics:
                    topics.append(t)
    return topics
