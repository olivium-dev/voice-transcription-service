from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from openai import APIConnectionError, APIError, APITimeoutError, RateLimitError

from app.config import get_settings
from app.whisper_client import TranscriptionResult, WhisperClient, WhisperUnavailable


def _make_client(transcribe_side_effect):
    fake_openai = MagicMock()
    fake_openai.audio.transcriptions.create = AsyncMock(side_effect=transcribe_side_effect)
    get_settings.cache_clear()
    return WhisperClient(get_settings(), client=fake_openai)


async def test_transcribe_returns_text():
    response = MagicMock()
    response.text = "مرحبا"
    client = _make_client([response])
    result = await client.transcribe(b"\x00", filename="x.m4a", content_type="audio/mp4")
    assert result == TranscriptionResult(text="مرحبا", language="ar")


@pytest.mark.parametrize(
    "exc",
    [
        APIConnectionError(request=httpx.Request("POST", "https://api.openai.com")),
        APITimeoutError(request=httpx.Request("POST", "https://api.openai.com")),
        RateLimitError(
            "rate-limited",
            response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com")),
            body=None,
        ),
    ],
)
async def test_transcribe_raises_unavailable_on_transient_errors(exc):
    client = _make_client(exc)
    with pytest.raises(WhisperUnavailable):
        await client.transcribe(b"\x00", filename="x.m4a", content_type="audio/mp4")


async def test_transcribe_raises_unavailable_on_5xx():
    five_hundred = APIError(
        "boom",
        request=httpx.Request("POST", "https://api.openai.com"),
        body=None,
    )
    five_hundred.status_code = 503
    client = _make_client(five_hundred)
    with pytest.raises(WhisperUnavailable):
        await client.transcribe(b"\x00", filename="x.m4a", content_type="audio/mp4")


async def test_transcribe_reraises_4xx():
    bad_request = APIError(
        "bad",
        request=httpx.Request("POST", "https://api.openai.com"),
        body=None,
    )
    bad_request.status_code = 400
    client = _make_client(bad_request)
    with pytest.raises(APIError):
        await client.transcribe(b"\x00", filename="x.m4a", content_type="audio/mp4")
