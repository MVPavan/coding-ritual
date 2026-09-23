"""The `dws` console script, exercised as an installed program.

These run the entry point the way a user gets it — resolved from PATH in the
synced environment — so they fail if the script is never installed, not just if
`main()` misbehaves when imported.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest


@pytest.fixture(scope="session")
def dws_script() -> str:
    script = shutil.which("dws")
    if script is None:
        pytest.fail("the `dws` console script is not installed in this environment")
    return script


def run(script: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [script, *args], capture_output=True, text=True, timeout=60, check=False
    )


def test_help_exits_zero_and_names_the_command(dws_script: str) -> None:
    result = run(dws_script, "--help")

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("usage: dws")
    assert result.stderr == ""


def test_help_describes_dws_as_a_scaffold_without_claiming_capabilities(
    dws_script: str,
) -> None:
    help_text = run(dws_script, "--help").stdout.lower()

    assert "scaffold" in help_text
    # No capability is implemented yet, so no subcommand may advertise one.
    for unimplemented in ("fetch", "search", "crawl", "serve", "daemon", "mcp"):
        assert unimplemented not in help_text


def test_bare_invocation_prints_the_same_help_and_exits_zero(dws_script: str) -> None:
    bare = run(dws_script)

    assert bare.returncode == 0, bare.stderr
    assert bare.stdout == run(dws_script, "--help").stdout


def test_unrecognised_flag_is_an_argparse_usage_error(dws_script: str) -> None:
    result = run(dws_script, "--no-such-flag")

    assert result.returncode == 2
    assert result.stdout == ""
    assert "unrecognized arguments: --no-such-flag" in result.stderr


def test_unrecognised_positional_is_an_argparse_usage_error(dws_script: str) -> None:
    result = run(dws_script, "fetch")

    assert result.returncode == 2
    assert "usage: dws" in result.stderr


def test_version_flag_reports_the_installed_distribution_version(dws_script: str) -> None:
    from importlib.metadata import version

    result = run(dws_script, "--version")

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"dws {version('dws')}"


def test_module_execution_matches_the_console_script(dws_script: str) -> None:
    import sys

    module = subprocess.run(
        [sys.executable, "-m", "dws", "--help"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert module.returncode == 0, module.stderr
    assert module.stdout == run(dws_script, "--help").stdout
