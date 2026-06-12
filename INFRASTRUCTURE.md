# Yapper Infrastructure

## Services

| Service | How it runs | Port | Notes |
|---------|-------------|------|-------|
| Whisper STT | Docker (onerahmet/openai-whisper-asr-webservice:latest-gpu) | 9001 | GPU passthrough |
| Ollama LLM | systemd service | 11434 | mistral:7b or qwen2.5:7b |
| Yapper server | python3 server/server.py | 7860 | HTTPS with self-signed cert |

## Start commands

```bash
# Whisper
docker run -d --name whisper-server --gpus all \
  -p 9001:9000 -e ASR_MODEL=base \
  onerahmet/openai-whisper-asr-webservice:latest-gpu

# Yapper
cd /mnt/truenas/Yapper/Yapper
python3 server/server.py --ssl-certfile cert.pem --ssl-keyfile key.pem
```

## Network

- Server IP: 192.168.2.21
- Browser access: https://192.168.2.21:7860
- Accept self-signed cert warning in browser

## File paths

- Project: /mnt/truenas/Yapper/Yapper
- Logs: /mnt/truenas/Yapper/Yapper/logs/
- Lesson plans: /mnt/truenas/Yapper/Yapper/lessons/plans/
- Student profile: /mnt/truenas/Yapper/Yapper/student_profile.json
