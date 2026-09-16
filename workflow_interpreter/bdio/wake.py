"""Idempotent notification writes through the same guarded bd event transport."""

from typing import Final

from workflow_interpreter.bdio import reads
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import CarrierIntegrityError, StoreError
from workflow_interpreter.bdio.keys import wake_fire_key
from workflow_interpreter.bdio.records import RowRecord, parse_event, parse_row
from workflow_interpreter.bdio.wire import (
    KEY_WF_KIND,
    KEY_WF_ROOT_ID,
    EventMetadata,
    IssueType,
    WfKind,
    metadata_dict,
)
from workflow_interpreter.contracts.wake import WakeEvent

MSG_WAKE_IDENTITY: Final[str] = "wake event disagrees with its root or fire key"
MSG_WAKE_CHANGED: Final[str] = "wake fire key already records a different payload"
FIRST_WAKE_SEQ: Final[int] = -1
"""Wake seq decreases monotonically, independently of nonnegative driver seq."""
TITLE_WAKE: Final[str] = "wake {condition} {root_id}"


def _existing(client: BdClient, root_id: str, event: WakeEvent) -> RowRecord | None:
    """Re-find and verify identical evidence, including after an ambiguous write."""
    found = reads.find_event(client, root_id, event.fire_key)
    if found is not None and parse_event(found) != event:
        raise CarrierIntegrityError(MSG_WAKE_CHANGED)
    return found


def append_wake_event(client: BdClient, root_id: str, event: WakeEvent) -> RowRecord:
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
    # Include metadata-only wake carriers: losing payload cannot free a slot.
    metadata = EventMetadata(
        wf_root_id=root_id,
        event_key=event.fire_key,
        seq=min(
            0,
            min(
                (
                    EventMetadata.model_validate(bead.metadata).seq
                    for bead in client.list_beads(
                        metadata_filters={
                            KEY_WF_ROOT_ID: root_id,
                            KEY_WF_KIND: WfKind.EVENT.value,
                        },
                        issue_type=IssueType.EVENT,
                    )
                ),
                default=0,
            ),
        )
        + FIRST_WAKE_SEQ,
    )
    try:
        return parse_row(
            client._create_bead(
                title=TITLE_WAKE.format(
                    condition=event.condition.value, root_id=root_id
                ),
                metadata=metadata_dict(metadata),
                issue_type=IssueType.EVENT,
                event_payload=metadata_dict(event),
            )
        )
    except StoreError:
        existing = _existing(client, root_id, event)
        if existing is not None:
            return existing
        raise
