"""Focused proof for phase-bridge admission and recovery."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Final

import pytest

from tests._fake_bd import FakeBd, InjectedCrash
from tests._workspace import Fixture
from tests.conftest import Signer
from workflow_interpreter.bdio import (
    GateArtifact,
    GatePayload,
    GateVerifier,
    canonical_payload_bytes,
)
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.signing import payload_digest
from workflow_interpreter.bridge import (
    AdmissionRefused,
    BridgeRoot,
    DetachedRepositoryGate,
    GateEvidence,
    LandingDisposition,
    LandingHooks,
    LandingIntent,
    PhaseAdapter,
    PhaseAdmission,
    PhaseBridgeRecord,
    PhaseBridgeState,
    PhaseLanding,
    RepositoryGateResult,
)
from workflow_interpreter.bridge.landing import T1_MESSAGE
from workflow_interpreter.schema.models import IsolationMode, Outcome
from workflow_interpreter.supervisor import Git
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.paths import WrapperPaths, write_record
from workflow_interpreter.supervisor.sandbox import SandboxMode

EPIC_ID = "phase-1"
STAGE_ID = "stage-a"
TARGET_REF = "refs/heads/main"
BASE_COMMIT = "a" * 40
ROOT_ID: Final[str] = "bridge-root"


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
    fixture = Fixture(tmp_path, IsolationMode.WORKTREE)
    return fixture.repo, fixture.base


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


class _GateAuthority:
    """Return one already signature-verified immutable ship-gate observation."""

    def __init__(
        self,
        artifact_oid: str,
        tree: str,
        verifier: GateVerifier,
        signer: Signer,
    ) -> None:
        self._artifact_oid = artifact_oid
        self._tree = tree
        self._verifier = verifier
        self._signer = signer
        self.calls = 0

    def verify(self, root_id: str) -> GateEvidence:
        """Describe the closed acceptance whose payload was re-verified upstream."""
        self.calls += 1
        payload = GatePayload(
            graph_id="phase-bridge",
            root_id=root_id,
            gate_key="ship",
            outcome=Outcome.ACCEPT,
            artifact=GateArtifact(commit_oid=self._artifact_oid, tree_oid=self._tree),
            nonce="reverified-ship-gate",
        )
        encoded = canonical_payload_bytes(payload)
        with tempfile.TemporaryDirectory() as directory:
            approval = self._verifier.verify(
                payload_bytes=encoded,
                signature=self._signer(encoded, None),
                work_dir=Path(directory),
            )
        return GateEvidence(
            root_id=root_id,
            gate_node="ship",
            closed=True,
            immutable=True,
            accepted=True,
            artifact_oid=self._artifact_oid,
            tree=self._tree,
            fingerprint=approval.fingerprint,
            digest=payload_digest(encoded),
            artifact_ref=self._artifact_oid,
        )


class _RepositoryGate:
    """Record the real detached tree the injected gate was asked to grade."""

    def __init__(self, artifact_oid: str, tree: str) -> None:
        self._artifact_oid = artifact_oid
        self._tree = tree
        self.calls = 0

    def verify(self, artifact_oid: str, tree: str) -> RepositoryGateResult:
        """Return a complete green receipt for the artifact's real Git identity."""
        self.calls += 1
        assert artifact_oid == self._artifact_oid
        assert tree == self._tree
        return RepositoryGateResult(
            artifact_oid=artifact_oid,
            tree=tree,
            complete=True,
            green=True,
            results=("repository gate green",),
        )


class _CrashAfterCas(LandingHooks):
    """Open the post-CAS crash window without exposing a production fault flag."""

    def after_cas(self) -> None:
        """Interrupt before the landing receipt exists."""
        raise InjectedCrash("post-CAS interruption")


def _commit_artifact(repo: Path) -> tuple[str, str]:
    """Commit an artifact on the temporary repository's real mainline history."""
    subprocess.run(
        ["git", "checkout", "--quiet", "-b", "artifact"], cwd=repo, check=True
    )
    (repo / "artifact.txt").write_text("signed artifact\n", encoding="utf-8")
    subprocess.run(["git", "add", "artifact.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "signed artifact"],
        cwd=repo,
        check=True,
    )
    artifact_oid = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tree = subprocess.run(
        ["git", "rev-parse", f"{artifact_oid}^{{tree}}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "checkout", "--quiet", "main"], cwd=repo, check=True)
    return artifact_oid, tree


def _landing_context(repo: Path, tmp_path: Path) -> tuple[Git, WrapperPaths]:
    """Build the real Git and wrapper-path services for one temporary history."""
    config = SupervisorConfig(
        repo_root=repo,
        wrapper_root=tmp_path / "bridge-wrapper",
        host="bridge-test",
        sandbox=SandboxMode.OFF,
    )
    return Git(config), WrapperPaths(config, ROOT_ID)


def test_post_cas_recovery_closes_only_the_signed_artifact(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """A real-Git post-CAS interruption recovers closure without another ref move."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    admitted = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    ).admitted(ROOT_ID)
    PhaseAdapter(fake_client).prepare(
        STAGE_ID, admitted.model_copy(update={"state": PhaseBridgeState.PREPARED})
    )
    PhaseAdapter(fake_client).admit(
        STAGE_ID,
        admitted.model_copy(update={"state": PhaseBridgeState.PREPARED}),
        root_id=ROOT_ID,
    )
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    git, paths = _landing_context(repo, tmp_path)
    landing = PhaseLanding(
        PhaseAdapter(fake_client),
        git,
        repo,
        paths,
        gate,
        repository_gate,
        hooks=_CrashAfterCas(),
    )

    with pytest.raises(InjectedCrash, match="post-CAS interruption"):
        landing.land(STAGE_ID)

    assert _ref_target(repo) == artifact_oid
    assert git.ref_target(TARGET_REF, cwd=repo) == artifact_oid
    recovered = PhaseLanding(
        PhaseAdapter(fake_client),
        git,
        repo,
        paths,
        gate,
        repository_gate,
    ).recover(STAGE_ID)

    assert recovered.disposition is LandingDisposition.CLOSED
    assert _ref_target(repo) == artifact_oid
    assert fake_bd.rows[STAGE_ID]["status"] == "closed"
    assert gate.calls == 2
    assert repository_gate.calls == 2


def _ref_target(repo: Path) -> str:
    """Read the actual target ref so recovery tests never mock ref motion."""
    return subprocess.run(
        ["git", "rev-parse", TARGET_REF],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _reflog(repo: Path) -> tuple[str, ...]:
    """Capture the target's real ref-motion evidence before recovery runs."""
    return tuple(
        subprocess.run(
            ["git", "reflog", "show", "--format=%H", TARGET_REF],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )


def test_recovery_refuses_unrelated_history_without_closing_or_moving_a_ref(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """An interrupted landing cannot turn unrelated post-CAS history into closure."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    git, paths = _landing_context(repo, tmp_path)
    with pytest.raises(InjectedCrash):
        PhaseLanding(
            adapter,
            git,
            repo,
            paths,
            gate,
            repository_gate,
            hooks=_CrashAfterCas(),
        ).land(STAGE_ID)
    unrelated = subprocess.run(
        ["git", "commit-tree", f"{base}^{{tree}}", "-m", "unrelated"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(["git", "update-ref", TARGET_REF, unrelated], cwd=repo, check=True)
    before_recovery = _reflog(repo)

    result = PhaseLanding(adapter, git, repo, paths, gate, repository_gate).recover(
        STAGE_ID
    )

    assert result.disposition is LandingDisposition.HUMAN_ATTENTION
    assert _ref_target(repo) == unrelated
    assert _reflog(repo) == before_recovery
    assert fake_bd.rows[STAGE_ID]["status"] == "in_progress"


def test_recovery_closes_when_a_descendant_contains_the_signed_artifact(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """A target descendant may finish closure but recovery still cannot move it."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    git, paths = _landing_context(repo, tmp_path)
    with pytest.raises(InjectedCrash):
        PhaseLanding(
            adapter,
            git,
            repo,
            paths,
            gate,
            repository_gate,
            hooks=_CrashAfterCas(),
        ).land(STAGE_ID)
    subprocess.run(["git", "checkout", "--quiet", "main"], cwd=repo, check=True)
    (repo / "descendant.txt").write_text("descendant\n", encoding="utf-8")
    subprocess.run(["git", "add", "descendant.txt"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "--quiet", "-m", "post-CAS descendant"],
        cwd=repo,
        check=True,
    )
    descendant = _ref_target(repo)
    before_recovery = _reflog(repo)

    result = PhaseLanding(adapter, git, repo, paths, gate, repository_gate).recover(
        STAGE_ID
    )

    assert result.disposition is LandingDisposition.CLOSED
    assert _ref_target(repo) == descendant
    assert _reflog(repo) == before_recovery
    assert fake_bd.rows[STAGE_ID]["status"] == "closed"


def test_fake_dependencies_reflect_its_row_instead_of_a_vacuous_empty_fixture(
    fake_bd: FakeBd, fake_client: BdClient
) -> None:
    """A dependency assertion can now fail when the fake stage actually has one."""
    stage = _stage_row()
    stage["dependencies"] = [{"issue_id": STAGE_ID, "depends_on_id": "blocker"}]
    fake_bd.rows[STAGE_ID] = stage

    dependencies = PhaseAdapter(fake_client).dependencies(STAGE_ID)

    assert len(dependencies) == 1
    assert dependencies[0].model_dump() == {
        "issue_id": STAGE_ID,
        "depends_on_id": "blocker",
    }


def test_intent_before_cas_refuses_without_restarting_the_landing(
    fake_bd: FakeBd,
    fake_client: BdClient,
    gate_verifier: GateVerifier,
    sign_payload: Signer,
    tmp_path: Path,
) -> None:
    """An intact intent at H is operator work, never an automatic second CAS."""
    repo, base = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    adapter = PhaseAdapter(fake_client)
    prepared = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
    )
    adapter.prepare(STAGE_ID, prepared)
    adapter.admit(STAGE_ID, prepared, root_id=ROOT_ID)
    gate = _GateAuthority(artifact_oid, tree, gate_verifier, sign_payload)
    repository_gate = _RepositoryGate(artifact_oid, tree)
    git, paths = _landing_context(repo, tmp_path)
    intent = LandingIntent(
        ref=TARGET_REF,
        expected_base=base,
        artifact_oid=artifact_oid,
        tree=tree,
        gate_receipt_digest=gate.verify(ROOT_ID).digest,
        stage=STAGE_ID,
        attempt=1,
    )
    write_record(paths.instance_dir / "phase-bridge-landing.json", intent)
    before_recovery = _reflog(repo)

    result = PhaseLanding(adapter, git, repo, paths, gate, repository_gate).recover(
        STAGE_ID
    )

    assert result.disposition is LandingDisposition.HUMAN_ATTENTION
    assert result.observed_target == base
    assert _ref_target(repo) == base
    assert _reflog(repo) == before_recovery
    assert fake_bd.rows[STAGE_ID]["status"] == "in_progress"


def test_repository_gate_discloses_t1_before_running_the_detached_checkout(
    tmp_path: Path,
) -> None:
    """Operator output names the trusted-code boundary before the gate can execute."""
    repo, _ = _temporary_repo(tmp_path)
    artifact_oid, tree = _commit_artifact(repo)
    git, paths = _landing_context(repo, tmp_path)
    events: list[str] = []

    def checks(checkout: Path, candidate: str) -> tuple[str, ...]:
        """Prove the production gate receives a clean detached candidate tree."""
        assert candidate == artifact_oid
        assert (
            subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=checkout,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            == artifact_oid
        )
        assert events == [T1_MESSAGE]
        return ("five numbered items / six commands green",)

    result = DetachedRepositoryGate(git, paths, checks, events.append).verify(
        artifact_oid, tree
    )

    assert result.results == ("five numbered items / six commands green",)
