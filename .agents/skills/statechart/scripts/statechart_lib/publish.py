"""Results go to a missing or empty folder, staged beside it and moved into
place with one rename."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


class OutputError(Exception):
    """The output folder cannot take the results."""


Identity = tuple[int, int, int] | None  # device, inode, change time; None: absent


def _occupied(out: Path) -> bool:
    return out.exists() and (not out.is_dir() or any(out.iterdir()))


def _identity(out: Path) -> Identity:
    try:
        found = os.stat(out, follow_symlinks=False)
    except FileNotFoundError:
        return None
    return (found.st_dev, found.st_ino, found.st_ctime_ns)


def prepare(out: Path) -> tuple[Path, Identity]:
    """Refuse a folder that already holds something; return the staging
    folder beside it and the output folder's identity, to compare later."""
    if _occupied(out):
        raise OutputError(
            f"{out} already holds files, and results only go to a folder that "
            "is missing or empty; choose another folder with --out"
        )
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{out.name}.staging-", dir=out.parent))
    return stage, _identity(out)


def publish(stage: Path, out: Path, identity: Identity, files: dict[str, str]) -> None:
    """Write the files into the staging folder and move it into place in one
    rename, writing nothing if the output folder was created, removed,
    replaced or filled meanwhile."""
    for name, text in files.items():
        (stage / name).write_text(text)
    if _occupied(out) or _identity(out) != identity:
        raise OutputError(f"{out} changed while the check ran; nothing was written")
    try:
        os.replace(stage, out)  # onto a missing or empty folder: one step
    except OSError as error:
        raise OutputError(
            f"{out} changed while the check ran; nothing was written ({error})"
        ) from None


def discard(*folders: Path | None) -> None:
    for folder in folders:
        if folder is not None:
            shutil.rmtree(folder, ignore_errors=True)
