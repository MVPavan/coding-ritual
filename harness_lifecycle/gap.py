#!/usr/bin/env python3
"""Gap report + adoption ledger for reference-harness curation.

Complements scan.py. Where `scan drift` answers "what changed upstream?", this
answers "what do the reference harnesses ship that OUR harness doesn't — minus
whatever we've already decided about?".

  ours [--out FILE]
      Catalog our own harness (root .claude/ + mvp-harness/plugins/*) into one
      merged catalog.
  gap <reference> [--kind KIND] [--beads]
      Capabilities in <reference> with no counterpart in ours, excluding anything
      already recorded in the ledger. <reference> is a reference_harnesses/<name>
      path, a catalogs/<name>.json file, or a bare <name> under catalogs/.
  ledger list
  ledger add --repo R --id LOGICAL_ID --status adopted|rejected|deferred
             --reason TEXT [--our-id OUR_ID] [--source-sha SHA]

Matching a reference capability to ours: exact logical_id -> curated alias ->
normalized name -> otherwise it is a gap. Fuzzy name similarity is surfaced only
as a hint, never used to auto-match.

Pure standard library; imports the scanner from scan.py.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import shlex
import sys
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan  # noqa: E402

HL_DIR = Path(__file__).resolve().parent
REPO_ROOT = HL_DIR.parent
ALIASES_PATH = HL_DIR / "aliases.json"
LEDGER_PATH = HL_DIR / "ledger.json"
CATALOGS_DIR = HL_DIR / "catalogs"

OUR_HARNESS_ROOT = REPO_ROOT / ".claude"
PLUGINS_GLOB = "mvp-harness/plugins/*"

FUZZY_HINT_THRESHOLD = 0.62
LEDGER_SCHEMA = "harness-adoption-ledger/v1"


# --- "ours": merge root harness + plugins into one catalog --------------------


def _merge_capability(existing: scan.Capability, other: scan.Capability) -> scan.Capability:
    return scan.Capability(
        kind=existing.kind,
        name=existing.name,
        logical_id=existing.logical_id,
        canonical_path=existing.canonical_path,
        paths=tuple(sorted(set(existing.paths) | set(other.paths))),
        description=existing.description or other.description,
        content_hash=existing.content_hash,
        signature_hash=existing.signature_hash,
        variant_hashes=tuple(sorted(set(existing.variant_hashes) | set(other.variant_hashes))),
        line_count=existing.line_count,
    )


def merge_catalogs(name: str, source: str, catalogs: list[scan.Catalog]) -> scan.Catalog:
    """Union several catalogs by logical_id (first wins for the canonical copy)."""
    by_id: dict[str, scan.Capability] = {}
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
    return scan.Catalog(
        repo=name,
        source=source,
        source_commit=None,
        counts=counts,
        physical_scanned=sum(c.physical_scanned for c in catalogs),
        excluded=sum(c.excluded for c in catalogs),
        capabilities=caps,
    )


def _drop_template_caps(catalog: scan.Catalog) -> scan.Catalog:
    """Drop a plugin's template/ payload — it is a genericised copy of the root
    harness, not a capability of its own (avoids double-counting in 'ours')."""
    kept = tuple(c for c in catalog.capabilities if not c.canonical_path.startswith("template/"))
    return dataclasses.replace(catalog, capabilities=kept)


def build_ours() -> scan.Catalog:
    """Catalog our reusable surface: root .claude/ + .codex/ + every shipped plugin,
    excluding each plugin's template/ copy of the root harness."""
    roots = [OUR_HARNESS_ROOT, REPO_ROOT / ".codex"] + sorted(REPO_ROOT.glob(PLUGINS_GLOB))
    catalogs: list[scan.Catalog] = []
    for root in roots:
        if root.is_dir():
            cat = scan.scan_repo(root, root.name, source=f"ours:{root.name}", source_commit=None)
            catalogs.append(_drop_template_caps(cat))
    return merge_catalogs("ours", "root .claude/.codex + plugins", catalogs)


# --- Matching -----------------------------------------------------------------


def _normalize_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _normalized_index(ours: scan.Catalog) -> dict[tuple[str, str], str]:
    index: dict[tuple[str, str], str] = {}
    for cap in ours.capabilities:
        index[(cap.kind.value, _normalize_name(cap.name))] = cap.logical_id
    return index


def match_to_ours(
    cap: scan.Capability,
    our_ids: dict[str, scan.Capability],
    aliases: dict[str, str],
    normalized: dict[tuple[str, str], str],
) -> str | None:
    """Return the matching OUR logical_id, or None if this is a genuine gap."""
    if cap.logical_id in our_ids:
        return cap.logical_id
    alias = aliases.get(cap.logical_id)
    if alias and alias in our_ids:
        return alias
    return normalized.get((cap.kind.value, _normalize_name(cap.name)))


def fuzzy_hint(cap: scan.Capability, ours: scan.Catalog) -> str | None:
    best_ratio = 0.0
    best_name = ""
    for our_cap in ours.capabilities:
        if our_cap.kind is not cap.kind:
            continue
        ratio = SequenceMatcher(None, cap.name, our_cap.name).ratio()
        if ratio > best_ratio:
            best_ratio, best_name = ratio, our_cap.name
    if best_ratio >= FUZZY_HINT_THRESHOLD:
        return f"{best_name} ({best_ratio:.0%})"
    return None


# --- Ledger -------------------------------------------------------------------


def load_json(path: Path) -> Any:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_aliases() -> dict[str, str]:
    data = load_json(ALIASES_PATH) or {}
    return dict(data.get("aliases", {}))


def load_ledger() -> list[dict[str, object]]:
    data = load_json(LEDGER_PATH) or {}
    return list(data.get("entries", []))


def ledger_index(entries: list[dict[str, object]]) -> dict[tuple[str, str], dict[str, object]]:
    return {(str(e["repo"]), str(e["logical_id"])): e for e in entries}


def write_ledger(entries: list[dict[str, object]]) -> None:
    payload = {
        "schema": LEDGER_SCHEMA,
        "_comment": (load_json(LEDGER_PATH) or {}).get(
            "_comment", "adoption decisions; see harness_lifecycle/README.md"
        ),
        "entries": entries,
    }
    LEDGER_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# --- Reference resolution -----------------------------------------------------


def resolve_reference(arg: str) -> scan.Catalog:
    path = Path(arg)
    if path.suffix == ".json" and path.exists():
        return scan.Catalog.from_dict(load_json(path))
    if path.is_dir():
        root = path.resolve()
        commit = None
        if (root / ".git").exists():
            try:
                commit = scan.pinned_commit(root)
            except Exception:  # noqa: BLE001 - best effort commit stamp
                commit = None
        return scan.scan_repo(root, root.name, source="working-tree", source_commit=commit)
    catalog_path = CATALOGS_DIR / f"{arg}.json"
    if catalog_path.exists():
        return scan.Catalog.from_dict(load_json(catalog_path))
    raise SystemExit(f"reference not found: {arg} (tried path, *.json, catalogs/{arg}.json)")


# --- Commands -----------------------------------------------------------------


@dataclass(frozen=True)
class Gap:
    cap: scan.Capability
    hint: str | None


def compute_gap(
    ref: scan.Catalog, ours: scan.Catalog, kind: str | None
) -> tuple[list[Gap], list[tuple[scan.Capability, dict[str, object]]]]:
    our_ids = ours.by_logical_id()
    aliases = load_aliases()
    normalized = _normalized_index(ours)
    ledger = ledger_index(load_ledger())
    gaps: list[Gap] = []
    improved: list[tuple[scan.Capability, dict[str, object]]] = []
    for cap in ref.capabilities:
        if kind and cap.kind.value != kind:
            continue
        entry = ledger.get((ref.repo, cap.logical_id))
        if entry is not None:
            if entry.get("status") == "adopted":
                source_hash = entry.get("source_content_hash")
                if source_hash and cap.content_hash != source_hash:
                    improved.append((cap, entry))
            continue
        if match_to_ours(cap, our_ids, aliases, normalized) is not None:
            continue
        gaps.append(Gap(cap=cap, hint=fuzzy_hint(cap, ours)))
    gaps.sort(key=lambda g: g.cap.logical_id)
    return gaps, improved


def render_gap(ref: scan.Catalog, ours: scan.Catalog, gaps: list[Gap], improved, emit_beads: bool) -> str:
    lines = [
        f"## gap: {ref.repo}  vs  ours ({sum(v['logical'] for v in ours.counts.values())} capabilities)",
        f"{len(gaps)} capabilities they have that we don't (ledgered decisions excluded)",
    ]
    by_kind: dict[str, list[Gap]] = {}
    for gap in gaps:
        by_kind.setdefault(gap.cap.kind.value, []).append(gap)
    for kind in scan.Kind:
        bucket = by_kind.get(kind.value)
        if not bucket:
            continue
        lines.append(f"\n### {kind.value} ({len(bucket)})")
        for gap in bucket:
            desc = f" — {gap.cap.description}" if gap.cap.description else ""
            hint = f"   [similar to ours: {gap.hint}]" if gap.hint else ""
            lines.append(f"  + {gap.cap.name}{desc}{hint}")
    if improved:
        lines.append(f"\n### ⚑ upstream improved since we adopted ({len(improved)})")
        for cap, entry in improved:
            lines.append(f"  ~ {cap.logical_id}  (adopted as {entry.get('our_id', '?')}; reason: {entry.get('reason', '')})")
    if emit_beads and gaps:
        lines.append("\n### bd create lines (review before running)")
        for gap in gaps:
            title = f"Evaluate {gap.cap.kind.value} {gap.cap.name} from {ref.repo}"
            desc = (f"Gap candidate {gap.cap.logical_id} from {ref.repo} "
                    f"({gap.cap.canonical_path}). Decide adopt/reject/defer via harness-evaluate.")
            lines.append(
                f"bd create --title={shlex.quote(title)} "
                f"--description={shlex.quote(desc)} --type=task --priority=3"
            )
    if not gaps and not improved:
        lines.append("\nNo gaps — everything they ship is covered or already decided.")
    return "\n".join(lines)


def cmd_ours(args: argparse.Namespace) -> int:
    ours = build_ours()
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(ours.to_dict(), indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out}", file=sys.stderr)
    print(scan.render_catalog_summary(ours))
    return 0


def cmd_gap(args: argparse.Namespace) -> int:
    ref = resolve_reference(args.reference)
    ours = build_ours()
    gaps, improved = compute_gap(ref, ours, args.kind)
    print(render_gap(ref, ours, gaps, improved, args.beads))
    return 0


def cmd_ledger(args: argparse.Namespace) -> int:
    entries = load_ledger()
    if args.ledger_command == "list":
        if not entries:
            print("ledger is empty")
            return 0
        for row in entries:
            print(f"{row['status']:<9} {row['repo']}/{row['logical_id']}"
                  f"  -> {row.get('our_id', '-')}  ({row.get('reason', '')})")
        return 0
    # add
    source_hash = None
    if args.status == "adopted":
        catalog_path = CATALOGS_DIR / f"{args.repo}.json"
        if catalog_path.exists():
            ref = scan.Catalog.from_dict(load_json(catalog_path))
            match = ref.by_logical_id().get(args.id)
            if match:
                source_hash = match.content_hash
    entries = [e for e in entries if not (e["repo"] == args.repo and e["logical_id"] == args.id)]
    entry: dict[str, object] = {
        "repo": args.repo,
        "logical_id": args.id,
        "status": args.status,
        "reason": args.reason,
        "date": date.today().isoformat(),
    }
    if args.our_id:
        entry["our_id"] = args.our_id
    if args.source_sha:
        entry["source_sha"] = args.source_sha
    if source_hash:
        entry["source_content_hash"] = source_hash
    entries.append(entry)
    entries.sort(key=lambda e: (str(e["repo"]), str(e["logical_id"])))
    write_ledger(entries)
    print(f"recorded: {args.status} {args.repo}/{args.id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reference-harness gap report + adoption ledger.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_ours = sub.add_parser("ours", help="catalog our own harness (.claude + plugins)")
    p_ours.add_argument("--out", help="write merged catalog JSON here")
    p_ours.set_defaults(func=cmd_ours)

    p_gap = sub.add_parser("gap", help="capabilities a reference has that we don't")
    p_gap.add_argument("reference", help="reference_harnesses/<name> path, catalogs/<name>.json, or <name>")
    p_gap.add_argument("--kind", help="restrict to one kind (skill/command/agent/rule/hook/mcp/plugin)")
    p_gap.add_argument("--beads", action="store_true", help="also print bd create lines for the gaps")
    p_gap.set_defaults(func=cmd_gap)

    p_led = sub.add_parser("ledger", help="record/list adoption decisions")
    led_sub = p_led.add_subparsers(dest="ledger_command", required=True)
    led_sub.add_parser("list", help="list ledger entries")
    p_add = led_sub.add_parser("add", help="record a decision")
    p_add.add_argument("--repo", required=True)
    p_add.add_argument("--id", required=True, help="reference logical_id, e.g. skill:tdd-workflow")
    p_add.add_argument("--status", required=True, choices=["adopted", "rejected", "deferred"])
    p_add.add_argument("--reason", required=True)
    p_add.add_argument("--our-id", help="our logical_id it maps to (for adopted)")
    p_add.add_argument("--source-sha", help="reference commit sha at decision time")
    p_led.set_defaults(func=cmd_ledger)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
