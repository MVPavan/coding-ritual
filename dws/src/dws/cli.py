"""Installed command client and local API/worker launchers."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from http.client import InvalidURL
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from dws import __version__


def build_parser() -> argparse.ArgumentParser:
    """Build help without importing service or optional MCP dependencies."""
    parser = argparse.ArgumentParser(
        prog="dws",
        description="Discover, retain and retrieve exact public-web evidence.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--api-url",
        default=None,
        help="Trusted command API URL; environment proxies bypassed and redirects refused",
    )
    parser.add_argument(
        "--token", default=None, help="API bearer token; defaults to local token file"
    )
    parser.add_argument(
        "--data-dir", type=Path, default=None, help="DWS persistent state directory"
    )
    commands = parser.add_subparsers(dest="command")

    def command(name: str, *, workspace: bool = True) -> argparse.ArgumentParser:
        sub = commands.add_parser(name)
        sub.set_defaults(operation=name.replace("-", "_"))
        if workspace:
            sub.add_argument("--workspace", dest="workspace_id", default="default")
        return sub

    def render(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--render", choices=("auto", "always", "never"), default="auto")

    api = command("api", workspace=False)
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8765)
    worker = command("worker", workspace=False)
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--idle-seconds", type=float, default=2)
    search = command("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--domain", dest="domains", action="append", default=[])
    fetch = command("fetch")
    fetch.add_argument("url")
    fetch.add_argument("--run", dest="run_id")
    fetch.add_argument("--refresh", action="store_true")
    fetch.add_argument("--max-age", dest="max_age_seconds", type=int, default=3600)
    render(fetch)
    crawl = command("crawl")
    crawl.add_argument("seed_url")
    crawl.add_argument("--run", dest="run_id")
    crawl.add_argument("--scope", choices=("same_host", "same_path"), default="same_path")
    crawl.add_argument("--pages", dest="max_pages", type=int, default=50)
    crawl.add_argument("--depth", dest="max_depth", type=int, default=2)
    crawl.add_argument("--seconds", dest="max_seconds", type=int, default=300)
    crawl.add_argument("--idempotency-key")
    render(crawl)
    retrieve = command("retrieve")
    retrieve.add_argument("query")
    retrieve.add_argument("--run", dest="run_id")
    retrieve.add_argument("--crawl", dest="crawl_id")
    retrieve.add_argument("--document", dest="document_ids", action="append", default=[])
    retrieve.add_argument("--limit", type=int, default=5)
    retrieve.add_argument("--max-chars", type=int, default=6000)
    read = command("read")
    read.add_argument("snapshot_id")
    read.add_argument("--start", dest="line_start", type=int, default=1)
    read.add_argument("--end", dest="line_end", type=int)
    read.add_argument("--section")
    read.add_argument("--max-chars", type=int, default=6000)
    for name in ("job-status", "job-cancel"):
        job = command(name)
        job.add_argument("job_id")
        if name == "job-status":
            job.add_argument("--offset", type=int, default=0)
            job.add_argument("--limit", type=int, default=20)
    for name in ("pin", "unpin", "export", "expire"):
        snapshot = command(name)
        snapshot.add_argument("snapshot_id")
        if name == "unpin":
            snapshot.set_defaults(operation="pin", pinned=False)
    for name in ("workspace", "run"):
        group = commands.add_parser(name).add_subparsers(dest="action", required=True)
        create = group.add_parser("create")
        create.add_argument("name")
        create.set_defaults(operation=name + "_create")
        listing = group.add_parser("list")
        listing.add_argument("--limit", type=int, default=50)
        listing.add_argument("--offset", type=int, default=0)
        listing.set_defaults(operation=name + "_list")
        if name == "run":
            create.add_argument("--workspace", dest="workspace_id", default="default")
            listing.add_argument("--workspace", dest="workspace_id", default="default")
    gc = command("gc", workspace=False)
    gc.add_argument("--apply", dest="dry_run", action="store_false", default=True)
    index = commands.add_parser("index").add_subparsers(dest="action", required=True)
    for name in ("status", "rebuild"):
        index.add_parser(name).set_defaults(operation="index_" + name)
    command("diagnostics", workspace=False)
    command("backup", workspace=False)
    restore = command("restore", workspace=False)
    restore.add_argument("backup_id")
    return parser


def _failure(code: str, message: str) -> int:
    print(json.dumps({"error": {"code": code, "message": message}}))
    return 1


class _NoRedirects(HTTPRedirectHandler):
    """An API redirect must never forward the local bearer token."""

    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def _call(args: argparse.Namespace) -> int:
    api_url = args.api_url or os.environ.get("DWS_API_URL", "http://127.0.0.1:8765")
    if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in api_url):
        return _failure("invalid_api_url", "The API URL contains invalid characters.")
    try:
        parsed = urlsplit(api_url)
        # Validate the port before urllib can raise an unhandled InvalidURL.
        if parsed.port == 0:
            return _failure("invalid_api_url", "The API URL must use a nonzero port.")
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return _failure("invalid_api_url", "The API URL must use HTTP or HTTPS.")
        if parsed.username is not None or parsed.password is not None:
            return _failure("invalid_api_url", "Supply bearer credentials using --token.")
    except ValueError:
        return _failure("invalid_api_url", "The API URL is malformed.")
    token = args.token or os.environ.get("DWS_TOKEN")
    if not token:
        directory = args.data_dir or Path(os.environ.get("DWS_DATA_DIR", ".state"))
        try:
            token = (directory / "api-token").read_text().strip()
        except (OSError, UnicodeError):
            return _failure("authentication_required", "Start the API or configure DWS_TOKEN.")
    payload: dict[str, Any] = {
        key: value
        for key, value in vars(args).items()
        if key not in {"api_url", "token", "data_dir", "command", "action", "operation"}
        and value is not None
    }
    try:
        request = Request(
            api_url.rstrip("/") + "/v1/" + args.operation,
            data=json.dumps(payload).encode(),
            headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
            method="POST",
        )
        opener = build_opener(ProxyHandler({}), _NoRedirects())
        try:
            response = opener.open(request, timeout=120)
        except HTTPError as error:
            if 300 <= error.code < 400:
                error.close()
                return _failure("api_redirect_denied", "The trusted API endpoint redirected.")
            response = error
        with response:
            body = response.read(2_000_001)
            if len(body) > 2_000_000:
                return _failure(
                    "response_too_large", "API response exceeded the client byte limit."
                )
            result = json.loads(body)
            if not isinstance(result, dict):
                return _failure(
                    "invalid_response", "The API returned an invalid response object."
                )
            print(json.dumps(result, ensure_ascii=False))
            return 1 if response.status >= 400 or "error" in result else 0
    except InvalidURL:
        return _failure("invalid_api_url", "The API URL is malformed.")
    except (URLError, TimeoutError, OSError):
        return _failure(
            "api_unavailable", "Cannot reach the DWS API; check its URL and running state."
        )
    except (ValueError, UnicodeDecodeError, RecursionError):
        return _failure("invalid_response", "The API returned invalid JSON.")


def main(argv: Sequence[str] | None = None) -> int:
    """Execute through the shared daemon contract; help/version stay lightweight."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    if args.command not in {"api", "worker"}:
        return _call(args)
    from dws.config import Settings

    values = Settings.from_env().model_dump()
    for key in ("api_url", "token", "data_dir"):
        if getattr(args, key) is not None:
            values[key] = getattr(args, key)
    if args.data_dir:
        values["data_dir"] = args.data_dir.absolute()
    settings = Settings.model_validate(values)
    if args.command == "api":
        import uvicorn

        from dws.api import create_app

        if not 1 <= args.port <= 65535:
            parser.error("--port must be between 1 and 65535")
        uvicorn.run(create_app(settings), host=args.host, port=args.port)
    else:
        import asyncio
        import logging

        from dws.worker import run

        if not 0.1 <= args.idle_seconds <= 60:
            parser.error("--idle-seconds must be between 0.1 and 60")
        logging.basicConfig(level=logging.INFO)
        asyncio.run(run(settings, once=args.once, idle_seconds=args.idle_seconds))
    return 0
