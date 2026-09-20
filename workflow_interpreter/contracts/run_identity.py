"""Which task, which epic and which attempt a root belongs to (§3.7, R8).

The run identity is PINNED on the root at creation and read back from the root
record. It is never recovered by parsing a root id: `<task>-a<n>` is a ledger
convention (D8), a tracker-minted id carries no such structure at all, and a
debrief that wrote its evidence into a directory named by a parsed id would be
naming it after a string rather than after a fact.

The epic is an INPUT for the same reason. It used to be derived from the task
id — the parent prefix of a dotted bead id — which made `tasks.epic_id` a
restatement of the key it hangs off and tied the engine to one tracker's id
shape. It is now supplied at mint and carried here, so the column and this
model answer with what a human named rather than with a parse.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Final

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

FIRST_ATTEMPT: Final[int] = 1
"""Attempts are counted from one; `a0` names no run (§3.7, D16)."""

MODEL: Final[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

SAFE_COMPONENT_PATTERN: Final[str] = r"[A-Za-z0-9][A-Za-z0-9._-]*"
"""The charset half of one safe path component — the ONE expression this
engine has, shared by `foreman/identifiers.py` and re-applied on the shell
side by `scripts/verify-debrief.sh` as a POSIX `case` glob.

The identity is interpolated into a repository path and compared against the
paths a commit touched, so a component containing `/` or `..` would not name a
directory but redefine one, and a regex metacharacter would silently widen the
comparison. A leading `.` is excluded too: `..` is the traversal, and no id
starts with a dot."""

TRAVERSAL: Final[str] = ".."
LOCK_SUFFIX: Final[str] = ".lock"
"""The two forms the charset alone lets through and git refuses under
`refs/wf/exports/<id>`: `a..b` is a path traversal to every consumer that
joins the component onto a directory, and `foo.lock` is how git names the
lock file of the ref `foo` — verified against `git check-ref-format`."""

MSG_UNSAFE_COMPONENT: Final[str] = "{kind} is not one safe path component: {value!r}"

_SAFE_COMPONENT: Final[re.Pattern[str]] = re.compile(SAFE_COMPONENT_PATTERN)


class ComponentKind(StrEnum):
    """What a refused component was being read as, for the refusal message."""

    IDENTIFIER = "identifier"
    TASK = "task id"
    EPIC = "epic id"
    BEAD = "bead id"
    TRACKER_REF = "tracker ref"


class InvalidIdentifier(ValueError):
    """An identifier is unsafe for use as a path component or a ref name."""


def safe_component(
    value: str, *, kind: ComponentKind = ComponentKind.IDENTIFIER
) -> str:
    """Return one safe single-component identifier or refuse it by name.

    Refusing HERE rather than at the ref, the path or the row is the point:
    every boundary downstream would fail differently, and two of them —
    a `docs/workstreams/<epic>/…` grant and a `refs/wf/exports/<task>` pin —
    fail in ways that widen containment rather than close it.
    """
    if (
        not _SAFE_COMPONENT.fullmatch(value)
        or TRAVERSAL in value
        or value.endswith(LOCK_SUFFIX)
    ):
        raise InvalidIdentifier(MSG_UNSAFE_COMPONENT.format(kind=kind, value=value))
    return value


SafeComponent = Annotated[str, AfterValidator(safe_component)]

AttemptNumber = Annotated[int, Field(ge=FIRST_ATTEMPT)]
"""The rule an attempt is under, as one alias: the record below is validated
by it, and the ledger validates a CARRIER's pinned attempt through the same
adapter rather than restating `>= 1` in a second place (`ledger/store.py`)."""


class RunIdentity(BaseModel):
    """The task, epic and attempt number one root is an attempt at (§3.7)."""

    model_config = MODEL

    task_id: SafeComponent
    epic_id: SafeComponent
    """The `docs/workstreams/<epic>/` this run's knowledge belongs under.

    Under the same grammar as the task id, and for the same reason: it is a
    second free path component on the one containment boundary
    `scripts/verify-debrief.sh` re-expands (§3.7)."""
    attempt: AttemptNumber

    @property
    def run_directory(self) -> str:
        """The one repo-relative directory a debrief of this run may write."""
        return f"docs/workstreams/{self.epic_id}/runs/{self.task_id}/a{self.attempt}"
