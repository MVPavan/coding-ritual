"""Fresh candidate authority through deterministic profiles, Git and signed gates."""

from dataclasses import replace
from pathlib import Path

import pytest

from tests._supervisor import ChildScript
from tests.test_foreman_main import _bridge_adapter
from tests.test_integration_admission import source_lab
from workflow_interpreter.bridge.adapter import PhaseAdapter
from workflow_interpreter.bridge.command import execute_phase_bridge
from workflow_interpreter.bridge.integration import (
    IntegrationRequest,
    prepare_integration,
)
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.schema.models import Outcome


def prepared_lab(tmp_path, monkeypatch, signing_config, sign_payload):
    lab, owner, composition, source = source_lab(tmp_path)
    # Preserve durable roots while adding the real signature verifier to this lab.
    lab._signing = signing_config
    lab.signer = sign_payload
    lab._build_fresh()
    lab.pin_checks(
        {
            "scripts/verify-feature.sh": "#!/bin/sh\npython3 -c \"import ast; from pathlib import Path; ast.parse(Path('src/feature.py').read_text())\"\n"
        }
    )
    composition = replace(
        lab.composition,
        config=lab.config.model_copy(
            update={"bridge_checks": composition.config.bridge_checks}
        ),
    )
    lab.composition = composition
    lab.spawner.bind(composition)
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    record = prepare_integration(
        composition,
        IntegrationRequest(
            owner_id=owner.root_id,
            epic_id="phase",
            stage_id="stage",
            request_key="combine",
            sources=(("source", 0, source.receipt_digest),),
        ),
    )
    lab.profiles.bind_node(
        "integrate",
        ChildScript(
            marker='{"outcome":"done"}',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 2\n",
            commit=True,
        ),
    )
    lab.profiles.bind_node(
        "review", ChildScript(marker='{"outcome":"accept"}', effects='{"paths":[]}')
    )
    return lab, owner, record


def entry(lab, *, retry=False, retry_landing=False):
    return execute_phase_bridge(
        lab.composition,
        epic_id="phase",
        stage_id="stage",
        retry=retry,
        trace=False,
        retry_landing=retry_landing,
    )


def approve_integration(lab, record):
    before = entry(lab)
    assert before.exit_code == 0, before.report
    gates = lab.store.reads.list_gates(record.root_id)
    assert len(gates) == 1 and gates[0].metadata.gate_node == "ship", before.report
    assert lab.git.head_commit(cwd=lab.repo) == record.expected_base_commit
    assert _bridge_adapter(lab).show("stage").status != "closed"
    lab.root = lab.store.reads.load_root(record.root_id)
    lab.approve(gates[0].gate_id, Outcome.APPROVE)


def test_normal_entry_requires_fresh_review_and_explicit_ship(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    approve_integration(lab, record)
    result = entry(lab)
    assert result.exit_code == 0, result.report
    assert result.report["state"] == "completed"
    assert (lab.repo / "src/feature.py").read_text() == "value = 2\n"
    assert _bridge_adapter(lab).show("stage").status == "closed"
    state = lab.store.coordination_store().state(owner.root_id)
    assert len(state.children) == 2
    assert state.integrations["combine"].authorization is not None
    from workflow_interpreter.bridge.integration import IntegrationGuard

    claim = IntegrationGuard(lab.composition).claim(
        state.integrations["combine"].target_key
    )
    assert claim[1].disposition == "released"


@pytest.mark.proc
@pytest.mark.parametrize(
    "boundary", ["before-cas", "after-cas", "intent", "receipt", "relation", "close"]
)
def test_cancellation_and_crash_recovery_are_forward_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    boundary: str,
) -> None:
    from tests._fake_bd import InjectedCrash
    from workflow_interpreter.bridge import landing
    from workflow_interpreter.bridge.landing import LandingHooks

    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    approve_integration(lab, record)
    coordinator = lab.store.coordination_store(composition=lab.composition)
    armed = True
    real_write = landing.write_record
    real_land = PhaseAdapter.land

    def after_cas(self):
        nonlocal armed
        if armed and boundary == "after-cas":
            armed = False
            coordinator.cancel_child(
                owner.root_id,
                record.integration_slot,
                0,
                "cancel",
                "after observed CAS",
            )
            raise InjectedCrash("after CAS")
        if armed and boundary == "close":
            armed = False
            lab.fake_bd.lose_response_on("close")

    def write(path, value):
        nonlocal armed
        real_write(path, value)
        if armed and (
            (boundary == "intent" and path.name == landing.LANDING_INTENT_FILE)
            or (boundary == "receipt" and path.name == landing.LANDING_RECEIPT_FILE)
        ):
            armed = False
            raise InjectedCrash("durable journal fault")

    def relation(self, stage_id, value):
        nonlocal armed
        result = real_land(self, stage_id, value)
        if armed and boundary == "relation":
            armed = False
            raise InjectedCrash("relation persisted")
        return result

    monkeypatch.setattr(LandingHooks, "after_cas", after_cas)
    monkeypatch.setattr(landing, "write_record", write)
    monkeypatch.setattr(PhaseAdapter, "land", relation)
    if boundary == "before-cas":
        coordinator.cancel_child(
            owner.root_id,
            record.integration_slot,
            0,
            "cancel",
            "before authority handoff",
        )
        refused = entry(lab)
        assert refused.exit_code == 2
        assert lab.git.head_commit(cwd=lab.repo) == record.expected_base_commit
        assert _bridge_adapter(lab).show("stage").status != "closed"
        return
    with pytest.raises(InjectedCrash):
        entry(lab)
    if boundary == "intent":
        pending = entry(lab)
        assert pending.report["disposition"] == "pending"
        assert entry(lab, retry=True).exit_code == 2
        assert lab.git.head_commit(cwd=lab.repo) == record.expected_base_commit
        recovered = entry(lab, retry_landing=True)
    else:
        recovered = entry(lab)
    assert recovered.exit_code == 0, recovered.report
    assert _bridge_adapter(lab).show("stage").status == "closed"
    assert lab.git.head_commit(cwd=lab.repo) != record.expected_base_commit
    assert len(lab.store.coordination_store().state(owner.root_id).children) == 2


@pytest.mark.parametrize("conflict", [False, True])
def test_combines_code_markdown_reader_receipt_and_new_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    conflict: bool,
) -> None:
    import json
    import sys

    from pydantic import TypeAdapter

    from tests._supervisor import FakeProfile, commit_all
    from workflow_interpreter.bdio import ResolvedSetting
    from workflow_interpreter.foreman.decisions import admission_of
    from workflow_interpreter.foreman.resolve import _resolved_config
    from workflow_interpreter.schema.loader import canonical_bytes, load_graph
    from workflow_interpreter.supervisor.profile import RunnerCommand

    lab, owner, composition, source = source_lab(tmp_path)
    lab._signing = signing_config
    lab.signer = sign_payload
    lab._build_fresh()
    composition = replace(
        lab.composition,
        config=lab.config.model_copy(
            update={"bridge_checks": composition.config.bridge_checks}
        ),
    )
    lab.composition = composition
    lab.spawner.bind(composition)
    coordinator = lab.store.coordination_store(composition=composition)
    graph = tmp_path / "markdown-reader.toml"
    text = lab._toml.read_text().replace(
        'allowed_paths = ["src/**"]', 'allowed_paths = ["docs/**"]'
    )
    text = text.replace('on = "done"\nto = "done"', 'on = "done"\nto = "source-review"')
    text += """
[[node]]
name = "source-review"
kind = "task"
runner = "profile:critic"
instructions = "Review the Markdown change."
allowed_paths = []
verify = [{cmd="scripts/review-checks.sh", timeout="20s"}]
writes = false
isolation = "worktree"
inputs = ["source_diff"]
context_budget_bytes = 16000
max_wall = "1m"
stale_after = "1m"
max_infra_retries = 0
max_steers = 0
outcomes = ["accept"]
[[edge]]
from = "source-review"
on = "accept"
to = "done"
[[source]]
name = "source_diff"
producer = "node:work"
optional = false
trim_priority = 1
"""
    if conflict:
        text = text.replace('allowed_paths = ["docs/**"]', 'allowed_paths = ["src/**"]')
    graph.write_text(text)
    definition = load_graph(graph)
    admission = admission_of(owner, slot="markdown", generation=0).model_copy(
        update={
            "graph_body": canonical_bytes(definition.document).decode(),
            "config_json": TypeAdapter(tuple[ResolvedSetting, ...])
            .dump_json(_resolved_config(composition, definition, {}))
            .decode(),
        }
    )
    child = coordinator.start_child(owner.root_id, "markdown", admission)

    class MarkdownScript(ChildScript):
        def shell(self):
            return "mkdir -p docs\n" + super().shell()

    lab.profiles.bind_node(
        "work",
        MarkdownScript(
            marker='{"outcome":"done"}',
            effects=json.dumps(
                {"paths": ["src/feature.py" if conflict else "docs/design.md"]}
            ),
            write_path="src/feature.py" if conflict else "docs/design.md",
            write_body="value = 3\n" if conflict else "Documented contribution\n",
            commit=True,
        ),
    )
    lab.profiles.bind_node(
        "source-review",
        ChildScript(marker='{"outcome":"accept"}', effects='{"paths":[]}'),
    )
    result = Foreman(composition).run(child.root_id, poll_s=0.01, max_wall_s=10)
    assert result.report.terminal, result
    markdown = coordinator.collect_child(owner.root_id, "markdown", 0)
    assert markdown.artifact_source == "activation-input"
    (lab.repo / "target.txt").write_text("independent target edit\n")
    new_base = commit_all(lab.repo, "independent target")
    monkeypatch.setattr(
        PhaseAdapter, "from_config", classmethod(lambda *_: _bridge_adapter(lab))
    )
    record = prepare_integration(
        composition,
        IntegrationRequest(
            owner_id=owner.root_id,
            epic_id="phase",
            stage_id="stage",
            request_key="combine",
            sources=(
                ("source", 0, source.receipt_digest),
                ("markdown", 0, markdown.receipt_digest),
            ),
        ),
    )
    assert record.expected_base_commit == new_base
    root = lab.store.reads.load_root(record.root_id)
    manifest = next(
        i.body for i in root.metadata.instance_inputs if i.name == "integration_sources"
    )
    entries = json.loads(manifest)
    assert len(entries) == 2 and all(e["repository_contribution"] for e in entries)
    assert entries[1]["writer_activations"]

    class CombiningProfile(FakeProfile):
        def build_command(self, task, session_id):
            assert manifest in task.brief
            script = """
import json, os, subprocess, sys
from pathlib import Path
entries = json.loads(sys.argv[1])
def git(*args, **kw):
    return subprocess.run(["git", *args], check=True, stdout=subprocess.PIPE, **kw).stdout
if sys.argv[2] == "integrate":
    for item in entries:
        if item["repository_contribution"]:
            r = item["receipt"]
            patch = git("diff", r["base_commit"], r["artifact_commit"])
            git("apply", "--index", "-", input=patch)
    git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-m", "integrate explicit sources")
assert Path("src/feature.py").read_text() == "value = 2\\n"
assert Path("docs/design.md").read_text() == "Documented contribution\\n"
assert Path("target.txt").read_text() == "independent target edit\\n"
Path(os.environ["WF_EFFECTS_FILE"]).write_text(json.dumps({"paths": ["src/feature.py", "docs/design.md"] if sys.argv[2] == "integrate" else []}))
Path(os.environ["WF_OUTCOME_FILE"]).write_text(json.dumps({"outcome": "done" if sys.argv[2] == "integrate" else "accept"}))
"""
            return RunnerCommand(
                argv=(sys.executable, "-c", script, manifest, task.node),
                env={"PATH": "/usr/bin:/bin", **task.channels.env()},
                cwd=task.cwd,
                log_path=task.channels.log_path,
                session_id=session_id,
            )

    lab.profiles.profile = CombiningProfile(ChildScript())
    lab.profiles._by_node.clear()
    if conflict:
        result = entry(lab)
        assert result.exit_code == 0, result.report
        assert all(
            g.metadata.gate_node != "ship"
            for g in lab.store.reads.list_gates(record.root_id)
        )
        assert lab.git.head_commit(cwd=lab.repo) == new_base
        assert _bridge_adapter(lab).show("stage").status != "closed"
        return
    approve_integration(lab, record)
    result = entry(lab)
    assert result.exit_code == 0, result.report
    assert (lab.repo / "src/feature.py").read_text() == "value = 2\n"
    assert (lab.repo / "docs/design.md").read_text() == "Documented contribution\n"
    assert (lab.repo / "target.txt").read_text() == "independent target edit\n"


def test_stale_base_retry_keeps_original_budget_and_requires_new_approval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    from tests._supervisor import commit_all

    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    approve_integration(lab, record)
    settled = Foreman(lab.composition).run(record.root_id, poll_s=0.01, max_wall_s=10)
    assert settled.report.terminal
    (lab.repo / "new-target.txt").write_text("preserve this\n")
    base = commit_all(lab.repo, "target moved")
    stale = entry(lab)
    assert stale.report["disposition"] == "branch-moved"
    result = entry(lab, retry=True)
    assert result.exit_code == 0, result.report
    successor = _bridge_adapter(lab).record("stage")
    assert successor.attempt == 2 and successor.root_id != record.root_id
    assert successor.expected_base_commit == base
    assert successor.previous_attempts == (record.instance_key,)
    state = lab.store.coordination_store().state(owner.root_id)
    assert len(state.reservations) == 4
    assert sum(r.capacity.ceiling for r in state.reservations.values()) == 14
    from workflow_interpreter.bridge.integration import IntegrationGuard

    claim = IntegrationGuard(lab.composition).claim(
        state.integrations["combine"].target_key
    )
    assert claim[1].attempt == 2
    assert lab.git.head_commit(cwd=lab.repo) == base
    gate = lab.store.reads.list_gates(successor.root_id)[0]
    assert gate.metadata.gate_node == "ship" and gate.bead.status == "open"
    lab.root = lab.store.reads.load_root(successor.root_id)
    lab.approve(gate.gate_id, Outcome.APPROVE)
    result = entry(lab)
    assert result.exit_code == 0, result.report
    assert (lab.repo / "new-target.txt").read_text() == "preserve this\n"


@pytest.mark.parametrize(
    "failure",
    [
        "partial-writer",
        "reject-review",
        "failed-check",
        "review-other-tree",
        "cancel-after-checks",
    ],
)
def test_invalid_candidate_never_moves_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    failure: str,
) -> None:
    from workflow_interpreter.bridge.landing import DetachedRepositoryGate

    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    if failure == "partial-writer":
        lab.profiles.bind_node(
            "integrate",
            ChildScript(
                marker='{"outcome":"done"}',
                effects='{"paths":["src/feature.py"]}',
                write_path="src/feature.py",
                write_body="uncommitted\n",
            ),
        )
    elif failure == "reject-review":
        lab.profiles.bind_node(
            "review",
            ChildScript(
                marker='{"outcome":"reject"}',
                effects='{"paths":[]}',
                artifact_path="findings.md",
                artifact_body="Required source omitted",
            ),
        )
    elif failure == "failed-check":
        lab.profiles.bind_node(
            "integrate",
            ChildScript(
                marker='{"outcome":"done"}',
                effects='{"paths":["src/feature.py"]}',
                write_path="src/feature.py",
                write_body="syntax error\n",
                commit=True,
            ),
        )
    if failure in ("partial-writer", "reject-review", "failed-check"):
        result = entry(lab)
        assert result.exit_code == 0, result.report
        gates = lab.store.reads.list_gates(record.root_id)
        assert gates and all(g.metadata.gate_node != "ship" for g in gates), (
            result.report
        )
    else:
        approve_integration(lab, record)
        settled = Foreman(lab.composition).run(
            record.root_id, poll_s=0.01, max_wall_s=10
        )
        assert settled.report.terminal
        if failure == "review-other-tree":
            review = next(
                a
                for a in lab.store.reads.list_activations(record.root_id)
                if a.metadata.node == "review"
            )
            lab.store._client._merge_metadata(
                review.activation_id,
                {"intended_base_commit": record.expected_base_commit},
            )
        else:
            real_verify = DetachedRepositoryGate.verify

            def cancel_after_checks(self, artifact_oid, tree):
                result = real_verify(self, artifact_oid, tree)
                lab.store.coordination_store(composition=lab.composition).cancel_child(
                    owner.root_id,
                    record.integration_slot,
                    0,
                    "cancel",
                    "checks finished before CAS handoff",
                )
                return result

            monkeypatch.setattr(DetachedRepositoryGate, "verify", cancel_after_checks)
        result = entry(lab)
        assert result.exit_code == 2, result.report
    assert lab.git.head_commit(cwd=lab.repo) == record.expected_base_commit
    assert _bridge_adapter(lab).show("stage").status != "closed"


@pytest.mark.parametrize("boundary", ["association", "claim", "bridge"])
def test_retry_journal_recovers_through_normal_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    signing_config,
    sign_payload,
    boundary: str,
) -> None:
    from tests._fake_bd import InjectedCrash
    from tests._supervisor import commit_all
    from workflow_interpreter.bridge.integration import IntegrationGuard

    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    approve_integration(lab, record)
    assert (
        Foreman(lab.composition)
        .run(record.root_id, poll_s=0.01, max_wall_s=10)
        .report.terminal
    )
    (lab.repo / "moved.txt").write_text("new base\n")
    commit_all(lab.repo, "target moved")
    cls, method = {
        "association": (IntegrationGuard, "save"),
        "claim": (IntegrationGuard, "write_claim"),
        "bridge": (PhaseAdapter, "prepare"),
    }[boundary]
    original = getattr(cls, method)
    armed = True

    def crash(self, *args, **kwargs):
        nonlocal armed
        result = original(self, *args, **kwargs)
        if armed:
            armed = False
            raise InjectedCrash("retry boundary")
        return result

    monkeypatch.setattr(cls, method, crash)
    with pytest.raises(InjectedCrash):
        entry(lab, retry=True)
    result = entry(lab)
    assert result.exit_code == 0, result.report
    successor = _bridge_adapter(lab).record("stage")
    assert successor.attempt == 2
    state = lab.store.coordination_store().state(owner.root_id)
    assert len(state.reservations) == 4 and len(state.children) == 3
    assert lab.store.reads.list_gates(successor.root_id)[0].metadata.gate_node == "ship"


def test_direct_adapter_close_cannot_promote_membership_to_landing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    from workflow_interpreter.bridge.adapter import PhaseAdapterError
    from workflow_interpreter.bridge.errors import BridgeRefusal
    from workflow_interpreter.bridge.integration import IntegrationGuard

    lab, _, record = prepared_lab(tmp_path, monkeypatch, signing_config, sign_payload)
    forged = record.landed(
        record.expected_base_commit,
        lab.git.tree_oid(record.expected_base_commit, cwd=lab.repo),
        "child-approval",
        "invented-receipt",
    ).closed()
    adapter = _bridge_adapter(lab)
    with pytest.raises(PhaseAdapterError, match="runtime guard"):
        adapter.close("stage", forged, "invented-receipt")
    stripped = forged.model_copy(
        update={
            "integration_digest": None,
            "integration_owner": None,
            "integration_slot": None,
            "integration_generation": None,
        }
    )
    with pytest.raises(PhaseAdapterError, match="strip"):
        adapter.close("stage", stripped, "invented-receipt")
    adapter.integration_guard = IntegrationGuard(lab.composition)
    with pytest.raises(BridgeRefusal):
        adapter.close("stage", forged, "invented-receipt")
    assert adapter.show("stage").status != "closed"


@pytest.mark.proc
def test_final_handoff_excludes_racing_cancellation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, signing_config, sign_payload
) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from workflow_interpreter.bridge.integration import IntegrationGuard
    from workflow_interpreter.supervisor.errors import LockUnavailable

    lab, owner, record = prepared_lab(
        tmp_path, monkeypatch, signing_config, sign_payload
    )
    approve_integration(lab, record)
    assert (
        Foreman(lab.composition)
        .run(record.root_id, poll_s=0.01, max_wall_s=10)
        .report.terminal
    )
    handoff, release = Event(), Event()
    original = IntegrationGuard.pre_cas

    def paused(self, value):
        original(self, value)
        handoff.set()
        assert release.wait(timeout=10)

    monkeypatch.setattr(IntegrationGuard, "pre_cas", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(entry, lab)
        try:
            assert handoff.wait(timeout=10)
            with pytest.raises(LockUnavailable):
                lab.store.coordination_store(composition=lab.composition).cancel_child(
                    owner.root_id,
                    record.integration_slot,
                    0,
                    "race",
                    "racing final handoff",
                )
        finally:
            release.set()
        result = future.result(timeout=15)
    assert result.exit_code == 0, result.report
    lab.store.coordination_store(composition=lab.composition).cancel_child(
        owner.root_id, record.integration_slot, 0, "after", "after observed landing"
    )
    assert entry(lab).exit_code == 0
    assert _bridge_adapter(lab).show("stage").status == "closed"
