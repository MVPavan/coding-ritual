"""Shared closed capability inputs and acquisition records."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    workspace_id: str = Field(default="default", min_length=1, max_length=100)


class SearchRequest(Input):
    query: str = Field(min_length=1, max_length=512)
    limit: int = Field(default=10, ge=1, le=50)
    domains: list[str] = Field(default_factory=list, max_length=20)


class FetchRequest(Input):
    url: str = Field(min_length=1, max_length=4096)
    run_id: str | None = Field(default=None, max_length=100)
    refresh: bool = False
    render: Literal["auto", "always", "never"] = "auto"
    max_age_seconds: int = Field(default=3600, ge=0, le=31_536_000)


class CrawlRequest(Input):
    seed_url: str = Field(min_length=1, max_length=4096)
    run_id: str | None = Field(default=None, max_length=100)
    scope: Literal["same_host", "same_path"] = "same_path"
    max_pages: int = Field(default=50, ge=1, le=5000)
    max_depth: int = Field(default=2, ge=0, le=20)
    max_seconds: int = Field(default=300, ge=1, le=3600)
    render: Literal["auto", "always", "never"] = "auto"
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=128)


class RetrieveRequest(Input):
    query: str = Field(min_length=1, max_length=512)
    run_id: str | None = None
    crawl_id: str | None = None
    document_ids: list[str] = Field(default_factory=list, max_length=100)
    limit: int = Field(default=5, ge=1, le=50)
    max_chars: int = Field(default=6000, ge=256, le=100_000)


class ReadRequest(Input):
    snapshot_id: str = Field(min_length=1, max_length=100)
    line_start: int = Field(default=1, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    section: str | None = Field(default=None, min_length=1, max_length=256)
    max_chars: int = Field(default=6000, ge=256, le=100_000)


class JobRequest(Input):
    job_id: str = Field(min_length=1, max_length=100)
    offset: int = Field(default=0, ge=0, le=2**63 - 1)
    limit: int = Field(default=20, ge=1, le=100)


class Capture(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    requested_url: str
    final_url: str
    content_type: str
    title: str
    text: str
    raw: bytes = Field(repr=False, exclude=True)
    # Extractor-owned retained-text offsets; never infer pages from source headings.
    pdf_page_starts: list[tuple[int, int]] = Field(
        default_factory=list, repr=False, exclude=True
    )
    links: list[str] = Field(default_factory=list)
    redirects: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    normalizer: str
    provider: str
