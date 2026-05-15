from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status

from ..config import Settings, get_settings
from ..dependencies import get_transcription_service
from ..models import QueuedTranscriptionResponse, TranscriptionResponse
from ..storage import StorageError
from ..transcription_service import TranscriptionService

router = APIRouter(tags=["transcription"])

ALLOWED_PREFIXES = ("audio/", "video/", "application/octet-stream")


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse | QueuedTranscriptionResponse,
    responses={
        202: {"model": QueuedTranscriptionResponse},
        400: {"description": "Missing or invalid audio"},
        413: {"description": "Audio exceeds maximum upload size"},
    },
)
async def transcribe(
    response: Response,
    audio: UploadFile = File(..., description="Voice audio file to transcribe"),
    settings: Settings = Depends(get_settings),
    service: TranscriptionService = Depends(get_transcription_service),
) -> TranscriptionResponse | QueuedTranscriptionResponse:
    if audio.filename in (None, ""):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "audio filename required")

    content_type = audio.content_type or "application/octet-stream"
    if not content_type.startswith(ALLOWED_PREFIXES):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"unsupported content-type: {content_type}",
        )

    data = await audio.read()
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "audio payload is empty")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(
            413,
            f"audio exceeds {settings.max_upload_bytes} bytes",
        )

    try:
        result = await service.transcribe(
            data=data, filename=audio.filename or "audio.bin", content_type=content_type
        )
    except StorageError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"audio storage unavailable: {exc}",
        ) from exc

    if isinstance(result, QueuedTranscriptionResponse):
        response.status_code = status.HTTP_202_ACCEPTED
    return result
