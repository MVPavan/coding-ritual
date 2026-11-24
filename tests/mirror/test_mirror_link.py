"""Spec criterion Link race, and the `link` subcommand's checks."""

from __future__ import annotations

import fcntl
import os

import pytest

from tests.mirror._harness import Mirror

pytestmark = pytest.mark.bd

TRIAGE = "test:triage"


def test_link_race_mirror_link_first_then_triage_link_is_a_conflict(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    assert mirror.run("outbound").returncode == 0
    mine = mirror.beads()[bead]["external_ref"]
    outside = mirror.fake.add_issue("outsider", "a bug report")

    before = mirror.store_snapshot()
    proc = mirror.run("link", bead, str(outside), "--actor", TRIAGE)
    assert (
        proc.returncode == 9 and "link conflict" in proc.stderr and mine in proc.stderr
    )
    assert mirror.store_snapshot() == before


def test_link_race_triage_link_first_then_mirror_link_is_a_conflict(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    mirror.fake.set_fault("lose_create_response", True)
    assert mirror.run("outbound").returncode == 5  # created; the reply was lost
    mirror.fake.set_fault("lose_create_response", False)
    outside = mirror.fake.add_issue("outsider", "a bug report")

    linked = mirror.run("link", bead, str(outside), "--actor", TRIAGE)
    assert linked.returncode == 0, linked.stderr
    theirs = f"https://github.com/acme/widgets/issues/{outside}"
    assert mirror.beads()[bead]["external_ref"] == theirs
    assert any(c.endswith(f"--actor {TRIAGE} beads_env=0") for c in mirror.bd_calls())

    before = mirror.store_snapshot()
    for _ in range(2):
        proc = mirror.run("outbound")
        assert proc.returncode == 0, proc.stderr
        assert f"held: {bead}: link conflict" in proc.stdout and theirs in proc.stdout
    assert mirror.store_snapshot() == before
    assert mirror.fake.creates() == 1


def test_link_names_an_issue_in_the_repository_and_writes_only_an_empty_field(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("A task", "task")
    pull = mirror.fake.add_pull()
    before = mirror.store_snapshot()
    proc = mirror.run("link", bead, str(pull), "--actor", TRIAGE)
    assert proc.returncode == 9 and "pull request" in proc.stderr
    proc = mirror.run("link", bead, "404", "--actor", TRIAGE)
    assert proc.returncode == 9 and "does not exist" in proc.stderr
    assert mirror.store_snapshot() == before

    outside = mirror.fake.add_issue("outsider", "a bug report")
    assert mirror.run("link", bead, str(outside), "--actor", TRIAGE).returncode == 0
    again = mirror.run("link", bead, str(outside), "--actor", TRIAGE)
    assert again.returncode == 0 and "already linked" in again.stdout
    assert mirror.fake.writes() == []

    # A tracking-only link: the mirror never creates a second issue for the bead.
    assert mirror.run("outbound", "--bead", bead).returncode == 0
    assert mirror.fake.creates() == 0


def test_link_checks_two_beads_naming_the_same_issue_are_reported_and_left_alone(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    first = mirror.create_bead("Bead A", "feature")
    second = mirror.create_bead("Bead B", "task")
    assert mirror.run("outbound").returncode == 0
    (issue,) = mirror.fake.issues()
    url = mirror.beads()[first]["external_ref"]

    before = mirror.store_snapshot()
    refused = mirror.run("link", second, str(issue["number"]), "--actor", TRIAGE)
    assert refused.returncode == 9 and first in refused.stderr
    assert mirror.store_snapshot() == before

    mirror.bd("update", second, "--external-ref", url)  # the Beads workflow elsewhere
    linked = mirror.store_snapshot()
    writes = len(mirror.fake.writes())
    for _ in range(2):
        proc = mirror.run("outbound")
        assert proc.returncode == 0, proc.stderr
        assert (
            f"beads {', '.join(sorted([first, second]))} all name issue #{issue['number']}"
            in proc.stdout
        )
    pr = mirror.run("outbound", "--bead", second)
    assert pr.returncode == 9 and first in pr.stderr
    mirror.fake.edit_issue(issue["number"], title="Edited on GitHub")
    for manual in (("overwrite", first), ("retire", first)):
        refused = mirror.run(*manual)
        assert refused.returncode == 9 and second in refused.stderr, manual
    assert len(mirror.fake.writes()) == writes and mirror.store_snapshot() == linked
    assert mirror.fake.issue(issue["number"])["title"] == "Edited on GitHub"
    assert "retired" not in mirror.fake.issue(issue["number"])["body"].split("\n")[0]


def test_link_checks_adoption_never_makes_two_beads_name_one_issue(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    first = mirror.create_bead("Bead A", "feature")
    second = mirror.create_bead("Bead B", "task")
    mirror.fake.set_fault("lose_create_response", True)  # A's create: reply lost
    mirror.fake.set_fault("listing_lag", 1)  # and not listed yet
    assert mirror.run("outbound").returncode == 5
    mirror.fake.set_fault("lose_create_response", False)
    (issue,) = mirror.fake.issues()
    linked = mirror.run("link", second, str(issue["number"]), "--actor", TRIAGE)
    assert linked.returncode == 0, linked.stderr  # triage links B to A's issue

    for _ in range(2):
        proc = mirror.run("outbound")
        assert proc.returncode == 0, proc.stderr
    assert f"held: {first}: create held" in proc.stdout and second in proc.stdout
    assert mirror.beads()[first].get("external_ref") is None
    refused = mirror.run("resolve", first, "--adopt", str(issue["number"]))
    assert refused.returncode == 9 and second in refused.stderr
    assert mirror.beads()[first].get("external_ref") is None
    assert mirror.fake.creates() == 1


def test_link_race_link_waits_for_the_clone_lock(mirror: Mirror) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("A task", "task")
    outside = mirror.fake.add_issue("outsider", "a bug report")
    before = mirror.store_snapshot()
    fd = os.open(mirror.mirror_dir / "lock", os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        busy = mirror.run(
            "--lock-wait", "0.2", "link", bead, str(outside), "--actor", TRIAGE
        )
        assert busy.returncode == 7 and "busy" in busy.stderr
        assert mirror.store_snapshot() == before and mirror.fake.calls() == []
    finally:
        os.close(fd)
    linked = mirror.run("link", bead, str(outside), "--actor", TRIAGE)
    assert linked.returncode == 0, linked.stderr


def test_link_pr_path_refuses_a_link_to_a_pull_request_or_a_missing_issue(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    pull = mirror.fake.add_pull()
    base = "https://github.com/acme/widgets/issues/"
    for number in (pull, 42):
        bead = mirror.create_bead(f"Links #{number}", "task")
        mirror.bd("update", bead, "--external-ref", f"{base}{number}")
        proc = mirror.run("outbound", "--bead", bead)
        assert proc.returncode == 9 and "not tracked" in proc.stderr, proc.stderr
        assert f"{base}{number}" not in proc.stdout
    assert bead not in mirror.state()["tracking"]
    assert mirror.fake.writes() == []


def test_link_checks_a_stale_tracking_entry_makes_no_shared_issue(
    mirror: Mirror,
) -> None:
    """B tracked #1 and is now linked to #2 in Beads; A links #1. Only current links
    count, so neither is left alone and B's tracking moves to #2."""
    mirror.write_switch()
    first = mirror.fake.add_issue("outsider", "a bug report")
    second = mirror.fake.add_issue("outsider", "another bug report")
    a = mirror.create_bead("Bead A", "task")
    b = mirror.create_bead("Bead B", "task")
    assert mirror.run("link", b, str(first), "--actor", TRIAGE).returncode == 0
    assert mirror.run("outbound").returncode == 0
    assert mirror.state()["tracking"] == {b: first}

    base = "https://github.com/acme/widgets/issues/"
    mirror.bd("update", b, "--external-ref", f"{base}{second}")
    mirror.bd("update", a, "--external-ref", f"{base}{first}")
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert "all name issue" not in proc.stdout
    assert mirror.state()["tracking"] == {a: first, b: second}

    # B's link is cleared and #2 assigned to A: B's old entry claims nothing either.
    mirror.bd("update", b, "--external-ref", "")
    mirror.bd("update", a, "--external-ref", f"{base}{second}")
    for _ in range(2):
        proc = mirror.run("outbound")
        assert proc.returncode == 0, proc.stderr
        assert "all name issue" not in proc.stdout
        assert mirror.state()["tracking"][a] == second
    pr = mirror.run("outbound", "--bead", a)
    assert pr.returncode == 0 and pr.stdout.strip().endswith(f"{base}{second}")


def test_link_pr_path_refuses_an_issue_deleted_after_it_was_tracked_or_enrolled(
    mirror: Mirror,
) -> None:
    """A URL the state cached is not reported: the pr path reads the issue fresh."""
    mirror.write_switch()
    outside = mirror.fake.add_issue("outsider", "a bug report")
    tracked = mirror.create_bead("Tracked", "task")
    assert mirror.run("link", tracked, str(outside), "--actor", TRIAGE).returncode == 0
    enrolled = mirror.create_bead("Enrolled")
    for bead in (tracked, enrolled):
        proc = mirror.run("outbound", "--bead", bead)
        assert proc.returncode == 0, proc.stderr
    number = int(mirror.beads()[enrolled]["external_ref"].rsplit("/", 1)[1])

    for bead, gone in ((tracked, outside), (enrolled, number)):
        mirror.fake.delete_issue(gone)
        proc = mirror.run("outbound", "--bead", bead)
        assert proc.returncode == 9 and f"#{gone}" in proc.stderr, proc.stderr
        assert "/issues/" not in proc.stdout.strip().splitlines()[-1]


def test_link_checks_a_retired_bead_whose_link_was_cleared_claims_nothing(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    b = mirror.create_bead("Bead B", "feature", "-d", "Body.")
    assert mirror.run("outbound").returncode == 0
    number = int(mirror.beads()[b]["external_ref"].rsplit("/", 1)[1])
    assert mirror.run("retire", b).returncode == 0
    a = mirror.create_bead("Bead A", "task")
    mirror.bd("update", b, "--external-ref", "")

    link = mirror.run("link", a, str(number), "--actor", TRIAGE)

    assert link.returncode == 0, link.stderr
    assert mirror.beads()[a]["external_ref"].endswith(f"/issues/{number}")
