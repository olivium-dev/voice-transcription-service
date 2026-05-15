# voice-transcription-service

Voice-to-text transcription microservice for the Jeeb MVP. Receives an audio file,
stores the original in object storage, transcribes it via the OpenAI Whisper API
with an Arabic language hint, and returns the text. On Whisper outage, the audio
is still persisted and the transcription is queued for asynchronous retry.

## Endpoints

- `POST /transcribe` (multipart/form-data) — `audio` file part required.
  - 200 OK: `{ "audio_id", "transcription", "language", "duration_ms", "storage_uri" }`
  - 202 Accepted: `{ "audio_id", "status": "queued", "reason", "storage_uri" }` (Whisper unavailable)
  - 400 Bad Request: missing/invalid audio
  - 413 Payload Too Large: above hard upload cap
- `GET /health/live` — process liveness
- `GET /health/ready` — readiness (storage + Whisper reachability)

## Acceptance criteria (T-backend-006 / JEEB-24)

- [x] Audio uploaded and stored in object storage (S3-compatible)
- [x] Whisper API called with `language=ar` hint
- [x] Transcription returned within 5 seconds for 30s audio (httpx 5s timeout, no needless I/O)
- [x] Graceful fallback: audio saved, transcription queued if Whisper unavailable

## Configuration

| Env var | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | — | required for live Whisper calls |
| `WHISPER_MODEL` | `whisper-1` | OpenAI Whisper model id |
| `WHISPER_LANGUAGE` | `ar` | ISO-639-1 language hint |
| `WHISPER_TIMEOUT_SECONDS` | `5` | per-request timeout |
| `STORAGE_BUCKET` | `jeeb-voice-audio` | S3 bucket |
| `STORAGE_ENDPOINT_URL` | — | optional MinIO endpoint |
| `STORAGE_REGION` | `us-east-1` | AWS region |
| `COMPRESSION_THRESHOLD_BYTES` | `5242880` | 5 MB threshold for ffmpeg recompression |
| `MAX_UPLOAD_BYTES` | `26214400` | 25 MB hard cap (Whisper file-size limit) |
| `REDIS_URL` | `redis://redis:6379/0` | retry queue |
| `RETRY_QUEUE_KEY` | `voice:transcribe:retry` | Redis list key for queued jobs |

## Local development

```bash
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8080
```

## Tests

```bash
uv run pytest
```
