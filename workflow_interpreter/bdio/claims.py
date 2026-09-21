"""Integration-target claims — the one shared row two runs contend for (§3.2).

A claim is not a workflow carrier: it has no root, no `seq` and no lifecycle.
It exists so that two attempts aiming at one integration target serialise, and
it is therefore read and written by the contractor rather than by the foreman.

What lives here is the SHAPE — the record and the surface a caller programs
against. The implementation is `ledger.claims.LedgerClaims` (R11): claims are
ledger-local now, and `bdio` may not import the ledger, so the surface is a
protocol and the composition root supplies the one that answers it.

The payload stays opaque. What a claim MEANS is the contractor's model; what
the store owns is the key it is found by and the holder it is held by.
"""

from __future__ import annotations

from typing import Final, Protocol

from pydantic import BaseModel

from workflow_interpreter.bdio.wire import ROW_MODEL, Metadata

CLAIM_KEY: Final[str] = "integration_target_key"
"""The metadata key a claim payload states its target under."""


class ClaimRecord(BaseModel):
    """One claim: the target it names, who holds it, and what it carries."""

    model_config = ROW_MODEL

    id: str
    holder: str
    payload: Metadata


class ClaimStore(Protocol):
    """Read a target's claim, take it, or move one already held.

    Taking and moving are one method with one distinguishing argument rather
    than two methods, because the caller's evidence is what tells them apart:
    a caller that read no claim must LOSE a race for the target, and a caller
    that read its own claim is entitled to move it.

    That evidence is the HOLDER it read, so the move is a compare-and-swap: a
    transfer written from a stale read names a holder that has since changed,
    and is refused rather than applied over whoever holds the target now.
    """

    def find(self, key: str) -> tuple[ClaimRecord, ...]:
        """Every claim row carrying `key` — at most one."""
        ...

    def write(
        self,
        key: str,
        holder: str,
        payload: Metadata,
        expected_holder: str | None = None,
    ) -> None:
        """Claim the target, or move the claim `expected_holder` still holds."""
        ...
