from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str = Field(default="", description="OpenAI API key for Whisper")
    whisper_model: str = "whisper-1"
    whisper_language: str = "ar"
    whisper_timeout_seconds: float = 5.0

    storage_bucket: str = "jeeb-voice-audio"
    storage_endpoint_url: str | None = None
    storage_region: str = "us-east-1"
    storage_access_key_id: str | None = None
    storage_secret_access_key: str | None = None

    compression_threshold_bytes: int = 5 * 1024 * 1024
    max_upload_bytes: int = 25 * 1024 * 1024

    redis_url: str = "redis://redis:6379/0"
    retry_queue_key: str = "voice:transcribe:retry"

    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
