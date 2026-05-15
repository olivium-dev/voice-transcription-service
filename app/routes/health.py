from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ..config import Settings, get_settings
from ..dependencies import get_storage, get_whisper
from ..models import HealthStatus
from ..storage import ObjectStorage
from ..whisper_client import WhisperClient

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthStatus)
async def liveness() -> HealthStatus:
    return HealthStatus(status="ok")


@router.get("/health/ready", response_model=HealthStatus)
async def readiness(
    response: Response,
    settings: Settings = Depends(get_settings),
    storage: ObjectStorage = Depends(get_storage),
    whisper: WhisperClient = Depends(get_whisper),
) -> HealthStatus:
    # head() returns False for both "missing" and "unreachable" — we treat reachability
    # as the boto client not raising at all when probing a sentinel key.
    try:
        storage.head(f"_healthcheck/{settings.storage_bucket}")
        storage_status: str = "ok"
    except Exception:
        storage_status = "unreachable"

    whisper_status = "ok" if await whisper.ping() else "unreachable"
    overall = "ok" if whisper_status == "ok" and storage_status == "ok" else "degraded"
    if overall == "degraded":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthStatus(status=overall, storage=storage_status, whisper=whisper_status)  # type: ignore[arg-type]
