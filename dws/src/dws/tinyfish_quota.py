"""Disposable, process-shared hosted quota state; never part of evidence backups.

Reservations commit before HTTP. Failed calls count, and deleting this file
rebuilds empty accounting (it cannot reconstruct usage held by the provider).
"""

from __future__ import annotations

import math
import os
import sqlite3
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime
from threading import Event
from typing import Any, Literal

from dws.config import Settings, prepare_owner_state

Operation = Literal["search", "fetch"]


class TinyFishQuota:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = settings.data_dir / "tinyfish-quota.sqlite3"

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        prepare_owner_state(self.settings.data_dir)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.close(fd)
        conn = sqlite3.connect(self.path, timeout=1)
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS reservations (kind TEXT, at REAL, units INT)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS quota_window ON reservations(kind,at)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cooldown (kind TEXT PRIMARY KEY, until REAL)"
            )
            yield conn
        finally:
            conn.close()

    def reserve(
        self,
        kind: Operation,
        units: int = 1,
        *,
        reservation_id: int | None = None,
        deadline: float | None = None,
        minimum_remaining: float = 0,
        abandoned: Event | None = None,
    ) -> str | None:
        """Atomically reserve units in both rolling windows, or return a skip code."""
        try:
            with self.connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                now = time.time()
                conn.execute("DELETE FROM reservations WHERE at<=?", (now - 86400,))
                row = conn.execute(
                    "SELECT until FROM cooldown WHERE kind=?", (kind,)
                ).fetchone()
                if row and row[0] > now:
                    conn.commit()
                    return "server_cooldown"
                windows = (
                    (
                        (60, self.settings.tinyfish_search_per_minute, "quota_minute"),
                        (3600, self.settings.tinyfish_search_per_hour, "quota_hour"),
                    )
                    if kind == "search"
                    else (
                        (60, self.settings.tinyfish_fetch_per_minute, "quota_minute"),
                        (86400, self.settings.tinyfish_fetch_per_day, "quota_day"),
                    )
                )
                for seconds, limit, code in windows:
                    used = conn.execute(
                        "SELECT COALESCE(sum(units),0) FROM reservations WHERE kind=? AND at>?",
                        (kind, now - seconds),
                    ).fetchone()[0]
                    if used + units > limit:
                        conn.commit()
                        return code
                # A delayed/cancelled executor must not spend an unsendable unit.
                # This check occurs under the write lock, immediately before insert.
                if (abandoned is not None and abandoned.is_set()) or (
                    deadline is not None and deadline - time.monotonic() < minimum_remaining
                ):
                    conn.rollback()
                    return "provider_timeout"
                conn.execute(
                    "INSERT INTO reservations(rowid,kind,at,units) VALUES (?,?,?,?)",
                    (reservation_id, kind, now, units),
                )
                conn.commit()
                return None
        except (sqlite3.Error, OSError, ValueError):
            # Fail closed: accounting unavailable must never allow an unreserved call.
            return "unavailable"

    def release(self, kind: Operation, reservation_id: int) -> None:
        """Release this unsent reservation only; sent failures must keep counting."""
        try:
            with self.connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "DELETE FROM reservations WHERE kind=? AND rowid=?",
                    (kind, reservation_id),
                )
                conn.commit()
        except (sqlite3.Error, OSError, ValueError):
            pass  # Fail closed if operational storage cannot release an unused unit.

    def observe(
        self,
        kind: Operation,
        status: int,
        headers: Mapping[str, str],
        body: dict[str, Any] | None = None,
    ) -> None:
        now = time.time()
        bound = 3600 if kind == "search" else 86400
        deadlines: list[float] = []

        def add(value: object, *, relative: bool = False) -> None:
            try:
                number = float(str(value)) + (now if relative else 0)
                if math.isfinite(number) and number > now:
                    deadlines.append(min(number, now + bound))
            except (ValueError, TypeError, OverflowError):
                pass

        if status == 429 or headers.get("x-ratelimit-remaining") == "0":
            add(headers.get("x-ratelimit-reset"))
            if status == 429:
                add(headers.get("retry-after"), relative=True)
                error = (body or {}).get("error")
                details = error.get("details") if isinstance(error, dict) else None
                if isinstance(details, dict):
                    reset = details.get("resets_at")
                    if isinstance(reset, str) and len(reset) <= 64:
                        try:
                            parsed = datetime.fromisoformat(reset.replace("Z", "+00:00"))
                            if parsed.tzinfo is not None:
                                add(parsed.timestamp())
                        except (ValueError, OverflowError, OSError):
                            pass
                if not deadlines:
                    deadlines.append(now + 60)
        if not deadlines:
            return
        try:
            with self.connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO cooldown VALUES (?,?) ON CONFLICT(kind) DO UPDATE "
                    "SET until=max(until,excluded.until)",
                    (kind, max(deadlines)),
                )
                conn.commit()
        except (sqlite3.Error, OSError, ValueError):
            pass  # Reservations still enforce local limits if a signal cannot be saved.
