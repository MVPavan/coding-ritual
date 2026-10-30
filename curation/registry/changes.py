"""Changed-since-ruled: the §4 baseline cascade and its git probes."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Any

from curation.registry.config import RegistryConfig
from curation.registry.models import ChangeInfo, Event, RoundHeader
from curation.scan.models import Capability


def _diff_folder(cap: Capability) -> str:
    """The submodule-relative path to diff for a capability — a skill's whole
    folder, or a single-file capability's path."""
    if cap.kind.value == "skill":
        parent = str(Path(cap.canonical_path).parent)
        if parent and parent != ".":
            return f"{parent}/"
    return cap.canonical_path


GIT_TIMEOUT = 15


def _git_returncode(submodule: Path, *args: str) -> int | None:
    """Run git in `submodule`, returning its exit code, or None when the process
    cannot run at all (git missing, not a repo, timeout) — never raising so a
    broken baseline becomes "unknown" rather than crashing `gap` (review #19)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(submodule), *args],
            capture_output=True,
            timeout=GIT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.returncode


def _commit_exists(submodule: Path, sha: str) -> bool:
    return _git_returncode(submodule, "cat-file", "-e", f"{sha}^{{commit}}") == 0


def _git_diff_changed(
    submodule: Path, base: str, pin: str | None, folder: str
) -> bool | None:
    """True/False whether `folder` differs between `base` and `pin` (HEAD when
    `pin` is None); None when the diff cannot be run (e.g. commit absent)."""
    if not submodule.is_dir() or not _commit_exists(submodule, base):
        return None
    if pin and not _commit_exists(submodule, pin):
        return None
    args = ["diff", "--quiet", base]
    if pin:
        args.append(pin)
    args += ["--", folder]
    code = _git_returncode(submodule, *args)
    if code == 0:
        return False
    if code == 1:
        return True
    return None


def _change_info(
    cfg: RegistryConfig,
    ref: Any,
    cap: Capability,
    event: Event,
    header: RoundHeader | None,
) -> ChangeInfo:
    """Changed-since-ruled with the §4 baseline cascade."""
    src = event.source
    repo = ref.repo
    submodule = cfg.repo_root / "reference_harnesses" / repo
    folder = _diff_folder(cap)
    pin = ref.source_commit
    base_sha = src.sha if src else None
    round_pin = header.pins.get(repo) if header else None

    display_base = base_sha or round_pin
    diff_cmd: str | None = None
    label: str | None = None
    if display_base:
        # shlex.join over an argument array so a hostile path/SHA can never become
        # executable shell when the printed command is pasted (review #11).
        argv = ["git", "-C", f"reference_harnesses/{repo}", "diff", display_base]
        if pin:
            argv.append(pin)
        argv += ["--", folder]
        diff_cmd = shlex.join(argv)
        if not base_sha and round_pin:
            label = "baseline inferred from round pin"

    # The §4 cascade, exactly: tree_hash → git diff on sha → git diff on the
    # round pin → unknown. No content_hash fallback (review #1); an unavailable
    # baseline stays unknown rather than silently reading "no".
    changed = "unknown"
    if src and src.tree_hash and cap.tree_hash:
        changed = "yes" if src.tree_hash != cap.tree_hash else "no"
    elif base_sha:
        res = _git_diff_changed(submodule, base_sha, pin, folder)
        if res is not None:
            changed = "yes" if res else "no"
    elif round_pin:
        res = _git_diff_changed(submodule, round_pin, pin, folder)
        if res is not None:
            changed = "yes" if res else "no"
    return ChangeInfo(changed=changed, diff_cmd=diff_cmd, label=label)
