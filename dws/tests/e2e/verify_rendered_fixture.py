"""Real DWS -> protected Crawl4AI -> deterministic JS fixture product journey.

Uses fresh containers/state and internal synthetic public/private networks. No
production service is changed and no public/private-policy exception is enabled.
Run from the DWS product with its already prepared runtime/browser images.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import subprocess
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

PRODUCT = Path(__file__).resolve().parents[2]
EXPECTED = "BrowserRenderedMarker actual browser content."


def fixture() -> None:
    """Record accepted TCP connections, including preflights and failed HTTP."""
    log = Path("/evidence/fixture-events.jsonl")
    guard = threading.Lock()

    def record(kind: str, **values: Any) -> None:
        with guard, log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"kind": kind, **values}) + "\n")

    class Server(ThreadingHTTPServer):
        daemon_threads = True

        def get_request(self) -> tuple[Any, Any]:
            connection, peer = super().get_request()
            record("tcp", destination=connection.getsockname()[0], peer=peer[0])
            return connection, peer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _format: str, *_args: Any) -> None:
            pass

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            record(
                "http",
                path=path,
                destination=self.connection.getsockname()[0],
                peer=self.client_address[0],
            )
            if path == "/javascript":
                encoded = base64.b64encode(EXPECTED.encode()).decode()
                private = os.environ["DWS_FIXTURE_PRIVATE_URL"]
                body = f"""<!doctype html><html><head>
<title>Deterministic rendered evidence</title></head><body>
<div id="evidence">Loading</div><p id="status">Waiting</p>
<script>
document.getElementById('evidence').textContent = atob('{encoded}');
fetch('{private}/forbidden-browser-subrequest').then(function() {{
  document.getElementById('status').textContent = 'Private request unexpectedly succeeded';
}}).catch(function() {{
  document.getElementById('status').textContent = 'Private subrequest blocked';
}});
</script></body></html>""".encode()
            else:
                body = b"Independent private reachability control"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    Server(("0.0.0.0", 8080), Handler).serve_forever()


_HTTP_CLIENT = """
import json, os, urllib.error, urllib.request
value = json.load(open('/evidence/request.json'))
headers = {'Content-Type': 'application/json'}
if value.get('authenticated'):
    headers['Authorization'] = 'Bearer ' + os.environ['DWS_TOKEN']
request = urllib.request.Request(value['url'],
    data=json.dumps(value['body']).encode() if 'body' in value else None,
    headers=headers, method=value.get('method', 'GET'))
try:
    with urllib.request.urlopen(request, timeout=40) as response:
        body = response.read(1000000).decode()
        print(json.dumps({'status': response.status,
            'body': json.loads(body) if value.get('json', True) else body}))
except urllib.error.HTTPError as exc:
    print(json.dumps({'status': exc.code, 'body': json.loads(exc.read(1000000))}))
"""


def verify(output: Path) -> int:
    output = output.resolve()
    if not output.is_relative_to(PRODUCT) or output == PRODUCT:
        raise ValueError("Verification output must stay beneath the DWS product folder")
    output.mkdir(parents=True, exist_ok=True)
    for name in ("state", "tmp", "cache", "logs"):
        (output / name).mkdir(exist_ok=True)
    (output / "fixture-events.jsonl").write_text("")
    started = time.monotonic()
    deadline = started + 240
    prefix = "dws-rendered-" + uuid.uuid4().hex[:10]
    segment = secrets.randbelow(220) + 20
    public_subnet, private_subnet = f"11.231.{segment}.0/24", f"172.29.{segment}.0/24"
    fixture_public, browser_public, api_public = (
        f"11.231.{segment}.{index}" for index in (3, 2, 4)
    )
    fixture_private = f"172.29.{segment}.3"
    public_network, private_network = prefix + "-public", prefix + "-private"
    source, browser, api = prefix + "-source", prefix + "-browser", prefix + "-api"
    containers: list[str] = []
    networks: list[str] = []
    token = secrets.token_hex(32)
    environment = output / "fixture.env"
    environment.write_text(
        "DWS_TOKEN="
        + token
        + "\nDWS_CRAWL4AI_TOKEN="
        + token
        + "\nCRAWL4AI_API_TOKEN="
        + token
        + "\nDWS_CRAWL4AI_URL=http://"
        + browser_public
        + ":11235"
        + "\nDWS_DATA_DIR=/evidence/state\nDWS_DDGS_ENABLED=false"
        + "\nDWS_MCP_ENABLED=false\nCRAWL4AI_ALLOW_INTERNAL_URLS=false"
        + "\nCRAWL4AI_ALLOW_INSECURE_TLS=false\nCRAWL4AI_HOOKS_ENABLED=false"
        + "\nDWS_FIXTURE_PRIVATE_URL=http://"
        + fixture_private
        + ":8080"
        + "\nPYTHONDONTWRITEBYTECODE=1\nTMPDIR=/evidence/tmp"
        + "\nXDG_CACHE_HOME=/evidence/cache\nXDG_STATE_HOME=/evidence/state\n"
    )
    environment.chmod(0o600)
    report: dict[str, Any] = {
        "passed": False,
        "scope": "Deterministic rendered acquisition and one private subrequest",
        "public_network": public_subnet,
        "private_network": private_subnet,
        "production_services_modified": False,
        "policy_exceptions_enabled": False,
        "full_historical_security_matrix_rerun": False,
    }

    def docker(*arguments: str, check: bool = True, timeout: float = 90) -> str:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Rendered-fixture verification deadline exceeded")
        result = subprocess.run(
            ["docker", *arguments],
            capture_output=True,
            text=True,
            timeout=max(1, min(timeout, remaining)),
            check=False,
        )
        if check and result.returncode:
            raise RuntimeError(
                (result.stderr or result.stdout).replace(token, "<redacted>")[:1500]
            )
        return result.stdout

    def events() -> list[dict[str, Any]]:
        path = output / "fixture-events.jsonl"
        return (
            [json.loads(line) for line in path.read_text().splitlines()]
            if path.exists()
            else []
        )

    def request(
        url: str, body: dict[str, Any] | None = None, *, json_body: bool = True
    ) -> dict[str, Any]:
        value: dict[str, Any] = {
            "url": url,
            "authenticated": url.startswith("http://127.0.0.1:8765"),
            "json": json_body,
        }
        if body is not None:
            value.update(method="POST", body=body)
        (output / "request.json").write_text(json.dumps(value))
        decoded = json.loads(
            docker(
                "exec",
                api,
                "/app/.runtime/container-env/bin/python",
                "-c",
                _HTTP_CLIENT,
                timeout=45,
            )
        )
        if not isinstance(decoded, dict):
            raise ValueError("Fixture HTTP client returned a non-object response")
        return decoded

    try:
        for name, subnet in (
            (public_network, public_subnet),
            (private_network, private_subnet),
        ):
            networks.append(name)
            docker("network", "create", "--internal", "--subnet", subnet, name)
        report["runtime_image"] = json.loads(docker("image", "inspect", "dws-runtime:local"))[
            0
        ]["Id"]
        report["browser_image"] = json.loads(docker("image", "inspect", "dws-crawl4ai:local"))[
            0
        ]["Id"]
        report["overlay_source_sha256"] = hashlib.sha256(
            (PRODUCT / "docker/crawl4ai-egress/patch.py").read_bytes()
        ).hexdigest()
        common = [
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--env-file",
            str(environment),
            "--cpus",
            "2",
        ]
        containers.append(source)
        docker(
            "run",
            "-d",
            "--name",
            source,
            *common,
            "--pids-limit",
            "128",
            "--network",
            public_network,
            "--ip",
            fixture_public,
            "--mount",
            f"type=bind,src={PRODUCT},dst=/app,readonly",
            "--mount",
            f"type=bind,src={output},dst=/evidence",
            "--entrypoint",
            "python",
            str(report["runtime_image"]),
            "/app/tests/e2e/verify_rendered_fixture.py",
            "fixture",
        )
        docker("network", "connect", "--ip", fixture_private, private_network, source)
        containers.append(browser)
        docker(
            "run",
            "-d",
            "--name",
            browser,
            *common,
            "--pids-limit",
            "256",
            "--network",
            public_network,
            "--ip",
            browser_public,
            "--memory",
            "2g",
            "--memory-swap",
            "2g",
            "--shm-size",
            "256m",
            "--tmpfs",
            "/tmp:rw,nosuid,size=512m,uid=999,gid=999",
            "--tmpfs",
            "/var/lib/redis:rw,noexec,nosuid,size=64m,uid=999,gid=999",
            "--tmpfs",
            "/home/appuser/.crawl4ai:rw,noexec,nosuid,size=128m,uid=999,gid=999",
            "--tmpfs",
            "/home/appuser/.gunicorn:rw,noexec,nosuid,size=4m,uid=999,gid=999",
            "-e",
            "TMPDIR=/tmp",
            "-e",
            "XDG_CACHE_HOME=/home/appuser/.cache",
            "-e",
            "XDG_STATE_HOME=/home/appuser/.crawl4ai",
            "-e",
            "GUNICORN_BIND=0.0.0.0:11235",
            str(report["browser_image"]),
        )
        docker("network", "connect", private_network, browser)
        containers.append(api)
        docker(
            "run",
            "-d",
            "--name",
            api,
            *common,
            "--pids-limit",
            "128",
            "--network",
            public_network,
            "--ip",
            api_public,
            "--memory",
            "768m",
            "--mount",
            f"type=bind,src={PRODUCT},dst=/app,readonly",
            "--mount",
            f"type=bind,src={output},dst=/evidence",
            "--entrypoint",
            "/app/.runtime/container-env/bin/dws",
            str(report["runtime_image"]),
            "api",
            "--host",
            "0.0.0.0",
            "--port",
            "8765",
        )
        docker("network", "connect", private_network, api)
        api_private = json.loads(docker("inspect", api))[0]["NetworkSettings"]["Networks"][
            private_network
        ]["IPAddress"]
        report["private_control_peer"] = api_private
        health = (
            "import os,urllib.request; "
            "urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:11235/health',"
            "headers={'Authorization':'Bearer '+os.environ['CRAWL4AI_API_TOKEN']}),"
            "timeout=2).close()"
        )
        for _attempt in range(45):
            if time.monotonic() >= deadline:
                raise TimeoutError("Isolated provider startup deadline exceeded")
            healthy = (
                subprocess.run(
                    ["docker", "exec", browser, "python", "-c", health],
                    capture_output=True,
                    timeout=5,
                ).returncode
                == 0
            )
            if healthy:
                try:
                    if request("http://127.0.0.1:8765/health")["status"] == 200:
                        break
                except (RuntimeError, ValueError):
                    pass
            time.sleep(2)
        else:
            raise RuntimeError("Isolated API/browser did not become ready")
        print("Isolated DWS and protected browser ready", flush=True)
        source_url = f"http://{fixture_public}:8080/javascript"
        static = request(source_url, json_body=False)
        assert static["status"] == 200 and EXPECTED not in static["body"], (
            "Fixture source already contains rendered evidence"
        )
        fetched = request(
            "http://127.0.0.1:8765/v1/fetch",
            {"url": source_url, "render": "always", "refresh": True},
        )
        assert fetched["status"] == 200, fetched
        capture = fetched["body"]
        assert capture["provider"] == "crawl4ai", capture
        snapshot = capture["snapshot_id"]
        read = request(
            "http://127.0.0.1:8765/v1/read", {"snapshot_id": snapshot, "max_chars": 6000}
        )
        assert read["status"] == 200 and EXPECTED in read["body"]["text"], read
        artifact = output / "state/artifacts" / snapshot
        normalized = (artifact / "normalized.txt").read_text()
        raw = (artifact / "source.bin").read_text()
        assert EXPECTED in raw and EXPECTED in normalized, (
            "Rendered evidence absent from retained artifacts"
        )
        assert read["body"]["text"] == normalized, (
            "Read did not match exact retained normalized artifact"
        )
        assert "Private subrequest blocked" in normalized, (
            "Private browser subrequest was not attempted/completed"
        )
        before_control = events()
        assert any(
            event.get("kind") == "http"
            and event.get("path") == "/javascript"
            and event.get("peer") == browser_public
            for event in before_control
        ), "Actual browser did not acquire the fixture"
        private_connections = [
            event for event in before_control if event.get("destination") == fixture_private
        ]
        assert not private_connections, "Browser reached the forbidden private destination"
        denied = request(
            "http://127.0.0.1:8765/v1/fetch",
            {"url": f"http://{fixture_private}:8080/forbidden-main", "render": "always"},
        )
        assert denied["status"] == 403 and denied["body"]["error"]["code"] == "policy_denied", (
            denied
        )
        control = request(
            f"http://{fixture_private}:8080/reachability-control", json_body=False
        )
        assert control["status"] == 200
        observed = events()
        assert any(
            event.get("destination") == fixture_private
            and event.get("path") == "/reachability-control"
            for event in observed
        ), "Private observer reachability was not demonstrated"
        assert not any(
            event.get("path") in {"/forbidden-browser-subrequest", "/forbidden-main"}
            for event in observed
        ), "Forbidden target received an HTTP request"
        report.update(
            passed=True,
            snapshot_id=snapshot,
            provider=capture["provider"],
            exact_text=read["body"]["text"],
            source_url=source_url,
            normalized_sha256=hashlib.sha256(normalized.encode()).hexdigest(),
            source_sha256=hashlib.sha256((artifact / "source.bin").read_bytes()).hexdigest(),
            private_main_status=denied["status"],
            private_main_code="policy_denied",
            private_browser_connections_before_control=len(private_connections),
            private_reachability_control=True,
            warnings=capture.get("warnings", []),
            artifact_path=str(artifact.relative_to(PRODUCT)),
        )
    except Exception as exc:
        report["error"] = (type(exc).__name__ + ": " + str(exc)).replace(token, "<redacted>")[
            :2000
        ]
    finally:
        # Cleanup has its own bounded calls even when the verification deadline expires.
        cleanup: list[dict[str, Any]] = []
        try:
            for name in reversed(containers):
                item: dict[str, Any] = {"container": name, "removed": False}
                try:
                    logs = subprocess.run(
                        ["docker", "logs", "--tail", "100", name],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    (output / "logs" / (name + ".log")).write_text(
                        (logs.stdout + logs.stderr).replace(token, "<redacted>")
                    )
                except (subprocess.TimeoutExpired, OSError) as exc:
                    item["log_error"] = type(exc).__name__
                try:
                    removed = subprocess.run(
                        ["docker", "rm", "-f", name],
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )
                    item["removed"] = removed.returncode == 0
                    if removed.returncode:
                        item["error"] = removed.stderr.replace(token, "<redacted>")[:400]
                except (subprocess.TimeoutExpired, OSError) as exc:
                    item["error"] = type(exc).__name__
                cleanup.append(item)
            for name in reversed(networks):
                item = {"network": name, "removed": False}
                try:
                    removed = subprocess.run(
                        ["docker", "network", "rm", name],
                        capture_output=True,
                        text=True,
                        timeout=20,
                    )
                    item["removed"] = removed.returncode == 0
                    if removed.returncode:
                        item["error"] = removed.stderr.replace(token, "<redacted>")[:400]
                except (subprocess.TimeoutExpired, OSError) as exc:
                    item["error"] = type(exc).__name__
                cleanup.append(item)
            report["cleanup"] = cleanup
            if any(not entry["removed"] or entry.get("log_error") for entry in cleanup):
                report["passed"] = False
            if report.get("private_reachability_control"):
                # Inspect the persisted observer after browser removal, so a late
                # TCP-only attempt cannot evade the earlier negative snapshot.
                try:
                    final_private = [
                        event
                        for event in events()
                        if event["kind"] == "tcp"
                        and event.get("destination") == fixture_private
                    ]
                    report["private_connections_after_cleanup"] = len(final_private)
                    if (
                        len(final_private) != 1
                        or final_private[0].get("peer") != report["private_control_peer"]
                    ):
                        report.update(passed=False, late_private_connection_failure=True)
                except (OSError, ValueError) as exc:
                    report.update(passed=False, observer_cleanup_error=type(exc).__name__)
        finally:
            try:
                environment.unlink(missing_ok=True)
                report["fixture_credential_removed"] = True
            except OSError as exc:
                report.update(
                    passed=False,
                    fixture_credential_removed=False,
                    credential_cleanup_error=type(exc).__name__,
                )
            report["seconds"] = round(time.monotonic() - started, 3)
            try:
                (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
            except OSError as exc:
                report.update(passed=False, receipt_write_error=type(exc).__name__)
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report["passed"] else 1


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "fixture":
        fixture()
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        "--output",
        dest="output",
        type=Path,
        default=PRODUCT / ".runtime/verification-rerun/rendered-fixture",
    )
    arguments = parser.parse_args()
    return verify(arguments.output)


if __name__ == "__main__":
    raise SystemExit(main())
