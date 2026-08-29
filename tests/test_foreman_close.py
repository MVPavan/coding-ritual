"""Focused C2a contracts for the crash-window settlement branch."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from tests._bdio import (
    entry_request,
    handle,
    load_definition,
    make_root,
)
from tests._supervisor import (
    FakeProfile,
    FrozenClock,
    commit_all,
    dead_pid,
    handle_for,
    head_of,
    make_config,
    make_git,
    make_paths,
    make_repo,
    make_store,
    make_workspace,
    node_of,
    verifier_pins,
)
from tests._supervisor import (
    make_root as make_supervisor_root,
)
from workflow_interpreter.bdio import (
    ActivationRecord,
    Deviation,
    Evidence,
    ExitRecord,
    GateState,
    Lifecycle,
    RootRecord,
)
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.carriers import ArtifactIdentity
from workflow_interpreter.foreman import close as close_module
from workflow_interpreter.foreman.close import settle
from workflow_interpreter.foreman.compose import InstanceWiring
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor import (
    BranchAdvance,
    BranchAdvanceOutcome,
    CompletionEvidence,
    ExitObserver,
    ExitReason,
)
from workflow_interpreter.supervisor.paths import write_record


class StoreDouble:
    """Close-only store double that makes duplicate evidence writes observable."""

    def __init__(self, activation: object) -> None:
        self.activation = activation
        self.recorded = 0
        self.closed = 0

    def record_evidence(self, *args: object) -> object:
        """Fail if the evidence-recorded branch tries to derive evidence again."""
        self.recorded += 1
        raise AssertionError("evidence must not be re-recorded")

    def close_activation(self, *args: object, **kwargs: object) -> object:
        """Record the one legal close operation."""
        self.closed += 1
        return self.activation


def _completion_paths(
    tmp_path: Path,
    root: RootRecord,
    activation: ActivationRecord,
    outcome: Outcome = Outcome.DONE,
) -> object:
    """Write the durable completion that the evidence crash window reads."""
    evidence = activation.metadata.evidence
    paths = make_paths(make_config(tmp_path / "repo", tmp_path), root.root_id)
    write_record(
        paths.completion(activation.activation_id),
        CompletionEvidence(
            outcome=outcome,
            claimed_outcome=None if evidence is None else evidence.claimed_outcome,
            evidence=Evidence() if evidence is None else evidence,
        ),
    )
    return paths


def test_settle_closes_evidence_recorded_without_replaying(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """The crash window closes recorded evidence without re-derivation."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.EVIDENCE_RECORDED,
                    "evidence": Evidence(claimed_outcome=Outcome.DONE),
                }
            )
        }
    )
    store = StoreDouble(activation)
    wiring = SimpleNamespace(
        store=store, paths=_completion_paths(tmp_path, root, activation)
    )
    result = settle(
        cast(InstanceWiring, wiring),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )
    assert result.activation == activation
    assert store.recorded == 0
    assert store.closed == 1


def test_settle_closes_a_real_recorded_done_from_its_completion(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A real evidence crash window preserves the completion verdict, not fail_code."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = fake_store.record_dispatch(activation.activation_id, handle())
    activation = fake_store.record_exit(
        activation.activation_id,
        ExitRecord(exit_code=0, ended_at="2026-08-28T00:00:00Z", reason="ok"),
    )
    evidence = Evidence(claimed_outcome=Outcome.DONE)
    activation = fake_store.record_evidence(activation.activation_id, evidence)
    assert activation.metadata.outcome is None

    paths = make_paths(make_config(tmp_path / "repo", tmp_path), root.root_id)
    write_record(
        paths.completion(activation.activation_id),
        CompletionEvidence(
            outcome=Outcome.DONE,
            claimed_outcome=Outcome.DONE,
            evidence=evidence,
        ),
    )
    settled = settle(
        cast(InstanceWiring, SimpleNamespace(store=fake_store, paths=paths)),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    ).activation

    assert settled.metadata.lifecycle is Lifecycle.CLOSED
    assert settled.metadata.outcome is Outcome.DONE


def test_settle_replays_an_uncomputable_verdict_after_completion_loss(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """The durable evidence closes from a freshly re-derived fail-code outcome."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = fake_store.record_dispatch(activation.activation_id, handle())
    activation = fake_store.record_exit(
        activation.activation_id,
        ExitRecord(exit_code=1, ended_at="2026-08-28T00:00:00Z", reason="failed"),
    )
    evidence = Evidence(claimed_outcome=None)
    activation = fake_store.record_evidence(activation.activation_id, evidence)

    replayed: list[ExitRecord] = []

    def replay(*args: object, **kwargs: object) -> object:
        replayed.append(cast(ExitRecord, args[3]))
        return SimpleNamespace(
            completion=CompletionEvidence(
                outcome=Outcome.FAIL_CODE,
                claimed_outcome=None,
                evidence=Evidence(note="newly derived evidence is not persisted"),
            ),
            usage=None,
        )

    paths = make_paths(make_config(tmp_path / "repo", tmp_path), root.root_id)
    settled = settle(
        cast(
            InstanceWiring,
            SimpleNamespace(
                store=fake_store, observer=SimpleNamespace(replay=replay), paths=paths
            ),
        ),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    ).activation

    assert replayed == [activation.metadata.exit_record]
    assert settled.metadata.lifecycle is Lifecycle.CLOSED
    assert settled.metadata.outcome is Outcome.FAIL_CODE
    assert settled.metadata.evidence == evidence


def test_settle_halts_when_missing_completion_cannot_be_replayed(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """An unavailable re-derivation is visible to a human instead of wedging."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = fake_store.record_dispatch(activation.activation_id, handle())
    activation = fake_store.record_exit(
        activation.activation_id,
        ExitRecord(exit_code=1, ended_at="2026-08-28T00:00:00Z", reason="failed"),
    )
    activation = fake_store.record_evidence(activation.activation_id, Evidence())
    paths = make_paths(make_config(tmp_path / "repo", tmp_path), root.root_id)
    observer = SimpleNamespace(
        replay=lambda *args, **kwargs: (_ for _ in ()).throw(OSError("unavailable"))
    )

    result = settle(
        cast(
            InstanceWiring,
            SimpleNamespace(store=fake_store, observer=observer, paths=paths),
        ),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert result.awaiting is True
    assert result.opened is not None


def test_settle_maps_a_malformed_recorded_completion_to_transport_error(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A corrupt crash-window record is handled like a corrupt exit record."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = fake_store.record_dispatch(activation.activation_id, handle())
    activation = fake_store.record_exit(
        activation.activation_id,
        ExitRecord(exit_code=1, ended_at="2026-08-28T00:00:00Z", reason="failed"),
    )
    evidence = Evidence()
    activation = fake_store.record_evidence(activation.activation_id, evidence)
    paths = make_paths(make_config(tmp_path / "repo", tmp_path), root.root_id)
    paths.ensure_activation_dir(activation.activation_id)
    paths.completion(activation.activation_id).write_text("not json", encoding="utf-8")

    settled = settle(
        cast(InstanceWiring, SimpleNamespace(store=fake_store, paths=paths)),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    ).activation

    assert settled.metadata.lifecycle is Lifecycle.CLOSED
    assert settled.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert settled.metadata.evidence == evidence


def test_settle_halts_when_real_replay_contradicts_recorded_evidence(
    tmp_path: Path,
) -> None:
    """A replay cannot replace a durable done claim after its marker is lost."""
    repo = make_repo(tmp_path)
    base = head_of(repo)
    config = make_config(repo, tmp_path, fake_proc=False)
    _, store = make_store(tmp_path, base)
    root = make_supervisor_root(store, repo, "settle-replay")
    paths = make_paths(config, root.root_id)
    git = make_git(config)
    clock = FrozenClock()
    workspace = make_workspace(paths, git, clock)
    node = node_of(root.definition.document, "implement")
    activation = store.mint_activation(root.root_id, entry_request()).activation
    activation = store.record_dispatch(activation.activation_id, handle_for(dead_pid()))
    paths.ensure_activation_dir(activation.activation_id)
    workspace.prepare(activation, node)
    tree = workspace.path_for(node)
    (tree / "src" / "feature.py").write_text("value = 2\n", encoding="utf-8")
    commit_all(tree, "healthy runner result")
    paths.outcome(activation.activation_id).write_text(
        json.dumps({"outcome": "done"}), encoding="utf-8"
    )
    paths.effects(activation.activation_id).write_text(
        json.dumps({"paths": ["src/feature.py"]}), encoding="utf-8"
    )
    observer = ExitObserver(config, paths, git, store, workspace, clock)
    observed = observer.observe(
        activation,
        node,
        FakeProfile(),
        exit_code=0,
        reason=ExitReason.EXITED,
        pinned_digests=verifier_pins(repo, node.name, "scripts/verify-feature.sh"),
    )
    assert observed.completion.outcome is Outcome.DONE
    assert observed.completion.evidence.claimed_outcome is Outcome.DONE
    activation = store.record_evidence(
        observed.activation.activation_id, observed.completion.evidence
    )
    paths.completion(activation.activation_id).unlink()
    paths.outcome(activation.activation_id).unlink()

    result = settle(
        cast(
            InstanceWiring,
            SimpleNamespace(
                store=store,
                observer=observer,
                workspace=workspace,
                repo_root=repo,
                paths=paths,
            ),
        ),
        root,
        node,
        activation,
        FakeProfile(),
    )

    assert result.awaiting is True
    assert result.opened is not None
    assert store.reads.load_activation(activation.activation_id).metadata.lifecycle is (
        Lifecycle.EVIDENCE_RECORDED
    )


def test_settle_halts_when_real_replay_cannot_restore_missing_exit_record(
    tmp_path: Path,
) -> None:
    """A corrupt evidence record opens a halt instead of leaking a bd conflict."""
    repo = make_repo(tmp_path)
    base = head_of(repo)
    config = make_config(repo, tmp_path, fake_proc=False)
    fake, store = make_store(tmp_path, base)
    root = make_supervisor_root(store, repo, "settle-exit-replay")
    paths = make_paths(config, root.root_id)
    git = make_git(config)
    clock = FrozenClock()
    workspace = make_workspace(paths, git, clock)
    node = node_of(root.definition.document, "implement")
    activation = store.mint_activation(root.root_id, entry_request()).activation
    activation = store.record_dispatch(activation.activation_id, handle_for(dead_pid()))
    paths.ensure_activation_dir(activation.activation_id)
    workspace.prepare(activation, node)
    tree = workspace.path_for(node)
    (tree / "src" / "feature.py").write_text("value = 2\n", encoding="utf-8")
    commit_all(tree, "healthy runner result")
    paths.outcome(activation.activation_id).write_text(
        json.dumps({"outcome": "done"}), encoding="utf-8"
    )
    paths.effects(activation.activation_id).write_text(
        json.dumps({"paths": ["src/feature.py"]}), encoding="utf-8"
    )
    observer = ExitObserver(config, paths, git, store, workspace, clock)
    observed = observer.observe(
        activation,
        node,
        FakeProfile(),
        exit_code=0,
        reason=ExitReason.EXITED,
        pinned_digests=verifier_pins(repo, node.name, "scripts/verify-feature.sh"),
    )
    activation = store.record_evidence(
        observed.activation.activation_id, observed.completion.evidence
    )
    paths.completion(activation.activation_id).unlink()
    fake.rows[activation.activation_id]["metadata"]["exit_record"] = None
    activation = store.reads.load_activation(activation.activation_id)

    result = settle(
        cast(
            InstanceWiring,
            SimpleNamespace(
                store=store,
                observer=observer,
                workspace=workspace,
                repo_root=repo,
                paths=paths,
            ),
        ),
        root,
        node,
        activation,
        FakeProfile(),
    )

    assert result.awaiting is True
    assert result.opened is not None
    assert store.reads.load_activation(activation.activation_id).metadata.lifecycle is (
        Lifecycle.EVIDENCE_RECORDED
    )


def test_settle_stalls_when_recorded_evidence_is_missing(
    fake_store: WorkflowStore,
) -> None:
    """The crash-window branch cannot close without its durable evidence."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"lifecycle": Lifecycle.EVIDENCE_RECORDED}
            )
        }
    )
    store = StoreDouble(activation)
    result = settle(
        cast(InstanceWiring, SimpleNamespace(store=store)),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert result.stalled == "evidence is missing"
    assert store.closed == 0


@pytest.mark.parametrize(
    ("state", "outcome", "awaiting", "closed_outcome"),
    (
        (GateState.OPEN, None, True, None),
        (GateState.CLOSED, Outcome.ABANDON, False, Outcome.FAIL_CODE),
        (GateState.CLOSED, Outcome.APPROVE, False, Outcome.DONE),
    ),
)
def test_settle_uses_the_recorded_effects_gate_without_replaying(
    fake_store: WorkflowStore,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    state: GateState,
    outcome: Outcome | None,
    awaiting: bool,
    closed_outcome: Outcome | None,
) -> None:
    """Evidence-recorded effects are decided from their durable gate only."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.EVIDENCE_RECORDED,
                    "evidence": Evidence(
                        claimed_outcome=Outcome.DONE,
                        undeclared_effects=("outside.txt",),
                    ),
                }
            )
        }
    )

    class EffectsStore(StoreDouble):
        def __init__(self, activation: object) -> None:
            super().__init__(activation)
            self.outcome: Outcome | None = None
            self.reads = SimpleNamespace(
                load_gate=lambda _: SimpleNamespace(
                    metadata=SimpleNamespace(opening_outcome=Outcome.DONE)
                )
            )

        def close_activation(self, *args: object, **kwargs: object) -> object:
            self.outcome = cast(Outcome, args[1])
            return super().close_activation(*args, **kwargs)

    store = EffectsStore(activation)
    gate = SimpleNamespace(
        metadata=SimpleNamespace(state=state, outcome=outcome), gate_id="effects"
    )
    monkeypatch.setattr(close_module, "_effects_gate", lambda *args: gate)
    result = settle(
        cast(
            InstanceWiring,
            SimpleNamespace(
                store=store, paths=_completion_paths(tmp_path, root, activation)
            ),
        ),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert result.awaiting is awaiting
    assert store.outcome is closed_outcome


def test_settle_approved_recorded_effects_uses_the_gate_verdict(
    fake_store: WorkflowStore,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An approved recorded-effects gate supplies the close outcome and audit fact."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.EVIDENCE_RECORDED,
                    "evidence": Evidence(
                        claimed_outcome=Outcome.DONE,
                        undeclared_effects=("outside.txt",),
                    ),
                }
            )
        }
    )

    class ApprovalStore(StoreDouble):
        def __init__(self, activation: object) -> None:
            super().__init__(activation)
            self.outcome: Outcome | None = None
            self.deviations: tuple[Deviation, ...] = ()
            self.reads = SimpleNamespace(
                load_gate=lambda _: SimpleNamespace(
                    metadata=SimpleNamespace(opening_outcome=Outcome.DONE)
                )
            )

        def close_activation(self, *args: object, **kwargs: object) -> object:
            self.outcome = cast(Outcome, args[1])
            self.deviations = cast(tuple[Deviation, ...], kwargs["deviations"])
            return super().close_activation(*args, **kwargs)

    store = ApprovalStore(activation)
    gate = SimpleNamespace(
        metadata=SimpleNamespace(state=GateState.CLOSED, outcome=Outcome.APPROVE),
        gate_id="effects",
    )
    monkeypatch.setattr(close_module, "_effects_gate", lambda *args: gate)

    settle(
        cast(
            InstanceWiring,
            SimpleNamespace(
                store=store, paths=_completion_paths(tmp_path, root, activation)
            ),
        ),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert store.outcome is Outcome.DONE
    assert store.deviations == (
        Deviation(
            kind="undeclared_effects_accepted",
            reason="undeclared effects approved",
            recorded_at="settle",
            gate_id="effects",
        ),
    )


def test_settle_awaits_a_lifecycle_that_is_not_ready_to_close(
    fake_store: WorkflowStore,
) -> None:
    """Only recorded exits and evidence enter settlement."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    store = StoreDouble(activation)
    result = settle(
        cast(InstanceWiring, SimpleNamespace(store=store)),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert result.awaiting is True
    assert store.closed == 0


def test_settle_closes_an_exit_without_a_record_as_transport_error(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A corrupt exit-recorded lifecycle is one durable transport failure."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"lifecycle": Lifecycle.EXIT_RECORDED}
            )
        }
    )

    class OutcomeStore(StoreDouble):
        def __init__(self, activation: object) -> None:
            super().__init__(activation)
            self.outcome: Outcome | None = None

        def close_activation(self, *args: object, **kwargs: object) -> object:
            self.outcome = cast(Outcome, args[1])
            return super().close_activation(*args, **kwargs)

    store = OutcomeStore(activation)
    paths = make_paths(make_config(tmp_path / "repo", tmp_path), root.root_id)
    result = settle(
        cast(InstanceWiring, SimpleNamespace(store=store, paths=paths)),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert result.activation == activation
    assert store.outcome is Outcome.ERROR_TRANSPORT


def test_settle_replays_an_exit_record_recovered_from_the_wrapper_file(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """R3 prefers bd's exit record but recovers the crash-window file when absent."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"lifecycle": Lifecycle.EXIT_RECORDED}
            )
        }
    )
    paths = make_paths(make_config(tmp_path / "repo", tmp_path), root.root_id)
    exit_record = ExitRecord(
        exit_code=0, ended_at="2026-08-28T00:00:00Z", reason="done"
    )
    write_record(paths.exit_file(activation.activation_id), exit_record)

    class RecordingStore(StoreDouble):
        def record_evidence(self, *args: object) -> object:
            self.recorded += 1
            return self.activation

    observed: list[ExitRecord] = []

    def replay(*args: object, **kwargs: object) -> object:
        observed.append(cast(ExitRecord, args[3]))
        return SimpleNamespace(
            completion=CompletionEvidence(
                outcome=Outcome.DONE,
                claimed_outcome=Outcome.DONE,
                evidence=Evidence(),
            ),
            usage=None,
        )

    observer = SimpleNamespace(replay=replay)
    store = RecordingStore(activation)

    result = settle(
        cast(
            InstanceWiring, SimpleNamespace(store=store, observer=observer, paths=paths)
        ),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert result.awaiting is False
    assert observed == [exit_record]
    assert store.recorded == store.closed == 1


class ExitStoreDouble(StoreDouble):
    """Store double that exposes the effects-gate write as an observable result."""

    def __init__(self, activation: object) -> None:
        super().__init__(activation)
        self.opened = 0

    def open_gate(self, *args: object) -> object:
        """Leave the effects gate open so settlement must await approval."""
        self.opened += 1
        return SimpleNamespace(
            metadata=SimpleNamespace(state=GateState.OPEN, outcome=None),
            gate_id="effects",
        )

    def record_evidence(self, *args: object) -> object:
        """Expose the durable evidence write before the gate can await approval."""
        self.recorded += 1
        return self.activation


class RecordingStore(StoreDouble):
    """Store double that retains evidence and close payloads for settlement checks."""

    def __init__(self, activation: object) -> None:
        super().__init__(activation)
        self.evidence: Evidence | None = None
        self.deviations: tuple[Deviation, ...] = ()

    def record_evidence(self, *args: object) -> object:
        """Capture the P13 evidence write before returning the durable record."""
        self.recorded += 1
        self.evidence = cast(Evidence, args[1])
        return self.activation

    def close_activation(self, *args: object, **kwargs: object) -> object:
        """Capture deviations without re-deriving the completion."""
        self.closed += 1
        self.deviations = cast(tuple[Deviation, ...], kwargs.get("deviations", ()))
        return self.activation


def test_settle_records_evidence_then_awaits_the_effects_gate(
    fake_store: WorkflowStore,
) -> None:
    """Undeclared effects open a gate instead of closing the claimed outcome."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"lifecycle": Lifecycle.EXIT_RECORDED, "exit_record": object()}
            )
        }
    )
    store = ExitStoreDouble(activation)
    completion = CompletionEvidence(
        outcome=Outcome.DONE,
        claimed_outcome=Outcome.DONE,
        evidence=Evidence(
            undeclared_effects=("outside.txt",),
            artifact=ArtifactIdentity(commit_oid="c" * 40, tree_oid="t" * 40),
        ),
    )
    observer = SimpleNamespace(
        replay=lambda *args, **kwargs: SimpleNamespace(
            completion=completion, usage=None
        )
    )
    result = settle(
        cast(InstanceWiring, SimpleNamespace(store=store, observer=observer)),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )
    assert result.awaiting is True
    assert result.opened == "effects"
    assert store.recorded == 1
    assert store.opened == 1
    assert store.closed == 0


@pytest.mark.parametrize(
    ("gate_outcome", "closed_outcome"),
    ((Outcome.ABANDON, Outcome.FAIL_CODE), (Outcome.APPROVE, Outcome.DONE)),
)
def test_settle_closes_each_verified_effects_decision(
    fake_store: WorkflowStore,
    gate_outcome: Outcome,
    closed_outcome: Outcome,
) -> None:
    """A closed effects gate either discards or accepts the recorded residue."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"lifecycle": Lifecycle.EXIT_RECORDED, "exit_record": object()}
            )
        }
    )

    class ClosedEffectsStore(ExitStoreDouble):
        def __init__(self, activation: object) -> None:
            super().__init__(activation)
            self.outcome: Outcome | None = None
            self.reads = SimpleNamespace(
                load_gate=lambda _: SimpleNamespace(
                    metadata=SimpleNamespace(opening_outcome=Outcome.DONE)
                )
            )

        def open_gate(self, *args: object) -> object:
            self.opened += 1
            return SimpleNamespace(
                metadata=SimpleNamespace(state=GateState.CLOSED, outcome=gate_outcome),
                gate_id="effects",
            )

        def close_activation(self, *args: object, **kwargs: object) -> object:
            self.outcome = cast(Outcome, args[1])
            return super().close_activation(*args, **kwargs)

    store = ClosedEffectsStore(activation)
    completion = CompletionEvidence(
        outcome=Outcome.DONE,
        claimed_outcome=Outcome.DONE,
        evidence=Evidence(
            undeclared_effects=("outside.txt",),
            artifact=ArtifactIdentity(commit_oid="c" * 40, tree_oid="t" * 40),
        ),
    )
    observer = SimpleNamespace(
        replay=lambda *args, **kwargs: SimpleNamespace(
            completion=completion, usage=None
        )
    )
    result = settle(
        cast(InstanceWiring, SimpleNamespace(store=store, observer=observer)),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert result.awaiting is False
    assert store.outcome is closed_outcome


def test_settle_stalls_on_an_invalid_closed_effects_gate(
    fake_store: WorkflowStore,
) -> None:
    """A corrupt effects decision retains recorded evidence instead of looping."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"lifecycle": Lifecycle.EXIT_RECORDED, "exit_record": object()}
            )
        }
    )

    class InvalidEffectsStore(ExitStoreDouble):
        def open_gate(self, *args: object) -> object:
            self.opened += 1
            return SimpleNamespace(
                metadata=SimpleNamespace(
                    state=GateState.CLOSED, outcome=Outcome.REBUDGET
                ),
                gate_id="effects",
            )

    store = InvalidEffectsStore(activation)
    observer = SimpleNamespace(
        replay=lambda *args, **kwargs: SimpleNamespace(
            completion=CompletionEvidence(
                outcome=Outcome.DONE,
                claimed_outcome=Outcome.DONE,
                evidence=Evidence(
                    undeclared_effects=("outside.txt",),
                    artifact=ArtifactIdentity(commit_oid="c" * 40, tree_oid="t" * 40),
                ),
            ),
            usage=None,
        )
    )

    result = settle(
        cast(InstanceWiring, SimpleNamespace(store=store, observer=observer)),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert result.awaiting is False
    assert result.stalled == "effects gate has invalid outcome"
    assert store.recorded == 1


def test_settle_maps_replay_failures_to_error_transport(
    fake_store: WorkflowStore,
) -> None:
    """An unrecoverable exit is closed once as transport failure with its class."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"lifecycle": Lifecycle.EXIT_RECORDED, "exit_record": object()}
            )
        }
    )
    store = StoreDouble(activation)
    observer = SimpleNamespace(
        replay=lambda *args, **kwargs: (_ for _ in ()).throw(OSError())
    )
    settle(
        cast(InstanceWiring, SimpleNamespace(store=store, observer=observer)),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )
    assert store.closed == 1


def test_settle_replay_walks_back_to_the_prior_artifact_at_the_same_node(
    fake_store: WorkflowStore,
) -> None:
    """§10.5 compares rework attempts, not an intervening review activation."""
    root = make_root(fake_store, load_definition())
    seed = fake_store.mint_activation(root.root_id, entry_request()).activation
    previous = seed.model_copy(
        update={
            "bead": seed.bead.model_copy(update={"id": "previous"}),
            "metadata": seed.metadata.model_copy(
                update={
                    "node": "implement",
                    "lifecycle": Lifecycle.CLOSED,
                    "outcome": Outcome.DONE,
                    "evidence": Evidence(
                        artifact=ArtifactIdentity(
                            commit_oid="c" * 40, tree_oid="t" * 40
                        )
                    ),
                }
            ),
        }
    )
    review = seed.model_copy(
        update={
            "bead": seed.bead.model_copy(update={"id": "review"}),
            "metadata": seed.metadata.model_copy(
                update={
                    "node": "review",
                    "predecessor_activation_id": previous.activation_id,
                    "evidence": None,
                }
            ),
        }
    )
    activation = seed.model_copy(
        update={
            "bead": seed.bead.model_copy(update={"id": "current"}),
            "metadata": seed.metadata.model_copy(
                update={
                    "node": "implement",
                    "predecessor_activation_id": review.activation_id,
                    "lifecycle": Lifecycle.EXIT_RECORDED,
                    "exit_record": ExitRecord(
                        exit_code=0,
                        ended_at="2026-08-28T00:00:00Z",
                        reason="done",
                    ),
                }
            ),
        }
    )

    class PreviousStore(StoreDouble):
        def __init__(self) -> None:
            super().__init__(activation)
            self.reads = SimpleNamespace(
                load_activation={
                    previous.activation_id: previous,
                    review.activation_id: review,
                }.__getitem__
            )

        def record_evidence(self, *args: object) -> object:
            self.recorded += 1
            return activation

    previous_trees: list[str | None] = []

    def replay(*args: object, **kwargs: object) -> object:
        previous_trees.append(cast(str | None, kwargs["previous_tree_oid"]))
        return SimpleNamespace(
            completion=CompletionEvidence(
                outcome=Outcome.DONE, claimed_outcome=Outcome.DONE, evidence=Evidence()
            ),
            usage=None,
        )

    settle(
        cast(
            InstanceWiring,
            SimpleNamespace(
                store=PreviousStore(), observer=SimpleNamespace(replay=replay)
            ),
        ),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )

    assert previous_trees == ["t" * 40]


def test_settle_bounds_a_cyclic_predecessor_walk(
    fake_store: WorkflowStore, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A malformed predecessor cycle cannot keep a settlement tick in reads."""
    root = make_root(fake_store, load_definition())
    seed = fake_store.mint_activation(root.root_id, entry_request()).activation
    current = seed.model_copy(
        update={
            "bead": seed.bead.model_copy(update={"id": "current"}),
            "metadata": seed.metadata.model_copy(
                update={
                    "lifecycle": Lifecycle.EXIT_RECORDED,
                    "exit_record": ExitRecord(
                        exit_code=0,
                        ended_at="2026-08-28T00:00:00Z",
                        reason="done",
                    ),
                    "predecessor_activation_id": "cycle",
                }
            ),
        }
    )
    cycle = current.model_copy(
        update={
            "bead": current.bead.model_copy(update={"id": "cycle"}),
            "metadata": current.metadata.model_copy(
                update={"predecessor_activation_id": "current"}
            ),
        }
    )

    class CycleStore(RecordingStore):
        def __init__(self) -> None:
            super().__init__(current)
            self.lookups: list[str] = []
            self.reads = SimpleNamespace(load_activation=self.load_activation)

        def load_activation(self, activation_id: str) -> ActivationRecord:
            self.lookups.append(activation_id)
            return {"current": current, "cycle": cycle}[activation_id]

    previous_trees: list[str | None] = []

    def replay(*args: object, **kwargs: object) -> object:
        previous_trees.append(cast(str | None, kwargs["previous_tree_oid"]))
        return SimpleNamespace(
            completion=CompletionEvidence(
                outcome=Outcome.DONE,
                claimed_outcome=Outcome.DONE,
                evidence=Evidence(),
            ),
            usage=None,
        )

    observer = SimpleNamespace(replay=replay)
    store = CycleStore()
    monkeypatch.setattr(close_module, "_MAX_PREDECESSOR_HOPS", 2)

    settle(
        cast(InstanceWiring, SimpleNamespace(store=store, observer=observer)),
        root,
        root.index.nodes["implement"],
        current,
        SimpleNamespace(),
    )

    assert store.lookups == ["cycle", "current"]
    assert previous_trees == [None]


@pytest.mark.parametrize(
    ("again", "stalled", "deviation", "note"),
    [
        (BranchAdvanceOutcome.ADVANCED, None, None, True),
        (BranchAdvanceOutcome.UNCHANGED, None, None, True),
        (BranchAdvanceOutcome.DIVERGED, None, "instance_branch_diverged", False),
        (BranchAdvanceOutcome.MISSING, "instance branch missing", None, False),
    ],
)
def test_settle_replays_missing_branch_before_recording_evidence(
    fake_store: WorkflowStore,
    again: BranchAdvanceOutcome,
    stalled: str | None,
    deviation: str | None,
    note: bool,
) -> None:
    """A missing pinned branch either advances safely or stalls without a write."""
    root = make_root(fake_store, load_definition())
    activation = fake_store.mint_activation(root.root_id, entry_request()).activation
    activation = activation.model_copy(
        update={
            "metadata": activation.metadata.model_copy(
                update={"lifecycle": Lifecycle.EXIT_RECORDED, "exit_record": object()}
            )
        }
    )
    store = RecordingStore(activation)
    completion = CompletionEvidence(
        outcome=Outcome.DONE,
        claimed_outcome=Outcome.ACCEPT,
        evidence=Evidence(
            artifact=ArtifactIdentity(commit_oid="c" * 40, tree_oid="t" * 40)
        ),
        branch=BranchAdvance(outcome=BranchAdvanceOutcome.MISSING, target="c" * 40),
    )
    workspace = SimpleNamespace(
        advance_instance_branch=lambda *args, **kwargs: BranchAdvance(
            outcome=again, target="c" * 40
        )
    )
    observer = SimpleNamespace(
        replay=lambda *args, **kwargs: SimpleNamespace(
            completion=completion, usage=None
        )
    )
    result = settle(
        cast(
            InstanceWiring,
            SimpleNamespace(
                store=store, observer=observer, workspace=workspace, repo_root="."
            ),
        ),
        root,
        root.index.nodes["implement"],
        activation,
        SimpleNamespace(),
    )
    assert result.stalled == stalled
    if stalled is not None:
        assert store.recorded == store.closed == 0
    else:
        assert store.evidence is not None
        assert store.evidence.claimed_outcome is Outcome.ACCEPT
        assert tuple(item.kind for item in store.deviations) == (
            () if deviation is None else (deviation,)
        )
        assert (
            store.evidence.note == f"instance branch advanced at settle to {'c' * 40}"
        ) is note
