"""Spec criterion Failures (manual runs) and the fake gh's own contract."""

from __future__ import annotations

import json
import subprocess
from typing import Any

import pytest

from tests.mirror._harness import HOST, Mirror

pytestmark = pytest.mark.bd

FAULTS: list[tuple[str, Any, str]] = [
    ("unauthenticated", True, "not authenticated"),
    ("rate_limited", 403, "rate limit"),
    ("rate_limited", 429, "rate limit"),
    ("offline", True, "cannot reach"),
]


@pytest.mark.parametrize("args", [["outbound"], ["outbound", "--dry-run"]])
@pytest.mark.parametrize(("fault", "value", "cause"), FAULTS)
def test_failures_manual_run_exits_non_zero_with_the_cause(
    mirror: Mirror, args: list[str], fault: str, value: Any, cause: str
) -> None:
    mirror.write_switch()
    mirror.fake.set_fault(fault, value)
    before = mirror.store_snapshot()
    proc = mirror.run(*args)
    assert proc.returncode == 5
    assert cause in proc.stderr and HOST in proc.stderr
    assert proc.stdout == ""
    assert "state.json" not in mirror.mirror_files()
    assert mirror.fake.writes() == []
    assert mirror.store_snapshot() == before


@pytest.mark.parametrize("args", [["outbound"], ["outbound", "--dry-run"]])
def test_failures_gh_missing_exits_non_zero_with_the_cause(
    mirror: Mirror, args: list[str]
) -> None:
    mirror.write_switch()
    before = mirror.store_snapshot()
    proc = mirror.run(*args, gh_on_path=False)
    assert proc.returncode == 5 and "gh not found" in proc.stderr
    assert "state.json" not in mirror.mirror_files()
    assert mirror.fake.calls() == []
    assert mirror.store_snapshot() == before


def run_fake(
    m: Mirror, *args: str, stdin: str | None = None
) -> subprocess.CompletedProcess[str]:
    feed: dict[str, Any] = (
        {"stdin": subprocess.DEVNULL} if stdin is None else {"input": stdin}
    )
    return subprocess.run(
        [str(m.bin_dir / "gh"), *args],
        env=m.env(),
        capture_output=True,
        text=True,
        check=False,
        **feed,
    )


UPDATED = (
    "query MirrorUpdated($id: ID!, $creator: String!, $since: DateTime!,"
    " $first: Int!, $after: String) {"
    " node(id: $id) { ... on Repository {"
    " issues(first: $first, after: $after,"
    " filterBy: {createdBy: $creator, since: $since}, states: [OPEN, CLOSED]) {"
    " nodes { id number } pageInfo { hasNextPage endCursor } } } } }"
)
MALFORMED_GRAPHQL = [
    # A misspelt filter argument: GitHub rejects it; the fake must not serve it.
    UPDATED.replace("since: $since", "typo: $since"),
    # A variable bound to the wrong argument.
    UPDATED.replace(
        "createdBy: $creator, since: $since", "createdBy: $since, since: $creator"
    ),
    # A selected field the hosted API does not have.
    UPDATED.replace("nodes { id number }", "nodes { id numbr }"),
    # A mutation with an input field its input type does not have.
    "mutation($input: CloseIssueInput!) { closeIssue(input: $input) { issue { id } } }",
]


def test_fake_gh_fails_any_unrecorded_call(mirror: Mirror) -> None:
    unserved = [
        ["api", "--hostname", HOST, "repos/acme/widgets/issues"],
        ["api", "user"],
        ["api", "--hostname", "evil.example", "user"],
        ["api", "--hostname", HOST, "--method", "DELETE", "repos/acme/widgets"],
        ["issue", "list"],
    ]
    for argv in unserved:
        proc = run_fake(mirror, *argv)
        assert proc.returncode == 99 and "unrecognised call" in proc.stderr
    graphql = ["api", "--hostname", HOST, "graphql", "--input", "-"]
    variables = {
        "id": "R_kgDOAcmeW1",
        "creator": "mirror-bot",
        "since": "2026-01-01T00:00:00Z",
        "first": 100,
        "after": None,
        "input": {"issueId": "I_kwDOx1", "stateReason": "COMPLETED"},
    }
    for query in MALFORMED_GRAPHQL:
        body = json.dumps({"query": query, "variables": variables})
        proc = run_fake(mirror, *graphql, stdin=body)
        assert proc.returncode == 99 and "unrecognised call" in proc.stderr, query
    state = mirror.fake.load()
    assert [u["argv"] for u in state["unrecognised"]] == unserved + [graphql] * len(
        MALFORMED_GRAPHQL
    )
    state["unrecognised"] = []  # cleared so the fixture's own empty-log check passes
    mirror.fake.save(state)


@pytest.mark.parametrize(
    ("status", "header"), [(403, "X-Ratelimit-Remaining: 0"), (429, "Retry-After: 60")]
)
def test_fake_gh_rate_limit_carries_the_rate_headers(
    mirror: Mirror, status: int, header: str
) -> None:
    mirror.fake.set_fault("rate_limited", status)
    proc = run_fake(mirror, "api", "--hostname", HOST, "--include", "user")
    assert proc.returncode == 1 and f"(HTTP {status})" in proc.stderr
    assert header in proc.stdout and "X-Ratelimit-Reset:" in proc.stdout
