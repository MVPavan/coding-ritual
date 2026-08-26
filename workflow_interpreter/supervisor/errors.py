"""Typed failures of the supervisor wrapper (spec v0.3 §5–§8, §12).

Flat hierarchy, like `bdio.errors`: the foreman routes on the class, never on a
message. Every one of these is a REFUSAL — the supervisor's job is to fail
loudly rather than dispatch a child whose preconditions were not proven.
"""

from __future__ import annotations


class SupervisorError(Exception):
    """Base class for every failure raised by the supervisor wrapper."""


class SupervisorConfigError(SupervisorError):
    """Injected configuration is unusable (relative path, missing repo)."""


class WrapperDirError(SupervisorError):
    """The wrapper directory could not be read or written durably."""


class ForkBarrierError(SupervisorError):
    """The child never reached the barrier, or crossed it without a receipt (§5.2)."""


class ExecLedgerError(SupervisorError):
    """The exec ledger disagrees with what the launch claims happened (§5.2)."""


class GitCommandError(SupervisorError):
    """A git invocation failed, timed out, or was outside the closed set."""


class PreconditionRefused(SupervisorError):
    """The §5.4 worktree precondition does not hold and cannot be repaired."""


class DirtyTreeRefused(PreconditionRefused):
    """§12: resetting would destroy work the wrapper cannot attribute to the runner.

    Tier-2 human confirmation naming the exact paths is the only release; the
    supervisor never auto-resets its way out of this one. `protected_head` is
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


class LockUnavailable(SupervisorError):
    """The §12 in-repo execution band is held by another runner."""


class ContinuationRefused(SupervisorError):
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
      also refuses an empty session, but by then the runner is dead and the
      activation is closed `steered` — a refusal that costs the work it was
      protecting is not fail-closed.
    - `Dispatcher.dispatch` raises it when a `steer-continuation` reaches the
      launch with no instructions, and when instructions reach a mint that is
      not one.
    """


class TerminationFailed(SupervisorError):
    """A child survived TERM and KILL, so no proof of death exists (§8.1)."""


class VerifyTreeError(SupervisorError):
    """The §7.3 checks have no trustworthy tree to run in.

    Loud on purpose. The alternative is grading whatever tree happens to be
    there, which is how a check ends up passing on content the artifact commit
    does not contain (§7.3, §7.4).
    """


# Deliberately absent: a `MarkerError` and a `VerifierProvenanceError`.
# §6 and §7.3 both say a bad marker and an edited examiner are `fail_code`
# plus an audit flag — a VERDICT, computed and recorded. Raising instead would
# skip the exit record §7.1 depends on and route nothing at all.
