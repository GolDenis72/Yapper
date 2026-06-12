# cat > /tmp/README.md << 'EOF'

# \# Yapper 🎙️

# 

# A fully local AI-powered English conversation tutor. No cloud, no subscriptions — runs entirely on your own hardware.

# 

# \---

# 

# \## What it does

# 

# \- Listens to you speak in English via browser microphone

# \- Responds naturally via voice (text-to-speech)

# \- Tracks grammar mistakes and vocabulary gaps in real time

# \- After each session: analyses errors, identifies weak spots, generates a plan for the next lesson

# \- Follows CEFR methodology (A1 → B2 progression)

# \- Supports multiple student profiles (e.g. different family members)

# \- Flags vocabulary gaps mid-conversation with a hotkey (F9)

# \- Pause/resume session without losing context

# 

# \---

# 

# \## Architecture overview

# 

# ```

# Browser (Windows/Mac/Linux)

# &#x20;   │

# &#x20;   │  HTTPS + WebSocket (wss://)

# &#x20;   ▼

# ┌─────────────────────────────────┐

# │  server.py  (FastAPI + uvicorn) │  ← entry point for web mode

# │                                 │

# │  /          → static/index.html │

# │  /ws        → WebSocket handler │

# │  /health    → service status    │

# │  /topics    → topic list        │

# │  /progress  → progress report   │

# └────────────┬────────────────────┘

# &#x20;            │

# &#x20;   ┌────────▼─────────────────────────────────┐

# &#x20;   │           Session flow                    │

# &#x20;   │                                           │

# &#x20;   │  1. Browser sends audio (base64 webm)     │

# &#x20;   │  2. core/stt.py  → Whisper server         │

# &#x20;   │  3. core/llm.py  → Ollama                 │

# &#x20;   │  4. core/tts.py  → edge-tts               │

# &#x20;   │  5. Audio MP3 sent back to browser        │

# &#x20;   └───────────────────────────────────────────┘

# ```

# 

# \---

# 

# \## Module reference

# 

# \### Entry points

# 

# | File | Purpose |

# |------|---------|

# | `server.py` | FastAPI web server. Handles HTTP routes and WebSocket sessions. Main entry point for web mode. |

# | `main.py` | Console-only entry point. For terminal use without a browser. |

# 

# \### core/

# 

# All low-level I/O. No business logic here.

# 

# | File | Purpose | Key functions |

# |------|---------|---------------|

# | `core/stt.py` | Speech-to-Text. Sends WAV audio to Whisper HTTP server. | `transcribe(audio\_bytes)` → str, `ping()` → bool |

# | `core/tts.py` | Text-to-Speech via edge-tts (Microsoft voices, free). | `speak(text)` → bytes (sync), `speak\_async(text)` → bytes (async, use in server.py) |

# | `core/llm.py` | LLM interface to Ollama. Supports streaming and non-streaming. | `chat(messages, stream)` → generator or str, `ping()` → bool |

# | `core/audio.py` | Microphone capture, audio playback, hotkey listener. Console mode only. | `record\_until\_silence()` → bytes, `play\_audio(bytes)`, `start\_hotkey\_listener()` |

# 

# \### config/

# 

# | File | Purpose |

# |------|---------|

# | `config/settings.py` | All configuration. Reads from `.env`. Exports paths, URLs, model names, hotkeys. |

# 

# \### pedagogy/

# 

# The brain of the tutor. All teaching logic lives here.

# 

# | File | Purpose | Key functions |

# |------|---------|---------------|

# | `pedagogy/student\_profile.py` | Student profile: name, level, topics, session stats. Stored as `student\_profile.json`. | `load()`, `save()`, `create\_interactive()`, `set\_level()`, `summary()` |

# | `pedagogy/assessment.py` | CEFR level assessment. Run on first session only. Uses LLM to conduct a natural conversation and evaluate level. Does NOT correct errors during assessment. | `run\_assessment(profile, speak\_fn, listen\_fn)` → dict |

# | `pedagogy/prompts.py` | All LLM system prompts. Tutor prompt, analysis prompt, lesson plan prompt, monthly test prompt. | `build\_tutor\_prompt()`, `build\_analysis\_prompt()`, `build\_lesson\_plan\_prompt()` |

# | `pedagogy/error\_tracker.py` | Parses `\[ERROR: ...]` and `\[TOPIC\_DISCOVERED: ...]` tags from LLM responses. Logs errors per session. | `SessionTracker` class: `parse\_response()`, `flag\_vocab\_gap()`, `save()` |

# | `pedagogy/lesson\_planner.py` | Post-session analysis and next lesson plan generation. Calls LLM with error log and history. | `run\_post\_session\_analysis()`, `generate\_lesson\_plan()`, `load\_current\_plan()` |

# | `pedagogy/topics.py` | Topic bank: 11 topics with vocabulary lists and conversation questions. | `suggest\_topics(profile)`, `get\_vocabulary(topic)`, `get\_random\_question(topic)` |

# | `pedagogy/progress.py` | Progress tracking, streak counter, CEFR progress bar, monthly test results. | `get\_progress\_report(name)`, `record\_monthly\_test()`, `get\_session\_streak()` |

# 

# \### static/

# 

# Browser frontend.

# 

# | File | Purpose |

# |------|---------|

# | `static/index.html` | Single-page app. Profile setup, session controls, conversation view, progress panel. |

# | `static/app.js` | WebSocket client. Handles mic recording (MediaRecorder API), audio playback, UI state. |

# | `static/style.css` | Dark theme UI styles. |

# 

# \---

# 

# \## Data flow — one conversation turn

# 

# ```

# 1\. User holds mic button in browser

# 2\. MediaRecorder captures audio → webm blob

# 3\. blob → base64 → WebSocket message {type: "audio\_chunk", data: "..."}

# 4\. server.py receives → decodes base64 → WAV bytes

# 5\. core/stt.py sends WAV to Whisper server (port 9001)

# 6\. Whisper returns transcribed text

# 7\. server.py sends {type: "user\_message", text: "..."} to browser

# 8\. Text added to messages\[] → sent to Ollama via core/llm.py

# 9\. Ollama streams response tokens

# 10\. core/tts.py converts response to MP3 via edge-tts

# 11\. server.py sends {type: "assistant\_message", text: "...", audio: "base64mp3"}

# 12\. Browser plays MP3, displays text

# 13\. pedagogy/error\_tracker.py parses \[ERROR:...] tags from response (invisible to user)

# ```

# 

# \---

# 

# \## WebSocket message protocol

# 

# \### Client → Server

# 

# | Message type | Payload | Description |

# |-------------|---------|-------------|

# | `start\_session` | `{topic: string}` | Start a conversation session |

# | `stop\_session` | `{}` | End session, trigger analysis |

# | `audio\_chunk` | `{data: base64}` | Send recorded audio |

# | `vocab\_flag` | `{context: string}` | Flag vocabulary gap (F9 key) |

# | `change\_topic` | `{topic: string}` | Switch conversation topic |

# | `get\_progress` | `{}` | Request progress report |

# | `save\_profile` | `{data: object}` | Save student profile |

# 

# \### Server → Client

# 

# | Message type | Payload | Description |

# |-------------|---------|-------------|

# | `status` | `{whisper, ollama, profile}` | Initial connection status |

# | `session\_started` | `{topic, vocabulary, duration}` | Session began |

# | `session\_ended` | `{duration, errors, vocab\_gaps, next\_topic}` | Session finished |

# | `assistant\_message` | `{text, audio: base64}` | Tutor response with audio |

# | `user\_message` | `{text}` | Transcribed user speech |

# | `status\_text` | `{text}` | Status update (Listening/Thinking/Speaking) |

# | `assessment\_started` | `{}` | Assessment began |

# | `assessment\_done` | `{level, result}` | Assessment complete |

# | `progress` | `{report: string}` | Progress report text |

# | `error` | `{message}` | Error notification |

# 

# \---

# 

# \## File storage

# 

# ```

# yapper/

# ├── student\_profile.json        ← student profile (auto-created)

# ├── logs/

# │   ├── errors/                 ← per-session error logs (JSON)

# │   │   └── YYYYMMDD\_HHMM\_Name.json

# │   ├── vocabulary/             ← vocabulary gap logs (JSON)

# │   │   └── YYYYMMDD\_HHMM\_Name.json

# │   ├── analysis/               ← post-session LLM analysis (JSON)

# │   │   └── YYYYMMDD\_HHMM\_Name.json

# │   ├── assessment.json         ← first-run assessment result

# │   └── progress\_Name.json      ← monthly test history

# └── lessons/

# &#x20;   └── plans/                  ← generated lesson plans (JSON)

# &#x20;       └── YYYYMMDD\_HHMM\_Name.json

# ```

# 

# \---

# 

# \## Stack

# 

# | Component | Tool | Version | Notes |

# |-----------|------|---------|-------|

# | STT | Whisper (onerahmet/openai-whisper-asr-webservice) | latest-gpu | Docker, port 9001 |

# | LLM | Ollama + mistral:7b | 2026 | Local, \~42 tok/s on RTX 3060 |

# | TTS | edge-tts | 7.x | Free Microsoft voices, no API key |

# | Web server | FastAPI + uvicorn | latest | HTTPS with self-signed cert |

# | Frontend | Vanilla JS + HTML | — | No framework, MediaRecorder API |

# 

# \---

# 

# \## Hardware tested on

# 

# \- Ubuntu 22.04

# \- NVIDIA RTX 3060 12GB

# \- Ollama running as systemd service

# \- Whisper running in Docker with GPU passthrough

# 

# \---

# 

# \## Quick start

# 

# ```bash

# git clone https://github.com/GolDenis72/Yapper

# cd Yapper

# 

# \# Install dependencies

# pip install -r requirements.txt

# sudo apt install -y libportaudio2

# 

# \# Start Whisper (Docker)

# docker run -d --name whisper-server --gpus all \\

# &#x20; -p 9001:9000 -e ASR\_MODEL=base \\

# &#x20; onerahmet/openai-whisper-asr-webservice:latest-gpu

# 

# \# Configure

# cp .env.example .env

# \# Edit .env if needed

# 

# \# Generate SSL cert (required for browser microphone)

# openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \\

# &#x20; -days 365 -nodes -subj "/CN=YOUR\_SERVER\_IP"

# 

# \# Run

# python3 server.py --ssl-certfile cert.pem --ssl-keyfile key.pem

# 

# \# Open in browser

# \# https://YOUR\_SERVER\_IP:7860

# \# Accept the self-signed cert warning

# ```

# 

# \---

# 

# \## Known issues / TODO

# 

# \- \[ ] Whisper `base` model has low accuracy — upgrade to `large-v3` for production

# \- \[ ] Add `initial\_prompt` to Whisper requests (topic context improves accuracy \~30%)

# \- \[ ] Microphone test button with sentence read-back

# \- \[ ] Convert browser audio from webm to wav before sending to Whisper

# \- \[ ] Lesson plan JSON parsing sometimes fails (LLM doesn't return clean JSON)

# \- \[ ] Add `.env` UI in browser (change model, voice, session duration without restart)

# 

# \---

# 

# \## Lesson flow

# 

# 1\. \*\*First run\*\* — profile setup + CEFR assessment (natural conversation, no corrections)

# 2\. \*\*Session\*\* — free conversation on chosen topic, tutor corrects gently using reformulation technique

# 3\. \*\*Vocabulary gap\*\* — press F9 when you used a non-English word; logged for next lesson

# 4\. \*\*Post-session\*\* — LLM analyses error log, groups by type, generates next lesson plan

# 5\. \*\*Next session\*\* — opens with callback question referencing last session, focuses on weak points

# 6\. \*\*Monthly test\*\* — structured CEFR assessment to track progress

# 

# \---

# 

# \## CEFR levels

# 

# A1 → A2 → B1 → B2 → C1 → C2

# 

# Typical progression: \~200 study hours per level. Regular conversation practice accelerates this significantly.

# EOF

# echo "done"

