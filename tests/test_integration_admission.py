"""Explicit collected sources bind one original-owner integration member."""

import json
import sys
import time
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path
from typing import Final

import pytest

from tests.test_children_process import writer_lab
from tests.test_foreman_main import _contractor_adapter, _contractor_stage
from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.foreman.decisions import admission_of
from workflow_interpreter.foreman.tick import Foreman, TickReport


def source_lab(tmp_path: Path, store: BackendKind = BackendKind.BD):
    """One collected source child, on the caller's backend (run-ledger §3.2).

    `store` is a parameter because the §6 acceptance for this slice is that
    admission has no wall problem on the LEDGER and still works on bd: the
    30 s wall this file used to need is the bd round trip per tick, so the
    two runs are the measurement as much as the assertion.
    """
    from workflow_interpreter.inspector.sandbox import SandboxMode

    lab, owner, composition, spawner = writer_lab(
        tmp_path,
        sandbox=SandboxMode.BWRAP,
        store=store,
    )
    from workflow_interpreter.contractor.verification import CheckCommand

    composition = replace(
        composition,
        config=composition.config.model_copy(
            update={
                "contractor_checks": (
                    CheckCommand(
                        name="checks",
                        argv=(
                            sys.executable,
                            "-c",
                            "from pathlib import Path; assert Path('src/feature.py').is_file()",
                        ),
                    ),
                )
            }
        ),
    )
    coordinator = lab.store.coordination_store(composition=composition)
    coordinator.start_child(
        owner.root_id, "source", admission_of(owner, slot="source", generation=0)
    )
    result = coordinator.drive_children(owner.root_id, 1, 8)
    assert not result.timed_out
    source = coordinator.collect_child(owner.root_id, "source", 0)
    for process in spawner.processes:
        process.join(timeout=5)
        assert not process.is_alive()
    # The stage bead goes into the SHARED file, because the forked children
    # read their own copy of it. On the ledger backend the run made no bd
    # write at all, so the file may not exist yet — its absence is "no rows",
    # not a failure.
    state = lab.fake_bd._state
    data = (
        json.loads(state.read_text()) if state.exists() else {"rows": {}, "next_id": 1}
    )
    data["rows"]["stage"] = _contractor_stage(
        "stage", description="Combine the collected work"
    )
    state.write_text(json.dumps(data))
    return lab, owner, composition, source


LEDGER_WALL_BUDGET_S: Final[float] = 7.5
"""What the same drill is allowed on the ledger. A quarter of the 30 s the bd
drill used to be given, asserted rather than claimed: the §6 acceptance for
this slice is that admission has no wall problem, and a budget nobody measures
is not a measurement."""

START_TICK_BD_CALLS: Final[int] = 34
"""Calls the first decision tick makes: instantiation and admission writes."""
STEADY_TICK_BD_CALLS: Final[int] = 5
"""Calls a steady-state decision tick makes; pinned by
`test_admission_tick_stays_at_five_bd_calls` so a regression here is caught by
a count rather than by a clock."""
CLOSING_TICK_BD_CALLS: Final[int] = 29
"""Calls ONE closing tick makes: collection plus terminal writes."""
CLOSING_TICKS: Final[int] = 2
"""How many closing ticks the drill ends with — the terminal is reached in the
first and disposed in the second."""
CLOSE_TICK_BD_CALLS: Final[int] = CLOSING_TICK_BD_CALLS * CLOSING_TICKS
"""Calls the two closing ticks make together."""
OPENING_SPLIT_TICK_BD_CALLS: Final[int] = 18
"""The second opening tick, when the opening takes two: the foreman looked
before the forked member had exited, so instantiation and admission split."""
EXPECTED_TICKS: Final[int] = 8
"""Steady ticks the drill is expected to need while the forked writer runs;
measured at 6, with two ticks of slack."""
BD_CALL_SAFETY: Final[float] = 1.5
"""Headroom over the measured per-call latency, for host jitter."""
FIXED_CALL_ALLOWANCE_S: Final[float] = 10.0
"""Wall the drill spends OUTSIDE bd: fork, sandbox setup, git, verification."""
EXPECTED_BD_CALLS: Final[int] = (
    START_TICK_BD_CALLS + STEADY_TICK_BD_CALLS * EXPECTED_TICKS + CLOSE_TICK_BD_CALLS
)


MAX_CALIBRATED_LATENCY_S: Final[float] = 1.0
"""The slowest `bd` round trip this file will calibrate a budget from.

A budget derived from an unbounded sample is not a bound: one pathological
latency measurement (a cold host, a paging storm) would widen the wall until
any engine passed it. Above this the drill SKIPS and says so, because a
measurement nobody can trust is not evidence either way."""
START_TICK_TOLERANCE: Final[int] = 1
"""The opening tick measures 33 or 34 depending on whether the forked member
has already exited when the foreman first looks — one read either way."""
TOTAL_CALL_TOLERANCE: Final[int] = 18
"""How far over `EXPECTED_BD_CALLS` the whole drill may go: one extra opening
tick (measured at 18 calls) and nothing more. The steady count varies with
where the forked member is when the foreman looks, so the total is asserted as
a CEILING — which is exactly the premise `bd_wall_budget_s` rests on."""


def tick_shape_refusal(per_tick: Sequence[int]) -> str | None:
    """Why this per-tick call sequence is not the drill's shape, or `None`.

    Pure, so the classification itself is testable without bd. The shape is
    positional rather than inferred from the counts, because inferring it is
    exactly the hole the review found: an early regressed tick that happens to
    cost MORE than a steady one used to be read as a second opening tick and
    then only had to stay under a total ceiling to pass. So the opening prefix
    is the first tick (33 or 34) plus at most the known split tick, the
    closing suffix is exactly two 29-call ticks, and EVERY tick in between must
    equal `STEADY_TICK_BD_CALLS` — no tolerance, no inference.
    """
    if len(per_tick) < CLOSING_TICKS + 1:
        return f"the drill made {len(per_tick)} ticks: {list(per_tick)}"
    opening = {START_TICK_BD_CALLS - START_TICK_TOLERANCE, START_TICK_BD_CALLS}
    if per_tick[0] not in opening:
        return f"the opening tick cost {per_tick[0]}, not {sorted(opening)}: {list(per_tick)}"
    steady_from = 1
    if per_tick[1] == OPENING_SPLIT_TICK_BD_CALLS:
        steady_from = 2
    closing = per_tick[-CLOSING_TICKS:]
    if any(count != CLOSING_TICK_BD_CALLS for count in closing):
        return f"the closing ticks cost {list(closing)}: {list(per_tick)}"
    middle = per_tick[steady_from : len(per_tick) - CLOSING_TICKS]
    for index, count in enumerate(middle, start=steady_from):
        if count != STEADY_TICK_BD_CALLS:
            return (
                f"tick {index} cost {count}, not the steady "
                f"{STEADY_TICK_BD_CALLS}: {list(per_tick)}"
            )
    return None


def calibrated_latency_s(sample: float) -> float:
    """The measured `bd` latency, or a skip when it is too slow to trust."""
    if sample > MAX_CALIBRATED_LATENCY_S:
        pytest.skip(
            f"one bd round trip measured {sample:.2f}s, over the "
            f"{MAX_CALIBRATED_LATENCY_S:.1f}s this drill will calibrate a wall "
            "budget from; the measurement, not the engine, is what failed"
        )
    return sample


def bd_wall_budget_s(bd_latency_s: float) -> float:
    """The bd drill's wall budget, derived from this host's measured latency.

    `cr-xu34`: the old fixed 30 s assumed a ~50 ms `bd` invocation. On a host
    where one round trip costs ~290 ms the same 132 expected calls need ~38 s,
    so the drill stalled with `run max_wall` on a healthy engine. Deriving the
    budget keeps it host-independent while staying tight enough to FAIL if the
    engine doubles its per-tick calls: doubling every count roughly doubles the
    bd share of the wall, which is 1.5x the budget's own headroom. Anything
    beyond about 1.5x of `EXPECTED_BD_CALLS` (198 calls) breaks the budget.
    """
    return FIXED_CALL_ALLOWANCE_S + EXPECTED_BD_CALLS * bd_latency_s * BD_CALL_SAFETY


@pytest.mark.parametrize("store", (BackendKind.BD, BackendKind.LEDGER))
def test_replay_admits_only_one_original_owner_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, store: BackendKind
) -> None:
    """Replay converges on one member — and it converges on EITHER backend.

    Run on both because this is the §6 acceptance for the cutover: the test
    exists to prove the admission replay, and running it on the ledger proves
    the same replay without the per-tick bd round trip that made its wall
    budget flaky (`cr-xu34`).

    The ledger run is TIMED. In this file bd is the in-process double, so the
    number here bounds the engine's own work rather than the transport's; the
    round trips a real `bd` binary costs are measured by the real-bd rig
    (`tests/test_cutover_rig.py`).
    """
    from workflow_interpreter.contractor import integration
    from workflow_interpreter.contractor.adapter import ContractorAdapter

    started = time.monotonic()
    lab, owner, composition, source = source_lab(tmp_path, store)
    monkeypatch.setattr(
        ContractorAdapter,
        "from_config",
        classmethod(lambda *_, **__: _contractor_adapter(lab)),
    )
    request = integration.IntegrationRequest(
        owner_id=owner.root_id,
        epic_id="phase",
        stage_id="stage",
        request_key="combine",
        sources=(("source", 0, source.receipt_digest),),
    )
    first = integration.prepare_integration(composition, request)
    assert integration.prepare_integration(composition, request) == first
    # §3.2: the integration root is the owner's child, so the record that
    # admits it names the owner's backend — a record that named bd here would
    # contradict the ledger row its own root was created with.
    assert first.root_backend is store
    state = lab.store.coordination_store().state(owner.root_id)
    assert len(state.children) == 2
    assert len(state.reservations) == 3
    assert state.active[first.integration_slot] == first.root_id
    root = lab.store.reads.load_root(first.root_id)
    assert root.metadata.coordination.owner_id == owner.root_id
    assert set(root.metadata.essential_inputs) == {
        "integration_sources",
        "stage_brief",
        "target_base",
    }
    wall_s = time.monotonic() - started
    if store is BackendKind.LEDGER:
        assert wall_s < LEDGER_WALL_BUDGET_S, (
            f"the ledger admission drill took {wall_s:.2f}s, over its "
            f"{LEDGER_WALL_BUDGET_S:.1f}s budget"
        )


@pytest.mark.parametrize(
    ("per_tick", "accepted"),
    (
        ((34, 5, 5, 5, 29, 29), True),
        ((33, 5, 29, 29), True),
        ((34, 18, 5, 5, 29, 29), True),
        ((34, 6, 5, 5, 29, 29), False),
        ((34, 5, 6, 5, 29, 29), False),
        ((34, 5, 5, 5, 29), False),
        ((34, 5, 5, 5, 29, 30), False),
        ((31, 5, 5, 29, 29), False),
    ),
)
def test_the_tick_shape_classifier_places_every_tick(
    per_tick: tuple[int, ...], accepted: bool
) -> None:
    """The classification the bd drill rests on, decided without bd.

    `(34, 6, …)` is the regression the review found: a second tick that is
    dearer than a steady one but cheaper than an opening one used to pass as
    "still opening" and then only had to fit under a total ceiling.
    """
    refusal = tick_shape_refusal(per_tick)

    assert (refusal is None) is accepted, refusal


def test_admission_tick_stays_at_five_bd_calls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A steady admission tick costs exactly five bd calls, timing aside.

    The wall budget the bd drill derives is only as honest as this count, and a
    clock cannot tell a slow host from a chattier engine (`cr-xu34`). Here bd is
    the in-process double, so the counts are exact and deterministic: the drill
    measures 33-34 calls across its opening tick (sometimes split as 34 then
    18), 5 on every steady tick, and 29 on each of the two closing ticks.
    """
    from workflow_interpreter.inspector.sandbox import SandboxMode

    lab, owner, composition, spawner = writer_lab(tmp_path, sandbox=SandboxMode.BWRAP)
    coordinator = lab.store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "source", admission_of(owner, slot="source", generation=0)
    )
    per_tick: list[int] = []
    calls = [0]
    run = BdClient._run
    tick = Foreman.tick

    def counted(self: BdClient, argv: Sequence[str]) -> str:
        calls[0] += 1
        return run(self, argv)

    def counted_tick(self: Foreman, root_id: str) -> TickReport:
        before = calls[0]
        try:
            return tick(self, root_id)
        finally:
            per_tick.append(calls[0] - before)

    monkeypatch.setattr(BdClient, "_run", counted)
    monkeypatch.setattr(Foreman, "tick", counted_tick)
    try:
        result = Foreman(composition).run(child.root_id, poll_s=0.01, max_wall_s=60)
    finally:
        for process in spawner.processes:
            process.join(timeout=5)
    assert result.report.terminal, result
    # EVERY tick is classified by position and asserted on its own; a tick that
    # is neither the opening, the known split, nor one of the two closing ticks
    # must cost exactly `STEADY_TICK_BD_CALLS`, whatever the total says.
    assert tick_shape_refusal(per_tick) is None
    total = sum(per_tick)
    assert total <= EXPECTED_BD_CALLS + TOTAL_CALL_TOLERANCE, (
        f"the drill made {total} bd calls, over the "
        f"{EXPECTED_BD_CALLS} the wall budget is derived from: {per_tick}"
    )
    assert total >= START_TICK_BD_CALLS + CLOSE_TICK_BD_CALLS, per_tick


@pytest.mark.parametrize("change", ["duplicate", "digest", "generation", "missing"])
def test_invalid_source_never_admits_integration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    from workflow_interpreter.contractor.adapter import ContractorAdapter
    from workflow_interpreter.contractor.errors import ContractorRefusal
    from workflow_interpreter.contractor.integration import (
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.schema.decisions import CoordinationError

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        ContractorAdapter,
        "from_config",
        classmethod(lambda *_, **__: _contractor_adapter(lab)),
    )
    sources = (("source", 0, source.receipt_digest),)
    sources = {
        "duplicate": sources * 2,
        "digest": (("source", 0, "wrong"),),
        "generation": (("source", 1, source.receipt_digest),),
        "missing": (("missing", 0, source.receipt_digest),),
    }[change]
    before = lab.store.coordination_store().state(owner.root_id)
    with pytest.raises((ContractorRefusal, CoordinationError)):
        prepare_integration(
            composition,
            IntegrationRequest(
                owner_id=owner.root_id,
                epic_id="phase",
                stage_id="stage",
                request_key="combine",
                sources=sources,
            ),
        )
    assert lab.store.coordination_store().state(owner.root_id) == before


def test_changed_request_key_refuses_without_second_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workflow_interpreter.contractor.adapter import ContractorAdapter
    from workflow_interpreter.contractor.errors import ContractorRefusal
    from workflow_interpreter.contractor.integration import (
        IntegrationRequest,
        prepare_integration,
    )

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        ContractorAdapter,
        "from_config",
        classmethod(lambda *_, **__: _contractor_adapter(lab)),
    )
    request = IntegrationRequest(
        owner_id=owner.root_id,
        epic_id="phase",
        stage_id="stage",
        request_key="combine",
        sources=(("source", 0, source.receipt_digest),),
    )
    prepare_integration(composition, request)
    before = lab.store.coordination_store().state(owner.root_id)
    with pytest.raises(ContractorRefusal, match="payload changed"):
        prepare_integration(
            composition,
            request.model_copy(update={"sources": (("source", 0, "changed"),)}),
        )
    assert lab.store.coordination_store().state(owner.root_id) == before


@pytest.mark.parametrize(
    "fault", ["association", "contractor", "reservation", "root", "child", "admission"]
)
def test_prepared_faults_repair_only_saved_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    from tests._fake_bd import InjectedCrash
    from workflow_interpreter.bdio import roots
    from workflow_interpreter.bdio.coordination import CoordinationStore
    from workflow_interpreter.contractor.adapter import ContractorAdapter
    from workflow_interpreter.contractor.integration import (
        IntegrationGuard,
        IntegrationRequest,
        prepare_integration,
    )

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        ContractorAdapter,
        "from_config",
        classmethod(lambda *_, **__: _contractor_adapter(lab)),
    )
    request = IntegrationRequest(
        owner_id=owner.root_id,
        epic_id="phase",
        stage_id="stage",
        request_key="combine",
        sources=(("source", 0, source.receipt_digest),),
    )
    cls, method = {
        "association": (IntegrationGuard, "save"),
        "contractor": (ContractorAdapter, "prepare"),
        "reservation": (CoordinationStore, "_reserve"),
        "root": (roots, "create_root"),
        "child": (CoordinationStore, "start_child"),
        "admission": (ContractorAdapter, "admit"),
    }[fault]
    original = getattr(cls, method)
    armed = True

    def crash(self, *args, **kwargs):
        nonlocal armed
        result = original(self, *args, **kwargs)
        if armed:
            armed = False
            raise InjectedCrash("saved boundary")
        return result

    monkeypatch.setattr(cls, method, crash)
    with pytest.raises(InjectedCrash):
        prepare_integration(composition, request)
    state = lab.store.coordination_store().state(owner.root_id)
    saved = state.integrations["combine"]
    assert saved.admission.slot == "integration.stage.1"
    result = prepare_integration(composition, request)
    assert (
        result.root_id
        == lab.store.coordination_store()
        .state(owner.root_id)
        .active["integration.stage.1"]
    )
    assert len(lab.store.coordination_store().state(owner.root_id).reservations) == 3
    if saved.receipt:
        assert saved.receipt.root_id == result.root_id


def test_other_owner_busy_before_target_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from workflow_interpreter.contractor.adapter import ContractorAdapter
    from workflow_interpreter.contractor.errors import ContractorRefusal
    from workflow_interpreter.contractor.integration import (
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.foreman.resolve import instantiate
    from workflow_interpreter.inspector.gitio import Git

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        ContractorAdapter,
        "from_config",
        classmethod(lambda *_, **__: _contractor_adapter(lab)),
    )
    request = IntegrationRequest(
        owner_id=owner.root_id,
        epic_id="phase",
        stage_id="stage",
        request_key="combine",
        sources=(("source", 0, source.receipt_digest),),
    )
    prepare_integration(composition, request)
    other = instantiate(
        composition,
        lab._toml,
        instance_key="other",
        instance_inputs={},
        allow_test_flags=False,
        overrides={},
        backend=composition.config.store,
    )
    real_ref = Git.ref_target

    def no_snapshot(self, ref, *, cwd):
        if ref.startswith("refs/heads/"):
            pytest.fail("busy contender must not snapshot target")
        return real_ref(self, ref, cwd=cwd)

    monkeypatch.setattr(Git, "ref_target", no_snapshot)
    with pytest.raises(ContractorRefusal, match="busy"):
        prepare_integration(
            composition, request.model_copy(update={"owner_id": other.root_id})
        )
    assert len(lab.store.coordination_store().state(other.root_id).reservations) == 1


@pytest.mark.bd
def test_real_beads_roundtrips_integration_claim_and_one_root(
    tmp_path: Path, bd_config, bd_latency_s: float
) -> None:
    """The drill against a real bd, on a wall this host's latency justifies.

    `cr-xu34`: measured here at ~290 ms per `bd` invocation (the fixed 30 s
    this used to pass assumed ~50 ms), so the budget is
    `bd_wall_budget_s(...)` — about 67 s — rather than a constant.
    """
    import subprocess
    from dataclasses import replace

    from workflow_interpreter.bdio import WorkflowStore
    from workflow_interpreter.bdio.client import BdClient
    from workflow_interpreter.contractor.integration import (
        IntegrationGuard,
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.contractor.verification import CheckCommand
    from workflow_interpreter.foreman.resolve import instantiate
    from workflow_interpreter.foreman.tick import Foreman

    lab, _, composition, spawner = writer_lab(tmp_path)
    store = WorkflowStore(BdClient(bd_config))
    composition = replace(
        composition,
        store=store,
        config=composition.config.model_copy(
            update={
                "bd": bd_config,
                "contractor_checks": (
                    CheckCommand(
                        name="source",
                        argv=(
                            sys.executable,
                            "-c",
                            "from pathlib import Path; assert Path('src/feature.py').is_file()",
                        ),
                    ),
                ),
            }
        ),
    )
    spawner.bind(composition)
    owner = instantiate(
        composition,
        lab._toml,
        instance_key="p4-real-owner-" + tmp_path.name,
        instance_inputs={},
        allow_test_flags=False,
        overrides={},
        backend=composition.config.store,
    )
    coordinator = store.coordination_store(composition=composition)
    child = coordinator.start_child(
        owner.root_id, "source", admission_of(owner, slot="source", generation=0)
    )
    try:
        result = Foreman(composition).run(
            child.root_id,
            poll_s=0.05,
            max_wall_s=bd_wall_budget_s(calibrated_latency_s(bd_latency_s)),
        )
        assert result.report.terminal, result
        source = coordinator.collect_child(owner.root_id, "source", 0)

        def create(*args):
            return (
                subprocess.check_output(
                    ["bd", "create", *args, "--silent"],
                    cwd=bd_config.workspace,
                    timeout=30,
                )
                .decode()
                .strip()
            )

        epic = create("--title", "P4 isolated test", "--type", "epic")
        stage = create(
            "--title",
            "P4 isolated integration",
            "--parent",
            epic,
            "--description",
            "Combine the explicit source",
        )
        request = IntegrationRequest(
            owner_id=owner.root_id,
            epic_id=epic,
            stage_id=stage,
            request_key="real-integration",
            sources=(("source", 0, source.receipt_digest),),
        )
        record = prepare_integration(composition, request)
        assert prepare_integration(composition, request) == record
        state = coordinator.state(owner.root_id)
        assert len(state.children) == 2 and len(state.reservations) == 3
        claim = IntegrationGuard(composition).claim(
            state.integrations[request.request_key].target_key
        )
        assert (
            claim is not None
            and claim[1].association_digest == record.integration_digest
        )
    finally:
        for process in spawner.processes:
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)


@pytest.mark.parametrize(
    "failure", ["envelope", "capacity", "uncollected", "cancelled", "artifact-ref"]
)
def test_admission_limits_and_source_authority_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    from workflow_interpreter.contractor.adapter import ContractorAdapter
    from workflow_interpreter.contractor.errors import ContractorRefusal
    from workflow_interpreter.contractor.integration import (
        IntegrationRequest,
        prepare_integration,
    )
    from workflow_interpreter.foreman.envelope import EnvelopeRefusal
    from workflow_interpreter.schema.decisions import CoordinationError

    lab, owner, composition, source = source_lab(tmp_path)
    monkeypatch.setattr(
        ContractorAdapter,
        "from_config",
        classmethod(lambda *_, **__: _contractor_adapter(lab)),
    )
    coordinator = lab.store.coordination_store(composition=composition)
    sources = (("source", 0, source.receipt_digest),)
    if failure == "envelope":
        data = json.loads(lab.fake_bd._state.read_text())
        data["rows"]["stage"]["description"] = "x" * 62000
        lab.fake_bd._state.write_text(json.dumps(data))
    elif failure == "capacity":
        for slot in ("reserved-1", "reserved-2"):
            coordinator.start_child(
                owner.root_id, slot, admission_of(owner, slot=slot, generation=0)
            )
    elif failure in ("uncollected", "cancelled"):
        coordinator.start_child(
            owner.root_id, "pending", admission_of(owner, slot="pending", generation=0)
        )
        if failure == "cancelled":
            coordinator.cancel_child(
                owner.root_id, "pending", 0, "stop", "not a contribution"
            )
        sources = (("pending", 0, "no-collection"),)
    else:
        lab.git.update_ref(
            source.outputs_ref, owner.metadata.instance_base_commit, cwd=lab.repo
        )
    before = set(coordinator.state(owner.root_id).children)
    with pytest.raises((ContractorRefusal, CoordinationError, EnvelopeRefusal)):
        prepare_integration(
            composition,
            IntegrationRequest(
                owner_id=owner.root_id,
                epic_id="phase",
                stage_id="stage",
                request_key="combine",
                sources=sources,
            ),
        )
    assert set(coordinator.state(owner.root_id).children) == before
