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

from collections.abc import Sequence
from typing import Final

import structlog

from workflow_interpreter.bdio import (
    bounds,
    canary,
    gates,
    mint,
    reads,
    supervision,
    transitions,
)
from workflow_interpreter.bdio.bounds import BoundRefusal
from workflow_interpreter.bdio.capabilities import ArtifactReader, BranchHeadReader
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.config import BdConfig, SigningConfig
from workflow_interpreter.bdio.errors import (
    BdConfigError,
    BoundExceededError,
    CarrierIntegrityError,
    LifecycleConflictError,
)
from workflow_interpreter.bdio.mint import MintFacts
from workflow_interpreter.bdio.records import (
    ActivationRecord,
    CanaryResult,
    GateRecord,
    MintResult,
    RootRecord,
)
from workflow_interpreter.bdio.roots import create_root
from workflow_interpreter.bdio.signing import GateVerifier
from workflow_interpreter.bdio.wire import (
    ActivationMetadata,
    BeadRecord,
    BoundSetting,
    Deviation,
    EventPayload,
    Evidence,
    ExitRecord,
    GateOpenRequest,
    InstanceInput,
    Lifecycle,
    MintReason,
    MintRequest,
    PreconditionRecord,
    ProcessHandle,
    ResolvedSetting,
    StaleFlagRecord,
    Usage,
    metadata_dict,
)
from workflow_interpreter.schema.models import GraphDefinition, Outcome

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

_TITLE_ACTIVATION: Final[str] = "wf {node} r{round_no} #{seq}"
_REASON_ACTIVATION: Final[str] = "outcome={outcome}"
_REASON_SUPERSEDED: Final[str] = "outcome=superseded superseded_by={winner}"

_MSG_ALL_SUPERSEDED: Final[str] = (
    "every activation for idempotency_key={key!r} is superseded"
)
_MSG_CLOSE_CONFLICT: Final[str] = (
    "activation {activation_id} is already closed {found}, refusing to close {wanted}"
)
_MSG_SUPERSEDE_CONFLICT: Final[str] = (
    "activation {activation_id} is already superseded by {found}, not {wanted}"
)
_MSG_SUPERSEDE_OUTCOME: Final[str] = (
    "close_activation refuses the system outcome {outcome} — use supersede_activation()"
)
_MSG_NO_VERIFIER: Final[str] = (
    "no GateVerifier injected; a gate cannot be closed without §9 verification"
)
_MSG_CLOSE_SUPERSEDED: Final[str] = (
    "activation {activation_id} is superseded by {winner}; closing it {wanted} "
    "would resurrect a lost race into routing truth (§3.2)"
)
_MSG_SUPERSEDE_COMPLETED: Final[str] = (
    "activation {activation_id} already recorded outcome {outcome}; superseding "
    "a COMPLETED activation would destroy the outcome the frontier routed on "
    "(§3.2, §3.3)"
)
_MSG_SUPERSEDE_NO_WINNER: Final[str] = (
    "supersede names winner {winner!r}, which is not a live activation of this "
    "root under idempotency_key={key!r}; {activation_id} would be destroyed to "
    "settle a race that cannot be shown to exist (§3.2)"
)
_MSG_SUPERSEDE_DEAD_WINNER: Final[str] = (
    "supersede names winner {winner!r}, which is itself superseded; closing "
    "{activation_id} onto it would leave the key with nothing live (§3.2)"
)
_MSG_SUPERSEDE_LOSES: Final[str] = (
    "supersede names winner {winner!r}, which does not win the §3.2 tie-break "
    "against {activation_id} (completed first, then lowest seq, then lowest id)"
)
_MSG_TWO_COMPLETED: Final[str] = (
    "idempotency_key={key!r} has more than one COMPLETED activation "
    "({found}); the race cannot be resolved without destroying a recorded "
    "outcome — triage it (§3.2)"
)


def _race_order(record: ActivationRecord) -> tuple[bool, int, str]:
    """The §3.2 winner rule as a sort key: completed first, then `seq`, then id.

    One definition, used both to pick a winner among race residue and to prove
    a caller-named winner actually is one.
    """
    return (
        not record.metadata.is_completed,
        record.metadata.seq,
        record.bead.id,
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
        client: BdClient,
        verifier: GateVerifier | None = None,
        *,
        artifact_reader: ArtifactReader | None = None,
        branch_head_reader: BranchHeadReader | None = None,
    ) -> None:
        self._client = client
        self._verifier = verifier
        self._artifact_reader = artifact_reader
        self._branch_head_reader = branch_head_reader
        self._reads = reads.WorkflowReads(client)

    @classmethod
    def from_config(
        cls,
        config: BdConfig,
        signing: SigningConfig | None = None,
        *,
        artifact_reader: ArtifactReader | None = None,
        branch_head_reader: BranchHeadReader | None = None,
    ) -> WorkflowStore:
        """Build a store from configuration alone — the supported entry point.

        The transport stays sealed: `BdClient` is not exported (§0.1), so a
        caller with a `BdConfig` and a `SigningConfig` had no way to construct
        a store without reaching into the package. It has one now, and it is
        the only one.
        """
        client = BdClient(config)
        verifier = None if signing is None else GateVerifier(signing, config.workspace)
        return cls(
            client,
            verifier,
            artifact_reader=artifact_reader,
            branch_head_reader=branch_head_reader,
        )

    def for_root(self, *, branch_head_reader: BranchHeadReader) -> WorkflowStore:
        """Derive a root-scoped store without replacing injected capabilities.

        The transport, verifier, and artifact reader are process-scoped
        authority.  A root contributes only its branch-head reader.
        """
        return WorkflowStore(
            self._client,
            self._verifier,
            artifact_reader=self._artifact_reader,
            branch_head_reader=branch_head_reader,
        )

    @property
    def reads(self) -> reads.WorkflowReads:
        """The §4 read vocabulary — the only bd handle this store hands out."""
        return self._reads

    # -- §11 startup canary ----------------------------------------------

    def startup_canary(self) -> CanaryResult:
        """Assert the pinned backend and workspace, and round-trip a wisp (§11)."""
        return canary.startup_canary(self._client)

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
        )

    # -- activations -----------------------------------------------------

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
        root = self._reads.load_root(root_id)
        # ONE fetch of the instance's beads serves the ceiling count, the
        # activation views, the key lookup and the derivation.
        beads = self._reads.instance_beads(root_id)
        activations = reads.activations_of(beads)
        gates_of_instance = reads.gates_of(beads)
        facts = mint.derive_mint_facts(
            root, request, activations, self._branch_head_reader, gates_of_instance
        )
        existing = tuple(
            record
            for record in activations
            if record.metadata.idempotency_key == facts.idempotency_key
        )
        if existing:
            return MintResult(
                activation=self._resolve_race(existing, facts.idempotency_key),
                idempotency_key=facts.idempotency_key,
                created=False,
            )

        refusal = self._pre_mint_refusal(root, facts, beads, activations)
        if refusal is not None:
            raise BoundExceededError(refusal)

        seq = reads.next_seq(beads)
        metadata = ActivationMetadata(
            wf_root_id=root_id,
            node=facts.node,
            region=facts.region,
            round_no=facts.round_no,
            seq=seq,
            predecessor_activation_id=facts.predecessor_activation_id,
            predecessor_gate_id=facts.predecessor_gate_id,
            outcome_taken=facts.outcome_taken,
            idempotency_key=facts.idempotency_key,
            mint_reason=facts.mint_reason,
            inputs=request.inputs,
            runner_profile=request.runner_profile,
            model=request.model,
            session_id=request.session_id,
            intended_base_commit=facts.intended_base_commit,
            deviations=request.deviations,
        )
        record = self._client._create_bead(
            title=_TITLE_ACTIVATION.format(
                node=facts.node, round_no=facts.round_no, seq=seq
            ),
            metadata=metadata_dict(metadata),
        )
        _LOG.info(
            "wf.activation.minted",
            root_id=root_id,
            activation_id=record.id,
            node=facts.node,
            round_no=facts.round_no,
            idempotency_key=facts.idempotency_key,
        )
        winner = self._resolve_race(
            self._reads.find_by_idempotency_key(root_id, facts.idempotency_key),
            facts.idempotency_key,
        )
        return MintResult(
            activation=winner,
            idempotency_key=facts.idempotency_key,
            created=winner.activation_id == record.id,
        )

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
        (`supervision.py` holds the rule, and does its own fresh read so the
        lifecycle check sits as close to the write as bd allows).
        """
        return supervision.record_precondition(
            self._client, self._load_activation, activation_id, record
        )

    def record_stale_flag(
        self, activation_id: str, flag: StaleFlagRecord
    ) -> ActivationRecord:
        """Mirror the §8.2 stale flag into bd; the FIRST raise wins.

        Staleness is a hint for a tier-2 decision, not a verdict, so a re-raise
        must not rewrite when the runner actually went quiet — the recorded
        flag is returned unchanged rather than overwritten (§8.2). Refused
        outright unless the activation is still `dispatched`: the flag is a
        statement about a RUNNING child.
        """
        return supervision.record_stale_flag(
            self._client, self._load_activation, activation_id, flag
        )

    def record_dispatch(
        self, activation_id: str, handle: ProcessHandle
    ) -> ActivationRecord:
        """Phase B: the state moves only after the handle is durable (§5.2).

        The settled guard runs FIRST, before the idempotence short-circuit: a
        recorded outcome is terminal even where a losing race left `lifecycle`
        saying `dispatched`, and a short-circuit that returns such a row reports
        success for a state write nobody may make (`transitions.py`).

        The session id travels with the handle. `Profile.prepare` is the only
        minter of one (§5.2), and it runs at LAUNCH, so an activation whose
        mint carried none would leave every continuation and infra retry
        copying an empty id off its metadata. It is written only when the
        recorded id is EMPTY, and a handle naming a different non-empty session
        is refused rather than dropped (`assert_same_session`).
        """
        record = self._load_activation(activation_id)
        transitions.assert_not_settled(record, Lifecycle.DISPATCHED)
        transitions.assert_same_session(
            activation_id, record.metadata.session_id, handle.session_id
        )
        if record.metadata.lifecycle is Lifecycle.DISPATCHED:
            transitions.assert_same(
                activation_id, record.metadata.handle, handle, Lifecycle.DISPATCHED
            )
            return record
        transitions.assert_lifecycle(record, Lifecycle.MINTED, Lifecycle.DISPATCHED)
        session: dict[str, object] = (
            {"session_id": handle.session_id}
            if handle.session_id and not record.metadata.session_id
            else {}
        )
        return self._apply(
            activation_id,
            lifecycle=Lifecycle.DISPATCHED,
            allowed=frozenset({Lifecycle.MINTED}),
            handle=handle,
            **session,
        )

    def record_exit(
        self, activation_id: str, exit_record: ExitRecord
    ) -> ActivationRecord:
        """Mirror the wrapper's exit record into bd (§5.3) — the §7.1 observable."""
        record = self._load_activation(activation_id)
        transitions.assert_not_settled(record, Lifecycle.EXIT_RECORDED)
        if record.metadata.lifecycle is Lifecycle.EXIT_RECORDED:
            transitions.assert_same(
                activation_id,
                record.metadata.exit_record,
                exit_record,
                Lifecycle.EXIT_RECORDED,
            )
            return record
        transitions.assert_lifecycle(
            record, Lifecycle.DISPATCHED, Lifecycle.EXIT_RECORDED
        )
        return self._apply(
            activation_id,
            lifecycle=Lifecycle.EXIT_RECORDED,
            allowed=frozenset({Lifecycle.DISPATCHED}),
            exit_record=exit_record,
        )

    def record_evidence(
        self,
        activation_id: str,
        evidence: Evidence,
        usage: Usage | None = None,
    ) -> ActivationRecord:
        """Record computed §7 evidence before the outcome is decided."""
        record = self._load_activation(activation_id)
        transitions.assert_not_settled(record, Lifecycle.EVIDENCE_RECORDED)
        if record.metadata.lifecycle is Lifecycle.EVIDENCE_RECORDED:
            transitions.assert_same(
                activation_id,
                record.metadata.evidence,
                evidence,
                Lifecycle.EVIDENCE_RECORDED,
            )
            return record
        transitions.assert_lifecycle(
            record, Lifecycle.EXIT_RECORDED, Lifecycle.EVIDENCE_RECORDED
        )
        return self._apply(
            activation_id,
            lifecycle=Lifecycle.EVIDENCE_RECORDED,
            allowed=frozenset({Lifecycle.EXIT_RECORDED}),
            evidence=evidence,
            usage=usage,
        )

    def close_activation(
        self,
        activation_id: str,
        outcome: Outcome,
        *,
        evidence: Evidence | None = None,
        usage: Usage | None = None,
        deviations: Sequence[Deviation] = (),
    ) -> ActivationRecord:
        """Close with the outcome that IS the routing truth (§3.3).

        A re-run that finds the outcome already recorded does NOT return early:
        it repairs the close forward, because a recorded outcome on an open
        bead is a half-finished transition the frontier would otherwise re-pick
        forever (probed, phase-2 review).

        A SUPERSEDED activation is refused outright: `supersede` is terminal
        too, and closing over it would turn a lost race back into an edge a
        successor can be minted from — forged routing truth in two typed calls
        with no signature anywhere (probed, phase-2 review).

        The "already closed" test is the RECORDED OUTCOME, not the lifecycle. A
        transition whose merge landed after a concurrent close leaves the row
        `status=closed lifecycle=exit-recorded outcome=steered`; keying this
        guard on `is_completed` (which needs `lifecycle == closed`) let a second
        close walk straight through it and overwrite the `steered` a
        continuation was already minted from (probed, round 3). A bd row that is
        closed with NO recorded outcome is a different state — the §5.1 crash
        window — and is still repaired forward, which is why bd's status does
        not appear here.
        """
        if outcome is Outcome.SUPERSEDED:
            raise LifecycleConflictError(
                _MSG_SUPERSEDE_OUTCOME.format(outcome=outcome.value)
            )
        record = self._load_activation(activation_id)
        if record.metadata.is_superseded:
            raise CarrierIntegrityError(
                _MSG_CLOSE_SUPERSEDED.format(
                    activation_id=activation_id,
                    winner=record.metadata.superseded_by,
                    wanted=outcome.value,
                )
            )
        reason = _REASON_ACTIVATION.format(outcome=outcome.value)
        if record.metadata.is_settled:
            if record.metadata.outcome is not outcome:
                raise LifecycleConflictError(
                    _MSG_CLOSE_CONFLICT.format(
                        activation_id=activation_id,
                        found=record.metadata.outcome,
                        wanted=outcome.value,
                    )
                )
            transitions.assert_close_payload(record, evidence, usage, deviations)
            return self._finish(record, reason)
        applied = self._apply(
            activation_id,
            lifecycle=Lifecycle.CLOSED,
            allowed=transitions.OPEN_LIFECYCLES,
            outcome=outcome,
            evidence=evidence if evidence is not None else record.metadata.evidence,
            usage=usage if usage is not None else record.metadata.usage,
            deviations=(*record.metadata.deviations, *deviations),
        )
        _LOG.info(
            "wf.activation.closed", activation_id=activation_id, outcome=outcome.value
        )
        return self._finish(applied, reason)

    def supersede_activation(self, loser_id: str, winner_id: str) -> ActivationRecord:
        """Append-only race resolution: never `bd delete`, never reopen (§3.2).

        A COMPLETED activation is never a loser: its recorded outcome is what
        the frontier routed on, so overwriting it with `superseded` destroys
        routing truth rather than resolving a race (probed, phase-2 review).

        The WINNER is proved, not taken on the caller's word: it must exist,
        share this root AND this idempotency key, still be live, and win the
        §3.2 tie-break. Without that, superseding the sole activation of an
        instance onto `"wf-does-not-exist"` succeeded and left the key with
        nothing live under it — the next mint refused (probed, phase-2 r3).

        "Never a loser" is the RECORDED OUTCOME, not `is_completed`: that
        property requires `lifecycle == closed`, and a losing merge drags the
        lifecycle back under a row that already carries one — leaving
        `status=closed lifecycle=exit-recorded outcome=steered`, which walked
        straight through this guard and overwrote the `steered` a continuation
        was minted from (probed, r4). An already-SUPERSEDED activation is the
        one settled row this still accepts, because superseding it again is the
        idempotent re-run below.
        """
        record = self._load_activation(loser_id)
        if record.metadata.is_settled and not record.metadata.is_superseded:
            raise CarrierIntegrityError(
                _MSG_SUPERSEDE_COMPLETED.format(
                    activation_id=loser_id,
                    outcome=None
                    if record.metadata.outcome is None
                    else record.metadata.outcome.value,
                )
            )
        self._assert_race_winner(record, winner_id)
        reason = _REASON_SUPERSEDED.format(winner=winner_id)
        if record.metadata.superseded_by is not None:
            if record.metadata.superseded_by != winner_id:
                raise LifecycleConflictError(
                    _MSG_SUPERSEDE_CONFLICT.format(
                        activation_id=loser_id,
                        found=record.metadata.superseded_by,
                        wanted=winner_id,
                    )
                )
            return self._finish(record, reason)
        applied = self._apply(
            loser_id,
            lifecycle=Lifecycle.SUPERSEDED,
            allowed=transitions.OPEN_LIFECYCLES,
            outcome=Outcome.SUPERSEDED,
            superseded_by=winner_id,
        )
        _LOG.warning("wf.activation.superseded", loser=loser_id, winner=winner_id)
        return self._finish(applied, reason)

    # -- gates and events ------------------------------------------------

    def open_gate(self, root_id: str, request: GateOpenRequest) -> GateRecord:
        """Open a gate under its deterministic key — a re-tick re-finds it (§3.4)."""
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
            raise BdConfigError(_MSG_NO_VERIFIER)
        return gates.close_gate_verified(
            self._client,
            self._verifier,
            root_id,
            gate_id,
            payload_bytes=payload_bytes,
            signature=signature,
            artifact_reader=self._artifact_reader,
        )

    def append_event(
        self, root_id: str, payload: EventPayload, *, seq: int | None = None
    ) -> BeadRecord:
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
        live = [record for record in found if not record.metadata.is_superseded]
        if not live:
            raise CarrierIntegrityError(_MSG_ALL_SUPERSEDED.format(key=key))
        if len(live) == 1:
            return live[0]
        completed = [record for record in live if record.metadata.is_completed]
        if len(completed) > 1:
            raise CarrierIntegrityError(
                _MSG_TWO_COMPLETED.format(
                    key=key,
                    found=", ".join(record.activation_id for record in completed),
                )
            )
        ordered = sorted(live, key=_race_order)
        winner, *losers = ordered
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

    def _pre_mint_refusal(
        self,
        root: RootRecord,
        facts: MintFacts,
        beads: Sequence[BeadRecord],
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
        return transitions.finish(self._client, record, reason)


__all__ = ["WorkflowStore"]
