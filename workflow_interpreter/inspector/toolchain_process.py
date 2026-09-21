"""Bounded host uv commands over admitted dependency metadata."""

import os
import shutil
import signal
import subprocess
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from workflow_interpreter.inspector import toolchain_constants as tc
from workflow_interpreter.inspector.toolchain_files import measure
from workflow_interpreter.inspector.toolchain_models import (
    ToolchainConfig,
    ToolchainUnavailable,
)

OUTPUT_LIMIT: Final[int] = 16 * 1024
POLL_INTERVAL: Final[float] = 0.05
MSG_OUTPUT: Final[str] = "toolchain command output exceeds byte bound"
MSG_TIMEOUT: Final[str] = "toolchain command timed out"


def run_uv(
    config: ToolchainConfig,
    args: tuple[str, ...],
    cwd: Path,
    env: Mapping[str, str],
) -> str:
    """Bound runtime, output, temporary bytes, and disk reserve; kill on refusal."""
    with (
        tempfile.TemporaryFile() as output,
        subprocess.Popen(
            [config.uv_binary, *args],
            cwd=cwd,
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process,
    ):
        deadline = time.monotonic() + config.timeout_s
        try:
            while True:
                try:
                    process.wait(timeout=POLL_INTERVAL)
                except subprocess.TimeoutExpired:
                    pass
                if os.fstat(output.fileno()).st_size > OUTPUT_LIMIT:
                    raise ToolchainUnavailable(MSG_OUTPUT)
                if shutil.disk_usage(cwd).free < config.reserve_bytes:
                    raise ToolchainUnavailable(tc.MSG_DISK)
                cache = env.get(tc.ENV_CACHE)
                if cache is not None:
                    try:
                        measure(Path(cache), config, allow_internal_absolute=True)
                    except FileNotFoundError:
                        if process.returncode is not None:
                            raise
                if process.returncode is not None:
                    break
                if time.monotonic() >= deadline:
                    raise ToolchainUnavailable(MSG_TIMEOUT)
        except BaseException:
            # Own process group, still unreaped when signalled; no pid reuse.
            if process.returncode is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=config.timeout_s)
            raise
        output.seek(0)
        text = output.read(OUTPUT_LIMIT).decode(errors="replace").strip()
        if process.returncode:
            raise ToolchainUnavailable(
                tc.MSG_COMMAND.format(
                    operation=args[0],
                    exit_code=process.returncode,
                    text=text,
                )
            )
        return text
