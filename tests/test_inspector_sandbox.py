"""The §2 mount bound: the plan a dispatch computes, and the argv it wraps with.

Everything here is slice 1 of `docs/plans/allowed-paths-enforcement-phase-1.md`:
`plan_for` (three checkout shapes), `wrap` (bind ORDER is mount order) and
`probe` (once per process). The rigs are real — `git init` and `git worktree
add` under `tmp_path` — because the two shapes differ only in what git actually
writes on disk, and a fake `.git` would let a wrong shape pass.

Only the `proc` test needs a real `bwrap`; it skips loudly with `probe().reason`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Final, NamedTuple

import pytest

from workflow_interpreter.inspector.channels import path_allowed
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.errors import (
    SandboxPathRefused,
    SandboxUnavailable,
)
from workflow_interpreter.inspector.profile import TaskSpec, channels_for
from workflow_interpreter.inspector.sandbox import (
    ARG_BIND,
    ARG_DEV_BIND,
    ARG_DIE_WITH_PARENT,
    ARG_END,
    BWRAP_BINARY,
    COMMONDIR_FILE,
    CONFIG_FILE,
    ENV_UV_CACHE_DIR,
    ENV_UV_PYTHON_INSTALL_DIR,
    FS_ROOT,
    GITDIR_FILE,
    REASON_OFF,
    WF_FENCE_DIR,
    SandboxMode,
    SandboxPlan,
    grant_directory,
    plan_for,
    probe,
    reset_probe_cache,
    wrap,
)
from workflow_interpreter.profiles._base import toolchain_env

ROOT_ID: Final[str] = "wf-root-1"
ACTIVATION: Final[str] = "wf-42"
HOST: Final[str] = "lab"
MODEL: Final[str] = "claude-opus-5"
NODE: Final[str] = "implement"
GIT_TIMEOUT_S: Final[float] = 60.0
RUN_TIMEOUT_S: Final[float] = 120.0
GRANT: Final[str] = "tests/acceptance/**"
GRANT_DIR: Final[str] = "tests/acceptance"
SHELL: Final[str] = "/bin/sh"
REFUSED_TEXT: Final[tuple[str, ...]] = (
    "Read-only file system",
    "Device or resource busy",
    "Text file busy",
)
"""A ro-bound FILE refuses a rename over it as `EBUSY`, a ro-bound TREE as
`EROFS` (plan §8) — a test asserting the errno has to accept both."""

GIT_ISOLATION: Final[dict[str, str]] = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
}
"""The host's own git config, dropped: the rig configures every identity the
sandboxed `git commit` needs, and an operator's `~/.gitconfig` must not be able
to decide whether this test passes."""


class Rig(NamedTuple):
    """One dispatch's paths: the two ro roots, the checkout and the channels."""

    repo_root: Path
    wrapper_root: Path
    checkout: Path
    channels: Path


def _git(cwd: Path, *args: str) -> str:
    """Run git in a throwaway rig with an explicit timeout."""
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
    )
    return completed.stdout.strip()


def _init(repo: Path) -> None:
    """A git repo with one commit and an identity a crew can commit under."""
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "--quiet", "--initial-branch=main")
    _git(repo, "config", "user.email", "wf@test")
    _git(repo, "config", "user.name", "wf test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "--quiet", "-m", "initial")


def _rig(tmp_path: Path, checkout: Path) -> Rig:
    """The roots and channels every shape shares, all existing on disk."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    wrapper_root = tmp_path / ".wf"
    channels = wrapper_root / ROOT_ID / ACTIVATION / "channels"
    channels.mkdir(parents=True, exist_ok=True)
    return Rig(repo_root, wrapper_root, checkout, channels)


def _plain_rig(tmp_path: Path) -> Rig:
    """A checkout with no `.git` at all — the first `plan_for` shape."""
    checkout = tmp_path / ".wf" / ROOT_ID / "plain"
    checkout.mkdir(parents=True, exist_ok=True)
    return _rig(tmp_path, checkout)


def _in_repo_rig(tmp_path: Path) -> Rig:
    """An in-repo checkout: `<C> == <M>` and `.git` is a directory."""
    rig = _rig(tmp_path, tmp_path / "repo")
    _init(rig.repo_root)
    return rig


WORKTREE_BRANCH: Final[str] = f"wf/{ROOT_ID}/candidate"
"""Namespaced, because §5.4 names every candidate branch `wf/<root_id>`
(`inspector/artifact.py::BRANCH_TEMPLATE`) and the git write set descends to
the directory holding THIS branch. A rig on a top-level branch would have made
`refs/heads` and `logs/refs/heads` themselves the grant and hidden the whole
point of the narrowing."""
BRANCH_DIR: Final[str] = f"wf/{ROOT_ID}"


def _worktree_rig(tmp_path: Path) -> Rig:
    """A real `git worktree`: `<C>/.git` is a FILE naming `<G>`."""
    rig = _rig(tmp_path, tmp_path / ".wf" / ROOT_ID / "worktree")
    _init(rig.repo_root)
    _git(
        rig.repo_root,
        "worktree",
        "add",
        "--quiet",
        str(rig.checkout),
        "-b",
        WORKTREE_BRANCH,
    )
    return rig


def _gitdir(rig: Rig) -> Path:
    """`<G>` — the worktree's per-worktree git dir under the main repo."""
    return rig.repo_root / ".git" / "worktrees" / rig.checkout.name


def _task(
    rig: Rig,
    *,
    writes: bool = True,
    allowed_paths: tuple[str, ...] = (GRANT,),
) -> TaskSpec:
    """A `TaskSpec` naming this rig's checkout and the grants under test."""
    activation_dir = rig.channels.parent
    return TaskSpec(
        root_id=ROOT_ID,
        activation_id=ACTIVATION,
        node=NODE,
        model=MODEL,
        writes=writes,
        allowed_paths=allowed_paths,
        cwd=str(rig.checkout),
        channels=channels_for(activation_dir, activation_dir / "run.jsonl", ACTIVATION),
    )


def _plan(
    rig: Rig,
    *,
    writes: bool = True,
    allowed_paths: tuple[str, ...] = (GRANT,),
) -> SandboxPlan:
    """`plan_for` over one rig, so no test re-spells the keyword roots."""
    return plan_for(
        _task(rig, writes=writes, allowed_paths=allowed_paths),
        repo_root=rig.repo_root,
        wrapper_root=rig.wrapper_root,
        channels_dir=rig.channels,
    )


def _config(
    tmp_path: Path, sandbox: SandboxMode = SandboxMode.BWRAP
) -> InspectorConfig:
    """An inspector config carrying only the field `probe` reads."""
    return InspectorConfig(
        repo_root=tmp_path / "repo",
        wrapper_root=tmp_path / ".wf",
        host=HOST,
        sandbox=sandbox,
    )


@pytest.fixture(autouse=True)
def _clean_probe_cache() -> object:
    """No test may inherit another's cached capability (the slot is module-level)."""
    reset_probe_cache()
    yield None
    reset_probe_cache()


# --- plan_for: the three checkout shapes -----------------------------------


def test_no_git_checkout_binds_grants_and_channels_only(tmp_path: Path) -> None:
    """A plain checkout binds only its activation-private toolchain cache."""
    rig = _plain_rig(tmp_path)
    plan = _plan(rig)
    assert plan.git_rw == ()
    assert plan.ro_pins == ()
    assert plan.grants == (rig.checkout / GRANT_DIR,)
    assert plan.channels == (rig.channels,)
    assert plan.toolchain_cache == (rig.channels.parent / "toolchain" / "uv-cache",)
    assert plan.ro_roots == (rig.repo_root, rig.wrapper_root, rig.checkout)


def test_in_repo_checkout_binds_the_whole_git_dir(tmp_path: Path) -> None:
    """Shape 2: `.git` is a directory, rw as a WHOLE — `index.lock` lands in it."""
    rig = _in_repo_rig(tmp_path)
    plan = _plan(rig)
    git_dir = rig.checkout / ".git"
    assert plan.git_rw == (git_dir,)
    assert git_dir / "config" in plan.ro_pins
    assert git_dir / "config.worktree" in plan.ro_pins
    assert git_dir / "hooks" in plan.ro_pins
    assert git_dir / "info" in plan.ro_pins


def test_worktree_checkout_binds_the_common_dir_and_the_worktree_gitdir(
    tmp_path: Path,
) -> None:
    """Shape 3: `.git` is a file; the object store comes from `<G>/commondir`."""
    rig = _worktree_rig(tmp_path)
    plan = _plan(rig)
    common = rig.repo_root / ".git"
    gitdir = _gitdir(rig)
    assert plan.git_rw == (
        common / "objects",
        common / "refs" / "heads" / BRANCH_DIR,
        common / "logs" / "refs" / "heads" / BRANCH_DIR,
        gitdir,
    )
    assert plan.ro_pins == (
        common / WF_FENCE_DIR,
        gitdir / "commondir",
        gitdir / "gitdir",
        gitdir / "config.worktree",
        gitdir / "info",
    )


def test_git_dir_detection_distinguishes_worktree_from_in_repo(
    tmp_path: Path,
) -> None:
    """A `.git` FILE must never be bound as if it were the git directory."""
    worktree = _plan(_worktree_rig(tmp_path / "wt"))
    in_repo = _plan(_in_repo_rig(tmp_path / "ir"))
    assert not any(bind.name == ".git" for bind in worktree.git_rw)
    assert [bind.name for bind in in_repo.git_rw] == [".git"]


# --- pins: pre-creation, and existence gating ------------------------------


def test_worktree_precreates_only_the_fixed_set(tmp_path: Path) -> None:
    """`packed-refs`, `config.worktree` and `info/` — the bind sources bwrap needs."""
    rig = _worktree_rig(tmp_path)
    gitdir = _gitdir(rig)
    assert not (rig.repo_root / ".git" / "packed-refs").exists()
    assert not (gitdir / "config.worktree").exists()
    _plan(rig)
    assert not (rig.repo_root / ".git" / "packed-refs").exists()
    assert (gitdir / "config.worktree").is_file()
    assert (gitdir / "info").is_dir()
    assert not (rig.repo_root / ".git" / "refs" / "wf").exists()


def test_worktree_precreates_the_reflog_dir(tmp_path: Path) -> None:
    """The BRANCH's reflog directory is pre-created, not existence-gated: a repo
    whose first ref update has not happened has no `logs/`, and the crew's own
    commit then dies trying to CREATE it under a read-only `.git` (plan §2)."""
    rig = _worktree_rig(tmp_path)
    common = rig.repo_root / ".git"
    shutil.rmtree(common / "logs")
    assert not (common / "logs").exists()
    branch_logs = common / "logs" / "refs" / "heads" / BRANCH_DIR
    assert branch_logs in _plan(rig).git_rw
    assert branch_logs.is_dir()


def test_worktree_precreates_and_binds_the_branch_ref_dir(
    tmp_path: Path,
) -> None:
    """`git pack-refs` prunes `refs/heads/wf` and the next commit must recreate
    the loose ref there, so the directory is made; it is not bound because
    `<common>/refs` above already covers it."""
    rig = _worktree_rig(tmp_path)
    common = rig.repo_root / ".git"
    branch_refs = common / "refs" / "heads" / BRANCH_DIR
    shutil.rmtree(branch_refs)
    assert not branch_refs.exists()
    plan = _plan(rig)
    assert branch_refs.is_dir()
    assert branch_refs in plan.git_rw


def test_the_plan_binds_no_reflog_but_this_branch_s_own(tmp_path: Path) -> None:
    """The reflog grant may not reach another branch's or the wrapper's history.

    `<common>/logs` holds `logs/refs/heads/main` — the parent checkout's own
    history — and `logs/refs/wf/...`, the reflog of the §6 evidence refs, which
    unlike `refs/wf` has no read-only pin standing behind it. Binding the
    directory whole made both writable on the outer layer; this asserts the
    three paths one at a time rather than restating the tuple above.
    """
    rig = _worktree_rig(tmp_path)
    common = rig.repo_root / ".git"
    logs = common / "logs"
    (logs / "refs" / "wf").mkdir(parents=True, exist_ok=True)
    (logs / "refs" / "wf" / "evidence").write_text("entry\n", encoding="utf-8")
    git_rw = _plan(rig).git_rw

    assert logs not in git_rw
    assert logs / "refs" not in git_rw
    assert logs / "refs" / "heads" not in git_rw
    assert logs / "refs" / "wf" not in git_rw
    assert logs / "refs" / "heads" / BRANCH_DIR in git_rw


def test_a_detached_worktree_gets_no_shared_ref_or_reflog_grant(
    tmp_path: Path,
) -> None:
    """A detached head moves `<G>/HEAD` and `<G>/logs/HEAD` and nothing shared.

    §7.3's grading checkout is branchless on purpose, and a checkout with no
    branch has no branch reflog to append to — so it is granted none. Fail-closed
    is the point: the alternative is deriving a directory from a `HEAD` whose
    contents name no branch.
    """
    rig = _worktree_rig(tmp_path)
    common = rig.repo_root / ".git"
    _git(rig.checkout, "checkout", "--quiet", "--detach")

    git_rw = _plan(rig).git_rw

    assert not any(path.is_relative_to(common / "logs") for path in git_rw)
    assert common / "objects" in git_rw
    assert _gitdir(rig) in git_rw


def test_a_head_naming_a_path_outside_refs_heads_grants_nothing(
    tmp_path: Path,
) -> None:
    """`<G>/HEAD` is inside the writable `<G>`, so it is crew-controlled text.

    A `HEAD` that walks out of `refs/heads` is the escape this closes: without
    the check it would name `<common>/hooks` as a branch directory and hand the
    next dispatch write access to the programs the wrapper's own git runs.
    """
    rig = _worktree_rig(tmp_path)
    common = rig.repo_root / ".git"
    (common / "hooks").mkdir(exist_ok=True)
    (_gitdir(rig) / "HEAD").write_text(
        "ref: refs/heads/../../hooks/x\n", encoding="utf-8"
    )

    git_rw = _plan(rig).git_rw

    assert common / "hooks" not in git_rw
    assert not any(path.is_relative_to(common / "logs") for path in git_rw)


def test_a_head_naming_refs_heads_itself_grants_nothing(tmp_path: Path) -> None:
    """`ref: refs/heads` has no branch NAME, so its parent is `refs` — the whole
    ref namespace, evidence refs included. A ref must be strictly deeper than
    `refs/heads` before a directory is derived from it."""
    rig = _worktree_rig(tmp_path)
    common = rig.repo_root / ".git"
    (_gitdir(rig) / "HEAD").write_text("ref: refs/heads\n", encoding="utf-8")

    git_rw = _plan(rig).git_rw

    assert common / "logs" / "refs" not in git_rw
    assert not any(path.is_relative_to(common / "logs") for path in git_rw)


def test_a_symlinked_branch_directory_grants_nothing(tmp_path: Path) -> None:
    """A crew can write in `<common>/refs/heads`, so the directory the NEXT
    dispatch derives from `HEAD` is attacker-reachable. Replacing it with a link
    to `hooks/` would have the vendor layer grant the programs the wrapper's own
    git executes; the mount bound binds by real path and would refuse, so the
    two layers must not be allowed to disagree about what the name means."""
    rig = _worktree_rig(tmp_path)
    common = rig.repo_root / ".git"
    (common / "hooks").mkdir(exist_ok=True)
    branch_refs = common / "refs" / "heads" / BRANCH_DIR
    shutil.rmtree(branch_refs)
    branch_refs.symlink_to(common / "hooks")

    with pytest.raises(SandboxPathRefused, match="symlink"):
        _plan(rig)


def test_both_checkout_shapes_pin_the_ledger_fence_directory(
    tmp_path: Path,
) -> None:
    """`<common>/wf` is read-only in every shape that has a git directory.

    The in-repo shape is the one that NEEDS it — `.git` is bound read-write as
    a whole, so without the pin a crew could unlink the locked inode and
    leave every ledger writer holding a lock on a file nobody else can see
    (run-ledger §3.4). The worktree shape pins the same directory, so the two
    shapes cannot drift.
    """
    in_repo = _in_repo_rig(tmp_path / "ir")
    worktree = _worktree_rig(tmp_path / "wt")

    for rig, common in (
        (in_repo, in_repo.repo_root / ".git"),
        (worktree, worktree.repo_root / ".git"),
    ):
        fence = common / WF_FENCE_DIR
        plan = _plan(rig)
        assert fence.is_dir(), fence
        assert fence in plan.ro_pins
        assert not any(fence.is_relative_to(bind) for bind in plan.grants)


def test_evidence_refs_remain_outside_the_write_grant(tmp_path: Path) -> None:
    """No evidence ref yet ⇒ no bind source ⇒ no pin; one ref ⇒ the pin appears."""
    rig = _worktree_rig(tmp_path)
    common = rig.repo_root / ".git"
    assert common / "refs" / "wf" not in _plan(rig).ro_pins
    (common / "refs" / "wf").mkdir(parents=True)
    (common / "refs" / "wf" / "evidence").write_text("0" * 40 + "\n", encoding="utf-8")
    assert not any(
        (common / "refs" / "wf").is_relative_to(p) for p in _plan(rig).git_rw
    )


def test_in_repo_pins_only_submodule_configs_that_exist(tmp_path: Path) -> None:
    """`modules/*/config` is existence-gated: a fresh worktree has none."""
    rig = _in_repo_rig(tmp_path)
    git_dir = rig.checkout / ".git"
    (git_dir / "modules" / "empty").mkdir(parents=True)
    (git_dir / "modules" / "vendored").mkdir(parents=True)
    (git_dir / "modules" / "vendored" / "config").write_text("", encoding="utf-8")
    pins = _plan(rig).ro_pins
    assert git_dir / "modules" / "vendored" / "config" in pins
    assert git_dir / "modules" / "empty" / "config" not in pins


# --- grants ----------------------------------------------------------------


def test_grant_directory_is_created_when_absent(tmp_path: Path) -> None:
    """A grant names a MOUNT source; bwrap refuses to bind one that is not there."""
    rig = _plain_rig(tmp_path)
    assert not (rig.checkout / GRANT_DIR).exists()
    assert _plan(rig).grants == (rig.checkout / GRANT_DIR,)
    assert (rig.checkout / GRANT_DIR).is_dir()


@pytest.mark.parametrize(
    ("grant", "expected"),
    [("tests/acceptance/**", "tests/acceptance"), ("src/**", "src")],
)
def test_grant_directory_is_the_same_mapping_with_no_filesystem_work(
    grant: str, expected: str
) -> None:
    """Phase 2's seam: the §6 profiles express THIS grant set in their own layer.

    Pure on purpose — a profile builds argv and must never create the directory
    `_grant_path` pre-creates as a mount source.
    """
    assert grant_directory(grant) == PurePosixPath(expected)


@pytest.mark.parametrize("grant", [".git/**", "./**", "**", "tests", "/abs/**"])
def test_grant_directory_refuses_every_shape_the_mount_bound_refuses(
    grant: str,
) -> None:
    """One shape check, so a profile cannot widen a grant the bound would reject."""
    with pytest.raises(SandboxPathRefused):
        grant_directory(grant)


def test_a_bare_grant_directory_is_allowed_by_the_shared_grant_mapping() -> None:
    """`src` and `src/` must not be false outside `src/**` for a dirty submodule."""
    grant = "src/**"

    assert grant_directory(grant) == PurePosixPath("src")
    assert path_allowed("src", (grant,)) is True
    assert path_allowed("src/", (grant,)) is True


def test_grant_resolving_outside_the_checkout_is_refused(tmp_path: Path) -> None:
    """A symlinked grant is the escape `realpath` containment exists to catch."""
    rig = _plain_rig(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (rig.checkout / "escape").symlink_to(outside)
    with pytest.raises(SandboxPathRefused):
        _plan(rig, allowed_paths=("escape/**",))


def test_a_grant_with_a_symlinked_directory_segment_is_refused(tmp_path: Path) -> None:
    """`link/child/**` must not mount `real/child` and misclassify `link/x`."""
    rig = _plain_rig(tmp_path)
    real = rig.checkout / "real"
    real.mkdir()
    (rig.checkout / "link").symlink_to(real, target_is_directory=True)

    with pytest.raises(SandboxUnavailable, match="link"):
        _plan(rig, allowed_paths=("link/child/**",))


def test_writes_false_gets_no_grants_and_no_git_rw(tmp_path: Path) -> None:
    """§2 W2: three ro roots plus `channels/`, and nothing else is writable."""
    plan = _plan(_worktree_rig(tmp_path), writes=False)
    assert (plan.grants, plan.git_rw, plan.ro_pins) == ((), (), ())
    assert len(plan.channels) == 1


def test_missing_ro_root_is_refused(tmp_path: Path) -> None:
    """A root that does not exist would make bwrap fail with a bare `rc=1` (§8)."""
    rig = _plain_rig(tmp_path)
    with pytest.raises(SandboxPathRefused):
        plan_for(
            _task(rig),
            repo_root=tmp_path / "absent",
            wrapper_root=rig.wrapper_root,
            channels_dir=rig.channels,
        )


# --- wrap: bind order IS mount order ---------------------------------------


def test_wrap_emits_pins_after_every_rw_bind(tmp_path: Path) -> None:
    """The §2 blocker: a pin placed before a later rw bind of its parent re-opens."""
    rig = _worktree_rig(tmp_path)
    plan = _plan(rig)
    argv = wrap(("crew", "--go"), plan)
    assert argv[:5] == (
        BWRAP_BINARY,
        ARG_DIE_WITH_PARENT,
        ARG_DEV_BIND,
        FS_ROOT,
        FS_ROOT,
    )
    assert argv[-3:] == (ARG_END, "crew", "--go")
    assert argv.count(ARG_END) == 1
    last_rw = max(index for index, word in enumerate(argv) if word == ARG_BIND)
    first_pin = min(argv.index(str(pin)) for pin in plan.ro_pins if str(pin) in argv)
    assert last_rw < first_pin


def test_wrap_emits_the_groups_in_plan_order(tmp_path: Path) -> None:
    """`channels` → `uv-cache` → pins, so a later rw cache bind cannot reopen pins."""
    rig = _worktree_rig(tmp_path)
    plan = _plan(rig)
    argv = wrap(("crew",), plan)
    ordered = [
        argv.index(str(path))
        for group in (
            plan.ro_roots,
            plan.git_rw,
            plan.grants,
            plan.channels,
            plan.toolchain_cache,
            plan.ro_pins,
        )
        for path in group
    ]
    assert ordered == sorted(ordered)


def test_wrap_is_the_identity_under_sandbox_off(tmp_path: Path) -> None:
    """`off` is a real off switch, not a differently-shaped box."""
    plan = _plan(_plain_rig(tmp_path))
    assert wrap(("crew", "--go"), plan, mode=SandboxMode.OFF) == ("crew", "--go")


# --- probe -----------------------------------------------------------------


def test_probe_is_measured_once_per_process(tmp_path: Path) -> None:
    """One `bwrap` self-test per wrapper process, not one per dispatch."""
    config = _config(tmp_path)
    first = probe(config)
    assert probe(config) is first
    reset_probe_cache()
    assert probe(config) is not first


def test_probe_reports_off_without_touching_the_cache(tmp_path: Path) -> None:
    """`sandbox = off` must not consume the slot a later `bwrap` config reads."""
    off = probe(_config(tmp_path, SandboxMode.OFF))
    assert (off.available, off.reason) == (True, REASON_OFF)
    assert probe(_config(tmp_path)).reason != REASON_OFF


# --- the real bound --------------------------------------------------------


def _run(
    argv: tuple[str, ...], script: str, cwd: Path
) -> subprocess.CompletedProcess[str]:
    """Run one shell script inside the wrapped argv, capturing what it said."""
    return subprocess.run(
        (*argv, SHELL, "-c", script),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT_S,
        env={"PATH": "/usr/bin:/bin", "HOME": str(cwd), **GIT_ISOLATION},
    )


@pytest.mark.proc
def test_real_bwrap_bound_holds_for_a_worktree_checkout(tmp_path: Path) -> None:
    """The whole point, exercised: grant writable, everything else refused."""
    capability = probe(_config(tmp_path))
    if not capability.available:
        pytest.skip(capability.reason)
    rig = _worktree_rig(tmp_path)
    plan = _plan(rig)
    box = wrap((), plan)
    assert box[-1] == ARG_END
    grant = rig.checkout / GRANT_DIR

    inside = _run(box, f"echo crew > {grant}/note.txt", rig.checkout)
    assert inside.returncode == 0, inside.stderr
    assert (grant / "note.txt").is_file()

    outside = _run(box, f"echo crew > {rig.checkout}/escape.txt", rig.checkout)
    assert outside.returncode != 0
    assert "Read-only file system" in outside.stderr

    committed = _run(box, "git add -A && git commit --quiet -m crew", rig.checkout)
    assert committed.returncode == 0, committed.stderr
    assert _git(rig.checkout, "log", "-1", "--pretty=%s") == "crew"

    hook = _run(box, f"echo evil > {rig.repo_root}/.git/hooks/pre-commit", rig.checkout)
    assert hook.returncode != 0
    assert any(text in hook.stderr for text in REFUSED_TEXT), hook.stderr

    pinned = _run(box, f"echo evil > {_gitdir(rig)}/config.worktree", rig.checkout)
    assert pinned.returncode != 0
    assert any(text in pinned.stderr for text in REFUSED_TEXT), pinned.stderr


@pytest.mark.proc
def test_real_bwrap_refuses_git_config_and_the_evidence_refs(tmp_path: Path) -> None:
    """O2's three program-executing surfaces, and the wrapper's own refs.

    `refs/wf` is asserted here rather than in the plan-shape family because it
    is only PINNED once an evidence ref exists (its bind source has to be on
    disk); the unit family owns the "not pinned yet" half.
    """
    capability = probe(_config(tmp_path))
    if not capability.available:
        pytest.skip(capability.reason)
    rig = _worktree_rig(tmp_path)
    evidence = rig.repo_root / ".git" / "refs" / "wf" / "evidence"
    evidence.parent.mkdir(parents=True)
    evidence.write_text(
        _git(rig.repo_root, "rev-parse", "HEAD") + "\n", encoding="utf-8"
    )
    plan = _plan(rig)
    assert not any(evidence.is_relative_to(p) for p in plan.git_rw)
    box = wrap((), plan)

    configured = _run(box, "git config user.name intruder", rig.checkout)
    assert configured.returncode != 0
    assert any(text in configured.stderr for text in REFUSED_TEXT), configured.stderr

    hook = _run(box, f"echo evil > {rig.repo_root}/.git/hooks/pre-push", rig.checkout)
    assert hook.returncode != 0
    assert any(text in hook.stderr for text in REFUSED_TEXT), hook.stderr

    forged = _run(box, f"echo {'0' * 40} > {evidence}", rig.checkout)
    assert forged.returncode != 0
    assert any(text in forged.stderr for text in REFUSED_TEXT), forged.stderr
    assert evidence.read_text(encoding="utf-8").strip() != "0" * 40


@pytest.mark.proc
def test_real_bwrap_leaves_the_channels_writable(tmp_path: Path) -> None:
    """The §6 channels are the one writable thing a `writes = false` node has."""
    capability = probe(_config(tmp_path))
    if not capability.available:
        pytest.skip(capability.reason)
    rig = _worktree_rig(tmp_path)
    box = wrap((), _plan(rig, writes=False, allowed_paths=()))

    reported = _run(box, f"echo done > {rig.channels}/outcome.json", rig.checkout)
    assert reported.returncode == 0, reported.stderr
    assert (rig.channels / "outcome.json").is_file()

    blocked = _run(box, f"echo x > {rig.checkout}/seed.txt", rig.checkout)
    assert blocked.returncode != 0
    assert any(text in blocked.stderr for text in REFUSED_TEXT), blocked.stderr

    staged = _run(box, "git add -A && git commit -m nope", rig.checkout)
    assert staged.returncode != 0, staged.stdout


@pytest.mark.proc
@pytest.mark.nested_sandbox
def test_real_bwrap_reads_reference_exports_but_refuses_export_and_engine_writes(
    tmp_path: Path,
) -> None:
    """Reference evidence is visible through the wrapper root, never writable."""
    capability = probe(_config(tmp_path))
    if not capability.available:
        pytest.skip(capability.reason)
    rig = _worktree_rig(tmp_path)
    activation = rig.channels.parent
    evidence = activation / "evidence" / "published"
    evidence.mkdir(parents=True)
    index = evidence / "index.json"
    index.write_text('{"diff_path":"diff-000.patch"}\n', encoding="utf-8")
    (evidence / "diff-000.patch").write_text("pinned diff\n", encoding="utf-8")
    engine_record = activation / "launch-receipt.json"
    engine_record.write_text("engine\n", encoding="utf-8")
    box = wrap((), _plan(rig, writes=False, allowed_paths=()))

    observed = _run(
        box,
        f"cat {index} > {rig.channels}/observed.json",
        rig.checkout,
    )
    assert observed.returncode == 0, observed.stderr
    assert (rig.channels / "observed.json").read_text(
        encoding="utf-8"
    ) == index.read_text(encoding="utf-8")
    for target in (index, rig.checkout / "seed.txt", engine_record):
        blocked = _run(box, f"echo tamper > {target}", rig.checkout)
        assert blocked.returncode != 0
        assert any(text in blocked.stderr for text in REFUSED_TEXT), blocked.stderr


UV_BINARY: Final[str] = "uv"
UV_TIMEOUT_S: Final[float] = 600.0
SCRATCH: Final[str] = "scratch"
_SKIP_NO_UV: Final[str] = "uv is not on PATH"


def _repo_rig(tmp_path: Path) -> Rig:
    """A real worktree of a real Python project, entirely under `tmp_path`.

    A LOCAL SHARED clone of this repo first, then a worktree of the clone: the
    §2 toolchain env can only be proved against a checkout that really has a
    `pyproject.toml`, a lock and tests, and the rig may still never touch the
    developer's own `.git` (`plan_for` pre-creates bind sources in it).
    """
    origin = Path(__file__).resolve().parent.parent
    repo_root = tmp_path / "origin"
    checkout = tmp_path / "checkout"
    # A SPACE in the wrapper root on purpose: `PYTEST_ADDOPTS` is shlex-split
    # by pytest, so an unquoted `-o cache_dir=` would arrive as two arguments
    # and this run would die on an unrecognised one.
    wrapper_root = tmp_path / "wf root"
    scratch = wrapper_root / ROOT_ID / ACTIVATION / "channels" / SCRATCH
    scratch.mkdir(parents=True, exist_ok=True)
    _git(
        origin,
        "clone",
        "--quiet",
        "--local",
        "--shared",
        "--no-checkout",
        str(origin),
        str(repo_root),
    )
    _git(repo_root, "worktree", "add", "--quiet", "--detach", str(checkout), "HEAD")
    return Rig(repo_root, wrapper_root, checkout, scratch.parent)


def _uv_env(scratch: Path | None, home: Path) -> dict[str, str]:
    """The child env for `uv run`, with and without the §2 redirection."""
    base = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        **GIT_ISOLATION,
    }
    if scratch is None:
        return base
    return {**base, **toolchain_env(str(scratch))}


@pytest.mark.proc
@pytest.mark.nested_sandbox
def test_uv_run_uses_the_cache_with_read_only_home_under_the_bound(
    tmp_path: Path,
) -> None:
    """`HOME=<wrapper_root>/read-only-home` runs `uv`, not `~/.cache/uv` EROFS.

    The explicit interpreter avoids a network-dependent managed-Python download;
    `UV_CACHE_DIR=<activation-dir>/toolchain/uv-cache` and its read-write bind are the
    behavior under test.

    `nested_sandbox` remains because a vendor sandbox cannot start the nested
    `bwrap`; the read-only-HOME cache case is covered by this probe itself.
    """
    capability = probe(_config(tmp_path))
    if not capability.available:
        pytest.skip(capability.reason)
    if shutil.which(UV_BINARY) is None:
        pytest.skip(_SKIP_NO_UV)
    rig = _repo_rig(tmp_path)
    plan = plan_for(
        _task(rig, allowed_paths=()),
        repo_root=rig.repo_root,
        wrapper_root=rig.wrapper_root,
        channels_dir=rig.channels,
    )
    box = wrap(
        (
            UV_BINARY,
            "run",
            "--no-project",
            "--python",
            sys.executable,
            "python",
            "-c",
            "import sys; assert sys.version_info >= (3, 13)",
        ),
        plan,
    )
    home = rig.wrapper_root / "read-only-home"
    home.mkdir()

    bounded_env = _uv_env(None, home)
    bounded_env[ENV_UV_CACHE_DIR] = str(plan.toolchain_cache[0])
    bounded_env[ENV_UV_PYTHON_INSTALL_DIR] = str(plan.toolchain_cache[0] / "python")
    bounded = _uv_run(box, rig.checkout, bounded_env)
    assert bounded.returncode == 0, bounded.stdout + bounded.stderr
    assert plan.toolchain_cache[0].is_dir()


def _uv_run(
    argv: tuple[str, ...], cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Run the wrapped `uv` invocation, capturing both streams."""
    return subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        timeout=UV_TIMEOUT_S,
        env=env,
    )


FSMONITOR_CONFIG: Final[str] = '[core]\n\tfsmonitor = "touch {marker}; false"\n'
"""A `config` whose `core.fsmonitor` is a SHELL COMMAND git runs on every
`git status`. `commondir` is what decides which `config` that is."""
PWNED: Final[str] = "PWNED"
COMMONDIR_ESCAPE: Final[str] = "escape"


@pytest.mark.proc
def test_the_worktree_gitdir_pointers_cannot_be_repointed(tmp_path: Path) -> None:
    """The rw bind of `<G>` must not carry `commondir`/`gitdir` with it.

    Repointing `commondir` at a crew-controlled directory holding a `config`
    with `core.fsmonitor` makes the WRAPPER's own next `git status` — run
    outside the box, as the wrapper — execute that command. `<G>` has to be
    read-write for `index.lock`, so the two pointer files are pinned back.
    """
    capability = probe(_config(tmp_path))
    if not capability.available:
        pytest.skip(capability.reason)
    rig = _worktree_rig(tmp_path)
    gitdir = _gitdir(rig)
    plan = _plan(rig)
    assert gitdir / COMMONDIR_FILE in plan.ro_pins
    assert gitdir / GITDIR_FILE in plan.ro_pins
    box = wrap((), plan)

    # The escape, exactly as a crew would stage it: a writable directory it
    # controls, a hostile `config` in it, and `commondir` repointed at it.
    escape = rig.channels / COMMONDIR_ESCAPE
    marker = rig.channels / PWNED
    escape.mkdir(parents=True, exist_ok=True)
    (escape / CONFIG_FILE).write_text(
        FSMONITOR_CONFIG.format(marker=marker), encoding="utf-8"
    )
    repointed = _run(box, f"echo {escape} > {gitdir}/{COMMONDIR_FILE}", rig.checkout)

    assert repointed.returncode != 0
    assert any(text in repointed.stderr for text in REFUSED_TEXT), repointed.stderr
    # The wrapper's own git, outside the box, on the tree the crew just left.
    _git(rig.checkout, "status", "--porcelain")
    assert not marker.exists()


@pytest.mark.proc
def test_a_crew_cannot_replace_the_ledger_fence_inode_in_either_shape(
    tmp_path: Path,
) -> None:
    """The fence file survives `rm`, `mv` and a truncating write from inside.

    Replacing the INODE is the escape that matters: every other ledger writer
    holds its `flock` on the file this one would have unlinked, so a crew
    that could swap it would silently un-fence import, migration and restore
    (run-ledger §3.4). Both checkout shapes, because `.git` is writable as a
    whole in one of them.
    """
    capability = probe(_config(tmp_path))
    if not capability.available:
        pytest.skip(capability.reason)

    for rig in (_in_repo_rig(tmp_path / "ir"), _worktree_rig(tmp_path / "wt")):
        # Plan first: the fence directory is a bind source, pre-created by the
        # planner exactly as the foreman pre-creates it before any dispatch.
        box = wrap((), _plan(rig))
        lock = rig.repo_root / ".git" / WF_FENCE_DIR / "ledger.lock"
        lock.write_text("fence\n", encoding="utf-8")
        inode = lock.stat().st_ino

        for script in (
            f"rm -f {lock}",
            f"mv {lock} {lock}.stolen",
            f"echo evil > {lock}",
        ):
            attempt = _run(box, script, rig.checkout)
            assert attempt.returncode != 0, script
            assert any(text in attempt.stderr for text in REFUSED_TEXT), attempt.stderr
        assert lock.stat().st_ino == inode
        assert lock.read_text(encoding="utf-8") == "fence\n"


@pytest.mark.proc
def test_the_in_repo_shape_blocks_a_sibling_worktree_added_after_planning(
    tmp_path: Path,
) -> None:
    """A post-plan sibling `commondir` write must fail, not receive `.git` rw."""
    capability = probe(_config(tmp_path))
    if not capability.available:
        pytest.skip(capability.reason)
    rig = _in_repo_rig(tmp_path)
    plan = _plan(rig)
    sibling = tmp_path / "sibling"
    _git(rig.repo_root, "worktree", "add", "--quiet", str(sibling), "-b", "wf-other")
    pointer = rig.checkout / ".git" / "worktrees" / sibling.name / COMMONDIR_FILE
    assert rig.checkout / ".git" / "worktrees" in plan.ro_pins

    repointed = _run(wrap((), plan), f"echo /tmp > {pointer}", rig.checkout)
    assert repointed.returncode != 0
    assert any(text in repointed.stderr for text in REFUSED_TEXT), repointed.stderr


@pytest.mark.parametrize(
    "grant",
    (
        "./**",
        "tests",
        ".git/**",
        "a/.git/**",
        "src//**",
        "/src/**",
        "**",
    ),
)
def test_a_grant_that_is_not_a_plain_directory_glob_is_refused(
    tmp_path: Path, grant: str
) -> None:
    """Defence in depth behind the §4 schema pattern, not a duplicate of it.

    `./**` maps to the WHOLE checkout, a bare `tests` is taken literally as a
    directory named `tests`, and any `.`-leading segment re-opens a pin — and
    `.git/**` used to raise a bare `FileExistsError`, an `OSError` that
    `inspect.py`'s generic catch spends an infra retry on instead of halting.
    """
    rig = _plain_rig(tmp_path)
    with pytest.raises(SandboxPathRefused):
        _plan(rig, allowed_paths=(grant,))
