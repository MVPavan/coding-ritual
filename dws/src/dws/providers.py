"""Model-free discovery and acquisition adapters with explicit failure signals."""

from __future__ import annotations

import asyncio
import base64
import codecs
import importlib.metadata
import json
import os
import re
import secrets
import signal
import sys
import time
from collections.abc import Callable
from contextlib import suppress
from email.message import Message
from threading import Event
from typing import Any
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import httpcore
import httpx
from bs4 import BeautifulSoup, UnicodeDammit
from bs4.dammit import EncodingDetector
from markdownify import markdownify

from dws.config import Settings
from dws.errors import DWSError
from dws.models import Capture, FetchRequest, RevalidationCandidate, SearchRequest
from dws.net import acquisition_slot, canonical_url, client, resolve_addresses, response_bytes
from dws.tinyfish_quota import Operation, TinyFishQuota


def _reject_incomplete_response(status: int | None) -> None:
    if status in {206, 226}:
        raise DWSError(
            "partial_response",
            f"Partial or delta HTTP responses are not supported (HTTP {status})",
            502,
        )


def _validator(value: str | None, limit: int) -> str | None:
    if value and len(value) <= limit and all(32 <= ord(char) < 127 for char in value):
        return value
    return None


def _etag(value: str | None) -> str | None:
    validated = _validator(value, 512)
    if validated and re.fullmatch(r'(?:W/)?"[!\x23-\x7e]*"', validated):
        return validated
    return None


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
        self.tinyfish_quota = TinyFishQuota(settings)

    def _tinyfish_skip(self, *, fetch: bool = False) -> str | None:
        if not self.settings.tinyfish_enabled or (
            fetch and not self.settings.tinyfish_fetch_escalation
        ):
            return "disabled"
        if not self.settings.tinyfish_api_key:
            return "not_configured"
        return None

    @property
    def tinyfish_fetch_budget(self) -> float:
        return min(self.settings.request_timeout, 25)

    @property
    def acquisition_timeout(self) -> float:
        if self._tinyfish_skip(fetch=True) is not None:
            return self.settings.request_timeout
        # A crawl page timer encloses slot admission as well as both acquisition
        # timers. Reserve the bounded slot wait so it cannot shorten escalation.
        return (
            min(5.0, self.settings.request_timeout)
            + self.settings.request_timeout
            + self.tinyfish_fetch_budget
        )

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
        capture = await self._acquire(request, scope_check=scope_check)
        if capture is None:
            raise DWSError(
                "unexpected_not_modified", "Source returned an unsolicited 304.", 502
            )
        return capture

    async def revalidate(
        self, request: FetchRequest, candidate: RevalidationCandidate
    ) -> Capture | None:
        return await self._acquire(request, candidate=candidate)

    async def _acquire(
        self,
        request: FetchRequest,
        *,
        scope_check: Callable[[str], bool] | None = None,
        candidate: RevalidationCandidate | None = None,
    ) -> Capture | None:
        try:
            async with acquisition_slot(self.settings):
                # Local acquisition retains its full original deadline. Only a
                # completed blocked-source failure opens a separate hosted budget.
                needs_render_without_provider = False
                try:
                    async with asyncio.timeout(self.settings.request_timeout):
                        url = await self.validate_url(request.url)
                        if scope_check is not None and not scope_check(url):
                            raise DWSError(
                                "scope_denied", "Source is outside the crawl scope", 403
                            )
                        if request.render == "always":
                            return await self._render(url, scope_check=scope_check)
                        capture, needs_render = await self._static(
                            url, scope_check=scope_check, candidate=candidate
                        )
                        if capture is None:
                            return None
                        if needs_render and request.render == "auto":
                            needs_render_without_provider = not self.settings.crawl4ai_url
                            return await self._render(url, scope_check=scope_check)
                        if needs_render:
                            raise DWSError(
                                "render_required", "Source requires browser rendering", 422
                            )
                        return capture
                except DWSError as original:
                    # Missing local rendering is an internal escalation trigger;
                    # callers still receive the original render_unavailable/503.
                    escalation_code = (
                        "render_required" if needs_render_without_provider else original.code
                    )
                    eligible = request.render != "never" and (
                        original.code in {"challenge_page", "render_failed"}
                        or (
                            original.code == "source_http_error"
                            and original.source_status in {401, 403, 429, 451}
                        )
                        or (
                            escalation_code == "render_required"
                            and not self.settings.crawl4ai_url
                        )
                    )
                    reason = "ineligible" if not eligible else self._tinyfish_skip(fetch=True)
                    target_status = None
                    if reason is None:
                        try:
                            deadline = time.monotonic() + self.tinyfish_fetch_budget
                            async with asyncio.timeout_at(deadline):
                                # Public validation is stricter than the owner's
                                # local private-host override, including all DNS answers.
                                await self._tinyfish_public_url(url)
                                return await self._tinyfish_fetch(
                                    url,
                                    escalation_code,
                                    scope_check,
                                    deadline=deadline,
                                    ttl=(
                                        0
                                        if request.refresh
                                        else request.max_age_seconds
                                        if "max_age_seconds" in request.model_fields_set
                                        else self.settings.tinyfish_fetch_ttl
                                    ),
                                )
                        except DWSError as failure:
                            reason = (
                                failure.code
                                if failure.code
                                in {
                                    "quota_minute",
                                    "quota_day",
                                    "server_cooldown",
                                    "rate_limited",
                                    "auth_failed",
                                    "invalid_response",
                                    "unavailable",
                                    "provider_timeout",
                                    "target_blocked",
                                    "scope_denied",
                                }
                                else "ineligible"
                            )
                            target_status = failure.target_status
                        except TimeoutError:
                            reason = "provider_timeout"
                    original.escalation = {"provider": "tinyfish", "reason": reason}
                    if target_status is not None:
                        original.escalation["target_status"] = target_status
                    raise original from None
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

    async def _tinyfish_public_url(self, url: str) -> str:
        value = await self.validate_url(url)
        parsed = urlsplit(value)
        if parsed.hostname in self.settings.allowed_private_hosts:
            raise DWSError(
                "policy_denied", "Hosted acquisition denies private-host overrides", 403
            )
        await resolve_addresses(
            parsed.hostname or "", parsed.port or (443 if parsed.scheme == "https" else 80), ()
        )
        return value

    async def _tinyfish_json(
        self,
        kind: Operation,
        *,
        params: dict[str, str] | None = None,
        body: dict[str, object] | None = None,
        deadline: float | None = None,
    ) -> dict[str, Any]:
        if deadline is None:
            reason = await asyncio.to_thread(self.tinyfish_quota.reserve, kind)
            if reason:
                raise DWSError(reason, "Hosted provider quota is unavailable", 503)
        else:
            assert kind == "fetch" and body is not None
            margin_ms = max(100, min(1000, int(self.tinyfish_fetch_budget * 1000) // 5))
            minimum_remaining = (margin_ms + 100) / 1000
            if deadline - time.monotonic() < minimum_remaining:
                raise DWSError("provider_timeout", "Hosted acquisition has no usable time", 503)
            # Identify only this reservation so an unsent call can release it.
            # The cancellation signal also fences a late executor/SQLite writer.
            reservation_id = secrets.randbits(63) or 1
            abandoned = Event()
            sending = False
            possibly_reserved = True
            try:
                reason = await asyncio.to_thread(
                    self.tinyfish_quota.reserve,
                    kind,
                    reservation_id=reservation_id,
                    deadline=deadline,
                    minimum_remaining=minimum_remaining,
                    abandoned=abandoned,
                )
                possibly_reserved = reason is None
                if reason:
                    raise DWSError(reason, "Hosted provider quota is unavailable", 503)
                # Validation, SQLite and executor scheduling have already spent
                # part of the absolute budget. Leave HTTP headroom and a 100ms floor.
                provider_ms = int((deadline - time.monotonic()) * 1000) - margin_ms
                if provider_ms < 100:
                    raise DWSError(
                        "provider_timeout", "Hosted acquisition has no usable time", 503
                    )
                body["per_url_timeout_ms"] = provider_ms
                sending = True
            finally:
                if not sending:
                    abandoned.set()
                    if possibly_reserved:
                        await asyncio.to_thread(
                            self.tinyfish_quota.release, kind, reservation_id
                        )
        try:
            return await self._provider_json(
                self.settings.tinyfish_search_url
                if kind == "search"
                else self.settings.tinyfish_fetch_url,
                "GET" if kind == "search" else "POST",
                params=params,
                body=body,
                tinyfish_operation=kind,
            )
        except DWSError as error:
            if error.code in {"rate_limited", "auth_failed"}:
                raise
            code = (
                "invalid_response"
                if error.code
                in {"invalid_provider_response", "partial_response", "response_too_large"}
                else "unavailable"
            )
            raise DWSError(code, "Hosted provider could not serve the request", 503) from None
        except (
            httpx.HTTPError,
            httpcore.NetworkError,
            httpcore.ProtocolError,
            httpcore.TimeoutException,
            TimeoutError,
            ValueError,
        ):
            raise DWSError(
                "unavailable", "Hosted provider could not serve the request", 503
            ) from None

    async def _tinyfish_fetch(
        self,
        url: str,
        local_code: str,
        scope_check: Callable[[str], bool] | None,
        *,
        ttl: int,
        deadline: float,
    ) -> Capture:
        response = await self._tinyfish_json(
            "fetch",
            deadline=deadline,
            body={
                "urls": [url],
                "format": "markdown",
                "links": True,
                "ttl": ttl,
                "include_etag_and_last_modified": False,
            },
        )
        rows, errors = response.get("results"), response.get("errors")
        if isinstance(errors, list) and errors:
            detail = errors[0] if isinstance(errors[0], dict) else {}
            token = detail.get("error")
            code = (
                "provider_timeout"
                if token == "timeout"
                else "target_blocked"
                if token == "target_http_error"
                else "unavailable"
            )
            failure = DWSError(code, "Hosted provider failed to acquire the source", 503)
            status = detail.get("status")
            if code == "target_blocked" and type(status) is int and 100 <= status <= 599:
                failure.target_status = status
            raise failure
        if (
            not isinstance(rows, list)
            or len(rows) != 1
            or not isinstance(rows[0], dict)
            or not isinstance(errors, list)
        ):
            raise DWSError("invalid_response", "Hosted provider omitted its page result", 502)
        row = rows[0]
        if (
            row.get("url") != url
            or row.get("format") != "markdown"
            or not isinstance(row.get("text"), str)
            or not row["text"].strip()
            or not isinstance(row.get("final_url"), str)
        ):
            raise DWSError(
                "invalid_response", "Hosted provider returned an invalid page result", 502
            )
        final = await self._tinyfish_public_url(row["final_url"])
        if scope_check is not None and not scope_check(final):
            raise DWSError("scope_denied", "Hosted destination is outside the crawl scope", 403)
        try:
            raw = row["text"].encode("utf-8")
        except UnicodeError:
            raise DWSError("invalid_response", "Hosted text is not valid UTF-8", 502) from None
        if len(raw) > self.settings.max_bytes:
            raise DWSError("invalid_response", "Hosted text exceeds its byte limit", 413)
        warnings = [
            "provider_text_only_original_bytes_unavailable",
            "hosted_provider_acquisition",
            "escalated_from_" + local_code,
        ]
        if ttl > 0:
            warnings.append("provider_cache_permitted")
        if scope_check is not None:
            warnings.append("hosted_crawl_scope_checked_after_navigation")
        links: list[str] = []
        chars = 0
        supplied = row.get("links", [])
        if not isinstance(supplied, list):
            raise DWSError("invalid_response", "Hosted links are malformed", 502)
        for link in supplied:
            reference = link.get("url") if isinstance(link, dict) else link
            if not isinstance(reference, str):
                warnings.append("invalid_or_unsupported_html_link_ignored")
                continue
            try:
                href = _html_url(reference, final)
            except (DWSError, ValueError):
                warnings.append("invalid_or_unsupported_html_link_ignored")
                continue
            if href not in links:
                if (
                    len(links) >= min(2000, self.settings.max_pages * 20)
                    or chars + len(href) > 200000
                ):
                    warnings.append("discovered_links_truncated")
                    break
                links.append(href)
                chars += len(href)
        if len(row["text"]) > self.settings.max_text_chars:
            warnings.append("normalized_text_truncated")
        return Capture(
            requested_url=url,
            final_url=final,
            content_type="text/vnd.tinyfish.markdown",
            title=str(row.get("title") or "")[:512],
            raw=raw,
            text=row["text"][: self.settings.max_text_chars],
            links=links,
            redirects=[final] if final != url else [],
            provider="tinyfish",
            normalizer="tinyfish/fetch-markdown/1",
            warnings=list(dict.fromkeys(warnings)),
        )

    async def _static(
        self,
        requested: str,
        *,
        scope_check: Callable[[str], bool] | None = None,
        candidate: RevalidationCandidate | None = None,
    ) -> tuple[Capture | None, bool]:
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
                headers: dict[str, str] = {}
                if candidate is not None:
                    etag = _etag(candidate.etag)
                    if etag:
                        headers["If-None-Match"] = etag
                    if candidate.last_modified:
                        headers["If-Modified-Since"] = candidate.last_modified
                async with http.stream("GET", current, headers=headers) as response:
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
                    if response.status_code == 304:
                        if not headers:
                            raise DWSError(
                                "unexpected_not_modified",
                                "Source returned an unsolicited 304.",
                                502,
                            )
                        if (
                            candidate is None
                            or current != candidate.final_url
                            or redirects != candidate.redirects
                        ):
                            raise DWSError(
                                "revalidation_redirect_changed",
                                "A 304 followed a different source redirect chain.",
                                502,
                            )
                        wire_bytes = 0
                        async for chunk in response.aiter_raw():
                            wire_bytes += len(chunk)
                            if wire_bytes > self.settings.max_bytes:
                                raise DWSError(
                                    "response_too_large",
                                    "Source exceeds the configured byte limit",
                                    413,
                                )
                            if chunk:
                                raise DWSError(
                                    "invalid_response", "A 304 carried source bytes.", 502
                                )
                        return None, False
                    if not 200 <= response.status_code < 300:
                        error = DWSError(
                            "source_http_error",
                            f"Source returned HTTP {response.status_code}",
                            502,
                        )
                        error.source_status = response.status_code
                        raise error
                    _reject_incomplete_response(response.status_code)
                    raw = await response_bytes(response, self.settings.max_bytes)
                    etag = _etag(response.headers.get("etag"))
                    last_modified = _validator(response.headers.get("last-modified"), 128)
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
                            etag=etag,
                            last_modified=last_modified,
                        ), False
                    if content_type in {"text/html", "application/xhtml+xml"} or (
                        not content_type and raw.lstrip().startswith(b"<")
                    ):
                        charset, charset_warnings = _transport_charset(declared_type)
                        normalized, needs_render = await self._normalize_html(
                            raw,
                            requested,
                            current,
                            redirects,
                            charset=charset,
                            charset_warnings=charset_warnings,
                        )
                        return normalized.model_copy(
                            update={"etag": etag, "last_modified": last_modified}
                        ), needs_render
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
                            etag=etag,
                            last_modified=last_modified,
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
        tinyfish_operation: Operation | None = None,
    ) -> dict[str, Any]:
        endpoint = canonical_url(endpoint)
        provider_host = urlsplit(endpoint).hostname or ""
        # The configured service address is an owner-selected destination only.
        # It is never added to the allowed hosts for requested web content.
        async with client((provider_host,), self.settings.request_timeout) as http:
            headers = {"Authorization": "Bearer " + token} if token else {}
            if tinyfish_operation is not None:
                headers = {
                    "X-API-Key": self.settings.tinyfish_api_key or "",
                    "Accept": "application/json",
                }
            async with http.stream(
                method, endpoint, params=params, json=body, headers=headers
            ) as response:
                if tinyfish_operation is not None:
                    signal_body = None
                    # Save header signals before reading a potentially stalled body.
                    await asyncio.to_thread(
                        self.tinyfish_quota.observe,
                        tinyfish_operation,
                        response.status_code,
                        response.headers,
                    )
                    if response.status_code == 429:
                        try:
                            async with asyncio.timeout(
                                min(0.2, self.settings.request_timeout / 8)
                            ):
                                data = await response_bytes(
                                    response, min(self.settings.max_bytes, 65536)
                                )
                            value = json.loads(data)
                            if isinstance(value, dict):
                                signal_body = value
                        except (
                            DWSError,
                            ValueError,
                            RecursionError,
                            TimeoutError,
                            httpx.HTTPError,
                            httpcore.NetworkError,
                            httpcore.ProtocolError,
                            httpcore.TimeoutException,
                        ):
                            pass
                    if signal_body is not None:
                        await asyncio.to_thread(
                            self.tinyfish_quota.observe,
                            tinyfish_operation,
                            response.status_code,
                            response.headers,
                            signal_body,
                        )
                    if response.status_code == 429:
                        raise DWSError(
                            "rate_limited", "Hosted provider rate limit reached", 503
                        )
                    if response.status_code in {401, 403}:
                        raise DWSError(
                            "auth_failed", "Hosted provider authentication failed", 503
                        )
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
            if tinyfish_operation is not None and self.settings.tinyfish_api_key:
                escaped_key = json.dumps(self.settings.tinyfish_api_key, ensure_ascii=False)[
                    1:-1
                ]
                if escaped_key in json.dumps(value, ensure_ascii=False):
                    # Reject reflected credentials rather than alter retained evidence.
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
            # crawl4ai#2116 (v0.9.3+): a 200 result row carries success=false with
            # an error_message instead of a generic 500. An anti-bot block is a
            # source outcome, not a provider fault; recognize only that fixed
            # prefix without echoing provider text. Hosted escalation eligibility
            # is decided by _acquire after this typed local failure.
            if str(row.get("error_message") or "").startswith("Blocked by anti-bot protection"):
                raise DWSError(
                    "challenge_page",
                    "Source blocked rendering with anti-bot protection",
                    422,
                )
            raise DWSError(
                "render_failed", "Crawl4AI could not acquire the requested page", 502
            )
        status = row.get("status_code")
        if status is not None and (not isinstance(status, int) or not 200 <= status < 300):
            error = DWSError(
                "source_http_error", "Rendered source returned an unsuccessful HTTP status", 502
            )
            error.source_status = status if isinstance(status, int) else None
            raise error
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
        attempts: list[dict[str, str]] = []
        active_provider: str | None = None
        try:
            async with (
                acquisition_slot(self.settings),
                asyncio.timeout(self.settings.request_timeout),
            ):
                rows: list[Any] | None = None
                provider = ""
                failed_engines: list[str] = []
                reason = self._tinyfish_skip()
                if reason is None:
                    try:
                        async with asyncio.timeout(min(5, self.settings.request_timeout / 4)):
                            params = {"query": request.query}
                            if domains:
                                params["include_domains"] = ",".join(domains)
                            response = await self._tinyfish_json("search", params=params)
                        result = response.get("results")
                        if (
                            not isinstance(result, list)
                            or not isinstance(response.get("query"), str)
                            or not isinstance(response.get("total_results"), int)
                            or not isinstance(response.get("page"), int)
                            or any(
                                not isinstance(row, dict)
                                or any(
                                    not isinstance(row.get(key), str)
                                    for key in ("url", "title", "snippet")
                                )
                                for row in result
                            )
                        ):
                            raise DWSError(
                                "invalid_response", "Hosted search response is malformed", 502
                            )
                        rows, provider = result, "tinyfish"
                        reason = "served"
                    except DWSError as error:
                        reason = error.code
                    except TimeoutError:
                        reason = "unavailable"
                attempts.append({"provider": "tinyfish", "reason": reason})
                if rows is None and self.settings.searxng_url:
                    active_provider = "searxng"
                    try:
                        searxng_budget = self.settings.request_timeout / 2
                        if self._tinyfish_skip() is not None:
                            searxng_budget = max(1, searxng_budget)
                        async with asyncio.timeout(searxng_budget):
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
                        if isinstance(failed, list):
                            for item in failed[:20]:
                                name = (
                                    item[0]
                                    if isinstance(item, (list, tuple)) and item
                                    else item
                                )
                                if isinstance(name, str):
                                    failed_engines.append(name[:64])
                            failed_engines = sorted(set(failed_engines))[:20]
                        if failed:
                            warnings.append("searxng_engines_incomplete")
                            if not result:
                                raise DWSError(
                                    "provider_unavailable",
                                    "SearXNG returned no results while engines failed",
                                    503,
                                )
                        rows, provider = result, "searxng"
                        attempts.append({"provider": "searxng", "reason": "served"})
                    except DWSError as exc:
                        if exc.code in {"policy_denied", "invalid_url", "response_too_large"}:
                            raise
                        warnings.append("searxng_unavailable")
                        attempts.append({"provider": "searxng", "reason": "unavailable"})
                    except (
                        httpx.HTTPError,
                        httpcore.NetworkError,
                        httpcore.ProtocolError,
                        httpcore.TimeoutException,
                        TimeoutError,
                    ):
                        warnings.append("searxng_unavailable")
                        attempts.append({"provider": "searxng", "reason": "unavailable"})
                    active_provider = None
                elif rows is None:
                    attempts.append({"provider": "searxng", "reason": "not_configured"})
                if rows is None and self.settings.ddgs_enabled:
                    active_provider = "ddgs"
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
                    attempts.append({"provider": "ddgs", "reason": "served"})
                    active_provider = None
                if rows is None:
                    attempts.append({"provider": "ddgs", "reason": "disabled"})
                    raise DWSError(
                        "search_unavailable", "No usable search provider is configured", 503
                    )
                results: list[dict[str, object]] = []
                seen: set[str] = set()
                upstream_engines: set[str] = set()
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
                    engines = row.get("engines")
                    if provider == "searxng" and isinstance(engines, list):
                        upstream_engines.update(
                            engine[:64] for engine in engines[:20] if isinstance(engine, str)
                        )
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
                    if provider == "tinyfish" and isinstance(row.get("date"), str):
                        results[-1]["date"] = row["date"][:128]
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
                    "engine_path": {
                        "attempts": attempts,
                        "provider": provider,
                        "backend": "auto" if provider == "ddgs" else None,
                        "upstream_engines": sorted(upstream_engines)[:20],
                        "failed_primary_engines": failed_engines,
                    },
                    "results": results,
                    "warnings": list(dict.fromkeys(warnings)),
                    "evidence": False,
                    "ranking": "provider_order_not_truth_or_credibility",
                    "freshness": "provider_claims_unverified",
                }
                if provider == "ddgs":
                    output["provider_details"] = {"backend": "auto", "max_threads": 2}
                    if "searxng_unavailable" in warnings:
                        warnings.append("fallback_upstream_independence_unverified")
                        output["warnings"] = list(dict.fromkeys(warnings))
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
        except (DWSError, TimeoutError) as failure:
            if active_provider is not None:
                attempts.append({"provider": active_provider, "reason": "unavailable"})
            search_error = (
                failure
                if isinstance(failure, DWSError)
                else DWSError("provider_timeout", "Search exceeded its deadline", 504)
            )
            search_error.engine_path = {"attempts": attempts}
            raise search_error from None

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
