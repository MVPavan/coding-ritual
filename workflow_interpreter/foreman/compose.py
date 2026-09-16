"""Composition root for one foreman process and one instance wiring."""

import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import MintRequest, WorkflowStore
from workflow_interpreter.bdio.backend import BackendLocator, bd_backend
from workflow_interpreter.bdio.constants import BackendKind
from workflow_interpreter.bdio.coordination import CoordinationStore
from workflow_interpreter.bdio.reads import WorkflowReads
from workflow_interpreter.foreman.config import ForemanConfig
from workflow_interpreter.foreman.constants import WRAPPER_HANDLE
from workflow_interpreter.schema.decisions import DecisionRequest, DecisionResponse
from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF, procfs
from workflow_interpreter.supervisor.band import BandLock
from workflow_interpreter.supervisor.clock import Clock
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.exit import ExitObserver
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.paths import WrapperPaths, write_durable
from workflow_interpreter.supervisor.profile import Profile
from workflow_interpreter.supervisor.recover import Recovery
from workflow_interpreter.supervisor.run import Supervisor
from workflow_interpreter.supervisor.workspace import Workspace


class InstanceBranchMissing(ValueError):
    """The instance branch needed to derive a mint base does not exist."""


def instance_head(git: Git, repo_root: Path, root_id: str) -> str:
    """Read the instance branch head or fail before any activation is minted."""
    branch = INSTANCE_BRANCH_REF.format(root_id=root_id)
    head = git.ref_target(branch, cwd=repo_root)
    if head is None:
        raise InstanceBranchMissing(f"instance branch {branch} is missing")
    return head


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

    def __init__(self, supervisor_config: SupervisorConfig, config_path: Path) -> None:
        self._supervisor_config = supervisor_config
        self._config_path = config_path

    def launch(
        self, launch: WrapperLaunch, *, wiring: "InstanceWiring | None" = None
    ) -> None:
        """Detach the wrapper and leave an informational process identity record."""
        paths = WrapperPaths(self._supervisor_config, launch.root_id)
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
                    "supervise",
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
            start_time=procfs.read_start_time(self._supervisor_config, process.pid),
            boot_id=procfs.read_boot_id(self._supervisor_config),
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
    supervisor: Supervisor
    recovery: Recovery
    observer: ExitObserver
    branch_head_reader: Callable[[], str]


@dataclass(frozen=True)
class Composition:
    """The injected process-wide dependencies and factory for per-root state."""

    config: ForemanConfig
    store: WorkflowStore
    supervisor_config: SupervisorConfig
    git: Git
    clock: Clock
    profiles: ProfileResolver
    spawner: Spawner
    host_env: Mapping[str, str]
    locate_backend: BackendLocator = bd_backend
    """Which backend owns a root, answered before the root is loaded (§3.2)."""

    def __post_init__(self) -> None:
        """Keep the explicit supervisor dependency aligned with the config guard."""
        if self.supervisor_config != self.config.supervisor:
            raise ValueError("supervisor_config must match foreman config")

    def store_for_root(self, root_id: str) -> WorkflowStore:
        """The store this root is read and written through (§3.2).

        The backend is pinned per root, so it is chosen BEFORE the root is
        loaded; the process-wide store is only the factory it comes from. Any
        read or write about ONE root goes through here, not through
        `composition.store`, which serves discovery and the task bead alone.
        """
        return self._store_on(root_id, self.locate_backend(root_id))

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
        """Build one wiring with exactly one ``BandLock`` shared throughout."""
        paths = WrapperPaths(self.supervisor_config, root_id)
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
                    != self.supervisor_config.wrapper_root.resolve()
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
            supervisor=Supervisor(
                self.supervisor_config,
                paths,
                self.git,
                store,
                workspace,
                self.clock,
                host_env=self.host_env,
            ),
            recovery=Recovery(
                self.supervisor_config, paths, store, workspace, self.clock
            ),
            observer=ExitObserver(
                self.supervisor_config,
                paths,
                self.git,
                store,
                workspace,
                self.clock,
            ),
            branch_head_reader=branch_head_reader,
        )
