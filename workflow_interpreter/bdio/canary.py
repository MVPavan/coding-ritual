"""§11 startup canary — run at the top of every tick, before any dispatch.

Two assertions: bd reports the pinned backend identity, and one ephemeral
wisp round-trips its metadata. A fallback or schema-skewed store must refuse
dispatch loudly rather than degrade quietly (drill 11), and the round-trip
proves the §3 carrier still works on this store before anything is bet on it.

The wisp is the ONE permitted decision-irrelevant ephemeral bead (§3.4). It is
left for TTL compaction rather than closed, so the wrapper never needs delete
authority.
"""

from __future__ import annotations

import secrets
from typing import Final

from workflow_interpreter.bdio.client import BdClient
from workflow_interpreter.bdio.errors import (
    BdCommandError,
    CanaryFailedError,
    LossyWriteError,
)
from workflow_interpreter.bdio.records import CanaryResult
from workflow_interpreter.bdio.wire import CanaryMetadata, metadata_dict

CANARY_WISP_TYPE: Final[str] = "heartbeat"
CANARY_NONCE_BYTES: Final[int] = 16
CANARY_PROBE: Final[tuple[int, ...]] = (1, 2, 3)

_CONTEXT_BACKEND: Final[str] = "backend"
_CONTEXT_DOLT_MODE: Final[str] = "dolt_mode"
_CONTEXT_BD_VERSION: Final[str] = "bd_version"
_CONTEXT_REPO_ROOT: Final[str] = "repo_root"
_CONTEXT_BEADS_DIR: Final[str] = "beads_dir"

BEADS_DIR_NAME: Final[str] = ".beads"

_TITLE_CANARY: Final[str] = "wf canary {nonce}"
_MSG_BACKEND: Final[str] = (
    "bd context reports {field}={found!r}, pinned {expected!r} — refusing "
    "dispatch on a fallback or skewed store (§11)"
)
_MSG_ROUNDTRIP: Final[str] = "canary metadata did not round-trip: {reason}"
_MSG_NO_CONTEXT: Final[str] = (
    "bd context failed ({reason}); it resolves against the PROCESS cwd as well "
    "as -C, so the tick must run from inside a git repository even though "
    "every other bd read works — refusing dispatch (§11)"
)


def startup_canary(client: BdClient) -> CanaryResult:
    """Assert the pinned backend AND workspace, then round-trip a wisp (§11).

    Backend identity alone answers "is this a real dolt store", not "is it the
    RIGHT one": bd resolves a workspace per invocation, so a canary that
    passes against some other project's beads proves nothing about the store
    the instance is about to be written to. `repo_root` and `beads_dir` are
    asserted against the injected workspace as well.

    `is_redirected` is deliberately NOT asserted: it reports that `-C` pointed
    somewhere other than the process cwd, which is the normal case for every
    invocation this wrapper makes (probed 2026-08-25 — true from the repo,
    false from inside the workspace).
    """
    try:
        context = client.context()
    except BdCommandError as exc:
        raise CanaryFailedError(_MSG_NO_CONTEXT.format(reason=exc)) from exc
    config = client.config
    workspace = config.workspace.resolve()
    for field, expected in (
        (_CONTEXT_BACKEND, config.expected_backend),
        (_CONTEXT_DOLT_MODE, config.expected_dolt_mode),
        (_CONTEXT_BD_VERSION, config.expected_bd_version),
        (_CONTEXT_REPO_ROOT, str(workspace)),
        (_CONTEXT_BEADS_DIR, str(workspace / BEADS_DIR_NAME)),
    ):
        found = context.get(field)
        if found != expected:
            raise CanaryFailedError(
                _MSG_BACKEND.format(field=field, found=found, expected=expected)
            )
    nonce = secrets.token_hex(CANARY_NONCE_BYTES)
    metadata = CanaryMetadata(nonce=nonce, probe=CANARY_PROBE)
    try:
        record = client._create_bead(
            title=_TITLE_CANARY.format(nonce=nonce),
            metadata=metadata_dict(metadata),
            ephemeral=True,
            wisp_type=CANARY_WISP_TYPE,
        )
    except LossyWriteError as exc:
        raise CanaryFailedError(_MSG_ROUNDTRIP.format(reason=exc)) from exc
    return CanaryResult(
        backend=str(context[_CONTEXT_BACKEND]),
        dolt_mode=str(context[_CONTEXT_DOLT_MODE]),
        bd_version=str(context[_CONTEXT_BD_VERSION]),
        wisp_id=record.id,
        nonce=nonce,
    )
