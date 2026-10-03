"""Real HTTP evidence sources used by the product journeys."""

from __future__ import annotations

import gzip
import json
import threading
from contextlib import AbstractContextManager, suppress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit


def text_pdf(text: str | list[str]) -> bytes:
    """Create a valid PDF with explicit physical pages and no generator dependency."""
    pages = [text] if isinstance(text, str) else text
    children = " ".join(f"{4 + 2 * index} 0 R" for index in range(len(pages)))
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{children}] /Count {len(pages)} >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    for index, page in enumerate(pages):
        escaped = page.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 12 Tf 50 750 Td ({escaped}) Tj ET".encode("ascii")
        objects.extend(
            [
                b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                b"/Resources << /Font << /F1 3 0 R >> >> /Contents "
                + f"{5 + 2 * index} 0 R >>".encode(),
                b"<< /Length "
                + str(len(stream)).encode()
                + b" >>\nstream\n"
                + stream
                + b"\nendstream",
            ]
        )
    document = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, item in enumerate(objects, 1):
        offsets.append(len(document))
        document.extend(f"{index} 0 obj\n".encode() + item + b"\nendobj\n")
    xref = len(document)
    document.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode())
    document.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(document)


class FixtureSite(AbstractContextManager["FixtureSite"]):
    """An actual HTTP server, including redirects and interrupted connections."""

    def __init__(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        self.revision = "original"
        self.search_down = False
        self.search_partial_status: int | None = None
        self.requests: list[str] = []
        self.slow_started = threading.Event()
        self.release_slow = threading.Event()
        self.shared_started = threading.Event()
        self.release_shared = threading.Event()
        self.budget_started = threading.Event()
        self.release_budget = threading.Event()
        self.discovery_started = threading.Event()
        self.release_discovery = threading.Event()
        self.hold_crawl_seed = False
        self.seed_started = threading.Event()
        self.release_seed = threading.Event()
        self.redirect_target: str | None = None
        self.render_scope_fixture = False
        self.render_markdown_fixture = False
        self.rendered_html = (
            '<html><head><meta charset="iso-8859-1">'
            "<title>Rendered provenance</title></head><body>"
            "<h1>Rendered provenance</h1>"
            "<p>DomFallbackMarker retained rendered DOM passage: £ café.</p></body></html>"
        )
        self.provider_markdown = (
            "# Rendered provenance\n\n"
            "ProviderMarkdownMarker supplied by the configured renderer."
        )
        self.deep_provider_json = False
        self._lock = threading.Lock()
        self._log = directory / "source-http.jsonl"
        site = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, _format: str, *_args: object) -> None:
                return

            def do_POST(self) -> None:
                with site._lock:
                    site.requests.append(urlsplit(self.path).path)
                    with site._log.open("a", encoding="utf-8") as log:
                        log.write(
                            json.dumps(
                                {
                                    "method": "POST",
                                    "path": self.path,
                                    "had_authorization": bool(
                                        self.headers.get("Authorization")
                                    ),
                                }
                            )
                            + "\n"
                        )
                if site.deep_provider_json or self.path == "/cli-deep-json/v1/read":
                    body = b"[" * 14000 + b"0" + b"]" * 14000
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if site.render_markdown_fixture and urlsplit(self.path).path == "/crawl":
                    payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    requested = payload["urls"][0]
                    row: dict[str, object] = {
                        "success": True,
                        "status_code": 200,
                        "url": requested,
                        "html": site.rendered_html,
                    }
                    if requested.endswith("/blank.html"):
                        row["markdown"] = {"raw_markdown": " \n\t "}
                    elif requested.endswith("/raw.html"):
                        row["markdown"] = {"raw_markdown": site.provider_markdown}
                    elif requested.endswith("/partial.html"):
                        row["status_code"] = 206
                        row["html"] = "<h1>PartialRenderedMarker retained rendered prefix.</h1>"
                    elif requested.endswith("/delta.html"):
                        row["status_code"] = 226
                        row["html"] = "<h1>DeltaRenderedMarker retained rendered delta.</h1>"
                    body = json.dumps({"results": [row]}).encode()
                    transport_status = (
                        206
                        if requested.endswith("/transport-partial.html")
                        else 226
                        if requested.endswith("/transport-delta.html")
                        else 200
                    )
                    self.send_response(transport_status)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    if transport_status == 206:
                        self.send_header(
                            "Content-Range", f"bytes 0-{len(body) - 1}/{len(body) + 1000}"
                        )
                    elif transport_status == 226:
                        self.send_header("IM", "diffe")
                        self.send_header("ETag", '"provider-current"')
                        self.send_header("Delta-Base", '"provider-base"')
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if site.render_scope_fixture and urlsplit(self.path).path == "/crawl":
                    payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    requested = payload["urls"][0]
                    child = requested.endswith("/child.html")
                    final = site.url + "/render-observer/evidence.html" if child else requested
                    html = (
                        "<h1>OffScopeRenderedMarker must not be published</h1>"
                        if child
                        else "<h1>RenderedRedirectMarker retained seed</h1>"
                        '<a href="child.html">Redirecting child</a>'
                    )
                    body = json.dumps(
                        {
                            "results": [
                                {
                                    "success": True,
                                    "status_code": 200,
                                    "url": requested,
                                    "redirected_url": final,
                                    "html": html,
                                }
                            ]
                        }
                    ).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                    return
                if site.redirect_target:
                    self.send_response(307)
                    self.send_header("Location", site.redirect_target + "/collector")
                    self.end_headers()
                    return
                body = b'{"schema_version":"1.0","collector":true}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:
                parsed = urlsplit(self.path)
                path = parsed.path
                with site._lock:
                    site.requests.append(path)
                    with site._log.open("a", encoding="utf-8") as log:
                        log.write(
                            json.dumps(
                                {
                                    "path": self.path,
                                    "range": self.headers.get("Range"),
                                    "a_im": self.headers.get("A-IM"),
                                }
                            )
                            + "\n"
                        )
                status, content_type, body = 200, "text/html; charset=utf-8", b""
                content_encoding: str | None = None
                content_range: str | None = None
                response_headers: dict[str, str] = {}
                if path == "/search":
                    status = 503 if site.search_down else site.search_partial_status or 200
                    query = parse_qs(parsed.query).get("q", [""])[0]
                    selected = "/filing.pdf" if "filing" in query.lower() else "/article"
                    body = json.dumps(
                        {
                            "results": [
                                {
                                    "url": site.url + selected,
                                    "title": "Public filing"
                                    if selected.endswith("pdf")
                                    else "Architecture",
                                    "content": "Discovery snippet; not acquired evidence.",
                                    "engines": ["fixture"],
                                }
                            ],
                            "unresponsive_engines": [],
                        }
                    ).encode()
                    if site.deep_provider_json:
                        body = b"[" * 14000 + b"0" + b"]" * 14000
                    if site.search_partial_status == 206:
                        content_range = f"bytes 0-{len(body) - 1}/{len(body) + 1000}"
                    elif site.search_partial_status == 226:
                        response_headers = {
                            "IM": "diffe",
                            "ETag": '"search-current"',
                            "Delta-Base": '"search-base"',
                        }
                    content_type = "application/json"
                elif path == "/article":
                    paragraphs = "".join(
                        f"<p>Architecture section {i}: SharedMarker {site.revision} evidence "
                        "is retained independently of its retrieval index.</p>"
                        for i in range(40)
                    )
                    body = (
                        "<html><head><title>Architecture evidence</title></head><body>"
                        "<h1>Architecture evidence</h1>"
                        f"<p>RevisionMarker {site.revision} public architecture statement.</p>"
                        f"{paragraphs}<h2>Late material</h2>"
                        "<p>LatePassageAmber exact architecture evidence near the end.</p>"
                        "<table><tr><th>Metric</th><th>Value</th></tr>"
                        "<tr><td>Latency</td><td>17 milliseconds</td></tr>"
                        "</table></body></html>"
                    ).encode()
                elif path in {
                    "/charset/header.html",
                    "/charset/bom.html",
                    "/charset/unknown.html",
                }:
                    variant = path.rsplit("/", 1)[-1].split(".", 1)[0]
                    marker = {
                        "header": "HeaderCharsetMarker",
                        "bom": "BomCharsetMarker",
                        "unknown": "UnknownCharsetMarker",
                    }[variant]
                    declared = "utf-8" if variant == "unknown" else "iso-8859-1"
                    body = (
                        f'<html><head><meta charset="{declared}">'
                        "<title>Encoding evidence</title></head><body>"
                        f"<h1>Encoding evidence</h1><p>{marker} cost £ café.</p>"
                        "</body></html>"
                    ).encode()
                    if variant == "bom":
                        body = b"\xef\xbb\xbf" + body
                        content_type = "text/html; charset=iso-8859-1"
                    elif variant == "unknown":
                        content_type = "text/html; charset=dws-unknown-encoding"
                elif path == "/charset/latin1.txt":
                    content_type = "text/plain; charset=iso-8859-1"
                    body = "LatinCharsetMarker cost £ café.\n".encode("iso-8859-1")
                elif path in {"/filing.pdf", "/filings/Annual%20Report.pdf"}:
                    content_type = "application/pdf"
                    body = text_pdf("Public filing RevenueMarker 2026 revenue was 314 million.")
                elif path == "/partial/mixed/start.html":
                    body = (
                        b"<h1>MixedCompletenessMarker healthy seed retained.</h1>"
                        b'<a href="range.html">Incomplete range</a>'
                        b'<a href="delta.html">Unsupported delta</a>'
                    )
                elif path in {
                    "/partial/plain",
                    "/partial/html",
                    "/partial/pdf",
                    "/partial/mixed/range.html",
                }:
                    status = 206
                    if path.endswith("/plain"):
                        content_type = "text/plain; charset=utf-8"
                        body = b"PartialSourceMarker retained prefix only.\n"
                    elif path.endswith("/pdf"):
                        content_type = "application/pdf"
                        body = text_pdf("PartialPdfMarker retained partial source.")
                    else:
                        body = b"<h1>PartialHtmlMarker retained source prefix.</h1>"
                    content_range = f"bytes 0-{len(body) - 1}/{len(body) + 1000}"
                elif path in {"/partial/delta", "/partial/mixed/delta.html"}:
                    status, content_type = 226, "text/plain; charset=utf-8"
                    body = b"1c\nDeltaPatchMarker changed line only.\n.\n"
                    response_headers = {
                        "IM": "diffe",
                        "ETag": '"delta-current"',
                        "Delta-Base": '"delta-base"',
                    }
                elif path == "/blank.pdf":
                    content_type = "application/pdf"
                    body = text_pdf("")
                elif path == "/multipage.pdf":
                    content_type = "application/pdf"
                    body = text_pdf(
                        [
                            "PhysicalPageOneMarker retained on physical first page.",
                            "PhysicalPageTwoMarker retained on physical second page.",
                        ]
                    )
                elif path in {"/html/page-heading", "/html/extreme-page-heading"}:
                    number = "7" if path.endswith("/page-heading") else "7" * 5000
                    body = (
                        "<html><head><title>Untrusted page heading</title></head><body>"
                        f"<h1>Page {number}</h1><p>HtmlPageMarker ordinary website "
                        "evidence.</p>"
                        "</body></html>"
                    ).encode()
                elif path == "/html/code-sections":
                    body = (
                        b"<html><body><h1>Install</h1>"
                        b"<pre># Shell comment\necho ready</pre>"
                        b"<p>AfterCodeMarker remains in installation evidence.</p>"
                        b"<h2>Other</h2><p>NestedOtherMarker retained subsection.</p>"
                        b"</body></html>"
                    )
                elif path == "/html/sharp-heading":
                    body = (
                        b"<html><body><h1>C#</h1>"
                        b"<p>SharpHeadingMarker exact programming language title.</p>"
                        b"</body></html>"
                    )
                elif path == "/text/fenced-sections":
                    content_type = "text/markdown; charset=utf-8"
                    body = (
                        b"# Fences\n\n"
                        b"   ~~~~sh\n# Tilde comment\n~~~\n```\n~~~~ trailing\n"
                        b"# Still code\n   ~~~~~\n\n"
                        b"```sh\n# Backtick comment\necho ready\n```\n\n"
                        b"AfterFenceMarker code is retained.\n\n"
                        b"# Closing ###\nClosingMarker optional hashes are delimiters.\n\n"
                        b"# Escaped \\#\nEscapedHashMarker literal escape is retained.\n"
                    )
                elif path == "/text/setext-sections":
                    content_type = "text/markdown; charset=utf-8"
                    body = (
                        b"Overview\n========\n\n"
                        b"OverviewSetextMarker retained introductory evidence.\n\n"
                        b"```\nForged setext\n=============\n```\n\n"
                        b"Nested\nDetails\n--------\n\n"
                        b"NestedSetextMarker belongs to the Overview hierarchy.\n\n"
                        b"Later\nOverview\n========\n\n"
                        b"LaterSetextMarker starts another top level section.\n"
                    )
                elif path == "/text/empty-atx-sections":
                    content_type = "text/markdown; charset=utf-8"
                    body = (
                        b"# Overview\n\nEmptyBoundaryMarker retained overview evidence.\n\n"
                        b"#\n\nOtherBodyAfterEmptyMarker belongs to an unnamed section.\n\n"
                        b"# Retained\n\nRetainedBoundaryMarker retained next evidence.\n\n"
                        b"# ###\n\nOtherBodyAfterHashesMarker belongs to an unnamed section.\n"
                    )
                elif path == "/html/dense-sections":
                    body = (
                        "<html><head><title>Dense documentation</title></head><body>"
                        + "".join(
                            f"<h2>Dense section {index}</h2><p>Section body {index} "
                            + ("DenseFinalMarker " if index == 15999 else "")
                            + "retained exact evidence.</p>"
                            for index in range(16000)
                        )
                        + "</body></html>"
                    ).encode()
                elif path == "/text/adversarial-heading":
                    content_type = "text/plain; charset=utf-8"
                    body = (
                        "# A" + " " * 4096 + "B\n\n"
                        "WhitespaceHeadingMarker retained exact text.\n"
                    ).encode()
                elif path.startswith("/scope/"):
                    label = path.rsplit("/", 1)[-1]
                    if label == "coalesced" or label.startswith("admission-"):
                        site.shared_started.set()
                        site.release_shared.wait(timeout=12)
                    repetitions = "SharedMarker " * 50 if label.startswith("decoy") else ""
                    body = (
                        f"<h1>Workspace {label}</h1><p>SharedMarker Owner{label} exact "
                        f"workspace evidence for {label}. {repetitions}</p>"
                    ).encode()
                elif path == "/crawl/start.html":
                    if site.hold_crawl_seed:
                        site.seed_started.set()
                        site.release_seed.wait(timeout=12)
                    body = (
                        b"<h1>Crawl start</h1><p>DurableMarker retained starting evidence.</p>"
                        b'<a href="/crawl/a">A</a><a href="/crawl/a">Duplicate A</a>'
                        b'<a href="/crawl/slow">Slow</a><a href="/outside">Off scope</a>'
                        b'<a href="/crawl/missing">Missing</a>'
                    )
                elif path == "/crawl/a":
                    body = (
                        b"<h1>Cycle A</h1><p>DurableMarker cycle evidence.</p>"
                        b'<a href="/crawl/start.html">Back to start</a><a href="/crawl/b">B</a>'
                    )
                elif path == "/crawl/b":
                    body = b"<h1>Cycle B</h1><p>DurableMarker completed evidence.</p>"
                elif path == "/crawl/slow":
                    site.slow_started.set()
                    site.release_slow.wait(timeout=12)
                    body = b"<h1>Slow source</h1><p>DurableMarker delayed evidence.</p>"
                elif path == "/reconnect/start.html":
                    body = b"<h1>Reconnected research</h1><p>LostAckMarker exact evidence.</p>"
                elif path == "/retry/start.html":
                    body = (
                        b"<h1>Retry evidence</h1><p>RetryMarker retained starting evidence.</p>"
                        b'<a href="/retry/unavailable">Unavailable source</a>'
                    )
                elif path == "/retry/unavailable":
                    status, body = 503, b"Provider temporarily unavailable"
                elif path == "/budget/start.html":
                    body = (
                        b"<h1>Budget evidence</h1><p>TimeBudgetMarker "
                        b"retained before expiry.</p>"
                        b'<a href="/budget/slow">Slow next source</a>'
                    )
                elif path == "/budget/slow":
                    site.budget_started.set()
                    site.release_budget.wait(timeout=12)
                    body = b"<h1>Delayed beyond global crawl budget</h1>"
                elif path == "/docs/truncated/start.html":
                    body = (
                        "<h1>DiscoveryLimitMarker retained source</h1>"
                        '<a href="/docs/truncated/slow">Early admitted child</a>'
                        + "".join(
                            f'<a href="/outside-discovery/{i}">Outside {i}</a>'
                            for i in range(2005)
                        )
                        + '<a href="/docs/truncated/late">Late valid child</a>'
                    ).encode()
                elif path == "/docs/truncated/slow":
                    site.discovery_started.set()
                    site.release_discovery.wait(timeout=20)
                    body = b"<h1>DiscoveryLimitMarker admitted child completed</h1>"
                elif path == "/docs/truncated/late":
                    body = b"<h1>Late valid link beyond disclosed discovery limit</h1>"
                elif path == "/docs/relative/start.html":
                    body = (
                        b'<html><head><base href="./manual/"></head><body>'
                        b"<h1>BaseRelativeMarker documentation</h1>"
                        b'<a href="  intro.html \t">Padded introduction</a></body></html>'
                    )
                elif path == "/docs/absolute/start.html":
                    body = (
                        '<html><head><base href="'
                        + site.url
                        + '/filings/"></head><body><h1>BaseAbsoluteMarker filing</h1>'
                        '<a href=" Annual Report.pdf ">Annual filing</a></body></html>'
                    ).encode()
                elif path == "/docs/invalid/start.html":
                    body = (
                        b'<html><head><base href="javascript:alert(1)">'
                        b'<base href="https://"><base href="./manual/"></head><body>'
                        b"<h1>BaseFallbackMarker documentation</h1>"
                        b'<a href="intro.html">Introduction</a></body></html>'
                    )
                elif path == "/docs/private/start.html":
                    body = (
                        '<html><head><base href="http://localhost:'
                        + str(site.server.server_port)
                        + '/private-base/"></head><body><h1>Private base is metadata</h1>'
                        '<a href="secret.html">Off scope private child</a></body></html>'
                    ).encode()
                elif path == "/docs/v1.0/":
                    body = (
                        b"<h1>VersionedDirectoryMarker documentation</h1>"
                        b'<a href="intro.html">Inside version</a>'
                        b'<a href="../other/observer.html">Sibling version observer</a>'
                    )
                elif path == "/docs/v1.0/intro.html":
                    body = b"<h1>VersionedDirectoryMarker correctly scoped introduction</h1>"
                elif path in {
                    "/docs/redirect/public/start.html",
                    "/docs/redirect/private/start.html",
                }:
                    body = (
                        b"<h1>RedirectScopeMarker retained seed</h1>"
                        b'<a href="child.html">Forward redirect child</a>'
                    )
                elif path in {
                    "/docs/redirect/public/child.html",
                    "/docs/redirect/private/child.html",
                }:
                    host = (
                        site.url
                        if "/public/" in path
                        else (f"http://localhost:{site.server.server_port}")
                    )
                    self.send_response(302)
                    self.send_header("Location", host + "/redirect-observer/evidence.html")
                    self.end_headers()
                    return
                elif path == "/redirect-observer/evidence.html":
                    body = (
                        b"<h1>DirectRedirectMarker legitimate directly selected evidence</h1>"
                    )
                elif path in {
                    "/docs/relative/manual/intro.html",
                    "/docs/invalid/manual/intro.html",
                }:
                    body = b"<h1>BaseChildMarker correct resolved introduction</h1>"
                elif path == "/unicode":
                    body = (
                        "<html><head><title>" + "証拠" * 150 + "</title></head><body>"
                        "<h1>Unicode evidence</h1><p>"
                        + "証" * 18000
                        + "</p>"
                        + "".join(f'<a href="/citation/{i}">引用{i}</a>' for i in range(8))
                        + "</body></html>"
                    ).encode()
                elif path == "/redirect-denied":
                    self.send_response(302)
                    self.send_header(
                        "Location", f"http://localhost:{site.server.server_port}/private-target"
                    )
                    self.end_headers()
                    return
                elif path in {"/oversized", "/compressed-oversized"}:
                    body = b"<h1>Oversized</h1><p>" + b"large evidence " * 10_000 + b"</p>"
                    if path == "/compressed-oversized":
                        body = gzip.compress(body)
                        content_encoding = "gzip"
                elif path == "/javascript":
                    body = (
                        b'<html><body><div id="app"></div>'
                        b'<script>document.getElementById("app").innerHTML='
                        b'"<p>BrowserRenderedMarker actual browser content.</p>";</script>'
                        b"</body></html>"
                    )
                elif path in {"/private-target", "/outside"}:
                    body = b"<h1>This source must never be acquired by the tested request.</h1>"
                else:
                    status, body = 404, b"Source not found"
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                if content_encoding:
                    self.send_header("Content-Encoding", content_encoding)
                if content_range:
                    self.send_header("Content-Range", content_range)
                for name, value in response_headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                with suppress(BrokenPipeError, ConnectionResetError):
                    self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> FixtureSite:
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.release_slow.set()
        self.release_shared.set()
        self.release_budget.set()
        self.release_discovery.set()
        self.release_seed.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
