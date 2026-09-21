"""What a tracker can fail with (§3.3).

Two shapes for the PORT — writes never raise, they answer `Applied`,
`Conflict` or `Unknown`, because a write that raised would put the decision
about a landed commit in an exception handler; reads raise, because a read has
no desired state to fall back on — and the bd TRANSPORT's own failures, which
moved here in S6 when bd stopped being a record store (R1). Those stay
`StoreTransportError` subclasses: that is the one name a caller above the
store seam is allowed to catch, and a bd transport defect is still one.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from workflow_interpreter.bdio.errors import StoreOutputError, StoreTransportError

_MSG_COMMAND: Final[str] = "bd {subcommand} failed (exit {returncode}): {stderr}"
_MSG_TIMEOUT: Final[str] = "bd {subcommand} exceeded its {timeout_s}s timeout"
_MSG_UNAVAILABLE: Final[str] = "bd {subcommand} could not be run: {reason}"
_MSG_FORBIDDEN: Final[str] = (
    "refused to construct a bd invocation outside the closed command set: {detail}"
)


class TrackerUnavailable(RuntimeError):
    """The tracker could not be reached. Retryable."""


class TrackerRefused(RuntimeError):
    """The tracker answered, and the answer was no. Permanent."""


class BdCommandError(StoreTransportError):
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


class BdTimeoutError(StoreTransportError):
    """bd did not finish inside the configured timeout."""

    def __init__(self, argv: Sequence[str], timeout_s: float, subcommand: str) -> None:
        self.argv = tuple(argv)
        self.timeout_s = timeout_s
        self.subcommand = subcommand
        super().__init__(
            _MSG_TIMEOUT.format(subcommand=subcommand, timeout_s=timeout_s)
        )


class BdUnavailableError(StoreTransportError):
    """The bd binary could not be executed at all (missing, not executable).

    A defect of the transport, not an answer about the caller's ids: the
    crew raises `OSError` before bd ever runs, and mapping it here is what
    keeps a broken installation from reading as an ordinary refusal.
    """

    def __init__(self, argv: Sequence[str], subcommand: str, reason: str) -> None:
        self.argv = tuple(argv)
        self.subcommand = subcommand
        super().__init__(_MSG_UNAVAILABLE.format(subcommand=subcommand, reason=reason))


class BdOutputError(StoreOutputError):
    """bd's `--json` output could not be parsed, or had an unexpected shape."""


class BdItemMissing(BdOutputError):
    """bd answered, in the shape this wrapper reads, that it holds no such row.

    The ONE unreadable answer that is a fact about the ITEM rather than about
    the store: `bd show` returning an empty array says the id is not there.
    Its parent says only "bd's output was not usable", which invalid or
    truncated JSON also says — and reading THAT as "no item" let a real,
    non-closed bead be mistaken for an absent one (cr-m6am).
    """


class ForbiddenInvocationError(StoreTransportError):
    """An argv outside the closed command set was constructed.

    Structural, not advisory: the client asserts this before spawning, so a
    future edit that reaches for `--force` or `bd delete` fails loudly here
    instead of reaching bd (§0 write boundary).
    """

    def __init__(self, detail: str) -> None:
        super().__init__(_MSG_FORBIDDEN.format(detail=detail))
