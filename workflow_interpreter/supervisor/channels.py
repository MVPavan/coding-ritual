"""The three §6 runner channels, read and validated (`exit.py` decides).

`$WF_OUTCOME_FILE`, `$WF_ARTIFACT_DIR` and `$WF_EFFECTS_FILE` are the only ways
a runner reports anything, and all three are wrapper-provided files inside the
wrapper directory — writable regardless of the node's `writes`, so a
`writes = false` reviewer can still report (§6).

Reading them is separated from GRADING them on purpose: everything here returns
`(value, reason)` and refuses to interpret. "Two markers" is a fact about a
file; "two markers means `fail_code`, never fallback routing" is a §7 rule, and
it lives with the other §7 rules.

Also here: the two conventions a PRODUCER and a READER in different modules
have to render identically — the §7.3 pinned-digest key, and the §7.4 committer
identity a runner's commits carry. A convention rendered in two places is a
convention that drifts.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
from pathlib import Path, PurePosixPath
from typing import Final

from pydantic import ValidationError

from workflow_interpreter.bdio import (
    ConfigSource,
    Outcome,
    ResolvedSetting,
    RootRecord,
)
from workflow_interpreter.schema.models import GraphDocument
from workflow_interpreter.supervisor import fswalk
from workflow_interpreter.supervisor.models import EffectsManifest, OutcomeMarker
from workflow_interpreter.supervisor.outputs import OutputsWalk, UnsafeEntry, UnsafeKind
from workflow_interpreter.supervisor.paths import read_json_documents
from workflow_interpreter.supervisor.sandbox import grant_directory

VERIFIER_DIGEST_KEY: Final[str] = "verify.{node}.{program}.sha256"
"""The §7.3 pinned-digest convention in the root's resolved config. §14 defers
a closed resolved-config vocabulary; until then this is the wrapper's, applied
consistently by `verifier_digest_key` — the ONE place producer and reader
render it, so they cannot drift."""

DIGEST_SUFFIX: Final[str] = ".sha256"

ENV_GIT_COMMITTER_NAME: Final[str] = "GIT_COMMITTER_NAME"
ENV_GIT_COMMITTER_EMAIL: Final[str] = "GIT_COMMITTER_EMAIL"
COMMITTER_NAME: Final[str] = "wf-runner"
COMMITTER_EMAIL: Final[str] = "runner+{activation_id}@workflow-interpreter.invalid"
"""The §7.4 identity every commit a runner makes is stamped with, carrying the
ACTIVATION id so one attempt's commits cannot be mistaken for another's.

Set on the child's environment by `RunnerChannels.env()` (§6) and required by
`Workspace.pin_artifact` in addition to path containment. It is an ATTRIBUTION
mechanism, not an authorization one: a runner can unset the variables, and §0.3
already treats the in-process runner as semi-trusted. What it removes is the
ACCIDENT — a dead runner's manifest naming a path the human later commits made
the human's commit "attributable" on path containment alone, and that pin is
what authorizes the next reset to move HEAD off it (probed, Opus#21)."""

REASON_MARKER_ABSENT: Final[str] = "no marker in $WF_OUTCOME_FILE"
REASON_MARKER_COUNT: Final[str] = "expected exactly one marker, found {count}"
REASON_MARKER_INVALID: Final[str] = "marker did not validate: {reason}"
REASON_MARKER_UNDECLARED: Final[str] = (
    "marker claims {outcome}, which node {node} does not declare"
)
REASON_EFFECTS: Final[str] = "$WF_EFFECTS_FILE {detail}"


def _capture_file(source_fd: int, destination: Path, size: int) -> None:
    """Copy a held regular inode into the wrapper-owned output snapshot."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    output_fd: int | None = None
    input_fd: int | None = None
    try:
        output_fd = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
            0o600,
        )
        input_fd = os.open(f"/proc/self/fd/{source_fd}", os.O_RDONLY | os.O_CLOEXEC)
        offset = 0
        while offset < size:
            sent = os.sendfile(output_fd, input_fd, offset, size - offset)
            if sent == 0:
                break
            offset += sent
    except OSError:
        destination.unlink(missing_ok=True)
        raise
    finally:
        if input_fd is not None:
            os.close(input_fd)
        if output_fd is not None:
            os.close(output_fd)


def walk_outputs(
    root: Path,
    snapshot: Path,
    *,
    max_files: int,
    max_bytes: int,
    max_walk_entries: int,
    max_depth: int,
) -> OutputsWalk:
    """Capture bounded regular output files without following runner links."""
    shutil.rmtree(snapshot, ignore_errors=True)
    snapshot.mkdir(parents=True, exist_ok=True)
    try:
        root_fd = fswalk.open_root(root)
    except OSError:
        return OutputsWalk(unsafe=(UnsafeEntry(path=".", kind=UnsafeKind.ROOT),))
    paths: list[str] = []
    unsafe: list[UnsafeEntry] = []
    total = 0
    truncated = False
    seen = 0
    stack: list[tuple[str, int, int, list[os.DirEntry[str]] | None, int]] = [
        ("", root_fd, 0, None, 0)
    ]
    try:
        while stack:
            relative_dir, dir_fd, depth, ordered, index = stack[-1]
            if ordered is None:
                too_wide = False
                try:
                    with os.scandir(dir_fd) as entries:
                        buffered: list[os.DirEntry[str]] = []
                        remaining = max_walk_entries - seen
                        for entry in entries:
                            buffered.append(entry)
                            seen += 1
                            if len(buffered) > remaining:
                                too_wide = True
                                break
                except OSError:
                    unsafe.append(
                        UnsafeEntry(
                            path=relative_dir or ".", kind=UnsafeKind.CAPTURE_FAILED
                        )
                    )
                    _, closed_fd, _, _, _ = stack.pop()
                    os.close(closed_fd)
                    continue
                if too_wide:
                    unsafe.append(
                        UnsafeEntry(path=relative_dir or ".", kind=UnsafeKind.TOO_WIDE)
                    )
                    truncated = True
                    break
                ordered = sorted(buffered, key=lambda entry: entry.name)
                stack[-1] = (relative_dir, dir_fd, depth, ordered, 0)
                continue
            if index == len(ordered):
                _, closed_fd, _, _, _ = stack.pop()
                os.close(closed_fd)
                continue
            entry = ordered[index]
            stack[-1] = (relative_dir, dir_fd, depth, ordered, index + 1)
            relative = f"{relative_dir}/{entry.name}" if relative_dir else entry.name
            try:
                entry_fd = fswalk.open_entry(dir_fd, entry.name)
                kind = fswalk.classify(entry_fd)
            except OSError:
                unsafe.append(
                    UnsafeEntry(path=relative, kind=UnsafeKind.CAPTURE_FAILED)
                )
                continue
            if kind is fswalk.FsKind.DIRECTORY:
                os.close(entry_fd)
                if depth + 1 >= max_depth:
                    unsafe.append(UnsafeEntry(path=relative, kind=UnsafeKind.TOO_DEEP))
                    truncated = True
                    continue
                try:
                    child_fd = fswalk.open_child_dir(dir_fd, entry.name)
                except OSError:
                    unsafe.append(
                        UnsafeEntry(path=relative, kind=UnsafeKind.CAPTURE_FAILED)
                    )
                    continue
                stack.append((relative, child_fd, depth + 1, None, 0))
                continue
            if kind is fswalk.FsKind.SYMLINK:
                unsafe.append(UnsafeEntry(path=relative, kind=UnsafeKind.SYMLINK))
                os.close(entry_fd)
                continue
            if kind is not fswalk.FsKind.REGULAR:
                unsafe.append(UnsafeEntry(path=relative, kind=UnsafeKind.SPECIAL))
                os.close(entry_fd)
                continue
            size = os.fstat(entry_fd).st_size
            if len(paths) >= max_files or total + size > max_bytes:
                truncated = True
                os.close(entry_fd)
                continue
            try:
                _capture_file(entry_fd, snapshot / relative, size)
            except OSError:
                unsafe.append(
                    UnsafeEntry(path=relative, kind=UnsafeKind.CAPTURE_FAILED)
                )
            else:
                paths.append(relative)
                total += size
            finally:
                os.close(entry_fd)
    finally:
        for _, descriptor, _, _, _ in stack:
            os.close(descriptor)
    return OutputsWalk(
        paths=tuple(sorted(paths)),
        unsafe=tuple(sorted(unsafe, key=lambda item: (item.path, item.kind.value))),
        truncated=truncated,
        total_bytes=total,
    )


def runner_committer_email(activation_id: str) -> str:
    """The §7.4 committer address one activation's runner commits under."""
    return COMMITTER_EMAIL.format(activation_id=activation_id)


def verifier_digest_key(node_name: str, cwd: str | None, program: str) -> str:
    """The §7.3 pin key for one check's program — keyed by WHERE it resolves.

    The program alone was not a key. Two legitimate checks on one node can
    declare the same `argv[0]` under different `cwd`s (`scripts/check.sh` in
    two subprojects), and they are different files with different digests: the
    producer wrote one and overwrote the other, so one of the two checks failed
    provenance forever and was never run.

    The key is `cwd / argv[0]` AS DECLARED in the pinned graph — the two strings
    joined, not the path they resolve to. That is deliberate and it is what both
    callers can compute: the producer (`pin_verifier_digests`) hashes at
    instantiation, against the repo, before any checkout exists, and the reader
    (`verify.run_checks`) looks the pin up before it resolves anything. Naming
    it the "resolved path" was simply wrong — `..`, a symlink or an absolute
    `cwd` all key differently from where they land, and `ResolvedCheck.escapes`
    is what refuses those rather than this.

    Both callers render it HERE, because a convention rendered in two places is
    a convention that drifts.
    """
    return VERIFIER_DIGEST_KEY.format(
        node=node_name, program=(PurePosixPath(cwd or "") / program).as_posix()
    )


def pinned_verifier_digests(root: RootRecord) -> dict[str, str]:
    """The §7.3 verify-script digests pinned into the root at instantiation."""
    return {
        setting.key: str(setting.value)
        for setting in root.metadata.resolved_config
        if setting.key.endswith(DIGEST_SUFFIX)
    }


def pin_verifier_digests(
    document: GraphDocument, repo_root: Path
) -> tuple[ResolvedSetting, ...]:
    """Hash every declared `verify` program, as resolved config for `create_root`.

    The PRODUCER for `pinned_verifier_digests`, which had none: the reader and
    the key convention lived here while the settings themselves were only ever
    built by hand, so nothing guaranteed the two agreed. §7.3's whole claim is
    that the digest was recorded at INSTANTIATION, before any runner could edit
    the script, so this is a function of the pinned graph and the repo at that
    moment and of nothing else.

    A program that is not there hashes to `""`, which no real file matches —
    the check is refused rather than run, which is §7.3's own answer for a
    verifier whose provenance cannot be established.
    """
    digests: dict[str, str] = {}
    for node in document.node:
        for check in node.verify or ():
            argv = shlex.split(check.cmd)
            if not argv:
                continue
            program = repo_root / (check.cwd or "") / argv[0]
            digests[verifier_digest_key(node.name, check.cwd, argv[0])] = (
                sha256_file(program) or ""
            )
    return tuple(
        ResolvedSetting(key=key, value=value, source=ConfigSource.PROJECT_CONFIG)
        for key, value in sorted(digests.items())
    )


def sha256_file(path: Path) -> str | None:
    """The sha256 of a file, or `None` when it is not there to hash."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError, PermissionError):
        return None


def read_marker(
    path: Path, declared: frozenset[Outcome], node_name: str
) -> tuple[OutcomeMarker | None, str | None]:
    """THE reserved outcome channel (§6): exactly one marker, or a reason why not."""
    try:
        documents = read_json_documents(path)
    except FileNotFoundError:
        return None, REASON_MARKER_ABSENT
    except (OSError, ValueError) as exc:
        return None, REASON_MARKER_INVALID.format(reason=exc)
    if len(documents) != 1:
        return None, REASON_MARKER_COUNT.format(count=len(documents))
    try:
        marker = OutcomeMarker.model_validate(documents[0])
    except ValidationError as exc:
        return None, REASON_MARKER_INVALID.format(reason=exc)
    if marker.outcome not in declared:
        return None, REASON_MARKER_UNDECLARED.format(
            outcome=marker.outcome.value, node=node_name
        )
    return marker, None


def read_effects(path: Path) -> tuple[EffectsManifest | None, str | None]:
    """The declared-paths manifest (§6); missing or unparseable fails closed."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None, REASON_EFFECTS.format(detail="is absent")
    except OSError as exc:
        return None, REASON_EFFECTS.format(detail=f"is unreadable: {exc}")
    try:
        return EffectsManifest.model_validate_json(raw), None
    except ValidationError as exc:
        return None, REASON_EFFECTS.format(detail=f"did not parse: {exc}")


def path_allowed(path: str, allowed_paths: tuple[str, ...]) -> bool:
    """Whether an observed path is exempt from undeclared-effect reporting.

    Not a containment check: §7.5 also exempts whatever the runner declares,
    so this answers "was this change expected here", never "was it allowed"
    (ADR 0001).
    """
    candidate = PurePosixPath(path)
    return any(
        candidate == grant_directory(pattern) or candidate.full_match(pattern)
        for pattern in allowed_paths
    )
