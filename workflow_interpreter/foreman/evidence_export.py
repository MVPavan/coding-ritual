"""Export verified producer evidence as engine-owned, read-only file pointers."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Final

from workflow_interpreter.bdio import (
    ActivationRecord,
    Evidence,
    InputBinding,
    RootRecord,
)
from workflow_interpreter.foreman.envelope import InputsUnavailable
from workflow_interpreter.foreman.execution import resolved_node
from workflow_interpreter.supervisor.errors import GitCommandError
from workflow_interpreter.supervisor.gitcmd import GitOutputTooLarge, GitSubcommand
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.paths import write_durable

EXPORT_MAX_DIFF_BYTES: Final[int] = 8 * 1024 * 1024
EXPORT_MAX_REPORT_BYTES: Final[int] = 4 * 1024 * 1024
EXPORT_MAX_REPORTS: Final[int] = 256
EXPORT_MAX_TOTAL_BYTES: Final[int] = 32 * 1024 * 1024
_TREE_LIST_MAX_BYTES: Final[int] = 2 * 1024 * 1024
_REGULAR_MODES: Final[frozenset[str]] = frozenset({"100644", "100755"})
_INDEX_NAME: Final[str] = "index.json"

Report = tuple[str, str, bytes]


def export_reference(
    git: Git,
    repo_root: Path,
    activation_dir: Path,
    root: RootRecord,
    binding: InputBinding,
    producer: ActivationRecord,
) -> str:
    """Re-verify bound evidence, publish it atomically, and return one pointer."""
    if producer.activation_id != binding.producer_activation_id:
        raise InputsUnavailable("input producer does not match its binding")
    evidence = producer.metadata.evidence
    if evidence is None:
        raise InputsUnavailable("input producer has no evidence")
    base: str | None = None
    candidate: str | None = None
    tree: str | None = None
    diff: bytes | None = None
    try:
        if resolved_node(root, producer.metadata.node).node.writes:
            artifact = evidence.artifact
            base = (
                producer.metadata.pre_attempt_commit
                or producer.metadata.intended_base_commit
            )
            if artifact is None or base is None:
                raise InputsUnavailable(
                    "writing input has incomplete artifact evidence"
                )
            candidate, tree = artifact.commit_oid, artifact.tree_oid
            if (
                tree != binding.digest
                or git.ref_target(binding.artifact_ref, cwd=repo_root) != candidate
                or git.tree_oid(candidate, cwd=repo_root) != tree
                or not git.commit_exists(base, cwd=repo_root)
                or not git.is_ancestor(base, candidate, cwd=repo_root)
            ):
                raise InputsUnavailable("writing artifact pin does not resolve")
            diff = git.bounded_bytes(
                GitSubcommand.DIFF,
                "--no-ext-diff",
                "--no-textconv",
                base,
                candidate,
                cwd=repo_root,
                limit=EXPORT_MAX_DIFF_BYTES,
            )
            reports = _reports(git, repo_root, evidence, initial_size=len(diff))
        else:
            if (
                evidence.outputs_ref != binding.artifact_ref
                or evidence.outputs_tree_oid != binding.digest
            ):
                raise InputsUnavailable("output tree does not match its binding")
            reports = _reports(git, repo_root, evidence, required=True)
    except GitOutputTooLarge as error:
        raise InputsUnavailable(
            f"reference evidence exceeds export limit: {error}"
        ) from None
    except (GitCommandError, UnicodeError, OSError) as error:
        raise InputsUnavailable(
            f"reference evidence could not be exported: {error}"
        ) from None

    try:
        publication = _publication_dir(
            activation_dir, binding, producer, base, candidate, tree, reports
        )
        _publish(publication, diff, reports, producer, base, candidate, tree)
    except (OSError, UnicodeError) as error:
        raise InputsUnavailable(
            f"reference evidence could not be published: {error}"
        ) from None
    pointer: dict[str, str] = {
        "index_path": str(publication / _INDEX_NAME),
        "producer_activation_id": producer.activation_id,
        "producer_node": producer.metadata.node,
    }
    for key, value in (
        ("base_commit", base),
        ("candidate_commit", candidate),
        ("candidate_tree", tree),
    ):
        if value is not None:
            pointer[key] = value
    return json.dumps(pointer, sort_keys=True, separators=(",", ":"))


def _reports(
    git: Git,
    repo_root: Path,
    evidence: Evidence,
    *,
    required: bool = False,
    initial_size: int = 0,
) -> tuple[Report, ...]:
    """Read only bounded regular blobs from a pinned output tree."""
    ref, tree = evidence.outputs_ref, evidence.outputs_tree_oid
    if ref is None and tree is None and not required:
        return ()
    if not isinstance(ref, str) or not isinstance(tree, str):
        raise InputsUnavailable("published reports are not completely pinned")
    commit = git.ref_target(ref, cwd=repo_root)
    if commit is None or git.tree_oid(commit, cwd=repo_root) != tree:
        raise InputsUnavailable("published report tree does not resolve")
    entries = git.tree_blobs(
        tree, cwd=repo_root, limit=_TREE_LIST_MAX_BYTES, max_entries=EXPORT_MAX_REPORTS
    )
    reports: list[Report] = []
    total = initial_size
    for mode, oid, logical_path in entries:
        if mode not in _REGULAR_MODES:
            raise InputsUnavailable("published reports contain an unsupported entry")
        body = git.bounded_bytes(
            GitSubcommand.CAT_FILE,
            "blob",
            oid,
            cwd=repo_root,
            limit=EXPORT_MAX_REPORT_BYTES,
        )
        if total + len(body) > EXPORT_MAX_TOTAL_BYTES:
            raise InputsUnavailable("reference evidence exceeds total export limit")
        total += len(body)
        reports.append((logical_path, oid, body))
    return tuple(reports)


def _publication_dir(
    activation_dir: Path,
    binding: InputBinding,
    producer: ActivationRecord,
    base: str | None,
    candidate: str | None,
    tree: str | None,
    reports: tuple[Report, ...],
) -> Path:
    _safe_directory(activation_dir)
    parent = activation_dir / "evidence"
    if parent.exists() or parent.is_symlink():
        _safe_directory(parent)
    else:
        parent.mkdir(mode=0o700)
    fingerprint = json.dumps(
        {
            "binding": binding.model_dump(mode="json"),
            "producer": producer.activation_id,
            "base": base,
            "candidate": candidate,
            "tree": tree,
            "reports": [(path, oid) for path, oid, _ in reports],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return parent / hashlib.sha256(fingerprint).hexdigest()[:24]


def _safe_directory(path: Path) -> None:
    """Refuse a symlink or non-directory at every engine-owned parent."""
    try:
        path.lstat()
    except FileNotFoundError as error:
        raise InputsUnavailable(f"evidence parent is missing: {path}") from error
    if not path.is_dir() or path.is_symlink():
        raise InputsUnavailable(f"evidence parent is not a safe directory: {path}")


def _publish(
    destination: Path,
    diff: bytes | None,
    reports: tuple[Report, ...],
    producer: ActivationRecord,
    base: str | None,
    candidate: str | None,
    tree: str | None,
) -> None:
    """Publish a complete staged set; index is written only after all bodies."""
    parent = destination.parent
    _safe_directory(parent)
    if os.path.lexists(destination):
        _remove_engine_tree(destination)
    stage = parent / f".{destination.name}.{uuid.uuid4().hex}.stage"
    stage.mkdir(mode=0o700)
    try:
        index: dict[str, object] = {
            "version": 1,
            "producer_activation_id": producer.activation_id,
            "producer_node": producer.metadata.node,
            "reports": [],
        }
        for key, value in (
            ("base_commit", base),
            ("candidate_commit", candidate),
            ("candidate_tree", tree),
        ):
            if value is not None:
                index[key] = value
        if diff is not None:
            write_durable(stage / "diff-000.patch", diff)
            index["diff_path"] = str(destination / "diff-000.patch")
        report_index: list[dict[str, str]] = []
        for position, (logical_path, oid, body) in enumerate(reports):
            name = f"report-{position:03d}.txt"
            write_durable(stage / name, body)
            report_index.append(
                {
                    "logical_path": logical_path,
                    "blob_oid": oid,
                    "path": str(destination / name),
                }
            )
        index["reports"] = report_index
        write_durable(
            stage / _INDEX_NAME,
            json.dumps(index, sort_keys=True, separators=(",", ":")).encode() + b"\n",
        )
        os.replace(stage, destination)
        _fsync(parent)
    except BaseException:
        try:
            if os.path.lexists(stage):
                _remove_engine_tree(stage)
        except (OSError, InputsUnavailable):
            pass
        raise


def _remove_engine_tree(path: Path) -> None:
    _safe_directory(path)
    for root, directories, files in os.walk(path, topdown=True, followlinks=False):
        for name in (*directories, *files):
            if (Path(root) / name).is_symlink():
                raise InputsUnavailable("unsafe stale evidence entry")
    shutil.rmtree(path)


def _fsync(directory: Path) -> None:
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
