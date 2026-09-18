"""The typed write API — every bd write in the system goes through here (§0.1).

`WorkflowStore` is the whole surface: one method per §4 command-table row. The
model may read bd freely through `store.reads`; it never emits a bd write
string, because the only write strings that exist are the ones `client.py`
builds from these calls — and the transport's own write methods are
package-private, so "read directly" is not one refactor away from "close a
gate without verifying it".

Three invariants shape almost every method:

- **Append-only.** Nothing is ever deleted or reopened; a losing race is
  superseded, a corrected state is a new bead (§3, §0.1).
- **Metadata first, close second.** A crash between the two leaves an open
  bead whose outcome is already recorded. The other order would leave a
  closed bead with no routing truth — unrecoverable (§5.1, §3.3).
- **Repair forward, never refuse.** Which means the half-finished state above
  is FINISHED on the next call, not reported as a conflict: a lifecycle
  refusal there wedges the bead permanently, since §0.1 leaves no raw bd
  write to fix it with (`finalize.py`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from pydantic import JsonValue

from workflow_interpreter.bdio import (
    bounds,
    gates,
    inspection,
    mint,
    reads,
    rpc_control,
    transitions,
)
from workflow_interpreter.bdio.backend import (
    PinnedBackendFactory,
    StoreBackend,
    StoreBackendFactory,
)
from workflow_interpreter.bdio.bounds import BoundRefusal
from workflow_interpreter.bdio.capabilities import ArtifactReader, BranchHeadReader
from workflow_interpreter.bdio.claims import ClaimStore
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.config import BdConfig, SigningConfig
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.coordination import CoordinationStore
from workflow_interpreter.bdio.errors import (
    BoundExceededError,
    CarrierIntegrityError,
    StoreConfigError,
)
from workflow_interpreter.bdio.mint import MintFacts
from workflow_interpreter.bdio.records import (
    ActivationRecord,
    CanaryResult,
    GateRecord,
    InstanceRecord,
    MintResult,
    RootRecord,
    RowRecord,
)
from workflow_interpreter.bdio.roots import create_root, settle_root
from workflow_interpreter.bdio.rpc_records import (
    ControlRegistration,
    SessionCompletion,
    SessionRegistration,
)
from workflow_interpreter.bdio.signing import GateVerifier
from workflow_interpreter.bdio.wake import append_wake_event
from workflow_interpreter.bdio.wire import (
    ActivationMetadata,
    BoundSetting,
    Deviation,
    EventPayload,
    Evidence,
    ExitRecord,
    GateOpenRequest,
    InstanceInput,
    Lifecycle,
    Metadata,
    MintReason,
    MintRequest,
    NodeSetting,
    PreconditionRecord,
    ProcessHandle,
    ResolvedSetting,
    StaleFlagRecord,
    Usage,
    metadata_dict,
)
from workflow_interpreter.contracts.execution import ExecutionRegistry
from workflow_interpreter.contracts.rpc_control import ControlState
from workflow_interpreter.contracts.run_identity import RunIdentity
from workflow_interpreter.contracts.wake import WakeEvent
from workflow_interpreter.schema.decisions import (
    BoundaryIdentity,
    CoordinationError,
    DecisionRequest,
    DecisionResponse,
)
from workflow_interpreter.schema.models import GraphDefinition, Outcome

if TYPE_CHECKING:
    from workflow_interpreter.foreman.compose import Composition

from workflow_interpreter.bdio import activation_writes
from workflow_interpreter.bdio.activation_writes import (
    _FIELD_CREW_PROFILE,
    _FIELD_MODEL,
    _MSG_NO_VERIFIER,
    _MSG_SUPERSEDE_DEAD_WINNER,
    _MSG_SUPERSEDE_LOSES,
    _MSG_SUPERSEDE_NO_WINNER,
    _assert_pinned_execution_setting,
    _race_decision,
    _race_order,
    pinned_execution_setting,
)


class WorkflowStore:
    """The typed bd write API for one workspace (§0.1 write boundary).

    Capabilities the wrapper must own rather than trust are injected here: the
    §9 gate verifier, the workspace-scoped artifact reader that re-hashes a
    mutable gate document, and the branch-head reader §3.2 resolves
    `intended_base_commit` against. Each is optional, and the operation that
    needs a missing one refuses — it never falls back to a caller's word.
    """

    def __init__(
        self,
        client: StoreBackend,
        verifier: GateVerifier | None = None,
        *,
        artifact_reader: ArtifactReader | None = None,
        branch_head_reader: BranchHeadReader | None = None,
        member_band: object | None = None,
        backend_factory: StoreBackendFactory | None = None,
        claims_backend: StoreBackend | None = None,
    ) -> None:
        self._member_band = member_band
        self._client = client
        self._claims_backend = claims_backend
        self._verifier = verifier
        self._artifact_reader = artifact_reader
        self._branch_head_reader = branch_head_reader
        self._backend_factory: StoreBackendFactory = (
            PinnedBackendFactory(client) if backend_factory is None else backend_factory
        )
        self._reads = reads.WorkflowReads(client)

    @classmethod
    def from_config(
        cls,
        config: BdConfig,
        signing: SigningConfig | None = None,
        *,
        artifact_reader: ArtifactReader | None = None,
        branch_head_reader: BranchHeadReader | None = None,
        backend_factory: StoreBackendFactory | None = None,
        claims_backend: StoreBackend | None = None,
    ) -> WorkflowStore:
        """Build a store from configuration alone — the supported entry point.

        The transport stays sealed: `BdClient` is not exported (§0.1), so a
        caller with a `BdConfig` and a `SigningConfig` had no way to construct
        a store without reaching into the package. It has one now, and it is
        the only one.

        The backend comes from the factory, not from a constructor call here:
        a root is pinned to its backend (§3.2), so which transport a store is
        built on has to be somebody else's answer.
        """
        factory: StoreBackendFactory = (
            PinnedBackendFactory(BdClient(config))
            if backend_factory is None
            else backend_factory
        )
        verifier = None if signing is None else GateVerifier(signing, config.workspace)
        return cls(
            factory(BackendKind.BD),
            verifier,
            artifact_reader=artifact_reader,
            branch_head_reader=branch_head_reader,
            backend_factory=factory,
            claims_backend=claims_backend,
        )

    def for_root(
        self,
        *,
        branch_head_reader: BranchHeadReader,
        member_band: object | None = None,
        backend: BackendKind | None = None,
    ) -> WorkflowStore:
        """Derive a root-scoped store without replacing injected capabilities.

        The verifier and artifact reader are process-scoped authority. A root
        contributes its branch-head reader and its pinned backend: the backend
        is immutable per root (§3.2), so the store a root is served by comes
        from the factory rather than from whichever transport the caller
        happened to hold.
        """
        return WorkflowStore(
            self._backend_factory(self._client.kind if backend is None else backend),
            self._verifier,
            artifact_reader=self._artifact_reader,
            branch_head_reader=branch_head_reader,
            member_band=member_band,
            backend_factory=self._backend_factory,
            claims_backend=self._claims_backend,
        )

    @property
    def reads(self) -> reads.WorkflowReads:
        """The §4 read vocabulary — the only bd handle this store hands out."""
        return self._reads

    # -- §11 startup canary ----------------------------------------------

    def startup_canary(self) -> CanaryResult:
        """Assert the pinned backend and round-trip a carrier (§11)."""
        return self._client.probe()

    # -- roots -----------------------------------------------------------

    def create_root(
        self,
        *,
        instance_key: str,
        definition: GraphDefinition,
        resolved_config: Sequence[ResolvedSetting],
        instance_inputs: Sequence[InstanceInput] = (),
        allow_test_flags: bool = False,
        instance_base_commit: str | None = None,
        run_identity: RunIdentity | None = None,
        profiles: ExecutionRegistry | None = None,
    ) -> RootRecord:
        """Pin a graph into bd as a new instance (§3.1), idempotently by key."""
        return create_root(
            self._client,
            instance_key=instance_key,
            definition=definition,
            resolved_config=resolved_config,
            instance_inputs=instance_inputs,
            allow_test_flags=allow_test_flags,
            instance_base_commit=instance_base_commit,
            run_identity=run_identity,
            profiles=profiles,
        )

    def settle_root(self, root_id: str, terminal: str) -> RootRecord:
        """Record the terminal an instance reached and close its root (§3.1).

        The only durable statement that an instance is OVER: the tick log and
        the trace events say which edge was taken, but nothing said "this
        instance is settled" where `status` or a human could read it, so the
        root bead stayed open forever (cr-o85.34.24). Idempotent — a re-tick
        after the terminal rewrites nothing.
        """
        return settle_root(self._client, root_id, terminal)

    # -- activations -----------------------------------------------------

    @property
    def claims(self) -> ClaimStore:
        """The integration-target claim surface (§3.2 shared serialisation).

        Served by an injected backend when one was given (D20): claims stay
        bd-backed while `store` can still select bd, because two backends
        discovering claims in two stores could not see each other's
        reservations. A ledger-backed run therefore reads and writes its
        claims through the SAME bd rows a bd-backed run does.
        """
        return ClaimStore(
            self._client if self._claims_backend is None else self._claims_backend
        )

    def coordination_store(
        self,
        *,
        verify_decision: Callable[[DecisionRequest], DecisionResponse] | None = None,
        composition: Composition | None = None,
    ) -> CoordinationStore:
        """Durable admission/consumption operations, distinct from local lifecycle."""
        return CoordinationStore(self._client, verify_decision, composition=composition)

    def assert_member(self, root_id: str) -> None:
        """Validate opt-in membership and the local single-flight capability."""
        root = self._reads.load_root(root_id)
        coordinator = self.coordination_store()
        coordinator.validate_member(root)
        coordinator.assert_child_progress(root)
        if root.metadata.coordination is not None:
            state = coordinator.state(root.metadata.coordination.owner_id)
            child = state.children.get(root.metadata.coordination.slot)
            reservation = state.reservations.get(
                root.metadata.coordination.reservation_id
            )
            if reservation is not None and reservation.capacity.kind == "child":
                if child is None:
                    raise CoordinationError("child admission incomplete")
                if child.cancellation is not None:
                    raise CoordinationError("child cancellation fences dispatch")
                if child.collection is not None:
                    raise CoordinationError("collected child cannot dispatch")
            if state.human_attention:
                raise CoordinationError("owner requires human attention")
            boundary = root.metadata.decision_boundary
            if boundary is not None:
                from workflow_interpreter.schema.decisions import digest_record

                request = state.requests.get(digest_record(boundary))
                if (
                    request is None
                    or request.state != "applied"
                    or request.response is None
                    or request.response.action != "continue_declared"
                ):
                    raise CoordinationError(
                        "decision boundary blocks ordinary dispatch"
                    )
        if root.metadata.coordination is not None and not getattr(
            self._member_band, "held", False
        ):
            raise CoordinationError("coordinated mutation requires the member band")

    def queue_decision(self, root_id: str, boundary: BoundaryIdentity) -> None:
        """Persist boundary under the member band; owner reconciliation runs later."""
        self.assert_member(root_id)
        self._client._merge_metadata(
            root_id, {"decision_boundary": metadata_dict(boundary)}
        )

    def mint_activation(self, root_id: str, request: MintRequest) -> MintResult:
        """Mint an activation, or re-find the one this key already minted (§3.2).

        Every fact the bounds and the identity key are computed from is DERIVED
        from the pinned graph and the recorded trace (`mint.py`); the request
        carries intent only.

        Order is load-bearing: natural-key lookup FIRST, bounds SECOND, create
        LAST. Checking bounds before the lookup would let a full ceiling turn a
        crash-recovery re-tick into a refusal for work that already exists.

        After the create, the key is looked up AGAIN. Ticks are single-flight
        (§4), so a duplicate should be impossible; when the lock fails anyway,
        this read-after-write resolves the residue inside the same call instead
        of leaving two live heads until some later tick (§3.2, drill 10).
        `created` then reports whether OUR bead is the surviving one.
        """
        from contextlib import nullcontext

        from workflow_interpreter.inspector.band import BandLock

        coordinator = self.coordination_store()
        root = self._reads.load_root(root_id)
        guard = (
            BandLock(coordinator.member_lock_path(root_id, "launch"))
            if coordinator.child_for_root(root) is not None
            else nullcontext()
        )
        with guard:
            return self._mint_activation(root_id, request)

    def _mint_activation(self, root_id: str, request: MintRequest) -> MintResult:
        """Apply the typed activation write."""
        return activation_writes._mint_activation(self, root_id, request)

    def _preflight_steer_continuation(
        self,
        root_id: str,
        activation: ActivationRecord,
        continuation: MintRequest,
    ) -> None:
        """Check a fresh steer continuation as if its parent were closed `steered`."""
        return activation_writes._preflight_steer_continuation(
            self, root_id, activation, continuation
        )

    def _prepare_mint(
        self,
        root_id: str,
        request: MintRequest,
        root: RootRecord,
        beads: Sequence[InstanceRecord],
        activations: Sequence[ActivationRecord],
    ) -> tuple[
        MintFacts,
        tuple[ActivationRecord, ...],
        ActivationMetadata | None,
        Metadata | None,
    ]:
        """Perform the complete non-mutating portion of ``mint_activation``."""
        return activation_writes._prepare_mint(
            self, root_id, request, root, beads, activations
        )

    def record_envelope(
        self, activation_id: str, envelope: dict[str, JsonValue]
    ) -> None:
        """Persist exact brief accounting before dispatch; replay must agree."""
        current = self._reads.load_activation(activation_id).metadata.envelope
        if current is not None and current != envelope:
            raise CarrierIntegrityError("envelope changed after preparation")
        if current is None:
            self._client._merge_metadata(activation_id, {"envelope": envelope})

    def record_precondition(
        self, activation_id: str, record: PreconditionRecord
    ) -> ActivationRecord:
        """Write the §3.2 carry-forward trio the §5.4 precondition proved.

        Called between the mint and the exec, and durably BEFORE the fork
        barrier releases the child: a crash after the exec must never leave a
        dispatched activation whose `pre_attempt_commit` was never recorded,
        because §3.2 derives a later rework's `intended_base_commit` from it
        and silently falls through to the branch head — which after a reject IS
        the rejected artifact.

        No lifecycle move: the trio is a fact about the tree, not a state
        (`inspection.py` holds the rule, and does its own fresh read so the
        lifecycle check sits as close to the write as bd allows).
        """
        return inspection.record_precondition(
            self._client, self._load_activation, activation_id, record
        )

    def record_stale_flag(
        self, activation_id: str, flag: StaleFlagRecord
    ) -> ActivationRecord:
        """Mirror the §8.2 stale flag into bd; the FIRST raise wins.

        Staleness is a hint for a tier-2 decision, not a verdict, so a re-raise
        must not rewrite when the crew actually went quiet — the recorded
        flag is returned unchanged rather than overwritten (§8.2). Refused
        outright unless the activation is still `dispatched`: the flag is a
        statement about a RUNNING child.
        """
        return inspection.record_stale_flag(
            self._client, self._load_activation, activation_id, flag
        )

    def record_dispatch(
        self, activation_id: str, handle: ProcessHandle, *, launch_id: str | None = None
    ) -> ActivationRecord:
        """Phase B: the state moves only after the handle is durable (§5.2)."""
        return activation_writes.record_dispatch(
            self, activation_id, handle, launch_id=launch_id
        )

    def reserve_in_place_steer(
        self,
        activation_id: str,
        registration: SessionRegistration,
        turn_id: str,
        instructions_digest: str,
    ) -> ControlRegistration:
        """Spend the shared steer cap on an identity-bound RPC intent."""
        self.assert_member(registration.root_id)
        return rpc_control.reserve(
            self._client,
            self._reads,
            activation_id,
            registration,
            turn_id,
            instructions_digest,
        )

    def record_control_state(
        self,
        activation_id: str,
        control: ControlRegistration,
        state: ControlState,
        *,
        resolution_reason: str | None = None,
    ) -> ControlRegistration:
        """Record delivery evidence without creating a routing or approval fact."""
        return rpc_control.record_state(
            self._client, self._reads, activation_id, control, state, resolution_reason
        )

    def record_session_completion(
        self, activation_id: str, completion: SessionCompletion
    ) -> ActivationRecord:
        """Record one correlated successful vendor turn, never process death."""
        return inspection.record_session_completion(
            self._client, self._load_activation, activation_id, completion
        )

    def register_session(
        self, activation_id: str, registration: SessionRegistration
    ) -> ActivationRecord:
        """Register correlated app-server identity before authorizing any turn."""
        return inspection.register_session(
            self._client, self._load_activation, activation_id, registration
        )

    def record_exit(
        self, activation_id: str, exit_record: ExitRecord
    ) -> ActivationRecord:
        """Mirror the wrapper's exit record into bd (§5.3) — the §7.1 observable."""
        return activation_writes.record_exit(self, activation_id, exit_record)

    def record_evidence(
        self,
        activation_id: str,
        evidence: Evidence,
        usage: Usage | None = None,
    ) -> ActivationRecord:
        """Record computed §7 evidence before the outcome is decided."""
        return activation_writes.record_evidence(self, activation_id, evidence, usage)

    def close_activation(
        self,
        activation_id: str,
        outcome: Outcome,
        *,
        evidence: Evidence | None = None,
        usage: Usage | None = None,
        deviations: Sequence[Deviation] = (),
    ) -> ActivationRecord:
        """Close with the outcome that IS the routing truth (§3.3)."""
        return activation_writes.close_activation(
            self,
            activation_id,
            outcome,
            evidence=evidence,
            usage=usage,
            deviations=deviations,
        )

    def supersede_activation(self, loser_id: str, winner_id: str) -> ActivationRecord:
        """Append-only race resolution: never `bd delete`, never reopen (§3.2)."""
        return activation_writes.supersede_activation(self, loser_id, winner_id)

    # -- gates and events ------------------------------------------------

    def open_gate(self, root_id: str, request: GateOpenRequest) -> GateRecord:
        """Open a gate under its deterministic key — a re-tick re-finds it (§3.4)."""
        self.assert_member(root_id)
        return gates.open_gate(self._client, root_id, request)

    def close_gate_verified(
        self,
        root_id: str,
        gate_id: str,
        *,
        payload_bytes: bytes,
        signature: bytes,
    ) -> GateRecord:
        """Take a gate's edge — only after a §9 signature verifies.

        A `binds = "mutable"` gate is re-hashed here through the injected
        artifact reader. There is no parameter by which a caller can state the
        current digest, because a caller-echoed digest is not a re-hash (§9).
        """
        if self._verifier is None:
            raise StoreConfigError(_MSG_NO_VERIFIER)
        return gates.close_gate_verified(
            self._client,
            self._verifier,
            root_id,
            gate_id,
            payload_bytes=payload_bytes,
            signature=signature,
            artifact_reader=self._artifact_reader,
        )

    def append_wake_event(self, root_id: str, event: WakeEvent) -> RowRecord:
        """Append a deduplicated notification, with no activation or gate authority."""
        return append_wake_event(self._client, root_id, event)

    def append_event(
        self, root_id: str, payload: EventPayload, *, seq: int | None = None
    ) -> RowRecord:
        """Append one transition event, idempotently and INLINE (§3.3)."""
        return gates.append_event(self._client, root_id, payload, seq=seq)

    # -- internals -------------------------------------------------------

    def _resolve_race(
        self, found: Sequence[ActivationRecord], key: str
    ) -> ActivationRecord:
        """Apply the §3.2 supersede rule to post-mint duplicates.

        A COMPLETED activation wins outright, whatever its `seq`: it already
        produced the outcome the frontier routed on, and superseding it would
        destroy routing truth to tidy up a duplicate (probed, phase-2 review).
        Two completed duplicates cannot be resolved that way at all, so they
        fail toward triage rather than picking one to erase.

        Otherwise winner = lowest `seq`, tie broken by the lexicographically
        lowest bead id — deterministic, so two ticks racing to resolve the same
        residue pick the same winner and the loser is closed exactly once.
        """
        winner, losers = _race_decision(found, key)
        for loser in losers:
            self.supersede_activation(loser.activation_id, winner.activation_id)
        return self._load_activation(winner.activation_id)

    def _assert_race_winner(self, loser: ActivationRecord, winner_id: str) -> None:
        """§3.2: prove the named winner is one, before anything is destroyed.

        Everything the rule needs comes from ONE query — the key lookup returns
        exactly the activations that raced, so "exists", "same root", "same
        idempotency key" and "wins the tie-break" are all decided against it.
        """
        candidates = self._reads.find_by_idempotency_key(
            loser.metadata.wf_root_id, loser.metadata.idempotency_key
        )
        winner = next(
            (
                record
                for record in candidates
                if record.activation_id == winner_id
                and record.activation_id != loser.activation_id
            ),
            None,
        )
        if winner is None:
            raise CarrierIntegrityError(
                _MSG_SUPERSEDE_NO_WINNER.format(
                    winner=winner_id,
                    activation_id=loser.activation_id,
                    key=loser.metadata.idempotency_key,
                )
            )
        if winner.metadata.is_superseded:
            raise CarrierIntegrityError(
                _MSG_SUPERSEDE_DEAD_WINNER.format(
                    winner=winner_id, activation_id=loser.activation_id
                )
            )
        if _race_order(winner) > _race_order(loser):
            raise CarrierIntegrityError(
                _MSG_SUPERSEDE_LOSES.format(
                    winner=winner_id, activation_id=loser.activation_id
                )
            )

    def _assert_mint_permitted(
        self,
        root: RootRecord,
        facts: MintFacts,
        beads: Sequence[InstanceRecord],
        activations: Sequence[ActivationRecord],
        request: MintRequest,
    ) -> tuple[str, str]:
        """Verify the execution pins and every deterministic pre-mint bound."""
        crew_profile = pinned_execution_setting(root, facts.node, NodeSetting.CREW)
        model = pinned_execution_setting(root, facts.node, NodeSetting.MODEL)
        _assert_pinned_execution_setting(
            node=facts.node,
            field=_FIELD_CREW_PROFILE,
            requested=request.crew_profile,
            pinned=crew_profile,
        )
        _assert_pinned_execution_setting(
            node=facts.node,
            field=_FIELD_MODEL,
            requested=request.model,
            pinned=model,
        )
        refusal = self._pre_mint_refusal(root, facts, beads, activations)
        if refusal is not None:
            raise BoundExceededError(refusal)
        return crew_profile, model

    def _pre_mint_refusal(
        self,
        root: RootRecord,
        facts: MintFacts,
        beads: Sequence[InstanceRecord],
        activations: Sequence[ActivationRecord],
    ) -> BoundRefusal | None:
        """Every §10 pre-mint predicate that applies to this mint, in order.

        The ceiling is checked first because it admits no exemption; the round
        and system-outcome caps then apply per the mint's reason. A bound the
        graph does not declare (an acyclic region has no `max_entries`) is not
        evaluated — there is nothing to breach.

        Every bound is read through `bounds.effective_bound` against the gates
        already in `beads`: a §10.4 raise lives on the gate bead that carried
        its approval, so reading the root alone would enforce the pre-rebudget
        bound and refuse the mint the human just authorized.
        """
        instance_gates = reads.gates_of(beads)
        refusal = bounds.instance_ceiling_refusal(
            bead_count=bounds.ceiling_count(beads),
            max_total_activations=bounds.effective_bound(
                root, instance_gates, BoundSetting.MAX_TOTAL_ACTIVATIONS
            )
            or 0,
        )
        if refusal is not None:
            return refusal

        views = mint.views_of(activations)
        if facts.region is not None:
            max_entries = bounds.effective_bound(
                root, instance_gates, BoundSetting.MAX_ENTRIES, facts.region
            )
            if max_entries is not None:
                refusal = bounds.region_round_refusal(
                    region=facts.region,
                    distinct_rounds=bounds.distinct_rounds(views, facts.region),
                    target_round=facts.round_no,
                    max_entries=max_entries,
                )
                if refusal is not None:
                    return refusal

        if facts.mint_reason is MintReason.INFRA_RETRY:
            max_infra = bounds.effective_bound(
                root, instance_gates, BoundSetting.MAX_INFRA_RETRIES, facts.node
            )
            if max_infra is not None:
                return bounds.infra_retry_refusal(
                    node=facts.node,
                    round_no=facts.round_no,
                    consecutive_infra_closes=bounds.consecutive_infra_closes(
                        views, facts.node, facts.round_no
                    ),
                    max_infra_retries=max_infra,
                )
        if facts.mint_reason is MintReason.STEER_CONTINUATION:
            max_steers = bounds.effective_bound(
                root, instance_gates, BoundSetting.MAX_STEERS, facts.node
            )
            if max_steers is not None:
                return bounds.steer_refusal(
                    node=facts.node,
                    round_no=facts.round_no,
                    steer_closes=bounds.steer_closes(views, facts.node, facts.round_no),
                    max_steers=max_steers,
                )
        return None

    def _load_activation(self, activation_id: str) -> ActivationRecord:
        """Read one activation through the carrier contract."""
        return self._reads.load_activation(activation_id)

    def _apply(
        self,
        activation_id: str,
        *,
        lifecycle: Lifecycle,
        allowed: frozenset[Lifecycle],
        **changes: object,
    ) -> ActivationRecord:
        """Move the §5.1 state through the delta-only writer (`transitions.py`)."""
        return transitions.apply(
            self._client,
            self._load_activation,
            activation_id,
            lifecycle=lifecycle,
            allowed=allowed,
            **changes,
        )

    def _finish(self, record: ActivationRecord, reason: str) -> ActivationRecord:
        """Drive this activation's bd close to completion, idempotently."""
        return transitions.finish(self._client, self._load_activation, record, reason)


__all__ = ["WorkflowStore"]


__all__ = ["WorkflowStore", "pinned_execution_setting"]
