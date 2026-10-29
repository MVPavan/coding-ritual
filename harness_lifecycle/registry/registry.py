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
import subprocess
import sys
from datetime import UTC, datetime
from datetime import date as date_cls
from pathlib import Path
from typing import Any, Literal

import yaml
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
    "X": frozenset({"Coordination", "Continuity", "Governance", "Communication"}),
    "U": frozenset({"Tooling", "Tutoring"}),
}
STAGE_ORDER = list(SUBSTAGES)
ALL_SUBSTAGES = frozenset().union(*SUBSTAGES.values())
# Trait placements use only these domains (GUIDE.md §1; traits-design §1).
TRAIT_DOMAINS = frozenset({"core", "engineering"})
DOMAIN_ORDER = ["core", "engineering", "design", "marketing", "sales", "media"]

# Stubs with no target (README §2 rule 5); the in-progress drafts folder.
STUB_SKILLS = frozenset({"cost-estimate", "verification-before-completion"})
IN_PROGRESS_DIR = "in-progress"

REFERENCE_KINDS = frozenset(
    {"adopt", "adopt-merged", "reject", "defer", "out-of-scope"}
)
OURS_KINDS = frozenset({"add", "update", "merge", "split", "rename", "retire"})
EVENT_KINDS = REFERENCE_KINDS | OURS_KINDS
# Trait subjects (<repo>:<logical_id>#<trait_id>) may only carry these kinds (§5);
# `adopt-merged` is a capability-checkpoint kind, never a trait kind (review #16).
TRAIT_KINDS = frozenset({"adopt", "reject", "defer", "out-of-scope"})
_SLUG_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# Trait IDs in the two trait files are kebab slugs (traits-design Terms).
_TRAIT_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


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
    # True when this round rules upstream skills trait by trait (§5).
    trait_level: bool = False

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
    # Whole-folder hash for a skill (scan.py §4); None on legacy rulings.
    tree_hash: str | None = None


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
    # --- trait-level fields (§5); all optional so sealed events still validate ---
    into: str | None = None  # a different trait our skill provides (modified adopt)
    modification: str | None = None  # one-line note on how the trait was changed
    pending: str | None = None  # bead id for the edit that will deliver an adopt
    carried_from: list[str] = Field(default_factory=list)  # earlier trait subjects
    withdraws: list[str] = Field(default_factory=list)  # ours-side `update` only

    @model_validator(mode="after")
    def _check(self) -> Event:
        _require_iso(self.date, f"event {self.id}")
        self._check_contextual_fields()
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
            # An idea event's subject is <repo>:<logical_id>#<slug> (§2); a
            # capability checkpoint's is the bare <repo>:<logical_id>.
            if self.subject != want and not self.subject.startswith(f"{want}#"):
                raise ValueError(
                    f"{self.id}: subject {self.subject!r} disagrees with source {want!r}"
                )
            if "#" in self.subject:
                self._check_trait_subject()
        # `adopt-merged needs adaptation` is contextual (only outside trait-level
        # rounds, README §5); it is enforced in `check`, not here (review #4).
        return self

    def _check_contextual_fields(self) -> None:
        """Trait-level fields only where §5 defines them (review r1 #11)."""
        trait = "#" in self.subject
        if self.pending is not None:
            if not (trait and self.kind == "adopt"):
                raise ValueError(f"{self.id}: `pending` is only for a trait adopt")
            if not self.pending.strip():
                raise ValueError(f"{self.id}: `pending` is empty")
        if (self.into is not None or self.modification is not None) and not (
            trait and self.kind == "adopt"
        ):
            raise ValueError(
                f"{self.id}: `into`/`modification` are only for a trait adopt"
            )
        if self.carried_from and not trait:
            raise ValueError(f"{self.id}: `carried_from` is only for trait events")
        if self.withdraws and self.kind != "update":
            raise ValueError(f"{self.id}: `withdraws` is only for an ours-side update")

    def _check_trait_subject(self) -> None:
        """Trait identity rules (§5): skill-only logical ids, allowed trait
        kinds, a valid slug, and `modification` on a modified adoption."""
        assert self.source is not None
        if self.kind not in TRAIT_KINDS:
            raise ValueError(
                f"{self.id}: trait subject {self.subject!r} has kind {self.kind!r}; "
                f"trait kinds are {sorted(TRAIT_KINDS)}"
            )
        if not self.source.logical_id.startswith("skill:"):
            raise ValueError(
                f"{self.id}: trait-level rulings apply to skills only, not "
                f"{self.source.logical_id!r}"
            )
        slug = self.subject.split("#", 1)[1]
        if not _SLUG_RE.fullmatch(slug):
            raise ValueError(f"{self.id}: {slug!r} is not a valid trait slug")
        # A modified adoption points `into` a different trait and must say how (§5).
        if (
            self.kind == "adopt"
            and self.into is not None
            and self.into != slug
            and not self.modification
        ):
            raise ValueError(
                f"{self.id}: modified adoption into {self.into!r} needs `modification`"
            )


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


# --- Trait files (traits-design §1–§3) ----------------------------------------


def _check_trait_ids(ids: Any, where: str) -> None:
    """Every trait ID is a kebab slug (traits-design Terms, review r1 #5)."""
    for tid in ids:
        if not isinstance(tid, str) or not _TRAIT_ID_RE.fullmatch(tid):
            raise ValueError(f"{where}: {tid!r} is not a kebab-case trait ID")


def _check_secondary(secondary: list[str]) -> None:
    for sub in secondary:
        if sub not in ALL_SUBSTAGES:
            raise ValueError(f"secondary: {sub!r} is not a sub-stage")


class Placement(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    domain: str
    stage: str
    substage: str

    @model_validator(mode="after")
    def _check(self) -> Placement:
        if self.domain not in TRAIT_DOMAINS:
            raise ValueError(f"placement: unknown domain {self.domain!r}")
        if self.stage not in SUBSTAGES:
            raise ValueError(f"placement: unknown stage {self.stage!r}")
        if self.substage not in SUBSTAGES[self.stage]:
            raise ValueError(
                f"placement: {self.substage!r} is not a sub-stage of {self.stage}"
            )
        return self


class Retirement(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    date: str
    replaced_by: list[str]

    @model_validator(mode="after")
    def _check(self) -> Retirement:
        _require_iso(self.date, "retired")
        _check_trait_ids(self.replaced_by, "replaced_by")
        return self


class TraitDefinition(BaseModel):
    """One entry of `trait-definitions.yaml` (traits-design §1)."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    definition: str
    placement: Placement
    secondary: list[str] = Field(default_factory=list)
    distinct_from: list[str] = Field(default_factory=list)
    note: str | None = None
    retired: Retirement | None = None

    @model_validator(mode="after")
    def _check(self) -> TraitDefinition:
        if self.distinct_from and not self.note:
            raise ValueError("distinct_from requires a note")
        _check_trait_ids(self.distinct_from, "distinct_from")
        _check_secondary(self.secondary)
        return self


class OursTraitEntry(BaseModel):
    """An `ours:<skill>` entry of `traits.yaml` (traits-design §2)."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    tree_hash: str
    traits: list[str]
    notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> OursTraitEntry:
        _check_trait_ids(self.traits, "traits")
        _check_trait_ids(self.notes, "notes")
        return self


class UpstreamTraitEntry(BaseModel):
    """A `<repo>:<logical_id>` entry of `traits.yaml` (traits-design §2)."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)

    reviewed_sha: str
    tree_hash: str
    placement: Placement
    traits: list[str]
    removed: dict[str, str] = Field(default_factory=dict)
    added: dict[str, str] = Field(default_factory=dict)
    notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> UpstreamTraitEntry:
        _check_trait_ids(self.traits, "traits")
        for name in ("removed", "added", "notes"):
            _check_trait_ids(getattr(self, name), name)
        return self


class _StrictYamlLoader(yaml.SafeLoader):
    """`yaml.safe_load` that errors on a duplicate mapping key (§3): PyYAML keeps
    the last silently, which would drop a trait definition or list."""


def _no_duplicate_keys(loader: _StrictYamlLoader, node: Any) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=True)
    return mapping


_StrictYamlLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicate_keys
)


def load_trait_definitions(
    cfg: RegistryConfig,
) -> tuple[dict[str, TraitDefinition], list[str]]:
    """Parse `trait-definitions.yaml`; absent means empty (§1)."""
    path = cfg.trait_definitions_path
    if not path.is_file():
        return {}, []
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictYamlLoader)
    except yaml.YAMLError as exc:
        return {}, [f"trait-definitions.yaml: {exc}"]
    if raw is None:
        return {}, []
    if not isinstance(raw, dict):
        return {}, ["trait-definitions.yaml: top level must be a mapping"]
    out: dict[str, TraitDefinition] = {}
    errors: list[str] = []
    for tid, body in raw.items():
        if not isinstance(tid, str) or not _TRAIT_ID_RE.fullmatch(tid):
            errors.append(
                f"trait-definitions.yaml: {tid!r} is not a kebab-case trait ID"
            )
            continue
        try:
            out[tid] = TraitDefinition.model_validate(body)
        except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
            errors.append(f"trait-definitions.yaml: {tid}: {exc}")
    return out, errors


def load_traits(
    cfg: RegistryConfig,
) -> tuple[dict[str, OursTraitEntry | UpstreamTraitEntry], list[str]]:
    """Parse `traits.yaml`; absent means empty (§2). `ours:` keys are ours
    entries, every other key an upstream entry."""
    path = cfg.traits_path
    if not path.is_file():
        return {}, []
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_StrictYamlLoader)
    except yaml.YAMLError as exc:
        return {}, [f"traits.yaml: {exc}"]
    if raw is None:
        return {}, []
    if not isinstance(raw, dict):
        return {}, ["traits.yaml: top level must be a mapping"]
    out: dict[str, OursTraitEntry | UpstreamTraitEntry] = {}
    errors: list[str] = []
    for key, body in raw.items():
        if not isinstance(key, str):
            errors.append(f"traits.yaml: key {key!r} is not a string")
            continue
        model = OursTraitEntry if key.startswith("ours:") else UpstreamTraitEntry
        try:
            out[key] = model.model_validate(body)
        except Exception as exc:  # noqa: BLE001 - surfaced as a validation error
            errors.append(f"traits.yaml: {key}: {exc}")
    return out, errors


def _ours_traits(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
) -> dict[str, OursTraitEntry]:
    return {
        k[len("ours:") :]: v for k, v in traits.items() if isinstance(v, OursTraitEntry)
    }


def _upstream_traits(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
) -> dict[str, UpstreamTraitEntry]:
    return {k: v for k, v in traits.items() if isinstance(v, UpstreamTraitEntry)}


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
    trait_definitions_path: Path
    traits_path: Path
    traits_md_path: Path
    catalogs_dir: Path
    skills_dir: Path
    our_harness_root: Path
    codex_root: Path
    plugins_glob: str = "mvp-harness/plugins/*"
    # Rounds sealed before traits existed (§5 "Awaiting trait ruling"). Closed:
    # a round sealed after the migration is never added.
    pre_trait_rounds: frozenset[str] = frozenset(
        {"2026-10-14-migration", "2026-10-14-owner-review"}
    )

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
            trait_definitions_path=registry_dir / "trait-definitions.yaml",
            traits_path=registry_dir / "traits.yaml",
            traits_md_path=registry_dir / "TRAITS.md",
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


def live_events(events: list[Event]) -> list[Event]:
    """Events still operative — those not superseded by a later event, in ledger
    order. Every lifecycle, merge, withdrawal and coverage consumer reads this
    single list, so a correction (supersede a bad event with a good one) takes
    effect everywhere at once instead of each check re-deciding supersession
    (review #8, N2/N3). History and provenance consumers keep raw events."""
    dead = superseded_ids(events)
    return [event for event in events if event.id not in dead]


def effective_by_subject(events: list[Event]) -> dict[str, Event]:
    """The latest event per subject, in ledger order. Callers pass `live_events`,
    so superseded events are already excluded (review #8)."""
    current: dict[str, Event] = {}
    for event in events:
        current[event.subject] = event
    return current


def round_header_by_id(headers: list[RoundHeader]) -> dict[str, RoundHeader]:
    return {h.round_id: h for h in headers}


# --- Trait-level helpers (§5) -------------------------------------------------


def _is_trait_subject(subject: str) -> bool:
    """A trait event's subject carries a trailing ``#<trait_id>``."""
    return "#" in subject


def _trait_base(subject: str) -> str:
    """The capability subject (<repo>:<logical_id>) of a trait subject."""
    return subject.split("#", 1)[0]


def _trait_slug(subject: str) -> str | None:
    return subject.split("#", 1)[1] if "#" in subject else None


def effective_traits_for(current: dict[str, Event], base: str) -> dict[str, Event]:
    """Effective trait events whose subject is ``<base>#<trait_id>``, keyed by
    trait id."""
    out: dict[str, Event] = {}
    for subject, event in current.items():
        if _is_trait_subject(subject) and _trait_base(subject) == base:
            slug = _trait_slug(subject)
            if slug is not None:
                out[slug] = event
    return out


def _same_sha(a: str | None, b: str | None) -> bool:
    """Two commit shas name the same commit when one is a prefix of the other,
    so a short sha matches its full form."""
    if not a or not b:
        return False
    a, b = a.lower(), b.lower()
    return a.startswith(b) or b.startswith(a)


def _is_grandfathered(
    event: Event,
    current: dict[str, Event],
    upstream_traits: dict[str, UpstreamTraitEntry],
    pre_trait_rounds: frozenset[str],
) -> bool:
    """A checkpoint sealed before traits existed, whose subject now has an
    upstream entry but no trait ruling: awaiting a trait ruling (§5)."""
    return (
        _round_of(event) in pre_trait_rounds
        and event.subject in upstream_traits
        and not effective_traits_for(current, event.subject)
    )


def _is_trait_level(
    event: Event,
    current: dict[str, Event],
    trait_rounds: set[str],
    upstream_traits: dict[str, UpstreamTraitEntry],
    pre_trait_rounds: frozenset[str],
) -> bool:
    """A capability checkpoint not grandfathered is trait-level when its round
    is trait-level, its subject has an upstream entry, or its subject has any
    effective trait ruling (§5)."""
    if _is_grandfathered(event, current, upstream_traits, pre_trait_rounds):
        return False
    return (
        _round_of(event) in trait_rounds
        or event.subject in upstream_traits
        or bool(effective_traits_for(current, event.subject))
    )


def build_lifecycle(events: list[Event]) -> tuple[dict[str, str], set[str]]:
    """Our skill lifecycle, read in ledger order (§3, §5).

    Returns ``(forward, retired)``: a one-step ``old -> new`` map across
    ``rename``/``merge`` and the set of retired skill names. Trait IDs are
    global, so a merge needs no slug map (§5). Callers pass `live_events`, so
    superseded lifecycle events are already excluded (review #8).
    """
    forward: dict[str, str] = {}
    retired: set[str] = set()
    for event in events:
        if event.kind in {"rename", "merge"} and event.subject.startswith("ours:"):
            old = event.subject[len("ours:") :]
            if event.skill:
                forward[old] = event.skill
        elif event.kind == "retire" and event.skill:
            retired.add(event.skill)
    return forward, retired


def resolve_skill(name: str, forward: dict[str, str]) -> str:
    """Follow rename/merge until the current survivor."""
    seen: set[str] = set()
    while name in forward and name not in seen:
        seen.add(name)
        name = forward[name]
    return name


# --- Generated block markers (§7) ---------------------------------------------

TRAITS_OPEN = "<!-- registry:generated traits -->"
TRAITS_CLOSE = "<!-- /registry:generated traits -->"
SOURCES_OPEN = "<!-- registry:generated sources -->"
SOURCES_CLOSE = "<!-- /registry:generated sources -->"
DECLINED_OPEN = "<!-- registry:generated declined -->"
DECLINED_CLOSE = "<!-- /registry:generated declined -->"


def withdrawn_destinations(
    events: list[Event], forward: dict[str, str]
) -> dict[tuple[str, str], str]:
    """(trait subject, resolved destination skill) pairs currently withdrawn,
    mapped to the withdrawal date. Keyed per destination so withdrawing a trait
    from one skill never touches the same trait adopted into another (review #7).
    Ordered by ledger position: a *delivered* (non-pending) `adopt` into that
    same destination after the withdrawing `update` makes it live again; a
    pending adopt is intent, not delivery, so it never clears a withdrawal (§5).

    `events` is the RAW list, like `retained_adoptions`: a delivered adopt keeps
    reviving the obligation even when later superseded, while a superseded
    withdrawing `update` never operates (review r1 #1)."""
    dead = superseded_ids(events)
    withdrawn: dict[tuple[str, str], str] = {}
    for event in events:
        if (
            event.kind == "update"
            and event.withdraws
            and event.skill
            and event.id not in dead
        ):
            dest = resolve_skill(event.skill, forward)
            for subject in event.withdraws:
                withdrawn[(subject, dest)] = event.date
        elif (
            event.kind == "adopt"
            and not event.pending
            and _is_trait_subject(event.subject)
            and event.skill
            and ":" not in event.skill
        ):
            withdrawn.pop((event.subject, resolve_skill(event.skill, forward)), None)
    return withdrawn


def retained_adoptions(
    events: list[Event], forward: dict[str, str]
) -> dict[tuple[str, str], Event]:
    """The last delivered `adopt` event per (trait subject, resolved destination
    skill), in ledger order — the adoption we still provide even after a later
    upstream revision is declined (§5). Keyed per destination so adopting one
    trait into A and then into B keeps A's coverage obligation until A withdraws
    it, rather than B silently replacing A (review #6, N1).

    Reads only non-pending `adopt` events: a pending adopt is intent, not
    delivery, so it never enters the fold and never replaces a delivered
    obligation (§5, round-2 #1). Computed from RAW events, including a superseded
    `adopt`: per §5 only an ours-side `update` with `withdraws` removes an
    adoption obligation; an upstream `reject`/`defer` that supersedes the adopt
    never does (review r3). `forward` and the withdrawal state come from live
    events, so the coverage check and the sources block — which both read this
    function — can never disagree."""
    out: dict[tuple[str, str], Event] = {}
    for event in events:
        if (
            event.kind == "adopt"
            and not event.pending
            and _is_trait_subject(event.subject)
            and event.skill
            and ":" not in event.skill
        ):
            dest = resolve_skill(event.skill, forward)
            out[(event.subject, dest)] = event
    return out


def _our_tree_hashes(ours: Any) -> dict[str, str]:
    """Current tree hash of each of our skills, keyed by bare skill name."""
    out: dict[str, str] = {}
    for cap in ours.capabilities:
        if cap.kind.value == "skill":
            out[cap.name] = cap.tree_hash
    return out


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


def _diff_folder(cap: Any) -> str:
    """The submodule-relative path to diff for a capability — a skill's whole
    folder, or a single-file capability's path."""
    if cap.kind.value == "skill":
        parent = str(Path(cap.canonical_path).parent)
        if parent and parent != ".":
            return f"{parent}/"
    return cap.canonical_path


GIT_TIMEOUT = 15


def _git_returncode(submodule: Path, *args: str) -> int | None:
    """Run git in `submodule`, returning its exit code, or None when the process
    cannot run at all (git missing, not a repo, timeout) — never raising so a
    broken baseline becomes "unknown" rather than crashing `gap` (review #19)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(submodule), *args],
            capture_output=True,
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.returncode


def _commit_exists(submodule: Path, sha: str) -> bool:
    return _git_returncode(submodule, "cat-file", "-e", f"{sha}^{{commit}}") == 0


def _git_diff_changed(
    submodule: Path, base: str, pin: str | None, folder: str
) -> bool | None:
    """True/False whether `folder` differs between `base` and `pin` (HEAD when
    `pin` is None); None when the diff cannot be run (e.g. commit absent)."""
    if not submodule.is_dir() or not _commit_exists(submodule, base):
        return None
    if pin and not _commit_exists(submodule, pin):
        return None
    args = ["diff", "--quiet", base]
    if pin:
        args.append(pin)
    args += ["--", folder]
    code = _git_returncode(submodule, *args)
    if code == 0:
        return False
    if code == 1:
        return True
    return None


class ChangeInfo(BaseModel):
    model_config = ConfigDict(frozen=True)

    changed: str  # "yes" | "no" | "unknown"
    diff_cmd: str | None = None
    label: str | None = None


def _change_info(
    cfg: RegistryConfig, ref: Any, cap: Any, event: Event, header: RoundHeader | None
) -> ChangeInfo:
    """Changed-since-ruled with the §4 baseline cascade."""
    src = event.source
    repo = ref.repo
    submodule = cfg.repo_root / "reference_harnesses" / repo
    folder = _diff_folder(cap)
    pin = ref.source_commit
    base_sha = src.sha if src else None
    round_pin = header.pins.get(repo) if header else None

    display_base = base_sha or round_pin
    diff_cmd: str | None = None
    label: str | None = None
    if display_base:
        # shlex.join over an argument array so a hostile path/SHA can never become
        # executable shell when the printed command is pasted (review #11).
        argv = ["git", "-C", f"reference_harnesses/{repo}", "diff", display_base]
        if pin:
            argv.append(pin)
        argv += ["--", folder]
        diff_cmd = shlex.join(argv)
        if not base_sha and round_pin:
            label = "baseline inferred from round pin"

    # The §4 cascade, exactly: tree_hash → git diff on sha → git diff on the
    # round pin → unknown. No content_hash fallback (review #1); an unavailable
    # baseline stays unknown rather than silently reading "no".
    changed = "unknown"
    if src and src.tree_hash and cap.tree_hash:
        changed = "yes" if src.tree_hash != cap.tree_hash else "no"
    elif base_sha:
        res = _git_diff_changed(submodule, base_sha, pin, folder)
        if res is not None:
            changed = "yes" if res else "no"
    elif round_pin:
        res = _git_diff_changed(submodule, round_pin, pin, folder)
        if res is not None:
            changed = "yes" if res else "no"
    return ChangeInfo(changed=changed, diff_cmd=diff_cmd, label=label)


def _adopt_target(ruling: Event, forward: dict[str, str]) -> str:
    """The rendered adoption target of a trait `adopt` ruling: a `doc:`/`kind:`
    target verbatim, otherwise the survivor skill and the adopted trait id."""
    assert ruling.skill is not None
    if ":" in ruling.skill:  # doc: or kind: target, no trait id, no lifecycle
        return ruling.skill
    survivor = resolve_skill(ruling.skill, forward)
    tid = ruling.into or _trait_slug(ruling.subject)
    return f"{survivor}#{tid}" if tid else survivor


def _traits_line(
    subject: str,
    event: Event,
    current: dict[str, Event],
    upstream_traits: dict[str, UpstreamTraitEntry],
    forward: dict[str, str],
) -> str:
    """The per-trait ruling summary for a changed capability (§5). Adopt targets
    are resolved through the lifecycle so renamed/merged skills read true (#10)."""
    entry = upstream_traits.get(subject)
    trait_events = effective_traits_for(current, subject)
    parts: list[str] = []
    if entry:
        for tid in entry.traits:
            ruling = trait_events.get(tid)
            if ruling is None:
                continue
            if ruling.kind == "adopt" and ruling.skill:
                suffix = ", pending" if ruling.pending else ""
                parts.append(f"{tid} adopt→{_adopt_target(ruling, forward)}{suffix}")
            else:
                parts.append(f"{tid} {ruling.kind}")
    if parts:
        return " · ".join(parts)
    if event.adaptation and event.adaptation.modifications:
        return "; ".join(event.adaptation.modifications)
    return _one_line(event.why, 100)


def cmd_gap(cfg: RegistryConfig, args: argparse.Namespace) -> int:
    ref = resolve_reference(cfg, args.reference)
    ours = build_ours(cfg)
    headers, events, errors = load_ledger(cfg)
    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        return 1
    live = live_events(events)
    current = effective_by_subject(live)
    headers_by_id = round_header_by_id(headers)
    traits, _ = load_traits(cfg)
    upstream_traits = _upstream_traits(traits)
    forward, _ = build_lifecycle(live)
    our_ids = ours.by_logical_id()
    normalized = _normalized_index(ours)

    not_reviewed: list[Any] = []
    present_unruled: list[Any] = []
    changed: list[tuple[Any, Event, ChangeInfo]] = []
    hash_unknown: list[tuple[Any, Event, ChangeInfo]] = []
    for cap in ref.capabilities:
        if args.kind and cap.kind.value != args.kind:
            continue
        event = current.get(f"{ref.repo}:{cap.logical_id}")
        if event is None:
            if match_to_ours(cap, our_ids, normalized) is not None:
                present_unruled.append(cap)
            else:
                not_reviewed.append(cap)
            continue
        info = _change_info(cfg, ref, cap, event, headers_by_id.get(_round_of(event)))
        if info.changed == "yes":
            changed.append((cap, event, info))
        elif info.changed == "unknown":
            hash_unknown.append((cap, event, info))

    # Removed upstream: ruled subjects with no catalog entry any more (§5),
    # generated independently of reference records and honoring --kind (review #13).
    removed_upstream = [
        (subject, event)
        for subject, event in _removed_upstream(
            ref.repo, current, set(ref.by_logical_id())
        )
        if not args.kind
        or event.source is None
        or event.source.logical_id.startswith(f"{args.kind}:")
    ]

    # Awaiting trait ruling: a grandfathered pre-trait checkpoint whose subject
    # now has an upstream entry but no trait ruling (§5).
    awaiting = [
        (event, upstream_traits[subject])
        for subject, event in current.items()
        if subject.startswith(f"{ref.repo}:")
        and _is_grandfathered(event, current, upstream_traits, cfg.pre_trait_rounds)
        and (
            not args.kind
            or event.source is None
            or event.source.logical_id.startswith(f"{args.kind}:")
        )
    ]

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
        for cap, event, info in sorted(changed, key=lambda t: t[0].logical_id):
            lines.append(
                f"  ~ {cap.logical_id}  (ruled {event.kind} in {_round_of(event)})"
            )
            if info.diff_cmd:
                suffix = f"  [{info.label}]" if info.label else ""
                lines.append(f"    diff: {info.diff_cmd}{suffix}")
            lines.append(
                "    traits: "
                + _traits_line(
                    f"{ref.repo}:{cap.logical_id}",
                    event,
                    current,
                    upstream_traits,
                    forward,
                )
            )
    if hash_unknown:
        lines.append(f"\n### baseline unknown — review ({len(hash_unknown)})")
        for cap, event, info in sorted(hash_unknown, key=lambda t: t[0].logical_id):
            lines.append(
                f"  ? {cap.logical_id}  (ruled {event.kind}, no usable baseline)"
            )
    if removed_upstream:
        lines.append(f"\n### removed upstream ({len(removed_upstream)})")
        for subject, event in sorted(removed_upstream, key=lambda t: t[0]):
            dest = f" → {event.skill}" if event.skill else ""
            lines.append(f"  - {subject}  (last ruled {event.kind}{dest})")
    if awaiting:
        lines.append(f"\n### awaiting trait ruling ({len(awaiting)})")
        for event, entry in sorted(awaiting, key=lambda t: t[0].subject):
            lines.append(
                f"  * {event.subject.split(':', 1)[1]}  (checkpoint {event.id}, "
                f"traits listed at {entry.reviewed_sha})"
            )
    if not (
        not_reviewed
        or present_unruled
        or changed
        or hash_unknown
        or removed_upstream
        or awaiting
    ):
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
    if "source" not in data and data.get("kind") == "adopt" and not data.get("pending"):
        # Completing a pending adopt copies its source, never the current catalog
        # (§5, review r1 #4).
        _, events, _ = load_ledger(cfg)
        prior = effective_by_subject(live_events(events)).get(subject)
        if prior is not None and prior.kind == "adopt" and prior.pending:
            assert prior.source is not None
            data["source"] = prior.source.model_dump(exclude_none=True)
    if "source" not in data and ":" in subject and not subject.startswith("ours:"):
        # An idea subject carries a trailing #<slug>; the catalog is keyed by the
        # bare logical id, so strip it before autofilling the source.
        repo, _, logical = subject.partition(":")
        source = _autofill_source(cfg, repo, logical.split("#", 1)[0])
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
    """Adopted lineage: one entry per adopted trait (the last delivered adopt,
    else the pending one, labelled), and a capability checkpoint only when no
    trait adopt into this skill stands for it (review r1 #12)."""
    adopts = [
        e
        for e in events
        if e.skill == skill
        and e.kind in {"adopt", "adopt-merged"}
        and e.source is not None
    ]
    by_trait: dict[str, Event] = {}
    for e in adopts:
        if _is_trait_subject(e.subject):
            held = by_trait.get(e.subject)
            if held is None or held.pending or not e.pending:
                by_trait[e.subject] = e
    trait_bases = {_trait_base(subject) for subject in by_trait}
    rows: list[Event] = []
    for e in adopts:
        if _is_trait_subject(e.subject):
            if by_trait.get(e.subject) is e:
                rows.append(e)
        elif e.subject not in trait_bases:
            rows.append(e)
    if not rows:
        return "No adopted lineage recorded."
    lines: list[str] = []
    for event in rows:
        src = event.source
        assert src is not None
        sha = f" @ {src.sha}" if src.sha else ""
        path = f" `{src.path}`" if src.path else ""
        pending = f" (pending {event.pending})" if event.pending else ""
        lines.append(f"- **{event.subject}**{path}{sha}{pending}")
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


def _carried_replacements(current: dict[str, Event]) -> dict[str, Event]:
    """Earlier trait subject -> the effective event that carries it (§5): used to
    render ``upstream replaced it with B`` on an adoption of A."""
    out: dict[str, Event] = {}
    for event in current.values():
        for carried in event.carried_from:
            out[carried] = event
    return out


def _traits_record_block(
    skill: str,
    ours_traits: dict[str, OursTraitEntry],
    definitions: dict[str, TraitDefinition],
) -> str:
    """The skill's traits from `traits.yaml`, with their definitions (§7)."""
    entry = ours_traits.get(skill)
    if entry is None or not entry.traits:
        return "No traits recorded."
    lines: list[str] = []
    for tid in entry.traits:
        d = definitions.get(tid)
        text = d.definition if d else ""
        note = entry.notes.get(tid)
        suffix = f" ({note})" if note else ""
        lines.append(f"- `{tid}`: {text}{suffix}")
    return "\n".join(lines)


def _sources_block(
    skill: str,
    events: list[Event],
    current: dict[str, Event],
    forward: dict[str, str],
    withdrawn: dict[tuple[str, str], str],
    retired: set[str],
    ours_traits: dict[str, OursTraitEntry],
    definitions: dict[str, TraitDefinition],
) -> str:
    """Per trait id, the upstream traits adopted into it — the last delivered
    adopt even when later superseded, withdrawn or replaced upstream (§5, §7).
    `skill` is the current survivor name; adoptions are matched through the
    lifecycle.

    Reads the same `retained_adoptions` that the coverage check (C) reads, so the
    listed sources and the enforced obligations can never disagree (review r3)."""
    adopts: dict[str, Event] = {
        subject: adopt
        for (subject, dest), adopt in retained_adoptions(events, forward).items()
        if dest == skill
    }
    if not adopts:
        return "No adopted traits recorded."
    replaced = _carried_replacements(current)
    listed = set(ours_traits[skill].traits) if skill in ours_traits else set()
    grouped: dict[str, list[str]] = {}
    for subject, event in adopts.items():
        assert event.subject is not None
        tid = event.into or _trait_slug(subject)
        sha = event.source.sha if event.source else None
        label = f"adopted at {sha}" if sha else "adopted"
        d = definitions.get(tid or "")
        if d and d.retired and tid not in listed:
            label += f"; adopted as {tid}, now {', '.join(d.retired.replaced_by)}"
        if (subject, skill) in withdrawn:
            label += f"; withdrawn {withdrawn[(subject, skill)]}"
        elif skill in retired:
            label += "; no longer provided"
        elif subject in replaced:
            b = replaced[subject]
            bid = _trait_slug(b.subject)
            label += f"; upstream replaced it with {bid} ({b.kind})"
        else:
            cur = current.get(subject)
            if cur is not None and cur.kind != "adopt":
                label += f"; current upstream revision {cur.kind}"
        grouped.setdefault(tid or "(unmapped)", []).append(f"  - `{subject}` ({label})")
    lines: list[str] = []
    for tid in sorted(grouped):
        lines.append(f"- `{tid}`:")
        lines.extend(sorted(grouped[tid]))
    return "\n".join(lines)


def _declined_block(
    skill: str, current: dict[str, Event], forward: dict[str, str]
) -> str:
    """Upstream traits whose effective ruling is reject/defer, considered for this
    skill, with the reason (§7)."""
    lines: list[str] = []
    for subject, event in sorted(current.items()):
        if (
            _is_trait_subject(subject)
            and event.kind in {"reject", "defer"}
            and event.skill
            and ":" not in event.skill
            and resolve_skill(event.skill, forward) == skill
        ):
            lines.append(f"- `{subject}` ({event.kind}): {_one_line(event.why, 160)}")
    return "\n".join(lines) if lines else "No declined traits recorded."


_CAPABILITY_RE = re.compile(r"^##\s+Capability\s*$", re.MULTILINE)


def _strip_covers_section(text: str) -> str:
    """Remove a hand-written ``### Covers`` section (traits-design §7); the traits
    block takes its place. Keeps everything before and after it."""
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    skipping = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().lstrip("#").strip() == "covers" and stripped.startswith(
            "#"
        ):
            skipping = True
            continue
        if skipping:
            # The Covers list ends at the next heading or generated block marker.
            if stripped.startswith(("#", "<!--")):
                skipping = False
            else:
                continue
        out.append(line)
    return "".join(out)


def _ensure_traits_block(out: str) -> str:
    """Make sure the generated ``traits`` block exists, inserted where Covers used
    to be — after the Capability paragraph, before the first generated block."""
    if TRAITS_OPEN in out:
        return out
    block = f"{TRAITS_OPEN}\n{TRAITS_CLOSE}"
    for marker in (SOURCES_OPEN, DECLINED_OPEN, LINEAGE_OPEN, HISTORY_OPEN):
        idx = out.find(marker)
        if idx != -1:
            return f"{out[:idx]}{block}\n\n{out[idx:]}"
    return f"{out.rstrip()}\n\n{block}\n"


def render_record(
    text: str,
    events: list[Event],
    dead: set[str],
    ours_traits: dict[str, OursTraitEntry],
    definitions: dict[str, TraitDefinition],
    opted_in: bool = False,
) -> str:
    fm, _ = parse_record(text)
    out = _strip_covers_section(text)
    lineage = _lineage_block(fm.skill, events)
    history = _history_block(fm.skill, events, dead)
    reviews = _reviews_block(fm.skill, events)
    out = _replace_block(out, LINEAGE_OPEN, LINEAGE_CLOSE, lineage)
    out = _replace_block(out, HISTORY_OPEN, HISTORY_CLOSE, history)
    if REVIEWS_OPEN in out:
        out = _replace_block(out, REVIEWS_OPEN, REVIEWS_CLOSE, reviews)
    else:
        out = _insert_after(
            out, HISTORY_CLOSE, f"{REVIEWS_OPEN}\n{reviews}\n{REVIEWS_CLOSE}"
        )
    # A skill with a traits.yaml entry (or targeted by a retained adoption) carries
    # the traits block and the sources/declined provenance blocks; insert them
    # lazily when missing so a required view can never silently disappear (#14).
    if fm.skill in ours_traits or opted_in:
        out = _ensure_traits_block(out)
        if SOURCES_OPEN not in out:
            out = _insert_after(out, REVIEWS_CLOSE, f"{SOURCES_OPEN}\n{SOURCES_CLOSE}")
        if DECLINED_OPEN not in out:
            out = _insert_after(
                out, SOURCES_CLOSE, f"{DECLINED_OPEN}\n{DECLINED_CLOSE}"
            )
    if TRAITS_OPEN in out:
        out = _replace_block(
            out,
            TRAITS_OPEN,
            TRAITS_CLOSE,
            _traits_record_block(fm.skill, ours_traits, definitions),
        )
    if SOURCES_OPEN in out or DECLINED_OPEN in out:
        live = live_events(events)
        current = effective_by_subject(live)
        forward, retired = build_lifecycle(live)
        withdrawn = withdrawn_destinations(events, forward)
        if SOURCES_OPEN in out:
            out = _replace_block(
                out,
                SOURCES_OPEN,
                SOURCES_CLOSE,
                _sources_block(
                    fm.skill,
                    events,
                    current,
                    forward,
                    withdrawn,
                    retired,
                    ours_traits,
                    definitions,
                ),
            )
        if DECLINED_OPEN in out:
            out = _replace_block(
                out,
                DECLINED_OPEN,
                DECLINED_CLOSE,
                _declined_block(fm.skill, current, forward),
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


_CAP_KINDS = frozenset({"skill", "agent", "command", "rule", "hook", "mcp", "plugin"})


def _is_genuine_capability_subject(subject: str) -> bool:
    """A capability subject the scanner would surface if it still shipped — so a
    `doc:` ruling or a scanner-excluded `-test` hook never reads as "removed
    upstream" (reviews #13 / avoids false positives)."""
    _, _, logical = subject.partition(":")
    kind, _, rest = logical.partition(":")
    if kind not in _CAP_KINDS:
        return False
    name = rest.rsplit("/", 1)[-1].split("#", 1)[0]
    return not (kind == "hook" and scan._is_test_script(name))


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


def _traits_cell(
    subject: str,
    current: dict[str, Event],
    entry: UpstreamTraitEntry,
) -> str:
    """`3 adopt · 1 reject` (removed traits excluded) for a capability row (§7)."""
    trait_events = effective_traits_for(current, subject)
    counts: dict[str, int] = {}
    for tid in entry.traits:
        ruling = trait_events.get(tid)
        if ruling is not None:
            counts[ruling.kind] = counts.get(ruling.kind, 0) + 1
    return " · ".join(f"{n} {kind}" for kind, n in sorted(counts.items())) or "—"


def _reference_destinations(
    subject: str,
    event: Event,
    current: dict[str, Event],
    forward: dict[str, str],
) -> str:
    """Every destination for a capability row — resolved from its trait adoptions
    through the lifecycle, not just the checkpoint's single target (review #10)."""
    dests: list[str] = []
    seen: set[str] = set()
    for ruling in effective_traits_for(current, subject).values():
        if ruling.kind != "adopt" or not ruling.skill:
            continue
        label = _adopt_target(ruling, forward)
        if label not in seen:
            seen.add(label)
            dests.append(label)
    if dests:
        return ", ".join(dests)
    return event.skill or ""


def render_reference(
    catalog: Any,
    current: dict[str, Event],
    our_ids: dict[str, Any],
    normalized: dict[tuple[str, str], str],
    upstream_traits: dict[str, UpstreamTraitEntry] | None = None,
    *,
    cfg: RegistryConfig | None = None,
    headers_by_id: dict[str, RoundHeader] | None = None,
    forward: dict[str, str] | None = None,
) -> str:
    upstream_traits = upstream_traits or {}
    headers_by_id = headers_by_id or {}
    forward = forward or {}
    # The Traits column appears only once a repo has at least one traits.yaml
    # entry (§7), so a tree with none renders unchanged; for opted-in repos the
    # changed column shares `gap`'s baseline cascade so the two never disagree
    # (review #9).
    has_traits = any(s.startswith(f"{catalog.repo}:") for s in upstream_traits)
    header = "| Their capability | Status | Into ours | Last ruled at | Changed upstream since? |"
    rule = "|---|---|---|---|---|"
    if has_traits:
        header = (
            "| Their capability | Status | Into ours | Traits | "
            "Last ruled at | Changed upstream since? |"
        )
        rule = "|---|---|---|---|---|---|"
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
        header,
        rule,
    ]
    for cap in catalog.capabilities:
        status, event, changed = classify_capability(
            cap, catalog.repo, current, our_ids, normalized
        )
        subject = f"{catalog.repo}:{cap.logical_id}"
        into = event.skill or "" if event else ""
        ruled = _round_of(event) if event else ""
        # The changed column shares gap's §4 baseline cascade for every repo so
        # the two never disagree (review #9); the Ideas column stays opt-in.
        if event is not None and cfg is not None:
            changed = _change_info(
                cfg, catalog, cap, event, headers_by_id.get(_round_of(event))
            ).changed
        if has_traits:
            if event is not None:
                into = _reference_destinations(subject, event, current, forward)
            entry = upstream_traits.get(subject)
            traits = _traits_cell(subject, current, entry) if entry else ""
            lines.append(
                f"| `{cap.logical_id}` | {status} | {into} | {traits} | {ruled} | {changed} |"
            )
        else:
            lines.append(
                f"| `{cap.logical_id}` | {status} | {into} | {ruled} | {changed} |"
            )
    removed = _removed_upstream(catalog.repo, current, set(catalog.by_logical_id()))
    if removed:
        lines.append("")
        lines.append("## Removed capabilities (removed upstream)")
        lines.append("")
        for subject, event in removed:
            dest = f" → {event.skill}" if event.skill else ""
            lines.append(f"- `{subject}` — last ruled {event.kind}{dest}")
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


def _ruling_suffix(ruling: Event | None, forward: dict[str, str]) -> str:
    """The ` — <kind>` suffix (plus ` → <target>` for an adopt, and `, pending
    <bead>`) for a trait's effective ruling; empty when unruled (§7). Reuses the
    ledger's effective rulings so TRAITS.md never disagrees with the ledger."""
    if ruling is None:
        return ""
    if ruling.kind == "adopt" and ruling.skill:
        pending = f", pending {ruling.pending}" if ruling.pending else ""
        return f" — adopt{pending} → {_adopt_target(ruling, forward)}"
    return f" — {ruling.kind}"


def _placement_key(p: Placement) -> tuple[tuple[int, str], int, str]:
    return (
        _domain_key(p.domain),
        STAGE_ORDER.index(p.stage) if p.stage in STAGE_ORDER else len(STAGE_ORDER),
        p.substage,
    )


def render_traits(
    cfg: RegistryConfig,
    current: dict[str, Event],
    forward: dict[str, str],
    definitions: dict[str, TraitDefinition],
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
) -> str:
    """TRAITS.md: a by-skill and a by-trait view of every trait (§7)."""
    ours = _ours_traits(traits)
    upstream = _upstream_traits(traits)
    records = {fm.skill: fm for fm in load_records(cfg).values()}

    def defn(tid: str) -> str:
        d = definitions.get(tid)
        return d.definition if d else ""

    lines = [
        "# Traits",
        "",
        "<!-- GENERATED by registry.py build. Do not edit. -->",
        "",
        (
            "By skill, then by trait. The vocabulary and lists live in "
            "`trait-definitions.yaml` and `traits.yaml`; rulings come from the ledger."
        ),
        "",
        "## By skill",
        "",
        "### Ours",
        "",
    ]
    # Ours, grouped by the record's placement.
    placed_ours = [
        (records[skill], entry) for skill, entry in ours.items() if skill in records
    ]
    for fm, entry in sorted(
        placed_ours,
        key=lambda t: (_domain_key(t[0].domain), t[0].stage, t[0].substage, t[0].skill),
    ):
        lines.append(f"#### {fm.domain} · {fm.stage} · {fm.substage} — {fm.skill}")
        for tid in entry.traits:
            lines.append(f"- `{tid}`: {defn(tid)}")
        lines.append("")
    # Upstream, grouped by repo then placement, with the effective ruling suffix.
    by_repo: dict[str, list[tuple[str, UpstreamTraitEntry]]] = {}
    for subject, entry in upstream.items():
        by_repo.setdefault(subject.partition(":")[0], []).append((subject, entry))
    for repo in sorted(by_repo):
        lines.append(f"### {repo}")
        lines.append("")
        for subject, entry in sorted(
            by_repo[repo], key=lambda t: (_placement_key(t[1].placement), t[0])
        ):
            p = entry.placement
            name = subject.partition(":")[2]
            lines.append(f"#### {p.domain} · {p.stage} · {p.substage} — {name}")
            trait_events = effective_traits_for(current, subject)
            for tid in entry.traits:
                suffix = _ruling_suffix(trait_events.get(tid), forward)
                lines.append(f"- `{tid}`: {defn(tid)}{suffix}")
            lines.append("")

    # By trait: every defined trait (plus any listed trait without a definition),
    # grouped by the definition's placement.
    lines.append("## By trait")
    lines.append("")
    listed = {tid for entry in traits.values() for tid in entry.traits}
    all_ids = set(definitions) | listed
    ordered = sorted(
        all_ids,
        key=lambda tid: (
            _placement_key(definitions[tid].placement)
            if tid in definitions
            else (len(DOMAIN_ORDER), len(STAGE_ORDER), ""),
            tid,
        ),
    )
    heading = None
    for tid in ordered:
        d = definitions.get(tid)
        p = d.placement if d else None
        here = f"{p.domain} · {p.stage} · {p.substage}" if p else "(undefined)"
        if here != heading:
            heading = here
            lines.append(f"### {here}")
            lines.append("")
        retired = " *(retired)*" if d and d.retired else ""
        lines.append(f"#### `{tid}`{retired}")
        if d:
            lines.append(f"{d.definition}")
        holders = sorted(skill for skill, e in ours.items() if tid in e.traits)
        for skill in holders:
            lines.append(f"- ours: `{skill}`")
        for subject, entry in sorted(upstream.items()):
            if tid not in entry.traits:
                continue
            ruling = effective_traits_for(current, subject).get(tid)
            lines.append(f"- `{subject}`{_ruling_suffix(ruling, forward)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


# --- build --------------------------------------------------------------------


def build_outputs(cfg: RegistryConfig) -> dict[Path, str]:
    """Every generated file's path → its current content (no writes)."""
    _, events, errors = load_ledger(cfg)
    if errors:
        raise SystemExit("ledger has errors; run `check`:\n" + "\n".join(errors))
    headers = load_ledger(cfg)[0]
    headers_by_id = round_header_by_id(headers)
    live = live_events(events)
    current = effective_by_subject(live)
    dead = superseded_ids(events)  # history: render_record marks superseded events
    forward, _ = build_lifecycle(live)
    opted_in = _opted_in_skills(
        events, forward
    )  # raw: obligation survives supersession
    definitions, def_errors = load_trait_definitions(cfg)
    traits, trait_errors = load_traits(cfg)
    if def_errors or trait_errors:
        raise SystemExit(
            "trait files have errors; run `check`:\n"
            + "\n".join(def_errors + trait_errors)
        )
    ours_traits = _ours_traits(traits)
    upstream_traits = _upstream_traits(traits)
    outputs: dict[Path, str] = {}
    for path in record_paths(cfg):
        fm, _ = parse_record(path.read_text(encoding="utf-8"))
        outputs[path] = render_record(
            path.read_text(encoding="utf-8"),
            events,
            dead,
            ours_traits,
            definitions,
            fm.skill in opted_in,
        )
    records = load_records(cfg)
    outputs[cfg.index_path] = render_index(cfg, records)
    outputs[cfg.traits_md_path] = render_traits(
        cfg, current, forward, definitions, traits
    )
    ours = build_ours(cfg)
    our_ids = ours.by_logical_id()
    normalized = _normalized_index(ours)
    for cat_path in _catalog_files(cfg):
        catalog = scan.Catalog.from_dict(
            json.loads(cat_path.read_text(encoding="utf-8"))
        )
        outputs[cfg.references_dir / f"{cat_path.stem}.md"] = render_reference(
            catalog,
            current,
            our_ids,
            normalized,
            upstream_traits,
            cfg=cfg,
            headers_by_id=headers_by_id,
            forward=forward,
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
    definitions, def_errors = load_trait_definitions(cfg)
    traits, trait_errors = load_traits(cfg)
    errors += def_errors + trait_errors
    # One live (non-superseded) event list feeds every lifecycle/withdrawal
    # consumer, so a correction takes effect everywhere at once (N2/N3). Coverage
    # obligations instead read raw events (an upstream reject never withdraws an
    # adoption — only an ours-side `update` does), so `_check_trait_level` and
    # `_opted_in_skills` get the raw list (review r3).
    live = live_events(events)
    forward, retired = build_lifecycle(live)
    warnings: list[str] = []
    errors += _check_effective_targets(
        cfg, live, set(records), aliases, ours, forward, retired
    )
    errors += _check_carried_from(
        events
    )  # history: carried_from names an earlier subject
    errors += _check_withdraws(
        events, forward
    )  # raw: superseded adopt still withdrawable
    errors += _check_adopt_merged_adaptation(headers, live)
    errors += _check_block_pairing(cfg)
    errors += _check_trait_definitions(definitions)
    errors += _check_traits_yaml(cfg, traits, definitions, set(records), ours, events)
    warnings += _retired_trait_warnings(traits, definitions)
    warnings += _overlap_warnings(traits, records)
    errors += _check_trait_level(
        cfg, headers, events, ours, forward, retired, definitions, traits
    )

    # Records with no traits.yaml entry stay lazy; report how many (traits-design).
    ours_traits = _ours_traits(traits)
    lazy = sum(
        1
        for skill, fm in records.items()
        if fm.status == "active" and skill not in ours_traits
    )

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

    for line in warnings:
        print(f"warning: {line}", file=sys.stderr)
    if errors:
        for line in errors:
            print(f"error: {line}", file=sys.stderr)
        print(f"\n{len(errors)} problem(s)", file=sys.stderr)
        return 1
    print(
        f"ok: {len(headers)} round(s), {len(events)} event(s), "
        f"{len(records)} skill record(s); "
        f"{lazy} record(s) without a traits.yaml entry (lazy)"
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


def _target_exists(
    target: str | None,
    existing: set[str],
    ours: Any,
    cfg: RegistryConfig | None = None,
) -> bool:
    """True when an adoption target resolves. A plain name must be a skill
    record, alias or stub. A `doc:<repo-relative path>` target (a method
    document, §2) resolves when the file exists. A `kind:name` target is valid
    only when kind is a real non-skill kind, name is non-empty, and that
    capability exists in our shipped surface — matched by full logical id or by
    exact (kind, name). The exact-name form covers the documented legacy prefix
    normalization (e.g. `agent:code-reviewer` ↔ `agent:agents/code-reviewer`,
    the legacy short form), since a capability's `name` is the bare leaf. A
    fabricated namespace such as `agent:does-not-exist/agents/code-reviewer`
    matches neither and is rejected."""
    if not target:
        return False
    if target.startswith("doc:"):
        rel = target[len("doc:") :]
        # Must be a repo-relative path that stays inside repo_root, even through
        # symlinks — `doc:/etc/passwd` and `doc:../x` are rejected (review #15).
        if not rel or rel.startswith("/") or ".." in Path(rel).parts:
            return False
        if cfg is None:
            return True
        root = cfg.repo_root.resolve()
        resolved = (cfg.repo_root / rel).resolve()
        if not resolved.is_relative_to(root):
            return False
        return resolved.is_file()
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
    cfg: RegistryConfig,
    events: list[Event],
    records: set[str],
    aliases: set[str],
    ours: Any,
    forward: dict[str, str],
    retired: set[str],
) -> list[str]:
    """Every live adoption carries a source and a target that resolves today.
    A target is resolved through our rename/merge lifecycle (§3); a target that
    was retired is "adopted, no longer provided", not an error. An unresolved,
    still-active target is an error."""
    existing = records | aliases | STUB_SKILLS
    effective = effective_by_subject(events)
    errors: list[str] = []
    for subject, event in effective.items():
        if event.kind not in {"adopt", "adopt-merged"}:
            continue
        if event.source is None:
            errors.append(f"{event.id}: live adoption of {subject} has no source")
        target = event.skill
        # Plain skill targets follow rename/merge; kind:name and doc: targets do not.
        resolved = target
        if target and ":" not in target:
            resolved = resolve_skill(target, forward)
        if resolved in retired:
            continue
        if _target_exists(resolved, existing, ours, cfg):
            continue
        errors.append(
            f"{event.id}: live adoption of {subject} has an invalid "
            f"skill target {event.skill!r}"
        )
    return errors


def _check_carried_from(events: list[Event]) -> list[str]:
    """Each carried_from must name an *earlier* trait subject — not itself, not a
    capability subject, and not one introduced only later (§5, review #18)."""
    errors: list[str] = []
    seen_before: set[str] = set()
    for event in events:
        for carried in event.carried_from:
            if carried == event.subject:
                errors.append(f"{event.id}: carried_from {carried!r} is itself")
            elif not _is_trait_subject(carried):
                errors.append(
                    f"{event.id}: carried_from {carried!r} is not a trait subject"
                )
            elif carried not in seen_before:
                errors.append(
                    f"{event.id}: carried_from {carried!r} is not an earlier trait subject"
                )
        seen_before.add(event.subject)
    return errors


def _check_withdraws(events: list[Event], forward: dict[str, str]) -> list[str]:
    """An ours-side `update` withdraws only traits adopted into this skill (§5).
    Reads raw events: an adoption superseded by an upstream reject is still a
    live obligation and remains withdrawable (review r3)."""
    errors: list[str] = []
    for event in events:
        if event.kind != "update" or not event.withdraws:
            continue
        skill = resolve_skill(event.skill or "", forward)
        for subject in event.withdraws:
            adopted_here = any(
                e.kind == "adopt"
                and e.subject == subject
                and e.skill
                and ":" not in e.skill
                and resolve_skill(e.skill, forward) == skill
                for e in events
            )
            if not adopted_here:
                errors.append(
                    f"{event.id}: withdraws {subject!r} but no adopt event targets "
                    f"{event.skill!r}"
                )
    return errors


def _check_adopt_merged_adaptation(
    headers: list[RoundHeader], events: list[Event]
) -> list[str]:
    """An `adopt-merged` capability event outside a trait-level round must carry
    `adaptation` (README §5, review #4); inside one it is optional."""
    trait_rounds = {h.round_id for h in headers if h.trait_level}
    errors: list[str] = []
    for event in events:
        if (
            event.kind == "adopt-merged"
            and not _is_trait_subject(event.subject)
            and event.adaptation is None
            and _round_of(event) not in trait_rounds
        ):
            errors.append(
                f"{event.id}: adopt-merged needs `adaptation` outside a trait-level round"
            )
    return errors


_BLOCK_MARKERS = (
    (TRAITS_OPEN, TRAITS_CLOSE),
    (SOURCES_OPEN, SOURCES_CLOSE),
    (DECLINED_OPEN, DECLINED_CLOSE),
    (LINEAGE_OPEN, LINEAGE_CLOSE),
    (HISTORY_OPEN, HISTORY_CLOSE),
    (REVIEWS_OPEN, REVIEWS_CLOSE),
)


def _check_block_pairing(cfg: RegistryConfig) -> list[str]:
    """Each generated block that appears must be correctly paired and ordered:
    exactly one open and one close, with the close after the open (review #14)."""
    errors: list[str] = []
    for path in record_paths(cfg):
        text = path.read_text(encoding="utf-8")
        for open_tag, close_tag in _BLOCK_MARKERS:
            opens = text.count(open_tag)
            closes = text.count(close_tag)
            if opens == 0 and closes == 0:
                continue
            if opens != 1 or closes != 1 or text.find(open_tag) > text.find(close_tag):
                errors.append(
                    f"{_rel(cfg, path)}: malformed {open_tag!r} block (open/close pairing)"
                )
    return errors


def _opted_in_skills(events: list[Event], forward: dict[str, str]) -> set[str]:
    """Skills that are targeted by a retained trait adoption — the records that
    must carry traits/provenance blocks (§7)."""
    out: set[str] = set()
    for adopt in retained_adoptions(events, forward).values():
        dest = adopt.skill
        if dest and ":" not in dest:
            out.add(resolve_skill(dest, forward))
    return out


def _checkpoint_expectation(kinds: list[str]) -> tuple[str, bool]:
    """(expected capability kind, whether a target is required) for the trait
    rulings of one checkpoint (removed traits already excluded), per README §5b."""
    adopts = [k for k in kinds if k == "adopt"]
    if adopts and len(adopts) == len(kinds):
        return "adopt", True
    if adopts:
        return "adopt-merged", True
    if len(set(kinds)) == 1:
        return kinds[0], False
    return "reject", False


def _trait_satisfied(
    trait_id: str, listed: set[str], definitions: dict[str, TraitDefinition]
) -> bool:
    """A holder lists the trait, or — when it is retired — every `replaced_by`
    trait (traits-design §1)."""
    if trait_id in listed:
        return True
    d = definitions.get(trait_id)
    if d and d.retired and d.retired.replaced_by:
        return all(r in listed for r in d.retired.replaced_by)
    return False


def _catalog_subjects(cfg: RegistryConfig) -> set[str]:
    """Every `<repo>:<logical_id>` currently in a catalog file (traits-design §2:
    an upstream key must be in the catalog or ruled removed upstream)."""
    out: set[str] = set()
    for cat_path in _catalog_files(cfg):
        try:
            catalog = scan.Catalog.from_dict(
                json.loads(cat_path.read_text(encoding="utf-8"))
            )
        except Exception:  # noqa: BLE001, S112 - malformed catalogs ignored here
            continue
        for logical in catalog.by_logical_id():
            out.add(f"{catalog.repo}:{logical}")
    return out


def _check_trait_definitions(
    definitions: dict[str, TraitDefinition],
) -> list[str]:
    """`distinct_from` and `replaced_by` resolve to defined traits (§1, §4)."""
    errors: list[str] = []
    for tid, d in definitions.items():
        for other in d.distinct_from:
            if other not in definitions:
                errors.append(
                    f"trait-definitions.yaml: {tid}: distinct_from {other!r} is undefined"
                )
        if d.retired:
            for repl in d.retired.replaced_by:
                if repl not in definitions:
                    errors.append(
                        f"trait-definitions.yaml: {tid}: replaced_by {repl!r} is undefined"
                    )
    return errors


def _check_traits_yaml(
    cfg: RegistryConfig,
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
    definitions: dict[str, TraitDefinition],
    records: set[str],
    ours: Any,
    events: list[Event],
) -> list[str]:
    """Each entry: a resolvable key, defined trait IDs, no repeats, metadata keys
    that are defined and belong to the entry, and — for an ours entry — a
    tree_hash matching its skill folder today (§2).

    An upstream key is `<repo>:skill:<path>` and is in that repo's catalog or
    has ledger history (an event on the capability, which is then a
    removed-upstream subject) (review r1 #7)."""
    errors: list[str] = []
    tree_hashes = _our_tree_hashes(ours)
    catalog_subjects = _catalog_subjects(cfg)
    ruled = {e.subject for e in events if not _is_trait_subject(e.subject)}
    for key, entry in traits.items():
        if isinstance(entry, OursTraitEntry):
            skill = key[len("ours:") :]
            if skill not in records:
                errors.append(f"traits.yaml: {key}: no skill record for {skill!r}")
            want = tree_hashes.get(skill)
            if want is not None and entry.tree_hash != want:
                errors.append(f"traits.yaml: {key}: tree_hash is stale")
            permitted = {"notes": set(entry.traits)}
        else:
            repo, _, logical = key.partition(":")
            if not repo or not logical.startswith("skill:") or logical == "skill:":
                errors.append(
                    f"traits.yaml: {key}: an upstream key is <repo>:skill:<path>"
                )
            elif key not in catalog_subjects and key not in ruled:
                errors.append(
                    f"traits.yaml: {key}: not in its catalog and has no "
                    f"removed-upstream history in the ledger"
                )
            for tid in entry.removed:
                if tid in entry.traits:
                    errors.append(
                        f"traits.yaml: {key}: removed trait {tid!r} is still listed"
                    )
            held = set(entry.traits) | set(entry.removed)
            permitted = {"removed": held, "added": held, "notes": held}
        for name, allowed in permitted.items():
            for tid in getattr(entry, name):
                if tid not in definitions:
                    errors.append(
                        f"traits.yaml: {key}: {name} trait {tid!r} is undefined"
                    )
                elif tid not in allowed:
                    errors.append(
                        f"traits.yaml: {key}: {name} trait {tid!r} is not in the entry"
                    )
        seen: set[str] = set()
        for tid in entry.traits:
            if tid in seen:
                errors.append(f"traits.yaml: {key}: trait {tid!r} is listed twice")
            seen.add(tid)
            if tid not in definitions:
                errors.append(f"traits.yaml: {key}: trait {tid!r} is undefined")
    return errors


def _retired_trait_warnings(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
    definitions: dict[str, TraitDefinition],
) -> list[str]:
    """While any entry lists a retired trait, warn and name the holders (§1)."""
    holders: dict[str, list[str]] = {}
    for key, entry in traits.items():
        for tid in entry.traits:
            d = definitions.get(tid)
            if d and d.retired:
                holders.setdefault(tid, []).append(key)
    return [
        f"retired trait {tid!r} still listed by {', '.join(sorted(keys))}"
        for tid, keys in sorted(holders.items())
    ]


def _overlap_warnings(
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
    records: dict[str, Frontmatter],
) -> list[str]:
    """A trait listed by two of our active skills is an overlap (§6)."""
    holders: dict[str, list[str]] = {}
    for skill, entry in _ours_traits(traits).items():
        fm = records.get(skill)
        if fm is None or fm.status != "active":
            continue
        for tid in entry.traits:
            holders.setdefault(tid, []).append(skill)
    shared = {tid: skills for tid, skills in holders.items() if len(skills) > 1}
    if not shared:
        return []
    lines = [f"overlap: {len(shared)} trait(s) listed by more than one active skill"]
    for tid, skills in sorted(shared.items()):
        lines.append(f"overlap: {tid!r} in {', '.join(sorted(skills))}")
    return lines


def _check_trait_level(
    cfg: RegistryConfig,
    headers: list[RoundHeader],
    events: list[Event],
    ours: Any,
    forward: dict[str, str],
    retired: set[str],
    definitions: dict[str, TraitDefinition],
    traits: dict[str, OursTraitEntry | UpstreamTraitEntry],
) -> list[str]:
    """Trait-level consistency, completeness, membership and coverage (§5).

    `events` is the RAW list: the current ruling and withdrawal state come from
    live events, but coverage obligations (C) read raw events so a superseded
    adopt still obliges the trait list until an ours-side `update` withdraws it
    (review r3)."""
    errors: list[str] = []
    live = live_events(events)
    current = effective_by_subject(live)
    upstream_traits = _upstream_traits(traits)
    ours_traits = _ours_traits(traits)
    tree_hashes = _our_tree_hashes(ours)
    trait_rounds = {h.round_id for h in headers if h.trait_level}
    withdrawn = withdrawn_destinations(events, forward)

    # (A) Consistency — whenever a capability has effective trait rulings, it
    # needs an effective checkpoint (review r1 #2), and that checkpoint (whatever
    # its kind) must agree with them (review #3).
    trait_bases = {_trait_base(s) for s in current if _is_trait_subject(s)}
    for base in sorted(trait_bases):
        checkpoint = current.get(base)
        if checkpoint is None:
            first = min(ev.id for ev in effective_traits_for(current, base).values())
            errors.append(
                f"{first}: trait rulings on {base!r} have no effective capability "
                f"checkpoint"
            )
            continue
        entry = upstream_traits.get(base)
        removed = set(entry.removed) if entry else set()
        active = {
            slug: ev
            for slug, ev in effective_traits_for(current, base).items()
            if slug not in removed
        }
        if not active:
            continue
        expected_kind, needs_target = _checkpoint_expectation(
            [ev.kind for ev in active.values()]
        )
        if checkpoint.kind != expected_kind:
            errors.append(
                f"{checkpoint.id}: checkpoint kind {checkpoint.kind!r} disagrees with "
                f"its traits (expected {expected_kind!r})"
            )
        if needs_target:
            targets = {ev.skill for ev in active.values() if ev.kind == "adopt"}
            if checkpoint.skill not in targets:
                errors.append(
                    f"{checkpoint.id}: checkpoint target {checkpoint.skill!r} is not one "
                    f"of its trait targets {sorted(t for t in targets if t)!r}"
                )

    # (B) Completeness — every effective trait-level checkpoint (not
    # grandfathered, and its round is trait-level, its subject has an entry or
    # any trait ruling), whatever its kind, needs its entry, a matching
    # reviewed_sha and tree_hash, and a ruling for every listed trait (§5). A
    # grandfathered pre-trait checkpoint awaits a trait ruling (`gap` lists it).
    for subject, event in current.items():
        if subject.startswith("ours:") or _is_trait_subject(subject):
            continue
        if event.source is None or not event.source.logical_id.startswith("skill:"):
            continue
        entry = upstream_traits.get(subject)
        trait_rulings = effective_traits_for(current, subject)
        if not _is_trait_level(
            event, current, trait_rounds, upstream_traits, cfg.pre_trait_rounds
        ):
            continue  # checkpoint-only, or awaiting a trait ruling
        if entry is None:
            errors.append(
                f"{event.id}: trait-level checkpoint {subject!r} has no traits.yaml entry"
            )
            continue
        if not event.source.sha:
            errors.append(f"{event.id}: trait-level checkpoint {subject!r} has no sha")
        elif not _same_sha(entry.reviewed_sha, event.source.sha):
            errors.append(
                f"{event.id}: traits.yaml reviewed_sha disagrees with the checkpoint"
            )
        if not event.source.tree_hash:
            errors.append(
                f"{event.id}: trait-level checkpoint {subject!r} has no tree_hash"
            )
        elif entry.tree_hash != event.source.tree_hash:
            errors.append(
                f"{event.id}: traits.yaml tree_hash disagrees with the checkpoint"
            )
        for tid in entry.traits:
            if tid not in trait_rulings:
                errors.append(
                    f"{event.id}: trait {tid!r} in {subject!r} has no effective ruling"
                )

    # Retirement — a subject introduced (its first event dated) on or after a
    # trait's retirement may not use it, in any of its events; a subject whose
    # first event predates retirement continues (§1, review r1 #9, r2 #2).
    first_event: dict[str, Event] = {}
    for event in events:
        first_event.setdefault(event.subject, event)
    for event in events:
        tid = _trait_slug(event.subject)
        d = definitions.get(tid) if tid else None
        if not (d and d.retired):
            continue
        first = first_event[event.subject]
        introduced = first.date
        if date_cls.fromisoformat(introduced) >= date_cls.fromisoformat(d.retired.date):
            errors.append(
                f"{event.id}: new subject {event.subject!r} (introduced "
                f"{introduced}) uses trait {tid!r}, retired {d.retired.date}"
            )

    # Pending completion — a delivered adopt whose subject's effective event, in
    # the history preceding it, is a pending adopt must supersede that pending
    # event and copy its source (§5, review r1 #4, r2 #1).
    for idx, event in enumerate(events):
        if event.kind != "adopt" or event.pending or "#" not in event.subject:
            continue
        prior = effective_by_subject(live_events(events[:idx])).get(event.subject)
        if prior is None or prior.kind != "adopt" or not prior.pending:
            continue
        if prior.id not in event.supersedes:
            errors.append(
                f"{event.id}: completing adopt of {event.subject!r} must supersede "
                f"pending {prior.id}"
            )
        if prior.source != event.source:
            errors.append(
                f"{event.id}: completing adopt of {event.subject!r} must copy "
                f"`source` from pending {prior.id}"
            )

    # Membership — every effective trait ruling names a trait listed (or removed)
    # in its upstream entry; an adopt targets a skill or `doc:`; a modified
    # adoption resolves its `distinct_from`; a fulfilled pending adopt errors.
    for subject, event in current.items():
        if not _is_trait_subject(subject):
            continue
        base = _trait_base(subject)
        tid = _trait_slug(subject) or ""
        entry = upstream_traits.get(base)
        if entry is None:
            errors.append(
                f"{event.id}: trait ruling {subject!r} has no traits.yaml entry"
            )
        elif tid not in entry.traits and tid not in entry.removed:
            errors.append(
                f"{event.id}: trait {tid!r} is not listed in traits.yaml entry {base!r}"
            )
        if (
            event.kind == "adopt"
            and event.skill
            and ":" in event.skill
            and not event.skill.startswith("doc:")
        ):
            errors.append(
                f"{event.id}: trait adopt targets {event.skill!r}; a trait lands in "
                f"a skill or a `doc:` file"
            )
        if event.kind == "adopt" and event.into and event.into != tid:
            into_def = definitions.get(event.into)
            if into_def is None or tid not in into_def.distinct_from:
                errors.append(
                    f"{event.id}: modified adoption into {event.into!r} must name "
                    f"{tid!r} in its distinct_from"
                )
        if event.kind == "adopt" and event.pending and event.skill:
            dest = event.skill
            if ":" not in dest:
                survivor = resolve_skill(dest, forward)
                target_tid = event.into or tid
                oentry = ours_traits.get(survivor)
                if oentry and target_tid in oentry.traits:
                    errors.append(
                        f"{event.id}: pending adopt of {subject!r} but {survivor!r} "
                        f"already lists {target_tid!r} (fulfilled: record the "
                        f"completing adopt)"
                    )

    # (C) Every adoption we still provide (last delivered adopt, not withdrawn)
    # must be listed by an active target skill in traits.yaml — independently of
    # the trait's current upstream ruling (review #5, #6), per resolved target.
    for (subject, _dest), adopt in retained_adoptions(events, forward).items():
        dest = adopt.skill
        if not dest or ":" in dest:
            continue
        survivor = resolve_skill(dest, forward)
        if (subject, survivor) in withdrawn or survivor in retired:
            continue
        tid = adopt.into or _trait_slug(subject) or ""
        oentry = ours_traits.get(survivor)
        if oentry is None:
            errors.append(
                f"{adopt.id}: target skill {survivor!r} has no traits.yaml entry"
            )
            continue
        if not _trait_satisfied(tid, set(oentry.traits), definitions):
            errors.append(
                f"{adopt.id}: trait {tid!r} is not listed by skill {survivor!r}"
            )
        want_hash = tree_hashes.get(survivor)
        if want_hash is not None and oentry.tree_hash != want_hash:
            errors.append(f"{adopt.id}: target skill {survivor!r} tree_hash is stale")
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
