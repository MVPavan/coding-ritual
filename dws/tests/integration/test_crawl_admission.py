"""Protected HTTP crawl admission with actual deadlines and acknowledged replay."""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
import uvicorn
from test_product import Product
from test_product import product as product

from dws.api import create_app
from dws.config import Settings


def test_crawl_validation_deadline_and_concurrently_acknowledged_replay(
    product: Product,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product.stop(product.worker)
    product.stop(product.api)
    monkeypatch.setenv("DWS_MCP_ENABLED", "false")
    app = create_app(
        Settings(
            data_dir=Path(product.env["DWS_DATA_DIR"]),
            token=product.env["DWS_TOKEN"],
            ddgs_enabled=False,
            min_free_bytes=0,
            allowed_private_hosts=("127.0.0.1",),
        )
    )
    entered = threading.Event()
    competitor_acknowledged = threading.Event()
    validation_calls = {"timeout": 0, "replay": 0}

    async def validate_with_deadline(url: str) -> str:
        if url.endswith("/admission-timeout"):
            validation_calls["timeout"] += 1
        else:
            validation_calls["replay"] += 1
            if validation_calls["replay"] != 1:
                return url
            entered.set()
            acknowledged = await asyncio.to_thread(competitor_acknowledged.wait, 5)
            assert acknowledged, "Concurrent submitter did not acknowledge its job"
        # Fault injection belongs to this isolated app's acquisition instance.
        # The deadline itself raises a real TimeoutError through the HTTP route.
        async with asyncio.timeout(0.02):
            await asyncio.sleep(1)
        raise AssertionError("Expected validation deadline did not expire")

    app.state.engine.acquisition.validate_url = validate_with_deadline
    listener = socket.socket()
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", product.port))
    server = uvicorn.Server(
        uvicorn.Config(
            app, host="127.0.0.1", port=product.port, log_level="critical", access_log=False
        )
    )
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started and time.monotonic() < deadline:
            assert thread.is_alive(), "Actual API stopped before readiness"
            threading.Event().wait(0.01)
        assert server.started, "Actual API did not become ready"
        timeout_payload = {
            "seed_url": product.site.url + "/admission-timeout",
            "idempotency_key": "timeout-without-ack",
            "render": "never",
        }
        unauthenticated, _ = product.request("crawl", timeout_payload, token=None)
        assert unauthenticated == 401
        assert validation_calls == {"timeout": 0, "replay": 0}
        timed_out, timeout_response = product.request("crawl", timeout_payload)
        assert timed_out == 504
        assert timeout_response == {
            "error": {
                "code": "source_timeout",
                "message": "Crawl source validation exceeded its deadline",
            }
        }
        with app.state.engine.store.connection() as db:
            after_timeout = db.execute("SELECT count(*) FROM dws_jobs").fetchone()[0]
        assert after_timeout == 0, "Failed source validation acknowledged a job"

        replay_payload = {
            "seed_url": product.site.url + "/admission-replay",
            "idempotency_key": "concurrently-acknowledged",
            "render": "never",
        }
        with ThreadPoolExecutor(max_workers=1) as executor:
            first = executor.submit(product.request, "crawl", replay_payload)
            assert entered.wait(5), "First submitter did not enter validation"
            second_status, second = product.request("crawl", replay_payload)
            assert second_status == 200
            competitor_acknowledged.set()
            recovered_status, recovered = first.result(timeout=5)
        assert recovered_status == 200
        assert recovered["job_id"] == second["job_id"]
        repeated_status, repeated = product.request("crawl", replay_payload)
        assert repeated_status == 200 and repeated["job_id"] == second["job_id"]
        assert validation_calls == {"timeout": 1, "replay": 2}
        with app.state.engine.store.connection() as db:
            jobs = db.execute("SELECT job_id,state FROM dws_jobs").fetchall()
            pages = db.execute("SELECT url,state,attempts FROM dws_frontier").fetchall()
        assert len(jobs) == 1 and jobs[0]["job_id"] == second["job_id"]
        assert jobs[0]["state"] == "queued"
        assert len(pages) == 1 and pages[0]["attempts"] == 0
        (product.directory / "crawl-admission-receipt.json").write_text(
            json.dumps(
                {
                    "transport": "real authenticated localhost HTTP",
                    "fault": "actual asyncio.timeout in test-owned Acquisition.validate_url",
                    "unauthenticated_status": unauthenticated,
                    "timeout_status": timed_out,
                    "timeout_response": timeout_response,
                    "jobs_after_unrecovered_timeout": after_timeout,
                    "concurrent_replay_status": recovered_status,
                    "concurrent_replay_same_job": True,
                    "repeated_replay_same_job": True,
                    "final_jobs": len(jobs),
                    "final_frontier_rows": len(pages),
                    "source_validation_calls": validation_calls,
                },
                indent=2,
            )
            + "\n"
        )
    finally:
        competitor_acknowledged.set()
        server.should_exit = True
        thread.join(timeout=8)
        listener.close()
    assert not thread.is_alive(), "Actual API did not stop cleanly"
