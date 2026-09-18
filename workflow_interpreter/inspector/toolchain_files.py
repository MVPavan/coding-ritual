"""Bounded private copies and selective imports from uv's wheel cache."""

import os
import shutil
import stat
import subprocess
from pathlib import Path

from workflow_interpreter.inspector import toolchain_constants as tc
from workflow_interpreter.inspector.toolchain_models import (
    CopyMethod,
    ToolchainConfig,
    ToolchainUnavailable,
)


def measure(
    root: Path,
    config: ToolchainConfig,
    *,
    allow_internal_absolute: bool = False,
) -> int:
    """Reject special files and escaping links before copying a bounded tree."""
    total = 0
    entries = 0
    pending = [root]
    while pending:
        path = pending.pop()
        entries += 1
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            if (
                path.readlink().is_absolute() and not allow_internal_absolute
            ) or not path.resolve().is_relative_to(root):
                raise ToolchainUnavailable(tc.MSG_ESCAPE.format(path=path))
        elif stat.S_ISDIR(info.st_mode):
            for child in path.iterdir():
                pending.append(child)
                if entries + len(pending) > config.max_entries:
                    raise ToolchainUnavailable(tc.MSG_BOUNDS)
        elif stat.S_ISREG(info.st_mode):
            total += info.st_size
        else:
            raise ToolchainUnavailable(tc.MSG_SPECIAL.format(path=path))
        if entries > config.max_entries or total > config.max_bytes:
            raise ToolchainUnavailable(tc.MSG_BOUNDS)
    return total


def copy_tree(source: Path, target: Path, config: ToolchainConfig) -> CopyMethod:
    """Copy inodes, requesting reflinks when available and ordinary copies otherwise."""
    size = measure(source, config)
    target.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(target).free < size + config.reserve_bytes:
        raise ToolchainUnavailable(tc.MSG_DISK)
    for method, option in (
        (CopyMethod.AUTO, "--reflink=auto"),
        (CopyMethod.PLAIN, "--reflink=never"),
    ):
        result = subprocess.run(
            [
                config.copy_binary,
                "-R",
                "--no-preserve=ownership",
                option,
                "--",
                str(source) + "/.",
                str(target),
            ],
            timeout=config.timeout_s,
            check=False,
            capture_output=True,
        )
        if result.returncode == 0:
            measure(target, config)
            return method
    raise ToolchainUnavailable(tc.MSG_COPY)


def sync_tree(root: Path) -> None:
    """Flush files and directory entries before publishing a prepared tree."""
    for directory, _, files in os.walk(root, followlinks=False):
        for name in files:
            path = Path(directory) / name
            if not path.is_symlink():
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
        descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def import_wheels(
    host: Path,
    target: Path,
    packages: tuple[tuple[str, str], ...],
    config: ToolchainConfig,
) -> None:
    """Import only locked wheel versions, relocating uv's archive links internally.

    uv validates the imported registry cache against the pinned lock during sync.
    Unknown cache layouts are misses, never a reason to copy the entire cache.
    """
    wheels = host / tc.WHEELS
    indexes = [wheels / tc.PYPI]
    index = wheels / tc.INDEX
    if index.is_dir():
        indexes.extend(index.iterdir())
    scanned = 0
    for bucket in indexes:
        for name, version in packages:
            directory = bucket / name
            if not directory.is_dir():
                continue
            for entry in directory.iterdir():
                scanned += 1
                if scanned > config.max_entries:
                    raise ToolchainUnavailable(tc.MSG_INDEX_BOUND)
                if not entry.name.startswith(version + "-"):
                    continue
                destination = target / entry.relative_to(host)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if entry.is_symlink():
                    archive = entry.resolve(strict=True)
                    if not archive.is_relative_to(host / tc.ARCHIVES):
                        raise ToolchainUnavailable(tc.MSG_ARCHIVE_LINK)
                    private_archive = target / archive.relative_to(host)
                    if not private_archive.exists():
                        copy_tree(archive, private_archive, config)
                    destination.symlink_to(
                        os.path.relpath(private_archive, destination.parent)
                    )
                elif entry.is_file():
                    if entry.stat().st_size > config.max_bytes:
                        raise ToolchainUnavailable(tc.MSG_WHEEL_BOUND)
                    shutil.copyfile(entry, destination)
                else:
                    raise ToolchainUnavailable(tc.MSG_WHEEL_ENTRY)
                measure(target, config)


def read_regular(path: Path, limit: int) -> bytes | None:
    """Read bounded metadata without following links or blocking on special files."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ToolchainUnavailable(tc.MSG_PIN_REGULAR.format(path=path))
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise ToolchainUnavailable(tc.MSG_PIN_SIZE.format(path=path))
        return data
    finally:
        os.close(descriptor)


def relocate_links(root: Path, config: ToolchainConfig) -> None:
    """Relocate uv-created internal links in an unlaunched host staging tree."""
    measure(root, config, allow_internal_absolute=True)
    for directory, directories, files in os.walk(root, followlinks=False):
        for name in (*directories, *files):
            path = Path(directory) / name
            if path.is_symlink() and path.readlink().is_absolute():
                target = path.resolve()
                path.unlink()
                path.symlink_to(os.path.relpath(target, path.parent))
    measure(root, config)
