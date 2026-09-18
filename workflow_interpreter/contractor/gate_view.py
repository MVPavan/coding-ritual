"""Contractor-owned additions to the human gate view."""

from __future__ import annotations

from typing import Final

from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.contractor.adapter import PhaseAdapter, PhaseAdapterError

_INSTANCE_KEY_PREFIX: Final[str] = "contract:"
_ATTEMPT_DELIMITER: Final[str] = ":attempt:"
MSG_INSTANCE_KEY_MISMATCH: Final[str] = (
    "contractor stage {stage_id!r} does not own root instance_key {instance_key!r}"
)


def contractor_gate_view(
    instance_key: str, config: BdConfig, *, root_id: str, reads: WorkflowReads
) -> dict[str, object]:
    """Render retry evidence only for roots admitted through the contractor.

    The stage record remains the authority for attempts, so ordinary interpreter
    roots never receive contractor-specific metadata and do not cause an extra read.

    `config` builds the TASK bead's transport, which stays bd (§3.2), and
    `reads` is the store THIS ROOT is pinned to: `owns_root` is a root lookup,
    and a contractor view that asked bd about a ledger-backed root would answer
    that a live run does not exist.
    """
    stage_id = _stage_id(instance_key)
    if stage_id is None:
        return {}
    adapter = PhaseAdapter.from_config(config, reads)
    record = adapter.record(stage_id)
    is_current_attempt = record.instance_key == instance_key
    if (
        record.stage_id != stage_id
        or adapter.show(stage_id).parent != record.epic_id
        or not adapter.owns_root(instance_key, root_id)
        or (is_current_attempt and record.root_id != root_id)
        or (not is_current_attempt and instance_key not in record.previous_attempts)
    ):
        raise PhaseAdapterError(
            MSG_INSTANCE_KEY_MISMATCH.format(
                stage_id=stage_id, instance_key=instance_key
            )
        )
    return {
        "attempt": record.attempt,
        "is_current_attempt": is_current_attempt,
        "previous_attempts": record.previous_attempts,
    }


def _stage_id(instance_key: str) -> str | None:
    """Extract the stage segment from the contractor's own canonical root key."""
    if not instance_key.startswith(_INSTANCE_KEY_PREFIX):
        return None
    identity, delimiter, attempt = instance_key.rpartition(_ATTEMPT_DELIMITER)
    if not delimiter or not attempt.isdecimal() or int(attempt) < 1:
        return None
    _, separator, stage_id = identity.removeprefix(_INSTANCE_KEY_PREFIX).partition(":")
    return stage_id if separator and stage_id else None
