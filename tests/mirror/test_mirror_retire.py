"""Spec criterion Retire (and Scope: exclusion on an enrolled bead), plus `map`."""

from __future__ import annotations

import pytest

from tests.mirror._harness import Mirror, banner

pytestmark = pytest.mark.bd


def publish(m: Mirror, title: str = "Export widgets") -> tuple[str, int]:
    bead = m.create_bead(title, "feature", "-d", "Body text.")
    assert m.run("outbound").returncode == 0
    return bead, int(m.beads()[bead]["external_ref"].rsplit("/", 1)[1])


def test_retire_marks_the_banner_last_and_is_never_managed_or_adopted_again(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    body = mirror.fake.issue(number)["body"]
    proc = mirror.run("retire", bead)
    assert proc.returncode == 0, proc.stderr
    issue = mirror.fake.issue(number)
    first, rest = issue["body"].split("\n", 1)
    assert first == banner(mirror.project_id, bead, retired=True)
    assert rest == body.split("\n", 1)[1] and issue["state"] == "OPEN"
    assert mirror.fake.writes()[-1]["write"] == "updateIssue"

    writes = len(mirror.fake.writes())
    mirror.bd("update", bead, "--title", "Renamed in Beads")
    mirror.bd("close", bead, "--reason", "done")
    mirror.fake.edit_issue(number, title="Edited on GitHub")
    (mirror.mirror_dir / "state.json").unlink()
    for _ in range(2):
        proc = mirror.run("outbound")
        assert proc.returncode == 0, proc.stderr
    assert len(mirror.fake.writes()) == writes, "not managed again"
    assert mirror.fake.issue(number)["title"] == "Edited on GitHub"
    assert mirror.state()["tracking"] == {bead: number}
    assert mirror.state()["enrolled"] == {}
    adopt = mirror.run("resolve", bead, "--adopt", str(number))
    assert adopt.returncode == 9, "nor adopted"


def test_retire_by_exclusion_on_an_enrolled_bead_leaves_the_issue_as_it_is(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.bd("update", bead, "--set-metadata", "mirror=never", "--title", "New")
    mirror.bd("close", bead, "--reason", "done")
    before = len(mirror.fake.writes())
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert f"{bead}: issue #{number} retired" in proc.stdout
    assert [w["write"] for w in mirror.fake.writes()[before:]] == ["updateIssue"]
    issue = mirror.fake.issue(number)
    assert issue["state"] == "OPEN" and issue["title"] == "Export widgets"
    assert issue["body"].startswith(banner(mirror.project_id, bead, retired=True))
    assert mirror.fake.comments(number) == []


@pytest.mark.parametrize(
    ("fault", "value", "code"),
    [("drop_write", ["updateIssue"], 5), ("fail_write", {"updateIssue": "offline"}, 5)],
    ids=["dropped", "offline"],
)
def test_retire_fails_loudly_and_the_bead_stays_managed_when_the_write_fails(
    mirror: Mirror, fault: str, value: object, code: int
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.set_fault(fault, value)
    proc = mirror.run("retire", bead)
    assert (
        proc.returncode == code
        and "retiring" in proc.stderr
        and "failed" in proc.stderr
    )
    assert bead in mirror.state()["enrolled"] and mirror.state()["tracking"] == {}
    assert mirror.fake.issue(number)["body"].startswith(banner(mirror.project_id, bead))


def test_retire_with_the_state_lost_finds_the_issue_through_the_link(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    (mirror.mirror_dir / "state.json").unlink()
    proc = mirror.run("retire", bead)
    assert proc.returncode == 0, proc.stderr
    assert mirror.fake.issue(number)["body"].startswith(
        banner(mirror.project_id, bead, retired=True)
    )


def test_retire_issue_found_only_by_the_listing_makes_the_bead_tracking_only(
    mirror: Mirror,
) -> None:
    """With the state lost and the bead's link cleared, the retired issue in the
    listing is never adopted and no second issue is created."""
    mirror.write_switch()
    bead, number = publish(mirror)
    assert mirror.run("retire", bead).returncode == 0
    (mirror.mirror_dir / "state.json").unlink()
    mirror.bd("update", bead, "--external-ref", "")
    writes = len(mirror.fake.writes())
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert len(mirror.fake.writes()) == writes and mirror.fake.creates() == 1
    assert mirror.state()["tracking"] == {bead: number}
    assert mirror.state()["enrolled"] == {}


def test_retire_failing_for_one_excluded_bead_is_held_and_the_others_still_sync(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    # beads sync in ID order: the failing retire comes first
    pair = sorted([publish(mirror, "Alpha"), publish(mirror, "Beta")])
    (excluded, first), (other, second) = pair
    body = mirror.fake.issue(first)["body"]
    mirror.fake.edit_issue(first, body="Note from alice\n" + body)  # banner not first
    mirror.bd("update", excluded, "--set-metadata", "mirror=never")
    mirror.bd("update", other, "--title", "Other renamed")
    mirror.bd("close", other, "--reason", "done")
    for _ in range(2):
        proc = mirror.run("outbound")
        assert proc.returncode == 0, proc.stderr
        assert (
            f"held: {excluded}: retiring #{first} for {excluded} failed" in proc.stdout
        )
    issue = mirror.fake.issue(second)
    assert issue["state"] == "CLOSED" and issue["title"] == "Other renamed"
    assert excluded in mirror.state()["enrolled"]

    mirror.fake.edit_issue(first, body=body)  # the banner is first again
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert mirror.state()["tracking"] == {excluded: first}
    assert excluded not in mirror.state()["holds"]


def test_map_prints_bead_and_issue_from_the_state_and_links_without_github(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    enrolled, first = publish(mirror, "Enrolled")
    retired, second = publish(mirror, "Retired")
    assert mirror.run("retire", retired).returncode == 0
    outside = mirror.fake.add_issue("alice", "An outside report")
    linked = mirror.create_bead("Tracked", "task")
    assert (
        mirror.run("link", linked, str(outside), "--actor", "test:triage").returncode
        == 0
    )
    calls = len(mirror.fake.calls())

    proc = mirror.run("map")
    assert proc.returncode == 0, proc.stderr
    url = "https://github.com/acme/widgets/issues/"
    assert f"{enrolled}\t#{first}\t{url}{first}\tenrolled" in proc.stdout
    assert f"{retired}\t#{second}\t{url}{second}\ttracking-only" in proc.stdout
    assert f"{linked}\t#{outside}\t{url}{outside}\tlinked" in proc.stdout
    assert len(mirror.fake.calls()) == calls, "map makes no GitHub call"
