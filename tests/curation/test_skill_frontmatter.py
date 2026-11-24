"""`.claude/scripts/skill-catalog.py` parses every skill's frontmatter as YAML."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from tests.checks import test_skill_catalog_script as routes

SCRIPT = Path(__file__).resolve().parents[2] / ".claude/scripts/skill-catalog.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("skill_catalog_yaml", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


catalog = _load()


@pytest.mark.parametrize(
    ("frontmatter", "expected"),
    [
        ("name: a\ndescription: Use when x: y holds.\n", "not valid YAML"),
        ("name: a\ndescription: Use.\ndisable-model-invocation: yes-ish\n", "boolean"),
        ("name: [a]\ndescription: Use.\n", "`name` must be a string"),
    ],
)
def test_malformed_frontmatter_fails(
    tmp_path: Path, frontmatter: str, expected: str
) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "SKILL.md").write_text(f"---\n{frontmatter}---\n\n# A\n")

    failures = catalog.frontmatter_failures(tmp_path, tmp_path)

    assert len(failures) == 1 and expected in failures[0], failures


def test_quoted_colon_is_valid(tmp_path: Path) -> None:
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "SKILL.md").write_text(
        '---\nname: a\ndescription: "Use when x: y holds."\n---\n'
    )

    assert catalog.frontmatter_failures(tmp_path, tmp_path) == []


def test_every_installed_skill_parses() -> None:
    root = SCRIPT.parents[2]
    assert catalog.frontmatter_failures(root, root / ".claude/skills") == []


def _add_skill(frontmatter: str) -> Callable[[Path], None]:
    def write(skills: Path) -> None:
        (skills / "a").mkdir()
        (skills / "a" / "SKILL.md").write_text(f"---\n{frontmatter}---\n\n# A\n")

    return write


def test_check_fails_on_an_unquoted_colon(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = routes._check(
        tmp_path,
        routes.ROUTER,
        capsys,
        _add_skill("name: a\ndescription: Use when x: y holds.\n"),
    )

    assert code == 1
    assert "a/SKILL.md: frontmatter is not valid YAML" in out


def test_entries_follow_the_yaml_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    flag = "disable-model-invocation: true # manual only\n"
    skills = routes._tree(tmp_path, routes.ROUTER)
    _add_skill(f"name: a\ndescription: Use.\n{flag}")(skills)
    routes.catalog.cmd_write(tmp_path, skills)

    sidecar = (skills / "a" / "agents" / "openai.yaml").read_text()
    assert "allow_implicit_invocation: false" in sidecar
    capsys.readouterr()
    assert routes.catalog.cmd_check(tmp_path, skills) == 0, capsys.readouterr().out
