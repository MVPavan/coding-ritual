"""Frozen results from walking runner-owned output directories."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

_MODEL = ConfigDict(frozen=True, extra="forbid")


class UnsafeKind(StrEnum):
    """Why an output entry was excluded from the wrapper-owned snapshot."""

    ROOT = "root"
    SYMLINK = "symlink"
    SPECIAL = "special"
    TOO_DEEP = "too-deep"
    TOO_WIDE = "too-wide"
    CAPTURE_FAILED = "capture-failed"


class UnsafeEntry(BaseModel):
    """One excluded output path and its safe classification."""

    model_config = _MODEL

    path: str
    kind: UnsafeKind


class OutputsWalk(BaseModel):
    """The bounded wrapper-owned capture of runner output."""

    model_config = _MODEL

    paths: tuple[str, ...] = ()
    unsafe: tuple[UnsafeEntry, ...] = ()
    truncated: bool = False
    total_bytes: int = 0


__all__ = ["OutputsWalk", "UnsafeEntry", "UnsafeKind"]
