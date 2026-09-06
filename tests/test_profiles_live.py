"""The real CLIs, driven by the real argv the profiles build.

Deselected at COLLECTION unless `--run-live` is passed (`tests/conftest.py`),
because these spend tokens and need working vendor auth. A marker default in
`addopts` was not a gate — any `-m` on the command line replaced it, so
`pytest -q -m "not bd"` selected them. Run them explicitly:

```
uv run pytest tests/ -q --run-live -m live
```

They exist because the `proc` family cannot catch the one failure mode that
actually bit during the step-0 probes: an argv that is accepted by the CLI and
then quietly does not do what it says. `Write(<path>)` allow-rules parsed fine,
emitted fine, and denied the wrapper's own outcome channel. Only a real run
tells you that. Each test therefore asserts a BOUND — a file that must exist and
a file that must not — rather than merely that the process exited 0.

Every invocation is the profile's own `build_command` output: same argv, same
environment, same working directory. `stdin` is the one difference, and it is a
deliberate one — see `test_profiles_process.py` and the flagged gap: the fork
launcher does not redirect fd 0, and every CLI probed reads or waits on it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Final

import pytest

from tests._profiles import (
    HOST_ENV,
    make_profile_config,
    make_task,
    new_session,
)
from tests._supervisor import FrozenClock
from workflow_interpreter.profiles import fold_usage
from workflow_interpreter.profiles.claude import ClaudeProfile
from workflow_interpreter.profiles.codex import CodexProfile
from workflow_interpreter.supervisor.profile import EventType, RunnerCommand

TIMEOUT_S: Final[float] = 300.0
AGENT_LIST_TIMEOUT_S: Final[float] = 120.0

ALLOWED: Final[str] = "live-allowed.txt"
DENIED: Final[str] = "live-denied.txt"

RESUME_INSTRUCTION: Final[str] = "now reply with the single word two, and stop"

pytestmark = pytest.mark.live


def host_env() -> dict[str, str]:
    """The real host environment, so the CLIs can find their credentials.

    The unit families inject a stand-in; a live run needs the actual one, and
    this is the only place in the suite that reads it. The profile still copies
    only its named passthrough keys out of it.
    """
    return dict(os.environ)


def require(binary: str) -> str:
    """Resolve a vendor CLI, or skip the test that wanted it."""
    found = shutil.which(binary)
    if found is None:
        pytest.skip(f"{binary} is not on PATH")
    return found


def run(command: RunnerCommand) -> subprocess.CompletedProcess[str]:
    """Execute a built `RunnerCommand` exactly as the launcher would, plus stdin."""
    return subprocess.run(
        list(command.argv),
        env=dict(command.env),
        cwd=command.cwd,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_S,
        stdin=subprocess.DEVNULL,
        check=False,
    )


def bound_brief(task_cwd: str, artifact_dir: str) -> str:
    """A prompt that asks for one permitted write and one forbidden one."""
    return (
        "Do exactly two things with the Write tool or a shell command, then "
        f"stop. (1) write the single character x to {artifact_dir}/{ALLOWED} . "
        f"(2) write the single character x to {task_cwd}/{DENIED} . "
        "Then reply with the single word done."
    )


@pytest.mark.live
def test_claude_read_only_really_is_read_only(tmp_path: Path) -> None:
    """The `writes = false` bound, enforced by the real CLI, plus §8.1 identity.

    Two assertions in one run because the second costs nothing extra: the
    resumed session must be the SAME session (drill 14's "session id identical"
    half), and the bound must still hold across the continuation.
    """
    require("claude")
    profile = ClaudeProfile(
        make_profile_config(),
        FrozenClock(),
        host_env(),
    )
    task = make_task(tmp_path, writes=False, model="default")
    task = task.model_copy(
        update={"brief": bound_brief(task.cwd, task.channels.artifact_dir)}
    )
    session = new_session()

    completed = run(profile.build_command(task, session))

    assert completed.returncode == 0, completed.stderr
    assert Path(task.channels.artifact_dir, ALLOWED).exists(), completed.stdout
    assert not Path(task.cwd, DENIED).exists()
    events = list(profile.parse_output(completed.stdout.splitlines()))
    assert {event.session for event in events if event.session} == {session}
    assert [event for event in events if event.type is EventType.RESULT]
    assert fold_usage(events).known is True

    resumed = run(profile.build_resume_command(session, RESUME_INSTRUCTION, task))

    assert resumed.returncode == 0, resumed.stderr
    continued = list(profile.parse_output(resumed.stdout.splitlines()))
    assert {event.session for event in continued if event.session} == {session}


@pytest.mark.live
def test_codex_read_only_really_is_read_only(tmp_path: Path) -> None:
    """Same bound, enforced by an OS sandbox instead of a permission engine.

    Codex's session id is discovered rather than assigned, so the identity half
    is asserted between the launch's `thread.started` and the resume's.
    """
    require("codex")
    profile = CodexProfile(
        make_profile_config(),
        FrozenClock(),
        host_env(),
    )
    task = make_task(tmp_path, writes=False, model="default")
    task = task.model_copy(
        update={"brief": bound_brief(task.cwd, task.channels.artifact_dir)}
    )

    completed = run(profile.build_command(task, ""))

    assert completed.returncode == 0, completed.stderr
    assert Path(task.channels.artifact_dir, ALLOWED).exists(), completed.stdout
    assert not Path(task.cwd, DENIED).exists()
    events = list(profile.parse_output(completed.stdout.splitlines()))
    thread = events[0].session
    assert thread

    resumed = run(profile.build_resume_command(thread, RESUME_INSTRUCTION, task))

    assert resumed.returncode == 0, resumed.stderr
    continued = list(profile.parse_output(resumed.stdout.splitlines()))
    assert continued[0].session == thread


GRANT: Final[str] = "src/**"
GRANT_DIR: Final[str] = "src"
"""One `allowed_paths` grant, for the phase-2 bound claude now expresses in its
own permission engine. Codex has no such case: its sandbox cannot make a
writer's working root read-only, so the mount bound is its whole bound."""


@pytest.mark.live
def test_claude_writes_only_inside_its_declared_grant(tmp_path: Path) -> None:
    """Phase 2, against the real permission engine: the grant is the bound.

    `writes = true` used to grant the whole checkout, so the denied file below
    would simply have been written. The refusal is claude's own — no mount bound
    is applied here, because `run` execs the argv the profile built rather than
    the wrapped one the launcher would.
    """
    require("claude")
    profile = ClaudeProfile(
        make_profile_config(),
        FrozenClock(),
        host_env(),
    )
    task = make_task(tmp_path, writes=True, model="default", allowed_paths=(GRANT,))
    granted = Path(task.cwd, GRANT_DIR)
    granted.mkdir(parents=True, exist_ok=True)
    task = task.model_copy(update={"brief": bound_brief(task.cwd, str(granted))})

    completed = run(profile.build_command(task, new_session()))

    assert completed.returncode == 0, completed.stderr
    assert Path(granted, ALLOWED).exists(), completed.stdout
    assert not Path(task.cwd, DENIED).exists()


@pytest.mark.live
def test_codex_resume_still_lacks_the_flags_the_profile_routes_around() -> None:
    """The asymmetry the codex profile is built around — no tokens spent.

    `codex exec` takes `-s/--sandbox` and `-C/--cd`; `codex exec resume` takes
    neither, so the box travels as `-c` overrides and the working root as the
    process working directory. If a release ever adds them, this test fails and
    the resume path can be simplified.
    """
    binary = require("codex")
    launch = subprocess.run(
        [binary, "exec", "--help"],
        capture_output=True,
        text=True,
        timeout=AGENT_LIST_TIMEOUT_S,
        stdin=subprocess.DEVNULL,
        check=True,
    ).stdout
    resume = subprocess.run(
        [binary, "exec", "resume", "--help"],
        capture_output=True,
        text=True,
        timeout=AGENT_LIST_TIMEOUT_S,
        stdin=subprocess.DEVNULL,
        check=True,
    ).stdout

    assert "--sandbox" in launch
    assert "--add-dir" in launch
    assert "--sandbox" not in resume
    assert "--add-dir" not in resume
    assert "--config" in resume


@pytest.mark.live
def test_opencode_still_has_no_bound_to_offer(tmp_path: Path) -> None:
    """The canary behind `OpencodeProfile`'s refusal — no tokens spent.

    The refusal rests on a fact about the installed CLI: its resolved permission
    stack allows everything, for every agent, from ambient configuration the
    wrapper does not own. If that ever stops being true this test fails, which
    is the signal to give this vendor a real `build_command`.
    """
    binary = require("opencode")
    completed = subprocess.run(
        [binary, "agent", "list"],
        env={**HOST_ENV, **host_env()},
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=AGENT_LIST_TIMEOUT_S,
        stdin=subprocess.DEVNULL,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert '"permission": "*"' in completed.stdout
    assert '"action": "allow"' in completed.stdout
