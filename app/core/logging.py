import json
import logging
import time
from typing import Any, Dict

from fastapi import Request


class JsonFormatter(logging.Formatter):
    """Lightweight JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        payload: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "context") and isinstance(record.context, dict):
            payload.update(record.context)
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        user = getattr(request.state, "user", None)
        context = {
            "method": request.method,
            "path": request.url.path,
            "status_code": getattr(response, "status_code", 500),
            "duration_ms": round(duration_ms, 2),
            "user_id": getattr(user, "id", None) or getattr(request.state, "user_id", None),
            "tenant_id": getattr(user, "tenant_id", None) or getattr(request.state, "tenant_id", None),
            "ip": request.client.host if request.client else None,
            "endpoint": request.scope.get("endpoint").__name__ if request.scope.get("endpoint") else None,
        }
        logging.getLogger("api.request").info("request", extra={"context": context})
