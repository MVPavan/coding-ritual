"""One application facade for CLI, HTTP and MCP."""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import os
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from dws.config import Settings
from dws.errors import DWSError
from dws.jobs import Jobs
from dws.models import (
    CrawlRequest,
    FetchRequest,
    Input,
    JobRequest,
    ReadRequest,
    RetrieveRequest,
    SearchRequest,
)
from dws.net import canonical_url
from dws.providers import Acquisition
from dws.store import Store


class Empty(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class WorkspaceCreate(Empty):
    name: str = Field(min_length=1, max_length=128)


class RunCreate(Input):
    name: str = Field(default="", max_length=128)


class WorkspaceList(Empty):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=2**63 - 1)


class RunList(Input):
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=2**63 - 1)


class SnapshotInput(Input):
    snapshot_id: str = Field(min_length=1, max_length=100)


class PinInput(SnapshotInput):
    pinned: bool = True


class GCInput(Empty):
    dry_run: bool = True


class RestoreInput(Empty):
    backup_id: str = Field(min_length=1, max_length=100)


REQUEST_MODELS: dict[str, type[BaseModel]] = {
    "search": SearchRequest,
    "fetch": FetchRequest,
    "crawl": CrawlRequest,
    "retrieve": RetrieveRequest,
    "read": ReadRequest,
    "job_status": JobRequest,
    "job_cancel": JobRequest,
    "workspace_create": WorkspaceCreate,
    "workspace_list": WorkspaceList,
    "run_create": RunCreate,
    "run_list": RunList,
    "pin": PinInput,
    "export": SnapshotInput,
    "expire": SnapshotInput,
    "gc": GCInput,
    "index_status": Empty,
    "index_rebuild": Empty,
    "diagnostics": Empty,
    "backup": Empty,
    "restore": RestoreInput,
}


class Engine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.store = Store(settings)
        self.acquisition = Acquisition(settings)
        self.jobs = Jobs(settings, self.store, self.acquisition)

    @asynccontextmanager
    async def acquisition_group(self, request: FetchRequest) -> AsyncIterator[None]:
        # Fixed lock stripes bound persistent coordination state. Equivalent
        # simultaneous fetches share a stripe and recheck the committed cache.
        key = f"{request.workspace_id}|{canonical_url(request.url)}|{request.render}"
        stripe = int(hashlib.sha256(key.encode()).hexdigest()[:4], 16) % 64
        path = self.settings.data_dir / "locks" / f"fetch-group-{stripe}.lock"
        descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        started = time.monotonic()
        try:
            while True:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() - started > self.settings.request_timeout:
                        raise DWSError(
                            "busy", "Equivalent acquisition is still running", 429
                        ) from None
                    await asyncio.sleep(0.05)
            yield
        finally:
            os.close(descriptor)

    async def execute(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        model = REQUEST_MODELS.get(operation)
        if model is None:
            raise DWSError("unknown_operation", "Unknown DWS capability", 404)
        request = model.model_validate(payload)
        result: dict[str, Any]
        if isinstance(request, SearchRequest):
            result = await self.acquisition.search(request)
        elif isinstance(request, FetchRequest):
            request = FetchRequest.model_validate(
                {**request.model_dump(), "url": canonical_url(request.url)}
            )
            # Look up retained evidence before contacting any provider.
            async with self.acquisition_group(request):
                cached = await asyncio.to_thread(self.store.cached_fetch, request)
                if cached is not None:
                    result = cached
                else:
                    capture = await self.acquisition.fetch(request)
                    result = await asyncio.to_thread(
                        self.store.save_capture, capture, request.workspace_id, request.run_id
                    )
                    result["cache"] = {"hit": False, "stale": False}
        elif isinstance(request, CrawlRequest):
            result = await self.jobs.submit(request)
        elif isinstance(request, RetrieveRequest):
            result = await asyncio.to_thread(self.store.retrieve, request)
        elif isinstance(request, ReadRequest):
            result = await asyncio.to_thread(self.store.read, request)
        elif isinstance(request, JobRequest):
            fn = self.jobs.status if operation == "job_status" else self.jobs.cancel
            result = await asyncio.to_thread(fn, request)
        elif isinstance(request, WorkspaceCreate):
            result = await asyncio.to_thread(self.store.create_workspace, request.name)
        elif isinstance(request, RunCreate):
            result = await asyncio.to_thread(
                self.store.create_run, request.workspace_id, request.name
            )
        elif isinstance(request, WorkspaceList):
            result = await asyncio.to_thread(
                self.store.list_workspaces, request.limit, request.offset
            )
        elif isinstance(request, RunList):
            result = await asyncio.to_thread(
                self.store.list_runs, request.workspace_id, request.limit, request.offset
            )
        elif isinstance(request, PinInput):
            result = await asyncio.to_thread(
                self.store.pin, request.snapshot_id, request.workspace_id, request.pinned
            )
        elif isinstance(request, SnapshotInput):
            snapshot_action = self.store.export if operation == "export" else self.store.expire
            result = await asyncio.to_thread(
                snapshot_action, request.snapshot_id, request.workspace_id
            )
        elif isinstance(request, GCInput):
            result = await asyncio.to_thread(self.store.gc, request.dry_run)
        elif isinstance(request, RestoreInput):
            result = await asyncio.to_thread(self.store.restore, request.backup_id)
        elif operation == "index_rebuild":
            result = await asyncio.to_thread(self.store.rebuild_index)
        elif operation == "backup":
            result = await asyncio.to_thread(self.store.backup)
        else:
            result = await asyncio.to_thread(self.store.diagnostics)
        response = {"schema_version": "1.0", "request_id": uuid.uuid4().hex, **result}
        if (
            len(json.dumps(response, ensure_ascii=False).encode())
            > self.settings.max_response_bytes
        ):
            raise DWSError(
                "output_limit",
                "Result exceeds the response byte budget; reduce result count or read range.",
                413,
            )
        return response
