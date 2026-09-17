"""The structured findings one closed activation leaves (run-ledger §3.3).

The plan gives the ledger a `findings` table — `activation_id, round_no,
severity, text` — and S3 shipped it without a writer. This module is that
writer's vocabulary, and it lives in `bdio/` rather than in either backend
because both must answer the same way: the ledger inserts these rows inside
the close transaction, and the bd backend carries the very carriers they are
derived from, so `foreman/ledger_render.py` renders identical bytes on either.

**Two kinds of row, and the reviewer's come first.** A `review` row is the
reviewer's OWN numbered finding, parsed out of the artifact it wrote
(`parse_review_findings`) before its evidence was recorded, carried verbatim
on `Evidence.review_findings` — so both backends hold it and the ledger
persists exactly those bytes. A `diagnostic` row is derived from the close
carriers the record already holds (`Evidence`, §7), in this fixed order per
activation:

1. every verify check that did not exit zero — BLOCKER;
2. a graded outcome that contradicts the claimed one — MAJOR;
3. every undeclared effect — MAJOR;
4. a failing graded outcome — BLOCKER, carrying the note when there is one;
5. the note on a non-failing outcome — INFO.

Deterministic by construction: one pass over ordered carrier fields, no clock,
no set iteration, so two derivations of one unchanged record are equal.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio.carriers import ReviewFinding, Severity
from workflow_interpreter.bdio.records import ActivationRecord
from workflow_interpreter.schema.models import Outcome

MODEL: Final[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

MAX_FINDING_BYTES: Final[int] = 2048
"""Per finding: enough for a numbered item with its `file:line` and reasoning,
and small enough that even a full set stays a rounding error against the
~130 KB argv ceiling ADR 0003 measured."""
MAX_REVIEW_FINDINGS_BYTES: Final[int] = 8192
"""Every review finding of ONE activation, together. The carrier rides the bd
`--metadata` argv element beside the rest of the evidence (2–5 KB in
production, ADR 0003), so this is the whole budget the extraction may spend."""
TRUNCATION_MARKER: Final[str] = " …[truncated]"
"""Appended to any text a bound cut, so a shortened finding is never mistaken
for a complete one."""

_NUMBERED_ITEM: Final[re.Pattern[str]] = re.compile(
    r"^\s{0,3}(?:[*_]{0,2})(\d{1,3})[.)]\s"
)
"""What starts one reviewer finding: a numbered list item, optionally emphasised
(`**1.** …`) and slightly indented, exactly as review reports are written."""
_SEVERITY_WORD: Final[re.Pattern[str]] = re.compile(r"\b(BLOCKER|MAJOR|MINOR|INFO)\b")
"""The reviewer's own severity word, taken from the item that declares one."""
DEFAULT_REVIEW_SEVERITY: Final[Severity] = Severity.MAJOR
"""What an item that names no severity is stored as. A reviewer finding is a
problem by definition, and filing it as INFO would hide it under the
diagnostics; MAJOR is the honest floor, and the verbatim text says the rest."""

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


class FindingKind(StrEnum):
    """Whose statement one row is — the `findings.kind` column."""

    REVIEW = "review"
    DIAGNOSTIC = "diagnostic"


class Finding(BaseModel):
    """One row of §3.3's `findings`, from one closed activation."""

    model_config = MODEL

    activation_id: str
    round_no: int
    severity: Severity
    text: str
    kind: FindingKind = FindingKind.DIAGNOSTIC


def _bounded(text: str, limit: int) -> str:
    """`text` cut to `limit` BYTES, marked when it was cut.

    Cut on the encoded form and decoded back with the partial character
    dropped, because a bound measured in bytes and applied to characters is
    not a bound on what the carrier costs.
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    marker = TRUNCATION_MARKER.encode("utf-8")
    keep = max(limit - len(marker), 0)
    return encoded[:keep].decode("utf-8", "ignore") + TRUNCATION_MARKER


def _severity_of(text: str) -> Severity:
    """The severity the reviewer named in this item, or the documented floor."""
    match = _SEVERITY_WORD.search(text)
    return (
        DEFAULT_REVIEW_SEVERITY if match is None else Severity(match.group(1).lower())
    )


def parse_review_findings(text: str) -> tuple[ReviewFinding, ...]:
    """The reviewer's own findings, read out of the artifact it wrote (§3.3).

    Numbered list items are the structure review reports actually have, so
    each one becomes a row carrying its own bytes. An artifact with no such
    structure is NOT refused and NOT summarised: it becomes a single bounded
    verbatim row, because a finding the engine could not parse is still a
    finding a human must read.
    """
    stripped = text.strip()
    if not stripped:
        return ()
    items: list[list[str]] = []
    for line in stripped.splitlines():
        if _NUMBERED_ITEM.match(line):
            items.append([line])
        elif items:
            items[-1].append(line)
    bodies = ["\n".join(item).strip() for item in items] or [stripped]
    findings: list[ReviewFinding] = []
    spent = 0
    for body in bodies:
        remaining = MAX_REVIEW_FINDINGS_BYTES - spent
        if remaining <= 0:
            break
        bounded = _bounded(body, min(MAX_FINDING_BYTES, remaining))
        findings.append(ReviewFinding(severity=_severity_of(body), text=bounded))
        spent += len(bounded.encode("utf-8"))
    return tuple(findings)


def findings_of(activation: ActivationRecord) -> tuple[Finding, ...]:
    """Every finding one CLOSED activation's carriers state (§3.3).

    The reviewer's own findings first, verbatim, then the derived diagnostics:
    a reader of `findings.md` should meet the review before the engine's
    account of it. An activation that has not completed answers with nothing:
    a round still running has no verdict, and a row written for it would have
    to be revised.
    """
    metadata = activation.metadata
    if not metadata.is_completed or metadata.outcome is None:
        return ()
    evidence = metadata.evidence
    round_no = int(metadata.round_no)
    reviewed: list[tuple[Severity, str]] = [
        (item.severity, item.text)
        for item in (() if evidence is None else evidence.review_findings)
    ]
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
            kind=kind,
        )
        for kind, rows in (
            (FindingKind.REVIEW, reviewed),
            (FindingKind.DIAGNOSTIC, texts),
        )
        for severity, text in rows
    )
