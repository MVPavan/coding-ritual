"""Candidate Python selectors cannot become host uv options or paths."""

import json
from pathlib import Path

import pytest

from tests import test_toolchain_seeding
from tests.test_toolchain_seeding import SeedLab
from workflow_interpreter.inspector.toolchain_models import ToolchainUnavailable

seed_lab = test_toolchain_seeding.seed_lab


@pytest.mark.parametrize("source", [".python-version", "pyproject.toml"])
@pytest.mark.parametrize(
    "selector",
    [
        "--config-file=/checkout/evil.toml",
        "--directory=/checkout",
        "--no-managed-python",
        "3.13 --no-managed-python",
        "/checkout/python",
        "3.13\n--no-managed-python",
        "3" * 129,
    ],
)
def test_candidate_request_refuses_before_host_uv(
    seed_lab: SeedLab, source: str, selector: str
) -> None:
    """Reject option injection, executable paths, and oversized selectors early."""
    path = seed_lab.repo / source
    if source == "pyproject.toml":
        path.write_text(
            '[project]\nname = "example"\nversion = "1.0"\n'
            f"requires-python = {json.dumps(selector)}\n"
        )
    else:
        path.write_text(selector)
    with pytest.raises(ToolchainUnavailable, match="invalid Python request"):
        seed_lab.seeder.prepare(
            seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "activation"
        )
    assert not seed_lab.calls.exists()


@pytest.mark.parametrize("source", [".python-version", "pyproject.toml"])
@pytest.mark.parametrize(
    "selector",
    [">=3.13", "3.13.9", ">=3.13, <3.14", "python3.13", "cpython@3.13.9"],
)
def test_valid_candidate_request_is_a_positional_argument(
    seed_lab: SeedLab, source: str, selector: str
) -> None:
    """Ordinary version requests remain usable after the option terminator."""
    path = seed_lab.repo / source
    if source == "pyproject.toml":
        path.write_text(
            '[project]\nname = "example"\nversion = "1.0"\n'
            f"requires-python = {json.dumps(selector)}\n"
        )
    else:
        path.write_text(selector)
    seed_lab.seeder.prepare(
        seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "activation"
    )
    calls = [json.loads(line)[0] for line in seed_lab.calls.read_text().splitlines()]
    finds = [args for args in calls if args[:2] == ["python", "find"]]
    assert finds and all(args[-2:] == ["--", selector] for args in finds)


def test_project_materialization_uses_validated_request(
    seed_lab: SeedLab, tmp_path: Path
) -> None:
    """Host project metadata gets a normalized request, preserving raw digest bytes."""
    raw = b" 3.13.9 \n"
    (seed_lab.repo / ".python-version").write_bytes(raw)
    pins = seed_lab.seeder._pins(seed_lab.repo, seed_lab.base, ".")
    assert pins is not None
    destination = tmp_path / "metadata"
    pins.write(destination)
    assert (destination / ".python-version").read_text() == "3.13.9\n"
    assert pins.python == raw


@pytest.mark.parametrize("empty", ["", " \n "])
def test_empty_python_selection_falls_through(seed_lab: SeedLab, empty: str) -> None:
    """Blank interpreter files fall back to project constraints, then defaults."""
    (seed_lab.repo / ".python-version").write_text(empty)
    pins = seed_lab.seeder._pins(seed_lab.repo, seed_lab.base, ".")
    assert pins is not None and pins.python_request == ">=3.13"
    project = seed_lab.repo / "pyproject.toml"
    project.write_text(project.read_text().replace('">=3.13"', '""'))
    pins = seed_lab.seeder._pins(seed_lab.repo, seed_lab.base, ".")
    assert pins is not None and pins.python_request is None


def test_project_range_is_not_materialized_as_python_version(
    seed_lab: SeedLab, tmp_path: Path
) -> None:
    """SYNC supplies an interpreter; a project range is not a version file."""
    pins = seed_lab.seeder._pins(seed_lab.repo, seed_lab.base, ".")
    assert pins is not None
    destination = tmp_path / "metadata"
    pins.write(destination)
    assert not (destination / ".python-version").exists()
