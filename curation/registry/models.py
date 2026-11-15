"""Pydantic models of the ledger, skill records and trait files (no I/O)."""

from __future__ import annotations

import re
from datetime import date as date_cls
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from curation.registry.vocab import (
    _SLUG_RE,
    _TRAIT_ID_RE,
    ALL_SUBSTAGES,
    OURS_KINDS,
    PLAYBOOK_KINDS,
    SUBSTAGES,
    TRAIT_DOMAINS,
    TRAIT_KINDS,
)


class StrictModel(BaseModel):
    """Base of every registry model: a wrong type is an error, never coerced
    (`"yes"` is not a bool, `"3"` is not an int), unknown keys are rejected, and
    instances are immutable. Every value the files hold is a JSON/YAML scalar,
    list or mapping already of the declared type (dates are ISO strings)."""

    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)


class Excluded(StrictModel):
    rule: str
    why: str
    count: int = 0


class RoundHeader(StrictModel):
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


class Source(StrictModel):
    repo: str
    logical_id: str
    path: str | None = None
    sha: str | None = None
    content_hash: str | None = None
    # Whole-folder hash for a skill (scan.py §4); None on legacy rulings.
    tree_hash: str | None = None


class Adaptation(StrictModel):
    merged_from: list[str] = Field(default_factory=list)
    modifications: list[str] = Field(default_factory=list)
    deliberately_dropped: list[str] = Field(default_factory=list)


class GuideOverride(StrictModel):
    """The owner keeps an adoption the guide check found in conflict (2.9):
    the ruling that decided it, and its date."""

    ruling: str
    date: str

    @model_validator(mode="after")
    def _check(self) -> GuideOverride:
        if not self.ruling.strip():
            raise ValueError("guide override: `ruling` is empty")
        _require_iso(self.date, "guide override")
        return self


class GuideVerdict(StrictModel):
    verdict: Literal["ok", "reword", "conflict"]
    rules: list[str]
    override: GuideOverride | None = None

    @model_validator(mode="after")
    def _check(self) -> GuideVerdict:
        if self.override is not None and self.verdict != "conflict":
            raise ValueError("a guide override is only for a `conflict` verdict")
        return self

    @property
    def supports_adopt(self) -> bool:
        """`ok`, or a `conflict` the owner overrode."""
        return self.verdict == "ok" or self.override is not None


Stance = Literal["avoid", "reword"]

_RULE_ID_RE = re.compile(r"^[A-Z]+-\d+$")
_DIGEST_RE = re.compile(r"^[0-9a-f]{12}$")


def _check_rules(rules: dict[str, str], where: str) -> None:
    """GUIDE rule IDs mapped to 12-hex digests (stages-design §Trait policy)."""
    for rule, digest in rules.items():
        if not _RULE_ID_RE.fullmatch(rule):
            raise ValueError(f"{where}: {rule!r} is not a GUIDE rule ID")
        if not _DIGEST_RE.fullmatch(digest):
            raise ValueError(f"{where}: {rule} digest {digest!r} is not 12 hex chars")


class PolicyBasis(StrictModel):
    """The trait policy a trait event was recorded under (`policy_basis`)."""

    stance: Stance
    rules: dict[str, str]

    @model_validator(mode="after")
    def _check(self) -> PolicyBasis:
        _check_rules(self.rules, "policy_basis")
        return self


class Event(StrictModel):
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
    # --- decision fields (stages-design Stage 3) ---
    report: str | None = None  # repo-relative path of the cited report (3.2)
    retarget: str | None = None  # why the target is not the row's (3.2)
    rewording: str | None = None  # the wording change of a trait adopt (3.4a)
    # the target's hash when a rewording was pended, or a playbook event's (§4b)
    target_tree_hash: str | None = None
    guide: GuideVerdict | None = None  # a rewording completion's confirmation
    revisit_when: str | None = None  # when a defer is reconsidered (3.5)
    # --- trait policy (stages-design §Trait policy) ---
    override: str | None = None  # why an `avoid` trait is adopted anyway (3.5a)
    policy_basis: PolicyBasis | None = None  # the policy the event was recorded under

    @model_validator(mode="after")
    def _check(self) -> Event:
        _require_iso(self.date, f"event {self.id}")
        self._check_contextual_fields()
        if self.subject.startswith("doc:"):
            self._check_playbook_subject()
        elif self.kind in OURS_KINDS:
            if not self.skill:
                raise ValueError(f"{self.id}: {self.kind} needs a `skill` target")
            if self.skill.startswith("doc:") and self.kind not in {"merge", "rename"}:
                self._check_playbook_subject()
            elif self.kind in {"merge", "rename"}:
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

    def _check_playbook_subject(self) -> None:
        """A playbook is its own subject (§4b); a `rename` names the new path
        in `skill`. Only the shape is checked here: the playbooks folder is
        config, so `record` and `check` decide that a path names a playbook."""
        if self.kind == "rename":
            # subject names the old path; skill names the new one (README §4b)
            new = self.skill or ""
            if not new.startswith("doc:") or new == self.subject:
                raise ValueError(
                    f"{self.id}: rename on a playbook subject: a playbook is renamed "
                    f"only to another `doc:` playbook path, got {self.skill!r}"
                )
        elif self.kind not in PLAYBOOK_KINDS:
            raise ValueError(
                f"{self.id}: {self.kind} on a playbook subject: only "
                f"{sorted(PLAYBOOK_KINDS | {'rename'})}; a playbook has no `retire` yet"
            )
        elif self.subject != self.skill:
            raise ValueError(
                f"{self.id}: a playbook event's subject and skill are the same "
                f"`doc:<path>`, got {self.subject!r} and {self.skill!r}"
            )
        for path in (self.subject, self.skill or ""):
            if path == "doc:" or "#" in path:
                raise ValueError(f"{self.id}: {path!r} is not a playbook path")

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
        for name in (
            "report",
            "retarget",
            "rewording",
            "target_tree_hash",
            "override",
            "revisit_when",
        ):
            value = getattr(self, name)
            if value is not None and not value.strip():
                raise ValueError(f"{self.id}: `{name}` is empty")
        if self.revisit_when is not None and self.kind != "defer":
            raise ValueError(f"{self.id}: `revisit_when` is only for a defer")
        if (self.report is not None or self.retarget is not None) and not trait:
            raise ValueError(
                f"{self.id}: `report`/`retarget` are only for trait events"
            )
        adopt = trait and self.kind == "adopt"
        if self.rewording is not None and not adopt:
            raise ValueError(f"{self.id}: `rewording` is only for a trait adopt")
        if self.override is not None and not adopt:
            raise ValueError(f"{self.id}: `override` is only for a trait adopt")
        if self.policy_basis is not None and not trait:
            raise ValueError(f"{self.id}: `policy_basis` is only for trait events")
        playbook = self.kind in PLAYBOOK_KINDS and self.subject.startswith("doc:")
        if self.target_tree_hash is not None and not (
            playbook or (adopt and self.pending and self.rewording)
        ):
            raise ValueError(
                f"{self.id}: `target_tree_hash` is only for a pending rewording adopt "
                f"or a playbook `add`/`update`"
            )
        if self.guide is not None and not (adopt and self.pending is None):
            raise ValueError(f"{self.id}: `guide` is only for a delivered trait adopt")

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


class Frontmatter(StrictModel):
    skill: str
    domain: str
    stage: str
    substage: str
    secondary: list[str] = Field(default_factory=list)
    family: str | None = None
    aliases: list[str] = Field(default_factory=list)
    status: Literal["active", "retired"] = "active"


def _check_trait_ids(ids: Any, where: str) -> None:
    """Every trait ID is a kebab slug (traits-design Terms, review r1 #5)."""
    for tid in ids:
        if not isinstance(tid, str) or not _TRAIT_ID_RE.fullmatch(tid):
            raise ValueError(f"{where}: {tid!r} is not a kebab-case trait ID")


def _check_secondary(secondary: list[str]) -> None:
    for sub in secondary:
        if sub not in ALL_SUBSTAGES:
            raise ValueError(f"secondary: {sub!r} is not a sub-stage")


class Placement(StrictModel):
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


class Retirement(StrictModel):
    date: str
    replaced_by: list[str]

    @model_validator(mode="after")
    def _check(self) -> Retirement:
        _require_iso(self.date, "retired")
        _check_trait_ids(self.replaced_by, "replaced_by")
        return self


class TraitDefinition(StrictModel):
    """One entry of `trait-definitions.yaml` (traits-design §1)."""

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


class OursTraitEntry(StrictModel):
    """An `ours:<skill>` or `doc:<path>` entry of `traits/ours.yaml` (§2; a
    `doc:` entry's `tree_hash` is over its one file, stages-design 1.4-1.5)."""

    tree_hash: str
    traits: list[str]
    notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> OursTraitEntry:
        _check_trait_ids(self.traits, "traits")
        _check_trait_ids(self.notes, "notes")
        return self


class Analysis(StrictModel):
    """One analysis of an upstream skill at a sha (stages-design §Entries)."""

    tree_hash: str
    placement: Placement
    traits: list[str]
    added: dict[str, str] = Field(default_factory=dict)
    changed: dict[str, str] = Field(default_factory=dict)
    removed: dict[str, str] = Field(default_factory=dict)
    notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check(self) -> Analysis:
        _check_trait_ids(self.traits, "traits")
        for name in ("added", "changed", "removed", "notes"):
            _check_trait_ids(getattr(self, name), name)
        return self


class UpstreamTraitEntry(StrictModel):
    """A `<repo>:<logical_id>` entry of `traits/<repo>.yaml`: analyses keyed by
    sha and two pointers (stages-design §Entries)."""

    accepted: str | None
    proposed: str | None
    analyses: dict[str, Analysis]

    @model_validator(mode="after")
    def _check(self) -> UpstreamTraitEntry:
        if self.accepted is None and self.proposed is None:
            raise ValueError("`accepted` or `proposed` must be set")
        if self.accepted is not None and self.accepted == self.proposed:
            raise ValueError("`accepted` and `proposed` name the same analysis")
        for name in ("accepted", "proposed"):
            sha = getattr(self, name)
            if sha is not None and sha not in self.analyses:
                raise ValueError(f"{name} {sha!r} names no analysis")
        return self

    @property
    def newest_sha(self) -> str:
        """`proposed` when set, else `accepted`."""
        sha = self.proposed or self.accepted
        assert sha is not None
        return sha

    @property
    def newest(self) -> Analysis:
        return self.analyses[self.newest_sha]


class SkillEntry(StrictModel):
    """One `skills.yaml` entry: an `.claude/skills/<name>` folder's placement
    and identity (stages-design §Skills file)."""

    domain: str
    stage: str
    substage: str
    secondary: list[str]
    family: str | None
    aliases: list[str]
    status: Literal["active", "retired"]
    boundary: str | None

    @model_validator(mode="after")
    def _check(self) -> SkillEntry:
        if self.stage not in SUBSTAGES:
            raise ValueError(f"unknown stage {self.stage!r}")
        if self.substage not in SUBSTAGES[self.stage]:
            raise ValueError(f"{self.substage!r} is not a sub-stage of {self.stage}")
        _check_secondary(self.secondary)
        if self.boundary is not None and not self.boundary.strip():
            raise ValueError("boundary is empty")
        return self

    def frontmatter(self, skill: str) -> Frontmatter:
        return Frontmatter(
            skill=skill,
            domain=self.domain,
            stage=self.stage,
            substage=self.substage,
            secondary=list(self.secondary),
            family=self.family,
            aliases=list(self.aliases),
            status=self.status,
        )


class ChangeInfo(StrictModel):
    changed: str  # "yes" | "no" | "unknown"
    diff_cmd: str | None = None
    label: str | None = None


# --- report file (stages-design §Report file) ----------------------------------


class LastCritic(StrictModel):
    """The critic round an acceptance followed; `fail` is a request for
    changes (REVISE)."""

    by: str
    date: str
    verdict: Literal["fail"]

    @model_validator(mode="after")
    def _check(self) -> LastCritic:
        _require_iso(self.date, "last critic")
        return self


class CriticVerdict(StrictModel):
    """`pass`: the critic passed it. `accepted`: after the critic's last round
    failed, `by` accepted the fixes on `date` without a further critic pass;
    `last_critic` records that round."""

    by: str
    date: str
    verdict: Literal["pass", "fail", "accepted"]
    last_critic: LastCritic | None = None

    @model_validator(mode="after")
    def _check(self) -> CriticVerdict:
        _require_iso(self.date, "critic")
        if (self.verdict == "accepted") != (self.last_critic is not None):
            raise ValueError(
                "`last_critic` is set exactly when the verdict is accepted"
            )
        if self.last_critic is not None and self.last_critic.date > self.date:
            raise ValueError("an acceptance cannot predate the critic round it follows")
        return self

    @property
    def clears_seal(self) -> bool:
        return self.verdict in {"pass", "accepted"}


class MappingLine(StrictModel):
    """One blind-extraction line → trait IDs (playbook §4 step 2)."""

    line: int
    to: list[str]
    mark: Literal["match", "split", "new"]

    @model_validator(mode="after")
    def _check(self) -> MappingLine:
        if not self.to:
            raise ValueError(f"mapping line {self.line}: `to` is empty")
        if self.mark == "match" and len(self.to) != 1:
            raise ValueError(f"mapping line {self.line}: a match maps to one trait")
        if self.mark == "split" and len(self.to) < 2:
            raise ValueError(
                f"mapping line {self.line}: a split maps to at least two traits"
            )
        _check_trait_ids(self.to, f"mapping line {self.line}")
        return self


class ReportAnalysis(StrictModel):
    blind: list[str]
    mapping: list[MappingLine]

    @model_validator(mode="after")
    def _check(self) -> ReportAnalysis:
        for item in self.mapping:
            if not 1 <= item.line <= len(self.blind):
                raise ValueError(f"mapping line {item.line} names no blind line")
        return self


class Pairing(StrictModel):
    """The three pairing signals (2.1): computed overlap, placement match and
    suggestion; judged purpose match, flag and reason."""

    overlap: dict[str, int]
    placement_match: list[str]
    suggested: str | None
    purpose_match: str | None
    purpose: str | None
    flag: str | None
    reason: str | None


Holding = Literal["present", "variant"]


class PolicyPrefill(StrictModel):
    """A row's `policy`: the trait's live trait-policy.yaml stance (2.9)."""

    stance: Stance
    rules: list[str]


class ReportRow(StrictModel):
    """One upstream trait's comparison row (2.2-2.9)."""

    scope: Literal["new", "changed", "recompare", "reconsider"]
    change: list[str]
    fact: Literal["present", "variant", "absent"]
    provider: str | None
    candidates: list[str]
    via: str | None
    also_in: dict[str, Holding]
    ours: list[str]
    recommendation: Literal["adopt", "defer", "reject", "out-of-scope"] | None
    delivery: Literal["delivered", "pending"] | None
    target: str | None
    modification: str | None
    rewording: str | None
    revisit_when: str | None
    policy: PolicyPrefill | None  # pre-filled from trait-policy.yaml
    guide: GuideVerdict | None
    reason: str | None

    @model_validator(mode="after")
    def _check(self) -> ReportRow:
        if (self.fact == "absent") != (self.provider is None):
            raise ValueError("`provider` is set exactly when the fact is not absent")
        _check_trait_ids(self.candidates, "candidates")
        return self


class ReportSkill(StrictModel):
    upstream_tree_hash: str
    # The skill's accepted analysis when the skill was drafted (computed).
    accepted: str | None
    compared_with: str
    pairing: Pairing
    analysis: ReportAnalysis
    traits: dict[str, ReportRow]

    @model_validator(mode="after")
    def _check(self) -> ReportSkill:
        if self.compared_with.startswith("doc:"):
            raise ValueError("compared_with is a skill or `none`, never a doc:")
        _check_trait_ids(self.traits, "traits")
        return self


class Report(StrictModel):
    """`registry/reviews/<date>-upstream-<harness>-<version>.yaml`."""

    harness: str
    # The harness's previous reviewed pin, set by the author (informational).
    from_sha: str | None = None
    to_sha: str
    supersedes: list[str] | None
    analysis_critic: CriticVerdict | None
    comparison_critic: CriticVerdict | None
    themes: str | None
    skills: dict[str, ReportSkill]

    @property
    def critics_cleared(self) -> bool:
        """Both critic fields are `pass` or `accepted`: ready to seal."""
        return all(
            c is not None and c.clears_seal
            for c in (self.analysis_critic, self.comparison_critic)
        )


# --- trait policy and sharing (stages-design §Trait policy, §Shared traits) -----


class PolicyEntry(StrictModel):
    """One `trait-policy.yaml` entry: a standing stance on a trait."""

    stance: Stance
    rules: dict[str, str]
    why: str
    decided: str
    reviewed: str
    ledger: str
    from_: list[str] = Field(alias="from")
    # On a retired key only: replacement → `carried` or why not.
    reconciled: dict[str, str] | None = None

    @model_validator(mode="after")
    def _check(self) -> PolicyEntry:
        _check_rules(self.rules, "rules")
        _require_iso(self.decided, "decided")
        _require_iso(self.reviewed, "reviewed")
        for name in ("why", "ledger"):
            if not getattr(self, name).strip():
                raise ValueError(f"`{name}` is empty")
        _check_trait_ids(self.from_, "from")
        if self.reconciled is not None:
            _check_trait_ids(self.reconciled, "reconciled")
            for tid, how in self.reconciled.items():
                if not how.strip():
                    raise ValueError(f"reconciled {tid}: empty")
        return self

    def basis(self) -> PolicyBasis:
        return PolicyBasis(stance=self.stance, rules=dict(self.rules))

    def prefill(self) -> PolicyPrefill:
        return PolicyPrefill(stance=self.stance, rules=sorted(self.rules))


class SharingEntry(StrictModel):
    """One `trait-sharing.yaml` entry: why our skills share a trait."""

    skills: list[str]
    why: str
    reviewed: str

    @model_validator(mode="after")
    def _check(self) -> SharingEntry:
        _require_iso(self.reviewed, "reviewed")
        if not self.why.strip():
            raise ValueError("`why` is empty")
        if len(set(self.skills)) != len(self.skills):
            raise ValueError("`skills` lists a holder twice")
        return self
