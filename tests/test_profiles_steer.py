"""§8.1 session continuity, end to end through the real machinery.

Split out of `test_profiles_process.py` when R1 gave the family a §5.6 half:
the same `Lab` (`tests/_profiles.py`), a real fork barrier, a real steer, a real
recovery, and a real `Supervisor.run` over the continuation.

What the family is FOR is one sentence: a steer must cost the human nothing but
a session. Three ways it used to cost more, all asserted here —

- the continuation started a NEW session, so the steer evaporated and the round
  was simply re-run (`build_resume_command` was never called);
- the continuation could not be dispatched through the only composition that
  watches a child and records its exit, so §8.1's second half had no production
  path at all (`Supervisor.run` has no argument for the instructions, and the
  §5.6 recovery that finds a crashed steer holds nothing but a `MintRequest`);
- the refusal for an unresumable session landed AFTER the kill, so learning that
  the steer was impossible cost the work it was supposed to redirect.
"""

from __future__ import annotations

import uuid
from typing import Final

import pytest

from tests._profiles import Lab
from tests._supervisor import IMPLEMENT, entry_mint, node_of
from workflow_interpreter.bdio import Lifecycle, MintReason
from workflow_interpreter.profiles import RunnerName
from workflow_interpreter.schema.models import Outcome
from workflow_interpreter.supervisor import (
    ExecLedger,
    Recovery,
    SteerIntent,
    SteerResult,
    procfs,
)
from workflow_interpreter.supervisor.errors import ContinuationRefused
from workflow_interpreter.supervisor.models import MonitorVerdict
from workflow_interpreter.supervisor.paths import write_record
from workflow_interpreter.supervisor.steer import instructions_digest

STEER_REASON: Final[str] = "the runner is looping on the same failing test"
STEER_INSTRUCTIONS: Final[str] = "stop rewriting the fixture; fix the assertion"


def steer(lab: Lab, parent_id: str, *, session_id: str = "made-up") -> SteerResult:
    """Steer a dispatched activation, with a caller-supplied (wrong) session id."""
    return lab.steerer.steer(
        lab.store.reads.load_activation(parent_id),
        reason=STEER_REASON,
        instructions=STEER_INSTRUCTIONS,
        continuation=entry_mint(
            mint_reason=MintReason.STEER_CONTINUATION,
            predecessor_activation_id=parent_id,
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
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="")
    parent = launched.activation
    assert launched.handle is not None
    session = launched.handle.session_id
    uuid.UUID(session)  # `prepare` minted it; claude refuses anything else.

    steered = steer(
        lab, parent.activation_id, session_id="a-session-the-caller-made-up"
    )

    assert steered.intent.continuation.session_id == session
    continuation = lab.dispatch(
        RunnerName.CLAUDE,
        request=steered.intent.continuation,
        instructions=STEER_INSTRUCTIONS,
    )

    receipt = continuation.receipt
    assert receipt is not None
    assert_resumes(receipt.argv, session)
    assert continuation.handle is not None
    assert continuation.handle.session_id == session


@pytest.mark.proc
def test_a_steer_continuation_runs_to_exit_recorded_through_supervisor_run(
    lab: Lab,
) -> None:
    """R1: the §8.1 continuation's only production entry point is this one.

    `Supervisor.run` is what dispatches, watches for `max_wall`, and records the
    exit; `Dispatcher.dispatch(instructions=...)` alone does none of those. And
    `Supervisor.run` has no argument for a human's prose — so once dispatch
    started REFUSING a continuation with no instructions, every steer that
    reached production was refused at the launch instead of resuming.

    Nothing but the `MintRequest` `Steerer` produced is handed over here. The
    text comes off the predecessor's own durable intent file, and the proof is
    the continuation's receipt plus a real watch loop reaching `exit-recorded`
    with exactly one exec on the ledger.
    """
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="")
    assert launched.handle is not None
    session = launched.handle.session_id
    steered = steer(lab, launched.activation.activation_id)

    result = lab.run(RunnerName.CLAUDE, request=steered.intent.continuation)

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
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="")
    parent = launched.activation
    assert launched.handle is not None
    session = launched.handle.session_id
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
    result = lab.run(RunnerName.CLAUDE, request=resolution.steer.intent.continuation)

    receipt = result.dispatch.receipt
    assert receipt is not None
    assert_resumes(receipt.argv, session)
    assert result.observation is not None
    assert result.observation.activation.metadata.lifecycle is Lifecycle.EXIT_RECORDED


@pytest.mark.proc
def test_steering_a_runner_with_no_resumable_session_refuses_before_the_kill(
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
    launched = lab.dispatch(RunnerName.CODEX, session_id="")
    parent = launched.activation
    assert launched.handle is not None
    assert launched.handle.session_id == ""

    with pytest.raises(ContinuationRefused, match="no session a continuation"):
        steer(lab, parent.activation_id)

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
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="")
    parent = launched.activation
    steered = steer(lab, parent.activation_id)
    lab.paths.steer_intent(parent.activation_id).unlink()

    with pytest.raises(ContinuationRefused, match="no steer instructions"):
        lab.dispatch(RunnerName.CLAUDE, request=steered.intent.continuation)


@pytest.mark.proc
def test_a_torn_steer_intent_refuses_rather_than_wedging_the_dispatch(
    lab: Lab,
) -> None:
    """Drill 18 applied to the intent file: malformed classifies, never raises.

    A crash can leave a half-written record. Letting the `WrapperDirError` out
    of `dispatch` would wedge the activation on every subsequent tick; treating
    it as absent walks to the same fail-closed refusal a missing file gets.
    """
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="")
    parent = launched.activation
    steered = steer(lab, parent.activation_id)
    lab.paths.steer_intent(parent.activation_id).write_text(
        '{"activation_id": "wf-', encoding="utf-8"
    )

    with pytest.raises(ContinuationRefused, match="no steer instructions"):
        lab.dispatch(RunnerName.CLAUDE, request=steered.intent.continuation)


@pytest.mark.proc
def test_resume_instructions_are_refused_for_a_mint_that_is_not_a_continuation(
    lab: Lab,
) -> None:
    """The other half: only a `steer-continuation` may rejoin another session."""
    with pytest.raises(ContinuationRefused, match="mint reason is entry"):
        lab.dispatch(RunnerName.CLAUDE, instructions=STEER_INSTRUCTIONS)


@pytest.mark.proc
def test_the_steer_intent_keeps_the_prose_out_of_every_bd_record(lab: Lab) -> None:
    """R1's boundary: the text is wrapper-local, the digest is what bd may see.

    The intent file carries the instructions so §5.6 can finish the steer; the
    §8.1 deviation recorded on the close carries the REASON, and nothing anywhere
    in the instance's beads carries the prose. Asserted over the whole bd
    workspace rather than over one field, because "which record could leak it"
    is exactly the question a field-by-field check cannot answer.
    """
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="", sleep_s=0.0)
    parent = launched.activation
    assert launched.handle is not None
    lab.await_exit(launched.handle)

    steered = steer(lab, parent.activation_id)

    assert steered.intent.instructions == STEER_INSTRUCTIONS
    assert steered.intent.instructions_digest == instructions_digest(STEER_INSTRUCTIONS)
    beads = lab.store.reads.instance_beads(lab.root.root_id)
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
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="")
    parent = launched.activation
    assert launched.handle is not None
    session = launched.handle.session_id
    steered = steer(lab, parent.activation_id)
    continuation = lab.run(RunnerName.CLAUDE, request=steered.intent.continuation)
    continuation_id = continuation.dispatch.activation.activation_id
    lab.store.close_activation(continuation_id, Outcome.ERROR_TRANSPORT)
    retry = entry_mint(
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=continuation_id,
        session_id=session,
    )

    result = lab.dispatch(RunnerName.CLAUDE, request=retry)

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
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="")
    parent = launched.activation
    assert launched.handle is not None
    session = launched.handle.session_id
    steered = steer(lab, parent.activation_id)
    continuation = lab.run(RunnerName.CLAUDE, request=steered.intent.continuation)
    continuation_id = continuation.dispatch.activation.activation_id
    lab.store.close_activation(continuation_id, Outcome.ERROR_TRANSPORT)
    first_retry = lab.store.mint_activation(
        lab.paths.root_id,
        entry_mint(
            mint_reason=MintReason.INFRA_RETRY,
            predecessor_activation_id=continuation_id,
            session_id=session,
        ),
    ).activation
    lab.store.close_activation(first_retry.activation_id, Outcome.ERROR_TRANSPORT)
    second_retry = entry_mint(
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=first_retry.activation_id,
        session_id=session,
    )

    result = lab.dispatch(RunnerName.CLAUDE, request=second_retry)

    receipt = result.receipt
    assert receipt is not None
    assert_resumes(receipt.argv, session)


@pytest.mark.proc
def test_a_retry_that_carries_a_steer_but_no_session_is_refused(lab: Lab) -> None:
    """A carried steer with no session to rejoin is refused BEFORE `prepare`.

    `prepare` mints a fresh uuid for a vendor that pre-assigns one, so a
    launch here would "resume" a session that has never existed — the CLI
    starting a brand-new one with the steer text as its first turn. Checked
    where `Steerer` checks it before the kill (`steer.py`), for the same
    reason: the answer is knowable before anything is spent.
    """
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="")
    steered = steer(lab, launched.activation.activation_id)
    continuation = lab.run(RunnerName.CLAUDE, request=steered.intent.continuation)
    continuation_id = continuation.dispatch.activation.activation_id
    lab.store.close_activation(continuation_id, Outcome.ERROR_TRANSPORT)
    retry = entry_mint(
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=continuation_id,
        session_id="",
    )

    with pytest.raises(ContinuationRefused, match="no session to rejoin"):
        lab.dispatch(RunnerName.CLAUDE, request=retry)


@pytest.mark.proc
def test_a_retry_of_a_continuation_whose_intent_is_gone_is_refused(lab: Lab) -> None:
    """No intent file, no carry-forward: refuse rather than launch fresh.

    The intent file is the only place the steer's prose is durable (bd never
    sees it), so a retry that cannot read it back has nothing to continue —
    and relaunching the node's original brief is exactly the silent loss this
    family exists to prevent.
    """
    launched = lab.dispatch(RunnerName.CLAUDE, session_id="")
    parent = launched.activation
    steered = steer(lab, parent.activation_id)
    continuation = lab.run(RunnerName.CLAUDE, request=steered.intent.continuation)
    continuation_id = continuation.dispatch.activation.activation_id
    lab.store.close_activation(continuation_id, Outcome.ERROR_TRANSPORT)
    lab.paths.steer_intent(parent.activation_id).unlink()
    retry = entry_mint(
        mint_reason=MintReason.INFRA_RETRY,
        predecessor_activation_id=continuation_id,
        session_id=str(uuid.uuid4()),
    )

    with pytest.raises(ContinuationRefused, match="infra-retry"):
        lab.dispatch(RunnerName.CLAUDE, request=retry)
