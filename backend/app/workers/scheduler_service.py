from __future__ import annotations

import asyncio
import logging
import signal
from datetime import UTC, datetime

from app.workers.tasks.scheduler import run_scheduler_tick


logger = logging.getLogger(__name__)


def seconds_to_next_minute(now: datetime | None = None) -> float:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    elapsed = current.second + current.microsecond / 1_000_000
    return max(0.1, 60.0 - elapsed)


async def serve(max_consecutive_failures: int = 5) -> None:
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(signum, stop.set)
        except NotImplementedError:  # pragma: no cover - Windows development only
            pass

    failures = 0
    while not stop.is_set():
        try:
            dispatched = await run_scheduler_tick()
            failures = 0
            logger.info("scheduler_tick_complete", extra={"jobs_dispatched": len(dispatched)})
        except Exception:
            failures += 1
            logger.exception(
                "scheduler_tick_failed",
                extra={"consecutive_failures": failures},
            )
            if failures >= max_consecutive_failures:
                raise
        try:
            await asyncio.wait_for(stop.wait(), timeout=seconds_to_next_minute())
        except TimeoutError:
            continue


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
