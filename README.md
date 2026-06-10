# Yapper 🎙️

A local AI-powered English conversation tutor. No cloud, no subscriptions — runs entirely on your own hardware.

## What it does

- Listens to you speak in English
- Responds naturally via voice
- Tracks your grammar mistakes and vocabulary gaps in real time
- After each session: analyzes errors, identifies weak spots, builds a plan for the next lesson
- Follows CEFR methodology (A1 → B2 progression)

## How it works

```
Microphone → STT (Whisper) → LLM (Ollama / Mistral 7B) → TTS (edge-tts) → Speakers
                                        ↓
                               Error & vocabulary log (JSON)
                                        ↓
                               Post-session analysis → Lesson plan
```

## Stack

| Component | Tool | Notes |
|-----------|------|-------|
| STT | faster-whisper / Whisper server | Local, no cloud |
| LLM | Ollama + Mistral 7B | Local, ~42 tok/s on RTX 3060 |
| TTS | edge-tts | Free, high quality English voices |
| Logs | JSON files | errors/ and vocabulary/ |

## Hardware

Tested on:
- Ubuntu 24.x
- NVIDIA RTX 3060 12GB
- Ollama running locally

## Project structure

```
yapper/
├── config/
│   └── settings.py          # ports, model names, paths
├── core/
│   ├── stt.py               # speech-to-text
│   ├── tts.py               # text-to-speech
│   ├── llm.py               # Ollama interface
│   └── audio.py             # microphone capture & playback
├── pedagogy/
│   ├── prompts.py           # CEFR-based system prompts
│   ├── error_tracker.py     # real-time error logging
│   └── lesson_planner.py    # post-session analysis & planning
├── logs/
│   ├── errors/              # grammar mistake logs (JSON)
│   └── vocabulary/          # vocabulary gap logs (JSON)
├── lessons/
│   └── plans/               # generated lesson plans
├── main.py                  # entry point
├── .env.example             # configuration template
└── README.md
```

## Lesson flow

1. **Session** — free conversation, tutor corrects mistakes gently in real time
2. **Logging** — all errors and vocabulary gaps saved with context
3. **Analysis** — post-session review groups errors by type (articles, tenses, prepositions, vocabulary)
4. **Planning** — next lesson plan generated based on weak spots
5. **Repeat** — topics drilled until progress is confirmed

## Vocabulary gap feature

Press a hotkey mid-conversation when you used a Russian word because you didn't know the English one.
The system logs it and adds it — plus related words — to the next lesson plan.

## Progress tracking

- Initial CEFR level assessment on first run
- Monthly progress tests
- Error frequency charts over time

## Getting started

```bash
git clone https://github.com/YOUR_USERNAME/Yapper
cd Yapper
pip install -r requirements.txt
cp .env.example .env
# edit .env with your settings
python main.py
```

## Requirements

- Ollama running with `mistral:7b` pulled
- NVIDIA GPU recommended (CPU works but slower)
- Microphone and speakers
