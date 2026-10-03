"""Installed CLI/API/worker journeys over actual HTTP and persistent evidence.

Run with the product environment, for example:
    .venv/bin/python -m pytest tests/integration \
        --basetemp=.runtime/pytest -o cache_dir=.runtime/pytest-cache
All test artifacts remain under the standalone DWS directory.
"""

from __future__ import annotations

import errno
import hashlib
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from http.client import HTTPConnection
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

import pytest
from fixture_site import FixtureSite

PRODUCT = Path(__file__).resolve().parents[2]
TERMINAL = {"succeeded", "partial", "failed", "cancelled"}
HTTP = build_opener(ProxyHandler({}))

INDEX_SCHEMA_PAUSE = r"""
import importlib.util
import json
import signal
import sqlite3
import sys
from pathlib import Path
from dws.config import Settings

mode, marker_name, source_name = sys.argv[1:]
if source_name:
    specification = importlib.util.spec_from_file_location(
        "dws.fc1_baseline_store", source_name
    )
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    Store = module.Store
else:
    from dws.store import Store

settings = Settings.from_env()
original_connection = Store._index_connection

class PausedConnection:
    def __init__(self, connection):
        self.connection = connection
        self.schema_created = False

    def execute(self, statement, *arguments):
        if "CREATE VIRTUAL TABLE" in statement.upper() and "PASSAGES" in statement.upper():
            self.schema_created = True
        return self.connection.execute(statement, *arguments)

    def commit(self):
        self.connection.commit()
        if self.schema_created:
            with sqlite3.connect(settings.data_dir / "management.sqlite3") as metadata:
                pending = metadata.execute(
                    "SELECT count(*) FROM snapshots WHERE expired=0 AND index_state!='ready'"
                ).fetchone()[0]
                outbox = metadata.execute("SELECT count(*) FROM index_outbox").fetchone()[0]
            rows = self.connection.execute("SELECT count(*) FROM passages").fetchone()[0]
            Path(marker_name).write_text(json.dumps({
                "mode": mode, "schema_committed": True, "index_rows": rows,
                "durable_pending_snapshots": pending, "durable_outbox_rows": outbox,
            }))
            while True:
                signal.pause()

    def __getattr__(self, attribute):
        return getattr(self.connection, attribute)

def watched_connection(store):
    return PausedConnection(original_connection(store))

if mode == "rebuild":
    store = Store(settings)
    Store._index_connection = watched_connection
    store.rebuild_index()
else:
    Store._index_connection = watched_connection
    Store(settings)
raise RuntimeError("Expected index schema commit checkpoint was not reached")
"""

PUBLICATION_PAUSE = r"""
import asyncio
import json
import signal
import sqlite3
import sys
from pathlib import Path
from dws.config import Settings
from dws.models import FetchRequest
from dws.providers import Acquisition
from dws.store import Store

mode, marker_name, url, workspace = sys.argv[1:]
settings = Settings.from_env()
store = Store(settings)
capture = asyncio.run(Acquisition(settings).fetch(FetchRequest(url=url, render="never")))
original_sync = Store._sync_dir

def checkpoint(path):
    original_sync(path)
    selected = (mode == "staged" and path.parent.name == "staging") or (
        mode == "renamed" and path.name == "artifacts"
    )
    if selected:
        destination = path if mode == "staged" else next(
            candidate for candidate in path.iterdir()
            if candidate.is_dir() and (candidate / "provenance.json").exists()
            and json.loads((candidate / "provenance.json").read_text())["requested_url"] == url
        )
        with sqlite3.connect(settings.data_dir / "management.sqlite3") as metadata:
            committed = metadata.execute(
                "SELECT count(*) FROM snapshots WHERE id=?", (destination.name,)
            ).fetchone()[0]
        Path(marker_name).write_text(json.dumps({
            "mode": mode, "path": str(destination), "snapshot_id": destination.name,
            "committed_snapshots": committed,
            "files": sorted(item.name for item in destination.iterdir()),
        }))
        while True:
            signal.pause()

Store._sync_dir = staticmethod(checkpoint)
store.save_capture(capture, workspace, None)
raise RuntimeError("Publication interruption checkpoint was not reached")
"""

COPY_TRACE = r"""
import json
import os
import sqlite3
import sys
from pathlib import Path
from dws.config import Settings
from dws.errors import DWSError
from dws.store import Store

operation, backup_id, fail = sys.argv[1:]
settings = Settings.from_env()
store = Store(settings)
events = []
original_fsync = os.fsync
original_connect = sqlite3.connect

def watched_fsync(fd):
    path = Path(os.readlink('/proc/self/fd/' + str(fd)))
    if fail == 'true' and path.name == 'source.bin':
        events.append({'kind': 'failed_fsync', 'path': str(path)})
        raise OSError('Owner fixture interrupted copied-file fsync')
    original_fsync(fd)
    events.append({'kind': 'fsync', 'path': str(path), 'directory': path.is_dir()})

class WatchedConnection(sqlite3.Connection):
    def backup(self, target, *arguments, **keywords):
        destination = target.execute('PRAGMA database_list').fetchone()[2]
        if Path(destination) == settings.data_dir / 'management.sqlite3':
            events.append({'kind': 'metadata_publish', 'path': destination})
        return super().backup(target, *arguments, **keywords)

def watched_connect(*arguments, **keywords):
    keywords.setdefault('factory', WatchedConnection)
    return original_connect(*arguments, **keywords)

os.fsync = watched_fsync
sqlite3.connect = watched_connect
try:
    result = store.backup() if operation == 'backup' else store.restore(backup_id)
    events.append({'kind': 'acknowledged'})
    outcome = {'ok': True, 'result': result, 'events': events}
except DWSError as error:
    outcome = {'ok': False, 'status': error.status, 'error': error.payload(), 'events': events}
print(json.dumps(outcome))
"""


CAPTURE_IO_API = r"""
# Test-owned child API; faults target only this isolated capture filesystem.

from __future__ import annotations

import errno
import json
import os
import sys
from pathlib import Path

import uvicorn
from dws.api import create_app

app = create_app()
store = app.state.engine.store
state = store.root
control = state.parent / "capture-io-control.json"
events = state.parent / "capture-io-events.jsonl"
original_write = store._write
original_fsync = os.fsync


def selected() -> str:
    return json.loads(control.read_text())["mode"] if control.exists() else ""


def record(kind: str, path: Path, mode: str, **extra: object) -> None:
    with events.open("a") as stream:
        stream.write(
            json.dumps({"kind": kind, "path": str(path), "mode": mode, **extra}) + "\n"
        )


def fail(kind: str, path: Path, mode: str, number: int) -> None:
    record(kind, path, mode, errno=number)
    raise OSError(number, "Private owner failure at " + str(path))


def watched_write(path: Path, data: bytes) -> None:
    mode = selected()
    if mode == "write-enospc" and path.name == "normalized.txt":
        assert (path.parent / "source.bin").is_file()
        fail("write_failed", path, mode, errno.ENOSPC)
    if mode == "write-unclassified" and path.name == "normalized.txt":
        assert (path.parent / "source.bin").is_file()
        record("unclassified_write_failed", path, mode, errno=None)
        raise RuntimeError("Private owner unexpected failure at " + str(path))
    original_write(path, data)
    record("write_completed", path, mode)


def watched_fsync(fd: int) -> None:
    path = Path(os.readlink("/proc/self/fd/" + str(fd)))
    mode = selected()
    if (
        mode == "file-fsync-eio"
        and path.name == "normalized.txt"
        and path.parent.parent == state / "staging"
    ):
        fail("file_fsync_failed", path, mode, errno.EIO)
    if mode == "publication-fsync-edquot" and path == state / "artifacts":
        url = json.loads(control.read_text())["url"]
        renamed = [
            item for item in path.iterdir()
            if (item / "provenance.json").is_file()
            and json.loads((item / "provenance.json").read_text())["requested_url"] == url
        ]
        assert len(renamed) == 1
        record("renamed_before_failed_fsync", renamed[0], mode)
        fail("publication_fsync_failed", path, mode, errno.EDQUOT)
    original_fsync(fd)
    if path.is_relative_to(state / "staging") or path == state / "artifacts":
        record("fsync_completed", path, mode, directory=path.is_dir())


store._write = watched_write
os.fsync = watched_fsync
uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="warning")
"""


class Product:
    def __init__(self, directory: Path, site: FixtureSite) -> None:
        self.directory = directory
        self.site = site
        with socket.socket() as port:
            port.bind(("127.0.0.1", 0))
            self.port = port.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.env = dict(os.environ)
        self.env.update(
            {
                "DWS_DATA_DIR": str(directory / "state"),
                "DWS_API_URL": self.url,
                "DWS_TOKEN": "integration-owner-token",
                "DWS_SEARXNG_URL": site.url,
                "DWS_DDGS_ENABLED": "false",
                "DWS_CRAWL4AI_URL": "",
                "DWS_ALLOWED_PRIVATE_HOSTS": "127.0.0.1",
                "DWS_MIN_FREE_BYTES": "0",
                "DWS_MAX_BYTES": "32768",
                "DWS_REQUEST_TIMEOUT": "10",
                "DWS_MAX_JOBS": "6",
                "DWS_MAX_STORAGE_BYTES": "8000000",
                "DWS_LEASE_SECONDS": "10",
                "DWS_MCP_ENABLED": "false",
                "PYTHONDONTWRITEBYTECODE": "1",
                "TMPDIR": str(directory / "tmp"),
                "XDG_CACHE_HOME": str(directory / "cache"),
            }
        )
        for local in ("tmp", "cache"):
            (directory / local).mkdir()
        self.api: subprocess.Popen[bytes] | None = None
        self.worker: subprocess.Popen[bytes] | None = None
        self.logs: list[Any] = []

    def start_api(self, *, script: str | None = None) -> None:
        log = (self.directory / "api.log").open("ab")
        self.logs.append(log)
        command = [
            sys.executable,
            "-m",
            "dws",
            "api",
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
        ]
        if script is not None:
            script_path = self.directory / "capture-io-api.py"
            script_path.write_text(script)
            command = [sys.executable, str(script_path), str(self.port)]
        self.api = subprocess.Popen(
            command,
            cwd=PRODUCT,
            env=self.env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if self.api.poll() is not None:
                pytest.fail("API exited:\n" + (self.directory / "api.log").read_text())
            try:
                with HTTP.open(self.url + "/ready", timeout=1) as response:
                    if response.status == 200:
                        return
            except (URLError, TimeoutError):
                threading.Event().wait(0.1)
        pytest.fail("API readiness timed out:\n" + (self.directory / "api.log").read_text())

    def start_worker(self) -> None:
        log = (self.directory / "worker.log").open("ab")
        self.logs.append(log)
        self.worker = subprocess.Popen(
            [sys.executable, "-m", "dws", "worker"],
            cwd=PRODUCT,
            env=self.env,
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    @staticmethod
    def stop(process: subprocess.Popen[bytes] | None, *, kill: bool = False) -> None:
        if process is None or process.poll() is not None:
            return
        process.kill() if kill else process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)

    def close(self) -> None:
        self.site.release_slow.set()
        self.site.release_shared.set()
        self.site.release_budget.set()
        self.site.release_discovery.set()
        self.site.release_seed.set()
        self.stop(self.worker)
        self.stop(self.api)
        for log in self.logs:
            log.close()

    def request(
        self,
        operation: str,
        payload: dict[str, Any],
        *,
        token: str | None = "integration-owner-token",
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        request_headers = {"Content-Type": "application/json"}
        if token is not None:
            request_headers["Authorization"] = "Bearer " + token
        request_headers.update(headers or {})
        request = Request(
            self.url + "/v1/" + operation,
            data=json.dumps(payload).encode(),
            headers=request_headers,
            method="POST",
        )
        try:
            with HTTP.open(request, timeout=30) as response:
                return response.status, json.load(response)
        except HTTPError as error:
            return error.code, json.load(error)

    def call(self, operation: str, **payload: Any) -> dict[str, Any]:
        status, result = self.request(operation, payload)
        assert status == 200, (operation, status, result)
        assert result["schema_version"] == "1.0"
        if operation == "job_status":
            total, offset = result["counts"]["total"], result["offset"]
            shown = len(result["manifest"])
            assert total == sum(
                value for key, value in result["counts"].items() if key != "total"
            )
            if offset < total:
                assert offset + shown <= total, result
            else:
                assert not result["manifest"], result
            assert result["next_offset"] == (
                offset + shown if offset + shown < total else None
            ), result
            for row in result["manifest"]:
                assert result["counts"][row["state"]] > 0, result
        return result

    def run_cli(
        self, *arguments: str, env_updates: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "dws", *arguments],
            cwd=PRODUCT,
            env={**self.env, **(env_updates or {})},
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def cli(self, *arguments: str, env_updates: dict[str, str] | None = None) -> dict[str, Any]:
        completed = self.run_cli(*arguments, env_updates=env_updates)
        assert completed.returncode == 0, (arguments, completed.stdout, completed.stderr)
        result = cast(dict[str, Any], json.loads(completed.stdout))
        assert result["schema_version"] == "1.0"
        return result

    def await_job(
        self, job_id: str, *, timeout: float = 30, workspace_id: str = "default"
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        result: dict[str, Any] = {}
        while time.monotonic() < deadline:
            result = self.call(
                "job_status", job_id=job_id, workspace_id=workspace_id, limit=100
            )
            if result["state"] in TERMINAL:
                return result
            assert self.worker is not None and self.worker.poll() is None, (
                self.directory / "worker.log"
            ).read_text()
            threading.Event().wait(0.2)
        pytest.fail(f"Specific job {job_id} did not finish: {result}")

    def await_retrieval(self, query: str, **scope: Any) -> dict[str, Any]:
        deadline = time.monotonic() + 10
        result: dict[str, Any] = {}
        while time.monotonic() < deadline:
            result = self.call("retrieve", query=query, **scope)
            if result["results"] and not result.get("partial", False):
                return result
            threading.Event().wait(0.2)
        pytest.fail(f"Retrieval for specific scope {scope} stayed incomplete: {result}")

    def interrupt_index_schema_commit(self, mode: str) -> dict[str, Any]:
        self.stop(self.worker)
        self.stop(self.api)
        if mode == "missing-startup":
            state = Path(self.env["DWS_DATA_DIR"])
            for artifact in state.glob("index.sqlite3*"):
                artifact.unlink()
        source = self.env.get("DWS_TEST_STORE_SOURCE", "")
        if source:
            resolved = Path(source).resolve()
            assert resolved.is_relative_to(PRODUCT) and resolved.is_file()
            source = str(resolved)
        marker = self.directory / f"{mode}-schema-committed.json"
        with (self.directory / f"{mode}-child.log").open("wb") as log:
            child = subprocess.Popen(
                [sys.executable, "-c", INDEX_SCHEMA_PAUSE, mode, str(marker), source],
                cwd=PRODUCT,
                env=self.env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 15
                while not marker.exists() and time.monotonic() < deadline:
                    assert child.poll() is None, (
                        self.directory / f"{mode}-child.log"
                    ).read_text()
                    threading.Event().wait(0.05)
                assert marker.exists(), (
                    "The actual index-schema commit checkpoint was not reached"
                )
                observed = cast(dict[str, Any], json.loads(marker.read_text()))
            finally:
                self.stop(child, kill=True)
        assert child.returncode == -9, "Recovery must follow an actual abrupt process kill"
        return observed

    def interrupt_publication(self, mode: str, workspace: str) -> dict[str, Any]:
        self.stop(self.worker)
        self.stop(self.api)
        marker = self.directory / f"{mode}-publication.json"
        log_path = self.directory / f"{mode}-publication-child.log"
        with log_path.open("wb") as log:
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    PUBLICATION_PAUSE,
                    mode,
                    str(marker),
                    self.site.url + f"/scope/orphan-{mode}",
                    workspace,
                ],
                cwd=PRODUCT,
                env=self.env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            try:
                deadline = time.monotonic() + 15
                while not marker.exists() and time.monotonic() < deadline:
                    assert child.poll() is None, log_path.read_text()
                    threading.Event().wait(0.05)
                assert marker.exists(), "Actual publication fsync checkpoint not reached"
                observed = cast(dict[str, Any], json.loads(marker.read_text()))
            finally:
                self.stop(child, kill=True)
        assert child.returncode == -9
        return observed

    def trace_copy(
        self, operation: str, *, backup_id: str = "", fail: bool = False
    ) -> dict[str, Any]:
        completed = subprocess.run(
            [sys.executable, "-c", COPY_TRACE, operation, backup_id, str(fail).lower()],
            cwd=PRODUCT,
            env=self.env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert completed.returncode == 0, (completed.stdout, completed.stderr)
        result = cast(dict[str, Any], json.loads(completed.stdout))
        suffix = "failure" if fail else "success"
        (self.directory / f"{operation}-copy-{suffix}.json").write_text(
            json.dumps(result, indent=2) + "\n"
        )
        return result


@pytest.fixture
def product() -> Any:
    artifacts = PRODUCT / ".runtime" / "product-tests"
    artifacts.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="journey-", dir=artifacts))
    with FixtureSite(directory) as site:
        instance = Product(directory, site)
        try:
            instance.start_api()
            instance.start_worker()
            yield instance
        finally:
            instance.close()


def test_research_journeys_retain_exact_evidence(product: Product) -> None:
    discovery = product.cli("search", "systems architecture")
    assert discovery["results"][0]["url"] == product.site.url + "/article"
    captured = product.cli("fetch", discovery["results"][0]["url"], "--render", "never")
    snapshot = captured["snapshot_id"]
    original = product.cli("read", snapshot)
    assert "RevisionMarker original" in original["text"]
    assert "17 milliseconds" in original["text"], (
        "Acquisition must preserve useful table values"
    )
    product.await_retrieval("LatePassageAmber")
    passages = product.cli("retrieve", "LatePassageAmber")
    assert passages["results"], passages
    passage = passages["results"][0]
    exact = product.cli(
        "read",
        snapshot,
        "--start",
        str(passage["line_start"]),
        "--end",
        str(passage["line_end"]),
    )
    assert passage["text"] == original["text"][passage["char_start"] : passage["char_end"]]
    relative_start = passage["char_start"] - exact["char_start"]
    relative_end = passage["char_end"] - exact["char_start"]
    assert relative_start >= 0
    assert passage["text"] == exact["text"][relative_start:relative_end]
    product.cli("pin", snapshot)
    product.site.revision = "revised"
    fresh = product.cli(
        "fetch", product.site.url + "/article", "--refresh", "--render", "never"
    )
    assert fresh["snapshot_id"] != snapshot
    assert "RevisionMarker original" in product.cli("read", snapshot)["text"]
    assert "RevisionMarker revised" in product.cli("read", fresh["snapshot_id"])["text"]
    exported = product.cli("export", snapshot)
    assert exported["snapshot_id"] == snapshot
    export_path = Path(exported["path"])
    assert export_path.is_relative_to(product.directory)
    assert (export_path / "normalized.txt").read_text() == original["text"]
    pinned_expiry_status, pinned_expiry = product.request("expire", {"snapshot_id": snapshot})
    assert pinned_expiry_status == 409, pinned_expiry

    filing = product.cli("search", "public filing")
    pdf = product.cli("fetch", filing["results"][0]["url"], "--render", "never")
    pdf_read = product.cli("read", pdf["snapshot_id"])
    assert "RevenueMarker 2026 revenue was 314 million" in pdf_read["text"]
    assert any(location["page"] == 1 for location in pdf_read["location_map"])
    assert pdf["content_type"].startswith("application/pdf")
    product.await_retrieval("RevenueMarker")
    assert product.cli("retrieve", "RevenueMarker")["results"]
    product.cli("unpin", snapshot)
    product.cli("expire", snapshot)
    unavailable_status, unavailable = product.request("read", {"snapshot_id": snapshot})
    assert unavailable_status in {404, 410}, unavailable
    assert unavailable["error"]["code"] in {
        "snapshot_expired",
        "expired",
        "snapshot_unavailable",
    }
    assert product.site.requests.count("/article") == 2, (
        "read must not reacquire expired evidence"
    )
    for route in ("/html/page-heading", "/html/extreme-page-heading"):
        html = product.cli("fetch", product.site.url + route, "--render", "never")
        html_read = product.cli("read", html["snapshot_id"], "--max-chars", "12000")
        assert "HtmlPageMarker" in html_read["text"]
        assert all(location.get("page") is None for location in html_read["location_map"])
        html_hits = product.await_retrieval(
            "HtmlPageMarker", document_ids=[html["document_id"]]
        )
        assert html_hits["results"]
        for hit in html_hits["results"]:
            assert hit["text"] == html_read["text"][hit["char_start"] : hit["char_end"]]
    multipage = product.cli("fetch", product.site.url + "/multipage.pdf", "--render", "never")
    physical = product.cli("read", multipage["snapshot_id"])
    for marker, page in (("PhysicalPageOneMarker", 1), ("PhysicalPageTwoMarker", 2)):
        position = physical["text"].index(marker)
        assert (
            next(
                location["page"]
                for location in physical["location_map"]
                if location["char_start"] <= position < location["char_end"]
            )
            == page
        )
    charset_receipts = []
    for variant, marker in (
        ("header", "HeaderCharsetMarker"),
        ("bom", "BomCharsetMarker"),
        ("latin1", "LatinCharsetMarker"),
        ("unknown", "UnknownCharsetMarker"),
    ):
        if variant == "latin1":
            route = "/charset/latin1.txt"
            expected_raw = "LatinCharsetMarker cost £ café.\n".encode("iso-8859-1")
            expected_text = "LatinCharsetMarker cost £ café."
        else:
            route = f"/charset/{variant}.html"
            declared = "utf-8" if variant == "unknown" else "iso-8859-1"
            expected_raw = (
                f'<html><head><meta charset="{declared}">'
                "<title>Encoding evidence</title></head><body>"
                f"<h1>Encoding evidence</h1><p>{marker} cost £ café.</p>"
                "</body></html>"
            ).encode()
            if variant == "bom":
                expected_raw = b"\xef\xbb\xbf" + expected_raw
            expected_text = "# Encoding evidence\n\n" + marker + " cost £ café."
        selected = product.cli("fetch", product.site.url + route, "--render", "never")
        exact = product.cli("read", selected["snapshot_id"])
        assert exact["text"] == expected_text, (variant, exact)
        folder = Path(product.env["DWS_DATA_DIR"]) / "artifacts" / selected["snapshot_id"]
        assert (folder / "source.bin").read_bytes() == expected_raw
        assert selected["raw_hash"] == hashlib.sha256(expected_raw).hexdigest()
        assert selected["text_hash"] == hashlib.sha256(expected_text.encode()).hexdigest()
        provenance = json.loads((folder / "provenance.json").read_text())
        assert provenance["normalizer"] == selected["normalizer"] == exact["normalizer"]
        assert provenance["raw_hash"] == selected["raw_hash"]
        assert provenance["text_hash"] == selected["text_hash"]
        expected_decoder = {
            "header": "decode/utf-8/http/1",
            "bom": "decode/utf-8/bom/1",
            "latin1": "decode/iso8859-1/http/1",
            "unknown": "decode/utf-8/inferred/1",
        }[variant]
        assert expected_decoder in provenance["normalizer"].split("+")
        assert ("transport_charset_invalid_ignored" in provenance["warnings"]) == (
            variant == "unknown"
        )
        assert ("transport_charset_overridden_by_bom" in provenance["warnings"]) == (
            variant == "bom"
        )
        assert ("source_encoding_inferred" in provenance["warnings"]) == (variant == "unknown")
        assert "source_encoding_replacement_characters" not in provenance["warnings"]
        indexed = product.await_retrieval(marker, document_ids=[selected["document_id"]])
        assert {hit["snapshot_id"] for hit in indexed["results"]} == {selected["snapshot_id"]}
        for hit in indexed["results"]:
            cited = product.call(
                "read",
                snapshot_id=selected["snapshot_id"],
                line_start=hit["line_start"],
                line_end=hit["line_end"],
            )
            assert hit["text"] == exact["text"][hit["char_start"] : hit["char_end"]]
            assert "£ café" in hit["text"]
            assert hit["citation"] == cited["citation"]
        charset_receipts.append(
            {
                "variant": variant,
                "snapshot_id": selected["snapshot_id"],
                "normalizer": provenance["normalizer"],
                "raw_hash": provenance["raw_hash"],
                "text_hash": provenance["text_hash"],
                "warnings": provenance["warnings"],
                "exact_cited_passage": True,
            }
        )
    (product.directory / "source-charset-receipt.json").write_text(
        json.dumps({"cases": charset_receipts}, indent=2)
    )
    section_receipts = []
    for route, title, marker, expected_titles in (
        ("/html/code-sections", "Install", "AfterCodeMarker", ["Install", "Other"]),
        ("/html/sharp-heading", "C#", "SharpHeadingMarker", ["C#"]),
        (
            "/text/fenced-sections",
            "Fences",
            "AfterFenceMarker",
            ["Fences", "Closing", "Escaped \\#"],
        ),
    ):
        selected = product.cli("fetch", product.site.url + route, "--render", "never")
        exact = product.cli("read", selected["snapshot_id"])
        section = product.call("read", snapshot_id=selected["snapshot_id"], section=title)
        assert marker in section["text"], (route, section)
        assert [item["title"] for item in exact["sections"]] == expected_titles
        if title == "Install":
            assert "# Shell comment" in section["text"] and "echo ready" in section["text"]
            assert "NestedOtherMarker" in section["text"]
            status, absent = product.request(
                "read", {"snapshot_id": selected["snapshot_id"], "section": "Shell comment"}
            )
            assert status == 404 and absent["error"]["code"] == "section_not_found", absent
        elif title == "C#":
            assert exact["text"].startswith("# C#\n")
        else:
            assert "# Tilde comment" in section["text"]
            assert "# Backtick comment" in section["text"]
            assert "# Still code" in section["text"]
            assert "ClosingMarker" not in section["text"]
            for named, expected_marker in (
                ("Closing", "ClosingMarker"),
                ("Escaped \\#", "EscapedHashMarker"),
            ):
                named_section = product.call(
                    "read", snapshot_id=selected["snapshot_id"], section=named
                )
                assert expected_marker in named_section["text"]
        indexed = product.await_retrieval(marker, document_ids=[selected["document_id"]])
        assert {hit["snapshot_id"] for hit in indexed["results"]} == {selected["snapshot_id"]}
        for hit in indexed["results"]:
            assert hit["text"] == exact["text"][hit["char_start"] : hit["char_end"]]
        section_receipts.append(
            {"snapshot_id": selected["snapshot_id"], "titles": expected_titles, "route": route}
        )
    for route, expected_titles in (
        ("/text/setext-sections", ["Overview", "Nested\nDetails", "Later\nOverview"]),
        ("/text/empty-atx-sections", ["Overview", "Retained"]),
    ):
        selected = product.cli("fetch", product.site.url + route, "--render", "never")
        exact = product.cli("read", selected["snapshot_id"])
        overview = product.call("read", snapshot_id=selected["snapshot_id"], section="Overview")
        assert [item["title"] for item in exact["sections"]] == expected_titles
        if route.endswith("setext-sections"):
            assert "OverviewSetextMarker" in overview["text"]
            assert "NestedSetextMarker" in overview["text"]
            assert "LaterSetextMarker" not in overview["text"]
            assert overview["text"].startswith("Overview\n========\n")
            for title, marker in (
                ("Nested\nDetails", "NestedSetextMarker"),
                ("Later\nOverview", "LaterSetextMarker"),
            ):
                multiline_section = product.call(
                    "read", snapshot_id=selected["snapshot_id"], section=title
                )
                assert marker in multiline_section["text"]
            marker = "NestedSetextMarker"
        else:
            assert "EmptyBoundaryMarker" in overview["text"]
            assert "OtherBodyAfterEmptyMarker" not in overview["text"]
            assert "RetainedBoundaryMarker" not in overview["text"]
            retained = product.call(
                "read", snapshot_id=selected["snapshot_id"], section="Retained"
            )
            assert "RetainedBoundaryMarker" in retained["text"]
            assert "OtherBodyAfterHashesMarker" not in retained["text"]
            marker = "RetainedBoundaryMarker"
        assert overview["text"] == exact["text"][overview["char_start"] : overview["char_end"]]
        indexed = product.await_retrieval(marker, document_ids=[selected["document_id"]])
        assert {hit["snapshot_id"] for hit in indexed["results"]} == {selected["snapshot_id"]}
        for hit in indexed["results"]:
            assert hit["text"] == exact["text"][hit["char_start"] : hit["char_end"]]
        section_receipts.append(
            {"snapshot_id": selected["snapshot_id"], "titles": expected_titles, "route": route}
        )
    (product.directory / "source-section-receipt.json").write_text(
        json.dumps({"cases": section_receipts, "exact_scoped_passages": True}, indent=2)
    )
    product.stop(product.worker)
    product.stop(product.api)
    product.env.update(
        {
            "DWS_MAX_BYTES": "4000000",
            "DWS_MAX_TEXT_CHARS": "2000000",
            "DWS_MAX_STORAGE_BYTES": "150000000",
            "DWS_REQUEST_TIMEOUT": "20",
        }
    )
    product.start_api()
    product.start_worker()
    started = time.monotonic()
    dense = product.cli("fetch", product.site.url + "/html/dense-sections", "--render", "never")
    capture_seconds = time.monotonic() - started
    assert capture_seconds < float(product.env["DWS_REQUEST_TIMEOUT"])
    section = product.call(
        "read", snapshot_id=dense["snapshot_id"], section="Dense section 15999"
    )
    assert "DenseFinalMarker" in section["text"]
    assert section["line_end"] >= section["line_start"]
    for line in section["location_map"]:
        assert line.get("page") is None
    dense_hits = product.await_retrieval(
        "DenseFinalMarker", document_ids=[dense["document_id"]]
    )
    hit = dense_hits["results"][0]
    exact_lines = product.call(
        "read",
        snapshot_id=dense["snapshot_id"],
        line_start=hit["line_start"],
        line_end=hit["line_end"],
    )
    relative_start, relative_end = (
        hit["char_start"] - exact_lines["char_start"],
        hit["char_end"] - exact_lines["char_start"],
    )
    assert hit["text"] == exact_lines["text"][relative_start:relative_end]
    started = time.monotonic()
    whitespace = product.cli(
        "fetch", product.site.url + "/text/adversarial-heading", "--render", "never"
    )
    whitespace_seconds = time.monotonic() - started
    assert whitespace_seconds < float(product.env["DWS_REQUEST_TIMEOUT"])
    whitespace_read = product.cli("read", whitespace["snapshot_id"], "--max-chars", "12000")
    assert whitespace_read["text"].startswith("# A" + " " * 4096 + "B\n")
    assert "WhitespaceHeadingMarker" in whitespace_read["text"]
    mapping_path = (
        Path(product.env["DWS_DATA_DIR"])
        / "artifacts"
        / whitespace["snapshot_id"]
        / "mapping.json"
    )
    whitespace_mapping = json.loads(mapping_path.read_text())
    assert whitespace_mapping["sections"][0]["title"] == "A" + " " * 4096 + "B"
    assert all(location.get("page") is None for location in whitespace_read["location_map"])
    whitespace_hits = product.await_retrieval(
        "WhitespaceHeadingMarker", document_ids=[whitespace["document_id"]]
    )
    for passage in whitespace_hits["results"]:
        assert (
            passage["text"]
            == whitespace_read["text"][passage["char_start"] : passage["char_end"]]
        )
    long_query = " ".join(f"zzmissing{index:02d}" for index in range(32)) + " DenseFinalMarker"
    assert len(long_query) < 512
    all_terms = product.call("retrieve", query=long_query, document_ids=[dense["document_id"]])
    assert {passage["snapshot_id"] for passage in all_terms["results"]} == {
        dense["snapshot_id"]
    }
    all_terms_cli = product.cli("retrieve", long_query, "--document", dense["document_id"])
    assert {passage["snapshot_id"] for passage in all_terms_cli["results"]} == {
        dense["snapshot_id"]
    }
    (product.directory / "source-mapping-receipt.json").write_text(
        json.dumps(
            {
                "html_page_headings_are_not_pdf_locations": True,
                "extreme_heading_digits": 5000,
                "physical_pdf_pages": [1, 2],
                "dense_sections": 16000,
                "dense_capture_seconds": capture_seconds,
                "dense_request_budget_seconds": 20,
                "snapshot_id": dense["snapshot_id"],
                "exact_passage_verified": True,
                "interior_heading_spaces": 4096,
                "interior_heading_capture_seconds": whitespace_seconds,
                "retained_match_at_query_term": 33,
            },
            indent=2,
        )
        + "\n"
    )


def test_scoped_concurrency_index_loss_and_backup_restore(product: Product) -> None:
    workspaces = [
        product.call("workspace_create", name=f"project-{i}")["workspace_id"] for i in range(4)
    ]

    def capture_owned(index: int) -> dict[str, Any]:
        return product.call(
            "fetch",
            url=product.site.url + f"/scope/{index}",
            workspace_id=workspaces[index],
            render="never",
        )

    with ThreadPoolExecutor(max_workers=4) as callers:
        captured = list(callers.map(capture_owned, range(4)))
        # Enough strongly matching unrelated documents to detect global top-K
        # followed by scope filtering, which can incorrectly empty a workspace.
        list(
            callers.map(
                lambda index: product.call(
                    "fetch", url=product.site.url + f"/scope/decoy-{index}", render="never"
                ),
                range(8),
            )
        )
    product.await_retrieval("SharedMarker")
    with ThreadPoolExecutor(max_workers=4) as callers:
        scoped_results = list(
            callers.map(
                lambda workspace: product.await_retrieval(
                    "SharedMarker", workspace_id=workspace
                ),
                workspaces,
            )
        )
    for index, (item, scoped) in enumerate(zip(captured, scoped_results, strict=True)):
        assert scoped["results"], scoped
        assert all(result["snapshot_id"] == item["snapshot_id"] for result in scoped["results"])
        assert all(f"Owner{index}" in result["text"] for result in scoped["results"])
        status, denied = product.request(
            "read",
            {"snapshot_id": item["snapshot_id"], "workspace_id": workspaces[(index + 1) % 4]},
        )
        assert status == 404, denied
    run = product.call("run_create", workspace_id=workspaces[0], name="specific-run")["run_id"]
    isolated = product.call(
        "fetch",
        url=product.site.url + "/scope/run-only",
        workspace_id=workspaces[0],
        run_id=run,
        render="never",
    )
    run_hits = product.await_retrieval("SharedMarker", workspace_id=workspaces[0], run_id=run)
    assert {hit["snapshot_id"] for hit in run_hits["results"]} == {isolated["snapshot_id"]}
    document_hits = product.call(
        "retrieve",
        query="SharedMarker",
        workspace_id=workspaces[0],
        document_ids=[captured[0]["document_id"]],
    )
    assert {hit["snapshot_id"] for hit in document_hits["results"]} == {
        captured[0]["snapshot_id"]
    }
    product.stop(product.worker)
    index_overlap = product.call(
        "fetch", url=product.site.url + "/scope/index-overlap", render="never"
    )
    assert index_overlap["index_state"] == "pending"
    assert product.call("read", snapshot_id=index_overlap["snapshot_id"])["text"]
    barrier = threading.Barrier(4)

    aliases = [
        product.site.url + "/scope/coalesced#first",
        product.site.url + "/scope/coalesced#second",
        product.site.url.replace("http://", "HTTP://") + "/scope/coalesced#third",
        product.site.url + "/scope/coalesced",
    ]

    def equivalent_fetch(url: str) -> dict[str, Any]:
        barrier.wait(timeout=5)
        return product.call("fetch", url=url, render="never")

    with ThreadPoolExecutor(max_workers=7) as callers:
        equivalent = [callers.submit(equivalent_fetch, url) for url in aliases]
        try:
            assert product.site.shared_started.wait(timeout=3)
            assert all(not request.done() for request in equivalent)
            assert product.call(
                "read", snapshot_id=captured[0]["snapshot_id"], workspace_id=workspaces[0]
            )["text"]
            overlapping = product.call(
                "retrieve", query="SharedMarker", workspace_id=workspaces[3]
            )
            assert {hit["snapshot_id"] for hit in overlapping["results"]} == {
                captured[3]["snapshot_id"]
            }
            product.start_worker()
            indexed_while_acquiring = product.await_retrieval(
                "SharedMarker", document_ids=[index_overlap["document_id"]]
            )
            assert {hit["snapshot_id"] for hit in indexed_while_acquiring["results"]} == {
                index_overlap["snapshot_id"]
            }
            assert all(not request.done() for request in equivalent)
            extra = [
                callers.submit(
                    product.request,
                    "fetch",
                    {"url": product.site.url + f"/scope/admission-{i}", "render": "never"},
                )
                for i in range(3)
            ]
            completed, _pending = wait(extra, timeout=3, return_when=FIRST_COMPLETED)
            assert completed, "One of seven concurrent callers must reach the six-request limit"
            assert any(
                request.result()[0] == 429 and request.result()[1]["error"]["code"] == "busy"
                for request in completed
            )
        finally:
            product.site.release_shared.set()
        equivalent_results = [request.result(timeout=15) for request in equivalent]
        assert len({result["snapshot_id"] for result in equivalent_results}) == 1
        assert product.site.requests.count("/scope/coalesced") == 1
        assert (
            "Ownercoalesced"
            in product.call("read", snapshot_id=equivalent_results[0]["snapshot_id"])["text"]
        )
        admitted = [request.result(timeout=15) for request in extra]
        assert all(status in {200, 429} for status, _result in admitted)
        assert any(status == 429 for status, _result in admitted)
    snapshot = captured[0]["snapshot_id"]
    product.call("pin", snapshot_id=snapshot, workspace_id=workspaces[0])
    before = product.call("read", snapshot_id=snapshot, workspace_id=workspaces[0])["text"]
    product.stop(product.worker)
    old_backup = product.cli("backup")
    post_backup = product.call(
        "fetch",
        url=product.site.url + "/scope/post-backup",
        workspace_id=workspaces[0],
        render="never",
    )
    product.call("pin", snapshot_id=post_backup["snapshot_id"], workspace_id=workspaces[0])
    acknowledged = product.call(
        "crawl",
        seed_url=product.site.url + "/crawl/start.html",
        max_pages=4,
        render="never",
        idempotency_key="post-backup-acknowledged",
    )
    refusal_status, refusal = product.request("restore", {"backup_id": old_backup["backup_id"]})
    assert (
        refusal_status == 409 and refusal["error"]["code"] == "restore_would_discard_state"
    ), refusal
    assert (
        product.call(
            "read", snapshot_id=post_backup["snapshot_id"], workspace_id=workspaces[0]
        )["pinned"]
        is True
    )
    assert product.call("job_status", job_id=acknowledged["job_id"])["state"] == "queued"
    backup = product.cli("backup")
    product.stop(product.api)
    canonical_index = Path(product.env["DWS_DATA_DIR"]) / "index.sqlite3"
    assert canonical_index.exists(), "The index must be independent from management state"
    for index_artifact in canonical_index.parent.glob(canonical_index.name + "*"):
        index_artifact.unlink()
    product.start_api()
    assert (
        product.call("read", snapshot_id=snapshot, workspace_id=workspaces[0])["text"] == before
    )
    pending = product.call("retrieve", query="SharedMarker", workspace_id=workspaces[0])
    assert pending["partial"] is True and not pending["results"], pending
    product.cli("index", "rebuild")
    assert product.call("retrieve", query="SharedMarker", workspace_id=workspaces[0])["results"]
    canonical = Path(product.env["DWS_DATA_DIR"]) / "artifacts" / snapshot / "normalized.txt"
    canonical.chmod(0o600)
    canonical.write_text("Corrupted local copy after the backup.")
    corrupted_status, corrupted = product.request(
        "read", {"snapshot_id": snapshot, "workspace_id": workspaces[0]}
    )
    assert corrupted_status == 500 and corrupted["error"]["code"] == "artifact_integrity"
    restored = product.cli("restore", backup["backup_id"])
    assert restored["repaired_artifacts"] == 1
    assert (
        product.call("read", snapshot_id=snapshot, workspace_id=workspaces[0])["text"] == before
    )
    dry_run = product.cli("gc")
    assert dry_run["dry_run"] is True
    assert (
        product.call("read", snapshot_id=snapshot, workspace_id=workspaces[0])["text"] == before
    )
    product.call("pin", snapshot_id=captured[1]["snapshot_id"], workspace_id=workspaces[1])
    pressure = Path(product.env["DWS_DATA_DIR"]) / "owner-pressure-fixture.bin"
    with pressure.open("wb") as artificial_pressure:
        artificial_pressure.truncate(int(product.env["DWS_MAX_STORAGE_BYTES"]))
    assert product.cli("diagnostics")["write_admission"] == "storage_limit"
    assert (
        product.call("read", snapshot_id=snapshot, workspace_id=workspaces[0])["text"] == before
    )
    assert product.call("job_status", job_id=acknowledged["job_id"])["state"] == "queued"
    for operation, payload in (
        ("workspace_create", {"name": "pressure-rejected-workspace"}),
        ("run_create", {"workspace_id": workspaces[0], "name": "pressure-rejected-run"}),
        (
            "crawl",
            {
                "seed_url": product.site.url + "/crawl/start.html",
                "idempotency_key": "pressure-new",
            },
        ),
        (
            "fetch",
            {
                "url": product.site.url + "/scope/0",
                "workspace_id": workspaces[0],
                "render": "never",
            },
        ),
        ("fetch", {"url": product.site.url + "/scope/no-space", "render": "never"}),
    ):
        pressure_status, refused = product.request(operation, payload)
        assert pressure_status == 507 and refused["error"]["code"] == "storage_limit", refused
    product.call(
        "pin", snapshot_id=captured[1]["snapshot_id"], workspace_id=workspaces[1], pinned=False
    )
    product.call("expire", snapshot_id=captured[1]["snapshot_id"], workspace_id=workspaces[1])
    collected = product.cli("gc", "--apply")
    assert captured[1]["snapshot_id"] in collected["snapshot_ids"]
    assert (
        product.call("read", snapshot_id=snapshot, workspace_id=workspaces[0])["pinned"] is True
    )
    pressure.unlink()
    assert product.cli("diagnostics")["write_admission"] == "available"
    assert product.call("workspace_create", name="after-pressure")["workspace_id"]
    diagnostics = product.cli("diagnostics")
    assert "integration-owner-token" not in json.dumps(diagnostics)


def test_durable_crawl_restart_idempotency_cancel_and_scope(product: Product) -> None:
    product.site.hold_crawl_seed = True
    submitted = product.cli(
        "crawl",
        product.site.url + "/crawl/start.html",
        "--pages",
        "8",
        "--depth",
        "3",
        "--seconds",
        "30",
        "--render",
        "never",
        "--idempotency-key",
        "durable-crawl",
    )
    job_id = submitted["job_id"]
    assert product.site.seed_started.wait(timeout=10)
    poll_finished = threading.Event()

    def poll_frontier_pages(target: str) -> int:
        observations = 0
        deadline = time.monotonic() + 15
        while not poll_finished.is_set() and time.monotonic() < deadline:
            product.call("job_status", job_id=target, limit=1)
            observations += 1
            threading.Event().wait(0.01)
        return observations

    with ThreadPoolExecutor(max_workers=1) as readers:
        frontier_reader = readers.submit(poll_frontier_pages, job_id)
        assert product.call("job_status", job_id=job_id, limit=1)["counts"]["total"] == 1
        product.site.release_seed.set()
        assert product.site.slow_started.wait(timeout=10), (
            "Worker must execute the durable crawl"
        )
        poll_finished.set()
        assert frontier_reader.result(timeout=15) >= 1
    product.site.hold_crawl_seed = False
    product.stop(product.worker, kill=True)
    product.stop(product.api, kill=True)
    product.site.release_slow.set()
    product.start_api()
    repeated = product.call(
        "crawl",
        seed_url=product.site.url + "/crawl/start.html",
        max_pages=8,
        max_depth=3,
        max_seconds=30,
        render="never",
        idempotency_key="durable-crawl",
    )
    assert repeated["job_id"] == job_id
    product.start_worker()
    terminal = product.await_job(job_id, timeout=35)
    assert terminal["state"] == "partial", terminal
    assert terminal["manifest"], terminal
    assert terminal["counts"]["failed"] == 1
    assert terminal["counts"]["total"] == sum(
        value for key, value in terminal["counts"].items() if key != "total"
    )
    assert terminal["discovery"]["off_scope"] == 1
    assert terminal["discovery"]["duplicate"] >= 1
    assert product.site.requests.count("/crawl/start.html") == 1
    assert product.site.requests.count("/crawl/a") == 1
    assert "/outside" not in product.site.requests
    assert product.await_retrieval("DurableMarker", crawl_id=job_id)["results"]
    for outcome in terminal["manifest"]:
        if outcome.get("snapshot_id"):
            assert product.call("read", snapshot_id=outcome["snapshot_id"])["text"]

    product.site.slow_started.clear()
    product.site.release_slow.clear()
    cancel_job = product.call(
        "crawl",
        seed_url=product.site.url + "/crawl/start.html",
        max_pages=8,
        max_depth=3,
        max_seconds=30,
        render="never",
        idempotency_key="cancel-crawl",
    )["job_id"]
    assert product.site.slow_started.wait(timeout=10)
    cancelled = product.cli("job-cancel", cancel_job)
    assert cancelled["job_id"] == cancel_job
    poll_finished.clear()
    with ThreadPoolExecutor(max_workers=1) as readers:
        cancellation_reader = readers.submit(poll_frontier_pages, cancel_job)
        product.site.release_slow.set()
        cancellation = product.await_job(cancel_job)
        poll_finished.set()
        assert cancellation_reader.result(timeout=15) >= 1
    assert cancellation["state"] in {"cancelled", "canceled"}, cancellation
    assert product.await_retrieval("DurableMarker", crawl_id=cancel_job)["results"]
    assert product.cli("job-status", cancel_job)["state"] == cancellation["state"]
    bounded = product.cli(
        "crawl",
        product.site.url + "/crawl/start.html",
        "--pages",
        "2",
        "--depth",
        "3",
        "--seconds",
        "30",
        "--render",
        "never",
    )
    limit_stop = product.await_job(bounded["job_id"])
    assert limit_stop["stop_reason"] == "page_limit" and limit_stop["counts"]["total"] == 2

    # An invalid persisted request must be quarantined without starving a later
    # acknowledged job or discarding already published evidence from this crawl.
    product.stop(product.worker)
    healthy = product.call(
        "crawl",
        seed_url=product.site.url + "/reconnect/start.html",
        render="never",
        idempotency_key="healthy-after-corrupt-request",
    )["job_id"]
    product.stop(product.api)
    metadata = Path(product.env["DWS_DATA_DIR"]) / "management.sqlite3"
    with sqlite3.connect(metadata) as database:
        database.execute(
            "UPDATE dws_jobs SET request_json=?,state='queued',updated_at=0 WHERE job_id=?",
            (json.dumps({"seed_url": "x" * 5000}), job_id),
        )
    product.start_api()
    product.start_worker()
    assert product.await_job(healthy)["state"] == "succeeded"
    quarantined = product.call("job_status", job_id=job_id)
    assert quarantined["state"] == "partial"
    assert quarantined["stop_reason"] == "invalid_persisted_request"
    assert quarantined["request_error"]["code"] == "invalid_persisted_request"
    assert "invalid_persisted_request" in quarantined["warnings"]
    retained = next(row["snapshot_id"] for row in terminal["manifest"] if row["snapshot_id"])
    assert "DurableMarker" in product.cli("read", retained)["text"]


def test_access_outbound_resource_bounds_and_provider_failures(product: Product) -> None:
    status, response = product.request(
        "fetch", {"url": product.site.url + "/article"}, token=None
    )
    assert status == 401 and response["error"]["code"] == "authentication_required"
    connection = HTTPConnection("127.0.0.1", product.port, timeout=10)
    connection.request(
        "POST",
        "/v1/diagnostics",
        body=b"[" * 14000 + b"0" + b"]" * 14000,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer integration-owner-token",
        },
    )
    deep_json = connection.getresponse()
    deep_error = deep_json.read()
    assert 400 <= deep_json.status < 500 and json.loads(deep_error)["error"]["code"] == (
        "invalid_json"
    )
    assert len(deep_error) <= 65536
    connection.close()
    assert product.call("diagnostics")["write_admission"] == "available"
    status, response = product.request(
        "fetch",
        {"url": product.site.url + "/article"},
        headers={"Origin": "https://attacker.example"},
    )
    assert status == 403 and response["error"]["code"] == "local_access_only"
    for headers in ({"Origin": "http://["}, {"Host": "["}):
        status, response = product.request("diagnostics", {}, headers=headers)
        assert status == 403 and response["error"]["code"] == "local_access_only", response
    status, response = product.request(
        "diagnostics", {}, headers={"Authorization": "Bearer \u00e9"}
    )
    assert status == 401 and response["error"]["code"] == "authentication_required"
    with FixtureSite(product.directory / "collector") as collector:
        proxy_environment = {
            name: collector.url
            for name in (
                "HTTP_PROXY",
                "http_proxy",
                "HTTPS_PROXY",
                "https_proxy",
                "ALL_PROXY",
                "all_proxy",
            )
        }
        proxy_environment.update({"NO_PROXY": "", "no_proxy": ""})
        direct = product.cli("diagnostics", env_updates=proxy_environment)
        assert direct["retrieval_backend"] == "sqlite-fts5"
        assert not collector.requests, "The CLI must ignore ambient proxies carrying its bearer"
        product.site.redirect_target = collector.url
        redirected = product.run_cli(
            "--api-url",
            product.site.url + "/api-redirect",
            "diagnostics",
            env_updates=proxy_environment,
        )
        assert redirected.returncode == 1, (redirected.stdout, redirected.stderr)
        assert json.loads(redirected.stdout)["error"]["code"] == "api_redirect_denied"
        assert "/api-redirect/v1/diagnostics" in product.site.requests
        assert not collector.requests, "The API bearer must never reach a redirect collector"
        product.site.redirect_target = None
    status, response = product.request(
        "crawl", {"seed_url": product.site.url, "max_pages": 99999}
    )
    assert status == 422 and response["error"]["code"] == "invalid_request"
    product.stop(product.worker)
    job = product.call(
        "crawl", seed_url=product.site.url + "/reconnect/start.html", render="never"
    )["job_id"]
    signed_boundary = 2**63 - 1
    for operation, payload, arguments, result_key in (
        ("workspace_list", {}, ("workspace", "list"), "workspaces"),
        ("run_list", {}, ("run", "list"), "runs"),
        ("job_status", {"job_id": job}, ("job-status", job), "manifest"),
    ):
        status, response = product.request(
            operation, {**payload, "offset": signed_boundary + 1}
        )
        assert status == 422 and response["error"]["code"] == "invalid_request", response
        rejected = product.run_cli(*arguments, "--offset", str(signed_boundary + 1))
        assert rejected.returncode == 1
        assert json.loads(rejected.stdout)["error"]["code"] == "invalid_request"
        boundary = product.cli(*arguments, "--offset", str(signed_boundary))
        assert boundary[result_key] == []
    oversized_canonical = product.site.url + "/" + "証" * 1000
    metadata = Path(product.env["DWS_DATA_DIR"]) / "management.sqlite3"
    with sqlite3.connect(metadata) as database:
        admitted_before = database.execute("SELECT count(*) FROM dws_jobs").fetchone()[0]
    status, response = product.request("crawl", {"seed_url": oversized_canonical})
    assert status == 422 and response["error"]["code"] == "invalid_request", response
    rejected = product.run_cli("crawl", oversized_canonical)
    assert rejected.returncode == 1
    assert json.loads(rejected.stdout)["error"]["code"] == "invalid_request"
    with sqlite3.connect(metadata) as database:
        assert (
            database.execute("SELECT count(*) FROM dws_jobs").fetchone()[0] == admitted_before
        )
    product.call("job_cancel", job_id=job)
    assert product.call("diagnostics")["write_admission"] == "available"
    product.start_worker()
    for url, expected_status, code in (
        ("file:///etc/passwd", 400, "invalid_url"),
        ("http://169.254.169.254/latest/meta-data", 403, "policy_denied"),
        (product.site.url + "/redirect-denied", 403, "policy_denied"),
    ):
        status, response = product.request("fetch", {"url": url, "render": "never"})
        assert status == expected_status and response["error"]["code"] == code, response
    assert "/private-target" not in product.site.requests, (
        "Redirect denial must precede acquisition"
    )
    retained = product.call("fetch", url=product.site.url + "/article", render="never")
    retained_before_policy = product.call("read", snapshot_id=retained["snapshot_id"])["text"]
    with sqlite3.connect(metadata) as database:
        captured_before_policy = database.execute("SELECT count(*) FROM snapshots").fetchone()[
            0
        ]
    for literal in (
        "64:ff9b::7f00:1",
        "64:ff9b::a00:1",
        "64:ff9b::a9fe:a9fe",
        "64:ff9b:1::7f00:1",
        "fec0::1",
        "fec0:1234::42",
        "4000::1",
        "::ffff:0:127.0.0.1",
        "ff02::1",
        "224.0.0.1",
    ):
        authority = f"[{literal}]" if ":" in literal else literal
        encoded_private = f"http://{authority}/latest/meta-data"
        for operation, key in (("fetch", "url"), ("crawl", "seed_url")):
            status, response = product.request(
                operation, {key: encoded_private, "render": "never"}
            )
            assert status == 403 and response["error"]["code"] == "policy_denied", response
    with sqlite3.connect(metadata) as database:
        assert (
            database.execute("SELECT count(*) FROM dws_jobs").fetchone()[0] == admitted_before
        )
        assert (
            database.execute("SELECT count(*) FROM snapshots").fetchone()[0]
            == captured_before_policy
        )
    assert (
        product.call("read", snapshot_id=retained["snapshot_id"])["text"]
        == retained_before_policy
    )
    normal = product.call("fetch", url=product.site.url + "/article", render="never")
    assert "RevisionMarker" in product.call("read", snapshot_id=normal["snapshot_id"])["text"]
    partial_urls = [
        product.site.url + "/partial/" + kind for kind in ("plain", "html", "pdf", "delta")
    ]
    with sqlite3.connect(metadata) as database:
        before_partial = database.execute("SELECT count(*) FROM snapshots").fetchone()[0]
    for partial_url in partial_urls:
        status, response = product.request("fetch", {"url": partial_url, "render": "never"})
        assert status == 502 and response["error"]["code"] == "partial_response", response
        rejected = product.run_cli("fetch", partial_url, "--render", "never")
        assert rejected.returncode == 1, rejected.stdout
        assert json.loads(rejected.stdout)["error"]["code"] == "partial_response"
    incomplete = product.call("crawl", seed_url=partial_urls[0], render="never", max_pages=1)
    partial_job = product.await_job(incomplete["job_id"])
    assert partial_job["state"] == "failed" and partial_job["counts"]["succeeded"] == 0
    assert partial_job["counts"]["failed"] == 1
    assert partial_job["manifest"][0]["error_code"] == "partial_response"
    assert partial_job["manifest"][0]["snapshot_id"] is None
    assert partial_job["manifest"][0]["attempts"] <= 2
    partial_requests = [
        row
        for row in map(
            json.loads, (product.directory / "source-http.jsonl").read_text().splitlines()
        )
        if row["path"].startswith("/partial/")
    ]
    assert partial_requests and all(row["range"] is None for row in partial_requests)
    assert all(row["a_im"] is None for row in partial_requests)
    with sqlite3.connect(metadata) as database:
        assert (
            database.execute("SELECT count(*) FROM snapshots").fetchone()[0] == before_partial
        )
    healthy = product.call(
        "crawl",
        seed_url=product.site.url + "/reconnect/start.html",
        render="never",
        max_pages=1,
    )
    following = product.await_job(healthy["job_id"])
    assert following["state"] == "succeeded" and following["counts"]["succeeded"] == 1
    assert (
        "LostAckMarker"
        in product.call("read", snapshot_id=following["manifest"][0]["snapshot_id"])["text"]
    )
    assert (
        product.call("read", snapshot_id=normal["snapshot_id"])["text"]
        == retained_before_policy
    )
    mixed = product.call(
        "crawl",
        seed_url=product.site.url + "/partial/mixed/start.html",
        render="never",
        max_pages=3,
    )
    mixed_final = product.await_job(mixed["job_id"])
    assert mixed_final["state"] == "partial"
    assert mixed_final["counts"]["succeeded"] == 1 and mixed_final["counts"]["failed"] == 2
    seed = next(row for row in mixed_final["manifest"] if row["state"] == "succeeded")
    seed_read = product.call("read", snapshot_id=seed["snapshot_id"])
    assert "MixedCompletenessMarker" in seed_read["text"]
    for failed in (row for row in mixed_final["manifest"] if row["state"] == "failed"):
        assert failed["error_code"] == "partial_response"
        assert failed["snapshot_id"] is None and 1 <= failed["attempts"] <= 2
    with sqlite3.connect(metadata) as database:
        rejected_fragments = database.execute(
            "SELECT count(*) FROM snapshots WHERE requested_url IN (?,?)",
            (
                product.site.url + "/partial/mixed/range.html",
                product.site.url + "/partial/mixed/delta.html",
            ),
        ).fetchone()[0]
    assert rejected_fragments == 0
    mixed_hits = product.await_retrieval("MixedCompletenessMarker", crawl_id=mixed["job_id"])
    assert {hit["snapshot_id"] for hit in mixed_hits["results"]} == {seed["snapshot_id"]}
    for hit in mixed_hits["results"]:
        assert hit["text"] == seed_read["text"][hit["char_start"] : hit["char_end"]]
    assert not product.call(
        "retrieve", query="PartialHtmlMarker DeltaPatchMarker", crawl_id=mixed["job_id"]
    )["results"]
    for path, code, expected_status in (
        ("/oversized", "response_too_large", 413),
        ("/compressed-oversized", "response_too_large", 413),
        ("/blank.pdf", "extraction_failed", 422),
        ("/missing", "source_http_error", 502),
    ):
        status, response = product.request(
            "fetch", {"url": product.site.url + path, "render": "never"}
        )
        assert status == expected_status and response["error"]["code"] == code, response
    product.site.search_down = True
    status, response = product.request("search", {"query": "systems architecture"})
    assert status == 503 and response["error"]["code"] == "search_unavailable", response
    assert "results" not in response, (
        "A provider outage must not become a successful empty search"
    )
    product.stop(product.worker)
    product.stop(product.api)
    product.site.search_down = False
    product.site.deep_provider_json = True
    product.env["DWS_CRAWL4AI_URL"] = product.site.url
    product.start_api()
    retained_text = product.call("read", snapshot_id=normal["snapshot_id"])["text"]
    with sqlite3.connect(metadata) as database:
        captures_before = database.execute("SELECT count(*) FROM snapshots").fetchone()[0]
    status, bad_provider = product.request(
        "fetch", {"url": product.site.url + "/javascript", "render": "always"}
    )
    assert status == 502 and bad_provider["error"]["code"] == "invalid_provider_response", (
        bad_provider
    )
    status, bad_search = product.request("search", {"query": "malformed provider response"})
    assert status == 503 and bad_search["error"]["code"] == "search_unavailable", bad_search
    assert "results" not in bad_search
    with sqlite3.connect(metadata) as database:
        assert (
            database.execute("SELECT count(*) FROM snapshots").fetchone()[0] == captures_before
        )
    assert product.call("read", snapshot_id=normal["snapshot_id"])["text"] == retained_text

    product.site.deep_provider_json = False
    product.site.render_markdown_fixture = True
    for source_status in (206, 226):
        product.site.search_partial_status = source_status
        status, partial_search = product.request(
            "search", {"query": f"partial provider response {source_status}"}
        )
        assert status == 503 and partial_search["error"]["code"] == "search_unavailable", (
            partial_search
        )
        assert "results" not in partial_search
        rejected_search = product.run_cli(
            "search", f"partial provider response {source_status}"
        )
        assert rejected_search.returncode == 1
        assert json.loads(rejected_search.stdout)["error"]["code"] == "search_unavailable"
    product.site.search_partial_status = None
    with sqlite3.connect(metadata) as database:
        before_rendered_partial = database.execute("SELECT count(*) FROM snapshots").fetchone()[
            0
        ]
    for route in ("partial", "delta", "transport-partial", "transport-delta"):
        selected_url = product.site.url + f"/renderer/{route}.html"
        status, response = product.request("fetch", {"url": selected_url, "render": "always"})
        assert status == 502 and response["error"]["code"] == "partial_response", response
        rejected = product.run_cli("fetch", selected_url, "--render", "always")
        assert rejected.returncode == 1, rejected.stdout
        assert json.loads(rejected.stdout)["error"]["code"] == "partial_response"
        with sqlite3.connect(metadata) as database:
            assert (
                database.execute("SELECT count(*) FROM snapshots").fetchone()[0]
                == before_rendered_partial
            )
    renderer_receipts = []
    for mode in ("missing", "blank", "raw"):
        selected_url = product.site.url + f"/renderer/{mode}.html"
        rendered = product.cli("fetch", selected_url, "--render", "always")
        exact = product.cli("read", rendered["snapshot_id"])
        expected = (
            "# Rendered provenance\n\n"
            "ProviderMarkdownMarker supplied by the configured renderer."
            if mode == "raw"
            else "# Rendered provenance\n\n"
            "DomFallbackMarker retained rendered DOM passage: £ café."
        )
        assert exact["text"] == expected
        expected_prefix = (
            "crawl4ai/raw-markdown/1+" if mode == "raw" else "crawl4ai/rendered-html/1+"
        )
        assert rendered["normalizer"].startswith(expected_prefix), rendered
        assert "decode/utf-8/dom/1" in rendered["normalizer"].split("+"), rendered
        unavailable = "provider_markdown_unavailable_html_normalized"
        assert (unavailable in exact["warnings"]) == (mode != "raw"), exact
        folder = Path(product.env["DWS_DATA_DIR"]) / "artifacts" / rendered["snapshot_id"]
        raw = (folder / "source.bin").read_bytes()
        normalized = (folder / "normalized.txt").read_bytes()
        provenance = json.loads((folder / "provenance.json").read_text())
        assert raw == product.site.rendered_html.encode()
        assert normalized == expected.encode()
        for key, value in (
            ("provider", "crawl4ai"),
            ("normalizer", rendered["normalizer"]),
            ("raw_hash", hashlib.sha256(raw).hexdigest()),
            ("text_hash", hashlib.sha256(normalized).hexdigest()),
        ):
            assert provenance[key] == exact[key] == rendered[key] == value
        assert provenance["warnings"] == exact["warnings"]
        assert provenance["requested_url"] == provenance["final_url"] == selected_url
        renderer_receipts.append(
            {
                "mode": mode,
                "snapshot_id": rendered["snapshot_id"],
                "document_id": rendered["document_id"],
                "normalizer": provenance["normalizer"],
                "text_hash": provenance["text_hash"],
                "raw_hash": provenance["raw_hash"],
                "warnings": provenance["warnings"],
            }
        )
    product.start_worker()
    for receipt in renderer_receipts:
        marker = "ProviderMarkdownMarker" if receipt["mode"] == "raw" else "DomFallbackMarker"
        indexed = product.await_retrieval(marker, document_ids=[receipt["document_id"]])
        assert {row["snapshot_id"] for row in indexed["results"]} == {receipt["snapshot_id"]}
    assert product.call("read", snapshot_id=normal["snapshot_id"])["text"] == retained_text
    (product.directory / "renderer-provenance-receipt.json").write_text(
        json.dumps({"cases": renderer_receipts, "retained_read_unchanged": True}, indent=2)
    )
    (product.directory / "partial-response-receipt.json").write_text(
        json.dumps(
            {
                "static_formats": ["text/plain", "text/html", "application/pdf"],
                "no_range_requests": True,
                "no_delta_acceptance_requested": True,
                "static_response_statuses": [206, 226],
                "partial_job_id": incomplete["job_id"],
                "partial_job_state": partial_job["state"],
                "partial_job_snapshot": partial_job["manifest"][0]["snapshot_id"],
                "healthy_following_job_id": healthy["job_id"],
                "healthy_following_job_state": following["state"],
                "rendered_206_rejected": True,
                "provider_transport_206_rejected": True,
                "search_transport_206_unavailable_without_fallback": True,
                "provider_transport_statuses_rejected": [206, 226],
                "rendered_main_statuses_rejected": [206, 226],
                "search_transport_statuses_unavailable": [206, 226],
                "mixed_crawl_job_id": mixed["job_id"],
                "mixed_crawl_state": mixed_final["state"],
                "mixed_crawl_counts": mixed_final["counts"],
                "mixed_seed_snapshot_id": seed["snapshot_id"],
                "partial_sources_not_published": True,
                "retained_exact_read_unchanged": True,
            },
            indent=2,
        )
    )

    # Fail real owned writes/fsyncs inside an isolated API subprocess. No
    # production fault hook is exposed; the real source and CLI remain active.
    product.stop(product.worker)
    product.stop(product.api)
    product.start_api(script=CAPTURE_IO_API)
    assert product.call("pin", snapshot_id=normal["snapshot_id"], pinned=True)["pinned"]
    state = Path(product.env["DWS_DATA_DIR"])
    control = product.directory / "capture-io-control.json"
    io_receipts = []
    for mode, expected_status, expected_code, expected_errno in (
        ("write-enospc", 507, "disk_pressure", errno.ENOSPC),
        ("file-fsync-eio", 500, "artifact_write_failed", errno.EIO),
        ("publication-fsync-edquot", 507, "disk_pressure", errno.EDQUOT),
        ("write-unclassified", 500, "internal_error", None),
    ):
        url = product.site.url + "/scope/" + mode
        with sqlite3.connect(state / "management.sqlite3") as io_metadata:
            before_counts = {
                table: io_metadata.execute("SELECT count(*) FROM " + table).fetchone()[0]
                for table in ("documents", "snapshots", "capture_events", "index_outbox")
            }
        before_dirs = {
            category: sorted(item.name for item in (state / category).iterdir())
            for category in ("artifacts", "staging")
        }
        control.write_text(json.dumps({"mode": mode, "url": url}))
        status, failed = product.request(
            "fetch", {"url": url, "render": "never", "refresh": True}
        )
        assert status == expected_status and failed["error"]["code"] == expected_code, (
            mode,
            status,
            failed,
        )
        assert len(json.dumps(failed)) < 1024
        assert str(state) not in json.dumps(failed) and "Private owner" not in json.dumps(
            failed
        )
        cli_failed = product.run_cli("fetch", url, "--render", "never", "--refresh")
        assert cli_failed.returncode == 1, (mode, cli_failed.stdout, cli_failed.stderr)
        cli_error = json.loads(cli_failed.stdout)
        assert cli_error["error"]["code"] == expected_code, cli_error
        assert len(cli_failed.stdout) < 1024
        assert str(state) not in cli_failed.stdout + cli_failed.stderr
        assert "Private owner" not in cli_failed.stdout + cli_failed.stderr
        with sqlite3.connect(state / "management.sqlite3") as io_metadata:
            after_counts = {
                table: io_metadata.execute("SELECT count(*) FROM " + table).fetchone()[0]
                for table in before_counts
            }
        assert after_counts == before_counts, (mode, before_counts, after_counts)
        assert {
            category: sorted(item.name for item in (state / category).iterdir())
            for category in before_dirs
        } == before_dirs, mode
        assert product.call("gc", dry_run=True)["orphan_candidate_count"] == 0
        io_retained = product.call("read", snapshot_id=normal["snapshot_id"])
        assert io_retained["pinned"] and io_retained["text"] == retained_text
        events = [
            json.loads(line)
            for line in (product.directory / "capture-io-events.jsonl").read_text().splitlines()
            if json.loads(line)["mode"] == mode
        ]
        failure_kind = {
            "write-enospc": "write_failed",
            "file-fsync-eio": "file_fsync_failed",
            "publication-fsync-edquot": "publication_fsync_failed",
            "write-unclassified": "unclassified_write_failed",
        }[mode]
        injected = [event for event in events if event["kind"] == failure_kind]
        assert len(injected) == 2
        assert all(event["errno"] == expected_errno for event in injected)
        assert any(
            event["kind"] == "fsync_completed" and event["path"].endswith("/source.bin")
            for event in events
        )
        if mode == "publication-fsync-edquot":
            assert sum(event["kind"] == "write_completed" for event in events) == 8
            checkpoints = [
                event for event in events if event["kind"] == "renamed_before_failed_fsync"
            ]
            assert len(checkpoints) == 2
            assert all(not Path(event["path"]).exists() for event in checkpoints)
        control.write_text(json.dumps({"mode": ""}))
        recovered = product.cli("fetch", url, "--render", "never", "--refresh")
        recovered_read = product.call("read", snapshot_id=recovered["snapshot_id"])
        assert "Owner" + mode in recovered_read["text"]
        normalized = state / "artifacts" / recovered["snapshot_id"] / "normalized.txt"
        assert hashlib.sha256(normalized.read_bytes()).hexdigest() == recovered["text_hash"]
        io_retained = product.call("read", snapshot_id=normal["snapshot_id"])
        assert io_retained["pinned"] and io_retained["text"] == retained_text
        io_receipts.append(
            {
                "mode": mode,
                "injected_errno": expected_errno,
                "api_status": status,
                "error_code": expected_code,
                "cli_exit": cli_failed.returncode,
                "metadata_unchanged": True,
                "artifact_trees_unchanged": True,
                "retained_pinned_read_unchanged": True,
                "recovered_snapshot_id": recovered["snapshot_id"],
                "recovered_text_hash": recovered["text_hash"],
            }
        )
    (product.directory / "capture-io-receipt.json").write_text(
        json.dumps({"cases": io_receipts, "no_orphans": True}, indent=2)
    )


def test_owner_limits_lost_ack_reconnect_and_encoded_evidence(product: Product) -> None:
    product.stop(product.worker)
    product.stop(product.api)
    product.env.update(
        {
            "DWS_MAX_JOBS": "2",
            "DWS_MAX_RESPONSE_BYTES": "16384",
            "DWS_MAX_BYTES": "100000",
        }
    )
    product.start_api()
    known = product.cli("fetch", product.site.url + "/article", "--render", "never")
    queued = [
        product.call(
            "crawl",
            seed_url=product.site.url + f"/queue/{i}.html",
            render="never",
            idempotency_key=f"queue-slot-{i}",
        )
        for i in range(2)
    ]
    queue_status, queue_full = product.request(
        "crawl", {"seed_url": product.site.url + "/queue/third.html", "render": "never"}
    )
    assert queue_status == 429 and queue_full["error"]["code"] == "queue_full"
    assert product.cli("read", known["snapshot_id"])["text"]
    assert all(
        product.call("job_status", job_id=job["job_id"])["state"] == "queued" for job in queued
    )
    product.cli("job-cancel", queued[0]["job_id"])
    reopened = product.call(
        "crawl",
        seed_url=product.site.url + "/queue/reopened.html",
        render="never",
        idempotency_key="reopened-slot",
    )
    assert reopened["state"] == "queued"
    product.cli("job-cancel", queued[1]["job_id"])
    product.cli("job-cancel", reopened["job_id"])

    lost_payload = {
        "seed_url": product.site.url + "/reconnect/start.html",
        "render": "never",
        "idempotency_key": "caller-lost-acknowledgement",
        "max_pages": 2,
    }
    connection = HTTPConnection("127.0.0.1", product.port, timeout=10)
    connection.request(
        "POST",
        "/v1/crawl",
        body=json.dumps(lost_payload),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer integration-owner-token",
        },
    )
    acknowledgement = connection.getresponse()
    assert acknowledgement.status == 200
    acknowledgement.close()  # The client loses the body containing its job handle.
    connection.close()
    with sqlite3.connect(Path(product.env["DWS_DATA_DIR"]) / "management.sqlite3") as metadata:
        persisted = metadata.execute(
            "SELECT job_id FROM dws_jobs WHERE idempotency_key=?",
            (lost_payload["idempotency_key"],),
        ).fetchall()
    assert len(persisted) == 1
    recovered = product.call("crawl", **lost_payload)
    assert recovered["job_id"] == persisted[0][0]
    product.start_worker()
    reconnect = product.await_job(recovered["job_id"])
    assert reconnect["state"] == "succeeded" and reconnect["counts"]["succeeded"] == 1
    assert product.site.requests.count("/reconnect/start.html") == 1

    depth = product.call(
        "crawl",
        seed_url=product.site.url + "/crawl/start.html",
        max_depth=0,
        max_pages=8,
        render="never",
    )
    depth_stop = product.await_job(depth["job_id"])
    assert depth_stop["stop_reason"] == "depth_limit"
    assert depth_stop["counts"]["total"] == 1 and depth_stop["discovery"]["depth_limited"] > 0
    assert (
        "/crawl/a" not in product.site.requests and "/crawl/slow" not in product.site.requests
    )

    retry = product.call(
        "crawl",
        seed_url=product.site.url + "/retry/start.html",
        max_pages=4,
        max_depth=2,
        render="never",
    )
    retry_stop = product.await_job(retry["job_id"])
    assert retry_stop["state"] == "partial" and retry_stop["counts"]["succeeded"] == 1
    unavailable = next(
        row for row in retry_stop["manifest"] if row["url"].endswith("/retry/unavailable")
    )
    assert unavailable["state"] == "failed" and unavailable["attempts"] == 2
    assert product.site.requests.count("/retry/unavailable") == 2

    timed = product.call(
        "crawl",
        seed_url=product.site.url + "/budget/start.html",
        max_pages=4,
        max_depth=2,
        max_seconds=1,
        render="never",
    )
    assert product.site.budget_started.wait(timeout=10)
    time_stop = product.await_job(timed["job_id"], timeout=10)
    product.site.release_budget.set()
    assert time_stop["stop_reason"] == "time_limit" and time_stop["counts"]["succeeded"] == 1
    assert time_stop["limits"]["max_seconds"] == 1
    assert 0 < time_stop["updated_at"] - time_stop["started_at"] < 3
    preserved = next(
        row["snapshot_id"] for row in time_stop["manifest"] if row["state"] == "succeeded"
    )
    assert "TimeBudgetMarker" in product.cli("read", preserved)["text"]

    unicode_capture = product.cli("fetch", product.site.url + "/unicode", "--render", "never")
    connection = HTTPConnection("127.0.0.1", product.port, timeout=10)
    connection.request(
        "POST",
        "/v1/read",
        body=json.dumps({"snapshot_id": unicode_capture["snapshot_id"], "max_chars": 16000}),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer integration-owner-token",
        },
    )
    oversized = connection.getresponse()
    encoded = oversized.read()
    assert oversized.status == 413 and json.loads(encoded)["error"]["code"] == "output_limit"
    assert len(encoded) <= 16384
    connection.close()
    bounded = product.cli("read", unicode_capture["snapshot_id"], "--max-chars", "256")
    assert bounded["truncated"] is True and "証拠" in bounded["text"]


def test_interrupted_index_recreation_preserves_pinned_scoped_evidence(
    product: Product,
) -> None:
    workspace = product.call("workspace_create", name="interrupted-index-owner")["workspace_id"]
    captured = product.call(
        "fetch",
        url=product.site.url + "/scope/interrupted-index",
        workspace_id=workspace,
        render="never",
    )
    product.call("pin", snapshot_id=captured["snapshot_id"], workspace_id=workspace)
    original = product.call("read", snapshot_id=captured["snapshot_id"], workspace_id=workspace)
    assert product.await_retrieval("SharedMarker", workspace_id=workspace)["results"]
    selected_mode = os.environ.get("DWS_TEST_INDEX_MODE")
    modes = (selected_mode,) if selected_mode else ("rebuild", "missing-startup")
    for mode in modes:
        assert mode in {"rebuild", "missing-startup"}
        interrupted = product.interrupt_index_schema_commit(mode)
        assert interrupted["schema_committed"] is True and interrupted["index_rows"] == 0
        product.start_api()
        intact = product.call(
            "read", snapshot_id=captured["snapshot_id"], workspace_id=workspace
        )
        assert intact["pinned"] is True and intact["text"] == original["text"]
        assert intact["text_hash"] == original["text_hash"]
        pending = product.call("retrieve", query="SharedMarker", workspace_id=workspace)
        assert pending["partial"] is True and pending["index_state"] == "pending", pending
        assert pending["pending_snapshots"] == 1 and not pending["results"], pending
        assert interrupted["durable_pending_snapshots"] == 1
        assert interrupted["durable_outbox_rows"] == 1
        product.start_worker()
        recovered = product.await_retrieval("SharedMarker", workspace_id=workspace)
        assert {hit["snapshot_id"] for hit in recovered["results"]} == {captured["snapshot_id"]}
        for passage in recovered["results"]:
            assert (
                passage["text"] == original["text"][passage["char_start"] : passage["char_end"]]
            )
        assert not product.call("retrieve", query="SharedMarker")["results"]
    assert product.site.requests.count("/scope/interrupted-index") == 1

    product.stop(product.worker)
    acknowledged = product.call(
        "crawl",
        seed_url=product.site.url + "/reconnect/start.html",
        render="never",
        idempotency_key="survives-publication-crash",
    )["job_id"]
    for publication_window in ("staged", "renamed"):
        publication = product.interrupt_publication(publication_window, workspace)
        orphan = Path(publication["path"])
        assert publication["committed_snapshots"] == 0
        assert publication["files"] == [
            "mapping.json",
            "normalized.txt",
            "provenance.json",
            "source.bin",
        ]
        assert orphan.is_dir() and orphan.is_relative_to(product.directory)
        product.start_api()
        dry_run = product.cli("gc")
        assert dry_run["orphan_candidate_count"] == 1
        assert dry_run["orphan_removed_count"] == 0 and dry_run["orphan_bytes"] > 0
        assert dry_run["orphan_paths"] == [
            str(orphan.relative_to(Path(product.env["DWS_DATA_DIR"])))
        ]
        assert orphan.is_dir(), "Dry-run cleanup must preserve interrupted publication files"
        assert product.call("job_status", job_id=acknowledged)["state"] == "queued"
        retained = product.call(
            "read", snapshot_id=captured["snapshot_id"], workspace_id=workspace
        )
        assert retained["pinned"] is True and retained["text"] == original["text"]
        applied = product.cli("gc", "--apply")
        assert applied["orphan_candidate_count"] == 1
        assert applied["orphan_removed_count"] == 1 and not applied["cleanup_errors"]
        assert not orphan.exists()
        assert (
            product.call("read", snapshot_id=captured["snapshot_id"], workspace_id=workspace)[
                "text"
            ]
            == original["text"]
        )
    product.start_worker()
    assert product.await_job(acknowledged)["state"] == "succeeded"
    product.stop(product.worker)
    damaged = []
    for index in range(20):
        bad = product.call(
            "fetch",
            url=product.site.url + f"/scope/outbox-damaged-{index}",
            workspace_id=workspace,
            render="never",
        )
        bad_path = (
            Path(product.env["DWS_DATA_DIR"])
            / "artifacts"
            / bad["snapshot_id"]
            / "normalized.txt"
        )
        bad_path.chmod(0o600)
        bad_path.write_text("Owner fixture damaged retained normalized bytes.")
        damaged.append(bad["snapshot_id"])
    healthy = product.call(
        "fetch",
        url=product.site.url + "/scope/fairhealthy",
        workspace_id=workspace,
        render="never",
    )
    product.call("pin", snapshot_id=healthy["snapshot_id"], workspace_id=workspace)
    healthy_read = product.call(
        "read", snapshot_id=healthy["snapshot_id"], workspace_id=workspace
    )
    product.start_worker()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        indexed = product.call(
            "read", snapshot_id=healthy["snapshot_id"], workspace_id=workspace
        )
        if indexed["index_state"] == "ready":
            break
        assert product.worker is not None and product.worker.poll() is None
        threading.Event().wait(0.2)
    else:
        pytest.fail("Twenty failed outbox events starved the later healthy capture")
    visible = product.call("retrieve", query="Ownerfairhealthy", workspace_id=workspace)
    assert {hit["snapshot_id"] for hit in visible["results"]} == {healthy["snapshot_id"]}
    assert visible["partial"] is True and visible["pending_snapshots"] == 20
    for passage in visible["results"]:
        assert (
            passage["text"] == healthy_read["text"][passage["char_start"] : passage["char_end"]]
        )
    diagnostics = product.call("diagnostics")
    assert diagnostics["index_states"]["error"] == 20
    assert diagnostics["counts"]["index_outbox"] == 20
    bad_status, bad_read = product.request(
        "read", {"snapshot_id": damaged[0], "workspace_id": workspace}
    )
    assert bad_status == 500 and bad_read["error"]["code"] == "artifact_integrity"
    (product.directory / "outbox-fairness-receipt.json").write_text(
        json.dumps(
            {
                "damaged_snapshots": damaged,
                "healthy_snapshot_id": healthy["snapshot_id"],
                "healthy_index_state": "ready",
                "honest_failed_events": 20,
                "healthy_exact_passage_available": True,
            },
            indent=2,
        )
        + "\n"
    )


def test_literal_state_paths_backup_repair_and_missing_original(product: Product) -> None:
    product.stop(product.worker)
    product.stop(product.api)
    state = product.directory / "state # query? literal%20"
    product.env["DWS_DATA_DIR"] = str(state)
    product.start_api()
    product.start_worker()
    workspace = product.cli("workspace", "create", "literal-state-owner")["workspace_id"]
    run = product.call("run_create", workspace_id=workspace, name="literal-state-run")["run_id"]
    capture = product.call(
        "fetch",
        url=product.site.url + "/scope/literal-state",
        workspace_id=workspace,
        run_id=run,
        render="never",
    )
    snapshot = capture["snapshot_id"]
    product.call("pin", snapshot_id=snapshot, workspace_id=workspace)
    original = product.call("read", snapshot_id=snapshot, workspace_id=workspace)
    product.cli("index", "rebuild")
    passages = product.call(
        "retrieve", query="SharedMarker", workspace_id=workspace, run_id=run
    )
    assert not passages["partial"] and passages["index_state"] == "ready", passages
    assert {hit["snapshot_id"] for hit in passages["results"]} == {snapshot}
    for passage in passages["results"]:
        assert passage["text"] == original["text"][passage["char_start"] : passage["char_end"]]
    product.stop(product.worker)
    acknowledged = product.call(
        "crawl",
        seed_url=product.site.url + "/reconnect/start.html",
        workspace_id=workspace,
        run_id=run,
        render="never",
    )["job_id"]
    backup = product.cli("backup")
    assert Path(backup["path"]).parent == state / "backups"
    manifest_path = Path(backup["path"]) / "manifest.json"
    valid_manifest_bytes = manifest_path.read_bytes()
    valid_manifest = json.loads(valid_manifest_bytes)
    invalid_manifests: list[object] = [
        [],
        {**valid_manifest, "files": []},
        {**valid_manifest, "files": {"management.sqlite3": []}},
    ]
    try:
        for invalid_manifest in invalid_manifests:
            manifest_path.chmod(0o600)
            manifest_path.write_text(json.dumps(invalid_manifest))
            status, refusal = product.request("restore", {"backup_id": backup["backup_id"]})
            assert status == 422 and refusal["error"]["code"] == "invalid_backup", refusal
            still_pinned = product.call("read", snapshot_id=snapshot, workspace_id=workspace)
            assert still_pinned["pinned"] is True and still_pinned["text"] == original["text"]
            assert (
                product.call("job_status", job_id=acknowledged, workspace_id=workspace)["state"]
                == "queued"
            )
    finally:
        manifest_path.write_bytes(valid_manifest_bytes)
        manifest_path.chmod(0o444)
    exports_before = set((state / "exports").iterdir())
    backups_before = set((state / "backups").iterdir())
    raw = state / "artifacts" / snapshot / "source.bin"
    raw.unlink()
    assert (
        product.call("read", snapshot_id=snapshot, workspace_id=workspace)["text"]
        == original["text"]
    )
    assert product.call("retrieve", query="SharedMarker", workspace_id=workspace)["results"]
    failures = []
    for operation, payload in (
        ("export", {"snapshot_id": snapshot, "workspace_id": workspace}),
        ("backup", {}),
    ):
        connection = HTTPConnection("127.0.0.1", product.port, timeout=10)
        connection.request(
            "POST",
            "/v1/" + operation,
            body=json.dumps(payload),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer integration-owner-token",
            },
        )
        response = connection.getresponse()
        encoded = response.read()
        assert response.status == 503, (operation, response.status, encoded)
        error = json.loads(encoded)
        assert error["error"]["code"] == "artifact_unavailable", error
        assert str(state).encode() not in encoded and b"source.bin" not in encoded
        failures.append(
            {"operation": operation, "status": response.status, "code": error["error"]["code"]}
        )
        connection.close()
    assert set((state / "exports").iterdir()) == exports_before
    assert set((state / "backups").iterdir()) == backups_before
    restored = product.cli("restore", backup["backup_id"])
    assert restored["repaired_artifacts"] == 1 and raw.is_file()
    assert (
        product.call("job_status", job_id=acknowledged, workspace_id=workspace)["state"]
        == "queued"
    )
    assert product.call("read", snapshot_id=snapshot, workspace_id=workspace)["pinned"] is True
    exported = product.call("export", snapshot_id=snapshot, workspace_id=workspace)
    assert (Path(exported["path"]) / "source.bin").read_bytes() == raw.read_bytes()
    product.stop(product.api)
    product.start_api()
    after_restart = product.call(
        "retrieve", query="SharedMarker", workspace_id=workspace, run_id=run
    )
    assert {hit["snapshot_id"] for hit in after_restart["results"]} == {snapshot}
    assert (
        product.call("read", snapshot_id=snapshot, workspace_id=workspace)["text"]
        == original["text"]
    )
    assert not [
        path
        for path in product.directory.iterdir()
        if path.name.startswith("state") and path not in {state, product.directory / "state"}
    ]
    product.stop(product.api)
    before_failed_copy = set((state / "backups").iterdir())
    failed_copy = product.trace_copy("backup", fail=True)
    assert not failed_copy["ok"] and failed_copy["status"] == 503
    assert failed_copy["error"]["error"]["code"] == "artifact_unavailable"
    assert not any(event["kind"] == "acknowledged" for event in failed_copy["events"])
    assert set((state / "backups").iterdir()) == before_failed_copy
    durable_copy = product.trace_copy("backup")
    assert durable_copy["ok"]
    durable_backup = durable_copy["result"]
    destination = Path(durable_backup["path"])
    synced = {event["path"] for event in durable_copy["events"] if event["kind"] == "fsync"}
    assert durable_copy["events"][-1]["kind"] == "acknowledged"
    for copied in destination.rglob("*"):
        assert str(copied) in synced, copied
    assert str(destination) in synced and str(destination.parent) in synced

    fresh = product.directory / "fresh # query? literal%20"
    imported_backup = fresh / "backups" / durable_backup["backup_id"]
    imported_backup.parent.mkdir(parents=True, mode=0o700)
    fresh.chmod(0o700)
    shutil.copytree(destination, imported_backup)
    product.env["DWS_DATA_DIR"] = str(fresh)
    product.start_api()
    product.stop(product.api)
    failed_restore = product.trace_copy(
        "restore", backup_id=durable_backup["backup_id"], fail=True
    )
    assert not failed_restore["ok"] and failed_restore["status"] == 503
    assert not any(event["kind"] == "metadata_publish" for event in failed_restore["events"])
    assert not list((fresh / "artifacts").iterdir())
    with sqlite3.connect(fresh / "management.sqlite3") as database:
        assert database.execute("SELECT count(*) FROM snapshots").fetchone()[0] == 0
    durable_restore = product.trace_copy("restore", backup_id=durable_backup["backup_id"])
    assert durable_restore["ok"]
    events = durable_restore["events"]
    publication = next(
        index for index, event in enumerate(events) if event["kind"] == "metadata_publish"
    )
    synced_before_refs = {
        event["path"] for event in events[:publication] if event["kind"] == "fsync"
    }
    restored_artifacts = fresh / "artifacts" / snapshot
    for copied in restored_artifacts.iterdir():
        assert str(copied) in synced_before_refs, copied
    assert str(restored_artifacts) in synced_before_refs
    assert str(restored_artifacts.parent) in synced_before_refs
    product.start_api()
    restored_read = product.call("read", snapshot_id=snapshot, workspace_id=workspace)
    assert restored_read["pinned"] is True and restored_read["text"] == original["text"]
    assert restored_read["text_hash"] == original["text_hash"]
    assert (restored_artifacts / "source.bin").read_bytes() == raw.read_bytes()
    assert {
        hit["snapshot_id"]
        for hit in product.call(
            "retrieve", query="SharedMarker", workspace_id=workspace, run_id=run
        )["results"]
    } == {snapshot}
    assert (
        product.call("job_status", job_id=acknowledged, workspace_id=workspace)["state"]
        == "queued"
    )
    product.start_worker()
    assert product.await_job(acknowledged, workspace_id=workspace)["state"] == "succeeded"
    receipt = {
        "state": str(state),
        "snapshot_id": snapshot,
        "workspace_id": workspace,
        "run_id": run,
        "backup_id": backup["backup_id"],
        "job_id": acknowledged,
        "repaired_artifacts": 1,
        "missing_original_failures": failures,
        "unintended_sibling_databases": [],
        "fresh_restored_state": str(fresh),
        "copy_fsync_before_ack": True,
        "artifact_fsync_before_metadata_publication": True,
        "injected_fsync_failures_cleaned": True,
        "malformed_manifest_shapes_rejected_without_state_change": 3,
    }
    (product.directory / "literal-state-repair-receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n"
    )


def test_documentation_discovery_limits_html_bases_and_legacy_recovery(
    product: Product,
) -> None:
    product.stop(product.worker)
    product.stop(product.api)
    product.env["DWS_MAX_BYTES"] = "300000"
    product.start_api()
    product.start_worker()
    discovered = product.cli(
        "crawl",
        product.site.url + "/docs/truncated/start.html",
        "--pages",
        "5",
        "--seconds",
        "90",
        "--render",
        "never",
        "--idempotency-key",
        "discovery-limit-survives-restart",
    )["job_id"]
    assert product.site.discovery_started.wait(timeout=10)
    status = product.call("job_status", job_id=discovered)
    seed = next(row["snapshot_id"] for row in status["manifest"] if row["state"] == "succeeded")
    assert status["discovery_limited"] is True
    assert status["discovery"]["discovery_limited"] == 1
    assert "discovered_links_truncated" in status["warnings"]
    product.call("pin", snapshot_id=seed)
    saved = product.call("read", snapshot_id=seed)["text"]
    assert "DiscoveryLimitMarker" in saved
    product.stop(product.worker, kill=True)
    zero_observation = product.call(
        "crawl",
        seed_url=product.site.url + "/reconnect/start.html",
        render="never",
        idempotency_key="historical-zero-discovery",
    )["job_id"]
    product.stop(product.api)

    # Construct a genuine historical database/backup in this stopped fixture.
    # The current startup must recover the observation from retained captures.
    state = Path(product.env["DWS_DATA_DIR"])
    with sqlite3.connect(state / "management.sqlite3") as database:
        database.execute("ALTER TABLE dws_jobs DROP COLUMN discovery_limited_count")
    legacy = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from dws.config import Settings; from dws.store import Store; "
            "print(json.dumps(Store(Settings.from_env()).backup()))",
        ],
        cwd=PRODUCT,
        env=product.env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert legacy.returncode == 0, (legacy.stdout, legacy.stderr)
    backup = json.loads(legacy.stdout)
    with sqlite3.connect(Path(backup["path"]) / "management.sqlite3") as database:
        assert "discovery_limited_count" not in {
            row[1] for row in database.execute("PRAGMA table_info(dws_jobs)")
        }
    product.start_api()
    migrated = product.call("job_status", job_id=discovered)
    assert migrated["discovery"]["discovery_limited"] == 1
    assert product.call("read", snapshot_id=seed)["pinned"] is True
    restored = product.cli("restore", backup["backup_id"])
    assert restored["restored_snapshots"] >= 1
    assert product.call("job_status", job_id=discovered)["discovery"]["discovery_limited"] == 1
    assert product.call("job_status", job_id=zero_observation)["discovery"] == {
        "off_scope": 0,
        "depth_limited": 0,
        "duplicate": 0,
        "queue_limited": 0,
        "discovery_limited": 0,
    }
    assert product.call("read", snapshot_id=seed)["text"] == saved
    product.site.release_discovery.set()
    product.start_worker()
    terminal = product.await_job(discovered)
    assert terminal["state"] == "partial" and terminal["stop_reason"] == "discovery_limit"
    assert terminal["counts"]["succeeded"] == 2 and terminal["counts"]["total"] == 2
    assert terminal["discovery"]["discovery_limited"] == 1
    assert product.site.requests.count("/docs/truncated/start.html") == 1
    assert "/docs/truncated/late" not in product.site.requests
    assert product.await_retrieval("DiscoveryLimitMarker", crawl_id=discovered)["results"]
    assert product.await_job(zero_observation)["state"] == "succeeded"
    product.stop(product.worker)
    refusal_status, refusal = product.request("restore", {"backup_id": backup["backup_id"]})
    assert refusal_status == 409 and refusal["error"]["code"] == "restore_would_discard_state"
    assert product.call("job_status", job_id=discovered)["state"] == "partial"
    assert product.call("read", snapshot_id=seed)["text"] == saved
    product.start_worker()

    for label, child, scope in (
        ("relative", "/docs/relative/manual/intro.html", "same_path"),
        ("absolute", "/filings/Annual%20Report.pdf", "same_host"),
        ("invalid", "/docs/invalid/manual/intro.html", "same_path"),
    ):
        source = product.site.url + f"/docs/{label}/start.html"
        capture = product.cli("fetch", source, "--render", "never")
        exact = product.cli("read", capture["snapshot_id"])
        assert product.site.url + child in capture["links"]
        assert product.site.url + child in exact["text"]
        assert "html_base_url_applied" in capture["warnings"]
        if label == "invalid":
            assert "invalid_html_base_ignored" in capture["warnings"]
        crawl = product.call(
            "crawl", seed_url=source, scope=scope, max_pages=4, render="never"
        )["job_id"]
        complete = product.await_job(crawl)
        assert complete["state"] == "succeeded", complete
        acquired = next(
            row for row in complete["manifest"] if row["url"] == product.site.url + child
        )
        child_read = product.cli("read", acquired["snapshot_id"])
        if label == "absolute":
            assert "RevenueMarker" in child_read["text"]
            assert any(location["page"] == 1 for location in child_read["location_map"])
        else:
            assert "BaseChildMarker" in child_read["text"]
        assert child in product.site.requests
    private = product.call(
        "crawl", seed_url=product.site.url + "/docs/private/start.html", render="never"
    )["job_id"]
    private_stop = product.await_job(private)
    assert private_stop["counts"]["succeeded"] == 1
    assert private_stop["discovery"]["off_scope"] == 1
    assert not any(path.startswith("/private-base/") for path in product.site.requests)
    denied_status, denied = product.request(
        "fetch",
        {
            "url": f"http://localhost:{product.site.server.server_port}/private-base/secret.html",
            "render": "never",
        },
    )
    assert denied_status == 403 and denied["error"]["code"] == "policy_denied"
    versioned = product.call(
        "crawl", seed_url=product.site.url + "/docs/v1.0/", max_pages=4, render="never"
    )["job_id"]
    versioned_stop = product.await_job(versioned)
    assert versioned_stop["state"] == "succeeded"
    assert versioned_stop["scope"]["path_prefix"] == "/docs/v1.0"
    assert versioned_stop["counts"]["succeeded"] == 2
    assert versioned_stop["discovery"]["off_scope"] == 1
    assert "/docs/v1.0/intro.html" in product.site.requests
    assert "/docs/other/observer.html" not in product.site.requests
    for target, code in (("public", "scope_denied"), ("private", "policy_denied")):
        redirected = product.call(
            "crawl",
            seed_url=product.site.url + f"/docs/redirect/{target}/start.html",
            max_pages=4,
            render="never",
        )["job_id"]
        outcome = product.await_job(redirected)
        assert outcome["state"] == "partial" and outcome["counts"]["succeeded"] == 1
        failed = next(row for row in outcome["manifest"] if row["state"] == "failed")
        assert failed["error_code"] == code and failed["attempts"] == 1
        seed_capture = next(
            row["snapshot_id"] for row in outcome["manifest"] if row["state"] == "succeeded"
        )
        assert "RedirectScopeMarker" in product.cli("read", seed_capture)["text"]
        assert "/redirect-observer/evidence.html" not in product.site.requests
    direct_redirect = product.cli(
        "fetch", product.site.url + "/docs/redirect/public/child.html", "--render", "never"
    )
    assert direct_redirect["final_url"] == product.site.url + "/redirect-observer/evidence.html"
    assert "DirectRedirectMarker" in product.cli("read", direct_redirect["snapshot_id"])["text"]
    assert product.site.requests.count("/redirect-observer/evidence.html") == 1

    # A real HTTP provider fixture proves the returned final URL cannot publish
    # off-scope evidence. It does not simulate or claim browser navigation safety.
    product.stop(product.worker)
    product.stop(product.api)
    product.site.render_scope_fixture = True
    product.env["DWS_CRAWL4AI_URL"] = product.site.url
    product.start_api()
    product.start_worker()
    rendered = product.call(
        "crawl",
        seed_url=product.site.url + "/docs/render/start.html",
        max_pages=4,
        render="always",
    )["job_id"]
    rendered_stop = product.await_job(rendered)
    assert rendered_stop["state"] == "partial" and rendered_stop["counts"]["succeeded"] == 1
    rejected = next(row for row in rendered_stop["manifest"] if row["state"] == "failed")
    assert rejected["error_code"] == "scope_denied" and rejected["attempts"] == 1
    seed_capture = next(
        row["snapshot_id"] for row in rendered_stop["manifest"] if row["state"] == "succeeded"
    )
    assert "RenderedRedirectMarker" in product.cli("read", seed_capture)["text"]
    assert product.await_retrieval("RenderedRedirectMarker", crawl_id=rendered)["results"]
    assert not product.call("retrieve", query="OffScopeRenderedMarker", crawl_id=rendered)[
        "results"
    ]
    with sqlite3.connect(Path(product.env["DWS_DATA_DIR"]) / "management.sqlite3") as database:
        assert (
            database.execute(
                "SELECT count(*) FROM snapshots WHERE final_url=?",
                (product.site.url + "/render-observer/evidence.html",),
            ).fetchone()[0]
            == 0
        )
