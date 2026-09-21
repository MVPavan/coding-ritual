"""Whether a task is closed, derived once and then LATCHED (§3.5, R6).

Closure is not a stored state. A stored CLOSED can only be written after the
export bytes exist, so it could never be IN the export — either it violates D5
("never closable before the record is durable") or it is lost the moment the
ledger is rebuilt from the file that is supposed to carry the whole record.

So it is derived, from two facts and one latch:

```text
closed(task):
    if tasks.state != LANDED:                        return False
    if tasks.export_oid is set:                      return True    # the latch
    oid = anchor_oid(task)            # committed blob first, export ref second
    if oid is None:                                  return False
    if blob_hash(.wf/export/<task>.jsonl) != oid:    return False
    tasks.export_oid = oid                           # derive once, then latch
    return True
```

The LANDED gate comes FIRST, above the latch, and both ends of the latch hold
it: `ledger.export.pin_export` refuses a task that has not landed, and a latch
found on one is not an answer this module will give. `wf ledger pin-export` is
an operator command that can be aimed at any task at all, so without the gate
an in-flight task could be latched closed forever — and its landing would then
skip `adapter.land` and the real pin. `wf ledger export` holds the same gate,
for the rebuild's sake rather than the latch's (§3.9, `write_landed_export`).

The latch is what makes it MONOTONIC, and monotonicity is the whole point. A
live re-export is a function of mutable state — the header carries the schema
version and `projections` is exported — so recomputing closure would reopen
every closed task after one migration or one attention drain. Today's
`export_oid is None` is monotonic; this keeps that property and adds only the
rebuild path.

The file ON DISK is hashed, never a fresh export, exactly as `reverify._pin_check`
does, and the anchor comes from `reverify.anchor_oid` itself: `wf ledger verify`
and `closed()` must never disagree about which bytes are this task's record. A
stale committed blob that no longer matches the file is "not closed" to both,
and the orchestrator recommits.

`retired(task) = closed(task) ∨ state ∈ {ABANDONED, ABANDONED_EXTERNAL}`: an
abandoned task never exports, so terminal cleanup and archive would otherwise
defer forever (§3.8). Sibling admission and the succession guard read it too.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final, Protocol

import structlog

from workflow_interpreter.contracts.run_identity import ComponentKind, safe_component
from workflow_interpreter.inspector.gitio import NO_BLOB, Git
from workflow_interpreter.ledger.constants import (
    LANDING_INTENT_FILE,
    LANDING_INTENT_PHASE,
    TaskState,
)
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.errors import LedgerBusyRefusal, LedgerTransportError
from workflow_interpreter.ledger.reverify import anchor_oid
from workflow_interpreter.ledger.tasks import export_oid, record_export_oid, task_state

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)


def closed(database: LedgerDatabase, git: Git, task_id: str) -> bool:
    """Whether this task's whole record is durable in git (§3.5).

    The first ask that can answer yes WRITES the answer, so every later ask is
    a column read and no git state can take it back.

    The LANDED gate is asked BEFORE the latch: a task that has not landed is
    not closed whatever its `export_oid` column says, because a latch on one
    could only have been written by something that had no business writing it.
    """
    if task_state(database, task_id) is not TaskState.LANDED:
        return False
    if export_oid(database, task_id) is not None:
        return True
    anchor, pinned, relative = anchor_oid(database.repo_root, task_id)
    if anchor is None or pinned is None:
        return False
    found = git.hash_working_file(relative, cwd=database.repo_root)
    if found == NO_BLOB or found != pinned:
        return False
    _latch(database, task_id, pinned)
    _LOG.info(
        "wf.ledger.closure_derived",
        task_id=task_id,
        anchor=anchor.value,
        oid=pinned,
    )
    return True


def _latch(database: LedgerDatabase, task_id: str, pinned: str) -> None:
    """Record the derived answer, or leave it to the next ask (§3.5).

    Every caller of `closed()` is a READER — cleanup, archive, the succession
    guard, the close refusal — and this is the one write inside that read. A
    ledger opened `mode=ro`, or one whose writer holds the database past
    `busy_timeout`, must still get the derived answer: the latch is an
    optimisation over `anchor_oid` and losing it costs one git call next time,
    while raising here would turn a question into a failure.
    """
    try:
        record_export_oid(database, task_id, pinned)
    except (LedgerBusyRefusal, LedgerTransportError) as unwritable:
        _LOG.info(
            "wf.ledger.closure_not_latched",
            task_id=task_id,
            oid=pinned,
            reason=str(unwritable),
        )


_RETIRING_STATES: Final[frozenset[TaskState]] = frozenset(
    {TaskState.ABANDONED, TaskState.ABANDONED_EXTERNAL}
)


def retired(database: LedgerDatabase, git: Git, task_id: str) -> bool:
    """Whether this task is over — closed, or abandoned (§3.5, §3.8).

    What terminal cleanup and archive read. An abandoned task has no export
    and never will, so asking them to wait for closure would keep its worktree
    and its refs forever.

    BOTH abandonments retire. Who decided is the only difference between them
    — we did, or the tracker did — and it is not a difference any consumer of
    this question has: a task whose item somebody closed mid-epic exports no
    more than one we stopped ourselves, so leaving it open would wedge every
    sibling's admission on a task no verb can move.
    """
    return closed(database, git, task_id) or abandoned(database, task_id)


def abandoned(database: LedgerDatabase, task_id: str) -> bool:
    """Whether this task was retired by abandonment rather than by closure.

    The half of `retired()` that says the run STOPPED. Archive reads it by
    name: an abandon ends a task mid-run, so its roots reach no terminal node
    and a settlement check that stands for "this run is over" has to hear the
    retirement instead (§3.8).
    """
    return task_state(database, task_id) in _RETIRING_STATES


_SQL_LANDING_INTENT: Final[str] = (
    "SELECT 1 FROM landings WHERE task_id = ? AND attempt = ? AND phase = ?"
)


def landing_begun(database: LedgerDatabase, task_id: str, attempt: int) -> bool:
    """Whether this attempt journalled a landing intent (§3.8, D17).

    The intent row is written BEFORE the fast-forward CAS and outlives both the
    process and a `git clean`ed `.wf/`, so it is the one durable fact that says
    "this attempt's work may already be on the target ref". `wf contract`'s
    recovery keys on the same intent; abandon refuses on it, so the two cannot
    disagree about whether a landing is in flight.
    """
    with database.locked() as connection:
        row = connection.execute(
            _SQL_LANDING_INTENT, (task_id, attempt, LANDING_INTENT_PHASE)
        ).fetchone()
    return row is not None


class ClosureProbe(Protocol):
    """What a caller needs to ask about a task's closure, and nothing else.

    A protocol rather than the class below because the contractor depends on
    the QUESTION, not on the ledger that answers it: the adapter holds one of
    these to refuse a close and a succession, and it must not know what a
    database is.
    """

    def closed(self, task_id: str) -> bool:
        """Whether this task's whole record is durable in git."""
        ...

    def retired(self, task_id: str) -> bool:
        """Whether this task is closed or abandoned."""
        ...

    def landing_begun(self, task_id: str, attempt: int, root_id: str | None) -> bool:
        """Whether this attempt's landing has begun, by row or by file."""
        ...


class TaskClosure:
    """The ledger's own answer to both questions, for one checkout.

    The contractor holds one of these rather than a database and a git seam:
    the adapter owns bead writes and may not grow a ledger of its own, but the
    close it performs and the succession it refuses are both decided by
    whether the task's record is already durable (§3.5).
    """

    def __init__(
        self, database: LedgerDatabase, git: Git, wrapper_root: Path | None = None
    ) -> None:
        self._database = database
        self._git = git
        self._wrapper_root = wrapper_root
        """Where this engine home keeps its instance directories, when the
        caller knows (§3.8, D17). It is what lets `landing_begun` read the
        wrapper intent FILE — the evidence `landing.recover` reads first —
        rather than the restored row alone: a rebuild that never anchored the
        row would otherwise let `wf phase abandon` delete a worktree whose
        commit is already on the target ref (gate B, finding 2a)."""

    def closed(self, task_id: str) -> bool:
        """Whether this task's whole record is durable in git."""
        return closed(self._database, self._git, task_id)

    def retired(self, task_id: str) -> bool:
        """Whether this task is closed or abandoned."""
        return retired(self._database, self._git, task_id)

    def landing_begun(self, task_id: str, attempt: int, root_id: str | None) -> bool:
        """Whether this attempt's landing has begun — the row, then the file.

        Two pieces of evidence because either can be the only one left: the
        row survives a deleted wrapper directory, and the file survives a
        ledger this checkout rebuilt from an anchor older than the landing.
        `landing.recover` reads the file first for the same reason, so the two
        cannot disagree about whether a landing is in flight (D17).
        """
        return landing_begun(self._database, task_id, attempt) or self._intent_file(
            root_id
        )

    def _intent_file(self, root_id: str | None) -> bool:
        """Whether this root's wrapper directory still holds a landing intent."""
        if self._wrapper_root is None or root_id is None:
            return False
        return (
            self._wrapper_root
            / safe_component(root_id, kind=ComponentKind.IDENTIFIER)
            / LANDING_INTENT_FILE
        ).is_file()


class NoLedgerClosure:
    """The answer for a composition that has no ledger at all (§3.5, D5).

    A named probe rather than an absent one, because "nobody asked" and "the
    answer is no" have to be the same thing here: no ledger means no export
    can exist, so no task of this wiring can have its record durable in git,
    and the close that depends on it is refused by name (`MSG_NOT_CLOSABLE`).
    Succession sees the same "not closed, not retired" a ledger-less wiring has
    always had — there is no evidence to refuse it with.
    """

    def closed(self, task_id: str) -> bool:
        """No: without a ledger there is no export, so no durable record."""
        return False

    def retired(self, task_id: str) -> bool:
        """No: a task this wiring cannot export is not one it can retire."""
        return False

    def landing_begun(self, task_id: str, attempt: int, root_id: str | None) -> bool:
        """No: a wiring with no ledger journals no landing intent (D17)."""
        return False


def closure_probe(
    database: LedgerDatabase | None, git: Git, wrapper_root: Path | None = None
) -> ClosureProbe:
    """The probe for a composition whose ledger is optional.

    One definition, because every construction site of `ContractorAdapter`
    supplies a probe (the adapter takes no absent one), and a second copy of
    "ledger or not" would be a second chance to get the ledger-less case wrong.
    """
    return (
        NoLedgerClosure()
        if database is None
        else TaskClosure(database, git, wrapper_root)
    )
