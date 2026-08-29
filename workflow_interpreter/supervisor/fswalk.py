"""Descriptor-relative filesystem classification for untrusted runner trees."""

from __future__ import annotations

import os
import stat
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Final

_DIRECTORY_FLAGS: Final[int] = (
    os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
)
_ENTRY_FLAGS: Final[int] = os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC


class FsKind(StrEnum):
    """The file kind visible through an already-open descriptor."""

    REGULAR = "regular"
    SYMLINK = "symlink"
    DIRECTORY = "directory"
    OTHER = "other"


def open_root(path: os.PathLike[str] | str) -> int:
    """Open and pin a directory root without accepting a symlink."""
    return os.open(path, _DIRECTORY_FLAGS)


def open_child_dir(parent_fd: int, name: str) -> int:
    """Open a child directory by name beneath an already-pinned parent."""
    return os.open(name, _DIRECTORY_FLAGS, dir_fd=parent_fd)


def open_entry(dir_fd: int, name: str) -> int:
    """Open a child inode for classification without reading its contents."""
    return os.open(name, _ENTRY_FLAGS, dir_fd=dir_fd)


def classify(fd: int) -> FsKind:
    """Classify the inode held by `fd` from its mode alone."""
    mode = os.fstat(fd).st_mode
    if stat.S_ISREG(mode):
        return FsKind.REGULAR
    if stat.S_ISLNK(mode):
        return FsKind.SYMLINK
    if stat.S_ISDIR(mode):
        return FsKind.DIRECTORY
    return FsKind.OTHER


def classify_relative(root_fd: int, relative: str) -> FsKind:
    """Classify a relative path without resolving a symlinked ancestor."""
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"invalid relative path: {relative!r}")
    directory_fd = os.dup(root_fd)
    try:
        for name in parts[:-1]:
            child_fd = open_child_dir(directory_fd, name)
            os.close(directory_fd)
            directory_fd = child_fd
        entry_fd = open_entry(directory_fd, parts[-1])
        try:
            return classify(entry_fd)
        finally:
            os.close(entry_fd)
    finally:
        os.close(directory_fd)


def read_link_relative(root_fd: int, relative: str) -> str:
    """Read a link target through pinned directory descriptors only."""
    parts = PurePosixPath(relative).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise ValueError(f"invalid relative path: {relative!r}")
    directory_fd = os.dup(root_fd)
    try:
        for name in parts[:-1]:
            child_fd = open_child_dir(directory_fd, name)
            os.close(directory_fd)
            directory_fd = child_fd
        return os.readlink(parts[-1], dir_fd=directory_fd)
    finally:
        os.close(directory_fd)


__all__ = [
    "FsKind",
    "classify",
    "classify_relative",
    "open_child_dir",
    "open_entry",
    "open_root",
    "read_link_relative",
]
