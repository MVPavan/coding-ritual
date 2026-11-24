"""Spec criterion Close, plus the carried case: two distinct closes with the same stored
time and reason.

The rule for that case: the key is what the spec names (bead, the close time Beads
recorded, the reason's hash), so two closes Beads records identically share one key
and the second posts nothing; the comment already there states that reason and time.
"""

from __future__ import annotations

import hashlib

import pytest

from tests.mirror._harness import ACCOUNT, Mirror

pytestmark = pytest.mark.bd


def key_of(m: Mirror, bead: str) -> str:
    """The closing comment's key as the command documents it, for a copied-key comment."""
    row = m.beads()[bead]
    digest = hashlib.sha256(str(row.get("close_reason") or "").encode()).hexdigest()
    return f"<!-- bead-mirror close bead={bead} at={row['closed_at']} reason={digest[:16]} -->"


def publish(m: Mirror, title: str = "Export widgets") -> tuple[str, int]:
    bead = m.create_bead(title)
    assert m.run("outbound").returncode == 0
    return bead, int(m.beads()[bead]["external_ref"].rsplit("/", 1)[1])


def ok(m: Mirror, *args: str) -> str:
    proc = m.run(*(args or ("outbound",)))
    assert proc.returncode == 0, proc.stderr
    return str(proc.stdout)


def mirror_comments(m: Mirror, number: int) -> list[str]:
    return [c["body"] for c in m.fake.comments(number) if c["author"] == ACCOUNT]


def test_close_closes_the_issue_then_posts_the_reason_once_and_a_rerun_adds_none(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.bd("close", bead, "--reason", "Shipped; thanks @alice")
    ok(mirror)
    issue = mirror.fake.issue(number)
    assert issue["state"] == "CLOSED"
    (comment,) = mirror_comments(mirror, number)
    assert (
        comment == key_of(mirror, bead) + "\nClosed in Beads: Shipped; thanks `@alice`"
    )
    order = [w["write"] for w in mirror.fake.writes()]
    assert order.index("closeIssue") < order.index("addComment")

    writes = len(mirror.fake.writes())
    ok(mirror)
    assert len(mirror.fake.writes()) == writes, "a rerun adds none"


def test_close_reason_failing_the_screen_is_posted_as_closed_in_beads(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.bd("close", bead, "--reason", "Fixed on 10.0.0.12:8080")
    out = ok(mirror)
    assert "close reason holds a private IP address" in out
    (comment,) = mirror_comments(mirror, number)
    assert comment.endswith("\nClosed in Beads.") and "10.0.0.12" not in comment


def test_close_reopen_and_second_close_add_one_more_even_in_the_same_second(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.bd("close", bead, "--reason", "first")
    ok(mirror)
    at = mirror.beads()[bead]["closed_at"]

    mirror.bd("reopen", bead)
    ok(mirror)
    assert mirror.fake.issue(number)["state"] == "OPEN"
    mirror.import_row(bead, status="closed", closed_at=at, close_reason="second")
    ok(mirror)  # the same recorded second, a different reason
    assert mirror.fake.issue(number)["state"] == "CLOSED"
    assert [c.split("\n")[1] for c in mirror_comments(mirror, number)] == [
        "Closed in Beads: first",
        "Closed in Beads: second",
    ]

    mirror.bd("reopen", bead)
    ok(mirror)
    mirror.import_row(
        bead, status="closed", closed_at="2030-01-01T00:00:00Z", close_reason="second"
    )
    ok(mirror)  # a different time, the same reason
    assert len(mirror_comments(mirror, number)) == 3
    writes = len(mirror.fake.writes())
    ok(mirror)
    assert len(mirror.fake.writes()) == writes


def test_close_two_distinct_closes_with_the_same_stored_time_and_reason_post_one_comment(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.bd("close", bead, "--reason", "done")
    ok(mirror)
    row = mirror.beads()[bead]

    mirror.bd("reopen", bead)
    ok(mirror)
    mirror.import_row(
        bead, status="closed", closed_at=row["closed_at"], close_reason="done"
    )
    ok(mirror)
    assert mirror.fake.issue(number)["state"] == "CLOSED", "the state still converges"
    assert mirror_comments(mirror, number) == [
        key_of(mirror, bead) + "\nClosed in Beads: done"
    ]


def test_close_collaborator_comment_copying_the_key_does_not_suppress_it(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.bd("close", bead, "--reason", "done")
    mirror.fake.add_comment(
        number, "alice", key_of(mirror, bead) + "\nClosed in Beads: done"
    )
    ok(mirror)
    assert len(mirror_comments(mirror, number)) == 1
    assert len(mirror.fake.comments(number)) == 2


def test_close_comment_waits_while_the_comments_cannot_all_be_read(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    for n in range(3):
        mirror.fake.add_comment(number, "alice", f"comment {n}")
    mirror.fake.set_fault("comments_page_size", 1)
    mirror.fake.set_fault("failed_comments_page", 2)
    mirror.bd("close", bead, "--reason", "done")
    out = ok(mirror)
    assert mirror.fake.issue(number)["state"] == "CLOSED"
    assert (
        "closing comment on #1 waits" in out and mirror_comments(mirror, number) == []
    )

    mirror.fake.set_fault("failed_comments_page", None)
    ok(mirror)
    ok(mirror)
    assert len(mirror_comments(mirror, number)) == 1
    assert [w["write"] for w in mirror.fake.writes()].count("closeIssue") == 1


def test_close_comment_that_waited_is_posted_once_github_reports_no_update(
    mirror: Mirror,
) -> None:
    """A closed bead awaiting its comment is touched on every run, even when neither
    Beads nor GitHub reports a change since the checkpoint."""
    mirror.write_switch()
    bead, number = publish(mirror)
    for n in range(3):
        mirror.fake.add_comment(number, "alice", f"comment {n}")
    mirror.fake.set_fault("comments_page_size", 1)
    mirror.fake.set_fault("failed_comments_page", 2)
    mirror.bd("close", bead, "--reason", "done")
    ok(mirror)
    assert mirror_comments(mirror, number) == []

    mirror.fake.set_fault("failed_comments_page", None)
    mirror.fake.edit_issue(number, updated_at="2000-01-01T00:00:00Z")
    state = mirror.state()
    state["checkpoints"]["outbound"] = "2099-01-01T00:00:00Z"
    mirror.save_state(state)
    ok(mirror)
    assert len(mirror_comments(mirror, number)) == 1


def test_close_comment_is_not_posted_on_an_issue_reopened_while_it_waited(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    for n in range(3):
        mirror.fake.add_comment(number, "alice", f"comment {n}")
    mirror.fake.set_fault("comments_page_size", 1)
    mirror.fake.set_fault("failed_comments_page", 2)
    mirror.bd("close", bead, "--reason", "done")
    assert "closing comment on #1 waits" in ok(mirror)

    mirror.fake.set_fault("failed_comments_page", None)
    mirror.fake.edit_issue(number, state="OPEN")  # a collaborator reopens it
    out = ok(mirror)
    assert f"held: {bead}: open-or-closed held" in out
    assert mirror_comments(mirror, number) == []
    assert mirror.fake.issue(number)["state"] == "OPEN"


def test_close_comment_github_dropped_is_not_recorded_and_is_posted_on_retry(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.set_fault("drop_write", ["addComment"])
    mirror.bd("close", bead, "--reason", "done")
    out = ok(mirror)
    assert "closing comment" in out and mirror_comments(mirror, number) == []
    assert mirror.state()["enrolled"][bead].get("comment_key") is None

    mirror.fake.set_fault("drop_write", None)
    ok(mirror)
    ok(mirror)
    assert len(mirror_comments(mirror, number)) == 1


def test_close_comment_key_on_a_later_page_is_found_when_a_page_is_malformed(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.add_comment(number, "alice", "first!")
    mirror.bd("close", bead, "--reason", "done")
    ok(mirror)
    saved = mirror.state()
    saved["enrolled"][bead]["comment_key"] = None  # its record was lost
    mirror.save_state(saved)
    mirror.fake.set_fault("comments_page_size", 1)
    mirror.fake.set_fault("malformed_comments_page", 1)
    assert "closing comment on #1 waits" in ok(mirror)
    assert len(mirror_comments(mirror, number)) == 1

    mirror.fake.set_fault("malformed_comments_page", None)
    ok(mirror)
    assert len(mirror_comments(mirror, number)) == 1
    assert mirror.state()["enrolled"][bead]["comment_key"] == key_of(mirror, bead)


@pytest.mark.parametrize(
    ("error", "cause"),
    [
        ("rate_limited_429", "rate limit"),
        ("unauthenticated", "not authenticated"),
        ("offline", "cannot reach"),
        # GraphQL's own rate limit: no HTTP status in gh's message, whatever its exit.
        ("graphql_rate_limited", "rate limit"),
        ("graphql_rate_limited_exit_0", "rate limit"),
        # ...also when it comes with partial data and a field path.
        ("graphql_rate_limited_partial", "rate limit"),
        ("graphql_rate_limited_partial_exit_0", "rate limit"),
    ],
)
def test_close_late_github_failure_exits_non_zero_with_the_cause_and_the_comment_waits(
    mirror: Mirror, error: str, cause: str
) -> None:
    mirror.write_switch()
    bead, number = publish(mirror)
    mirror.fake.set_fault("fail_query", {"MirrorComments": error})
    mirror.bd("close", bead, "--reason", "done")
    proc = mirror.run("outbound")
    assert proc.returncode == 5 and cause in proc.stderr, proc.stderr
    assert mirror.fake.issue(number)["state"] == "CLOSED"
    assert mirror.state()["enrolled"][bead]["confirmed"] == "CLOSED"
    assert mirror_comments(mirror, number) == []

    mirror.fake.set_fault("fail_query", None)
    ok(mirror)
    assert len(mirror_comments(mirror, number)) == 1
    assert [w["write"] for w in mirror.fake.writes()].count("closeIssue") == 1
