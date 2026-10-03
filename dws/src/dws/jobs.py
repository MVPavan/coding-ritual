"""Persisted bounded crawl frontier, executed independently of API requests."""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import posixpath
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast
from urllib.parse import unquote, urljoin, urlsplit

from pydantic import ValidationError

from .config import Settings
from .errors import DWSError
from .models import CrawlRequest, FetchRequest, JobRequest
from .net import canonical_url


def _canonical(url: str) -> str:
    return canonical_url(url)


def _path(url: str) -> str:
    return posixpath.normpath(unquote(urlsplit(url).path or "/"))


def _scope_path(url: str) -> str:
    path = _path(url)
    if not urlsplit(url).path.endswith("/") and "." in path.rsplit("/", 1)[-1]:
        path = posixpath.dirname(path)
    return path.rstrip("/") or "/"


class Jobs:
    """A single bounded page executor, with cross-process admission and fencing.

    The execution flock is held during acquisition; metadata/maintenance locks
    are held only for short local operations. Losing a process releases its flock,
    allowing recovery without waiting for a stale timestamp to expire.
    """

    def __init__(self, settings: Settings, store: Any, acquisition: Any) -> None:
        self.settings = settings
        self.store = store
        self.acquisition = acquisition
        self.owner = uuid.uuid4().hex
        self.lock_path = settings.data_dir / "worker-execution.lock"
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._executing = False
        with self._db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS dws_jobs (
                    job_id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL,
                    run_id TEXT, request_json TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    idempotency_key TEXT, state TEXT NOT NULL,
                    cancel_requested INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL, started_at REAL, deadline_at REAL,
                    updated_at REAL NOT NULL, stop_reason TEXT,
                    lease_owner TEXT, lease_until REAL, lease_epoch INTEGER NOT NULL DEFAULT 0,
                    off_scope_count INTEGER NOT NULL DEFAULT 0,
                    depth_limited_count INTEGER NOT NULL DEFAULT 0,
                    duplicate_count INTEGER NOT NULL DEFAULT 0,
                    queue_limited_count INTEGER NOT NULL DEFAULT 0,
                    discovery_limited_count INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(workspace_id, idempotency_key)
                );
                CREATE TABLE IF NOT EXISTS dws_frontier (
                    job_id TEXT NOT NULL REFERENCES dws_jobs(job_id),
                    url TEXT NOT NULL, depth INTEGER NOT NULL, state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, snapshot_id TEXT,
                    error_code TEXT, error_message TEXT,
                    created_at REAL NOT NULL, updated_at REAL NOT NULL,
                    PRIMARY KEY(job_id, url)
                );
                CREATE INDEX IF NOT EXISTS dws_frontier_ready
                    ON dws_frontier(job_id, state, depth, created_at);
            """)
            # API and worker may start together against a pre-existing database.
            # Serialize the additive migration and preserve all acknowledged jobs.
            db.execute("BEGIN IMMEDIATE")
            self.migrate_discovery(db)
            db.commit()

    @staticmethod
    def migrate_discovery(db: sqlite3.Connection) -> None:
        """Upgrade legacy jobs in a caller-owned serialized transaction."""
        columns = {row["name"] for row in db.execute("PRAGMA table_info(dws_jobs)")}
        if not columns or "discovery_limited_count" in columns:
            return
        db.execute(
            "ALTER TABLE dws_jobs ADD COLUMN discovery_limited_count INTEGER NOT NULL DEFAULT 0"
        )
        for job in db.execute(
            "SELECT * FROM dws_jobs WHERE state IN ('queued','running')"
        ).fetchall():
            db.execute(
                "UPDATE dws_jobs SET discovery_limited_count=? WHERE job_id=?",
                (Jobs._discovery_limited_count(db, job), job["job_id"]),
            )

    @contextmanager
    def _db(self) -> Iterator[sqlite3.Connection]:
        with self.store.maintenance(), self.store.connection() as db:
            yield db

    async def submit(self, request: CrawlRequest) -> dict[str, Any]:
        # An acknowledged ID is durable even if its source no longer resolves.
        # Syntax and request identity are local; live policy validation belongs
        # only to admission of a genuinely new job.
        seed = _canonical(request.seed_url)
        try:
            bounded = CrawlRequest.model_validate(
                {
                    **request.model_dump(),
                    "seed_url": seed,
                    "max_pages": min(request.max_pages, self.settings.max_pages),
                    "max_depth": min(request.max_depth, self.settings.max_depth),
                    "max_seconds": min(request.max_seconds, self.settings.max_crawl_seconds),
                }
            )
        except ValidationError:
            raise DWSError(
                "invalid_request", "The canonical crawl request exceeds input limits", 422
            ) from None
        encoded = json.dumps(
            bounded.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        fingerprint = hashlib.sha256(
            json.dumps(
                request.model_copy(update={"seed_url": seed}).model_dump(mode="json"),
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        with self._db() as db:
            db.execute("BEGIN")
            self.store.validate_scope(db, bounded.workspace_id, bounded.run_id)
            previous_id = self._previous_job(db, bounded, fingerprint)
        if previous_id is not None:
            return self.status(
                JobRequest(workspace_id=bounded.workspace_id, job_id=previous_id)
            )
        try:
            await self.acquisition.validate_url(seed)
        except (DWSError, TimeoutError) as error:
            # Another submitter may have admitted this same key while our DNS
            # request was pending. Reuse its durable result without new work.
            with self._db() as db:
                previous_id = self._previous_job(db, bounded, fingerprint)
            if previous_id is not None:
                return self.status(
                    JobRequest(workspace_id=bounded.workspace_id, job_id=previous_id)
                )
            if isinstance(error, TimeoutError):
                raise DWSError(
                    "source_timeout", "Crawl source validation exceeded its deadline", 504
                ) from None
            raise
        now = time.time()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            self.store.validate_scope(db, bounded.workspace_id, bounded.run_id)
            previous_id = self._previous_job(db, bounded, fingerprint)
            if previous_id is not None:
                db.commit()
                return self.status(
                    JobRequest(workspace_id=bounded.workspace_id, job_id=previous_id)
                )
            active = db.execute(
                "SELECT count(*) FROM dws_jobs WHERE state IN ('queued','running')"
            ).fetchone()[0]
            if active >= self.settings.max_jobs:
                raise DWSError("queue_full", "The durable crawl queue is full", 429)
            self.store.admit_metadata(len(encoded.encode()) + len(seed.encode()))
            job_id = "crawl_" + uuid.uuid4().hex
            db.execute(
                "INSERT INTO dws_jobs(job_id,workspace_id,run_id,request_json,fingerprint,"
                "idempotency_key,state,created_at,updated_at) VALUES(?,?,?,?,?,?,'queued',?,?)",
                (
                    job_id,
                    bounded.workspace_id,
                    bounded.run_id,
                    encoded,
                    fingerprint,
                    bounded.idempotency_key,
                    now,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO dws_frontier(job_id,url,depth,state,created_at,updated_at) "
                "VALUES(?,?,0,'queued',?,?)",
                (job_id, seed, now, now),
            )
            db.commit()
        return self.status(JobRequest(workspace_id=bounded.workspace_id, job_id=job_id))

    @staticmethod
    def _previous_job(
        db: sqlite3.Connection, request: CrawlRequest, fingerprint: str
    ) -> str | None:
        if request.idempotency_key is None:
            return None
        previous = db.execute(
            "SELECT job_id,fingerprint FROM dws_jobs "
            "WHERE workspace_id=? AND idempotency_key=?",
            (request.workspace_id, request.idempotency_key),
        ).fetchone()
        if previous is None:
            return None
        if previous["fingerprint"] != fingerprint:
            raise DWSError(
                "idempotency_conflict", "This key already names a different crawl", 409
            )
        return str(previous["job_id"])

    def _job(self, db: sqlite3.Connection, request: JobRequest) -> sqlite3.Row:
        row = db.execute(
            "SELECT * FROM dws_jobs WHERE job_id=? AND workspace_id=?",
            (request.job_id, request.workspace_id),
        ).fetchone()
        if row is None:
            raise DWSError(
                "job_not_found", "No crawl with this ID exists in the workspace", 404
            )
        return cast(sqlite3.Row, row)

    @staticmethod
    def _stored_request(job: sqlite3.Row) -> CrawlRequest | None:
        try:
            request = CrawlRequest.model_validate_json(job["request_json"])
            if request.workspace_id != job["workspace_id"] or request.run_id != job["run_id"]:
                return None
            return CrawlRequest.model_validate(
                {**request.model_dump(), "seed_url": _canonical(request.seed_url)}
            )
        except ValidationError:
            return None
        except DWSError as error:
            if error.code != "invalid_url":
                raise
            return None

    def status(self, request: JobRequest) -> dict[str, Any]:
        with self._db() as db:
            # Progress and the paged manifest must share one committed snapshot.
            db.execute("BEGIN")
            job = self._job(db, request)
            stored_request = self._stored_request(job)
            counts = self._counts(db, request.job_id)
            discovery_limited_count = self._discovery_limited_count(db, job)
            rows = db.execute(
                "SELECT url,depth,state,attempts,snapshot_id,error_code,error_message "
                "FROM dws_frontier "
                "WHERE job_id=? ORDER BY depth,created_at,url LIMIT ? OFFSET ?",
                (request.job_id, request.limit, request.offset),
            ).fetchall()
            parameters = stored_request.model_dump() if stored_request is not None else {}
            state, stop_reason = job["state"], job["stop_reason"]
            if state == "succeeded" and stop_reason == "exhausted" and discovery_limited_count:
                # Historical jobs keep their persisted identity/progress, while the
                # response discloses truncation already recorded in their captures.
                state, stop_reason = "partial", "discovery_limit"
            result = {
                "job_id": job["job_id"],
                "crawl_id": job["job_id"],
                "workspace_id": job["workspace_id"],
                "run_id": job["run_id"],
                "state": state,
                "stop_reason": stop_reason,
                "created_at": job["created_at"],
                "started_at": job["started_at"],
                "updated_at": job["updated_at"],
                "deadline_at": job["deadline_at"],
                "cancel_requested": bool(job["cancel_requested"]),
                "discovery_limited": bool(discovery_limited_count),
                "residual_pages": counts["in_progress"] if job["cancel_requested"] else 0,
                "limits": {
                    key: parameters.get(key)
                    for key in ("max_pages", "max_depth", "max_seconds")
                },
                "scope": {
                    "mode": parameters.get("scope"),
                    "seed_url": parameters.get("seed_url"),
                    "path_prefix": _scope_path(stored_request.seed_url)
                    if stored_request is not None
                    else None,
                },
                "counts": counts,
                "discovery": {
                    key: job[key + "_count"]
                    for key in ("off_scope", "depth_limited", "duplicate", "queue_limited")
                },
                "warnings": ["discovered_links_truncated"] if discovery_limited_count else [],
                "manifest": [dict(row) for row in rows],
                "offset": request.offset,
                "limit": request.limit,
                "next_offset": request.offset + len(rows)
                if request.offset + len(rows) < counts["total"]
                else None,
                "notes": [
                    "max_pages bounds admitted URLs, including failed pages",
                    "Indexing may remain pending after crawl completion",
                    "discovery_limited counts pages; the omitted link count is unknown",
                ],
            }
            result["discovery"]["discovery_limited"] = discovery_limited_count
            if stored_request is None:
                result["request_error"] = {
                    "code": "invalid_persisted_request",
                    "message": "Stored crawl request is invalid",
                }
                result["warnings"].append("invalid_persisted_request")
            while (
                result["manifest"] and len(json.dumps(result)) > self.settings.max_output_chars
            ):
                result["manifest"].pop()
                result["next_offset"] = request.offset + len(result["manifest"])
            if rows and not result["manifest"]:
                raise DWSError(
                    "output_limit",
                    "Increase the operator output limit to inspect this crawl manifest",
                    413,
                )
            return result

    def cancel(self, request: JobRequest) -> dict[str, Any]:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            job = self._job(db, request)
            if job["state"] in ("queued", "running"):
                now = time.time()
                db.execute(
                    "UPDATE dws_jobs SET cancel_requested=1,updated_at=? WHERE job_id=?",
                    (now, request.job_id),
                )
                if not self._counts(db, request.job_id)["in_progress"]:
                    self._finish(db, request.job_id, "cancelled")
            db.commit()
        return self.status(request)

    @staticmethod
    def _counts(db: sqlite3.Connection, job_id: str) -> dict[str, int]:
        counts = dict.fromkeys(
            ("queued", "in_progress", "succeeded", "failed", "cancelled", "skipped"), 0
        )
        for row in db.execute(
            "SELECT state,count(*) AS n FROM dws_frontier WHERE job_id=? GROUP BY state",
            (job_id,),
        ):
            counts[row["state"]] = row["n"]
        counts["total"] = sum(counts.values())
        return counts

    @staticmethod
    def _discovery_limited_count(
        db: sqlite3.Connection, job: sqlite3.Row | dict[str, Any]
    ) -> int:
        if job["discovery_limited_count"]:
            return int(job["discovery_limited_count"])
        # Older acknowledged work already retained acquisition warnings even
        # before the job had its own durable discovery counter.
        return int(
            db.execute(
                "SELECT count(*) FROM dws_frontier f JOIN snapshots s ON s.id=f.snapshot_id "
                "WHERE f.job_id=? AND f.state='succeeded' AND EXISTS "
                "(SELECT 1 FROM json_each(s.warnings_json) "
                "WHERE value='discovered_links_truncated')",
                (job["job_id"],),
            ).fetchone()[0]
        )

    def _finish(self, db: sqlite3.Connection, job_id: str, reason: str | None = None) -> None:
        job = db.execute("SELECT * FROM dws_jobs WHERE job_id=?", (job_id,)).fetchone()
        counts = self._counts(db, job_id)
        discovery_limited_count = self._discovery_limited_count(db, job)
        reason = reason or (
            "page_limit"
            if job["queue_limited_count"]
            else "depth_limit"
            if job["depth_limited_count"]
            else "discovery_limit"
            if discovery_limited_count
            else "exhausted"
        )
        if reason == "cancelled":
            state, frontier_state = "cancelled", "cancelled"
        elif reason == "invalid_persisted_request":
            state = "partial" if counts["succeeded"] else "failed"
            frontier_state = "skipped"
        elif counts["succeeded"] == 0 and counts["failed"]:
            state, frontier_state, reason = "failed", "skipped", "error"
        elif reason != "exhausted" or counts["failed"]:
            state, frontier_state = "partial", "skipped"
        else:
            state, frontier_state = "succeeded", "skipped"
        now = time.time()
        db.execute(
            "UPDATE dws_frontier SET state=?,updated_at=? WHERE job_id=? AND state='queued'",
            (frontier_state, now, job_id),
        )
        db.execute(
            "UPDATE dws_jobs SET state=?,stop_reason=?,updated_at=?,"
            "discovery_limited_count=?,lease_owner=NULL,lease_until=NULL WHERE job_id=?",
            (state, reason, now, discovery_limited_count, job_id),
        )

    def _claim(self) -> tuple[dict[str, Any], dict[str, Any]] | None:
        now = time.time()
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            # The global execution flock proves there is no other live page
            # executor. Recover abandoned frontier work, regardless of timestamp.
            db.execute(
                "UPDATE dws_frontier SET state='queued',updated_at=? "
                "WHERE state='in_progress' AND job_id IN "
                "(SELECT job_id FROM dws_jobs WHERE state IN ('queued','running'))",
                (now,),
            )
            jobs = db.execute(
                "SELECT * FROM dws_jobs WHERE state IN ('queued','running') "
                "ORDER BY updated_at,created_at"
            ).fetchall()
            for job in jobs:
                if job["cancel_requested"]:
                    self._finish(db, job["job_id"], "cancelled")
                    continue
                request = self._stored_request(job)
                if request is None:
                    db.execute(
                        "UPDATE dws_frontier SET error_code='invalid_persisted_request',"
                        "error_message='Stored crawl request is invalid' "
                        "WHERE job_id=? AND state='queued'",
                        (job["job_id"],),
                    )
                    self._finish(db, job["job_id"], "invalid_persisted_request")
                    continue
                deadline = job["deadline_at"] or now + request.max_seconds
                if now >= deadline:
                    self._finish(db, job["job_id"], "time_limit")
                    continue
                page = db.execute(
                    "SELECT * FROM dws_frontier WHERE job_id=? AND state='queued' "
                    "ORDER BY depth,created_at,url LIMIT 1",
                    (job["job_id"],),
                ).fetchone()
                if page is None:
                    self._finish(db, job["job_id"])
                    continue
                if page["attempts"] >= 2:
                    db.execute(
                        "UPDATE dws_frontier SET state='failed',error_code='attempt_limit',"
                        "error_message='Acquisition attempt limit reached',updated_at=? "
                        "WHERE job_id=? AND url=?",
                        (now, job["job_id"], page["url"]),
                    )
                    continue
                epoch = job["lease_epoch"] + 1
                db.execute(
                    "UPDATE dws_jobs SET state='running',"
                    "started_at=COALESCE(started_at,?),deadline_at=?,"
                    "lease_owner=?,lease_until=?,lease_epoch=?,updated_at=? WHERE job_id=?",
                    (
                        now,
                        deadline,
                        self.owner,
                        now + self.settings.lease_seconds,
                        epoch,
                        now,
                        job["job_id"],
                    ),
                )
                db.execute(
                    "UPDATE dws_frontier SET state='in_progress',attempts=attempts+1,"
                    "updated_at=? WHERE job_id=? AND url=?",
                    (now, job["job_id"], page["url"]),
                )
                claimed = dict(job)
                claimed.update(
                    lease_epoch=epoch,
                    deadline_at=deadline,
                    request_json=json.dumps(
                        request.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
                    ),
                )
                db.commit()
                return claimed, dict(page)
            db.commit()
        return None

    def _fence(self, db: sqlite3.Connection, job: dict[str, Any]) -> None:
        row = db.execute(
            "SELECT state,lease_owner,lease_epoch,lease_until FROM dws_jobs WHERE job_id=?",
            (job["job_id"],),
        ).fetchone()
        if (
            row is None
            or row["state"] != "running"
            or row["lease_owner"] != self.owner
            or row["lease_epoch"] != job["lease_epoch"]
            or row["lease_until"] <= time.time()
        ):
            raise DWSError(
                "lease_lost", "Crawl page ownership expired; publication refused", 409
            )

    async def _heartbeat(self, job: dict[str, Any], stopped: asyncio.Event) -> None:
        while not stopped.is_set():
            try:
                await asyncio.wait_for(
                    stopped.wait(), timeout=min(10.0, self.settings.lease_seconds / 3)
                )
            except TimeoutError:
                with self._db() as db:
                    db.execute(
                        "UPDATE dws_jobs SET lease_until=? WHERE job_id=? AND lease_owner=? "
                        "AND lease_epoch=? AND state='running'",
                        (
                            time.time() + self.settings.lease_seconds,
                            job["job_id"],
                            self.owner,
                            job["lease_epoch"],
                        ),
                    )

    @staticmethod
    def _in_scope(request: CrawlRequest, url: str) -> bool:
        seed, candidate = urlsplit(request.seed_url), urlsplit(url)
        if candidate.scheme not in ("http", "https") or (
            candidate.hostname,
            candidate.port,
        ) != (seed.hostname, seed.port):
            return False
        prefix = _scope_path(request.seed_url)
        return (
            request.scope == "same_host"
            or prefix == "/"
            or _path(url) == prefix
            or _path(url).startswith(prefix + "/")
        )

    def _publish_links(
        self,
        db: sqlite3.Connection,
        job: dict[str, Any],
        page: dict[str, Any],
        final_url: str,
        links: list[str],
    ) -> str | None:
        request = CrawlRequest.model_validate_json(job["request_json"])
        total = self._counts(db, job["job_id"])["total"]
        increments = dict.fromkeys(
            ("off_scope", "depth_limited", "duplicate", "queue_limited"), 0
        )
        admission_stop: str | None = None
        for link in links[:10_000]:
            try:
                url = _canonical(urljoin(final_url, link))
                if not self._in_scope(request, url):
                    increments["off_scope"] += 1
                    continue
            except (ValueError, DWSError):
                increments["off_scope"] += 1
                continue
            if db.execute(
                "SELECT 1 FROM dws_frontier WHERE job_id=? AND url=?", (job["job_id"], url)
            ).fetchone():
                increments["duplicate"] += 1
                continue
            if page["depth"] >= request.max_depth:
                increments["depth_limited"] += 1
                continue
            if total >= request.max_pages:
                increments["queue_limited"] += 1
                continue
            try:
                self.store.admit_metadata(len(url.encode()))
            except DWSError as error:
                if error.code not in ("storage_limit", "disk_pressure"):
                    raise
                # Preserve this captured page and the already admitted frontier.
                # Only further discovery stops when metadata cannot be admitted.
                admission_stop = error.code
                increments["queue_limited"] += 1
                break
            now = time.time()
            db.execute(
                "INSERT INTO dws_frontier(job_id,url,depth,state,created_at,updated_at) "
                "VALUES(?,?,?,'queued',?,?)",
                (job["job_id"], url, page["depth"] + 1, now, now),
            )
            total += 1
        for name, amount in increments.items():
            db.execute(
                f"UPDATE dws_jobs SET {name}_count={name}_count+? WHERE job_id=?",
                (amount, job["job_id"]),
            )
        return admission_stop

    def _complete_page(
        self,
        db: sqlite3.Connection,
        job: dict[str, Any],
        page: dict[str, Any],
        capture: Any,
        snapshot: dict[str, Any],
    ) -> None:
        """Join capture publication and frontier progress in one metadata commit."""
        self._fence(db, job)
        current = db.execute(
            "SELECT * FROM dws_jobs WHERE job_id=?", (job["job_id"],)
        ).fetchone()
        discovery_limited = (
            "discovered_links_truncated" in capture.warnings or len(capture.links) > 10_000
        )
        previous_discovery_count = (
            self._discovery_limited_count(db, current) if discovery_limited else 0
        )
        db.execute(
            "UPDATE dws_frontier SET state='succeeded',snapshot_id=?,error_code=NULL,"
            "error_message=NULL,updated_at=? WHERE job_id=? AND url=?",
            (snapshot["snapshot_id"], time.time(), job["job_id"], page["url"]),
        )
        if discovery_limited:
            # A captured page remains useful even when its links were bounded.
            # Persist that observation with the page before cancellation/limits
            # can finish the job, and keep processing its admitted frontier.
            db.execute(
                "UPDATE dws_jobs SET discovery_limited_count=? WHERE job_id=?",
                (previous_discovery_count + 1, job["job_id"]),
            )
        if current["cancel_requested"]:
            self._finish(db, job["job_id"], "cancelled")
            return
        admission_stop = self._publish_links(db, job, page, capture.final_url, capture.links)
        if admission_stop is not None:
            self._finish(db, job["job_id"], admission_stop)
        elif time.time() >= job["deadline_at"]:
            self._finish(db, job["job_id"], "time_limit")
        elif not self._counts(db, job["job_id"])["queued"]:
            self._finish(db, job["job_id"])
        else:
            db.execute(
                "UPDATE dws_jobs SET updated_at=?,lease_owner=NULL,lease_until=NULL "
                "WHERE job_id=?",
                (time.time(), job["job_id"]),
            )

    async def tick(self) -> bool:
        if self._executing:
            return False
        with self.lock_path.open("a+b") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
            self._executing = True
            try:
                claim = self._claim()
                if claim is None:
                    return False
                job, page = claim
                request = CrawlRequest.model_validate_json(job["request_json"])
                stopped = asyncio.Event()
                heartbeat = asyncio.create_task(self._heartbeat(job, stopped))
                try:
                    timeout = min(
                        self.settings.request_timeout,
                        max(0.001, job["deadline_at"] - time.time()),
                    )
                    async with asyncio.timeout(timeout):
                        capture = await self.acquisition.fetch(
                            FetchRequest(
                                workspace_id=request.workspace_id,
                                run_id=request.run_id,
                                url=page["url"],
                                render=request.render,
                            ),
                            scope_check=lambda target: self._in_scope(request, target),
                        )
                    if not self._in_scope(request, _canonical(capture.final_url)):
                        raise DWSError(
                            "scope_denied", "Crawl document redirected outside its scope", 403
                        )
                    self.store.save_capture(
                        capture,
                        workspace_id=request.workspace_id,
                        run_id=request.run_id,
                        crawl_id=job["job_id"],
                        fence=lambda db: self._fence(db, job),
                        on_commit=lambda db, snapshot: self._complete_page(
                            db, job, page, capture, snapshot
                        ),
                    )
                except asyncio.CancelledError:
                    self._release_page(
                        job,
                        page,
                        "worker_interrupted",
                        "Worker stopped; page remains resumable",
                        retry=True,
                    )
                    raise
                except Exception as error:
                    code = (
                        error.code
                        if isinstance(error, DWSError)
                        else "timeout"
                        if isinstance(error, TimeoutError)
                        else "acquisition_failed"
                    )
                    message = (
                        error.message
                        if isinstance(error, DWSError)
                        else "Acquisition timed out"
                        if isinstance(error, TimeoutError)
                        else "Page acquisition failed"
                    )
                    retry = (
                        code
                        not in (
                            "policy_denied",
                            "scope_denied",
                            "invalid_url",
                            "response_too_large",
                            "lease_lost",
                            "storage_limit",
                            "disk_pressure",
                        )
                        and page["attempts"] + 1 < 2
                    )
                    self._release_page(job, page, code, message, retry)
                finally:
                    stopped.set()
                    await heartbeat
                return True
            finally:
                self._executing = False

    def _release_page(
        self, job: dict[str, Any], page: dict[str, Any], code: str, message: str, retry: bool
    ) -> None:
        with self._db() as db:
            db.execute("BEGIN IMMEDIATE")
            current = db.execute(
                "SELECT * FROM dws_jobs WHERE job_id=? AND lease_owner=? AND lease_epoch=?",
                (job["job_id"], self.owner, job["lease_epoch"]),
            ).fetchone()
            if current:
                db.execute(
                    "UPDATE dws_frontier SET state=?,error_code=?,error_message=?,updated_at=? "
                    "WHERE job_id=? AND url=? AND state='in_progress'",
                    (
                        "queued" if retry else "failed",
                        code,
                        message[:512],
                        time.time(),
                        job["job_id"],
                        page["url"],
                    ),
                )
                if current["cancel_requested"]:
                    self._finish(db, job["job_id"], "cancelled")
                elif time.time() >= current["deadline_at"]:
                    self._finish(db, job["job_id"], "time_limit")
                elif not self._counts(db, job["job_id"])["queued"]:
                    self._finish(db, job["job_id"])
                else:
                    db.execute(
                        "UPDATE dws_jobs SET updated_at=?,lease_owner=NULL,lease_until=NULL "
                        "WHERE job_id=?",
                        (time.time(), job["job_id"]),
                    )
            db.commit()
