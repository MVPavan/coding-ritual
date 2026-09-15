"""Real, network-denied QMD lexical qualification helpers.

These helpers deliberately exercise only QMD's lexical lifecycle.  They do
not provide a DWS runtime adapter and must never become one by accident.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

QMD_BIN_ENVIRONMENT = "DWS_QMD_BIN"
PROCESS_TIMEOUT_SECONDS = 45.0


@dataclass(frozen=True)
class QmdState:
    """One disposable QMD database, config directory, model cache, and cwd."""

    root: Path
    corpus: Path
    cwd: Path
    config: Path
    cache: Path
    home: Path
    index: Path


def configured_qmd_binary() -> str:
    """Resolve the real QMD executable without recording a machine-local path."""
    configured = os.environ.get(QMD_BIN_ENVIRONMENT)
    if configured:
        candidate = Path(configured)
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        pytest.fail(f"{QMD_BIN_ENVIRONMENT} does not name an executable: {configured}")
    discovered = shutil.which("qmd")
    if discovered:
        return discovered
    pytest.fail(f"configure {QMD_BIN_ENVIRONMENT} or put qmd on PATH")


def bubblewrap_binary() -> str:
    """Require the host-provided network denial boundary; never silently skip it."""
    discovered = shutil.which("bwrap")
    if discovered:
        return discovered
    pytest.fail("QMD qualification requires bwrap for --unshare-net execution")


def new_state(tmp_path: Path) -> QmdState:
    """Build all writable QMD locations below a single pytest-owned directory."""
    root = tmp_path / "qmd-state"
    corpus = root / "corpus"
    cwd = root / "cwd"
    config = root / "config"
    cache = root / "cache"
    home = root / "home"
    for path in (corpus, cwd, config, cache, home):
        path.mkdir(parents=True)
    return QmdState(
        root=root,
        corpus=corpus,
        cwd=cwd,
        config=config,
        cache=cache,
        home=home,
        index=root / "index.sqlite",
    )


def command(state: QmdState, *arguments: str) -> list[str]:
    """Build an argv-only QMD invocation inside a network-denied bubblewrap sandbox."""
    return [
        bubblewrap_binary(),
        "--die-with-parent",
        "--unshare-net",
        "--ro-bind",
        "/",
        "/",
        "--bind",
        str(state.root),
        str(state.root),
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--clearenv",
        "--setenv",
        "PATH",
        os.environ.get("PATH", ""),
        "--setenv",
        "HOME",
        str(state.home),
        "--setenv",
        "QMD_CONFIG_DIR",
        str(state.config),
        "--setenv",
        "XDG_CACHE_HOME",
        str(state.cache),
        "--setenv",
        "INDEX_PATH",
        str(state.index),
        "--chdir",
        str(state.cwd),
        "--",
        configured_qmd_binary(),
        *arguments,
    ]


def run(state: QmdState, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run an allowed real QMD command with finite execution and captured evidence."""
    result = subprocess.run(
        command(state, *arguments),
        cwd=state.cwd,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=PROCESS_TIMEOUT_SECONDS,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert_empty_model_cache(state)
    return result


def start(state: QmdState, *arguments: str) -> subprocess.Popen[str]:
    """Start one bounded update process; callers own its prompt termination and wait."""
    return subprocess.Popen(
        command(state, *arguments),
        cwd=state.cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def assert_empty_model_cache(state: QmdState) -> None:
    """Make model use/download visible even when lexical commands otherwise succeed."""
    model_cache = state.cache / "qmd" / "models"
    if model_cache.exists():
        assert not any(model_cache.iterdir()), f"model cache populated at {model_cache}"


def json_output(result: subprocess.CompletedProcess[str]) -> object:
    """Decode a QMD --format json response rather than relying on terminal formatting."""
    return json.loads(result.stdout)
