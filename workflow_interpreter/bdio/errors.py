"""Typed failures of the bd write boundary (spec v0.3 §0 threat model).

Every failure of the typed wrapper is one of these; a caller never sees a raw
`subprocess` or `json` exception. The hierarchy is flat on purpose — the
foreman routes on the class, not on a message.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checking only
    from workflow_interpreter.bdio.bounds import BoundRefusal

_MSG_COMMAND: Final[str] = "bd {subcommand} failed (exit {returncode}): {stderr}"
_MSG_TIMEOUT: Final[str] = "bd {subcommand} exceeded its {timeout_s}s timeout"
_MSG_FORBIDDEN: Final[str] = (
    "refused to construct a bd invocation outside the closed command set: {detail}"
)


class BdioError(Exception):
    """Base class for every failure raised by the typed bd wrapper."""


class BdConfigError(BdioError):
    """Injected configuration is unusable (missing path, workspace overlap)."""


class BdCommandError(BdioError):
    """bd exited non-zero."""

    def __init__(
        self, argv: Sequence[str], returncode: int, stderr: str, subcommand: str
    ) -> None:
        self.argv = tuple(argv)
        self.returncode = returncode
        self.stderr = stderr
        self.subcommand = subcommand
        super().__init__(
            _MSG_COMMAND.format(
                subcommand=subcommand, returncode=returncode, stderr=stderr.strip()
            )
        )


class BdTimeoutError(BdioError):
    """bd did not finish inside the configured timeout."""

    def __init__(self, argv: Sequence[str], timeout_s: float, subcommand: str) -> None:
        self.argv = tuple(argv)
        self.timeout_s = timeout_s
        self.subcommand = subcommand
        super().__init__(
            _MSG_TIMEOUT.format(subcommand=subcommand, timeout_s=timeout_s)
        )


class BdOutputError(BdioError):
    """bd's `--json` output could not be parsed, or had an unexpected shape."""


class ForbiddenInvocationError(BdioError):
    """An argv outside the closed command set was constructed.

    Structural, not advisory: the client asserts this before spawning, so a
    future edit that reaches for `--force` or `bd delete` fails loudly here
    instead of reaching bd (§0 write boundary).
    """

    def __init__(self, detail: str) -> None:
        super().__init__(_MSG_FORBIDDEN.format(detail=detail))


class LossyWriteError(BdioError):
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


class CarrierIntegrityError(BdioError):
    """A bd row does not carry the metadata the §3 encoding requires."""


class PinnedGraphMismatchError(BdioError):
    """The root's pinned body does not match its recorded hash (§3.1) — halt."""


class LifecycleConflictError(BdioError):
    """A state write contradicts the state already recorded (§5.1)."""


class BoundExceededError(BdioError):
    """A §10 pre-mint predicate refused the mint."""

    def __init__(self, refusal: BoundRefusal) -> None:
        self.refusal = refusal
        super().__init__(refusal.detail)


class BoundEvaluationError(BdioError):
    """A bound could not be evaluated — fail closed, never mint (§10)."""


class GateVerificationError(BdioError):
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


class CanaryFailedError(BdioError):
    """The §11 startup canary failed — refuse dispatch loudly."""
