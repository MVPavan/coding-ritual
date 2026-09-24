"""§8.1 session continuity, end to end through the real machinery.

Split out of `test_profiles_process.py` when R1 gave the family a §5.6 half:
the same `Lab` (`tests/_profiles.py`), a real fork barrier, a real steer, a real
recovery, and a real `Inspector.run` over the continuation.

What the family is FOR is one sentence: a steer must cost the human nothing but
a session. Three ways it used to cost more, all asserted here —

- the continuation started a NEW session, so the steer evaporated and the round
  was simply re-run (`build_resume_command` was never called);
- the continuation could not be dispatched through the only composition that
  watches a child and records its exit, so §8.1's second half had no production
  path at all (`Inspector.run` has no argument for the instructions, and the
  §5.6 recovery that finds a crashed steer holds nothing but a `MintRequest`);
- the refusal for an unresumable session landed AFTER the kill, so learning that
  the steer was impossible cost the work it was supposed to redirect.
"""

from __future__ import annotations

import time
import uuid
from datetime import timedelta
from pathlib import Path
from typing import Final

import pytest

from tests._foreman import ForemanLab
from tests._inspector import IMPLEMENT, ChildScript, entry_mint, handle_for, node_of
from tests._profiles import Lab, host_env_with, stub_env
from workflow_interpreter.bdio import Lifecycle, MintReason, MintRequest, ProcessHandle
from workflow_interpreter.bdio.rpc_records import SessionRegistration
from workflow_interpreter.contracts.sessions import SessionMode
from workflow_interpreter.foreman.compose import Composition, ProfileResolver
from workflow_interpreter.foreman.config import CrewBinding
from workflow_interpreter.foreman.inspector import WrapperExit, run_wrapper
from workflow_interpreter.foreman.tick import Foreman
from workflow_interpreter.inspector import (
    ExecLedger,
    Recovery,
    SteerIntent,
    SteerResult,
    procfs,
)
from workflow_interpreter.inspector.errors import ContinuationRefused
from workflow_interpreter.inspector.models import MonitorVerdict
from workflow_interpreter.inspector.paths import write_record
from workflow_interpreter.inspector.profile import (
    ChildLauncher,
    CrewCommand,
    Profile,
    TaskSpec,
)
from workflow_interpreter.inspector.sandbox import SandboxMode
from workflow_interpreter.inspector.steer import instructions_digest
from workflow_interpreter.profiles import CrewName, ProfileConfig
from workflow_interpreter.profiles.claude import ClaudeProfile
from workflow_interpreter.profiles.errors import TaskRefused
from workflow_interpreter.schema.models import Outcome

STEER_REASON: Final[str] = "the crew is looping on the same failing test"
STEER_INSTRUCTIONS: Final[str] = "stop rewriting the fixture; fix the assertion"
PINNED_MODEL: Final[str] = "claude-opus-5"


def _selected_registration(
    lab: Lab,
    activation_id: str,
    thread_id: str,
    *,
    crew_version: str = "codex-cli 0.155.1",
) -> SessionRegistration:
    """A durable source identity for launch-contract tests."""
    return SessionRegistration(
        root_id=lab.root.root_id,
        activation_id=activation_id,
        launch_id="source-launch",
        handle=handle_for(41, log_path=str(lab.paths.log(activation_id))),
        thread_id=thread_id,
        crew_profile="fake",
        crew_version=crew_version,
        model="fake-model",
        effort="medium",
        policy_digest="policy",
        state_path="",
    )


@pytest.mark.proc
def test_real_process_lab_grants_scheduler_time_per_virtual_poll(
    lab: Lab, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A virtual process poll also yields a bounded real scheduling window."""
    real_sleeps: list[float] = []
    before = lab.clock.now()
    monkeypatch.setattr("tests._inspector.time.sleep", real_sleeps.append)

    lab.clock.sleep(lab.config.poll_interval_s)

    assert real_sleeps == [0.05]
    assert lab.clock.now() == before + timedelta(seconds=1.0)


def steer(
    lab: Lab,
    parent_id: str,
    *,
    session_id: str = "made-up",
    observe: bool = True,
) -> SteerResult:
    """Steer a dispatched activation, with a caller-supplied (wrong) session id."""
    if observe:
        lab.observe_session(parent_id)
    return lab.steerer.steer(
        lab.store.reads.load_activation(parent_id),
        reason=STEER_REASON,
        instructions=STEER_INSTRUCTIONS,
        continuation=entry_mint(
            mint_reason=MintReason.STEER_CONTINUATION,
            predecessor_activation_id=parent_id,
            crew_profile=lab.store.reads.load_activation(
                parent_id
            ).metadata.crew_profile,
            session_id=session_id,
        ),
    )


def assert_resumes(argv: tuple[str, ...], session: str) -> None:
    """The argv of a §8.1 continuation: `--resume <id>`, no fresh session, text."""
    assert "--resume" in argv, argv
    assert argv[argv.index("--resume") + 1] == session, argv
    assert "--session-id" not in argv, argv
    assert STEER_INSTRUCTIONS in argv, argv


@pytest.mark.proc
@pytest.mark.parametrize("crew", [CrewName.CLAUDE, CrewName.CODEX])
def test_plain_resume_uses_only_the_durable_brief_delta(
    tmp_path: Path, crew: CrewName
) -> None:
    """A plain resume needs neither steer lineage nor steer instructions."""
    source_session = (
        str(uuid.UUID("0199f0b4-4018-7f67-a3f1-9ec893c475ae"))
        if crew is CrewName.CLAUDE
        else "0199f0b4-4018-7f67-a3f1-9ec893c475ae"
    )
    resumed = Lab(tmp_path / "resumed")
    request = entry_mint(session_id="")
    activation = resumed.store.mint_activation(resumed.root.root_id, request).activation
    resumed.store._client._merge_metadata(
        activation.activation_id,
        {
            "session_mode": SessionMode.RESUME,
            "session_source_activation_id": activation.activation_id,
            "source_session_id": source_session,
            "session_registration": _selected_registration(
                resumed,
                activation.activation_id,
                source_session,
                crew_version=(
                    "2.1.0 (Claude Code)"
                    if crew is CrewName.CLAUDE
                    else "codex-cli 0.155.1"
                ),
            ).model_dump(mode="json"),
        },
    )

    fresh_envelope = "PROTOCOL AND CONTEXT PREAMBLE\nnew instruction"
    delta = "new instruction"
    launched = resumed.dispatch(
        crew,
        request=request,
        session_id="",
        sleep_s=0.0,
        brief=fresh_envelope,
        resume_brief=delta,
    )

    assert launched.receipt is not None
    argv = launched.receipt.argv
    if crew is CrewName.CLAUDE:
        assert argv[argv.index("--resume") + 1] == source_session
        assert "--session-id" not in argv
    else:
        exec_at = argv.index("exec")
        assert argv[exec_at : exec_at + 3] == ("exec", "resume", source_session)
    assert delta in argv
    assert fresh_envelope not in argv
    if launched.handle is not None:
        resumed.await_exit(launched.handle)

    fresh = Lab(tmp_path / "fresh")
    launched_fresh = fresh.dispatch(crew, session_id="", sleep_s=0.0)
    assert launched_fresh.receipt is not None
    fresh_argv = launched_fresh.receipt.argv
    if crew is CrewName.CLAUDE:
        assert "--session-id" in fresh_argv
        assert "--resume" not in fresh_argv
    else:
        exec_at = fresh_argv.index("exec")
        assert fresh_argv[exec_at + 1] != "resume"
    if launched_fresh.handle is not None:
        fresh.await_exit(launched_fresh.handle)


@pytest.mark.proc
@pytest.mark.parametrize("registered_id", [None, "different-thread"])
def test_plain_resume_refuses_an_unregistered_or_mismatched_selected_source(
    tmp_path: Path, registered_id: str | None
) -> None:
    """A selected source and its exact observed vendor id are one contract."""
    lab = Lab(tmp_path)
    request = entry_mint(session_id="")
    activation = lab.store.mint_activation(lab.root.root_id, request).activation
    source_session = str(uuid.uuid4())
    delta: dict[str, object] = {
        "session_mode": SessionMode.RESUME,
        "session_source_activation_id": activation.activation_id,
        "source_session_id": source_session,
    }
    if registered_id is not None:
        delta["session_registration"] = _selected_registration(
            lab, activation.activation_id, registered_id
        ).model_dump(mode="json")
    lab.store._client._merge_metadata(activation.activation_id, delta)

    with pytest.raises(ContinuationRefused, match="resume source contract"):
        lab.dispatch(CrewName.CLAUDE, request=request, sleep_s=0.0)


@pytest.mark.proc
def test_plain_resume_refuses_an_empty_delta(tmp_path: Path) -> None:
    """A resumed turn with nothing to say is refused, never sent as empty text."""
    lab = Lab(tmp_path)
    request = entry_mint(session_id="")
    activation = lab.store.mint_activation(lab.root.root_id, request).activation
    source_session = str(uuid.UUID("0199f0b4-4018-7f67-a3f1-9ec893c475ae"))
    lab.store._client._merge_metadata(
        activation.activation_id,
        {
            "session_mode": SessionMode.RESUME,
            "session_source_activation_id": activation.activation_id,
            "source_session_id": source_session,
            "session_registration": _selected_registration(
                lab,
                activation.activation_id,
                source_session,
                crew_version="2.1.0 (Claude Code)",
            ).model_dump(mode="json"),
        },
    )

    with pytest.raises(TaskRefused, match="no brief delta to send"):
        lab.dispatch(CrewName.CLAUDE, request=request, sleep_s=0.0, resume_brief=None)


@pytest.mark.proc
def test_plain_resume_refuses_a_source_with_no_registered_cli_version(
    tmp_path: Path,
) -> None:
    """Design §6: an unqualified source version refuses reuse at launch too."""
    lab = Lab(tmp_path)
    request = entry_mint(session_id="")
    activation = lab.store.mint_activation(lab.root.root_id, request).activation
    source_session = str(uuid.UUID("0199f0b4-4018-7f67-a3f1-9ec893c475ae"))
    registration = _selected_registration(
        lab, activation.activation_id, source_session
    ).model_copy(update={"crew_version": None})
    lab.store._client._merge_metadata(
        activation.activation_id,
        {
            "session_mode": SessionMode.RESUME,
            "session_source_activation_id": activation.activation_id,
            "source_session_id": source_session,
            "session_registration": registration.model_dump(mode="json"),
        },
    )

    with pytest.raises(ContinuationRefused, match="registered no CLI version"):
        lab.dispatch(CrewName.CLAUDE, request=request, sleep_s=0.0)


@pytest.mark.proc
def test_failed_cli_version_probe_allows_fresh_but_refuses_resume(
    tmp_path: Path,
) -> None:
    """Unknown process compatibility must never disable the reuse guard."""
    missing_binary = tmp_path / "missing-codex"
    fresh = Lab(tmp_path / "fresh")
    launched = fresh.dispatch(CrewName.CODEX, binary=missing_binary, sleep_s=0.0)
    assert launched.receipt is not None
    if launched.handle is not None:
        fresh.await_exit(launched.handle)

    resumed = Lab(tmp_path / "resumed")
    request = entry_mint(session_id="")
    activation = resumed.store.mint_activation(resumed.root.root_id, request).activation
    session_id = "observed-thread"
    resumed.store._client._merge_metadata(
        activation.activation_id,
        {
            "session_mode": SessionMode.RESUME,
            "session_source_activation_id": activation.activation_id,
            "source_session_id": session_id,
            "session_registration": _selected_registration(
                resumed, activation.activation_id, session_id
            ).model_dump(mode="json"),
        },
    )

    with pytest.raises(ContinuationRefused, match="CLI version unavailable"):
        resumed.dispatch(
            CrewName.CODEX,
            request=request,
            binary=missing_binary,
            resume_brief="new instruction",
        )


@pytest.mark.proc
def test_routed_claude_roles_keep_their_own_pinned_efforts(
    tmp_path: Path,
) -> None:
    """One root routes both roles to one vendor without sharing an effort."""

    class RecordingClaude(ClaudeProfile):
        """Keep the real vendor command for each routed task."""

        def __init__(self, config: ProfileConfig) -> None:
            super().__init__(config, lab.clock, host_env_with(**stub_env()))
            self.commands: dict[str, CrewCommand] = {}

        def build_command(self, task: TaskSpec, session_id: str) -> CrewCommand:
            command = super().build_command(task, session_id)
            self.commands[task.node] = command
            return command

        def launch(
            self, command: CrewCommand, launcher: ChildLauncher
        ) -> ProcessHandle:
            """Run the foreman fixture child after retaining Claude's invocation."""
            if "review" in self.commands and self.commands["review"] == command:
                script = ChildScript(
                    marker='{"outcome":"accept"}',
                    effects='{"paths":[]}',
                    artifact_path="finding.md",
                    artifact_body="no findings",
                )
            else:
                script = ChildScript(
                    marker='{"outcome":"done"}',
                    effects='{"paths":["src/feature.py"]}',
                    write_path="src/feature.py",
                    write_body="value = 2\n",
                    commit=True,
                )
            return launcher(
                command.model_copy(update={"argv": ("/bin/sh", "-c", script.shell())})
            )

    class RecordingProfiles(ProfileResolver):
        """Route both roles through the same recording Claude profile."""

        def __init__(self, profile: RecordingClaude) -> None:
            self._profile = profile

        def profile_for(self, name: str) -> RecordingClaude:
            assert name == CrewName.CLAUDE.value
            return self._profile

        def version_for(self, name: str) -> str | None:
            """The recording profile is in-process; no CLI was ever probed."""
            del name
            return None

    lab = ForemanLab(
        tmp_path,
        roles={
            "implementer": CrewBinding(
                profile="claude", model=PINNED_MODEL, effort="high"
            ),
            "critic": CrewBinding(
                profile="claude", model=PINNED_MODEL, effort="medium"
            ),
        },
        sandbox=SandboxMode.OFF,
    )
    profile = RecordingClaude(ProfileConfig())
    lab.profiles = RecordingProfiles(profile)
    lab.composition = Composition(
        lab.config,
        lab.store,
        lab.inspector_config,
        lab.git,
        lab.clock,
        lab.profiles,
        lab.spawner,
        host_env=lab.composition.host_env,
    )
    lab.spawner.bind(lab.composition)
    lab.foreman = Foreman(lab.composition)
    root = lab.instantiate_resolved()
    minted = (
        lab.wiring()
        .store.mint_activation(
            root.root_id,
            MintRequest(
                node=IMPLEMENT,
                mint_reason=MintReason.ENTRY,
                crew_profile=CrewName.CLAUDE.value,
                model=PINNED_MODEL,
                effort="high",
                session_id="",
            ),
        )
        .activation
    )
    assert (
        run_wrapper(lab.composition, root.root_id, minted.activation_id)
        is WrapperExit.DONE
    )

    for _ in range(12):
        lab.tick()
        if set(profile.commands) == {"implement", "review"}:
            break

    assert set(profile.commands) == {"implement", "review"}
    for command in profile.commands.values():
        assert command.argv[command.argv.index("--model") + 1] == PINNED_MODEL
    assert (
        profile.commands["implement"].argv[
            profile.commands["implement"].argv.index("--effort") + 1
        ]
        == "high"
    )
    assert (
        profile.commands["review"].argv[
            profile.commands["review"].argv.index("--effort") + 1
        ]
        == "medium"
    )


@pytest.mark.proc
def test_wrapper_refuses_corrupted_activation_crew(
    tmp_path: Path,
) -> None:
    """A mutated crew cannot redirect a pinned activation to another vendor."""

    lab = ForemanLab(
        tmp_path,
        roles={
            "implementer": CrewBinding(
                profile="claude", model=PINNED_MODEL, effort="high"
            ),
            "critic": CrewBinding(
                profile="claude", model=PINNED_MODEL, effort="medium"
            ),
        },
        sandbox=SandboxMode.OFF,
    )
    profile = lab.profiles.profile

    class RecordingProfiles(ProfileResolver):
        """Record the vendor the wrapper selects at the profile boundary."""

        def __init__(self) -> None:
            self.selected: list[str] = []

        def profile_for(self, name: str) -> Profile:
            self.selected.append(name)
            return profile

        def version_for(self, name: str) -> str | None:
            """The recording profile is in-process; no CLI was ever probed."""
            del name
            return None

    profiles = RecordingProfiles()
    lab.profiles = profiles
    lab.composition = Composition(
        lab.config,
        lab.store,
        lab.inspector_config,
        lab.git,
        lab.clock,
        lab.profiles,
        lab.spawner,
        host_env=lab.composition.host_env,
    )
    lab.spawner.bind(lab.composition)
    root = lab.instantiate_resolved()
    minted = (
        lab.wiring()
        .store.mint_activation(
            root.root_id,
            MintRequest(
                node=IMPLEMENT,
                mint_reason=MintReason.ENTRY,
                crew_profile=CrewName.CLAUDE.value,
                model=PINNED_MODEL,
                effort="high",
                session_id="",
            ),
        )
        .activation
    )
    lab.backend._merge_metadata(
        minted.activation_id, {"crew_profile": (CrewName.CODEX.value)}
    )

    assert (
        run_wrapper(lab.composition, root.root_id, minted.activation_id)
        is WrapperExit.DONE
    )

    assert profiles.selected == []
    closed = lab.store.reads.load_activation(minted.activation_id)
    assert closed.metadata.lifecycle is Lifecycle.CLOSED
    assert closed.metadata.outcome is Outcome.ERROR_TRANSPORT


@pytest.mark.proc
def test_a_steer_continuation_resumes_the_session_the_launch_actually_ran(
    lab: Lab,
) -> None:
    """M4: launch → steer → continuation, through the real §5.2/§8.1 machinery.

    Three things were missing and are asserted here as one chain. Nothing called
    `Profile.prepare`, so the session id was whatever the mint request carried;
    nothing called `build_resume_command`, so a continuation started a NEW
    session and the human's steer evaporated; and the continuation's session id
    came from the caller rather than from the child that was killed.

    The evidence is the continuation's own durable receipt: `--resume <id>` with
    the id the FIRST child ran under, `--session-id` gone, and the steer
    instructions on the argv.
    """
    launched = lab.dispatch(CrewName.CLAUDE, session_id="")
    parent = launched.activation
    assert launched.handle is not None
    session = launched.handle.session_id
    uuid.UUID(session)  # `prepare` minted it; claude refuses anything else.

    steered = steer(
        lab, parent.activation_id, session_id="a-session-the-caller-made-up"
    )

    assert steered.intent.continuation.session_id == session
    continuation = lab.dispatch(
        CrewName.CLAUDE,
        request=steered.intent.continuation,
        instructions=STEER_INSTRUCTIONS,
    )

    receipt = continuation.receipt
    assert receipt is not None
    assert_resumes(receipt.argv, session)
    assert continuation.handle is not None
    assert continuation.handle.session_id == session


@pytest.mark.proc
def test_a_steer_continuation_runs_to_exit_recorded_through_inspector_run(
    lab: Lab,
) -> None:
    """R1: the §8.1 continuation's only production entry point is this one.

    `Inspector.run` is what dispatches, watches for `max_wall`, and records the
    exit; `Dispatcher.dispatch(instructions=...)` alone does none of those. And
    `Inspector.run` has no argument for a human's prose — so once dispatch
    started REFUSING a continuation with no instructions, every steer that
    reached production was refused at the launch instead of resuming.

    Nothing but the `MintRequest` `Steerer` produced is handed over here. The
    text comes off the predecessor's own durable intent file, and the proof is
    the continuation's receipt plus a real watch loop reaching `exit-recorded`
    with exactly one exec on the ledger.
    """
    launched = lab.dispatch(CrewName.CLAUDE, session_id="", owned=True)
    assert launched.handle is not None
    session = launched.handle.session_id
    steered = steer(lab, launched.activation.activation_id)

    result = lab.run(CrewName.CLAUDE, request=steered.intent.continuation)

    receipt = result.dispatch.receipt
    assert receipt is not None
    assert_resumes(receipt.argv, session)
    assert result.monitor is not None
    assert result.monitor.verdict is MonitorVerdict.EXITED
    assert result.observation is not None
    assert result.observation.exit_record.exit_code == 0
    assert result.observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED
    activation_id = result.dispatch.activation.activation_id
    assert ExecLedger(lab.paths.ledger(activation_id)).count() == 1


@pytest.mark.proc
def test_a_steer_that_crashed_before_the_kill_still_reaches_a_resumed_child(
    lab: Lab,
) -> None:
    """§5.6 case 0a, carried all the way to a running continuation.

    The wrapper died between writing the intent and signalling the child, which
    is the window the intent file exists for. Recovery finishes the steer and
    mints the continuation — and then holds nothing but that `MintRequest`,
    which is exactly the position R1 says must be dispatchable. The instructions
    come back off the same file recovery classified from.
    """
    launched = lab.dispatch(CrewName.CLAUDE, session_id="", owned=True)
    parent = launched.activation
    assert launched.handle is not None
    session = launched.handle.session_id
    lab.observe_session(parent.activation_id)
    node = node_of(lab.root.definition.document, IMPLEMENT)
    write_record(
        lab.paths.steer_intent(parent.activation_id),
        SteerIntent(
            activation_id=parent.activation_id,
            reason=STEER_REASON,
            instructions=STEER_INSTRUCTIONS,
            instructions_digest=instructions_digest(STEER_INSTRUCTIONS),
            requested_at="2026-08-26T12:01:00Z",
            continuation=entry_mint(
                mint_reason=MintReason.STEER_CONTINUATION,
                predecessor_activation_id=parent.activation_id,
                session_id=session,
            ),
        ),
    )
    recovery = Recovery(lab.config, lab.paths, lab.store, lab.workspace, lab.clock)

    resolution = recovery.resolve(
        lab.store.reads.load_activation(parent.activation_id), node
    )

    assert resolution.steer is not None
    result = lab.run(CrewName.CLAUDE, request=resolution.steer.intent.continuation)

    receipt = result.dispatch.receipt
    assert receipt is not None
    assert_resumes(receipt.argv, session)
    assert result.observation is not None
    assert result.observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED


@pytest.mark.proc
def test_steering_a_crew_with_no_resumable_session_refuses_before_the_kill(
    lab: Lab,
) -> None:
    """R1: the refusal that used to arrive one kill too late.

    Codex names its thread in its first event and can pre-assign nothing (§5.2),
    so a steer raised before that event has no session to continue. The refusal
    existed — in `build_resume_command`, reached after the child was dead and
    the activation was closed `steered`. The round was spent to learn it.

    Checked here in the order that matters: the child is still ALIVE afterwards,
    no intent was persisted for recovery to act on, and bd still says the
    activation is dispatched.
    """
    launched = lab.dispatch(CrewName.CODEX, session_id="")
    parent = launched.activation
    assert launched.handle is not None
    assert launched.handle.session_id == ""

    with pytest.raises(ContinuationRefused, match="no session a continuation"):
        steer(lab, parent.activation_id, observe=False)

    assert procfs.prove_liveness(lab.config, launched.handle).alive is True
    assert not lab.paths.steer_intent(parent.activation_id).exists()
    reloaded = lab.store.reads.load_activation(parent.activation_id)
    assert reloaded.metadata.lifecycle is Lifecycle.DISPATCHED
    assert reloaded.metadata.outcome is None


@pytest.mark.proc
def test_dispatching_a_continuation_with_nothing_to_continue_refuses(
    lab: Lab,
) -> None:
    """§8.1 mints exactly one continuation and resumes with it — or refuses.

    Falling back to `build_command` would launch a fresh session carrying the
    node's original brief, so the steer would cost a round and change nothing.

    "Nothing to continue with" is now a state rather than a forgotten argument:
    the intent file is the wrapper directory's, and `.wf/` is an observation
    cache §P1 allows to be lost. Losing it must refuse, not launch fresh.
    """
    launched = lab.dispatch(CrewName.CLAUDE, session_id="")
    parent = launched.activation
    steered = steer(lab, parent.activation_id)
    lab.paths.steer_intent(parent.activation_id).unlink()

    with pytest.raises(ContinuationRefused, match="no steer instructions"):
        lab.dispatch(CrewName.CLAUDE, request=steered.intent.continuation)


@pytest.mark.proc
def test_a_torn_steer_intent_refuses_rather_than_wedging_the_dispatch(
    lab: Lab,
) -> None:
    """Drill 18 applied to the intent file: malformed classifies, never raises.

    A crash can leave a half-written record. Letting the `WrapperDirError` out
    of `dispatch` would wedge the activation on every subsequent tick; treating
    it as absent walks to the same fail-closed refusal a missing file gets.
    """
    launched = lab.dispatch(CrewName.CLAUDE, session_id="")
    parent = launched.activation
    steered = steer(lab, parent.activation_id)
    lab.paths.steer_intent(parent.activation_id).write_text(
        '{"activation_id": "wf-', encoding="utf-8"
    )

    with pytest.raises(ContinuationRefused, match="no steer instructions"):
        lab.dispatch(CrewName.CLAUDE, request=steered.intent.continuation)


@pytest.mark.proc
def test_resume_instructions_are_refused_for_a_mint_that_is_not_a_continuation(
    lab: Lab,
) -> None:
    """The other half: only a `steer-continuation` may rejoin another session."""
    with pytest.raises(ContinuationRefused, match="mint reason is entry"):
        lab.dispatch(CrewName.CLAUDE, instructions=STEER_INSTRUCTIONS)


@pytest.mark.proc
def test_the_steer_intent_keeps_the_prose_out_of_every_bd_record(lab: Lab) -> None:
    """R1's boundary: the text is wrapper-local, the digest is what bd may see.

    The intent file carries the instructions so §5.6 can finish the steer; the
    §8.1 deviation recorded on the close carries the REASON, and nothing anywhere
    in the instance's beads carries the prose. Asserted over the whole bd
    workspace rather than over one field, because "which record could leak it"
    is exactly the question a field-by-field check cannot answer.
    """
    launched = lab.dispatch(CrewName.CLAUDE, session_id="", sleep_s=0.0)
    parent = launched.activation
    assert launched.handle is not None
    lab.await_exit(launched.handle)

    steered = steer(lab, parent.activation_id)

    assert steered.intent.instructions == STEER_INSTRUCTIONS
    assert steered.intent.instructions_digest == instructions_digest(STEER_INSTRUCTIONS)
    beads = lab.store.reads.instance_records(lab.root.root_id)
    dumped = repr([bead.model_dump(mode="json") for bead in beads])
    assert STEER_INSTRUCTIONS not in dumped
    assert STEER_REASON in dumped


@pytest.mark.proc
def test_an_infra_retry_of_a_continuation_carries_the_steer_forward(lab: Lab) -> None:
    """cr-o85.19: a retry of a §8.1 continuation IS a continuation (§8.1/§10.2).

    Only the continuation itself used to read the steer back, so a transport
    failure of the continuation left the dispatcher with a choice between
    relaunching the node's ORIGINAL brief in a fresh session and refusing the
    retry outright; it refused. Neither is what §8.1 means: the retry re-attempts
    the same steered work, so it resumes the same session with the same text,
    read off the STEERED activation's intent file one hop further back.
    """
    launched = lab.dispatch(CrewName.CLAUDE, session_id="", owned=True)
    parent = launched.activation
    assert launched.handle is not None
    session = launched.handle.session_id
    steered = steer(lab, parent.activation_id)
    continuation = lab.run(CrewName.CLAUDE, request=steered.intent.continuation)
    continuation_id = continuation.dispatch.activation.activation_id
    lab.store.close_activation(continuation_id, Outcome.ERROR_TRANSPORT)
    retry = entry_mint(
        crew_profile=CrewName.CLAUDE.value,
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=continuation_id,
        session_id=session,
    )

    result = lab.dispatch(CrewName.CLAUDE, request=retry)

    receipt = result.receipt
    assert receipt is not None
    assert_resumes(receipt.argv, session)
    assert result.handle is not None
    assert result.handle.session_id == session


@pytest.mark.proc
def test_a_retry_of_a_retry_still_finds_the_steer(lab: Lab) -> None:
    """The ancestry is walked, not one hop: R2 → R1 → C → S still resumes.

    A retry may itself fail in transport, and the intent lives two (or more)
    hops back on the STEERED activation; a one-hop reading would relaunch the
    original brief in a fresh session — the silent loss, one activation further
    down the chain.
    """
    launched = lab.dispatch(CrewName.CLAUDE, session_id="", owned=True)
    parent = launched.activation
    assert launched.handle is not None
    session = launched.handle.session_id
    steered = steer(lab, parent.activation_id)
    continuation = lab.run(CrewName.CLAUDE, request=steered.intent.continuation)
    continuation_id = continuation.dispatch.activation.activation_id
    lab.store.close_activation(continuation_id, Outcome.ERROR_TRANSPORT)
    first_retry = lab.store.mint_activation(
        lab.paths.root_id,
        entry_mint(
            crew_profile=CrewName.CLAUDE.value,
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=continuation_id,
            session_id=session,
        ),
    ).activation
    lab.store.close_activation(first_retry.activation_id, Outcome.ERROR_TRANSPORT)
    second_retry = entry_mint(
        crew_profile=CrewName.CLAUDE.value,
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=first_retry.activation_id,
        session_id=session,
    )

    result = lab.dispatch(CrewName.CLAUDE, request=second_retry)

    receipt = result.receipt
    assert receipt is not None
    assert_resumes(receipt.argv, session)


@pytest.mark.proc
def test_a_retry_of_a_continuation_whose_intent_is_gone_is_refused(lab: Lab) -> None:
    """No intent file, no carry-forward: refuse rather than launch fresh.

    The intent file is the only place the steer's prose is durable (bd never
    sees it), so a retry that cannot read it back has nothing to continue —
    and relaunching the node's original brief is exactly the silent loss this
    family exists to prevent.
    """
    launched = lab.dispatch(CrewName.CLAUDE, session_id="", owned=True)
    parent = launched.activation
    steered = steer(lab, parent.activation_id)
    continuation = lab.run(CrewName.CLAUDE, request=steered.intent.continuation)
    continuation_id = continuation.dispatch.activation.activation_id
    lab.store.close_activation(continuation_id, Outcome.ERROR_TRANSPORT)
    lab.paths.steer_intent(parent.activation_id).unlink()
    retry = entry_mint(
        crew_profile=CrewName.CLAUDE.value,
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=continuation_id,
        session_id=str(uuid.uuid4()),
    )

    with pytest.raises(ContinuationRefused, match="infra-retry"):
        lab.dispatch(CrewName.CLAUDE, request=retry)


@pytest.mark.parametrize("crew", [CrewName.CLAUDE, CrewName.CODEX])
def test_foreman_delivered_resume_and_retry_match_recorded_envelope(
    tmp_path: Path, crew: CrewName
) -> None:
    """Serialize the real composed task, resume, and infra retry via vendor stubs."""
    import hashlib

    from tests._profiles import PASSTHROUGH, write_stub
    from workflow_interpreter.foreman.inputs import select_bindings
    from workflow_interpreter.foreman.inspector import _task_builder
    from workflow_interpreter.inspector import Dispatcher, Steerer
    from workflow_interpreter.inspector.launch import DispatchResult
    from workflow_interpreter.inspector.profile import observe_session
    from workflow_interpreter.profiles.registry import ProfileRegistry

    lab = ForemanLab(tmp_path, sandbox=SandboxMode.OFF)
    root = lab.instantiate()
    wiring = lab.wiring()
    assert all(
        item.key != "node.implement.crew" for item in root.metadata.resolved_config
    )
    node = root.index.nodes[IMPLEMENT]
    bindings = select_bindings(root.index, root, node, (), 1)
    request = entry_mint(
        model="fake",
        crew_profile=crew.value,
        effort="medium",
        session_id=str(uuid.uuid4()) if crew is CrewName.CLAUDE else "",
        inputs=bindings,
    )
    binary = write_stub(tmp_path, crew)
    profile = ProfileRegistry(
        ProfileConfig(
            binary_overrides={crew: str(binary)}, passthrough_env=PASSTHROUGH
        ),
        lab.clock,
        host_env_with(**stub_env()),
    ).profile_for(crew.value)
    request = request.model_copy(update={"crew_version": profile.cli_version()})
    dispatcher = Dispatcher(wiring.paths, wiring.store, lab.clock)
    builder = _task_builder(root, wiring, lab.git)

    def launch(request: MintRequest) -> DispatchResult:
        result = dispatcher.dispatch(
            request,
            profile,
            builder,
            lambda activation: wiring.workspace.prepare(activation, node),
        )
        assert result.handle is not None
        try:
            assert result.receipt is not None
            argv = result.receipt.argv
            payload = (
                argv[argv.index("-p") + 1] if crew is CrewName.CLAUDE else argv[-1]
            )
            metadata = wiring.store.reads.load_activation(
                result.activation.activation_id
            ).metadata
            assert metadata.envelope is not None
            if request.mint_reason is MintReason.ENTRY:
                assert "Do not spawn or delegate" in payload
                assert "implement the lab fixture" in payload
                assert node.instructions is not None and node.instructions in payload
                assert metadata.envelope["byte_count"] == len(payload.encode())
                assert (
                    metadata.envelope["sha256"]
                    == hashlib.sha256(payload.encode()).hexdigest()
                )
            else:
                assert payload == STEER_INSTRUCTIONS
            if request.mint_reason is MintReason.ENTRY:
                for _attempt in range(100):
                    current = wiring.store.reads.load_activation(
                        result.activation.activation_id
                    )
                    registration = observe_session(root, current, profile).registration
                    if registration is not None:
                        assert registration.effort == current.metadata.effort
                        assert (
                            registration.policy_digest == current.metadata.policy_digest
                        )
                        assert (
                            registration.crew_version == current.metadata.crew_version
                        )
                        wiring.store.register_session(
                            current.activation_id, registration
                        )
                        break
                    time.sleep(0.005)
                else:
                    raise AssertionError("vendor identity event was not observed")
            return result
        finally:
            assert procfs.terminate(
                lab.inspector_config, result.handle, lab.clock
            ).confirmed_dead

    first = launch(request)
    first_source = wiring.store.reads.load_activation(first.activation.activation_id)
    steered = Steerer(
        lab.inspector_config,
        wiring.paths,
        wiring.store,
        lab.clock,
        workspace=wiring.workspace,
    ).steer(
        first_source,
        reason=STEER_REASON,
        instructions=STEER_INSTRUCTIONS,
        continuation=entry_mint(
            model="fake",
            crew_profile=crew.value,
            mint_reason=MintReason.STEER_CONTINUATION,
            predecessor_activation_id=first.activation.activation_id,
            inputs=bindings,
        ),
    )
    continued = launch(steered.intent.continuation)
    wiring.store.close_activation(
        continued.activation.activation_id, Outcome.ERROR_TRANSPORT
    )
    retry = entry_mint(
        model="fake",
        crew_profile=crew.value,
        effort="medium",
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=continued.activation.activation_id,
        session_id=continued.handle.session_id,
        inputs=bindings,
    )
    # Original RAW intent remains required, even though the builder could
    # construct a nonempty task without it.
    intent_path = wiring.paths.steer_intent(first.activation.activation_id)
    raw_intent = intent_path.read_bytes()
    intent_path.unlink()
    with pytest.raises(ContinuationRefused):
        dispatcher.dispatch(retry, profile, builder)
    intent_path.write_bytes(raw_intent)
    launch(retry)
