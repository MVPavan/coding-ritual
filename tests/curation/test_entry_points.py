"""The thin entry points run with PYTHONPATH unset, and the stdlib-only parts of
`curation` import no third-party package (stages-design, Acceptance 13)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCAN = REPO / "harness_lifecycle" / "scan.py"
REGISTRY = REPO / "harness_lifecycle" / "registry" / "registry.py"


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def _run(*argv: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=_env(),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_scan_entry_runs_without_pythonpath(tmp_path: Path) -> None:
    skill = tmp_path / "harness" / "skills" / "alpha"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: Alpha.\n---\n# Alpha\n", encoding="utf-8"
    )
    # The isolated interpreter (-I) ignores PYTHONPATH and site-packages, so the
    # entry must find `curation` on its own and need nothing beyond stdlib.
    result = _run(
        sys.executable,
        "-I",
        str(SCAN),
        "catalog",
        str(tmp_path / "harness"),
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    assert "## catalog: harness" in result.stdout
    assert f"{'skill':<10}{1:>10}{1:>10}" in result.stdout


def test_registry_entry_runs_without_pythonpath(tmp_path: Path) -> None:
    result = _run(sys.executable, str(REGISTRY), "--help", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Skill + capability registry." in result.stdout


@pytest.mark.parametrize("module", ["curation", "curation.scan", "curation.scan.cli"])
def test_stdlib_only_import(module: str) -> None:
    # Only modules the import itself loads count (site may preload others).
    code = (
        "import sys\n"
        f"sys.path.insert(0, {str(REPO)!r})\n"
        "before = set(sys.modules)\n"
        f"import {module}\n"
        "new = {n.split('.')[0] for n in set(sys.modules) - before}\n"
        "print(','.join(sorted(new - sys.stdlib_module_names - {'curation'})))\n"
    )
    result = _run(sys.executable, "-I", "-c", code, cwd=REPO)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ""
