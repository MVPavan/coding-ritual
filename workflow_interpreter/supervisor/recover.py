"""§5.6 recovery classification — liveness-proving, and never a crash loop.

A tick that finds a dispatched-not-closed activation must answer one question
with evidence: did this run finish, is it still running, or is it gone? The
three §5.6 cases are evaluated in the spec's order, with two fail-closed
answers in front of them that the spec's three cannot express:

0a. **steer-pending** — a durable §8.1 steer intent and no close. The death was
    DELIBERATE, and the human is owed the continuation the intent names.
    Reading this as case 3 closed `error_transport`, spent an infra retry, and
    dropped the continuation; recovery finishes the steer instead, idempotently
    (`Steerer.resume`).
0b. **indeterminate** — liveness could not be answered at all (`/proc`
    unreadable for a reason other than "gone"). Nothing is closed and nothing
    is signalled: the question §5.6 asks needs an answer, and a guess here
    lets a retry run beside a survivor.
1.  **exit-recorded** — bd holds an exit record, or the wrapper dir does. The
    on-disk file is the crash-window fallback for exactly the window between
    the child's exit and `record_exit`; a MISSING file with a bd record is
    still `exit-recorded` (§5.3). `evidence_complete` says whether the §7
    computation also finished — if it did not, §7 is simply re-run, because it
    is deterministic over git and the wrapper dir.
2.  **running** — the process is alive AND provably ours: pid present, boot id
    equal, `/proc` start time equal. Two out of three is not liveness; it is a
    reused pid, and the wrapper's flags govern only when all three hold (§8.2).
3.  **dead-without-exit** — everything else, including identity mismatch. TERM
    the group (idempotent, and a no-op once the identity check fails), pin any
    orphan commit FIRST so the evidence survives, then close `error_transport`
    with `evidence: exit_unobserved`. A fresh attempt is subject to the §10.2
    infra cap, which is the foreman's call, not this module's.

**The pin is a precondition of the close, not a best effort beside it.** §5.6
says the wrapper pins an ahead commit FIRST, and the reason is that the close
is what releases the next attempt to reset the tree. Swallowing a pin failure
and closing anyway left a real commit with no ref for a reset to orphan and a
gc to collect, so a pin that could neither succeed nor be shown unnecessary now
leaves the activation open for the next tick.

**Preserving a commit is not the same as claiming it.** Recovery runs the same
attribution tests live pinning runs — it used to run none, so in-repo it named
whatever the human had committed since the wrapper died as this activation's
artifact, which then WAS the wrapper lineage authorizing the next reset to
destroy it (probed). An ahead commit it cannot attribute goes to the
`orphan/` quarantine instead: reachable forever, claimed by nobody, and
invisible to `_is_runner_lineage`.

**Malformed input classifies; it never raises.** A truncated exit file or a
corrupt JSONL tail is recorded in `malformed` and treated as absent, which
walks the classification toward case 3. The alternative is a tick that dies on
the same bad file forever (drill 18), and a crash loop is strictly worse than a
conservative `error_transport`. (A malformed launch RECEIPT is the dispatch
path's problem, and `Dispatcher._reattach` classifies it the same way.)
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

import structlog
from pydantic import BaseModel

from workflow_interpreter.bdio import (
    ActivationRecord,
    ArtifactIdentity,
    Evidence,
    ExitRecord,
    Lifecycle,
    Outcome,
    WorkflowStore,
)
from workflow_interpreter.schema.models import Node
from workflow_interpreter.supervisor import procfs
from workflow_interpreter.supervisor.channels import read_effects
from workflow_interpreter.supervisor.clock import Clock, to_iso
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.errors import SupervisorError, WrapperDirError
from workflow_interpreter.supervisor.models import (
    EXIT_CODE_UNOBSERVED,
    RECORD_MODEL,
    CompletionEvidence,
    ExitReason,
    Liveness,
    LivenessProof,
    PinOutcome,
    PinResult,
    RecoveryCase,
    RecoveryClassification,
    SteerIntent,
    TerminationProof,
)
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    read_tail,
)
from workflow_interpreter.supervisor.steer import Steerer, SteerResult
from workflow_interpreter.supervisor.workspace import Workspace

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

EVIDENCE_EXIT_UNOBSERVED: Final[str] = "exit_unobserved"
"""The §5.6 case-3 evidence note, recorded verbatim on the close."""

MALFORMED_EXIT_FILE: Final[str] = "exit-file"
MALFORMED_LOG: Final[str] = "log"
MALFORMED_COMPLETION: Final[str] = "completion"
MALFORMED_STEER_INTENT: Final[str] = "steer-intent"

_HALT_INDETERMINATE: Final[str] = (
    "liveness could not be proven either way; closing would let a retry run "
    "beside a child that may still be alive (§5.6)"
)
_HALT_ORPHAN_PIN: Final[str] = (
    "the ahead commit could neither be pinned nor ruled out; closing would "
    "authorize a reset that leaves it unreachable (§5.6)"
)
_NOTE_QUARANTINED: Final[str] = (
    "the ahead commit {commit} could not be attributed to this activation and "
    "is preserved, unclaimed, at {ref}"
)

_OPEN_LIFECYCLES: Final[frozenset[Lifecycle]] = frozenset(
    {
        Lifecycle.MINTED,
        Lifecycle.DISPATCHED,
        Lifecycle.EXIT_RECORDED,
        Lifecycle.EVIDENCE_RECORDED,
    }
)
"""States a steer can still be finished from. A CLOSED or SUPERSEDED activation
has already reached its terminal, and a leftover intent file beside it is
residue, not an instruction."""


class RecoveryResolution(BaseModel):
    """What resolving a case-3 activation did, and the evidence it preserved."""

    model_config = RECORD_MODEL

    classification: RecoveryClassification
    termination: TerminationProof | None = None
    pin: PinResult | None = None
    """What became of any commit the dead attempt left ahead of its base:
    claimed as its artifact, QUARANTINED as unattributable, or nothing at all."""
    closed: ActivationRecord | None = None
    steer: SteerResult | None = None
    halted: str | None = None
    """Why this activation was left OPEN. Set whenever recovery could not
    resolve it safely — an unanswerable liveness question, or an ahead commit
    that could be neither pinned nor ruled out."""

    @property
    def orphan(self) -> ArtifactIdentity | None:
        """The commit recovery CLAIMED as this activation's artifact, if any.

        `None` for a quarantined commit, which is preserved without being
        claimed: recording it as the artifact is the false statement §7.4
        exists to forbid, and it is what turned a human's commit into wrapper
        lineage the next reset was allowed to destroy (probed).
        """
        return None if self.pin is None else self.pin.identity


def _read_optional[RecordT: BaseModel](
    path: Path, model: type[RecordT], marker: str, malformed: list[str]
) -> RecordT | None:
    """Read a wrapper-dir record; a malformed one is recorded and treated as absent."""
    try:
        return read_record(path, model)
    except WrapperDirError:
        malformed.append(marker)
        return None


def classify(
    config: SupervisorConfig,
    paths: WrapperPaths,
    activation: ActivationRecord,
) -> RecoveryClassification:
    """Answer §5.6's question for one activation. Pure: nothing is written."""
    activation_id = activation.activation_id
    malformed: list[str] = []

    recorded = activation.metadata.exit_record
    from_file = False
    if recorded is None:
        recorded = _read_optional(
            paths.exit_file(activation_id), ExitRecord, MALFORMED_EXIT_FILE, malformed
        )
        from_file = recorded is not None
    completion = _read_optional(
        paths.completion(activation_id),
        CompletionEvidence,
        MALFORMED_COMPLETION,
        malformed,
    )
    intent = _read_optional(
        paths.steer_intent(activation_id),
        SteerIntent,
        MALFORMED_STEER_INTENT,
        malformed,
    )
    if activation.metadata.lifecycle not in _OPEN_LIFECYCLES:
        intent = None

    try:
        tail = read_tail(paths.log(activation_id), config.log_tail_bytes)
    except WrapperDirError:
        malformed.append(MALFORMED_LOG)
        tail = ""

    handle = activation.metadata.handle
    proof: LivenessProof | None = (
        None if handle is None else procfs.prove_liveness(config, handle)
    )
    return RecoveryClassification(
        case=_case(intent, recorded, proof),
        activation_id=activation_id,
        proof=proof,
        exit_record=recorded,
        exit_from_file=from_file,
        evidence_complete=completion is not None,
        steer_intent=intent,
        log_tail=tail,
        malformed=tuple(malformed),
    )


def _case(
    intent: SteerIntent | None,
    recorded: ExitRecord | None,
    proof: LivenessProof | None,
) -> RecoveryCase:
    """The §5.6 case, with the two fail-closed answers checked first.

    The steer intent outranks the exit record on purpose: `Steerer` writes the
    exit file between the kill and the close, so a crash inside that window
    leaves BOTH, and reading the exit record first would hand a deliberate kill
    to §7 — which would find no marker and grade it `fail_code`.
    """
    if intent is not None:
        return RecoveryCase.STEER_PENDING
    if recorded is not None:
        return RecoveryCase.EXIT_RECORDED
    if proof is not None and proof.status is Liveness.INDETERMINATE:
        return RecoveryCase.INDETERMINATE
    if proof is not None and proof.alive:
        return RecoveryCase.RUNNING
    return RecoveryCase.DEAD_WITHOUT_EXIT


class Recovery:
    """Classifies a dispatched-not-closed activation and resolves case 3 (§5.6)."""

    def __init__(
        self,
        config: SupervisorConfig,
        paths: WrapperPaths,
        store: WorkflowStore,
        workspace: Workspace,
        clock: Clock,
    ) -> None:
        self._config = config
        self._paths = paths
        self._store = store
        self._workspace = workspace
        self._clock = clock
        self._steerer = Steerer(config, paths, store, clock)

    def classify(self, activation: ActivationRecord) -> RecoveryClassification:
        """The §5.6 case for this activation, computed from evidence alone."""
        return classify(self._config, self._paths, activation)

    def resolve(self, activation: ActivationRecord, node: Node) -> RecoveryResolution:
        """Classify, then resolve the cases that have a safe resolution.

        Case 3's order is the §5.6 order and matters: TERM the group before
        touching git (a process that may still be committing must not race the
        pin), pin the orphan commit before the bd write (§7.4's "git first, bd
        second"), and close last — the close is what the frontier routes on.

        `running`, `exit-recorded` and `indeterminate` are all left alone: the
        first two belong to §8.2 and §7, and the third has no evidence to act
        on. `steer-pending` is finished rather than closed.
        """
        classification = self.classify(activation)
        if classification.case is RecoveryCase.STEER_PENDING:
            return self._finish_steer(activation, classification)
        if classification.case is RecoveryCase.INDETERMINATE:
            _LOG.error(
                "wf.recovery.indeterminate",
                activation_id=activation.activation_id,
                error=None
                if classification.proof is None
                else classification.proof.read_error,
            )
            return RecoveryResolution(
                classification=classification, halted=_HALT_INDETERMINATE
            )
        if classification.case is not RecoveryCase.DEAD_WITHOUT_EXIT:
            return RecoveryResolution(classification=classification)

        handle = activation.metadata.handle
        termination = (
            None
            if handle is None
            else procfs.terminate(self._config, handle, self._clock)
        )
        pin = self._pin_orphan(activation, node)
        if not pin.settled:
            # §5.6 pins the ahead commit FIRST for a reason: the close is what
            # releases the next attempt to reset this tree. Closing now would
            # authorize destroying a commit nothing references.
            return RecoveryResolution(
                classification=classification,
                termination=termination,
                pin=pin,
                halted=_HALT_ORPHAN_PIN,
            )
        closed = self._close_unobserved(activation, pin)
        _LOG.warning(
            "wf.recovery.exit_unobserved",
            activation_id=activation.activation_id,
            ahead_commit=pin.commit,
            pin_outcome=pin.outcome.value,
            malformed=classification.malformed,
        )
        return RecoveryResolution(
            classification=classification,
            termination=termination,
            pin=pin,
            closed=closed,
        )

    def _finish_steer(
        self, activation: ActivationRecord, classification: RecoveryClassification
    ) -> RecoveryResolution:
        """Carry a crashed §8.1 steer to its end, idempotently (§8.1, drill 14)."""
        intent = classification.steer_intent
        if intent is None:  # pragma: no cover - the case is derived from it
            return RecoveryResolution(classification=classification)
        result = self._steerer.resume(activation, intent)
        _LOG.warning(
            "wf.recovery.steer_finished",
            activation_id=activation.activation_id,
            continuation_id=result.continuation.activation.activation_id,
        )
        return RecoveryResolution(
            classification=classification,
            termination=result.termination,
            closed=result.closed,
            steer=result,
        )

    def _pin_orphan(self, activation: ActivationRecord, node: Node) -> PinResult:
        """Preserve a commit the dead attempt left ahead of its base (§5.6).

        It runs the SAME attribution tests live pinning runs, and that is the
        whole point of the method. Recovery used to pass no declaration at all,
        so in-repo it pinned whatever HEAD happened to be — including a commit
        the human made after the wrapper died. That pin then WAS wrapper
        lineage, `head_protected` went false, and the next precondition reset
        the human's commit away (probed).

        The declaration comes from the effects manifest the dead runner left.
        No manifest in-repo means no evidence separating the two authors, so the
        commit is QUARANTINED: preserved under `orphan/`, claimed by nobody.

        `settled` on the result is what the close depends on: pinned, preserved,
        or provably absent. A git failure settles none of those — it leaves the
        question open, and an open question is not a licence to close.
        """
        try:
            return self._workspace.pin_artifact(
                activation,
                node,
                declared=self._declared_effects(activation.activation_id),
                quarantine=True,
            )
        except (SupervisorError, OSError) as exc:
            _LOG.error(
                "wf.recovery.orphan_pin_failed",
                activation_id=activation.activation_id,
                error=str(exc),
            )
            return PinResult(outcome=PinOutcome.REFUSED, reason=str(exc))

    def _declared_effects(self, activation_id: str) -> frozenset[str] | None:
        """The dead runner's `$WF_EFFECTS_FILE` paths, or `None` when there are none.

        `None` and `frozenset()` are different answers and both matter: an empty
        manifest is a runner that declared it changed nothing, while no manifest
        at all is no evidence — which in-repo makes any ahead commit
        unattributable (§7.5, §12).
        """
        effects, _ = read_effects(self._paths.effects(activation_id))
        return None if effects is None else frozenset(effects.paths)

    def _close_unobserved(
        self, activation: ActivationRecord, pin: PinResult
    ) -> ActivationRecord:
        """Close `error_transport` with `evidence: exit_unobserved` (§5.6).

        The exit is mirrored into bd first when the lifecycle still allows it,
        so the trace shows WHAT was observed (nothing, at this timestamp) rather
        than jumping from `dispatched` to a close with no terminal record. The
        exit code is the `EXIT_CODE_UNOBSERVED` sentinel and never `0`: the one
        thing this record must not be able to state is a success nobody saw.

        A quarantined commit is named in the NOTE and never in `artifact`: the
        evidence has to say a commit exists and where to find it without saying
        this activation produced it (§7.4).
        """
        activation_id = activation.activation_id
        if activation.metadata.lifecycle is Lifecycle.DISPATCHED:
            self._store.record_exit(
                activation_id,
                ExitRecord(
                    exit_code=EXIT_CODE_UNOBSERVED,
                    ended_at=to_iso(self._clock.now()),
                    reason=ExitReason.EXIT_UNOBSERVED.value,
                ),
            )
        note = EVIDENCE_EXIT_UNOBSERVED
        if pin.outcome is PinOutcome.QUARANTINED:
            note = f"{note}; {_NOTE_QUARANTINED.format(commit=pin.commit, ref=pin.ref)}"
        return self._store.close_activation(
            activation_id,
            Outcome.ERROR_TRANSPORT,
            evidence=Evidence(artifact=pin.identity, note=note),
        )
