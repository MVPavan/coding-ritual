"""An in-memory bd substitute, driven through the real `BdClient` transport.

This is a `CommandRunner`, not a mock of the wrapper: the argv is built,
closed-set-checked and parsed exactly as it would be for a real `bd`, and
every write still goes through the read-back verification in `client.py`.
What it buys over the live binary is CONTROL — the two things a real bd
cannot give a test deterministically:

- **Crash injection.** `crash_on` makes the Nth matching command die the way
  a killed process does, so the window between the metadata write and the
  `bd close` can be opened at will and inspected.
- **Reentrant scheduling.** `pause_before` runs a callback just before a
  chosen command executes, so two interleaved mints can be expressed as
  ordinary single-threaded code with no barriers and no flakiness.

Semantics mirror the probed behaviour of bd 1.1.0: `--metadata` MERGES at the
top level, closing twice succeeds and overwrites the reason, and `--json`
reads return a list of rows.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any, Final

from workflow_interpreter.bdio.client import CompletedCommand

BD_VERSION: Final[str] = "1.1.0"
BACKEND: Final[str] = "dolt"
DOLT_MODE: Final[str] = "embedded"
BEADS_DIR_NAME: Final[str] = ".beads"

_SUBCOMMAND_INDEX: Final[int] = 5
_STATUS_OPEN: Final[str] = "open"
_STATUS_CLOSED: Final[str] = "closed"
_ID_TEMPLATE: Final[str] = "wf-{number}"

_VALUE_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "--title",
        "--type",
        "--metadata",
        "--event-payload",
        "--wisp-type",
        "--reason",
        "--limit",
    }
)
_BOOL_FLAGS: Final[frozenset[str]] = frozenset(
    {
        "--no-inherit-labels",
        "--silent",
        "--ephemeral",
        "--json",
        "--all",
        "--include-gates",
    }
)
_REPEATED_FLAG: Final[str] = "--metadata-field"


class InjectedCrash(Exception):
    """The bd process died mid-command — what a real crash looks like here."""


class FakeBd:
    """An in-memory bd workspace exposed as a `CommandRunner`."""

    def __init__(self, workspace: str) -> None:
        self.workspace = workspace
        self.rows: dict[str, dict[str, Any]] = {}
        self.calls: list[tuple[str, tuple[str, ...]]] = []
        self._next_id = 1
        self._crashes: list[tuple[str, int]] = []
        self._pauses: list[tuple[str, Callable[[], None]]] = []
        self._seen: dict[str, int] = {}

    # -- scheduling controls ---------------------------------------------

    def crash_on(self, subcommand: str, occurrence: int = 1) -> None:
        """Kill the process on the Nth `subcommand` FROM NOW, before it lands.

        Relative rather than absolute, so a test can set up state through the
        normal API and then arm the crash without counting the setup's calls.
        """
        self._crashes.append((subcommand, self._seen.get(subcommand, 0) + occurrence))

    def pause_before(self, subcommand: str, callback: Callable[[], None]) -> None:
        """Run `callback` once, immediately before the next `subcommand`."""
        self._pauses.append((subcommand, callback))

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
        if (subcommand, self._seen[subcommand]) in self._crashes:
            raise InjectedCrash(f"bd {subcommand} died mid-command")
        handler = {
            "create": self._create,
            "update": self._update,
            "close": self._close,
            "show": self._show,
            "list": self._list,
            "context": self._context,
        }[subcommand]
        return CompletedCommand(returncode=0, stdout=handler(args), stderr="")

    def _fire_pause(self, subcommand: str) -> None:
        """Run and consume a one-shot pause registered for this subcommand."""
        for index, (name, callback) in enumerate(self._pauses):
            if name == subcommand:
                del self._pauses[index]
                callback()
                return

    # -- subcommands ------------------------------------------------------

    def _create(self, args: list[str]) -> str:
        flags = _parse(args)
        bead_id = _ID_TEMPLATE.format(number=self._next_id)
        self._next_id += 1
        payload = flags.get("--event-payload")
        self.rows[bead_id] = {
            "id": bead_id,
            "title": flags.get("--title", ""),
            "status": _STATUS_OPEN,
            "issue_type": flags.get("--type", "task"),
            "metadata": json.loads(flags.get("--metadata", "{}")),
            "payload": payload,
            "close_reason": None,
            "ephemeral": "--ephemeral" in args,
            "wisp_type": flags.get("--wisp-type"),
        }
        return bead_id

    def _update(self, args: list[str]) -> str:
        flags = _parse(args[1:])
        # bd MERGES top-level metadata keys rather than replacing the object.
        self.rows[args[0]]["metadata"].update(json.loads(flags["--metadata"]))
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
            if _matches(row, flags.get(_REPEATED_FLAG, []), flags.get("--type"))
        ]
        return json.dumps(sorted(selected, key=lambda row: str(row["id"])))

    def _context(self, args: list[str]) -> str:
        return json.dumps(
            {
                "backend": BACKEND,
                "dolt_mode": DOLT_MODE,
                "bd_version": BD_VERSION,
                "repo_root": self.workspace,
                "beads_dir": f"{self.workspace}/{BEADS_DIR_NAME}",
            }
        )


def _parse(args: list[str]) -> dict[str, Any]:
    """Flags of one bd argv tail: repeated `--metadata-field` collects."""
    flags: dict[str, Any] = {}
    index = 0
    while index < len(args):
        token = args[index]
        if token == _REPEATED_FLAG:
            flags.setdefault(_REPEATED_FLAG, []).append(args[index + 1])
            index += 2
        elif token in _VALUE_FLAGS:
            flags[token] = args[index + 1]
            index += 2
        elif token in _BOOL_FLAGS:
            flags[token] = True
            index += 1
        else:
            index += 1
    return flags


def _matches(
    row: dict[str, Any], metadata_filters: list[str], issue_type: str | None
) -> bool:
    """Whether a row satisfies every `--metadata-field k=v` filter (ANDed)."""
    if issue_type is not None and row["issue_type"] != issue_type:
        return False
    for entry in metadata_filters:
        key, _, value = entry.partition("=")
        found = row["metadata"].get(key)
        if found is None or str(found) != value:
            return False
    return True
