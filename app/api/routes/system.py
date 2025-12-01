import os
import time
from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.db.models.user import User
from app.schemas.system import SystemVersion

router = APIRouter(prefix="/api/system", tags=["System"])
public_router = APIRouter(prefix="/api", tags=["Health"])


def _load_average() -> Dict[str, float | None]:
    try:
        import psutil  # type: ignore

        one, five, fifteen = psutil.getloadavg()
        return {"1m": one, "5m": five, "15m": fifteen}
    except Exception:
        try:
            one, five, fifteen = os.getloadavg()
            return {"1m": one, "5m": five, "15m": fifteen}
        except Exception:
            try:
                with open("/proc/loadavg", "r", encoding="utf-8") as f:
                    parts = f.read().split()
                    return {"1m": float(parts[0]), "5m": float(parts[1]), "15m": float(parts[2])}
            except Exception:
                return {"1m": None, "5m": None, "15m": None}


@router.get(
    "/health",
    summary="System health (superadmin)",
    description="Returns system status, uptime, load averages, and DB connectivity. Superadmin only.",
)
async def system_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_superadmin:
        raise HTTPException(status_code=403, detail="Forbidden")

    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unreachable"

    start_time = getattr(request.app.state, "process_start_time", time.time())
    uptime_seconds = int(time.time() - start_time)
    load = _load_average()

    return {
        "status": "ok",
        "database": db_status,
        "uptime_seconds": uptime_seconds,
        "version": "1.0.0",
        "load": load,
    }


@router.get(
    "/version",
    summary="Version info",
    description="Return version, build, and startup timestamp for this deployment.",
    response_model=SystemVersion,
)
async def system_version(request: Request) -> SystemVersion:
    start_time = getattr(request.app.state, "process_start_time", time.time())
    timestamp = datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    version = getattr(settings, "APP_VERSION", None) or getattr(settings, "VERSION", "1.0.0-rc1")
    build = getattr(settings, "BUILD_COMMIT", None) or getattr(settings, "BUILD", "dev")
    return SystemVersion(version=version, build=build, timestamp=timestamp)


@public_router.get("/health", summary="Public health", description="Unauthenticated health check.")
async def public_health() -> Dict[str, str]:
    return {"status": "ok"}
