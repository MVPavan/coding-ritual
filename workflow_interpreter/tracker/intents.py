"""Desired states, never toggles — and the three ways one can be answered.

Why a desired state (R2): the outbox retries, and a retry of "add the label"
is not the same operation twice while a retry of "the label should be present"
is. `Claim(held=False)` is the release for exactly that reason — a separate
`Release` intent would be a toggle wearing a noun's name.

The union is discriminated on `kind`, so an outbox row parses back into the
same intent that was enqueued without the enqueuer having to say which class it
was.
"""

from __future__ import annotations

from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from workflow_interpreter.tracker.constants import IntentKind, ResultKind
from workflow_interpreter.tracker.models import TrackerRef, WorkItem


class _Intent(BaseModel):
    """The two fields every intent has: what it wants, and about which item."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: IntentKind
    ref: TrackerRef


class Claim(_Intent):
    """This actor should (or should not) hold the item."""

    kind: Literal[IntentKind.CLAIM] = IntentKind.CLAIM
    actor: str
    held: bool = True


class Close(_Intent):
    """The item should be closed, with this reason recorded."""

    kind: Literal[IntentKind.CLOSE] = IntentKind.CLOSE
    reason: str


class SetFlag(_Intent):
    """This flag should be present on the item, or absent from it."""

    kind: Literal[IntentKind.SET_FLAG] = IntentKind.SET_FLAG
    flag: str
    on: bool


class Annotate(_Intent):
    """This key should read as this text on the item."""

    kind: Literal[IntentKind.ANNOTATE] = IntentKind.ANNOTATE
    key: str
    text: str


type TrackerIntent = Claim | Close | SetFlag | Annotate

INTENT_ADAPTER: Final[TypeAdapter[TrackerIntent]] = TypeAdapter(
    Annotated[Claim | Close | SetFlag | Annotate, Field(discriminator="kind")]
)
"""Parses an outbox row back into the intent that was enqueued (§3.3)."""


class _Result(BaseModel):
    """What a tracker answered, in the one shape every caller branches on."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    result: ResultKind


class Applied(_Result):
    """The desired state is the tracker's state, read back."""

    result: ResultKind = ResultKind.APPLIED
    observed: WorkItem | None = None


class Conflict(_Result):
    """The tracker disagrees. The caller decides; nothing is rolled back."""

    result: ResultKind = ResultKind.CONFLICT
    reason: str
    observed: WorkItem | None = None


class Unknown(_Result):
    """The tracker did not answer. This, and only this, goes to the outbox."""

    result: ResultKind = ResultKind.UNKNOWN
    reason: str


type TrackerResult = Applied | Conflict | Unknown
