"""Spec criteria Create, Store change and Lost state (no duplicate)."""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from typing import Any

import pytest

from tests.mirror._harness import ACCOUNT, Mirror, banner

pytestmark = pytest.mark.bd


def state(m: Mirror) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((m.mirror_dir / "state.json").read_text())
    return data


def lose_the_create(m: Mirror, lag: int) -> None:
    m.fake.set_fault("lose_create_response", True)
    m.fake.set_fault("listing_lag", lag)


def test_create_killed_after_github_created_is_adopted_once_even_if_closed(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    mirror.fake.set_fault("hang_after_create", 5)
    run = mirror.run("outbound", background=True)
    deadline = time.monotonic() + 30
    while not mirror.fake.issues() and time.monotonic() < deadline:
        time.sleep(0.05)
    run.kill()
    run.wait(timeout=10)
    assert bead in state(mirror)["pending"], "the attempt was durable before the create"
    assert mirror.beads()[bead].get("external_ref") is None

    mirror.fake.set_fault("hang_after_create", 0)
    (issue,) = mirror.fake.issues()
    mirror.fake.set_issue_state(issue["number"], "CLOSED")
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert f"adopted #{issue['number']}" in proc.stdout
    assert mirror.fake.creates() == 1 and len(mirror.fake.issues()) == 1
    assert mirror.beads()[bead]["external_ref"].endswith(f"/issues/{issue['number']}")
    assert state(mirror)["pending"] == {}


@pytest.mark.parametrize(
    ("fault", "value"),
    [
        ("lose_create_response", True),
        ("error_after_create", True),
        # A selected field failed after the create: a mutation path and an error code.
        ("error_after_create", "field_error_after_write"),
        # A pathless coded error that names no parse or validation failure.
        ("error_after_create", "internal_error_after_write"),
    ],
    ids=["lost", "error", "field-error", "internal-error"],
)
def test_create_lost_response_while_listing_lags_is_adopted_without_a_duplicate_even_if_closed(
    mirror: Mirror, fault: str, value: object
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    mirror.fake.set_fault(fault, value)  # created; the reply was lost or an error
    mirror.fake.set_fault("listing_lag", 1)
    mirror.fake.set_fault("close_created", True)  # closed before recovery
    first = mirror.run("outbound")
    assert first.returncode == 5 and "pending create" in first.stderr
    mirror.fake.set_fault(fault, False)

    waiting = mirror.run("outbound")
    assert waiting.returncode == 0 and "waiting for the create" in waiting.stdout
    assert mirror.fake.creates() == 1
    assert mirror.beads()[bead].get("external_ref") is None

    adopted = mirror.run("outbound")
    assert adopted.returncode == 0 and "adopted #1" in adopted.stdout
    assert mirror.fake.creates() == 1
    assert mirror.beads()[bead]["external_ref"].endswith("/issues/1")


def test_create_pending_with_no_match_is_never_resent_and_holds_after_a_day(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    lose_the_create(mirror, lag=1000)
    assert mirror.run("outbound").returncode == 5
    mirror.fake.set_fault("lose_create_response", False)
    assert mirror.run("outbound").returncode == 0
    assert mirror.fake.creates() == 1

    saved = state(mirror)
    saved["pending"][bead]["since"] = "2026-01-01T00:00:00Z"
    (mirror.mirror_dir / "state.json").write_text(json.dumps(saved))
    held = mirror.run("outbound")
    assert held.returncode == 0
    assert f"held: {bead}: create held" in held.stdout and "resolve" in held.stdout
    pr = mirror.run("outbound", "--bead", bead)
    assert pr.returncode == 9 and "create held" in pr.stderr
    assert mirror.fake.creates() == 1

    assert mirror.run("resolve", bead, "--create").returncode == 0
    assert mirror.run("outbound").returncode == 0
    assert mirror.fake.creates() == 2, "only the owner's resolve allows another create"
    assert mirror.beads()[bead]["external_ref"].endswith("/issues/2")


def test_create_copied_banner_from_another_author_is_never_adopted(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    copied = mirror.fake.add_issue("outsider", banner(mirror.project_id, bead) + "\nhi")
    mirror.fake.set_fault("ignore_creator_filter", True)  # the listing shows it too
    refused = mirror.run("resolve", bead, "--adopt", str(copied))
    assert (
        refused.returncode == 9
        and "not a live issue the mirror account created" in refused.stderr
    )

    assert mirror.run("outbound").returncode == 0
    mine = [i for i in mirror.fake.issues() if i["author"] == ACCOUNT]
    assert len(mine) == 1 and mine[0]["number"] != copied
    assert mirror.beads()[bead]["external_ref"].endswith(f"/issues/{mine[0]['number']}")


@pytest.mark.parametrize(
    ("bodies", "resolution"),
    [
        (["{ours}", "{ours}"], "adopt"),
        (["<!-- bead-mirror v1 store=another-store bead={bead} -->"], "create"),
        (["<!-- bead-mirror v1 bead={bead} -->"], "create"),
        (["<!--bead-mirror v1 store={store} bead={bead}-->"], "create"),
        (["A collaborator's note above.\n{ours}"], "create"),
    ],
    ids=["several", "another-store", "missing-store", "not-strict", "off-line-1"],
)
def test_create_several_candidates_or_another_store_hold_until_resolve(
    mirror: Mirror, bodies: list[str], resolution: str
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    ours = banner(mirror.project_id, bead)
    numbers = [
        mirror.fake.add_issue(
            ACCOUNT, b.format(ours=ours, bead=bead, store=mirror.project_id) + "\ntext"
        )
        for b in bodies
    ]
    before = mirror.store_snapshot()
    for _ in range(2):
        proc = mirror.run("outbound")
        assert proc.returncode == 0, proc.stderr
        assert f"held: {bead}: create held" in proc.stdout
        assert all(f"#{n}" in proc.stdout for n in numbers)
    assert mirror.fake.writes() == [] and mirror.store_snapshot() == before

    if resolution == "adopt":
        assert mirror.run("resolve", bead, "--adopt", str(numbers[0])).returncode == 0
        expected = numbers[0]
    else:
        assert mirror.run("resolve", bead, "--create").returncode == 0
        assert mirror.run("outbound").returncode == 0
        expected = max(numbers) + 1
    assert mirror.beads()[bead]["external_ref"].endswith(f"/issues/{expected}")
    after = mirror.run("outbound")
    assert after.returncode == 0 and "held" not in after.stdout
    assert mirror.fake.creates() == (0 if resolution == "adopt" else 1)


def test_create_failed_listing_page_creates_nothing(mirror: Mirror) -> None:
    mirror.write_switch()
    for other in ("ma-other1", "ma-other2"):
        mirror.fake.add_issue(ACCOUNT, banner(mirror.project_id, other))
    bead = mirror.create_bead("Export widgets")
    mirror.fake.set_fault("page_size", 1)
    mirror.fake.set_fault("failed_page", 2)
    before = mirror.store_snapshot()
    proc = mirror.run("outbound")
    assert proc.returncode == 5 and "listing is incomplete" in proc.stderr
    assert mirror.fake.writes() == [] and mirror.store_snapshot() == before
    assert state(mirror)["pending"] == {}

    mirror.fake.set_fault("failed_page", None)
    assert mirror.run("outbound").returncode == 0
    assert mirror.fake.creates() == 1 and mirror.beads()[bead]["external_ref"]


@pytest.mark.parametrize("linked", [True, False], ids=["linked", "link-never-written"])
def test_lost_state_creates_no_duplicate(mirror: Mirror, linked: bool) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    if linked:
        assert mirror.run("outbound").returncode == 0
    else:  # the run that created it died before writing the state or the link
        mirror.fake.add_issue(ACCOUNT, banner(mirror.project_id, bead) + "\ntext")
    (mirror.mirror_dir / "state.json").unlink(missing_ok=True)

    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert len(mirror.fake.issues()) == 1
    assert mirror.fake.creates() == (1 if linked else 0)
    assert mirror.beads()[bead]["external_ref"].endswith("/issues/1")
    assert state(mirror)["enrolled"][bead]["number"] == 1


def test_store_change_does_not_adopt_the_first_stores_issue(
    mirror: Mirror, other_store: tuple[Path, str]
) -> None:
    mirror.write_switch()
    twin = "ma-twin"
    mirror.create_bead("First store's bead", "feature", "--id", twin)
    assert mirror.run("outbound").returncode == 0
    (first,) = mirror.fake.issues()

    shutil.rmtree(mirror.clone / ".beads")
    shutil.copytree(other_store[0] / ".beads", mirror.clone / ".beads", symlinks=True)
    mirror.project_id = other_store[1]
    mirror.create_bead("Second store's bead", "feature", "--id", twin, "--force")
    mirror.write_switch()
    assert mirror.run("outbound").returncode == 4, (
        "the state is bound to the first store"
    )
    assert mirror.run("reset-state").returncode == 0

    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert (
        f"held: {twin}: create held" in proc.stdout
        and f"#{first['number']}" in proc.stdout
    )
    assert mirror.beads()[twin].get("external_ref") is None
    assert mirror.fake.creates() == 1


def test_create_refused_for_one_bead_holds_it_and_creates_the_others(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    poisoned = mirror.create_bead("Poisoned title", "feature", "--id", "ma-aaa")
    good = mirror.create_bead("Short title", "feature", "--id", "ma-zzz")
    long_title = mirror.create_bead("L" * 300, "feature", "--id", "ma-mmm")
    mirror.fake.set_fault("refuse_create_titled", "Poisoned")
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert f"held: {poisoned}: create refused" in proc.stdout
    beads = mirror.beads()
    assert beads[good].get("external_ref") and beads[long_title].get("external_ref")
    assert beads[poisoned].get("external_ref") is None
    assert state(mirror)["pending"] == {}
    (bounded,) = [i["title"] for i in mirror.fake.issues() if i["title"][0] == "L"]
    assert len(bounded) <= 256 and bounded.endswith("L…"), "GitHub's title limit"

    mirror.fake.set_fault("refuse_create_titled", None)
    again = mirror.run("outbound")
    assert again.returncode == 0 and "held" not in again.stdout
    assert mirror.beads()[poisoned].get("external_ref")


@pytest.mark.parametrize(
    "fault",
    ["rate_limited_429", "graphql_rate_limited", "unauthenticated", "offline"],
)
def test_create_rejected_before_github_created_anything_clears_the_attempt(
    mirror: Mirror, fault: str
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    mirror.fake.set_fault("fail_create", fault)  # only createIssue fails
    proc = mirror.run("outbound")
    assert proc.returncode == 5, proc.stderr
    assert state(mirror)["pending"] == {} and mirror.fake.issues() == []

    mirror.fake.set_fault("fail_create", None)
    assert mirror.run("outbound").returncode == 0
    assert mirror.fake.creates() == 1 and len(mirror.fake.issues()) == 1
    assert mirror.beads()[bead]["external_ref"].endswith("/issues/1")


def test_create_whose_label_is_refused_holds_that_bead_and_creates_the_others(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bug = mirror.create_bead("A bug", "bug")
    feature = mirror.create_bead("A feature", "feature")
    mirror.fake.set_fault("refuse_label", "bead-type:bug")
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert f"held: {bug}: create refused" in proc.stdout
    beads = mirror.beads()
    assert beads[feature].get("external_ref") and beads[bug].get("external_ref") is None
    assert state(mirror)["pending"] == {}

    mirror.fake.set_fault("refuse_label", None)
    again = mirror.run("outbound")
    assert again.returncode == 0 and "held" not in again.stdout
    assert mirror.beads()[bug].get("external_ref")


def test_create_resolve_create_refuses_without_a_held_create_or_with_one_live_match(
    mirror: Mirror,
) -> None:
    """Lost state after a create that was never linked: the listing proves the issue is
    the bead's, so `resolve --create` must not release a second create."""
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    mirror.fake.add_issue(ACCOUNT, banner(mirror.project_id, bead) + "\ntext")
    refused = mirror.run("resolve", bead, "--create")
    assert refused.returncode == 9 and "no held create" in refused.stderr

    since = "2026-01-01T00:00:00Z"
    mirror.save_state(
        {"version": 1, "binding": mirror.binding(), "pending": {bead: {"since": since}}}
    )
    refused = mirror.run("resolve", bead, "--create")
    assert refused.returncode == 9 and "resolve --adopt 1" in refused.stderr

    assert mirror.run("outbound").returncode == 0
    assert mirror.fake.creates() == 0 and len(mirror.fake.issues()) == 1
    assert mirror.beads()[bead]["external_ref"].endswith("/issues/1")


@pytest.mark.parametrize("malformed", ["no_has_next", "stuck_cursor"])
def test_create_malformed_listing_page_creates_nothing(
    mirror: Mirror, malformed: str
) -> None:
    """A page that does not say whether another follows, or repeats its cursor, is an
    incomplete listing: the bead's issue on a later page must still be found."""
    mirror.write_switch()
    mirror.fake.add_issue(ACCOUNT, banner(mirror.project_id, "ma-other1"))
    bead = mirror.create_bead("Export widgets")
    mirror.fake.add_issue(ACCOUNT, banner(mirror.project_id, bead) + "\ntext")
    mirror.fake.set_fault("page_size", 1)
    mirror.fake.set_fault("malformed_page", {"page": 1, "kind": malformed})
    proc = mirror.run("outbound")
    assert proc.returncode == 5 and "listing is incomplete" in proc.stderr
    assert (
        mirror.fake.writes() == [] and mirror.beads()[bead].get("external_ref") is None
    )

    mirror.fake.set_fault("malformed_page", None)
    proc = mirror.run("outbound")
    assert proc.returncode == 0 and "adopted #2" in proc.stdout
    assert mirror.fake.creates() == 0


@pytest.mark.parametrize("first_rebuild_fails", [False, True], ids=["clean", "retry"])
def test_lost_state_adopts_the_issue_of_a_bead_closed_since_it_was_created(
    mirror: Mirror, first_rebuild_fails: bool
) -> None:
    """The create succeeded, the run died before linking, the bead closed and the state
    was lost: no bead is eligible for a create, yet the rebuild still finds the issue,
    even when the first rebuild's listing failed and a ``--bead`` run came between."""
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    mirror.fake.add_issue(ACCOUNT, banner(mirror.project_id, bead) + "\ntext")
    mirror.bd("close", bead, "--reason", "done")
    if first_rebuild_fails:
        mirror.fake.set_fault("failed_page", 1)
        failed = mirror.run("outbound")
        assert failed.returncode == 5 and "listing is incomplete" in failed.stderr
        mirror.fake.set_fault("failed_page", None)
        other = mirror.create_bead("Never published", "task")
        mirror.bd("close", other, "--reason", "dropped")
        assert mirror.run("outbound", "--bead", other).returncode == 9
        assert mirror.beads()[bead].get("external_ref") is None
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert "adopted #1" in proc.stdout
    assert f"held: {bead}: open-or-closed held: #1 is open" in proc.stdout
    assert mirror.beads()[bead]["external_ref"].endswith("/issues/1")
    assert state(mirror)["enrolled"][bead]["number"] == 1
    written = [w["write"] for w in mirror.fake.writes()]
    assert "createIssue" not in written and "closeIssue" not in written
