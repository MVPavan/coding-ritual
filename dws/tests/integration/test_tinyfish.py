"""Hosted-provider routing over real HTTP, shared state, and retained evidence."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import pytest
from fixture_site import FixtureSite

from dws.config import Settings
from dws.errors import DWSError
from dws.models import FetchRequest, SearchRequest
from dws.providers import Acquisition
from dws.store import Store

KEY = "sentinel-tinyfish-secret-do-not-leak"
PUBLIC = "https://example.com/challenge"


class TinySite:
    def __init__(self) -> None:
        self.mode = "ok"
        self.fetch_delay = 0.0
        self.honor_fetch_timeout = False
        self.url_error: dict[str, Any] | None = None
        self.links: list[str] | None = None
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.final = PUBLIC
        self.quota_path: Path | None = None
        self.unlocked: list[bool] = []
        site = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: object) -> None:
                pass

            def do_GET(self) -> None:
                self.respond(False)

            def do_POST(self) -> None:
                self.respond(True)

            def respond(self, fetch: bool) -> None:
                path = urlsplit(self.path).path
                if path == "/search":
                    body: Any = {"results": [{"url": PUBLIC, "title": "Fallback"}]}
                    status, headers = 200, {}
                else:
                    assert self.headers.get("X-API-Key") == KEY
                    assert self.headers.get("Accept") == "application/json"
                    args = (
                        json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                        if fetch
                        else parse_qs(urlsplit(self.path).query)
                    )
                    site.calls.append(("fetch" if fetch else "search", args))
                    if site.quota_path is not None:
                        with sqlite3.connect(site.quota_path, timeout=0.1) as conn:
                            try:
                                conn.execute("BEGIN IMMEDIATE")
                                site.unlocked.append(True)
                                conn.rollback()
                            except sqlite3.OperationalError:
                                site.unlocked.append(False)
                    status, headers = 200, {}
                    body = (
                        {
                            "results": [
                                {
                                    "url": args["urls"][0],
                                    "final_url": site.final,
                                    "title": "Hosted",
                                    "format": "markdown",
                                    "text": "# Hosted\n\nExact provider text.\n",
                                    "links": [{"url": "/next"}, {"url": "javascript:bad"}],
                                }
                            ],
                            "errors": [],
                        }
                        if fetch
                        else {
                            "query": "query",
                            "results": [
                                {
                                    "url": PUBLIC,
                                    "title": "Tiny",
                                    "snippet": "Hosted snippet",
                                    "date": "2026-10-04",
                                }
                            ],
                            "total_results": 1,
                            "page": 0,
                        }
                    )
                    if fetch and site.links is not None:
                        body["results"][0]["links"] = site.links
                    if fetch and site.fetch_delay:
                        delay = site.fetch_delay
                        if (
                            site.honor_fetch_timeout
                            and delay > args["per_url_timeout_ms"] / 1000
                        ):
                            delay = args["per_url_timeout_ms"] / 1000
                            body = {
                                "results": [],
                                "errors": [{"url": PUBLIC, "error": "timeout"}],
                            }
                        time.sleep(delay)
                    if site.mode == "slow":
                        time.sleep(0.8)
                    elif site.mode == "429":
                        status, headers = 429, {"Retry-After": "30"}
                        body = {"error": {"message": KEY}}
                    elif site.mode == "daily":
                        from datetime import UTC, datetime

                        status = 429
                        reset = datetime.fromtimestamp(time.time() + 120, UTC).isoformat()
                        body = {
                            "error": {
                                "code": "DAILY_LIMIT_EXCEEDED",
                                "details": {"resets_at": reset},
                            }
                        }
                    elif site.mode == "garbage":
                        headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "NaN"}
                    elif site.mode == "echo_secret":
                        body["results"][0]["title"] = KEY
                    elif site.mode == "remaining":
                        headers = {
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int(time.time()) + 30),
                        }
                    elif site.mode in {"500", "401", "403", "302"}:
                        status = int(site.mode)
                        headers = {"Location": site.url + "/leaked"}
                        body = {"error": KEY}
                    elif site.mode == "malformed":
                        body = "invalid-json " + KEY
                    elif site.mode == "missing":
                        body = {"unexpected": KEY}
                    elif site.mode == "url_error":
                        body = {
                            "results": [],
                            "errors": [{"url": PUBLIC, "error": "untrusted provider error"}],
                        }
                    if fetch and site.url_error is not None:
                        body = {"results": [], "errors": [{"url": PUBLIC, **site.url_error}]}
                raw = body.encode() if isinstance(body, str) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for name, value in headers.items():
                    self.send_header(name, value)
                self.end_headers()
                with suppress(BrokenPipeError, ConnectionResetError):
                    self.wfile.write(raw)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> TinySite:
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)


@pytest.fixture
def configured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    with TinySite() as site:
        for name, value in {
            "DATA_DIR": str(tmp_path),
            "TINYFISH_API_KEY": KEY,
            "TINYFISH_SEARCH_URL": site.url + "/tiny-search",
            "TINYFISH_FETCH_URL": site.url + "/tiny-fetch",
            "SEARXNG_URL": site.url,
            "DDGS_ENABLED": "false",
            "REQUEST_TIMEOUT": "2",
            "MIN_FREE_BYTES": "0",
            "ALLOWED_PRIVATE_HOSTS": "127.0.0.1",
        }.items():
            monkeypatch.setenv("DWS_" + name, value)
        site.quota_path = tmp_path / "tinyfish-quota.sqlite3"
        yield site


def search() -> dict[str, object]:
    return asyncio.run(Acquisition(Settings.from_env()).search(SearchRequest(query="query")))


def test_default_search(configured: TinySite) -> None:
    result = asyncio.run(
        Acquisition(Settings.from_env()).search(
            SearchRequest(query="query", domains=["example.com"])
        )
    )
    assert result["provider"] == "tinyfish"
    assert result["engine_path"]["attempts"] == [{"provider": "tinyfish", "reason": "served"}]
    assert result["results"][0]["date"] == "2026-10-04"
    assert result["freshness"] == "provider_claims_unverified"
    assert configured.calls[0][1]["include_domains"] == ["example.com"]
    assert configured.unlocked == [True]
    from pydantic import ValidationError

    settings = Settings.from_env()
    for endpoint in (
        "http://example.com/",
        "https://user:password@example.com/",
        "ftp://example.com/",
    ):
        with pytest.raises(ValidationError) as failure:
            Settings(tinyfish_api_key=KEY, tinyfish_search_url=endpoint)
        assert KEY not in str(failure.value) + repr(failure.value)
    assert KEY not in settings.model_dump_json() + repr(settings)


@pytest.mark.parametrize(
    ("limit", "reason"), [("MINUTE", "quota_minute"), ("HOUR", "quota_hour")]
)
def test_shared_quota(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch, limit: str, reason: str
) -> None:
    monkeypatch.setenv("DWS_TINYFISH_SEARCH_PER_" + limit, "1")
    assert search()["provider"] == "tinyfish"
    code = """import asyncio,json
from dws.config import Settings
from dws.providers import Acquisition
from dws.models import SearchRequest
print(json.dumps(asyncio.run(Acquisition(Settings.from_env()).search(SearchRequest(query='query')))))
"""
    child = subprocess.run(
        [sys.executable, "-c", code],
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=True,
    )
    result = json.loads(child.stdout)
    assert result["provider"] == "searxng"
    assert result["engine_path"]["attempts"] == [
        {"provider": "tinyfish", "reason": reason},
        {"provider": "searxng", "reason": "served"},
    ]
    assert len(configured.calls) == 1
    assert KEY not in child.stdout + child.stderr


@pytest.mark.parametrize("mode", ["429", "remaining"])
def test_server_cooldown(configured: TinySite, mode: str) -> None:
    configured.mode = mode
    assert search()["provider"] == ("tinyfish" if mode == "remaining" else "searxng")
    configured.mode = "ok"
    result = search()
    assert result["provider"] == "searxng"
    assert result["engine_path"]["attempts"][0]["reason"] == "server_cooldown"
    assert len(configured.calls) == 1


@pytest.mark.parametrize(
    ("mode", "reason"),
    [
        ("500", "unavailable"),
        ("slow", "unavailable"),
        ("malformed", "invalid_response"),
        ("missing", "invalid_response"),
        ("401", "auth_failed"),
        ("403", "auth_failed"),
        ("302", "unavailable"),
    ],
)
def test_failure_fallback(configured: TinySite, mode: str, reason: str) -> None:
    configured.mode = mode
    start = time.monotonic()
    result = search()
    assert result["provider"] == "searxng"
    assert result["engine_path"]["attempts"][0]["reason"] == reason
    assert time.monotonic() - start < 1.8
    assert len(configured.calls) == 1  # redirects must not carry the key onward
    assert KEY not in json.dumps(result)


@pytest.mark.parametrize(
    ("name", "value", "reason"),
    [("TINYFISH_API_KEY", "", "not_configured"), ("TINYFISH_ENABLED", "false", "disabled")],
)
def test_off(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch, name: str, value: str, reason: str
) -> None:
    monkeypatch.setenv("DWS_" + name, value)
    result = search()
    assert result["provider"] == "searxng"
    assert result["engine_path"]["attempts"][0]["reason"] == reason
    assert not configured.calls
    # Invalid header encoding must not expose credential bytes in exception reprs.
    monkeypatch.setenv("DWS_TINYFISH_ENABLED", "true")
    monkeypatch.setenv("DWS_TINYFISH_API_KEY", KEY + "é")
    invalid_key = search()
    assert invalid_key["provider"] == "searxng"
    assert invalid_key["engine_path"]["attempts"][0]["reason"] == "unavailable"
    assert KEY not in json.dumps(invalid_key)
    assert not configured.calls


def public_source(
    monkeypatch: pytest.MonkeyPatch, source: FixtureSite, path: str = "/challenge"
) -> Acquisition:
    """Use the real challenge HTTP fixture behind a public-source DNS test seam."""
    acquisition = Acquisition(Settings.from_env())
    original = acquisition._static
    from dws import providers

    resolve = providers.resolve_addresses

    async def addresses(host: str, port: int, allowed: tuple[str, ...]) -> list[str]:
        if host == "example.com":
            return ["93.184.216.34"]
        return await resolve(host, port, allowed)

    async def static(url: str, **kwargs: Any):
        # The fixture is the source transport seam; crawl policy still checks
        # the logical public URL before acquisition and the hosted final URL.
        kwargs["scope_check"] = None
        return await original(source.url + path, **kwargs)

    monkeypatch.setattr(providers, "resolve_addresses", addresses)
    monkeypatch.setattr(acquisition, "_static", static)
    return acquisition


def test_fetch_provenance_and_secrets(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        capture = asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert capture.provider == "tinyfish"
        assert capture.normalizer == "tinyfish/fetch-markdown/1"
        assert capture.raw == b"# Hosted\n\nExact provider text.\n"
        assert capture.text.encode() == capture.raw
        assert capture.content_type == "text/vnd.tinyfish.markdown"
        assert capture.links == ["https://example.com/next"]
        outbound = configured.calls[0][1].copy()
        assert 100 <= outbound.pop("per_url_timeout_ms") <= 1600
        assert outbound == {
            "urls": [PUBLIC],
            "format": "markdown",
            "links": True,
            "ttl": 3600,
            "include_etag_and_last_modified": False,
        }
        assert set(capture.warnings) >= {
            "provider_text_only_original_bytes_unavailable",
            "hosted_provider_acquisition",
            "escalated_from_challenge_page",
            "provider_cache_permitted",
        }
        store = Store(Settings.from_env())
        saved = store.save_capture(capture, "default", None)
        assert store.cached_fetch(FetchRequest(url=PUBLIC)) is not None
        assert store.cached_fetch(FetchRequest(url=PUBLIC, render="never")) is None
        assert store.cached_fetch(FetchRequest(url=PUBLIC, render="always")) is not None
        assert store.revalidation_candidate(FetchRequest(url=PUBLIC, max_age_seconds=0)) is None
        exported = store.export(saved["snapshot_id"], "default")
        assert (Path(exported["path"]) / "source.bin").read_bytes() == capture.raw
        diagnostic = store.diagnostics()
        assert diagnostic["tinyfish"]["configured"] is True
        assert diagnostic["tinyfish"]["fetch"]["windows"][0]["used"] == 1
        backup = store.backup()
        assert KEY not in repr(Settings.from_env())
        assert KEY not in Settings.from_env().model_dump_json()
        assert KEY not in json.dumps([saved, exported, diagnostic, backup]) + caplog.text
        for path in tmp_path.rglob("*"):
            if path.is_file():
                assert KEY.encode() not in path.read_bytes(), path
        assert not list((tmp_path / "backups").rglob("tinyfish-quota*"))


@pytest.mark.parametrize(
    ("setting", "value", "reason"),
    [
        ("TINYFISH_FETCH_ESCALATION", "false", "disabled"),
        ("TINYFISH_FETCH_PER_DAY", "1", "quota_day"),
        ("TINYFISH_FETCH_PER_MINUTE", "1", "quota_minute"),
    ],
)
def test_fetch_skips_keep_original(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch, setting: str, value: str, reason: str
) -> None:
    monkeypatch.setenv("DWS_" + setting, value)
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        if reason != "disabled":
            asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        count = len(configured.calls)
        with pytest.raises(DWSError) as failure:
            asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert failure.value.code == "challenge_page"
        assert failure.value.payload()["error"]["escalation"]["reason"] == reason
        assert len(configured.calls) == count


@pytest.mark.parametrize("case", ["never", "private", "scope", "url_error"])
def test_fetch_boundaries(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        configured.final = "https://example.com/outside" if case == "scope" else PUBLIC
        configured.mode = "url_error" if case == "url_error" else "ok"
        request = FetchRequest(
            url=source.url + "/challenge" if case == "private" else PUBLIC,
            render="never" if case == "never" else "auto",
        )
        with pytest.raises(DWSError) as failure:
            asyncio.run(
                acquisition.fetch(
                    request,
                    scope_check=lambda url: (
                        url != configured.final if case == "scope" else True
                    ),
                )
            )
        assert failure.value.code == "challenge_page"
        assert failure.value.payload()["error"]["escalation"]["reason"] == (
            "ineligible"
            if case in {"never", "private"}
            else "scope_denied"
            if case == "scope"
            else "unavailable"
        )
        assert len(configured.calls) == (1 if case in {"scope", "url_error"} else 0)
        assert KEY not in json.dumps(failure.value.payload()) + repr(failure.value)


def test_atomic_reservations(configured: TinySite, monkeypatch: pytest.MonkeyPatch) -> None:
    """Independent API-like clients race for one unit; only one may send HTTP."""
    from concurrent.futures import ThreadPoolExecutor

    monkeypatch.setenv("DWS_TINYFISH_SEARCH_PER_MINUTE", "1")
    code = """import asyncio,json
from dws.config import Settings
from dws.providers import Acquisition
from dws.models import SearchRequest
print(json.dumps(asyncio.run(Acquisition(Settings.from_env()).search(SearchRequest(query='query')))))
"""

    def run_client(_: int) -> str:
        child = subprocess.run(
            [sys.executable, "-c", code],
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=True,
        )
        assert KEY not in child.stdout + child.stderr
        return json.loads(child.stdout)["provider"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        providers = list(pool.map(run_client, range(4)))
    assert providers.count("tinyfish") == 1
    assert providers.count("searxng") == 3
    assert len(configured.calls) == 1
    quota = Settings.from_env().data_dir / "tinyfish-quota.sqlite3"
    quota.unlink()  # deliberate disposable-state reset, after all clients have exited
    assert search()["provider"] == "tinyfish"


def test_fetch_deadline_and_crawl_quota(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dws.jobs import Jobs
    from dws.models import CrawlRequest, JobRequest

    monkeypatch.setenv("DWS_REQUEST_TIMEOUT", "1")
    monkeypatch.setenv("DWS_TINYFISH_FETCH_PER_DAY", "1")
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        original = acquisition._static

        async def late_block(url: str, **kwargs: Any):
            await asyncio.sleep(0.7)
            return await original(url, **kwargs)

        monkeypatch.setattr(acquisition, "_static", late_block)
        configured.fetch_delay = 1.3  # longer than hosted budget -> ORIGINAL error survives
        with pytest.raises(DWSError) as failed:
            asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert failed.value.code == "challenge_page"
        assert failed.value.payload()["error"]["escalation"]["reason"] == "provider_timeout"
        assert len(configured.calls) == 1
        # Failed URLs counted toward the daily budget: a worker cannot send another.
        store = Store(Settings.from_env())
        jobs = Jobs(Settings.from_env(), store, acquisition)
        job = asyncio.run(jobs.submit(CrawlRequest(seed_url=PUBLIC, max_pages=1)))
        asyncio.run(jobs.tick())
        result = jobs.status(JobRequest(job_id=job["job_id"]))
        assert result["manifest"][0]["error_code"] == "challenge_page"
        assert result["manifest"][0]["escalation"]["reason"] == "quota_day"
        assert len(configured.calls) == 1
        # Reset accounting only for this isolated test's second deadline scenario.
        (Settings.from_env().data_dir / "tinyfish-quota.sqlite3").unlink()
        configured.mode = "ok"
        configured.fetch_delay = 0.3
        start = time.monotonic()
        capture = asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert capture.provider == "tinyfish"
        assert 1.0 < time.monotonic() - start < 1.5


@pytest.mark.parametrize(
    ("code", "status", "render", "eligible"),
    [
        ("source_http_error", 401, "auto", True),
        ("source_http_error", 403, "auto", True),
        ("source_http_error", 429, "auto", True),
        ("source_http_error", 451, "auto", True),
        ("source_http_error", 500, "auto", False),
        ("render_failed", None, "always", True),
        ("empty_content", None, "auto", False),
        ("response_too_large", None, "auto", False),
        ("scope_denied", None, "auto", False),
        ("source_timeout", None, "auto", False),
    ],
)
def test_escalation_trigger_matrix(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    code: str,
    status: int | None,
    render: str,
    eligible: bool,
) -> None:
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        original = DWSError(code, "Original source error", 502)
        original.source_status = status

        async def fail(*args: Any, **kwargs: Any):
            raise original

        monkeypatch.setattr(acquisition, "_static", fail)
        monkeypatch.setattr(acquisition, "_render", fail)
        if eligible:
            capture = asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC, render=render)))
            assert capture.provider == "tinyfish"
            assert "escalated_from_" + code in capture.warnings
        else:
            with pytest.raises(DWSError) as failure:
                asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC, render=render)))
            assert failure.value is original
            assert failure.value.payload()["error"]["escalation"]["reason"] == "ineligible"
        assert len(configured.calls) == int(eligible)


def test_render_required_and_timeout_boundary(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch
) -> None:
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)

        async def needs_render(*args: Any, **kwargs: Any):
            from dws.models import Capture

            return Capture(
                requested_url=PUBLIC,
                final_url=PUBLIC,
                content_type="text/html",
                text="shell",
                raw=b"shell",
                title="",
                normalizer="test",
                provider="httpx",
            ), True

        monkeypatch.setattr(acquisition, "_static", needs_render)
        capture = asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert capture.provider == "tinyfish"
        assert "escalated_from_render_required" in capture.warnings

        from dws.cli import _exit_code

        for mode, reason in (("500", "unavailable"), ("ok", "quota_day")):
            configured.mode = mode
            monkeypatch.setenv("DWS_TINYFISH_FETCH_PER_DAY", "1" if mode == "ok" else "1000")
            acquisition = public_source(monkeypatch, source)
            monkeypatch.setattr(acquisition, "_static", needs_render)
            with pytest.raises(DWSError) as skipped:
                asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
            assert (skipped.value.code, skipped.value.status) == ("render_unavailable", 503)
            assert (
                skipped.value.message == "Rendering is required but Crawl4AI is not configured"
            )
            assert skipped.value.payload()["error"]["escalation"]["reason"] == reason
            assert _exit_code(skipped.value.code, skipped.value.status) == 4
        calls = len(configured.calls)

        async def timed_out(*args: Any, **kwargs: Any):
            raise TimeoutError

        monkeypatch.setattr(acquisition, "_static", timed_out)
        with pytest.raises(DWSError) as failure:
            asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert failure.value.code == "source_timeout"
        assert len(configured.calls) == calls


def test_api_cli_mcp_worker_parity_and_secret_outputs(
    configured: TinySite, tmp_path: Path
) -> None:
    from test_product import Product

    directory = tmp_path / "product"
    directory.mkdir()
    with FixtureSite(directory / "source") as source:
        product = Product(directory, source)
        product.env["DWS_TINYFISH_FETCH_PER_DAY"] = "1"
        setup = f"""
import asyncio
import dws.providers as providers
from dws.providers import Acquisition
original_resolve = providers.resolve_addresses
original_static = Acquisition._static
async def addresses(host, port, allowed):
    if host == 'example.com':
        return ['93.184.216.34']
    return await original_resolve(host, port, allowed)
async def static(self, url, **kwargs):
    kwargs['scope_check'] = None
    return await original_static(self, {source.url + "/challenge"!r}, **kwargs)
providers.resolve_addresses = addresses
Acquisition._static = static
"""
        script = (
            setup
            + """
import sys,uvicorn
from dws.api import create_app
from dws.config import Settings
uvicorn.run(create_app(Settings.from_env()), host='127.0.0.1', port=int(sys.argv[1]))
"""
        )
        try:
            product.start_api(script=script)
            discovery = product.cli("search", "query")
            assert discovery["provider"] == "tinyfish"
            assert discovery["engine_path"]["attempts"][0]["reason"] == "served"
            captured = product.cli("fetch", PUBLIC)
            assert captured["provider"] == "tinyfish"
            snapshot = captured["snapshot_id"]
            outputs = [
                discovery,
                captured,
                product.cli("read", snapshot),
                product.cli("export", snapshot),
                product.call("diagnostics"),
                product.call("backup"),
            ]
            api_diagnostics = product.call("diagnostics")["tinyfish"]
            assert api_diagnostics == product.cli("diagnostics")["tinyfish"]
            assert api_diagnostics["search"]["windows"][0]["used"] == 1
            assert api_diagnostics["fetch"]["windows"][0]["used"] == 1
            job = product.call("crawl", seed_url=PUBLIC, max_pages=1)
            worker = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    setup + "\nfrom dws.worker import run\nfrom dws.config import Settings\n"
                    "asyncio.run(run(Settings.from_env(), once=True))",
                ],
                env=product.env,
                capture_output=True,
                text=True,
                check=True,
            )
            progress = product.call("job_status", job_id=job["job_id"])
            assert progress["manifest"][0]["error_code"] == "challenge_page"
            assert progress["manifest"][0]["escalation"]["reason"] == "quota_day"
            outputs.append(progress)
            # FastMCP uses the identical engine result and structured error payload.
            mcp_code = (
                setup
                + """
import json
from fastmcp import Client
from dws.config import Settings
from dws.engine import Engine
from dws.mcp_adapter import create_mcp
async def probe():
    async with Client(create_mcp(Engine(Settings.from_env()))) as client:
        result = await client.call_tool('search', {'query': 'query'})
        assert result.structured_content['provider'] == 'tinyfish'
        assert result.structured_content['engine_path']['attempts'][0]['reason'] == 'served'
        print(json.dumps(result.structured_content))
asyncio.run(probe())
"""
            )
            mcp = subprocess.run(
                [sys.executable, "-c", mcp_code],
                env=product.env,
                capture_output=True,
                text=True,
                check=True,
            )
            assert (
                KEY
                not in json.dumps(outputs)
                + worker.stdout
                + worker.stderr
                + mcp.stdout
                + mcp.stderr
            )
        finally:
            product.close()
        for path in directory.rglob("*"):
            if path.is_file():
                assert KEY.encode() not in path.read_bytes(), path


def test_ddgs_fallback_order(configured: TinySite, monkeypatch: pytest.MonkeyPatch) -> None:
    from dws import providers

    monkeypatch.setenv("DWS_DDGS_ENABLED", "true")
    acquisition = Acquisition(Settings.from_env())
    original = acquisition._provider_json

    async def unavailable(endpoint: str, method: str, **kwargs: Any):
        if endpoint.endswith("/search"):
            raise DWSError("provider_unavailable", "SearXNG failed", 503)
        return await original(endpoint, method, **kwargs)

    async def ddgs(*args: Any, **kwargs: Any):
        return {"results": [{"href": PUBLIC, "title": "DDGS"}]}

    monkeypatch.setattr(acquisition, "_provider_json", unavailable)
    monkeypatch.setattr(providers, "_helper", ddgs)
    configured.mode = "500"
    result = asyncio.run(acquisition.search(SearchRequest(query="query")))
    assert result["engine_path"]["attempts"] == [
        {"provider": "tinyfish", "reason": "unavailable"},
        {"provider": "searxng", "reason": "unavailable"},
        {"provider": "ddgs", "reason": "served"},
    ]
    assert set(result["warnings"]) >= {
        "searxng_unavailable",
        "fallback_upstream_independence_unverified",
    }


def test_rolling_windows_and_server_signal_parsing(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    monkeypatch.setenv("DWS_TINYFISH_SEARCH_PER_MINUTE", "1")
    monkeypatch.setenv("DWS_TINYFISH_SEARCH_PER_HOUR", "2")
    assert search()["provider"] == "tinyfish"
    from dws import tinyfish_quota

    now = time.time()
    clock = SimpleNamespace(time=lambda: now)
    monkeypatch.setattr(tinyfish_quota, "time", clock)
    assert search()["engine_path"]["attempts"][0]["reason"] == "quota_minute"
    now += 61
    assert search()["provider"] == "tinyfish"
    now += 61
    assert search()["engine_path"]["attempts"][0]["reason"] == "quota_hour"
    now += 3601
    assert search()["provider"] == "tinyfish"
    monkeypatch.undo()
    # Restore the original environment after undoing the clock/config patches.
    # The fixture itself still owns this fake server; settings are explicit here.
    settings = Settings(
        data_dir=configured.quota_path.parent,
        tinyfish_api_key=KEY,
        tinyfish_search_url=configured.url + "/tiny-search",
        tinyfish_fetch_url=configured.url + "/tiny-fetch",
        searxng_url=configured.url,
        ddgs_enabled=False,
    )
    acquisition = Acquisition(settings)
    configured.mode = "garbage"
    assert (
        asyncio.run(acquisition.search(SearchRequest(query="query")))["provider"] == "tinyfish"
    )
    assert (
        asyncio.run(acquisition.search(SearchRequest(query="query")))["provider"] == "tinyfish"
    )
    configured.mode = "echo_secret"
    result = asyncio.run(acquisition.search(SearchRequest(query="query")))
    assert result["provider"] == "searxng"
    assert result["engine_path"]["attempts"][0]["reason"] == "invalid_response"
    assert KEY not in json.dumps(result)


def test_daily_server_signal(configured: TinySite, monkeypatch: pytest.MonkeyPatch) -> None:
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        configured.mode = "daily"
        with pytest.raises(DWSError) as failure:
            asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert failure.value.code == "challenge_page"
        assert failure.value.payload()["error"]["escalation"]["reason"] == "rate_limited"
        configured.mode = "ok"
        with pytest.raises(DWSError) as failure:
            asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert failure.value.payload()["error"]["escalation"]["reason"] == "server_cooldown"
        assert len(configured.calls) == 1


@pytest.mark.parametrize("rendered", [False, True])
def test_blocked_status_transport(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch, rendered: bool
) -> None:
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        if rendered:
            source.render_markdown_fixture = True
            monkeypatch.setenv("DWS_CRAWL4AI_URL", source.url)
        for status in (401, 403, 429, 451, 500):
            acquisition = public_source(monkeypatch, source, path=f"/blocked/{status}")
            url = f"https://example.com/blocked/{status}" if rendered else PUBLIC
            request = FetchRequest(url=url, render="always" if rendered else "auto")
            # Fetch results must be associated with the URL submitted to the provider.
            configured.final = url
            if status == 500:
                with pytest.raises(DWSError) as failure:
                    asyncio.run(acquisition.fetch(request))
                assert failure.value.code == "source_http_error"
                assert failure.value.payload()["error"]["escalation"]["reason"] == "ineligible"
            else:
                capture = asyncio.run(acquisition.fetch(request))
                assert capture.provider == "tinyfish"
                assert "escalated_from_source_http_error" in capture.warnings
        assert len(configured.calls) == 4


@pytest.mark.parametrize("launcher", ["api", "worker"])
def test_real_cli_launchers_preserve_secrets(
    configured: TinySite, tmp_path: Path, launcher: str
) -> None:
    from test_product import Product

    directory = tmp_path / "real-product"
    directory.mkdir()
    with FixtureSite(directory / "source") as source:
        product = Product(directory, source)
        public_url = "http://93.184.216.34/challenge"
        configured.final = public_url
        configured.quota_path = directory / "state" / "tinyfish-quota.sqlite3"
        # Only the TCP transport maps a public test origin to its local fixture.
        # The real launchers, acquisition, address policy, and settings stay intact.
        seam = directory / "transport-seam"
        seam.mkdir()
        (seam / "sitecustomize.py").write_text(f"""
import httpcore
original_connect = httpcore.AnyIOBackend.connect_tcp
async def fixture_connect(self, host, port, *args, **kwargs):
    if host == '93.184.216.34' and port == 80:
        host, port = '127.0.0.1', {source.server.server_port}
    return await original_connect(self, host, port, *args, **kwargs)
httpcore.AnyIOBackend.connect_tcp = fixture_connect
""")
        product.env["PYTHONPATH"] = str(seam) + os.pathsep + os.environ.get("PYTHONPATH", "")
        outputs: list[dict[str, Any]] = []
        try:
            product.start_api()  # actual python -m dws api, without a custom launcher
            if launcher == "api":
                result = product.call("search", query="query")
                assert result["provider"] == "tinyfish"
                outputs.extend([result, product.cli("search", "query")])
            else:
                job = product.call("crawl", seed_url=public_url, max_pages=1)
                product.start_worker()  # actual python -m dws worker
                progress = product.await_job(job["job_id"])
                assert progress["counts"]["succeeded"] == 1, progress
                captured = product.cli("fetch", public_url)
                assert captured["provider"] == "tinyfish"
                assert "escalated_from_challenge_page" in captured["warnings"]
                assert [kind for kind, _ in configured.calls] == ["fetch"]
                outputs.extend(
                    [
                        progress,
                        captured,
                        product.cli("read", captured["snapshot_id"]),
                        product.cli("export", captured["snapshot_id"]),
                    ]
                )
            outputs.extend([product.call("diagnostics"), product.call("backup")])
            assert KEY not in json.dumps(outputs)
        finally:
            product.close()
        for path in directory.rglob("*"):
            if path.is_file():
                assert KEY.encode() not in path.read_bytes(), path


@pytest.mark.parametrize(
    ("field", "endpoint"),
    [
        ("tinyfish_search_url", "https://attacker.example/private-marker"),
        ("tinyfish_fetch_url", "https://api.search.tinyfish.ai/"),
        ("tinyfish_search_url", "https://api.fetch.tinyfish.ai/"),
        ("tinyfish_fetch_url", "https://api.fetch.tinyfish.ai:444/private-marker"),
        ("tinyfish_search_url", "https://api.search.tinyfish.ai.attacker.example/"),
    ],
)
def test_product_endpoint_allowlist(field: str, endpoint: str) -> None:
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as failure:
        Settings(**{field: endpoint}, tinyfish_api_key=KEY)
    assert endpoint not in str(failure.value) + repr(failure.value)
    assert KEY not in str(failure.value) + repr(failure.value)
    settings = Settings(
        tinyfish_api_key=KEY,
        tinyfish_search_url="https://api.search.tinyfish.ai:443/",
        tinyfish_fetch_url="https://api.fetch.tinyfish.ai/",
    )
    assert settings.tinyfish_search_url == "https://api.search.tinyfish.ai/"
    assert Settings(
        tinyfish_search_url="http://127.0.0.1:8123/"
    ).tinyfish_search_url.startswith("http:")
    assert Settings(tinyfish_fetch_url="http://[::1]:8123/").tinyfish_fetch_url.startswith(
        "http:"
    )


def test_hosted_link_truncation_finishes_crawl_as_partial(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dws.jobs import Jobs
    from dws.models import CrawlRequest, JobRequest

    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        configured.links = [f"https://outside.example/{i}" for i in range(2001)]
        store = Store(Settings.from_env())
        jobs = Jobs(Settings.from_env(), store, acquisition)
        job = asyncio.run(jobs.submit(CrawlRequest(seed_url=PUBLIC, max_pages=1)))
        assert asyncio.run(jobs.tick())
        result = jobs.status(JobRequest(job_id=job["job_id"]))
        assert (result["state"], result["stop_reason"]) == ("partial", "discovery_limit")
        assert result["discovery"]["discovery_limited"] == 1
        assert "discovered_links_truncated" in result["warnings"]


def test_provider_timeout_leaves_deadline_margin(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch
) -> None:
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        # A provider finishing at its advertised timeout still needs HTTP overhead.
        configured.fetch_delay = 0.01
        assert asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC))).provider == "tinyfish"
        provider_ms = configured.calls[0][1]["per_url_timeout_ms"]
        assert 100 <= provider_ms <= 1600  # DWS escalation budget is 2000ms


def test_cli_overrides_revalidate_without_losing_other_secrets(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import uvicorn

    from dws.cli import main

    captured: list[Settings] = []
    monkeypatch.setenv("DWS_CRAWL4AI_TOKEN", "sentinel-browser-secret")
    monkeypatch.setenv("DWS_TOKEN", "environment-owner")

    def capture_settings(app: Any, **kwargs: Any) -> None:
        captured.append(app.state.engine.settings)

    monkeypatch.setattr(uvicorn, "run", capture_settings)
    assert (
        main(
            [
                "--api-url",
                configured.url,
                "--token",
                "override-owner",
                "--data-dir",
                str(tmp_path / "overridden"),
                "api",
            ]
        )
        == 0
    )
    settings = captured[0]
    assert settings.tinyfish_api_key == KEY
    assert settings.crawl4ai_token == "sentinel-browser-secret"
    assert settings.token == "override-owner"
    assert settings.data_dir == tmp_path / "overridden"
    assert settings.api_url == configured.url
    assert KEY not in settings.model_dump_json() + repr(settings)


@pytest.mark.parametrize(
    ("fields", "ttl"),
    [
        ({}, 86400),
        ({"max_age_seconds": 17}, 17),
        ({"max_age_seconds": 3600}, 3600),
        ({"max_age_seconds": 0}, 0),
        ({"refresh": True}, 0),
        ({"refresh": True, "max_age_seconds": 17}, 0),
    ],
)
def test_fetch_ttl_policy_through_engine(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    fields: dict[str, Any],
    ttl: int,
) -> None:
    from dws.engine import Engine

    monkeypatch.setenv("DWS_TINYFISH_FETCH_TTL", "86400")
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        engine = Engine(Settings.from_env())
        engine.acquisition = public_source(monkeypatch, source)
        result = asyncio.run(engine.execute("fetch", {"url": PUBLIC, **fields}))
        assert configured.calls[0][1]["ttl"] == ttl
        assert ("provider_cache_permitted" in result["warnings"]) == (ttl > 0)


def test_cli_fetch_preserves_optional_age_and_allows_full_deadline(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from io import BytesIO

    from dws import cli

    seen: list[tuple[dict[str, Any], float]] = []

    class Response(BytesIO):
        status = 200

    class Opener:
        def open(self, request: Any, *, timeout: float) -> BytesIO:
            seen.append((json.loads(request.data), timeout))
            return Response(b"{}")

    monkeypatch.setenv("DWS_TOKEN", "owner-token")
    monkeypatch.setattr(cli, "build_opener", lambda *_args: Opener())
    assert cli.main(["fetch", PUBLIC]) == 0
    assert "max_age_seconds" not in seen[-1][0]
    # Group admission plus acquisition can each take 150s; allow response headroom.
    assert seen[-1][1] >= 330
    assert cli.main(["fetch", PUBLIC, "--max-age", "0", "--refresh"]) == 0
    assert seen[-1][0]["max_age_seconds"] == 0
    assert seen[-1][0]["refresh"] is True
    assert cli.main(["search", "query"]) == 0
    assert seen[-1][1] == 120
    assert KEY not in capsys.readouterr().out


def test_mcp_fetch_ttl_parity(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fastmcp import Client

    from dws.engine import Engine
    from dws.mcp_adapter import create_mcp

    monkeypatch.setenv("DWS_TINYFISH_FETCH_TTL", "86400")
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        engine = Engine(Settings.from_env())
        engine.acquisition = public_source(monkeypatch, source)

        async def run() -> None:
            async with Client(create_mcp(engine)) as client:
                for fields, ttl in [
                    ({}, 86400),
                    ({"max_age_seconds": 0}, 0),
                    ({"refresh": True}, 0),
                ]:
                    result = await client.call_tool("fetch", {"url": PUBLIC, **fields})
                    assert not result.is_error
                    assert configured.calls[-1][1]["ttl"] == ttl

        asyncio.run(run())


@pytest.mark.parametrize(
    ("crawl_seconds", "wait_for_slot"), [(None, False), (1, False), (3, False), (3, True)]
)
def test_longer_hosted_budget_and_crawl_deadlines(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    crawl_seconds: int | None,
    wait_for_slot: bool,
) -> None:
    from dws.jobs import Jobs
    from dws.models import CrawlRequest, JobRequest

    monkeypatch.setenv("DWS_REQUEST_TIMEOUT", "1")
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        local_started = asyncio.Event()
        release_local = asyncio.Event()
        if wait_for_slot:
            from contextlib import asynccontextmanager

            from dws import providers

            slot = providers.acquisition_slot

            @asynccontextmanager
            async def delayed_slot(settings: Settings):
                # A legitimate admission wait, within the slot's one-second limit.
                await asyncio.sleep(0.8)
                async with slot(settings):
                    yield

            monkeypatch.setattr(providers, "acquisition_slot", delayed_slot)

        async def delayed_block(url: str, **kwargs: Any):
            local_started.set()
            await release_local.wait()
            raise DWSError("challenge_page", "Fixture source requires a browser", 422)

        async def timed_attempt(operation: Any):
            # Control local phase duration; HTTP/parser startup must not consume
            # the unallocated 0.4s of this one-second local acquisition budget.
            task = asyncio.create_task(operation)
            timer = None
            try:
                async with asyncio.timeout(4):
                    await local_started.wait()
                    timer = asyncio.get_running_loop().call_later(0.6, release_local.set)
                    return await task
            finally:
                if timer is not None:
                    timer.cancel()
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

        monkeypatch.setattr(acquisition, "_static", delayed_block)
        configured.fetch_delay = 0.7  # exceeds the previous half-second hosted budget
        started = time.monotonic()
        if crawl_seconds is None:
            capture = asyncio.run(timed_attempt(acquisition.fetch(FetchRequest(url=PUBLIC))))
            assert capture.provider == "tinyfish"
        else:
            jobs = Jobs(Settings.from_env(), Store(Settings.from_env()), acquisition)
            job = asyncio.run(
                jobs.submit(
                    CrawlRequest(
                        seed_url=PUBLIC,
                        max_pages=1,
                        max_seconds=crawl_seconds,
                    )
                )
            )
            assert asyncio.run(timed_attempt(jobs.tick()))
            result = jobs.status(JobRequest(job_id=job["job_id"]))
            if crawl_seconds == 1:
                assert result["stop_reason"] == "time_limit"
                assert result["counts"]["succeeded"] == 0
                assert time.monotonic() - started < 1.4
            else:
                assert result["state"] == "succeeded"
                assert result["counts"]["succeeded"] == 1
        assert len(configured.calls) == 1
        assert 100 <= configured.calls[0][1]["per_url_timeout_ms"] <= 800
        assert acquisition.acquisition_timeout == 3
        capped = Acquisition(Settings(request_timeout=120, tinyfish_api_key=KEY))
        assert capped.tinyfish_fetch_budget == 25
        assert capped.acquisition_timeout == 150


def test_failed_claim_commit_does_not_start_crawl_deadline(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from dws import jobs as jobs_module
    from dws.jobs import Jobs
    from dws.models import CrawlRequest, JobRequest

    acquisition = Acquisition(Settings.from_env())
    store = Store(Settings.from_env())
    jobs = Jobs(Settings.from_env(), store, acquisition)
    job = asyncio.run(jobs.submit(CrawlRequest(seed_url=PUBLIC, max_pages=1, max_seconds=3)))
    request = JobRequest(job_id=job["job_id"])
    wall, elapsed = time.time(), time.monotonic()
    monkeypatch.setattr(
        jobs_module, "time", SimpleNamespace(time=lambda: wall, monotonic=lambda: elapsed)
    )
    connect = sqlite3.connect
    fail_commit = True

    class FailingCommit(sqlite3.Connection):
        def commit(self) -> None:
            nonlocal fail_commit
            if fail_commit:
                fail_commit = False
                raise sqlite3.OperationalError("Transient commit failure")
            super().commit()

    def hooked_connect(database: Any, **kwargs: Any):
        if database == store.metadata_path:
            kwargs["factory"] = FailingCommit
        return connect(database, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", hooked_connect)
    with pytest.raises(sqlite3.OperationalError, match="Transient commit failure"):
        asyncio.run(jobs.tick())
    rolled_back = jobs.status(request)
    assert rolled_back["state"] == "queued"
    assert rolled_back["started_at"] is rolled_back["deadline_at"] is None
    wall += 4
    elapsed += 4
    claim = jobs._claim()
    assert claim is not None  # An uncommitted claim cannot spend the job's budget.
    assert claim[0]["deadline_monotonic"] == elapsed + 3
    running = jobs.status(request)
    assert running["state"] == "running"
    assert running["started_at"] == wall
    assert running["deadline_at"] == wall + 3
    assert not configured.calls


@pytest.mark.parametrize(
    ("wall_step", "elapsed_step", "max_pages", "expected"),
    [
        (10, 0, 1, "succeeded"),
        (10, 0, 2, "succeeded"),
        (-10, 4, 1, "partial"),
        (-10, 2, 2, "partial"),
    ],
)
def test_crawl_deadline_uses_elapsed_time_across_clock_steps(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    wall_step: int,
    elapsed_step: int,
    max_pages: int,
    expected: str,
) -> None:
    from types import SimpleNamespace

    from dws import jobs as jobs_module
    from dws.jobs import Jobs
    from dws.models import CrawlRequest, JobRequest

    wall_start, elapsed_start = time.time(), time.monotonic()
    wall_offset = elapsed_offset = 0
    clock = SimpleNamespace(
        time=lambda: wall_start + time.monotonic() - elapsed_start + wall_offset,
        monotonic=lambda: time.monotonic() + elapsed_offset,
    )
    monkeypatch.setattr(jobs_module, "time", clock)
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        fetch = acquisition.fetch

        async def stepped_fetch(*args: Any, **kwargs: Any):
            nonlocal wall_offset, elapsed_offset
            capture = await fetch(*args, **kwargs)
            wall_offset = wall_step
            elapsed_offset += elapsed_step
            return capture

        monkeypatch.setattr(acquisition, "fetch", stepped_fetch)
        jobs = Jobs(Settings.from_env(), Store(Settings.from_env()), acquisition)

        async def run() -> dict[str, Any]:
            job = await jobs.submit(
                CrawlRequest(
                    seed_url=PUBLIC,
                    scope="same_path" if max_pages == 1 else "same_host",
                    max_pages=max_pages,
                    max_seconds=3,
                )
            )
            for page in range(max_pages):
                assert await jobs.tick()
                result = jobs.status(JobRequest(job_id=job["job_id"]))
                if page + 1 < max_pages:
                    assert result["state"] == "running", result
            return result

        result = asyncio.run(run())
        assert result["state"] == expected, result
        assert result["stop_reason"] == (
            "exhausted" if expected == "succeeded" else "time_limit"
        )
        assert result["counts"]["succeeded"] == max_pages
        assert len(configured.calls) == max_pages


@pytest.mark.parametrize(
    ("error", "reason", "status"),
    [
        ({"error": "timeout"}, "provider_timeout", None),
        ({"error": "target_http_error", "status": 429}, "target_blocked", 429),
        ({"error": "target_http_error", "status": True}, "target_blocked", None),
        ({"error": "target_http_error", "status": "429"}, "target_blocked", None),
        ({"error": "target_http_error", "status": 99}, "target_blocked", None),
        ({"error": "target_http_error", "status": 600}, "target_blocked", None),
        ({"error": "untrusted provider text"}, "unavailable", None),
    ],
)
def test_per_url_error_vocabulary_and_spent_quota(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    error: dict[str, Any],
    reason: str,
    status: int | None,
) -> None:
    monkeypatch.setenv("DWS_TINYFISH_FETCH_PER_DAY", "1")
    configured.url_error = error
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        with pytest.raises(DWSError) as failed:
            asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert (failed.value.code, failed.value.status) == ("challenge_page", 422)
        expected: dict[str, str | int] = {"provider": "tinyfish", "reason": reason}
        if status is not None:
            expected["target_status"] = status
        assert failed.value.payload()["error"]["escalation"] == expected
        assert KEY not in json.dumps(failed.value.payload())
        assert "untrusted provider text" not in str(failed.value.payload())
        with pytest.raises(DWSError) as exhausted:
            asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert exhausted.value.escalation["reason"] == "quota_day"
        assert len(configured.calls) == 1


def test_target_status_survives_crawl_manifest(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dws.jobs import Jobs
    from dws.models import CrawlRequest, JobRequest

    configured.url_error = {"error": "target_http_error", "status": 429}
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        jobs = Jobs(Settings.from_env(), Store(Settings.from_env()), acquisition)
        job = asyncio.run(jobs.submit(CrawlRequest(seed_url=PUBLIC, max_pages=1)))
        assert asyncio.run(jobs.tick())
        result = jobs.status(JobRequest(job_id=job["job_id"]))
        assert result["manifest"][0]["error_code"] == "challenge_page"
        assert result["manifest"][0]["escalation"] == {
            "provider": "tinyfish",
            "reason": "target_blocked",
            "target_status": 429,
        }
        assert KEY not in json.dumps(result)


@pytest.mark.parametrize(
    ("stage", "delay", "sent"),
    [
        ("validation", 0.5, True),
        ("reservation", 0.5, True),
        ("validation", 0.85, False),
        ("reservation", 0.85, False),
        ("post_reservation", 0.85, False),
        ("reservation", 1.1, False),
    ],
)
def test_hosted_timeout_uses_remaining_budget_and_skips_without_quota(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    stage: str,
    delay: float,
    sent: bool,
) -> None:
    monkeypatch.setenv("DWS_REQUEST_TIMEOUT", "1")
    monkeypatch.setenv("DWS_TINYFISH_FETCH_PER_DAY", "1")
    configured.honor_fetch_timeout = True
    configured.fetch_delay = 0.6
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        public_url = acquisition._tinyfish_public_url
        reserve = acquisition.tinyfish_quota.reserve

        async def delayed_validation(url: str) -> str:
            await asyncio.sleep(delay)
            return await public_url(url)

        def delayed_reservation(*args: Any, **kwargs: Any) -> str | None:
            if stage == "reservation":
                time.sleep(delay)
            reason = reserve(*args, **kwargs)
            if stage == "post_reservation":
                time.sleep(delay)
            return reason

        if stage == "validation":
            monkeypatch.setattr(acquisition, "_tinyfish_public_url", delayed_validation)
        else:
            monkeypatch.setattr(acquisition.tinyfish_quota, "reserve", delayed_reservation)
        with pytest.raises(DWSError) as failed:
            asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
        assert failed.value.code == "challenge_page"
        assert failed.value.escalation == {"provider": "tinyfish", "reason": "provider_timeout"}
        assert len(configured.calls) == int(sent)
        if sent:
            # Half the one-second budget is already gone, plus HTTP headroom.
            assert 100 <= configured.calls[0][1]["per_url_timeout_ms"] <= 400
        monkeypatch.setattr(acquisition, "_tinyfish_public_url", public_url)
        monkeypatch.setattr(acquisition.tinyfish_quota, "reserve", reserve)
        configured.fetch_delay = 0
        if sent:
            with pytest.raises(DWSError) as exhausted:
                asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC)))
            assert exhausted.value.escalation["reason"] == "quota_day"
        else:
            assert (
                asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC))).provider == "tinyfish"
            )
        assert len(configured.calls) == 1


def test_identical_fetch_waits_through_render_and_hosted_escalation(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from dws.engine import Engine

    monkeypatch.setenv("DWS_REQUEST_TIMEOUT", "1")
    configured.fetch_delay = 0.7
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        engine = Engine(Settings.from_env())
        engine.acquisition = public_source(monkeypatch, source)

        async def run() -> None:
            rendering = asyncio.Event()

            async def failed_render(*_args: Any, **_kwargs: Any):
                rendering.set()
                await asyncio.sleep(0.7)
                raise DWSError("render_failed", "Local rendering failed", 503)

            monkeypatch.setattr(engine.acquisition, "_render", failed_render)
            payload = {"url": PUBLIC, "render": "always"}
            first = asyncio.create_task(engine.execute("fetch", payload))
            await rendering.wait()
            results = await asyncio.gather(
                first,
                engine.execute("fetch", payload),
                return_exceptions=True,
            )
            assert all(isinstance(result, dict) for result in results), results
            assert results[0]["snapshot_id"] == results[1]["snapshot_id"]
            assert len(configured.calls) == 1

        asyncio.run(run())


def test_mcp_catalog_stays_seven_tools(configured: TinySite) -> None:
    from fastmcp import Client

    from dws.engine import Engine
    from dws.mcp_adapter import create_mcp

    async def run() -> None:
        async with Client(create_mcp(Engine(Settings.from_env()))) as client:
            tools = await client.list_tools()
            assert {tool.name for tool in tools} == {
                "search",
                "fetch",
                "crawl",
                "retrieve",
                "read",
                "job_status",
                "job_cancel",
            }

    asyncio.run(run())
    assert not configured.calls


def test_quota_reservation_commits_after_bounded_diagnostics_read(
    configured: TinySite, monkeypatch: pytest.MonkeyPatch
) -> None:
    from concurrent.futures import ThreadPoolExecutor

    from dws.tinyfish_quota import TinyFishQuota

    quota = TinyFishQuota(Settings.from_env())
    assert quota.reserve("search") is None
    read_started = threading.Event()
    commit_started = threading.Event()
    committed = threading.Event()
    connect = sqlite3.connect
    used = quota._used

    class WriterConnection(sqlite3.Connection):
        def commit(self) -> None:
            commit_started.set()
            super().commit()
            committed.set()

    def hooked_connect(database: Any, **kwargs: Any):
        if database == quota.path:
            kwargs["factory"] = WriterConnection
        return connect(database, **kwargs)

    def hold_read(conn: sqlite3.Connection, kind: Any, now: float, seconds: int) -> int:
        count = used(conn, kind, now, seconds)
        if not isinstance(conn, WriterConnection) and not read_started.is_set():
            # The SELECT acquired SHARED; let the real writer reach COMMIT first.
            read_started.set()
            assert commit_started.wait(1)
            time.sleep(0.08)
            assert not committed.is_set()
        return count

    monkeypatch.setattr(sqlite3, "connect", hooked_connect)
    monkeypatch.setattr(quota, "_used", hold_read)
    with ThreadPoolExecutor(max_workers=2) as pool:
        reader = pool.submit(quota.diagnostics)
        assert read_started.wait(1)
        writer = pool.submit(quota.reserve, "search")
        result = reader.result(timeout=2)
        assert writer.result(timeout=2) is None
    assert committed.is_set()
    assert result["accounting"] == "ok"
    assert result["search"]["windows"][0]["used"] == 1
    assert quota.diagnostics()["search"]["windows"][0]["used"] == 2
    assert not configured.calls


def test_quota_diagnostics_real_usage_cooldown_and_readonly(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from datetime import UTC, datetime

    assert search()["provider"] == "tinyfish"
    assert search()["provider"] == "tinyfish"
    with FixtureSite(Settings.from_env().data_dir / "source") as source:
        acquisition = public_source(monkeypatch, source)
        assert asyncio.run(acquisition.fetch(FetchRequest(url=PUBLIC))).provider == "tinyfish"
        configured.mode = "429"
        assert search()["provider"] == "searxng"
        path = acquisition.tinyfish_quota.path
        now = time.time()
        with sqlite3.connect(path) as db:
            db.executemany(
                "INSERT INTO reservations VALUES (?,?,?)",
                [
                    ("search", now - 61, 2),
                    ("search", now - 3601, 1000),
                    ("fetch", now - 86401, 1000),
                ],
            )
            db.execute("INSERT INTO cooldown VALUES (?,?)", ("fetch", now - 1))
        before = path.read_bytes()
        calls = len(configured.calls)
        # A RESERVED writer lock allows reads but would block attempted quota writes.
        with sqlite3.connect(path) as writer:
            writer.execute("BEGIN IMMEDIATE")
            result = Store(Settings.from_env()).diagnostics()["tinyfish"]
            writer.rollback()
        assert result["accounting"] == "ok"
        assert result["scope"] == "dws_reservations_only"
        assert result["search"]["windows"] == [
            {"window": "minute", "used": 3, "limit": 30, "remaining": 27},
            {"window": "hour", "used": 5, "limit": 500, "remaining": 495},
        ]
        assert result["fetch"]["windows"] == [
            {"window": "minute", "used": 1, "limit": 150, "remaining": 149},
            {"window": "day", "used": 1, "limit": 1000, "remaining": 999},
        ]
        cooldown = datetime.fromisoformat(result["search"]["cooldown_until"])
        assert cooldown.utcoffset() == datetime.now(UTC).utcoffset()
        assert cooldown.timestamp() > time.time()
        assert result["fetch"]["cooldown_until"] is None
        assert path.read_bytes() == before  # Includes old rows; reporting never prunes.
        assert len(configured.calls) == calls
        assert KEY not in json.dumps(result)


@pytest.mark.parametrize(
    ("key", "enabled", "fetch"), [(False, True, True), (True, False, True), (True, True, False)]
)
def test_quota_diagnostics_missing_database_and_flags(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    key: bool,
    enabled: bool,
    fetch: bool,
) -> None:
    monkeypatch.setenv("DWS_TINYFISH_API_KEY", KEY if key else "")
    monkeypatch.setenv("DWS_TINYFISH_ENABLED", str(enabled))
    monkeypatch.setenv("DWS_TINYFISH_FETCH_ESCALATION", str(fetch))
    monkeypatch.setenv("DWS_TINYFISH_SEARCH_PER_MINUTE", "2")
    monkeypatch.setenv("DWS_TINYFISH_FETCH_PER_DAY", "7")
    store = Store(Settings.from_env())
    path = store.root / "tinyfish-quota.sqlite3"
    assert not path.exists()
    result = store.diagnostics()["tinyfish"]
    assert (result["configured"], result["enabled"], result["fetch_escalation"]) == (
        key,
        enabled,
        fetch,
    )
    assert result["accounting"] == "ok"
    assert result["search"]["windows"][0]["limit"] == 2
    assert result["fetch"]["windows"][1]["limit"] == 7
    for operation in ("search", "fetch"):
        assert result[operation]["cooldown_until"] is None
        for window in result[operation]["windows"]:
            assert window["used"] == 0
            assert window["remaining"] == window["limit"]
    assert not list(store.root.glob("tinyfish-quota.sqlite3*"))
    assert not configured.calls
    assert KEY not in json.dumps(result)


@pytest.mark.parametrize("failure", ["corrupt", "locked", "permission"])
def test_quota_diagnostics_unavailable_preserves_other_diagnostics(
    configured: TinySite,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    from contextlib import ExitStack, closing

    store = Store(Settings.from_env())
    path = store.root / "tinyfish-quota.sqlite3"
    if failure == "corrupt":
        path.write_bytes(b"not a database")
    else:
        assert Acquisition(Settings.from_env()).tinyfish_quota.reserve("search") is None
    with ExitStack() as stack:
        if failure == "locked":
            writer = stack.enter_context(closing(sqlite3.connect(path)))
            writer.execute("BEGIN EXCLUSIVE")
        elif failure == "permission":
            connect = sqlite3.connect

            def denied(database: Any, **kwargs: Any):
                if str(database).startswith(path.as_uri()):
                    raise PermissionError(KEY)
                return connect(database, **kwargs)

            monkeypatch.setattr(sqlite3, "connect", denied)
        started = time.monotonic()
        result = store.diagnostics()
        assert time.monotonic() - started < 0.5
        assert result["status"] == "ok"
        assert result["metadata_integrity"] == "ok"
        assert result["tinyfish"]["accounting"] == "unavailable"
        assert result["tinyfish"]["configured"] is True
        for operation in ("search", "fetch"):
            for window in result["tinyfish"][operation]["windows"]:
                assert window["used"] is None
                assert window["remaining"] is None
        assert not configured.calls
        assert KEY not in json.dumps(result)
