from __future__ import annotations

import os

import boto3
import fakeredis
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("STORAGE_BUCKET", "jeeb-voice-audio-test")
os.environ.setdefault("STORAGE_REGION", "us-east-1")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.config import get_settings
from app.dependencies import (
    get_retry_queue,
    get_storage,
    get_whisper,
)
from app.main import create_app
from app.retry_queue import RetryQueue
from app.storage import S3ObjectStorage


@pytest.fixture()
def settings():
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture()
def s3_storage(settings):
    with mock_aws():
        client = boto3.client("s3", region_name=settings.storage_region)
        client.create_bucket(Bucket=settings.storage_bucket)
        yield S3ObjectStorage(settings, client=client)


@pytest.fixture()
def retry_queue(settings):
    fake = fakeredis.FakeRedis(decode_responses=True)
    yield RetryQueue(url=settings.redis_url, key=settings.retry_queue_key, client=fake)


class StubWhisper:
    def __init__(self, *, text: str = "مرحبا", raise_unavailable: bool = False) -> None:
        self.text = text
        self.raise_unavailable = raise_unavailable
        self.calls: list[dict] = []

    async def transcribe(self, audio, *, filename, content_type):
        self.calls.append({"filename": filename, "content_type": content_type, "size": len(audio)})
        if self.raise_unavailable:
            from app.whisper_client import WhisperUnavailable

            raise WhisperUnavailable("simulated outage")
        from app.whisper_client import TranscriptionResult

        return TranscriptionResult(text=self.text, language="ar")

    async def ping(self) -> bool:
        return not self.raise_unavailable


@pytest.fixture()
def whisper_stub():
    return StubWhisper()


@pytest.fixture()
def client(settings, s3_storage, whisper_stub, retry_queue):
    app = create_app()
    app.dependency_overrides[get_storage] = lambda: s3_storage
    app.dependency_overrides[get_whisper] = lambda: whisper_stub
    app.dependency_overrides[get_retry_queue] = lambda: retry_queue
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
