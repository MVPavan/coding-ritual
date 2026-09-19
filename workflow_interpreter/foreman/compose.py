"""Composition root for one foreman process and one instance wiring."""

import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import MintRequest, WorkflowStore
from workflow_interpreter.bdio.backend import (
    BackendLocator,
    PinnableBackendLocator,
    RecordPinnableBackendLocator,
    bd_backend,
)
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.coordination import CoordinationStore
from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.foreman.config import ForemanConfig
from workflow_interpreter.foreman.constants import WRAPPER_HANDLE
from workflow_interpreter.inspector import INSTANCE_BRANCH_REF, procfs
from workflow_interpreter.inspector.band import BandLock
from workflow_interpreter.inspector.clock import Clock
from workflow_interpreter.inspector.config import InspectorConfig
from workflow_interpreter.inspector.exit import ExitObserver
from workflow_interpreter.inspector.gitio import Git
from workflow_interpreter.inspector.paths import WrapperPaths, write_durable
from workflow_interpreter.inspector.profile import Profile
from workflow_interpreter.inspector.recover import Recovery
from workflow_interpreter.inspector.run import Inspector
from workflow_interpreter.inspector.workspace import Workspace
from workflow_interpreter.ledger.database import LedgerDatabase
from workflow_interpreter.ledger.paths import ensure_fence_dir
from workflow_interpreter.schema.decisions import DecisionRequest, DecisionResponse


class InstanceBranchMissing(ValueError):
    """The instance branch needed to derive a mint base does not exist."""


def instance_head(git: Git, repo_root: Path, root_id: str) -> str:
    """Read the instance branch head or fail before any activation is minted."""
    branch = INSTANCE_BRANCH_REF.format(root_id=root_id)
    head = git.ref_target(branch, cwd=repo_root)
    if head is None:
        raise InstanceBranchMissing(f"instance branch {branch} is missing")
    return head


MSG_NO_BRANCH_YET: Final[str] = (
    "a root being created has no instance branch yet; its base is pinned, never read"
)


def _no_branch_yet() -> str:
    """The branch-head reader of a store that exists only to CREATE a root."""
    raise InstanceBranchMissing(MSG_NO_BRANCH_YET)


class WrapperLaunch(BaseModel):
    """The durable dispatch intent a detached wrapper needs to recover."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    root_id: str
    activation_id: str
    request: MintRequest


class WrapperHandle(BaseModel):
    """Best-effort identity for a wrapper that may exit immediately."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    pid: int
    start_time: str | None
    boot_id: str | None


class Spawner(Protocol):
    """Boundary that starts a wrapper after durable dispatch intent exists."""

    def launch(
        self, launch: WrapperLaunch, *, wiring: "InstanceWiring | None" = None
    ) -> None: ...


class ProfileResolver(Protocol):
    """Boundary used by later slices to resolve a profile name."""

    def profile_for(self, name: str) -> Profile: ...


class DetachedSpawner:
    """Start one wrapper without a shell or a borrowed terminal."""

    def __init__(
        self,
        inspector_config: InspectorConfig,
        config_path: Path,
        task_id: str,
        epic_id: str,
    ) -> None:
        self._inspector_config = inspector_config
        self._config_path = config_path
        self._task_id = task_id
        self._epic_id = epic_id

    def launch(
        self, launch: WrapperLaunch, *, wiring: "InstanceWiring | None" = None
    ) -> None:
        """Detach the wrapper and leave an informational process identity record."""
        paths = WrapperPaths(self._inspector_config, launch.root_id)
        directory = paths.ensure_activation_dir(launch.activation_id)
        with (
            paths.wrapper_log(launch.activation_id).open("ab") as wrapper_stdout,
            paths.wrapper_log(launch.activation_id).open("ab") as wrapper_stderr,
        ):
            process = subprocess.Popen(
                (
                    sys.executable,
                    "-m",
                    "workflow_interpreter.foreman",
                    # `--config` is a top-level option of the entrypoint parser,
                    # so it precedes the subcommand here too (`__main__._parser`).
                    "--config",
                    str(self._config_path),
                    # D16: the wrapper re-enters as its own process and has to
                    # be told the task too, or it could not locate a backend.
                    "--task",
                    self._task_id,
                    # And the epic, for the same reason: it is an input (§3.7),
                    # so a process that was not told it has none to pin.
                    "--epic",
                    self._epic_id,
                    "inspector",
                    launch.root_id,
                    launch.activation_id,
                ),
                stdin=subprocess.DEVNULL,
                stdout=wrapper_stdout,
                stderr=wrapper_stderr,
                start_new_session=True,
            )
        handle = WrapperHandle(
            pid=process.pid,
            start_time=procfs.read_start_time(self._inspector_config, process.pid),
            boot_id=procfs.read_boot_id(self._inspector_config),
        )
        write_durable(
            directory / WRAPPER_HANDLE,
            handle.model_dump_json(exclude_none=False).encode("utf-8") + b"\n",
        )


@dataclass(frozen=True)
class InstanceWiring:
    """All instance-scoped collaborators share the same execution band."""

    paths: WrapperPaths
    repo_root: Path
    band: BandLock
    store: WorkflowStore
    workspace: Workspace
    inspector: Inspector
    recovery: Recovery
    observer: ExitObserver
    branch_head_reader: Callable[[], str]


AttentionDrain = Callable[[str], None]
"""Writes one root's task the attention label its ledger state implies (§3.2.4).

Injected rather than constructed by the driver, because it is a bd WRITE and a
composition root decides where those come from. The ledger's implementation is
`ledger.reconcile.RootAttentionDrain`."""


def no_attention_drain(root_id: str) -> None:
    """The default: a bd-backed root keeps no projections, so none are owed."""


@dataclass(frozen=True)
class Composition:
    """The injected process-wide dependencies and factory for per-root state."""

    config: ForemanConfig
    store: WorkflowStore
    inspector_config: InspectorConfig
    git: Git
    clock: Clock
    profiles: ProfileResolver
    spawner: Spawner
    host_env: Mapping[str, str]
    ledger: LedgerDatabase | None = None
    """This process's one ledger connection, holding the shared fence (§3.4.1).

    The composition root owns it because a process has exactly one, and the
    surfaces built from it — the landing journal, the export pin, the
    reconciler — are composed, never self-constructed."""
    task_id: str | None = None
    """The task bead every root of this process belongs to (D16).

    Optional only because a test wiring may have no bead to name; every
    production entry point supplies it, and the surfaces that need it —
    export before close, the ledger's rows — refuse without one."""
    epic_id: str | None = None
    """The epic this process's task belongs under, as an INPUT (§3.7, R8).

    Never derived from `task_id`: it is the second free path component of the
    `docs/workstreams/<epic>/runs/<task>/a<n>` grant, and a parse of one id
    cannot answer for a tracker that does not shape its ids that way. Carried
    here so that `RunIdentity` is pinned from a fact the composition root
    decided, exactly as the task is."""
    locate_backend: BackendLocator = bd_backend
    """Which backend owns a root, answered before the root is loaded (§3.2)."""
    drain_attention: AttentionDrain = no_attention_drain
    """Drains a settling root's pending attention projections (§3.2.4)."""

    def __post_init__(self) -> None:
        """Keep the explicit inspector dependency aligned with the config guard."""
        if self.inspector_config != self.config.inspector:
            raise ValueError("inspector_config must match foreman config")

    def store_for_root(self, root_id: str) -> WorkflowStore:
        """The store this root is read and written through (§3.2).

        The backend is pinned per root, so it is chosen BEFORE the root is
        loaded; the process-wide store is only the factory it comes from. Any
        read or write about ONE root goes through here, not through
        `composition.store`, which serves discovery and the task bead alone.
        """
        return self._store_on(root_id, self.locate_backend(root_id))

    def creation_store(self, backend: BackendKind) -> WorkflowStore:
        """The store a root that does not exist YET is created through (§3.2).

        A root's backend is pinned before the root exists — on the contractor
        record at prepare, or on the `tasks` row for a run with no contractor — so
        creation is the one operation that cannot ask the locator for an id it
        is about to mint. It is given the pin instead, and creating through
        `composition.store` (which is built on whatever transport this process
        happened to start on) is what D18 forbids: a retry admitted after the
        switch flipped would land on the backend its own record denies.
        """
        return self.store.for_root(branch_head_reader=_no_branch_yet, backend=backend)

    def pin_root_backend(self, root_id: str, backend: BackendKind) -> None:
        """Tell the locator the backend a just-created root was pinned to (§3.2).

        Nothing durable answers for a bd root of a ledger-pinned task — the
        ledger holds no row for it and the `tasks` row names the first
        attempt's backend — so without this the next read of that root would go
        to the wrong store and report a live run as missing. A locator with no
        pin surface answers bd for everything already and has nothing to learn.
        """
        locator = self.locate_backend
        if isinstance(locator, PinnableBackendLocator):
            locator.pin(root_id, backend)

    def pin_record_backend(self, root_id: str, backend: BackendKind) -> None:
        """Tell the locator what a contractor record says about a root (§3.2).

        Every resume and recovery entry installs this BEFORE it loads the
        root: a process that restarted holds no pin, and for a bd attempt of
        a ledger-pinned task the `tasks` row answers for attempt one, so a
        load that asked first would read the wrong store and report a live
        run as missing (D18). The record leads §3.2's order, so a store that
        answers differently refuses here rather than overruling it.
        """
        locator = self.locate_backend
        if isinstance(locator, RecordPinnableBackendLocator):
            locator.pin_record(root_id, backend)

    def _store_on(self, root_id: str, backend: BackendKind) -> WorkflowStore:
        """The root's store over an ALREADY located backend.

        A caller that needs both the located backend and the store must locate
        once and pass that single answer here: two calls to the locator may
        answer differently, and a root loaded from one backend must never be
        wired to another (§3.2).
        """
        return self.store.for_root(
            branch_head_reader=lambda: instance_head(
                self.git, self.config.repo_root, root_id
            ),
            backend=backend,
        )

    def coordination_for_root(
        self,
        owner_id: str,
        *,
        verify_decision: Callable[[DecisionRequest], DecisionResponse] | None = None,
        composition: "Composition | None" = None,
    ) -> CoordinationStore:
        """Coordination for ONE owner root, over that root's backend (§3.2).

        The reservation ledger lives in the owner's own record, which the
        coordination store loads and saves through the backend it is bound
        to. Binding it to `composition.store` would query the process-wide
        backend for a root that may be pinned to another one.
        """
        return self.store_for_root(owner_id).coordination_store(
            verify_decision=verify_decision, composition=composition
        )

    def reads_for_root(self, root_id: str) -> WorkflowReads:
        """The §4 read vocabulary over the store this root is pinned to."""
        return self.store_for_root(root_id).reads

    def for_root(self, root_id: str) -> InstanceWiring:
        """Build one wiring with exactly one ``BandLock`` shared throughout.

        The ledger fence directory is created HERE, before any dispatch this
        wiring can make: every crew sandbox pins `<git common dir>/wf/`
        read-only (`inspector/sandbox.py`), and a pin whose bind source does
        not exist would leave the locked inode replaceable from inside the box
        (run-ledger §3.4).
        """
        ensure_fence_dir(self.config.repo_root)
        paths = WrapperPaths(self.inspector_config, root_id)
        branch_head_reader = lambda: instance_head(
            self.git, self.config.repo_root, root_id
        )
        backend = self.locate_backend(root_id)
        root_store = self._store_on(root_id, backend)
        root = root_store.reads.load_root(root_id)
        coordinator = root_store.coordination_store()
        link = root.metadata.coordination
        band_path = paths.band_lock
        if link is not None:
            child = coordinator.child_for_root(root)
            if child is not None:
                if (
                    Path(child.wrapper_root)
                    != self.inspector_config.wrapper_root.resolve()
                ):
                    from workflow_interpreter.schema.decisions import CoordinationError

                    raise CoordinationError("conflicting child wrapper location")
                band_path = coordinator.member_lock_path(root_id, root=root)
        band = BandLock(band_path)
        store = root_store.for_root(
            branch_head_reader=branch_head_reader, member_band=band, backend=backend
        )
        workspace = Workspace(paths, self.git, self.clock, band, advance_branch=True)
        return InstanceWiring(
            paths=paths,
            repo_root=self.config.repo_root,
            band=band,
            store=store,
            workspace=workspace,
            inspector=Inspector(
                self.inspector_config,
                paths,
                self.git,
                store,
                workspace,
                self.clock,
                host_env=self.host_env,
            ),
            recovery=Recovery(
                self.inspector_config, paths, store, workspace, self.clock
            ),
            observer=ExitObserver(
                self.inspector_config,
                paths,
                self.git,
                store,
                workspace,
                self.clock,
            ),
            branch_head_reader=branch_head_reader,
        )
