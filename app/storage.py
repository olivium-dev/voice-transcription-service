from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import boto3
from botocore.client import BaseClient
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

from .config import Settings


class StorageError(RuntimeError):
    """Raised when persisting the original audio fails."""


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    size_bytes: int

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"


class ObjectStorage(Protocol):
    def put_audio(self, key: str, data: bytes, content_type: str) -> StoredObject: ...

    def head(self, key: str) -> bool: ...


class S3ObjectStorage:
    def __init__(self, settings: Settings, client: BaseClient | None = None) -> None:
        self._bucket = settings.storage_bucket
        self._client = client or boto3.client(
            "s3",
            region_name=settings.storage_region,
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key_id,
            aws_secret_access_key=settings.storage_secret_access_key,
            config=BotoConfig(
                retries={"max_attempts": 3, "mode": "standard"},
                connect_timeout=2,
                read_timeout=5,
            ),
        )

    def put_audio(self, key: str, data: bytes, content_type: str) -> StoredObject:
        try:
            self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError(f"failed to persist audio {key}: {exc}") from exc
        return StoredObject(bucket=self._bucket, key=key, size_bytes=len(data))

    def head(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
        except (BotoCoreError, ClientError):
            return False
        return True
