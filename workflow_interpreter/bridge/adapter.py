"""The closed Beads surface used by phase admission."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from pydantic import ValidationError

from workflow_interpreter.bdio import finalize
from workflow_interpreter.bdio.client import BdClient, DependencyRecord, DependencyType
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.reads import find_roots
from workflow_interpreter.bdio.wire import BeadRecord, Metadata
from workflow_interpreter.bridge.models import PhaseBridgeRecord, PhaseBridgeState

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

    @classmethod
    def from_config(cls, config: BdConfig) -> PhaseAdapter:
        """Build the bridge's read/write adapter without exposing bd transport."""
        return cls(BdClient(config))

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
        stored = self._client._claim_and_merge_metadata(
            stage_id, self._metadata(admitted)
        )
        return self._record(stored.metadata)

    def land(self, stage_id: str, record: PhaseBridgeRecord) -> PhaseBridgeRecord:
        """Persist and read back the artifact relation after a successful CAS."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.LANDED, MSG_WRONG_INCOMING_STATE)
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        return self._record(stored.metadata)

    def close(
        self, stage_id: str, record: PhaseBridgeRecord, receipt_digest: str
    ) -> PhaseBridgeRecord:
        """Close and read back a stage whose durable relation names its receipt."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.CLOSED, MSG_WRONG_INCOMING_STATE)
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        closed = finalize.close_forward(
            self._client,
            stored,
            MSG_CLOSE_REASON.format(digest=receipt_digest),
        )
        return self._record(closed.metadata)

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
        expected_history = (*stored.previous_attempts, stored.instance_key)
        if incoming.previous_attempts != expected_history:
            raise PhaseAdapterError(MSG_SUCCESSION_HISTORY)
