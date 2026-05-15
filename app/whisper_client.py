from __future__ import annotations

from dataclasses import dataclass

import httpx
from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError

from .config import Settings


class WhisperUnavailable(RuntimeError):
    """Raised when Whisper API is unreachable or transiently failing — caller should queue."""


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    language: str


class WhisperClient:
    """Async wrapper around the OpenAI audio.transcriptions endpoint.

    `WhisperUnavailable` is reserved for the outage cases that the acceptance criteria
    require us to handle gracefully: network errors, timeouts, 5xx, and rate limits.
    Programmer errors (invalid request, auth failure) propagate as `APIError`.
    """

    def __init__(self, settings: Settings, client: AsyncOpenAI | None = None) -> None:
        self._settings = settings
        self._client = client or AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=httpx.Timeout(settings.whisper_timeout_seconds),
            max_retries=0,
        )

    async def transcribe(
        self, audio: bytes, *, filename: str, content_type: str
    ) -> TranscriptionResult:
        try:
            response = await self._client.audio.transcriptions.create(
                model=self._settings.whisper_model,
                file=(filename, audio, content_type),
                language=self._settings.whisper_language,
                response_format="json",
            )
        except (APIConnectionError, APITimeoutError, RateLimitError) as exc:
            raise WhisperUnavailable(str(exc)) from exc
        except APIError as exc:
            status = getattr(exc, "status_code", None)
            if status is not None and status >= 500:
                raise WhisperUnavailable(str(exc)) from exc
            raise

        text = getattr(response, "text", "") or ""
        return TranscriptionResult(text=text, language=self._settings.whisper_language)

    async def ping(self) -> bool:
        try:
            await self._client.models.list()
        except Exception:
            return False
        return True
