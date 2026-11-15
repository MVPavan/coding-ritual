"""`.claude/scripts/skill-catalog.py`: the router's reachability gate (unit-kinds R3).

Each case builds a tiny skills tree whose router routes one playbook and one
principle, breaks one route, and runs the whole `--check`.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2] / ".claude" / "scripts" / "skill-catalog.py"
)

PLAYBOOK_ENTRY = "- `playbooks/example.md`: a request to do the example."
PRINCIPLE_ENTRY = "- `principles/example.md`: the example situation holds."

ROUTER = f"""\
---
name: mvp-mode
description: Use at the start of every task.
---

When unsure, read `references/catalog.md`.

## Playbooks

{PLAYBOOK_ENTRY}

## Principles

{PRINCIPLE_ENTRY}

## Skills by situation
"""


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("skill_catalog", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module by name
    spec.loader.exec_module(module)
    return module


catalog = _load()


def _tree(root: Path, router: str) -> Path:
    skills = root / "skills"
    (skills / "mvp-mode" / "playbooks").mkdir(parents=True)
    (skills / "mvp-mode" / "playbooks" / "example.md").write_text("# Example\n")
    (skills / "mvp-mode" / "references").mkdir()
    (skills / "mvp-mode" / "references" / "catalog.md").write_text(
        f"# Catalog\n\n{catalog.MARKER}\n"
    )
    (skills / "mvp-mode" / "SKILL.md").write_text(router)
    (skills / "mvp-mode" / "principles").mkdir()
    (skills / "mvp-mode" / "principles" / "example.md").write_text(
        "# Example\n\nCited as `principle-example`.\n"
    )
    catalog.cmd_write(root, skills)
    return skills


def _check(
    root: Path,
    router: str,
    capsys: pytest.CaptureFixture[str],
    after: Callable[[Path], None] | None = None,
) -> tuple[int, str]:
    skills = _tree(root, router)
    if after is not None:
        after(skills)
    capsys.readouterr()
    code: int = catalog.cmd_check(root, skills)
    return code, capsys.readouterr().out


def test_valid_routes_pass(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code, out = _check(tmp_path, ROUTER, capsys)
    assert code == 0, out


def _delete_playbook(skills: Path) -> None:
    (skills / "mvp-mode" / "playbooks" / "example.md").unlink()


def _cite(text: str) -> Callable[[Path], None]:
    def write(skills: Path) -> None:
        (skills / "mvp-mode" / "playbooks" / "example.md").write_text(text)

    return write


def _add_principle_skill_folder(skills: Path) -> None:
    (skills / "principle-stray").mkdir()
    (skills / "principle-stray" / "SKILL.md").write_text(
        "---\nname: principle-stray\ndescription: Stray.\n---\n"
    )


def _add_principle_folder_named_otherwise(skills: Path) -> None:
    (skills / "principle-stray").mkdir()
    (skills / "principle-stray" / "SKILL.md").write_text(
        "---\nname: ordinary-name\ndescription: Stray.\n---\n"
    )


def _add_principle_folder_sidecar_only(skills: Path) -> None:
    (skills / "principle-stray" / "agents").mkdir(parents=True)
    (skills / "principle-stray" / "agents" / "openai.yaml").write_text("policy: {}\n")


@pytest.mark.parametrize(
    ("router", "after", "expected"),
    [
        pytest.param(
            ROUTER.replace("references/catalog.md", "references/missing.md"),
            None,
            "does not point at references/catalog.md",
            id="missing-catalog-link",
        ),
        pytest.param(
            ROUTER.replace(
                PRINCIPLE_ENTRY,
                f"<!-- {PRINCIPLE_ENTRY} -->",
            ),
            None,
            "principle principles/example.md has no entry",
            id="comment-only-mention",
        ),
        pytest.param(
            ROUTER.replace(f"{PRINCIPLE_ENTRY}\n", ""),
            None,
            "principle principles/example.md has no entry",
            id="principle-without-entry",
        ),
        pytest.param(
            ROUTER.replace("principles/example.md", "principles/ghost.md"),
            None,
            "entry `principles/ghost.md`",
            id="principle-entry-names-nothing",
        ),
        pytest.param(
            ROUTER,
            _cite("Apply `principle-ghost`.\n"),
            "unresolved principle `principle-ghost`",
            id="cited-principle-without-file",
        ),
        pytest.param(
            ROUTER,
            _cite("Run /principle-example now.\n"),
            "dead slash pointer /principle-example",
            id="principle-slash-form",
        ),
        pytest.param(
            ROUTER,
            _add_principle_skill_folder,
            "skill folder principle-stray",
            id="principle-as-skill-folder",
        ),
        pytest.param(
            ROUTER,
            _add_principle_folder_named_otherwise,
            "skill folder principle-stray",
            id="principle-folder-declaring-another-name",
        ),
        pytest.param(
            ROUTER,
            _add_principle_folder_sidecar_only,
            "skill folder principle-stray",
            id="principle-folder-with-only-a-sidecar",
        ),
        pytest.param(
            ROUTER.replace(f"{PLAYBOOK_ENTRY}\n", ""),
            None,
            "playbook playbooks/example.md has no entry",
            id="missing-entry",
        ),
        pytest.param(
            ROUTER.replace("a request to do the example.", ""),
            None,
            "names no situation",
            id="entry-without-situation",
        ),
        pytest.param(
            ROUTER,
            _delete_playbook,
            "entry `playbooks/example.md`",
            id="deleted-target",
        ),
        pytest.param(
            ROUTER.replace("`references/catalog.md`", "`references/catalog.md.bak`"),
            None,
            "does not point at references/catalog.md",
            id="catalog-link-extended",
        ),
        pytest.param(
            ROUTER.replace(PLAYBOOK_ENTRY, f"~~~markdown\n{PLAYBOOK_ENTRY}\n~~~"),
            None,
            "playbook playbooks/example.md has no entry",
            id="entry-in-tilde-fence",
        ),
        pytest.param(
            ROUTER.replace(PLAYBOOK_ENTRY, f"   ```\n{PLAYBOOK_ENTRY}\n   ```"),
            None,
            "playbook playbooks/example.md has no entry",
            id="entry-in-indented-fence",
        ),
    ],
)
def test_broken_routes_fail(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    router: str,
    after: Callable[[Path], None] | None,
    expected: str,
) -> None:
    code, out = _check(tmp_path, router, capsys, after)
    assert code != 0, out
    assert expected in out, out
