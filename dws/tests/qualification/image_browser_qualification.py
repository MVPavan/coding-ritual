"""Opt-in protective-overlay qualification against real isolated browser transports.

Run from repository root with --output under scratchpad/dws/browser-containment/.
No host ports, extra capabilities, external traffic, or shared runtime state.
A partial/failed fixture is not a passing qualification. Raw baseline is preserved.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

BASE = (
    "unclecode/crawl4ai@sha256:bd36741e7bdd35ddc1a05d9183e1d6d8cefb61dd640d944a25d026b76e917690"
)
PUBLIC4 = "11.203.0.3"
PUBLIC6 = "2001:4860:abcd:71::3"
QUALIFICATION = Path(__file__).resolve().parent


def extract_state(html: str) -> dict[str, Any]:
    """Read the executed DOM state node, never marker strings in page source."""

    class Parser(HTMLParser):
        active = False
        parts: list[str]

        def __init__(self) -> None:
            super().__init__()
            self.parts = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag == "pre" and dict(attrs).get("id") == "dws-state":
                self.active = True

        def handle_endtag(self, tag: str) -> None:
            if tag == "pre":
                self.active = False

        def handle_data(self, data: str) -> None:
            if self.active:
                self.parts.append(data)

    parser = Parser()
    parser.feed(html)
    try:
        value = json.loads("".join(parser.parts))
        return dict(value) if isinstance(value, dict) else {}
    except ValueError:
        return {}


def case_failures(case: dict[str, Any]) -> list[str]:
    """Executable receipt contract; also exercised by destructive receipt mutations."""
    failures = []
    name = case["name"]
    status = case["response"]["status"]
    events = [event for group in case["events"].values() for event in group]
    public = case["positive"] or name.startswith("webtransport-")
    scripted = public or name.endswith("-resources")
    if case["forbidden"]:
        failures.append("forbidden-receipt")
    if scripted:
        state = case.get("state", {})
        if status != 200 or not case["rendered"]:
            failures.append("rendering")
        if not case.get("actions_complete") or state.get("complete") is not True:
            failures.append("actions-completion")
        for action in ("fetch", "beacon", "img", "script", "iframe", "ws", "stun:", "turn:"):
            observed = state.get("actions", {}).get(action, {})
            if observed.get("issued") is not True:
                failures.append("action-issued-" + action)
            if action not in ("stun:", "turn:") and observed.get("constructed") is not True:
                failures.append("action-constructed-" + action)
    if public:
        if not case["websocket_open"]:
            failures.append("websocket-open")
        paths = {event.get("path") for event in events if event["kind"] == "http"}
        for resource in ("fetch", "beacon", "img", "script", "iframe", "ws"):
            if "/positive/" + resource not in paths:
                failures.append("resource-" + resource)
        if not any(
            event["kind"] == "turn_data"
            and event["bytes"] >= 20
            and event["prefix_hex"].startswith("0003")
            and event["prefix_hex"][8:16] == "2112a442"
            for event in events
        ):
            failures.append("turn-allocate")
    if name.startswith("webtransport-"):
        wt = case.get("state", {}).get("webtransport", {})
        if (
            wt.get("available") is not True
            or wt.get("issued") is not True
            or wt.get("constructed") is not True
            or wt.get("error") is not None
            or wt.get("target") != case["wt_target"]
        ):
            failures.append("webtransport-construction")
    if name.startswith("tls-"):
        if status != 500:
            failures.append("tls-status")
        if not any(
            e["kind"] == "tcp" and e["port"] == urlsplit(case["url"]).port for e in events
        ):
            failures.append("tls-tcp-reached")
        if any(e["kind"] == "http" for e in events):
            failures.append("tls-http-leak")
    expected = None
    if name.endswith("-direct") or name.startswith("mixed"):
        expected = 400
    elif name.endswith(("-redirect", "-connect")) or name.startswith("rebind"):
        expected = 500
    elif name.startswith("bypass-"):
        expected = 422 if name == "bypass-python-hook" else 400
    if expected is not None and status != expected:
        failures.append("denial-status")
    return failures


def quic_initial(event: dict[str, Any]) -> bool:
    """Recognize a padded QUIC v1 Initial long header, not an arbitrary UDP hit."""
    if event.get("kind") != "udp" or event.get("port") != 443 or event.get("bytes", 0) < 1200:
        return False
    data = bytes.fromhex(event.get("prefix_hex", ""))
    if len(data) < 8 or data[0] & 0xF0 != 0xC0 or data[1:5] != b"\x00\x00\x00\x01":
        return False
    try:
        dcid = data[5]
        if not 1 <= dcid <= 20:
            return False
        offset = 6 + dcid
        scid = data[offset]
        if scid > 20:
            return False
        offset += 1 + scid
        # Initial, fresh context: no server-issued retry token.
        if data[offset] != 0:
            return False
        offset += 1
        size = 1 << (data[offset] >> 6)
        encoded = data[offset : offset + size]
        if len(encoded) != size:
            return False
        length = int.from_bytes(encoded, "big") & ((1 << (8 * size - 2)) - 1)
        return length >= 17 and offset + size + length <= event["bytes"]
    except IndexError:
        return False


def assertion_sensitivity(cases: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Remove evidence from actual passing cases; each mutation must be rejected."""
    checks = []
    public = next(case for case in cases if case["positive"])
    if case_failures(public):
        raise RuntimeError("cannot calibrate assertions against a failing positive case")
    for resource in ("fetch", "beacon", "img", "script", "iframe", "ws", "turn"):
        altered = copy.deepcopy(public)
        for events in altered["events"].values():
            events[:] = [
                event
                for event in events
                if not (
                    event["kind"] == "turn_data"
                    if resource == "turn"
                    else event.get("path") == "/positive/" + resource
                )
            ]
        reason = "turn-allocate" if resource == "turn" else "resource-" + resource
        if reason not in case_failures(altered):
            raise RuntimeError("receipt mutation escaped assertion: " + resource)
        checks.append({"mutation": "remove " + resource + " receipts", "rejected_by": reason})
    resource_case = next(case for case in cases if case["name"].endswith("-resources"))
    for field in ("actions_complete", "state_complete"):
        altered = copy.deepcopy(resource_case)
        if field == "actions_complete":
            altered[field] = False
        else:
            altered["state"]["complete"] = False
        if "actions-completion" not in case_failures(altered):
            raise RuntimeError("missing completion evidence accepted")
        checks.append({"mutation": "remove " + field, "rejected_by": "actions-completion"})
    tls = next(case for case in cases if case["name"] == "tls-untrusted")
    altered = copy.deepcopy(tls)
    for events in altered["events"].values():
        events[:] = [event for event in events if event["kind"] != "tcp"]
    if "tls-tcp-reached" not in case_failures(altered):
        raise RuntimeError("missing TLS TCP evidence accepted")
    checks.append({"mutation": "remove TLS TCP", "rejected_by": "tls-tcp-reached"})
    altered = copy.deepcopy(tls)
    next(iter(altered["events"].values())).append({"kind": "http", "path": "/page"})
    if "tls-http-leak" not in case_failures(altered):
        raise RuntimeError("TLS HTTP leak accepted")
    checks.append({"mutation": "insert TLS HTTP leak", "rejected_by": "tls-http-leak"})
    return checks


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    prefix = "dws-browser-containment-" + uuid.uuid4().hex[:10]
    containers: list[str] = []
    networks: list[str] = []
    built = False
    result: dict[str, Any] = {"prefix": prefix, "base": BASE, "cases": [], "cleanup": []}

    def command(argv: list[str], check: bool = True, timeout: int = 90) -> str:
        start = time.monotonic()
        cp = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        with (output / "commands.jsonl").open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "argv": argv,
                        "rc": cp.returncode,
                        "seconds": time.monotonic() - start,
                        "stdout": cp.stdout,
                        "stderr": cp.stderr,
                    }
                )
                + "\n"
            )
        if check and cp.returncode:
            raise RuntimeError(f"command failed: {argv[:3]}: {cp.stderr[:1000]}")
        return cp.stdout

    def docker(*args: str, check: bool = True, timeout: int = 90) -> str:
        return command(["docker", *args], check=check, timeout=timeout)

    def request(container: str, url: str, payload: dict[str, Any] | None = None) -> Any:
        code = """import json,sys,urllib.request,urllib.error
url,body=sys.argv[1:]
r=urllib.request.Request(url,data=None if body=='null' else body.encode(),headers={
'Content-Type':'application/json','Authorization':'Bearer dws-synthetic-test-token'})
try:
 with urllib.request.urlopen(r,timeout=25) as s:
  print(json.dumps({'status':s.status,'body':s.read().decode()}))
except urllib.error.HTTPError as e:
 print(json.dumps({'status':e.code,'body':e.read().decode()}))
"""
        return json.loads(
            docker(
                "exec", container, "python", "-c", code, url, json.dumps(payload), timeout=35
            )
        )

    def observations(container: str) -> list[dict[str, Any]]:
        return list(json.loads(request(container, "http://127.0.0.1:8081/")["body"]))

    fixture_files = output / "fixtures"
    fixture_files.mkdir()
    # Synthetic keys only. No certificate-ignore flags or caller TLS exceptions.
    for name in ("ca", "server", "untrusted"):
        args = [
            "openssl",
            "req",
            "-new",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(fixture_files / f"{name}.key"),
            "-out",
            str(fixture_files / f"{name}.{'csr' if name == 'server' else 'crt'}"),
            "-subj",
            f"/CN=DWS synthetic {name}",
        ]
        if name != "server":
            args += ["-x509", "-days", "2", "-addext", "basicConstraints=critical,CA:TRUE"]
        command(args)
    extensions = fixture_files / "server.ext"
    extensions.write_text(
        "subjectAltName=DNS:public.dws.test,DNS:public6.dws.test\n"
        "basicConstraints=critical,CA:FALSE\nextendedKeyUsage=serverAuth\n"
    )
    command(
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            str(fixture_files / "server.csr"),
            "-CA",
            str(fixture_files / "ca.crt"),
            "-CAkey",
            str(fixture_files / "ca.key"),
            "-CAcreateserial",
            "-out",
            str(fixture_files / "server.crt"),
            "-days",
            "2",
            "-extfile",
            str(extensions),
        ]
    )
    for path in fixture_files.iterdir():
        path.chmod(0o644)  # disposable synthetic keys readable by container UID 999
    common = [
        "--memory",
        "2g",
        "--cpus",
        "2",
        "--pids-limit",
        "256",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--shm-size",
        "256m",
        "--mount",
        f"type=bind,src={fixture_files.resolve()},dst=/fixtures,readonly",
    ]
    for name in ("browser_containment_fixture.py", "browser_fixture_trust.py"):
        common += ["--mount", f"type=bind,src={QUALIFICATION / name},dst=/{name},readonly"]
    try:
        docker(
            "build",
            "--network",
            "none",
            "--pull=false",
            "-t",
            prefix,
            "dws/docker/crawl4ai-egress",
            timeout=120,
        )
        built = True
        info = json.loads(docker("image", "inspect", prefix))[0]
        image = info["Id"]
        result["image_metadata"] = info
        # Exercise actual missing-proxy and forbidden owner-environment failures.
        guards = {
            "missing_proxy": [
                "-c",
                "from crawl4ai import BrowserConfig; from egress_broker "
                "import enforce_egress; enforce_egress(BrowserConfig())",
            ],
            "internal_escape": [
                "-c",
                "import os; os.environ['CRAWL4AI_ALLOW_INTERNAL_URLS']="
                "'true'; import egress_broker",
            ],
            "tls_escape": [
                "-c",
                "import os; os.environ['CRAWL4AI_ALLOW_INSECURE_TLS']="
                "'true'; import egress_broker",
            ],
        }
        result["guards"] = {}
        for name, args in guards.items():
            docker(
                "run",
                "--rm",
                "--name",
                prefix + "-guard",
                "--network",
                "none",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--memory",
                "256m",
                "--pids-limit",
                "64",
                "--entrypoint",
                "python",
                image,
                *args,
                check=False,
            )
            receipt = json.loads((output / "commands.jsonl").read_text().splitlines()[-1])
            result["guards"][name] = {"rc": receipt["rc"], "stderr": receipt["stderr"]}
            if receipt["rc"] != 1 or "RuntimeError: DWS" not in receipt["stderr"]:
                raise RuntimeError(f"fail-closed guard not proved: {name}")
        definitions = [
            (
                "public",
                ["--subnet", "11.203.0.0/24", "--ipv6", "--subnet", "2001:4860:abcd:71::/64"],
            ),
            ("private", ["--ipv6", "--subnet", "fd71:d05::/64"]),
            ("metadata", ["--subnet", "169.254.169.0/24"]),
            ("nat64", ["--ipv6", "--subnet", "64:ff9b::a00:0/120"]),
            ("six_to_four", ["--ipv6", "--subnet", "2002:7f00:1::/64"]),
            ("linklocal6", ["--ipv6", "--subnet", "fe80:0:0:71::/64"]),
        ]
        for kind, args in definitions:
            network = prefix + "-" + kind
            docker(
                "network",
                "create",
                "--internal",
                "--label",
                "dws.qualification=" + prefix,
                *args,
                network,
            )
            networks.append(network)
        fixture, browser = prefix + "-fixture", prefix + "-browser"
        connections = [
            (networks[1], ["--ip6", "fd71:d05::3"]),
            (networks[2], ["--ip", "169.254.169.254"]),
            (networks[3], ["--ip6", "64:ff9b::a00:3"]),
            (networks[4], ["--ip6", "2002:7f00:1::3"]),
            (networks[5], ["--ip6", "fe80:0:0:71::3"]),
        ]
        # Start a waiting fixture container, assign addresses, then start observers.
        docker(
            "run",
            "-d",
            "--name",
            fixture,
            *common,
            "--network",
            networks[0],
            "--ip",
            PUBLIC4,
            "--ip6",
            PUBLIC6,
            "--entrypoint",
            "sleep",
            image,
            "900",
        )
        containers.append(fixture)
        for network, args in connections:
            docker("network", "connect", *args, network, fixture)
        fixture_info = json.loads(docker("inspect", fixture))[0]
        private4 = fixture_info["NetworkSettings"]["Networks"][networks[1]]["IPAddress"]
        dns_config: dict[str, Any] = {
            "public.dws.test": [PUBLIC4],
            "public6.dws.test": [PUBLIC6],
            "wrong.dws.test": [PUBLIC4],
            "mixed4.dws.test": [PUBLIC4, private4],
            "mixed6.dws.test": [PUBLIC4, "fd71:d05::3"],
            "rebind4.dws.test": {"type": 1, "first": [PUBLIC4], "later": ["169.254.169.254"]},
            "rebind6.dws.test": {"type": 28, "first": [PUBLIC6], "later": ["fd71:d05::3"]},
        }
        (fixture_files / "dns.json").write_text(json.dumps(dns_config))
        docker("exec", "-d", fixture, "python", "/browser_containment_fixture.py")
        docker(
            "run",
            "-d",
            "--name",
            browser,
            *common,
            "--network",
            networks[0],
            "--ip",
            "11.203.0.2",
            "--ip6",
            "2001:4860:abcd:71::2",
            "--dns",
            PUBLIC4,
            "-e",
            "CRAWL4AI_API_TOKEN=dws-synthetic-test-token",
            "--entrypoint",
            "bash",
            image,
            "-c",
            "python /browser_fixture_trust.py && exec bash entrypoint.sh",
        )
        containers.append(browser)
        for network in networks[1:]:
            docker("network", "connect", network, browser)
        docker("exec", "-d", browser, "python", "/browser_containment_fixture.py")
        for _ in range(20):
            health = docker(
                "exec", browser, "curl", "-sf", "http://127.0.0.1:11235/health", check=False
            )
            if health:
                result["health"] = json.loads(health)
                break
            time.sleep(1)
        else:
            raise RuntimeError("provider startup failed within bounded wait")
        result["startup_processes"] = docker("top", browser, "-eo", "pid,args")
        # Explicit test-only direct-browser positive control. It shares only
        # the synthetic public network, uses normal TLS, and never fetches a
        # forbidden target. It bypasses Crawl4AI/proxy and omits disable-quic;
        # the production overlay and candidate launch path are unchanged.
        control = prefix + "-quic-control"
        docker(
            "run",
            "-d",
            "--name",
            control,
            *common,
            "--network",
            networks[0],
            "--ip",
            "11.203.0.4",
            "--ip6",
            "2001:4860:abcd:71::4",
            "--dns",
            PUBLIC4,
            "--entrypoint",
            "sleep",
            image,
            "120",
        )
        containers.append(control)
        docker("exec", control, "python", "/browser_fixture_trust.py")
        before_control = len(observations(fixture))
        control_code = """import asyncio,json,pathlib
from playwright.async_api import async_playwright
async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,args=['--no-sandbox','--enable-quic',
            '--force-webrtc-ip-handling-policy=disable_non_proxied_udp',
            '--host-resolver-rules=MAP public6.dws.test [2001:4860:abcd:71::3]'])
        result={'browser_version':browser.version,'cases':[]}
        for host in ['public.dws.test','public6.dws.test']:
            page=await browser.new_page()
            url='https://'+host+':8443/page?to=https://'+host+':8443/positive'
            entry={'url':url}
            try:
                await page.goto(url,wait_until='domcontentloaded',timeout=15000)
                await page.wait_for_function('window.dwsState?.complete === true',timeout=10000)
                await page.wait_for_timeout(3000)
                entry['state']=await page.evaluate('window.dwsState')
                entry['proof']=await page.locator('#proof').text_content()
            except Exception as error:
                entry['error']=str(error)
            finally:
                result['cases'].append(entry)
                await page.close()
        parents=[]
        for path in pathlib.Path('/proc').glob('[0-9]*/cmdline'):
            try:
                argv=path.read_bytes().replace(b'\\x00',b' ').decode(errors='replace')
                if '/chrome-headless-shell ' in argv and ' --type=' not in argv:
                    parents.append(argv)
            except OSError:
                pass
        result['parents']=parents
        await browser.close()
        print(json.dumps(result))
asyncio.run(main())
"""
        control_result = json.loads(
            docker("exec", control, "python", "-c", control_code, timeout=60)
        )
        control_events = observations(fixture)[before_control:]
        result["cleanup"].append(docker("rm", "-f", control))
        containers.remove(control)
        initials = [event for event in control_events if quic_initial(event)]
        source_by_destination = {PUBLIC4: "11.203.0.4", PUBLIC6: "2001:4860:abcd:71::4"}
        calibrated = all(
            any(e["destination"] == destination and e["peer"][0] == source for e in initials)
            for destination, source in source_by_destination.items()
        )
        calibrated = calibrated and all(
            case.get("proof") == "DWS_RENDERED_OK"
            and case["state"]["complete"] is True
            and case["state"]["webtransport"]["constructed"] is True
            and case["state"]["webtransport"]["error"] is None
            for case in control_result["cases"]
        )
        calibrated = (
            calibrated
            and bool(control_result["parents"])
            and all(
                "--disable-quic" not in line
                and "--proxy-server" not in line
                and "--ignore-certificate-errors" not in line
                for line in control_result["parents"]
            )
        )
        result["quic_control"] = {
            "calibrated": calibrated,
            "browser": control_result,
            "events": control_events,
            "quic_initials": initials,
            "difference": "direct Playwright, no proxy, enable-quic; "
            "synthetic public6 hostname mapped to its assigned IPv6; "
            "same binary, TLS trust, nonroot and container restrictions",
        }
        # Sensitivity independent of Chromium/proxy: dial ONLY each observer's
        # own assigned addresses from inside its container; never host gateways.
        sensitivity = """import socket,sys,json,pathlib,ipaddress
addresses=json.loads(sys.argv[1]); out=[]
for ip in addresses:
    family=socket.AF_INET6 if ':' in ip else socket.AF_INET
    for kind,port in [(socket.SOCK_DGRAM,3478),(socket.SOCK_DGRAM,443),
                      (socket.SOCK_STREAM,3478),(socket.SOCK_STREAM,8080)]:
        s=socket.socket(family,kind);s.settimeout(2)
        try:
            scope=0
            if ip.startswith('fe80:'):
                for line in pathlib.Path('/proc/net/if_inet6').read_text().splitlines():
                    fields=line.split()
                    if fields[0]==ipaddress.IPv6Address(ip).packed.hex():
                        scope=socket.if_nametoindex(fields[-1])
            target=(ip,port,0,scope) if family==socket.AF_INET6 else (ip,port)
            s.connect(target);s.send(b'DWS_LISTENER_SENSITIVITY')
            out.append([ip,port,'sent'])
        except OSError as e:
            out.append([ip,port,str(e)])
        finally:
            s.close()
print(json.dumps(out))
"""
        addresses = [
            PUBLIC4,
            PUBLIC6,
            private4,
            "169.254.169.254",
            "fd71:d05::3",
            "64:ff9b::a00:3",
            "2002:7f00:1::3",
            "fe80:0:0:71::3",
        ]
        result["sensitivity"] = {}
        for container, ips in [(fixture, addresses), (browser, ["127.0.0.1", "::1"])]:
            result["sensitivity"][container] = {
                "injections": json.loads(
                    docker("exec", container, "python", "-c", sensitivity, json.dumps(ips))
                ),
                "observations": observations(container),
            }
        targets = {
            "loopback4": "127.0.0.1",
            "private4": private4,
            "metadata": "169.254.169.254",
            "decimal": "2130706433",
            "loopback6": "[::1]",
            "ula": "[fd71:d05::3]",
            "linklocal6": "[fe80:0:0:71::3]",
            "mapped": f"[::ffff:{private4}]",
            "nat64": "[64:ff9b::a00:3]",
            "six_to_four": "[2002:7f00:1::3]",
        }

        def crawl_case(
            name: str,
            url: str,
            positive: bool = False,
            overrides: dict[str, Any] | None = None,
            wt_target: str | None = None,
        ) -> None:
            before = {c: len(observations(c)) for c in (fixture, browser)}
            response = request(
                browser,
                "http://127.0.0.1:11235/crawl",
                {
                    "urls": [url],
                    "crawler_config": {
                        "type": "CrawlerRunConfig",
                        "params": {"delay_before_return_html": 1.5, "page_timeout": 7000},
                    },
                    **(overrides or {}),
                },
            )
            delta = {c: observations(c)[count:] for c, count in before.items()}
            forbidden = [
                event
                for events in delta.values()
                for event in events
                if event["kind"] in ("tcp", "udp")
                and event["destination"] not in (PUBLIC4, PUBLIC6)
            ]
            items = json.loads(response["body"]).get("results", [])
            markdown = "\n".join(
                item.get("markdown", {}).get("raw_markdown", "") for item in items
            )
            result["cases"].append(
                {
                    "name": name,
                    "url": url,
                    "positive": positive,
                    "response": response,
                    "events": delta,
                    "forbidden": forbidden,
                    "rendered": "DWS_RENDERED_OK" in markdown,
                    "websocket_open": "DWS_WS_OPEN" in markdown,
                    "markdown": markdown,
                    "actions_complete": "DWS_ACTIONS_ISSUED" in markdown,
                    "state": extract_state(items[0].get("html", "")) if items else {},
                    "wt_target": wt_target,
                }
            )
            (output / "progress.json").write_text(
                json.dumps(
                    {
                        "last_case": name,
                        "cases": len(result["cases"]),
                        "forbidden_events": len(forbidden),
                    }
                )
            )

        for host in ("public.dws.test", "public6.dws.test"):
            for scheme, port in (("http", 8080), ("https", 8443)):
                base = f"{scheme}://{host}:{port}"
                page = f"{base}/page?to={quote(base + '/positive', safe='')}"
                crawl_case(f"positive-{host}-{scheme}", page, True)
                crawl_case(
                    f"redirect-{host}-{scheme}",
                    base + "/redirect?to=" + quote(page, safe=""),
                    True,
                )
        crawl_case("tls-untrusted", "https://public.dws.test:8444/page")
        crawl_case("tls-wrong-host", "https://wrong.dws.test:8443/page")
        base = "http://public.dws.test:8080"
        for name, target in targets.items():
            destination = f"http://{target}:8080/forbidden-{name}"
            crawl_case(name + "-direct", destination)
            crawl_case(name + "-redirect", base + "/redirect?to=" + quote(destination, safe=""))
            crawl_case(name + "-resources", base + "/page?to=" + quote(destination, safe=""))
            # HTTPS exercises CONNECT to the forbidden destination through redirects.
            crawl_case(
                name + "-connect",
                base
                + "/redirect?to="
                + quote(f"https://{target}:8443/forbidden-{name}", safe=""),
            )
        secure = "https://public.dws.test:8443"
        for name in ("loopback4", "metadata", "loopback6", "ula"):
            wt_target = f"https://{targets[name]}:443/transport"
            crawl_case(
                "webtransport-" + name,
                secure
                + "/page?to="
                + quote(secure + "/positive", safe="")
                + "&wt="
                + quote(wt_target, safe=""),
                wt_target=wt_target,
            )
        for host in ("mixed4", "mixed6", "rebind4", "rebind6"):
            crawl_case(host, f"http://{host}.dws.test:8080/forbidden-{host}")
        bypasses: dict[str, dict[str, Any]] = {
            "python-hook": {
                "hooks": {"hooks": {"before_goto": "raise Exception('synthetic')"}}
            },
        }
        for field, value in {
            "proxy": "http://127.0.0.1:8080",
            "cdp_url": "http://127.0.0.1:8080",
            "extra_args": [
                "--force-webrtc-ip-handling-policy=default",
                "--enable-quic",
                "--ignore-certificate-errors",
                "--host-resolver-rules=MAP * 127.0.0.1",
            ],
        }.items():
            bypasses[field] = {
                "browser_config": {"type": "BrowserConfig", "params": {field: value}}
            }
        for name, payload in bypasses.items():
            crawl_case("bypass-" + name, base + "/page", overrides=payload)
        result["final_processes"] = docker("top", browser, "-eo", "pid,args")
        result["resources"] = docker("stats", "--no-stream", "--format", "{{json .}}", browser)
        result["container"] = json.loads(docker("inspect", browser))[0]
        result["all_observations"] = {c: observations(c) for c in (fixture, browser)}
        result["networks"] = [json.loads(docker("network", "inspect", n))[0] for n in networks]
        for case in result["cases"]:
            case["assertion_failures"] = case_failures(case)
        failed = [c["name"] for c in result["cases"] if c["assertion_failures"]]
        result["assertion_sensitivity"] = assertion_sensitivity(result["cases"])
        # Include traffic between case windows, after listener calibration.
        all_live = [
            event
            for container, events in result["all_observations"].items()
            for event in events[len(result["sensitivity"][container]["observations"]) :]
        ]
        result["global_forbidden"] = [
            event
            for event in all_live
            if event["kind"] in ("tcp", "udp")
            and (event["kind"] == "udp" or event["destination"] not in (PUBLIC4, PUBLIC6))
        ]
        if result["global_forbidden"]:
            failed.append("global-forbidden-receipts")
        dns = [e for e in all_live if e["kind"] == "dns"]
        expected_dns = {
            "mixed4.dws.test": ([PUBLIC4, private4],),
            "mixed6.dws.test": ([PUBLIC4], ["fd71:d05::3"]),
            "rebind4.dws.test": ([PUBLIC4], ["169.254.169.254"]),
            "rebind6.dws.test": ([PUBLIC6], ["fd71:d05::3"]),
        }
        result["dns_receipt_failures"] = []
        for host, answers in expected_dns.items():
            observed = [
                event["answers"] for event in dns if event["name"] == host and event["answers"]
            ]
            if (
                any(answer not in observed for answer in answers)
                or host.startswith("rebind")
                and observed.index(answers[0]) >= observed.index(answers[1])
            ):
                result["dns_receipt_failures"].append(host)
        if result["dns_receipt_failures"]:
            failed.append("dns-receipts")
        if not result["quic_control"]["calibrated"]:
            failed.append("quic-control-inconclusive")
        sensitivity_gaps = []
        for observation in result["sensitivity"].values():
            seen = {
                (e["kind"], e.get("destination"), e.get("port"))
                for e in observation["observations"]
                if e["kind"] in ("tcp", "udp")
            }
            for ip, port, outcome in observation["injections"]:
                # Both TCP and UDP are injected on 3478; require both receipts.
                kinds = (
                    ("tcp", "udp") if port == 3478 else (("udp",) if port == 443 else ("tcp",))
                )
                if outcome != "sent" or any((kind, ip, port) not in seen for kind in kinds):
                    sensitivity_gaps.append([ip, port, outcome])
        result["sensitivity_gaps"] = sensitivity_gaps
        if sensitivity_gaps:
            failed.append("listener-sensitivity")
        result["launch_checks"] = []
        for stage in ("startup_processes", "final_processes"):
            parents = [
                line
                for line in result[stage].splitlines()
                if "/chrome-headless-shell " in line and " --type=" not in line
            ]
            ok = bool(parents) and all(
                "--force-webrtc-ip-handling-policy=disable_non_proxied_udp" in line
                and "--disable-quic" in line
                and "--proxy-server=http://127.0.0.1:" in line
                and "--ignore-certificate-errors" not in line
                for line in parents
            )
            result["launch_checks"].append({"stage": stage, "ok": ok, "parents": parents})
            if not ok:
                failed.append(stage + "-policy")
        result["failed_cases"] = failed
        result["verdict"] = "FAIL" if failed else "OBSERVED_CASES_PASS_REVIEW_REQUIRED"
    except BaseException as exc:
        result["error"] = repr(exc)
        result["verdict"] = "INCOMPLETE"
        raise
    finally:
        for name in reversed(containers):
            docker("logs", "--tail", "150", name, check=False)
            result["cleanup"].append(docker("rm", "-f", name, check=False))
        for name in reversed(networks):
            result["cleanup"].append(docker("network", "rm", name, check=False))
        if built:
            result["cleanup"].append(docker("image", "rm", prefix, check=False))
        result["source_sha256"] = {
            str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [
                Path(__file__),
                QUALIFICATION / "browser_containment_fixture.py",
                QUALIFICATION / "browser_fixture_trust.py",
                Path("dws/docker/crawl4ai-egress/patch.py"),
                Path("dws/docker/crawl4ai-egress/Dockerfile"),
            ]
        }
        (output / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"verdict": result["verdict"], "failed_cases": result["failed_cases"]}))
    if result["failed_cases"]:
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
