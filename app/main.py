from __future__ import annotations

from fastapi import FastAPI

from .config import get_settings
from .logging_setup import configure_logging
from .routes import health, transcribe


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Jeeb Voice Transcription Service",
        version="0.1.0",
        description=(
            "OpenAI Whisper-backed voice transcription with object storage and queued fallback."
        ),
    )
    app.include_router(transcribe.router)
    app.include_router(health.router)
    return app


app = create_app()
