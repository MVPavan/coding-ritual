"""Model-free discovery and acquisition adapters with explicit failure signals."""

from __future__ import annotations

import asyncio
import base64
import codecs
import importlib.metadata
import json
import os
import signal
import sys
from collections.abc import Callable
from contextlib import suppress
from email.message import Message
from typing import Any
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import httpcore
import httpx
from bs4 import BeautifulSoup, UnicodeDammit
from bs4.dammit import EncodingDetector
from markdownify import markdownify

from dws.config import Settings
from dws.errors import DWSError
from dws.models import Capture, FetchRequest, SearchRequest
from dws.net import acquisition_slot, canonical_url, client, resolve_addresses, response_bytes


def _reject_incomplete_response(status: int | None) -> None:
    if status in {206, 226}:
        raise DWSError(
            "partial_response",
            f"Partial or delta HTTP responses are not supported (HTTP {status})",
            502,
        )


def _normalizer() -> str:
    return (
        "markdownify/"
        + importlib.metadata.version("markdownify")
        + "+beautifulsoup4/"
        + importlib.metadata.version("beautifulsoup4")
    )


def _transport_charset(content_type: str) -> tuple[str | None, list[str]]:
    """Accept supported text codecs, not executable/binary codec transforms."""
    message = Message()
    message["Content-Type"] = content_type
    label = message.get_param("charset")
    if label is None:
        return None, []
    try:
        if not isinstance(label, str) or not 0 < len(label) <= 128:
            raise LookupError
        encoding = codecs.lookup(label.strip()).name
        if encoding in {
            "utf-7",
            "unicode-escape",
            "raw-unicode-escape",
            "punycode",
            "idna",
            "charmap",
        }:
            raise LookupError
        b"".decode(encoding)
        return encoding, []
    except (LookupError, UnicodeError, ValueError):
        return None, ["transport_charset_invalid_ignored"]


def _decode_text(
    raw: bytes,
    charset: str | None,
    *,
    is_html: bool = False,
    known_utf8: bool = False,
) -> tuple[str, str, list[str]]:
    """BOM/transport precedence; unlabelled HTML keeps BeautifulSoup's heuristic."""
    warnings: list[str] = []
    body, bom = EncodingDetector.strip_byte_order_mark(raw)
    if is_html and charset in {"ascii", "iso8859-1"}:
        # HTML's legacy Latin-1/ASCII labels mean Windows-1252. Plain text
        # retains the declared Python codec rather than imposing HTML rules.
        charset = "cp1252"
    if known_utf8:
        encoding, source = "utf-8", "dom"
    elif bom:
        encoding, source = codecs.lookup(bom).name, "bom"
        if charset is not None and charset != encoding:
            warnings.append("transport_charset_overridden_by_bom")
    elif charset:
        encoding, source = charset, "http"
    elif is_html:
        detected = UnicodeDammit(raw, is_html=True)
        if detected.unicode_markup is None or detected.original_encoding is None:
            raise DWSError(
                "extraction_failed", "HTML character encoding could not be decoded", 422
            )
        encoding = codecs.lookup(detected.original_encoding).name
        warnings.append("source_encoding_inferred")
        if detected.contains_replacement_characters:
            warnings.append("source_encoding_replacement_characters")
        return detected.unicode_markup, "+decode/" + encoding + "/inferred/1", warnings
    else:
        encoding, source = "utf-8", "default"
        warnings.append("source_encoding_assumed_utf8")
    try:
        text = body.decode(encoding)
    except UnicodeError:
        text = body.decode(encoding, errors="replace")
        warnings.extend(
            [
                "source_bytes_invalid_for_declared_encoding"
                if source == "http"
                else "source_bytes_invalid_for_selected_encoding",
                "source_encoding_replacement_characters",
            ]
        )
    return text, "+decode/" + encoding + "/" + source + "/1", warnings


def _html_url(reference: str, base: str) -> str:
    """Adapt an HTML URL reference before applying the strict acquisition schema."""
    reference = reference.strip(" \t\n\r\f")
    if any(ord(char) < 32 or ord(char) == 127 for char in reference):
        raise ValueError("HTML URL contains control characters")
    parsed_reference = urlsplit(reference)
    explicit_authority = reference.startswith("//") or (
        bool(parsed_reference.scheme)
        and reference.lower().startswith(parsed_reference.scheme + "://")
    )
    if explicit_authority and not parsed_reference.hostname:
        raise ValueError("HTML URL has an empty authority")
    resolved = urlsplit(urljoin(base, reference))
    # Never quote authority/scheme: encoding those could turn malformed or
    # credential-bearing destinations into apparently acceptable HTTP URLs.
    safe = "/:@!$&'()*+,;=-._~%"
    return canonical_url(
        urlunsplit(
            (
                resolved.scheme,
                resolved.netloc,
                quote(resolved.path, safe=safe),
                quote(resolved.query, safe=safe + "?"),
                quote(resolved.fragment, safe=safe + "?"),
            )
        )
    )


def _html_capture(
    raw: bytes,
    requested: str,
    final: str,
    redirects: list[str],
    settings: Settings,
    *,
    charset: str | None = None,
    charset_warnings: list[str] | None = None,
    known_utf8: bool = False,
) -> tuple[Capture, bool]:
    markup, decoding, encoding_warnings = _decode_text(
        raw, charset, is_html=True, known_utf8=known_utf8
    )
    # Unicode input prevents the parser from reinterpreting a stale meta charset.
    soup = BeautifulSoup(markup, "html.parser")
    title = soup.title.get_text(" ", strip=True)[:512] if soup.title else ""
    scripts_present = bool(soup.find("script"))
    visible = soup.get_text(" ", strip=True).lower()
    challenge = (
        any(
            "/cdn-cgi/challenge-platform/" in str(tag.get("src", ""))
            for tag in soup.find_all("script")
        )
        or (len(visible) < 2000 and "checking your browser before accessing" in visible)
        or (
            "just a moment" in title.lower()
            and ("verify" in visible or "javascript" in visible)
        )
        or (len(visible) < 2000 and "verify you are human" in visible)
    )
    if challenge:
        raise DWSError(
            "challenge_page", "Source returned a browser challenge, not usable evidence", 422
        )
    # Inert template/noscript content cannot supply the document's link base.
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    warnings = list(charset_warnings or []) + encoding_warnings
    link_base = final
    for base in soup.find_all("base", href=True):
        try:
            link_base = _html_url(str(base["href"]), final)
        except (DWSError, ValueError):
            if "invalid_html_base_ignored" not in warnings:
                warnings.append("invalid_html_base_ignored")
            continue
        warnings.append("html_base_url_applied")
        break
    body = soup.body or soup
    links: list[str] = []
    link_chars = 0
    links_truncated = False
    for tag in body.find_all("a", href=True):
        try:
            reference = str(tag["href"])
            href = _html_url(reference, link_base)
        except (DWSError, ValueError):
            if "invalid_or_unsupported_html_link_ignored" not in warnings:
                warnings.append("invalid_or_unsupported_html_link_ignored")
            continue
        if (
            any(char in " \t\n\r\f" for char in reference)
            and "html_link_url_normalized" not in warnings
        ):
            warnings.append("html_link_url_normalized")
        if href not in links:
            if (
                len(links) < min(2000, settings.max_pages * 20)
                and link_chars + len(href) <= 200_000
            ):
                links.append(href)
                link_chars += len(href)
            else:
                links_truncated = True
        tag["href"] = href
    text = markdownify(str(body), heading_style="ATX", bullets="-", strip=["img"])
    text = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if title and not text.startswith("# " + title):
        text = "# " + title + "\n\n" + text
    useful = body.get_text(" ", strip=True)
    needs_render = scripts_present and (
        len(useful) < 120
        or "enable javascript to" in useful.lower()
        or "requires javascript" in useful.lower()
    )
    if links_truncated:
        warnings.append("discovered_links_truncated")
    if len(text) > settings.max_text_chars:
        text = text[: settings.max_text_chars]
        warnings.append("normalized_text_truncated")
    if not useful.strip():
        if not needs_render:
            raise DWSError("empty_content", "Source contains no usable text", 422)
        warnings.append("script_dependent_content")
    return Capture(
        requested_url=requested,
        final_url=final,
        content_type="text/html",
        title=title,
        text=text,
        raw=raw,
        links=links[: settings.max_pages * 20],
        redirects=redirects,
        warnings=warnings,
        normalizer=_normalizer()
        + decoding
        + "+html-url/1"
        + (
            "+html-base/1"
            if any(
                warning in warnings
                for warning in ("html_base_url_applied", "invalid_html_base_ignored")
            )
            else ""
        ),
        provider="httpx",
    ), needs_render


_PROCESS_PREAMBLE = """
import json, os, resource, sys
resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
resource.setrlimit(resource.RLIMIT_CPU, (35, 35))
resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
"""

_PDF_SCRIPT = (
    _PROCESS_PREAMBLE
    + """
from io import BytesIO
from pypdf import PdfReader, __version__
payload = json.loads(sys.stdin.buffer.read())
import base64
try:
    reader = PdfReader(BytesIO(base64.b64decode(payload['body'])), strict=False)
    if reader.is_encrypted:
        raise ValueError('encrypted_pdf')
    limit = payload['limit']
    sections = []
    page_starts = []
    used = 0
    has_text = False
    warnings = ['pdf_layout_may_differ_from_original']
    for number, page in enumerate(reader.pages, 1):
        content = page.extract_text() or ''
        has_text = has_text or bool(content.strip())
        if not content.strip():
            warnings.append('page_%d_has_no_extractable_text' % number)
        section = '## Page %d\\n\\n%s' % (number, content.strip())
        if used + len(section) > limit:
            retained = section[:max(0, limit - used)]
            if retained:
                page_starts.append((used, number))
            sections.append(retained)
            warnings.append('normalized_text_truncated')
            break
        page_starts.append((used, number))
        sections.append(section)
        used += len(section) + 2
    text = '\\n\\n'.join(sections)[:limit]
    if not has_text:
        raise ValueError('no_extractable_text')
    title = str(reader.metadata.title or '')[:512] if reader.metadata else ''
    print(json.dumps({
        'text': text, 'title': title,
        'pdf_page_starts': [
            (start, number) for start, number in page_starts if 0 <= start < len(text)
        ],
        'warnings': list(dict.fromkeys(warnings)), 'version': __version__
    }))
except Exception:
    print(json.dumps({'error': 'extraction_failed'}))
"""
)

_DDGS_SCRIPT = (
    _PROCESS_PREAMBLE
    + """
from ddgs import DDGS
payload = json.loads(sys.stdin.buffer.read())
try:
    # DDGS is a metasearch SDK. Restricting it to DuckDuckGo makes fallback
    # repeat the same CAPTCHA failure as the default SearXNG engine.
    DDGS.threads = 2
    results = DDGS(timeout=payload['timeout']).text(
        payload['query'], max_results=payload['limit'], backend='auto'
    )
    normalized = [{
        'url': str(row.get('href', ''))[:4096],
        'title': str(row.get('title', ''))[:512],
        'snippet': str(row.get('body', ''))[:2000]
    } for row in results[:payload['limit']]]
    print(json.dumps({'results': normalized}))
except Exception:
    print(json.dumps({'error': 'provider_unavailable'}))
"""
)


_HTML_SCRIPT = (
    _PROCESS_PREAMBLE
    + """
import base64
from dws.config import Settings
from dws.errors import DWSError
from dws.providers import _html_capture
payload = json.loads(sys.stdin.buffer.read())
try:
    capture, needs_render = _html_capture(
        base64.b64decode(payload['body']), payload['requested'], payload['final'],
        payload['redirects'], Settings(**payload['limits']),
        charset=payload.get('charset'), charset_warnings=payload.get('charset_warnings'),
        known_utf8=payload.get('known_utf8', False)
    )
    print(json.dumps({'capture': capture.model_dump(), 'needs_render': needs_render}))
except DWSError as exc:
    print(json.dumps({'error': exc.code, 'message': exc.message, 'status': exc.status}))
except Exception:
    print(json.dumps({'error': 'extraction_failed', 'message': 'HTML extraction failed',
                      'status': 422}))
"""
)


async def _helper(
    script: str, payload: dict[str, object], settings: Settings
) -> dict[str, Any]:
    """Kill the entire isolated extraction/provider process group on every exit."""
    temporary = (settings.data_dir / "provider-tmp").resolve()
    temporary.mkdir(parents=True, exist_ok=True, mode=0o700)
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"}
    }
    environment.update(
        {
            "TMPDIR": str(temporary),
            "TEMP": str(temporary),
            "XDG_CACHE_HOME": str(temporary),
            "XDG_STATE_HOME": str(temporary),
        }
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-I",
        "-c",
        script,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        cwd=temporary,
        env=environment,
        start_new_session=True,
    )
    assert process.stdin is not None and process.stdout is not None

    async def write_input() -> None:
        assert process.stdin is not None
        try:
            process.stdin.write(json.dumps(payload).encode())
            await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            process.stdin.close()

    writer = asyncio.create_task(write_input())
    output = bytearray()
    max_output = settings.max_text_chars * 6 + 65_536
    try:
        async with asyncio.timeout(settings.request_timeout):
            while chunk := await process.stdout.read(65_536):
                output.extend(chunk)
                if len(output) > max_output:
                    raise DWSError(
                        "response_too_large", "Extraction output exceeds its limit", 413
                    )
            await writer
            await process.wait()
        value = json.loads(output)
        if not isinstance(value, dict) or process.returncode != 0:
            raise ValueError
        return value
    except (ValueError, json.JSONDecodeError):
        raise DWSError(
            "provider_unavailable", "Provider or extraction process failed", 503
        ) from None
    finally:
        writer.cancel()
        if process.returncode is None:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            await process.wait()
        await asyncio.gather(writer, return_exceptions=True)


class Acquisition:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def validate_url(self, url: str) -> str:
        value = canonical_url(url)
        parsed = urlsplit(value)
        async with asyncio.timeout(self.settings.request_timeout):
            await resolve_addresses(
                parsed.hostname or "",
                parsed.port or (443 if parsed.scheme == "https" else 80),
                self.settings.allowed_private_hosts,
            )
        return value

    async def fetch(
        self,
        request: FetchRequest,
        *,
        scope_check: Callable[[str], bool] | None = None,
    ) -> Capture:
        try:
            async with (
                acquisition_slot(self.settings),
                asyncio.timeout(self.settings.request_timeout),
            ):
                url = await self.validate_url(request.url)
                if scope_check is not None and not scope_check(url):
                    raise DWSError("scope_denied", "Source is outside the crawl scope", 403)
                if request.render == "always":
                    return await self._render(url, scope_check=scope_check)
                capture, needs_render = await self._static(url, scope_check=scope_check)
                if needs_render and request.render == "auto":
                    return await self._render(url, scope_check=scope_check)
                if needs_render:
                    raise DWSError("render_required", "Source requires browser rendering", 422)
                return capture
        except TimeoutError:
            raise DWSError(
                "source_timeout", "Source acquisition exceeded its deadline", 504
            ) from None
        except (
            httpx.HTTPError,
            httpcore.NetworkError,
            httpcore.ProtocolError,
            httpcore.TimeoutException,
        ):
            raise DWSError("source_unavailable", "Source transport failed", 502) from None

    async def _static(
        self,
        requested: str,
        *,
        scope_check: Callable[[str], bool] | None = None,
    ) -> tuple[Capture, bool]:
        current = requested
        redirects: list[str] = []
        async with client(
            self.settings.allowed_private_hosts, self.settings.request_timeout
        ) as http:
            for hop in range(6):
                current = await self.validate_url(current)
                # Destination policy has priority; every allowed redirect must
                # also stay in this crawl's document area before any GET.
                if scope_check is not None and not scope_check(current):
                    raise DWSError(
                        "scope_denied", "Source redirect is outside the crawl scope", 403
                    )
                async with http.stream("GET", current) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if hop == 5 or not response.headers.get("location"):
                            raise DWSError(
                                "redirect_limit",
                                "Source redirect chain is invalid or too long",
                                502,
                            )
                        current = canonical_url(urljoin(current, response.headers["location"]))
                        redirects.append(current)
                        continue
                    if not 200 <= response.status_code < 300:
                        raise DWSError(
                            "source_http_error",
                            f"Source returned HTTP {response.status_code}",
                            502,
                        )
                    _reject_incomplete_response(response.status_code)
                    raw = await response_bytes(response, self.settings.max_bytes)
                    declared_type = response.headers.get("content-type", "")
                    content_type = declared_type.split(";", 1)[0].strip().lower()
                    if raw.startswith(b"%PDF-") or content_type == "application/pdf":
                        parsed = await _helper(
                            _PDF_SCRIPT,
                            {
                                "body": base64.b64encode(raw).decode(),
                                "limit": self.settings.max_text_chars,
                            },
                            self.settings,
                        )
                        if parsed.get("error"):
                            raise DWSError(
                                "extraction_failed",
                                "PDF has no usable text or is invalid; OCR is not enabled",
                                422,
                            )
                        return Capture(
                            requested_url=requested,
                            final_url=current,
                            content_type="application/pdf",
                            title=parsed["title"],
                            text=parsed["text"],
                            raw=raw,
                            pdf_page_starts=parsed["pdf_page_starts"],
                            redirects=redirects,
                            warnings=parsed["warnings"],
                            normalizer="pypdf/" + parsed["version"] + "+page-boundaries/1",
                            provider="httpx",
                        ), False
                    if content_type in {"text/html", "application/xhtml+xml"} or (
                        not content_type and raw.lstrip().startswith(b"<")
                    ):
                        charset, charset_warnings = _transport_charset(declared_type)
                        return await self._normalize_html(
                            raw,
                            requested,
                            current,
                            redirects,
                            charset=charset,
                            charset_warnings=charset_warnings,
                        )
                    if content_type in {"text/plain", "text/markdown"}:
                        charset, warnings = _transport_charset(declared_type)
                        decoded, decoding, encoding_warnings = _decode_text(raw, charset)
                        text = decoded.strip()
                        warnings.extend(encoding_warnings)
                        if not text:
                            raise DWSError(
                                "empty_content", "Source contains no usable text", 422
                            )
                        if len(text) > self.settings.max_text_chars:
                            warnings.append("normalized_text_truncated")
                        return Capture(
                            requested_url=requested,
                            final_url=current,
                            content_type=content_type,
                            title="",
                            text=text[: self.settings.max_text_chars],
                            raw=raw,
                            redirects=redirects,
                            warnings=warnings,
                            normalizer="text/1" + decoding,
                            provider="httpx",
                        ), False
                    raise DWSError(
                        "unsupported_content",
                        "Source is not supported HTML, text, or PDF content",
                        415,
                    )
        raise DWSError("redirect_limit", "Source redirect limit was reached", 502)

    async def _normalize_html(
        self,
        raw: bytes,
        requested: str,
        final: str,
        redirects: list[str],
        *,
        charset: str | None = None,
        charset_warnings: list[str] | None = None,
        known_utf8: bool = False,
    ) -> tuple[Capture, bool]:
        parsed = await _helper(
            _HTML_SCRIPT,
            {
                "body": base64.b64encode(raw).decode(),
                "requested": requested,
                "final": final,
                "redirects": redirects,
                "charset": charset,
                "charset_warnings": charset_warnings or [],
                "known_utf8": known_utf8,
                "limits": {
                    "max_text_chars": self.settings.max_text_chars,
                    "max_pages": self.settings.max_pages,
                },
            },
            self.settings,
        )
        if parsed.get("error"):
            raise DWSError(str(parsed["error"]), str(parsed["message"]), int(parsed["status"]))
        return Capture.model_validate({**parsed["capture"], "raw": raw}), bool(
            parsed["needs_render"]
        )

    async def _provider_json(
        self,
        endpoint: str,
        method: str,
        *,
        params: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
        token: str | None = None,
    ) -> dict[str, Any]:
        endpoint = canonical_url(endpoint)
        provider_host = urlsplit(endpoint).hostname or ""
        # The configured service address is an owner-selected destination only.
        # It is never added to the allowed hosts for requested web content.
        async with client((provider_host,), self.settings.request_timeout) as http:
            headers = {"Authorization": "Bearer " + token} if token else {}
            async with http.stream(
                method, endpoint, params=params, json=body, headers=headers
            ) as response:
                if not 200 <= response.status_code < 300:
                    raise DWSError(
                        "provider_unavailable",
                        f"Provider returned HTTP {response.status_code}",
                        503,
                    )
                _reject_incomplete_response(response.status_code)
                raw = await response_bytes(response, self.settings.max_bytes)
        try:
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError
            return value
        except (ValueError, json.JSONDecodeError, RecursionError):
            raise DWSError(
                "invalid_provider_response", "Provider returned malformed JSON", 502
            ) from None

    async def _render(
        self,
        url: str,
        *,
        scope_check: Callable[[str], bool] | None = None,
    ) -> Capture:
        if not self.settings.crawl4ai_url:
            raise DWSError(
                "render_unavailable",
                "Rendering is required but Crawl4AI is not configured",
                503,
            )
        response = await self._provider_json(
            self.settings.crawl4ai_url.rstrip("/") + "/crawl",
            "POST",
            body={
                "urls": [url],
                "crawler_config": {
                    "type": "CrawlerRunConfig",
                    "params": {
                        "page_timeout": int(self.settings.request_timeout * 1000),
                        "delay_before_return_html": 0.2,
                    },
                },
            },
            token=self.settings.crawl4ai_token,
        )
        results = response.get("results")
        if (
            not isinstance(results, list)
            or len(results) != 1
            or not isinstance(results[0], dict)
        ):
            raise DWSError(
                "invalid_provider_response", "Crawl4AI returned no single page result", 502
            )
        row = results[0]
        if row.get("success") is not True:
            # Do not expose untrusted provider exception text or fall back.
            raise DWSError(
                "render_failed", "Crawl4AI could not acquire the requested page", 502
            )
        status = row.get("status_code")
        if status is not None and (not isinstance(status, int) or not 200 <= status < 300):
            raise DWSError(
                "source_http_error", "Rendered source returned an unsuccessful HTTP status", 502
            )
        _reject_incomplete_response(status)
        final = await self.validate_url(str(row.get("redirected_url") or row.get("url") or url))
        if scope_check is not None and not scope_check(final):
            raise DWSError(
                "scope_denied",
                "Rendered destination is outside the crawl scope; evidence refused. "
                "The configured browser may have navigated there before this result check",
                403,
            )
        html = row.get("html")
        if not isinstance(html, str) or not html.strip():
            raise DWSError(
                "invalid_provider_response", "Crawl4AI did not retain rendered HTML", 502
            )
        raw = html.encode("utf-8")
        if len(raw) > self.settings.max_bytes:
            raise DWSError("response_too_large", "Rendered HTML exceeds its byte limit", 413)
        capture, _ = await self._normalize_html(
            raw, url, final, [final] if final != url else [], known_utf8=True
        )
        markdown = row.get("markdown")
        # Fit/pruned markdown is never canonical. raw_markdown is the broad DOM
        # transformation; the HTML normalization is a safe compatibility fallback.
        raw_markdown = markdown.get("raw_markdown") if isinstance(markdown, dict) else markdown
        warnings = list(capture.warnings)
        text = capture.text
        normalizer = "crawl4ai/rendered-html/1+" + capture.normalizer
        html_links_normalized = any(
            warning in warnings
            for warning in (
                "html_base_url_applied",
                "invalid_html_base_ignored",
                "html_link_url_normalized",
            )
        )
        if isinstance(raw_markdown, str) and raw_markdown.strip() and not html_links_normalized:
            text = raw_markdown.strip()
            normalizer = "crawl4ai/raw-markdown/1+" + capture.normalizer
            if capture.title and not text.startswith("# " + capture.title):
                text = "# " + capture.title + "\n\n" + text
            if len(text) > self.settings.max_text_chars:
                text = text[: self.settings.max_text_chars]
                if "normalized_text_truncated" not in warnings:
                    warnings.append("normalized_text_truncated")
        elif html_links_normalized:
            # The provider's raw Markdown can retain relative links or resolve
            # them against the page URL. Keep the same canonical DOM-derived
            # links as acquisition/crawl, including a retained HTML base tag.
            warnings.append("provider_markdown_rebased_from_retained_html")
        else:
            warnings.append("provider_markdown_unavailable_html_normalized")
        warnings.extend(
            [
                "browser_subrequest_policy_delegated_to_configured_provider",
                "browser_intermediate_redirect_chain_unavailable",
            ]
        )
        if scope_check is not None:
            warnings.append("browser_crawl_scope_checked_after_navigation")
        return capture.model_copy(
            update={
                "text": text,
                "warnings": warnings,
                "provider": "crawl4ai",
                "normalizer": normalizer,
            }
        )

    async def search(self, request: SearchRequest) -> dict[str, object]:
        warnings: list[str] = []
        domains = self._domains(request.domains)
        try:
            async with (
                acquisition_slot(self.settings),
                asyncio.timeout(self.settings.request_timeout),
            ):
                rows: list[Any] | None = None
                provider = ""
                if self.settings.searxng_url:
                    try:
                        async with asyncio.timeout(max(1, self.settings.request_timeout / 2)):
                            response = await self._provider_json(
                                self.settings.searxng_url.rstrip("/") + "/search",
                                "GET",
                                params={"q": request.query, "format": "json"},
                            )
                        result = response.get("results")
                        if not isinstance(result, list):
                            raise DWSError(
                                "invalid_provider_response",
                                "SearXNG omitted its result list",
                                502,
                            )
                        failed = response.get("unresponsive_engines", [])
                        if failed:
                            warnings.append("searxng_engines_incomplete")
                            if not result:
                                raise DWSError(
                                    "provider_unavailable",
                                    "SearXNG returned no results while engines failed",
                                    503,
                                )
                        rows, provider = result, "searxng"
                    except DWSError as exc:
                        if exc.code in {"policy_denied", "invalid_url", "response_too_large"}:
                            raise
                        warnings.append("searxng_unavailable")
                    except (
                        httpx.HTTPError,
                        httpcore.NetworkError,
                        httpcore.ProtocolError,
                        httpcore.TimeoutException,
                        TimeoutError,
                    ):
                        warnings.append("searxng_unavailable")
                if rows is None and self.settings.ddgs_enabled:
                    value = await _helper(
                        _DDGS_SCRIPT,
                        {
                            "query": request.query,
                            "limit": request.limit,
                            "timeout": min(15, self.settings.request_timeout),
                        },
                        self.settings,
                    )
                    if value.get("error") or not isinstance(value.get("results"), list):
                        raise DWSError(
                            "provider_unavailable",
                            "DDGS search failed; try later or configure SearXNG",
                            503,
                        )
                    rows, provider = value["results"], "ddgs"
                if rows is None:
                    raise DWSError(
                        "search_unavailable", "No usable search provider is configured", 503
                    )
                results: list[dict[str, object]] = []
                seen: set[str] = set()
                for row in rows:
                    if not isinstance(row, dict):
                        warnings.append("malformed_search_result_skipped")
                        continue
                    try:
                        url = canonical_url(str(row.get("url") or row.get("href") or ""))
                    except DWSError:
                        warnings.append("invalid_search_url_skipped")
                        continue
                    host = urlsplit(url).hostname or ""
                    if domains and not any(
                        host == domain or host.endswith("." + domain) for domain in domains
                    ):
                        continue
                    if url in seen:
                        continue
                    seen.add(url)
                    results.append(
                        {
                            "url": url,
                            "title": str(row.get("title", ""))[:512],
                            "snippet": str(
                                row.get("content", row.get("snippet", row.get("body", "")))
                            )[:2000],
                            "rank": len(results) + 1,
                        }
                    )
                    if len(results) >= request.limit:
                        break
                if domains:
                    warnings.append(
                        "domain_filter_applied_to_provider_results_not_exhaustive_search"
                    )
                output: dict[str, object] = {
                    "query": request.query,
                    "workspace_id": request.workspace_id,
                    "domains": domains,
                    "provider": provider,
                    "results": results,
                    "warnings": list(dict.fromkeys(warnings)),
                    "evidence": False,
                    "ranking": "provider_order_not_truth_or_credibility",
                    "freshness": "provider_claims_unverified",
                }
                if provider == "ddgs":
                    output["provider_details"] = {"backend": "auto", "max_threads": 2}
                while (
                    results
                    and len(json.dumps(output, ensure_ascii=False))
                    > self.settings.max_output_chars
                ):
                    results.pop()
                    output["warnings"] = list(
                        dict.fromkeys(warnings + ["search_output_truncated"])
                    )
                if len(json.dumps(output, ensure_ascii=False)) > self.settings.max_output_chars:
                    raise DWSError(
                        "output_budget_too_small",
                        "Output limit cannot carry the requested search scope",
                        422,
                    )
                return output
        except TimeoutError:
            raise DWSError("provider_timeout", "Search exceeded its deadline", 504) from None

    @staticmethod
    def _domains(domains: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in domains:
            if "://" in value or "/" in value or ":" in value or "@" in value:
                raise DWSError(
                    "invalid_domain",
                    "Domain filters must be hostnames without paths or credentials",
                )
            try:
                host = value.rstrip(".").encode("idna").decode("ascii").lower()
            except UnicodeError:
                raise DWSError("invalid_domain", "Domain filter is invalid") from None
            if not host or any(not (char.isalnum() or char in ".-") for char in host):
                raise DWSError("invalid_domain", "Domain filter is invalid")
            normalized.append(host)
        return list(dict.fromkeys(normalized))
