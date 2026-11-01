"""Catalog data types: capabilities, catalogs and catalog diffs (stdlib only)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

SCHEMA = "harness-capability-catalog/v1"


class Kind(str, Enum):
    """The kinds of capability a harness can ship."""

    SKILL = "skill"
    PLAYBOOK = "playbook"
    COMMAND = "command"
    AGENT = "agent"
    RULE = "rule"
    HOOK = "hook"
    MCP = "mcp"
    PLUGIN = "plugin"


@dataclass(frozen=True)
class Capability:
    """One logical capability, collapsed across mirror copies."""

    kind: Kind
    name: str
    category: str
    logical_id: str
    canonical_path: str
    paths: tuple[str, ...]
    description: str
    content_hash: str
    signature_hash: str
    variant_hashes: tuple[str, ...]
    line_count: int
    # Non-capability files bundled inside a skill's own folder (prompt templates
    # handed to subagents, helper scripts), or a playbook's reference folder. They
    # are part of it, not separate capabilities, so they are recorded here rather
    # than as own rows.
    assets: tuple[str, ...] = ()
    # sha256 over every file in a skill's folder (SKILL.md + assets) or over a
    # playbook's file and reference folder; for other kinds it equals content_hash.
    # Lets `gap` see asset-only changes (§4).
    tree_hash: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "name": self.name,
            "category": self.category,
            "logical_id": self.logical_id,
            "canonical_path": self.canonical_path,
            "paths": list(self.paths),
            "description": self.description,
            "content_hash": self.content_hash,
            "signature_hash": self.signature_hash,
            "variant_hashes": list(self.variant_hashes),
            "line_count": self.line_count,
            "assets": list(self.assets),
            # Written verbatim; never fabricated from content_hash. A skill whose
            # folder hash is unknown stays "" so `gap` treats it as no baseline.
            "tree_hash": self.tree_hash,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Capability:
        content_hash = str(data["content_hash"])
        kind = Kind(data["kind"])
        raw_tree = data.get("tree_hash")
        if raw_tree:
            tree_hash = str(raw_tree)
        elif kind is not Kind.SKILL:
            # For non-skills the tree hash *is* the content hash (§4), so a legacy
            # catalog without the field can safely reconstruct it.
            tree_hash = content_hash
        else:
            # A legacy skill catalog has no real folder hash; leave it unknown
            # rather than fabricating one from SKILL.md alone (review #12).
            tree_hash = ""
        return Capability(
            kind=kind,
            name=str(data["name"]),
            category=str(data.get("category", "")),
            logical_id=str(data["logical_id"]),
            canonical_path=str(data["canonical_path"]),
            paths=tuple(str(p) for p in data.get("paths", [])),
            description=str(data.get("description", "")),
            content_hash=content_hash,
            signature_hash=str(data["signature_hash"]),
            variant_hashes=tuple(str(h) for h in data.get("variant_hashes", [])),
            line_count=int(data.get("line_count", 0)),
            assets=tuple(str(a) for a in data.get("assets", [])),
            tree_hash=tree_hash,
        )


@dataclass(frozen=True)
class Catalog:
    """A full capability inventory of one harness at one point in time."""

    repo: str
    source: str
    source_commit: str | None
    counts: dict[str, dict[str, int]]
    physical_scanned: int
    excluded: int
    capabilities: tuple[Capability, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema": SCHEMA,
            "repo": self.repo,
            "source": self.source,
            "source_commit": self.source_commit,
            "physical_scanned": self.physical_scanned,
            "excluded": self.excluded,
            "counts": self.counts,
            "capabilities": [c.to_dict() for c in self.capabilities],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Catalog:
        return Catalog(
            repo=str(data["repo"]),
            source=str(data.get("source", "")),
            source_commit=(
                str(data["source_commit"]) if data.get("source_commit") else None
            ),
            counts=dict(data.get("counts", {})),
            physical_scanned=int(data.get("physical_scanned", 0)),
            excluded=int(data.get("excluded", 0)),
            capabilities=tuple(
                Capability.from_dict(c) for c in data.get("capabilities", [])
            ),
        )

    def by_logical_id(self) -> dict[str, Capability]:
        return {c.logical_id: c for c in self.capabilities}


@dataclass(frozen=True)
class _Entry:
    kind: Kind
    name: str
    relpath: str
    dedup_key: str
    content_hash: str
    signature_hash: str
    description: str
    line_count: int
    rank: int
    category: str = ""
    assets: tuple[str, ...] = ()
    tree_hash: str = ""


class Material(str, Enum):
    MATERIAL = "material"
    MINOR = "minor"


@dataclass(frozen=True)
class CatalogDiff:
    added: tuple[Capability, ...]
    removed: tuple[Capability, ...]
    moved: tuple[tuple[Capability, Capability], ...]
    modified_material: tuple[tuple[Capability, str], ...]
    modified_minor: tuple[tuple[Capability, str], ...]
