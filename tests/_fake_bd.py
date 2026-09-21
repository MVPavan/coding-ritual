"""An in-memory bd substitute, driven through the real `BdClient` transport.

This is a `CommandRunner`, not a mock of the wrapper: the argv is built,
closed-set-checked and parsed exactly as it would be for a real `bd`. What it
buys over the live binary is CONTROL — crash injection (`crash_on`) and
reentrant scheduling (`pause_before`), so a window can be opened at will and
two interleaved callers expressed as ordinary single-threaded code.

Scoped to the TRACKER since S6: bd is not a record store (R1), so the
transport can no longer construct `create`, `context` or `--metadata` at all
(`BdSubcommand`, `ALLOWED_FLAGS`) and this double no longer answers them.
What is left is exactly what `BdTracker` asks.

Semantics mirror the probed behaviour of bd 1.1.0: closing twice succeeds and
overwrites the reason, `--json` reads return a list of rows, and `--add-label`
/ `--remove-label` are set semantics — adding a label twice leaves one,
removing one that is absent is a no-op. That last pair is the run-ledger §3.2
attention projection, and it is idempotent by design because the reconciler
REPLAYS it.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any, Final

from workflow_interpreter.tracker.bd_transport import CompletedCommand

_SUBCOMMAND_INDEX: Final[int] = 5
_STATUS_CLOSED: Final[str] = "closed"

_VALUE_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "--reason",
        "--limit",
        "--parent",
        "--add-label",
        "--remove-label",
        "--assignee",
        "--status",
    }
)
_BOOL_FLAGS: Final[frozenset[str]] = frozenset({"--json", "--all", "--include-gates"})


class InjectedCrash(Exception):
    """The bd process died mid-command — what a real crash looks like here."""


class FakeBd:
    """An in-memory bd workspace exposed as a `CommandRunner`."""

    def __init__(self, workspace: str) -> None:
        self.workspace = workspace
        self.rows: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self._crashes: list[tuple[str, int]] = []
        self._lost_responses: list[tuple[str, int]] = []
        self._pauses: list[tuple[str, Callable[[], None]]] = []
        self._seen: dict[str, int] = {}
        self._refusing = False
        self._refuse_after: int | None = None

    # -- scheduling controls ---------------------------------------------

    def crash_on(self, subcommand: str, occurrence: int = 1) -> None:
        """Kill the process on the Nth `subcommand` FROM NOW, before it lands.

        Relative rather than absolute, so a test can set up state through the
        normal API and then arm the crash without counting the setup's calls.
        """
        self._crashes.append((subcommand, self._seen.get(subcommand, 0) + occurrence))

    def lose_response_on(self, subcommand: str, occurrence: int = 1) -> None:
        """Persist the command, then lose its response to model a real write window."""
        self._lost_responses.append(
            (subcommand, self._seen.get(subcommand, 0) + occurrence)
        )

    def pause_before(self, subcommand: str, callback: Callable[[], None]) -> None:
        """Run `callback` once, immediately before the next `subcommand`."""
        self._pauses.append((subcommand, callback))

    def refuse_after(self, commands: int) -> None:
        """Refuse everything once this many MORE commands have been served.

        The window §3.4's claim opened: a claim-capable tracker has to be
        reachable for the admit itself, so "the tracker is gone" has to start
        after it rather than before, and the count is the claim's own cost.
        """
        self._refuse_after = len(self.calls) + commands

    def refuse_everything(self) -> None:
        """Make every later command fail the way an unreachable tracker does.

        S4's acceptance is that a task which has PREPARED runs to a landing
        with the tracker gone (§3.3, R4), and "gone" has to mean every call:
        a fake that still answered reads would prove only that the writes
        were skipped. The attempt is still recorded, so a test can name which
        call — if any — the engine still owes the tracker.
        """
        self._refusing = True

    def command_count(self, subcommand: str) -> int:
        """How many `subcommand` invocations this workspace has served."""
        return sum(1 for name, _ in self.calls if name == subcommand)

    # -- CommandRunner ----------------------------------------------------

    def __call__(self, argv: Sequence[str], timeout_s: float) -> CompletedCommand:
        """Execute one bd argv against the in-memory store."""
        subcommand = argv[_SUBCOMMAND_INDEX]
        args = list(argv[_SUBCOMMAND_INDEX + 1 :])
        self._fire_pause(subcommand)
        self.calls.append((subcommand, tuple(argv)))
        self._seen[subcommand] = self._seen.get(subcommand, 0) + 1
        if self._refuse_after is not None and len(self.calls) > self._refuse_after:
            self._refusing = True
        if self._refusing:
            raise InjectedCrash(f"bd {subcommand} cannot reach the tracker")
        if (subcommand, self._seen[subcommand]) in self._crashes:
            raise InjectedCrash(f"bd {subcommand} died mid-command")
        handler = {
            "update": self._update,
            "close": self._close,
            "show": self._show,
            "list": self._list,
            "dep": self._dependencies,
        }[subcommand]
        stdout = handler(args)
        if (subcommand, self._seen[subcommand]) in self._lost_responses:
            raise InjectedCrash(f"bd {subcommand} response lost after persistence")
        return CompletedCommand(returncode=0, stdout=stdout, stderr="")

    def _fire_pause(self, subcommand: str) -> None:
        """Run and consume a one-shot pause registered for this subcommand."""
        for index, (name, callback) in enumerate(self._pauses):
            if name == subcommand:
                del self._pauses[index]
                callback()
                return

    # -- subcommands ------------------------------------------------------

    def _update(self, args: list[str]) -> str:
        flags = _parse(args[1:])
        row = self.rows[args[0]]
        labels: list[str] = row.setdefault("labels", [])
        added = flags.get("--add-label")
        if added is not None and added not in labels:
            labels.append(added)
        removed = flags.get("--remove-label")
        if removed is not None and removed in labels:
            labels.remove(removed)
        # Probed on bd 1.1.0: `--assignee ""` clears the field, and `--status`
        # is written as given.
        if "--assignee" in flags:
            row["assignee"] = flags["--assignee"]
        if "--status" in flags:
            row["status"] = flags["--status"]
        return ""

    def _close(self, args: list[str]) -> str:
        flags = _parse(args[1:])
        row = self.rows[args[0]]
        row["status"] = _STATUS_CLOSED
        row["close_reason"] = flags["--reason"]
        return ""

    def _show(self, args: list[str]) -> str:
        row = self.rows.get(args[0])
        return json.dumps([row] if row is not None else [])

    def _list(self, args: list[str]) -> str:
        flags = _parse(args)
        selected = [
            row
            for row in self.rows.values()
            if "--parent" not in flags or row.get("parent") == flags["--parent"]
        ]
        return json.dumps(sorted(selected, key=lambda row: str(row["id"])))

    def _dependencies(self, args: list[str]) -> str:
        """Return the selected row's own dependency records, like `bd dep list`."""
        bead_id = args[1]
        return json.dumps(self.rows[bead_id].get("dependencies", []))


def _parse(args: list[str]) -> dict[str, Any]:
    """Flags of one bd argv tail, in the closed set the transport may build."""
    flags: dict[str, Any] = {}
    index = 0
    while index < len(args):
        token = args[index]
        if token in _VALUE_FLAGS:
            flags[token] = args[index + 1]
            index += 2
        elif token in _BOOL_FLAGS:
            flags[token] = True
            index += 1
        else:
            index += 1
    return flags
