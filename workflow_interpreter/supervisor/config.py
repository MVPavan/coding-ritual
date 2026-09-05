"""Injected configuration for the supervisor wrapper (§5.3, §8, §12).

Frozen, constructed by the caller, handed in at construction time. Like
`bdio.config` this is deliberately NOT `pydantic-settings`: no supervisor
decision may depend on an ambient environment read (`rules/python/safety.md`),
because a wrapper whose grace periods or `/proc` root come from the process
environment is a wrapper the runner it supervises could reconfigure.

**Linux only.** `/proc`, `boot_id`, process groups and `flock` are all
Linux-specific and are used unguarded; there is no Windows shim and none is
planned (§5.3 records `host_boot_id` and `proc_start_time` precisely because
they are cheap and exact on Linux).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

from workflow_interpreter.supervisor.errors import SupervisorConfigError
from workflow_interpreter.supervisor.sandbox import SandboxMode

CONFIG_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="forbid", arbitrary_types_allowed=False
)

DEFAULT_GIT_BINARY: Final[str] = "git"
DEFAULT_PROC_ROOT: Final[Path] = Path("/proc")
DEFAULT_BOOT_ID_PATH: Final[Path] = Path("/proc/sys/kernel/random/boot_id")
DEFAULT_GIT_TIMEOUT_S: Final[float] = 120.0
DEFAULT_TERM_GRACE_S: Final[float] = 10.0
DEFAULT_KILL_GRACE_S: Final[float] = 5.0
DEFAULT_BARRIER_TIMEOUT_S: Final[float] = 30.0
DEFAULT_POLL_INTERVAL_S: Final[float] = 1.0
DEFAULT_LOG_TAIL_BYTES: Final[int] = 2048
DEFAULT_MAX_OUTPUT_FILES: Final[int] = 2000
DEFAULT_MAX_OUTPUT_BYTES: Final[int] = 32 * 1024 * 1024
DEFAULT_MAX_OUTPUT_ENTRIES: Final[int] = 10000
DEFAULT_MAX_OUTPUT_DEPTH: Final[int] = 32
"""§8.2: the foreman reads at most a ~2KB tail on a stale flag."""

WRAPPER_DIR_NAME: Final[str] = ".wf"

_MSG_RELATIVE: Final[str] = "{field} must be an absolute path, got {value}"
_MSG_INSIDE_REPO: Final[str] = (
    "wrapper_root {wrapper_root} is inside repo_root {repo_root}; the wrapper "
    "dir must survive a `git clean` of the workspace it observes (§P1)"
)


class SupervisorConfig(BaseModel):
    """Everything the wrapper needs; nothing is discovered from the process.

    `wrapper_root` is the `.wf/` observation cache BESIDE the repo (§P1): losing
    it costs telemetry, never correctness, but a `git clean -fdx` inside the
    workspace must not be able to take the exec ledger with it — hence the
    containment check.
    """

    model_config = CONFIG_MODEL

    repo_root: Path
    wrapper_root: Path
    host: str = Field(min_length=1)
    sandbox: SandboxMode = SandboxMode.BWRAP
    """O5: the §2 mount bound is ON for every node of both shipped graphs.

    `off` is an operator escape hatch that is RECORDED, never silent — the
    launch receipt carries the mode and the close carries an audit flag."""
    git_binary: str = DEFAULT_GIT_BINARY
    git_timeout_s: float = Field(default=DEFAULT_GIT_TIMEOUT_S, gt=0)
    proc_root: Path = DEFAULT_PROC_ROOT
    boot_id_path: Path = DEFAULT_BOOT_ID_PATH
    term_grace_s: float = Field(default=DEFAULT_TERM_GRACE_S, gt=0)
    kill_grace_s: float = Field(default=DEFAULT_KILL_GRACE_S, gt=0)
    barrier_timeout_s: float = Field(default=DEFAULT_BARRIER_TIMEOUT_S, gt=0)
    poll_interval_s: float = Field(default=DEFAULT_POLL_INTERVAL_S, gt=0)
    log_tail_bytes: int = Field(default=DEFAULT_LOG_TAIL_BYTES, gt=0)
    max_output_files: int = Field(default=DEFAULT_MAX_OUTPUT_FILES, gt=0)
    max_output_bytes: int = Field(default=DEFAULT_MAX_OUTPUT_BYTES, gt=0)
    max_output_entries: int = Field(default=DEFAULT_MAX_OUTPUT_ENTRIES, gt=0)
    max_output_depth: int = Field(default=DEFAULT_MAX_OUTPUT_DEPTH, gt=0)

    def model_post_init(self, context: object, /) -> None:
        """Refuse a configuration the §P1 store separation cannot hold under."""
        for field, value in (
            ("repo_root", self.repo_root),
            ("wrapper_root", self.wrapper_root),
        ):
            if not value.is_absolute():
                raise SupervisorConfigError(
                    _MSG_RELATIVE.format(field=field, value=value)
                )
        if self.wrapper_root.is_relative_to(self.repo_root):
            raise SupervisorConfigError(
                _MSG_INSIDE_REPO.format(
                    wrapper_root=self.wrapper_root, repo_root=self.repo_root
                )
            )
