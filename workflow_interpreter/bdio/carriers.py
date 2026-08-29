"""Shared BDI/O carrier primitives kept below :mod:`bdio.wire`.

The wire module re-exports these names so established callers retain their
public import path while structural metadata carriers stay within their cap.
"""

from __future__ import annotations

import hashlib
import re
from enum import StrEnum
from typing import Annotated, Final

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    StringConstraints,
    model_validator,
)

from workflow_interpreter.schema.models import Outcome

WIRE_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True,
    extra="forbid",
    populate_by_name=True,
    arbitrary_types_allowed=False,
)
"""`extra="forbid"` on read too: an unexpected metadata key on a workflow bead
is tamper evidence (§0), so it fails loud instead of being ignored."""

Metadata = dict[str, JsonValue]
JSON_SAFE_INT_LIMIT: Final[int] = 2**53 - 1
"""bd's JSON path runs integers through float64 and rounds silently past this
magnitude (probed). The read-back check in `client.py` catches it after the
fact; this bound refuses it before the write."""
JsonSafeInt = Annotated[int, Field(ge=-JSON_SAFE_INT_LIMIT, le=JSON_SAFE_INT_LIMIT)]
"""Every carrier integer: exactly representable through bd's JSON path."""

COMMIT_OID_PATTERN: Final[str] = r"^[0-9a-f]{40}$"
CommitOid = Annotated[str, StringConstraints(pattern=COMMIT_OID_PATTERN)]
"""A full git object id, lowercase hex. Where §3.2 states a commit it must BE a
commit: `""` used to satisfy the type, and an all-empty carrier then compared
equal to an activation that had nothing recorded at all — so the write that
should have happened was skipped as "already recorded"."""

_SCOPE_PLACEHOLDER: Final[str] = "{scope}"
_SCOPE_CAPTURE: Final[str] = "([^.]+)"


class IssueType(StrEnum):
    """The bd issue types this wrapper may create — a closed set.

    `event` is native in bd 1.1.0 (probed 2026-08-25); the `types.custom`
    prerequisite §11 assumed does not exist.
    """

    TASK = "task"
    EVENT = "event"


class WfKind(StrEnum):
    """The §3 discriminator carried by every workflow bead."""

    ROOT = "root"
    ACTIVATION = "activation"
    GATE = "gate"
    EVENT = "event"
    CANARY = "canary"


class Lifecycle(StrEnum):
    """§5.1 activation states."""

    MINTED = "minted"
    DISPATCHED = "dispatched"
    EXIT_RECORDED = "exit-recorded"
    EVIDENCE_RECORDED = "evidence-recorded"
    CLOSED = "closed"
    SUPERSEDED = "superseded"


TERMINAL_LIFECYCLES: Final[frozenset[Lifecycle]] = frozenset(
    {Lifecycle.CLOSED, Lifecycle.SUPERSEDED}
)
"""The two §5.1 states nothing is ever written past."""


class GateState(StrEnum):
    """A §3.4 gate bead is open until `close_gate_verified` succeeds."""

    OPEN = "open"
    CLOSED = "closed"


class ConfigSource(StrEnum):
    """§3.1 provenance tag on every resolved setting."""

    GRAPH_DEFAULT = "graph-default"
    ROLE_BINDING = "role-binding"
    PROJECT_CONFIG = "project-config"
    INSTANCE_OVERRIDE = "instance-override"


class MintReason(StrEnum):
    """Why an activation is being minted — selects the §10 predicates.

    `INFRA_RETRY` and `STEER_CONTINUATION` inherit the current `round_no`
    (§10.1) and are capped by `max_infra_retries` / `max_steers` (§10.2).
    """

    ENTRY = "entry"
    EDGE = "edge"
    INFRA_RETRY = "infra-retry"
    STEER_CONTINUATION = "steer-continuation"


class GateReason(StrEnum):
    """Why a gate bead exists — exhaustion and halt gates are keyed differently."""

    TRANSITION = "transition"
    EXHAUSTION = "exhaustion"
    HALT = "halt"


class BoundSetting(StrEnum):
    """Resolved-config keys that override a pinned bound (§3.1, §10.4).

    Dotted scope + field. The spec fixes the provenance tagging but not the
    key syntax; this is the wrapper's convention, applied consistently by
    `bounds.effective_bound`.
    """

    MAX_TOTAL_ACTIVATIONS = "instance.max_total_activations"
    MAX_ENTRIES = "region.{scope}.max_entries"
    MAX_INFRA_RETRIES = "node.{scope}.max_infra_retries"
    MAX_STEERS = "node.{scope}.max_steers"

    def at(self, scope: str = "") -> str:
        """The concrete resolved-config key for this bound at `scope`."""
        return self.value.format(scope=scope)

    @property
    def scoped(self) -> bool:
        """Whether this bound is scoped to a named region or node."""
        return _SCOPE_PLACEHOLDER in self.value


class ScopedBound(BaseModel):
    """A resolved-config bound key decomposed into its setting and scope."""

    model_config = WIRE_MODEL

    setting: BoundSetting
    scope: str = ""


def parse_bound_key(key: str) -> ScopedBound | None:
    """Decompose a resolved-config bound key, or `None` if it is not one.

    §9 restricts a `rebudget` mutation to this closed vocabulary, so an
    unparseable key must be distinguishable from a valid one — never coerced.
    """
    for setting in BoundSetting:
        if not setting.scoped:
            if key == setting.value:
                return ScopedBound(setting=setting)
            continue
        pattern = re.escape(setting.value).replace(
            re.escape(_SCOPE_PLACEHOLDER), _SCOPE_CAPTURE
        )
        match = re.fullmatch(pattern, key)
        if match is not None:
            return ScopedBound(setting=setting, scope=match.group(1))
    return None


class Breaker(StrEnum):
    """§10.5 wrapper-computed breaker flags recorded as evidence."""

    NO_PROGRESS = "no_progress"


class ResolvedSetting(BaseModel):
    """One resolved configuration value with its §3.1 provenance tag."""

    model_config = WIRE_MODEL

    key: str
    value: str | JsonSafeInt | bool
    source: ConfigSource


class InputBinding(BaseModel):
    """An immutable input tuple bound at mint (§2 'Input binding')."""

    model_config = WIRE_MODEL

    name: str
    producer_activation_id: str
    artifact_ref: str
    digest: str


class ProcessHandle(BaseModel):
    """§5.3 handle — boot id and start time defeat PID reuse and reboots."""

    model_config = WIRE_MODEL

    pid: JsonSafeInt
    pgid: JsonSafeInt
    host: str
    host_boot_id: str
    proc_start_time: str
    started_at: str
    log_path: str
    session_id: str


class ExitRecord(BaseModel):
    """The wrapper's mirrored exit record — the §7.1 post-crash observable."""

    model_config = WIRE_MODEL

    exit_code: JsonSafeInt
    ended_at: str
    reason: str


class ArtifactIdentity(BaseModel):
    """§7.4 honest naming: git object ids, recorded as such."""

    model_config = WIRE_MODEL

    commit_oid: str
    tree_oid: str


class VerifyOutcome(BaseModel):
    """One `verify` entry's result, with the §7.3 pinned-source digest."""

    model_config = WIRE_MODEL

    cmd: str
    exit_code: JsonSafeInt
    script_digest: str


class Evidence(BaseModel):
    """Computed, never claimed (§7)."""

    model_config = WIRE_MODEL

    verify: tuple[VerifyOutcome, ...] = ()
    artifact: ArtifactIdentity | None = None
    undeclared_effects: tuple[str, ...] = ()
    breaker: Breaker | None = None
    note: str | None = None
    outputs_ref: str | None = None
    outputs_tree_oid: str | None = None
    claimed_outcome: Outcome | None = None


class Usage(BaseModel):
    """Normalized runner usage; `known = False` is legal (§6)."""

    model_config = WIRE_MODEL

    known: bool
    input_tokens: JsonSafeInt | None = None
    output_tokens: JsonSafeInt | None = None
    cost_usd: str | None = None
    """Money as a decimal string: JSON floats are not exact, and bd's JSON
    path silently rounds large numerics (probed)."""


class Deviation(BaseModel):
    """A tier-2 deviation record (§1)."""

    model_config = WIRE_MODEL

    kind: str
    reason: str
    recorded_at: str
    instructions_digest: str | None = None
    gate_id: str | None = None


class InstanceInput(BaseModel):
    """An immutable instance-scoped input pinned on the root."""

    model_config = WIRE_MODEL

    name: str
    sha256: str
    body: str

    @model_validator(mode="after")
    def _matches_body(self) -> InstanceInput:
        """Refuse a declared digest that does not authenticate the stored body."""
        if hashlib.sha256(self.body.encode("utf-8")).hexdigest() != self.sha256:
            raise ValueError("instance input sha256 does not match body")
        return self
