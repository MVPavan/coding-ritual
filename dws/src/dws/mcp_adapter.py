"""Optional MCP tools and retained resources over the same DWS engine."""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError
from fastmcp.tools import ToolResult
from mcp_types import ContentBlock, ResourceLink, TextContent
from pydantic import ValidationError

from dws.engine import Engine
from dws.errors import DWSError


def create_mcp(engine: Engine) -> FastMCP:
    """Create a thin adapter; application state and validation stay in Engine."""
    mcp = FastMCP("DWS", mask_error_details=True)

    async def execute(operation: str, payload: dict[str, Any]) -> ToolResult:
        try:
            result = await engine.execute(operation, payload)
        except DWSError as error:
            return ToolResult(
                content=[TextContent(text=f"{error.code}: {error.message[:512]}")],
                structured_content=error.payload(),
                is_error=True,
            )
        except ValidationError as error:
            fields = [".".join(str(x) for x in item["loc"]) for item in error.errors()]
            public = {"error": {"code": "invalid_request", "fields": fields[:20]}}
            return ToolResult(
                content=[
                    TextContent(text="Invalid request fields: " + ", ".join(fields)[:512])
                ],
                structured_content=public,
                is_error=True,
            )
        content: list[ContentBlock] = [TextContent(text=f"DWS {operation} result.")]
        snapshots = [result] if result.get("snapshot_id") else result.get("results", [])
        seen: set[str] = set()
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                continue
            identifier, workspace = snapshot.get("snapshot_id"), snapshot.get("workspace_id")
            if (
                not isinstance(identifier, str)
                or not isinstance(workspace, str)
                or identifier in seen
            ):
                continue
            seen.add(identifier)
            uri = (
                "dws://workspace/"
                + quote(workspace, safe="")
                + "/snapshot/"
                + quote(identifier, safe="")
                + "/content"
            )
            content.append(
                ResourceLink(
                    name=identifier,
                    title=str(snapshot.get("title", "Retained snapshot"))[:256],
                    uri=uri,
                    mime_type="text/markdown",
                    description="Exact retained snapshot; use read for bounded ranges.",
                )
            )
            if len(seen) == 5:
                break
        return ToolResult(content=content, structured_content=result)

    @mcp.tool(output_schema=None)
    async def search(
        query: str,
        workspace_id: str = "default",
        limit: int = 10,
        domains: list[str] | None = None,
    ) -> ToolResult:
        """Discover public-web URLs; snippets are discovery metadata, not acquired evidence."""
        return await execute(
            "search",
            {
                "query": query,
                "workspace_id": workspace_id,
                "limit": limit,
                "domains": domains or [],
            },
        )

    @mcp.tool(output_schema=None)
    async def fetch(
        url: str,
        workspace_id: str = "default",
        run_id: str | None = None,
        refresh: bool = False,
        render: Literal["auto", "always", "never"] = "auto",
        max_age_seconds: int = 3600,
    ) -> ToolResult:
        """Capture a selected public URL and return a stable retained-evidence handle."""
        return await execute(
            "fetch",
            {
                "url": url,
                "workspace_id": workspace_id,
                "run_id": run_id,
                "refresh": refresh,
                "render": render,
                "max_age_seconds": max_age_seconds,
            },
        )

    @mcp.tool(output_schema=None)
    async def crawl(
        seed_url: str,
        workspace_id: str = "default",
        run_id: str | None = None,
        scope: Literal["same_host", "same_path"] = "same_path",
        max_pages: int = 50,
        max_depth: int = 2,
        max_seconds: int = 300,
        render: Literal["auto", "always", "never"] = "auto",
        idempotency_key: str | None = None,
    ) -> ToolResult:
        """Submit a durable bounded crawl; inspect and cancel it using its job handle."""
        return await execute(
            "crawl",
            {
                "seed_url": seed_url,
                "workspace_id": workspace_id,
                "run_id": run_id,
                "scope": scope,
                "max_pages": max_pages,
                "max_depth": max_depth,
                "max_seconds": max_seconds,
                "render": render,
                "idempotency_key": idempotency_key,
            },
        )

    @mcp.tool(output_schema=None)
    async def retrieve(
        query: str,
        workspace_id: str = "default",
        run_id: str | None = None,
        crawl_id: str | None = None,
        document_ids: list[str] | None = None,
        limit: int = 5,
        max_chars: int = 6000,
    ) -> ToolResult:
        """Retrieve exact retained passages with scope enforced before ranking and limiting."""
        return await execute(
            "retrieve",
            {
                "query": query,
                "workspace_id": workspace_id,
                "run_id": run_id,
                "crawl_id": crawl_id,
                "document_ids": document_ids or [],
                "limit": limit,
                "max_chars": max_chars,
            },
        )

    @mcp.tool(output_schema=None)
    async def read(
        snapshot_id: str,
        workspace_id: str = "default",
        line_start: int = 1,
        line_end: int | None = None,
        section: str | None = None,
        max_chars: int = 6000,
    ) -> ToolResult:
        """Read an exact bounded snapshot range or section without depending on its index."""
        return await execute(
            "read",
            {
                "snapshot_id": snapshot_id,
                "workspace_id": workspace_id,
                "line_start": line_start,
                "line_end": line_end,
                "section": section,
                "max_chars": max_chars,
            },
        )

    @mcp.tool(output_schema=None)
    async def job_status(
        job_id: str,
        workspace_id: str = "default",
        offset: int = 0,
        limit: int = 20,
    ) -> ToolResult:
        """Inspect durable job state and a bounded result-manifest page."""
        return await execute(
            "job_status",
            {
                "job_id": job_id,
                "workspace_id": workspace_id,
                "offset": offset,
                "limit": limit,
            },
        )

    @mcp.tool(output_schema=None)
    async def job_cancel(job_id: str, workspace_id: str = "default") -> ToolResult:
        """Request cancellation while preserving all already acquired evidence."""
        return await execute("job_cancel", {"job_id": job_id, "workspace_id": workspace_id})

    @mcp.resource(
        "dws://workspace/{workspace_id}/snapshot/{snapshot_id}/content",
        mime_type="text/markdown",
    )
    async def snapshot_content(workspace_id: str, snapshot_id: str) -> str:
        """Read the complete exact snapshot only when it fits the operator output budget."""
        try:
            result = await engine.execute(
                "read",
                {
                    "workspace_id": workspace_id,
                    "snapshot_id": snapshot_id,
                    "max_chars": min(engine.settings.max_output_chars, 100_000),
                },
            )
        except DWSError as error:
            raise ResourceError(f"{error.code}: {error.message[:512]}") from None
        except ValidationError:
            raise ResourceError(
                "invalid_request: Invalid retained resource identifier."
            ) from None
        if result.get("truncated"):
            raise ResourceError(
                "resource_too_large: Use the read tool for bounded lines or sections."
            )
        text = result.get("text")
        if not isinstance(text, str):
            raise ResourceError("invalid_response: Snapshot content is unavailable.")
        return text

    return mcp
