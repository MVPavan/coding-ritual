"""Isolated real-image qualification; stdlib only, no public engine requests.

Run from the repository root. Requires Docker access and the pinned image cached.
All evidence goes to scratchpad/dws/searxng-image/fix1/run-<unique-id>.
Use --inject-finalization-failures for a deliberately failing cleanup control.
"""

from __future__ import annotations

import json
import secrets
import subprocess
import sys
import time
from contextlib import suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen

IMAGE = (
    "ghcr.io/searxng/searxng@sha256:"
    "a93b665d10ce0675e8d2124187943111399ba69f384228c51b4cd21fdceda0bc"
)
PYTHON = "/usr/local/searxng/.venv/bin/python"


class Fixture(BaseHTTPRequestHandler):
    """Only a synthetic upstream; the SearXNG engine implementation is unchanged."""

    def do_GET(self) -> None:
        query = parse_qs(urlsplit(self.path).query).get("q", [""])[0]
        status = 503 if query == "unavailable" else 200
        if query == "timeout":
            time.sleep(2)
        payload = json.dumps(
            {
                "items": []
                if query == "empty"
                else [
                    {
                        "url": "https://example.org/dws-fixture",
                        "title": "DWS fixture result",
                        "content": "Synthetic snippet, no fetched page body.",
                    }
                ]
            }
        ).encode()
        if query == "malformed":
            payload = b"not-json"
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        with suppress(BrokenPipeError):
            self.wfile.write(payload)


def request(url: str) -> dict[str, Any]:
    try:
        response = urlopen(url, timeout=8)
    except HTTPError as error:
        response = error
    except URLError as error:
        return {"transport_error": str(error.reason)}
    with response:
        body = response.read().decode()
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = None
        return {"status": response.status, "json": parsed, "body": body}


EXPECTED_FAILURES = {
    "malformed": "parsing error",
    "timeout": "timeout",
    "unavailable": "HTTP error",
}
TRACKER_MARKERS = (
    "TRACKER_PATTERNS",
    "cdn.jsdelivr.net",
    "rules1.clearurls.xyz",
    "rules2.clearurls.xyz",
)


def assert_failure(query: str, body: dict[str, Any]) -> None:
    assert body["results"] == [], body
    assert body["unresponsive_engines"] == [["dws-fixture", EXPECTED_FAILURES[query]]], body


def qualify(*, inject_finalization_failures: bool = False) -> None:
    root = Path(__file__).resolve().parents[3]
    unique = secrets.token_hex(4)
    prefix = f"dws-searxng-{unique}"
    out = root / "scratchpad/dws/searxng-image/fix1" / f"run-{unique}"
    out.mkdir(parents=True)
    print(out, flush=True)
    config = root / "dws/docker/searxng"
    created: list[str] = []
    network_created = False
    results: dict[str, Any] = {}
    primary_error: BaseException | None = None
    finalization_errors: list[Exception] = []
    cleanup_attempts: list[list[str]] = []

    def docker(*args: str) -> str:
        completed = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=90, check=False
        )
        if completed.returncode:
            raise RuntimeError(f"docker {args[0]} failed: {completed.stderr}")
        return completed.stdout + (completed.stderr if args[0] == "logs" else "")

    def start(name: str, extra: list[str], command: list[str]) -> None:
        docker(
            "create",
            "--name",
            name,
            "--label",
            f"dws.searxng.probe={unique}",
            "--network",
            prefix,
            "--user",
            "977:977",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--read-only",
            "--memory",
            "512m",
            "--memory-swap",
            "512m",
            "--cpus",
            "1",
            "--pids-limit",
            "128",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=32m,uid=977,gid=977",
            "--tmpfs",
            "/var/cache/searxng:rw,noexec,nosuid,size=32m,uid=977,gid=977",
            *extra,
            IMAGE,
            *command,
        )
        created.append(name)
        docker("start", name)

    def client(path: str, target: str = "service") -> dict[str, Any]:
        return cast(
            dict[str, Any],
            json.loads(
                docker(
                    "exec",
                    f"{prefix}-fixture",
                    PYTHON,
                    "/probe.py",
                    "request",
                    f"http://{prefix}-{target}:8080{path}",
                )
            ),
        )

    try:
        results["image"] = json.loads(docker("image", "inspect", IMAGE))[0]
        docker(
            "network", "create", "--internal", "--label", f"dws.searxng.probe={unique}", prefix
        )
        network_created = True
        start(
            f"{prefix}-fixture",
            [
                "--tmpfs",
                "/etc/searxng:rw,noexec,nosuid,size=1m,uid=977,gid=977",
                "--mount",
                f"type=bind,src={Path(__file__).resolve()},dst=/probe.py,readonly",
                "--entrypoint",
                PYTHON,
            ],
            ["/probe.py", "fixture"],
        )
        base = (config / "settings.yml").read_text()
        fixture_settings = base.replace("keep_only: [duckduckgo, wikipedia]", "keep_only: []")
        fixture_settings += f"""
engines:
  - name: dws-fixture
    engine: json_engine
    enable_http: true
    shortcut: dwstest
    categories: general
    search_url: 'http://{prefix}-fixture:8081/?q={{query}}'
    results_query: items
    url_query: url
    title_query: title
    content_query: content
    timeout: 0.5
"""
        for role, settings in [
            ("service", fixture_settings),
            ("nojson", fixture_settings.replace("formats: [html, json]", "formats: [html]")),
            ("candidate", base),
            # Negative config control: inactive still initializes in this pinned build.
            (
                "tracker-control",
                base.replace(
                    "plugins:\n",
                    "plugins:\n  searx.plugins.tracker_url_remover.SXNGPlugin:\n"
                    "    active: false\n",
                ),
            ),
        ]:
            directory = out / role
            directory.mkdir()
            (directory / "settings.yml").write_text(settings)
            start(
                f"{prefix}-{role}",
                [
                    "--mount",
                    f"type=bind,src={directory},dst=/etc/searxng,readonly",
                    "--mount",
                    f"type=bind,src={config / 'healthcheck.py'},dst=/healthcheck.py,readonly",
                    "--env",
                    f"SEARXNG_SECRET={secrets.token_hex(32)}",
                    "--env",
                    "GRANIAN_HOST=0.0.0.0",
                    "--env",
                    "GRANIAN_WORKERS=1",
                    "--env",
                    "FORCE_OWNERSHIP=false",
                ],
                [],
            )
            for _ in range(30):
                health = client("/healthz", role)
                if health.get("status") == 200:
                    break
                time.sleep(1)
            else:
                raise RuntimeError(f"{role} failed startup")
            results[f"{role}_config"] = client("/config", role)
            if role != "nojson":
                docker("exec", f"{prefix}-{role}", PYTHON, "/healthcheck.py")
            plugins = results[f"{role}_config"]["json"]["plugins"]
            tracker = [p for p in plugins if p["name"] == "tracker_url_remover"]
            startup_log = docker("logs", f"{prefix}-{role}")
            (out / f"{role}.startup.log").write_text(startup_log)
            markers = [marker for marker in TRACKER_MARKERS if marker in startup_log]
            results[f"{role}_tracker"] = {"plugins": tracker, "log_markers": markers}
            if role == "tracker-control":
                assert tracker == [{"name": "tracker_url_remover", "enabled": False}], tracker
                assert set(markers) == set(TRACKER_MARKERS), startup_log
            else:
                assert not tracker and not markers, (tracker, markers)
        assert [e["name"] for e in results["service_config"]["json"]["engines"]] == [
            "dws-fixture"
        ]
        results["no_query"] = client("/search?format=json")
        assert results["no_query"]["status"] == 400
        results["json_disabled"] = client("/search?q=fixture&format=json", "nojson")
        assert results["json_disabled"]["status"] == 403
        for query in ["success", "empty", "malformed", "timeout", "unavailable"]:
            # Fresh engine suspension state for each failure class.
            if query in {"timeout", "unavailable"}:
                docker("restart", f"{prefix}-service")
                for _ in range(30):
                    if client("/healthz").get("status") == 200:
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError("service restart failed")
            response = client(
                "/search?" + urlencode({"q": query, "format": "json", "engines": "dws-fixture"})
            )
            results[query] = response
            assert response["status"] == 200, response
            body = response["json"]
            assert isinstance(body["results"], list)
            if query == "success":
                assert body["results"][0]["url"] == "https://example.org/dws-fixture"
                assert not body["unresponsive_engines"]
            elif query == "empty":
                assert body["results"] == [] and body["unresponsive_engines"] == []
            else:
                assert_failure(query, body)
                # Regression control on the actual response, not another fake service.
                wrong = dict(body, unresponsive_engines=[["dws-fixture", "wrong category"]])
                try:
                    assert_failure(query, wrong)
                except AssertionError:
                    results.setdefault("wrong_category_rejected", []).append(query)
                else:
                    raise AssertionError(f"wrong {query} category was accepted")
        assert not results["candidate_config"]["json"]["limiter"]["enabled"]
        assert {e["name"] for e in results["candidate_config"]["json"]["engines"]} == {
            "duckduckgo",
            "wikipedia",
        }
        results["confinement"] = docker(
            "exec",
            f"{prefix}-service",
            "/bin/sh",
            "-c",
            "id; cat /proc/1/status; cat /proc/mounts",
        )
        results["stats"] = docker("stats", "--no-stream", "--format", "{{json .}}", *created)
        docker("stop", f"{prefix}-service")
        results["service_unavailable"] = client("/search?q=fixture&format=json")
        assert "transport_error" in results["service_unavailable"]
        # Include restarts in the absence check, not only the first startup.
        for role in ["service", "nojson", "candidate"]:
            log = docker("logs", f"{prefix}-{role}")
            assert not any(marker in log for marker in TRACKER_MARKERS), role
        if inject_finalization_failures:
            raise RuntimeError("INJECTED primary operation error after real API checks")
        results["outcome"] = "PASS"
    except BaseException as error:
        primary_error = error
        results["outcome"] = "FAIL"
    finally:
        # Each evidence operation is independent, and cleanup is outside its failure path.
        try:
            for index, name in enumerate(created):
                try:
                    if inject_finalization_failures and index == 0:
                        raise RuntimeError("INJECTED log collection failure")
                    (out / f"{name}.log").write_text(docker("logs", name))
                except Exception as error:
                    finalization_errors.append(error)
                try:
                    # Never persist Config.Env (contains the ephemeral signing secret).
                    inspection = json.loads(docker("inspect", name))[0]
                    (out / f"{name}.inspect.json").write_text(
                        json.dumps(
                            {
                                k: inspection[k]
                                for k in [
                                    "Id",
                                    "State",
                                    "HostConfig",
                                    "Mounts",
                                    "NetworkSettings",
                                ]
                            },
                            indent=2,
                        )
                    )
                except Exception as error:
                    finalization_errors.append(error)
            try:
                (out / "results.json").write_text(json.dumps(results, indent=2))
            except Exception as error:
                finalization_errors.append(error)
        finally:
            # No discovery or broad deletion: only names successfully created by this run.
            for index, name in enumerate(reversed(created)):
                command = ["rm", "--force", "--volumes", name]
                cleanup_attempts.append(command)
                try:
                    docker(*command)
                    if inject_finalization_failures and index == 0:
                        # Simulate a lost success acknowledgement. Resource is removed,
                        # but the cleanup caller sees an error and must continue.
                        raise RuntimeError("INJECTED removal acknowledgement failure")
                except Exception as error:
                    finalization_errors.append(error)
            if network_created:
                command = ["network", "rm", prefix]
                cleanup_attempts.append(command)
                try:
                    docker(*command)
                except Exception as error:
                    finalization_errors.append(error)
        summary = {
            "outcome": "FAIL" if primary_error or finalization_errors else "PASS",
            "evidence": str(out),
            "owned_containers": created,
            "owned_network": prefix if network_created else None,
            "cleanup_attempts": cleanup_attempts,
            "primary_error": repr(primary_error) if primary_error else None,
            "finalization_errors": [repr(error) for error in finalization_errors],
        }
        try:
            (out / "finalization.json").write_text(json.dumps(summary, indent=2))
        except Exception as error:
            finalization_errors.append(error)
            summary["outcome"] = "FAIL"
            summary["finalization_errors"] = [repr(error) for error in finalization_errors]
        print(json.dumps(summary), flush=True)
    errors: list[BaseException] = []
    if primary_error is not None:
        errors.append(primary_error)
    errors.extend(finalization_errors)
    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise BaseExceptionGroup(
            "Qualification and finalization errors (primary first)", errors
        )


if __name__ == "__main__":
    if sys.argv[1:] == ["fixture"]:
        ThreadingHTTPServer(("0.0.0.0", 8081), Fixture).serve_forever()
    elif sys.argv[1:2] == ["request"]:
        print(json.dumps(request(sys.argv[2])))
    elif sys.argv[1:] == ["--inject-finalization-failures"]:
        qualify(inject_finalization_failures=True)
    elif not sys.argv[1:]:
        qualify()
    else:
        raise SystemExit("expected no arguments or --inject-finalization-failures")
