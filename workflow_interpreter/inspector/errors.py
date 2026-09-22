"""Typed failures of the inspector wrapper (spec v0.3 §5–§8, §12).

Flat hierarchy, like `bdio.errors`: the foreman routes on the class, never on a
message. Every one of these is a REFUSAL — the inspector's job is to fail
loudly rather than dispatch a child whose preconditions were not proven.
"""

from __future__ import annotations

from enum import StrEnum


class InspectorError(Exception):
    """Base class for every failure raised by the inspector wrapper."""


class InspectorConfigError(InspectorError):
    """Injected configuration is unusable (relative path, missing repo)."""


class WrapperDirError(InspectorError):
    """The wrapper directory could not be read or written durably."""


class ForkBarrierError(InspectorError):
    """The child never reached the barrier, or crossed it without a receipt (§5.2)."""


class ForkBarrierAbortError(ForkBarrierError):
    """An unacknowledged barrier child was aborted and was never a crew (§5.2)."""


class ExecLedgerError(InspectorError):
    """The exec ledger disagrees with what the launch claims happened (§5.2)."""


class GitCommandError(InspectorError):
    """A git invocation failed, timed out, or was outside the closed set."""


class PreconditionRefused(InspectorError):
    """The §5.4 worktree precondition does not hold and cannot be repaired."""


class SnapshotFailed(InspectorError):
    """A pre-destruction snapshot could not be safely created or pinned."""


class InterruptedWorkPreservationFailed(SnapshotFailed):
    """Producer recovery failed; leave its activation open until preservation retries."""


class BandNotHeld(PreconditionRefused):
    """An in-repo caller omitted the already-required execution band."""


class DirtyTreeRefused(PreconditionRefused):
    """§12: resetting would destroy work the wrapper cannot attribute to the crew.

    Tier-2 human confirmation naming the exact paths is the only release; the
    inspector never auto-resets its way out of this one. `protected_head` is
    set when the thing at risk is a COMMIT rather than a file — HEAD sits on
    something no wrapper ref pins, so `reset --hard` would orphan it.
    """

    def __init__(
        self,
        detail: str,
        protected_paths: tuple[str, ...],
        *,
        protected_head: str | None = None,
    ) -> None:
        self.protected_paths = protected_paths
        self.protected_head = protected_head
        super().__init__(detail)


class ResumeMismatchReason(StrEnum):
    """Why a resumed writer's tree proof failed (§3)."""

    MISSING_SNAPSHOT = "missing_snapshot"
    """The selected source carries no session id or no pinned tree OID, so
    there is nothing to prove the shared checkout against."""
    INTERVENING_WRITER = "intervening_writer"
    """The checkout no longer holds the tree the session was left on: somebody
    else wrote it between the two turns."""


class ResumeTreeMismatch(PreconditionRefused):
    """§3: the shared checkout is not the tree this vendor session remembers.

    A refusal rather than a fresh fallback, deliberately: launching fresh would
    reset a tree whose session was SELECTED for exactly the state it holds, and
    the OIDs an owner needs in order to inspect or recover it would be gone
    with it. The owner may mint fresh explicitly afterwards.
    """

    def __init__(
        self,
        detail: str,
        *,
        reason: ResumeMismatchReason,
        expected: str | None = None,
        observed: str | None = None,
    ) -> None:
        self.reason = reason
        self.expected = expected
        self.observed = observed
        super().__init__(detail)


class ReadOnlyTreeMutation(InspectorError):
    """§3: a non-writing activation's checkout changed while it ran.

    Best-effort by construction — a steered or crashed reviewer never reaches
    the check at all — so it states what WAS observed and never stands in for
    the next resumed writer's mandatory match.
    """


class SandboxUnavailable(InspectorError):
    """This host cannot hold the §2 mount bound, so no dispatch may happen (O1).

    Permanent by nature — a missing `bwrap` or a self-test that does not enforce
    will not fix itself on a retry — so the foreman closes it as a dead end
    rather than burning §10.2 infra retries on it.
    """


class SandboxPathRefused(SandboxUnavailable):
    """A path could not be made into a mount bind the bound may safely carry.

    Defence in depth behind the §4 schema pattern: a grant resolving outside the
    checkout, or a mandatory read-only root that is not on disk. Refusing here
    beats handing bwrap a bad bind source, which fails as an ambiguous `rc=1`
    (plan §8). It is a permanent bound refusal, so inheriting
    `SandboxUnavailable` sends it through the same retry-exempt halt path.
    """


class LockUnavailable(InspectorError):
    """The §12 in-repo execution band is held by another crew."""


class ContinuationRefused(InspectorError):
    """A §8.1 continuation has nothing to continue WITH, at either end.

    §8.1 mints exactly one continuation and dispatches it via
    `build_resume_command`. Falling back to `build_command` there would start a
    fresh session carrying the node's ORIGINAL brief, so the human's steer would
    vanish silently and the round would simply be re-run — the one outcome a
    steer exists to prevent.

    One class for both ends of that sentence, because the foreman's remediation
    is the same one (do not treat this steer as taken):

    - `Steerer.steer` raises it when the activation has no resumable session,
      BEFORE the intent is written and the child is killed. `build_resume_command`
      also refuses an empty session, but by then the crew is dead and the
      activation is closed `steered` — a refusal that costs the work it was
      protecting is not fail-closed.
    - `Dispatcher.dispatch` raises it when a `steer-continuation` reaches the
      launch with no instructions, and when instructions reach a mint that is
      not one.
    """


class TerminationFailed(InspectorError):
    """A child survived TERM and KILL, so no proof of death exists (§8.1)."""


class VerifyTreeError(InspectorError):
    """The §7.3 checks have no trustworthy tree to run in.

    Loud on purpose. The alternative is grading whatever tree happens to be
    there, which is how a check ends up passing on content the artifact commit
    does not contain (§7.3, §7.4).
    """


# Deliberately absent: a `MarkerError` and a `VerifierProvenanceError`.
# §6 and §7.3 both say a bad marker and an edited examiner are `fail_code`
# plus an audit flag — a VERDICT, computed and recorded. Raising instead would
# skip the exit record §7.1 depends on and route nothing at all.
