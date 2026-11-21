"""Spec criterion Authority (and the switch and stub contracts around it)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.mirror._harness import ACCOUNT, COMMAND, HOST, REPO_NODE_ID, Mirror

pytestmark = pytest.mark.bd

LATER_STAGES = [
    "supervise",
    "worker",
]


def assert_nothing_written(m: Mirror, before: str) -> None:
    assert m.fake.writes() == []
    assert "state.json" not in m.mirror_files()
    assert m.store_snapshot() == before


@pytest.mark.parametrize(
    "args",
    [
        ["outbound"],
        ["outbound", "--dry-run"],
        ["reset-state"],
        ["inbound"],
        ["worker"],
        ["overwrite"],
        ["outbound", "--bogus"],
    ],
)
def test_authority_no_switch_no_writes_and_no_output(
    mirror: Mirror, args: list[str]
) -> None:
    before = mirror.store_snapshot()
    proc = mirror.run(*args)
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    assert not mirror.mirror_dir.exists()
    assert mirror.fake.calls() == []
    assert mirror.bd_calls() == []
    assert mirror.store_snapshot() == before


def test_authority_checks_pass_dry_run_writes_nothing(mirror: Mirror) -> None:
    mirror.write_switch()
    before = mirror.store_snapshot()
    proc = mirror.run("outbound", "--dry-run")
    assert proc.returncode == 0, proc.stderr
    assert "checks passed" in proc.stdout and "planned writes: none" in proc.stdout
    assert mirror.mirror_files() == ["switch.json"]
    assert_nothing_written(mirror, before)
    assert [c["route"] for c in mirror.fake.calls()] == [
        "GET user",
        "GET repos/OWNER/NAME",
        "graphql MirrorIssues",  # no state yet: the rebuild lists the mirror's issues
    ]


def test_authority_manual_run_binds_state_to_store_repository_and_account(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    before = mirror.store_snapshot()
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    state = json.loads((mirror.mirror_dir / "state.json").read_text())
    assert state["binding"] == {
        "store_project_id": mirror.project_id,
        "repo_node_id": REPO_NODE_ID,
        "account": ACCOUNT,
    }
    assert mirror.fake.writes() == []
    assert mirror.store_snapshot() == before


@pytest.mark.parametrize("args", [["outbound"], ["outbound", "--dry-run"]])
def test_authority_different_beads_store_stops_with_report(
    mirror: Mirror, other_store: tuple[object, str], args: list[str]
) -> None:
    mirror.write_switch(store_project_id=other_store[1])
    before = mirror.store_snapshot()
    proc = mirror.run(*args)
    assert proc.returncode == 4
    assert "different store" in proc.stderr and other_store[1] in proc.stderr
    assert mirror.fake.calls() == []
    assert_nothing_written(mirror, before)


def test_authority_beads_environment_override_is_ignored(
    mirror: Mirror, other_store: tuple[object, str]
) -> None:
    other_dir = str(other_store[0]) + "/.beads"
    override = {"BEADS_DIR": other_dir, "BEADS_DB": other_dir + "/embeddeddolt"}
    mirror.write_switch()
    assert mirror.run("outbound", "--dry-run", extra_env=override).returncode == 0
    # The override names the store the switch now records; the clone's own store still wins.
    mirror.write_switch(store_project_id=other_store[1])
    proc = mirror.run("outbound", extra_env=override)
    assert proc.returncode == 4 and "different store" in proc.stderr
    assert mirror.bd_calls() and all(
        c.endswith("beads_env=0") for c in mirror.bd_calls()
    )


@pytest.mark.parametrize("args", [["outbound"], ["outbound", "--dry-run"]])
def test_authority_wrong_gh_account_stops_with_report(
    mirror: Mirror, args: list[str]
) -> None:
    mirror.write_switch()
    mirror.fake.set("login", "someone-else")
    before = mirror.store_snapshot()
    proc = mirror.run(*args)
    assert proc.returncode == 4
    assert "someone-else" in proc.stderr and ACCOUNT in proc.stderr
    assert_nothing_written(mirror, before)


@pytest.mark.parametrize(
    ("override", "expect"),
    [
        ({"repo_node_id": "R_kgDOSomethingElse"}, "node ID"),
        ({"repo": "acme/missing"}, "not found"),
    ],
)
def test_authority_repository_with_different_node_id_stops_with_report(
    mirror: Mirror, override: dict[str, str], expect: str
) -> None:
    mirror.write_switch(**override)
    before = mirror.store_snapshot()
    proc = mirror.run("outbound")
    assert proc.returncode == 4 and expect in proc.stderr
    assert_nothing_written(mirror, before)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("store_project_id", "another-store"),
        ("repo_node_id", "R_kgDOAnotherRepo"),
        ("account", "another-account"),
    ],
)
def test_authority_state_bound_elsewhere_stops_until_reset_state(
    mirror: Mirror, field: str, value: str
) -> None:
    mirror.write_switch()
    assert mirror.run("outbound").returncode == 0
    state_file = mirror.mirror_dir / "state.json"
    state = json.loads(state_file.read_text())
    state["binding"][field] = value
    state_file.write_text(json.dumps(state))
    stale = state_file.read_bytes()

    for args in (["outbound"], ["outbound", "--dry-run"], ["outbound"]):
        proc = mirror.run(*args)
        assert (
            proc.returncode == 4
            and "reset-state" in proc.stderr
            and value in proc.stderr
        )
        assert state_file.read_bytes() == stale
    assert mirror.fake.writes() == []

    assert mirror.run("reset-state").returncode == 0
    assert not state_file.exists()
    assert mirror.run("outbound").returncode == 0
    assert json.loads(state_file.read_text())["binding"][field] != value


def test_authority_unreadable_state_stops_until_reset_state(mirror: Mirror) -> None:
    mirror.write_switch()
    (mirror.mirror_dir / "state.json").write_text("{not json")
    proc = mirror.run("outbound")
    assert proc.returncode == 4 and "reset-state" in proc.stderr
    assert mirror.run("reset-state").returncode == 0
    assert mirror.run("outbound").returncode == 0


def test_authority_ambient_repository_override_does_not_redirect(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    proc = mirror.run(
        "outbound",
        extra_env={"GH_REPO": "evil/elsewhere", "GH_HOST": "evil.example"},
    )
    assert proc.returncode == 0, proc.stderr
    calls = mirror.fake.calls()
    assert calls and all(c["ambient"] == [] for c in calls)
    assert all(c["argv"][1:3] == ["--hostname", HOST] for c in calls)


@pytest.mark.parametrize(
    "switch",
    ["{not json", json.dumps({"host": HOST}), json.dumps({"repo": "no-slash"})],
)
def test_invalid_switch_stops_with_report(mirror: Mirror, switch: str) -> None:
    mirror.mirror_dir.mkdir()
    (mirror.mirror_dir / "switch.json").write_text(switch)
    proc = mirror.run("outbound", "--dry-run")
    assert proc.returncode == 3 and "switch" in proc.stderr
    assert mirror.fake.calls() == [] and mirror.bd_calls() == []


@pytest.mark.parametrize("command", LATER_STAGES)
def test_later_subcommands_are_stubs_that_fail(mirror: Mirror, command: str) -> None:
    mirror.write_switch()
    proc = mirror.run(command)
    assert proc.returncode == 8 and "not implemented" in proc.stderr
    assert mirror.fake.calls() == []


def test_authority_switch_is_found_with_git_older_than_path_format(
    mirror: Mirror,
) -> None:
    """Git before 2.31 echoes ``--path-format=absolute`` instead of rejecting it."""
    git = mirror.tools_dir / "git"
    real = git.resolve()
    git.unlink()
    git.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = rev-parse ] && [ "$2" = --path-format=absolute ]; then\n'
        f'  echo "$2"; shift 2; exec "{real}" rev-parse "$@"\n'
        "fi\n"
        f'exec "{real}" "$@"\n'
    )
    git.chmod(0o755)
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert mirror.beads()[bead]["external_ref"].endswith("/issues/1")


def test_authority_git_selectors_naming_another_clone_do_not_select_its_switch(
    mirror: Mirror, other_store: tuple[Path, str], tmp_path: Path
) -> None:
    """Run in a clone without a switch while Git's selectors name an opted-in clone:
    the command answers for the clone it runs in (silence, no call), and the reverse
    run still checks its own store."""
    mirror.write_switch()
    plain = tmp_path / "plain"
    shutil.copytree(other_store[0], plain, symlinks=True)
    toward = {"GIT_DIR": str(mirror.clone / ".git"), "GIT_WORK_TREE": str(mirror.clone)}
    before = mirror.store_snapshot()
    proc = subprocess.run(
        [sys.executable, str(COMMAND), "outbound"],
        cwd=plain,
        env=mirror.env(toward),
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")
    assert mirror.fake.calls() == [] and mirror.bd_calls() == []
    assert "state.json" not in mirror.mirror_files()
    assert mirror.store_snapshot() == before

    away = {"GIT_DIR": str(plain / ".git"), "GIT_WORK_TREE": str(plain)}
    proc = mirror.run("outbound", "--dry-run", extra_env=away)
    assert proc.returncode == 0 and "checks passed" in proc.stdout, proc.stderr
