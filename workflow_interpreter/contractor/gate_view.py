"""Contractor-owned additions to the human gate view."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from workflow_interpreter.contractor.adapter import ContractorAdapterError
from workflow_interpreter.contractor.tracker_wiring import adapter_of

if TYPE_CHECKING:
    from workflow_interpreter.foreman.compose import Composition

_INSTANCE_KEY_PREFIX: Final[str] = "contract:"
_ATTEMPT_DELIMITER: Final[str] = ":attempt:"
MSG_INSTANCE_KEY_MISMATCH: Final[str] = (
    "contractor stage {stage_id!r} does not own root instance_key {instance_key!r}"
)


def contractor_gate_view(
    instance_key: str,
    composition: Composition,
    *,
    root_id: str,
) -> dict[str, object]:
    """Render retry evidence only for roots admitted through the contractor.

    The stage record remains the authority for attempts, so ordinary interpreter
    roots never receive contractor-specific metadata and do not cause an extra read.

    The COMPOSITION is what it takes, rather than a config, a `reads` and a
    record store: the adapter is wired in one place now (§3.3), and the reads
    it needs are the store THIS ROOT is pinned to — `owns_root` is a root
    lookup, and a contractor view that asked bd about a ledger-backed root
    would answer that a live run does not exist.
    """
    stage_id = _stage_id(instance_key)
    if stage_id is None:
        return {}
    adapter = adapter_of(composition, composition.reads_for_root(root_id))
    record = adapter.record(stage_id)
    is_current_attempt = record.instance_key == instance_key
    # The CONFIGURED tracker, and an absent item contradicts nothing (R9): a
    # null tracker holds none at all, and a view that refused for the lack of
    # one would make the gate unreadable on every tracker but bd.
    item = adapter.item(stage_id)
    if (
        record.stage_id != stage_id
        or (item is not None and item.parent != record.epic_id)
        or not adapter.owns_root(instance_key, root_id)
        or (is_current_attempt and record.root_id != root_id)
        or (not is_current_attempt and instance_key not in record.previous_attempts)
    ):
        raise ContractorAdapterError(
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
