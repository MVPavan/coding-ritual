"""Private pre-destruction snapshot plumbing."""

from __future__ import annotations

import os
import shutil
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.supervisor import fswalk
from workflow_interpreter.supervisor.gitcmd import (
    GIT_INDEX_FILE,
    SNAPSHOT_IDENTITY,
    GitSubcommand,
    GitTransport,
    chunk_argv,
)

HEAD = "HEAD"
_MODEL = ConfigDict(frozen=True, extra="forbid")
_REGULAR_MODE = "100644"
_EXECUTABLE_MODE = "100755"
_SYMLINK_MODE = "120000"
_GITLINK_MODE = "160000"


class StageEntry(BaseModel):
    """One NUL-framed index entry emitted by `git ls-files --stage`."""

    model_config = _MODEL

    mode: str
    oid: str
    path: str


def parse_stage_entries(text: str) -> tuple[StageEntry, ...]:
    """Parse `ls-files -z --stage` without ever line-splitting a pathname."""
    entries: list[StageEntry] = []
    for record in text.split("\0"):
        if not record:
            continue
        header, separator, path = record.partition("\t")
        fields = header.split()
        if not separator or len(fields) != 3:
            raise ValueError("invalid git stage entry")
        entries.append(StageEntry(mode=fields[0], oid=fields[1], path=path))
    return tuple(entries)


def snapshot_commit(
    git: GitTransport,
    *,
    message: str,
    parents: Sequence[str],
    index_path: Path,
    cwd: Path,
) -> str:
    """Commit a filter-free working-tree snapshot through a throwaway index."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.unlink(missing_ok=True)
    env = {GIT_INDEX_FILE: str(index_path), **SNAPSHOT_IDENTITY}
    git.run(GitSubcommand.READ_TREE, HEAD, cwd=cwd, env=env)
    staged = parse_stage_entries(
        git.run(GitSubcommand.LS_FILES, "-z", "--stage", cwd=cwd, env=env).stdout
    )
    indexed = {entry.path: entry for entry in staged}
    untracked = tuple(
        path
        for path in git.run(
            GitSubcommand.LS_FILES,
            "-z",
            "--others",
            "--exclude-standard",
            cwd=cwd,
            env=env,
        ).stdout.split("\0")
        if path and path not in indexed
    )
    pending: list[tuple[str, str, Path]] = []
    deletions: list[str] = []
    links = index_path.parent / "prereset.links"
    links.mkdir(parents=True, exist_ok=True)
    try:
        root_fd = fswalk.open_root(cwd)
        try:
            for path in (*indexed, *untracked):
                cached = indexed.get(path)
                if cached is not None and cached.mode == _GITLINK_MODE:
                    continue
                if path.endswith("/"):
                    continue
                try:
                    kind = fswalk.classify_relative(root_fd, path)
                except (FileNotFoundError, NotADirectoryError):
                    if cached is not None:
                        deletions.append(path)
                    continue
                if kind is fswalk.FsKind.DIRECTORY or kind is fswalk.FsKind.OTHER:
                    if cached is not None:
                        deletions.append(path)
                    continue
                source = cwd / path
                mode = _REGULAR_MODE
                if kind is fswalk.FsKind.SYMLINK:
                    source = links / str(len(pending))
                    source.write_bytes(
                        os.fsencode(fswalk.read_link_relative(root_fd, path))
                    )
                    mode = _SYMLINK_MODE
                elif source.stat().st_mode & 0o111:
                    mode = _EXECUTABLE_MODE
                pending.append((mode, path, source))
        finally:
            os.close(root_fd)
        additions: list[tuple[str, str, str]] = []
        sources = tuple(str(source) for _, _, source in pending)
        pending_index = 0
        for chunk in chunk_argv(
            sources,
            fixed=(GitSubcommand.HASH_OBJECT.value, "-w", "--no-filters", "--"),
        ):
            oids = git.run(
                GitSubcommand.HASH_OBJECT,
                "-w",
                "--no-filters",
                "--",
                *chunk,
                cwd=cwd,
                env=env,
            ).stdout.splitlines()
            if len(oids) != len(chunk):
                raise ValueError("git hash-object returned an unexpected oid count")
            for oid in oids:
                mode, path, _ = pending[pending_index]
                additions.append((mode, oid, path))
                pending_index += 1
        cacheinfo = tuple(f"{mode},{oid},{path}" for mode, oid, path in additions)
        for chunk in chunk_argv(
            cacheinfo,
            fixed=(GitSubcommand.UPDATE_INDEX.value, "--add", "--replace"),
            repeated=("--cacheinfo",),
        ):
            update_args = ["--add", "--replace"]
            for entry in chunk:
                update_args.extend(("--cacheinfo", entry))
            git.run(
                GitSubcommand.UPDATE_INDEX,
                *update_args,
                cwd=cwd,
                env=env,
            )
        for chunk in chunk_argv(
            deletions, fixed=(GitSubcommand.UPDATE_INDEX.value, "--force-remove", "--")
        ):
            git.run(
                GitSubcommand.UPDATE_INDEX,
                "--force-remove",
                "--",
                *chunk,
                cwd=cwd,
                env=env,
            )
        tree = git.run(GitSubcommand.WRITE_TREE, cwd=cwd, env=env).text
        args: list[str] = [tree]
        for parent in parents:
            args += ["-p", parent]
        return git.run(
            GitSubcommand.COMMIT_TREE, *args, "-m", message, cwd=cwd, env=env
        ).text
    finally:
        shutil.rmtree(links, ignore_errors=True)


def commit_directory(
    git: GitTransport,
    paths: tuple[str, ...],
    *,
    root: Path,
    message: str,
    index_path: Path,
    cwd: Path,
) -> str:
    """Commit selected wrapper-owned regular files through a throwaway index."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.unlink(missing_ok=True)
    env = {
        "GIT_DIR": str(cwd / ".git"),
        GIT_INDEX_FILE: str(index_path),
        **SNAPSHOT_IDENTITY,
    }
    try:
        pending = tuple(str(root / path) for path in paths)
        oids: list[str] = []
        for chunk in chunk_argv(
            pending,
            fixed=(GitSubcommand.HASH_OBJECT.value, "-w", "--no-filters", "--"),
        ):
            oids.extend(
                git.run(
                    GitSubcommand.HASH_OBJECT,
                    "-w",
                    "--no-filters",
                    "--",
                    *chunk,
                    cwd=cwd,
                    env=env,
                ).stdout.splitlines()
            )
        if len(oids) != len(paths):
            raise ValueError("git hash-object returned an unexpected oid count")
        entries = tuple(
            f"100644,{oid},{path}" for oid, path in zip(oids, paths, strict=True)
        )
        for chunk in chunk_argv(
            entries,
            fixed=(GitSubcommand.UPDATE_INDEX.value, "--add"),
            repeated=("--cacheinfo",),
        ):
            args = ["--add"]
            for entry in chunk:
                args.extend(("--cacheinfo", entry))
            git.run(GitSubcommand.UPDATE_INDEX, *args, cwd=cwd, env=env)
        tree = git.run(GitSubcommand.WRITE_TREE, cwd=cwd, env=env).text
        return git.run(
            GitSubcommand.COMMIT_TREE, tree, "-m", message, cwd=cwd, env=env
        ).text
    finally:
        index_path.unlink(missing_ok=True)
