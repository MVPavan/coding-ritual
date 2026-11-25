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


@pytest.mark.parametrize("exists", [True, False])
def test_canonical_skill_paths_are_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], exists: bool
) -> None:
    """A `.agents/skills/...` reference must name a file in the selected tree."""
    target = tmp_path / "skills" / "tdd" / "present.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Present\n")
    name = "present.md" if exists else "missing.md"
    code, out = _check(
        tmp_path,
        ROUTER,
        capsys,
        _cite(f"# Example\n\nSee `.agents/skills/tdd/{name}`.\n"),
    )
    if exists:
        assert code == 0, out
    else:
        assert code == 1, out
        assert "dead path .agents/skills/tdd/missing.md" in out


# --- U8: routes.md, the selected tree, inventories, pointers-only ------------


def _run(argv: list[str], capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    capsys.readouterr()
    code: int = catalog.main(argv)
    return code, capsys.readouterr().out


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _routes(skills: Path, text: str) -> None:
    _write(skills / "mvp-mode" / "routes.md", text)


def _skill(skills: Path, name: str, body: str = "") -> None:
    _write(
        skills / name / "SKILL.md",
        f"---\nname: {name}\ndescription: Use for {name}.\n---\n{body}",
    )
    _write(
        skills / name / "agents" / "openai.yaml",
        "policy:\n  allow_implicit_invocation: true\n",
    )


def test_routes_md_playbook_line_routes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A playbook routed only from routes.md is reachable."""

    def move(skills: Path) -> None:
        router = skills / "mvp-mode" / "SKILL.md"
        router.write_text(router.read_text().replace(f"{PLAYBOOK_ENTRY}\n", ""))
        _routes(skills, f"# Routes\n\n{PLAYBOOK_ENTRY}\n")

    code, out = _check(tmp_path, ROUTER, capsys, move)
    assert code == 0, out


def test_dead_path_in_routes_md_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _check(
        tmp_path,
        ROUTER,
        capsys,
        lambda skills: _routes(
            skills, "# Routes\n\nMethod in `playbooks/ghost/notes.md`.\n"
        ),
    )
    assert code == 1, out
    assert "dead path playbooks/ghost/notes.md" in out


@pytest.mark.parametrize("prefix", [".agents/skills", ".claude/skills"])
def test_skill_tokens_resolve_against_selected_tree(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], prefix: str
) -> None:
    """`--root` holds harness-scan, the selected tree does not: the token fails."""
    for held in (".agents/skills", ".claude/skills"):
        _write(tmp_path / held / "harness-scan" / "SKILL.md", "# Scan\n")
    skills = _tree(tmp_path, ROUTER)
    _cite(f"# Example\n\nSee `{prefix}/harness-scan/SKILL.md`.\n")(skills)
    code, out = _run(["--root", str(tmp_path), "--skills-dir", str(skills)], capsys)
    assert code == 1, out
    assert f"dead path {prefix}/harness-scan/SKILL.md" in out


def test_other_agents_tokens_are_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, out = _check(
        tmp_path, ROUTER, capsys, _cite("# Example\n\nSee `.agents/ghost.json`.\n")
    )
    assert code == 1, out
    assert "dead path .agents/ghost.json" in out


def test_extra_repo_skill_needs_pointers_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills = _tree(tmp_path, ROUTER)
    _skill(skills, "repo-extra")
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills)]
    code, out = _run(argv, capsys)
    assert code == 1, out
    assert "stale generated section" in out
    code, out = _run([*argv, "--pointers-only"], capsys)
    assert code == 0, out


@pytest.mark.parametrize("pointers_only", [False, True])
def test_replaces_line_to_absent_new_name_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], pointers_only: bool
) -> None:
    skills = _tree(tmp_path, ROUTER)
    _routes(
        skills, f"- Replaces `example-skill` with `ghost-skill` (baseline {BASELINE})\n"
    )
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills)]
    code, out = _run(argv + ["--pointers-only"] * pointers_only, capsys)
    assert code == 1, out
    assert (
        "FAIL skills/mvp-mode/routes.md: Replaces `example-skill` with `ghost-skill`"
        " — `ghost-skill` names nothing installed"
    ) in out


def test_pointers_only_follows_replaces_and_lists_migrations(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An old name resolves through its replacement; a repo-owned file that
    still names it is listed for local migration."""
    skills = _tree(tmp_path, ROUTER)
    _skill(
        skills,
        "local-scan",
        "Run /old-scan, then read `.agents/skills/old-scan/SKILL.md`.\n",
    )
    _routes(skills, f"- Replaces `old-scan` with `local-scan` (baseline {BASELINE})\n")
    _write(
        tmp_path / ".repo-context" / "harness-settings.txt", "repo-owned\tlocal-scan\n"
    )
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills), "--pointers-only"]
    code, out = _run(argv, capsys)
    assert code == 0, out
    assert "local-scan/SKILL.md:5 /old-scan" in out
    assert "local-scan/SKILL.md:5 .agents/skills/old-scan/SKILL.md" in out


def _inventory(root: Path, *paths: str) -> str:
    listing = root / "inventory.txt"
    listing.write_text("".join(f"{p}\n" for p in paths))
    return str(listing)


@pytest.mark.parametrize("marked", [False, True])
def test_inventory_decides_overlay_tokens(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], marked: bool
) -> None:
    """`--root` holds unit-kinds.md, the inventory does not; `(if present)`
    makes the reference conditional."""
    _write(tmp_path / ".repo-context" / "unit-kinds.md", "# Kinds\n")
    skills = _tree(tmp_path, ROUTER)
    suffix = " (if present)" if marked else ""
    _cite(f"# Example\n\nLogged in `.repo-context/unit-kinds.md`{suffix}.\n")(skills)
    listing = _inventory(tmp_path, ".repo-context/repo-map.md")
    argv = [
        "--root",
        str(tmp_path),
        "--skills-dir",
        str(skills),
        "--inventory",
        listing,
    ]
    code, out = _run(argv, capsys)
    if marked:
        assert code == 0, out
    else:
        assert code == 1, out
        assert "dead path .repo-context/unit-kinds.md" in out


def test_inventory_directory_token_resolves(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    skills = _tree(tmp_path, ROUTER)
    _cite("# Example\n\nSee `.repo-context/` and `.repo-context/unit-kinds.md`.\n")(
        skills
    )
    listing = _inventory(tmp_path, ".repo-context/repo-map.md")
    argv = [
        "--root",
        str(tmp_path),
        "--skills-dir",
        str(skills),
        "--inventory",
        listing,
    ]
    code, out = _run(argv, capsys)
    assert code == 1, out
    assert "dead path .repo-context/unit-kinds.md" in out
    assert "dead path .repo-context/ " not in out


@pytest.mark.parametrize(
    "plant", [".agents/skills/../inventory.txt", ".codex/README.md"]
)
def test_inventory_rejects_pointers_the_install_lacks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], plant: str
) -> None:
    """Both exist on disk beside the staged tree; neither is in the install:
    a `..` out of the skills tree and a `.codex/` path the inventory lacks."""
    _write(tmp_path / ".codex" / "README.md", "# Codex\n")
    skills = _tree(tmp_path, ROUTER)
    _cite(f"# Example\n\nSee `{plant}`, `.codex/hooks.json` and `.codex/skills/`.\n")(
        skills
    )
    listing = _inventory(tmp_path, ".codex/hooks.json")
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills), "--inventory", listing]
    code, out = _run(argv, capsys)
    assert code == 1, out
    assert f"dead path {plant}" in out
    assert "dead path .codex/hooks.json" not in out
    assert "dead path .codex/skills/" not in out


# --- U8 review: staged install, Replaces targets, router-relative paths -----

BASELINE = "0" * 64
REPO = SCRIPT.parents[2]

# The overlay stubs the installer writes (scratchpad/mvp-stack/e0a/plan-B.md,
# U11): the standard `.repo-context/` overlay, `GLOSSARY.md` and
# `coding-style.md`, `harness-settings.txt` and the router's `routes.md`.
INSTALL_STUBS = (
    *(
        f".repo-context/{name}"
        for name in (
            "brief.md",
            "repo-map.md",
            "docs-index.md",
            "verification.md",
            "invariants.md",
            "tools.md",
            "tracking.md",
            "learnings.md",
            "adoption-report.md",
            "code-intel.md",
            "GLOSSARY.md",
            "coding-style.md",
            "harness-settings.txt",
        )
    ),
    ".agents/skills/mvp-mode/routes.md",
)


def test_staged_payload_passes_with_install_inventory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The shipped skill tree, minus the workshop's `repo-owned` units, names
    only what an install holds: its own files, the template's `.claude` and
    `.codex` residue and the overlay stubs."""
    import shutil
    import subprocess

    def tracked(*paths: str) -> list[str]:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z", "--", *paths],
            capture_output=True,
            check=True,
        ).stdout
        return [p for p in out.decode().split("\0") if p]

    owned = catalog.read_settings(REPO).get("repo-owned", [])
    assert owned, "the workshop lists its repo-owned units"
    stage = tmp_path / "skills"
    prefix = ".agents/skills/"
    for path in tracked(prefix):
        rel = path[len(prefix) :]
        if any(
            rel == o.rstrip("/") or rel.startswith(o.rstrip("/") + "/") for o in owned
        ):
            continue
        if not (REPO / path).is_file():
            continue
        (stage / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / path, stage / rel)
    catalog.cmd_write(tmp_path, stage)
    installed = [
        prefix + str(p.relative_to(stage)) for p in stage.rglob("*") if p.is_file()
    ]
    listing = _inventory(
        tmp_path, *installed, *tracked(".claude", ".codex"), *INSTALL_STUBS
    )
    code, out = _run(
        [
            "--check",
            "--root",
            str(tmp_path),
            "--skills-dir",
            str(stage),
            "--inventory",
            listing,
        ],
        capsys,
    )
    assert code == 0, out


@pytest.mark.parametrize("pointers_only", [False, True])
@pytest.mark.parametrize(
    ("new", "plant"),
    [
        (".agents/skills/ghost-skill/README.md", "ghost-skill/README.md"),
        ("playbooks/ghost.md", "mvp-mode/playbooks/ghost.md/"),
        ("ghost-skill", "ghost-skill/notes.md"),
    ],
)
def test_replaces_new_side_must_be_a_unit_entry_point(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pointers_only: bool,
    new: str,
    plant: str,
) -> None:
    """An existing README, a directory or a folder without SKILL.md is no unit."""
    skills = _tree(tmp_path, ROUTER)
    target = skills / plant
    if plant.endswith("/"):
        target.mkdir(parents=True)
    else:
        _write(target, "# Not a unit\n")
    _routes(skills, f"- Replaces `old-scan` with `{new}` (baseline {BASELINE})\n")
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills)]
    code, out = _run(argv + ["--pointers-only"] * pointers_only, capsys)
    assert code == 1, out
    assert (
        f"FAIL skills/mvp-mode/routes.md: Replaces `old-scan` with `{new}`"
        f" — `{new}` names nothing installed"
    ) in out


@pytest.mark.parametrize("present", [False, True])
def test_file_beneath_replaced_skill_needs_its_counterpart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], present: bool
) -> None:
    skills = _tree(tmp_path, ROUTER)
    _skill(
        skills, "local-scan", "Read `.agents/skills/old-scan/references/deleted.md`.\n"
    )
    if present:
        _write(skills / "local-scan" / "references" / "deleted.md", "# Kept\n")
    _routes(skills, f"- Replaces `old-scan` with `local-scan` (baseline {BASELINE})\n")
    _write(
        tmp_path / ".repo-context" / "harness-settings.txt", "repo-owned\tlocal-scan\n"
    )
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills), "--pointers-only"]
    code, out = _run(argv, capsys)
    if present:
        assert code == 0, out
        assert (
            "MIGRATE local-scan/SKILL.md:5 .agents/skills/old-scan/references/deleted.md"
            in out
        )
    else:
        assert code == 1, out
        assert "FAIL dead path .agents/skills/old-scan/references/deleted.md" in out


def _forked_router(tmp_path: Path, mapping: bool) -> Path:
    """The router still routes `playbooks/example.md`; the repo forked it to
    `playbooks/local.md` and withdrew the old file."""
    skills = _tree(tmp_path, ROUTER)
    playbooks = skills / "mvp-mode" / "playbooks"
    (playbooks / "example.md").rename(playbooks / "local.md")
    lines = ["- `playbooks/local.md`: a request to do the local example.\n"]
    if mapping:
        lines.append(
            f"- Replaces `playbooks/example.md` with `playbooks/local.md`"
            f" (baseline {BASELINE})\n"
        )
    _routes(skills, "".join(lines))
    return skills


@pytest.mark.parametrize("mapping", [False, True])
def test_forked_router_route_follows_replaces(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], mapping: bool
) -> None:
    skills = _forked_router(tmp_path, mapping)
    _skill(skills, "local-caller", "Run `playbooks/example.md` first.\n")
    _write(
        tmp_path / ".repo-context" / "harness-settings.txt",
        "repo-owned\tlocal-caller\n",
    )
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills), "--pointers-only"]
    code, out = _run(argv, capsys)
    if mapping:
        assert code == 0, out
        assert "MIGRATE local-caller/SKILL.md:5 playbooks/example.md" in out
    else:
        assert code == 1, out
        assert "FAIL dead path playbooks/example.md at skills/mvp-mode/SKILL.md" in out


def test_live_route_to_replaced_playbook_resolves(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A routes.md row may still name the old playbook while the mapping holds."""
    skills = _forked_router(tmp_path, mapping=True)
    routes = skills / "mvp-mode" / "routes.md"
    routes.write_text(
        routes.read_text() + "- `playbooks/example.md`: the old request.\n"
    )
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills), "--pointers-only"]
    code, out = _run(argv, capsys)
    assert code == 0, out


@pytest.mark.parametrize("pointers_only", [False, True])
@pytest.mark.parametrize("comment", ["", " <!-- forked for the local scan -->"])
def test_replaces_old_operand_is_not_a_dead_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pointers_only: bool,
    comment: str,
) -> None:
    """The mapping parser and the operand exemption read the same masked row."""
    skills = _tree(tmp_path, ROUTER)
    _skill(skills, "local-scan")
    catalog.cmd_write(tmp_path, skills)
    _routes(
        skills,
        f"- Replaces `.agents/skills/old-scan/SKILL.md` with `local-scan`"
        f" (baseline {BASELINE}){comment}\n",
    )
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills)]
    code, out = _run(argv + ["--pointers-only"] * pointers_only, capsys)
    assert code == 0, out


# --- U8 review round 2: one identity per operand, one resolver per reference -


def _alias_skill(skills: Path) -> None:
    """The folder `alias-name` declares the skill `other-name`."""
    _write(
        skills / "alias-name" / "SKILL.md",
        "---\nname: other-name\ndescription: Use for aliases.\n---\n",
    )


@pytest.mark.parametrize(
    ("new", "passes"),
    [
        ("alias-name", False),
        ("other-name", True),
        (".agents/skills/alias-name/SKILL.md", True),
    ],
)
def test_replaces_bare_name_is_a_declared_skill_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], new: str, passes: bool
) -> None:
    """`/old-scan` resolves only when its replacement is a skill `/other-name`
    reaches; the folder name alone is not one."""
    skills = _tree(tmp_path, ROUTER)
    _alias_skill(skills)
    _skill(skills, "local-caller", "Run /old-scan.\n")
    _routes(skills, f"- Replaces `old-scan` with `{new}` (baseline {BASELINE})\n")
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills), "--pointers-only"]
    code, out = _run(argv, capsys)
    if passes:
        assert code == 0, out
    else:
        assert code == 1, out
        assert f"`{new}` names nothing installed" in out
        assert "dead slash pointer /old-scan" in out


def test_replaces_old_skill_path_matches_its_declared_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An old skill named by its path is the one `/other-name` calls."""
    skills = _tree(tmp_path, ROUTER)
    _alias_skill(skills)
    _skill(skills, "local-scan")
    _skill(skills, "local-caller", "Run /other-name.\n")
    _routes(
        skills,
        f"- Replaces `.agents/skills/alias-name/SKILL.md` with `local-scan`"
        f" (baseline {BASELINE})\n",
    )
    _write(
        tmp_path / ".repo-context" / "harness-settings.txt",
        "repo-owned\tlocal-caller\n",
    )
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills), "--pointers-only"]
    code, out = _run(argv, capsys)
    assert code == 0, out
    assert "MIGRATE local-caller/SKILL.md:5 /other-name" in out


@pytest.mark.parametrize("pointers_only", [False, True])
@pytest.mark.parametrize(
    ("line", "passes"),
    [
        pytest.param("Open `playbooks/smoke.md` next.", True, id="own-companion"),
        pytest.param("See `playbooks/example.md:18`.", True, id="citation"),
        pytest.param("See `playbooks/example.md:18-20`.", True, id="citation-range"),
        pytest.param("Read `playbooks/optional.md` (if present).", True, id="optional"),
        pytest.param("Run `playbooks/ghost.md` first.", False, id="missing-shared"),
    ],
)
def test_router_relative_paths_resolve_like_their_reader(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    pointers_only: bool,
    line: str,
    passes: bool,
) -> None:
    skills = _tree(tmp_path, ROUTER)
    _skill(skills, "release-check", line + "\n")
    _write(skills / "release-check" / "playbooks" / "smoke.md", "# Smoke\n")
    catalog.cmd_write(tmp_path, skills)
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills)]
    code, out = _run(argv + ["--pointers-only"] * pointers_only, capsys)
    if passes:
        assert code == 0, out
    else:
        assert code == 1, out
        assert (
            "FAIL dead path playbooks/ghost.md at skills/release-check/SKILL.md:5"
            in out
        )


@pytest.mark.parametrize("old", ["principle-example", "principles/example.md"])
@pytest.mark.parametrize("new", ["principle-local", "principles/local.md"])
def test_principle_operands_share_the_citation_identity(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], old: str, new: str
) -> None:
    skills = _tree(tmp_path, ROUTER)
    principles = skills / "mvp-mode" / "principles"
    (principles / "example.md").rename(principles / "local.md")
    _skill(skills, "local-caller", "Apply `principle-example`.\n")
    _routes(skills, f"- Replaces `{old}` with `{new}` (baseline {BASELINE})\n")
    _write(
        tmp_path / ".repo-context" / "harness-settings.txt",
        "repo-owned\tlocal-caller\n",
    )
    argv = ["--root", str(tmp_path), "--skills-dir", str(skills), "--pointers-only"]
    code, out = _run(argv, capsys)
    assert code == 0, out
    assert "MIGRATE local-caller/SKILL.md:5 principle-example" in out


@pytest.mark.parametrize(
    ("comment", "passes"),
    [("# (if present)", True), ("# (if present) else create it first", False)],
)
def test_if_present_comment_is_an_exact_annotation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], comment: str, passes: bool
) -> None:
    code, out = _check(
        tmp_path,
        ROUTER,
        capsys,
        _cite(f'# Example\n\n    CONFIG = ".repo-context/ghost.toml"  {comment}\n'),
    )
    if passes:
        assert code == 0, out
    else:
        assert code == 1, out
        assert "dead path .repo-context/ghost.toml" in out
