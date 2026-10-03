"""Canonical captured evidence, short SQLite transactions, and rebuildable FTS5.

The management database owns identity and retention. The separate FTS database
is disposable. No acquisition or provider call runs under a store lock.
"""

from __future__ import annotations

import bisect
import contextlib
import errno
import fcntl
import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

from dws.config import Settings, prepare_owner_state
from dws.errors import DWSError
from dws.models import Capture, FetchRequest, ReadRequest, RetrieveRequest

METADATA_HEADROOM = 262_144


def _stamp(value: float | None = None) -> str:
    return datetime.fromtimestamp(value if value is not None else time.time(), UTC).isoformat()


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class Store:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = prepare_owner_state(settings.data_dir).resolve()
        for name in ("artifacts", "locks", "staging", "exports", "backups"):
            self._owned(self.root / name).mkdir(exist_ok=True)
        self.metadata_path = self.root / "management.sqlite3"
        self.index_path = self.root / "index.sqlite3"
        with self.maintenance(exclusive=True), self.connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS workspaces (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
                    name TEXT NOT NULL, created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspaces(id),
                    canonical_url TEXT NOT NULL, created_at REAL NOT NULL,
                    UNIQUE(workspace_id, canonical_url)
                );
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
                    workspace_id TEXT NOT NULL REFERENCES workspaces(id), run_id TEXT,
                    crawl_id TEXT, requested_url TEXT NOT NULL, final_url TEXT NOT NULL,
                    captured_at REAL NOT NULL, raw_hash TEXT NOT NULL, text_hash TEXT NOT NULL,
                    mapping_hash TEXT NOT NULL, content_type TEXT NOT NULL, title TEXT NOT NULL,
                    normalizer TEXT NOT NULL, provider TEXT NOT NULL,
                    redirects_json TEXT NOT NULL, warnings_json TEXT NOT NULL,
                    links_json TEXT NOT NULL, artifact_dir TEXT NOT NULL,
                    text_chars INTEGER NOT NULL, line_count INTEGER NOT NULL,
                    total_bytes INTEGER NOT NULL, expires_at REAL NOT NULL,
                    pinned INTEGER NOT NULL DEFAULT 0, expired INTEGER NOT NULL DEFAULT 0,
                    expired_at REAL, index_state TEXT NOT NULL DEFAULT 'pending',
                    indexed_at REAL, index_error TEXT
                );
                CREATE INDEX IF NOT EXISTS snapshot_lookup
                    ON snapshots(workspace_id, requested_url, captured_at DESC);
                CREATE TABLE IF NOT EXISTS snapshot_contexts (
                    snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
                    workspace_id TEXT NOT NULL, run_id TEXT NOT NULL DEFAULT '',
                    crawl_id TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY(snapshot_id, run_id, crawl_id)
                );
                CREATE INDEX IF NOT EXISTS context_scope
                    ON snapshot_contexts(workspace_id, run_id, crawl_id);
                CREATE TABLE IF NOT EXISTS capture_events (
                    id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
                    workspace_id TEXT NOT NULL, run_id TEXT, crawl_id TEXT,
                    occurred_at REAL NOT NULL, kind TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS index_outbox (
                    snapshot_id TEXT PRIMARY KEY REFERENCES snapshots(id),
                    action TEXT NOT NULL, queued_at REAL NOT NULL
                );
            """)
            conn.execute(
                "INSERT OR IGNORE INTO workspaces VALUES ('default', 'Default', ?)",
                (time.time(),),
            )
        try:
            self._ensure_index()
        except (sqlite3.Error, DWSError) as exc:
            if isinstance(exc, DWSError) and exc.code not in (
                "storage_limit",
                "disk_pressure",
                "store_busy",
            ):
                raise
            # A broken disposable index must not disable canonical reads or
            # prevent an operator from requesting an explicit rebuild.
            with self.connection() as conn:
                conn.execute(
                    "UPDATE snapshots SET index_state='unavailable',"
                    "index_error='index_unavailable' WHERE expired=0"
                )

    def _owned(self, path: Path) -> Path:
        resolved = path.resolve()
        if not resolved.is_relative_to(self.root) or resolved == self.root:
            raise DWSError("unsafe_path", "Path is outside the DWS state directory.", 400)
        return resolved

    @contextlib.contextmanager
    def _lock(self, name: str, exclusive: bool = True, timeout: float = 10) -> Iterator[None]:
        path = self._owned(self.root / "locks" / (name + ".lock"))
        with path.open("a+b") as handle:
            mode = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
            until = time.monotonic() + timeout
            while True:
                try:
                    fcntl.flock(handle.fileno(), mode | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= until:
                        raise DWSError(
                            "store_busy", "Store maintenance is busy; retry shortly.", 503
                        ) from None
                    time.sleep(0.025)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def maintenance(
        self, exclusive: bool = False, timeout: float = 10
    ) -> contextlib.AbstractContextManager[None]:
        """Jobs must use this around local transactions, never network calls."""
        return self._lock("maintenance", exclusive, timeout)

    @contextlib.contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.metadata_path, timeout=10, uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA wal_autocheckpoint=16")
        conn.execute("PRAGMA cache_size=-64")
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _index_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.index_path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA wal_autocheckpoint=16")
        conn.execute("PRAGMA cache_size=-64")
        return conn

    def _ensure_index(self) -> None:
        with (
            self.maintenance(),
            self._lock("index-writer"),
            self._lock("artifact-publication"),
            self.connection() as meta,
        ):
            reset = not self.index_path.exists()
            if not reset:
                probe = sqlite3.connect(self.index_path.as_uri() + "?mode=ro", uri=True)
                try:
                    schema = probe.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='passages'"
                    ).fetchone()
                    reset = not schema
                    if (
                        schema
                        and not probe.execute("SELECT 1 FROM passages LIMIT 1").fetchone()
                    ):
                        reset = bool(
                            meta.execute(
                                "SELECT 1 FROM snapshots WHERE expired=0 "
                                "AND index_state='ready' LIMIT 1"
                            ).fetchone()
                        )
                except sqlite3.Error:
                    # The index is disposable. A corrupt or partly initialized
                    # file is recovered only after its durable rebuild intent.
                    reset = True
                finally:
                    probe.close()
            if reset:
                self._prepare_index_rebuild(meta)
                for suffix in ("", "-wal", "-shm"):
                    self._owned(Path(str(self.index_path) + suffix)).unlink(missing_ok=True)
            conn = self._index_connection()
            try:
                conn.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS passages USING fts5(
                    text, snapshot_id UNINDEXED, document_id UNINDEXED,
                    line_start UNINDEXED, line_end UNINDEXED,
                    char_start UNINDEXED, char_end UNINDEXED, tokenize='unicode61'
                )""")
                conn.commit()
            finally:
                conn.close()

    def _prepare_index_rebuild(self, meta: sqlite3.Connection) -> None:
        """Commit recovery intent before changing the disposable index files.

        The caller holds maintenance and index-writer ownership. FULL metadata
        durability guarantees a killed initializer/rebuilder leaves an outbox
        the normal worker can resume, even when a new empty index already exists.
        """
        meta.execute("BEGIN IMMEDIATE")
        count = meta.execute("SELECT count(*) FROM snapshots WHERE expired=0").fetchone()[0]
        self.admit_metadata(8192 + count * 128)
        meta.execute(
            "UPDATE snapshots SET index_state='pending',indexed_at=NULL,"
            "index_error=NULL WHERE expired=0"
        )
        meta.execute("DELETE FROM index_outbox")
        meta.execute(
            "INSERT INTO index_outbox SELECT id,'upsert',? FROM snapshots WHERE expired=0",
            (time.time(),),
        )
        meta.commit()

    def _validate_scope(
        self, conn: sqlite3.Connection, workspace_id: str, run_id: str | None = None
    ) -> None:
        if not conn.execute("SELECT 1 FROM workspaces WHERE id=?", (workspace_id,)).fetchone():
            raise DWSError("workspace_not_found", "Workspace does not exist.", 404)
        if (
            run_id
            and not conn.execute(
                "SELECT 1 FROM runs WHERE id=? AND workspace_id=?", (run_id, workspace_id)
            ).fetchone()
        ):
            raise DWSError("run_not_found", "Run does not exist in this workspace.", 404)

    def validate_scope(
        self, conn: sqlite3.Connection, workspace_id: str, run_id: str | None = None
    ) -> None:
        """Validate persisted scope in the caller's own acknowledgement transaction."""
        self._validate_scope(conn, workspace_id, run_id)

    def create_workspace(self, name: str) -> dict[str, Any]:
        if not name.strip() or len(name) > 256:
            raise DWSError("invalid_name", "Name must contain 1 to 256 characters.")
        ident, now = str(uuid.uuid4()), time.time()
        with self.maintenance(), self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self.admit_metadata(len(name.encode("utf-8")) + 128)
            conn.execute("INSERT INTO workspaces VALUES (?, ?, ?)", (ident, name, now))
        return {"workspace_id": ident, "name": name, "created_at": _stamp(now)}

    def create_run(self, workspace_id: str, name: str) -> dict[str, Any]:
        if not name.strip() or len(name) > 256:
            raise DWSError("invalid_name", "Name must contain 1 to 256 characters.")
        ident, now = str(uuid.uuid4()), time.time()
        with self.maintenance(), self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._validate_scope(conn, workspace_id)
            self.admit_metadata(len(name.encode("utf-8")) + len(workspace_id) + 128)
            conn.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?)", (ident, workspace_id, name, now)
            )
        return {
            "run_id": ident,
            "workspace_id": workspace_id,
            "name": name,
            "created_at": _stamp(now),
        }

    @staticmethod
    def _pagination(limit: int, offset: int) -> None:
        if not 1 <= limit <= 100 or offset < 0:
            raise DWSError("invalid_pagination", "Use limit 1 to 100 and a nonnegative offset.")

    def list_workspaces(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        self._pagination(limit, offset)
        with self.maintenance(), self.connection() as conn:
            conn.execute("BEGIN")
            total = conn.execute("SELECT count(*) FROM workspaces").fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM workspaces ORDER BY created_at,id LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            return {
                "workspaces": [
                    {
                        "workspace_id": row["id"],
                        "name": row["name"][:256],
                        "created_at": _stamp(row["created_at"]),
                    }
                    for row in rows
                ],
                "total": total,
                "offset": offset,
                "limit": limit,
                "next_offset": offset + len(rows) if offset + len(rows) < total else None,
            }

    def list_runs(self, workspace_id: str, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        self._pagination(limit, offset)
        with self.maintenance(), self.connection() as conn:
            conn.execute("BEGIN")
            self._validate_scope(conn, workspace_id)
            total = conn.execute(
                "SELECT count(*) FROM runs WHERE workspace_id=?", (workspace_id,)
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT * FROM runs WHERE workspace_id=? "
                "ORDER BY created_at,id LIMIT ? OFFSET ?",
                (workspace_id, limit, offset),
            ).fetchall()
            return {
                "workspace_id": workspace_id,
                "runs": [
                    {
                        "run_id": row["id"],
                        "workspace_id": workspace_id,
                        "name": row["name"][:256],
                        "created_at": _stamp(row["created_at"]),
                    }
                    for row in rows
                ],
                "total": total,
                "offset": offset,
                "limit": limit,
                "next_offset": offset + len(rows) if offset + len(rows) < total else None,
            }

    @staticmethod
    def _mapping(
        text: str, pdf_page_starts: list[tuple[int, int]] | None = None
    ) -> dict[str, Any]:
        lines: list[dict[str, Any]] = []
        headings: list[dict[str, Any]] = []
        open_sections: list[dict[str, Any]] = []
        page_starts = pdf_page_starts or []
        previous_start = -1
        for char_start, page_number in page_starts:
            if (
                type(char_start) is not int
                or type(page_number) is not int
                or not previous_start < char_start < len(text)
                or not 1 <= page_number <= 2**31 - 1
                or (char_start > 0 and text[char_start - 1] != "\n")
            ):
                raise DWSError(
                    "invalid_page_mapping",
                    "PDF extractor supplied invalid page boundaries.",
                    422,
                )
            previous_start = char_start
        position = 0
        page: int | None = None
        page_cursor = 0
        for number, line in enumerate(text.splitlines(keepends=True), 1):
            if page_cursor < len(page_starts) and page_starts[page_cursor][0] == position:
                page = page_starts[page_cursor][1]
                page_cursor += 1
            lines.append(
                {
                    "line": number,
                    "char_start": position,
                    "char_end": position + len(line),
                    "page": page,
                }
            )
            position += len(line)
        # Parse blocks only: titles retain their normalized Markdown spelling.
        # The parsing view uses the same line boundaries as the exact map above;
        # it does not replace retained text or its character offsets.
        tokens = MarkdownIt("commonmark").disable("inline").parse("\n".join(text.splitlines()))
        for index, token in enumerate(tokens):
            if token.type != "heading_open" or token.map is None:
                continue
            number = token.map[0] + 1
            level = int(token.tag[1:])
            title = tokens[index + 1].content
            while open_sections and open_sections[-1]["level"] >= level:
                open_sections.pop()["line_end"] = number - 1
            # Empty headings are boundaries, but have no selectable name.
            if title:
                section = {"title": title, "level": level, "line_start": number}
                headings.append(section)
                open_sections.append(section)
        for section in open_sections:
            section["line_end"] = len(lines)
        return {
            "version": 1,
            "offset_unit": "unicode_codepoints",
            "lines": lines,
            "sections": headings,
        }

    def _storage_usage(self) -> int:
        total = 0
        for path in self.root.rglob("*"):
            try:
                if path.is_file() and not path.is_symlink():
                    total += path.stat().st_size
            except FileNotFoundError:
                # Another owned connection may finish a WAL checkpoint between
                # enumeration and stat. Its removed file consumes no space.
                continue
        return total

    def _check_space(self, required: int) -> None:
        if self._storage_usage() + required > self.settings.max_storage_bytes:
            raise DWSError(
                "storage_limit",
                "DWS storage limit reached; export or explicitly expire unpinned evidence.",
                507,
            )
        if shutil.disk_usage(self.root).free - required < self.settings.min_free_bytes:
            raise DWSError(
                "disk_pressure",
                "Insufficient safe disk space; no pinned evidence was deleted.",
                507,
            )

    def admit_metadata(self, required_bytes: int = 0, *, artifact_bytes: int = 0) -> None:
        """Admit growth inside the caller's owned write transaction.

        This acquires no additional lock: callers retain their existing order.
        Four times the encoded payload plus 256 KiB reserves SQLite page/index,
        small bounded WAL, and terminal-update headroom. Reads and acknowledged
        job finalization do not require another admission.
        """
        self._check_space(
            METADATA_HEADROOM + max(0, required_bytes) * 4 + max(0, artifact_bytes)
        )

    @staticmethod
    def _write(path: Path, data: bytes) -> None:
        with path.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        path.chmod(0o444)

    @staticmethod
    def _sync_dir(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _sync_tree(self, path: Path) -> None:
        """Persist copied files and every directory entry before acknowledgement."""
        directories = [path]
        for child in path.rglob("*"):
            if child.is_symlink():
                raise OSError("Captured evidence tree contains a symlink")
            if child.is_dir():
                directories.append(child)
            elif child.is_file():
                with child.open("rb") as handle:
                    os.fsync(handle.fileno())
        for directory in sorted(directories, key=lambda item: len(item.parts), reverse=True):
            self._sync_dir(directory)
        self._sync_dir(path.parent)

    def _copy_tree(self, source: Path, destination: Path) -> None:
        try:
            shutil.copytree(source, destination)
            self._sync_tree(destination)
        except OSError:
            shutil.rmtree(destination, ignore_errors=True)
            raise DWSError(
                "artifact_unavailable", "Captured evidence could not be copied durably.", 503
            ) from None

    def _context(
        self,
        conn: sqlite3.Connection,
        snapshot_id: str,
        workspace_id: str,
        run_id: str | None,
        crawl_id: str | None,
        kind: str,
    ) -> None:
        conn.execute(
            "INSERT OR IGNORE INTO snapshot_contexts VALUES (?, ?, ?, ?)",
            (snapshot_id, workspace_id, run_id or "", crawl_id or ""),
        )
        conn.execute(
            "INSERT INTO capture_events VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), snapshot_id, workspace_id, run_id, crawl_id, time.time(), kind),
        )

    def save_capture(
        self,
        capture: Capture,
        workspace_id: str,
        run_id: str | None,
        crawl_id: str | None = None,
        fence: Callable[[sqlite3.Connection], None] | None = None,
        on_commit: Callable[[sqlite3.Connection, dict[str, Any]], None] | None = None,
    ) -> dict[str, Any]:
        if not capture.text.strip():
            raise DWSError(
                "empty_capture", "Acquisition produced no usable normalized text.", 422
            )
        if (
            len(capture.raw) > self.settings.max_bytes
            or len(capture.text) > self.settings.max_text_chars
        ):
            raise DWSError(
                "capture_limit", "Acquired content exceeds configured capture limits.", 413
            )
        snapshot_id, now = str(uuid.uuid4()), time.time()
        try:
            expires_at = now + self.settings.retention_seconds
            _stamp(expires_at)
        except (OverflowError, ValueError, OSError):
            raise DWSError(
                "invalid_retention", "Retention exceeds the supported UTC timestamp range.", 503
            ) from None
        text_bytes = capture.text.encode("utf-8")
        mapping = self._mapping(
            capture.text,
            capture.pdf_page_starts if capture.content_type == "application/pdf" else [],
        )
        mapping_bytes = _json(mapping).encode("utf-8")
        raw_hash, text_hash, mapping_hash = (
            _digest(capture.raw),
            _digest(text_bytes),
            _digest(mapping_bytes),
        )
        relative_dir = "artifacts/" + snapshot_id
        destination = self._owned(self.root / relative_dir)
        staging = self._owned(self.root / "staging" / snapshot_id)
        provenance = {
            "snapshot_id": snapshot_id,
            "requested_url": capture.requested_url,
            "final_url": capture.final_url,
            "redirects": capture.redirects,
            "captured_at": _stamp(now),
            "raw_hash": raw_hash,
            "text_hash": text_hash,
            "mapping_hash": mapping_hash,
            "normalizer": capture.normalizer,
            "provider": capture.provider,
            "content_type": capture.content_type,
            "warnings": capture.warnings,
            "links": capture.links,
            "title": capture.title,
        }
        provenance_bytes = _json(provenance).encode("utf-8")
        size = len(capture.raw) + len(text_bytes) + len(mapping_bytes) + len(provenance_bytes)
        with self.maintenance(), self._lock("artifact-publication"), self.connection() as conn:
            self._validate_scope(conn, workspace_id, run_id)
            conn.execute("BEGIN IMMEDIATE")
            self.admit_metadata(len(provenance_bytes), artifact_bytes=size)
            if fence is not None:
                fence(conn)
            existing = conn.execute(
                "SELECT id FROM documents WHERE workspace_id=? AND canonical_url=?",
                (workspace_id, capture.final_url),
            ).fetchone()
            document_id = existing["id"] if existing else str(uuid.uuid4())
            try:
                staging.mkdir()
                for filename, data in (
                    ("source.bin", capture.raw),
                    ("normalized.txt", text_bytes),
                    ("mapping.json", mapping_bytes),
                    ("provenance.json", provenance_bytes),
                ):
                    self._write(staging / filename, data)
                self._sync_dir(staging)
                os.replace(staging, destination)
                self._sync_dir(destination.parent)
                if not existing:
                    conn.execute(
                        "INSERT INTO documents VALUES (?, ?, ?, ?)",
                        (document_id, workspace_id, capture.final_url, now),
                    )
                conn.execute(
                    """INSERT INTO snapshots (
                    id,document_id,workspace_id,run_id,crawl_id,requested_url,final_url,captured_at,
                    raw_hash,text_hash,mapping_hash,content_type,title,normalizer,provider,
                    redirects_json,warnings_json,links_json,artifact_dir,text_chars,line_count,total_bytes,expires_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        snapshot_id,
                        document_id,
                        workspace_id,
                        run_id,
                        crawl_id,
                        capture.requested_url,
                        capture.final_url,
                        now,
                        raw_hash,
                        text_hash,
                        mapping_hash,
                        capture.content_type,
                        capture.title,
                        capture.normalizer,
                        capture.provider,
                        _json(capture.redirects),
                        _json(capture.warnings),
                        _json(capture.links),
                        relative_dir,
                        len(capture.text),
                        len(mapping["lines"]),
                        size,
                        expires_at,
                    ),
                )
                self._context(conn, snapshot_id, workspace_id, run_id, crawl_id, "acquired")
                conn.execute(
                    "INSERT INTO index_outbox VALUES (?, 'upsert', ?)", (snapshot_id, now)
                )
                if on_commit is not None:
                    internal = self._snapshot(self._row(conn, snapshot_id, workspace_id))
                    # Frontier expansion needs the full capture link set. This
                    # callback is internal, not a public capability response.
                    internal["links"] = capture.links
                    on_commit(conn, internal)
                conn.commit()
            except BaseException as error:
                conn.rollback()
                shutil.rmtree(staging, ignore_errors=True)
                shutil.rmtree(destination, ignore_errors=True)
                if isinstance(error, OSError):
                    if error.errno in {errno.ENOSPC, errno.EDQUOT}:
                        raise DWSError(
                            "disk_pressure",
                            "Captured evidence could not be written because storage is full "
                            "or a filesystem quota was reached.",
                            507,
                        ) from None
                    raise DWSError(
                        "artifact_write_failed",
                        "Captured evidence could not be durably written.",
                        500,
                    ) from None
                raise
            row = self._row(conn, snapshot_id, workspace_id)
            result = self._snapshot(row)
            result.update(
                {
                    "excerpt": capture.text[: min(2000, self.settings.max_output_chars)],
                    "truncated": len(capture.text) > min(2000, self.settings.max_output_chars),
                    "cached": False,
                }
            )
            return result

    def _row(
        self,
        conn: sqlite3.Connection,
        snapshot_id: str,
        workspace_id: str,
        include_expired: bool = False,
    ) -> sqlite3.Row:
        row: sqlite3.Row | None = conn.execute(
            "SELECT * FROM snapshots WHERE id=? AND workspace_id=?", (snapshot_id, workspace_id)
        ).fetchone()
        if row is None:
            raise DWSError(
                "snapshot_not_found", "Snapshot does not exist in this workspace.", 404
            )
        if row["expired"] and not include_expired:
            raise DWSError(
                "snapshot_expired",
                "Snapshot has explicitly expired; it was not replaced with live content.",
                410,
            )
        return row

    @staticmethod
    def _snapshot(row: sqlite3.Row) -> dict[str, Any]:
        links = json.loads(row["links_json"])
        redirects = json.loads(row["redirects_json"])
        warnings = json.loads(row["warnings_json"])
        link_preview = [url for url in links[:8] if len(url) <= 512]
        redirect_preview = [url for url in redirects[:4] if len(url) <= 1024]
        warning_preview = [warning[:256] for warning in warnings[:8]]
        return {
            "snapshot_id": row["id"],
            "document_id": row["document_id"],
            "workspace_id": row["workspace_id"],
            "run_id": row["run_id"],
            "crawl_id": row["crawl_id"],
            "source_url": row["requested_url"],
            "requested_url": row["requested_url"],
            "final_url": row["final_url"],
            "captured_at": _stamp(row["captured_at"]),
            "content_type": row["content_type"],
            "title": row["title"][:512],
            "title_truncated": len(row["title"]) > 512,
            "raw_hash": row["raw_hash"],
            "text_hash": row["text_hash"],
            "mapping_hash": row["mapping_hash"],
            "normalizer": row["normalizer"],
            "provider": row["provider"],
            "redirects": redirect_preview,
            "redirects_count": len(redirects),
            "redirects_truncated": len(redirects) != len(redirect_preview),
            "warnings": warning_preview,
            "warnings_count": len(warnings),
            "warnings_truncated": len(warnings) > 8
            or any(len(warning) > 256 for warning in warnings[:8]),
            "links": link_preview,
            "links_count": len(links),
            "links_truncated": len(links) != len(link_preview),
            "text_chars": row["text_chars"],
            "line_count": row["line_count"],
            "index_state": row["index_state"],
            "index_error": row["index_error"],
            "pinned": bool(row["pinned"]),
            "expired": bool(row["expired"]),
            "expires_at": _stamp(row["expires_at"]),
            "citation": "dws://snapshots/" + row["id"],
        }

    def get_snapshot(self, snapshot_id: str, workspace_id: str) -> dict[str, Any]:
        with self.maintenance(), self.connection() as conn:
            return self._snapshot(self._row(conn, snapshot_id, workspace_id))

    def _load(self, row: sqlite3.Row) -> tuple[str, dict[str, Any]]:
        folder = self._owned(self.root / row["artifact_dir"])
        try:
            text_bytes = self._owned(folder / "normalized.txt").read_bytes()
            mapping_bytes = self._owned(folder / "mapping.json").read_bytes()
        except OSError:
            raise DWSError(
                "artifact_unavailable",
                "Canonical snapshot files are unavailable; restore a verified backup.",
                503,
            ) from None
        if (
            _digest(text_bytes) != row["text_hash"]
            or _digest(mapping_bytes) != row["mapping_hash"]
        ):
            raise DWSError(
                "artifact_integrity", "Retained evidence failed its integrity check.", 500
            )
        return text_bytes.decode("utf-8"), json.loads(mapping_bytes)

    def _load_raw(self, row: sqlite3.Row) -> bytes:
        path = self._owned(self.root / row["artifact_dir"] / "source.bin")
        try:
            raw = path.read_bytes()
        except OSError:
            raise DWSError(
                "artifact_unavailable",
                "Original capture is unavailable; restore a verified backup.",
                503,
            ) from None
        if _digest(raw) != row["raw_hash"]:
            raise DWSError(
                "artifact_integrity", "Original capture failed its integrity check.", 500
            )
        return raw

    def cached_fetch(self, request: FetchRequest) -> dict[str, Any] | None:
        if request.refresh or request.max_age_seconds == 0:
            return None
        with self.maintenance(), self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._validate_scope(conn, request.workspace_id, request.run_id)
            condition = ""
            if request.render == "always":
                condition = " AND provider='crawl4ai'"
            elif request.render == "never":
                condition = " AND provider='httpx'"
            row = conn.execute(
                """SELECT * FROM snapshots WHERE workspace_id=? AND requested_url=?
                AND expired=0 AND captured_at>=?"""
                + condition
                + " ORDER BY captured_at DESC LIMIT 1",
                (request.workspace_id, request.url, time.time() - request.max_age_seconds),
            ).fetchone()
            if row is None:
                return None
            text, _ = self._load(row)
            self.admit_metadata(512)
            self._context(
                conn, row["id"], request.workspace_id, request.run_id, None, "cache_reuse"
            )
            result = self._snapshot(row)
            result.update(
                {
                    "excerpt": text[: min(2000, self.settings.max_output_chars)],
                    "cached": True,
                    "age_seconds": max(0, int(time.time() - row["captured_at"])),
                    "truncated": len(text) > min(2000, self.settings.max_output_chars),
                }
            )
            return result

    def read(self, request: ReadRequest) -> dict[str, Any]:
        with self.maintenance(), self.connection() as conn:
            row = self._row(conn, request.snapshot_id, request.workspace_id)
            text, mapping = self._load(row)
            lines = mapping["lines"]
            start, end = request.line_start, request.line_end or len(lines)
            if request.section:
                found = next(
                    (
                        s
                        for s in mapping["sections"]
                        if s["title"].casefold() == request.section.casefold()
                    ),
                    None,
                )
                if not found:
                    raise DWSError(
                        "section_not_found",
                        "Named section is not present in this snapshot.",
                        404,
                    )
                start, end = found["line_start"], found["line_end"]
            if start > len(lines) or end < start:
                raise DWSError(
                    "invalid_range", "Requested line range is outside this snapshot.", 416
                )
            end = min(end, len(lines))
            char_start, wanted_end = lines[start - 1]["char_start"], lines[end - 1]["char_end"]
            char_end = min(
                wanted_end, char_start + min(request.max_chars, self.settings.max_output_chars)
            )
            actual_end = bisect.bisect_left([line["char_end"] for line in lines], char_end) + 1
            result = self._snapshot(row)
            result.update(
                {
                    "text": text[char_start:char_end],
                    "line_start": start,
                    "line_end": actual_end,
                    "char_start": char_start,
                    "char_end": char_end,
                    "truncated": char_end < wanted_end,
                    "sections": [
                        {**section, "title": section["title"][:256]}
                        for section in mapping["sections"][:25]
                    ],
                    "sections_truncated": len(mapping["sections"]) > 25
                    or any(len(section["title"]) > 256 for section in mapping["sections"][:25]),
                    "location_map": lines[start - 1 : min(actual_end, start + 199)],
                    "location_map_truncated": actual_end - start + 1 > 200,
                }
            )
            return result

    @staticmethod
    def _chunks(text: str, mapping: dict[str, Any]) -> Iterator[tuple[str, int, int, int, int]]:
        offsets = [line["char_start"] for line in mapping["lines"]]
        start = 0
        while start < len(text):
            end = min(start + 2200, len(text))
            if end < len(text):
                newline = text.rfind("\n", start + 1100, end)
                if newline >= 0:
                    end = newline + 1
            if text[start:end].strip():
                yield (
                    text[start:end],
                    bisect.bisect_right(offsets, start),
                    bisect.bisect_right(offsets, end - 1),
                    start,
                    end,
                )
            if end == len(text):
                break
            start = max(start + 1, end - 220)

    def index_pending(self, limit: int = 20) -> int:
        with (
            self.maintenance(),
            self._lock("index-writer"),
            self._lock("artifact-publication"),
        ):
            if not self.index_path.exists():
                return 0
            return self._index_pending_unlocked(max(1, min(limit, 500)))

    def _index_pending_unlocked(self, limit: int) -> int:
        with self.connection() as meta:
            pending = meta.execute(
                "SELECT * FROM index_outbox ORDER BY queued_at LIMIT ?", (limit,)
            ).fetchall()
        count = 0
        index = self._index_connection()
        try:
            for event in pending:
                with self.connection() as meta:
                    meta.execute("BEGIN IMMEDIATE")
                    row = meta.execute(
                        "SELECT * FROM snapshots WHERE id=?", (event["snapshot_id"],)
                    ).fetchone()
                    try:
                        chunks: list[tuple[str, int, int, int, int]] = []
                        if row and not row["expired"] and event["action"] == "upsert":
                            text, mapping = self._load(row)
                            chunks = list(self._chunks(text, mapping))
                            # FTS term indexes, passage duplication, and WAL can
                            # exceed source bytes. Reserve 8x UTF-8 text plus
                            # per-chunk bookkeeping before touching the index.
                            self.admit_metadata(
                                len(text.encode("utf-8")) * 2 + len(chunks) * 256
                            )
                        index.execute(
                            "DELETE FROM passages WHERE snapshot_id=?", (event["snapshot_id"],)
                        )
                        if row and not row["expired"] and event["action"] == "upsert":
                            index.executemany(
                                "INSERT INTO passages VALUES (?,?,?,?,?,?,?)",
                                (
                                    (part, row["id"], row["document_id"], ls, le, cs, ce)
                                    for part, ls, le, cs, ce in chunks
                                ),
                            )
                        index.commit()
                        # Expiry can race indexing. The queued action comparison retains
                        # its newer delete event rather than resurrecting an expired row.
                        meta.execute(
                            "UPDATE snapshots SET index_state=CASE WHEN expired=1 "
                            "THEN 'expired' ELSE 'ready' END,indexed_at=?,index_error=NULL "
                            "WHERE id=?",
                            (time.time(), event["snapshot_id"]),
                        )
                        meta.execute(
                            "DELETE FROM index_outbox WHERE snapshot_id=? "
                            "AND action=? AND queued_at=?",
                            (event["snapshot_id"], event["action"], event["queued_at"]),
                        )
                        count += 1
                    except (DWSError, OSError, sqlite3.Error) as exc:
                        index.rollback()
                        error = exc.code if isinstance(exc, DWSError) else str(exc)[:256]
                        state = (
                            "blocked"
                            if error in ("storage_limit", "disk_pressure")
                            else "error"
                        )
                        if (
                            row
                            and not row["expired"]
                            and (row["index_state"] != state or row["index_error"] != error)
                        ):
                            meta.execute(
                                "UPDATE snapshots SET index_state=?,index_error=? WHERE id=?",
                                (state, error, event["snapshot_id"]),
                            )
                        # Keep failures retryable while yielding this queue position
                        # to healthy captures. A newer expiry/delete event retains
                        # its action and timestamp rather than being overwritten.
                        meta.execute(
                            "UPDATE index_outbox SET queued_at=? WHERE snapshot_id=? "
                            "AND action=? AND queued_at=?",
                            (
                                time.time(),
                                event["snapshot_id"],
                                event["action"],
                                event["queued_at"],
                            ),
                        )
        finally:
            index.close()
        return count

    @contextlib.contextmanager
    def _reader_slot(self) -> Iterator[None]:
        until = time.monotonic() + 2
        while True:
            for slot in range(4):
                lock = self._lock("index-reader-" + str(slot), timeout=0)
                try:
                    lock.__enter__()
                except DWSError:
                    continue
                try:
                    yield
                finally:
                    lock.__exit__(None, None, None)
                return
            if time.monotonic() >= until:
                raise DWSError(
                    "retrieval_busy",
                    "All bounded retrieval slots are busy; retry shortly.",
                    503,
                )
            time.sleep(0.025)

    def retrieve(self, request: RetrieveRequest) -> dict[str, Any]:
        tokens = re.findall(r"[^\W_]+", request.query, re.UNICODE)
        if not tokens:
            raise DWSError("invalid_query", "Query must include a searchable word.")
        match = " OR ".join('"' + token + '"' for token in tokens)
        with self.maintenance(), self._reader_slot(), self.connection() as meta:
            self._validate_scope(meta, request.workspace_id, request.run_id)
            scope = "s.workspace_id=? AND s.expired=0"
            args: list[Any] = [request.workspace_id]
            if request.run_id or request.crawl_id:
                scope += (
                    " AND EXISTS (SELECT 1 FROM meta.snapshot_contexts c "
                    "WHERE c.snapshot_id=s.id"
                )
                if request.run_id:
                    scope += " AND c.run_id=?"
                    args.append(request.run_id)
                if request.crawl_id:
                    scope += " AND c.crawl_id=?"
                    args.append(request.crawl_id)
                scope += ")"
            if request.document_ids:
                scope += (
                    " AND s.document_id IN ("
                    + ",".join("?" for _ in request.document_ids)
                    + ")"
                )
                args.extend(request.document_ids)
            result: dict[str, Any] = {
                "query": request.query,
                "workspace_id": request.workspace_id,
                "run_id": request.run_id,
                "crawl_id": request.crawl_id,
                "document_ids": request.document_ids,
                "results": [],
                "warnings": [],
                "truncated": False,
            }
            if not self.index_path.exists():
                result.update(
                    {
                        "index_state": "unavailable",
                        "warnings": ["index_unavailable"],
                        "partial": True,
                    }
                )
                return result
            index: sqlite3.Connection | None = None
            try:
                index = sqlite3.connect(
                    self.index_path.as_uri() + "?mode=ro", uri=True, timeout=5
                )
                index.row_factory = sqlite3.Row
                index.execute(
                    "ATTACH DATABASE ? AS meta",
                    (self.metadata_path.as_uri() + "?mode=ro",),
                )
                pending = index.execute(
                    "SELECT count(*) FROM meta.snapshots s WHERE "
                    + scope
                    + " AND s.index_state!='ready'",
                    args,
                ).fetchone()[0]
                hits = index.execute(
                    """SELECT passages.*,bm25(passages) AS rank FROM passages
                    JOIN meta.snapshots s ON s.id=passages.snapshot_id
                    WHERE passages MATCH ? AND """
                    + scope
                    + " ORDER BY rank LIMIT ?",
                    [match, *args, request.limit],
                ).fetchall()
                remaining = min(request.max_chars, self.settings.max_output_chars)
                for hit in hits:
                    if remaining <= 0:
                        result["truncated"] = True
                        break
                    row = self._row(meta, hit["snapshot_id"], request.workspace_id)
                    text, mapping = self._load(row)
                    cs, wanted = int(hit["char_start"]), int(hit["char_end"])
                    ce = min(wanted, cs + remaining)
                    exact = text[cs:ce]
                    if exact != hit["text"][: len(exact)]:
                        raise DWSError(
                            "index_integrity",
                            "Search index does not match retained evidence; rebuild it.",
                            500,
                        )
                    line_start = int(hit["line_start"])
                    line_end = (
                        bisect.bisect_left([line["char_end"] for line in mapping["lines"]], ce)
                        + 1
                    )
                    result["results"].append(
                        {
                            **self._snapshot(row),
                            "text": exact,
                            "line_start": line_start,
                            "line_end": line_end,
                            "char_start": cs,
                            "char_end": ce,
                            "score": float(hit["rank"]),
                            "truncated": ce < wanted,
                        }
                    )
                    remaining -= len(exact)
                    result["truncated"] |= ce < wanted
                result.update(
                    {
                        "index_state": "pending" if pending else "ready",
                        "pending_snapshots": pending,
                        "partial": bool(pending),
                    }
                )
                if pending:
                    result["warnings"].append("scope_indexing_incomplete")
                return result
            except sqlite3.Error:
                result.update(
                    {
                        "index_state": "unavailable",
                        "warnings": ["index_unavailable"],
                        "partial": True,
                    }
                )
                return result
            finally:
                if index is not None:
                    index.close()

    def rebuild_index(self) -> dict[str, Any]:
        with self.maintenance(exclusive=True), self._lock("index-writer"):
            return self._rebuild_unlocked()

    def _rebuild_unlocked(self) -> dict[str, Any]:
        with self.connection() as meta:
            self._prepare_index_rebuild(meta)
        # Remove only the disposable index. Canonical files/metadata are untouched.
        for suffix in ("", "-wal", "-shm"):
            self._owned(Path(str(self.index_path) + suffix)).unlink(missing_ok=True)
        index = self._index_connection()
        try:
            index.execute("""CREATE VIRTUAL TABLE passages USING fts5(
                text,snapshot_id UNINDEXED,
                document_id UNINDEXED,line_start UNINDEXED,line_end UNINDEXED,
                char_start UNINDEXED,char_end UNINDEXED,tokenize='unicode61')""")
            index.commit()
        finally:
            index.close()
        count = 0
        while True:
            processed = self._index_pending_unlocked(100)
            count += processed
            if not processed:
                break
        with self.connection() as meta:
            pending = meta.execute("SELECT count(*) FROM index_outbox").fetchone()[0]
        return {
            "indexed_snapshots": count,
            "pending_snapshots": pending,
            "index_state": "pending" if pending else "ready",
        }

    def pin(self, snapshot_id: str, workspace_id: str, pinned: bool = True) -> dict[str, Any]:
        with self.maintenance(), self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._row(conn, snapshot_id, workspace_id)
            conn.execute("UPDATE snapshots SET pinned=? WHERE id=?", (int(pinned), snapshot_id))
            return self._snapshot(self._row(conn, snapshot_id, workspace_id))

    def export(self, snapshot_id: str, workspace_id: str) -> dict[str, Any]:
        with self.maintenance(), self._lock("artifact-publication"), self.connection() as conn:
            row = self._row(conn, snapshot_id, workspace_id)
            self._load(row)
            folder = self._owned(self.root / row["artifact_dir"])
            self._load_raw(row)
            self._check_space(row["total_bytes"] + METADATA_HEADROOM)
            export_id = str(uuid.uuid4())
            destination = self._owned(self.root / "exports" / export_id)
            self._copy_tree(folder, destination)
            return {
                "export_id": export_id,
                "snapshot_id": snapshot_id,
                "path": str(destination),
                "files": [p.name for p in destination.iterdir()],
            }

    def expire(self, snapshot_id: str, workspace_id: str) -> dict[str, Any]:
        with self.maintenance(), self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = self._row(conn, snapshot_id, workspace_id, include_expired=True)
            if row["pinned"]:
                raise DWSError(
                    "snapshot_pinned", "Unpin the snapshot before explicitly expiring it.", 409
                )
            now = time.time()
            conn.execute(
                "UPDATE snapshots SET expired=1,expired_at=?,index_state='expired' WHERE id=?",
                (now, snapshot_id),
            )
            conn.execute(
                "INSERT OR REPLACE INTO index_outbox VALUES (?,'delete',?)", (snapshot_id, now)
            )
            return {"snapshot_id": snapshot_id, "expired": True, "artifacts_removed": False}

    def _orphan_directories(self, conn: sqlite3.Connection) -> list[tuple[Path, int]]:
        referenced = {
            self._owned(self.root / row["artifact_dir"])
            for row in conn.execute("SELECT artifact_dir FROM snapshots")
        }
        snapshot_ids = {row[0] for row in conn.execute("SELECT id FROM snapshots")}
        capture_files = {"source.bin", "normalized.txt", "mapping.json", "provenance.json"}
        database_files = {
            "management.sqlite3",
            "management.sqlite3-wal",
            "management.sqlite3-shm",
            "management.sqlite3-journal",
        }

        def canonical(value: str) -> bool:
            try:
                return str(uuid.UUID(value)) == value
            except ValueError:
                return False

        result = []
        for area in ("staging", "artifacts"):
            for path in (self.root / area).iterdir():
                if path.is_symlink() or not path.is_dir() or path.resolve() in referenced:
                    continue
                name = path.name
                if canonical(name):
                    if name in snapshot_ids:
                        continue
                    allowed = capture_files
                elif area == "staging" and name.startswith("restore-") and canonical(name[8:]):
                    allowed = database_files
                elif area == "staging" and name.startswith("repair-") and canonical(name[7:]):
                    allowed = {child.name for child in path.iterdir() if canonical(child.name)}
                else:
                    continue
                files = list(path.iterdir())
                if any(
                    child.is_symlink() or not child.is_file() or child.name not in allowed
                    for child in files
                ):
                    continue
                result.append((path, sum(child.stat().st_size for child in files)))
        return result

    def gc(self, dry_run: bool = True) -> dict[str, Any]:
        with (
            self.maintenance(exclusive=True),
            self._lock("artifact-publication"),
            self.connection() as conn,
        ):
            orphans = self._orphan_directories(conn)
            cleanup_errors: list[dict[str, str]] = []
            removed = orphan_removed = 0
            cache_events = conn.execute(
                "SELECT count(*) FROM capture_events WHERE kind='cache_reuse' "
                "AND snapshot_id IN (SELECT id FROM snapshots WHERE pinned=0)"
            ).fetchone()[0]
            has_jobs = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dws_jobs'"
            ).fetchone()
            active = ""
            if has_jobs:
                active = """ AND NOT EXISTS (SELECT 1 FROM snapshot_contexts c JOIN dws_jobs j
                    ON j.job_id=c.crawl_id WHERE c.snapshot_id=s.id
                    AND j.state IN ('queued','running'))"""
            rows = conn.execute(
                "SELECT * FROM snapshots s WHERE pinned=0 AND (expired=1 OR expires_at<?)"
                + active,
                (time.time(),),
            ).fetchall()
            candidates = [
                row
                for row in rows
                if self._owned(self.root / row["artifact_dir"]).exists() or not row["expired"]
            ]
            reclaimed = sum(
                row["total_bytes"]
                for row in candidates
                if self._owned(self.root / row["artifact_dir"]).exists()
            )
            if not dry_run:
                now = time.time()
                for row in candidates:
                    conn.execute(
                        "UPDATE snapshots SET expired=1,expired_at=COALESCE(expired_at,?),"
                        "index_state='expired' WHERE id=?",
                        (now, row["id"]),
                    )
                    conn.execute(
                        "INSERT OR REPLACE INTO index_outbox VALUES (?,'delete',?)",
                        (row["id"], now),
                    )
                # Commit tombstones before removing files so an interrupted cleanup
                # never serves a missing capture as available evidence.
                conn.commit()
                for row in candidates:
                    raw_path = self.root / row["artifact_dir"]
                    if raw_path.is_symlink() or (
                        raw_path.is_dir()
                        and any(
                            child.is_symlink()
                            or not child.is_file()
                            or child.name
                            not in {
                                "source.bin",
                                "normalized.txt",
                                "mapping.json",
                                "provenance.json",
                            }
                            for child in raw_path.iterdir()
                        )
                    ):
                        cleanup_errors.append(
                            {
                                "path": str(raw_path.relative_to(self.root)),
                                "code": "unsafe_cleanup_target",
                                "message": "Cleanup refused a symlink or unrecognized file.",
                            }
                        )
                        continue
                    path = self._owned(raw_path)
                    if path.exists():
                        try:
                            shutil.rmtree(path)
                            removed += 1
                        except OSError as exc:
                            cleanup_errors.append(
                                {
                                    "path": str(path.relative_to(self.root)),
                                    "code": "cleanup_failed",
                                    "message": str(exc)[:256],
                                }
                            )
                for path, _ in orphans:
                    try:
                        shutil.rmtree(path)
                        orphan_removed += 1
                    except OSError as exc:
                        cleanup_errors.append(
                            {
                                "path": str(path.relative_to(self.root)),
                                "code": "cleanup_failed",
                                "message": str(exc)[:256],
                            }
                        )
                # Explicit cleanup may discard repetitive unpinned cache-usage
                # history. Capture provenance, scope membership, snapshot/job
                # identities, and pinned history remain durable.
                conn.execute(
                    "DELETE FROM capture_events WHERE kind='cache_reuse' "
                    "AND snapshot_id IN (SELECT id FROM snapshots WHERE pinned=0)"
                )
                conn.commit()
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            return {
                "dry_run": dry_run,
                "candidate_count": len(candidates),
                "bytes": reclaimed,
                "snapshot_ids": [row["id"] for row in candidates[:100]],
                "truncated": len(candidates) > 100,
                "cache_events_to_prune": cache_events,
                "cache_events_pruned": 0 if dry_run else cache_events,
                "orphan_candidate_count": len(orphans),
                "orphan_bytes": sum(size for _, size in orphans),
                "orphan_paths": [str(path.relative_to(self.root)) for path, _ in orphans[:100]],
                "orphan_paths_truncated": len(orphans) > 100,
                "orphan_removed_count": orphan_removed,
                "snapshot_removed_count": removed,
                "cleanup_errors": cleanup_errors[:20],
                "cleanup_errors_truncated": len(cleanup_errors) > 20,
                "status": "partial" if cleanup_errors else "ok",
            }

    def backup(self) -> dict[str, Any]:
        with (
            self.maintenance(exclusive=True),
            self._lock("artifact-publication"),
            self.connection() as conn,
        ):
            ident = str(uuid.uuid4())
            destination = self._owned(self.root / "backups" / ident)
            rows = conn.execute("SELECT * FROM snapshots WHERE expired=0").fetchall()
            db_bytes = (
                conn.execute("PRAGMA page_count").fetchone()[0]
                * conn.execute("PRAGMA page_size").fetchone()[0]
            )
            self._check_space(
                sum(row["total_bytes"] for row in rows)
                + db_bytes
                + METADATA_HEADROOM
                + len(rows) * 512
            )
            try:
                destination.mkdir()
                backup_db = sqlite3.connect(destination / "management.sqlite3")
                try:
                    conn.backup(backup_db)
                finally:
                    backup_db.close()
                for row in rows:
                    self._load(row)
                    source = self._owned(self.root / row["artifact_dir"])
                    self._load_raw(row)
                    self._copy_tree(source, destination / row["artifact_dir"])
                files = {
                    str(path.relative_to(destination)): _digest(path.read_bytes())
                    for path in destination.rglob("*")
                    if path.is_file()
                }
                self._write(
                    destination / "manifest.json",
                    _json(
                        {
                            "version": 1,
                            "backup_id": ident,
                            "created_at": _stamp(),
                            "files": files,
                            "snapshots": len(rows),
                            "pinned_snapshots": [row["id"] for row in rows if row["pinned"]],
                        }
                    ).encode("utf-8"),
                )
                self._sync_tree(destination)
            except OSError:
                shutil.rmtree(destination, ignore_errors=True)
                raise DWSError(
                    "artifact_unavailable", "Backup evidence could not be copied durably.", 503
                ) from None
            except BaseException:
                shutil.rmtree(destination, ignore_errors=True)
                raise
            return {
                "backup_id": ident,
                "snapshots": len(rows),
                "pinned_snapshots": sum(bool(row["pinned"]) for row in rows),
                "path": str(destination),
            }

    @staticmethod
    def _restore_preserves_state(current: sqlite3.Connection, backup_path: Path) -> None:
        """Refuse rollback of any already retained or acknowledged product state.

        Current rows must be present unchanged in the backup. Comparison runs
        before artifact repairs/publication and metadata replacement. The index
        outbox and snapshot index diagnostics are disposable; only job leases
        are transient. Pins, expiry, contexts, capture events, and every frontier
        progress/cancellation/error field are retained state.
        """
        ignored = {
            "snapshots": {"index_state", "indexed_at", "index_error"},
            "dws_jobs": {"lease_owner", "lease_until", "lease_epoch"},
        }

        def quoted(name: str) -> str:
            return '"' + name.replace('"', '""') + '"'

        current.execute(
            "ATTACH DATABASE ? AS restore_candidate",
            (backup_path.as_uri() + "?mode=ro",),
        )
        try:
            tables = [
                row[0]
                for row in current.execute(
                    "SELECT name FROM main.sqlite_master WHERE type='table' "
                    "AND name NOT GLOB 'sqlite_*'"
                ).fetchall()
            ]
            empty = all(
                not current.execute(
                    "SELECT 1 FROM main." + quoted(table) + " LIMIT 1"
                ).fetchone()
                for table in tables
                if table not in ("workspaces", "index_outbox")
            )
            workspace_rows = current.execute("SELECT id,name FROM main.workspaces").fetchall()
            empty = empty and all(
                row["id"] == "default" and row["name"] == "Default" for row in workspace_rows
            )
            for table in tables:
                table_name = quoted(table)
                required_columns = [
                    row["name"]
                    for row in current.execute(
                        "PRAGMA main.table_info(" + table_name + ")"
                    ).fetchall()
                ]
                backup_columns = {
                    row["name"]
                    for row in current.execute(
                        "PRAGMA restore_candidate.table_info(" + table_name + ")"
                    ).fetchall()
                }
                missing_columns = set(required_columns) - backup_columns
                legacy_discovery = (
                    table == "dws_jobs" and "discovery_limited_count" in missing_columns
                )
                compatible_missing = {"discovery_limited_count"} if legacy_discovery else set()
                if missing_columns - compatible_missing:
                    raise DWSError(
                        "restore_would_discard_state",
                        "Backup lacks the current DWS management schema. "
                        "Restore with compatible product versions.",
                        409,
                    )
                if empty or table == "index_outbox":
                    # Bootstrap default-workspace timestamps and disposable
                    # outbox contents may differ; runtime schema must match.
                    continue
                columns = [
                    name for name in required_columns if name not in ignored.get(table, set())
                ]
                has_rows = current.execute(
                    "SELECT 1 FROM main." + table_name + " LIMIT 1"
                ).fetchone()
                if not has_rows:
                    continue
                equal = " AND ".join(
                    "c." + quoted(column) + " IS 0"
                    if legacy_discovery and column == "discovery_limited_count"
                    else "c." + quoted(column) + " IS b." + quoted(column)
                    for column in columns
                )
                # Primary-key columns occur in this predicate, allowing indexed
                # lookup. The sole historical default comparison retains every
                # nonzero discovery-limit observation by refusing its rollback.
                conflict = bool(
                    current.execute(
                        "SELECT 1 FROM main." + table_name + " c WHERE NOT EXISTS ("
                        "SELECT 1 FROM restore_candidate."
                        + table_name
                        + " b WHERE "
                        + equal
                        + ") LIMIT 1"
                    ).fetchone()
                )
                if conflict:
                    raise DWSError(
                        "restore_would_discard_state",
                        "Restore would discard or change current "
                        + table[:64]
                        + " state. Use a current backup or an empty state directory.",
                        409,
                    )
        finally:
            current.execute("DETACH DATABASE restore_candidate")

    def restore(self, backup_id: str) -> dict[str, Any]:
        from dws.jobs import Jobs

        try:
            if str(uuid.UUID(backup_id)) != backup_id:
                raise ValueError
        except (ValueError, AttributeError):
            raise DWSError(
                "invalid_backup", "Backup identifier is not a DWS-owned backup ID."
            ) from None
        with (
            self.maintenance(exclusive=True),
            self._lock("artifact-publication"),
            self._lock("index-writer"),
        ):
            folder = self._owned(self.root / "backups" / backup_id)
            try:
                manifest = json.loads((folder / "manifest.json").read_text("utf-8"))
                if (
                    not isinstance(manifest, dict)
                    or type(manifest.get("version")) is not int
                    or manifest.get("version") != 1
                    or manifest.get("backup_id") != backup_id
                    or not isinstance(manifest.get("files"), dict)
                    or "management.sqlite3" not in manifest["files"]
                ):
                    raise ValueError
                for relative, digest in manifest["files"].items():
                    if (
                        not isinstance(relative, str)
                        or not relative
                        or Path(relative).is_absolute()
                        or ".." in Path(relative).parts
                        or not isinstance(digest, str)
                        or len(digest) != 64
                        or any(character not in "0123456789abcdef" for character in digest)
                    ):
                        raise ValueError
                    path = self._owned(folder / relative)
                    if (
                        not path.is_relative_to(folder)
                        or path.is_symlink()
                        or _digest(path.read_bytes()) != digest
                    ):
                        raise ValueError
            except (OSError, ValueError, KeyError, TypeError):
                raise DWSError(
                    "invalid_backup",
                    "Backup is missing, malformed, or failed integrity validation.",
                    422,
                ) from None
            try:
                source = sqlite3.connect(
                    (folder / "management.sqlite3").as_uri() + "?mode=ro", uri=True
                )
            except sqlite3.Error:
                raise DWSError(
                    "backup_unavailable", "Backup database is unavailable.", 503
                ) from None
            source.row_factory = sqlite3.Row
            candidate: sqlite3.Connection | None = None
            restore_stage = self._owned(
                self.root / "staging" / ("restore-" + str(uuid.uuid4()))
            )
            candidate_path = restore_stage / "management.sqlite3"
            published: list[Path] = []
            repair_stage = self._owned(self.root / "staging" / ("repair-" + str(uuid.uuid4())))
            repaired = 0
            try:
                if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise DWSError(
                        "invalid_backup",
                        "Backup management database failed integrity validation.",
                        422,
                    )
                # The verified original remains immutable. Prepare the complete
                # compatible schema privately before comparing or publishing it.
                self._check_space(
                    (folder / "management.sqlite3").stat().st_size * 4 + METADATA_HEADROOM
                )
                restore_stage.mkdir()
                candidate = sqlite3.connect(candidate_path)
                candidate.row_factory = sqlite3.Row
                source.backup(candidate)
                candidate.execute("BEGIN IMMEDIATE")
                Jobs.migrate_discovery(candidate)
                candidate.commit()
                rows = candidate.execute("SELECT * FROM snapshots WHERE expired=0").fetchall()
                with self.connection() as current:
                    self._restore_preserves_state(current, candidate_path)
                    current_rows = {
                        row["id"]: row
                        for row in current.execute("SELECT * FROM snapshots").fetchall()
                    }
                    has_jobs = current.execute(
                        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dws_jobs'"
                    ).fetchone()
                    current_epochs = (
                        dict(current.execute("SELECT job_id,lease_epoch FROM dws_jobs"))
                        if has_jobs
                        else {}
                    )
                self._check_space(
                    sum(
                        row["total_bytes"]
                        for row in rows
                        if not self._owned(self.root / row["artifact_dir"]).exists()
                    )
                    + (folder / "management.sqlite3").stat().st_size * 4
                    + METADATA_HEADROOM
                )
                for row in rows:
                    current_row = current_rows.get(row["id"])
                    identity = (
                        "document_id",
                        "workspace_id",
                        "requested_url",
                        "final_url",
                        "captured_at",
                        "raw_hash",
                        "text_hash",
                        "mapping_hash",
                        "content_type",
                        "title",
                        "normalizer",
                        "provider",
                        "redirects_json",
                        "warnings_json",
                        "links_json",
                        "artifact_dir",
                    )
                    if current_row is not None and any(
                        current_row[key] != row[key] for key in identity
                    ):
                        raise DWSError(
                            "artifact_conflict",
                            "Backup conflicts with an existing immutable snapshot identity.",
                            409,
                        )
                    target = self._owned(self.root / row["artifact_dir"])
                    origin = self._owned(folder / row["artifact_dir"])
                    if not origin.is_relative_to(folder) or not origin.is_dir():
                        raise DWSError(
                            "invalid_backup", "Backup lacks required canonical artifacts.", 422
                        )
                    for name, expected in (
                        ("source.bin", row["raw_hash"]),
                        ("normalized.txt", row["text_hash"]),
                        ("mapping.json", row["mapping_hash"]),
                    ):
                        relative = str((origin / name).relative_to(folder))
                        if manifest["files"].get(relative) != expected:
                            raise DWSError(
                                "invalid_backup",
                                "Backup artifact manifest disagrees with management state.",
                                422,
                            )
                    if target.exists():
                        for item in origin.iterdir():
                            destination_file = target / item.name
                            valid = (
                                not destination_file.is_symlink()
                                and destination_file.is_file()
                                and _digest(destination_file.read_bytes())
                                == manifest["files"].get(str(item.relative_to(folder)))
                            )
                            if valid:
                                continue
                            if current_row is None:
                                raise DWSError(
                                    "artifact_conflict",
                                    "Untracked artifact directory conflicts with backup.",
                                    409,
                                )
                            # Only repair damaged files under an unchanged,
                            # management-owned identity. The verified bytes are
                            # fsynced before atomic replacement; valid siblings
                            # are never overwritten. An interruption therefore
                            # preserves each file as old or repaired, and never
                            # publishes partial file contents.
                            repair_stage.mkdir(exist_ok=True)
                            replacement = repair_stage / str(uuid.uuid4())
                            replacement_bytes = item.read_bytes()
                            self._check_space(len(replacement_bytes))
                            self._write(replacement, replacement_bytes)
                            os.replace(replacement, destination_file)
                            self._sync_dir(target)
                            repaired += 1
                    else:
                        self._copy_tree(origin, target)
                        published.append(target)
                # Lease fencing and indexing intent are part of the same atomic
                # compatible metadata publication, including after interruption.
                candidate.execute("BEGIN IMMEDIATE")
                exists = candidate.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='dws_jobs'"
                ).fetchone()
                if exists:
                    candidate.execute(
                        "UPDATE dws_jobs SET lease_owner=NULL,lease_until=NULL,"
                        "lease_epoch=lease_epoch+1"
                    )
                    for job_id, epoch in current_epochs.items():
                        candidate.execute(
                            "UPDATE dws_jobs SET lease_epoch=MAX(lease_epoch,?+1) "
                            "WHERE job_id=?",
                            (epoch, job_id),
                        )
                candidate.execute(
                    "UPDATE snapshots SET index_state='pending',indexed_at=NULL,"
                    "index_error=NULL WHERE expired=0"
                )
                candidate.execute(
                    "INSERT OR REPLACE INTO index_outbox "
                    "SELECT id,'upsert',? FROM snapshots WHERE expired=0",
                    (time.time(),),
                )
                candidate.commit()
                with self.connection() as destination:
                    candidate.backup(destination)
                    # Published metadata references must survive any subsequent
                    # index rebuild failure.
                    published.clear()
                try:
                    index = self._rebuild_unlocked()
                except DWSError as exc:
                    if exc.code not in ("storage_limit", "disk_pressure"):
                        raise
                    # Canonical restoration succeeded. Report the separately
                    # blocked disposable index honestly and retain its outbox.
                    index = {
                        "indexed_snapshots": 0,
                        "pending_snapshots": len(rows),
                        "index_state": "blocked",
                        "warnings": ["index_rebuild_" + exc.code],
                    }
                return {
                    "backup_id": backup_id,
                    "restored_snapshots": len(rows),
                    "repaired_artifacts": repaired,
                    **index,
                }
            except sqlite3.Error:
                raise DWSError(
                    "invalid_backup", "Backup schema could not be restored safely.", 422
                ) from None
            finally:
                if candidate is not None:
                    candidate.close()
                source.close()
                shutil.rmtree(restore_stage, ignore_errors=True)
                shutil.rmtree(repair_stage, ignore_errors=True)
                for path in published:
                    shutil.rmtree(path, ignore_errors=True)

    def diagnostics(self) -> dict[str, Any]:
        with self.maintenance(), self.connection() as conn:
            counts = {
                table: conn.execute("SELECT count(*) FROM " + table).fetchone()[0]
                for table in ("workspaces", "runs", "documents", "snapshots", "index_outbox")
            }
            states = {
                row[0]: row[1]
                for row in conn.execute(
                    "SELECT index_state,count(*) FROM snapshots GROUP BY index_state"
                )
            }
            integrity = conn.execute("PRAGMA quick_check").fetchone()[0]
            disk = shutil.disk_usage(self.root)
            storage_bytes = self._storage_usage()
            pressure = (
                "storage_limit"
                if storage_bytes + METADATA_HEADROOM > self.settings.max_storage_bytes
                else "disk_pressure"
                if disk.free - METADATA_HEADROOM < self.settings.min_free_bytes
                else None
            )
            return {
                "status": "ok" if integrity == "ok" and pressure is None else "degraded",
                "metadata_integrity": integrity,
                "counts": counts,
                "index_states": states,
                "index_available": self.index_path.exists(),
                "retrieval_backend": "sqlite-fts5",
                "storage_bytes": storage_bytes,
                "write_admission": pressure or "available",
                "metadata_headroom_bytes": METADATA_HEADROOM,
                "free_bytes": disk.free,
                "max_storage_bytes": self.settings.max_storage_bytes,
                "min_free_bytes": self.settings.min_free_bytes,
                "index_reader_slots": 4,
                "state_dir": str(self.root),
                "sqlite_version": sqlite3.sqlite_version,
            }
