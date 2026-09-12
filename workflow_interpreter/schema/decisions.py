"""Identity-bound decision and member-admission records, independent of I/O."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from workflow_interpreter.schema.models import (
    CoordinationLimits,
    DecisionAction,
    DecisionPolicy,
    DecisionTrigger,
    GraphDefinition,
)


class Record(BaseModel):
    """Frozen strict carrier; unknown authority fields are refused."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class CoordinationError(ValueError):
    """Coordination cannot safely progress."""


def digest_record(record: BaseModel) -> str:
    """Stable identity hash over a complete typed record."""
    return hashlib.sha256(
        json.dumps(
            record.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode()
    ).hexdigest()


class CoordinationLink(Record):
    owner_id: str
    slot: str
    generation: int = Field(ge=0)
    reservation_id: str
    ceiling: int = Field(gt=0)
    predecessor_id: str | None = None
    request_id: str | None = None


class MemberCapacity(Record):
    ceiling: int = Field(gt=0)
    kind: Literal["work", "decision", "replacement", "child"]


class MemberAdmission(Record):
    """Everything needed to repair create_root after a crash."""

    graph_body: str
    config_json: str
    inputs_json: str = "[]"
    base_commit: str
    slot: str
    generation: int = Field(ge=0)
    essential_inputs: tuple[str, ...] = ()
    essential_consumers: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    predecessor_id: str | None = None
    request_id: str | None = None
    templates: dict[str, "DecisionTemplate"] = Field(default_factory=dict)


class DecisionTemplate(Record):
    graph_body: str
    config_json: str


class Reservation(Record):
    reservation_id: str
    capacity: MemberCapacity
    admission: MemberAdmission
    root_id: str | None = None


class MemberReceipt(Record):
    root_id: str
    link: CoordinationLink


class BoundaryIdentity(Record):
    owner_id: str
    root_id: str
    generation: int
    graph_hash: str
    config_signature: str | None
    source_activation_id: str
    kind: DecisionTrigger
    route_digest: str
    artifact_commit: str
    artifact_tree: str
    policy_digest: str


class DecisionResponse(Record):
    version: Literal[1]
    request_id: str
    request_digest: str
    parent_generation: int
    artifact_digest: str
    producing_root_id: str
    producing_activation_id: str
    action: DecisionAction
    rationale: str = Field(min_length=1, max_length=2048)
    revision: str | None = Field(default=None, max_length=8192)


class DecisionRequest(Record):
    request_id: str
    boundary: BoundaryIdentity
    actions: tuple[DecisionAction, ...]
    decision_key: str
    state: Literal[
        "requested",
        "admitted",
        "awaiting_output",
        "consumed",
        "applied",
        "human_attention",
        "invalidated",
    ] = "requested"
    decision_root_id: str | None = None
    attempt_id: str | None = None
    response: DecisionResponse | None = None
    response_digest: str | None = None
    replacement_id: str | None = None
    rejected_output_tree: str | None = None
    envelope_reference: str | None = None
    envelope_sha256: str | None = None
    reserved_capacity_snapshot: int = 0
    reason: str | None = None


class DecisionConsumption(Record):
    request_id: str
    response_digest: str
    action: DecisionAction
    applied: bool
    replacement_id: str | None = None


class CancellationReceipt(Record):
    request_key: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=2048)
    state: Literal["cancel_pending", "cancelled"] = "cancel_pending"
    evidence: tuple[str, ...] = ()


class CollectedChildResult(Record):
    root_id: str
    slot: str
    generation: int
    terminal: str
    activation_id: str
    graph_hash: str
    config_signature: str | None
    base_commit: str
    outputs_ref: str
    outputs_commit: str
    outputs_tree: str
    artifact_commit: str
    artifact_tree: str
    artifact_source: Literal["computed-output", "activation-input"]
    evidence_digest: str
    receipt_digest: str = ""


class ChildRecord(Record):
    root_id: str
    slot: str
    generation: int = 0
    wrapper_root: str
    state: Literal[
        "admitted", "running", "settled", "collected", "cancel_pending", "cancelled"
    ] = "admitted"
    activation_id: str | None = None
    process_reference: str | None = None
    session_id: str | None = None
    pid: int | None = None
    proc_start_time: str | None = None
    terminal: str | None = None
    outcome: str | None = None
    evidence_reference: str | None = None
    attention: str | None = Field(default=None, max_length=2048)
    attention_source: Literal["runtime", "decision"] | None = None
    cancellation: CancellationReceipt | None = None
    collection: CollectedChildResult | None = None


class ChildCoordinationView(Record):
    owner_id: str
    reserved_activation_capacity: int
    reserved_decision_attempt_capacity: int
    children: tuple[ChildRecord, ...]
    timed_out: bool = False
    contended_slots: tuple[str, ...] = ()


class IntegrationRequest(Record):
    owner_id: str
    epic_id: str
    stage_id: str
    request_key: str = Field(min_length=1, max_length=128)
    sources: tuple[tuple[str, int, str], ...] = Field(min_length=1)


class IntegrationAssociation(Record):
    request: IntegrationRequest
    request_digest: str
    target_key: str
    target_ref: str
    base_commit: str
    admission: MemberAdmission
    admission_digest: str
    manifest_digest: str
    verification_policy_json: str
    attempt: int
    previous_attempts: tuple[str, ...] = ()
    predecessor_digest: str | None = Field(default=None, exclude_if=lambda v: v is None)
    state: Literal[
        "prepared", "root_bound", "admitted", "landing_authorized", "landed", "stale"
    ] = "prepared"
    receipt: MemberReceipt | None = Field(default=None, exclude_if=lambda v: v is None)
    bridge_digest: str | None = Field(default=None, exclude_if=lambda v: v is None)
    authorization: str | None = Field(default=None, exclude_if=lambda v: v is None)
    candidate_commit: str | None = Field(default=None, exclude_if=lambda v: v is None)
    candidate_tree: str | None = Field(default=None, exclude_if=lambda v: v is None)

    @property
    def identity_digest(self) -> str:
        # Lifecycle evidence is appended; source/admission identity never changes.
        return digest_record(
            self.model_copy(
                update={
                    "state": "prepared",
                    "receipt": None,
                    "bridge_digest": None,
                    "authorization": None,
                    "candidate_commit": None,
                    "candidate_tree": None,
                }
            )
        )


class IntegrationTargetClaim(Record):
    key: str
    owner_id: str
    stage_id: str
    request_digest: str
    attempt: int = Field(default=1, ge=1)
    association_digest: str | None = Field(default=None, exclude_if=lambda v: v is None)
    disposition: Literal["active", "released"] = "active"


class CoordinationState(Record):
    owner_id: str
    limits: CoordinationLimits
    reservations: dict[str, Reservation] = Field(default_factory=dict)
    active: dict[str, str] = Field(default_factory=dict)
    children: dict[str, ChildRecord] = Field(default_factory=dict)
    integrations: dict[str, IntegrationAssociation] = Field(default_factory=dict)
    successors: dict[str, "TrustedReplacementIntent"] = Field(default_factory=dict)
    requests: dict[str, DecisionRequest] = Field(default_factory=dict)
    human_attention: str | None = None


class CoordinationView(Record):
    owner_id: str
    active_root_id: str | None
    reserved_activation_capacity: int
    reserved_decision_attempt_capacity: int
    members: int
    replacements: int
    human_attention: str | None
    requests: tuple[DecisionRequest, ...]


def parse_response(body: str) -> DecisionResponse:
    """Refuse duplicate JSON keys, excessive bytes and unknown fields."""
    if len(body.encode("utf-8")) > 16384:
        raise CoordinationError("decision response exceeds 16384 bytes")

    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise CoordinationError("duplicate response key")
            result[key] = value
        return result

    return DecisionResponse.model_validate(json.loads(body, object_pairs_hook=unique))


def lower_decision(policy: "DecisionPolicy") -> "GraphDefinition":
    """Compile a bounded declaration into the existing graph language."""
    from workflow_interpreter.schema.loader import canonical_bytes, load_pinned_body
    from workflow_interpreter.schema.models import (
        Edge,
        FallbackRoute,
        GraphDocument,
        GraphMeta,
        InstanceBounds,
        IsolationMode,
        Node,
        NodeKind,
        Outcome,
        Source,
    )

    spec = policy.decision_task
    task = Node(
        name="decide",
        kind=NodeKind.TASK,
        runner=spec.runner,
        model=spec.model,
        instructions=spec.instructions,
        writes=False,
        isolation=IsolationMode.WORKTREE,
        allowed_paths=(),
        inputs=("decision_request",),
        verify=spec.verify,
        context_budget_bytes=spec.context_budget_bytes,
        max_wall=spec.max_wall,
        stale_after=spec.stale_after,
        max_infra_retries=spec.max_infra_retries,
        max_steers=spec.max_steers,
        outcomes=(Outcome.NO_DIFF,),
    )
    document = GraphDocument(
        graph=GraphMeta(
            id="bounded-decision",
            version="1.0.0",
            entry="decide",
            description="One ordinary decision task",
        ),
        instance=InstanceBounds(max_total_activations=spec.max_total_activations),
        node=(
            task,
            Node(name="decision_done", kind=NodeKind.TERMINAL),
            Node(name="decision_failed", kind=NodeKind.TERMINAL),
        ),
        edge=(
            Edge.model_validate(
                {"from": "decide", "on": Outcome.NO_DIFF, "to": "decision_done"}
            ),
        ),
        fallback=FallbackRoute(to="decision_failed"),
        source=(
            Source(
                name="decision_request",
                producer="instance",
                optional=False,
                trim_priority=1,
            ),
        ),
    )
    return load_pinned_body(canonical_bytes(document))


class TrustedReplacementRequest(Record):
    request_key: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=2048)
    graph: str
    inputs: dict[str, str] = Field(default_factory=dict)


class TrustedReplacementIntent(Record):
    """Durable successor journal; the saved admission is the replay authority."""

    request_key: str
    request_digest: str
    reason: str
    owner_id: str
    slot: str
    expected_generation: int = Field(ge=0)
    predecessor_id: str
    admission: MemberAdmission
    obligation_digest: str
    decision_id: str | None = None
    predecessor_bridge_json: str | None = None
    successor_bridge_json: str | None = None
    receipt: MemberReceipt | None = None
    state: Literal["prepared", "admitted"] = "prepared"


CoordinationState.model_rebuild()
