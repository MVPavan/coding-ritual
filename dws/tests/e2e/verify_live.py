"""Exercise running DWS Compose with real public sources and an actual MCP client.

This is a standalone product journey, not a pytest unit suite. All receipts,
cache and temporary paths stay beneath the independent product's .runtime/.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Awaitable, Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx
import httpx2

PRODUCT = Path(__file__).resolve().parents[2]
TERMINAL = {"succeeded", "partial", "cancelled", "failed"}


def mcp_http_factory(endpoint: str) -> Callable[..., httpx2.AsyncClient]:
    """Ignore ambient proxies and bind MCP bearer requests to one trusted origin."""
    expected = httpx2.URL(endpoint)

    def factory(
        headers: dict[str, str] | None = None,
        timeout: httpx2.Timeout | None = None,
        auth: httpx2.Auth | None = None,
        *,
        follow_redirects: bool = False,
    ) -> httpx2.AsyncClient:
        # FastMCP passes True; it must not weaken this verifier's token boundary.
        del follow_redirects

        async def same_origin(request: httpx2.Request) -> None:
            actual = request.url
            if actual.userinfo or (actual.scheme, actual.host, actual.port) != (
                expected.scheme,
                expected.host,
                expected.port,
            ):
                raise RuntimeError("MCP request denied outside the configured local API origin")

        return httpx2.AsyncClient(
            headers=headers,
            timeout=timeout or httpx2.Timeout(30, read=120),
            auth=auth,
            trust_env=False,
            follow_redirects=False,
            event_hooks={"request": [same_origin]},
        )

    return factory


async def mcp_token_boundary(token: str) -> dict[str, Any]:
    """Use real local collectors to prove proxy bypass and cross-origin refusal."""
    from fastmcp import Client
    from fastmcp.client.transports import StreamableHttpTransport

    observations = {
        name: {"requests": 0, "bearer_seen": False}
        for name in ("endpoint", "redirect_target", "proxy")
    }
    redirect_url = ""

    def handler(name: str) -> type[BaseHTTPRequestHandler]:
        class Collector(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                observations[name]["requests"] += 1
                observations[name]["bearer_seen"] |= (
                    self.headers.get("Authorization") == "Bearer " + token
                )
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(min(length, 65536))
                self.send_response(307 if name == "endpoint" else 500)
                if name == "endpoint":
                    self.send_header("Location", redirect_url)
                self.send_header("Content-Length", "0")
                self.end_headers()

            def do_GET(self) -> None:
                self.do_POST()

            def log_message(self, format: str, *args: Any) -> None:
                pass

        return Collector

    servers = {
        name: ThreadingHTTPServer(("127.0.0.1", 0), handler(name)) for name in observations
    }
    threads = [
        threading.Thread(target=server.serve_forever, daemon=True)
        for server in servers.values()
    ]
    for thread in threads:
        thread.start()
    redirect_url = f"http://127.0.0.1:{servers['redirect_target'].server_port}/mcp/"
    endpoint = f"http://127.0.0.1:{servers['endpoint'].server_port}/mcp/"
    proxy = f"http://127.0.0.1:{servers['proxy'].server_port}"
    names = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
        "no_proxy",
    )
    saved = {name: os.environ.get(name) for name in names}
    failed = False
    try:
        for name in names:
            os.environ[name] = "" if name.lower() == "no_proxy" else proxy
        transport = StreamableHttpTransport(
            endpoint,
            headers={"Authorization": "Bearer " + token},
            httpx_client_factory=mcp_http_factory(endpoint),
        )
        try:
            async with Client(transport, cache=False, timeout=5, init_timeout=5):
                pass
        except Exception:
            failed = True
        assert failed, "Redirecting non-MCP endpoint unexpectedly initialized"
        assert (
            observations["endpoint"]["requests"] > 0 and observations["endpoint"]["bearer_seen"]
        ), "Configured endpoint was not contacted directly"
        assert observations["proxy"]["requests"] == 0, "Ambient proxy received a bearer request"
        assert observations["redirect_target"]["requests"] == 0, (
            "Cross-origin redirect target received a bearer request"
        )
        return {
            "proxy_requests": 0,
            "redirect_target_requests": 0,
            "configured_endpoint_contacted": True,
            "redirect_initialization_rejected": True,
        }
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        for server in servers.values():
            await asyncio.to_thread(server.shutdown)
            server.server_close()
        for thread in threads:
            thread.join(timeout=2)


def configuration() -> dict[str, str]:
    """Read local owner configuration as data; never execute or print its secrets."""
    values: dict[str, str] = {}
    path = PRODUCT / ".runtime/owner.env"
    if path.exists():
        for original in path.read_text().splitlines():
            line = original.removeprefix("export ").strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            words = shlex.split(value, comments=True)
            if words:
                values[key.strip()] = " ".join(words)
    if os.environ.get("DWS_TOKEN"):
        values["DWS_TOKEN"] = os.environ["DWS_TOKEN"]
    return values


async def verify(base: str, output: Path, token: str) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema_version": "1.0",
        "journey": "real_compose_public_sources_and_mcp",
        "passed": False,
        "started_at": time.time(),
        "checks": {},
        "limitations": [
            "Public provider availability and source content may change.",
            "This helper does not replace deterministic failure/restart/security journeys.",
        ],
    }
    owned_jobs: list[str] = []
    snapshots: dict[str, dict[str, Any]] = {}
    headers = {"Authorization": "Bearer " + token}

    def checkpoint() -> None:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")

    async def stage(name: str, action: Callable[[], Awaitable[dict[str, Any]]]) -> bool:
        started = time.monotonic()
        try:
            evidence = await action()
            result = {
                "passed": True,
                "seconds": round(time.monotonic() - started, 3),
                "evidence": evidence,
            }
        except Exception as error:
            # API/SDK failures remain explicit; bearer values never enter receipts/stdout.
            result = {
                "passed": False,
                "seconds": round(time.monotonic() - started, 3),
                "error_type": type(error).__name__,
                "error": str(error).replace(token, "[redacted]")[:1000],
            }
        receipt["checks"][name] = result
        checkpoint()
        print(
            json.dumps(
                {"check": name, "passed": result["passed"], "seconds": result["seconds"]}
            ),
            flush=True,
        )
        return bool(result["passed"])

    checkpoint()
    async with httpx.AsyncClient(
        base_url=base, headers=headers, trust_env=False, timeout=120
    ) as api:
        await stage("mcp_proxy_and_redirect_boundary", lambda: mcp_token_boundary(token))

        async def command(operation: str, payload: dict[str, Any]) -> dict[str, Any]:
            response = await api.post("/v1/" + operation, json=payload)
            response.raise_for_status()
            result = response.json()
            assert isinstance(result, dict) and "error" not in result, (
                "Invalid command response"
            )
            assert result.get("schema_version") == "1.0", "Command schema mismatch"
            return result

        workspace = (
            await command("workspace_create", {"name": "Live end-to-end verification"})
        )["workspace_id"]
        run = (
            await command(
                "run_create",
                {"workspace_id": workspace, "name": "Public sources and MCP parity"},
            )
        )["run_id"]
        receipt.update(workspace_id=workspace, run_id=run)
        checkpoint()

        for name, url, render in (
            ("static", "https://example.com/", "never"),
            (
                "pdf",
                "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf",
                "never",
            ),
            ("rendered", "https://quotes.toscrape.com/js/", "always"),
        ):

            async def acquire(
                name: str = name, url: str = url, render: str = render
            ) -> dict[str, Any]:
                captured = await command(
                    "fetch",
                    {"workspace_id": workspace, "run_id": run, "url": url, "render": render},
                )
                snapshots[name] = captured
                read = await command(
                    "read",
                    {
                        "workspace_id": workspace,
                        "snapshot_id": captured["snapshot_id"],
                        "max_chars": 6000,
                    },
                )
                assert len(read["text"].strip()) > 10, "Captured evidence is empty"
                assert read["location_map"], "Retained evidence has no location mapping"
                if name == "pdf":
                    assert "Dummy PDF" in read["text"], "Public PDF text was not extracted"
                if name == "rendered":
                    assert (
                        "Albert Einstein" in read["text"] and captured["provider"] == "crawl4ai"
                    ), "JavaScript-rendered evidence is absent"
                await command(
                    "pin", {"workspace_id": workspace, "snapshot_id": captured["snapshot_id"]}
                )
                return {
                    key: captured.get(key)
                    for key in (
                        "snapshot_id",
                        "provider",
                        "normalizer",
                        "text_hash",
                        "warnings",
                    )
                }

            await stage(name + "_acquisition", acquire)

        async def cli_read() -> dict[str, Any]:
            snapshot = snapshots["static"]["snapshot_id"]
            env = os.environ.copy()
            env.update(
                DWS_TOKEN=token,
                DWS_API_URL=base,
                PYTHONDONTWRITEBYTECODE="1",
                TMPDIR=str(output / "tmp"),
            )
            result = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-m", "dws", "read", snapshot, "--workspace", workspace],
                env=env,
                cwd=PRODUCT,
                capture_output=True,
                text=True,
                timeout=45,
            )
            assert result.returncode == 0, "Installed CLI command failed"
            value = json.loads(result.stdout)
            expected = await command(
                "read", {"workspace_id": workspace, "snapshot_id": snapshot}
            )
            assert (
                value["text"] == expected["text"]
                and value["location_map"] == expected["location_map"]
            ), "CLI/API retained evidence differs"
            return {
                "snapshot_id": snapshot,
                "text_chars": len(value["text"]),
                "api_parity": True,
            }

        await stage("installed_cli_read", cli_read)

        async def mcp_journey() -> dict[str, Any]:
            from fastmcp import Client
            from fastmcp.client.transports import StreamableHttpTransport

            transport = StreamableHttpTransport(
                base + "/mcp/",
                headers=headers,
                httpx_client_factory=mcp_http_factory(base + "/mcp/"),
            )
            invoked: set[str] = set()
            async with Client(transport, cache=False, timeout=120) as client:

                async def tool(name: str, **payload: Any) -> dict[str, Any]:
                    response = await client.call_tool(
                        name, {"workspace_id": workspace, **payload}
                    )
                    result = response.structured_content or response.data
                    assert (
                        isinstance(result, dict)
                        and "error" not in result
                        and result.get("schema_version") == "1.0"
                    ), "Invalid MCP tool response"
                    invoked.add(name)
                    return result

                names = {item.name for item in await client.list_tools()}
                expected_tools = {
                    "search",
                    "fetch",
                    "crawl",
                    "retrieve",
                    "read",
                    "job_status",
                    "job_cancel",
                }
                assert expected_tools <= names, "Required MCP tools are absent"
                discovery = await tool(
                    "search", query="SQLite FTS5 official documentation", limit=3
                )
                assert discovery["results"], (
                    "No live search results; provider availability is not verified"
                )
                captured = await tool(
                    "fetch", url="https://example.com/", run_id=run, render="never"
                )
                snapshot = captured["snapshot_id"]
                assert snapshot == snapshots["static"]["snapshot_id"], (
                    "MCP/API did not share retained cache"
                )
                read = await tool("read", snapshot_id=snapshot, max_chars=6000)
                expected = await command(
                    "read",
                    {"workspace_id": workspace, "snapshot_id": snapshot, "max_chars": 6000},
                )
                assert (
                    read["text"] == expected["text"]
                    and read["location_map"] == expected["location_map"]
                ), "MCP/API retained evidence differs"
                resource = await client.read_resource(
                    f"dws://workspace/{workspace}/snapshot/{snapshot}/content"
                )
                assert len(resource) == 1 and resource[0].text == read["text"], (
                    "Retained MCP resource differs"
                )
                deadline = time.monotonic() + 30
                while True:
                    retrieved = await tool(
                        "retrieve", query="Example Domain", run_id=run, max_chars=6000
                    )
                    if retrieved["results"] or time.monotonic() >= deadline:
                        break
                    await asyncio.sleep(1)
                assert retrieved["results"], "Worker did not index the acquired snapshot"
                expected = await command(
                    "retrieve",
                    {
                        "workspace_id": workspace,
                        "query": "Example Domain",
                        "run_id": run,
                        "max_chars": 6000,
                    },
                )
                assert retrieved["results"] == expected["results"], (
                    "MCP/API retrieved passages differ"
                )
                long_query_payload = {
                    "query": "zqvneverword " * 32 + "Example",
                    "run_id": run,
                    "document_ids": [captured["document_id"]],
                    "max_chars": 6000,
                }
                long_query_mcp = await tool("retrieve", **long_query_payload)
                long_query_api = await command(
                    "retrieve", {"workspace_id": workspace, **long_query_payload}
                )
                assert long_query_mcp["results"] and not long_query_mcp["partial"], (
                    "MCP silently discarded the matching thirty-third query term"
                )
                assert long_query_mcp["results"] == long_query_api["results"], (
                    "MCP/API long-query passages differ"
                )
                assert all(
                    passage["snapshot_id"] == snapshot for passage in long_query_mcp["results"]
                ), "Long-query retrieval crossed the requested document scope"
                for passage in retrieved["results"]:
                    assert (
                        passage["snapshot_id"] == snapshot
                        and passage["workspace_id"] == workspace
                    )
                    assert (
                        read["text"][passage["char_start"] : passage["char_end"]]
                        == passage["text"]
                    ), "Retrieved text does not match canonical offsets"

                async def submit(pages: int) -> dict[str, Any]:
                    submitted = await tool(
                        "crawl",
                        seed_url="https://quotes.toscrape.com/",
                        run_id=run,
                        scope="same_path",
                        max_pages=pages,
                        max_depth=2,
                        max_seconds=90,
                        render="never",
                        idempotency_key=uuid.uuid4().hex,
                    )
                    owned_jobs.append(submitted["job_id"])
                    return submitted

                async def status(job: str) -> dict[str, Any]:
                    return await tool("job_status", job_id=job, limit=20)

                crawled = await submit(2)
                job = crawled["job_id"]
                immediate = await status(job)
                expected = await command(
                    "job_status", {"workspace_id": workspace, "job_id": job, "limit": 20}
                )
                assert (
                    immediate["job_id"] == expected["job_id"]
                    and immediate["limits"] == expected["limits"]
                ), "Acknowledged job is not inspectable through both interfaces"
                deadline = time.monotonic() + 100
                while True:
                    final = await status(job)
                    if final["state"] in TERMINAL or time.monotonic() >= deadline:
                        break
                    await asyncio.sleep(1)
                assert (
                    final["state"] in {"succeeded", "partial"}
                    and final["counts"]["succeeded"] >= 1
                ), "Public bounded crawl did not acquire evidence"
                assert final["counts"]["total"] <= 2 and final["stop_reason"], (
                    "Crawl budget/stop reason is missing"
                )

                cancelling = (await submit(20))["job_id"]
                deadline = time.monotonic() + 45
                while True:
                    before = await status(cancelling)
                    if (
                        before["counts"]["succeeded"] >= 1
                        or before["state"] in TERMINAL
                        or time.monotonic() >= deadline
                    ):
                        break
                    await asyncio.sleep(0.5)
                assert (
                    before["state"] in {"queued", "running"}
                    and before["counts"]["succeeded"] >= 1
                ), "Partial-evidence cancellation could not be demonstrated"
                retained = {
                    row["snapshot_id"] for row in before["manifest"] if row["snapshot_id"]
                }
                cancelled = await tool("job_cancel", job_id=cancelling)
                residual_at_request = cancelled["residual_pages"]
                deadline = time.monotonic() + 45
                while cancelled["state"] != "cancelled" and time.monotonic() < deadline:
                    await asyncio.sleep(1)
                    cancelled = await status(cancelling)
                assert cancelled["state"] == "cancelled" and cancelled["cancel_requested"], (
                    "Cancellation was not acknowledged durably"
                )
                assert retained <= {
                    row["snapshot_id"] for row in cancelled["manifest"] if row["snapshot_id"]
                }, "Cancellation lost retained evidence"
                for identifier in retained:
                    assert (await tool("read", snapshot_id=identifier))["text"], (
                        "Cancelled job evidence is no longer readable"
                    )
                assert invoked == expected_tools, (
                    "Not every required MCP capability was exercised"
                )
                return {
                    "tools_invoked": sorted(invoked),
                    "search_provider": discovery["provider"],
                    "search_results": len(discovery["results"]),
                    "resource_exact": True,
                    "read_and_retrieve_api_parity": True,
                    "thirty_third_query_term_matches": True,
                    "canonical_offsets_match": True,
                    "bounded_crawl": {
                        "state": final["state"],
                        "stop_reason": final["stop_reason"],
                        "counts": final["counts"],
                    },
                    "cancellation": {
                        "state": cancelled["state"],
                        "counts": cancelled["counts"],
                        "residual_at_request": residual_at_request,
                        "preserved_readable_snapshots": len(retained),
                    },
                }

        await stage("mcp_seven_capabilities", mcp_journey)
        receipt["passed"] = all(check["passed"] for check in receipt["checks"].values())
        # A failed journey must not leave its own crawl running or affect unrelated jobs.
        if not receipt["passed"]:
            cleanup: list[dict[str, Any]] = []
            for job in owned_jobs:
                try:
                    state = await command(
                        "job_status", {"workspace_id": workspace, "job_id": job}
                    )
                    if state["state"] not in TERMINAL:
                        state = await command(
                            "job_cancel", {"workspace_id": workspace, "job_id": job}
                        )
                    cleanup.append({"job_id": job, "state": state["state"]})
                except Exception as error:
                    cleanup.append({"job_id": job, "error_type": type(error).__name__})
            receipt["cleanup"] = cleanup
    receipt["finished_at"] = time.time()
    checkpoint()
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8765")
    parser.add_argument(
        "--output-dir", type=Path, default=PRODUCT / ".runtime/verification-rerun/live"
    )
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((PRODUCT / ".runtime").resolve()):
        parser.error("--output-dir must remain beneath the product's .runtime directory")
    parsed = urlsplit(args.api_url)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username is not None
        or parsed.password is not None
    ):
        parser.error("--api-url must identify the trusted local running DWS API")
    output.mkdir(parents=True, exist_ok=True)
    for directory in ("tmp", "cache"):
        (output / directory).mkdir(exist_ok=True)
    os.environ.update(TMPDIR=str(output / "tmp"), XDG_CACHE_HOME=str(output / "cache"))
    token = configuration().get("DWS_TOKEN")
    if not token:
        parser.error("Set DWS_TOKEN or configure the product-local .runtime/owner.env")
    try:
        receipt = asyncio.run(verify(args.api_url.rstrip("/"), output, token))
    except Exception as error:
        path = output / "receipt.json"
        receipt = json.loads(path.read_text()) if path.exists() else {}
        receipt.update(
            passed=False,
            error_type=type(error).__name__,
            error=str(error).replace(token, "[redacted]")[:1000],
            finished_at=time.time(),
        )
        path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": receipt["passed"], "receipt": str(output / "receipt.json")}))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
