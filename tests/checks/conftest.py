"""Session-scoped fixture project + shared uv environment for the check scripts."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.checks._project import build_project, copy_project


@pytest.fixture(scope="session")
def pristine_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """The fixture project, built once per session."""
    return build_project(tmp_path_factory.mktemp("pristine"))


@pytest.fixture(scope="session")
def uv_environment(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One resolved uv environment shared by every copy of the fixture project."""
    return tmp_path_factory.mktemp("uv-env") / "venv"


@pytest.fixture
def project(pristine_project: Path, tmp_path: Path) -> Iterator[Path]:
    """A private copy of the fixture project for one case to mutate."""
    yield copy_project(pristine_project, tmp_path / "project")
