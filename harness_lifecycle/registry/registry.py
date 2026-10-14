#!/usr/bin/env python3
"""Skill + capability registry: the curation tool described in README.md.

Replaces gap.py, ledger.json, aliases.json, export_csv.py and casebook.py with a
single append-only ledger (one JSONL file per round), hand-authored skill
records, and generated reference pages and INDEX. It imports scan.py (unchanged)
for catalogs.

Commands (see README.md §6):
  gap <harness> [--kind K] [--beads]   capabilities never ruled on, or changed
                                       upstream since ruled, or present-unruled
  ours                                 catalog our own capabilities
  round open <slug> / round seal <id>  start / seal a round file
  record ...                           append one validated event to the open round
  build                                regenerate INDEX.md, references/*.md, records
  check                                validate the ledger, records and generated files
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import sys
from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HL_DIR))
import scan  # type: ignore

REPO_ROOT = HL_DIR.parent

# --- Lifecycle coordinates (ADLC GUIDE.md §1) ---------------------------------

SUBSTAGES: dict[str, frozenset[str]] = {
    "Discovery": frozenset({"Research", "Charting"}),
    "Intake": frozenset({"Triage", "Clarification"}),
    "Design": frozenset(
        {"Grounding", "Specification", "Architecture", "Decomposition"}
    ),
    "Building": frozenset({"Implementation", "Diagnosis"}),
    "Verification": frozenset({"Testing", "Review", "Validation"}),
    "Delivery": frozenset({"Integration", "Release", "Closure"}),
    "Operations": frozenset({"Monitoring", "Response", "Maintenance"}),
    "Improvement": frozenset({"Retrospective", "Codification", "Evaluation"}),
    "X": frozenset({"Orchestration", "Continuity", "Governance", "Communication"}),
    "U": frozenset({"Tooling", "Tutoring"}),
}
STAGE_ORDER = list(SUBSTAGES)
DOMAIN_ORDER = ["core", "engineering", "design", "marketing", "sales", "media"]

# Stubs with no target (README §2 rule 5); the in-progress drafts folder.
STUB_SKILLS = frozenset({"cost-estimate", "verification-before-completion"})
IN_PROGRESS_DIR = "in-progress"

REFERENCE_KINDS = frozenset(
    {"adopt", "adopt-merged", "reject", "defer", "out-of-scope"}
)
OURS_KINDS = frozenset({"add", "update", "merge", "split", "rename", "retire"})
EVENT_KINDS = REFERENCE_KINDS | OURS_KINDS


# --- Models -------------------------------------------------------------------


class Excluded(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rule: str
    why: str
    count: int = 0


class RoundHeader(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["round"]
    round_id: str
    date: str
    scope: str
    pins: dict[str, str] = Field(default_factory=dict)
    method: str = ""
    evidence: list[str] = Field(default_factory=list)
    excluded: list[Excluded] = Field(default_factory=list)
    carried_debts: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> RoundHeader:
        _require_iso(self.date, f"round {self.round_id}")
        return self


class Source(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    repo: str
    logical_id: str
    path: str | None = None
    sha: str | None = None
    content_hash: str | None = None


class Adaptation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    merged_from: list[str] = Field(default_factory=list)
    modifications: list[str] = Field(default_factory=list)
    deliberately_dropped: list[str] = Field(default_factory=list)


class Event(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    type: Literal["event"]
    id: str
    date: str
    kind: Literal[
        "adopt",
        "adopt-merged",
        "reject",
        "defer",
        "out-of-scope",
        "add",
        "update",
        "merge",
        "split",
        "rename",
        "retire",
    ]
    subject: str
    why: str
    evidence: list[str] = Field(default_factory=list)
    skill: str | None = None
    source: Source | None = None
    adaptation: Adaptation | None = None
    family: str | None = None
    relation: str | None = None
    commit: str | None = None
    bead: str | None = None
    supersedes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> Event:
        _require_iso(self.date, f"event {self.id}")
        if self.kind in OURS_KINDS:
            if not self.skill:
                raise ValueError(f"{self.id}: {self.kind} needs a `skill` target")
            if self.kind in {"merge", "rename"}:
                # subject names the old skill; skill names the survivor/new name
                if not self.subject.startswith("ours:"):
                    raise ValueError(
                        f"{self.id}: {self.kind} subject must be ours:<old>"
                    )
                if self.subject == f"ours:{self.skill}":
                    raise ValueError(
                        f"{self.id}: {self.kind} old name and survivor {self.skill!r} are the same"
                    )
            elif self.subject != f"ours:{self.skill}":
                raise ValueError(
                    f"{self.id}: subject must be ours:{self.skill}, got {self.subject!r}"
                )
        else:  # a reference ruling
            if self.source is None:
                raise ValueError(
                    f"{self.id}: {self.kind} on a reference needs `source`"
                )
            want = f"{self.source.repo}:{self.source.logical_id}"
            if self.subject != want:
                raise ValueError(
                    f"{self.id}: subject {self.subject!r} disagrees with source {want!r}"
                )
            if self.kind == "adopt-merged" and self.adaptation is None:
                raise ValueError(f"{self.id}: adopt-merged needs `adaptation`")
        return self


def _require_iso(value: str, where: str) -> None:
    try:
        date_cls.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{where}: date {value!r} is not ISO 8601 ({exc})") from exc


def _today_iso() -> str:
    return datetime.now(tz=UTC).date().isoformat()


_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")


class Frontmatter(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    skill: str
    domain: str
    stage: str
    substage: str
    secondary: list[str] = Field(default_factory=list)
    family: str | None = None
    aliases: list[str] = Field(default_factory=list)
    status: Literal["active", "retired"] = "active"


# --- Configuration ------------------------------------------------------------


class RegistryConfig(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    repo_root: Path
    registry_dir: Path
    ledger_dir: Path
    manifest_path: Path
    skill_records_dir: Path
    references_dir: Path
    index_path: Path
    catalogs_dir: Path
    skills_dir: Path
    our_harness_root: Path
    codex_root: Path
    plugins_glob: str = "mvp-harness/plugins/*"

    @classmethod
    def default(cls) -> RegistryConfig:
        registry_dir = HL_DIR / "registry"
        return cls(
            repo_root=REPO_ROOT,
            registry_dir=registry_dir,
            ledger_dir=registry_dir / "ledger",
            manifest_path=registry_dir / "ledger" / "MANIFEST.json",
            skill_records_dir=registry_dir / "skill-records",
            references_dir=registry_dir / "references",
            index_path=registry_dir / "INDEX.md",
            catalogs_dir=HL_DIR / "catalogs",
            skills_dir=REPO_ROOT / ".claude" / "skills",
            our_harness_root=REPO_ROOT / ".claude",
            codex_root=REPO_ROOT / ".codex",
        )


# --- Ledger IO ----------------------------------------------------------------


def _round_files(cfg: RegistryConfig) -> list[Path]:
    if not cfg.ledger_dir.is_dir():
        return []
    return sorted(p for p in cfg.ledger_dir.glob("*.jsonl"))


def load_ledger(
    cfg: RegistryConfig,
) -> tuple[list[RoundHeader], list[Event], list[str]]:
    """Read every round file into validated headers and events, in order."""
    headers: list[RoundHeader] = []
    events: list[Event] = []
    errors: list[str] = []
    for path in _round_files(cfg):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"{path.name}:{lineno}: unparseable JSON ({exc})")
                continue
            kind = record.get("type")
            try:
                if kind == "round":
                    headers.append(RoundHeader.model_validate(record))
                elif kind == "event":
                    events.append(Event.model_validate(record))
                else:
                    errors.append(f"{path.name}:{lineno}: unknown record type {kind!r}")
            except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
                errors.append(f"{path.name}:{lineno}: schema error ({exc})")
    return headers, events, errors


def superseded_ids(events: list[Event]) -> set[str]:
    return {target for event in events for target in event.supersedes}


def effective_by_subject(events: list[Event]) -> dict[str, Event]:
    """The latest non-superseded event per subject, in ledger order."""
    dead = superseded_ids(events)
    current: dict[str, Event] = {}
    for event in events:
        if event.id in dead:
            continue
        current[event.subject] = event
    return current


def open_rounds(cfg: RegistryConfig) -> list[Path]:
    """Every unsealed round file (not yet in the manifest)."""
    recorded = _manifest_rounds(cfg)
    return [p for p in _round_files(cfg) if p.name not in recorded]


def open_round(cfg: RegistryConfig) -> Path | None:
    """The single unsealed round file; fails if more than one is open."""
    unsealed = open_rounds(cfg)
    if len(unsealed) > 1:
        names = ", ".join(p.name for p in unsealed)
        raise SystemExit(
            f"more than one open round ({names}) — seal one before recording"
        )
    return unsealed[0] if unsealed else None


# --- Sealing (ported from casebook.py) ----------------------------------------


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest_rounds(cfg: RegistryConfig) -> dict[str, str]:
    if cfg.manifest_path.is_file():
        data = json.loads(cfg.manifest_path.read_text(encoding="utf-8"))
        return dict(data.get("rounds", {}))
    return {}


def seal(cfg: RegistryConfig, round_id: str) -> None:
    """Record the sha256 of a round file. A sealed round is never re-digested; a
    sealed round that has since changed is refused rather than overwritten."""
    path = cfg.ledger_dir / f"{round_id}.jsonl"
    if not path.is_file():
        raise SystemExit(f"no round file to seal: {path}")
    recorded = _manifest_rounds(cfg)
    current = _sha256(path)
    if path.name in recorded:
        if recorded[path.name] != current:
            raise SystemExit(
                f"{path.name}: already sealed and has CHANGED — refusing to re-seal"
            )
        return  # already sealed with the same digest; nothing to do
    recorded[path.name] = current
    cfg.manifest_path.write_text(
        json.dumps(
            {
                "_comment": "sha256 of every sealed round file. registry.py check fails "
                "if a sealed file is modified or deleted. Never edit by hand.",
                "rounds": dict(sorted(recorded.items())),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def check_immutable(cfg: RegistryConfig) -> list[str]:
    recorded = _manifest_rounds(cfg)
    present = {p.name: _sha256(p) for p in _round_files(cfg)}
    errors: list[str] = []
    for name, digest in recorded.items():
        if name not in present:
            errors.append(
                f"{name}: sealed round file has been DELETED — the ledger is append-only"
            )
        elif present[name] != digest:
            errors.append(
                f"{name}: sealed round file has been MODIFIED — the ledger is append-only"
            )
    return errors


# --- "ours" catalog (ported from gap.py) --------------------------------------


def _merge_capability(existing: Any, other: Any) -> Any:
    return scan.Capability(
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
    return scan.Catalog(
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
    return scan.Catalog(
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
            cat = scan.scan_repo(
                root, root.name, source=f"ours:{root.name}", source_commit=None
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


def _one_line(text: str, width: int = 100) -> str:
    text = " ".join(text.split())
    return text if len(text) <= width else text[: width - 1] + "…"


# --- Reference resolution (submodule path, catalog file, or catalog name) -----


def resolve_reference(cfg: RegistryConfig, arg: str) -> Any:
    path = Path(arg)
    if path.suffix == ".json" and path.exists():
        return scan.Catalog.from_dict(json.loads(path.read_text(encoding="utf-8")))
    if path.is_dir():
        return _scan_dir(path.resolve())
    submodule = cfg.repo_root / "reference_harnesses" / arg
    if submodule.is_dir():
        return _scan_dir(submodule.resolve())
    catalog_path = cfg.catalogs_dir / f"{arg}.json"
    if catalog_path.exists():
        return scan.Catalog.from_dict(
            json.loads(catalog_path.read_text(encoding="utf-8"))
        )
    raise SystemExit(
        f"reference not found: {arg} (tried path, *.json, reference_harnesses/{arg}, catalogs/{arg}.json)"
    )


def _scan_dir(root: Path) -> Any:
    commit = None
    if (root / ".git").exists():
        try:
            commit = scan.pinned_commit(root)
        except Exception:  # noqa: BLE001 - best-effort commit stamp, no network
            commit = None
    return scan.scan_repo(root, root.name, source="working-tree", source_commit=commit)


# --- gap ----------------------------------------------------------------------


def cmd_gap(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    ref = resolve_reference(cfg, args.reference)
    ours = build_ours(cfg)
    _, events, errors = load_ledger(cfg)
    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        return 1
    current = effective_by_subject(events)
    our_ids = ours.by_logical_id()
    normalized = _normalized_index(ours)

    not_reviewed: list[Any] = []
    present_unruled: list[Any] = []
    changed: list[tuple[Any, Event]] = []
    hash_unknown: list[tuple[Any, Event]] = []
    for cap in ref.capabilities:
        if args.kind and cap.kind.value != args.kind:
            continue
        status, event, changed_flag = classify_capability(
            cap, ref.repo, current, our_ids, normalized
        )
        if status == "not reviewed":
            not_reviewed.append(cap)
        elif status == "present, unruled":
            present_unruled.append(cap)
        elif changed_flag == "hash unknown":
            assert event is not None
            hash_unknown.append((cap, event))
        elif changed_flag == "yes":
            assert event is not None
            changed.append((cap, event))

    lines = [f"## gap: {ref.repo}  ({ref.source})"]
    if not_reviewed:
        lines.append(f"\n### not reviewed ({len(not_reviewed)})")
        for cap in sorted(not_reviewed, key=lambda c: c.logical_id):
            desc = f" — {_one_line(cap.description)}" if cap.description else ""
            lines.append(f"  + {cap.logical_id}{desc}")
    if present_unruled:
        lines.append(f"\n### present, unruled ({len(present_unruled)})")
        for cap in sorted(present_unruled, key=lambda c: c.logical_id):
            lines.append(
                f"  = {cap.logical_id}  (we have the same capability but never ruled)"
            )
    if changed:
        lines.append(f"\n### changed since ruled ({len(changed)})")
        for cap, event in sorted(changed, key=lambda t: t[0].logical_id):
            lines.append(
                f"  ~ {cap.logical_id}  (ruled {event.kind} in {_round_of(event)})"
            )
    if hash_unknown:
        lines.append(f"\n### hash unknown — re-rule ({len(hash_unknown)})")
        for cap, event in sorted(hash_unknown, key=lambda t: t[0].logical_id):
            lines.append(
                f"  ? {cap.logical_id}  (ruled {event.kind}, no recorded hash)"
            )
    if not (not_reviewed or present_unruled or changed or hash_unknown):
        lines.append("\nNo gaps — everything they ship is ruled and current.")
    if args.beads:
        lines.append("\n### bd create lines (review before running)")
        for cap in sorted(not_reviewed, key=lambda c: c.logical_id):
            title = f"Evaluate {cap.kind.value} {cap.name} from {ref.repo}"
            desc = f"Gap candidate {cap.logical_id} ({cap.canonical_path}). Rule via harness-evaluate."
            lines.append(
                f"bd create --title={shlex.quote(title)} "
                f"--description={shlex.quote(desc)} --type=task --priority=3"
            )
    print("\n".join(lines))
    return 0


def _round_of(event: Event) -> str:
    return event.id.rsplit(":", 1)[0]


# --- ours ---------------------------------------------------------------------


def cmd_ours(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    ours = build_ours(cfg)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(ours.to_dict(), indent=2) + "\n", encoding="utf-8"
        )
        print(f"wrote {args.out}", file=sys.stderr)
    print(scan.render_catalog_summary(ours))
    return 0


# --- round / record -----------------------------------------------------------


def cmd_round(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    if args.round_command == "open":
        if open_rounds(cfg):
            names = ", ".join(p.name for p in open_rounds(cfg))
            raise SystemExit(f"a round is already open ({names}) — seal it first")
        date = args.date or _today_iso()
        # round_id is <yyyy-mm-dd>-<slug>; a slug that already carries a date
        # prefix is used as-is so the date is never doubled (cr-alnr).
        round_id = (
            args.slug if _DATE_PREFIX_RE.match(args.slug) else f"{date}-{args.slug}"
        )
        path = cfg.ledger_dir / f"{round_id}.jsonl"
        if path.exists():
            raise SystemExit(f"round file already exists: {path}")
        data = _json_arg(args)
        data["type"] = "round"
        data["round_id"] = round_id
        data.setdefault("date", date)
        if args.scope is not None:
            data["scope"] = args.scope
        data.setdefault("scope", "")
        header = RoundHeader.model_validate(data)
        cfg.ledger_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _dump(header.model_dump(exclude_defaults=False)) + "\n", encoding="utf-8"
        )
        print(f"opened {path}")
        return 0
    # seal
    seal(cfg, args.round_id)
    print(f"sealed {args.round_id}")
    return 0


def cmd_record(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    path = open_round(cfg)
    if path is None:
        raise SystemExit("no open round — run `round open <slug>` first")
    round_id = path.stem
    data = _json_arg(args)
    for field in ("id", "date", "kind", "subject", "why", "skill"):
        value = getattr(args, field, None)
        if value is not None:
            data[field] = value
    if getattr(args, "evidence", None):
        data["evidence"] = list(args.evidence)
    data["type"] = "event"
    data.setdefault("date", _today_iso())
    data.setdefault("id", _next_event_id(path, round_id))
    if not str(data["id"]).startswith(f"{round_id}:"):
        raise SystemExit(
            f"id {data['id']!r} does not belong to the open round {round_id!r}"
        )
    subject = str(data.get("subject", ""))
    if "source" not in data and ":" in subject and not subject.startswith("ours:"):
        repo, _, logical = subject.partition(":")
        source = _autofill_source(cfg, repo, logical)
        if source is not None:
            data["source"] = source
    event = Event.model_validate(data)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_dump(_event_dict(event)) + "\n")
    print(f"recorded {event.id} in {path.name}")
    return 0


def _json_arg(args: argparse.Namespace) -> dict[str, Any]:
    """Structured input for `record`/`round open`: --json, --json-file or stdin."""
    raw: str | None = getattr(args, "json", None)
    if raw is None and getattr(args, "json_file", None):
        raw = Path(args.json_file).read_text(encoding="utf-8")
    if raw is None and getattr(args, "stdin", False):
        raw = sys.stdin.read()
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise SystemExit("structured input must be a JSON object")
    return dict(parsed)


def _next_event_id(path: Path, round_id: str) -> str:
    """The next `<round_id>:<n>` for the open round, from the ids already present."""
    highest = 0
    prefix = f"{round_id}:"
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        rid = str(rec.get("id", ""))
        if rid.startswith(prefix):
            suffix = rid[len(prefix) :]
            if suffix.isdigit():
                highest = max(highest, int(suffix))
    return f"{round_id}:{highest + 1:03d}"


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
    return {
        "repo": repo,
        "logical_id": logical_id,
        "path": cap.canonical_path,
        "sha": ref.source_commit,
        "content_hash": cap.content_hash,
    }


def _event_dict(event: Event) -> dict[str, Any]:
    return event.model_dump(exclude_none=True)


def _dump(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


# --- Skill records ------------------------------------------------------------

LINEAGE_OPEN = "<!-- registry:generated lineage -->"
LINEAGE_CLOSE = "<!-- /registry:generated lineage -->"
HISTORY_OPEN = "<!-- registry:generated history -->"
HISTORY_CLOSE = "<!-- /registry:generated history -->"
REVIEWS_OPEN = "<!-- registry:generated reviews -->"
REVIEWS_CLOSE = "<!-- /registry:generated reviews -->"

# Citation forms recognised in an event's `evidence` entries and `why` text.
# A registry review file (with or without a `harness_lifecycle/registry/`
# prefix) and an old-prose comparison folder, now under archive/.
_REVIEW_RE = re.compile(r"reviews/(\d{4}-\d{2}-\d{2}-[a-z]+-[A-Za-z0-9._-]+?\.md)")
_COMPARISON_RE = re.compile(r"skill-comparisons/([A-Za-z0-9._-]+)")


def parse_record(text: str) -> tuple[Frontmatter, str]:
    """Split a record into validated frontmatter and the body after it."""
    if not text.startswith("---\n"):
        raise ValueError("record has no frontmatter")
    _, _, rest = text.partition("---\n")
    block, sep, body = rest.partition("\n---\n")
    if not sep:
        raise ValueError("record frontmatter is not closed")
    fm = _parse_frontmatter_block(block)
    return Frontmatter.model_validate(fm), body


def _parse_frontmatter_block(block: str) -> dict[str, Any]:
    fm: dict[str, Any] = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        value = raw.strip()
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            fm[key] = [item.strip() for item in inner.split(",") if item.strip()]
        elif value == "":
            fm[key] = None
        else:
            fm[key] = value.strip("\"'")
    return fm


def _lineage_block(skill: str, events: list[Event]) -> str:
    rows = [
        e
        for e in events
        if e.skill == skill
        and e.kind in {"adopt", "adopt-merged"}
        and e.source is not None
    ]
    if not rows:
        return "No adopted lineage recorded."
    lines: list[str] = []
    for event in rows:
        src = event.source
        assert src is not None
        sha = f" @ {src.sha}" if src.sha else ""
        path = f" `{src.path}`" if src.path else ""
        lines.append(f"- **{src.repo}:{src.logical_id}**{path}{sha}")
        adapt = event.adaptation
        if adapt and adapt.merged_from:
            for merged in adapt.merged_from:
                lines.append(f"  - merged from: {merged}")
        if adapt and adapt.modifications:
            for mod in adapt.modifications:
                lines.append(f"  - modified: {mod}")
        if adapt and adapt.deliberately_dropped:
            for drop in adapt.deliberately_dropped:
                lines.append(f"  - dropped: {drop}")
    return "\n".join(lines)


def _history_block(skill: str, events: list[Event], dead: set[str]) -> str:
    rows = [e for e in events if e.skill == skill or e.subject == f"ours:{skill}"]
    if not rows:
        return "No ledger history recorded."
    # Newest first, by date then id — a real chronological order, not file order.
    ordered = sorted(rows, key=lambda e: (e.date, e.id), reverse=True)
    lines: list[str] = []
    for event in ordered:
        mark = " *(superseded)*" if event.id in dead else ""
        lines.append(
            f"- `{event.date}` **{event.kind}** ({event.id}){mark}: {_one_line(event.why, 160)}"
        )
    return "\n".join(lines)


def _reviews_block(skill: str, events: list[Event]) -> str:
    """Every review cited by the same events the history block lists. Registry
    reviews first (newest file name first), then archived comparisons
    (alphabetical). Deduplicated; empty renders a single sentinel line."""
    rows = [e for e in events if e.skill == skill or e.subject == f"ours:{skill}"]
    review_files: set[str] = set()
    comparisons: set[str] = set()
    for event in rows:
        for text in [*event.evidence, event.why]:
            review_files.update(m.group(1) for m in _REVIEW_RE.finditer(text))
            comparisons.update(m.group(1) for m in _COMPARISON_RE.finditer(text))
    lines = [
        f"- [{name}](../../reviews/{name})"
        for name in sorted(review_files, reverse=True)
    ]
    lines += [
        f"- [skill-comparisons/{family}](../../../archive/skill-comparisons/{family}/)"
        for family in sorted(comparisons)
    ]
    return "\n".join(lines) if lines else "None yet."


def render_record(text: str, events: list[Event], dead: set[str]) -> str:
    fm, _ = parse_record(text)
    lineage = _lineage_block(fm.skill, events)
    history = _history_block(fm.skill, events, dead)
    reviews = _reviews_block(fm.skill, events)
    out = _replace_block(text, LINEAGE_OPEN, LINEAGE_CLOSE, lineage)
    out = _replace_block(out, HISTORY_OPEN, HISTORY_CLOSE, history)
    if REVIEWS_OPEN in out:
        out = _replace_block(out, REVIEWS_OPEN, REVIEWS_CLOSE, reviews)
    else:
        out = _insert_after(
            out, HISTORY_CLOSE, f"{REVIEWS_OPEN}\n{reviews}\n{REVIEWS_CLOSE}"
        )
    return out


def _insert_after(text: str, marker: str, block: str) -> str:
    """Insert a block one blank line after `marker` (used to add the reviews
    block to records that predate it)."""
    idx = text.find(marker)
    if idx == -1:
        raise ValueError(f"record is missing the {marker} block")
    end = idx + len(marker)
    return f"{text[:end]}\n\n{block}{text[end:]}"


def _replace_block(text: str, open_tag: str, close_tag: str, body: str) -> str:
    start = text.find(open_tag)
    end = text.find(close_tag)
    if start == -1 or end == -1:
        raise ValueError(f"record is missing the {open_tag} block")
    before = text[: start + len(open_tag)]
    after = text[end:]
    return f"{before}\n{body}\n{after}"


def record_paths(cfg: RegistryConfig) -> list[Path]:
    if not cfg.skill_records_dir.is_dir():
        return []
    return sorted(cfg.skill_records_dir.rglob("*.md"))


def load_records(cfg: RegistryConfig) -> dict[str, Frontmatter]:
    records: dict[str, Frontmatter] = {}
    for path in record_paths(cfg):
        fm, _ = parse_record(path.read_text(encoding="utf-8"))
        records[fm.skill] = fm
    return records


# --- Reference pages + INDEX --------------------------------------------------


def _catalog_files(cfg: RegistryConfig) -> list[Path]:
    if not cfg.catalogs_dir.is_dir():
        return []
    return sorted(p for p in cfg.catalogs_dir.glob("*.json") if p.stem != "ours")


def render_reference(
    catalog: Any,
    current: dict[str, Event],
    our_ids: dict[str, Any],
    normalized: dict[tuple[str, str], str],
) -> str:
    lines = [
        f"# {catalog.repo}",
        "",
        "<!-- GENERATED by registry.py build. Do not edit. -->",
        "",
        (
            f"Catalog: `{catalog.source_commit or catalog.source}`, "
            f"{len(catalog.capabilities)} capabilities."
        ),
        "",
        "| Their capability | Status | Into ours | Last ruled at | Changed upstream since? |",
        "|---|---|---|---|---|",
    ]
    for cap in catalog.capabilities:
        status, event, changed = classify_capability(
            cap, catalog.repo, current, our_ids, normalized
        )
        into = event.skill or "" if event else ""
        ruled = _round_of(event) if event else ""
        lines.append(
            f"| `{cap.logical_id}` | {status} | {into} | {ruled} | {changed} |"
        )
    return "\n".join(lines) + "\n"


def render_index(cfg: RegistryConfig, records: dict[str, Frontmatter]) -> str:
    lines = [
        "# Registry index",
        "",
        "<!-- GENERATED by registry.py build. Do not edit. -->",
        "",
        "Domain → stage → sub-stage. Each active skill under its primary home.",
        "",
    ]
    active = [fm for fm in records.values() if fm.status == "active"]
    domains = sorted({fm.domain for fm in active}, key=_domain_key)
    collisions: list[tuple[str, str, str, list[str]]] = []
    for domain in domains:
        lines.append(f"## {domain}")
        lines.append("")
        in_domain = [fm for fm in active if fm.domain == domain]
        for stage in STAGE_ORDER:
            stage_records = [fm for fm in in_domain if fm.stage == stage]
            if not stage_records:
                continue
            lines.append(f"### {stage}")
            for substage in sorted(SUBSTAGES[stage]):
                here = sorted(
                    (fm for fm in stage_records if fm.substage == substage),
                    key=lambda fm: fm.skill,
                )
                if not here:
                    continue
                names = ", ".join(fm.skill for fm in here)
                lines.append(f"- **{substage}**: {names}")
                if len(here) > 1:
                    collisions.append(
                        (domain, stage, substage, [fm.skill for fm in here])
                    )
            lines.append("")
    if collisions:
        lines.append("## Merge candidates")
        lines.append("")
        lines.append(
            "Two or more active skills share one domain · sub-stage (README §2 rule 3):"
        )
        lines.append("")
        for domain, stage, substage, clashing in collisions:
            lines.append(f"- {domain} · {stage} · {substage}: {', '.join(clashing)}")
        lines.append("")
    aliases = sorted({alias for fm in records.values() for alias in fm.aliases})
    if aliases:
        lines.append("## Aliases")
        lines.append("")
        for fm in sorted(records.values(), key=lambda fm: fm.skill):
            if fm.aliases:
                lines.append(f"- {fm.skill}: {', '.join(sorted(fm.aliases))}")
        lines.append("")
    lines.append("## Stubs")
    lines.append("")
    for stub in sorted(STUB_SKILLS):
        lines.append(f"- {stub} (no target)")
    lines.append("")
    return "\n".join(lines)


def _domain_key(domain: str) -> tuple[int, str]:
    return (
        DOMAIN_ORDER.index(domain) if domain in DOMAIN_ORDER else len(DOMAIN_ORDER),
        domain,
    )


# --- build --------------------------------------------------------------------


def build_outputs(cfg: RegistryConfig) -> dict[Path, str]:
    """Every generated file's path → its current content (no writes)."""
    _, events, errors = load_ledger(cfg)
    if errors:
        raise SystemExit("ledger has errors; run `check`:\n" + "\n".join(errors))
    current = effective_by_subject(events)
    dead = superseded_ids(events)
    outputs: dict[Path, str] = {}
    for path in record_paths(cfg):
        outputs[path] = render_record(path.read_text(encoding="utf-8"), events, dead)
    records = load_records(cfg)
    outputs[cfg.index_path] = render_index(cfg, records)
    ours = build_ours(cfg)
    our_ids = ours.by_logical_id()
    normalized = _normalized_index(ours)
    for cat_path in _catalog_files(cfg):
        catalog = scan.Catalog.from_dict(
            json.loads(cat_path.read_text(encoding="utf-8"))
        )
        outputs[cfg.references_dir / f"{cat_path.stem}.md"] = render_reference(
            catalog, current, our_ids, normalized
        )
    return outputs


def cmd_build(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    outputs = build_outputs(cfg)
    cfg.references_dir.mkdir(parents=True, exist_ok=True)
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"built: {len(outputs)} generated file(s)")
    return 0


# --- check --------------------------------------------------------------------


def cmd_check(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    errors: list[str] = []
    headers, events, load_errors = load_ledger(cfg)
    errors += load_errors

    seen: set[str] = set()
    known_rounds = {h.round_id for h in headers}
    for event in events:
        if event.id in seen:
            errors.append(f"{event.id}: duplicate event id")
        seen.add(event.id)
        if not event.why.strip():
            errors.append(f"{event.id}: why is empty")
        if _round_of(event) not in known_rounds:
            errors.append(f"{event.id}: round {_round_of(event)!r} has no header")
    errors += _check_supersession(events, seen)
    errors += _check_structure(cfg)
    open_now = open_rounds(cfg)
    if len(open_now) > 1:
        errors.append(
            "more than one open round: " + ", ".join(p.name for p in open_now)
        )
    errors += check_immutable(cfg)

    records: dict[str, Frontmatter] = {}
    for path in record_paths(cfg):
        try:
            fm, _ = parse_record(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - reported as a record error
            errors.append(f"{path.name}: {exc}")
            continue
        if fm.skill in records:
            errors.append(f"{path.name}: duplicate skill record for {fm.skill!r}")
        records[fm.skill] = fm
        expected = cfg.skill_records_dir / fm.domain / f"{fm.skill}.md"
        if path != expected:
            errors.append(
                f"{_rel(cfg, path)}: record path must be {fm.domain}/{fm.skill}.md"
            )
        if fm.stage not in SUBSTAGES:
            errors.append(f"{path.name}: unknown stage {fm.stage!r}")
        elif fm.substage not in SUBSTAGES[fm.stage]:
            errors.append(
                f"{path.name}: {fm.substage!r} is not a sub-stage of {fm.stage}"
            )

    errors += _check_skill_coverage(cfg, records)
    aliases = {alias for fm in records.values() for alias in fm.aliases}
    ours = build_ours(cfg)
    errors += _check_effective_targets(events, set(records), aliases, ours)

    if not errors:
        try:
            outputs = build_outputs(cfg)
        except SystemExit as exc:
            errors.append(str(exc))
            outputs = {}
        for path, content in outputs.items():
            on_disk = path.read_text(encoding="utf-8") if path.exists() else None
            if on_disk != content:
                errors.append(
                    f"{_rel(cfg, path)}: generated file is stale — run `build`"
                )

    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        print(f"\n{len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(
        f"ok: {len(headers)} round(s), {len(events)} event(s), "
        f"{len(records)} skill record(s)"
    )
    return 0


def _check_supersession(events: list[Event], seen: set[str]) -> list[str]:
    """Targets exist, belong to the same subject, superseded at most once, and
    chains are acyclic within a subject."""
    errors: list[str] = []
    by_id = {e.id: e for e in events}
    superseded_by: dict[str, str] = {}
    for event in events:
        for target in event.supersedes:
            if target not in seen:
                errors.append(f"{event.id}: supersedes unknown event {target!r}")
                continue
            if target == event.id:
                errors.append(f"{event.id}: supersedes itself")
            tgt = by_id[target]
            if tgt.subject != event.subject:
                errors.append(
                    f"{event.id}: supersedes {target} across subjects "
                    f"({event.subject} vs {tgt.subject})"
                )
            if target in superseded_by:
                errors.append(
                    f"{target}: superseded twice ({superseded_by[target]} and {event.id})"
                )
            superseded_by[target] = event.id
    # Acyclicity over the full supersedes graph (every edge, not just the first).
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    cyclic: set[str] = set()

    def visit(node: str, stack: list[str]) -> None:
        color[node] = GREY
        stack.append(node)
        for nxt in by_id.get(node).supersedes if node in by_id else []:  # type: ignore[union-attr]
            if nxt not in by_id:
                continue
            if color.get(nxt, WHITE) == GREY:
                cyclic.update(stack[stack.index(nxt) :] + [nxt])
            elif color.get(nxt, WHITE) == WHITE:
                visit(nxt, stack)
        stack.pop()
        color[node] = BLACK

    for node in by_id:
        if color.get(node, WHITE) == WHITE:
            visit(node, [])
    for node in sorted(cyclic):
        errors.append(f"{node}: supersession chain is cyclic")
    return errors


def _check_structure(cfg: RegistryConfig) -> list[str]:
    """Each round file: exactly one header on line 1, round_id == filename stem,
    every event id belongs to that round."""
    errors: list[str] = []
    for path in _round_files(cfg):
        stem = path.stem
        lines = path.read_text(encoding="utf-8").splitlines()
        if not lines:
            errors.append(f"{path.name}: empty round file")
            continue
        # Physical lines: the header must be line 1, with no blank lines anywhere.
        for lineno, line in enumerate(lines, 1):
            if not line.strip():
                errors.append(
                    f"{path.name}:{lineno}: blank line (one JSON record per line)"
                )
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            is_header = rec.get("type") == "round"
            if lineno == 1:
                if not is_header:
                    errors.append(
                        f"{path.name}: physical first line must be a round header"
                    )
                elif rec.get("round_id") != stem:
                    errors.append(
                        f"{path.name}: header round_id {rec.get('round_id')!r} != filename"
                    )
            elif is_header:
                errors.append(f"{path.name}:{lineno}: a second round header")
            elif not str(rec.get("id", "")).startswith(f"{stem}:"):
                errors.append(
                    f"{path.name}:{lineno}: event {rec.get('id')!r} does not belong to {stem}"
                )
    return errors


# Non-skill target kinds a `kind:name` adoption target may name.
NONSKILL_KINDS = frozenset({"agent", "command", "hook", "rule", "mcp", "plugin"})


def _target_exists(target: str | None, existing: set[str], ours: Any) -> bool:
    """True when an adoption target resolves. A plain name must be a skill
    record, alias or stub. A `kind:name` target is valid only when kind is a
    real non-skill kind, name is non-empty, and that capability exists in our
    shipped surface — matched by full logical id or by exact (kind, name). The
    exact-name form covers the documented legacy prefix normalization (e.g.
    `agent:code-reviewer` ↔ `agent:agents/code-reviewer`, the legacy short form),
    since a capability's `name` is the bare leaf. A fabricated namespace such as
    `agent:does-not-exist/agents/code-reviewer` matches neither and is rejected."""
    if not target:
        return False
    if ":" not in target:
        return target in existing
    kind, _, name = target.partition(":")
    if kind not in NONSKILL_KINDS or not name:
        return False
    for cap in ours.capabilities:
        if cap.kind.value != kind:
            continue
        if cap.logical_id == target or cap.name == name:
            return True
    return False


def _check_effective_targets(
    events: list[Event],
    records: set[str],
    aliases: set[str],
    ours: Any,
) -> list[str]:
    """Every live adoption carries a source and a target that resolves today.
    An unresolved target is an error."""
    existing = records | aliases | STUB_SKILLS
    effective = effective_by_subject(events)
    errors: list[str] = []
    for subject, event in effective.items():
        if event.kind not in {"adopt", "adopt-merged"}:
            continue
        if event.source is None:
            errors.append(f"{event.id}: live adoption of {subject} has no source")
        if _target_exists(event.skill, existing, ours):
            continue
        errors.append(
            f"{event.id}: live adoption of {subject} has an invalid "
            f"skill target {event.skill!r}"
        )
    return errors


def _rel(cfg: RegistryConfig, path: Path) -> str:
    try:
        return str(path.relative_to(cfg.registry_dir))
    except ValueError:
        return str(path)


def _check_skill_coverage(
    cfg: RegistryConfig, records: dict[str, Frontmatter]
) -> list[str]:
    if not cfg.skills_dir.is_dir():
        return []
    aliases = {alias for fm in records.values() for alias in fm.aliases}
    errors: list[str] = []
    for child in sorted(cfg.skills_dir.iterdir()):
        if not child.is_dir():
            continue
        name = child.name
        if (
            name == IN_PROGRESS_DIR
            or name in records
            or name in aliases
            or name in STUB_SKILLS
        ):
            continue
        errors.append(
            f".claude/skills/{name}: no record, and not an alias, stub or in-progress"
        )
    return errors


# --- CLI ----------------------------------------------------------------------


def _add_json_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", help="a JSON object with the full/partial record")
    parser.add_argument(
        "--json-file", dest="json_file", help="path to that JSON object"
    )
    parser.add_argument(
        "--stdin", action="store_true", help="read the JSON object from stdin"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Skill + capability registry.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gap = sub.add_parser("gap", help="capabilities never ruled on, or changed since")
    p_gap.add_argument("reference")
    p_gap.add_argument("--kind")
    p_gap.add_argument("--beads", action="store_true")
    p_gap.set_defaults(func=cmd_gap)

    p_ours = sub.add_parser("ours", help="catalog our own capabilities")
    p_ours.add_argument("--out")
    p_ours.set_defaults(func=cmd_ours)

    p_round = sub.add_parser("round", help="open or seal a round file")
    round_sub = p_round.add_subparsers(dest="round_command", required=True)
    p_open = round_sub.add_parser("open")
    p_open.add_argument("slug")
    p_open.add_argument("--date")
    p_open.add_argument("--scope")
    _add_json_args(p_open)
    p_seal = round_sub.add_parser("seal")
    p_seal.add_argument("round_id")
    p_round.set_defaults(func=cmd_round)

    p_rec = sub.add_parser("record", help="append one event to the open round")
    p_rec.add_argument("--id", help="default: the next <round_id>:<n>")
    p_rec.add_argument("--date", help="default: today")
    p_rec.add_argument("--kind", choices=sorted(EVENT_KINDS))
    p_rec.add_argument("--subject")
    p_rec.add_argument("--why")
    p_rec.add_argument("--evidence", action="append")
    p_rec.add_argument("--skill")
    _add_json_args(p_rec)
    p_rec.set_defaults(func=cmd_record)

    sub.add_parser(
        "build", help="regenerate INDEX.md, references/*.md, records"
    ).set_defaults(func=cmd_build)
    sub.add_parser(
        "check", help="validate the ledger, records and generated files"
    ).set_defaults(func=cmd_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    cfg = RegistryConfig.default()
    return int(args.func(cfg, args))


if __name__ == "__main__":
    raise SystemExit(main())
