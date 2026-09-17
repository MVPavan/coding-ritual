"""Which task and which attempt a root belongs to (run-ledger §2, §3.7).

The run identity is PINNED on the root at creation and read back from the root
record. It is never recovered by parsing a root id: `<task>-a<n>` is a ledger
convention (D8), bd-minted ids carry no such structure at all, and a debrief
that wrote its evidence into a directory named by a parsed id would be naming
it after a string rather than after a fact.

The epic segment is the one part that IS derived, because §2 defines it as a
deterministic function of the task id — the parent prefix of a dotted bead id,
the id itself when it is undotted — and not as a bd lookup.
"""

from __future__ import annotations

from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

EPIC_SEPARATOR: Final[str] = "."
FIRST_ATTEMPT: Final[int] = 1
"""Attempts are counted from one; `a0` names no run (§3.7, D16)."""

MODEL: Final[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

SAFE_COMPONENT_PATTERN: Final[str] = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"
"""One safe path component, and the same expression `scripts/verify-debrief.sh`
re-applies to the identity it is handed.

The identity is interpolated into a repository path and compared against the
paths a commit touched, so a task id containing `/` or `..` would not name a
directory but redefine one, and a regex metacharacter would silently widen the
comparison. A leading `.` is excluded too: `..` is the traversal, and no bead
id starts with a dot. `scripts/verify-debrief.sh` re-applies the same rule as a
POSIX `case` glob rather than a regex, because the shell side must not depend
on a regex dialect to decide containment."""

SafeComponent = Annotated[str, StringConstraints(pattern=SAFE_COMPONENT_PATTERN)]


def epic_segment(task_id: str) -> str:
    """The parent prefix of a dotted bead id — deterministic, no bd lookup (§2)."""
    head, separator, _ = task_id.partition(EPIC_SEPARATOR)
    return head if separator else task_id


class RunIdentity(BaseModel):
    """The task bead and attempt number one root is an attempt at (D16, §3.7)."""

    model_config = MODEL

    task_id: SafeComponent
    attempt: Annotated[int, Field(ge=FIRST_ATTEMPT)]

    @property
    def epic_segment(self) -> str:
        """The `docs/workstreams/<segment>/` this run's knowledge belongs under."""
        return epic_segment(self.task_id)

    @property
    def run_directory(self) -> str:
        """The one repo-relative directory a debrief of this run may write."""
        return (
            f"docs/workstreams/{self.epic_segment}/runs/{self.task_id}/a{self.attempt}"
        )
