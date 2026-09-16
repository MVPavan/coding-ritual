"""Opt-in codex-cli 0.154.0 runner; one wrapper-owned stdio turn per activation."""

import json
import subprocess
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from workflow_interpreter.bdio import ProcessHandle, Usage
from workflow_interpreter.bdio.rpc_records import SessionRegistration
from workflow_interpreter.contracts.rpc_usage import UsageSnapshot
from workflow_interpreter.contracts.transport import RunnerTransport
from workflow_interpreter.profiles.codex import (
    CodexProfile,
    _required_effort,
    _required_model,
)
from workflow_interpreter.profiles.codex_rpc import CODEX_VERSION
from workflow_interpreter.profiles.config import RunnerName
from workflow_interpreter.profiles.errors import TaskRefused
from workflow_interpreter.supervisor.errors import WrapperDirError
from workflow_interpreter.supervisor.paths import read_record
from workflow_interpreter.supervisor.profile import (
    RunnerCommand,
    RunnerEvent,
    TaskSpec,
    TerminalEnvelope,
)
from workflow_interpreter.supervisor.rpc_records import SESSION_FILE
from workflow_interpreter.supervisor.rpc_usage import USAGE_FILE

MSG_VERSION: Final[str] = f"codex-appserver requires codex-cli {CODEX_VERSION}"
MSG_STATE: Final[str] = "codex-appserver requires protected vendor state"
KEY_PROJECTS: Final[str] = "projects"
UNTRUSTED_PROJECT: Final[str] = '{trust_level="untrusted"}'
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
                "-c",
                KEY_PROJECTS
                + "={"
                + ",".join(
                    f"{json.dumps(path)}={UNTRUSTED_PROJECT}"
                    for path in sorted({str(checkout), root})
                )
                + "}",
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
        """Read protected identity and per-turn usage, never sum thread totals."""
        directory = Path(handle.log_path).parent
        try:
            registration = read_record(directory / SESSION_FILE, SessionRegistration)
            snapshot = read_record(directory / USAGE_FILE, UsageSnapshot)
        except (OSError, WrapperDirError):
            return TerminalEnvelope()
        if registration is None or registration.handle != handle:
            return TerminalEnvelope()
        counts = snapshot.per_turn if snapshot else None
        known = (
            counts is not None
            and counts.input is not None
            and counts.output is not None
        )
        usage = Usage(known=False)
        if known and counts is not None and counts.input is not None:
            usage = Usage(
                known=True,
                input_tokens=(
                    counts.input - counts.cached_input
                    if counts.cached_input is not None
                    else counts.input
                ),
                cache_read_input_tokens=counts.cached_input,
                output_tokens=counts.output,
            )
        return TerminalEnvelope(session_id=registration.thread_id, usage=usage)
