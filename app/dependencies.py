from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from .config import Settings, get_settings
from .retry_queue import RetryQueue
from .storage import ObjectStorage, S3ObjectStorage
from .transcription_service import TranscriptionService
from .whisper_client import WhisperClient


@lru_cache(maxsize=1)
def _storage(settings: Settings) -> ObjectStorage:
    return S3ObjectStorage(settings)


@lru_cache(maxsize=1)
def _whisper(settings: Settings) -> WhisperClient:
    return WhisperClient(settings)


@lru_cache(maxsize=1)
def _retry_queue(settings: Settings) -> RetryQueue:
    return RetryQueue(url=settings.redis_url, key=settings.retry_queue_key)


def get_storage(settings: Settings = Depends(get_settings)) -> ObjectStorage:
    return _storage(settings)


def get_whisper(settings: Settings = Depends(get_settings)) -> WhisperClient:
    return _whisper(settings)


def get_retry_queue(settings: Settings = Depends(get_settings)) -> RetryQueue:
    return _retry_queue(settings)


def get_transcription_service(
    settings: Settings = Depends(get_settings),
    storage: ObjectStorage = Depends(get_storage),
    whisper: WhisperClient = Depends(get_whisper),
    retry_queue: RetryQueue = Depends(get_retry_queue),
) -> TranscriptionService:
    return TranscriptionService(settings, storage, whisper, retry_queue)
