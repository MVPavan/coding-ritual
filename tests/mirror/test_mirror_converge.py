"""Spec criteria Converge and Outbound (a second run makes no writes), plus the carried
case: a GitHub-only text edit repaired on the next incremental run."""

from __future__ import annotations

import pytest

from tests.mirror._harness import ACCOUNT, REPO_NODE_ID, Mirror, banner

pytestmark = pytest.mark.bd


def publish(m: Mirror, title: str = "Export widgets", *extra: str) -> tuple[str, int]:
    bead = m.create_bead(title, "feature", *extra)
    proc = m.run("outbound")
    assert proc.returncode == 0, proc.stderr
    number = int(m.beads()[bead]["external_ref"].rsplit("/", 1)[1])
    return bead, number


def run_writes(m: Mirror, *args: str) -> list[dict[str, object]]:
    before = len(m.fake.writes())
    proc = m.run("outbound", *args)
    assert proc.returncode == 0, proc.stderr
    return m.fake.writes()[before:]


def test_converge_github_title_and_body_edit_is_replaced_and_other_labels_untouched(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    _, number = publish(mirror, "Export widgets", "-d", "Export as CSV.")
    want = mirror.fake.issue(number)
    assert run_writes(mirror) == [], "a second run makes no writes"

    # Canonically equal: surrounding spaces, CRLF, trailing whitespace. Nothing written.
    mirror.fake.edit_issue(
        number,
        title="  Export widgets \t",
        body=want["body"].replace("\n", "  \r\n") + "\r\n\r\n",
    )
    assert run_writes(mirror) == []

    mirror.fake.edit_issue(
        number,
        title="Export gadgets",
        body="Rewritten by a collaborator",
        labels=["bead-type:feature", "help wanted"],
    )
    writes = run_writes(mirror)
    assert [w["write"] for w in writes] == ["updateIssue"]
    issue = mirror.fake.issue(number)
    assert issue["title"] == want["title"] and issue["body"] == want["body"]
    assert issue["labels"] == ["bead-type:feature", "help wanted"]
    assert run_writes(mirror) == []


def test_converge_type_change_swaps_only_bead_type_labels_one_at_a_time(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.edit_issue(
        number, labels=["Bead-Type:Feature", "bead-type:epic", "help wanted"]
    )
    mirror.bd("update", bead, "--type", "bug")

    writes = run_writes(mirror)
    labels = [w for w in writes if "Label" in str(w["write"])]
    assert sorted(str(w["write"]) for w in labels) == [
        "addLabelsToLabelable",
        "createLabel",
        "removeLabelsFromLabelable",
        "removeLabelsFromLabelable",
    ]
    assert sorted(mirror.fake.issue(number)["labels"]) == [
        "bead-type:bug",
        "help wanted",
    ]
    calls = [c for c in writes if str(c["write"]).endswith("Labelable")]
    assert all(c["subject"] == number and c["label_ids"] == 1 for c in calls)
    assert run_writes(mirror) == []

    # Only the case differs: the label is the bead's, so nothing is written.
    mirror.fake.edit_issue(number, labels=["help wanted", "BEAD-TYPE:BUG"])
    assert run_writes(mirror) == []


def test_converge_value_github_stores_differently_is_not_storable_and_not_rewritten(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    mirror.fake.set_fault("stores_body_as", ["colour", "color"])
    bead, number = publish(mirror, "Paint", "-d", "Pick a colour.")
    # The create reply is the first read-back: already not storable, never rewritten.
    second = mirror.run("outbound")
    assert second.returncode == 0 and mirror.fake.writes()[-1]["write"] == "createIssue"
    assert f"not storable: {bead}: body of #{number}" in second.stdout

    mirror.bd("update", bead, "-d", "Pick a colour and a brush.")
    writes = run_writes(mirror)
    assert [w["write"] for w in writes] == ["updateIssue"]
    assert "a brush" in mirror.fake.issue(number)["body"]
    later = mirror.run("outbound")
    assert later.returncode == 0 and f"not storable: {bead}: body" in later.stdout
    assert run_writes(mirror) == [], "not rewritten on later runs"

    # The owner's overwrite writes it anyway; a new bead value is written once more.
    assert mirror.run("overwrite", bead, "body").returncode == 0
    assert mirror.fake.writes()[-1]["write"] == "updateIssue"
    mirror.bd("update", bead, "-d", "Pick a brush.")
    assert [w["write"] for w in run_writes(mirror)] == ["updateIssue"]
    assert mirror.fake.issue(number)["body"].endswith("Pick a brush.")
    settled = mirror.run("outbound")
    assert "not storable" not in settled.stdout
    assert mirror.state()["enrolled"][bead]["not_storable"] == {}


def test_converge_dropped_write_is_reported_not_storable(mirror: Mirror) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.set_fault("drop_write", ["updateIssue"])
    mirror.fake.edit_issue(number, title="Edited on GitHub")
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert f"{bead}: the title of #{number} is not storable" in proc.stdout
    assert run_writes(mirror) == []
    assert mirror.fake.issue(number)["title"] == "Edited on GitHub"


def test_converge_github_only_edit_is_repaired_on_the_next_incremental_run(
    mirror: Mirror,
) -> None:
    """Carried case: the bead is unchanged; GitHub reporting the issue as updated since
    the checkpoint is what brings it into the run. An issue GitHub does not report as
    updated waits for the full comparison (M2.2)."""
    mirror.write_switch()
    reported, first = publish(mirror, "First")
    quiet, second = publish(mirror, "Second")
    assert mirror.run("outbound").returncode == 0
    state = mirror.state()
    state["checkpoints"]["outbound"] = "2099-01-01T00:00:00Z"  # nothing changed since
    mirror.save_state(state)
    mirror.fake.edit_issue(first, title="Vandalised", updated_at="2099-06-01T00:00:00Z")
    mirror.fake.edit_issue(
        second, title="Also edited", updated_at="2000-01-01T00:00:00Z"
    )

    writes = run_writes(mirror)
    assert [(w["write"], w["subject"]) for w in writes] == [("updateIssue", first)]
    assert mirror.fake.issue(first)["title"] == "First"
    assert mirror.fake.issue(second)["title"] == "Also edited"
    assert "graphql MirrorUpdated" in mirror.fake.routes()
    assert mirror.beads()[reported]["title"] == "First"
    assert mirror.beads()[quiet]["title"] == "Second"


def test_converge_screened_text_update_is_held_and_reported(mirror: Mirror) -> None:
    mirror.write_switch()
    bead, number = publish(mirror, "Export widgets", "-d", "Plain.")
    body = mirror.fake.issue(number)["body"]
    mirror.bd("update", bead, "-d", "Now see /home/alice/notes.txt", "--title", "New")
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert f"held: {bead}: the body update is not published" in proc.stdout
    issue = mirror.fake.issue(number)
    assert issue["body"] == body and issue["title"] == "New"
    assert issue["body"].startswith(banner(mirror.project_id, bead))


def test_converge_beads_edit_is_written_when_github_reports_the_issue_unchanged(
    mirror: Mirror,
) -> None:
    """Outbound touches beads changed in Beads since the checkpoint, whatever GitHub
    reports as updated."""
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.edit_issue(number, updated_at="2000-01-01T00:00:00Z")
    mirror.bd("update", bead, "--title", "Renamed in Beads")
    writes = run_writes(mirror)
    assert [(w["write"], w["subject"]) for w in writes] == [("updateIssue", number)]
    assert mirror.fake.issue(number)["title"] == "Renamed in Beads"


def move_issue(m: Mirror, number: int, to: str | None) -> None:
    """Delete the issue from the switch's repository, or transfer it (same node ID)."""
    data = m.fake.load()
    home = next(r for r in data["repos"] if r["node_id"] == REPO_NODE_ID)
    issue = next(i for i in home["issues"] if i["number"] == number)
    home["issues"].remove(issue)
    if to is not None:
        data["repos"].append(
            {
                "node_id": to,
                "owner": "elsewhere",
                "name": "other",
                "labels": [],
                "issues": [dict(issue, number=1)],
                "pulls": [],
            }
        )
    m.fake.save(data)


@pytest.mark.parametrize("to", [None, "R_kgDOOther1"], ids=["deleted", "transferred"])
def test_converge_issue_gone_from_the_repository_is_left_alone_and_others_still_sync(
    mirror: Mirror, to: str | None
) -> None:
    mirror.write_switch()
    # beads sync in ID order: the gone one first
    pair = sorted([publish(mirror, "Alpha"), publish(mirror, "Beta")])
    (gone, first), (kept, second) = pair
    old = mirror.fake.issue(first)["title"]
    move_issue(mirror, first, to)
    mirror.bd("update", gone, "--title", "Gone renamed")
    mirror.bd("close", gone, "--reason", "done")
    mirror.bd("update", kept, "--title", "Kept renamed")
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert f"{gone}: issue #{first} cannot be read as an issue" in proc.stdout
    assert all(w["repo_node_id"] == REPO_NODE_ID for w in mirror.fake.writes())
    assert mirror.fake.issue(second)["title"] == "Kept renamed"
    if to is not None:
        moved = mirror.fake.issues(to)[0]
        assert moved["title"] == old and moved["state"] == "OPEN"


def test_converge_cached_enrolment_is_linked_only_once_the_issue_is_found_in_the_repository(
    mirror: Mirror,
) -> None:
    """The run that enrolled an issue died before linking it, and the issue was
    transferred before the retry: the cached URL is never written to the bead."""
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    number = mirror.fake.add_issue(ACCOUNT, banner(mirror.project_id, bead) + "\ntext")
    record = {
        "number": number,
        "node_id": mirror.fake.issue(number)["node_id"],
        "url": f"https://github.com/acme/widgets/issues/{number}",
    }
    mirror.save_state(
        {"version": 1, "binding": mirror.binding(), "enrolled": {bead: record}}
    )
    move_issue(mirror, number, "R_kgDOOther1")
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert f"{bead}: issue #{number} cannot be read as an issue" in proc.stdout
    assert mirror.beads()[bead].get("external_ref") is None
    assert mirror.fake.writes() == []
