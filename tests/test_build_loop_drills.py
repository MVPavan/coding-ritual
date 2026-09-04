"""Build-loop lifecycle drills on the real foreman seams (phase 7 D1).

`tests/test_build_loop_graph.py` proves the graph is legal and
`tests/test_build_loop_lab.py` proves the lab can carry it; what is left — and
what slices A and B were for — is that the loop actually RUNS: both regions,
the cross-region input binding, the rework and exhaustion back-edges, the
no-progress breaker, and the `fail_code` edges that used to dead-end.

Everything here runs on fake bd and real git, with the five verify scripts
stubbed to tiny passing bodies: slice C ships the real ones, and a drill that
waited on `mutate.sh` would cost 25 minutes to say nothing about routing.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Final

import pytest

from tests._foreman import (
    BUILD_LOOP_INSTANCE_INPUTS,
    BUILD_LOOP_ROLES,
    ForemanLab,
)
from tests._helpers import BUILD_LOOP_GRAPH
from tests._supervisor import ChildScript, verifier_pins
from tests.conftest import Signer
from workflow_interpreter.bdio import (
    BoundMutation,
    Breaker,
    GateReason,
    Outcome,
    SigningConfig,
)

# Every test in this file is a phase-7 D1 drill row.
pytestmark = pytest.mark.acceptance

NODE_WRITE_TESTS: Final[str] = "write_tests"
NODE_REVIEW_TESTS: Final[str] = "review_tests"
NODE_IMPLEMENT: Final[str] = "implement"
NODE_REVIEW_IMPL: Final[str] = "review_impl"
NODE_CRITIC: Final[str] = "critic"
NODE_SLICE_GATE: Final[str] = "slice_gate"
NODE_TRIAGE_TESTS: Final[str] = "triage_tests"
NODE_TRIAGE_BUILD: Final[str] = "triage_build"

# The tests region's `max_entries`, as `triage_tests` rebudgets it (§9 bound key).
TESTS_MAX_ENTRIES: Final[str] = "region.tests.max_entries"

INPUT_ACCEPTANCE_TESTS: Final[str] = "acceptance_tests"
INPUT_TEST_FINDINGS: Final[str] = "test_findings"

# The verify list each node declares in `workflows/build-loop.toml`; the §7.3
# digests are pinned per node AND program, so a drill that pins less than the
# graph names exits its first activation `fail_code` on a missing pin.
CHECK_TESTS_PARSE: Final[str] = "scripts/checks/tests-parse.sh"
CHECK_ASSERTION_STRENGTH: Final[str] = "scripts/checks/assertion-strength.sh"
CHECK_TESTS_UNTOUCHED: Final[str] = "scripts/checks/tests-untouched.sh"
CHECK_MUTATE: Final[str] = "scripts/checks/mutate.sh"
CHECK_GATE: Final[str] = "scripts/verify-feature.sh"
REVIEWER_CHECKS: Final[tuple[str, ...]] = (
    CHECK_TESTS_PARSE,
    CHECK_ASSERTION_STRENGTH,
)
VERIFY_SETS: Final[Mapping[str, tuple[str, ...]]] = {
    NODE_WRITE_TESTS: (CHECK_TESTS_PARSE,),
    NODE_REVIEW_TESTS: REVIEWER_CHECKS,
    NODE_IMPLEMENT: (CHECK_GATE, CHECK_TESTS_UNTOUCHED, CHECK_MUTATE),
    NODE_REVIEW_IMPL: REVIEWER_CHECKS,
    NODE_CRITIC: REVIEWER_CHECKS,
}

PASSING_CHECK: Final[str] = "#!/bin/sh\nexit 0\n"

# The fixture repo has neither directory, and a child redirecting into a
# missing one dies before it can report an outcome.
ACCEPTANCE_SEED: Final[str] = "tests/acceptance/__init__.py"
IMPLEMENTATION_SEED: Final[str] = "workflow_interpreter/__init__.py"
ACCEPTANCE_TEST: Final[str] = "tests/acceptance/test_slice.py"
IMPLEMENTATION_MODULE: Final[str] = "workflow_interpreter/slice.py"
FINDINGS_FILE: Final[str] = "findings.md"

FIRST_TESTS: Final[str] = "def test_slice() -> None:\n    assert slice_value() == 1\n"
SECOND_TESTS: Final[str] = "def test_slice() -> None:\n    assert slice_value() == 2\n"
FIRST_IMPL: Final[str] = "def slice_value() -> int:\n    return 1\n"
SECOND_IMPL: Final[str] = "def slice_value() -> int:\n    return 2\n"
REJECTION: Final[str] = "1. BLOCKER tests/acceptance/test_slice.py:1 cannot fail"
ACCEPTANCE: Final[str] = "no blocking findings"


def _armed_check(flag: Path) -> str:
    """A check body that is red exactly while `flag` exists on disk.

    Reviewer nodes share one script set against one commit, so a drill cannot
    make a check red for `critic` alone by editing bytes — the §7.3 pin would
    refuse them anyway. The flag lives outside the repo, so arming it between
    two ticks leaves every pinned digest intact.
    """
    return f"#!/bin/sh\nif [ -f {flag} ]; then exit 1; fi\nexit 0\n"


def _build_loop_lab(
    tmp_path: Path,
    *,
    checks: Mapping[str, str] | None = None,
    signing: SigningConfig | None = None,
    signer: Signer | None = None,
) -> ForemanLab:
    """A lab wired for build-loop with every declared verify script pinned."""
    lab = ForemanLab(
        tmp_path,
        toml=BUILD_LOOP_GRAPH,
        roles=BUILD_LOOP_ROLES,
        instance_inputs=BUILD_LOOP_INSTANCE_INPUTS,
        signing=signing,
        signer=signer,
    )
    bodies: dict[str, str] = {
        name: PASSING_CHECK for scripts in VERIFY_SETS.values() for name in scripts
    }
    bodies.update(checks or {})
    lab.pin_checks({**bodies, ACCEPTANCE_SEED: "", IMPLEMENTATION_SEED: ""})
    for node, scripts in VERIFY_SETS.items():
        lab.overrides.update(verifier_pins(lab.repo, node, *scripts))
    return lab


def _tests_script(body: str) -> ChildScript:
    """A `write_tests` child that commits one acceptance test."""
    return ChildScript(
        marker='{"outcome":"done"}\n',
        effects=f'{{"paths":["{ACCEPTANCE_TEST}"]}}',
        write_path=ACCEPTANCE_TEST,
        write_body=body,
        commit=True,
    )


def _implement_script(body: str) -> ChildScript:
    """An `implement` child that commits one module under its allowed path."""
    return ChildScript(
        marker='{"outcome":"done"}\n',
        effects=f'{{"paths":["{IMPLEMENTATION_MODULE}"]}}',
        write_path=IMPLEMENTATION_MODULE,
        write_body=body,
        commit=True,
    )


def _review_script(outcome: str, note: str) -> ChildScript:
    """A reviewer child: no repo write, one findings file in its outputs.

    The findings are realistic input CONTENT, not a binding precondition: the
    exit path pins an outputs ref unconditionally and commits an empty tree for
    a silent reviewer, so `critic` binds `test_findings` either way. Writing
    them keeps the drill's reviewers carrying the bytes a real one would.
    """
    return ChildScript(
        marker=f'{{"outcome":"{outcome}"}}\n',
        effects='{"paths":[]}',
        artifact_path=FINDINGS_FILE,
        artifact_body=note,
    )


def _run_node(lab: ForemanLab, node: str, script: ChildScript) -> str:
    """Dispatch `node`'s child and settle it, returning its activation id."""
    lab.profiles.bind_node(node, script)
    dispatched = lab.tick().dispatched
    assert dispatched is not None
    assert lab.store.reads.load_activation(dispatched).metadata.node == node
    assert lab.tick().settled == dispatched
    return dispatched


def _bindings(lab: ForemanLab, activation_id: str) -> dict[str, str]:
    """The producer each input of one activation was bound to at mint."""
    activation = lab.store.reads.load_activation(activation_id)
    return {
        binding.name: binding.producer_activation_id
        for binding in activation.metadata.inputs
    }


def test_the_happy_path_runs_both_regions_to_slice_done(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """One accepted slice: tests written and reviewed, built, reviewed, signed.

    The two binding assertions are the reason this drill exists at all: before
    slice A `implement` could not bind `acceptance_tests` across the region
    boundary, and `critic` did not declare `test_findings` at all.
    """
    lab = _build_loop_lab(tmp_path, signing=signing_config, signer=sign_payload)
    lab.instantiate()

    write_tests = _run_node(lab, NODE_WRITE_TESTS, _tests_script(FIRST_TESTS))
    review_tests = _run_node(
        lab, NODE_REVIEW_TESTS, _review_script("accept", ACCEPTANCE)
    )
    implement = _run_node(lab, NODE_IMPLEMENT, _implement_script(FIRST_IMPL))
    _run_node(lab, NODE_REVIEW_IMPL, _review_script("accept", ACCEPTANCE))
    critic = _run_node(lab, NODE_CRITIC, _review_script("accept", ACCEPTANCE))

    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    gate = lab.store.reads.load_gate(gate_id)
    assert gate.metadata.gate_node == NODE_SLICE_GATE
    lab.approve(gate_id, Outcome.APPROVE)
    assert lab.tick().closed_gates == (gate_id,)
    assert lab.tick().terminal is True

    assert _bindings(lab, implement)[INPUT_ACCEPTANCE_TESTS] == write_tests
    assert _bindings(lab, critic)[INPUT_TEST_FINDINGS] == review_tests


def test_a_rejected_test_round_rebinds_implement_to_the_second_round_tests(
    tmp_path: Path,
) -> None:
    """The tests region reworks, and `implement` binds the round it accepted.

    Binding the FIRST round's tests here would be silent and wrong: the
    implementer would build against exactly the tests its reviewer rejected.
    """
    lab = _build_loop_lab(tmp_path)
    lab.instantiate()

    _run_node(lab, NODE_WRITE_TESTS, _tests_script(FIRST_TESTS))
    _run_node(lab, NODE_REVIEW_TESTS, _review_script("reject", REJECTION))
    second_tests = _run_node(lab, NODE_WRITE_TESTS, _tests_script(SECOND_TESTS))
    _run_node(lab, NODE_REVIEW_TESTS, _review_script("accept", ACCEPTANCE))
    implement = _run_node(lab, NODE_IMPLEMENT, _implement_script(FIRST_IMPL))

    assert lab.store.reads.load_activation(second_tests).metadata.round_no == 2
    assert _bindings(lab, implement)[INPUT_ACCEPTANCE_TESTS] == second_tests


def test_two_rejected_test_rounds_exhaust_the_region_then_rebudget_re_enters(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """`max_entries = 2` ends the tests region at `triage_tests`, not at a stall."""
    lab = _build_loop_lab(tmp_path, signing=signing_config, signer=sign_payload)
    lab.instantiate()

    _run_node(lab, NODE_WRITE_TESTS, _tests_script(FIRST_TESTS))
    _run_node(lab, NODE_REVIEW_TESTS, _review_script("reject", REJECTION))
    _run_node(lab, NODE_WRITE_TESTS, _tests_script(SECOND_TESTS))
    _run_node(lab, NODE_REVIEW_TESTS, _review_script("reject", REJECTION))

    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    gate = lab.store.reads.load_gate(gate_id)
    assert gate.metadata.gate_node == NODE_TRIAGE_TESTS
    assert gate.metadata.gate_reason is GateReason.EXHAUSTION

    lab.approve(
        gate_id,
        Outcome.REBUDGET,
        mutation=BoundMutation(key=TESTS_MAX_ENTRIES, value=3),
    )
    assert lab.tick().closed_gates == (gate_id,)
    successor = lab.tick().dispatched
    assert successor is not None
    reopened = lab.store.reads.load_activation(successor)
    assert reopened.metadata.node == NODE_WRITE_TESTS
    assert reopened.metadata.round_no == 3


def test_an_unchanged_rework_tree_opens_triage_build_instead_of_looping(
    tmp_path: Path,
) -> None:
    """§10.5: a second `implement` with the rejected tree is no progress."""
    lab = _build_loop_lab(tmp_path)
    lab.instantiate()

    _run_node(lab, NODE_WRITE_TESTS, _tests_script(FIRST_TESTS))
    _run_node(lab, NODE_REVIEW_TESTS, _review_script("accept", ACCEPTANCE))
    _run_node(lab, NODE_IMPLEMENT, _implement_script(FIRST_IMPL))
    _run_node(lab, NODE_REVIEW_IMPL, _review_script("reject", REJECTION))
    repeated = _run_node(lab, NODE_IMPLEMENT, _implement_script(FIRST_IMPL))

    gate_id = lab.tick().opened_gate
    assert gate_id is not None
    evidence = lab.store.reads.load_activation(repeated).metadata.evidence
    assert evidence is not None
    assert evidence.breaker is Breaker.NO_PROGRESS
    gate = lab.store.reads.load_gate(gate_id)
    assert gate.metadata.gate_node == NODE_TRIAGE_BUILD
    assert gate.metadata.gate_reason is GateReason.TRANSITION


def test_a_red_check_at_the_critic_routes_back_to_implement(tmp_path: Path) -> None:
    """The B2 edge under test: `critic --fail_code--> implement`.

    Before slice B no node declared `fail_code` and no edge carried it, so a
    check the last reader could not run ended the instance in a dead end.
    """
    flag = tmp_path / "critic-red"
    lab = _build_loop_lab(
        tmp_path, checks={CHECK_ASSERTION_STRENGTH: _armed_check(flag)}
    )
    lab.instantiate()

    _run_node(lab, NODE_WRITE_TESTS, _tests_script(FIRST_TESTS))
    _run_node(lab, NODE_REVIEW_TESTS, _review_script("accept", ACCEPTANCE))
    _run_node(lab, NODE_IMPLEMENT, _implement_script(FIRST_IMPL))
    _run_node(lab, NODE_REVIEW_IMPL, _review_script("accept", ACCEPTANCE))
    flag.write_text("", encoding="utf-8")
    critic = _run_node(lab, NODE_CRITIC, _review_script("accept", ACCEPTANCE))

    assert lab.store.reads.load_activation(critic).metadata.outcome is Outcome.FAIL_CODE
    successor = lab.tick().dispatched
    assert successor is not None
    reworked = lab.store.reads.load_activation(successor)
    assert reworked.metadata.node == NODE_IMPLEMENT
    assert reworked.metadata.round_no == 2


def test_a_red_check_at_implement_re_enters_implement_as_a_new_round(
    tmp_path: Path,
) -> None:
    """The self-edge `implement --fail_code--> implement`, rounds still capping it."""
    flag = tmp_path / "implement-red"
    flag.write_text("", encoding="utf-8")
    lab = _build_loop_lab(tmp_path, checks={CHECK_TESTS_UNTOUCHED: _armed_check(flag)})
    lab.instantiate()

    _run_node(lab, NODE_WRITE_TESTS, _tests_script(FIRST_TESTS))
    _run_node(lab, NODE_REVIEW_TESTS, _review_script("accept", ACCEPTANCE))
    failed = _run_node(lab, NODE_IMPLEMENT, _implement_script(FIRST_IMPL))
    flag.unlink()
    repaired = _run_node(lab, NODE_IMPLEMENT, _implement_script(SECOND_IMPL))

    assert lab.store.reads.load_activation(failed).metadata.outcome is Outcome.FAIL_CODE
    green = lab.store.reads.load_activation(repaired)
    assert green.metadata.outcome is Outcome.DONE
    assert green.metadata.round_no == 2
