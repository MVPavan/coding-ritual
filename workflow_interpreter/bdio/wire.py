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

import hashlib
import json
from typing import Final, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    field_validator,
    model_validator,
)

from workflow_interpreter.bdio.carriers import (
    TERMINAL_LIFECYCLES,
    WIRE_MODEL,
    ArtifactIdentity,
    BoundSetting,
    Breaker,
    CommitOid,
    ConfigSource,
    Deviation,
    Evidence,
    ExitRecord,
    GateReason,
    GateState,
    InputBinding,
    InstanceInput,
    IssueType,
    JsonSafeInt,
    Lifecycle,
    Metadata,
    MintReason,
    NodeSetting,
    ProcessHandle,
    ResolvedSetting,
    ScopedBound,
    Usage,
    VerifyOutcome,
    WfKind,
    parse_bound_key,
    resolved_settings,
)
from workflow_interpreter.bdio.constants import (
    _MSG_BOTH_PREDECESSORS,
    _MSG_ENTRY_PREDECESSOR,
)
from workflow_interpreter.bdio.errors import CarrierIntegrityError
from workflow_interpreter.schema.decisions import (
    BoundaryIdentity,
    CoordinationLink,
    CoordinationState,
    DecisionTemplate,
)
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
    "WIRE_MODEL",
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
    "InstanceInput",
    "IssueType",
    "JsonSafeInt",
    "Lifecycle",
    "Metadata",
    "MintReason",
    "MintRequest",
    "NodeSetting",
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
    "config_signature",
    "metadata_dict",
    "parse_bound_key",
    "resolved_settings",
]

ROW_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="ignore", arbitrary_types_allowed=False
)
"""bd owns the row shape and adds fields between versions; we read our subset."""

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
KEY_TERMINAL: Final[str] = "terminal"
KEY_LIFECYCLE: Final[str] = "lifecycle"
"""The one key EVERY §5.1 transition owns, and therefore the one key a losing
race can still drag backwards (`transitions.py`)."""

CANON_EVENT_PAYLOAD: Final[str] = "wf-event-payload/1"
CANON_GATE_PAYLOAD: Final[str] = "wf-gate-payload/1"

_MSG_GATE_FIELDS: Final[str] = (
    "a {reason} gate needs {fields} to derive its §3.4 key; a gate key built "
    "from defaults would collide with an unrelated gate"
)
_MSG_MUTABLE_FIELDS: Final[str] = (
    "a binds={binds} gate needs artifact_ref and artifact_digest: the wrapper "
    "re-hashes the document itself at close (§9)"
)


def metadata_dict(model: BaseModel) -> Metadata:
    """A carrier as the JSON object bd stores (aliases applied, nulls elided).

    Nulls are elided because bd merges metadata on write: an absent key means
    "unchanged", so a model can only ever add or overwrite fields, never clear
    one. Nothing in §3 ever needs to clear a recorded fact.
    """
    dumped: Metadata = model.model_dump(mode="json", by_alias=True, exclude_none=True)
    return dumped


def config_signature(settings: tuple[ResolvedSetting, ...]) -> str:
    """Return the typed, order-independent signature of resolved config.

    Canonical JSON retains value type: the old `str()` hash collapsed `1` and
    `"1"`, making distinct pinned resolutions look identical.
    """

    entries: list[list[JsonValue]] = [
        [setting.key, setting.value, setting.source.value] for setting in settings
    ]
    return hashlib.sha256(
        canonical_json_bytes(sorted(entries, key=canonical_json_bytes))
    ).hexdigest()


# --- bd row -------------------------------------------------------------


class BeadRecord(BaseModel):
    """One bd row as `--json` returns it (the subset the wrapper reads)."""

    model_config = ROW_MODEL

    id: str
    title: str
    description: str | None = None
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
    parent: str | None = None


# --- shared value objects -----------------------------------------------


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
    instance_inputs: tuple[InstanceInput, ...] = ()
    essential_inputs: tuple[str, ...] | None = None
    essential_consumers: dict[str, tuple[str, ...]] | None = None
    coordination: CoordinationLink | None = None
    coordination_state: CoordinationState | None = None
    decision_boundary: BoundaryIdentity | None = None
    decision_templates: dict[str, DecisionTemplate] | None = None
    config_signature: str | None = None
    allow_test_flags: bool = False
    instance_base_commit: str | None = None
    superseded_by: str | None = None
    """Set on the loser of a concurrent create under one `instance_key`; the
    surviving root is the lowest bead id (same rule as §3.2 race residue)."""
    terminal: str | None = None
    """The terminal node this instance reached, written once when routing
    enters it (`WorkflowStore.settle_root`). Deliberately OUTSIDE
    `config_signature` and the `_assert_same_instance` comparisons in
    `roots.py`: an instance's identity is its pinned graph plus its
    creation-time resolution, so recording where it ENDED must not change the
    hash a signed §9 payload and root re-creation recovery compare against."""

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
    predecessor_gate_id: str | None = None
    outcome_taken: Outcome | None = None
    """The predecessor's recorded close outcome — the edge this mint took.
    Derived from the predecessor bead, never from the caller (§3.2)."""
    idempotency_key: str
    mint_reason: MintReason
    inputs: tuple[InputBinding, ...] = ()
    envelope: dict[str, JsonValue] | None = None
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
    """Mutable document ref, or immutable artifact commit OID.

    Never the digest source itself — the wrapper hashes the bytes.
    """
    artifact_digest: str | None = None
    """Mutable document SHA-256, or immutable artifact tree OID."""
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
    origin: Literal["activation", "gate"] = "activation"
    via_gate_id: str | None = None


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
    predecessor_gate_id: str | None = None
    runner_profile: str
    model: str
    session_id: str
    inputs: tuple[InputBinding, ...] = ()
    deviations: tuple[Deviation, ...] = ()

    @model_validator(mode="after")
    def _validate_predecessors(self) -> MintRequest:
        """Keep entry and successor predecessor shapes unambiguous."""
        if self.mint_reason is MintReason.ENTRY:
            predecessor = self.predecessor_activation_id or self.predecessor_gate_id
            if predecessor is not None:
                raise CarrierIntegrityError(
                    _MSG_ENTRY_PREDECESSOR.format(predecessor=predecessor)
                )
        elif (
            self.predecessor_activation_id is not None
            and self.predecessor_gate_id is not None
        ):
            raise CarrierIntegrityError(_MSG_BOTH_PREDECESSORS)
        return self


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
