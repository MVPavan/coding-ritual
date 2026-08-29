"""D2 flagged-graph end-to-end drill at the durable foreman seam."""

from __future__ import annotations

from pathlib import Path

from tests._foreman import ForemanLab, LockedPersistentBd
from tests._helpers import VALID_FIXTURE, mutate, write
from tests._supervisor import ChildScript
from tests.conftest import Signer
from workflow_interpreter.bdio import Outcome, SigningConfig
from workflow_interpreter.foreman.constants import FORCED_FIRST_REJECT


def test_drill_27_pins_the_opt_in_and_forces_only_the_first_review_brief(
    tmp_path: Path, signing_config: SigningConfig, sign_payload: Signer
) -> None:
    """DRILL-27 catches a flagged pin or forced-rejection clause lost on rebuild."""
    flagged = write(
        tmp_path,
        mutate(
            VALID_FIXTURE.read_text(encoding="utf-8"),
            (("test_force_first_reject = false", "test_force_first_reject = true"),),
        ),
    )
    state = tmp_path / "persistent-bd.json"

    def persistent(workspace: str) -> LockedPersistentBd:
        return LockedPersistentBd(workspace, state)

    lab = ForemanLab(
        tmp_path,
        toml=flagged,
        allow_test_flags=True,
        signing=signing_config,
        signer=sign_payload,
        bd_factory=persistent,
    )
    root = lab.instantiate()
    implement = lab.tick().dispatched
    assert implement is not None
    assert lab.tick().settled == implement
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"reject"}\n',
            effects='{"paths":[]}',
            artifact_path="review.md",
            artifact_body="request a rework",
        )
    )
    review = lab.tick().dispatched
    assert review is not None
    briefs = {task.activation_id: task.brief for task in lab.profiles.profile.tasks}
    assert FORCED_FIRST_REJECT not in briefs[implement]
    assert FORCED_FIRST_REJECT in briefs[review]

    lab.rebuild()
    rebuilt_root = lab.store.reads.load_root(root.root_id)
    assert rebuilt_root.metadata.allow_test_flags is True
    assert lab.tick().settled == review
    lab.profiles.next_script(
        ChildScript(
            marker='{"outcome":"done"}\n',
            effects='{"paths":["src/feature.py"]}',
            write_path="src/feature.py",
            write_body="value = 3\n",
            commit=True,
        )
    )
    rework = lab.tick().dispatched
    assert rework is not None
    assert lab.tick().settled == rework
    lab.profiles.next_script(
        ChildScript(marker='{"outcome":"accept"}\n', effects='{"paths":[]}')
    )
    accepted = lab.tick().dispatched
    assert accepted is not None
    assert lab.tick().settled == accepted
    ship = lab.tick().opened_gate
    assert ship is not None
    lab.approve(ship, Outcome.APPROVE)
    assert lab.tick().closed_gates == (ship,)
    assert lab.tick().terminal is True
