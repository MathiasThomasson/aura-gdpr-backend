import os
import time
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import settings
from app.db.database import get_db
from app.db.models.user import User

router = APIRouter(prefix="/api/system", tags=["System"])


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
)
async def system_version(request: Request):
    start_time = getattr(request.app.state, "process_start_time", time.time())
    return {
        "version": settings.VERSION,
        "build": settings.BUILD or "unknown",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(start_time)),
    }
