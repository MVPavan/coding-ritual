"""The §2 mount bound: `allowed_paths` expressed as real mounts, not as prose.

Phase 1 of `docs/plans/allowed-paths-enforcement-phase-1.md` (ADR 0001, owner
decisions O1-O5). A dispatched runner runs inside `bwrap`, and the ONLY writable
things it can reach in the workspace are the node's grants, the `channels/`
directory and the git state a commit needs. Everything else the wrapper cares
about — the main repo's tree, this repo's agent worktrees, the `.wf/`
observation cache — is bound read-only.

Three facts drive the whole design, and all three were probed rather than
assumed (plan §2):

- **Bind order IS mount order.** A read-only pin emitted BEFORE a later
  read-write bind of its parent is re-opened by that bind. `wrap` therefore
  emits, unconditionally: broad ro roots → git rw → grants → channels →
  uv-cache → **ro pins LAST**. `SandboxPlan`'s field order is that order;
  nothing else keeps them in step.
- **`--dev-bind / /` leaves everything not explicitly bound WRITABLE.** The
  `repo_root`/`wrapper_root` ro-binds are load-bearing, not defensive. `$HOME`
  and `/tmp` stay writable by design — an accepted residual (plan §8).
- **A bind source that does not exist fails the whole box** with a bare `rc=1`
  that is indistinguishable from a runner exiting 1. Hence the fixed
  pre-creation set below, existence gating for every other path, and
  `SandboxPathRefused` for a root that is simply not there.

This module is pure planning plus one capability probe: it never launches a
runner. `launch.py` applies `wrap` as the last transform before exec, and
`Dispatcher._launch` calls `probe` before a session is minted.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.supervisor.errors import SandboxPathRefused

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checking only
    from workflow_interpreter.supervisor.config import SupervisorConfig
    from workflow_interpreter.supervisor.profile import TaskSpec

SANDBOX_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="forbid", arbitrary_types_allowed=False
)

BWRAP_BINARY: Final[str] = "bwrap"
ARG_DIE_WITH_PARENT: Final[str] = "--die-with-parent"
"""Makes the box a leaf of the supervisor's process tree: a SIGKILLed wrapper
tears the sandbox down instead of leaving an unreapable runner holding mounts."""
ARG_DEV_BIND: Final[str] = "--dev-bind"
ARG_RO_BIND: Final[str] = "--ro-bind"
ARG_BIND: Final[str] = "--bind"
ARG_VERSION: Final[str] = "--version"
ARG_END: Final[str] = "--"
FS_ROOT: Final[str] = "/"
SHELL: Final[str] = "/bin/sh"
SHELL_COMMAND: Final[str] = "-c"
PROBE_TIMEOUT_S: Final[float] = 10.0
"""One `bwrap` startup measures ~2.3 ms (plan §3); this is a hang bound, not a
budget."""

GIT_ENTRY: Final[str] = ".git"
GITDIR_PREFIX: Final[str] = "gitdir:"
COMMONDIR_FILE: Final[str] = "commondir"
GITDIR_FILE: Final[str] = "gitdir"
WORKTREES_DIR: Final[str] = "worktrees"
"""`<G>`'s two POINTER files, and the directory that holds every `<G>`.

`commondir` decides which `config` git reads and `gitdir` decides which
checkout `<G>` belongs to. `<G>` itself must stay read-write (`index.lock`
is created in it), so both are pinned back — a runner that can repoint
`commondir` at a directory it controls makes the WRAPPER's own next
`git status`, run outside the box, execute the `core.fsmonitor` it plants
there. Probed: the escape works without these pins."""
OBJECTS_DIR: Final[str] = "objects"
REFS_DIR: Final[str] = "refs"
LOGS_DIR: Final[str] = "logs"
PACKED_REFS_FILE: Final[str] = "packed-refs"
CONFIG_FILE: Final[str] = "config"
CONFIG_WORKTREE_FILE: Final[str] = "config.worktree"
HOOKS_DIR: Final[str] = "hooks"
INFO_DIR: Final[str] = "info"
WF_REFS_DIR: Final[str] = "refs/wf"
"""The wrapper's evidence refs. Pinning it protects them as LOOSE refs only;
`packed-refs` stays rw for the runner's own commit, so ref forgery survives O2
and is filed separately (plan §8)."""
MODULES_CONFIG_GLOB: Final[str] = "modules/*/config"
"""Submodule configs, which name programs the same way `config` does. Only
in-repo mode needs them: a fresh worktree checkout has EMPTY submodule
directories with no `.git` file at all (probed, plan §8)."""

GRANT_SUFFIX: Final[str] = "/**"
"""The only `allowed_paths` shape the schema accepts (§4). Stripping it yields a
repo-relative DIRECTORY, which is what a mount source has to be."""

ENV_UV_PROJECT_ENVIRONMENT: Final[str] = "UV_PROJECT_ENVIRONMENT"
ENV_UV_CACHE_DIR: Final[str] = "UV_CACHE_DIR"
ENV_UV_PYTHON_INSTALL_DIR: Final[str] = "UV_PYTHON_INSTALL_DIR"
ENV_UV_FROZEN: Final[str] = "UV_FROZEN"
ENV_RUFF_CACHE_DIR: Final[str] = "RUFF_CACHE_DIR"
ENV_MYPY_CACHE_DIR: Final[str] = "MYPY_CACHE_DIR"
ENV_PYTEST_ADDOPTS: Final[str] = "PYTEST_ADDOPTS"
UV_FROZEN_VALUE: Final[str] = "1"
PYTEST_CACHE_OPTION: Final[str] = "-o cache_dir={path}"
UV_CACHE_DIRECTORY: Final[str] = "uv-cache"
UV_PYTHON_DIRECTORY: Final[str] = "python"
"""The §2 toolchain env, named here so the launcher and `profiles/_base.py`
IMPORT it rather than re-spell it.

A read-only checkout breaks the node's own `verify`: `uv run` creates `.venv`
in the checkout, ruff and mypy create caches there. Profiles point all five
toolchain locations at `$WF_SCRATCH_DIR`; the launcher replaces `UV_CACHE_DIR`
and `UV_PYTHON_INSTALL_DIR` with locations below the wrapper-root cache that
this plan binds read-write. `-o cache_dir=` is chosen over
`-p no:cacheprovider` because the latter also disables `--lf`/`--ff`/`--sw`.
`UV_FROZEN` is a stated limitation, not a nicety: a node under the bound cannot
`uv add` a dependency, and reports `fail_plan` instead."""

REASON_OFF: Final[str] = "off"
REASON_OK: Final[str] = "bwrap"
REASON_ABSENT: Final[str] = "bwrap is not on PATH"
REASON_VERSION: Final[str] = "`bwrap --version` failed: {detail}"
REASON_SELF_TEST: Final[str] = "the bwrap self-test did not hold: {detail}"
_DETAIL_NO_WRITE: Final[str] = "a write inside the read-write bind was refused"
_DETAIL_NO_BOUND: Final[str] = "a write outside the bound succeeded"
_DETAIL_EXIT: Final[str] = "the self-test exited {returncode}: {stderr}"

_SELF_TEST_INSIDE: Final[str] = "allowed"
_SELF_TEST_OUTSIDE: Final[str] = "denied"
_SELF_TEST_RW_DIR: Final[str] = "rw"
_SELF_TEST_EXIT_NO_WRITE: Final[int] = 3
_SELF_TEST_EXIT_NO_BOUND: Final[int] = 4
_SELF_TEST_SCRIPT: Final[str] = (
    "echo probe > {inside} || exit 3\n"
    "if echo probe > {outside} 2>/dev/null; then exit 4; fi\n"
    "exit 0\n"
)
"""`echo`, not `:`: a redirection failure on a POSIX SPECIAL builtin exits the
shell outright, which would collapse both failure modes into one status."""

_MSG_MISSING_ROOT: Final[str] = (
    "{field} {path} does not exist; the mount bound cannot read-only bind it"
)
_MSG_GITDIR: Final[str] = (
    "{path} is not a git worktree link: expected a {prefix!r} line, got {text!r}"
)
_MSG_ESCAPES: Final[str] = (
    "allowed_paths entry {grant!r} resolves to {resolved}, outside the checkout "
    "{checkout}; a grant may never widen the bound"
)
_MSG_GRANT_SYMLINK: Final[str] = (
    "allowed_paths entry {grant!r} has symlinked directory segment {segment!r} "
    "at {path}; a grant must name the same path git will report"
)
_MSG_GRANT_SHAPE: Final[str] = (
    "allowed_paths entry {grant!r} is not a directory grant; every entry must "
    "be <dir>/** with no empty segment and no segment starting with a dot"
)
_MSG_RELATIVE: Final[str] = "every sandbox bind must be absolute, got {path}"

_FIELD_REPO_ROOT: Final[str] = "repo_root"
_FIELD_WRAPPER_ROOT: Final[str] = "wrapper_root"


class SandboxMode(StrEnum):
    """Whether a dispatch runs inside the mount bound (O5: on by default)."""

    BWRAP = "bwrap"
    OFF = "off"


class SandboxCapability(BaseModel):
    """What `probe` learned about this host's ability to hold the bound.

    `reason` is operator-facing text on both paths: the `proc` tests skip with
    it, and the §3 refusal closes with it.
    """

    model_config = SANDBOX_MODEL

    available: bool
    version: str | None = None
    reason: str = ""
    binary: str = BWRAP_BINARY
    """The ABSOLUTE path `probe` resolved, so nothing has to resolve it twice.

    A bare `bwrap` in the wrapped argv would let the CHILD's `PATH` — a
    passthrough value the runner's environment carries — decide which binary
    holds the bound. Defaulted to the bare name only for the unresolved case,
    which never reaches `wrap` because the dispatch is refused first."""


class SandboxPlan(BaseModel):
    """One dispatch's mount set, in the order `wrap` must emit it.

    The field order is the BIND order and the bind order is the mount order —
    `ro_pins` last is what keeps a pin from being re-opened by a later
    read-write bind of its parent (plan §2). Reordering these fields is a
    security change, not a cosmetic one.
    """

    model_config = SANDBOX_MODEL

    binary: str = BWRAP_BINARY
    """What `wrap` execs, as `probe` resolved it (`SandboxCapability.binary`).

    On the PLAN rather than passed alongside it because the launcher already
    carries the plan and `wrap` already takes it: one object decides the whole
    invocation, and there is no second argument a caller can forget."""
    ro_roots: tuple[Path, ...] = ()
    git_rw: tuple[Path, ...] = ()
    grants: tuple[Path, ...] = ()
    channels: tuple[Path, ...] = ()
    toolchain_cache: tuple[Path, ...] = ()
    ro_pins: tuple[Path, ...] = ()

    def model_post_init(self, context: object, /) -> None:
        """Refuse a relative bind, which bwrap would resolve against its own cwd."""
        for group in (
            self.ro_roots,
            self.git_rw,
            self.grants,
            self.channels,
            self.toolchain_cache,
            self.ro_pins,
        ):
            for path in group:
                if not path.is_absolute():
                    raise SandboxPathRefused(_MSG_RELATIVE.format(path=path))


def _require_dir(field: str, path: Path) -> Path:
    """Resolve a mandatory read-only root, refusing one that is not there."""
    resolved = path.resolve()
    if not resolved.is_dir():
        raise SandboxPathRefused(_MSG_MISSING_ROOT.format(field=field, path=path))
    return resolved


def _existing(paths: tuple[Path, ...]) -> tuple[Path, ...]:
    """Keep only the paths that exist, preserving the caller's order."""
    return tuple(path for path in paths if path.exists())


def _ensure_file(path: Path) -> None:
    """Create an empty bind source when absent (the fixed pre-creation set)."""
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()


def _ensure_dir(path: Path) -> None:
    """Create a directory bind source when absent (the fixed pre-creation set)."""
    path.mkdir(parents=True, exist_ok=True)


def _refuse_bad_shape(grant: str) -> str:
    """Refuse anything that is not `<dir>/(<dir>/)*` + `/**`; return the relative dir.

    Defence in depth behind the §4 schema pattern, and NOT redundant with it:
    `plan_for` is reachable from a graph the schema never validated (a fixture,
    a test, a future caller), and each rejected shape is a real hole. `./**` and
    a bare `**` map to the WHOLE checkout; `tests` with no suffix is taken
    literally as a directory of that name; any `.`-leading segment reaches a pin
    (`.git/**` would re-open every one of them); an empty segment or a leading
    `/` makes the join mean something other than it reads.

    A typed refusal rather than whatever `mkdir` happens to raise: `.git/**` used
    to surface as a bare `FileExistsError`, and an `OSError` out of here is spent
    as a §10.2 infra retry by `supervise.py`'s generic catch instead of halting.
    """
    if not grant.endswith(GRANT_SUFFIX):
        raise SandboxPathRefused(_MSG_GRANT_SHAPE.format(grant=grant))
    relative = grant.removesuffix(GRANT_SUFFIX)
    segments = relative.split("/")
    if not segments or any(
        not segment or segment.startswith(".") for segment in segments
    ):
        raise SandboxPathRefused(_MSG_GRANT_SHAPE.format(grant=grant))
    return relative


def grant_directory(grant: str) -> PurePosixPath:
    """The repo-relative directory one `<dir>/**` grant names, as pure path math.

    Public because the §6 profiles express the SAME grant set in their own
    permission layers (phase 2 of `docs/plans/allowed-paths-enforcement.md`), and
    a second copy of the mapping is a second answer to "what does this grant
    mean". Pure on purpose: `_grant_path` resolves and PRE-CREATES a mount
    source, which is work a profile building argv must never do.
    """
    return PurePosixPath(_refuse_bad_shape(grant))


def _grant_path(grant: str, checkout: Path) -> Path:
    """Map one `<dir>/**` grant to the real directory it may write.

    `realpath` before the containment check, because a symlink inside the
    checkout pointing out of it is exactly the escape a lexical check misses.
    """
    relative = grant_directory(grant)
    named = checkout
    for segment in relative.parts:
        named /= segment
        if named.is_symlink():
            raise SandboxPathRefused(
                _MSG_GRANT_SYMLINK.format(grant=grant, segment=segment, path=named)
            )
    resolved = (checkout / relative).resolve()
    if not resolved.is_relative_to(checkout):
        raise SandboxPathRefused(
            _MSG_ESCAPES.format(grant=grant, resolved=resolved, checkout=checkout)
        )
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _parse_gitdir(git_file: Path) -> Path:
    """Read `<C>/.git` as the worktree link it is, yielding `<G>`."""
    text = git_file.read_text(encoding="utf-8").strip()
    if not text.startswith(GITDIR_PREFIX):
        raise SandboxPathRefused(
            _MSG_GITDIR.format(path=git_file, prefix=GITDIR_PREFIX, text=text)
        )
    named = Path(text[len(GITDIR_PREFIX) :].strip())
    if not named.is_absolute():
        named = git_file.parent / named
    return named.resolve()


def _common_dir(gitdir: Path) -> Path:
    """The shared git directory `<G>` borrows its object store from.

    `commondir` holds a path relative to `<G>` (`../..` in practice). Absent
    means `<G>` is its own common dir, which is a degenerate but bindable shape.
    """
    marker = gitdir / COMMONDIR_FILE
    if not marker.is_file():
        return gitdir
    named = Path(marker.read_text(encoding="utf-8").strip())
    if not named.is_absolute():
        named = gitdir / named
    return named.resolve()


def _in_repo_binds(
    git_dir: Path,
) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """In-repo shape: `.git` read-write as a WHOLE, minus what executes programs.

    Whole, because `index.lock` is created directly in `.git/` and a runner that
    cannot take it cannot commit (O2). The pins take back the parts that make
    git run a program: `config` and `config.worktree` name filters and hooks
    paths, `hooks/` holds the programs, `info/attributes` selects filter
    drivers, and `modules/*/config` is the same surface per submodule.

    The complete `worktrees/` directory is pinned, rather than enumerating its
    current children: a sibling created after planning is otherwise writable
    until this dispatch ends.
    """
    _ensure_file(git_dir / CONFIG_WORKTREE_FILE)
    _ensure_dir(git_dir / INFO_DIR)
    worktrees = git_dir / WORKTREES_DIR
    _ensure_dir(worktrees)
    pins = _existing(
        (
            git_dir / CONFIG_FILE,
            git_dir / CONFIG_WORKTREE_FILE,
            git_dir / HOOKS_DIR,
            git_dir / INFO_DIR,
            *sorted(git_dir.glob(MODULES_CONFIG_GLOB)),
            git_dir / WF_REFS_DIR,
            worktrees,
        )
    )
    return ((git_dir,), pins)


def _worktree_binds(
    git_file: Path,
) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Worktree shape: the common object store plus this worktree's own git dir.

    `logs` is load-bearing and was missed first: without it `git commit` dies
    `unable to append to '.git/logs/refs/heads/<branch>'`. It is PRE-CREATED
    rather than existence-gated: a repo whose first ref update has not happened
    yet has no `logs/` at all, and gating it there would leave the runner's own
    commit failing EROFS trying to create it under a read-only `.git`.

    `commondir` and `gitdir` are pinned back out of the read-write `<G>`: they
    are POINTERS, and a runner that repoints `commondir` at a directory it
    controls plants the `config` — and therefore the `core.fsmonitor` command —
    that the WRAPPER's own next `git status` executes, outside the box, as the
    wrapper. Probed: without these pins the marker file appears.
    """
    gitdir = _parse_gitdir(git_file)
    common = _common_dir(gitdir)
    _ensure_dir(common / LOGS_DIR)
    _ensure_file(common / PACKED_REFS_FILE)
    _ensure_file(gitdir / CONFIG_WORKTREE_FILE)
    _ensure_dir(gitdir / INFO_DIR)
    git_rw = _existing(
        (
            common / OBJECTS_DIR,
            common / REFS_DIR,
            common / LOGS_DIR,
            common / PACKED_REFS_FILE,
            gitdir,
        )
    )
    pins = _existing(
        (
            common / WF_REFS_DIR,
            gitdir / COMMONDIR_FILE,
            gitdir / GITDIR_FILE,
            gitdir / CONFIG_WORKTREE_FILE,
            gitdir / INFO_DIR,
        )
    )
    return (git_rw, pins)


def _git_binds(
    checkout: Path,
) -> tuple[tuple[Path, ...], tuple[Path, ...]]:
    """Route on what `<C>/.git` actually IS — directory, file, or nothing.

    No subprocess: the shape is on disk, and asking git would mean running git
    as the wrapper on a tree the runner controls.
    """
    entry = checkout / GIT_ENTRY
    if entry.is_dir():
        return _in_repo_binds(entry)
    if entry.is_file():
        return _worktree_binds(entry)
    return ((), ())


def plan_for(
    task: TaskSpec,
    *,
    repo_root: Path,
    wrapper_root: Path,
    channels_dir: Path,
    binary: str = BWRAP_BINARY,
) -> SandboxPlan:
    """Compute one dispatch's mount set from its `TaskSpec` and the wrapper roots.

    `binary` is what `probe` resolved; it is threaded through rather than
    re-resolved here because this function deliberately runs no subprocess.

    A `writes = false` node gets the three read-only roots and `channels/` and
    nothing more — it can still report (§6), and there is no writable git state
    to re-close, so it carries no pins either.
    """
    checkout = Path(task.cwd).resolve()
    ro_roots = (
        _require_dir(_FIELD_REPO_ROOT, repo_root),
        _require_dir(_FIELD_WRAPPER_ROOT, wrapper_root),
        checkout,
    )
    channels = (channels_dir.resolve(),)
    toolchain_cache = toolchain_cache_for(wrapper_root)
    if not task.writes:
        return SandboxPlan(
            binary=binary,
            ro_roots=ro_roots,
            channels=channels,
            toolchain_cache=toolchain_cache,
        )
    grants = tuple(_grant_path(grant, checkout) for grant in task.allowed_paths)
    git_rw, ro_pins = _git_binds(checkout)
    return SandboxPlan(
        binary=binary,
        ro_roots=ro_roots,
        git_rw=git_rw,
        grants=grants,
        channels=channels,
        toolchain_cache=toolchain_cache,
        ro_pins=ro_pins,
    )


def toolchain_cache_for(wrapper_root: Path) -> tuple[Path, ...]:
    """Create the wrapper-wide uv cache used by both sandbox modes."""
    cache_dir = (wrapper_root / UV_CACHE_DIRECTORY).resolve()
    _ensure_dir(cache_dir)
    return (cache_dir,)


def _binds(flag: str, paths: tuple[Path, ...]) -> list[str]:
    """One bind group as bwrap argv words: `<flag> <path> <path>`, in order."""
    words: list[str] = []
    for path in paths:
        words += [flag, str(path), str(path)]
    return words


def wrap(
    argv: tuple[str, ...],
    plan: SandboxPlan,
    *,
    mode: SandboxMode = SandboxMode.BWRAP,
) -> tuple[str, ...]:
    """Wrap an inner argv in the mount bound the plan describes.

    `mode` is a keyword with the O5 default so the ONE off switch lives beside
    the bind emission it disables; `SandboxMode.OFF` returns the argv untouched
    rather than building a differently-shaped box.
    """
    if mode is SandboxMode.OFF:
        return tuple(argv)
    words = [
        plan.binary,
        ARG_DIE_WITH_PARENT,
        ARG_DEV_BIND,
        FS_ROOT,
        FS_ROOT,
        *_binds(ARG_RO_BIND, plan.ro_roots),
        *_binds(ARG_BIND, plan.git_rw),
        *_binds(ARG_BIND, plan.grants),
        *_binds(ARG_BIND, plan.channels),
        *_binds(ARG_BIND, plan.toolchain_cache),
        *_binds(ARG_RO_BIND, plan.ro_pins),
    ]
    return (*words, ARG_END, *argv)


_CAPABILITY: SandboxCapability | None = None
"""Measured once per wrapper process (plan §3). Module-level rather than
config-carried because it is a fact about the HOST, not about a run."""


def reset_probe_cache() -> None:
    """Forget the measured capability, so a test can measure again."""
    global _CAPABILITY
    _CAPABILITY = None


def _self_test(binary: str) -> str:
    """Prove the bound both permits and refuses; return "" or a failure detail.

    A `bwrap` that runs but does not enforce is worse than an absent one,
    because the dispatch would proceed believing it is bounded.
    """
    with tempfile.TemporaryDirectory() as name:
        box = Path(name).resolve()
        writable = box / _SELF_TEST_RW_DIR
        writable.mkdir()
        script = _SELF_TEST_SCRIPT.format(
            inside=writable / _SELF_TEST_INSIDE, outside=box / _SELF_TEST_OUTSIDE
        )
        argv = [
            binary,
            ARG_DIE_WITH_PARENT,
            ARG_DEV_BIND,
            FS_ROOT,
            FS_ROOT,
            ARG_RO_BIND,
            str(box),
            str(box),
            ARG_BIND,
            str(writable),
            str(writable),
            ARG_END,
            SHELL,
            SHELL_COMMAND,
            script,
        ]
        try:
            completed = subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=PROBE_TIMEOUT_S,
            )
        except (OSError, subprocess.SubprocessError) as error:
            return str(error)
    if completed.returncode == 0:
        return ""
    if completed.returncode == _SELF_TEST_EXIT_NO_WRITE:
        return _DETAIL_NO_WRITE
    if completed.returncode == _SELF_TEST_EXIT_NO_BOUND:
        return _DETAIL_NO_BOUND
    return _DETAIL_EXIT.format(
        returncode=completed.returncode, stderr=completed.stderr.strip()
    )


def _measure() -> SandboxCapability:
    """Ask this host, once, whether it can hold the bound."""
    binary = shutil.which(BWRAP_BINARY)
    if binary is None:
        return SandboxCapability(available=False, reason=REASON_ABSENT)
    try:
        completed = subprocess.run(
            [binary, ARG_VERSION],
            check=False,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return SandboxCapability(
            available=False, reason=REASON_VERSION.format(detail=error)
        )
    if completed.returncode != 0:
        return SandboxCapability(
            available=False,
            reason=REASON_VERSION.format(detail=completed.stderr.strip()),
        )
    version = completed.stdout.strip()
    detail = _self_test(binary)
    if detail:
        return SandboxCapability(
            available=False,
            version=version,
            binary=binary,
            reason=REASON_SELF_TEST.format(detail=detail),
        )
    return SandboxCapability(
        available=True, version=version, binary=binary, reason=REASON_OK
    )


def probe(config: SupervisorConfig) -> SandboxCapability:
    """Whether this host can hold the bound, measured at most once per process.

    `sandbox = off` reports available without measuring anything and WITHOUT
    populating the slot: the off switch is a decision about this run, and it
    must not decide what a later `bwrap` configuration believes about the host.
    """
    global _CAPABILITY
    if config.sandbox is SandboxMode.OFF:
        return SandboxCapability(available=True, reason=REASON_OFF)
    if _CAPABILITY is None:
        _CAPABILITY = _measure()
    return _CAPABILITY
