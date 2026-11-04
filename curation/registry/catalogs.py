"""Our merged catalog, reference resolution and capability classification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from curation.registry.config import RegistryConfig
from curation.registry.ledger import _is_trait_subject
from curation.registry.loaders import _catalog_files
from curation.registry.models import Event
from curation.scan.catalog import _is_test_script, scan_repo
from curation.scan.drift import pinned_commit, scan_checkout
from curation.scan.models import Capability, Catalog


def _merge_capability(existing: Any, other: Any) -> Any:
    return Capability(
        kind=existing.kind,
        name=existing.name,
        category=existing.category,
        logical_id=existing.logical_id,
        canonical_path=existing.canonical_path,
        paths=tuple(sorted(set(existing.paths) | set(other.paths))),
        description=existing.description or other.description,
        content_hash=existing.content_hash,
        signature_hash=existing.signature_hash,
        variant_hashes=tuple(
            sorted(set(existing.variant_hashes) | set(other.variant_hashes))
        ),
        line_count=existing.line_count,
        tree_hash=existing.tree_hash,
    )


def merge_catalogs(name: str, source: str, catalogs: list[Any]) -> Any:
    by_id: dict[str, Any] = {}
    for catalog in catalogs:
        for cap in catalog.capabilities:
            if cap.logical_id in by_id:
                by_id[cap.logical_id] = _merge_capability(by_id[cap.logical_id], cap)
            else:
                by_id[cap.logical_id] = cap
    caps = tuple(sorted(by_id.values(), key=lambda c: c.logical_id))
    counts: dict[str, dict[str, int]] = {}
    for cap in caps:
        bucket = counts.setdefault(cap.kind.value, {"physical": 0, "logical": 0})
        bucket["logical"] += 1
        bucket["physical"] += 1
    return Catalog(
        repo=name,
        source=source,
        source_commit=None,
        counts=counts,
        physical_scanned=sum(c.physical_scanned for c in catalogs),
        excluded=sum(c.excluded for c in catalogs),
        capabilities=caps,
    )


def _drop_template_caps(catalog: Any) -> Any:
    kept = tuple(
        c for c in catalog.capabilities if not c.canonical_path.startswith("template/")
    )
    return Catalog(
        repo=catalog.repo,
        source=catalog.source,
        source_commit=catalog.source_commit,
        counts=catalog.counts,
        physical_scanned=catalog.physical_scanned,
        excluded=catalog.excluded,
        capabilities=kept,
    )


def build_ours(cfg: RegistryConfig) -> Any:
    roots = [cfg.our_harness_root, cfg.codex_root] + sorted(
        cfg.repo_root.glob(cfg.plugins_glob)
    )
    catalogs: list[Any] = []
    for root in roots:
        if root.is_dir():
            cat = scan_repo(
                root,
                root.name,
                source=f"ours:{root.name}",
                source_commit=None,
                catalog_playbooks=False,
            )
            catalogs.append(_drop_template_caps(cat))
    return merge_catalogs("ours", "root .claude/.codex + plugins", catalogs)


def _normalize_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _normalized_index(ours: Any) -> dict[tuple[str, str], str]:
    index: dict[tuple[str, str], str] = {}
    for cap in ours.capabilities:
        index[(cap.kind.value, _normalize_name(cap.name))] = cap.logical_id
    return index


def match_to_ours(
    cap: Any, our_ids: dict[str, Any], normalized: dict[tuple[str, str], str]
) -> str | None:
    if cap.logical_id in our_ids:
        return str(cap.logical_id)
    return normalized.get((cap.kind.value, _normalize_name(cap.name)))


def classify_capability(
    cap: Any,
    repo: str,
    current: dict[str, Event],
    our_ids: dict[str, Any],
    normalized: dict[tuple[str, str], str],
) -> tuple[str, Event | None, str]:
    """One classification used by both `gap` and the reference pages.

    Returns (status, effective_event, changed). status is the effective ruling
    kind, or "present, unruled" (we have the same capability, never ruled), or
    "not reviewed". changed is "", "no", "yes" or "hash unknown".
    """
    event = current.get(f"{repo}:{cap.logical_id}")
    if event is None:
        if match_to_ours(cap, our_ids, normalized) is not None:
            return "present, unruled", None, ""
        return "not reviewed", None, ""
    src_hash = event.source.content_hash if event.source else None
    if src_hash is None:
        changed = "hash unknown"
    elif src_hash != cap.content_hash:
        changed = "yes"
    else:
        changed = "no"
    return event.kind, event, changed


def resolve_reference(cfg: RegistryConfig, arg: str) -> Any:
    path = Path(arg)
    if path.suffix == ".json" and path.exists():
        return Catalog.from_dict(json.loads(path.read_text(encoding="utf-8")))
    if path.is_dir():
        return _scan_dir(path.resolve())
    submodule = cfg.repo_root / "reference_harnesses" / arg
    if submodule.is_dir():
        return _scan_dir(submodule.resolve())
    catalog_path = cfg.catalogs_dir / f"{arg}.json"
    if catalog_path.exists():
        return Catalog.from_dict(json.loads(catalog_path.read_text(encoding="utf-8")))
    raise SystemExit(
        f"reference not found: {arg} (tried path, *.json, reference_harnesses/{arg}, catalogs/{arg}.json)"
    )


def _scan_dir(root: Path) -> Any:
    commit = None
    if (root / ".git").exists():
        try:
            commit = pinned_commit(root)
        except Exception:  # noqa: BLE001 - best-effort commit stamp, no network
            commit = None
    return scan_checkout(root, root.name, commit)


_CAP_KINDS = frozenset(
    {"skill", "playbook", "agent", "command", "rule", "hook", "mcp", "plugin"}
)


def _is_genuine_capability_subject(subject: str) -> bool:
    """A capability subject the scanner would surface if it still shipped — so a
    `doc:` ruling or a scanner-excluded `-test` hook never reads as "removed
    upstream" (reviews #13 / avoids false positives)."""
    _, _, logical = subject.partition(":")
    kind, _, rest = logical.partition(":")
    if kind not in _CAP_KINDS:
        return False
    name = rest.rsplit("/", 1)[-1].split("#", 1)[0]
    return not (kind == "hook" and _is_test_script(name))


def _removed_upstream(
    repo: str, current: dict[str, Event], present_ids: set[str]
) -> list[tuple[str, Event]]:
    """Effective capability rulings whose logical id is no longer in the catalog
    (genuine upstream removals only), independent of reference records (§5, §6)."""
    return sorted(
        (
            (subject, event)
            for subject, event in current.items()
            if not subject.startswith("ours:")
            and not _is_trait_subject(subject)
            and event.source is not None
            and event.source.repo == repo
            and event.source.logical_id not in present_ids
            and _is_genuine_capability_subject(subject)
        ),
        key=lambda t: t[0],
    )


def _autofill_source(
    cfg: RegistryConfig, repo: str, logical_id: str
) -> dict[str, Any] | None:
    """Fill a reference source from the current catalog/scan, so a new ruling can
    later be flagged "changed since ruled"."""
    try:
        ref = resolve_reference(cfg, repo)
    except SystemExit:
        return None
    cap = ref.by_logical_id().get(logical_id)
    if cap is None:
        return None
    source: dict[str, Any] = {
        "repo": repo,
        "logical_id": logical_id,
        "path": cap.canonical_path,
        "sha": ref.source_commit,
        "content_hash": cap.content_hash,
    }
    # Only persist a real folder hash; never fabricate one for a legacy skill
    # whose catalog predates tree hashing (review #12).
    if cap.tree_hash:
        source["tree_hash"] = cap.tree_hash
    return source


def _catalog_subjects(cfg: RegistryConfig) -> set[str]:
    """Every `<repo>:<logical_id>` currently in a catalog file (traits-design §2:
    an upstream key must be in the catalog or ruled removed upstream)."""
    out: set[str] = set()
    for cat_path in _catalog_files(cfg):
        try:
            catalog = Catalog.from_dict(
                json.loads(cat_path.read_text(encoding="utf-8"))
            )
        except Exception:  # noqa: BLE001, S112 - malformed catalogs ignored here
            continue
        for logical in catalog.by_logical_id():
            out.add(f"{catalog.repo}:{logical}")
    return out
