"""The closed Beads surface used by phase admission."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Final

from pydantic import ValidationError

from workflow_interpreter.bdio import finalize
from workflow_interpreter.bdio.client import BdClient, DependencyRecord, DependencyType
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.reads import find_roots
from workflow_interpreter.bdio.wire import BeadRecord, Metadata
from workflow_interpreter.bridge.models import PhaseBridgeRecord, PhaseBridgeState

if TYPE_CHECKING:
    from workflow_interpreter.bridge.integration import IntegrationGuard

PHASE_BRIDGE_METADATA_KEY: Final[str] = "phase_bridge"
MSG_WRONG_STAGE: Final[str] = "phase bridge record belongs to stage {stage_id!r}"
MSG_WRONG_INCOMING_STATE: Final[str] = (
    "incoming phase bridge record expected state {state!r}, got {actual!r}"
)
MSG_IDEMPOTENT_STATE: Final[str] = (
    "idempotent phase bridge re-prepare requires stored state prepared, got {actual!r}"
)
MSG_IDEMPOTENT_RECORD: Final[str] = (
    "idempotent phase bridge re-prepare requires an incoming record identical to stored"
)
MSG_SUCCESSION_CLOSED: Final[str] = (
    "valid phase bridge succession refuses a closed stored record"
)
MSG_SUCCESSION_ATTEMPT: Final[str] = (
    "valid phase bridge succession requires incoming attempt {expected}, got {actual}"
)
MSG_SUCCESSION_HISTORY: Final[str] = (
    "valid phase bridge succession requires incoming previous_attempts to extend stored"
)
MSG_STORED_RECORD_UNREADABLE: Final[str] = (
    "stored phase bridge record is unreadable: {reason}"
)
MSG_CLOSE_REASON: Final[str] = "phase bridge landing receipt={digest}"
STATUS_CLOSED: Final[str] = "closed"


class PhaseAdapterError(ValueError):
    """A phase operation was requested with incompatible durable evidence."""


class PhaseAdapter:
    """Perform only fixed Beads operations needed to admit one named stage."""

    def __init__(self, client: BdClient) -> None:
        self._client = client
        self.integration_guard: IntegrationGuard | None = None

    @classmethod
    def from_config(cls, config: BdConfig) -> PhaseAdapter:
        """Build the bridge's read/write adapter without exposing bd transport."""
        return cls(BdClient(config))

    def guard_integration(
        self, record: PhaseBridgeRecord, *, post_cas: bool = False
    ) -> None:
        """Integration records are unusable without their runtime authority."""
        if self.integration_guard is not None:
            from workflow_interpreter.foreman.replacement import guard_bridge

            guard_bridge(self.integration_guard.composition, record)
        elif record.successor_key is not None:
            raise PhaseAdapterError("successor bridge requires runtime guard")
        stored = self.show(record.stage_id).metadata.get(PHASE_BRIDGE_METADATA_KEY)
        if (
            isinstance(stored, dict)
            and stored.get("integration_digest") is not None
            and stored.get("integration_digest") != record.integration_digest
        ):
            raise PhaseAdapterError(
                "cannot strip or change stored integration authority"
            )
        if (
            isinstance(stored, dict)
            and stored.get("successor_key") is not None
            and (stored.get("successor_owner"), stored.get("successor_key"))
            != (record.successor_owner, record.successor_key)
        ):
            raise PhaseAdapterError("cannot strip or change stored successor authority")
        if record.integration_digest is None:
            if any(
                (
                    record.integration_owner,
                    record.integration_slot,
                    record.integration_generation is not None,
                )
            ):
                raise PhaseAdapterError("incomplete integration binding")
            return
        if self.integration_guard is None:
            raise PhaseAdapterError("integration requires runtime guard")
        if post_cas:
            self.integration_guard.post_cas(record)
        else:
            self.integration_guard.binding(record)

    def show(self, stage_id: str) -> BeadRecord:
        """Read one resolved stage by id."""
        return self._client.show(stage_id)

    def direct_children(self, epic_id: str) -> tuple[BeadRecord, ...]:
        """List only rows whose persisted parent is the named epic."""
        return tuple(
            bead
            for bead in self._client.list_children(epic_id)
            if bead.parent == epic_id
        )

    def dependencies(self, stage_id: str) -> tuple[DependencyRecord, ...]:
        """Inspect the selected stage's declared dependencies."""
        return self._client.list_dependencies(stage_id)

    def blocking_dependencies(self, stage_id: str) -> tuple[DependencyRecord, ...]:
        """Return only unfinished blocking dependencies for a selected stage."""
        return tuple(
            dependency
            for dependency in self.dependencies(stage_id)
            if dependency.dependency_type is DependencyType.BLOCKS
            and dependency.status != STATUS_CLOSED
        )

    def record(self, stage_id: str) -> PhaseBridgeRecord:
        """Read the complete bridge relation currently persisted on a stage."""
        return self._record(self.show(stage_id).metadata)

    def owns_root(self, instance_key: str, root_id: str) -> bool:
        """Require a uniquely persisted root, not an inferred key-shaped owner."""
        roots = find_roots(self._client, instance_key)
        return (
            len(roots) == 1
            and roots[0].id == root_id
            and roots[0].metadata.get("wf_root_id") == root_id
        )

    def has_root(self, instance_key: str) -> bool:
        """Report whether raw durable evidence exists for one bridge identity."""
        return bool(find_roots(self._client, instance_key))

    def prepare(self, stage_id: str, record: PhaseBridgeRecord) -> PhaseBridgeRecord:
        """Persist and read back a complete pre-claim admission intent."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.PREPARED, MSG_WRONG_INCOMING_STATE)
        existing = self.show(stage_id).metadata.get(PHASE_BRIDGE_METADATA_KEY)
        if existing is not None:
            try:
                stored_record = PhaseBridgeRecord.model_validate(existing)
            except ValidationError as exc:
                raise PhaseAdapterError(
                    MSG_STORED_RECORD_UNREADABLE.format(reason=exc)
                ) from exc
            if (
                stored_record.integration_digest is not None
                and record.integration_digest is None
            ):
                raise PhaseAdapterError("cannot strip stored integration authority")
            if (
                stored_record.successor_key is not None
                and record.successor_key is None
                and record.integration_digest is None
            ):
                raise PhaseAdapterError("cannot strip stored successor authority")
            self._assert_prepare_shape(stored_record, record)
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        return self._record(stored.metadata)

    def admit(
        self, stage_id: str, record: PhaseBridgeRecord, *, root_id: str
    ) -> PhaseBridgeRecord:
        """Atomically claim a stage while writing its complete admitted relation."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.PREPARED, MSG_WRONG_INCOMING_STATE)
        admitted = record.admitted(root_id)
        self.guard_integration(admitted)
        stored = self._client._claim_and_merge_metadata(
            stage_id, self._metadata(admitted)
        )
        return self._record(stored.metadata)

    def gate_red(self, stage_id: str, record: PhaseBridgeRecord) -> PhaseBridgeRecord:
        """Keep a failed verification eligible only for the explicit retry contract."""
        self._assert_stage(stage_id, record)
        self.guard_integration(record)
        updated = record.model_copy(update={"state": PhaseBridgeState.GATE_RED})
        stored = self._client._merge_metadata(stage_id, self._metadata(updated))
        return self._record(stored.metadata)

    def land(self, stage_id: str, record: PhaseBridgeRecord) -> PhaseBridgeRecord:
        """Persist and read back the artifact relation after a successful CAS."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.LANDED, MSG_WRONG_INCOMING_STATE)
        self.guard_integration(record, post_cas=True)
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        return self._record(stored.metadata)

    def close(
        self, stage_id: str, record: PhaseBridgeRecord, receipt_digest: str
    ) -> PhaseBridgeRecord:
        """Close and read back a stage whose durable relation names its receipt."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.CLOSED, MSG_WRONG_INCOMING_STATE)
        self.guard_integration(record, post_cas=True)
        if record.landing_receipt_digest != receipt_digest:
            raise PhaseAdapterError("close receipt does not match landed relation")
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        closed = finalize.close_forward(
            self._client,
            stored,
            MSG_CLOSE_REASON.format(digest=receipt_digest),
        )
        result = self._record(closed.metadata)
        if result.integration_digest is not None and self.integration_guard is not None:
            self.integration_guard.finished(result)
        return result

    @staticmethod
    def _metadata(record: PhaseBridgeRecord) -> Metadata:
        """Serialize the whole nested record because bd replaces nested objects."""
        return {
            PHASE_BRIDGE_METADATA_KEY: record.model_dump(by_alias=True, mode="json")
        }

    @staticmethod
    def _record(metadata: Mapping[str, object]) -> PhaseBridgeRecord:
        """Parse the durable bridge record read back from a stage."""
        return PhaseBridgeRecord.model_validate(metadata[PHASE_BRIDGE_METADATA_KEY])

    @staticmethod
    def _assert_stage(stage_id: str, record: PhaseBridgeRecord) -> None:
        """Refuse to write a record for a different stage."""
        if record.stage_id != stage_id:
            raise PhaseAdapterError(MSG_WRONG_STAGE.format(stage_id=stage_id))

    @staticmethod
    def _assert_state(
        record: PhaseBridgeRecord, state: PhaseBridgeState, message: str
    ) -> None:
        """Refuse a phase bridge record that is not in an expected lifecycle state."""
        if record.state is not state:
            raise PhaseAdapterError(
                message.format(state=state.value, actual=record.state.value)
            )

    @staticmethod
    def _assert_prepare_shape(
        stored: PhaseBridgeRecord, incoming: PhaseBridgeRecord
    ) -> None:
        """Allow only exact recovery or one non-closed successor journal."""
        if incoming.attempt == stored.attempt:
            if stored.state is not PhaseBridgeState.PREPARED:
                raise PhaseAdapterError(
                    MSG_IDEMPOTENT_STATE.format(actual=stored.state.value)
                )
            if incoming != stored:
                raise PhaseAdapterError(MSG_IDEMPOTENT_RECORD)
            return
        if stored.state is PhaseBridgeState.CLOSED:
            raise PhaseAdapterError(MSG_SUCCESSION_CLOSED)
        expected_attempt = stored.attempt + 1
        if incoming.attempt != expected_attempt:
            raise PhaseAdapterError(
                MSG_SUCCESSION_ATTEMPT.format(
                    expected=expected_attempt, actual=incoming.attempt
                )
            )
        if (
            incoming.epic_id != stored.epic_id
            or incoming.stage_id != stored.stage_id
            or incoming.target_ref != stored.target_ref
            or (
                incoming.integration_digest is None
                and incoming.expected_base_commit != stored.expected_base_commit
            )
            or incoming.verification_policy != stored.verification_policy
        ):
            raise PhaseAdapterError("successor changes admitted identity or policy")
        expected_history = (*stored.previous_attempts, stored.instance_key)
        if incoming.previous_attempts != expected_history:
            raise PhaseAdapterError(MSG_SUCCESSION_HISTORY)
