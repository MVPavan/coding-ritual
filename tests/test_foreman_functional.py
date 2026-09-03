"""D2 functional drills at the real foreman tick seam."""

from __future__ import annotations

import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from tests._foreman import ForemanLab
from tests._helpers import VALID_FIXTURE, mutate, write
from tests._supervisor import ChildScript
from tests.conftest import Signer
from workflow_interpreter.bdio import (
    ActivationRecord,
    BoundMutation,
    Breaker,
    GateReason,
    Lifecycle,
    Outcome,
    SigningConfig,
    keys,
)
from workflow_interpreter.bdio.constants import (
    DEVIATION_INSTANCE_BRANCH_DIVERGED,
    DEVIATION_PRECONDITION_REFUSED,
)
from workflow_interpreter.bdio.wire import EventPayload
from workflow_interpreter.foreman.config import RunnerBinding
from workflow_interpreter.foreman.constants import DEVIATION_UNDECLARED_EFFECTS_ACCEPTED
from workflow_interpreter.foreman.gates import exhaustion_gate
from workflow_interpreter.foreman.routing import RouteKind, route
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.profiles.config import ProfileConfig, RunnerName
from workflow_interpreter.profiles.registry import ProfileRegistry
from workflow_interpreter.schema.models import Node
from workflow_interpreter.supervisor import (
    INSTANCE_BRANCH_REF,
    AuditFlag,
    BranchAdvanceOutcome,
    activation_ref,
)
from workflow_interpreter.supervisor.models import CompletionEvidence, PinResult
from workflow_interpreter.supervisor.paths import read_record
from workflow_interpreter.supervisor.workspace import Workspace

# Every test in this file is a §5 drill row (D2 functional drills).
pytestmark = pytest.mark.acceptance


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


def _ceiling_halted_review(
    tmp_path: Path, signing: SigningConfig, signer: Signer
) -> tuple[ForemanLab, str]:
    """Drive the same back-edge into a source-less instance-ceiling halt.

    The ceiling is checked before the region-round bound, so a tight enough
    `instance.max_total_activations` turns the would-be exhaustion breach into
    a plain halt with no source instead.
    """
    lab = ForemanLab(
        tmp_path,
        overrides={
            "region.build-review.max_entries": 1,
            "instance.max_total_activations": 2,
        },
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


def test_drill_21_ceiling_override_halts_then_rebudget_reopens_the_exhaustion_gate(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 21 catches a ceiling breach mistaken for the region's own exhaustion."""
    lab, halt_id = _ceiling_halted_review(
        tmp_path / "ceiling", signing_config, sign_payload
    )
    halted = lab.store.reads.load_gate(halt_id)
    assert halted.metadata.gate_reason is GateReason.HALT
    assert halted.metadata.source_activation_id is None

    lab.approve(
        halt_id,
        Outcome.REBUDGET,
        mutation=BoundMutation(key="instance.max_total_activations", value=5),
    )
    closed = lab.tick()
    assert closed.closed_gates == (halt_id,)

    exhaustion_id = lab.tick().opened_gate
    assert exhaustion_id is not None
    exhaustion = lab.store.reads.load_gate(exhaustion_id)
    assert exhaustion.metadata.gate_reason is GateReason.EXHAUSTION

    before_updates = lab.count("update")
    before_closes = lab.count("close")
    before_creates = lab.count("create")
    idle = lab.tick()
    assert idle.stalled is None
    assert idle.halted is False
    assert lab.count("update") == before_updates
    assert lab.count("close") == before_closes
    # The canary is exactly ONE `create` per tick (`crash_on_tick_create` skips
    # it with `occurrence + 1`, `tests/_foreman.py`), so "no write beyond the
    # canary" means the create count grows by exactly one. Snapshotting only
    # `update`/`close` left a duplicate gate or event bead invisible.
    assert lab.count("create") == before_creates + 1


def test_drill_21_ceiling_halt_approve_without_a_mutation_is_inert_and_re_halts_at_ordinal_1(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 21 catches an inert ceiling approve that fails to re-halt at ordinal 1."""
    lab, halt_id = _ceiling_halted_review(
        tmp_path / "ceiling-inert", signing_config, sign_payload
    )
    lab.approve(halt_id, Outcome.APPROVE)
    closed = lab.tick()
    assert closed.closed_gates == (halt_id,)

    re_halt = lab.tick().opened_gate
    assert re_halt is not None
    assert re_halt != halt_id
    assert lab.root is not None
    gate = lab.store.reads.load_gate(re_halt)
    assert gate.metadata.gate_reason is GateReason.HALT
    assert gate.metadata.source_activation_id is None
    assert gate.metadata.gate_key == keys.halt_gate_key(lab.root.root_id, 1)


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
    assert lab.root is not None
    assert exhausted.metadata.gate_key == keys.exhaustion_gate_key(
        lab.root.root_id, "build-review", 1
    )

    lab.approve(
        gate_id,
        Outcome.REBUDGET,
        mutation=BoundMutation(key="region.build-review.max_entries", value=2),
    )
    closed = lab.tick()
    successor = lab.tick().dispatched

    assert closed.closed_gates == (gate_id,)
    assert successor is not None
    assert lab.store.reads.load_activation(successor).metadata.round_no == 2
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
    exhaustion = lab.store.open_gate(
        root.root_id, exhaustion_gate(root.index, source, "triage")
    )
    no_progress = lab.store.reads.load_gate(no_progress_id)

    assert no_progress.metadata.gate_reason is GateReason.TRANSITION
    assert exhaustion.metadata.gate_reason is GateReason.EXHAUSTION
    assert no_progress.metadata.region == exhaustion.metadata.region == "build-review"
    assert no_progress.metadata.round_no == exhaustion.metadata.round_no
    assert no_progress.metadata.gate_key != exhaustion.metadata.gate_key


def test_a_breaker_gate_only_offers_outcomes_its_own_node_can_route(
    tmp_path: Path,
) -> None:
    """cr-mub: every verb a gate offers a human must lead somewhere.

    Found live, not in the lab. `no_progress_gate` and `exhaustion_gate`
    hardcoded a vocabulary per gate KIND while their target node declares its
    own; in the shipped graph `triage` declares `rebudget`/`abandon`, so the
    offered `approve` had no edge, fell to the graph fallback (`triage`, a
    GATE), and `cases.py` stalled with "gate route is not a task" on every
    subsequent tick — after consuming a valid signed approval. Picking the
    first offered outcome bricked the instance.

    Drill 23's own test asserts these two gates' region, round and key, and
    never their outcomes, which is why the lab stayed green.
    """
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
    exhaustion = lab.store.open_gate(
        root.root_id, exhaustion_gate(root.index, source, "triage")
    )

    for gate in (lab.store.reads.load_gate(no_progress_id), exhaustion):
        node = root.index.nodes[gate.metadata.gate_node]
        assert gate.metadata.outcomes, "a human gate must offer at least one verb"
        for outcome in gate.metadata.outcomes:
            decision = route(root.index, node, outcome)
            assert decision.kind in {RouteKind.TASK, RouteKind.TERMINAL}, (
                f"{gate.metadata.gate_node} offers {outcome.value}, "
                f"which routes {decision.kind}"
            )


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
    assert invalid.store.reads.load_gate(halt).metadata.halt_reason == (
        f"fail_code:implement:{invalid_id}"
    )
    assert len(invalid.beads("gate")) == 1
    assert len(invalid.beads("activation")) == 1

    empty = ForemanLab(
        tmp_path / "invalid-empty", signing=signing_config, signer=sign_payload
    )
    empty.instantiate()
    empty.profiles.next_script(ChildScript(marker="{}\n", effects='{"paths":[]}'))
    empty_id = empty.tick().dispatched
    assert empty_id is not None
    assert empty.tick().settled == empty_id
    empty_halt = empty.tick().opened_gate
    assert empty_halt is not None
    empty_closed = empty.store.reads.load_activation(empty_id)
    assert empty_closed.metadata.outcome is Outcome.FAIL_CODE
    assert empty_closed.metadata.evidence is not None
    assert empty_closed.metadata.evidence.claimed_outcome is None
    assert empty.store.reads.load_gate(empty_halt).metadata.gate_node == "halt"
    assert empty.store.reads.load_gate(empty_halt).metadata.halt_reason == (
        f"fail_code:implement:{empty_id}"
    )
    assert len(empty.beads("gate")) == 1
    assert len(empty.beads("activation")) == 1


def _undeclared_fail_code_halt(
    tmp_path: Path, signing: SigningConfig, signer: Signer
) -> tuple[ForemanLab, str, str]:
    """Close `implement` on an undeclared claim and open its dead-end halt."""
    lab = ForemanLab(tmp_path, signing=signing, signer=signer)
    lab.instantiate()
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id
    halt_id = lab.tick().opened_gate
    assert halt_id is not None
    return lab, activation_id, halt_id


def test_drill_25_halt_approve_remints_at_the_entry_node_with_the_dead_ends_round(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 25 catches an entry-node halt losing round_no or its origin event."""
    lab, failed_id, halt_id = _undeclared_fail_code_halt(
        tmp_path, signing_config, sign_payload
    )
    assert lab.root is not None
    failed = lab.store.reads.load_activation(failed_id)
    before_rounds = {
        activation.metadata.round_no
        for activation in lab.store.reads.list_activations(lab.root.root_id)
        if activation.metadata.region == "build-review"
    }

    lab.approve(halt_id, Outcome.APPROVE)
    assert lab.tick().closed_gates == (halt_id,)
    remint = lab.tick().dispatched
    assert remint is not None
    reminted = lab.store.reads.load_activation(remint)

    assert reminted.metadata.node == failed.metadata.node == "implement"
    assert reminted.metadata.predecessor_gate_id == halt_id
    assert reminted.metadata.round_no == 1
    after_rounds = {
        activation.metadata.round_no
        for activation in lab.store.reads.list_activations(lab.root.root_id)
        if activation.metadata.region == "build-review"
    }
    assert after_rounds == before_rounds

    events = [
        EventPayload.model_validate_json(row["payload"])
        for row in lab.beads("event")
        if isinstance(row["payload"], str)
    ]
    approvals = [
        event
        for event in events
        if (event.from_node, event.outcome, event.to_node)
        == ("halt", Outcome.APPROVE, "implement")
    ]
    assert len(approvals) == 1


def test_drill_25_halt_abandon_reaches_terminal(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 25 catches an entry-node halt that cannot be abandoned to terminal."""
    lab, _, halt_id = _undeclared_fail_code_halt(tmp_path, signing_config, sign_payload)
    lab.approve(halt_id, Outcome.ABANDON)
    assert lab.tick().closed_gates == (halt_id,)
    assert lab.tick().terminal is True


def test_drill_25_a_declared_fail_code_outcome_opens_triage_directly(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 25's sub-case catches a declared fail_code being routed through halt."""
    graph = write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (
                (
                    'outcomes      = ["done", "no_diff", "fail_plan"]',
                    'outcomes      = ["done", "no_diff", "fail_plan", "fail_code"]',
                ),
                (
                    '[[edge]]\nfrom = "implement"\non   = "no_diff"\nto   = "triage"\n\n',
                    (
                        '[[edge]]\nfrom = "implement"\non   = "no_diff"\nto   = "triage"\n\n'
                        '[[edge]]\nfrom = "implement"\non   = "fail_code"\nto   = "triage"\n\n'
                    ),
                ),
            ),
        ),
    )
    lab = ForemanLab(tmp_path, toml=graph, signing=signing_config, signer=sign_payload)
    lab.instantiate()
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"fail_code"}\n', effects='{"paths":[]}')
    )
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    assert lab.tick().settled == activation_id
    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.FAIL_CODE
    assert closed.metadata.evidence is not None
    assert closed.metadata.evidence.claimed_outcome is Outcome.FAIL_CODE

    gate = lab.store.reads.load_gate(gate_id)
    assert gate.metadata.gate_node == "triage"
    assert gate.metadata.opening_outcome is Outcome.FAIL_CODE
    assert all(row["metadata"].get("halt_reason") is None for row in lab.beads("gate"))


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
                    'isolation     = "worktree"               # worktree | in-repo',
                    'isolation     = "in-repo"                # worktree | in-repo',
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

    lab.tick()
    assert len(lab.beads("activation")) == 1

    lab.approve(halt, Outcome.APPROVE)
    assert lab.tick().closed_gates == (halt,)
    second_id = lab.tick().dispatched
    assert second_id is not None
    second_refused = lab.store.reads.load_activation(second_id)
    assert second_refused.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert second_refused.metadata.round_no == 1
    second_halt = lab.tick().opened_gate
    assert second_halt is not None
    assert second_halt != halt
    assert lab.store.reads.load_gate(second_halt).metadata.halt_reason == (
        f"precondition_refused:implement:{second_id}"
    )
    assert lab.root is not None
    assert lab.store.reads.load_gate(
        second_halt
    ).metadata.gate_key == keys.halt_gate_key(lab.root.root_id, 1)

    human_file.unlink()
    lab.approve(second_halt, Outcome.APPROVE)
    assert lab.tick().closed_gates == (second_halt,)
    third_id = lab.tick().dispatched
    assert third_id is not None
    third = lab.store.reads.load_activation(third_id)
    assert third.metadata.round_no == 1
    assert third.metadata.lifecycle is Lifecycle.EXIT_RECORDED


def test_drill_26_a_real_infra_failure_after_the_dirty_tree_recovery_keeps_the_full_budget(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """Drill 26 catches the refused dirty-tree closes being counted against P14's budget."""
    graph = write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (
                (
                    'isolation     = "worktree"               # worktree | in-repo',
                    'isolation     = "in-repo"                # worktree | in-repo',
                ),
                ("max_entries  = 3", "max_entries  = 1"),
            ),
        ),
    )
    lab = ForemanLab(tmp_path, toml=graph, signing=signing_config, signer=sign_payload)
    lab.instantiate()
    assert lab.root is not None
    human_file = lab.repo / "human.txt"
    human_file.write_text("do not reset me\n", encoding="utf-8")

    for _ in range(3):
        lab.tick()
    first_halt = next(
        row for row in lab.beads("gate") if row["metadata"].get("state") == "open"
    )
    lab.approve(str(first_halt["id"]), Outcome.APPROVE)
    for _ in range(3):
        lab.tick()

    human_file.unlink()
    second_halt = next(
        row for row in lab.beads("gate") if row["metadata"].get("state") == "open"
    )
    lab.approve(str(second_halt["id"]), Outcome.APPROVE)

    max_infra_retries = lab.root.index.nodes["implement"].max_infra_retries
    assert max_infra_retries is not None

    lab.profiles.next_script(ChildScript(exit_code=1))
    assert lab.tick().closed_gates == (str(second_halt["id"]),)
    implement_id = lab.tick().dispatched
    assert implement_id is not None
    lab.tick()

    for _ in range(max_infra_retries):
        lab.tick()
        lab.tick()

    error_runner_closes = [
        row
        for row in lab.beads("activation")
        if row["metadata"].get("node") == "implement"
        and row["metadata"].get("round_no") == 1
        and row["metadata"].get("outcome") == "error_runner"
    ]
    assert len(error_runner_closes) == 1 + max_infra_retries


# -- IN-REPO row, sub-cases (a) and (e) (scratchpad/probes/phase5-plan.md:357) --

_EMPTY_TREE_OID = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def _in_repo_implement_graph(tmp_path: Path) -> Path:
    """The row's premise: `implement` in-repo, `review` stays worktree."""
    return write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (
                (
                    'isolation     = "worktree"               # worktree | in-repo',
                    'isolation     = "in-repo"                # worktree | in-repo',
                ),
            ),
        ),
    )


def _detached_commit(repo: Path, message: str) -> str:
    """A commit reachable by no branch and sharing no history with `repo`'s HEAD.

    Built through `commit-tree` plumbing so the checked-out branch and HEAD are
    never touched. That distinction matters: moving the INSTANCE branch ref
    (`refs/heads/wf/<root>`, what row clause (a) means by "the branch") is a
    different fact than moving the repo's own checked-out HEAD, which would
    instead trip `_plan`'s protected-head refusal in `workspace.py` — a
    different mechanism (a dirty/foreign-HEAD precondition refusal, Drill 26's
    territory) that this row's (a) does not describe.
    """
    result = subprocess.run(
        ["git", "commit-tree", _EMPTY_TREE_OID, "-m", message],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "human",
            "GIT_AUTHOR_EMAIL": "human@test",
            "GIT_COMMITTER_NAME": "human",
            "GIT_COMMITTER_EMAIL": "human@test",
        },
    )
    return result.stdout.strip()


def _diverged_instance_branch_halt(
    tmp_path: Path,
    signing: SigningConfig,
    signer: Signer,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ForemanLab, str, str]:
    """Move the instance branch to an unrelated commit before round 1's pin.

    Row clause (a) names the ordering precisely: the branch has to still be at
    its ORIGINAL value when round 1 mints (its `intended_base_commit` is read
    from the branch right there, `mint.py`'s `_derive_base_commit`) and when
    its precondition verifies HEAD — and diverged only by the time
    `pin_artifact` runs, after the child has already committed. A single
    `lab.tick()` runs mint, precondition, launch AND `pin_artifact` inline
    (`InlineSpawner` is synchronous), with no test-visible pause between them,
    so the move is injected by wrapping `Workspace.pin_artifact` itself: the
    first call moves the branch immediately before delegating to the real
    implementation, which is the latest and only point that is honestly
    "before the pin" without also corrupting the mint or the precondition.
    """
    graph = _in_repo_implement_graph(tmp_path)
    lab = ForemanLab(tmp_path, toml=graph, signing=signing, signer=signer)
    root = lab.instantiate()
    branch_ref = INSTANCE_BRANCH_REF.format(root_id=root.root_id)
    unrelated = _detached_commit(lab.repo, "human moves the branch")

    original_pin_artifact = Workspace.pin_artifact
    moved = False

    def _pin_after_the_branch_moves(
        self: Workspace,
        activation: ActivationRecord,
        node: Node,
        *,
        declared: frozenset[str] | None = None,
        quarantine: bool = False,
    ) -> PinResult:
        nonlocal moved
        if not moved:
            lab.git.update_ref(branch_ref, unrelated, cwd=lab.repo)
            moved = True
        return original_pin_artifact(
            self, activation, node, declared=declared, quarantine=quarantine
        )

    monkeypatch.setattr(Workspace, "pin_artifact", _pin_after_the_branch_moves)

    activation_id = lab.tick().dispatched
    assert activation_id is not None
    original = read_record(
        lab.wiring().paths.completion(activation_id), CompletionEvidence
    )
    assert original is not None
    assert AuditFlag.INSTANCE_BRANCH_DIVERGED in original.audit_flags
    assert original.branch is not None
    assert original.branch.outcome is BranchAdvanceOutcome.DIVERGED
    assert original.branch.previous == unrelated
    assert original.outcome is Outcome.DONE
    assert original.evidence.artifact is not None
    pinned_commit = original.evidence.artifact.commit_oid
    assert original.branch.target == pinned_commit
    assert (
        lab.git.ref_target(activation_ref(root.root_id, activation_id), cwd=lab.repo)
        == pinned_commit
    )
    assert lab.git.ref_target(branch_ref, cwd=lab.repo) == unrelated

    # `completion.json` deleted => the next settle's replay recomputes rather
    # than reusing the cache, and must land on the identical flag and branch.
    lab.wiring().paths.completion(activation_id).unlink()
    assert lab.tick().settled == activation_id
    replayed = read_record(
        lab.wiring().paths.completion(activation_id), CompletionEvidence
    )
    assert replayed is not None
    assert AuditFlag.INSTANCE_BRANCH_DIVERGED in replayed.audit_flags
    assert replayed.branch == original.branch

    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.DONE
    assert any(
        deviation.kind == DEVIATION_INSTANCE_BRANCH_DIVERGED
        for deviation in closed.metadata.deviations
    )

    halt_id = lab.tick().opened_gate
    assert halt_id is not None
    halt = lab.store.reads.load_gate(halt_id)
    assert (
        halt.metadata.halt_reason
        == f"instance_branch_diverged:implement:{activation_id}"
    )
    assert halt.metadata.source_activation_id == activation_id
    # NO review mint: the diverged activation is a dead end, never a routable
    # head (`frontier.py`'s `candidates_a` excludes anything `_dead_end` flags).
    assert len(lab.beads("activation")) == 1
    return lab, activation_id, halt_id


def test_in_repo_branch_diverged_halt_approve_remints_at_round_ones_base(
    tmp_path: Path,
    signing_config: SigningConfig,
    sign_payload: Signer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Row clause (a): halt approve re-mints `implement` from round 1's OWN
    `pre_attempt_commit`, never from the diverged (and still untouched) branch."""
    lab, activation_id, halt_id = _diverged_instance_branch_halt(
        tmp_path, signing_config, sign_payload, monkeypatch
    )
    round1 = lab.store.reads.load_activation(activation_id)
    expected_base = round1.metadata.pre_attempt_commit
    assert expected_base is not None

    lab.approve(halt_id, Outcome.APPROVE)
    assert lab.tick().closed_gates == (halt_id,)
    remint_id = lab.tick().dispatched
    assert remint_id is not None
    reminted = lab.store.reads.load_activation(remint_id)
    assert reminted.metadata.node == "implement"
    assert reminted.metadata.intended_base_commit == expected_base


def test_in_repo_branch_diverged_halt_abandon_reaches_terminal(
    tmp_path: Path,
    signing_config: SigningConfig,
    sign_payload: Signer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Row clause (a): halt abandon reaches terminal, with no gate-origin re-mint."""
    lab, _activation_id, halt_id = _diverged_instance_branch_halt(
        tmp_path, signing_config, sign_payload, monkeypatch
    )
    lab.approve(halt_id, Outcome.ABANDON)
    assert lab.tick().closed_gates == (halt_id,)
    assert lab.tick().terminal is True


def test_in_repo_worktree_review_branch_advance_is_unchanged(
    tmp_path: Path,
    signing_config: SigningConfig,
    sign_payload: Signer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Row clause (e): H3 — review's worktree is checked out `-B wf/<root>` at
    the base (`gitio.py`'s `worktree_add`), so the runner's own commit already
    moves the instance branch; the wrapper's own advance finds nothing left to
    do (`BranchAdvance.unchanged`), and never calls `update_ref_cas`.
    """
    graph = _in_repo_implement_graph(tmp_path)
    lab = ForemanLab(tmp_path, toml=graph, signing=signing_config, signer=sign_payload)
    lab.instantiate()

    impl_id = lab.tick().dispatched
    assert impl_id is not None
    assert lab.tick().settled == impl_id

    # `reject`, not `accept`: `exit.py`'s `_grade_success_claim` runs its own
    # §7.3 anti-drift cross-check on the JUDGMENT_OUTCOME claim (`accept`) and
    # fails it closed whenever `verified` (the commit checks ran at) drifts
    # from `intended_base_commit` — which a commit always does. That is a
    # real, separate FAIL_CODE path, not the one row clause (e) is about, so
    # `reject` (a failure claim, never routed through that cross-check) is
    # what isolates the branch-advance mechanism cleanly.
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"reject"}\n',
            effects='{"paths":["findings.txt"]}',
            write_path="findings.txt",
            write_body="reviewed - needs work\n",
            commit=True,
            artifact_path="review.md",
            artifact_body="please rework\n",
        )
    )
    cas_calls: list[tuple[str, str, str]] = []
    original_cas = lab.git.update_ref_cas

    def _spy_cas(ref: str, new: str, old: str, *, cwd: Path) -> bool:
        cas_calls.append((ref, new, old))
        return original_cas(ref, new, old, cwd=cwd)

    monkeypatch.setattr(lab.git, "update_ref_cas", _spy_cas)

    report = lab.tick()
    review_id = report.dispatched
    assert review_id is not None
    assert report.stalled is None

    completion = read_record(
        lab.wiring().paths.completion(review_id), CompletionEvidence
    )
    assert completion is not None
    assert completion.branch is not None
    assert completion.branch.outcome is BranchAdvanceOutcome.UNCHANGED
    # `update_ref_cas` is the ONLY call site that ever touches the instance
    # branch ref (`workspace.py`'s `advance_instance_branch`): zero calls is
    # the literal "no branch update-ref" the row states.
    assert cas_calls == []
    # A short-name ref (`wf/<root>` instead of `refs/heads/wf/<root>`) makes
    # `Git.ref_target` raise `GitCommandError` immediately (`gitio.py`'s "ref
    # must start with refs/" guard). `_post_exit` catches `SupervisorError`
    # and converts it into a swallowed `fail_code`/`VERIFY_UNRUNNABLE` verdict
    # rather than letting it propagate — so "NO GitCommandError" is observed
    # here as the ABSENCE of that fail-closed verdict, not as a raised
    # exception the test process would ever see.
    assert completion.outcome is Outcome.REJECT
    assert AuditFlag.VERIFY_UNRUNNABLE not in completion.audit_flags


def test_in_repo_implement_happy_path_advances_branch_and_binds_ship_gate(
    tmp_path: Path,
    signing_config: SigningConfig,
    sign_payload: Signer,
) -> None:
    """The row's HEAD clause (cr-o85.33.12, scratchpad/probes/phase5-plan.md:357):
    an in-repo `implement` claims `done` with no interference at all — no
    human, no deletion, no divergence. All four named facts must land: the
    instance branch advances to the pinned commit, `review` is minted against
    that same commit, the reviewer's worktree is checked out there, and the
    `ship` gate that review's `accept` later opens binds to it too.
    """
    graph = _in_repo_implement_graph(tmp_path)
    lab = ForemanLab(tmp_path, toml=graph, signing=signing_config, signer=sign_payload)
    root = lab.instantiate()
    branch_ref = INSTANCE_BRANCH_REF.format(root_id=root.root_id)

    impl_id = lab.tick().dispatched
    assert impl_id is not None
    assert lab.tick().settled == impl_id

    closed = lab.store.reads.load_activation(impl_id)
    assert closed.metadata.outcome is Outcome.DONE
    assert closed.metadata.evidence is not None
    artifact = closed.metadata.evidence.artifact
    assert artifact is not None

    # "after implement: ref_target(wf branch) == artifact.commit_oid"
    assert lab.git.ref_target(branch_ref, cwd=lab.repo) == artifact.commit_oid

    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    review_id = lab.tick().dispatched
    assert review_id is not None
    review_activation = lab.store.reads.load_activation(review_id)
    assert review_activation.metadata.node == "review"

    # "`review` minted with intended_base_commit == artifact.commit_oid"
    assert review_activation.metadata.intended_base_commit == artifact.commit_oid

    # "the reviewer's worktree is created at that commit"
    worktree = lab.wiring().paths.worktree
    assert lab.git.head_commit(cwd=worktree) == artifact.commit_oid

    # `Workspace.prepare` SELF-HEALS a wrong head: `_plan` sets
    # `head_move_required` and `_apply` runs `reset_hard(intended)`, so a
    # head-move defect leaves every assertion above still green. The one thing
    # it cannot hide is the durable pre-reset pin the reset writes first
    # (workspace.py:391). Absence of that ref is what says the head was ALREADY
    # right rather than corrected on the way — same ref shape asserted present
    # in the rework case at tests/test_foreman_drills.py:624.
    for activation_id in (impl_id, review_id):
        assert (
            lab.git.ref_target(
                f"refs/wf/{root.root_id}/prereset/{activation_id}",
                cwd=lab.repo,
            )
            is None
        )

    assert lab.tick().settled == review_id
    accepted = lab.store.reads.load_activation(review_id)
    assert accepted.metadata.outcome is Outcome.ACCEPT

    ship_id = lab.tick().opened_gate
    assert ship_id is not None
    ship_gate = lab.store.reads.load_gate(ship_id)

    # "ship gate binds it" — bound to the very commit named in the clauses
    # above, the same way `test_drill_27_...`'s final invariant (c) reads the
    # SAME field for the worktree-isolation case (test_foreman_e2e.py).
    assert ship_gate.metadata.artifact_ref == artifact.commit_oid


def test_a_dispatched_task_carries_its_nodes_instructions_and_facts(
    tmp_path: Path,
) -> None:
    """ADR 0002: the brief a REAL dispatch builds, not one a test composed.

    `DefaultComposer` is unit-tested directly, but that proves nothing about
    the production wiring at `_task_builder`. Bypassing the composer there was
    killed by exactly one test, and that test is about the §13 forced-reject
    clause — so instructions and the fact frame would have been silently
    droppable the moment §13 changed. Same species as the defect recorded at
    `.claude/project/learnings.md` on test doubles satisfying a protocol.
    """
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    implement_id = lab.tick().dispatched
    assert implement_id is not None

    task = next(
        item
        for item in lab.profiles.profile.tasks
        if item.activation_id == implement_id
    )
    node = next(
        item for item in lab.definition.document.node if item.name == "implement"
    )

    assert node.instructions is not None
    assert node.instructions.strip() in task.brief
    # The facts the runner cannot derive from its inputs.
    assert "implement" in task.brief
    assert lab.definition.document.graph.id in task.brief
    assert "declared facts" in task.brief.lower()
    # And the §6 protocol is still there — the frame is an addition, not a swap.
    assert "$WF_OUTCOME_FILE" in task.brief
