"""Spec criterion Rename: a repository renamed after the checks, with its old name
taken by another repository, receives every write and the other repository none.

The end-to-end proof is a real create (M1.2); the helper tests show every write goes
through one path that only accepts node IDs.
"""

from __future__ import annotations

import importlib.util
from types import ModuleType

import pytest

from tests.mirror._harness import COMMAND, HOST, REPO_NODE_ID, Mirror

pytestmark = pytest.mark.bd

SQUATTER = "R_kgDOSquatter"


def load_command() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bead_mirror", COMMAND)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def rename_after_checks(m: Mirror) -> None:
    m.fake.set_fault(
        "rename_after_check",
        {
            "repo_node_id": REPO_NODE_ID,
            "new_name": "widgets-renamed",
            "squatter_node_id": SQUATTER,
        },
    )


def test_rename_nothing_after_the_checks_names_the_repository(mirror: Mirror) -> None:
    mirror.write_switch()
    rename_after_checks(mirror)
    proc = mirror.run("outbound", "--dry-run")
    assert proc.returncode == 0, proc.stderr
    calls = mirror.fake.calls()
    assert all(c["argv"][1:3] == ["--hostname", HOST] for c in calls)
    named = [c for c in calls if c["route"] == "GET repos/OWNER/NAME"]
    assert len(named) == 1 and named[0] is calls[1], (
        "only the check names the repository; later calls (the rebuild's listing) use "
        "its node ID"
    )
    assert len(calls) > 2
    assert all(c.get("repo_node_id") != SQUATTER for c in calls)
    assert mirror.fake.load()["faults"]["rename_after_check"]["done"]


def test_rename_create_after_the_checks_reaches_the_renamed_repository(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    bead = mirror.create_bead("Export widgets")
    rename_after_checks(mirror)
    proc = mirror.run("outbound")
    assert proc.returncode == 0, proc.stderr
    assert mirror.fake.load()["faults"]["rename_after_check"]["done"]
    (issue,) = mirror.fake.issues(REPO_NODE_ID)
    assert issue["labels"] == ["bead-type:feature"]
    assert mirror.fake.repo(SQUATTER)["issues"] == []
    assert mirror.fake.repo(SQUATTER)["labels"] == []
    after_check = mirror.fake.calls()[2:]
    assert after_check and all(
        c.get("repo_node_id") == REPO_NODE_ID for c in after_check
    )
    assert mirror.beads()[bead]["external_ref"].endswith(
        "/acme/widgets-renamed/issues/1"
    )


def test_rename_writes_reach_the_renamed_repository_and_not_the_squatter(
    mirror: Mirror,
) -> None:
    mod = load_command()
    switch = mirror.write_switch()
    rename_after_checks(mirror)
    gh = mod.Gh(
        HOST, mod.child_env(mirror.env({"GH_REPO": "acme/widgets", "GH_HOST": HOST}))
    )
    mod.check_github(switch, gh)  # the checks pass; the repository is then renamed

    created = gh.graphql_write(
        "createIssue", REPO_NODE_ID, {"title": "t"}, mod.CREATE_SELECTION
    )
    assert created["issue"]["url"].endswith("/acme/widgets-renamed/issues/1")
    assert [i["title"] for i in mirror.fake.repo(REPO_NODE_ID)["issues"]] == ["t"]
    assert mirror.fake.repo(SQUATTER)["issues"] == []
    assert all(c["ambient"] == [] for c in mirror.fake.calls())


@pytest.mark.parametrize(
    "subject",
    ["acme/widgets", "https://github.com/acme/widgets", "widgets", "acme/widgets#1"],
)
def test_rename_write_helper_accepts_only_node_ids(
    mirror: Mirror, subject: str
) -> None:
    mod = load_command()
    gh = mod.Gh(HOST, mod.child_env(mirror.env()))
    with pytest.raises(ValueError, match="node ID"):
        gh.graphql_write("createIssue", subject, {"title": "t"}, "issue { id }")
    with pytest.raises(ValueError, match="mutation"):
        gh.graphql_write("deleteRepository", REPO_NODE_ID, {}, "clientMutationId")
    assert mirror.fake.calls() == []
