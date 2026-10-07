"""Disposable, process-shared hosted quota state; never part of evidence backups.

Reservations commit before HTTP. Failed calls count, and deleting this file
rebuilds empty accounting (it cannot reconstruct usage held by the provider).
"""

from __future__ import annotations

import math
import os
import sqlite3
import stat
import time
from collections.abc import Iterator, Mapping
from contextlib import closing, contextmanager
from datetime import UTC, datetime
from threading import Event
from typing import Any, Literal

from dws.config import Settings, prepare_owner_state

Operation = Literal["search", "fetch"]


class TinyFishQuota:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.path = settings.data_dir / "tinyfish-quota.sqlite3"

    def _windows(self, kind: Operation) -> tuple[tuple[str, int, int], ...]:
        if kind == "search":
            return (
                ("minute", 60, self.settings.tinyfish_search_per_minute),
                ("hour", 3600, self.settings.tinyfish_search_per_hour),
            )
        return (
            ("minute", 60, self.settings.tinyfish_fetch_per_minute),
            ("day", 86400, self.settings.tinyfish_fetch_per_day),
        )

    @staticmethod
    def _used(conn: sqlite3.Connection, kind: Operation, now: float, seconds: int) -> int:
        return int(
            conn.execute(
                "SELECT COALESCE(sum(units),0) FROM reservations WHERE kind=? AND at>?",
                (kind, now - seconds),
            ).fetchone()[0]
        )

    def diagnostics(self) -> dict[str, Any]:
        """Read local accounting only; a missing database represents empty usage."""
        result: dict[str, Any] = {
            "configured": bool(self.settings.tinyfish_api_key),
            "enabled": self.settings.tinyfish_enabled,
            "fetch_escalation": self.settings.tinyfish_fetch_escalation,
            "accounting": "ok",
            "scope": "dws_reservations_only",
        }
        kinds: tuple[Operation, ...] = ("search", "fetch")
        for kind in kinds:
            result[kind] = {
                "windows": [
                    {"window": window, "used": 0, "limit": limit, "remaining": limit}
                    for window, _seconds, limit in self._windows(kind)
                ],
                "cooldown_until": None,
            }
        try:
            try:
                info = self.path.lstat()
            except FileNotFoundError:
                return result
            if not stat.S_ISREG(info.st_mode):
                raise ValueError("Quota state is not a regular file")
            with closing(
                sqlite3.connect(
                    self.path.absolute().as_uri() + "?mode=ro", uri=True, timeout=0.1
                )
            ) as conn:
                deadline = time.monotonic() + 0.1
                conn.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
                # The ~0.1s read lock may delay COMMIT within the writer's 1s busy timeout.
                conn.execute("BEGIN")  # One read snapshot across windows and cooldowns.
                now = time.time()
                for kind in kinds:
                    for window, (_name, seconds, limit) in zip(
                        result[kind]["windows"], self._windows(kind), strict=True
                    ):
                        used = self._used(conn, kind, now, seconds)
                        window.update(used=used, remaining=max(0, limit - used))
                    row = conn.execute(
                        "SELECT until FROM cooldown WHERE kind=?", (kind,)
                    ).fetchone()
                    if row and row[0] > now:
                        result[kind]["cooldown_until"] = datetime.fromtimestamp(
                            row[0], UTC
                        ).isoformat()
        except (sqlite3.Error, OSError, ValueError, TypeError, OverflowError):
            result["accounting"] = "unavailable"
            for kind in kinds:
                result[kind]["cooldown_until"] = None
                for window in result[kind]["windows"]:
                    window.update(used=None, remaining=None)
        return result

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
                for window, seconds, limit in self._windows(kind):
                    used = self._used(conn, kind, now, seconds)
                    if used + units > limit:
                        conn.commit()
                        return "quota_" + window
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
