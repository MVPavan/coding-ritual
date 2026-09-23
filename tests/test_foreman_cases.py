"""C2b lifecycle case contracts using the shared real-collaborator lab."""

from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from tests._bdio import handle
from tests._foreman import FAKE_PROFILE, ForemanLab, entry_request
from tests._inspector import SESSION_ID, ChildScript
from workflow_interpreter.bdio import CarrierIntegrityError, ExitRecord, Lifecycle
from workflow_interpreter.contracts.sessions import SessionMode
from workflow_interpreter.foreman import cases as cases_module
from workflow_interpreter.foreman.cases import advance_lifecycle, mint_entry, route_head
from workflow_interpreter.foreman.compose import WrapperLaunch
from workflow_interpreter.foreman.config import CrewBinding
from workflow_interpreter.foreman.constants import DISPATCH_REQUEST
from workflow_interpreter.inspector import Recovery
from workflow_interpreter.inspector.models import CompletionEvidence, RecoveryCase
from workflow_interpreter.inspector.paths import read_record
from workflow_interpreter.schema.models import Outcome


def _bd_writes(lab: ForemanLab) -> int:
    """Count every durable bd mutation, excluding reads and process-local files."""
    return sum(lab.count(command) for command in ("create", "update", "close"))


_LEGACY_S3_PINS: dict[str, None] = {
    "binding_digest": None,
    "role": None,
    "family": None,
    "effort": None,
    "context_cap_tokens": None,
    "execution_policy": None,
    "policy_digest": None,
    "catalog_digest": None,
    "crew_version": None,
}


def test_empty_lifecycle_mints_and_runs_one_real_wrapper(tmp_path: Path) -> None:
    """Entry mint reaches the wrapper's dispatch and exit-recorded lifecycle."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    before = _bd_writes(lab)

    report = mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    assert report.dispatched == activation.activation_id
    assert activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    assert _bd_writes(lab) - before == 5  # includes the immutable envelope record
    assert [launch.activation_id for launch in lab.spawner.launches] == [
        activation.activation_id
    ]


def test_minted_lifecycle_dispatches_and_records_its_exit(tmp_path: Path) -> None:
    """A real launch owns precondition, dispatch, and exit writes."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, lab.wiring(), root, minted)

    assert result.dispatched == minted.activation_id
    assert lab.store.reads.load_activation(minted.activation_id).metadata.lifecycle is (
        Lifecycle.EXIT_RECORDED
    )
    assert _bd_writes(lab) - before == 4  # precondition, envelope, dispatch, exit
    assert [launch.activation_id for launch in lab.spawner.launches] == [
        minted.activation_id,
    ]


def test_minted_dispatch_refuses_a_corrupted_activation_binding(
    tmp_path: Path,
) -> None:
    """A mutated model cannot become the vendor task of a minted row."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    lab.backend._merge_metadata(minted.activation_id, {"model": "legacy-model"})
    activation = lab.store.reads.load_activation(minted.activation_id)

    advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    closed = lab.store.reads.load_activation(minted.activation_id)
    assert closed.metadata.lifecycle is Lifecycle.CLOSED
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT
    assert lab.profiles.profile.tasks == []


def test_durable_launch_request_carries_the_resolved_session_contract(
    tmp_path: Path,
) -> None:
    """The S1 session fields survive mint and the durable pre-spawn record."""
    lab = ForemanLab(
        tmp_path,
        roles={
            "implementer": CrewBinding(
                profile="fake",
                model="fake",
                effort="medium",
                session_mode=SessionMode.RESUME,
            ),
            "critic": CrewBinding(profile="fake", model="fake", effort="medium"),
            "scribe": CrewBinding(profile="fake", model="fake", effort="medium"),
        },
    )
    root = lab.instantiate()

    mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    launch = read_record(
        lab.wiring().paths.activation_dir(activation.activation_id) / DISPATCH_REQUEST,
        WrapperLaunch,
    )
    assert launch is not None
    values = launch.request.model_dump()
    assert {
        "session_mode",
        "session_source_activation_id",
        "source_session_id",
    } <= values.keys()
    assert launch.request.session_mode is SessionMode.RESUME
    assert launch.request.session_source_activation_id is None
    assert launch.request.source_session_id is None


def test_dispatched_lifecycle_recovers_without_a_second_bd_write(
    tmp_path: Path,
) -> None:
    """A dead dispatched activation takes recovery and does not launch again."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.store.record_dispatch(minted.activation_id, handle())
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    assert result.stalled is not None
    assert _bd_writes(lab) == before
    assert lab.spawner.launches == []


def test_dispatched_lifecycle_counts_the_two_writes_of_a_closing_recovery(
    tmp_path: Path,
) -> None:
    """A recovery that closes an already-recorded outcome performs update then close."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(activation.activation_id, handle())

    class ClosingRecovery:
        def resolve(self, *_args: object) -> object:
            closed = lab.wiring().store.close_activation(
                activation.activation_id, Outcome.ERROR_TRANSPORT
            )
            return type("Resolution", (), {"closed": closed, "halted": None})()

    wiring = replace(lab.wiring(), recovery=cast(Recovery, ClosingRecovery()))
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, wiring, root, activation)

    assert result.settled == activation.activation_id
    assert _bd_writes(lab) - before == 2


def test_infra_retry_waits_for_pending_barrier_abort_cleanup(tmp_path: Path) -> None:
    """A closed transport retry cannot bypass the receipt's pending kill."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    dispatched = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    closed = lab.wiring().store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )

    class PendingAbortRecovery:
        def classify(self, *_args: object) -> object:
            return type("Classification", (), {"case": RecoveryCase.ABORT_PENDING})()

        def resolve(self, *_args: object) -> object:
            termination = type("Termination", (), {"confirmed_dead": False})()
            return type("Resolution", (), {"termination": termination})()

    wiring = replace(lab.wiring(), recovery=cast(Recovery, PendingAbortRecovery()))

    result = route_head(lab.composition, wiring, root, closed)

    assert result.stalled == "barrier abort cleanup is still pending"
    assert len(lab.store.reads.list_activations(root.root_id)) == 1


def test_infra_retry_rebuilds_its_request_from_the_root_pin(tmp_path: Path) -> None:
    """A legacy retry request cannot trip the mint boundary guard."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    dispatched = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    closed = lab.wiring().store.close_activation(
        dispatched.activation_id, Outcome.ERROR_TRANSPORT
    )
    lab.backend._merge_metadata(
        closed.activation_id, {"crew_profile": "legacy-crew", "model": "legacy-model"}
    )
    legacy = lab.store.reads.load_activation(closed.activation_id)

    result = route_head(lab.composition, lab.wiring(), root, legacy)

    assert result.dispatched is not None
    retried = lab.store.reads.load_activation(result.dispatched)
    assert retried.metadata.crew_profile == FAKE_PROFILE
    assert retried.metadata.model == "fake"


def test_exit_recorded_lifecycle_records_evidence_then_closes(tmp_path: Path) -> None:
    """Settlement owns one evidence update plus the close update and close command."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    activation = lab.store.reads.load_activation(activation_id)
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    assert result.settled == activation_id
    # evidence, the §3 session tree, the close update and the close command
    assert _bd_writes(lab) - before == 4


def test_completed_pre_s3_activation_does_not_block_later_ticks(tmp_path: Path) -> None:
    """A completed root-pinned row remains usable after activation pins arrive."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    first = lab.tick().dispatched
    assert first is not None
    lab.tick()
    closed = lab.store.reads.load_activation(first)
    assert closed.metadata.lifecycle is Lifecycle.CLOSED
    lab.backend._merge_metadata(
        first,
        _LEGACY_S3_PINS,
    )

    report = lab.tick()

    assert report.dispatched is not None
    successor = lab.store.reads.load_activation(report.dispatched)
    assert successor.metadata.node == "review"
    lab.tick()


@pytest.mark.parametrize("missing_digest", ["binding_digest", "policy_digest"])
def test_partial_activation_pin_halts_by_name(
    tmp_path: Path, missing_digest: str
) -> None:
    """A damaged S3 row cannot settle through the legacy root fallback."""
    lab = ForemanLab(tmp_path)
    lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    lab.backend._merge_metadata(
        activation_id,
        {missing_digest: None, "model": "tampered-model"},
    )

    report = lab.tick()

    assert report.opened_gate is not None
    gate = lab.store.reads.load_gate(report.opened_gate)
    assert gate.metadata.halt_reason == (
        f"unusable_resolution:implement:{activation_id}"
    )
    assert lab.tick().halted


def test_exit_recorded_legacy_settlement_uses_the_root_pinned_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-S3 exit remains attached to its root-pinned vendor."""
    lab = ForemanLab(
        tmp_path,
        overrides={
            "node.implement.crew": FAKE_PROFILE,
            "node.implement.model": "fake",
            "node.implement.effort": "medium",
            "node.implement.session_mode": "fresh",
        },
    )
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    dispatched = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    activation = lab.wiring().store.record_exit(
        dispatched.activation_id,
        ExitRecord(exit_code=0, ended_at="2026-09-08T00:00:00Z", reason="ok"),
    )
    lab.backend._merge_metadata(
        activation.activation_id,
        {"crew_profile": "legacy-crew", **_LEGACY_S3_PINS},
    )
    activation = lab.store.reads.load_activation(activation.activation_id)
    profiles: list[str] = []

    monkeypatch.setattr(
        lab.composition.profiles,
        "profile_for",
        lambda name: profiles.append(name) or lab.profiles.profile,
    )
    monkeypatch.setattr(
        cases_module,
        "settle",
        lambda *_args: type(
            "Settlement",
            (),
            {"activation": activation, "stalled": None},
        )(),
    )

    advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    assert profiles == [FAKE_PROFILE]


def test_dispatched_legacy_settlement_uses_the_root_pinned_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A pre-S3 dispatched row recovers with the root-pinned vendor."""
    lab = ForemanLab(
        tmp_path,
        overrides={
            "node.implement.crew": FAKE_PROFILE,
            "node.implement.model": "fake",
            "node.implement.effort": "medium",
            "node.implement.session_mode": "fresh",
        },
    )
    root = lab.instantiate()
    minted = (
        lab.wiring().store.mint_activation(root.root_id, entry_request()).activation
    )
    activation = lab.wiring().store.record_dispatch(minted.activation_id, handle())
    lab.backend._merge_metadata(
        activation.activation_id,
        {"crew_profile": "legacy-crew", **_LEGACY_S3_PINS},
    )
    activation = lab.store.reads.load_activation(activation.activation_id)
    profiles: list[str] = []

    class ExitRecordedRecovery:
        def resolve(self, *_args: object) -> object:
            return type(
                "Resolution",
                (),
                {
                    "classification": type(
                        "Classification",
                        (),
                        {
                            "exit_record": ExitRecord(
                                exit_code=0,
                                ended_at="2026-09-08T00:00:00Z",
                                reason="ok",
                            )
                        },
                    )(),
                    "closed": None,
                    "halted": None,
                },
            )()

    wiring = replace(lab.wiring(), recovery=cast(Recovery, ExitRecordedRecovery()))
    monkeypatch.setattr(
        lab.composition.profiles,
        "profile_for",
        lambda name: profiles.append(name) or lab.profiles.profile,
    )
    monkeypatch.setattr(
        cases_module,
        "settle",
        lambda *_args: type(
            "Settlement",
            (),
            {"activation": activation, "stalled": None},
        )(),
    )

    advance_lifecycle(lab.composition, wiring, root, activation)

    assert profiles == [FAKE_PROFILE]


def test_evidence_recorded_lifecycle_closes_from_the_saved_completion(
    tmp_path: Path,
) -> None:
    """A replay-free close writes its outcome and then finishes the bead."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    activation_id = lab.tick().dispatched
    assert activation_id is not None
    completion = read_record(
        lab.wiring().paths.completion(activation_id), CompletionEvidence
    )
    assert completion is not None
    activation = lab.store.record_evidence(activation_id, completion.evidence)
    before = _bd_writes(lab)

    result = advance_lifecycle(lab.composition, lab.wiring(), root, activation)

    assert result.settled == activation_id
    # the §3 session tree, then the close — the evidence is already recorded
    assert _bd_writes(lab) - before == 3


def test_the_mint_carries_no_session_and_the_dispatch_records_the_prepared_one(
    tmp_path: Path,
) -> None:
    """§5.2: `prepare()` is the only minter of session ids (cr-o85.34.9).

    The mint used to pre-assign a UUID whenever the bound profile happened to
    be named `claude`, which made the id a property of a string comparison in
    the foreman rather than of the profile that owns the session. The durable
    request the wrapper reads carries none, and the id the child actually ran
    under is written back by the dispatch that recorded the handle.
    """
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()

    mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    launch = read_record(
        lab.wiring().paths.activation_dir(activation.activation_id) / DISPATCH_REQUEST,
        WrapperLaunch,
    )
    assert launch is not None
    assert launch.request.session_id == ""
    assert activation.metadata.session_id == SESSION_ID
    assert activation.metadata.handle is not None
    assert activation.metadata.handle.session_id == SESSION_ID


def test_entry_mint_and_task_construction_read_the_roots_resolution(
    tmp_path: Path,
) -> None:
    """§3.1: an instance override reaches the mint AND the built task (cr-7h8).

    Both were recorded with provenance and then ignored — the mint re-read the
    live role map, and the task builder read the raw pinned node.
    """
    lab = ForemanLab(
        tmp_path,
        overrides={
            "node.implement.model": "override-model",
            "node.implement.token_budget": 1234,
        },
    )
    root = lab.instantiate()

    mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    assert activation.metadata.model == "override-model"
    task = lab.profiles.profile.tasks[-1]
    assert task.model == "override-model"
    assert task.token_budget == 1234


def test_a_role_rebinding_after_instantiation_reaches_a_new_mint(
    tmp_path: Path,
) -> None:
    """New mints use the owner's startup bindings, not historical root pins."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    lab.composition.config.roles["implementer"] = CrewBinding(
        profile=FAKE_PROFILE, model="drifted-model", effort="high"
    )

    mint_entry(lab.composition, lab.wiring(), root)

    activation = lab.store.reads.list_activations(root.root_id)[0]
    assert activation.metadata.crew_profile == FAKE_PROFILE
    assert activation.metadata.model == "drifted-model"
    assert activation.metadata.effort == "high"


def test_duplicate_mint_replays_before_new_binding_validation(tmp_path: Path) -> None:
    """A re-tick returns the ledger pin even if its request binding drifted."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    first = lab.wiring().store.mint_activation(root.root_id, entry_request())

    replay = lab.wiring().store.mint_activation(
        root.root_id, entry_request(model="invalid-new-model", effort="high")
    )

    assert replay.created is False
    assert replay.activation.metadata.model == first.activation.metadata.model
    assert replay.activation.metadata.effort == first.activation.metadata.effort


@pytest.mark.parametrize(
    "overrides",
    ({"effort": ""}, {"context_cap_tokens": 0}, {"context_cap_tokens": -1}),
)
def test_new_mint_refuses_unusable_effort_or_cap(
    tmp_path: Path, overrides: dict[str, object]
) -> None:
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()

    with pytest.raises(CarrierIntegrityError, match="effort|context cap"):
        lab.wiring().store.mint_activation(root.root_id, entry_request(**overrides))


def test_task_uses_activation_effort_and_context_cap(tmp_path: Path) -> None:
    """A direct mint's invocation stays intact when the root has older values."""
    lab = ForemanLab(tmp_path)
    root = lab.instantiate()
    minted = (
        lab.wiring()
        .store.mint_activation(
            root.root_id,
            entry_request(effort="high", context_cap_tokens=120000),
        )
        .activation
    )

    advance_lifecycle(lab.composition, lab.wiring(), root, minted)

    recorded = lab.store.reads.load_activation(minted.activation_id)
    task = lab.profiles.profile.tasks[-1]
    assert recorded.metadata.effort == "high"
    assert recorded.metadata.context_cap_tokens == 120000
    assert task.effort == "high"
    assert task.context_cap_tokens == 120000


def test_a_real_override_reaches_the_brief_the_task_and_the_workspace(
    tmp_path: Path,
) -> None:
    """An in-repo writer reaches every execution reader without becoming a non-writer.

    `writes` and `isolation` are resolved once and then read by everything:
    the brief the crew is given, the task it is launched with, and the
    directory it runs in. Driven through `resolve()`'s own checks, not a
    hand-built resolution.
    """
    lab = ForemanLab(tmp_path)
    lab.instantiate_resolved(
        {"node.implement.writes": True, "node.implement.isolation": "in-repo"}
    )
    lab.profiles.next_script(ChildScript(marker='{"outcome":"done"}\n'))

    report = lab.tick()

    assert report.dispatched is not None
    task = lab.profiles.profile.tasks[-1]
    assert task.writes is True
    assert task.cwd == str(lab.repo)
    assert "repository writes: yes" in task.brief
