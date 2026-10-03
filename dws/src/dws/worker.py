"""Independent durable crawl and derived-index worker process."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from contextlib import suppress

from .config import Settings
from .jobs import Jobs
from .providers import Acquisition
from .store import Store


async def run(settings: Settings, *, once: bool = False, idle_seconds: float = 2) -> None:
    store = Store(settings)
    jobs = Jobs(settings, store, Acquisition(settings))
    stopping = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(signum, stopping.set)
    logger = logging.getLogger("dws.worker")
    try:
        while not stopping.is_set():
            worked = False
            try:
                worked = await jobs.tick()
                if not stopping.is_set():
                    worked = bool(await asyncio.to_thread(store.index_pending, 20)) or worked
            except Exception as error:
                logger.error(
                    "Worker operation failed (%s); durable work remains resumable",
                    type(error).__name__,
                )
            if once:
                return
            if not worked and not stopping.is_set():
                with suppress(TimeoutError):
                    await asyncio.wait_for(stopping.wait(), timeout=idle_seconds)
    finally:
        for signum in (signal.SIGINT, signal.SIGTERM):
            loop.remove_signal_handler(signum)


def main() -> None:
    parser = argparse.ArgumentParser(description="Execute persisted DWS crawls and indexing")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Execute at most one page and bounded indexing batch",
    )
    parser.add_argument(
        "--idle-seconds",
        type=float,
        default=2,
        help="Idle poll interval, between 0.1 and 60 seconds",
    )
    args = parser.parse_args()
    if not 0.1 <= args.idle_seconds <= 60:
        parser.error("--idle-seconds must be between 0.1 and 60")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(run(Settings.from_env(), once=args.once, idle_seconds=args.idle_seconds))


if __name__ == "__main__":
    main()
