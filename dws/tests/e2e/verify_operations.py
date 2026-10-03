"""Verify wheel independence, a locked dependency upgrade, and Compose persistence.

Run after verify_live.py. This replaces only the existing DWS API/worker
containers; it preserves their state and never changes the main environment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import tomllib
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, BinaryIO
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

PRODUCT = Path(__file__).resolve().parents[2]

COMPOSE_OWNER_CONTROLS = {
    "DWS_MAX_BYTES": "2048",
    "DWS_MAX_TEXT_CHARS": "2048",
    "DWS_MAX_OUTPUT_CHARS": "512",
    "DWS_MAX_RESPONSE_BYTES": "16384",
    "DWS_REQUEST_TIMEOUT": "3",
    "DWS_MAX_PAGES": "1",
    "DWS_MAX_DEPTH": "1",
    "DWS_MAX_CRAWL_SECONDS": "3",
    "DWS_MAX_JOBS": "1",
    "DWS_ACQUISITION_SLOTS": "1",
    "DWS_MAX_STORAGE_BYTES": "1000000",
    "DWS_MIN_FREE_BYTES": "0",
    "DWS_RETENTION_SECONDS": "1",
    "DWS_LEASE_SECONDS": "10",
    "DWS_DDGS_ENABLED": "false",
}


def compose_model(prefix: list[str], env: dict[str, str]) -> dict[str, Any]:
    """Read a canonical model without persisting its possibly secret environment."""
    result = subprocess.run(
        prefix + ["config", "--format", "json"],
        cwd=PRODUCT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Read-only Compose configuration rendering failed")
    value: object = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise RuntimeError("Compose configuration was not an object")
    return value


def compose_owner_controls(output: Path, env: dict[str, str]) -> dict[str, Any]:
    """Prove owner settings reach both consumers without duplicating defaults."""
    output.mkdir()
    base = {
        key: value
        for key, value in env.items()
        if not key.startswith("DWS_") and key != "SEARXNG_SECRET"
    }
    (output / "docker").mkdir()
    base["DOCKER_CONFIG"] = str(output / "docker")
    required = (
        "DWS_TOKEN=compose-fixture-token\n"
        "DWS_CRAWL4AI_TOKEN=compose-fixture-browser-token\n"
        "SEARXNG_SECRET=compose-fixture-secret\n"
    )
    required_file, limits_file = output / "required.env", output / "limits.env"
    required_file.write_text(required)
    limits_file.write_text(
        required + "".join(f"{key}={value}\n" for key, value in COMPOSE_OWNER_CONTROLS.items())
    )
    for path in (required_file, limits_file):
        path.chmod(0o600)
    cases: tuple[tuple[str, Path, dict[str, str]], ...] = (
        ("shell", required_file, COMPOSE_OWNER_CONTROLS),
        ("env_file", limits_file, {}),
        ("unset", required_file, {}),
    )
    checks: dict[str, Any] = {}
    for label, path, overrides in cases:
        model = compose_model(
            ["docker", "compose", "--env-file", str(path), "-f", str(PRODUCT / "compose.yaml")],
            {**base, **overrides},
        )
        selected: dict[str, dict[str, str | None]] = {}
        for service in ("dws-api", "dws-worker"):
            settings = model["services"][service]["environment"]
            values = {key: settings.get(key) for key in COMPOSE_OWNER_CONTROLS}
            if label == "unset":
                assert all(value is None for value in values.values()), (
                    "Unspecified Compose limits must remain unresolved, "
                    "not empty or duplicated defaults"
                )
            else:
                assert values == COMPOSE_OWNER_CONTROLS, (
                    "Explicit owner controls did not reach both Compose consumers"
                )
            assert settings["DWS_DATA_DIR"] == "/app/.state"
            assert settings["DWS_SEARXNG_URL"] == "http://searxng:8080"
            assert settings["DWS_CRAWL4AI_URL"] == "http://crawl4ai:11235"
            assert settings["UV_PROJECT_ENVIRONMENT"] == "/app/.runtime/container-env"
            assert settings["DWS_MCP_ENABLED"] == "false"
            assert "DWS_ALLOWED_PRIVATE_HOSTS" not in settings
            selected[service] = values
        provider = model["services"]["crawl4ai"]["environment"]
        assert all(
            provider[key] == "false"
            for key in (
                "CRAWL4AI_ALLOW_INTERNAL_URLS",
                "CRAWL4AI_ALLOW_INSECURE_TLS",
                "CRAWL4AI_HOOKS_ENABLED",
            )
        )
        checks[label] = selected
    result = {
        "passed": True,
        "compose_sha256": digest(PRODUCT / "compose.yaml"),
        "owner_control_count": len(COMPOSE_OWNER_CONTROLS),
        "resolved_controls": checks,
        "fixed_paths_provider_routing_and_security_defaults_preserved": True,
        "unset_canonical_values_are_null": True,
        "defaults_defined_only_by_application": True,
        "owner_configuration_read_or_modified": False,
        "services_started_or_replaced": False,
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configuration() -> dict[str, str]:
    values: dict[str, str] = {}
    for original in (PRODUCT / ".runtime/owner.env").read_text().splitlines():
        line = original.removeprefix("export ").strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            words = shlex.split(value, comments=True)
            if words:
                values[key.strip()] = " ".join(words)
    return values


class Commands:
    def __init__(self, output: Path, env: dict[str, str]) -> None:
        self.output, self.env = output, env
        self.records: list[dict[str, Any]] = []

    def run(
        self,
        argv: list[str],
        label: str,
        cwd: Path,
        *,
        expected: int | None = 0,
        timeout: int = 180,
    ) -> subprocess.CompletedProcess[str]:
        started = time.monotonic()
        result = subprocess.run(
            argv, cwd=cwd, env=self.env, capture_output=True, text=True, timeout=timeout
        )
        private = [
            value
            for key, value in self.env.items()
            if any(word in key for word in ("TOKEN", "SECRET", "PASSWORD")) and value
        ]
        for stream in ("stdout", "stderr"):
            content = getattr(result, stream)
            for value in private:
                content = content.replace(value, "[redacted]")
            (self.output / f"{label}.{stream}.log").write_text(content)
        self.records.append(
            {
                "argv": argv,
                "cwd": str(cwd),
                "returncode": result.returncode,
                "seconds": round(time.monotonic() - started, 3),
                "stdout": f"{label}.stdout.log",
                "stderr": f"{label}.stderr.log",
            }
        )
        (self.output / "commands.json").write_text(json.dumps(self.records, indent=2) + "\n")
        if expected is not None and result.returncode != expected:
            raise RuntimeError(f"{label} failed; inspect its product-local command logs")
        return result


def prepared_mcp_variants(
    output: Path,
    environment: dict[str, str],
) -> dict[str, Any]:
    """Run real locked preparation and real APIs in isolated generic containers."""
    output = output.resolve()
    boundary = (PRODUCT / ".runtime").resolve()
    if output == boundary or not output.is_relative_to(boundary):
        raise ValueError("MCP preparation proof must remain beneath product .runtime/")
    output.mkdir(parents=True, exist_ok=False)
    prefix = "dws-mcp-prepare-" + uuid.uuid4().hex[:10]
    containers: list[str] = []
    report: dict[str, Any] = {
        "passed": False,
        "prefix": prefix,
        "cases": [],
        "cleanup": [],
        "main_owner_environment_read_or_changed": False,
        "main_consumers_replaced_or_synced": False,
        "network": "none",
        "published_host_ports": [],
    }
    env = {
        key: value
        for key, value in environment.items()
        if not key.startswith("DWS_") and key != "SEARXNG_SECRET"
    }
    for key, directory in {
        "TMPDIR": "tmp",
        "XDG_CACHE_HOME": "host-cache",
        "XDG_STATE_HOME": "host-state",
        "XDG_CONFIG_HOME": "host-config",
    }.items():
        path = output / directory
        path.mkdir()
        env[key] = str(path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    recorder = Commands(output, env)

    def command(argv: list[str], label: str) -> str:
        return recorder.run(argv, label, PRODUCT, timeout=90).stdout

    app = output / "product"
    app.mkdir()
    # Nested mounts must already exist beneath the read-only source bind.
    (app / ".runtime").mkdir()
    (app / ".state").mkdir()
    for name in ("pyproject.toml", "uv.lock", "README.md"):
        shutil.copy2(PRODUCT / name, app / name)
    shutil.copytree(PRODUCT / "src", app / "src", ignore=shutil.ignore_patterns("__pycache__"))
    (app / "docker").mkdir()
    for name in ("prepare_environment.sh", "run_application.sh"):
        shutil.copy2(PRODUCT / "docker" / name, app / "docker" / name)
    report["preparation_script_sha256"] = hashlib.sha256(
        (app / "docker/prepare_environment.sh").read_bytes()
    ).hexdigest()
    report["lock_sha256"] = hashlib.sha256((app / "uv.lock").read_bytes()).hexdigest()
    cache = output / "uv-cache"
    source_cache = PRODUCT / ".runtime/uv-cache"
    shutil.copytree(source_cache, cache, symlinks=True)
    roots = (source_cache.resolve(), Path("/app/.runtime/uv-cache"))
    rebased = 0
    for link in cache.rglob("*"):
        if not link.is_symlink():
            continue
        target = link.readlink()
        if target.is_absolute():
            relative = next(
                (target.relative_to(root) for root in roots if target.is_relative_to(root)),
                None,
            )
            if relative is None or not (cache / relative).exists():
                raise RuntimeError("Copied dependency cache has an escaping or missing link")
            link.unlink()
            link.symlink_to(os.path.relpath(cache / relative, link.parent))
            rebased += 1
        elif not (link.parent / target).resolve().is_relative_to(cache):
            raise RuntimeError("Copied dependency cache has an escaping relative link")
        if not link.resolve().is_relative_to(cache):
            raise RuntimeError("Copied dependency cache link escaped its owned snapshot")
    report["copied_cache_absolute_links_rebased"] = rebased
    report["copied_cache_links_resolve_only_within_owned_snapshot"] = True
    report["cache_owned_by_run_and_network_installation_disabled"] = True
    image = command(
        ["docker", "image", "inspect", "dws-runtime:local", "--format", "{{.Id}}"],
        "generic-image",
    ).strip()
    assert image.startswith("sha256:")
    report["runtime_image"] = image
    container_env = {
        "DWS_DATA_DIR": "/app/.state",
        "DWS_TOKEN": "dws-synthetic-mcp-token",
        "DWS_DDGS_ENABLED": "false",
        "DWS_SEARXNG_URL": "",
        "DWS_CRAWL4AI_URL": "",
        "UV_PROJECT_ENVIRONMENT": "/app/.runtime/container-env",
        "UV_CACHE_DIR": "/app/.runtime/uv-cache",
        "UV_OFFLINE": "true",
        "UV_LINK_MODE": "copy",
        "UV_PYTHON_DOWNLOADS": "never",
        "TMPDIR": "/app/.runtime/tmp",
        "XDG_CACHE_HOME": "/app/.runtime/cache",
        "XDG_STATE_HOME": "/app/.runtime/state",
        "XDG_CONFIG_HOME": "/app/.runtime/config",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
    }
    probe = """import asyncio,importlib.util,json,os,time,urllib.error,urllib.request
base='http://127.0.0.1:8765'
headers={'Authorization':'Bearer '+os.environ['DWS_TOKEN']}
out={'fastmcp_installed':importlib.util.find_spec('fastmcp') is not None,
     'mcp_flag_present':'DWS_MCP_ENABLED' in os.environ,'ready':False}
for attempt in range(30):
 try:
  request=urllib.request.Request(base+'/ready',headers=headers)
  with urllib.request.urlopen(request,timeout=1) as response:
   out['readiness']=json.loads(response.read());out['ready']=True
  break
 except (OSError,urllib.error.URLError) as error:
  out['last_startup_error_type']=type(error).__name__;time.sleep(.2)
if out['ready'] and out['readiness']['mcp']:
 from fastmcp import Client
 from fastmcp.client.transports import StreamableHttpTransport
 import httpx2 as httpx
 def factory(headers=None,timeout=None,auth=None,*,follow_redirects=False):
  return httpx.AsyncClient(headers=headers,timeout=timeout,trust_env=False,
                           follow_redirects=False,auth=auth)
 async def check():
  transport=StreamableHttpTransport(base+'/mcp/',headers=headers,
                                    httpx_client_factory=factory)
  async with Client(transport,cache=False,timeout=10) as client:
   return sorted(tool.name for tool in await client.list_tools())
 out['tools']=asyncio.run(check())
elif out['ready']:
 request=urllib.request.Request(base+'/mcp/',headers=headers)
 try:
  with urllib.request.urlopen(request,timeout=2) as response:out['mcp_status']=response.status
 except urllib.error.HTTPError as error:out['mcp_status']=error.code
print(json.dumps(out))
"""
    try:
        variants: tuple[tuple[str, str | None], ...] = (
            ("lowercase", "true"),
            ("uppercase", "TRUE"),
            ("mixed", "True"),
            ("false", "false"),
            ("unset", None),
        )
        for label, value in variants:
            case_dir = output / label
            runtime, state = case_dir / "runtime", case_dir / "state"
            runtime.mkdir(parents=True)
            state.mkdir(mode=0o700)
            (runtime / "uv-cache").mkdir()
            values = container_env.copy()
            if value is not None:
                values["DWS_MCP_ENABLED"] = value
            env.update(values)
            env.pop("DWS_MCP_ENABLED", None)
            if value is not None:
                env["DWS_MCP_ENABLED"] = value
            common = [
                "--network",
                "none",
                "--read-only",
                "--user",
                str(os.getuid()),
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                "1g",
                "--cpus",
                "2",
                "--pids-limit",
                "128",
                "--mount",
                f"type=bind,src={app},dst=/app,readonly",
                "--mount",
                f"type=bind,src={runtime},dst=/app/.runtime",
                "--mount",
                f"type=bind,src={cache},dst=/app/.runtime/uv-cache",
                "--mount",
                f"type=bind,src={state},dst=/app/.state",
            ]
            for name in values:
                common.extend(["-e", name])
            container = prefix + "-" + label
            case: dict[str, Any] = {"label": label, "value": value, "passed": False}
            report["cases"].append(case)
            try:
                assert not (runtime / "container-env").exists()
                containers.append(container)
                command(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--name",
                        container,
                        *common,
                        "--entrypoint",
                        "sleep",
                        image,
                        "180",
                    ],
                    label + "-start-container",
                )
                command(
                    [
                        "docker",
                        "exec",
                        container,
                        "/bin/sh",
                        "/app/docker/prepare_environment.sh",
                    ],
                    label + "-prepare",
                )
                case["locked_preparation_completed"] = True
                command(
                    [
                        "docker",
                        "exec",
                        "-d",
                        container,
                        "/bin/sh",
                        "-c",
                        "exec /bin/sh /app/docker/run_application.sh api --host 127.0.0.1 "
                        "--port 8765 > /app/.runtime/api.log 2>&1",
                    ],
                    label + "-start-api",
                )
                # The generic container stays alive if the application exits,
                # allowing readiness and package inspection through real exec.
                outcome = json.loads(
                    command(
                        [
                            "docker",
                            "exec",
                            container,
                            "/app/.runtime/container-env/bin/python",
                            "-c",
                            probe,
                        ],
                        label + "-probe",
                    )
                )
                if not isinstance(outcome, dict):
                    raise RuntimeError("MCP preparation probe did not return an object")
                case.update(outcome)
                enabled = value is not None and value.lower() == "true"
                assert outcome["ready"], "Prepared API did not become ready"
                assert outcome["readiness"]["mcp"] is enabled
                assert outcome["fastmcp_installed"] is enabled
                if enabled:
                    assert set(outcome["tools"]) == {
                        "search",
                        "fetch",
                        "crawl",
                        "retrieve",
                        "read",
                        "job_status",
                        "job_cancel",
                    }
                else:
                    assert outcome["mcp_status"] == 404
                assert outcome["mcp_flag_present"] is (value is not None)
                case["passed"] = True
            except (AssertionError, RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                case.update(error_type=type(error).__name__, error=str(error)[:200])
            finally:
                if container in containers:
                    try:
                        command(["docker", "rm", "-f", container], label + "-remove-container")
                        report["cleanup"].append({"name": container, "removed": True})
                        containers.remove(container)
                    except (OSError, subprocess.TimeoutExpired, RuntimeError) as error:
                        report["cleanup"].append(
                            {
                                "name": container,
                                "removed": False,
                                "error_type": type(error).__name__,
                            }
                        )
    finally:
        report["passed"] = (
            all(case["passed"] for case in report["cases"])
            and len(report["cases"]) == 5
            and not containers
            and all(entry.get("removed", False) for entry in report["cleanup"])
        )
        report["leftover_containers"] = list(containers)
        (output / "receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def trusted_local_api_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        _ = parsed.port  # Validate malformed or out-of-range port values as well.
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError
    except ValueError:
        raise ValueError(
            "The API URL must identify the trusted local DWS API without userinfo"
        ) from None
    return value.rstrip("/")


class NoRedirects(HTTPRedirectHandler):
    """Never forward the local bearer token through an API redirect."""

    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


class API:
    def __init__(self, base: str, token: str) -> None:
        self.base, self.token = trusted_local_api_url(base), token
        self.opener = build_opener(ProxyHandler({}), NoRedirects())

    def request(self, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        request = Request(
            self.base + path,
            data=None if body is None else json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            },
        )
        with self.opener.open(request, timeout=30) as response:
            result = json.load(response)
        if not isinstance(result, dict) or "error" in result:
            raise RuntimeError("DWS returned an invalid operation response")
        return result

    def command(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("/v1/" + operation, payload)

    def ready(self, timeout: float = 60) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while True:
            try:
                return self.request("/ready")
            except OSError as error:
                if isinstance(error, HTTPError) and 300 <= error.code < 400:
                    error.close()
                    raise RuntimeError("DWS API redirects are refused") from None
                if time.monotonic() >= deadline:
                    raise RuntimeError("DWS did not become ready within its deadline") from None
                time.sleep(0.1)


def redirect_boundary() -> dict[str, Any]:
    """Exercise the authenticated helper against two real local HTTP servers."""
    collected = {"requests": 0, "authorization_received": False}

    class Collector(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            collected["requests"] += 1
            collected["authorization_received"] = "Authorization" in self.headers
            body = b'{"collected":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args: object) -> None:
            pass

    with ThreadingHTTPServer(("127.0.0.1", 0), Collector) as collector:
        collector_url = f"http://127.0.0.1:{collector.server_port}"

        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(302)
                self.send_header("Location", collector_url + "/collect")
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args: object) -> None:
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), Redirect) as redirect:
            threads = [
                threading.Thread(target=server.serve_forever, daemon=True)
                for server in (collector, redirect)
            ]
            for thread in threads:
                thread.start()
            try:
                control = build_opener(ProxyHandler({}), NoRedirects())
                with control.open(collector_url + "/control", timeout=5) as response:
                    assert json.load(response) == {"collected": True}
                assert collected == {"requests": 1, "authorization_received": False}
                collected["requests"] = 0
                api = API(f"http://127.0.0.1:{redirect.server_port}", secrets.token_urlsafe(32))
                try:
                    api.request("/redirect")
                except HTTPError as error:
                    status = error.code
                    error.close()
                    assert status == 302
                else:
                    raise AssertionError("The authenticated helper followed an API redirect")
                assert collected == {"requests": 0, "authorization_received": False}
                return {
                    "passed": True,
                    "redirect_status": status,
                    "collector_positive_control": True,
                    "collector_requests_after_redirect": collected["requests"],
                    "authorization_forwarded": collected["authorization_received"],
                }
            finally:
                for server in (redirect, collector):
                    server.shutdown()
                for thread in threads:
                    thread.join(timeout=5)


class Source(BaseHTTPRequestHandler):
    changed = False

    def do_GET(self) -> None:
        marker = "Changed live source" if self.changed else "Retained baseline evidence"
        body = (
            "<html><head><title>Operations fixture</title></head><body>"
            f"<h1>{marker}</h1><p>The pinned citation survives an upgrade.</p></body></html>"
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass


@contextmanager
def consumers(
    executable: Path, work: Path, env: dict[str, str], output: Path, phase: str
) -> Iterator[tuple[API, list[dict[str, Any]]]]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    processes: list[tuple[subprocess.Popen[bytes], BinaryIO, str]] = []
    stopped: list[dict[str, Any]] = []
    try:
        for role, args in (
            ("api", ["api", "--port", str(port)]),
            ("worker", ["worker", "--idle-seconds", "0.1"]),
        ):
            log: BinaryIO = (output / f"{phase}-{role}.log").open("wb")
            process = subprocess.Popen(
                [str(executable), *args], cwd=work, env=env, stdout=log, stderr=log
            )
            processes.append((process, log, role))
        api = API(f"http://127.0.0.1:{port}", env["DWS_TOKEN"])
        api.ready(timeout=20)
        if any(process.poll() is not None for process, _, _ in processes):
            raise RuntimeError("An installed DWS consumer exited during startup")
        yield api, stopped
    finally:
        for process, _, _ in processes:
            if process.poll() is None:
                process.terminate()
        forced = False
        for process, log, role in processes:
            try:
                process.wait(timeout=45)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                forced = True
            finally:
                log.close()
            stopped.append({"role": role, "pid": process.pid, "exit": process.returncode})
        if forced:
            raise RuntimeError("DWS consumer required a forced shutdown")


def runtime(command: Commands, environment: Path, work: Path, phase: str) -> dict[str, Any]:
    code = (
        "import dws,importlib.util,importlib.metadata as m,json,sys,sqlite3;"
        "print(json.dumps({'package_source':dws.__file__,'python':sys.version,"
        "'sqlite':sqlite3.sqlite_version,'mcp_installed':"
        "importlib.util.find_spec('fastmcp') is not None,"
        "'packages':{n:m.version(n) for n in "
        "('dws','idna','httpx','fastapi','anyio','typing-extensions')}}))"
    )
    result = command.run(
        [str(environment / "bin/python"), "-B", "-c", code], phase + "-runtime", work
    )
    metadata: dict[str, Any] = json.loads(result.stdout)
    assert Path(metadata["package_source"]).is_relative_to(environment)
    assert not metadata["mcp_installed"], "Default installation unexpectedly includes MCP"
    return metadata


def installed_upgrade(output: Path, environment: dict[str, str]) -> dict[str, Any]:
    output.mkdir()
    project, work, installed = output / "project", output / "work", output / "environment"
    project.mkdir()
    work.mkdir()
    for name in ("pyproject.toml", "uv.lock", "README.md"):
        shutil.copy2(PRODUCT / name, project / name)
    shutil.copytree(
        PRODUCT / "src", project / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    env = environment.copy()
    env.pop("PYTHONPATH", None)
    env.update(
        UV_PROJECT_ENVIRONMENT=str(installed),
        UV_PYTHON=sys.executable,
        DWS_DATA_DIR=str(work / ".state"),
        DWS_TOKEN=secrets.token_urlsafe(32),
        DWS_MCP_ENABLED="false",
        DWS_ALLOWED_PRIVATE_HOSTS="127.0.0.1",
        DWS_DDGS_ENABLED="false",
        DWS_SEARXNG_URL="",
        DWS_CRAWL4AI_URL="",
        PYTHONDONTWRITEBYTECODE="1",
    )
    command = Commands(output, env)
    command.run(["uv", "lock", "--upgrade-package", "idna==3.19"], "baseline-lock", project)
    shutil.copy2(project / "uv.lock", output / "baseline.lock")
    command.run(
        ["uv", "sync", "--locked", "--no-dev", "--no-editable"], "baseline-sync", project
    )
    command.run(
        ["uv", "build", "--wheel", "--out-dir", str(output / "wheels")], "build-wheel", project
    )
    wheels = list((output / "wheels").glob("dws-*.whl"))
    assert len(wheels) == 1, "Current project did not produce exactly one DWS wheel"
    command.run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(installed / "bin/python"),
            "--no-deps",
            "--reinstall",
            str(wheels[0]),
        ],
        "install-wheel",
        work,
    )
    unavailable = output / "source-not-required"
    (project / "src").rename(unavailable)
    baseline = runtime(command, installed, work, "baseline")
    assert baseline["packages"]["idna"] == "3.19"
    Source.changed = False
    server = ThreadingHTTPServer(("127.0.0.1", 0), Source)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with consumers(installed / "bin/dws", work, env, output, "baseline") as (api, before):
            job = api.command(
                "crawl",
                {
                    "seed_url": f"http://127.0.0.1:{server.server_port}/docs/index.html",
                    "render": "never",
                    "max_pages": 1,
                    "max_depth": 0,
                    "idempotency_key": "operations-capture",
                },
            )
            deadline = time.monotonic() + 20
            while True:
                status = api.command("job_status", {"job_id": job["job_id"]})
                if status["state"] not in ("queued", "running"):
                    break
                assert time.monotonic() < deadline, (
                    "Installed worker did not complete its crawl"
                )
                time.sleep(0.1)
            assert status["counts"]["succeeded"] == 1
            snapshot = status["manifest"][0]["snapshot_id"]
            api.command("pin", {"snapshot_id": snapshot})
            original = api.command("read", {"snapshot_id": snapshot})
            assert original["pinned"] and "Retained baseline evidence" in original["text"]
            deadline = time.monotonic() + 15
            while True:
                retrieved = api.command("retrieve", {"query": "Retained baseline evidence"})
                if retrieved["results"]:
                    break
                assert time.monotonic() < deadline, (
                    "Installed worker did not index captured evidence"
                )
                time.sleep(0.1)
        assert before, "Consumers were not stopped before the dependency update"
        unavailable.rename(project / "src")
        Source.changed = True
        command.run(["uv", "lock", "--upgrade-package", "idna==3.20"], "upgrade-lock", project)
        shutil.copy2(project / "uv.lock", output / "upgraded.lock")
        command.run(
            ["uv", "sync", "--locked", "--no-dev", "--no-editable"], "upgrade-sync", project
        )
        (project / "src").rename(unavailable)
        upgraded = runtime(command, installed, work, "upgraded")
        assert upgraded["packages"]["idna"] == "3.20"
        with consumers(installed / "bin/dws", work, env, output, "upgraded") as (api, after):
            retained = api.command("read", {"snapshot_id": snapshot})
            durable = api.command("job_status", {"job_id": job["job_id"]})
            assert retained["text"] == original["text"] and retained["pinned"]
            assert durable["counts"]["succeeded"] == 1
        locks = [
            tomllib.loads((output / name).read_text())
            for name in ("baseline.lock", "upgraded.lock")
        ]
        old, new = [{p["name"]: p["version"] for p in lock["package"]} for lock in locks]
        delta = {
            name: {"before": old.get(name), "after": version}
            for name, version in new.items()
            if old.get(name) != version
        }
        assert delta == {"idna": {"before": "3.19", "after": "3.20"}}, delta
        return {
            "passed": True,
            "baseline": baseline,
            "upgraded": upgraded,
            "dependency_delta": delta,
            "wheel": wheels[0].name,
            "wheel_sha256": digest(wheels[0]),
            "source_checkout_required": False,
            "working_directory": str(work),
            "pythonpath_used": False,
            "snapshot_id": snapshot,
            "job_id": job["job_id"],
            "exact_pinned_read_after_upgrade": True,
            "retained_text_sha256": hashlib.sha256(original["text"].encode()).hexdigest(),
            "consumer_stops_before_upgrade": before,
            "consumer_stops_after_verification": after,
        }
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def compose_persistence(
    output: Path, env: dict[str, str], base: str, live_path: Path
) -> dict[str, Any]:
    output.mkdir()
    owner = configuration()
    token = os.environ.get("DWS_TOKEN") or owner.get("DWS_TOKEN")
    if not token:
        raise RuntimeError("Product-local owner configuration has no API token")
    live = json.loads(live_path.read_text())
    assert live["passed"], "Run the successful live journey before operations maintenance"
    snapshot = live["checks"]["static_acquisition"]["evidence"]["snapshot_id"]
    payload = {"snapshot_id": snapshot, "workspace_id": live["workspace_id"]}
    api = API(base, token)
    readiness = api.ready()
    original = api.command("read", payload)
    assert original["pinned"], "The live journey's retained citation is not pinned"
    compose_env = env.copy()
    for key, value in owner.items():
        compose_env.setdefault(key, value)
    compose_env["DWS_MCP_ENABLED"] = "true" if readiness["mcp"] else "false"
    command = Commands(output, compose_env)
    prefix = ["docker", "compose", "--env-file", str(PRODUCT / ".runtime/owner.env")]
    rendered = compose_model(prefix, compose_env)
    before_ids = command.run(
        prefix + ["ps", "-q", "dws-api", "dws-worker"], "before-ids", PRODUCT
    ).stdout.split()
    assert len(before_ids) == 2, "Both existing Compose consumers must be running"
    version_code = "import importlib.metadata as m; print(m.version('dws'))"
    before_version = command.run(
        prefix
        + [
            "exec",
            "-T",
            "dws-api",
            "/app/.runtime/container-env/bin/python",
            "-c",
            version_code,
        ],
        "before-version",
        PRODUCT,
    ).stdout.strip()
    refused = command.run(
        prefix + ["run", "--rm", "--no-deps", "prepare"],
        "live-preparation",
        PRODUCT,
        expected=None,
    )
    assert (
        refused.returncode != 0 and "Environment is in use" in refused.stdout + refused.stderr
    )
    # Recreate only the consumers against their existing locked environment.
    # There is no stopped-environment sync and no restore of historical state.
    command.run(
        prefix + ["up", "-d", "--no-deps", "--force-recreate", "dws-api", "dws-worker"],
        "replace-consumers",
        PRODUCT,
    )
    after_ready = api.ready(timeout=90)
    retained = api.command("read", payload)
    assert retained["text"] == original["text"] and retained["pinned"]
    after_ids = command.run(
        prefix + ["ps", "-q", "dws-api", "dws-worker"], "after-ids", PRODUCT
    ).stdout.split()
    assert len(after_ids) == 2 and not set(before_ids) & set(after_ids)
    after_version = command.run(
        prefix
        + [
            "exec",
            "-T",
            "dws-api",
            "/app/.runtime/container-env/bin/python",
            "-c",
            version_code,
        ],
        "after-version",
        PRODUCT,
    ).stdout.strip()
    assert before_version == after_version, "Container replacement unexpectedly changed DWS"
    consumer_controls: dict[str, Any] = {}
    inspect_code = (
        "import json,os; names=" + repr(list(COMPOSE_OWNER_CONTROLS)) + "; "
        "print(json.dumps({key:os.environ[key] for key in names if key in os.environ}))"
    )
    for service in ("dws-api", "dws-worker"):
        actual = json.loads(
            command.run(
                prefix
                + [
                    "exec",
                    "-T",
                    service,
                    "/app/.runtime/container-env/bin/python",
                    "-c",
                    inspect_code,
                ],
                service + "-owner-controls",
                PRODUCT,
            ).stdout
        )
        expected = rendered["services"][service]["environment"]
        for key in COMPOSE_OWNER_CONTROLS:
            if expected.get(key) is None:
                assert key not in actual, "Unresolved Compose control was passed to a consumer"
            else:
                assert actual.get(key) == expected[key], (
                    "Consumer owner control differs from Compose"
                )
        consumer_controls[service] = {
            "values": actual,
            "unset_controls_absent_at_runtime": sorted(
                set(COMPOSE_OWNER_CONTROLS) - set(actual)
            ),
            "matches_owner_rendered_configuration": True,
        }
    return {
        "passed": True,
        "snapshot_id": snapshot,
        "workspace_id": live["workspace_id"],
        "live_preparation_refused": True,
        "before_container_ids": before_ids,
        "after_container_ids": after_ids,
        "before_version": before_version,
        "after_version": after_version,
        "owner_controls_in_actual_consumers": consumer_controls,
        "readiness": after_ready,
        "exact_pinned_citation_survived": True,
        "environment_prepared_or_changed": False,
        "retained_text_sha256": hashlib.sha256(original["text"].encode()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=PRODUCT / ".runtime/verification-rerun/operations"
    )
    parser.add_argument("--api-url", default="http://127.0.0.1:8765")
    parser.add_argument("--live-receipt", type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--compose-config-only",
        action="store_true",
        help="Render owner-control cases without touching the running product",
    )
    mode.add_argument(
        "--mcp-prepare-only",
        action="store_true",
        help="Verify isolated locked MCP preparation without main consumer replacement",
    )
    args = parser.parse_args()
    output = args.output_dir.resolve()
    boundary = (PRODUCT / ".runtime").resolve()
    if output == boundary or not output.is_relative_to(boundary):
        parser.error("--output-dir must be a directory beneath the product's .runtime")
    live = (args.live_receipt or output.parent / "live/receipt.json").resolve()
    if not live.is_relative_to(boundary):
        parser.error("--live-receipt must remain beneath the product's .runtime")
    try:
        args.api_url = trusted_local_api_url(args.api_url)
    except ValueError as error:
        parser.error(str(error))
    output.mkdir(parents=True, exist_ok=True)
    run_dir = output / ("run-" + uuid.uuid4().hex[:12])
    run_dir.mkdir()
    env = os.environ.copy()
    for name in ("tmp", "cache", "python", "config", "state", "pycache"):
        (run_dir / name).mkdir()
    env.update(
        TMPDIR=str(run_dir / "tmp"),
        UV_CACHE_DIR=str(run_dir / "cache"),
        UV_PYTHON_INSTALL_DIR=str(run_dir / "python"),
        XDG_CACHE_HOME=str(run_dir / "cache"),
        XDG_CONFIG_HOME=str(run_dir / "config"),
        XDG_STATE_HOME=str(run_dir / "state"),
        PYTHONPYCACHEPREFIX=str(run_dir / "pycache"),
    )
    original = {name: digest(PRODUCT / name) for name in ("pyproject.toml", "uv.lock")}
    receipt: dict[str, Any] = {
        "schema_version": "1.0",
        "journey": "installed_product_and_operations",
        "requested_scope": "mcp_preparation_only" if args.mcp_prepare_only else "operations",
        "passed": False,
        "started_at": time.time(),
        "run_directory": str(run_dir),
        "checks": {},
        "limitations": [
            "Dependency proof uses a controlled localhost source explicitly allowed "
            "in its isolated environment.",
            "Main Compose replacement must run after live journeys and interrupts "
            "API/worker availability.",
        ],
    }
    path = output / "receipt.json"
    try:
        receipt["checks"]["compose_owner_controls"] = compose_owner_controls(
            run_dir / "compose-owner-controls", env
        )
        path.write_text(json.dumps(receipt, indent=2) + "\n")
        if args.compose_config_only:
            receipt["passed"] = True
            receipt["finished_at"] = time.time()
            path.write_text(json.dumps(receipt, indent=2) + "\n")
            print(json.dumps({"passed": True, "receipt": str(path)}))
            return 0
        receipt["checks"]["isolated_locked_mcp_preparation"] = prepared_mcp_variants(
            run_dir / "mcp-preparation", env
        )
        path.write_text(json.dumps(receipt, indent=2) + "\n")
        assert receipt["checks"]["isolated_locked_mcp_preparation"]["passed"], (
            "Isolated locked MCP preparation did not pass all five variants"
        )
        if not args.mcp_prepare_only:
            receipt["checks"]["local_api_redirect_guard"] = redirect_boundary()
            path.write_text(json.dumps(receipt, indent=2) + "\n")
            receipt["checks"]["installed_wheel_and_locked_dependency_upgrade"] = (
                installed_upgrade(run_dir / "installed", env)
            )
            path.write_text(json.dumps(receipt, indent=2) + "\n")
            receipt["checks"]["compose_replacement_and_environment_guard"] = (
                compose_persistence(run_dir / "compose", env, args.api_url, live)
            )
        receipt["main_manifest_and_lock_unchanged"] = original == {
            name: digest(PRODUCT / name) for name in original
        }
        assert receipt["main_manifest_and_lock_unchanged"]
        receipt["passed"] = True
    except Exception as error:
        receipt.update(error_type=type(error).__name__, error=str(error)[:1000])
    receipt["finished_at"] = time.time()
    path.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"passed": receipt["passed"], "receipt": str(path)}))
    return 0 if receipt["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
