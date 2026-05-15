from typing import Literal

from pydantic import BaseModel, Field


class TranscriptionResponse(BaseModel):
    audio_id: str
    transcription: str
    language: str
    duration_ms: int
    storage_uri: str
    status: Literal["completed"] = "completed"


class QueuedTranscriptionResponse(BaseModel):
    audio_id: str
    storage_uri: str
    status: Literal["queued"] = "queued"
    reason: str = Field(
        description="Why the transcription was queued instead of completed synchronously"
    )


class HealthStatus(BaseModel):
    status: Literal["ok", "degraded"]
    storage: Literal["ok", "unreachable"] | None = None
    whisper: Literal["ok", "unreachable"] | None = None


class RetryJobPayload(BaseModel):
    audio_id: str
    storage_key: str
    content_type: str
    queued_at: str
    attempts: int = 0
