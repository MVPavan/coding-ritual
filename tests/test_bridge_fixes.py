"""Milestone correction regressions at the real landing and Git boundaries."""

import json
import subprocess

import pytest

from tests.test_phase_bridge import (
    EPIC_ID,
    ROOT_ID,
    STAGE_ID,
    TARGET_REF,
    _commit_artifact,
    _GateAuthority,
    _landing_context,
    _policy,
    _RepositoryGate,
    _stage_row,
    _temporary_repo,
)
from workflow_interpreter.bridge import (
    DetachedRepositoryGate,
    LandingDisposition,
    LandingHooks,
    PhaseAdapter,
    PhaseBridgeRecord,
    PhaseLanding,
)
from workflow_interpreter.bridge.landing import LANDING_RECEIPT_FILE
from workflow_interpreter.bridge.verification import CheckCommand, VerificationPolicy


@pytest.fixture
def case(tmp_path, fake_bd, fake_client, gate_verifier, sign_payload):
    repo, base = _temporary_repo(tmp_path)
    oid, tree = _commit_artifact(repo)
    fake_bd.rows[STAGE_ID] = _stage_row()
    record = PhaseBridgeRecord.prepared(
        epic_id=EPIC_ID,
        stage_id=STAGE_ID,
        attempt=1,
        target_ref=TARGET_REF,
        expected_base_commit=base,
        verification_policy=_policy(),
    ).admitted(ROOT_ID)
    fake_bd.rows[STAGE_ID]["metadata"]["phase_bridge"] = record.model_dump(
        by_alias=True, mode="json"
    )
    git, paths = _landing_context(repo, tmp_path)
    adapter = PhaseAdapter(fake_client)
    authority = _GateAuthority(oid, tree, gate_verifier, sign_payload)
    checks = _RepositoryGate(oid, tree)
    landing = PhaseLanding(adapter, git, repo, paths, authority, checks)
    return landing, adapter, git, repo, paths, fake_bd, checks, base


def test_landed_relation_digest_cannot_be_overwritten(case, monkeypatch):
    landing, adapter, _, _, _, fake, _, _ = case
    real_close = adapter.close
    monkeypatch.setattr(
        adapter,
        "close",
        lambda *_: (_ for _ in ()).throw(RuntimeError("interrupted close")),
    )
    with pytest.raises(RuntimeError):
        landing.land(STAGE_ID)
    # Simulate the durable LANDED branch before close's metadata write.
    raw = fake.rows[STAGE_ID]["metadata"]["phase_bridge"]
    raw["state"] = "landed"
    raw["landing_receipt_digest"] = "different"
    monkeypatch.setattr(adapter, "close", real_close)
    with pytest.raises(ValueError, match="receipt digest"):
        landing.recover(STAGE_ID)
    assert raw["landing_receipt_digest"] == "different"
    assert fake.rows[STAGE_ID]["status"] != "closed"


@pytest.mark.parametrize("change", ("missing", "changed"))
def test_closed_history_does_not_execute_old_host_tool(case, tmp_path, change):
    landing, adapter, git, repo, paths, fake, _, _ = case
    program = tmp_path / "host-check"
    program.write_text("#!/bin/sh\nexit 0\n")
    program.chmod(0o755)
    policy = VerificationPolicy.pin(
        (CheckCommand(name="host", argv=(str(program),)),), repo
    )
    record = adapter.record(STAGE_ID).model_copy(update={"verification_policy": policy})
    fake.rows[STAGE_ID]["metadata"]["phase_bridge"] = record.model_dump(
        by_alias=True, mode="json"
    )
    landing._repository_gate = DetachedRepositoryGate(
        git, paths, policy, lambda _: None
    )
    assert landing.land(STAGE_ID).disposition is LandingDisposition.CLOSED
    if change == "missing":
        program.unlink()
    else:
        program.write_text("#!/bin/sh\nexit 17\n")
    before = fake.command_count("close")
    assert landing.recover(STAGE_ID).disposition is LandingDisposition.CLOSED
    assert fake.command_count("close") == before
    receipt_path = paths.instance_dir / LANDING_RECEIPT_FILE
    receipt = json.loads(receipt_path.read_text())
    receipt["policy_digest"] = "wrong"
    receipt_path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="correspond"):
        landing.recover(STAGE_ID)


def snapshot(repo):
    return (
        subprocess.check_output(["git", "status", "--porcelain=v1"], cwd=repo),
        subprocess.check_output(["git", "write-tree"], cwd=repo),
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo),
        (repo / "src/feature.py").read_bytes(),
        (repo / "local.txt").read_bytes() if (repo / "local.txt").exists() else None,
    )


@pytest.mark.parametrize(
    "change", ("unstaged", "staged", "untracked", "branch", "detached")
)
def test_post_cas_checkout_changes_remain_untouched(case, change):
    landing, _, git, repo, _, fake, _, base = case
    snapshots = []

    class Hooks(LandingHooks):
        def after_cas(self):
            if change in ("unstaged", "staged"):
                (repo / "src/feature.py").write_text("human edit\n")
                if change == "staged":
                    subprocess.run(
                        ["git", "add", "src/feature.py"], cwd=repo, check=True
                    )
            elif change == "untracked":
                (repo / "local.txt").write_text("human file\n")
            elif change == "branch":
                git.update_ref("refs/heads/other", base, cwd=repo)
                subprocess.run(
                    ["git", "symbolic-ref", "HEAD", "refs/heads/other"],
                    cwd=repo,
                    check=True,
                )
            else:
                subprocess.run(
                    ["git", "update-ref", "--no-deref", "HEAD", base],
                    cwd=repo,
                    check=True,
                )
            snapshots.append(snapshot(repo))

    landing._hooks = Hooks()
    result = landing.land(STAGE_ID)
    assert result.disposition is LandingDisposition.HUMAN_ATTENTION
    assert "coordinator" in result.reason
    assert snapshot(repo) == snapshots[0]
    again = landing.recover(STAGE_ID)
    assert again.disposition is LandingDisposition.HUMAN_ATTENTION
    assert snapshot(repo) == snapshots[0]
    assert fake.rows[STAGE_ID]["status"] != "closed"


def test_fresh_landing_requires_attached_target_before_cas(case):
    landing, _, git, repo, _, fake, _, base = case
    git.update_ref("refs/heads/other", base, cwd=repo)
    subprocess.run(
        ["git", "symbolic-ref", "HEAD", "refs/heads/other"], cwd=repo, check=True
    )
    result = landing.land(STAGE_ID)
    assert result.disposition is LandingDisposition.HUMAN_ATTENTION
    assert "attached" in result.reason
    assert git.ref_target(TARGET_REF, cwd=repo) == base
    assert fake.command_count("close") == 0


def test_landed_state_at_original_base_does_not_offer_landing_retry(case, monkeypatch):
    landing, adapter, git, repo, _, _, _, base = case
    monkeypatch.setattr(
        adapter, "close", lambda *_: (_ for _ in ()).throw(RuntimeError("before close"))
    )
    with pytest.raises(RuntimeError):
        landing.land(STAGE_ID)
    git.update_ref(TARGET_REF, base, cwd=repo)
    result = landing.recover(STAGE_ID)
    assert result.disposition is LandingDisposition.HUMAN_ATTENTION
    assert result.next_action is None
    with pytest.raises(ValueError, match="pending intent"):
        landing.retry_landing(STAGE_ID)


@pytest.mark.parametrize(
    "change",
    ("root", "stage", "attempt", "policy", "target", "dirty", "gate", "receipt"),
)
def test_explicit_pending_retry_refuses_changed_authority(case, monkeypatch, change):
    from workflow_interpreter.bridge.landing import LANDING_INTENT_FILE

    landing, _, git, repo, paths, fake, checks, _ = case
    original_write = landing._write_intent

    def interrupt(intent):
        original_write(intent)
        raise RuntimeError("intent persisted")

    monkeypatch.setattr(landing, "_write_intent", interrupt)
    with pytest.raises(RuntimeError):
        landing.land(STAGE_ID)
    path = paths.instance_dir / LANDING_INTENT_FILE
    raw = json.loads(path.read_text())
    calls = checks.calls
    pending = landing.recover(STAGE_ID)
    assert pending.disposition is LandingDisposition.PENDING
    assert checks.calls == calls
    if change in ("root", "stage", "attempt", "policy"):
        key, value = {
            "root": ("root_id", "other"),
            "stage": ("stage", "other"),
            "attempt": ("attempt", 2),
            "policy": ("policy_digest", "wrong"),
        }[change]
        raw[key] = value
        path.write_text(json.dumps(raw))
    elif change == "target":
        git.update_ref(TARGET_REF, raw["artifact_oid"], cwd=repo)
    elif change == "dirty":
        (repo / "local.txt").write_text("preserve me")
    elif change == "gate":
        landing._gate_authority._tree = "f" * 40
    else:
        receipt = landing._receipt(
            pending.intent, checks.verify(raw["artifact_oid"], raw["tree"])
        )
        (paths.instance_dir / LANDING_RECEIPT_FILE).write_text(
            receipt.model_dump_json()
        )
    before = snapshot(repo)
    if change in ("target", "dirty"):
        assert (
            landing.retry_landing(STAGE_ID).disposition is not LandingDisposition.CLOSED
        )
    else:
        with pytest.raises(ValueError):
            landing.retry_landing(STAGE_ID)
    assert snapshot(repo) == before
    assert path.exists()
    assert fake.rows[STAGE_ID]["status"] != "closed"
