"""Focused C2a contracts for foreman gate requests."""

import json
import uuid
from pathlib import Path
from typing import cast

import pytest

from tests._bdio import entry_request, load_definition, make_root
from tests._foreman import ForemanLab
from tests.conftest import Signer
from workflow_interpreter.bdio import (
    Evidence,
    GateOpenRequest,
    GateReason,
    GateRecord,
    GateState,
    GateVerificationError,
    SigningConfig,
    StaleApprovalError,
)
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.carriers import ArtifactIdentity
from workflow_interpreter.foreman import gates as gates_module
from workflow_interpreter.foreman.constants import (
    HALT_BRANCH_DIVERGED,
    HALT_FAIL_CODE,
    HALT_PRECONDITION_REFUSED,
)
from workflow_interpreter.foreman.gates import (
    effects_gate,
    exhaustion_gate,
    halt_gate,
    intake,
    no_progress_gate,
    payload_template,
    resume_hint,
    transition_gate,
)
from workflow_interpreter.schema.graph_index import build_index
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.profile import Profile


def test_transition_gate_copies_source_round_and_verified_identity(
    fake_store: WorkflowStore,
) -> None:
    """D-G1 binds the gate to the source artifact and preserves round facts."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    source = source.model_copy(
        update={
            "metadata": source.metadata.model_copy(
                update={
                    "evidence": Evidence(
                        artifact=ArtifactIdentity(
                            commit_oid="c" * 40, tree_oid="t" * 40
                        )
                    )
                }
            )
        }
    )
    request = transition_gate(
        cast(Git, object()),
        Path("."),
        build_index(root.definition.document, allow_test_flags=False),
        "ship",
        source,
        Outcome.ACCEPT,
    )
    assert request.artifact_ref == "c" * 40
    assert request.artifact_digest == "t" * 40
    assert request.region == source.metadata.region
    assert request.round_no == source.metadata.round_no


def test_halt_gate_carries_a_source_only_for_dead_end_reasons(
    fake_store: WorkflowStore,
) -> None:
    """Q14 keeps regular halts source-less while dead ends remain resumable."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    dead_end = halt_gate(f"fail_code:implement:{source.activation_id}", source=source)
    ordinary = halt_gate("ceiling:20", source=source)
    assert dead_end.source_activation_id == source.activation_id
    assert dead_end.round_no == source.metadata.round_no
    assert ordinary.source_activation_id is None
    assert ordinary.round_no is None


@pytest.mark.parametrize(
    "reason",
    (HALT_FAIL_CODE, HALT_BRANCH_DIVERGED, HALT_PRECONDITION_REFUSED),
)
def test_dead_end_halts_require_their_source(reason: str) -> None:
    """D-H2 refuses a dead-end halt that could not resume its source."""
    with pytest.raises(ValueError, match="dead-end halt requires its source"):
        halt_gate(reason.format(node="implement", activation_id="activation"))


def test_each_gate_opener_carries_its_distinguishing_fields(
    fake_store: WorkflowStore,
) -> None:
    """The five constructors cannot collapse distinct gate semantics together."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    transition = transition_gate(
        cast(Git, object()),
        Path("."),
        root.index,
        "ship",
        source.model_copy(
            update={
                "metadata": source.metadata.model_copy(
                    update={
                        "evidence": Evidence(
                            artifact=ArtifactIdentity(
                                commit_oid="c" * 40, tree_oid="t" * 40
                            )
                        )
                    }
                )
            }
        ),
        Outcome.ACCEPT,
    )
    exhaustion = exhaustion_gate(root.index, source, "triage")
    no_progress_source = source.model_copy(
        update={
            "metadata": source.metadata.model_copy(update={"outcome": Outcome.NO_DIFF})
        }
    )
    no_progress = no_progress_gate(root.index, no_progress_source, "triage")
    effects = effects_gate(
        source,
        Outcome.DONE,
        ArtifactIdentity(commit_oid="c" * 40, tree_oid="t" * 40),
    )
    halt = halt_gate("ceiling:20")
    assert transition.artifact_digest == "t" * 40
    assert exhaustion.gate_reason.value == "exhaustion"
    assert no_progress.gate_reason is GateReason.TRANSITION
    assert no_progress.opening_outcome is no_progress_source.metadata.outcome
    assert effects.gate_node == "effects"
    assert effects.opening_outcome is Outcome.DONE
    assert halt.gate_reason.value == "halt"


@pytest.mark.parametrize("no_progress_first", (True, False))
def test_no_progress_and_exhaustion_gates_open_in_one_region_and_round(
    fake_store: WorkflowStore, no_progress_first: bool
) -> None:
    """Their distinct semantics must not share the exhaustion key."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    source = fake_store.close_activation(source.activation_id, Outcome.NO_DIFF)

    no_progress_request = no_progress_gate(root.index, source, "triage")
    exhaustion_request = exhaustion_gate(root.index, source, "triage")
    first, second = (
        (no_progress_request, exhaustion_request)
        if no_progress_first
        else (exhaustion_request, no_progress_request)
    )

    first_gate = fake_store.open_gate(root.root_id, first)
    second_gate = fake_store.open_gate(root.root_id, second)

    assert first_gate.metadata.gate_key != second_gate.metadata.gate_key


class ProfileDouble:
    """Boundary double for the profile-owned resume command."""

    def build_resume_hint(self, session_id: str) -> str:
        """Return a recognizable command for the chosen session."""
        return f"resume {session_id}"


def test_resume_hint_and_refused_intake_report_a_durable_refusal(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A missing session and a refused signature cannot fabricate a gate close."""
    root = make_root(fake_store, load_definition())
    source = fake_store.mint_activation(root.root_id, entry_request()).activation
    source = source.model_copy(
        update={"metadata": source.metadata.model_copy(update={"session_id": ""})}
    )
    assert resume_hint(cast(Profile, ProfileDouble()), source) is None

    class RefusingStore:
        calls = 0

        def close_gate_verified(self, *args: object, **kwargs: object) -> object:
            self.calls += 1
            raise GateVerificationError("bad signature")

    gate = cast(
        GateRecord,
        type(
            "Gate",
            (),
            {"metadata": type("Meta", (), {"gate_key": "g"})(), "gate_id": "g"},
        )(),
    )
    inbox = tmp_path / "g"
    inbox.mkdir()
    (inbox / "payload.json").write_bytes(b"{}")
    (inbox / "payload.json.sig").write_bytes(b"bad")
    store = RefusingStore()
    result = intake(cast(WorkflowStore, store), root, gate, tmp_path)
    assert result.gate is None
    assert result.refusal == "bad signature"
    assert json.loads((inbox / "refusal.json").read_text(encoding="utf-8")) == {
        "error": "GateVerificationError",
        "reason": "bad signature",
    }
    assert store.calls == 1


def test_successful_intake_clears_an_earlier_refusal_receipt(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """A later verified close must not leave a stale refusal for the human."""
    root = make_root(fake_store, load_definition())
    gate = fake_store.open_gate(root.root_id, halt_gate("ceiling:20"))

    class RefusingStore:
        def close_gate_verified(self, *args: object, **kwargs: object) -> object:
            raise GateVerificationError("bad signature")

    class ClosingStore:
        def close_gate_verified(self, *args: object, **kwargs: object) -> GateRecord:
            return gate

    inbox = tmp_path / gate.metadata.gate_key
    inbox.mkdir()
    (inbox / "payload.json").write_bytes(b"{}")
    (inbox / "payload.json.sig").write_bytes(b"signature")
    intake(cast(WorkflowStore, RefusingStore()), root, gate, tmp_path)
    assert (inbox / "refusal.json").exists()

    result = intake(cast(WorkflowStore, ClosingStore()), root, gate, tmp_path)

    assert result.gate is gate
    assert not (inbox / "refusal.json").exists()


def test_refusal_receipt_write_failure_does_not_escape_intake(
    fake_store: WorkflowStore, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A receipt is diagnostic only; its filesystem failure cannot crash a tick."""
    root = make_root(fake_store, load_definition())
    gate = fake_store.open_gate(root.root_id, halt_gate("ceiling:20"))

    class RefusingStore:
        def close_gate_verified(self, *args: object, **kwargs: object) -> object:
            raise GateVerificationError("bad signature")

    def write_fails(*args: object, **kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(gates_module, "write_durable", write_fails)
    inbox = tmp_path / gate.metadata.gate_key
    inbox.mkdir()
    (inbox / "payload.json").write_bytes(b"{}")
    (inbox / "payload.json.sig").write_bytes(b"signature")

    result = intake(cast(WorkflowStore, RefusingStore()), root, gate, tmp_path)

    assert result.refusal == "bad signature"
    assert not (inbox / "refusal.json").exists()


@pytest.mark.parametrize("missing", ("payload.json", "payload.json.sig"))
def test_intake_leaves_a_gate_open_until_both_signed_files_exist(
    fake_store: WorkflowStore, tmp_path: Path, missing: str
) -> None:
    """Intake does not attempt a decision from a partial inbox payload."""
    root = make_root(fake_store, load_definition())

    class UncalledStore:
        def close_gate_verified(self, *args: object, **kwargs: object) -> object:
            raise AssertionError("partial gate inbox must stay open")

    gate = cast(
        GateRecord,
        type(
            "Gate",
            (),
            {"metadata": type("Meta", (), {"gate_key": "g"})(), "gate_id": "g"},
        )(),
    )
    inbox = tmp_path / "g"
    inbox.mkdir()
    (inbox / ({"payload.json", "payload.json.sig"} - {missing}).pop()).write_bytes(b"x")

    result = intake(cast(WorkflowStore, UncalledStore()), root, gate, tmp_path)
    assert result.gate is None
    assert result.refusal is None
    assert not (inbox / "refusal.json").exists()


def test_intake_reports_a_stale_approval_without_closing_the_gate(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """Drill 8 preserves the stale-approval reason for the human to repair."""
    root = make_root(fake_store, load_definition())

    class RefusingStore:
        def close_gate_verified(self, *args: object, **kwargs: object) -> object:
            raise StaleApprovalError("document changed")

    gate = cast(
        GateRecord,
        type(
            "Gate",
            (),
            {"metadata": type("Meta", (), {"gate_key": "g"})(), "gate_id": "g"},
        )(),
    )
    inbox = tmp_path / "g"
    inbox.mkdir()
    (inbox / "payload.json").write_bytes(b"{}")
    (inbox / "payload.json.sig").write_bytes(b"bad")

    result = intake(cast(WorkflowStore, RefusingStore()), root, gate, tmp_path)

    assert result.gate is None
    assert result.refusal == "document changed"
    assert (
        json.loads((inbox / "refusal.json").read_text(encoding="utf-8"))["error"]
        == "StaleApprovalError"
    )


def test_intake_reports_the_gate_it_closed(
    fake_store: WorkflowStore, tmp_path: Path
) -> None:
    """The caller can distinguish a verified close from an absent inbox."""
    root = make_root(fake_store, load_definition())
    gate = fake_store.open_gate(root.root_id, halt_gate("ceiling:20"))

    class ClosingStore:
        def close_gate_verified(self, *args: object, **kwargs: object) -> GateRecord:
            return gate

    inbox = tmp_path / gate.metadata.gate_key
    inbox.mkdir()
    (inbox / "payload.json").write_bytes(b"{}")
    (inbox / "payload.json.sig").write_bytes(b"signature")

    result = intake(cast(WorkflowStore, ClosingStore()), root, gate, tmp_path)

    assert result.gate is gate
    assert result.refusal is None
    assert not (inbox / "refusal.json").exists()


def test_payload_template_closes_each_human_gate_kind(
    gate_store: WorkflowStore, sign_payload: Signer
) -> None:
    """§3 #7 templates are the exact bytes a human signs to close each gate."""
    for gate_kind in ("transition", "exhaustion", "no_progress", "halt"):
        root = make_root(gate_store, load_definition())
        source = gate_store.mint_activation(root.root_id, entry_request()).activation
        source = source.model_copy(
            update={
                "metadata": source.metadata.model_copy(update={"outcome": Outcome.DONE})
            }
        )
        if gate_kind == "transition":
            artifact = ArtifactIdentity(commit_oid="c" * 40, tree_oid="t" * 40)
            transition_source = source.model_copy(
                update={
                    "metadata": source.metadata.model_copy(
                        update={"evidence": Evidence(artifact=artifact)}
                    )
                }
            )
            request = transition_gate(
                cast(Git, object()),
                Path("."),
                root.index,
                "ship",
                transition_source,
                Outcome.ACCEPT,
            )
        elif gate_kind == "exhaustion":
            request = exhaustion_gate(root.index, source, "triage")
        elif gate_kind == "no_progress":
            request = no_progress_gate(root.index, source, "ship")
        else:
            request = halt_gate("ceiling:20")

        gate = gate_store.open_gate(root.root_id, request)
        payload_bytes = (
            payload_template(root, gate)
            .replace("replace-with-a-unique-nonce", uuid.uuid4().hex)
            .encode("utf-8")
        )

        closed = gate_store.close_gate_verified(
            root.root_id,
            gate.gate_id,
            payload_bytes=payload_bytes,
            signature=sign_payload(payload_bytes, None),
        )

        assert closed.metadata.state is GateState.CLOSED


def test_lab_approve_writes_an_intake_payload_for_the_next_tick(
    signing_config: SigningConfig, sign_payload: Signer, tmp_path: Path
) -> None:
    """The lab reaches the real render, sign, and verified-close path."""
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    root = lab.instantiate()
    gate = lab.store.open_gate(root.root_id, halt_gate("ceiling:20"))

    lab.approve(gate.gate_id, Outcome.APPROVE)
    report = lab.tick()
    closed = lab.store.reads.load_gate(gate.gate_id)

    assert closed.metadata.state is GateState.CLOSED
    assert closed.metadata.outcome is Outcome.APPROVE
    assert report.closed_gates == (gate.gate_id,)


def test_lab_intake_closes_halt_before_another_ready_gate(
    signing_config: SigningConfig, sign_payload: Signer, tmp_path: Path
) -> None:
    """The real tick gives a serial halt precedence over every ordinary gate."""
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    root = lab.instantiate()
    halt = lab.store.open_gate(root.root_id, halt_gate("ceiling:20"))
    source = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    ship = lab.store.open_gate(
        root.root_id,
        GateOpenRequest(
            gate_node="ship",
            outcomes=(Outcome.APPROVE, Outcome.ABANDON),
            source_activation_id=source.activation_id,
            opening_outcome=Outcome.ACCEPT,
        ),
    )
    lab.approve(halt.gate_id, Outcome.APPROVE)
    lab.approve(ship.gate_id, Outcome.APPROVE)

    report = lab.tick()

    assert report.closed_gates == (halt.gate_id, ship.gate_id)
