"""Opt-in codex-cli 0.154.0 runner; one wrapper-owned stdio turn per activation."""

import subprocess
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from workflow_interpreter.bdio import ProcessHandle
from workflow_interpreter.contracts.transport import RunnerTransport
from workflow_interpreter.profiles.codex import (
    CodexProfile,
    _required_effort,
    _required_model,
)
from workflow_interpreter.profiles.codex_rpc import CODEX_VERSION
from workflow_interpreter.profiles.config import RunnerName
from workflow_interpreter.profiles.errors import TaskRefused
from workflow_interpreter.supervisor.profile import (
    RunnerCommand,
    RunnerEvent,
    TaskSpec,
    TerminalEnvelope,
)

MSG_VERSION: Final[str] = "codex-appserver requires codex-cli 0.154.0"
MSG_STATE: Final[str] = "codex-appserver requires protected vendor state"
MSG_AMBIENT: Final[str] = "codex-appserver refuses ambient project config/rules"
ENV_CODEX_HOME: Final[str] = "CODEX_HOME"
APP_SERVER: Final[str] = "app-server"


class CodexAppServerProfile(CodexProfile):
    """The experimental runner shares Codex grants, never its exec transport."""

    runner = RunnerName.CODEX_APPSERVER

    def build_command(self, task: TaskSpec, session_id: str) -> RunnerCommand:
        """Version-check without model work, then describe the barrier-owned server."""
        if task.vendor_state is None:
            raise TaskRefused(MSG_STATE)
        checkout = Path(task.checkout_read_root or task.cwd)
        if (checkout / ".codex" / "config.toml").exists() or (
            checkout / ".codex" / "rules"
        ).exists():
            raise TaskRefused(MSG_AMBIENT)
        try:
            version = subprocess.run(
                [self.binary(), "--version"],
                env=dict(self._host_env),
                capture_output=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise TaskRefused(MSG_VERSION) from error
        if (
            version.returncode
            or version.stdout.strip() != f"codex-cli {CODEX_VERSION}".encode()
        ):
            raise TaskRefused(MSG_VERSION)
        _required_model(task)
        _required_effort(task)
        root = self._workspace_root(task)
        command = self.command(
            [
                self.binary(),
                APP_SERVER,
                "--listen",
                "stdio://",
                *self._sandbox_flags(task, root),
            ],
            task,
            session_id,
            cwd=root,
        )
        return command.model_copy(
            update={
                "transport": RunnerTransport.STDIO_RPC,
                "env": {**command.env, ENV_CODEX_HOME: task.vendor_state},
            }
        )

    def build_resume_command(
        self, session_id: str, instructions: str, task: TaskSpec
    ) -> RunnerCommand:
        """The wrapper performs thread/resume and resubmits the fresh full envelope."""
        return self.build_command(
            task.model_copy(update={"brief": instructions}), session_id
        )

    def build_resume_hint(self, session_id: str) -> str:
        """App-server threads resume only through a newly bounded wrapper activation."""
        return f"codex-appserver thread/resume {session_id}"

    def parse_output(self, stream: Iterable[str]) -> Iterator[RunnerEvent]:
        """Read only wrapper-normalized telemetry, never register identity from it."""
        for line in stream:
            try:
                yield RunnerEvent.model_validate_json(line)
            except ValidationError:
                continue

    def collect_terminal_envelope(self, handle: ProcessHandle) -> TerminalEnvelope:
        """Until usage is recorded, report unknown rather than infer it from text."""
        return TerminalEnvelope(session_id=handle.session_id or None)
