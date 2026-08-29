"""Dirty-tree attribution and its durable carrier encoding (§12)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Final

import structlog
from pydantic import ValidationError

from workflow_interpreter.bdio import ActivationRecord
from workflow_interpreter.schema.loader import canonical_json_bytes
from workflow_interpreter.schema.models import IsolationMode, Node
from workflow_interpreter.supervisor.clock import Clock, to_iso
from workflow_interpreter.supervisor.errors import WrapperDirError
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.models import (
    DirtyEntry,
    DirtySnapshot,
    EntryKind,
    HumanConfirmation,
    RunnerAttribution,
)
from workflow_interpreter.supervisor.paths import (
    WrapperPaths,
    read_record,
    write_record,
)

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)


def encode_dirty_state(snapshot: DirtySnapshot) -> str:
    """Encode the §3.2 pre-attempt dirty-state carrier as canonical JSON."""
    return canonical_json_bytes(snapshot.model_dump(mode="json")).decode("utf-8")


def decode_dirty_state(value: str | None) -> DirtySnapshot | None:
    """Parse a recorded `pre_attempt_dirty_state`; `None` when absent or corrupt.

    `wire.py` validates that the carrier is canonical JSON of an OBJECT, and
    nothing validates that the object is a `DirtySnapshot` — so a row whose §3.2
    trio was written out of band (a hand edit, an older tool, a direct `bd
    update`; bead cr-too) decodes to a `ValidationError`. That is a `ValueError`,
    which is neither an `OSError` nor a `SupervisorError`, so it escaped
    `ExitObserver._post_exit`'s catch and took `observe()` down BEFORE
    `record_exit` ran — a provably-exited child left recorded as `dispatched`,
    re-classified as an infra failure on every subsequent tick (probed, r4).

    Corrupt provenance is therefore treated as NO provenance, which is the
    answer this package already gives a missing record and the direction §12
    resolves toward: with no snapshot, `_plan` has no attribution to match
    against, `record_attribution` records nothing, and every dirty path lands
    on the protected side. The warning is loud so the anomaly is seen.
    """
    if not value:
        return None
    try:
        return DirtySnapshot.model_validate_json(value)
    except ValidationError as exc:
        _LOG.warning("wf.dirty_state.undecodable", error=str(exc), value=value)
        return None


class AttributionManager:
    """Records only dirty paths the wrapper can positively attribute."""

    def __init__(
        self,
        paths: WrapperPaths,
        git: Git,
        clock: Clock,
        path_for: Callable[[Node], Path],
        entry_for: Callable[[Path, str, bool], DirtyEntry],
    ) -> None:
        """Bind attribution to one instance and its reset-planning callbacks."""
        self._paths = paths
        self._git = git
        self._clock = clock
        self._path_for = path_for
        self._entry_for = entry_for

    @staticmethod
    def is_runner_output(
        entry: DirtyEntry,
        attribution: RunnerAttribution | None,
        prior: DirtySnapshot | None,
        confirmation: HumanConfirmation | None,
        activation_id: str,
    ) -> bool:
        """Can the wrapper PROVE the runner left this exact content here? (§12)

        Two ways to answer yes, and every other answer is no:

        0. …unless the entry is not a regular FILE, which is refused before
           either. A directory (and a FIFO, and a symlink to one) has no blob,
           so its digest is `""` — and `""` is what every other such entry
           hashes to as well, which turns both the attribution test AND a
           tier-2 confirmation's content binding into `"" == ""`. A
           confirmation given when a nested checkout held one thing would
           release whatever it holds later, and `clean -f -d` on it takes the
           whole subtree (§12).
        1. a human released this path at this content, in THIS activation
           (tier-2, digest-bound and activation-bound);
        2. the path is TRACKED, the wrapper attributed it at a runner's exit,
           and nothing has changed it since — the recorded digest still equals
           what is on disk;
        3. …there is no third way. Absence of evidence is not attribution.

        Condition 2 is restricted to tracked paths because attribution partly
        rests on the runner's own `$WF_EFFECTS_FILE`, and the runner writes
        that file. A declaration naming a human's mid-run file — from malice or
        from a manifest built out of `git status` — would otherwise put
        never-committed content on the destroyable side, where the mistake has
        no undo at all: no blob, no commit, no reflog (probed). For a tracked
        path the content is in the object store either way.

        It carries a second guard even though `ExitObserver` already applies
        it: a path that was dirty when the attempt STARTED pre-existed that
        runner, so the runner cannot have produced it whatever else the record
        says.
        """
        if entry.kind is not EntryKind.FILE:
            return False
        if confirmation is not None and confirmation.releases(
            activation_id, entry.path, entry.digest
        ):
            return True
        if not entry.tracked:
            return False
        if prior is not None and entry.path in prior.paths:
            return False
        if attribution is None:
            return False
        return attribution.digest_of(entry.path) == entry.digest

    def read(self) -> RunnerAttribution | None:
        """Read the attribution record, failing closed when it is malformed."""
        try:
            return read_record(self._paths.attribution_record, RunnerAttribution)
        except WrapperDirError as exc:
            _LOG.warning("wf.attribution.unreadable", error=str(exc))
            return None

    def record_attribution(
        self,
        activation: ActivationRecord,
        node: Node,
        *,
        declared: frozenset[str],
    ) -> RunnerAttribution | None:
        """Record what this runner provably left dirty, for a later reset (§12).

        Called once, from `ExitObserver`, while the dead runner's activation
        still owns the §12 band — so `git status` here is the wrapper's own
        observation of what that runner left, not a guess made later.

        Entries survive three filters: the wrapper saw the path dirty, the
        runner DECLARED it, and it was not already dirty when this attempt
        started. Prior entries are carried forward untouched — a file the
        implementer left is still its work after a reviewer has run — because
        the reset-time digest comparison is what expires them: anything that
        edits a path breaks its match and returns it to protected.

        Untracked paths are recorded like any other — this file is an
        OBSERVATION, and a wrapper that edited its own observations to match
        its policy would be worth nothing. `_is_runner_output` is where the
        policy lives, and it never resets an untracked path on this evidence.

        Worktree mode records nothing: that tree has no other author.
        """
        if node.isolation is not IsolationMode.IN_REPO:
            return None
        cwd = self._path_for(node)
        pre_attempt = decode_dirty_state(activation.metadata.pre_attempt_dirty_state)
        if pre_attempt is None:
            # Unknown pre-attempt state cannot answer "was it already dirty",
            # so nothing is attributable — and the on-disk record is REPLACED
            # with an empty one, or an earlier attempt's entries would stay
            # live and authorize a reset this attempt cannot vouch for.
            _LOG.warning(
                "wf.attribution.no_pre_attempt_state",
                activation_id=activation.activation_id,
            )
            entries: tuple[DirtyEntry, ...] = ()
            carried: tuple[DirtyEntry, ...] = ()
        else:
            entries = tuple(
                self._entry_for(cwd, path, tracked)
                for path, tracked in self._git.status_paths(cwd=cwd)
                if path in declared and path not in pre_attempt.paths
            )
            carried = self._carry_forward(entries)
        record = RunnerAttribution(
            activation_id=activation.activation_id,
            observed_at=to_iso(self._clock.now()),
            head_commit=self._git.head_commit(cwd=cwd),
            entries=carried,
        )
        write_record(self._paths.attribution_record, record)
        _LOG.info(
            "wf.attribution.recorded",
            activation_id=activation.activation_id,
            paths=[entry.path for entry in entries],
        )
        return record

    def _carry_forward(self, entries: tuple[DirtyEntry, ...]) -> tuple[DirtyEntry, ...]:
        """Keep earlier attribution entries that this observation does not replace."""
        existing = self.read()
        if existing is None:
            return entries
        fresh = {entry.path for entry in entries}
        return entries + tuple(
            entry for entry in existing.entries if entry.path not in fresh
        )
