"""Idempotent notification writes through the same guarded bd event transport."""

from typing import Final

from workflow_interpreter.bdio import reads
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import BdioError, CarrierIntegrityError
from workflow_interpreter.bdio.keys import wake_fire_key
from workflow_interpreter.bdio.records import parse_event
from workflow_interpreter.bdio.wire import (
    BeadRecord,
    EventMetadata,
    IssueType,
    metadata_dict,
)
from workflow_interpreter.contracts.wake import WakeEvent

MSG_WAKE_IDENTITY: Final[str] = "wake event disagrees with its root or fire key"
MSG_WAKE_CHANGED: Final[str] = "wake fire key already records a different payload"
FIRST_WAKE_SEQ: Final[int] = -1
"""Wake notifications occupy negative seq; driver carriers start at zero."""
TITLE_WAKE: Final[str] = "wake {condition} {root_id}"


def _existing(client: BdClient, root_id: str, event: WakeEvent) -> BeadRecord | None:
    """Re-find and verify identical evidence, including after an ambiguous write."""
    found = reads.find_event(client, root_id, event.fire_key)
    if found is not None and parse_event(found) != event:
        raise CarrierIntegrityError(MSG_WAKE_CHANGED)
    return found


def append_wake_event(client: BdClient, root_id: str, event: WakeEvent) -> BeadRecord:
    """Append a notification without a mint, gate close, nonce or budget mutation."""
    event = WakeEvent.model_validate(event.model_dump())
    root = reads.load_root(client, root_id)
    if (
        event.root_id != root_id
        or event.instance_key != root.metadata.instance_key
        or event.fire_key
        != wake_fire_key(
            event.root_id, event.instance_key, event.condition, event.cursor
        )
        or event.fired_at is None
    ):
        raise CarrierIntegrityError(MSG_WAKE_IDENTITY)
    existing = _existing(client, root_id, event)
    if existing is not None:
        return existing
    metadata = EventMetadata(
        wf_root_id=root_id,
        event_key=event.fire_key,
        seq=FIRST_WAKE_SEQ - len(reads.list_wake_events(client, root_id)),
    )
    try:
        return client._create_bead(
            title=TITLE_WAKE.format(condition=event.condition.value, root_id=root_id),
            metadata=metadata_dict(metadata),
            issue_type=IssueType.EVENT,
            event_payload=metadata_dict(event),
        )
    except BdioError:
        existing = _existing(client, root_id, event)
        if existing is not None:
            return existing
        raise
