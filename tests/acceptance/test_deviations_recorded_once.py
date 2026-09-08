"""A deviation is recorded ONCE per activation close (bead cr-n2z.9).

`WorkflowStore.close_activation` owns the merge — it stores
`(*record.metadata.deviations, *deviations)` — so every caller may hand it only
the deviations THIS close adds. `foreman/finalize.py::decide`,
`foreman/close.py::settle` and `foreman/close.py::_completion_deviations` hand
it the activation's existing ones as well, and each close therefore writes the
carried deviations two or three times.

Every test here seeds ONE prior deviation on the activation through the public
`MintRequest.deviations` field, drives a real close through `ForemanLab`, and
reads `store.reads.load_activation(...).metadata.deviations` back off bd. The
observable is the ordered list of kinds (and, where two entries share a kind,
their reasons) — never a length.

None of them can be satisfied by deleting the merge from `close_activation`
instead of correcting its callers, and each says in its own docstring which
list the current code writes and which list that alternative would write.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest

from tests._bdio import handle
from tests._foreman import ForemanLab, entry_request
from tests._supervisor import ChildScript
from tests.conftest import Signer
from workflow_interpreter.bdio import Deviation, Outcome, SigningConfig
from workflow_interpreter.bdio.constants import (
    DEVIATION_BOUND_VIOLATED,
    DEVIATION_UNDECLARED_EFFECTS_ACCEPTED,
)
from workflow_interpreter.supervisor.sandbox import SandboxMode
from workflow_interpreter.supervisor.steer import DEVIATION_KIND_STEER

pytestmark = pytest.mark.acceptance

DONE_MARKER: Final[str] = '{"outcome":"done"}\n'
GRANTED_FILE: Final[str] = "src/feature.py"
"""Inside the implement node's `allowed_paths` (`src/**`)."""
UNGRANTED_FILE: Final[str] = "outside.py"
"""Outside it, so a write here is what §7 attributes as an undeclared effect."""
CARRIED_REASON: Final[str] = "carried in from an earlier steer"
"""The prior deviation's reason: distinct text, so a second `steer` entry on the
same record is told apart from the one the activation arrived with."""
STEER_REASON: Final[str] = "silent past stale_after"
CARRIED_AT: Final[str] = "2026-09-01T00:00:00Z"


@dataclass(frozen=True)
class _Signing:
    """`tests/conftest.py`'s two §9 fixtures as ONE test parameter.

    Not sugar: `scripts/checks/assertion-strength.sh` reads a test's body as
    the lines indented deeper than its `def`, so a signature wrapped across
    lines reads as a test with no assertions at all.
    """

    config: SigningConfig
    sign: Signer


@pytest.fixture
def signing(signing_config: SigningConfig, sign_payload: Signer) -> _Signing:
    """The allow-listed key and its signer, paired for the effects gate."""
    return _Signing(config=signing_config, sign=sign_payload)


def _mint_carrying_a_prior_deviation(lab: ForemanLab) -> str:
    """Mint the instance's entry activation with one deviation already on it.

    The §3.2 entry idempotency key is `hash(root_id, "entry")` and carries no
    payload, so the frontier's own `mint_entry` re-finds this activation rather
    than minting a second one: the next `lab.tick()` dispatches THIS record.
    `MintRequest.deviations` is the public way an activation comes to carry a
    deviation before it is ever closed.
    """
    assert lab.root is not None
    carried = Deviation(
        kind=DEVIATION_KIND_STEER, reason=CARRIED_REASON, recorded_at=CARRIED_AT
    )
    minted = (
        lab.wiring()
        .store.mint_activation(
            lab.root.root_id,
            entry_request(deviations=(carried,)),
        )
        .activation
    )
    return minted.activation_id


def _say_the_bound_was_on(lab: ForemanLab, activation_id: str) -> None:
    """Amend the receipt to `bwrap` and drop the cached verdict, so §7 re-runs.

    The bound is exactly what makes an out-of-grant write impossible, so the
    child runs UNBOUNDED and the receipt is then amended to say the bound was
    on; deleting `completion.json` makes the settle tick recompute §7 against
    what the worktree now holds. The four lines are written out rather than
    imported from `tests/test_supervisor_sandbox_bound.py`, whose helper is
    private to that module.
    """
    receipt_path = lab.wiring().paths.receipt(activation_id)
    body = json.loads(receipt_path.read_text(encoding="utf-8"))
    body["sandbox"] = SandboxMode.BWRAP.value
    receipt_path.write_text(json.dumps(body), encoding="utf-8")
    lab.wiring().paths.completion(activation_id).unlink()


def _kinds_and_reasons(lab: ForemanLab, activation_id: str) -> list[tuple[str, str]]:
    """The durable deviation list of one closed activation, in order."""
    closed = lab.store.reads.load_activation(activation_id)
    return [(item.kind, item.reason) for item in closed.metadata.deviations]


def test_a_bound_violation_lands_after_the_carried_one(tmp_path: Path) -> None:
    """A close that ADDS one deviation to an activation carrying one records two.

    Input: the entry activation is minted carrying one `steer` deviation
    (reason "carried in from an earlier steer"), its child writes `outside.py`
    with the bound off, and the receipt is then amended to say the bound WAS
    on — so the settle tick records a `bound_violated` deviation as it closes.

    Wrong output this catches — what the current code records:
    `['steer', 'steer', 'steer', 'bound_violated']`. `finalize.decide` returns
    `(*activation.metadata.deviations, violation)`, `settle` re-prepends
    `recorded.metadata.deviations`, and `close_activation` prepends the
    record's own again. Want `['steer', 'bound_violated']` — each deviation
    once, and the one this close added LAST.

    It is not a test that `close_activation` merges at all, either: delete the
    merge and leave the callers as they are and this reads
    `['steer', 'steer', 'bound_violated']`, which the assertion still refuses.
    """
    lab = ForemanLab(tmp_path, sandbox=SandboxMode.OFF)
    lab.instantiate()
    minted_id = _mint_carrying_a_prior_deviation(lab)
    lab.profiles.next_script(
        ChildScript(
            marker=DONE_MARKER,
            effects='{"paths":[]}',
            write_path=UNGRANTED_FILE,
            write_body="escaped = True\n",
        )
    )
    activation_id = lab.tick().dispatched
    assert activation_id == minted_id

    _say_the_bound_was_on(lab, activation_id)

    assert lab.tick().settled == activation_id
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert [item.kind for item in closed.metadata.deviations] == [
        DEVIATION_KIND_STEER,
        DEVIATION_BOUND_VIOLATED,
    ]
    assert closed.metadata.deviations[0].reason == CARRIED_REASON


def test_a_clean_close_records_the_carried_one_once(tmp_path: Path) -> None:
    """A close that adds NOTHING leaves the one deviation it inherited alone.

    Input: the entry activation is minted carrying one `steer` deviation and
    its child does the ordinary thing — writes and commits `src/feature.py`
    inside its grant, declares it, and exits `done`. This close adds no
    deviation of its own.

    Wrong output this catches — what the current code records:
    `['steer', 'steer', 'steer']`. `decide` returns
    `activation.metadata.deviations` on the clean branch, `settle` prepends
    `recorded.metadata.deviations` to that, and `close_activation` prepends the
    record's own once more. Want `['steer']`.

    Deleting the merge instead of correcting the callers does not satisfy it
    either: `settle` would still hand the store `('steer', 'steer')` and the
    record would read `['steer', 'steer']`.
    """
    lab = ForemanLab(tmp_path, sandbox=SandboxMode.OFF)
    lab.instantiate()
    minted_id = _mint_carrying_a_prior_deviation(lab)
    lab.profiles.next_script(
        ChildScript(
            marker=DONE_MARKER,
            effects='{"paths":["src/feature.py"]}',
            write_path=GRANTED_FILE,
            write_body="value = 3\n",
            commit=True,
        )
    )
    activation_id = lab.tick().dispatched
    assert activation_id == minted_id

    assert lab.tick().settled == activation_id
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.DONE
    assert _kinds_and_reasons(lab, activation_id) == [
        (DEVIATION_KIND_STEER, CARRIED_REASON)
    ]


def test_a_replay_close_records_each_once(tmp_path: Path, signing: _Signing) -> None:
    """The crash-window replay close duplicates too, and the steer close is why.

    Two closes of the same shape, because one alone cannot pin the slice:

    (a) STEER, first, and green on the current code. An entry activation is
    minted carrying one `steer` deviation (reason "carried in from an earlier
    steer") and is steered while dispatched. `supervisor/steer.py` is the
    caller that ALREADY has the shape this slice restores: it hands the store
    only the `steer` deviation it adds, so the carried one survives that close
    through `close_activation`'s merge and nothing else. Delete that merge —
    the alternative "fix" that would make (b) alone pass — and this half reads
    `[('steer', 'silent past stale_after')]`, having dropped the carried entry.
    Want both, carried first.

    (b) REPLAY, on a second instance whose entry activation is minted carrying
    the same `steer` deviation. Its child commits `outside.py` without
    declaring it, so settle records the evidence and opens the §7.5 effects
    gate; the gate is approved and `completion.json` is deleted before the
    settling tick — the crash-window shape, where the close runs through
    `close._completion_deviations` and a replay rather than through
    `finalize.decide`. Wrong output this catches — what the current code
    records: `['steer', 'steer', 'undeclared_effects_accepted']`, because
    `_completion_deviations` starts from `activation.metadata.deviations` and
    `close_activation` prepends the record's own again. Want
    `['steer', 'undeclared_effects_accepted']`.

    Together: (b) fails on the current code for the duplication, (a) fails on
    any implementation that stops merging in the store, and only a close that
    hands the store exactly what it adds satisfies both.
    """
    steered = ForemanLab(tmp_path / "steered", sandbox=SandboxMode.OFF)
    steered.instantiate()
    steered_id = _mint_carrying_a_prior_deviation(steered)
    steered.wiring().store.record_dispatch(steered_id, handle())
    steered.go_stale(steered_id)

    steered.steer(
        steered_id,
        reason=STEER_REASON,
        instructions="finish with the recorded constraints",
    )

    closed_steer = steered.store.reads.load_activation(steered_id)
    assert closed_steer.metadata.outcome is Outcome.STEERED
    assert _kinds_and_reasons(steered, steered_id) == [
        (DEVIATION_KIND_STEER, CARRIED_REASON),
        (DEVIATION_KIND_STEER, STEER_REASON),
    ]

    lab = ForemanLab(
        tmp_path / "replay",
        signing=signing.config,
        signer=signing.sign,
        sandbox=SandboxMode.OFF,
    )
    lab.instantiate()
    minted_id = _mint_carrying_a_prior_deviation(lab)
    lab.profiles.next_script(
        ChildScript(
            marker=DONE_MARKER,
            effects='{"paths":[]}',
            write_path=UNGRANTED_FILE,
            write_body="undeclared = True\n",
            commit=True,
        )
    )
    activation_id = lab.tick().dispatched
    assert activation_id == minted_id

    # The blocked close records the evidence and awaits a human at the gate.
    assert lab.tick().settled is None
    gates = lab.beads("gate")
    assert len(gates) == 1
    gate_id = str(gates[0]["id"])
    lab.approve(gate_id, Outcome.APPROVE)
    assert lab.tick().closed_gates == (gate_id,)

    # The crash window: the verdict this close reads back is gone, so the
    # settling tick replays it before closing (`close.settle`'s
    # EVIDENCE_RECORDED branch).
    lab.wiring().paths.completion(activation_id).unlink()

    assert lab.tick().settled == activation_id
    closed = lab.store.reads.load_activation(activation_id)
    assert closed.metadata.outcome is Outcome.DONE
    assert [item.kind for item in closed.metadata.deviations] == [
        DEVIATION_KIND_STEER,
        DEVIATION_UNDECLARED_EFFECTS_ACCEPTED,
    ]
    assert closed.metadata.deviations[0].reason == CARRIED_REASON
