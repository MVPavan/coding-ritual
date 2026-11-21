"""Spec criteria Open-or-closed held and Lost state (holds)."""

from __future__ import annotations

import pytest

from tests.mirror._harness import ACCOUNT, Mirror

pytestmark = pytest.mark.bd


def publish(m: Mirror, title: str = "Export widgets") -> tuple[str, int]:
    bead = m.create_bead(title)
    assert m.run("outbound").returncode == 0
    return bead, int(m.beads()[bead]["external_ref"].rsplit("/", 1)[1])


def run(m: Mirror, *args: str) -> tuple[str, list[str]]:
    before = len(m.fake.writes())
    proc = m.run(*(args or ("outbound",)))
    assert proc.returncode == 0, proc.stderr
    return str(proc.stdout), [str(w["write"]) for w in m.fake.writes()[before:]]


def state_writes(writes: list[str]) -> list[str]:
    return [w for w in writes if w in ("closeIssue", "reopenIssue")]


def test_held_issue_closed_on_github_is_held_every_run_until_the_bead_agrees(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.edit_issue(number, state="CLOSED")
    for _ in range(2):
        out, writes = run(mirror)
        assert (
            f"held: {bead}: open-or-closed held: #{number} was closed on GitHub" in out
        )
        assert writes == []
    assert mirror.fake.issue(number)["state"] == "CLOSED"

    mirror.bd("close", bead, "--reason", "done")
    out, writes = run(mirror)
    assert "held:" not in out and state_writes(writes) == []
    assert writes == ["addComment"], "agreement is confirmed, then the comment follows"


def test_held_issue_reopened_on_github_is_held_until_the_owner_overwrites(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.bd("close", bead, "--reason", "done")
    run(mirror)
    mirror.fake.edit_issue(number, state="OPEN")
    for _ in range(2):
        out, writes = run(mirror)
        assert f"held: {bead}: open-or-closed held: #{number} was open" in out
        assert writes == []

    out, writes = run(mirror, "overwrite", bead, "state")
    assert writes == ["closeIssue"] and "held:" not in out
    assert mirror.fake.issue(number)["state"] == "CLOSED"
    out, writes = run(mirror)
    assert writes == [] and "held:" not in out


def test_held_collaborator_change_between_write_and_read_back_is_not_confirmed(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.set_fault("collaborator_after_write", {"closeIssue": {"state": "OPEN"}})
    mirror.bd("close", bead, "--reason", "done")
    out, writes = run(mirror)
    assert writes == ["closeIssue"]
    assert (
        f"held: {bead}: open-or-closed held: #{number} was set closed but reads back open"
        in out
    )
    assert mirror.state()["enrolled"][bead]["confirmed"] is None
    assert mirror.fake.comments(number) == []

    out, writes = run(mirror)
    assert writes == [] and f"held: {bead}" in out
    assert mirror.fake.issue(number)["state"] == "OPEN"


def test_held_interrupted_read_back_confirms_nothing_and_the_next_run_settles(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.set_fault("interrupt_readback", True)
    mirror.bd("close", bead, "--reason", "done")
    proc = mirror.run("outbound")
    assert proc.returncode == 5 and "read-back" in proc.stderr
    assert mirror.state()["enrolled"][bead]["confirmed"] == "OPEN"
    assert mirror.fake.comments(number) == []

    out, writes = run(mirror)
    assert writes == ["addComment"] and "held:" not in out
    assert mirror.state()["enrolled"][bead]["confirmed"] == "CLOSED"


def test_lost_state_holds_every_open_or_closed_that_differs_and_reports_it(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    closed_bead, first = publish(mirror, "Closed in Beads")
    open_bead, second = publish(mirror, "Open in Beads")
    same, _ = publish(mirror, "Agrees")
    (mirror.mirror_dir / "state.json").unlink()
    mirror.bd("close", closed_bead, "--reason", "done")
    mirror.fake.edit_issue(second, state="CLOSED")

    out, writes = run(mirror)
    assert f"held: {closed_bead}: open-or-closed held: #{first} is open" in out
    assert f"held: {open_bead}: open-or-closed held: #{second} is closed" in out
    assert f"held: {same}" not in out
    assert "createIssue" not in writes and state_writes(writes) == []
    assert len(mirror.fake.issues()) == 3
    out, writes = run(mirror)
    assert writes == [] and out.count("open-or-closed held") == 2


def test_lost_state_finds_the_posted_closing_comment_and_posts_no_second(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.bd("close", bead, "--reason", "done")
    run(mirror)
    (mirror.mirror_dir / "state.json").unlink()
    out, writes = run(mirror)
    assert writes == [] and "held:" not in out
    assert [c["author"] for c in mirror.fake.comments(number)] == [ACCOUNT]


@pytest.mark.parametrize("title_overwrite", [False, True], ids=["retry", "overwrite"])
def test_held_interrupted_close_read_back_then_a_reopen_on_github_is_held_not_reclosed(
    mirror: Mirror, title_overwrite: bool
) -> None:
    """With ``overwrite``, a title-only overwrite before the retry sends no state, so it
    must not erase the unconfirmed close the retry judges."""
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.set_fault("interrupt_readback", True)
    mirror.bd("close", bead, "--reason", "done")
    assert mirror.run("outbound").returncode == 5
    mirror.fake.edit_issue(number, state="OPEN")  # a collaborator reopens it
    if title_overwrite:
        mirror.fake.edit_issue(number, title="Edited on GitHub")
        _, writes = run(mirror, "overwrite", bead, "title")
        assert writes == ["updateIssue"]
        assert mirror.fake.issue(number)["title"] == "Export widgets"
    for _ in range(2):
        out, writes = run(mirror)
        assert writes == [] and f"held: {bead}: open-or-closed held: #{number}" in out
    assert mirror.fake.issue(number)["state"] == "OPEN"
    assert mirror.fake.comments(number) == []


def test_held_overwrite_of_one_component_writes_only_that_component(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.edit_issue(number, title="Edited on GitHub")
    mirror.bd("close", bead, "--reason", "done")
    _, writes = run(mirror, "overwrite", bead, "title")
    assert writes == ["updateIssue"]
    issue = mirror.fake.issue(number)
    assert issue["title"] == "Export widgets" and issue["state"] == "OPEN"
    assert mirror.fake.comments(number) == []


@pytest.mark.parametrize(
    "failing, error",
    [
        ("updateIssue", "rate_limited_429"),
        ("updateIssue", "bad_gateway"),
        ("closeIssue", "rate_limited_429"),
    ],
)
def test_held_only_for_a_close_that_was_sent_not_one_a_failed_run_never_sent(
    mirror: Mirror, failing: str, error: str
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.bd("update", bead, "--title", "Export widgets v2")
    mirror.bd("close", bead, "--reason", "done")
    mirror.fake.set_fault("fail_write", {failing: error})
    assert mirror.run("outbound").returncode == 5
    assert mirror.fake.issue(number)["state"] == "OPEN"
    mirror.fake.set_fault("fail_write", None)

    out, writes = run(mirror)
    assert "held:" not in out and state_writes(writes) == ["closeIssue"]
    assert mirror.fake.issue(number)["state"] == "CLOSED"
    assert mirror.fake.issue(number)["title"] == "Export widgets v2"
    assert len(mirror.fake.comments(number)) == 1
