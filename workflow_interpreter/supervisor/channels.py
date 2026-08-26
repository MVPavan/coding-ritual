"""The three §6 runner channels, read and validated (`exit.py` decides).

`$WF_OUTCOME_FILE`, `$WF_ARTIFACT_DIR` and `$WF_EFFECTS_FILE` are the only ways
a runner reports anything, and all three are wrapper-provided files inside the
wrapper directory — writable regardless of the node's `writes`, so a
`writes = false` reviewer can still report (§6).

Reading them is separated from GRADING them on purpose: everything here returns
`(value, reason)` and refuses to interpret. "Two markers" is a fact about a
file; "two markers means `fail_code`, never fallback routing" is a §7 rule, and
it lives with the other §7 rules.

Also here: the two conventions a PRODUCER and a READER in different modules
have to render identically — the §7.3 pinned-digest key, and the §7.4 committer
identity a runner's commits carry. A convention rendered in two places is a
convention that drifts.
"""

from __future__ import annotations

import hashlib
import shlex
from pathlib import Path, PurePosixPath
from typing import Final

from pydantic import ValidationError

from workflow_interpreter.bdio import (
    ConfigSource,
    Outcome,
    ResolvedSetting,
    RootRecord,
)
from workflow_interpreter.schema.models import GraphDocument
from workflow_interpreter.supervisor.models import EffectsManifest, OutcomeMarker
from workflow_interpreter.supervisor.paths import read_json_documents

VERIFIER_DIGEST_KEY: Final[str] = "verify.{node}.{program}.sha256"
"""The §7.3 pinned-digest convention in the root's resolved config. §14 defers
a closed resolved-config vocabulary; until then this is the wrapper's, applied
consistently by `verifier_digest_key` — the ONE place producer and reader
render it, so they cannot drift."""

DIGEST_SUFFIX: Final[str] = ".sha256"

ENV_GIT_COMMITTER_NAME: Final[str] = "GIT_COMMITTER_NAME"
ENV_GIT_COMMITTER_EMAIL: Final[str] = "GIT_COMMITTER_EMAIL"
COMMITTER_NAME: Final[str] = "wf-runner"
COMMITTER_EMAIL: Final[str] = "runner+{activation_id}@workflow-interpreter.invalid"
"""The §7.4 identity every commit a runner makes is stamped with, carrying the
ACTIVATION id so one attempt's commits cannot be mistaken for another's.

Set on the child's environment by `RunnerChannels.env()` (§6) and required by
`Workspace.pin_artifact` in addition to path containment. It is an ATTRIBUTION
mechanism, not an authorization one: a runner can unset the variables, and §0.3
already treats the in-process runner as semi-trusted. What it removes is the
ACCIDENT — a dead runner's manifest naming a path the human later commits made
the human's commit "attributable" on path containment alone, and that pin is
what authorizes the next reset to move HEAD off it (probed, Opus#21)."""

REASON_MARKER_ABSENT: Final[str] = "no marker in $WF_OUTCOME_FILE"
REASON_MARKER_COUNT: Final[str] = "expected exactly one marker, found {count}"
REASON_MARKER_INVALID: Final[str] = "marker did not validate: {reason}"
REASON_MARKER_UNDECLARED: Final[str] = (
    "marker claims {outcome}, which node {node} does not declare"
)
REASON_EFFECTS: Final[str] = "$WF_EFFECTS_FILE {detail}"


def runner_committer_email(activation_id: str) -> str:
    """The §7.4 committer address one activation's runner commits under."""
    return COMMITTER_EMAIL.format(activation_id=activation_id)


def verifier_digest_key(node_name: str, cwd: str | None, program: str) -> str:
    """The §7.3 pin key for one check's program — keyed by WHERE it resolves.

    The program alone was not a key. Two legitimate checks on one node can
    declare the same `argv[0]` under different `cwd`s (`scripts/check.sh` in
    two subprojects), and they are different files with different digests: the
    producer wrote one and overwrote the other, so one of the two checks failed
    provenance forever and was never run.

    The key is `cwd / argv[0]` AS DECLARED in the pinned graph — the two strings
    joined, not the path they resolve to. That is deliberate and it is what both
    callers can compute: the producer (`pin_verifier_digests`) hashes at
    instantiation, against the repo, before any checkout exists, and the reader
    (`verify.run_checks`) looks the pin up before it resolves anything. Naming
    it the "resolved path" was simply wrong — `..`, a symlink or an absolute
    `cwd` all key differently from where they land, and `ResolvedCheck.escapes`
    is what refuses those rather than this.

    Both callers render it HERE, because a convention rendered in two places is
    a convention that drifts.
    """
    return VERIFIER_DIGEST_KEY.format(
        node=node_name, program=(PurePosixPath(cwd or "") / program).as_posix()
    )


def pinned_verifier_digests(root: RootRecord) -> dict[str, str]:
    """The §7.3 verify-script digests pinned into the root at instantiation."""
    return {
        setting.key: str(setting.value)
        for setting in root.metadata.resolved_config
        if setting.key.endswith(DIGEST_SUFFIX)
    }


def pin_verifier_digests(
    document: GraphDocument, repo_root: Path
) -> tuple[ResolvedSetting, ...]:
    """Hash every declared `verify` program, as resolved config for `create_root`.

    The PRODUCER for `pinned_verifier_digests`, which had none: the reader and
    the key convention lived here while the settings themselves were only ever
    built by hand, so nothing guaranteed the two agreed. §7.3's whole claim is
    that the digest was recorded at INSTANTIATION, before any runner could edit
    the script, so this is a function of the pinned graph and the repo at that
    moment and of nothing else.

    A program that is not there hashes to `""`, which no real file matches —
    the check is refused rather than run, which is §7.3's own answer for a
    verifier whose provenance cannot be established.
    """
    digests: dict[str, str] = {}
    for node in document.node:
        for check in node.verify or ():
            argv = shlex.split(check.cmd)
            if not argv:
                continue
            program = repo_root / (check.cwd or "") / argv[0]
            digests[verifier_digest_key(node.name, check.cwd, argv[0])] = (
                sha256_file(program) or ""
            )
    return tuple(
        ResolvedSetting(key=key, value=value, source=ConfigSource.PROJECT_CONFIG)
        for key, value in sorted(digests.items())
    )


def sha256_file(path: Path) -> str | None:
    """The sha256 of a file, or `None` when it is not there to hash."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError, PermissionError):
        return None


def read_marker(
    path: Path, declared: frozenset[Outcome], node_name: str
) -> tuple[OutcomeMarker | None, str | None]:
    """THE reserved outcome channel (§6): exactly one marker, or a reason why not."""
    try:
        documents = read_json_documents(path)
    except FileNotFoundError:
        return None, REASON_MARKER_ABSENT
    except (OSError, ValueError) as exc:
        return None, REASON_MARKER_INVALID.format(reason=exc)
    if len(documents) != 1:
        return None, REASON_MARKER_COUNT.format(count=len(documents))
    try:
        marker = OutcomeMarker.model_validate(documents[0])
    except ValidationError as exc:
        return None, REASON_MARKER_INVALID.format(reason=exc)
    if marker.outcome not in declared:
        return None, REASON_MARKER_UNDECLARED.format(
            outcome=marker.outcome.value, node=node_name
        )
    return marker, None


def read_effects(path: Path) -> tuple[EffectsManifest | None, str | None]:
    """The declared-paths manifest (§6); missing or unparseable fails closed."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None, REASON_EFFECTS.format(detail="is absent")
    except OSError as exc:
        return None, REASON_EFFECTS.format(detail=f"is unreadable: {exc}")
    try:
        return EffectsManifest.model_validate_json(raw), None
    except ValidationError as exc:
        return None, REASON_EFFECTS.format(detail=f"did not parse: {exc}")


def path_allowed(path: str, allowed_paths: tuple[str, ...]) -> bool:
    """Whether an observed path falls inside the node's static effect bound."""
    candidate = PurePosixPath(path)
    return any(candidate.full_match(pattern) for pattern in allowed_paths)
