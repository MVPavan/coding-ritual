"""Criteria References and Check (offline part), and the check's workflow as written.

The reference grammar has one fixture table, ``fixtures/references.json``. The command's
parser (the digest's) and the workflow's inline step, extracted from the YAML that
``install-check`` writes and run with bash against the fake ``gh``, must both give its
answers.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from tests.mirror._harness import COMMAND, HOST, REPO, Mirror, real_tool

pytestmark = pytest.mark.bd

TABLE = json.loads(
    (Path(__file__).resolve().parent / "fixtures" / "references.json").read_text(
        encoding="utf-8"
    )
)
WORKFLOW = Path(".github") / "workflows" / "bead-reference-check.yml"
FOUND = "Bead reference found: "


def command_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("bead_mirror", COMMAND)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def expected(row: dict[str, Any]) -> list[int]:
    return [] if row["refs"] == "none" else list(row["refs"])


def install(mirror: Mirror) -> str:
    mirror.write_switch()
    result = mirror.run("install-check")
    assert result.returncode == 0, result.stderr
    return (mirror.clone / WORKFLOW).read_text(encoding="utf-8")


def step_script(workflow: str) -> str:
    """The inline step's ``run: |`` block, as the runner's shell receives it."""
    lines = workflow.splitlines(keepends=True)
    start = next(i for i, line in enumerate(lines) if line.strip() == "run: |") + 1
    indent = len(lines[start]) - len(lines[start].lstrip(" "))
    block = []
    for line in lines[start:]:
        if line.strip() and not line.startswith(" " * indent):
            break
        block.append(line[indent:] if line.strip() else "\n")
    return "".join(block)


class Check:
    """Runs the extracted step the way GitHub's runner does, against the fake ``gh``."""

    def __init__(self, mirror: Mirror, tmp_path: Path) -> None:
        self.mirror = mirror
        self.script = tmp_path / "step.sh"
        self.script.write_text(step_script(install(mirror)), encoding="utf-8")
        self.installed = len(mirror.fake.calls())  # the authority checks' reads
        runtime = tmp_path / "runner-bin"
        runtime.mkdir()
        (runtime / "python3").symlink_to(real_tool("python3"))
        self.path = f"{mirror.bin_dir}:{runtime}"

    def run(self, number: int, exempt: str = "") -> subprocess.CompletedProcess[str]:
        env = {
            "PATH": self.path,
            "GITHUB_SERVER_URL": f"https://{HOST}",
            "GITHUB_REPOSITORY": REPO,
            "PR_NUMBER": str(number),
            "BEAD_REF_EXEMPT": exempt,
        }
        return subprocess.run(
            [
                real_tool("bash"),
                "--noprofile",
                "--norc",
                "-eo",
                "pipefail",
                str(self.script),
            ],
            env=env,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )


@pytest.fixture
def check(mirror: Mirror, tmp_path: Path) -> Check:
    return Check(mirror, tmp_path)


def found_by_check(result: subprocess.CompletedProcess[str]) -> list[int]:
    if result.returncode != 0:
        assert "Fix: add a reference" in result.stdout, result.stdout
        return []
    line = next(x for x in result.stdout.splitlines() if x.startswith(FOUND))
    return [int(n.strip().lstrip("#")) for n in line[len(FOUND) :].split(",")]


def test_references_fixture_table_gives_the_same_answer_in_the_digest_parser_and_the_check(
    mirror: Mirror, check: Check
) -> None:
    assert (TABLE["host"], TABLE["repo"]) == (HOST, REPO)
    parse = command_module().references
    pulls = [mirror.fake.add_pull(body=row["text"]) for row in TABLE["rows"]]
    for row, number in zip(TABLE["rows"], pulls):
        assert parse(row["text"], HOST, REPO) == expected(row), row["text"]
        assert found_by_check(check.run(number)) == expected(row), row["text"]
    reads = [c["argv"] for c in mirror.fake.calls()[check.installed :]]
    assert reads == [
        ["api", "--hostname", HOST, f"repos/{REPO}/pulls/{n}"] for n in pulls
    ]


def test_references_one_tracked_reference_among_others_makes_a_pull_request_tracked() -> (
    None
):
    module = command_module()
    body = "Refs #3 (a pull request), fixes #99 (missing) and refs #25"
    found = module.references(body, HOST, REPO)
    assert found == [3, 99, 25]
    assert module.tracked(found, {25, 40})
    assert not module.tracked(found, {40})
    assert not module.tracked([], {25})


def test_check_no_reference_fails_with_the_fix_in_the_message(
    mirror: Mirror, check: Check
) -> None:
    result = check.run(mirror.fake.add_pull(body="Tidies the docs."))
    assert result.returncode != 0
    assert "has no reference to an issue" in result.stdout
    assert "Fix: add a reference to an issue in this repository" in result.stdout
    assert "'Refs #42'" in result.stdout


def test_check_a_reference_passes(mirror: Mirror, check: Check) -> None:
    result = check.run(mirror.fake.add_pull(body="Tidies the docs.\n\nRefs #7"))
    assert result.returncode == 0, result.stdout
    assert f"{FOUND}#7" in result.stdout


def test_check_an_exempt_author_passes(mirror: Mirror, check: Check) -> None:
    exempt = "release-bot, Dependabot[bot]"
    for body in ("No reference here.", None):
        number = mirror.fake.add_pull(author="dependabot[bot]", body=body)
        assert check.run(number, exempt).returncode == 0
        assert check.run(number).returncode != 0
    number = mirror.fake.add_pull(author="someone", body="No reference here.")
    assert check.run(number, exempt).returncode != 0


@pytest.mark.parametrize("body", [None, "", "  \n\t "])
def test_check_an_empty_body_fails(
    mirror: Mirror, check: Check, body: str | None
) -> None:
    result = check.run(mirror.fake.add_pull(body=body))
    assert result.returncode != 0
    assert "description is empty" in result.stdout
    assert "Fix: add a reference" in result.stdout


@pytest.mark.parametrize(
    "fault, value, why",
    [
        ("malformed_pull", "no_user", "malformed pull request"),
        ("malformed_pull", "not_json", "malformed pull request"),
        ("offline", True, "could not be read through the API"),
    ],
)
def test_check_a_malformed_or_unreadable_payload_fails(
    mirror: Mirror, check: Check, fault: str, value: Any, why: str
) -> None:
    number = mirror.fake.add_pull(body="Refs #7")
    mirror.fake.set_fault(fault, value)
    result = check.run(number)
    assert result.returncode != 0
    assert why in result.stdout
    assert "Fix: add a reference" in result.stdout


def test_check_a_response_without_a_body_fails_even_for_an_exempt_author(
    mirror: Mirror, check: Check
) -> None:
    number = mirror.fake.add_pull(author="release-bot", body=None)
    assert check.run(number, "release-bot").returncode == 0, "an explicit null body"
    mirror.fake.set_fault("malformed_pull", "no_body")
    result = check.run(number, "release-bot")
    assert result.returncode != 0
    assert "malformed pull request" in result.stdout


def test_check_a_missing_pull_request_number_fails(check: Check) -> None:
    result = check.run(404)
    assert result.returncode != 0
    assert "could not be read through the API" in result.stdout
    assert "Fix: add a reference" in result.stdout


def test_workflow_is_trusted_minimal_and_carries_the_commands_grammar(
    mirror: Mirror,
) -> None:
    text = install(mirror)
    lines = text.splitlines()
    top = {line.split(":")[0] for line in lines if re.match(r"[a-z-]+:", line)}
    assert top == {"name", "on", "permissions", "concurrency", "jobs"}
    on = lines[lines.index("on:") + 1 :]
    assert on[: on.index("")] == [
        "  pull_request_target:",
        "    types: [opened, edited, reopened, synchronize]",
    ]
    assert [x for x in lines if re.match(r"\s*permissions:", x)] == ["permissions:"]
    perms = lines[lines.index("permissions:") + 1 :]
    assert perms[: perms.index("")] == ["  pull-requests: read"]
    conc = lines[lines.index("concurrency:") + 1 : lines.index("concurrency:") + 3]
    assert conc == [
        "  group: bead-reference-check-${{ github.event.pull_request.number }}",
        "  cancel-in-progress: true",
    ]
    after_jobs = lines[lines.index("jobs:") + 1 :]
    assert [x for x in after_jobs if re.match(r"  [a-z-]+:$", x)] == [
        "  bead-reference:"
    ]
    assert "    name: bead-reference" in lines
    assert "checkout" not in text and "uses:" not in text
    assert (
        "pull_request.body" not in text
        and "github.event.pull_request.title" not in text
    )
    script = step_script(text)
    assert "${{" not in script, "event fields reach the script only through env"
    assert "          BEAD_REF_EXEMPT: ${{ vars.BEAD_REF_EXEMPT }}" in lines
    module = command_module()
    assert f"re.compile({module.REFERENCE_PATTERN!r}, re.IGNORECASE)" in script
    assert module.check_grammar_source() in script


def test_install_check_writes_once_refuses_a_differing_file_and_force_replaces(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    path = mirror.clone / WORKFLOW
    first = mirror.run("install-check")
    assert first.returncode == 0 and str(path) in first.stdout
    written = path.read_text(encoding="utf-8")
    again = mirror.run("install-check")
    assert again.returncode == 0 and "unchanged" in again.stdout
    path.write_text(written + "# local edit\n", encoding="utf-8")
    refused = mirror.run("install-check")
    assert refused.returncode == 9 and "--force" in refused.stderr
    assert path.read_text(encoding="utf-8").endswith("# local edit\n")
    forced = mirror.run("install-check", "--force")
    assert forced.returncode == 0 and str(path) in forced.stdout
    assert path.read_text(encoding="utf-8") == written
    assert mirror.fake.writes() == []
    assert not [c for c in mirror.bd_calls() if c.startswith("update")]
    assert mirror.mirror_files() == ["switch.json"]


def test_install_check_with_an_authority_mismatch_writes_no_workflow(
    mirror: Mirror,
) -> None:
    mirror.write_switch()
    mirror.fake.set("login", "intruder")
    result = mirror.run("install-check")
    assert result.returncode == 4, result.stderr
    assert not (mirror.clone / WORKFLOW).exists()


def test_install_check_without_the_switch_is_silent_and_writes_nothing(
    mirror: Mirror,
) -> None:
    result = mirror.run("install-check")
    assert (result.returncode, result.stdout, result.stderr) == (0, "", "")
    assert not (mirror.clone / ".github").exists()
    assert mirror.fake.calls() == [] and mirror.bd_calls() == []
