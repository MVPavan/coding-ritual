"""The backend locator — which store a root is read and written through (§3.2).

The backend is pinned per attempt root at creation and never changes, so the
answer has to exist BEFORE the root is loaded. Three sources, in the plan's
order:

1. the **bridge record**, whose `root_backend` is written at prepare, before
   admission creates any root or branch — the only source that can answer for
   a root that does not exist yet;
2. the **ledger**, whose `roots` row carries the pin the root was created with
   and whose `tasks` row carries the pin for a run with no bridge (D16);
3. a **refusal** naming the root, because a root nobody pinned is a root that
   could be read from the wrong store — and reading it from the wrong store
   would report a live run as missing.

The bridge's answers arrive as pins rather than as a bd read per call: the
bridge has the record in hand when it composes a run, and re-reading bd every
tick to learn that the answer is bd is the round trip this whole plan exists
to remove.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.errors import StoreConfigError
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.tasks import root_backend, task_backend

MSG_UNPINNED: Final[str] = (
    "no backend is pinned for root {root_id!r} of task {task_id!r}: neither a "
    "bridge record nor a ledger tasks row names one (run-ledger §3.2)"
)


class RootBackendLocator:
    """Answers §3.2's locator question for the roots of ONE task.

    One task per process is not a simplification: `--task` is required to
    start any run (D16), and every root a foreman touches — attempts,
    composition children, decision and replacement roots — belongs to it.
    """

    def __init__(
        self,
        task_id: str,
        *,
        ledger: LedgerDatabase | None = None,
        pins: Mapping[str, BackendKind] = MappingProxyType({}),
    ) -> None:
        self._task_id = task_id
        self._ledger = ledger
        self._pins = dict(pins)

    def pin(self, root_id: str, backend: BackendKind) -> None:
        """Record what a bridge record already says about one root.

        Called by the composition root with a record it has just read, never
        by a caller inventing an answer: a pin that disagreed with the stored
        one would move a root between backends, which D18 forbids.
        """
        held = self._pins.get(root_id)
        if held is not None and held is not backend:
            raise StoreConfigError(
                f"root {root_id!r} is already pinned to {held.value!r}, "
                f"not {backend.value!r}"
            )
        self._pins[root_id] = backend

    def pin_record(self, root_id: str, backend: BackendKind) -> None:
        """Record what a BRIDGE RECORD says, behind every stronger source.

        The record is what a restarted process has for an attempt root the
        ledger holds no row for — a bd attempt of a ledger-pinned task, where
        the `tasks` row would otherwise answer for attempt one. It is the
        WEAKEST source even so: a `roots` row is the pin the root was actually
        created with, and a record may carry this field's default rather than
        an answer, because an integration bridge record never sets it
        (`bridge/integration.py`). So anything already known wins, silently.
        """
        if self._pins.get(root_id) is not None:
            return
        if self._ledger is not None:
            found = root_backend(self._ledger, root_id)
            if found is not None:
                self._pins[root_id] = found
                return
        self._pins[root_id] = backend

    def __call__(self, root_id: str) -> BackendKind:
        """The backend pinned for this root, or a refusal naming it."""
        pinned = self._pins.get(root_id)
        if pinned is not None:
            return pinned
        if self._ledger is not None:
            found = root_backend(self._ledger, root_id) or task_backend(
                self._ledger, self._task_id
            )
            if found is not None:
                self._pins[root_id] = found
                return found
        raise StoreConfigError(
            MSG_UNPINNED.format(root_id=root_id, task_id=self._task_id)
        )
