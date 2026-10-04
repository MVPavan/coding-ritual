"""Measure bounded mixed-operation bursts against isolated DWS processes and fixtures."""

from __future__ import annotations

import argparse
import fcntl
import json
import math
import os
import platform
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

PRODUCT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PRODUCT / "tests/integration"))
from fixture_site import FixtureSite  # noqa: E402
from test_product import Product  # noqa: E402
from verify_rendered_fixture import verify as verify_browser  # noqa: E402

BURSTS = (1, 5, 10, 20, 50)
OPERATIONS = ("fetch", "read", "retrieve", "search")
SLOTS = 4
ADMISSION = 6
CONTROL_P95_BOUND_MS = 2500
HTTP = build_opener(ProxyHandler({}))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return round(ordered[max(0, math.ceil(len(ordered) * fraction) - 1)], 1)


def request(product: Product, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
    start = time.perf_counter()
    outgoing = Request(
        product.url + "/v1/" + operation,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": "Bearer " + product.env["DWS_TOKEN"],
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        try:
            response = HTTP.open(outgoing, timeout=35)
        except HTTPError as error:
            response = error
        with response:
            status = response.status
            body = json.load(response)
            retry_header = response.headers.get("Retry-After")
        code = body.get("error", {}).get("code") if isinstance(body, dict) else None
        retry_body = (
            body.get("error", {}).get("retry_after_seconds") if isinstance(body, dict) else None
        )
        return {
            "operation": operation,
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "status": status,
            "code": code,
            "retry_after_header": retry_header,
            "retry_after_seconds": retry_body,
        }
    except Exception as error:
        return {
            "operation": operation,
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
            "status": 0,
            "code": type(error).__name__,
            "retry_after_header": None,
            "retry_after_seconds": None,
        }


def held_slots(directory: Path) -> int:
    occupied = 0
    for slot in range(SLOTS):
        path = directory / f"{slot}.lock"
        if not path.exists():
            continue
        descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                occupied += 1
            else:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
    return occupied


def summarize(samples: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for operation in (*OPERATIONS, "job_status", "job_cancel"):
        selected = [sample for sample in samples if sample["operation"] == operation]
        latencies = [sample["latency_ms"] for sample in selected]
        results[operation] = {
            "calls": len(selected),
            "p50_ms": percentile(latencies, 0.5) if latencies else None,
            "p95_ms": percentile(latencies, 0.95) if latencies else None,
            "max_ms": max(latencies) if latencies else None,
            "successes": sum(sample["status"] == 200 for sample in selected),
            "typed_429s": sum(sample["status"] == 429 for sample in selected),
            "other_errors": sum(sample["status"] not in {200, 429} for sample in selected),
        }
    return results


def verify(output: Path, *, static_only: bool = False) -> dict[str, Any]:
    output = output.resolve()
    if not output.is_relative_to(PRODUCT / ".runtime/verification"):
        raise ValueError("Output must be under .runtime/verification")
    output.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="concurrency-", dir=output))
    report: dict[str, Any] = {
        "passed": False,
        "started_at": datetime.now(UTC).isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "api_admission_limit": ADMISSION,
            "acquisition_slots": SLOTS,
            "fixture_delay_ms": 350,
            "control_p95_bound_ms": CONTROL_P95_BOUND_MS,
            "fixture_only": True,
            "owner_compose_modified": False,
        },
        "bursts": [],
        "artifact_directory": str(directory.relative_to(PRODUCT)),
    }
    try:
        with FixtureSite(directory) as site:
            product = Product(directory, site)
            product.env.update(
                {
                    "DWS_MAX_JOBS": str(ADMISSION),
                    "DWS_ACQUISITION_SLOTS": str(SLOTS),
                    "DWS_REQUEST_TIMEOUT": "30",
                }
            )
            try:
                product.start_api()
                product.start_worker()
                captured = product.call("fetch", url=site.url + "/article", render="never")
                product.await_retrieval("SharedMarker", document_ids=[captured["document_id"]])
                for callers in BURSTS:
                    site.qualification_started.clear()
                    site.qualification_release.clear()
                    with site._lock:
                        site.qualification_peak = 0
                    job = product.call(
                        "crawl",
                        seed_url=site.url + f"/qualification/crawl-{callers}",
                        render="never",
                        max_pages=1,
                        max_depth=0,
                        max_seconds=30,
                    )["job_id"]
                    if not site.qualification_started.wait(timeout=15):
                        raise AssertionError("Worker did not start the fixture crawl")
                    samples: list[dict[str, Any]] = []
                    peak_held = [0]
                    stop = threading.Event()
                    start = threading.Event()

                    def sample_slots(
                        stop_event: threading.Event = stop,
                        peak: list[int] = peak_held,
                    ) -> None:
                        while not stop_event.wait(0.01):
                            peak[0] = max(
                                peak[0],
                                held_slots(
                                    Path(product.env["DWS_DATA_DIR"]) / "acquisition-slots"
                                ),
                            )

                    sampler = threading.Thread(target=sample_slots, daemon=True)
                    sampler.start()

                    def workload(
                        operation: str,
                        index: int,
                        ready: threading.Event = start,
                        burst: int = callers,
                    ) -> dict[str, Any]:
                        ready.wait()
                        if operation == "fetch":
                            payload = {
                                "url": site.url + f"/qualification/item-{burst}-{index}",
                                "render": "never",
                                "refresh": True,
                            }
                        elif operation == "read":
                            payload = {"snapshot_id": captured["snapshot_id"]}
                        elif operation == "retrieve":
                            payload = {
                                "query": "SharedMarker",
                                "limit": 1,
                                "document_ids": [captured["document_id"]],
                            }
                        else:
                            payload = {"query": f"qualification {burst} {index}"}
                        return request(product, operation, payload)

                    try:
                        with ThreadPoolExecutor(max_workers=callers) as pool:
                            futures = [
                                pool.submit(workload, operation, index)
                                for index in range(callers)
                                for operation in OPERATIONS
                            ]
                            start.set()
                            for _ in range(5):
                                samples.append(request(product, "job_status", {"job_id": job}))
                                time.sleep(0.03)
                            cancel = request(product, "job_cancel", {"job_id": job})
                            samples.append(cancel)
                            for _ in range(10):
                                if cancel["status"] == 200:
                                    break
                                time.sleep(0.05)
                                cancel = request(product, "job_cancel", {"job_id": job})
                                samples.append(cancel)
                            samples.extend(
                                future.result(timeout=40) for future in as_completed(futures)
                            )
                    finally:
                        site.qualification_release.set()
                        stop.set()
                        sampler.join(timeout=2)
                    product.await_job(job, timeout=15)
                    metrics = summarize(samples)
                    with site._lock:
                        peak_fixture = site.qualification_peak
                    for sample in samples:
                        if sample["status"] == 429:
                            assert sample["code"] in {
                                "busy",
                                "acquisition_busy",
                                "retrieval_busy",
                                "queue_full",
                            }, sample
                            assert sample["retry_after_header"] == "1", sample
                            assert sample["retry_after_seconds"] == 1, sample
                    assert all(sample["status"] in {200, 429} for sample in samples), samples
                    assert metrics["job_status"]["successes"] > 0, metrics
                    assert metrics["job_cancel"]["successes"] > 0, metrics
                    assert metrics["job_status"]["p95_ms"] < CONTROL_P95_BOUND_MS, metrics
                    assert metrics["job_cancel"]["p95_ms"] < CONTROL_P95_BOUND_MS, metrics
                    assert 1 <= peak_held[0] <= SLOTS, peak_held
                    assert 1 <= peak_fixture <= SLOTS, peak_fixture
                    report["bursts"].append(
                        {
                            "callers": callers,
                            "workload_calls": 4 * callers,
                            "metrics": metrics,
                            "peak_held_acquisition_slots": peak_held[0],
                            "peak_fixture_acquisitions": peak_fixture,
                            "configured_slots": SLOTS,
                        }
                    )
            finally:
                site.qualification_release.set()
                product.close()
        if not static_only:
            browser_output = output / "browser"
            if verify_browser(browser_output, concurrency_probe=True) != 0:
                raise AssertionError("Isolated real-browser control probe failed")
            browser = json.loads((browser_output / "receipt.json").read_text())
            report["browser"] = {
                "passed": browser["passed"],
                "provider": browser["provider"],
                "job_controls": browser["browser_control"],
                "artifact_directory": str(browser_output.relative_to(PRODUCT)),
                "isolated_containers_cleaned": all(
                    item["removed"] for item in browser["cleanup"]
                ),
            }
        report["passed"] = True
    except Exception as error:
        report["error"] = type(error).__name__ + ": " + str(error)[:1500]
    report["finished_at"] = datetime.now(UTC).isoformat()
    (output / "concurrency.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    destination = args.output_dir or (
        PRODUCT
        / ".runtime/verification"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-concurrency")
    )
    result = verify(destination, static_only=args.static_only)
    print(json.dumps({"passed": result["passed"], "output": str(destination)}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
