from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from .compression import CompressionError, compress_to_opus, ffmpeg_available
from .config import Settings
from .logging_setup import logger
from .models import (
    QueuedTranscriptionResponse,
    RetryJobPayload,
    TranscriptionResponse,
)
from .retry_queue import RetryQueue, RetryQueueError
from .storage import ObjectStorage, StorageError
from .whisper_client import WhisperClient, WhisperUnavailable


class TranscriptionService:
    def __init__(
        self,
        settings: Settings,
        storage: ObjectStorage,
        whisper: WhisperClient,
        retry_queue: RetryQueue,
    ) -> None:
        self._settings = settings
        self._storage = storage
        self._whisper = whisper
        self._retry_queue = retry_queue

    async def transcribe(
        self,
        *,
        data: bytes,
        filename: str,
        content_type: str,
    ) -> TranscriptionResponse | QueuedTranscriptionResponse:
        audio_id = uuid.uuid4().hex
        storage_key = f"voice/{datetime.now(UTC):%Y/%m/%d}/{audio_id}/{filename}"
        log = logger.bind(audio_id=audio_id, filename=filename, size=len(data))

        original_size = len(data)
        stored = self._storage.put_audio(storage_key, data, content_type)
        log = log.bind(storage_uri=stored.uri)
        log.info("audio.stored", original_size=original_size)

        payload, payload_content_type, payload_filename = data, content_type, filename
        if original_size > self._settings.compression_threshold_bytes and ffmpeg_available():
            try:
                payload, payload_content_type = await compress_to_opus(data)
                payload_filename = f"{audio_id}.ogg"
                log.info(
                    "audio.compressed",
                    from_bytes=original_size,
                    to_bytes=len(payload),
                )
            except CompressionError as exc:
                log.warning("audio.compression_failed", error=str(exc))

        start = time.perf_counter()
        try:
            result = await self._whisper.transcribe(
                payload, filename=payload_filename, content_type=payload_content_type
            )
        except WhisperUnavailable as exc:
            log.warning("whisper.unavailable", error=str(exc))
            self._queue_for_retry(audio_id, stored.key, content_type)
            return QueuedTranscriptionResponse(
                audio_id=audio_id,
                storage_uri=stored.uri,
                reason=f"whisper_unavailable: {exc}",
            )
        duration_ms = int((time.perf_counter() - start) * 1000)
        log.info("whisper.completed", duration_ms=duration_ms, chars=len(result.text))

        return TranscriptionResponse(
            audio_id=audio_id,
            transcription=result.text,
            language=result.language,
            duration_ms=duration_ms,
            storage_uri=stored.uri,
        )

    def _queue_for_retry(self, audio_id: str, storage_key: str, content_type: str) -> None:
        job = RetryJobPayload(
            audio_id=audio_id,
            storage_key=storage_key,
            content_type=content_type,
            queued_at=datetime.now(UTC).isoformat(),
        )
        try:
            self._retry_queue.enqueue(job)
        except RetryQueueError as exc:
            # Audio is already persisted in storage; a worker can scan the bucket as
            # a backstop. Surface the error so the caller still gets a queued response.
            logger.error("retry_queue.enqueue_failed", audio_id=audio_id, error=str(exc))


def build_storage_error(exc: StorageError) -> dict[str, str]:
    return {"detail": "audio_storage_unavailable", "message": str(exc)}
