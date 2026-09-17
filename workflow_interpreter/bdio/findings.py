"""The structured findings one closed activation leaves (run-ledger §3.3).

The plan gives the ledger a `findings` table — `activation_id, round_no,
severity, text` — and S3 shipped it without a writer. This module is that
writer's vocabulary, and it lives in `bdio/` rather than in either backend
because both must answer the same way: the ledger inserts these rows inside
the close transaction, and the bd backend carries the very carriers they are
derived from, so `foreman/ledger_render.py` renders identical bytes on either.

**The mapping is derivation, not a new contract.** No runner output carries a
"findings" field today, and inventing one would change what a reviewer must
emit. So a finding is read from the close carriers the record already holds
(`Evidence`, §7), in this fixed order per activation:

1. every verify check that did not exit zero — BLOCKER;
2. a graded outcome that contradicts the claimed one — MAJOR;
3. every undeclared effect — MAJOR;
4. a failing graded outcome — BLOCKER, carrying the note when there is one;
5. the note on a non-failing outcome — INFO.

Deterministic by construction: one pass over ordered carrier fields, no clock,
no set iteration, so two derivations of one unchanged record are equal.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.records import ActivationRecord
from workflow_interpreter.schema.models import Outcome

MODEL: Final[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

FAILING_OUTCOMES: Final[frozenset[Outcome]] = frozenset(
    {
        Outcome.FAIL_CODE,
        Outcome.FAIL_PLAN,
        Outcome.REJECT,
        Outcome.ERROR_RUNNER,
        Outcome.ERROR_TRANSPORT,
    }
)
"""Outcomes that ARE a finding on their own: the round did not deliver."""

TEXT_VERIFY: Final[str] = "verify `{cmd}` exited {exit_code} after {attempts}"
TEXT_CLAIM: Final[str] = "claimed {claimed}, graded {outcome}"
TEXT_UNDECLARED: Final[str] = "undeclared effect: {path}"
TEXT_OUTCOME: Final[str] = "{node} graded {outcome}"
TEXT_OUTCOME_NOTE: Final[str] = "{node} graded {outcome}: {note}"


class Severity(StrEnum):
    """How much of a problem one finding is — the `findings.severity` column."""

    BLOCKER = "blocker"
    MAJOR = "major"
    INFO = "info"


class Finding(BaseModel):
    """One row of §3.3's `findings`, derived from one closed activation."""

    model_config = MODEL

    activation_id: str
    round_no: int
    severity: Severity
    text: str


def findings_of(activation: ActivationRecord) -> tuple[Finding, ...]:
    """Every finding one CLOSED activation's carriers state (§3.3).

    An activation that has not completed answers with nothing: a round still
    running has no verdict, and a row written for it would have to be revised.
    """
    metadata = activation.metadata
    if not metadata.is_completed or metadata.outcome is None:
        return ()
    evidence = metadata.evidence
    round_no = int(metadata.round_no)
    texts: list[tuple[Severity, str]] = []
    for check in () if evidence is None else evidence.verify:
        if check.exit_code != 0:
            texts.append(
                (
                    Severity.BLOCKER,
                    TEXT_VERIFY.format(
                        cmd=check.cmd,
                        exit_code=int(check.exit_code),
                        attempts=int(check.attempts),
                    ),
                )
            )
    claimed = None if evidence is None else evidence.claimed_outcome
    if claimed is not None and claimed is not metadata.outcome:
        texts.append(
            (
                Severity.MAJOR,
                TEXT_CLAIM.format(
                    claimed=claimed.value, outcome=metadata.outcome.value
                ),
            )
        )
    for path in () if evidence is None else evidence.undeclared_effects:
        texts.append((Severity.MAJOR, TEXT_UNDECLARED.format(path=path)))
    note = None if evidence is None else evidence.note
    if metadata.outcome in FAILING_OUTCOMES:
        texts.append(
            (
                Severity.BLOCKER,
                (
                    TEXT_OUTCOME.format(
                        node=metadata.node, outcome=metadata.outcome.value
                    )
                    if note is None
                    else TEXT_OUTCOME_NOTE.format(
                        node=metadata.node,
                        outcome=metadata.outcome.value,
                        note=note,
                    )
                ),
            )
        )
    elif note is not None:
        texts.append((Severity.INFO, note))
    return tuple(
        Finding(
            activation_id=activation.activation_id,
            round_no=round_no,
            severity=severity,
            text=text,
        )
        for severity, text in texts
    )
