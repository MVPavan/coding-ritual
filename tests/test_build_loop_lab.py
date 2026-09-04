"""The lab can carry build-loop, not only feature-delivery (phase 7 B7).

Before slice B `ForemanLab` hard-bound feature-delivery's two roles and its one
instance input, so build-loop could not even be instantiated on it — the drills
slice D adds have to stand on this.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from tests._foreman import (
    BUILD_LOOP_INSTANCE_INPUTS,
    BUILD_LOOP_ROLES,
    DEFAULT_LAB_INSTANCE_INPUTS,
    DEFAULT_LAB_ROLES,
    ForemanLab,
)
from tests._helpers import BUILD_LOOP_GRAPH, runner_roles
from tests._supervisor import ChildScript, verifier_pins

ENTRY_NODE: Final[str] = "write_tests"
ACCEPTANCE_TEST: Final[str] = "tests/acceptance/test_lab.py"
ACCEPTANCE_SEED: Final[str] = "tests/acceptance/__init__.py"
WRITE_TESTS_SCRIPT: Final[ChildScript] = ChildScript(
    marker='{"outcome":"done"}\n',
    effects=f'{{"paths":["{ACCEPTANCE_TEST}"]}}',
    write_path=ACCEPTANCE_TEST,
    write_body="def test_lab() -> None:\n    assert False\n",
    commit=True,
)


# `write_tests`'s only declared check; slice C ships the real one. Its bytes are
# pinned at create, so an absent script would exit the activation `fail_code`.
TESTS_PARSE_CHECK: Final[str] = "scripts/checks/tests-parse.sh"


def _build_loop_lab(tmp_path: Path) -> ForemanLab:
    """A lab wired for build-loop's roles, instance inputs and entry check."""
    lab = ForemanLab(
        tmp_path,
        toml=BUILD_LOOP_GRAPH,
        roles=BUILD_LOOP_ROLES,
        instance_inputs=BUILD_LOOP_INSTANCE_INPUTS,
    )
    # `pin_checks` is the lab's "commit this before the root is pinned" seam. The
    # seed file is here because the fixture repo has no `tests/acceptance/`, and a
    # child redirecting into a missing directory dies before it can report.
    lab.pin_checks({TESTS_PARSE_CHECK: "#!/bin/sh\nexit 0\n", ACCEPTANCE_SEED: ""})
    # `pinned_config` pins feature-delivery's two scripts by name, so build-loop's
    # own check has to be pinned here or the wrapper refuses it (§7.3 provenance).
    lab.overrides.update(verifier_pins(lab.repo, ENTRY_NODE, TESTS_PARSE_CHECK))
    return lab


def test_the_lab_instantiates_build_loop(tmp_path: Path) -> None:
    """A root pins the graph with both instance inputs and no unbound role."""
    lab = _build_loop_lab(tmp_path)

    root = lab.instantiate()

    assert runner_roles(lab.definition) == set(BUILD_LOOP_ROLES)
    assert set(lab.config.roles) == set(BUILD_LOOP_ROLES)
    assert root.metadata.graph_content_hash == lab.definition.content_hash
    assert {
        pinned.name: pinned.body for pinned in root.metadata.instance_inputs
    } == BUILD_LOOP_INSTANCE_INPUTS


def test_the_lab_dispatches_the_build_loop_entry_node(tmp_path: Path) -> None:
    """One tick past `create` mints and launches `write_tests`.

    Instantiating proves nothing about the wrapper seam: the activation has to
    be minted with `write_tests`'s bound runner, launched, and exit on its own
    declared check. The recorded `runner_profile` is the BINDING's vendor name,
    not the graph's `profile:test-author` spelling.
    """
    lab = _build_loop_lab(tmp_path)
    lab.instantiate()
    lab.profiles.bind_node(ENTRY_NODE, WRITE_TESTS_SCRIPT)

    report = lab.tick()

    assert report.dispatched is not None
    assert not report.halted
    dispatched = lab.store.reads.load_activation(report.dispatched)
    assert dispatched.metadata.node == ENTRY_NODE
    assert dispatched.metadata.runner_profile == BUILD_LOOP_ROLES["test-author"].profile
    # The close (and with it the graded outcome) belongs to the NEXT tick; what
    # this one proves is that the child ran under the right runner and exited
    # cleanly.
    assert dispatched.metadata.exit_record is not None
    assert dispatched.metadata.exit_record.exit_code == 0


def test_the_lab_defaults_still_bind_feature_delivery(tmp_path: Path) -> None:
    """The new parameters' defaults are exactly what every prior drill got."""
    lab = ForemanLab(tmp_path)

    root = lab.instantiate()

    assert lab.config.roles == dict(DEFAULT_LAB_ROLES)
    assert {
        pinned.name: pinned.body for pinned in root.metadata.instance_inputs
    } == dict(DEFAULT_LAB_INSTANCE_INPUTS)
