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
from pathlib import Path
from typing import Final, NamedTuple

import pytest

from workflow_interpreter.profiles._base import toolchain_env
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import SandboxPathRefused
from workflow_interpreter.supervisor.profile import TaskSpec, channels_for
from workflow_interpreter.supervisor.sandbox import (
    ARG_BIND,
    ARG_DEV_BIND,
    ARG_DIE_WITH_PARENT,
    ARG_END,
    BWRAP_BINARY,
    COMMONDIR_FILE,
    CONFIG_FILE,
    FS_ROOT,
    GITDIR_FILE,
    REASON_OFF,
    SandboxMode,
    SandboxPlan,
    plan_for,
    probe,
    reset_probe_cache,
    wrap,
)

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
    """A git repo with one commit and an identity a runner can commit under."""
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


def _worktree_rig(tmp_path: Path) -> Rig:
    """A real `git worktree`: `<C>/.git` is a FILE naming `<G>`."""
    rig = _rig(tmp_path, tmp_path / ".wf" / ROOT_ID / "worktree")
    _init(rig.repo_root)
    _git(rig.repo_root, "worktree", "add", "--quiet", str(rig.checkout), "-b", "wf-run")
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
) -> SupervisorConfig:
    """A supervisor config carrying only the field `probe` reads."""
    return SupervisorConfig(
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
    """Shape 1: nothing git-shaped to open, so nothing git-shaped to re-close."""
    rig = _plain_rig(tmp_path)
    plan = _plan(rig)
    assert plan.git_rw == ()
    assert plan.ro_pins == ()
    assert plan.grants == (rig.checkout / GRANT_DIR,)
    assert plan.channels == (rig.channels,)
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
        common / "refs",
        common / "logs",
        common / "packed-refs",
        gitdir,
    )
    assert plan.ro_pins == (
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
    assert (rig.repo_root / ".git" / "packed-refs").is_file()
    assert (gitdir / "config.worktree").is_file()
    assert (gitdir / "info").is_dir()
    assert not (rig.repo_root / ".git" / "refs" / "wf").exists()


def test_worktree_precreates_the_reflog_dir(tmp_path: Path) -> None:
    """`logs/` is pre-created, not existence-gated: a repo whose first ref update
    has not happened has no `logs/`, and the runner's own commit then dies
    trying to CREATE it under a read-only `.git` (plan §2)."""
    rig = _worktree_rig(tmp_path)
    logs = rig.repo_root / ".git" / "logs"
    shutil.rmtree(logs)
    assert not logs.exists()
    assert logs in _plan(rig).git_rw
    assert logs.is_dir()


def test_refs_wf_is_pinned_only_once_the_evidence_ref_exists(tmp_path: Path) -> None:
    """No evidence ref yet ⇒ no bind source ⇒ no pin; one ref ⇒ the pin appears."""
    rig = _worktree_rig(tmp_path)
    common = rig.repo_root / ".git"
    assert common / "refs" / "wf" not in _plan(rig).ro_pins
    (common / "refs" / "wf").mkdir(parents=True)
    (common / "refs" / "wf" / "evidence").write_text("0" * 40 + "\n", encoding="utf-8")
    assert _plan(rig).ro_pins[0] == common / "refs" / "wf"


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


def test_grant_resolving_outside_the_checkout_is_refused(tmp_path: Path) -> None:
    """A symlinked grant is the escape `realpath` containment exists to catch."""
    rig = _plain_rig(tmp_path)
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    (rig.checkout / "escape").symlink_to(outside)
    with pytest.raises(SandboxPathRefused):
        _plan(rig, allowed_paths=("escape/**",))


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
    argv = wrap(("runner", "--go"), plan)
    assert argv[:5] == (
        BWRAP_BINARY,
        ARG_DIE_WITH_PARENT,
        ARG_DEV_BIND,
        FS_ROOT,
        FS_ROOT,
    )
    assert argv[-3:] == (ARG_END, "runner", "--go")
    assert argv.count(ARG_END) == 1
    last_rw = max(index for index, word in enumerate(argv) if word == ARG_BIND)
    first_pin = min(argv.index(str(pin)) for pin in plan.ro_pins if str(pin) in argv)
    assert last_rw < first_pin


def test_wrap_emits_the_groups_in_plan_order(tmp_path: Path) -> None:
    """ro roots → git rw → grants → channels → pins, as `SandboxPlan` declares."""
    rig = _worktree_rig(tmp_path)
    plan = _plan(rig)
    argv = wrap(("runner",), plan)
    ordered = [
        argv.index(str(path))
        for group in (
            plan.ro_roots,
            plan.git_rw,
            plan.grants,
            plan.channels,
            plan.ro_pins,
        )
        for path in group
    ]
    assert ordered == sorted(ordered)


def test_wrap_is_the_identity_under_sandbox_off(tmp_path: Path) -> None:
    """`off` is a real off switch, not a differently-shaped box."""
    plan = _plan(_plain_rig(tmp_path))
    assert wrap(("runner", "--go"), plan, mode=SandboxMode.OFF) == ("runner", "--go")


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

    inside = _run(box, f"echo runner > {grant}/note.txt", rig.checkout)
    assert inside.returncode == 0, inside.stderr
    assert (grant / "note.txt").is_file()

    outside = _run(box, f"echo runner > {rig.checkout}/escape.txt", rig.checkout)
    assert outside.returncode != 0
    assert "Read-only file system" in outside.stderr

    committed = _run(box, "git add -A && git commit --quiet -m runner", rig.checkout)
    assert committed.returncode == 0, committed.stderr
    assert _git(rig.checkout, "log", "-1", "--pretty=%s") == "runner"

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
    assert rig.repo_root / ".git" / "refs" / "wf" in plan.ro_pins
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


UV_BINARY: Final[str] = "uv"
NODE_TEST_FILE: Final[str] = "tests/test_semantic_rules.py"
"""One small, self-contained module of THIS repo: enough to prove `uv run
pytest` starts and finishes inside the box, cheap enough to run twice."""
UV_TIMEOUT_S: Final[float] = 600.0
SCRATCH: Final[str] = "scratch"
VENV_DIR: Final[str] = "venv"
_SKIP_NO_UV: Final[str] = "uv is not on PATH"
_READ_ONLY: Final[str] = "Read-only file system"


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


def _uv_env(scratch: Path | None) -> dict[str, str]:
    """The child env for `uv run`, with and without the §2 redirection."""
    base = {
        "PATH": os.environ["PATH"],
        "HOME": os.environ["HOME"],
        **GIT_ISOLATION,
    }
    if scratch is None:
        return base
    return {**base, **toolchain_env(str(scratch))}


@pytest.mark.proc
def test_the_nodes_own_uv_gate_runs_under_the_bound(tmp_path: Path) -> None:
    """Plan §2 blocker 2: a read-only checkout breaks `uv run` without the env.

    Both halves, because only the pair shows the env is load-bearing rather than
    decorative: WITHOUT it `uv` dies creating `.venv` in the checkout; WITH it
    the node's own test file passes inside the same box.
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
    box = wrap((UV_BINARY, "run", "pytest", "-q", NODE_TEST_FILE), plan)
    scratch = rig.channels / SCRATCH

    bare = _uv_run(box, rig.checkout, _uv_env(None))
    assert bare.returncode != 0
    assert _READ_ONLY in bare.stderr, bare.stderr

    bounded = _uv_run(box, rig.checkout, _uv_env(scratch))
    assert bounded.returncode == 0, bounded.stdout + bounded.stderr
    assert (scratch / VENV_DIR).is_dir()


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

    Repointing `commondir` at a runner-controlled directory holding a `config`
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

    # The escape, exactly as a runner would stage it: a writable directory it
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
    # The wrapper's own git, outside the box, on the tree the runner just left.
    _git(rig.checkout, "status", "--porcelain")
    assert not marker.exists()


@pytest.mark.proc
def test_the_in_repo_shape_pins_every_sibling_worktree_pointer(tmp_path: Path) -> None:
    """In-repo mode binds `.git` WHOLE, so a node reaches other instances' worktrees.

    `.git/worktrees/<other>/commondir` is the same escape aimed at a sibling
    instance rather than at this one.
    """
    capability = probe(_config(tmp_path))
    if not capability.available:
        pytest.skip(capability.reason)
    rig = _in_repo_rig(tmp_path)
    sibling = tmp_path / "sibling"
    _git(rig.repo_root, "worktree", "add", "--quiet", str(sibling), "-b", "wf-other")
    pointer = rig.checkout / ".git" / "worktrees" / sibling.name / COMMONDIR_FILE
    plan = _plan(rig)
    assert pointer in plan.ro_pins

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
    `supervise.py`'s generic catch spends an infra retry on instead of halting.
    """
    rig = _plain_rig(tmp_path)
    with pytest.raises(SandboxPathRefused):
        _plan(rig, allowed_paths=(grant,))
