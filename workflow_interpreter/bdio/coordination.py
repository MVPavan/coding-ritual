"""Whole-member reservations and atomic consumption intents on one owner."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workflow_interpreter.foreman.compose import Composition

from pydantic import TypeAdapter

from workflow_interpreter.bdio import reads, roots
from workflow_interpreter.bdio.carriers import (
    BoundSetting,
    InstanceInput,
    ResolvedSetting,
)
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.records import RootRecord
from workflow_interpreter.bdio.wire import metadata_dict
from workflow_interpreter.schema.decisions import (
    BoundaryIdentity,
    CancellationReceipt,
    ChildCoordinationView,
    ChildRecord,
    CollectedChildResult,
    CoordinationError,
    CoordinationLink,
    CoordinationState,
    CoordinationView,
    DecisionConsumption,
    DecisionRequest,
    DecisionResponse,
    MemberAdmission,
    MemberCapacity,
    MemberReceipt,
    Reservation,
    TrustedReplacementIntent,
    digest_record,
)
from workflow_interpreter.schema.loader import load_pinned_body


def member_ceiling(root: RootRecord) -> int | None:
    """Immutable allocation; uninitialized opt-in roots fail closed."""
    if root.metadata.coordination is not None:
        return root.metadata.coordination.ceiling
    if root.definition.document.instance.coordination_limits is not None:
        raise CoordinationError("member reservation is not initialized")
    return None


class CoordinationStore:
    """Owner lock is used for admission/decisions, never ordinary mints."""

    def __init__(
        self,
        client: BdClient,
        verify_decision: Callable[[DecisionRequest], DecisionResponse] | None = None,
        *,
        composition: Composition | None = None,
    ) -> None:
        self._client = client
        self._composition = composition
        self._verify_decision = verify_decision

    def _lock_directory(self) -> Path:
        workspace = self._client.workspace.resolve()
        if any((workspace / ".wf-coordination").glob("*.lock")):
            raise CoordinationError(
                "legacy coordination locks require explicit offline migration; "
                "stop all old drivers before archiving the legacy lock directory"
            )
        return (workspace / ".beads").resolve() / "coordination"

    @contextmanager
    def _locked(self, owner_id: str) -> Iterator[None]:
        # Root IDs come from validated carrier reads, never arbitrary paths.
        from workflow_interpreter.supervisor.band import BandLock

        reads.load_root(self._client, owner_id)
        with BandLock(self._lock_directory() / f"{owner_id}.lock"):
            yield

    def state(self, owner_id: str) -> CoordinationState:
        state = reads.load_root(self._client, owner_id).metadata.coordination_state
        if state is None:
            raise CoordinationError("owner reservation ledger missing")
        return state

    def _save(self, state: CoordinationState) -> None:
        self._client._merge_metadata(
            state.owner_id, {"coordination_state": metadata_dict(state)}
        )

    def initialize(self, root_id: str, admission: MemberAdmission) -> MemberReceipt:
        with self._locked(root_id):
            root = reads.load_root(self._client, root_id)
            state = root.metadata.coordination_state
            if state is None:
                limits = root.definition.document.instance.coordination_limits
                if limits is None:
                    raise CoordinationError("coordination requires pinned limits")
                state = CoordinationState(owner_id=root_id, limits=limits)
                self._save(state)
            ceiling = self._capacity(admission)
            reservation = self._reserve(
                root_id,
                "initial",
                MemberCapacity(ceiling=ceiling, kind="work"),
                admission,
            )
            if reservation.root_id is not None:
                link = root.metadata.coordination
                if link is None or reservation.root_id != root_id:
                    raise CoordinationError("initial admission lost linkage")
                return MemberReceipt(root_id=root_id, link=link)
            return self._bind(root_id, reservation, root_id)

    @staticmethod
    def _capacity(admission: MemberAdmission) -> int:
        definition = load_pinned_body(admission.graph_body.encode())
        config = TypeAdapter(tuple[ResolvedSetting, ...]).validate_json(
            admission.config_json
        )
        value = next(
            (
                s.value
                for s in config
                if s.key == BoundSetting.MAX_TOTAL_ACTIVATIONS.at("")
            ),
            definition.document.instance.max_total_activations,
        )
        if type(value) is not int or value <= 0:
            raise CoordinationError("member needs a finite positive total ceiling")
        return value

    def _reserve(
        self,
        owner_id: str,
        key: str,
        capacity: MemberCapacity,
        admission: MemberAdmission,
        *,
        successor: TrustedReplacementIntent | None = None,
    ) -> Reservation:
        state = self.state(owner_id)
        graph = load_pinned_body(admission.graph_body.encode()).document
        expected_consumers = {
            name: tuple(n.name for n in graph.node if name in (n.inputs or ()))
            for name in admission.essential_inputs
        }
        inputs = TypeAdapter(tuple[InstanceInput, ...]).validate_json(
            admission.inputs_json
        )
        if (
            expected_consumers != admission.essential_consumers
            or any(not names for names in expected_consumers.values())
            or not set(expected_consumers) <= {i.name for i in inputs}
        ):
            raise CoordinationError(
                "essential advisory input consumer binding is invalid"
            )
        if capacity.ceiling != self._capacity(admission):
            raise CoordinationError("reservation must cover entire member ceiling")
        existing = state.reservations.get(key)
        if existing is not None:
            if existing.capacity != capacity or existing.admission != admission:
                raise CoordinationError("conflicting reservation replay")
            return existing
        items = (
            *state.reservations.values(),
            Reservation(reservation_id=key, capacity=capacity, admission=admission),
        )
        if (
            len(items) > state.limits.max_members
            or sum(r.capacity.ceiling for r in items) > state.limits.max_activations
            or sum(r.capacity.ceiling for r in items if r.capacity.kind == "decision")
            > state.limits.max_decision_attempts
            or sum(r.capacity.kind == "replacement" for r in items)
            > state.limits.max_replacements
        ):
            raise CoordinationError("whole-member reservation capacity exhausted")
        reservation = items[-1]
        self._save(
            state.model_copy(
                update={
                    "reservations": {**state.reservations, key: reservation},
                    "successors": {**state.successors, successor.request_key: successor}
                    if successor is not None
                    else state.successors,
                }
            )
        )
        return reservation

    def reserve(
        self,
        owner_id: str,
        admission_key: str,
        capacity: MemberCapacity,
        admission: MemberAdmission,
    ) -> Reservation:
        with self._locked(owner_id):
            return self._reserve(owner_id, admission_key, capacity, admission)

    def _bind(
        self, owner_id: str, reservation: Reservation, root_id: str
    ) -> MemberReceipt:
        admission = reservation.admission
        link = CoordinationLink(
            owner_id=owner_id,
            slot=admission.slot,
            generation=admission.generation,
            reservation_id=reservation.reservation_id,
            ceiling=reservation.capacity.ceiling,
            predecessor_id=admission.predecessor_id,
            request_id=admission.request_id,
        )
        root = reads.load_root(self._client, root_id)
        if root.metadata.coordination not in (None, link):
            raise CoordinationError("member linkage conflict")
        self._client._merge_metadata(
            root_id,
            {
                "coordination": metadata_dict(link),
                "essential_inputs": list(admission.essential_inputs),
                "essential_consumers": {
                    k: list(v) for k, v in admission.essential_consumers.items()
                },
                "decision_templates": {
                    k: metadata_dict(v) for k, v in admission.templates.items()
                },
            },
        )
        state = self.state(owner_id)
        reservation = reservation.model_copy(update={"root_id": root_id})
        self._save(
            state.model_copy(
                update={
                    "reservations": {
                        **state.reservations,
                        reservation.reservation_id: reservation,
                    },
                    "active": {**state.active, admission.slot: root_id},
                }
            )
        )
        return MemberReceipt(root_id=root_id, link=link)

    def admit_member(
        self,
        owner_id: str,
        slot: str,
        generation: int,
        admission: MemberAdmission,
        *,
        kind: str,
    ) -> MemberReceipt:
        if admission.slot != slot or admission.generation != generation:
            raise CoordinationError("member slot/generation mismatch")
        with self._locked(owner_id):
            key = digest_record(admission)
            state = self.state(owner_id)
            if kind == "decision" and admission.request_id in state.requests:
                source = reads.load_root(
                    self._client, state.requests[admission.request_id].boundary.root_id
                )
                self.assert_child_progress(source)
            for prior in state.reservations.values():
                if prior.admission.slot != slot:
                    continue
                if prior.admission.generation > generation or (
                    prior.admission.generation == generation
                    and prior.reservation_id != key
                ):
                    raise CoordinationError("stale or conflicting admission generation")
            if generation > 0:
                if admission.predecessor_id is None or admission.request_id is None:
                    raise CoordinationError(
                        "replacement requires durable predecessor intent"
                    )
                predecessor = reads.load_root(self._client, admission.predecessor_id)
                link = predecessor.metadata.coordination
                intent = state.successors.get(admission.request_id)
                if (
                    link is None
                    or link.owner_id != owner_id
                    or link.slot != slot
                    or link.generation + 1 != generation
                    or intent is None
                    or intent.admission != admission
                    or intent.predecessor_id != predecessor.root_id
                    or state.active.get(slot) == predecessor.root_id
                ):
                    raise CoordinationError(
                        "replacement predecessor is not fenced by its intent"
                    )
            capacity = MemberCapacity.model_validate(
                {"ceiling": self._capacity(admission), "kind": kind}
            )
            reservation = self._reserve(owner_id, key, capacity, admission)
            if reservation.root_id is not None:
                root = reads.load_root(self._client, reservation.root_id)
                if root.metadata.coordination is None:
                    raise CoordinationError("admitted root lost linkage")
                return MemberReceipt(
                    root_id=root.root_id, link=root.metadata.coordination
                )
            # Reservation and admission body already durable. Keyed root recovery is exact.
            root = roots.create_root(
                self._client,
                instance_key=f"coord-{owner_id}-{key}",
                definition=load_pinned_body(admission.graph_body.encode()),
                resolved_config=TypeAdapter(tuple[ResolvedSetting, ...]).validate_json(
                    admission.config_json
                ),
                instance_inputs=TypeAdapter(tuple[InstanceInput, ...]).validate_json(
                    admission.inputs_json
                ),
                instance_base_commit=admission.base_commit,
            )
            return self._bind(owner_id, reservation, root.root_id)

    def start_child(
        self, owner_id: str, slot: str, admission: MemberAdmission
    ) -> MemberReceipt:
        """Admit only standalone, finite children without replacement authority."""
        definition = load_pinned_body(admission.graph_body.encode())
        if (
            admission.predecessor_id
            or admission.request_id
            or admission.generation != 0
        ):
            raise CoordinationError("child requires standalone generation zero")
        import re

        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", slot):
            raise CoordinationError("invalid child slot")
        if self._composition is None:
            raise CoordinationError("child admission requires a runtime composition")
        from workflow_interpreter.foreman.execution import effective_node
        from workflow_interpreter.schema.models import IsolationMode

        settings = {
            s.key: s.value
            for s in TypeAdapter(tuple[ResolvedSetting, ...]).validate_json(
                admission.config_json
            )
        }
        for pinned in definition.document.node:
            node = effective_node(pinned, settings)
            if node.writes and node.isolation is not IsolationMode.WORKTREE:
                raise CoordinationError("writer child requires worktree isolation")
        wrapper = str(self._composition.supervisor_config.wrapper_root.resolve())
        receipt = self.admit_member(owner_id, slot, 0, admission, kind="child")
        with self._locked(owner_id):
            state = self.state(owner_id)
            prior = state.children.get(slot)
            if prior is not None:
                if prior.root_id != receipt.root_id or prior.wrapper_root != wrapper:
                    raise CoordinationError("conflicting child wrapper location")
            else:
                self._save(
                    state.model_copy(
                        update={
                            "children": {
                                **state.children,
                                slot: ChildRecord(
                                    root_id=receipt.root_id,
                                    slot=slot,
                                    wrapper_root=wrapper,
                                ),
                            }
                        }
                    )
                )
        from workflow_interpreter.foreman.resolve import ensure_instance_branch

        ensure_instance_branch(
            self._composition, reads.load_root(self._client, receipt.root_id)
        )
        return receipt

    def target_lock_path(self, key: str) -> Path:
        """Share canonical metadata namespace and legacy-lock migration checks."""
        import re

        if not re.fullmatch(r"[0-9a-f]{64}", key):
            raise CoordinationError("invalid integration target key")
        return self._lock_directory() / f"target-{key}.lock"

    def member_lock_path(self, root_id: str, purpose: str = "band") -> Path:
        """Canonical exclusion belongs to the Beads workspace, not wrapper home."""
        reads.load_root(self._client, root_id)
        if purpose not in ("band", "launch", "drive"):
            raise CoordinationError("unknown child lock purpose")
        return self._lock_directory() / f"{root_id}.{purpose}.lock"

    def child_record(self, owner_id: str, slot: str, generation: int) -> ChildRecord:
        state = self.state(owner_id)
        row = state.children.get(slot)
        if (
            type(generation) is not int
            or row is None
            or row.generation != generation
            or state.active.get(slot) != row.root_id
        ):
            raise CoordinationError("unknown or stale child generation")
        self.validate_member(reads.load_root(self._client, row.root_id))
        return row

    def update_child(self, owner_id: str, row: ChildRecord) -> None:
        """Short metadata transition; never called while waiting for a process."""
        if self.child_record(owner_id, row.slot, row.generation) == row:
            return
        with self._locked(owner_id):
            current = self.child_record(owner_id, row.slot, row.generation)
            if current.cancellation is not None and row.cancellation is None:
                raise CoordinationError("child cancellation fences progress")
            if current.collection is not None and row.collection != current.collection:
                raise CoordinationError("collected child is immutable")
            if (
                current.cancellation is not None
                and current.cancellation.state == "cancelled"
            ):
                row = row.model_copy(
                    update={"state": "cancelled", "cancellation": current.cancellation}
                )
            state = self.state(owner_id)
            self._save(
                state.model_copy(update={"children": {**state.children, row.slot: row}})
            )

    def child_status(self, owner_id: str) -> ChildCoordinationView:
        state = self.state(owner_id)
        view = self.coordination_view(owner_id)
        rows = tuple(state.children[k] for k in sorted(state.children))
        if self._composition is not None:
            from workflow_interpreter.foreman.children import observe

            rows = tuple(observe(self._composition, row) for row in rows)
        return ChildCoordinationView(
            owner_id=owner_id,
            reserved_activation_capacity=view.reserved_activation_capacity,
            reserved_decision_attempt_capacity=view.reserved_decision_attempt_capacity,
            children=rows,
        )

    def runtime(self) -> Composition:
        if self._composition is None:
            raise CoordinationError("child operation requires a runtime composition")
        return self._composition

    def cancel_child(
        self, owner_id: str, slot: str, generation: int, request_key: str, reason: str
    ) -> CancellationReceipt:
        from workflow_interpreter.foreman.children import finish_cancel

        intent = CancellationReceipt(request_key=request_key, reason=reason)
        with self._locked(owner_id):
            row = self.child_record(owner_id, slot, generation)
            if row.cancellation is not None:
                if (row.cancellation.request_key, row.cancellation.reason) != (
                    request_key,
                    reason,
                ):
                    raise CoordinationError("conflicting child cancellation replay")
            else:
                if row.collection is not None:
                    raise CoordinationError("collected child is immutable")
                state = self.state(owner_id)
                row = row.model_copy(
                    update={"state": "cancel_pending", "cancellation": intent}
                )
                self._save(
                    state.model_copy(update={"children": {**state.children, slot: row}})
                )
        return finish_cancel(self.runtime(), owner_id, row)

    def collect_child(
        self, owner_id: str, slot: str, generation: int
    ) -> CollectedChildResult:
        row = self.child_record(owner_id, slot, generation)
        if row.cancellation is not None:
            raise CoordinationError("cancelled child cannot collect")
        from workflow_interpreter.foreman.children import collect

        return collect(self.runtime(), owner_id, row)

    def recover_child(
        self, owner_id: str, slot: str, generation: int
    ) -> ChildCoordinationView:
        from workflow_interpreter.foreman.children import recover

        return recover(
            self.runtime(), owner_id, self.child_record(owner_id, slot, generation)
        )

    def drive_children(
        self, owner_id: str, max_concurrent: int, max_wall_s: float
    ) -> ChildCoordinationView:
        from workflow_interpreter.foreman.children import drive

        return drive(self.runtime(), owner_id, max_concurrent, max_wall_s)

    def child_for_root(self, root: RootRecord) -> ChildRecord | None:
        """Decision tasks inherit the originating child's cancellation fence."""
        link = root.metadata.coordination
        if link is None:
            return None
        state = self.state(link.owner_id)
        child = state.children.get(link.slot)
        if child is not None and child.root_id == root.root_id:
            return child
        request = state.requests.get(link.request_id or "")
        if request is not None:
            return next(
                (
                    r
                    for r in state.children.values()
                    if r.root_id == request.boundary.root_id
                ),
                None,
            )
        return None

    def assert_child_progress(self, root: RootRecord) -> None:
        link = root.metadata.coordination
        if link is not None:
            state = self.state(link.owner_id)
            if any(
                intent.predecessor_id == root.root_id
                for intent in state.successors.values()
            ):
                raise CoordinationError("successor intent fences predecessor progress")
            intent = state.successors.get(link.request_id or "")
            if intent is not None and intent.state != "admitted":
                raise CoordinationError("successor admission is incomplete")
        child = self.child_for_root(root)
        if child is not None and (
            child.cancellation is not None or child.collection is not None
        ):
            raise CoordinationError("child cancellation or collection fences progress")

    def validate_member(self, root: RootRecord) -> None:
        ceiling = member_ceiling(root)
        if ceiling is None:
            # Incomplete generated-member admission cannot run even though its graph has no policy.
            if root.metadata.instance_key.startswith("coord-"):
                raise CoordinationError("member admission incomplete")
            return
        link = root.metadata.coordination
        assert link is not None
        state = self.state(link.owner_id)
        reservation = state.reservations.get(link.reservation_id)
        if (
            reservation is None
            or reservation.root_id != root.root_id
            or reservation.capacity.ceiling != ceiling
            or reservation.admission.generation != link.generation
            or reservation.admission.slot != link.slot
            or reservation.admission.predecessor_id != link.predecessor_id
            or reservation.admission.request_id != link.request_id
            or state.active.get(link.slot) != root.root_id
        ):
            raise CoordinationError("stale generation or invalid member reservation")

    def attention(self, owner_id: str, reason: str) -> None:
        with self._locked(owner_id):
            state = self.state(owner_id)
            self._save(state.model_copy(update={"human_attention": reason}))

    def open_decision(
        self, boundary: BoundaryIdentity, actions: tuple[str, ...]
    ) -> DecisionRequest:
        with self._locked(boundary.owner_id):
            root = reads.load_root(self._client, boundary.root_id)
            self.validate_member(root)
            self.assert_child_progress(root)
            if root.metadata.decision_boundary != boundary:
                raise CoordinationError("boundary is no longer current")
            source = reads.load_activation(self._client, boundary.source_activation_id)
            policy = root.index.nodes[source.metadata.node].decision
            if (
                policy is None
                or digest_record(policy) != boundary.policy_digest
                or not set(actions) <= set(policy.actions)
            ):
                raise CoordinationError(
                    "request actions are not authorized by pinned policy"
                )
            if (
                boundary.kind not in ("fail_plan", "doubt")
                and "continue_declared" in actions
            ):
                raise CoordinationError("refused boundary cannot continue")
            state = self.state(boundary.owner_id)
            key = digest_record(boundary)
            if key in state.requests:
                return state.requests[key]
            request = DecisionRequest.model_validate(
                {
                    "request_id": key,
                    "boundary": boundary,
                    "actions": actions,
                    "decision_key": key,
                    "reserved_capacity_snapshot": sum(
                        r.capacity.ceiling for r in state.reservations.values()
                    ),
                }
            )
            self._save(
                state.model_copy(update={"requests": {**state.requests, key: request}})
            )
            return request

    def _update_request(self, owner_id: str, request: DecisionRequest) -> None:
        """Caller holds owner lock; updates carry complete prior immutable identity."""
        state = self.state(owner_id)
        prior = state.requests[request.request_id]
        if prior.boundary != request.boundary or prior.actions != request.actions:
            raise CoordinationError("request identity changed")
        self._save(
            state.model_copy(
                update={"requests": {**state.requests, request.request_id: request}}
            )
        )

    def consume_decision(
        self,
        owner_id: str,
        request_id: str,
        response: DecisionResponse,
    ) -> DecisionConsumption:
        """Called after immutable output verification; enforce identity again under owner lock."""
        with self._locked(owner_id):
            state = self.state(owner_id)
            request = state.requests[request_id]
            boundary = request.boundary
            root = reads.load_root(self._client, boundary.root_id)
            self.validate_member(root)
            self.assert_child_progress(root)
            if (
                request.state not in ("admitted", "awaiting_output")
                or request.response is not None
            ):
                raise CoordinationError("decision already consumed or unavailable")
            if (
                root.metadata.decision_boundary != boundary
                or response.request_id != request_id
                or response.request_digest != digest_record(boundary)
                or response.parent_generation != boundary.generation
                or response.artifact_digest != boundary.artifact_tree
                or response.producing_root_id != request.decision_root_id
                or response.producing_activation_id != request.attempt_id
                or response.action not in request.actions
            ):
                raise CoordinationError("stale or unauthorized decision response")
            if (
                self._verify_decision is None
                or self._verify_decision(request) != response
            ):
                raise CoordinationError("response differs from immutable output")
            digest = digest_record(response)
            attempt = reads.load_activation(
                self._client, response.producing_activation_id
            )
            envelope = attempt.metadata.envelope
            if envelope is None or not isinstance(envelope.get("sha256"), str):
                raise CoordinationError(
                    "decision attempt lacks durable envelope evidence"
                )
            self._update_request(
                owner_id,
                request.model_copy(
                    update={
                        "state": "consumed",
                        "response": response,
                        "response_digest": digest,
                        "envelope_reference": f"wf-activation://{attempt.activation_id}/envelope",
                        "envelope_sha256": envelope["sha256"],
                    }
                ),
            )
            return DecisionConsumption(
                request_id=request_id,
                response_digest=digest,
                action=response.action,
                applied=False,
            )

    def coordination_view(self, owner_id: str) -> CoordinationView:
        state = self.state(owner_id)
        values = state.reservations.values()
        return CoordinationView(
            owner_id=owner_id,
            active_root_id=state.active.get("work"),
            reserved_activation_capacity=sum(r.capacity.ceiling for r in values),
            reserved_decision_attempt_capacity=sum(
                r.capacity.ceiling for r in values if r.capacity.kind == "decision"
            ),
            members=len(state.reservations),
            replacements=sum(r.capacity.kind == "replacement" for r in values),
            human_attention=state.human_attention,
            requests=tuple(state.requests.values()),
        )
