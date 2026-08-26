"""Frozen carriers for every bd row the interpreter writes (§3).

One model per `wf_kind`, plus the bd row shape itself (`BeadRecord`). These
models are the ONLY thing serialized into bd metadata: `metadata_dict` dumps
them in JSON mode so the value written and the value read back are comparable
without a second conversion step, which is what makes the read-back
verification in `client.py` a real check rather than a type-coercion dance.

Outcome vocabularies are imported from the phase-1 schema models, never
re-declared — the closed enum has exactly one definition.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum
from typing import Annotated, Final

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    field_validator,
    model_validator,
)

from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.schema.loader import canonical_json_bytes
from workflow_interpreter.schema.models import (
    GRAPH_OUTCOMES,
    SYSTEM_OUTCOMES,
    BindsMode,
    GateType,
    Outcome,
)

__all__ = [
    "GRAPH_OUTCOMES",
    "SYSTEM_OUTCOMES",
    "ActivationMetadata",
    "ArtifactIdentity",
    "BeadRecord",
    "BindsMode",
    "BoundSetting",
    "Breaker",
    "CanaryMetadata",
    "ConfigSource",
    "Deviation",
    "EventMetadata",
    "EventPayload",
    "Evidence",
    "ExitRecord",
    "GateMetadata",
    "GateOpenRequest",
    "GateReason",
    "GateState",
    "GateType",
    "InputBinding",
    "IssueType",
    "JsonSafeInt",
    "Lifecycle",
    "Metadata",
    "MintReason",
    "MintRequest",
    "PreconditionRecord",
    "ProcessHandle",
    "ResolvedSetting",
    "RootMetadata",
    "ScopedBound",
    "StaleFlagRecord",
    "Usage",
    "VerifyOutcome",
    "WfKind",
    "canonical_json_bytes",
    "metadata_dict",
    "parse_bound_key",
]

WIRE_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True,
    extra="forbid",
    populate_by_name=True,
    arbitrary_types_allowed=False,
)
"""`extra="forbid"` on read too: an unexpected metadata key on a workflow bead
is tamper evidence (§0), so it fails loud instead of being ignored."""

ROW_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="ignore", arbitrary_types_allowed=False
)
"""bd owns the row shape and adds fields between versions; we read our subset."""

Metadata = dict[str, JsonValue]

JSON_SAFE_INT_LIMIT: Final[int] = 2**53 - 1
"""bd's JSON path runs integers through float64 and rounds silently past this
magnitude (probed). The read-back check in `client.py` catches it after the
fact; this bound refuses it before the write."""

JsonSafeInt = Annotated[int, Field(ge=-JSON_SAFE_INT_LIMIT, le=JSON_SAFE_INT_LIMIT)]
"""Every carrier integer: exactly representable through bd's JSON path."""

COMMIT_OID_PATTERN: Final[str] = r"^[0-9a-f]{40}$"
CommitOid = Annotated[str, StringConstraints(pattern=COMMIT_OID_PATTERN)]
"""A full git object id, lowercase hex. Where §3.2 states a commit it must BE a
commit: `""` used to satisfy the type, and an all-empty carrier then compared
equal to an activation that had nothing recorded at all — so the write that
should have happened was skipped as "already recorded"."""

_MSG_DIRTY_STATE_JSON: Final[str] = (
    "pre_attempt_dirty_state must be the canonical JSON object of a §12 dirty "
    "snapshot; {reason}"
)
_REASON_UNPARSEABLE: Final[str] = "it does not parse as JSON ({error})"
_REASON_NOT_OBJECT: Final[str] = "it parses as {kind}, not an object"
_REASON_NOT_CANONICAL: Final[str] = (
    "it is not canonical (sorted keys, no incidental whitespace) — a value that "
    "re-serializes differently cannot be compared for idempotence"
)

# --- metadata keys the §4 read vocabulary filters on --------------------
KEY_WF_KIND: Final[str] = "wf_kind"
KEY_WF_ROOT_ID: Final[str] = "wf_root_id"
KEY_IDEMPOTENCY_KEY: Final[str] = "idempotency_key"
KEY_GATE_KEY: Final[str] = "gate_key"
KEY_EVENT_KEY: Final[str] = "event_key"
KEY_INSTANCE_KEY: Final[str] = "instance_key"
KEY_SEQ: Final[str] = "seq"
KEY_NONCE: Final[str] = "nonce"
KEY_SUPERSEDED_BY: Final[str] = "superseded_by"
KEY_LIFECYCLE: Final[str] = "lifecycle"
"""The one key EVERY §5.1 transition owns, and therefore the one key a losing
race can still drag backwards (`transitions.py`)."""

CANON_EVENT_PAYLOAD: Final[str] = "wf-event-payload/1"
CANON_GATE_PAYLOAD: Final[str] = "wf-gate-payload/1"

_MSG_GATE_FIELDS: Final[str] = (
    "a {reason} gate needs {fields} to derive its §3.4 key; a gate key built "
    "from defaults would collide with an unrelated gate"
)
_SCOPE_PLACEHOLDER: Final[str] = "{scope}"
_SCOPE_CAPTURE: Final[str] = "([^.]+)"

_MSG_MUTABLE_FIELDS: Final[str] = (
    "a binds={binds} gate needs artifact_ref and artifact_digest: the wrapper "
    "re-hashes the document itself at close (§9)"
)


class IssueType(StrEnum):
    """The bd issue types this wrapper may create — a closed set.

    `event` is native in bd 1.1.0 (probed 2026-08-25); the `types.custom`
    prerequisite §11 assumed does not exist.
    """

    TASK = "task"
    EVENT = "event"


class WfKind(StrEnum):
    """The §3 discriminator carried by every workflow bead."""

    ROOT = "root"
    ACTIVATION = "activation"
    GATE = "gate"
    EVENT = "event"
    CANARY = "canary"


class Lifecycle(StrEnum):
    """§5.1 activation states."""

    MINTED = "minted"
    DISPATCHED = "dispatched"
    EXIT_RECORDED = "exit-recorded"
    EVIDENCE_RECORDED = "evidence-recorded"
    CLOSED = "closed"
    SUPERSEDED = "superseded"


TERMINAL_LIFECYCLES: Final[frozenset[Lifecycle]] = frozenset(
    {Lifecycle.CLOSED, Lifecycle.SUPERSEDED}
)
"""The two §5.1 states nothing is ever written past."""


class GateState(StrEnum):
    """A §3.4 gate bead is open until `close_gate_verified` succeeds."""

    OPEN = "open"
    CLOSED = "closed"


class ConfigSource(StrEnum):
    """§3.1 provenance tag on every resolved setting."""

    GRAPH_DEFAULT = "graph-default"
    PROJECT_CONFIG = "project-config"
    INSTANCE_OVERRIDE = "instance-override"


class MintReason(StrEnum):
    """Why an activation is being minted — selects the §10 predicates.

    `INFRA_RETRY` and `STEER_CONTINUATION` inherit the current `round_no`
    (§10.1) and are capped by `max_infra_retries` / `max_steers` (§10.2).
    """

    ENTRY = "entry"
    EDGE = "edge"
    INFRA_RETRY = "infra-retry"
    STEER_CONTINUATION = "steer-continuation"


class GateReason(StrEnum):
    """Why a gate bead exists — exhaustion and halt gates are keyed differently."""

    TRANSITION = "transition"
    EXHAUSTION = "exhaustion"
    HALT = "halt"


class Breaker(StrEnum):
    """§10.5 wrapper-computed breaker flags recorded as evidence."""

    NO_PROGRESS = "no_progress"


class BoundSetting(StrEnum):
    """Resolved-config keys that override a pinned bound (§3.1, §10.4).

    Dotted scope + field. The spec fixes the provenance tagging but not the
    key syntax; this is the wrapper's convention, applied consistently by
    `bounds.effective_bound`.
    """

    MAX_TOTAL_ACTIVATIONS = "instance.max_total_activations"
    MAX_ENTRIES = "region.{scope}.max_entries"
    MAX_INFRA_RETRIES = "node.{scope}.max_infra_retries"
    MAX_STEERS = "node.{scope}.max_steers"

    def at(self, scope: str = "") -> str:
        """The concrete resolved-config key for this bound at `scope`."""
        return self.value.format(scope=scope)

    @property
    def scoped(self) -> bool:
        """Whether this bound is scoped to a named region or node."""
        return _SCOPE_PLACEHOLDER in self.value


class ScopedBound(BaseModel):
    """A resolved-config bound key decomposed into its setting and scope."""

    model_config = WIRE_MODEL

    setting: BoundSetting
    scope: str = ""


def parse_bound_key(key: str) -> ScopedBound | None:
    """Decompose a resolved-config bound key, or `None` if it is not one.

    §9 restricts a `rebudget` mutation to this closed vocabulary, so an
    unparseable key must be distinguishable from a valid one — never coerced.
    """
    for setting in BoundSetting:
        if not setting.scoped:
            if key == setting.value:
                return ScopedBound(setting=setting)
            continue
        pattern = re.escape(setting.value).replace(
            re.escape(_SCOPE_PLACEHOLDER), _SCOPE_CAPTURE
        )
        match = re.fullmatch(pattern, key)
        if match is not None:
            return ScopedBound(setting=setting, scope=match.group(1))
    return None


def metadata_dict(model: BaseModel) -> Metadata:
    """A carrier as the JSON object bd stores (aliases applied, nulls elided).

    Nulls are elided because bd merges metadata on write: an absent key means
    "unchanged", so a model can only ever add or overwrite fields, never clear
    one. Nothing in §3 ever needs to clear a recorded fact.
    """
    dumped: Metadata = model.model_dump(mode="json", by_alias=True, exclude_none=True)
    return dumped


# --- bd row -------------------------------------------------------------


class BeadRecord(BaseModel):
    """One bd row as `--json` returns it (the subset the wrapper reads)."""

    model_config = ROW_MODEL

    id: str
    title: str
    status: str
    issue_type: str
    metadata: Metadata = Field(default_factory=dict)
    payload: str | None = None
    close_reason: str | None = None
    closed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    ephemeral: bool = False
    wisp_type: str | None = None


# --- shared value objects -----------------------------------------------


class ResolvedSetting(BaseModel):
    """One resolved configuration value with its §3.1 provenance tag."""

    model_config = WIRE_MODEL

    key: str
    value: str | JsonSafeInt | bool
    source: ConfigSource


class InputBinding(BaseModel):
    """An immutable input tuple bound at mint (§2 'Input binding')."""

    model_config = WIRE_MODEL

    name: str
    producer_activation_id: str
    artifact_ref: str
    digest: str


class ProcessHandle(BaseModel):
    """§5.3 handle — boot id and start time defeat PID reuse and reboots."""

    model_config = WIRE_MODEL

    pid: JsonSafeInt
    pgid: JsonSafeInt
    host: str
    host_boot_id: str
    proc_start_time: str
    started_at: str
    log_path: str
    session_id: str


class ExitRecord(BaseModel):
    """The wrapper's mirrored exit record — the §7.1 post-crash observable."""

    model_config = WIRE_MODEL

    exit_code: JsonSafeInt
    ended_at: str
    reason: str


class ArtifactIdentity(BaseModel):
    """§7.4 honest naming: git object ids, recorded as such."""

    model_config = WIRE_MODEL

    commit_oid: str
    tree_oid: str


class VerifyOutcome(BaseModel):
    """One `verify` entry's result, with the §7.3 pinned-source digest."""

    model_config = WIRE_MODEL

    cmd: str
    exit_code: JsonSafeInt
    script_digest: str


class Evidence(BaseModel):
    """Computed, never claimed (§7)."""

    model_config = WIRE_MODEL

    verify: tuple[VerifyOutcome, ...] = ()
    artifact: ArtifactIdentity | None = None
    undeclared_effects: tuple[str, ...] = ()
    breaker: Breaker | None = None
    note: str | None = None


class Usage(BaseModel):
    """Normalized runner usage; `known = False` is legal (§6)."""

    model_config = WIRE_MODEL

    known: bool
    input_tokens: JsonSafeInt | None = None
    output_tokens: JsonSafeInt | None = None
    cost_usd: str | None = None
    """Money as a decimal string: JSON floats are not exact, and bd's JSON
    path silently rounds large numerics (probed)."""


class Deviation(BaseModel):
    """A tier-2 deviation record (§1)."""

    model_config = WIRE_MODEL

    kind: str
    reason: str
    recorded_at: str


def _dirty_state_defect(value: str) -> str | None:
    """Why a `pre_attempt_dirty_state` is unusable, or `None` when it is fine.

    The three ways it can be: not JSON at all, JSON that is not an object, and
    an object whose serialization is not canonical. The last one matters as
    much as the first two — `record_precondition`'s idempotence is a string
    comparison, and two spellings of one snapshot compare unequal forever.
    """
    try:
        parsed = json.loads(value)
    except ValueError as exc:
        return _REASON_UNPARSEABLE.format(error=exc)
    if not isinstance(parsed, dict):
        return _REASON_NOT_OBJECT.format(kind=type(parsed).__name__)
    if canonical_json_bytes(parsed).decode("utf-8") != value:
        return _REASON_NOT_CANONICAL
    return None


class PreconditionRecord(BaseModel):
    """The §3.2 carry-forward trio, proven by the §5.4 precondition.

    Intent-only, like every other request carrier here: the supervisor states
    what it PROVED about the working tree before the child could exec, and
    `record_precondition` is the only thing that writes those three keys.

    Validated rather than trusted, because bd cannot help here: the write is a
    key-scoped merge with no compare-and-set, so a malformed trio would simply
    land and be read back by a LATER activation deriving its base from it.

    - the two commits must be real object ids. `""` used to type-check, which
      made an activation with nothing recorded compare EQUAL to a record of two
      empty strings — the idempotence short-circuit then skipped the write that
      was supposed to happen;
    - the dirty state must be a canonical JSON object, the exact form
      `encode_dirty_state` produces. Anything else either fails to decode at
      reset time or compares unequal to itself across a re-serialization.

    `supervision.py` re-reads the activation and re-checks the lifecycle
    immediately before the write, and writes only these three keys — bd merges
    metadata per key, so a stale carrier can no longer carry a lifecycle or a
    handle backwards with it.
    """

    model_config = WIRE_MODEL

    pre_attempt_commit: CommitOid
    reset_verified_commit: CommitOid
    pre_attempt_dirty_state: str | None = None
    """Canonical JSON of the §12 dirty snapshot; `None` in worktree mode."""

    @field_validator("pre_attempt_dirty_state")
    @classmethod
    def _canonical_dirty_state(cls, value: str | None) -> str | None:
        """Refuse a dirty state that is not the canonical JSON object it claims."""
        reason = None if value is None else _dirty_state_defect(value)
        if reason is not None:
            raise ValueError(_MSG_DIRTY_STATE_JSON.format(reason=reason))
        return value


class StaleFlagRecord(BaseModel):
    """The §8.2 stale flag as bd records it — "file AND bd metadata".

    Carries the two timestamps a tier-2 decision reads and nothing else: the
    node's `stale_after` is already in the pinned graph, and a float duration
    would ride bd's JSON float64 path for no gain (see `Usage.cost_usd`).

    Written once. §8.2 keeps the FIRST timestamp on a re-raise, so
    `record_stale_flag` is idempotent by returning the recorded flag rather
    than overwriting it.
    """

    model_config = WIRE_MODEL

    raised_at: str
    last_activity_at: str


# --- wf_kind carriers ---------------------------------------------------


class RootMetadata(BaseModel):
    """§3.1 root bead: the pinned graph body plus resolved config.

    `instance_key` is not named by §3.1; it is the wrapper's idempotency
    handle for root creation, so a crash between the create and the
    self-id write cannot produce a second instance (see `WorkflowStore.
    create_root`).
    """

    model_config = WIRE_MODEL

    wf_kind: WfKind = WfKind.ROOT
    wf_root_id: str | None = None
    instance_key: str
    graph_id: str
    graph_version: str
    graph_content_hash: str
    graph_body: str
    resolved_config: tuple[ResolvedSetting, ...] = ()
    """The §3.1 resolution this instance was CREATED with, and the only one it
    ever has: no root-config write happens after create. A §10.4 rebudget
    records its raise on the GATE bead that carried the approval, so two
    concurrent rebudgets cannot clobber each other through one whole-object
    root write (probed, phase-2 r3/r4). Bound authority is this config ⊕ the
    closed rebudget gates — `bounds.effective_bound`."""
    seq: JsonSafeInt = 0
    superseded_by: str | None = None
    """Set on the loser of a concurrent create under one `instance_key`; the
    surviving root is the lowest bead id (same rule as §3.2 race residue)."""

    @property
    def is_superseded(self) -> bool:
        """Whether this root lost a concurrent create for its instance key."""
        return self.superseded_by is not None


class ActivationMetadata(BaseModel):
    """§3.2 activation bead across its whole §5.1 lifecycle."""

    model_config = WIRE_MODEL

    wf_kind: WfKind = WfKind.ACTIVATION
    wf_root_id: str
    node: str
    region: str | None = None
    round_no: JsonSafeInt
    seq: JsonSafeInt
    predecessor_activation_id: str | None = None
    outcome_taken: Outcome | None = None
    """The predecessor's recorded close outcome — the edge this mint took.
    Derived from the predecessor bead, never from the caller (§3.2)."""
    idempotency_key: str
    mint_reason: MintReason
    inputs: tuple[InputBinding, ...] = ()
    runner_profile: str
    model: str
    session_id: str
    intended_base_commit: str
    pre_attempt_commit: str | None = None
    """§3.2 carry-forward, written by the phase-3 supervisor: the commit this
    attempt started from. `intended_base_commit` for a later rework mint at
    this node is derived from it, so it must be recorded from the first
    writing activation onward."""
    reset_verified_commit: str | None = None
    pre_attempt_dirty_state: str | None = None
    lifecycle: Lifecycle = Lifecycle.MINTED
    handle: ProcessHandle | None = None
    stale_flag: StaleFlagRecord | None = None
    """§8.2 requires the stale flag in the wrapper dir AND in bd metadata. The
    file alone loses a decision-relevant datum with the `.wf/` cache (§P1)."""
    exit_record: ExitRecord | None = None
    evidence: Evidence | None = None
    outcome: Outcome | None = None
    usage: Usage | None = None
    deviations: tuple[Deviation, ...] = ()
    superseded_by: str | None = None

    @property
    def is_superseded(self) -> bool:
        """Excluded from the frontier and round counting, counted by the ceiling."""
        return self.superseded_by is not None or self.outcome is Outcome.SUPERSEDED

    @property
    def is_settled(self) -> bool:
        """A terminal outcome is RECORDED here, whatever `lifecycle` now says.

        The guard every §5.1 transition refuses on, and deliberately weaker than
        `is_completed`: it counts a superseded activation too, and it does NOT
        require `lifecycle` to be terminal. bd has no compare-and-set, so a
        transition whose merge lands after a concurrent close writes its own
        `lifecycle` over the closed one — leaving `status=closed
        lifecycle=exit-recorded outcome=steered`. Keying the refusals on the
        lifecycle let the next write straight through that row and overwrite the
        outcome a continuation had already been minted from (probed, round 3).
        A recorded outcome is the routing truth; nothing may be written past it.
        """
        return self.outcome is not None or self.lifecycle in TERMINAL_LIFECYCLES

    @property
    def is_completed(self) -> bool:
        """Closed with a recorded, non-superseded outcome — this IS routing truth.

        A completed activation is the one state no later write may contradict:
        its outcome is what the frontier routed on and what a successor's
        `outcome_taken` was derived from (§3.3), so superseding it or closing
        it to a different outcome would rewrite history (probed, phase-2
        review).
        """
        return (
            self.lifecycle is Lifecycle.CLOSED
            and self.outcome is not None
            and not self.is_superseded
        )


class GateMetadata(BaseModel):
    """§3.4 gate bead — a plain bead, never native `bd gate` machinery."""

    model_config = WIRE_MODEL

    wf_kind: WfKind = WfKind.GATE
    wf_root_id: str
    gate_key: str
    gate_node: str
    gate_type: GateType = GateType.HUMAN
    binds: BindsMode = BindsMode.IMMUTABLE
    gate_reason: GateReason = GateReason.TRANSITION
    outcomes: tuple[Outcome, ...]
    source_activation_id: str | None = None
    opening_outcome: Outcome | None = None
    region: str | None = None
    round_no: JsonSafeInt | None = None
    halt_reason: str | None = None
    seq: JsonSafeInt
    state: GateState = GateState.OPEN
    outcome: Outcome | None = None
    verified_fingerprint: str | None = None
    nonce: str | None = None
    payload_digest: str | None = None
    bound_key: str | None = None
    """§10.4: the resolved-config key the closing approval's `bound_mutation`
    raised, written in the SAME `model_copy` as `state`, `outcome` and
    `payload_digest`. The bound therefore lands atomically with the close —
    there is no apply/close window in which the edge is taken without the
    raise, and no window in which the raise exists without the edge."""
    bound_value: JsonSafeInt | None = None
    """§10.4: the raised value. `bounds.effective_bound` takes the max per key
    across the instance's CLOSED rebudget gates, so a concurrent rebudget on a
    different gate bead cannot overwrite this one."""
    resume_hint: str | None = None
    artifact_ref: str | None = None
    """`binds = "mutable"`: what the injected artifact reader re-reads at close
    (§9). Never the digest source itself — the wrapper hashes the bytes."""
    artifact_digest: str | None = None
    """`binds = "mutable"`: the document's sha256 at gate-open (§9)."""
    stale_approval_receipts: tuple[str, ...] = ()


class EventMetadata(BaseModel):
    """§3.3 event bead metadata; the transition itself is the payload."""

    model_config = WIRE_MODEL

    wf_kind: WfKind = WfKind.EVENT
    wf_root_id: str
    event_key: str
    seq: JsonSafeInt


class EventPayload(BaseModel):
    """§3.3 `(from, outcome, to, activation_id, seq, actor)`.

    Written INLINE via `--event-payload`; the `@file` form stores the literal
    string `"@file"` with exit 0 (probed 2026-08-25).
    """

    model_config = WIRE_MODEL

    canon: str = CANON_EVENT_PAYLOAD
    from_node: str = Field(alias="from")
    outcome: Outcome
    to_node: str = Field(alias="to")
    activation_id: str
    seq: JsonSafeInt
    actor: str


class CanaryMetadata(BaseModel):
    """The one permitted decision-irrelevant wisp (§3.4, §11)."""

    model_config = WIRE_MODEL

    wf_kind: WfKind = WfKind.CANARY
    nonce: str
    probe: tuple[JsonSafeInt, ...]


# --- request objects ----------------------------------------------------


class MintRequest(BaseModel):
    """The INTENT of a mint: which node, why, and from which predecessor.

    Every fact the store can derive is absent by construction — `region` from
    the pinned graph, `round_no` and `intended_base_commit` from the recorded
    activations, `outcome_taken` from the predecessor's recorded close, bounds
    from the root's pinned body and resolved config (§3.1, §3.2). A caller
    that could state those could label an infra retry an `edge` mint and dodge
    its cap (probed, phase-2 review); it no longer can.
    """

    model_config = WIRE_MODEL

    node: str
    mint_reason: MintReason
    predecessor_activation_id: str | None = None
    runner_profile: str
    model: str
    session_id: str
    inputs: tuple[InputBinding, ...] = ()
    deviations: tuple[Deviation, ...] = ()


class GateOpenRequest(BaseModel):
    """Everything `open_gate` needs; the key is derived, never supplied.

    The key derivation is fail-closed: a gate reason whose key parts are
    missing is refused here rather than hashed from defaults, which would make
    two unrelated gates share one key (§3.4).
    """

    model_config = WIRE_MODEL

    gate_node: str
    outcomes: tuple[Outcome, ...]
    gate_reason: GateReason = GateReason.TRANSITION
    gate_type: GateType = GateType.HUMAN
    binds: BindsMode = BindsMode.IMMUTABLE
    source_activation_id: str | None = None
    opening_outcome: Outcome | None = None
    region: str | None = None
    round_no: JsonSafeInt | None = None
    resume_hint: str | None = None
    artifact_ref: str | None = None
    artifact_digest: str | None = None
    halt_reason: str | None = None

    @model_validator(mode="after")
    def _assert_key_parts(self) -> GateOpenRequest:
        """Refuse a request whose `gate_reason` cannot produce a distinct key."""
        required: tuple[tuple[str, object], ...]
        if self.gate_reason is GateReason.EXHAUSTION:
            required = (("region", self.region), ("round_no", self.round_no))
        elif self.gate_reason is GateReason.HALT:
            # A halt gate is keyed on the root and an ORDINAL (§10.3):
            # `halt_reason` is descriptive metadata, never a key part. Keying
            # on it made the ceiling-exempt mint unbounded — one exempt gate
            # per distinct caller string (probed, phase-2 review). Metadata is
            # not the same as optional, though: the §10.6 sweep reports WHY an
            # instance halted, and an unexplained halt is a dead end for the
            # human who has to resolve it.
            required = (("halt_reason", self.halt_reason),)
        else:
            required = (
                ("source_activation_id", self.source_activation_id),
                ("opening_outcome", self.opening_outcome),
            )
        missing = [name for name, value in required if not value]
        if missing:
            raise CarrierIntegrityError(
                _MSG_GATE_FIELDS.format(
                    reason=self.gate_reason.value, fields=", ".join(missing)
                )
            )
        if self.binds is BindsMode.MUTABLE and not (
            self.artifact_ref and self.artifact_digest
        ):
            raise CarrierIntegrityError(
                _MSG_MUTABLE_FIELDS.format(binds=self.binds.value)
            )
        return self
