"""The closed Beads surface used by phase admission."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from workflow_interpreter.bdio import finalize
from workflow_interpreter.bdio.client import BdClient, DependencyRecord
from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.wire import BeadRecord, Metadata
from workflow_interpreter.bridge.models import PhaseBridgeRecord, PhaseBridgeState

PHASE_BRIDGE_METADATA_KEY: Final[str] = "phase_bridge"
MSG_WRONG_STAGE: Final[str] = "phase bridge record belongs to stage {stage_id!r}"
MSG_WRONG_STATE: Final[str] = "expected phase bridge state {state!r}, got {actual!r}"
MSG_CLOSE_REASON: Final[str] = "phase bridge landing receipt={digest}"


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

    def record(self, stage_id: str) -> PhaseBridgeRecord:
        """Read the complete bridge relation currently persisted on a stage."""
        return self._record(self.show(stage_id).metadata)

    def prepare(self, stage_id: str, record: PhaseBridgeRecord) -> PhaseBridgeRecord:
        """Persist and read back a complete pre-claim admission intent."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.PREPARED)
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        return self._record(stored.metadata)

    def admit(
        self, stage_id: str, record: PhaseBridgeRecord, *, root_id: str
    ) -> PhaseBridgeRecord:
        """Atomically claim a stage while writing its complete admitted relation."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.PREPARED)
        admitted = record.admitted(root_id)
        stored = self._client._claim_and_merge_metadata(
            stage_id, self._metadata(admitted)
        )
        return self._record(stored.metadata)

    def land(self, stage_id: str, record: PhaseBridgeRecord) -> PhaseBridgeRecord:
        """Persist and read back the artifact relation after a successful CAS."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.LANDED)
        stored = self._client._merge_metadata(stage_id, self._metadata(record))
        return self._record(stored.metadata)

    def close(
        self, stage_id: str, record: PhaseBridgeRecord, receipt_digest: str
    ) -> PhaseBridgeRecord:
        """Close and read back a stage whose durable relation names its receipt."""
        self._assert_stage(stage_id, record)
        self._assert_state(record, PhaseBridgeState.CLOSED)
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
    def _assert_state(record: PhaseBridgeRecord, state: PhaseBridgeState) -> None:
        """Keep prepare and admission from overwriting later lifecycle states."""
        if record.state is not state:
            raise PhaseAdapterError(
                MSG_WRONG_STATE.format(state=state.value, actual=record.state.value)
            )
