"""The wrapper directory: layout, durable writes, and the §5.2 exec ledger.

`.wf/<root_id>/` beside the repo is the observation cache of §P1. Two of the
files in it are load-bearing for crash atomicity and get more than ordinary
care:

- **The launch receipt** must be on stable storage before the child may exec.
  `write_durable` is therefore temp-write → `fsync(file)` → `rename` →
  `fsync(dir)`: a rename is atomic, but a rename whose data was never flushed
  leaves a zero-length receipt after a power loss, and a flushed file whose
  directory entry was not flushed can vanish entirely.
- **The exec ledger** is append-only and written by the CHILD immediately
  before `execve`, with `O_APPEND` so concurrent appends cannot interleave
  offsets. It is the drills' exactly-once evidence (`wc -l`), so nothing here
  ever rewrites or truncates it.

Reads are deliberately asymmetric: an ABSENT file returns `None`, a MALFORMED
one raises. §5.6 has to tell "no exit was ever written" from "the exit file was
truncated by the crash", and both must classify deterministically (drill 18).

Linux-only (`os.fsync` on a directory fd).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ValidationError

from workflow_interpreter.schema.loader import canonical_json_bytes
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import WrapperDirError
from workflow_interpreter.supervisor.models import ExecLedgerEntry

WORKTREE_DIR: Final[str] = "worktree"
VERIFY_TREE_DIR: Final[str] = "verify-tree"
WORKSPACE_RECORD: Final[str] = "workspace.json"
ATTRIBUTION_RECORD: Final[str] = "attribution.json"
SNAPSHOT_INDEX: Final[str] = "prereset.index"
BAND_LOCK: Final[str] = "repo-band.lock"
RECEIPT_FILE: Final[str] = "launch-receipt.json"
LEDGER_FILE: Final[str] = "exec.ledger"
LOG_FILE: Final[str] = "run.jsonl"
OUTCOME_FILE: Final[str] = "outcome.json"
EFFECTS_FILE: Final[str] = "effects.json"
ARTIFACT_DIR: Final[str] = "artifacts"
EXIT_FILE: Final[str] = "exit.json"
COMPLETION_FILE: Final[str] = "completion.json"
STALE_FLAG: Final[str] = "stale.flag"
STEER_INTENT: Final[str] = "steer-intent.json"

TEMP_SUFFIX: Final[str] = ".tmp"
NEWLINE: Final[bytes] = b"\n"
ENCODING: Final[str] = "utf-8"

_MSG_MALFORMED: Final[str] = "{path} does not parse as {model}: {reason}"
_MSG_UNREADABLE: Final[str] = "{path} could not be read: {reason}"


def write_all(descriptor: int, data: bytes) -> None:
    """Write every byte of `data`, looping over short writes.

    `os.write` is the raw syscall and is allowed to write FEWER bytes than it
    was given. Ignoring its return renames a truncated record into place, which
    is precisely the half-written file `write_durable` exists to make
    impossible.
    """
    written = 0
    while written < len(data):
        written += os.write(descriptor, data[written:])


def write_durable(path: Path, data: bytes) -> None:
    """Write `data` to `path` so that a crash leaves the old file or the new one.

    Never a partial one: the temp file's data is flushed before the rename, and
    the containing directory is flushed after it, so the receipt the fork
    barrier depends on is either fully there or absent (§5.2).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}{TEMP_SUFFIX}")
    descriptor = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        write_all(descriptor, data)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temp, path)
    fsync_dir(path.parent)


def fsync_dir(directory: Path) -> None:
    """Flush a directory entry, so a renamed-in file survives a power loss."""
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def record_bytes(model: BaseModel) -> bytes:
    """A wrapper-dir record as canonical JSON with a trailing newline."""
    return canonical_json_bytes(model.model_dump(mode="json")) + NEWLINE


def write_record(path: Path, model: BaseModel) -> None:
    """Persist one frozen record durably."""
    write_durable(path, record_bytes(model))


def read_record[RecordT: BaseModel](path: Path, model: type[RecordT]) -> RecordT | None:
    """Read one record: `None` when absent, `WrapperDirError` when malformed."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise WrapperDirError(_MSG_UNREADABLE.format(path=path, reason=exc)) from exc
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise WrapperDirError(
            _MSG_MALFORMED.format(path=path, model=model.__name__, reason=exc)
        ) from exc


class WrapperPaths:
    """Every path of one instance's wrapper directory, derived not configured."""

    def __init__(self, config: SupervisorConfig, root_id: str) -> None:
        self._config = config
        self._root_id = root_id

    @property
    def config(self) -> SupervisorConfig:
        """The injected supervisor configuration."""
        return self._config

    @property
    def root_id(self) -> str:
        """The instance this wrapper directory belongs to."""
        return self._root_id

    @property
    def instance_dir(self) -> Path:
        """`.wf/<root_id>/` — the instance's observation cache."""
        return self._config.wrapper_root / self._root_id

    @property
    def worktree(self) -> Path:
        """The §5.4 per-instance worktree path."""
        return self.instance_dir / WORKTREE_DIR

    @property
    def verify_tree(self) -> Path:
        """The throwaway detached checkout §7.3's checks run in.

        Outside the runner's working tree on purpose: a check executed where
        the runner can still edit files grades the working tree, not the
        artifact commit the evidence NAMES (§7.3, §7.4).
        """
        return self.instance_dir / VERIFY_TREE_DIR

    @property
    def workspace_record(self) -> Path:
        """The §5.4 worktree record / §12 in-repo band record."""
        return self.instance_dir / WORKSPACE_RECORD

    @property
    def attribution_record(self) -> Path:
        """The §12 positive-attribution record — what the runner provably made.

        Instance-scoped because the §12 execution band is: one active runner
        per repo path, ever, so this file has exactly one writer at a time.
        """
        return self.instance_dir / ATTRIBUTION_RECORD

    @property
    def snapshot_index(self) -> Path:
        """The throwaway `GIT_INDEX_FILE` the pre-destruction snapshot builds in.

        Inside `.wf/`, never inside the repo: it is a git index file, and one
        lying in a working tree is both destroyable by the reset it protects
        and confusing to every git command run there.
        """
        return self.instance_dir / SNAPSHOT_INDEX

    @property
    def band_lock(self) -> Path:
        """The §12 single-flight lock, scoped to the repo this wrapper serves.

        It lives beside the repo rather than inside it: a lock file a
        `git clean -fdx` can delete is not an execution band. That is a
        deviation from §4's "scoped to the repo path", with the consequence
        that two wrapper roots over one repo would not exclude each other —
        recorded as a §14 deferred row so phase 5 sees it when it resolves
        wrapper roots, not only here.
        """
        return self._config.wrapper_root / BAND_LOCK

    def activation_dir(self, activation_id: str) -> Path:
        """`.wf/<root_id>/<activation_id>/` — one activation's artifacts."""
        return self.instance_dir / activation_id

    def ensure_activation_dir(self, activation_id: str) -> Path:
        """Create the activation directory (and its artifact dir) if absent."""
        directory = self.activation_dir(activation_id)
        (directory / ARTIFACT_DIR).mkdir(parents=True, exist_ok=True)
        return directory

    def receipt(self, activation_id: str) -> Path:
        """The §5.2 launch receipt — the fork barrier's durable condition."""
        return self.activation_dir(activation_id) / RECEIPT_FILE

    def ledger(self, activation_id: str) -> Path:
        """The §5.2 append-only exec ledger."""
        return self.activation_dir(activation_id) / LEDGER_FILE

    def log(self, activation_id: str) -> Path:
        """`log_path`: the runner's machine event stream (§5.3)."""
        return self.activation_dir(activation_id) / LOG_FILE

    def outcome(self, activation_id: str) -> Path:
        """`$WF_OUTCOME_FILE` — THE reserved outcome channel (§6)."""
        return self.activation_dir(activation_id) / OUTCOME_FILE

    def effects(self, activation_id: str) -> Path:
        """`$WF_EFFECTS_FILE` — the declared-paths manifest (§6)."""
        return self.activation_dir(activation_id) / EFFECTS_FILE

    def artifacts(self, activation_id: str) -> Path:
        """`$WF_ARTIFACT_DIR` — structured outputs, writable regardless of `writes`."""
        return self.activation_dir(activation_id) / ARTIFACT_DIR

    def exit_file(self, activation_id: str) -> Path:
        """The §5.3 exit file, demoted to a crash-window fallback once bd has it."""
        return self.activation_dir(activation_id) / EXIT_FILE

    def completion(self, activation_id: str) -> Path:
        """The computed §7 evidence, written AFTER the exit file.

        Its presence is what tells a later tick the §7 computation finished:
        an exit file without it is "exited, evidence incomplete" — re-run §7,
        never a §5.6 case-3 loss of a completed run.
        """
        return self.activation_dir(activation_id) / COMPLETION_FILE

    def stale_flag(self, activation_id: str) -> Path:
        """The §8.2 stale flag."""
        return self.activation_dir(activation_id) / STALE_FLAG

    def steer_intent(self, activation_id: str) -> Path:
        """The §8.1 steer intent, persisted before any signal is sent."""
        return self.activation_dir(activation_id) / STEER_INTENT


class ExecLedger:
    """The append-only §5.2 exec ledger for one activation.

    One line per real exec — the instrumentation drills 1, 2, 10 and 22 assert
    on. Appending is the child's job (`launch.py`); this class only builds the
    line and reads the file back.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        """The ledger file."""
        return self._path

    @staticmethod
    def line(entry: ExecLedgerEntry) -> bytes:
        """One ledger line: canonical JSON plus the newline `wc -l` counts."""
        return record_bytes(entry)

    def raw_lines(self) -> tuple[bytes, ...]:
        """Every non-empty line, unparsed — what `wc -l` sees."""
        try:
            raw = self._path.read_bytes()
        except FileNotFoundError:
            return ()
        except OSError as exc:
            raise WrapperDirError(
                _MSG_UNREADABLE.format(path=self._path, reason=exc)
            ) from exc
        return tuple(line for line in raw.split(NEWLINE) if line.strip())

    def count(self) -> int:
        """How many execs this activation has recorded."""
        return len(self.raw_lines())

    def entries(self) -> tuple[ExecLedgerEntry, ...]:
        """The parseable entries. A torn final line is skipped, never raised.

        A crash can leave a partial last line; refusing to read the ledger at
        all because of it would turn a recoverable dispatch into a crash loop
        (drill 18). `count()` still counts it, which is the conservative side:
        an exec that may have happened is treated as one that did.
        """
        parsed: list[ExecLedgerEntry] = []
        for line in self.raw_lines():
            try:
                parsed.append(ExecLedgerEntry.model_validate_json(line))
            except ValidationError:
                continue
        return tuple(parsed)

    def has_launch(self, launch_id: str) -> bool:
        """Whether a child ever crossed the barrier under this `launch_id`."""
        return any(entry.launch_id == launch_id for entry in self.entries())


def read_tail(path: Path, limit: int) -> str:
    """The last `limit` bytes of a file, decoded leniently (§8.2's 2KB tail).

    Lenient because the tail of a JSONL stream is routinely a partial UTF-8
    sequence, and a log tail is evidence for a human, never a parsed carrier.
    """
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            handle.seek(max(0, size - limit))
            return handle.read(limit).decode(ENCODING, errors="replace")
    except (FileNotFoundError, NotADirectoryError):
        return ""
    except OSError as exc:
        raise WrapperDirError(_MSG_UNREADABLE.format(path=path, reason=exc)) from exc


def read_json_documents(path: Path) -> tuple[object, ...]:
    """Every whitespace-separated JSON document in a file (§6 marker channel).

    Returns all of them, so "exactly one marker" can be CHECKED rather than
    assumed: a runner that appends a second marker must be caught, not have its
    first or last silently win (§6, drill 15).
    """
    raw = path.read_text(encoding=ENCODING)
    decoder = json.JSONDecoder()
    documents: list[object] = []
    index = 0
    while index < len(raw):
        if raw[index].isspace():
            index += 1
            continue
        document, index = decoder.raw_decode(raw, index)
        documents.append(document)
    return tuple(documents)
