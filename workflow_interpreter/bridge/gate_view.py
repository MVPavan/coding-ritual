"""Bridge-owned additions to the human gate view."""

from __future__ import annotations

from typing import Final

from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bridge.adapter import PhaseAdapter, PhaseAdapterError

_INSTANCE_KEY_PREFIX: Final[str] = "phase-bridge:"
_ATTEMPT_DELIMITER: Final[str] = ":attempt:"
MSG_INSTANCE_KEY_MISMATCH: Final[str] = (
    "phase bridge stage {stage_id!r} does not own root instance_key {instance_key!r}"
)


def phase_bridge_gate_view(instance_key: str, config: BdConfig) -> dict[str, object]:
    """Render retry evidence only for roots admitted through the phase bridge.

    The stage record remains the authority for attempts, so ordinary interpreter
    roots never receive bridge-specific metadata and do not cause an extra read.
    """
    stage_id = _stage_id(instance_key)
    if stage_id is None:
        return {}
    record = PhaseAdapter.from_config(config).record(stage_id)
    is_current_attempt = record.instance_key == instance_key
    if not is_current_attempt and instance_key not in record.previous_attempts:
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
    """Extract the stage segment from the bridge's own canonical root key."""
    if not instance_key.startswith(_INSTANCE_KEY_PREFIX):
        return None
    identity, delimiter, attempt = instance_key.rpartition(_ATTEMPT_DELIMITER)
    if not delimiter or not attempt.isdecimal() or int(attempt) < 1:
        return None
    _, separator, stage_id = identity.removeprefix(_INSTANCE_KEY_PREFIX).partition(":")
    return stage_id if separator and stage_id else None
