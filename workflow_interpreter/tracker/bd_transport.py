"""The bd CLI transport — the only place a bd process is spawned.

Moved here from `bdio/client.py` in S6, reduced to the traffic the tracker
adapter actually issues. bd is a TRACKER now (R1): the record-store half of
this transport — creating rows, merging carriers, closing gates, the §11
identity canary — had exactly one caller, the store seam that no longer
exists, and it went with it.

Three properties survive the move unchanged, because they are properties of
spawning bd at all:

1. **argv lists, never shell strings.** No shell is involved anywhere, so no
   metacharacter in a title, reason or label can become syntax.
2. **A closed command set.** The subcommand must be a `BdSubcommand` member
   and every `--flag` must be on `ALLOWED_FLAGS`; `--force`,
   `--ignore-schema-skew`, `--claim-next`, `bd delete`, `bd edit`, `bd gate`
   and `bd audit` are therefore structurally unconstructible rather than
   merely unused.
3. **Every write is read back.** `Applied(observed)` is a desired state the
   tracker AGREED to (§3.3), and only a read-back can say it did.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Protocol

import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator

from workflow_interpreter.bdio.errors import (
    BdCommandError,
    BdOutputError,
    BdTimeoutError,
    BdUnavailableError,
    ForbiddenInvocationError,
    LossyWriteError,
    StoreConfigError,
)
from workflow_interpreter.bdio.wire import ROW_MODEL, Metadata

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

STATUS_CLOSED: Final[str] = "closed"
STATUS_OPEN: Final[str] = "open"
STATUS_IN_PROGRESS: Final[str] = "in_progress"

DEFAULT_BD_BINARY: Final[str] = "bd"
DEFAULT_COMMAND_TIMEOUT_S: Final[float] = 60.0

_MSG_WORKSPACE_RELATIVE: Final[str] = (
    "workspace must be an absolute path, got {workspace}"
)
_MSG_UNKNOWN_SUBCOMMAND: Final[str] = (
    "subcommand {subcommand!r} is not in the closed set"
)
_MSG_UNKNOWN_FLAG: Final[str] = "flag {flag!r} is not on the allow-list"
_MSG_NOT_JSON: Final[str] = "bd {subcommand} did not emit JSON: {reason}"
_MSG_NOT_A_LIST: Final[str] = "bd {subcommand} --json returned {kind}, expected a list"
_MSG_NO_ROW: Final[str] = "bd show {bead_id} returned no row"
_MSG_NOT_CLOSED: Final[str] = "status is {status!r} after close"
_MSG_LABEL_ABSENT: Final[str] = "label {label!r} absent after adding it"
_MSG_LABEL_PRESENT: Final[str] = "label {label!r} still present after removing it"
_MSG_ASSIGNEE_MANGLED: Final[str] = (
    "assignee written as {written!r}, read back as {stored!r}"
)
_MSG_REASON_MANGLED: Final[str] = (
    "close reason written as {written!r}, read back as {stored!r}"
)

SURFACE_CLOSE: Final[str] = "close"
SURFACE_LABEL: Final[str] = "label"
SURFACE_ASSIGNEE: Final[str] = "assignee"


class BdConfig(BaseModel):
    """Everything the bd transport needs; nothing is discovered from the process.

    Deliberately not `pydantic-settings` (`rules/python/safety.md`): every bd
    invocation is fully determined by what the caller injected.
    """

    model_config = ConfigDict(
        frozen=True, extra="forbid", arbitrary_types_allowed=False
    )

    workspace: Path
    actor: str = Field(min_length=1)
    binary: str = DEFAULT_BD_BINARY
    command_timeout_s: float = Field(default=DEFAULT_COMMAND_TIMEOUT_S, gt=0)


class BeadRecord(BaseModel):
    """One bd row as `--json` returns it (the subset the adapter reads)."""

    model_config = ROW_MODEL

    id: str
    title: str
    description: str | None = None
    status: str
    issue_type: str
    assignee: str | None = None
    """Who holds the row — bd's own field, absent from `--json` when nobody
    does (probed on bd 1.1.0). It is the tracker port's `claimed_by` (§3.4)."""
    labels: tuple[str, ...] = ()
    metadata: Metadata = Field(default_factory=dict)
    payload: str | None = None
    close_reason: str | None = None
    closed_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    ephemeral: bool = False
    wisp_type: str | None = None
    parent: str | None = None

    @field_validator("labels", mode="before")
    @classmethod
    def _absent_labels_are_no_labels(cls, value: object) -> object:
        """bd emits `null` for a bead with no labels; that is an empty set."""
        return () if value is None else value


class BdSubcommand(StrEnum):
    """The bd subcommands this wrapper may run. Adding one is a design change."""

    UPDATE = "update"
    CLOSE = "close"
    SHOW = "show"
    LIST = "list"
    DEP = "dep"


class BdFlag(StrEnum):
    """The bd flags this wrapper may construct."""

    DIRECTORY = "-C"
    ACTOR = "--actor"
    JSON = "--json"
    LIMIT = "--limit"
    ALL = "--all"
    INCLUDE_GATES = "--include-gates"
    ADD_LABEL = "--add-label"
    REMOVE_LABEL = "--remove-label"
    PARENT = "--parent"
    REASON = "--reason"
    ASSIGNEE = "--assignee"
    STATUS = "--status"


ALLOWED_FLAGS: Final[frozenset[str]] = frozenset(flag.value for flag in BdFlag)

UNLIMITED: Final[str] = "0"
"""`--limit 0` = unlimited (probed); bd's default of 50 is never relied on."""

_SUBCOMMAND_INDEX: Final[int] = 5
"""`bd -C <ws> --actor <actor> <subcommand> …` — globals are always first."""

_SUBCOMMAND_VALUES: Final[frozenset[str]] = frozenset(
    subcommand.value for subcommand in BdSubcommand
)


class CompletedCommand(BaseModel):
    """The result of one bd invocation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    returncode: int
    stdout: str
    stderr: str


class DependencyType(StrEnum):
    """The dependency relations that Beads reports for an issue."""

    BLOCKS = "blocks"
    TRACKS = "tracks"
    RELATED = "related"
    PARENT_CHILD = "parent-child"
    DISCOVERED_FROM = "discovered-from"
    UNTIL = "until"
    CAUSED_BY = "caused-by"
    VALIDATES = "validates"
    RELATES_TO = "relates-to"
    SUPERSEDES = "supersedes"
    UNKNOWN = "unknown"


class DependencyRecord(BaseModel):
    """One dependency row returned by the bounded Beads dependency surface."""

    model_config = ROW_MODEL

    id: str
    status: str
    dependency_type: DependencyType

    @field_validator("dependency_type", mode="before")
    @classmethod
    def _unknown_dependency_type_is_nonblocking(cls, value: object) -> object:
        """Map future Beads relation names to the non-blocking enum member."""
        if isinstance(value, str):
            try:
                return DependencyType(value)
            except ValueError:
                return DependencyType.UNKNOWN
        return value


class CommandRunner(Protocol):
    """How a bd argv is executed. Injected so unit tests need no bd binary."""

    def __call__(
        self, argv: Sequence[str], timeout_s: float
    ) -> CompletedCommand: ...  # pragma: no cover - protocol


def run_subprocess(argv: Sequence[str], timeout_s: float) -> CompletedCommand:
    """Run `argv` with no shell and an explicit timeout."""
    completed = subprocess.run(
        list(argv),
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    return CompletedCommand(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


class BdClient:
    """A thin, injected-config bd transport with read-back verification.

    Writes are never retried here. A tracker intent is a desired STATE (R2),
    so the retry that matters is the outbox re-applying the intent, not this
    transport re-issuing a command whose effect it could not observe.
    """

    def __init__(self, config: BdConfig, runner: CommandRunner | None = None) -> None:
        if not config.workspace.is_absolute():
            raise StoreConfigError(
                _MSG_WORKSPACE_RELATIVE.format(workspace=config.workspace)
            )
        self._config = config
        self._runner: CommandRunner = runner if runner is not None else run_subprocess

    @property
    def config(self) -> BdConfig:
        """The injected configuration (frozen)."""
        return self._config

    @property
    def workspace(self) -> Path:
        """The bd workspace every invocation is scoped to via `-C`."""
        return self._config.workspace

    # -- invocation ------------------------------------------------------

    def _argv(self, subcommand: BdSubcommand, *args: str) -> tuple[str, ...]:
        """Build a full argv, globals first."""
        return (
            self._config.binary,
            BdFlag.DIRECTORY.value,
            str(self._config.workspace),
            BdFlag.ACTOR.value,
            self._config.actor,
            subcommand.value,
            *args,
        )

    @staticmethod
    def _assert_closed_set(argv: Sequence[str]) -> BdSubcommand:
        """Refuse any argv outside the closed command set before spawning.

        The subcommand is read from its fixed position rather than searched
        for, so an injected value that happens to spell `delete` is data, not
        a command; and every `-`-prefixed token must be an allow-listed flag,
        which is what makes `--force` and friends unconstructible.
        """
        for token in argv:
            if token.startswith("-") and token not in ALLOWED_FLAGS:
                raise ForbiddenInvocationError(_MSG_UNKNOWN_FLAG.format(flag=token))
        if len(argv) <= _SUBCOMMAND_INDEX:
            raise ForbiddenInvocationError(
                _MSG_UNKNOWN_SUBCOMMAND.format(subcommand=list(argv))
            )
        token = argv[_SUBCOMMAND_INDEX]
        if token not in _SUBCOMMAND_VALUES:
            raise ForbiddenInvocationError(
                _MSG_UNKNOWN_SUBCOMMAND.format(subcommand=token)
            )
        return BdSubcommand(token)

    def _run(self, argv: Sequence[str]) -> str:
        """Execute a verified argv, returning stdout; map every failure to a type."""
        subcommand = self._assert_closed_set(argv)
        timeout_s = self._config.command_timeout_s
        try:
            completed = self._runner(argv, timeout_s)
        except subprocess.TimeoutExpired as exc:
            raise BdTimeoutError(argv, timeout_s, subcommand.value) from exc
        except OSError as exc:
            # A missing or non-executable binary never reaches bd, so it says
            # nothing about the caller's ids; it must not escape as a bare
            # `OSError` that a caller above the seam reads as a refusal.
            raise BdUnavailableError(argv, subcommand.value, str(exc)) from exc
        if completed.returncode != 0:
            raise BdCommandError(
                argv, completed.returncode, completed.stderr, subcommand.value
            )
        return completed.stdout

    def _run_json(self, argv: Sequence[str]) -> list[dict[str, Any]]:
        """Execute a read and parse its `--json` array."""
        subcommand = self._assert_closed_set(argv)
        stdout = self._run(argv)
        try:
            parsed = json.loads(stdout)
        except ValueError as exc:
            raise BdOutputError(
                _MSG_NOT_JSON.format(subcommand=subcommand.value, reason=exc)
            ) from exc
        if not isinstance(parsed, list):
            raise BdOutputError(
                _MSG_NOT_A_LIST.format(
                    subcommand=subcommand.value, kind=type(parsed).__name__
                )
            )
        rows: list[dict[str, Any]] = parsed
        return rows

    # -- reads -----------------------------------------------------------

    def show(self, bead_id: str) -> BeadRecord:
        """`bd show <id> --json` — the read-back path for every write."""
        rows = self._run_json(self._argv(BdSubcommand.SHOW, bead_id, BdFlag.JSON.value))
        if not rows:
            raise BdOutputError(_MSG_NO_ROW.format(bead_id=bead_id))
        return BeadRecord.model_validate(rows[0])

    def list_children(self, parent_id: str) -> tuple[BeadRecord, ...]:
        """List a parent's descendants for callers that filter direct children."""
        rows = self._run_json(
            self._argv(
                BdSubcommand.LIST,
                BdFlag.JSON.value,
                BdFlag.LIMIT.value,
                UNLIMITED,
                BdFlag.ALL.value,
                BdFlag.INCLUDE_GATES.value,
                BdFlag.PARENT.value,
                parent_id,
            )
        )
        return tuple(BeadRecord.model_validate(row) for row in rows)

    def list_dependencies(self, bead_id: str) -> tuple[DependencyRecord, ...]:
        """List one bead's dependency records through a fixed command shape."""
        rows = self._run_json(
            self._argv(BdSubcommand.DEP, "list", bead_id, BdFlag.JSON.value)
        )
        return tuple(DependencyRecord.model_validate(row) for row in rows)

    # -- writes (each followed by read-back verification) -----------------

    def close(self, bead_id: str, reason: str) -> BeadRecord:
        """Close a bead with a structured reason and verify both landed.

        Closing twice succeeds and overwrites the reason (probed), so the
        caller decides idempotency above this transport — which `BdTracker`
        does, by reading the item first.
        """
        self._run(self._argv(BdSubcommand.CLOSE, bead_id, BdFlag.REASON.value, reason))
        record = self.show(bead_id)
        if record.status != STATUS_CLOSED:
            raise LossyWriteError(
                bead_id, SURFACE_CLOSE, _MSG_NOT_CLOSED.format(status=record.status)
            )
        if record.close_reason != reason:
            raise LossyWriteError(
                bead_id,
                SURFACE_CLOSE,
                _MSG_REASON_MANGLED.format(written=reason, stored=record.close_reason),
            )
        _LOG.debug("bd.close", bead_id=bead_id, reason=reason)
        return record

    def add_label(self, bead_id: str, label: str) -> BeadRecord:
        """Add one flag and verify it is on the bead (§3.3 `SetFlag`)."""
        return self._write_label(bead_id, label, BdFlag.ADD_LABEL, present=True)

    def remove_label(self, bead_id: str, label: str) -> BeadRecord:
        """Remove one flag and verify it is gone (§3.3 `SetFlag`)."""
        return self._write_label(bead_id, label, BdFlag.REMOVE_LABEL, present=False)

    def write_assignee(self, bead_id: str, assignee: str) -> BeadRecord:
        """Set (or, with an empty string, clear) who holds a row (§3.4).

        `bd update --assignee` and not `--claim`: `--claim` binds the row to
        bd's OWN user identity and refuses anything else, while the engine's
        claim is held by its configured actor — the identity a second session
        reads. So the actor is written explicitly, with the status bd's own
        claim would have set, and read back like every other write here.
        """
        status = STATUS_IN_PROGRESS if assignee else STATUS_OPEN
        self._run(
            self._argv(
                BdSubcommand.UPDATE,
                bead_id,
                BdFlag.ASSIGNEE.value,
                assignee,
                BdFlag.STATUS.value,
                status,
            )
        )
        record = self.show(bead_id)
        if (record.assignee or "") != assignee:
            raise LossyWriteError(
                bead_id,
                SURFACE_ASSIGNEE,
                _MSG_ASSIGNEE_MANGLED.format(written=assignee, stored=record.assignee),
            )
        _LOG.debug("bd.update.assignee", bead_id=bead_id, assignee=assignee)
        return record

    def _write_label(
        self, bead_id: str, label: str, flag: BdFlag, *, present: bool
    ) -> BeadRecord:
        """Write one label and read the bead back, as every other write does."""
        self._run(self._argv(BdSubcommand.UPDATE, bead_id, flag.value, label))
        record = self.show(bead_id)
        if (label in record.labels) is not present:
            raise LossyWriteError(
                bead_id,
                SURFACE_LABEL,
                (_MSG_LABEL_ABSENT if present else _MSG_LABEL_PRESENT).format(
                    label=label
                ),
            )
        _LOG.debug("bd.update.label", bead_id=bead_id, label=label, present=present)
        return record
