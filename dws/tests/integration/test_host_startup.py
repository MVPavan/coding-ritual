"""Actual host API startup, interrupted token publication, and concurrent starts."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest
from fixture_site import FixtureSite
from test_product import HTTP, PRODUCT, Product

HOST_START = (
    "import os,sys; os.umask(0o022); from dws.cli import main; "
    "raise SystemExit(main(sys.argv[1:]))"
)

# Hooks affect only this isolated child and pause at the actual token boundary.
# The API, HTTP authorization, filesystem, fsync and CLI remain real.
TOKEN_PUBLICATION_CHECKPOINT = r"""
import json
import os
import signal
import stat
import sys
import time
from pathlib import Path
from dws import api
from dws.cli import main

mode, marker_name, release_name, port = sys.argv[1:]
os.umask(0o022)
original_fsync, original_link = os.fsync, os.link
synced = False

def publish_marker(payload):
    temporary = Path(marker_name + ".tmp")
    temporary.write_text(json.dumps(payload))
    os.replace(temporary, marker_name)

def watched_fsync(descriptor):
    global synced
    info = os.fstat(descriptor)
    if stat.S_ISREG(info.st_mode):
        if mode == "fsync-error":
            publish_marker({"file_fsync_attempted": True})
            raise OSError("Injected isolated token fsync failure")
        original_fsync(descriptor)
        synced = True
    else:
        original_fsync(descriptor)

def watched_link(source, destination, **arguments):
    info = os.stat(source, dir_fd=arguments["src_dir_fd"], follow_symlinks=False)
    publish_marker({
        "file_fsync_complete": synced,
        "staged_mode": stat.S_IMODE(info.st_mode),
        "staged_owner_matches": info.st_uid == os.geteuid(),
        "staged_bytes": info.st_size,
        "destination": destination,
    })
    if mode == "kill-before-publish":
        while True:
            signal.pause()
    deadline = time.monotonic() + 15
    while not Path(release_name).exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("Token publication coordination timed out")
        time.sleep(0.02)
    return original_link(source, destination, **arguments)

api.os.fsync = watched_fsync
api.os.link = watched_link
raise SystemExit(main(["api", "--host", "127.0.0.1", "--port", port]))
"""


def _host(directory: Path, site: FixtureSite, state: Path | None = None) -> Product:
    directory.mkdir()
    product = Product(directory, site)
    product.env.pop("DWS_TOKEN", None)
    product.env.pop("PYTHONPATH", None)
    if state is not None:
        product.env["DWS_DATA_DIR"] = str(state)
    return product


def _launch(product: Product, label: str, *, mode: str | None = None) -> Path:
    marker = product.directory / (label + "-checkpoint.json")
    log = (product.directory / (label + ".log")).open("ab")
    product.logs.append(log)
    argv = [
        sys.executable,
        "-c",
        HOST_START,
        "api",
        "--host",
        "127.0.0.1",
        "--port",
        str(product.port),
    ]
    if mode is not None:
        argv = [
            sys.executable,
            "-c",
            TOKEN_PUBLICATION_CHECKPOINT,
            mode,
            str(marker),
            str(product.directory.parent / "publish-release"),
            str(product.port),
        ]
    product.api = subprocess.Popen(
        argv, cwd=PRODUCT, env=product.env, stdout=log, stderr=subprocess.STDOUT
    )
    return marker


def _ready(product: Product) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        assert product.api is not None and product.api.poll() is None, (
            "Host API exited before readiness"
        )
        try:
            with HTTP.open(product.url + "/ready", timeout=1) as response:
                assert response.status == 200
                return
        except (URLError, TimeoutError):
            threading.Event().wait(0.05)
    pytest.fail("Host API readiness timed out; inspect product-local startup logs")


def _failed_startup(product: Product, label: str, *, mode: str | None = None) -> Path:
    marker = _launch(product, label, mode=mode)
    assert product.api is not None
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if product.api.poll() is not None:
            assert product.api.returncode != 0
            assert not (Path(product.env["DWS_DATA_DIR"]) / "management.sqlite3").exists()
            return marker
        try:
            with HTTP.open(product.url + "/ready", timeout=0.2):
                pytest.fail("An API with an invalid token reached readiness")
        except (URLError, TimeoutError):
            threading.Event().wait(0.05)
    pytest.fail("Invalid-token startup did not fail within its deadline")


def _checkpoint(product: Product, marker: Path) -> dict[str, Any]:
    deadline = time.monotonic() + 15
    while not marker.exists() and time.monotonic() < deadline:
        assert product.api is not None and product.api.poll() is None, (
            "Token checkpoint child exited"
        )
        threading.Event().wait(0.05)
    assert marker.exists(), "Actual token publication checkpoint was not reached"
    result: dict[str, Any] = json.loads(marker.read_text())
    assert result["file_fsync_complete"] and result["staged_owner_matches"]
    assert result["staged_mode"] == 0o600 and result["staged_bytes"] == 44
    assert result["destination"] == "api-token"
    return result


def _authenticated_state(product: Product, name: str) -> dict[str, Any]:
    path = Path(product.env["DWS_DATA_DIR"]) / "api-token"
    info = path.stat()
    assert stat.S_ISREG(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o600
    assert info.st_uid == os.geteuid()
    token = path.read_text().removesuffix("\n")
    assert len(token) == 43
    status, before = product.request("workspace_list", {}, token=token)
    assert status == 200
    denied, result = product.request("workspace_create", {"name": "empty-bearer"}, token="")
    assert denied == 401 and result["error"]["code"] == "authentication_required"
    status, after = product.request("workspace_list", {}, token=token)
    assert status == 200
    assert before["workspaces"] == after["workspaces"] and before["total"] == after["total"], (
        "Unauthorized empty bearer had an effect"
    )
    status, created = product.request("workspace_create", {"name": name}, token=token)
    assert status == 200 and created["workspace_id"]
    unchanged = path.read_text().removesuffix("\n") == token
    assert unchanged, "The published token changed during authenticated operations"
    return {
        "mode": "0600",
        "owner_matches": True,
        "empty_bearer_status": denied,
        "unauthorized_effects": False,
        "generated_token_authorized": True,
    }


def _worker_once(product: Product, label: str, *, succeeds: bool = True) -> None:
    log = product.directory / (label + ".log")
    with log.open("wb") as stream:
        result = subprocess.run(
            [sys.executable, "-c", HOST_START, "worker", "--once"],
            cwd=PRODUCT,
            env=product.env,
            stdout=stream,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
    assert (result.returncode == 0) == succeeds, "Unexpected actual worker startup outcome"


def _private_root(product: Product) -> dict[str, Any]:
    state = Path(product.env["DWS_DATA_DIR"])
    info = state.lstat()
    assert stat.S_ISDIR(info.st_mode) and info.st_uid == os.geteuid()
    assert stat.S_IMODE(info.st_mode) == 0o700
    assert (state / "management.sqlite3").is_file()
    return {
        "root_mode": "0700",
        "owner_matches": True,
        "group_or_other_traversal": False,
        "metadata_exists": True,
    }


def _decoder_admission(
    product: Product, token: str, captured: dict[str, Any], original: str
) -> dict[str, Any]:
    scope = {"snapshot_id": captured["snapshot_id"], "workspace_id": captured["workspace_id"]}
    prefix = json.dumps(scope).removesuffix("}")
    body = (prefix + ', "line_start":' + "9" * 5000 + "}").encode()
    assert len(body) < 65536
    state = Path(product.env["DWS_DATA_DIR"])
    with sqlite3.connect(state / "management.sqlite3") as metadata:
        before = metadata.execute("SELECT count(*) FROM snapshots").fetchone()[0]
    for authorized, expected in ((False, 401), (True, 400)):
        request = Request(
            product.url + "/v1/read",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + (token if authorized else ""),
            },
            method="POST",
        )
        try:
            with HTTP.open(request, timeout=10):
                pytest.fail("An excessive JSON integer unexpectedly passed admission")
        except HTTPError as error:
            with error:
                result = json.load(error)
                assert error.code == expected
                assert result["error"]["code"] == (
                    "invalid_json" if authorized else "authentication_required"
                )
    completed = product.run_cli("read", captured["snapshot_id"], "--start", "9" * 5000)
    assert completed.returncode == 2, "CLI admitted an excessive integer argument"
    with sqlite3.connect(state / "management.sqlite3") as metadata:
        assert metadata.execute("SELECT count(*) FROM snapshots").fetchone()[0] == before
    status, retained = product.request("read", scope, token=token)
    assert status == 200 and retained["text"] == original and retained["pinned"]
    return {
        "request_bytes": len(body),
        "unauthorized_status": 401,
        "authorized_status": 400,
        "structured_error": "invalid_json",
        "cli_argument_exit": completed.returncode,
        "snapshot_count_unchanged": True,
        "ordinary_exact_read_after_rejection": True,
    }


def _cli_failure_recovery(product: Product, site: FixtureSite) -> dict[str, Any]:
    """Exercise installed command failures against real retained owner evidence."""
    executable = Path(sys.executable).with_name("dws")
    assert executable.is_file(), "The installed DWS command is unavailable"
    assert "DWS_TOKEN" not in product.env and "PYTHONPATH" not in product.env

    def invoke(*arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(executable), *arguments],
            cwd=PRODUCT,
            env=product.env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    def decoded(completed: subprocess.CompletedProcess[str]) -> dict[str, Any]:
        assert not completed.stderr and "Traceback" not in completed.stdout
        value: object = json.loads(completed.stdout)
        assert isinstance(value, dict), "The installed command returned non-object JSON"
        return value

    def rejected(code: str, *arguments: str) -> None:
        completed = invoke(*arguments)
        assert completed.returncode == 1
        assert len(completed.stdout.encode("utf-8")) < 2048
        assert decoded(completed)["error"]["code"] == code

    captured = invoke("fetch", site.url + "/article", "--render", "never")
    assert captured.returncode == 0
    snapshot = decoded(captured)["snapshot_id"]
    pinned = invoke("pin", snapshot)
    assert pinned.returncode == 0 and decoded(pinned)["pinned"]
    original_command = invoke("read", snapshot)
    assert original_command.returncode == 0
    original = decoded(original_command)
    assert original["text"] and original["pinned"]

    def retained_read() -> None:
        completed = invoke("read", snapshot)
        assert completed.returncode == 0
        retained = decoded(completed)
        assert retained["text"] == original["text"] and retained["pinned"]
        assert retained["text_hash"] == original["text_hash"]

    state = Path(product.env["DWS_DATA_DIR"])
    token_file = state / "api-token"
    credential = token_file.read_bytes()
    with sqlite3.connect(state / "management.sqlite3") as metadata:
        before = metadata.execute("SELECT count(*) FROM snapshots").fetchone()[0]
    try:
        token_file.write_bytes(b"\xff\xfe")
        rejected("authentication_required", "read", snapshot)
    finally:
        token_file.write_bytes(credential)
    retained_read()

    observed_before = len(site.requests)
    ports = ("not-a-port", "0", "65536", "-1")
    for port in ports:
        rejected(
            "invalid_api_url",
            "--api-url",
            "http://127.0.0.1:" + port + "/cli-invalid-port",
            "read",
            snapshot,
        )
        retained_read()
    assert len(site.requests) == observed_before, "A malformed API URL issued fixture traffic"

    malformed_urls = (
        ("host_space", "http://bad host"),
        ("host_control", "http://bad\x7fhost.invalid"),
        ("base_path_space", site.url + "/cli-invalid path"),
        ("base_path_tab", site.url + "/cli-invalid\tpath"),
        ("base_path_newline", site.url + "/cli-invalid\npath"),
    )
    for _label, api_url in malformed_urls:
        rejected("invalid_api_url", "--api-url", api_url, "read", snapshot)
        assert len(site.requests) == observed_before, "An invalid API URL issued HTTP traffic"
        retained_read()

    rejected(
        "invalid_response",
        "--api-url",
        site.url + "/cli-deep-json",
        "read",
        snapshot,
    )
    assert site.requests[observed_before:] == ["/cli-deep-json/v1/read"]
    retained_read()
    with sqlite3.connect(state / "management.sqlite3") as metadata:
        assert metadata.execute("SELECT count(*) FROM snapshots").fetchone()[0] == before
    assert token_file.read_bytes() == credential
    return {
        "installed_command": "dws",
        "environment_token_and_pythonpath_absent": True,
        "invalid_utf8_token": "authentication_required",
        "malformed_ports": list(ports),
        "malformed_port_error": "invalid_api_url",
        "malformed_ports_no_fixture_requests": True,
        "malformed_url_cases": [label for label, _url in malformed_urls],
        "malformed_url_error": "invalid_api_url",
        "malformed_urls_no_fixture_requests": True,
        "deep_json_endpoint": "/cli-deep-json/v1/read",
        "deep_json_response_bytes": 28001,
        "deep_json_error": "invalid_response",
        "errors_are_bounded_json_without_tracebacks": True,
        "snapshot_count_unchanged": True,
        "credential_restored": True,
        "same_api_exact_pinned_read_after_each_failure": True,
    }


def test_host_token_startup_survives_interruption_and_concurrent_publication() -> None:
    artifacts = PRODUCT / ".runtime/host-startup-tests"
    artifacts.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="journey-", dir=artifacts))
    receipt: dict[str, Any] = {"journey": "host_token_startup", "passed": False, "checks": {}}
    products: list[Product] = []
    try:
        with FixtureSite(directory / "source") as site:
            invalid = _host(directory / "invalid", site)
            products.append(invalid)
            state = Path(invalid.env["DWS_DATA_DIR"])
            state.mkdir(mode=0o700)
            token_file = state / "api-token"
            # Reproduce the exact interrupted legacy condition: published but empty.
            token_file.touch(mode=0o600)
            _failed_startup(invalid, "legacy-empty")
            receipt["checks"]["legacy_empty_file_fails_before_serving"] = True
            token_file.write_text("invalid whitespace credential\n")
            _failed_startup(invalid, "malformed")
            receipt["checks"]["malformed_file_fails_before_serving"] = True
            token_file.write_text("synthetic-existing-token\n")
            token_file.chmod(0o000)
            _failed_startup(invalid, "unreadable")
            receipt["checks"]["unreadable_file_fails_before_serving"] = True
            token_file.chmod(0o644)
            _failed_startup(invalid, "insecure-permissions")
            receipt["checks"]["insecure_file_fails_before_serving"] = True
            token_file.unlink()
            target = state / "synthetic-token-target"
            target.write_text("synthetic-existing-token\n")
            target.chmod(0o600)
            token_file.symlink_to(target)
            _failed_startup(invalid, "symlink")
            receipt["checks"]["symlink_file_fails_before_serving"] = True
            token_file.unlink()
            state.chmod(0o777)
            _failed_startup(invalid, "writable-directory")
            receipt["checks"]["directory_writable_by_others_fails_before_serving"] = True
            state.chmod(0o700)
            invalid.env["DWS_TOKEN"] = ""
            _failed_startup(invalid, "explicit-empty")
            assert not token_file.exists()
            receipt["checks"]["explicit_empty_token_fails_without_fallback"] = True
            invalid.env.pop("DWS_TOKEN")
            marker = _failed_startup(invalid, "fsync-error", mode="fsync-error")
            assert json.loads(marker.read_text())["file_fsync_attempted"]
            assert not token_file.exists() and not list(state.glob(".api-token-*.tmp"))
            receipt["checks"]["fsync_failure_never_publishes_token"] = True

            retention = _host(directory / "retention-admission", site)
            products.append(retention)
            retention_state = Path(retention.env["DWS_DATA_DIR"])
            retention.env["DWS_RETENTION_SECONDS"] = str(10**12)
            assert not retention_state.exists()
            _failed_startup(retention, "unsupported-retention-api")
            assert not retention_state.exists(), "Invalid API retention created owner state"
            _worker_once(retention, "unsupported-retention-worker", succeeds=False)
            assert not retention_state.exists(), "Invalid worker retention created owner state"
            for label in ("unsupported-retention-api", "unsupported-retention-worker"):
                assert (
                    "Retention exceeds the supported UTC timestamp range"
                    in (retention.directory / (label + ".log")).read_text()
                )
            retention.env.pop("DWS_RETENTION_SECONDS")
            _launch(retention, "supported-default-retention")
            _ready(retention)
            default_root = _private_root(retention)
            _authenticated_state(retention, "supported-retention")
            retained_capture = retention.cli(
                "fetch", site.url + "/article", "--render", "never"
            )
            retained_snapshot = retained_capture["snapshot_id"]
            retention.cli("pin", retained_snapshot)
            original_retained = retention.cli("read", retained_snapshot)
            assert original_retained["text"] and original_retained["pinned"]
            _worker_once(retention, "supported-default-worker")
            recovered_retained = retention.cli("read", retained_snapshot)
            assert recovered_retained["text"] == original_retained["text"]
            assert recovered_retained["text_hash"] == original_retained["text_hash"]
            assert recovered_retained["pinned"]
            receipt["checks"]["retention_timestamp_admission"] = {
                "unsupported_seconds": 10**12,
                "api_rejected_before_state_creation_or_readiness": True,
                "worker_rejected_before_state_creation": True,
                "default_api_root": default_root,
                "default_api_and_worker_start_normally": True,
                "exact_pinned_evidence_read_after_worker_start": True,
            }
            retention.stop(retention.api)

            interrupted = _host(directory / "interrupted", site)
            products.append(interrupted)
            marker = _launch(interrupted, "kill-before-publish", mode="kill-before-publish")
            observed = _checkpoint(interrupted, marker)
            interrupted_state = Path(interrupted.env["DWS_DATA_DIR"])
            assert not (interrupted_state / "api-token").exists()
            interrupted.stop(interrupted.api, kill=True)
            assert interrupted.api is not None and interrupted.api.returncode == -9
            abandoned = list(interrupted_state.glob(".api-token-*.tmp"))
            assert len(abandoned) == 1
            _launch(interrupted, "normal-restart")  # Unpatched API, umask 022.
            _ready(interrupted)
            receipt["checks"]["sigkill_before_publication"] = {
                "checkpoint": observed,
                "actual_exit": -9,
                "abandoned_stage_ignored": True,
                "restart": _authenticated_state(interrupted, "after-sigkill"),
            }
            receipt["checks"]["installed_cli_failure_recovery"] = _cli_failure_recovery(
                interrupted, site
            )
            interrupted.stop(interrupted.api)

            explicit = _host(directory / "explicit-token", site)
            products.append(explicit)
            explicit_token = secrets.token_urlsafe(32)
            explicit.env["DWS_TOKEN"] = explicit_token
            _launch(explicit, "explicit-new-root")
            _ready(explicit)
            new_root = _private_root(explicit)
            explicit_state = Path(explicit.env["DWS_DATA_DIR"])
            assert not (explicit_state / "api-token").exists()
            status, captured = explicit.request(
                "fetch", {"url": site.url + "/article", "render": "never"}, token=explicit_token
            )
            assert status == 200
            scope = {
                "snapshot_id": captured["snapshot_id"],
                "workspace_id": captured["workspace_id"],
            }
            status, _ = explicit.request("pin", scope, token=explicit_token)
            assert status == 200
            status, retained = explicit.request("read", scope, token=explicit_token)
            assert status == 200 and retained["pinned"] and retained["text"]
            assert list((explicit_state / "artifacts").rglob("normalized.txt"))
            explicit.stop(explicit.api)
            explicit_state.chmod(0o755)  # Owned legacy root with retained private evidence.
            _launch(explicit, "explicit-existing-root")
            _ready(explicit)
            tightened = _private_root(explicit)
            status, reread = explicit.request("read", scope, token=explicit_token)
            assert status == 200 and reread["text"] == retained["text"] and reread["pinned"]
            receipt["checks"]["explicit_token_new_and_existing_owner_root"] = {
                "umask": "022",
                "new_root": new_root,
                "existing_0755_tightened": tightened,
                "retained_metadata_and_artifact_access_protected_by_root": True,
                "exact_pinned_evidence_preserved": True,
            }
            receipt["checks"]["oversized_json_integer_admission"] = _decoder_admission(
                explicit, explicit_token, captured, retained["text"]
            )
            explicit.stop(explicit.api)

            worker_first = _host(directory / "worker-first", site)
            products.append(worker_first)
            _worker_once(worker_first, "new-root")
            private_worker = _private_root(worker_first)
            worker_state = Path(worker_first.env["DWS_DATA_DIR"])
            assert not (worker_state / "api-token").exists()
            worker_state.chmod(0o755)
            _worker_once(worker_first, "existing-root")
            tightened_worker = _private_root(worker_first)
            _launch(worker_first, "api-after-worker")
            _ready(worker_first)
            receipt["checks"]["worker_first_private_root"] = {
                "umask": "022",
                "new_root": private_worker,
                "existing_0755_tightened": tightened_worker,
                "api_after_worker": _authenticated_state(worker_first, "worker-first"),
            }
            worker_first.stop(worker_first.api)

            unsafe_target = directory / "unsafe-target"
            unsafe_target.mkdir(mode=0o700)
            unsafe_root = directory / "unsafe-root-link"
            unsafe_root.symlink_to(unsafe_target, target_is_directory=True)
            bad_root = _host(directory / "bad-explicit-root", site, unsafe_root)
            products.append(bad_root)
            bad_root.env["DWS_TOKEN"] = secrets.token_urlsafe(32)
            _failed_startup(bad_root, "explicit-root-symlink")
            _worker_once(bad_root, "worker-root-symlink", succeeds=False)
            assert not list(unsafe_target.iterdir())
            unsafe_root.unlink()
            unsafe_root.mkdir(mode=0o777)
            unsafe_root.chmod(0o777)
            _failed_startup(bad_root, "explicit-root-other-write")
            _worker_once(bad_root, "worker-root-other-write", succeeds=False)
            assert stat.S_IMODE(unsafe_root.stat().st_mode) == 0o777
            assert not list(unsafe_root.iterdir())
            receipt["checks"]["explicit_api_and_worker_reject_unsafe_roots"] = {
                "root_symlink_rejected": True,
                "other_writable_root_rejected": True,
                "unsafe_roots_not_modified": True,
            }

            shared = directory / "concurrent-state"
            shared.mkdir(mode=0o755)
            shared.chmod(0o755)
            concurrent = [
                _host(directory / f"concurrent-{index}", site, shared) for index in range(2)
            ]
            products.extend(concurrent)
            markers = [
                _launch(instance, "concurrent", mode="concurrent") for instance in concurrent
            ]
            observed_stages = [
                _checkpoint(instance, marker)
                for instance, marker in zip(concurrent, markers, strict=True)
            ]
            assert not (shared / "api-token").exists(), (
                "A token was visible before staged publication"
            )
            (directory / "publish-release").write_text("release\n")
            for instance in concurrent:
                _ready(instance)
                _private_root(instance)
            authenticated = [
                _authenticated_state(instance, f"concurrent-{index}")
                for index, instance in enumerate(concurrent)
            ]
            assert not list(shared.glob(".api-token-*.tmp"))
            receipt["checks"]["concurrent_actual_api_publication"] = {
                "fully_synced_stages": observed_stages,
                "both_apis_authorized_by_same_file": True,
                "authenticated_apis": authenticated,
                "temporary_stages_removed": True,
                "existing_shared_0755_root_tightened": True,
            }
            receipt["passed"] = True
    finally:
        for product in reversed(products):
            product.close()
        receipt["child_exit_codes"] = [
            product.api.returncode if product.api is not None else None for product in products
        ]
        (directory / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
