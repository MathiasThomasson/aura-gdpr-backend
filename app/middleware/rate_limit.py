import asyncio
import time
from collections import OrderedDict
from functools import wraps
from typing import Awaitable, Callable, Optional

from fastapi import HTTPException, Request

RateLimitedCallable = Callable[..., Awaitable]


_lock = asyncio.Lock()
_state: dict[str, OrderedDict[str, list[float]]] = {}
_MAX_IPS_PER_SCOPE = 10000
_HEALTH_PATHS = {"/api/system/ping", "/api/system/health", "/api/health"}


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


async def _enforce(scope: str, limit: int, window_seconds: int, request: Request) -> None:
    now = time.time()
    ip = _client_ip(request)
    async with _lock:
        scope_state = _state.setdefault(scope, OrderedDict())
        entries = scope_state.get(ip, [])
        cutoff = now - window_seconds
        entries = [ts for ts in entries if ts >= cutoff]
        if len(entries) >= limit:
            raise HTTPException(status_code=429, detail="Too many requests; please try again later.")
        entries.append(now)
        scope_state[ip] = entries
        scope_state.move_to_end(ip)
        # LRU cleanup
        while len(scope_state) > _MAX_IPS_PER_SCOPE:
            scope_state.popitem(last=False)


def rate_limit(scope: str, *, limit: int, window_seconds: int = 60) -> Callable[[RateLimitedCallable], RateLimitedCallable]:
    """Decorator to enforce per-IP rate limiting for a given scope."""

    def decorator(func: RateLimitedCallable) -> RateLimitedCallable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Optional[Request] = kwargs.get("request")
            if request is None:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
            if request is None:
                raise RuntimeError("rate_limit decorator requires a Request argument")
            if request.url.path in _HEALTH_PATHS:
                return await func(*args, **kwargs)
            await _enforce(scope, limit, window_seconds, request)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def rate_limit_dependency(scope: str, *, limit: int, window_seconds: int = 60) -> Callable[[Request], Awaitable[None]]:
    """Dependency-friendly variant."""

    async def dependency(request: Request) -> None:
        if request.url.path in _HEALTH_PATHS:
            return
        await _enforce(scope, limit, window_seconds, request)

    return dependency
