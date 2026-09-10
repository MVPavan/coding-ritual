"""Focused proof for phase-bridge admission and recovery."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests._fake_bd import FakeBd, InjectedCrash
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bridge import (
    AdmissionRefused,
    BridgeRoot,
    PhaseAdapter,
    PhaseAdmission,
    PhaseBridgeRecord,
    PhaseBridgeState,
)

EPIC_ID = "phase-1"
STAGE_ID = "stage-a"
TARGET_REF = "refs/heads/main"
BASE_COMMIT = "a" * 40


def _stage_row() -> dict[str, object]:
    """Build the direct-child stage the bridge is allowed to admit."""
    return {
        "id": STAGE_ID,
        "title": "one stage",
        "status": "open",
        "issue_type": "task",
        "metadata": {"unrelated": {"preserved": True}},
        "parent": EPIC_ID,
    }


def test_attempt_key_is_stable_and_distinct_per_attempt() -> None:
    """Keep a recovered attempt on its recorded root identity."""
    first = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )
    retry = first.next_attempt()

    assert first.instance_key == "phase-bridge:phase-1:stage-a:attempt:1"
    assert retry.instance_key == "phase-bridge:phase-1:stage-a:attempt:2"
    assert retry.previous_attempts == (first.instance_key,)


def test_adapter_writes_the_whole_record_then_claims_with_admission(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """Keep the stage journal complete across the prepare-to-admit boundary."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=BASE_COMMIT,
    )

    adapter.prepare(STAGE_ID, prepared)
    admitted = adapter.admit(STAGE_ID, prepared, root_id="wf-1")

    assert admitted.state is PhaseBridgeState.ADMITTED
    assert fake_bd.rows[STAGE_ID]["status"] == "in_progress"
    assert fake_bd.rows[STAGE_ID]["metadata"] == {
        "unrelated": {"preserved": True},
        "phase_bridge": admitted.model_dump(by_alias=True, mode="json"),
    }
    assert "--claim" in fake_bd.calls[-2][1]
    assert fake_bd.metadata_writes[-2]["phase_bridge"] == admitted.model_dump(
        by_alias=True, mode="json"
    )
    assert adapter.dependencies(STAGE_ID) == ()


class _Roots:
    """Script the root and branch seams around a real temporary Git history."""

    def __init__(self, fake_client: BdClient, repo: Path, base: str) -> None:
        self._client = fake_client
        self._repo = repo
        self._base = base
        self._roots: dict[str, BridgeRoot] = {}
        self._branches: set[str] = set()
        self.fail_branch = False

    def find(self, instance_key: str) -> BridgeRoot | None:
        """Find the root already created for an admission identity."""
        found = self._roots.get(instance_key)
        if found is not None:
            return found
        for row in self._client.list_beads(
            metadata_filters={"instance_key": instance_key}
        ):
            self._client._merge_metadata(row.id, {"root_id": row.id})
            recovered = BridgeRoot(
                root_id=row.id,
                instance_key=instance_key,
                instance_base_commit=str(row.metadata["base"]),
            )
            self._roots[instance_key] = recovered
            return recovered
        return None

    def create(self, instance_key: str) -> BridgeRoot:
        """Create one fake root through the real bd transport seam."""
        root = self._client._create_bead(
            title="phase root",
            metadata={"instance_key": instance_key, "base": self._base},
        )
        self._client._merge_metadata(root.id, {"root_id": root.id})
        created = BridgeRoot(
            root_id=root.id,
            instance_key=instance_key,
            instance_base_commit=self._base,
        )
        self._roots[instance_key] = created
        return created

    def ensure_branch(self, root: BridgeRoot) -> None:
        """Recreate an instance branch from the persisted root base."""
        if self.fail_branch:
            self.fail_branch = False
            raise InjectedCrash("branch creation died")
        if root.root_id not in self._branches:
            subprocess.run(
                ["git", "update-ref", f"refs/wf/{root.root_id}", self._base],
                cwd=self._repo,
                check=True,
                capture_output=True,
            )
            self._branches.add(root.root_id)


def _temporary_repo(tmp_path: Path) -> tuple[Path, str]:
    """Create the real Git history admission recovery must not reinterpret."""
    repo = tmp_path / "bridge-repo"
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "bridge@example.test"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Bridge Test"],
        check=True,
    )
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "--quiet", "-m", "base"], check=True
    )
    base = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return repo, base


def test_admission_recovers_after_root_creation_crash(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Resume one prepared intent instead of creating a second root."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: base)
    fake_bd.crash_on("create")

    with pytest.raises(InjectedCrash, match="bd create died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert recovered.state is PhaseBridgeState.ADMITTED
    assert fake_bd.command_count("create") == 2
    assert len(roots._roots) == 1
    assert fake_bd.rows[STAGE_ID]["metadata"]["phase_bridge"] == recovered.model_dump(
        by_alias=True, mode="json"
    )


def test_admission_repairs_a_root_interrupted_before_its_self_link(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Reuse the one raw root left between create and self-link."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: base)
    fake_bd.crash_on("update", occurrence=2)

    with pytest.raises(InjectedCrash, match="bd update died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    found = roots.find(recovered.instance_key)
    assert found is not None
    assert recovered.root_id == found.root_id
    assert fake_bd.command_count("create") == 1


def test_admission_reuses_a_root_when_branch_creation_is_interrupted(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Restore the branch from the root base without rereading coordinator HEAD."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    roots.fail_branch = True
    head = [base]
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: head[0])

    with pytest.raises(InjectedCrash, match="branch creation died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)
    head[0] = "b" * 40

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert recovered.state is PhaseBridgeState.ADMITTED
    assert fake_bd.command_count("create") == 1
    assert f"refs/wf/{recovered.root_id}" in {
        line.strip()
        for line in subprocess.run(
            ["git", "for-each-ref", "--format=%(refname)"],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    }


def test_admission_recovers_after_the_relation_write_is_interrupted(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Finish the stage relation without manufacturing another root."""
    fake_bd.rows[STAGE_ID] = _stage_row()
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    prepared_root = roots.create("phase-bridge:phase-1:stage-a:attempt:1")
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: base)
    fake_bd.crash_on("update", occurrence=2)

    with pytest.raises(InjectedCrash, match="bd update died"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    recovered = admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert recovered.root_id == prepared_root.root_id
    assert fake_bd.command_count("create") == 1


def test_conflicting_record_refuses_without_creating_a_root(
    fake_bd: FakeBd, fake_client: BdClient, tmp_path: Path
) -> None:
    """Leave ambiguous identity for a human instead of opening another journal."""
    conflicting = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit="c" * 40,
    )
    stage = _stage_row()
    stage["metadata"] = {"phase_bridge": conflicting.model_dump(by_alias=True)}
    fake_bd.rows[STAGE_ID] = stage
    repo, base = _temporary_repo(tmp_path)
    roots = _Roots(fake_client, repo, base)
    admission = PhaseAdmission(PhaseAdapter(fake_client), roots, lambda: base)

    with pytest.raises(AdmissionRefused, match="identity conflicts"):
        admission.admit(EPIC_ID, STAGE_ID, TARGET_REF, base)

    assert fake_bd.command_count("create") == 0
