from __future__ import annotations

import redis
from redis.exceptions import RedisError

from .models import RetryJobPayload


class RetryQueueError(RuntimeError):
    pass


class RetryQueue:
    def __init__(self, url: str, key: str, client: redis.Redis | None = None) -> None:
        self._client: redis.Redis = client or redis.from_url(
            url, decode_responses=True, socket_timeout=2
        )
        self._key = key

    def enqueue(self, job: RetryJobPayload) -> None:
        try:
            self._client.lpush(self._key, job.model_dump_json())
        except RedisError as exc:
            raise RetryQueueError(f"failed to enqueue retry job: {exc}") from exc

    def depth(self) -> int:
        try:
            return int(self._client.llen(self._key))
        except RedisError as exc:
            raise RetryQueueError(f"failed to read queue depth: {exc}") from exc
