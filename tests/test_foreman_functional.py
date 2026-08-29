"""D2 functional drills at the real foreman tick seam."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from tests._foreman import ForemanLab
from tests._helpers import VALID_FIXTURE, mutate, write
from tests._supervisor import ChildScript
from tests.conftest import Signer
from workflow_interpreter.bdio import (
    BoundMutation,
    Breaker,
    GateReason,
    Outcome,
    SigningConfig,
)
from workflow_interpreter.bdio.constants import DEVIATION_PRECONDITION_REFUSED
from workflow_interpreter.foreman.config import RunnerBinding
from workflow_interpreter.foreman.constants import DEVIATION_UNDECLARED_EFFECTS_ACCEPTED
from workflow_interpreter.foreman.gates import exhaustion_gate
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.profiles.config import ProfileConfig, RunnerName
from workflow_interpreter.profiles.registry import ProfileRegistry


def _exhausted_review(
    tmp_path: Path, signing: SigningConfig, signer: Signer
) -> tuple[ForemanLab, str]:
    """Drive the fixture's first back-edge into its max-entry exhaustion gate."""
    lab = ForemanLab(
        tmp_path,
        overrides={"region.build-review.max_entries": 1},
        signing=signing,
        signer=signer,
    )
    lab.instantiate()
    implement = lab.tick().dispatched
    assert implement is not None
    assert lab.tick().settled == implement
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"reject"}\n',
            effects='{"paths":[]}',
            artifact_path="review.md",
            artifact_body="rework this",
        )
    )
    review = lab.tick().dispatched
    assert review is not None
    assert lab.tick().settled == review
    gate = lab.tick().opened_gate
    assert gate is not None
    return lab, gate


def test_drill_21_rebudget_and_abandon_preserve_the_exhaustion_gate(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 21 catches a capped back-edge that bypasses its unique gate."""
    lab, gate_id = _exhausted_review(
        tmp_path / "rebudget", signing_config, sign_payload
    )
    exhausted = lab.store.reads.load_gate(gate_id)
    assert exhausted.metadata.gate_reason.value == "exhaustion"
    assert exhausted.metadata.round_no == 1

    lab.approve(
        gate_id,
        Outcome.REBUDGET,
        mutation=BoundMutation(key="region.build-review.max_entries", value=2),
    )
    closed = lab.tick()
    successor = lab.tick().dispatched

    assert closed.closed_gates == (gate_id,)
    assert successor is not None
    gate = lab.store.reads.load_gate(gate_id)
    assert gate.metadata.bound_key == "region.build-review.max_entries"
    assert gate.metadata.bound_value == 2
    assert len(lab.beads("gate")) == 1

    abandoned, abandon_gate = _exhausted_review(
        tmp_path / "abandon", signing_config, sign_payload
    )
    abandoned.approve(abandon_gate, Outcome.ABANDON)
    assert abandoned.tick().closed_gates == (abandon_gate,)
    assert abandoned.tick().terminal is True


def test_drill_22_missing_registry_binary_exhausts_infra_retries_to_fallback(
    tmp_path: Path,
) -> None:
    """Drill 22 drives the real registry's exit-127 path through its fallback."""
    lab = ForemanLab(tmp_path)
    missing_binary = tmp_path / "missing-codex"
    config = lab.config.model_copy(
        update={
            "roles": {
                "implementer": RunnerBinding(profile="codex"),
                "critic": RunnerBinding(profile="codex"),
            }
        }
    )
    profiles = ProfileRegistry(
        ProfileConfig(binary_overrides={RunnerName.CODEX: str(missing_binary)}),
        lab.supervisor_config,
        lab.clock,
        {},
    )
    lab.composition = replace(lab.composition, config=config, profiles=profiles)
    lab.spawner.bind(lab.composition)
    lab.foreman = Foreman(lab.composition)
    lab.instantiate()

    activation_ids: list[str] = []
    for _ in range(3):
        dispatched = lab.tick().dispatched
        assert dispatched is not None
        activation_ids.append(dispatched)
        assert lab.tick().settled == dispatched

    gate_id = lab.tick().opened_gate

    assert [
        lab.store.reads.load_activation(activation_id).metadata.outcome
        for activation_id in activation_ids
    ] == [Outcome.ERROR_RUNNER] * 3
    assert gate_id is not None
    gate = lab.store.reads.load_gate(gate_id)
    assert gate.metadata.opening_outcome is Outcome.ERROR_RUNNER
    assert gate.metadata.gate_node == "triage"


def test_drill_23_no_progress_and_exhaustion_open_distinct_region_gates(
    tmp_path: Path,
) -> None:
    """Drill 23 preserves both gates when a repeated tree trips the breaker."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    initial = lab.tick().dispatched
    assert initial is not None
    assert lab.tick().settled == initial
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"reject"}\n',
            effects='{"paths":[]}',
            artifact_path="review.md",
            artifact_body="rework this",
        )
    )
    review = lab.tick().dispatched
    assert review is not None
    assert lab.tick().settled == review
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 2\n",
            commit=True,
        )
    )
    rework = lab.tick().dispatched
    assert rework is not None
    assert lab.tick().settled == rework

    no_progress_id = lab.tick().opened_gate
    assert no_progress_id is not None
    source = lab.store.reads.load_activation(rework)
    assert source.metadata.evidence is not None
    assert source.metadata.evidence.breaker is Breaker.NO_PROGRESS
    exhaustion = lab.store.open_gate(root.root_id, exhaustion_gate(source, "triage"))
    no_progress = lab.store.reads.load_gate(no_progress_id)

    assert no_progress.metadata.gate_reason is GateReason.TRANSITION
    assert exhaustion.metadata.gate_reason is GateReason.EXHAUSTION
    assert no_progress.metadata.region == exhaustion.metadata.region == "build-review"
    assert no_progress.metadata.round_no == exhaustion.metadata.round_no
    assert no_progress.metadata.gate_key != exhaustion.metadata.gate_key


def test_drill_25_distinguishes_a_declared_fallback_from_an_undeclared_claim(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 25 catches a closed outcome enum being routed through fallback."""
    (tmp_path / "no-diff").mkdir()
    no_diff_graph = write(
        tmp_path / "no-diff",
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (
                (
                    '[[edge]]\nfrom = "implement"\non   = "no_diff"\nto   = "triage"\n\n',
                    "",
                ),
            ),
        ),
    )
    fallback = ForemanLab(
        tmp_path / "no-diff",
        toml=no_diff_graph,
        signing=signing_config,
        signer=sign_payload,
    )
    fallback.instantiate()
    fallback.profiles.next_script(
        ChildScript(marker='{"outcome":"no_diff"}\n', effects='{"paths":[]}')
    )
    activation = fallback.tick().dispatched
    assert activation is not None
    assert fallback.tick().settled == activation
    gate_id = fallback.tick().opened_gate
    assert gate_id is not None
    assert fallback.store.reads.load_gate(gate_id).metadata.gate_node == "triage"

    invalid = ForemanLab(
        tmp_path / "invalid", signing=signing_config, signer=sign_payload
    )
    invalid.instantiate()
    invalid.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    invalid_id = invalid.tick().dispatched
    assert invalid_id is not None
    assert invalid.tick().settled == invalid_id
    halt = invalid.tick().opened_gate
    assert halt is not None
    closed = invalid.store.reads.load_activation(invalid_id)
    assert closed.metadata.outcome is Outcome.FAIL_CODE
    assert closed.metadata.evidence is not None
    assert closed.metadata.evidence.claimed_outcome is None
    assert invalid.store.reads.load_gate(halt).metadata.gate_node == "halt"


def test_drill_24_requires_a_signed_decision_for_undeclared_effects(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 24 catches an out-of-bound artifact that advances without a gate."""
    lab = ForemanLab(tmp_path, signing=signing_config, signer=sign_payload)
    lab.instantiate()
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects='{"paths":[]}',
            write_path="outside.py",
            write_body="blocked = True\n",
            commit=True,
        )
    )
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled is None
    gates = lab.beads("gate")
    assert len(gates) == 1
    gate_id = str(gates[0]["id"])
    assert (
        lab.store.reads.load_activation(activation_id).metadata.lifecycle.value
        == "evidence-recorded"
    )

    lab.approve(gate_id, Outcome.APPROVE)
    assert lab.tick().closed_gates == (gate_id,)
    assert lab.tick().settled == activation_id
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.DONE
    assert closed.metadata.deviations[-1].kind == DEVIATION_UNDECLARED_EFFECTS_ACCEPTED


def test_drill_26_refuses_human_dirty_in_repo_state_without_counting_infra(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 26 catches a dirty-tree refusal mistaken for band contention."""
    graph = write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (
                (
                    'runner        = "profile:implementer"\nmodel         = "default"\nisolation     = "worktree"',
                    'runner        = "profile:implementer"\nmodel         = "default"\nisolation     = "in-repo"',
                ),
                ("max_entries  = 3", "max_entries  = 1"),
            ),
        ),
    )
    lab = ForemanLab(tmp_path, toml=graph, signing=signing_config, signer=sign_payload)
    lab.instantiate()
    human_file = lab.repo / "human.txt"
    human_file.write_text("do not reset me\n", encoding="utf-8")

    activation_id = lab.tick().dispatched
    assert activation_id is not None
    refused = lab.store.reads.load_activation(activation_id)
    halt = lab.tick().opened_gate

    assert human_file.read_text(encoding="utf-8") == "do not reset me\n"
    assert refused.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert len(refused.metadata.deviations) == 1
    assert refused.metadata.deviations[0].kind == DEVIATION_PRECONDITION_REFUSED
    assert "human.txt" in refused.metadata.deviations[0].reason
    assert refused.metadata.evidence is not None
    assert refused.metadata.evidence.note is not None
    assert "human.txt" in refused.metadata.evidence.note
    assert halt is not None
    assert lab.store.reads.load_gate(halt).metadata.halt_reason == (
        f"precondition_refused:implement:{activation_id}"
    )
