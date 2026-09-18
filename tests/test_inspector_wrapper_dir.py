"""The wrapper dir, `/proc` parsing and the two transports' structural refusals.

Small, unglamorous invariants that everything else rests on: a durable write
leaves no temp file behind, a MALFORMED record is distinguishable from an
ABSENT one, a torn ledger line is counted but not parsed, and neither transport
can be aimed outside what the wrapper owns.
"""

from __future__ import annotations

import os
import signal
import time
from pathlib import Path

import pytest

from tests._supervisor import (
    BOOT_ID,
    START_TIME,
    FrozenClock,
    handle_for,
    make_config,
    make_git,
    make_repo,
    write_proc_entry,
)
from workflow_interpreter.supervisor import (
    ExecLedger,
    ExecLedgerEntry,
    ForkBarrierLauncher,
    GitCommandError,
    Liveness,
    RunnerCommand,
    SupervisorConfigError,
    WrapperDirError,
    WrapperPaths,
)
from workflow_interpreter.supervisor import paths as paths_module
from workflow_interpreter.supervisor import procfs as procfs_module
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.gitio import GitSubcommand
from workflow_interpreter.supervisor.models import StaleFlag
from workflow_interpreter.supervisor.paths import (
    read_json_documents,
    read_record,
    read_tail,
    write_durable,
    write_record,
)
from workflow_interpreter.supervisor.procfs import (
    prove_liveness,
    read_start_time,
    terminate,
)
from workflow_interpreter.supervisor.sandbox import (
    UV_CACHE_DIRECTORY,
    SandboxMode,
    SandboxPlan,
)

ACTIVATION_ID = "wf-1"

FLAG = StaleFlag(
    activation_id=ACTIVATION_ID,
    raised_at="2026-08-25T12:00:00Z",
    last_activity_at="2026-08-25T11:00:00Z",
    stale_after_s=600.0,
)


def test_a_durable_write_leaves_no_temp_file(tmp_path: Path) -> None:
    """§5.2: temp → fsync → rename → fsync(dir), and nothing else on disk."""
    target = tmp_path / "nested" / "record.json"

    write_record(target, FLAG)

    assert read_record(target, StaleFlag) == FLAG
    assert [path.name for path in target.parent.iterdir()] == ["record.json"]


def test_a_durable_write_replaces_rather_than_truncates(tmp_path: Path) -> None:
    """A crashed rewrite leaves the OLD record, never a half-written one."""
    target = tmp_path / "record.json"
    write_durable(target, b'{"first": true}')

    write_durable(target, b'{"second": true}')

    assert target.read_bytes() == b'{"second": true}'


def test_absent_and_malformed_records_are_different_answers(tmp_path: Path) -> None:
    """§5.6 needs "never written" and "truncated by the crash" to be tellable apart."""
    missing = tmp_path / "gone.json"
    torn = tmp_path / "torn.json"
    torn.write_text('{"activation_id": "wf-1", "raised', encoding="utf-8")

    assert read_record(missing, StaleFlag) is None
    with pytest.raises(WrapperDirError, match="does not parse"):
        read_record(torn, StaleFlag)


def test_a_torn_ledger_line_counts_but_does_not_parse(tmp_path: Path) -> None:
    """The conservative side: an exec that may have happened is treated as one."""
    path = tmp_path / "exec.ledger"
    entry = ExecLedgerEntry(
        launch_id="a", activation_id="wf-1", pid=7, at="2026-08-25T12:00:00Z"
    )
    path.write_bytes(ExecLedger.line(entry) + b'{"launch_id": "b", "activ\n')
    ledger = ExecLedger(path)

    assert ledger.count() == 2
    assert [item.launch_id for item in ledger.entries()] == ["a"]
    assert ledger.has_launch("a")
    assert not ledger.has_launch("b")


def test_an_absent_ledger_is_empty(tmp_path: Path) -> None:
    """Drill 2's post-condition: no exec, no lines, no error."""
    assert ExecLedger(tmp_path / "nothing").count() == 0


def test_multiple_json_documents_are_all_returned(tmp_path: Path) -> None:
    """§6: "exactly one marker" can only be checked if two are visible."""
    path = tmp_path / "outcome.json"
    path.write_text('{"outcome": "done"}\n  {"outcome": "no_diff"}', encoding="utf-8")

    assert len(read_json_documents(path)) == 2


def test_a_log_tail_is_bounded_and_lenient(tmp_path: Path) -> None:
    """§8.2: the foreman reads ~2KB, and a partial UTF-8 sequence is not an error."""
    path = tmp_path / "run.jsonl"
    path.write_bytes(b"x" * 100 + b"\xff tail")

    tail = read_tail(path, 10)

    assert len(tail) == 10
    assert tail.endswith("tail")


def test_a_wrapper_dir_inside_the_repo_is_refused(tmp_path: Path) -> None:
    """§P1: a `git clean -fdx` must not be able to delete the exec ledger."""
    repo = tmp_path / "repo"
    with pytest.raises(SupervisorConfigError, match="inside repo_root"):
        SupervisorConfig(repo_root=repo, wrapper_root=repo / ".wf", host="lab")


def test_a_relative_path_is_refused(tmp_path: Path) -> None:
    """Every path the wrapper holds is absolute; nothing depends on the cwd."""
    with pytest.raises(SupervisorConfigError, match="absolute"):
        SupervisorConfig(
            repo_root=Path("repo"), wrapper_root=tmp_path / ".wf", host="lab"
        )


def test_git_refuses_a_working_directory_it_does_not_own(tmp_path: Path) -> None:
    """A `clean -f` must not be aimable at an unrelated checkout."""
    repo = make_repo(tmp_path)
    git = make_git(make_config(repo, tmp_path))

    with pytest.raises(GitCommandError, match="outside both"):
        git.run(GitSubcommand.STATUS, cwd=tmp_path.parent)


def test_git_has_no_publishing_subcommand() -> None:
    """Structural, not a convention: the supervisor cannot construct a push."""
    values = {subcommand.value for subcommand in GitSubcommand}

    assert values.isdisjoint({"push", "remote", "fetch", "commit"})


def test_start_time_survives_a_comm_containing_parens(tmp_path: Path) -> None:
    """Field 22 is read after the LAST `)`, because `comm` may contain them."""
    config = make_config(make_repo(tmp_path), tmp_path)
    write_proc_entry(config.proc_root, 4242, start_time=START_TIME)

    assert read_start_time(config, 4242) == START_TIME


def test_a_zombie_counts_as_dead(tmp_path: Path) -> None:
    """An unreaped child keeps its `/proc` entry; it is not still running."""
    config = make_config(make_repo(tmp_path), tmp_path)
    write_proc_entry(config.proc_root, 4243, state="Z")

    proof = prove_liveness(config, handle_for(4243, boot_id=BOOT_ID))

    assert proof.status is Liveness.DEAD
    assert proof.alive is False
    assert proof.zombie is True


def test_a_short_write_still_lands_the_whole_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """m18: `os.write` may write fewer bytes than it was handed.

    Ignoring its return renamed a TRUNCATED record into place — the exact
    half-written file the temp → fsync → rename dance exists to prevent. The
    kernel is emulated here by capping every write at one byte, which is the
    only deterministic way to exhibit a short write.
    """
    real_write = os.write

    def dribble(descriptor: int, data: bytes) -> int:
        return real_write(descriptor, data[:1])

    monkeypatch.setattr(paths_module.os, "write", dribble)
    target = tmp_path / "record.json"

    write_record(target, FLAG)

    assert read_record(target, StaleFlag) == FLAG


def test_an_unreadable_proc_entry_is_indeterminate_not_dead(tmp_path: Path) -> None:
    """B6: only ENOENT/ESRCH mean gone; every other error means "unknown".

    Reading an EACCES or EIO as DEAD closed a live activation §5.6 case 3 and
    let the retry run beside the survivor. A DIRECTORY where `stat` should be
    reproduces a non-ENOENT read failure without needing a permission the test
    runner may or may not be able to drop.
    """
    config = make_config(make_repo(tmp_path), tmp_path)
    (config.proc_root / "4244" / "stat").mkdir(parents=True)

    proof = prove_liveness(config, handle_for(4244, boot_id=BOOT_ID))

    assert proof.status is Liveness.INDETERMINATE
    assert proof.alive is False
    assert proof.read_error is not None


def test_an_unparseable_proc_entry_is_indeterminate_too(tmp_path: Path) -> None:
    """B6: an entry that exists but does not parse is not evidence of death."""
    config = make_config(make_repo(tmp_path), tmp_path)
    entry = config.proc_root / "4245"
    entry.mkdir(parents=True)
    (entry / "stat").write_text("nonsense with no comm marker\n", encoding="utf-8")

    assert prove_liveness(config, handle_for(4245)).status is Liveness.INDETERMINATE


def test_termination_never_claims_death_it_cannot_prove(tmp_path: Path) -> None:
    """B6: an indeterminate handle is not `confirmed_dead`, and is not signalled."""
    config = make_config(make_repo(tmp_path), tmp_path)
    (config.proc_root / "4246" / "stat").mkdir(parents=True)

    proof = terminate(config, handle_for(4246), FrozenClock())

    assert proof.confirmed_dead is False
    assert proof.signals_sent == ()


def test_a_zombie_leader_gets_its_group_killed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M12: the leader's own death does not end its children.

    A zombie leader is the one observation PROVING the process group id has not
    been recycled, so the group is provably ours and its survivors have to go
    before §5.6 recovery resets the tree under them. `terminate` used to return
    `confirmed_dead` here without signalling anything at all.
    """
    config = make_config(make_repo(tmp_path), tmp_path)
    write_proc_entry(config.proc_root, 4247, state="Z")
    signalled: list[tuple[int, int]] = []
    monkeypatch.setattr(
        procfs_module.os, "killpg", lambda pgid, sig: signalled.append((pgid, sig))
    )

    proof = terminate(config, handle_for(4247), FrozenClock())

    assert signalled == [(4247, signal.SIGKILL)]
    assert proof.signals_sent == ("SIGKILL",)
    assert proof.confirmed_dead is True


def test_a_vanished_leader_gets_no_group_signal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M12's boundary: with nothing of ours in the group, the pgid is a guess."""
    config = make_config(make_repo(tmp_path), tmp_path)
    signalled: list[tuple[int, int]] = []
    monkeypatch.setattr(
        procfs_module.os, "killpg", lambda pgid, sig: signalled.append((pgid, sig))
    )

    proof = terminate(config, handle_for(4248), FrozenClock())

    assert signalled == []
    assert proof.confirmed_dead is True


@pytest.mark.proc
def test_a_term_resistant_descendant_dies_when_its_leader_does_not(
    tmp_path: Path,
) -> None:
    """Sol#12: TERM killed the LEADER and the escalation window closed with it.

    §8.1's grace is owed to the process GROUP, and the leader's own death
    proves nothing about the rest of it. `_await_death` used to reap the leader
    as soon as it died, which retired the one `/proc` entry proving `pgid` had
    not been recycled — so no KILL could safely follow, and a descendant that
    ignored TERM kept writing the working tree while §5.6 reset it underneath.

    Here the leader dies on TERM and its grandchild traps it. The grandchild
    has to be gone by the time `terminate` returns.
    """
    repo = make_repo(tmp_path)
    config = make_config(repo, tmp_path, fake_proc=False)
    paths = WrapperPaths(config, "wf-group")
    paths.ensure_activation_dir(ACTIVATION_ID)
    clock = FrozenClock(real_sleep_s=0.2)
    pid_file = tmp_path / "grandchild.pid"
    grandchild_script = (
        f'/bin/sh -c \'trap "" TERM; echo $$ > {pid_file}; '
        "while :; do sleep 0.2; done' &"
    )
    command = RunnerCommand(
        argv=("/bin/sh", "-c", f"{grandchild_script}\nsleep 60\nexit 0\n"),
        env={"PATH": "/usr/bin:/bin"},
        cwd=str(repo),
        log_path=str(paths.log(ACTIVATION_ID)),
        session_id="sess-group",
    )
    handle = ForkBarrierLauncher(
        config,
        paths,
        clock,
        activation_id=ACTIVATION_ID,
        launch_id="group-1",
        plan=SandboxPlan(toolchain_cache=(config.wrapper_root / UV_CACHE_DIRECTORY,)),
        sandbox=SandboxMode.OFF,
    )(command)
    grandchild = int(_await_file(pid_file).strip())
    os.kill(grandchild, 0)  # it is alive, and it is not one of our children

    proof = terminate(config, handle, clock)

    assert _await_death_of(grandchild) is True
    assert "SIGKILL" in proof.signals_sent
    assert proof.confirmed_dead is True


def _await_file(path: Path, timeout_s: float = 10.0) -> str:
    """Wait for a file another process writes, then return its contents."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if path.exists():
            content = path.read_text(encoding="utf-8")
            if content.strip():
                return content
        time.sleep(0.02)
    raise AssertionError(f"{path.name} never appeared")


def _await_death_of(pid: int, timeout_s: float = 10.0) -> bool:
    """Whether a process outside our own children is gone, within the timeout."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, PermissionError):
            return True
        time.sleep(0.02)
    return False
