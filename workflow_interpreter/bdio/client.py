"""The bd CLI transport — the only place a bd process is spawned (§0).

Three properties this file exists to guarantee:

1. **argv lists, never shell strings.** No shell is involved anywhere, so no
   metacharacter in a title, reason or JSON payload can become syntax.
2. **A closed command set.** The subcommand must be a `BdSubcommand` member
   and every `--flag` must be on `ALLOWED_FLAGS`; `--force`,
   `--ignore-schema-skew`, `--claim-next`, `bd delete`, `bd edit`,
   `bd gate`, `bd audit` are therefore structurally unconstructible rather
   than merely unused (§0.1, §11 'prior probe facts').
3. **Every write is read back.** bd's extension surfaces are lossy by
   default — `--event-payload @file` stores the literal string, and integers
   beyond float64 precision are silently rounded (both probed) — so a write
   that did not land exactly raises `LossyWriteError` instead of passing.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Protocol

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.config import BdConfig
from workflow_interpreter.bdio.errors import (
    BdCommandError,
    BdConfigError,
    BdOutputError,
    BdTimeoutError,
    ForbiddenInvocationError,
    LossyWriteError,
)
from workflow_interpreter.bdio.wire import (
    BeadRecord,
    IssueType,
    Metadata,
    canonical_json_bytes,
)

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

STATUS_CLOSED: Final[str] = "closed"

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
_MSG_NO_ID: Final[str] = "bd create --silent emitted no issue id"
_MSG_MISSING_KEY: Final[str] = "key {key!r} absent after write"
_MSG_MANGLED: Final[str] = "key {key!r} written as {written!r}, read back as {stored!r}"
_MSG_PAYLOAD_ABSENT: Final[str] = "event payload absent after write"
_MSG_PAYLOAD_UNPARSEABLE: Final[str] = "event payload read back unparseable: {stored!r}"
_MSG_PAYLOAD_MANGLED: Final[str] = (
    "event payload written as {written!r}, read back as {stored!r}"
)
_MSG_NOT_CLOSED: Final[str] = "status is {status!r} after close"
_MSG_REASON_MANGLED: Final[str] = (
    "close reason written as {written!r}, read back as {stored!r}"
)

SURFACE_METADATA: Final[str] = "metadata"
SURFACE_EVENT_PAYLOAD: Final[str] = "event-payload"
SURFACE_CLOSE: Final[str] = "close"


class BdSubcommand(StrEnum):
    """The bd subcommands this wrapper may run. Adding one is a design change."""

    CREATE = "create"
    UPDATE = "update"
    CLOSE = "close"
    SHOW = "show"
    LIST = "list"
    CONTEXT = "context"


class BdFlag(StrEnum):
    """The bd flags this wrapper may construct."""

    DIRECTORY = "-C"
    ACTOR = "--actor"
    JSON = "--json"
    SILENT = "--silent"
    TITLE = "--title"
    TYPE = "--type"
    NO_INHERIT_LABELS = "--no-inherit-labels"
    METADATA = "--metadata"
    EVENT_PAYLOAD = "--event-payload"
    EPHEMERAL = "--ephemeral"
    WISP_TYPE = "--wisp-type"
    LIMIT = "--limit"
    ALL = "--all"
    INCLUDE_GATES = "--include-gates"
    METADATA_FIELD = "--metadata-field"
    REASON = "--reason"


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

    Writes are never retried here: a retried create without an idempotency
    re-check is exactly the duplicate the §3.2 natural key exists to prevent
    (§4 command table, 'Mint'). Retry policy lives in `api.py`, above the key
    lookup.
    """

    def __init__(self, config: BdConfig, runner: CommandRunner | None = None) -> None:
        if not config.workspace.is_absolute():
            raise BdConfigError(
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

    def context(self) -> dict[str, Any]:
        """`bd context --json` — backend identity for the §11 canary."""
        argv = self._argv(BdSubcommand.CONTEXT, BdFlag.JSON.value)
        stdout = self._run(argv)
        try:
            parsed = json.loads(stdout)
        except ValueError as exc:
            raise BdOutputError(
                _MSG_NOT_JSON.format(subcommand=BdSubcommand.CONTEXT.value, reason=exc)
            ) from exc
        if not isinstance(parsed, dict):
            raise BdOutputError(
                _MSG_NOT_A_LIST.format(
                    subcommand=BdSubcommand.CONTEXT.value, kind=type(parsed).__name__
                )
            )
        context: dict[str, Any] = parsed
        return context

    def show(self, bead_id: str) -> BeadRecord:
        """`bd show <id> --json` — the read-back path for every write."""
        rows = self._run_json(self._argv(BdSubcommand.SHOW, bead_id, BdFlag.JSON.value))
        if not rows:
            raise BdOutputError(_MSG_NO_ROW.format(bead_id=bead_id))
        return BeadRecord.model_validate(rows[0])

    def list_beads(
        self,
        *,
        metadata_filters: Mapping[str, str] | None = None,
        issue_type: IssueType | None = None,
    ) -> tuple[BeadRecord, ...]:
        """`bd list --json --limit 0 --all --include-gates` plus metadata filters.

        Always unlimited, always including closed rows and gates: the §4 read
        vocabulary needs closed activations for the idempotency lookup and the
        ceiling count, and bd's default limit is not something to rely on.
        Repeated `--metadata-field` filters are ANDed (probed).
        """
        args = [
            BdFlag.JSON.value,
            BdFlag.LIMIT.value,
            UNLIMITED,
            BdFlag.ALL.value,
            BdFlag.INCLUDE_GATES.value,
        ]
        if issue_type is not None:
            args += [BdFlag.TYPE.value, issue_type.value]
        for key, value in sorted((metadata_filters or {}).items()):
            args += [BdFlag.METADATA_FIELD.value, f"{key}={value}"]
        rows = self._run_json(self._argv(BdSubcommand.LIST, *args))
        return tuple(BeadRecord.model_validate(row) for row in rows)

    # -- writes (each followed by read-back verification) -----------------
    #
    # Package-private on purpose (§0.1). A generic `close_bead` or
    # `merge_metadata` in reach of a foreman is a one-line bypass of §9 gate
    # verification and the §5.1 lifecycle rules, so the transport's write
    # surface is reachable only from the typed operations in this package;
    # `WorkflowStore.reads` is what a caller gets.

    def _create_bead(
        self,
        *,
        title: str,
        metadata: Metadata,
        issue_type: IssueType = IssueType.TASK,
        event_payload: Metadata | None = None,
        ephemeral: bool = False,
        wisp_type: str | None = None,
    ) -> BeadRecord:
        """Create a workflow bead and verify it read back exactly as written."""
        args = [
            BdFlag.TITLE.value,
            title,
            BdFlag.TYPE.value,
            issue_type.value,
            BdFlag.NO_INHERIT_LABELS.value,
            BdFlag.METADATA.value,
            canonical_json_bytes(metadata).decode("utf-8"),
            BdFlag.SILENT.value,
        ]
        if event_payload is not None:
            # Inline JSON only: the `@file` form stores the literal string
            # "@file" and exits 0 (probed 2026-08-25, §3.3).
            args += [
                BdFlag.EVENT_PAYLOAD.value,
                canonical_json_bytes(event_payload).decode("utf-8"),
            ]
        if ephemeral:
            args.append(BdFlag.EPHEMERAL.value)
        if wisp_type is not None:
            args += [BdFlag.WISP_TYPE.value, wisp_type]

        bead_id = self._run(self._argv(BdSubcommand.CREATE, *args)).strip()
        if not bead_id:
            raise BdOutputError(_MSG_NO_ID)
        record = self.show(bead_id)
        self._assert_metadata(record, metadata)
        if event_payload is not None:
            self._assert_event_payload(record, event_payload)
        _LOG.debug("bd.create", bead_id=bead_id, issue_type=issue_type.value)
        return record

    def _merge_metadata(self, bead_id: str, metadata: Metadata) -> BeadRecord:
        """Merge metadata into a bead and verify the merged result.

        `bd update --metadata` merges and preserves JSON types; the
        `--set-metadata k=v` surface stringifies structured values (probed)
        and is therefore not on the flag allow-list at all.
        """
        self._run(
            self._argv(
                BdSubcommand.UPDATE,
                bead_id,
                BdFlag.METADATA.value,
                canonical_json_bytes(metadata).decode("utf-8"),
            )
        )
        record = self.show(bead_id)
        self._assert_metadata(record, metadata)
        _LOG.debug("bd.update", bead_id=bead_id, keys=sorted(metadata))
        return record

    def _close_bead(self, bead_id: str, reason: str) -> BeadRecord:
        """Close a bead with a structured reason and verify both landed.

        Closing twice succeeds and overwrites the reason (probed), so callers
        must decide idempotency above this transport, not rely on bd.
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

    # -- read-back verification ------------------------------------------

    @staticmethod
    def _assert_metadata(record: BeadRecord, written: Metadata) -> None:
        """Every written key must be present and structurally identical."""
        for key, value in written.items():
            if key not in record.metadata:
                raise LossyWriteError(
                    record.id, SURFACE_METADATA, _MSG_MISSING_KEY.format(key=key)
                )
            stored = record.metadata[key]
            if stored != value:
                raise LossyWriteError(
                    record.id,
                    SURFACE_METADATA,
                    _MSG_MANGLED.format(key=key, written=value, stored=stored),
                )

    @staticmethod
    def _assert_event_payload(record: BeadRecord, written: Metadata) -> None:
        """The payload must parse back to exactly the object handed in."""
        if record.payload is None:
            raise LossyWriteError(record.id, SURFACE_EVENT_PAYLOAD, _MSG_PAYLOAD_ABSENT)
        try:
            stored = json.loads(record.payload)
        except ValueError as exc:
            raise LossyWriteError(
                record.id,
                SURFACE_EVENT_PAYLOAD,
                _MSG_PAYLOAD_UNPARSEABLE.format(stored=record.payload),
            ) from exc
        if stored != written:
            raise LossyWriteError(
                record.id,
                SURFACE_EVENT_PAYLOAD,
                _MSG_PAYLOAD_MANGLED.format(written=written, stored=stored),
            )
