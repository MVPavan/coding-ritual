"""Apply only to the audited provider source; abort on hash/context drift."""

from __future__ import annotations

import hashlib
from pathlib import Path

BROKER = Path("/app/egress_broker.py")
MANAGER = Path("/usr/local/lib/python3.12/site-packages/crawl4ai/browser_manager.py")
EXPECTED = {
    BROKER: "9884e0a4d972607e1cd20aa70bf5d8d86767fe3d61a53ebc6bd3776880c822cf",
    MANAGER: "76724e47ccace4cee8c5b654f3c132744d30d9a98706984d77517be06a317c3d",
}


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"patch context count is not one: {old[:80]}")
    return text.replace(old, new, 1)


def main() -> None:
    sources = {path: path.read_text() for path in EXPECTED}
    for path, digest in EXPECTED.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"unrecognized base source: {path}")
    broker = sources[BROKER]
    broker = replace_once(
        broker,
        'ALLOW_INTERNAL = os.environ.get("CRAWL4AI_ALLOW_INTERNAL_URLS", '
        '"false").lower() == "true"',
        """ALLOW_INTERNAL = False
if os.environ.get("CRAWL4AI_ALLOW_INTERNAL_URLS", "false").lower() != "false":
    raise RuntimeError("DWS provider forbids internal-target escape hatch")""",
    )
    broker = replace_once(
        broker,
        'ALLOW_INSECURE_TLS = os.environ.get("CRAWL4AI_ALLOW_INSECURE_TLS", '
        '"false").lower() == "true"',
        """ALLOW_INSECURE_TLS = False
if os.environ.get("CRAWL4AI_ALLOW_INSECURE_TLS", "false").lower() != "false":
    raise RuntimeError("DWS provider forbids insecure TLS")""",
    )
    # Preserve the single upstream resolver/pinning policy. Replace only its
    # browser-configuration enforcement tail (verified by base hash above).
    marker = "# Chromium flags that would re-route or weaken egress; scrubbed server-side."
    if broker.count(marker) != 1:
        raise RuntimeError("missing enforcement tail")
    broker = (
        broker[: broker.index(marker)]
        + '''# DWS provider overlay: one owner for launch policy; no caller exceptions.
_DANGEROUS_BROWSER_ARGS = (
    "--proxy-", "--host-resolver-rules", "--ignore-certificate-errors",
    "--allow-insecure-localhost", "--force-webrtc-ip-handling-policy",
    "--enable-quic", "--disable-quic",
)
_REQUIRED_BROWSER_ARGS = (
    "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
    "--disable-quic",
)


def enforce_egress(browser_config) -> None:
    """Require the live pinning proxy before any browser can be constructed."""
    if browser_config is None:
        raise RuntimeError("DWS browser configuration missing")
    if browser_config.browser_type != "chromium" or browser_config.cdp_url:
        raise RuntimeError("DWS only qualifies locally launched Chromium")
    proxy = urlparse(_EGRESS_PROXY_URL or "")
    if proxy.scheme != "http" or proxy.hostname != "127.0.0.1" or not proxy.port:
        raise RuntimeError("DWS pinning proxy is not initialized")
    from crawl4ai import ProxyConfig
    browser_config.ignore_https_errors = False
    browser_config.proxy = None
    # Do not swallow import, validation or construction failures.
    browser_config.proxy_config = ProxyConfig(server=_EGRESS_PROXY_URL)
    browser_config.extra_args = [
        str(arg) for arg in (browser_config.extra_args or [])
        if not any(str(arg).startswith(prefix) for prefix in _DANGEROUS_BROWSER_ARGS)
    ] + list(_REQUIRED_BROWSER_ARGS)
'''
    )
    manager = sources[MANAGER]
    manager = replace_once(
        manager,
        '        """Common CLI flags for launching Chromium"""\n        flags = [',
        '''        """Common CLI flags for launching Chromium"""
        from egress_broker import enforce_egress
        enforce_egress(config)
        flags = [''',
    )
    manager = replace_once(
        manager,
        "        # dedupe\n        return list(dict.fromkeys(flags))",
        """        flags.extend(config.extra_args)
        # dedupe
        return list(dict.fromkeys(flags))""",
    )
    manager = replace_once(
        manager,
        "        self.config: BrowserConfig = browser_config\n",
        """        from egress_broker import enforce_egress
        enforce_egress(browser_config)
        self.config: BrowserConfig = browser_config
""",
    )
    manager = replace_once(
        manager,
        '        """Build browser launch arguments from config."""\n        args = [',
        '''        """Build browser launch arguments from config."""
        from egress_broker import enforce_egress
        enforce_egress(self.config)
        args = [''',
    )
    manager = replace_once(
        manager,
        '        """Returns full CLI args for launching the browser"""\n',
        '''        """Returns full CLI args for launching the browser"""
        from egress_broker import enforce_egress
        enforce_egress(self.browser_config)
''',
    )
    for flag in ("--ignore-certificate-errors", "--ignore-certificate-errors-spki-list"):
        line = f'            "{flag}",\n'
        if manager.count(line) != 2:
            raise RuntimeError("TLS flag context drift")
        manager = manager.replace(line, "")
    for path, text in ((BROKER, broker), (MANAGER, manager)):
        compile(text, str(path), "exec")
        path.write_text(text)
        print(f"{path}: {hashlib.sha256(text.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
