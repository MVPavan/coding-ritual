"""Whole-brief UTF-8 accounting. Optional sections are omitted, never truncated."""

import hashlib
from typing import Literal

from pydantic import BaseModel, ConfigDict


class InputsUnavailable(ValueError):
    """Required input cannot be proved or safely composed."""


class EnvelopeRefusal(InputsUnavailable):
    """An essential envelope exceeds its byte limit."""

    def __init__(self, measured: int, limit: int, *, exact: bool = True) -> None:
        self.measured = measured
        self.limit = limit
        self.exact = exact
        super().__init__(
            f"envelope requires {'at least ' if not exact else ''}{measured} utf8-bytes; limit {limit}"
        )


class InputOmission(BaseModel):
    """A full source remains accessible by its immutable reference."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    reason: Literal["missing", "budget"]
    reference: str | None = None
    digest: str | None = None
    measured_bytes: int | None = None
    exact: bool = True


class EnvelopeSection(BaseModel):
    """A labelled section with an explicit removal priority."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str
    name: str
    optional: bool = False
    trim_priority: int = 0
    reference: str | None = None
    digest: str | None = None


class ComposedEnvelope(BaseModel):
    """Exactly the brief passed to the adapter, with durable accounting."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str
    byte_count: int
    limit: int
    counting_method: Literal["utf8-bytes"] = "utf8-bytes"
    limit_source: str
    diagnostics: tuple[str, ...] = ()
    included: tuple[str, ...]
    omissions: tuple[InputOmission, ...]
    sha256: str


def compose_envelope(
    mandatory: str,
    sections: tuple[EnvelopeSection, ...],
    *,
    limit: int,
    reference: str,
    omissions: tuple[InputOmission, ...] = (),
    limit_source: str = "pinned",
    diagnostics: tuple[str, ...] = (),
) -> ComposedEnvelope:
    """Count all framing; drop optional sections in stable priority order."""
    kept = list(sections)
    omitted = list(omissions)
    candidates = sorted(
        (s for s in kept if s.optional), key=lambda s: (-s.trim_priority, s.name)
    )
    while True:
        manifest = "\n".join(item.model_dump_json() for item in omitted)
        digest = hashlib.sha256(manifest.encode()).hexdigest()
        footer = (
            f"Input omissions: {len(omitted)}; manifest {reference}; sha256 {digest}"
        )
        text = "\n\n".join(
            part.strip()
            for part in (mandatory, footer, *(s.text for s in kept))
            if part.strip()
        )
        size = len(text.encode("utf-8"))
        if size <= limit:
            return ComposedEnvelope(
                text=text,
                byte_count=size,
                limit=limit,
                limit_source=limit_source,
                diagnostics=diagnostics,
                included=tuple(s.name for s in kept),
                omissions=tuple(omitted),
                sha256=hashlib.sha256(text.encode()).hexdigest(),
            )
        if not candidates:
            raise EnvelopeRefusal(size, limit)
        drop = candidates.pop(0)
        kept.remove(drop)
        omitted.append(
            InputOmission(
                name=drop.name,
                reason="budget",
                reference=drop.reference,
                digest=drop.digest,
                measured_bytes=len(drop.text.encode()),
            )
        )
