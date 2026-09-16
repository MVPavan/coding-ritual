"""Integration-target claims — the one shared row two runs contend for (§3.2).

A claim is not a workflow carrier: it has no root, no `seq` and no lifecycle.
It exists so that two attempts aiming at one integration target serialise, and
it is therefore read and written by the bridge rather than by the foreman. It
still goes through the seam: a bridge that reached the transport for this one
row would be a second write path into the store (§0.1).

The payload stays opaque here. What a claim MEANS is the bridge's model; what
the store owns is the key it is found by and the row it lives on.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel

from workflow_interpreter.bdio.backend import StoreBackend
from workflow_interpreter.bdio.rows import NewRow, RowQuery
from workflow_interpreter.bdio.wire import ROW_MODEL, Metadata

CLAIM_KEY: Final[str] = "integration_target_key"
"""The metadata key a claim row is selected by."""

CLAIM_TITLE: Final[str] = "Integration target claim"


class ClaimRecord(BaseModel):
    """One claim row: the id it lives on and the payload it carries."""

    model_config = ROW_MODEL

    id: str
    payload: Metadata


class ClaimStore:
    """The claims surface of a `WorkflowStore` — read, then create or merge."""

    def __init__(self, backend: StoreBackend) -> None:
        self._backend = backend

    def find(self, key: str) -> tuple[ClaimRecord, ...]:
        """Every claim row carrying `key`.

        More than one is a contention defect the CALLER decides about: the
        store does not get to pick a winner among rows whose meaning it
        cannot read.
        """
        return tuple(
            ClaimRecord(id=row.id, payload=row.metadata)
            for row in self._backend.find_rows(
                RowQuery(metadata_filters={CLAIM_KEY: key})
            )
        )

    def write(self, key: str, payload: Metadata, claim_id: str | None = None) -> None:
        """Create the claim row, or merge the payload into the named one."""
        data: Metadata = {CLAIM_KEY: key, **payload}
        if claim_id is None:
            self._backend._create_row(NewRow(summary=CLAIM_TITLE, metadata=data))
            return
        self._backend._merge_metadata(claim_id, data)
