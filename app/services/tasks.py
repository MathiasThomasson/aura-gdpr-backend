import asyncio
from datetime import timedelta
from typing import Awaitable, Callable, Optional

from fastapi import BackgroundTasks


def fire_and_forget(background_tasks: BackgroundTasks, fn: Callable, *args, **kwargs) -> None:
    """Queue a function to run after the response is sent."""
    background_tasks.add_task(fn, *args, **kwargs)


def schedule_task(fn: Callable[..., Awaitable], delay: Optional[timedelta] = None, *args, **kwargs) -> asyncio.Task:
    """Simple scheduler placeholder; suitable for cron/worker integration later."""

    async def _runner():
        if delay:
            await asyncio.sleep(delay.total_seconds())
        return await fn(*args, **kwargs)

    return asyncio.create_task(_runner())
