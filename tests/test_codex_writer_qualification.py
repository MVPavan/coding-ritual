"""Real Codex sandbox qualification, with no model calls.

Prove edit/check/stage/commit under both sandbox layers, and deny writes to
other workflows, protected Git metadata and out-of-grant source. The outer
sandbox is also tested alone. Explicit old configurations retain red evidence.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

from tests._profiles import (
    git_write_roots_of,
    make_supervisor_config,
    make_task,
    writable_roots_in,
)
from tests._supervisor import GIT_TIMEOUT_S, FrozenClock, head_of
from workflow_interpreter.profiles._base import ENV_TMPDIR
from workflow_interpreter.profiles.codex import (
    CONFIG,
    KEY_SANDBOX_MODE,
    SANDBOX,
    WORKSPACE_WRITE,
    CodexProfile,
)
from workflow_interpreter.profiles.config import ProfileConfig
from workflow_interpreter.profiles.errors import UnsupportedOptionError
from workflow_interpreter.supervisor.errors import SandboxPathRefused
from workflow_interpreter.supervisor.profile import RunnerCommand, TaskSpec
from workflow_interpreter.supervisor.sandbox import (
    SandboxPlan,
    plan_for,
    worktree_git_write_roots,
    wrap,
)

CODEX: Final[str] = "codex"
BWRAP: Final[str] = "bwrap"
SANDBOX_SUBCOMMAND: Final[str] = "sandbox"
PROBE_TIMEOUT_S: Final[float] = 180.0
GRANTS: Final[tuple[str, ...]] = ("src/**",)
GRANTED_FILE: Final[str] = "src/feature.py"
UNGRANTED_FILE: Final[str] = "scripts/verify.sh"
"""Both exist in `make_repo`'s tree: one inside the node's single grant and one
outside it, so "the writer may write its grant" and "the writer may not write
the rest of its own checkout" are asked about real files."""

EROFS: Final[str] = "Read-only file system"
INDEX_LOCK: Final[str] = "index.lock"
COMMITTED: Final[str] = "COMMITTED"
STAGED: Final[str] = "STAGED"
EDITED: Final[str] = "EDITED"
DENIED: Final[str] = "DENIED"
ALLOWED: Final[str] = "ALLOWED"

_SKIP_NO_CODEX: Final[str] = "the codex binary is not on PATH"
_SKIP_NO_BWRAP: Final[str] = "the bwrap binary is not on PATH"

MOUNT_TARGETS: Final[tuple[str, ...]] = (".agents", ".codex")
"""Directories codex 0.154's sandbox creates in the working root as synthetic
bubblewrap mount targets and then removes.

Under the §2 mount bound a writer's checkout is read-only outside its grants, so
these have to be there ALREADY or codex fails at launch with a bare
`bwrap: Can't mkdir ...`. This repository commits both, which is why the
production path works; a lab checkout has neither, so the rig makes them. It is a
precondition of the environment, recorded here rather than hidden — see the
codex profile's module docstring for why the wrapper does not create them for
somebody else's checkout."""

COMMIT_IDENTITY: Final[tuple[str, ...]] = (
    "-c",
    "user.email=runner@wf.invalid",
    "-c",
    "user.name=wf-runner",
)
"""`git commit` needs an identity and the probe's git has no global config; the
§7.4 committer identity production stamps arrives through `GIT_COMMITTER_*` in
the child environment, which is asserted in `test_profiles_command.py` and is
not what this file is about."""

_WRITE_PROBE: Final[str] = (
    'if (echo probe > "{path}") 2>/dev/null; then echo "{allowed}:{label}"; else echo "{denied}:{label}"; fi'
)


def _write_probe(path: Path | str, label: str) -> str:
    """One `sh` line reporting whether a single path could be written."""
    return _WRITE_PROBE.format(path=path, label=label, allowed=ALLOWED, denied=DENIED)


def _requirements() -> None:
    """Skip rather than assert when the host cannot run an OS sandbox at all.

    An assertion about a bound that silently did not run is worse than no
    assertion (§0.3). The full gate runs on a host that has both.
    """
    if shutil.which(CODEX) is None:
        pytest.skip(_SKIP_NO_CODEX)
    if shutil.which(BWRAP) is None:
        pytest.skip(_SKIP_NO_BWRAP)


def _lab(tmp_path: Path, *, writes: bool = True) -> tuple[TaskSpec, SandboxPlan]:
    """A real §5.4 writer task and the real mount plan a dispatch would use.

    `plan_for` is the production function, called with the production arguments,
    and its mount-source pre-creation is part of what is being qualified: the
    codex grant names directories `plan_for` has already made sure exist.
    """
    task = make_task(tmp_path, writes=writes, allowed_paths=GRANTS if writes else ())
    for name in MOUNT_TARGETS:
        (Path(task.cwd) / name).mkdir(exist_ok=True)
    config = make_supervisor_config(tmp_path)
    _plant_neighbours(tmp_path, task)
    plan = plan_for(
        task,
        repo_root=config.repo_root,
        wrapper_root=config.wrapper_root,
        channels_dir=Path(task.channels.outcome_file).parent,
        binary=str(shutil.which(BWRAP)),
    )
    return task, plan


SIBLING: Final[str] = "sibling-worktree"
WF_REF: Final[str] = "refs/wf/evidence"
WF_REFLOG: Final[str] = "logs/refs/wf/evidence"
MAIN_REFLOG: Final[str] = "logs/refs/heads/main"
"""The two reflogs a writer must not reach, and neither is hypothetical.

`logs/refs/heads/main` is the PARENT checkout's own history, present in every
repository whose default branch has ever been committed to. `logs/refs/wf/...`
is the reflog of the §6 evidence refs — the wrapper's own bookkeeping, and the
one directory in `logs` where, unlike `refs/wf`, no read-only pin was standing
behind the grant. Both were writable while the git write set named `<common>/logs`
whole; `test_the_superseded_wide_grant_is_what_reached_those_reflogs` runs that
configuration and shows it."""


def _plant_neighbours(tmp_path: Path, task: TaskSpec) -> None:
    """Put the things a writer must not reach on disk BEFORE the plan is computed.

    Order is the whole point, and it is easy to get wrong: `plan_for` pins what
    EXISTS when it runs, so a `refs/wf` created afterwards is not pinned and the
    negative below would then be testing the vendor layer alone. A real instance
    has its evidence refs, their reflog and its sibling activations' worktrees
    already, so the lab has to as well.
    """
    common = _common_of(task)
    (common / WF_REF).parent.mkdir(parents=True, exist_ok=True)
    (common / WF_REF).write_text("0" * 40 + "\n", encoding="utf-8")
    (common / WF_REFLOG).parent.mkdir(parents=True, exist_ok=True)
    (common / WF_REFLOG).write_text("0" * 40 + " evidence\n", encoding="utf-8")
    assert (common / MAIN_REFLOG).is_file(), "the lab's parent branch has no reflog"
    sibling = Path(task.cwd).parent / SIBLING
    if sibling.exists():
        return
    subprocess.run(
        [
            "git",
            "worktree",
            "add",
            "--quiet",
            "-b",
            "wf/sibling/candidate",
            str(sibling),
        ],
        cwd=common.parent,
        check=True,
        capture_output=True,
        timeout=GIT_TIMEOUT_S,
    )


def _common_of(task: TaskSpec) -> Path:
    """The shared git directory behind this lab's worktree, walked independently."""
    return Path(git_write_roots_of(Path(task.cwd))[1]).parent


def _permission_config(argv: tuple[str, ...]) -> list[str]:
    """The sandbox configuration one built codex argv carries, as `codex sandbox` words.

    `codex sandbox` runs a command under the REAL sandbox the configuration
    describes, with no model turn and no tokens — but it takes only `-c`
    overrides, not `codex exec`'s `-s`/`-C`/`--add-dir`/`-m`. Two of those are
    re-spelled rather than dropped, and the re-spelling is CHECKED by the caller
    rather than trusted:

    - `-s workspace-write` becomes `-c sandbox_mode="workspace-write"`, which is
      the spelling the §8.1 resume argv already uses and the reason the resume
      path needs no translation at all;
    - `-C <root>` becomes the probe's working directory, exactly as it does in
      production, where `build_command` sets `cwd` to the same directory.

    `--add-dir` needs no translation: it is redundant with `writable_roots` by
    design, and `writable_roots` is a `-c` pair that comes through verbatim.
    """
    words = [CONFIG, f'{KEY_SANDBOX_MODE}="{WORKSPACE_WRITE}"']
    for index, word in enumerate(argv[:-1]):
        if word == CONFIG:
            words += [CONFIG, argv[index + 1]]
    return words


def _run(
    plan: SandboxPlan,
    command: RunnerCommand,
    permission_config: list[str],
    script: str,
    tmp_path: Path,
    *,
    vendor_layer: bool = True,
) -> str:
    """Run one `sh` script inside BOTH bounds: the mount bound, then codex's."""
    inner = (
        CODEX,
        SANDBOX_SUBCOMMAND,
        *permission_config,
        "--",
        "sh",
        "-c",
        script,
    )
    if not vendor_layer:
        inner = ("sh", "-c", script)
    done = subprocess.run(
        wrap(inner, plan),
        cwd=command.cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=PROBE_TIMEOUT_S,
        env=_probe_env(command, tmp_path),
    )
    return f"{done.stdout}{done.stderr}"


def _probe_env(command: RunnerCommand, tmp_path: Path) -> dict[str, str]:
    """The probe child's environment, with the two host values that are bounds.

    `TMPDIR` is one of them and it is not a nicety: `workspace-write` leaves
    `$TMPDIR` writable by DEFAULT — `exclude_tmpdir_env_var` is off and the
    profile deliberately leaves it off — so whatever `$TMPDIR` names is granted.
    In production that is harmless because the wrapper SETS it, to
    `$WF_SCRATCH_DIR` inside `channels/`, which the node already holds. In a test
    it is the opposite of harmless: pytest's `tmp_path` lives under the host's
    `$TMPDIR`, so an inherited one silently granted the whole lab — repository,
    parent `.git` and all — and every negative assertion below passed as
    `ALLOWED` while looking like a bound. Taking the value off the built
    `RunnerCommand` is what keeps the rig describing production rather than
    describing this machine.

    `CODEX_HOME` is the other: `codex sandbox` has no `--ignore-user-config`, and
    the host's own `~/.codex/config.toml` is ADDITIVE to
    `sandbox_workspace_write`, so an operator's ambient `writable_roots` would
    widen the very thing under test. An empty directory stands in for the flag
    production emits, which the caller asserts is on the real argv.
    """
    home = tmp_path / "codex-home"
    home.mkdir(exist_ok=True)
    return {
        **os.environ,
        "CODEX_HOME": str(home),
        ENV_TMPDIR: command.env[ENV_TMPDIR],
    }


# --- the decisive pair: red on the old configuration, green on the new -----


@pytest.mark.proc
@pytest.mark.nested_sandbox
def test_the_pre_fix_configuration_cannot_take_the_index_lock(tmp_path: Path) -> None:
    """RED: the writer configuration as it was cannot stage a single file.

    The old `_sandbox_flags` granted the §6 channels and nothing else, so this
    spells that configuration out literally rather than reaching for a git
    history. Running it proves the defect is in the CONFIGURATION and not in the
    rig: the source edit inside the node's grant succeeds, and the `git add`
    immediately after it dies on a lock file in the parent repository.
    """
    _requirements()
    task, plan = _lab(tmp_path)
    channels_dir = str(Path(task.channels.outcome_file).parent)
    pre_fix = [
        CONFIG,
        f'{KEY_SANDBOX_MODE}="{WORKSPACE_WRITE}"',
        CONFIG,
        f'sandbox_workspace_write.writable_roots=["{channels_dir}"]',
        CONFIG,
        "sandbox_workspace_write.network_access=false",
        CONFIG,
        "sandbox_workspace_write.exclude_slash_tmp=true",
    ]
    # Everything except the permission configuration is production's: the same
    # mount plan, the same working root, the same child `TMPDIR`. Only the
    # `-c` words are the old ones, so a failure here can only be about them.
    command = CodexProfile(ProfileConfig(), FrozenClock(), {}).build_command(task, "")

    observed = _run(
        plan,
        command,
        pre_fix,
        f"echo edited > {GRANTED_FILE} && echo {EDITED}; "
        f"git add {GRANTED_FILE} 2>&1 && echo {STAGED}",
        tmp_path,
    )

    assert EDITED in observed, observed
    assert STAGED not in observed, observed
    assert INDEX_LOCK in observed, observed
    assert EROFS in observed, observed


@pytest.mark.proc
@pytest.mark.nested_sandbox
@pytest.mark.parametrize("invocation", ["launch", "resume"])
def test_the_production_configuration_edits_stages_and_commits(
    tmp_path: Path, invocation: str
) -> None:
    """GREEN: edit -> check -> stage -> commit, on the argv production builds.

    Both invocations, because they are built by different code paths and §8.1
    lets a continuation finish what a launch started: `codex exec` states the
    grant as `-s`, `--add-dir` and `-c`, while `codex exec resume` accepts
    neither `-s` nor `--add-dir` and has to state all of it as `-c`. A
    continuation that described a narrower box would fail exactly here, at the
    commit, after the model had already been paid for.

    The identity half is asserted too, not just the exit status: the candidate's
    parent must be the base the worktree was on and the branch must be the one
    the wrapper put it on. A commit that landed somewhere else is not a
    candidate, however successfully it was made.
    """
    _requirements()
    task, plan = _lab(tmp_path)
    profile = CodexProfile(ProfileConfig(), FrozenClock(), {})
    command = (
        profile.build_command(task, "")
        if invocation == "launch"
        else profile.build_resume_command("0199f0", "carry on", task)
    )
    # The two re-spellings `_permission_config` makes, checked rather than assumed.
    if invocation == "launch":
        assert command.argv[command.argv.index(SANDBOX) + 1] == WORKSPACE_WRITE
    assert "--ignore-user-config" in command.argv
    assert command.cwd == task.cwd
    base = head_of(Path(task.cwd))

    observed = _run(
        plan,
        command,
        _permission_config(command.argv),
        f"echo edited > {GRANTED_FILE} && echo {EDITED}; "
        f"grep -q edited {GRANTED_FILE} && echo CHECKED; "
        f"git add {GRANTED_FILE} && echo {STAGED}; "
        f"git {' '.join(COMMIT_IDENTITY)} commit -q -m candidate && echo {COMMITTED}",
        tmp_path,
    )

    assert EDITED in observed, observed
    assert "CHECKED" in observed, observed
    assert STAGED in observed, observed
    assert COMMITTED in observed, observed
    candidate = head_of(Path(task.cwd))
    assert candidate != base
    assert _git(Path(task.cwd), "rev-parse", f"{candidate}^") == base
    assert _git(Path(task.cwd), "rev-parse", "--abbrev-ref", "HEAD").startswith("wf/")


def _git(cwd: Path, *args: str) -> str:
    """One plain git command in the lab, run OUTSIDE both bounds."""
    done = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
    )
    return done.stdout.strip()


# --- the negative half ----------------------------------------------------


@pytest.mark.proc
@pytest.mark.nested_sandbox
@pytest.mark.parametrize("vendor_layer", [True, False])
def test_the_protected_git_surface_stays_refused_through_the_whole_stack(
    tmp_path: Path,
    vendor_layer: bool,
) -> None:
    """Every path the writer must NOT reach, asked one at a time under both bounds.

    Five families, and they fail for different reasons on purpose:

    - `config`, `hooks/`, `info/`, `packed-refs` and `refs/wf` are outside the
      codex grant AND outside the mount bound's read-write set — refused twice;
    - the REFLOG surface, which is the one this list used to be missing:
      `logs/refs/heads/main` is the parent checkout's own history,
      `logs/refs/wf/evidence` is the §6 evidence refs' reflog and `logs/HEAD` is
      the parent checkout's HEAD reflog. All three sit under `<common>/logs`,
      which both layers once granted whole — the outer plan without even a pin
      to take `refs/wf` back. They are refused now because the grant descends to
      `logs/refs/heads/<namespace>`, the directory holding this candidate's own
      reflog and nothing above it. `refs/heads/main` is the same story for the
      ref itself: the outer bound still binds `<common>/refs` and pins only
      `refs/wf`, so this one is closed by the VENDOR layer being narrower —
      which is what a vendor layer restating the set narrower is for;
    - `<G>/commondir` and `<G>/gitdir` are INSIDE the codex grant, because `<G>`
      has to be, and are refused by the mount bound's `ro_pins` alone. This is
      the residual the module docstring names, and this assertion is what makes
      "the outer bound is the authority" a measurement instead of a claim;
    - a source file in the writer's own checkout that its `allowed_paths` did
      not grant, which is the §4 bound and not a git question at all;
    - the parent repository's own working tree and a SIBLING activation's
      worktree, neither of which this node has any business in. A grant of
      `<common>/objects` is shared state by nature, so "the writer reached its
      own git dir" must not have quietly become "the writer reached everybody's
      checkout".
    """
    _requirements()
    task, plan = _lab(tmp_path)
    # A neighbour created after planning must be protected too.
    common = _common_of(task)
    for prefix in ("refs/heads", "logs/refs/heads"):
        late = common / prefix / "wf/late/candidate"
        late.parent.mkdir(parents=True)
        late.write_text("late neighbour\n")
    roots = git_write_roots_of(Path(task.cwd))
    gitdir = Path(roots[0])
    common = Path(roots[1]).parent
    protected = {
        "late-ref": common / "refs/heads/wf/late/candidate",
        "late-reflog": common / "logs/refs/heads/wf/late/candidate",
        "sibling-ref": common / "refs/heads/wf/sibling/candidate",
        "sibling-reflog": common / "logs/refs/heads/wf/sibling/candidate",
        "worktree-config": gitdir / "config.worktree",
        "worktree-info": gitdir / "info/attributes",
        "config": common / "config",
        "hooks": common / "hooks" / "pre-commit",
        "info": common / "info" / "attributes",
        "packed-refs": common / "packed-refs",
        "refs-wf": common / WF_REF,
        "refs-main": common / "refs" / "heads" / "main",
        "reflog-wf": common / WF_REFLOG,
        "reflog-main": common / MAIN_REFLOG,
        "reflog-head": common / "logs" / "HEAD",
        "commondir": gitdir / "commondir",
        "gitdir-pointer": gitdir / "gitdir",
        "ungranted-source": Path(task.cwd) / UNGRANTED_FILE,
        "parent-worktree": common.parent / GRANTED_FILE,
        "sibling-worktree": Path(task.cwd).parent / SIBLING / GRANTED_FILE,
        "sibling-gitdir": common / "worktrees" / SIBLING / "index",
    }
    profile = CodexProfile(ProfileConfig(), FrozenClock(), {})
    command = profile.build_command(task, "")

    observed = _run(
        plan,
        command,
        _permission_config(command.argv),
        "\n".join(_write_probe(path, label) for label, path in protected.items()),
        tmp_path,
        vendor_layer=vendor_layer,
    )

    for label in protected:
        assert f"{DENIED}:{label}" in observed, f"{label}\n{observed}"
    assert ALLOWED not in observed, observed


@pytest.mark.proc
@pytest.mark.nested_sandbox
def test_the_superseded_wide_reflog_grant_is_what_opened_those_reflogs(
    tmp_path: Path,
) -> None:
    """RED for the reflog half of the negative above, on the real stack.

    A negative that has only ever been observed passing proves nothing about the
    grant — it may be refused for some reason that has nothing to do with the
    writable set. So this states the SUPERSEDED configuration literally, on both
    layers at once: `<common>/refs/heads` and `<common>/logs` as codex writable
    roots, and `<common>/logs` bound read-write in the mount plan with no pin
    behind it, which is exactly what the outer plan used to emit. Under it the
    parent checkout's `main` reflog and the wrapper's own `refs/wf` reflog are
    both writable, and `refs/heads/main` with them.

    Everything else — the checkout, the `<G>`, the object store, the pins, the
    child `TMPDIR` and `CODEX_HOME` — is the production lab's, so an `ALLOWED`
    here can only be about the two paths that were widened.
    """
    _requirements()
    task, plan = _lab(tmp_path)
    common = _common_of(task)
    gitdir, objects, _branch_refs, branch_logs = git_write_roots_of(Path(task.cwd))
    wide_roots = (gitdir, objects, str(common / "refs" / "heads"), str(common / "logs"))
    wide_plan = plan.model_copy(
        update={
            "git_rw": tuple(
                common / "logs"
                if str(path) == branch_logs
                else common / "refs"
                if str(path) == _branch_refs
                else path
                for path in plan.git_rw
            )
        }
    )
    assert common / "logs" in wide_plan.git_rw
    wide_config = [
        CONFIG,
        f'{KEY_SANDBOX_MODE}="{WORKSPACE_WRITE}"',
        CONFIG,
        f"sandbox_workspace_write.writable_roots={json.dumps(list(wide_roots))}",
        CONFIG,
        "sandbox_workspace_write.network_access=false",
        CONFIG,
        "sandbox_workspace_write.exclude_slash_tmp=true",
    ]
    command = CodexProfile(ProfileConfig(), FrozenClock(), {}).build_command(task, "")
    reached = {
        "reflog-main": common / MAIN_REFLOG,
        "reflog-wf": common / WF_REFLOG,
        "refs-main": common / "refs" / "heads" / "main",
    }

    observed = _run(
        wide_plan,
        command,
        wide_config,
        "\n".join(_write_probe(path, label) for label, path in reached.items()),
        tmp_path,
    )

    for label in reached:
        assert f"{ALLOWED}:{label}" in observed, f"{label}\n{observed}"


@pytest.mark.proc
@pytest.mark.nested_sandbox
def test_a_reviewer_can_write_its_channels_and_nothing_of_the_checkout(
    tmp_path: Path,
) -> None:
    """A `writes = false` node gains nothing from the writer's git grant.

    The grant is conditional on `writes`, so the thing to prove is that a
    reviewer — which is what every codex node in `config/foreman.example.toml`
    still is — can report and cannot touch source or git metadata. Rooted at
    `channels/`, with only its external private toolchain added, it is
    bounded twice over.
    """
    _requirements()
    task, plan = _lab(tmp_path, writes=False)
    task = task.model_copy(update={"toolchain_cache": str(plan.toolchain_cache[0])})
    profile = CodexProfile(ProfileConfig(), FrozenClock(), {})
    command = profile.build_command(task, "")
    assert writable_roots_in(command.argv) == (str(plan.toolchain_cache[0]),)
    assert not plan.toolchain_cache[0].is_relative_to(Path(task.cwd))
    roots_a_writer_would_get = git_write_roots_of(Path(task.cwd))

    observed = _run(
        plan,
        command,
        _permission_config(command.argv),
        "\n".join(
            [
                _write_probe(
                    Path(task.channels.artifact_dir) / "findings.md", "report"
                ),
                _write_probe(plan.toolchain_cache[0] / "probe", "cache"),
                _write_probe(Path(task.channels.log_path), "wrapper-record"),
                _write_probe(Path(task.cwd) / GRANTED_FILE, "source"),
                _write_probe(Path(roots_a_writer_would_get[0]) / "index", "index"),
                _write_probe(Path(roots_a_writer_would_get[1]) / "planted", "objects"),
            ]
        ),
        tmp_path,
    )

    assert f"{ALLOWED}:report" in observed, observed
    assert f"{ALLOWED}:cache" in observed, observed
    for label in ("source", "index", "objects", "wrapper-record"):
        assert f"{DENIED}:{label}" in observed, f"{label}\n{observed}"


# --- the refusals, which need no sandbox ----------------------------------


def test_an_in_repo_writer_is_refused_before_anything_is_dispatched(
    tmp_path: Path,
) -> None:
    """§12's in-repo band cannot be bounded for this vendor, so it is refused.

    There `index.lock` is created inside `<C>/.git`, the same directory that
    holds `config` and `hooks/`. `sandbox_workspace_write` grants whole
    directories and has no key that takes a subdirectory back, so a grant that
    let the node commit would also let it name the programs the wrapper's own
    git runs. The refusal happens in `build_command`, before the fork barrier
    and before any session is minted, and it says what to do instead.
    """
    checkout = tmp_path / "in-repo"
    checkout.mkdir()
    (checkout / ".git").mkdir()
    task = make_task(tmp_path, writes=True, cwd=checkout)
    profile = CodexProfile(ProfileConfig(), FrozenClock(), {})

    with pytest.raises(UnsupportedOptionError) as refusal:
        profile.build_command(task, "")

    assert "in-repo" in str(refusal.value)
    assert "worktree isolation" in str(refusal.value)


def test_a_writer_whose_checkout_proves_no_topology_is_refused(
    tmp_path: Path,
) -> None:
    """No `.git` at all means no proof of where the git state is, so: no grant.

    Fail-closed is the only safe direction here. The alternative — grant the
    channels and hope — is what produced the original defect, and guessing a
    `<G>` would mean naming a directory the mount bound never bound.
    """
    checkout = tmp_path / "bare"
    checkout.mkdir()
    task = make_task(tmp_path, writes=True, cwd=checkout)
    profile = CodexProfile(ProfileConfig(), FrozenClock(), {})

    with pytest.raises(SandboxPathRefused) as refusal:
        profile.build_command(task, "")

    assert "linked worktree" in str(refusal.value)


def test_the_granted_git_roots_are_the_four_a_commit_touches(tmp_path: Path) -> None:
    """The grant set, named independently of the code that computes it.

    `git_write_roots_of` walks `<C>/.git`, `<G>/commondir` and `<G>/HEAD` by
    hand. If this ever disagrees with `worktree_git_write_roots`, one of them is
    wrong about the repository on disk — which is the only way a vendor grant
    and a mount bind can silently stop describing the same thing.

    The last two entries are the branch's own directories, not `refs/heads` and
    `logs`: the lab checkout is on `wf/lab-checkout` exactly as §5.4 puts a
    candidate on `wf/<root_id>/candidate`, with separate instance directories; the
    parent checkout's `main` ref and reflog are outside the grant.
    """
    task = make_task(tmp_path, writes=True)
    common = _common_of(task)

    granted = worktree_git_write_roots(Path(task.cwd), task.root_id)

    assert tuple(str(path) for path in granted) == git_write_roots_of(Path(task.cwd))
    assert [path.name for path in granted] == [
        "worktree",
        "objects",
        task.root_id,
        task.root_id,
    ]
    assert granted[2] == common / "refs" / "heads" / "wf" / task.root_id
    assert granted[3] == common / "logs" / "refs" / "heads" / "wf" / task.root_id


def test_a_detached_writer_is_granted_no_shared_ref_or_reflog_directory(
    tmp_path: Path,
) -> None:
    """No branch, no branch grant: the commit moves only what is inside `<G>`.

    §7.3's grading checkout is branchless on purpose. Deriving a `refs/heads`
    directory for it would mean granting one the commit never writes, and
    `refs/heads` is where every other branch lives.
    """
    task = make_task(tmp_path, writes=True)
    checkout = Path(task.cwd)
    subprocess.run(
        ["git", "checkout", "--quiet", "--detach"],
        cwd=checkout,
        check=True,
        capture_output=True,
        timeout=GIT_TIMEOUT_S,
    )

    granted = worktree_git_write_roots(checkout, task.root_id)

    assert [path.name for path in granted] == ["worktree", "objects"]
    assert tuple(str(path) for path in granted) == git_write_roots_of(checkout)


def test_a_head_that_walks_out_of_refs_heads_grants_no_directory(
    tmp_path: Path,
) -> None:
    """`<G>/HEAD` is inside the writable `<G>`, so its text is runner-controlled.

    A previous dispatch that rewrote `HEAD` to `ref: refs/heads/../../hooks/x`
    would otherwise have the NEXT one grant `<common>/hooks` — the programs the
    wrapper's own git runs — to its vendor sandbox. The traversal is rejected
    and the grant falls back to `<G>` and the object store.
    """
    task = make_task(tmp_path, writes=True)
    checkout = Path(task.cwd)
    gitdir = Path(git_write_roots_of(checkout)[0])
    (gitdir / "HEAD").write_text("ref: refs/heads/../../hooks/x\n", encoding="utf-8")

    granted = worktree_git_write_roots(checkout, task.root_id)

    assert [path.name for path in granted] == ["worktree", "objects"]


@pytest.mark.parametrize("branch", ["main", "wf/legacy", "wf/sibling/candidate"])
def test_writer_head_cannot_select_another_instances_grants(
    tmp_path: Path, branch: str
) -> None:
    task, _ = _lab(tmp_path)
    gitdir = Path(git_write_roots_of(Path(task.cwd))[0])
    (gitdir / "HEAD").write_text(f"ref: refs/heads/{branch}\n")
    config = make_supervisor_config(tmp_path)
    with pytest.raises(SandboxPathRefused, match="isolated instance branch"):
        plan_for(
            task,
            repo_root=config.repo_root,
            wrapper_root=config.wrapper_root,
            channels_dir=Path(task.channels.outcome_file).parent,
        )
    with pytest.raises(SandboxPathRefused, match="isolated instance branch"):
        CodexProfile(ProfileConfig(), FrozenClock(), {}).build_command(task, "")
