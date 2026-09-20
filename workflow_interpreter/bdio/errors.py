"""Typed failures of the store boundary (spec v0.3 §0 threat model).

Every failure of the typed wrapper is one of these; a caller never sees a raw
`subprocess` or `json` exception. The names above the seam are backend-neutral
— `StoreError` and its neutral subclasses — so a caller routes on what went
wrong, never on which backend it happened in. The backend-specific shapes live with the backend that raises them —
`tracker/errors.py` since S6, because bd is a TRACKER now (R1) — and every one
of them is a `StoreTransportError`, which is the only name a caller above the
seam is allowed to catch.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checking only
    from workflow_interpreter.bdio.bounds import BoundRefusal


class StoreError(Exception):
    """Base class for every failure raised by the workflow store."""


class StoreConfigError(StoreError):
    """Injected configuration is unusable (missing path, workspace overlap)."""


class StoreTransportError(StoreError):
    """The backend's transport failed; its shape is the backend's private detail.

    Above the seam this is the only transport failure that exists: a caller
    that catches `BdCommandError` has pinned itself to one backend.
    """


class StoreBusyRefusal(StoreError):
    """A backend was contended past its bounded wait and REFUSED the write.

    Neutral on purpose: the ledger raises it (`ledger/errors.py`), and the
    activation-aware boundary above the seam records it as a deviation without
    learning that SQLite exists. bd never raises it — its transport has no
    write lock to wait on — so a caller that handles it is not thereby pinned
    to one backend.
    """


class StoreOutputError(StoreTransportError):
    """The backend answered, but not in a shape this wrapper can read.

    Distinct from its siblings on purpose: a command that failed, timed out or
    was refused before it ran is a transport DEFECT, while an unreadable answer
    is a store the caller may legitimately treat as "no usable record". Only
    this class may be converted into an ordinary refusal above the seam.
    """


class LossyWriteError(StoreError):
    """A write did not read back as written.

    bd's extension surfaces are lossy by default (probed: `--event-payload
    @file` stores the literal string; `--set-metadata` stringifies structured
    values; large integers lose precision through the JSON float path). Every
    write is therefore read back and compared; a silent drop raises.
    """

    def __init__(self, bead_id: str, surface: str, detail: str) -> None:
        self.bead_id = bead_id
        self.surface = surface
        super().__init__(f"lossy bd write on {bead_id} ({surface}): {detail}")


class CarrierIntegrityError(StoreError):
    """A bd row does not carry the metadata the §3 encoding requires."""


class PinnedGraphMismatchError(StoreError):
    """The root's pinned body does not match its recorded hash (§3.1) — halt."""


class LifecycleConflictError(StoreError):
    """A state write contradicts the state already recorded (§5.1)."""


class BoundExceededError(StoreError):
    """A §10 pre-mint predicate refused the mint."""

    def __init__(self, refusal: BoundRefusal) -> None:
        self.refusal = refusal
        super().__init__(refusal.detail)


class BoundEvaluationError(StoreError):
    """A bound could not be evaluated — fail closed, never mint (§10)."""


class GateVerificationError(StoreError):
    """Base class for every §9 refusal; a gate never closes on one of these."""


class SignatureRefusedError(GateVerificationError):
    """The detached signature does not verify over the canonical payload."""


class SignerNotAllowedError(GateVerificationError):
    """The signing key's fingerprint is not on the pinned allow-list (§9)."""


class PayloadMismatchError(GateVerificationError):
    """A verified payload does not describe this gate (§9 cross-checks)."""


class NonceReplayError(GateVerificationError):
    """The payload's nonce was already consumed by a closed gate (§9)."""


class StaleApprovalError(GateVerificationError):
    """A `binds = "mutable"` document changed after gate-open (§9)."""


class CanaryFailedError(StoreError):
    """The §11 startup canary failed — refuse dispatch loudly."""
