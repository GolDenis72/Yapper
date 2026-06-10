# pedagogy/topics.py — Topic bank with vocabulary and terminology

import random

# Each topic has:
# - name: display name
# - keywords: conversation starters and context words
# - vocabulary: key terms the student should know at B1-B2
# - questions: ready-made conversation questions

TOPICS = {
    "travel": {
        "name": "Travel",
        "keywords": ["trip", "journey", "destination", "abroad", "vacation"],
        "vocabulary": [
            "itinerary", "layover", "accommodation", "customs", "passport",
            "departure", "arrival", "souvenir", "budget", "backpacking",
            "round trip", "one-way", "check-in", "boarding pass", "jet lag"
        ],
        "questions": [
            "Tell me about your favourite trip. Where did you go?",
            "What's the most interesting place you've ever visited?",
            "Do you prefer travelling alone or with others? Why?",
            "What would be your dream destination and why?",
            "Have you ever had any problems while travelling?",
        ]
    },
    "food & cooking": {
        "name": "Food & Cooking",
        "keywords": ["recipe", "ingredient", "dish", "flavour", "cuisine"],
        "vocabulary": [
            "simmer", "sauté", "marinate", "dice", "fillet",
            "garnish", "seasoning", "appetizer", "entrée", "dessert",
            "texture", "aroma", "spicy", "savoury", "crispy"
        ],
        "questions": [
            "What's your favourite dish to cook at home?",
            "Do you prefer home-cooked meals or eating out?",
            "Tell me about a dish from your culture.",
            "Have you ever tried a food that surprised you?",
            "What's the most difficult thing you've ever cooked?",
        ]
    },
    "fishing": {
        "name": "Fishing",
        "keywords": ["catch", "bait", "rod", "lake", "river"],
        "vocabulary": [
            "lure", "spinner", "float", "sinker", "hook",
            "cast", "reel", "tackle", "bite", "perch",
            "pike", "carp", "trout", "fly fishing", "catch and release"
        ],
        "questions": [
            "Where do you usually go fishing?",
            "What's the biggest fish you've ever caught?",
            "What kind of bait or lures do you prefer?",
            "Do you fish alone or with friends?",
            "What time of year is best for fishing in your area?",
        ]
    },
    "work & career": {
        "name": "Work & Career",
        "keywords": ["job", "profession", "office", "salary", "project"],
        "vocabulary": [
            "deadline", "colleague", "promotion", "resignation", "interview",
            "freelance", "remote work", "workload", "feedback", "teamwork",
            "productivity", "overtime", "contract", "performance", "career path"
        ],
        "questions": [
            "What do you do for work? Do you enjoy it?",
            "What's the most challenging part of your job?",
            "Have you ever changed your career direction?",
            "What does your ideal work environment look like?",
            "Where do you see yourself professionally in 5 years?",
        ]
    },
    "technology": {
        "name": "Technology",
        "keywords": ["device", "software", "internet", "app", "digital"],
        "vocabulary": [
            "bandwidth", "algorithm", "cloud storage", "encryption", "interface",
            "automation", "artificial intelligence", "server", "debugging", "update",
            "firewall", "backup", "streaming", "latency", "open source"
        ],
        "questions": [
            "How has technology changed your daily life?",
            "What device could you not live without?",
            "What do you think about artificial intelligence?",
            "Do you think social media is more positive or negative?",
            "What technology do you wish existed but doesn't yet?",
        ]
    },
    "nature & environment": {
        "name": "Nature & Environment",
        "keywords": ["forest", "wildlife", "climate", "pollution", "conservation"],
        "vocabulary": [
            "ecosystem", "biodiversity", "carbon footprint", "renewable energy", "habitat",
            "deforestation", "endangered species", "sustainability", "drought", "flood",
            "greenhouse gas", "recycle", "compost", "emissions", "nature reserve"
        ],
        "questions": [
            "How do you connect with nature in your daily life?",
            "What environmental issues concern you most?",
            "Do you try to live sustainably? How?",
            "What's the most beautiful natural place you've seen?",
            "What can individuals do to help the environment?",
        ]
    },
    "sports": {
        "name": "Sports",
        "keywords": ["team", "match", "fitness", "training", "compete"],
        "vocabulary": [
            "tournament", "championship", "referee", "penalty", "stamina",
            "endurance", "warm-up", "sprint", "score", "draw",
            "substitute", "coach", "athlete", "personal best", "podium"
        ],
        "questions": [
            "Do you play any sports or exercise regularly?",
            "What sport do you enjoy watching most?",
            "Have you ever competed in any sporting event?",
            "What sport would you like to try?",
            "How important is physical fitness to you?",
        ]
    },
    "music & arts": {
        "name": "Music & Arts",
        "keywords": ["song", "artist", "concert", "gallery", "creative"],
        "vocabulary": [
            "melody", "rhythm", "lyrics", "genre", "composer",
            "canvas", "sculpture", "exhibition", "masterpiece", "abstract",
            "improvise", "orchestra", "acoustic", "portrait", "installation"
        ],
        "questions": [
            "What kind of music do you listen to?",
            "Have you ever been to a live concert or art exhibition?",
            "Do you play a musical instrument or create art?",
            "What song or piece of music means a lot to you?",
            "How does music or art affect your mood?",
        ]
    },
    "daily life": {
        "name": "Daily Life",
        "keywords": ["routine", "morning", "evening", "household", "weekend"],
        "vocabulary": [
            "commute", "errand", "chore", "schedule", "habit",
            "neighbourhood", "grocery", "appliance", "maintenance", "budget",
            "routine", "leisure", "priority", "balance", "productivity"
        ],
        "questions": [
            "Describe your typical weekday.",
            "What does your morning routine look like?",
            "How do you usually spend your weekends?",
            "What household tasks do you enjoy or hate?",
            "How do you balance work and personal life?",
        ]
    },
    "accounting": {
        "name": "Accounting & Finance",
        "keywords": ["budget", "invoice", "tax", "balance", "audit"],
        "vocabulary": [
            "accounts payable", "accounts receivable", "balance sheet", "cash flow", "depreciation",
            "dividend", "equity", "fiscal year", "gross profit", "ledger",
            "liability", "net income", "overhead", "payroll", "reconciliation",
            "revenue", "tax return", "trial balance", "write-off", "amortization"
        ],
        "questions": [
            "Can you walk me through a typical month-end closing process?",
            "What accounting software have you worked with?",
            "How do you handle discrepancies in financial records?",
            "What's the difference between cash and accrual accounting?",
            "How do you prepare for an audit?",
        ]
    },
    "news & current events": {
        "name": "News & Current Events",
        "keywords": ["headline", "politics", "economy", "global", "society"],
        "vocabulary": [
            "policy", "legislation", "inflation", "recession", "election",
            "diplomatic", "sanctions", "treaty", "crisis", "reform",
            "controversy", "spokesperson", "investigation", "press conference", "breaking news"
        ],
        "questions": [
            "How do you usually follow the news?",
            "What recent event has caught your attention?",
            "Do you think media coverage is generally trustworthy?",
            "What global issue concerns you most right now?",
            "How has a recent news story affected your life or thinking?",
        ]
    },
}


def get_topic(name: str) -> dict | None:
    """Get topic by key name."""
    return TOPICS.get(name)


def get_random_question(topic_name: str) -> str | None:
    """Get a random conversation question for a topic."""
    topic = TOPICS.get(topic_name)
    if not topic:
        return None
    return random.choice(topic["questions"])


def get_vocabulary(topic_name: str) -> list[str]:
    """Get vocabulary list for a topic."""
    topic = TOPICS.get(topic_name)
    if not topic:
        return []
    return topic["vocabulary"]


def suggest_topics(profile: dict) -> list[str]:
    """
    Suggest topics for a session based on student profile.
    Prioritizes professional topics, then preferred topics.
    """
    suggestions = []
    for t in profile.get("professional_topics", []):
        key = _match_topic_key(t)
        if key and key not in suggestions:
            suggestions.append(key)
    for t in profile.get("preferred_topics", []):
        key = _match_topic_key(t)
        if key and key not in suggestions:
            suggestions.append(key)
    return suggestions or list(TOPICS.keys())


def _match_topic_key(name: str) -> str | None:
    """Fuzzy match a topic name to a key in TOPICS."""
    name_lower = name.lower()
    for key in TOPICS:
        if key in name_lower or name_lower in key:
            return key
    # partial match
    for key, data in TOPICS.items():
        if any(kw in name_lower for kw in data["keywords"]):
            return key
    return None


def all_topic_names() -> list[str]:
    return list(TOPICS.keys())
