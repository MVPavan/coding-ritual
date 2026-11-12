"""The discovery record checker: plan 20 section 6's rules, `--next` and `--index`."""

import re
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).parents[2] / ".claude/skills/discovery"
SCRIPT = SKILL / "scripts/check_record.py"
TEMPLATE = SKILL / "templates/record.md"
HEADER_FIELDS = ["Question", "Area", "Topic", "Date", "Run", "Caller", "Outcome"]
HEAD = """# Discovery record

**Question:** How should run state be stored?
**Area:** general
**Topic:** run-state
**Date:** 2026-11-11
**Run:** s1-a
**Caller:** user
**Outcome:** JSONL settled; retention open.

| # | Question | Answer | Source | Confidence | Status |
|---|---|---|---|---|---|
"""
ROWS = {
    "code": "| 1 | Format? | JSONL | code: src/store.py:2 | high | established |\n",
    "outside": "| 2 | Locking? | flock | outside: Linux man page, 6.1, 2026-11-01 | medium | established |\n",
    "prototype": "| 3 | Fast? | Yes | prototype: reports/bench.md | low | established |\n",
    "owner": '| 4 | Rotate? | Daily | owner: "daily, keep 30" (2026-11-11) |  | decided |\n',
    "delegation": "| 5 | Path? | var/ | owner: delegation cr-1.2 |  | decided |\n",
    "routine": "| 6 | Name? | runs.jsonl | agent: routine, matches logs.jsonl |  | routine |\n",
    "proposed": "| 7 | Compress? | gzip weekly | agent: smallest change |  | proposed |\n",
    "open": "| 8 | Retention? |  |  |  | open |\n",
    "computed": "| 9 | How many? | 3 lines | computed: scripts/count.py -> reports/count.txt | high | established |\n",
}
GOOD = HEAD + "".join(ROWS.values())

# (old, new, rule): one fault planted in GOOD must be named by its rule.
FAULTS = [
    ("**Date:** 2026-11-11", "**Date:** 11/11/2026", "header"),
    ("**Caller:** user\n", "**Caller:** user\n**Revises:**\n", "header"),
    ("| JSONL | code:", "| JSONL | extra | code:", "cells"),
    ("| low | established |", "| low | settled |", "status"),
    ("| var/ | owner:", "| var/ | someone said so", "source"),
    ('owner: "daily, keep 30" (2026-11-11)', "agent: routine, obvious", "decided"),
    ('owner: "daily, keep 30" (2026-11-11)', 'owner: "daily, keep 30"', "owner"),
    ("owner: delegation cr-1.2", "owner: delegation", "owner"),
    ("| 8 | Retention? |  |  |", "| 8 | Retention? |  | owner: invented |", "owner"),
    ("| 8 | Retention? |  |  |", "| 8 | Retention? |  | agent: |", "agent"),
    ("| 8 | Retention? |  |  |", "| 8 | Retention? |  | prototype: |", "prototype"),
    ("src/store.py:2 |", "nonsense |", "code"),
    ("|---|---|---|---|---|---|\n", "", "table"),
    (
        "| # | Question | Answer | Source | Confidence | Status |",
        (
            "| 9 | Late? | x | agent: late |  | settled |\n"
            "| # | Question | Answer | Source | Confidence | Status |"
        ),
        "table",
    ),
    ("|---|---|---|---|---|---|", "| 1 | broken |", "table"),
    (
        "| 1 | Format? | JSONL | code: src/store.py:2 | high | established |",
        "|| 1 | Format? | JSONL | code: src/store.py:2 | high | established ||",
        "cells",
    ),
    (
        "| 1 | Format? | JSONL | code: src/store.py:2 | high | established |",
        "  | 1 | Format? | JSONL | code: src/store.py:2 | high | invented |",
        "status",
    ),
    ("code: src/store.py:2 | high", "agent: read it | high", "established"),
    ("code: src/store.py:2 | high", "code: src/store.py:2 | ", "established"),
    ("2026-11-01 | medium", "2026-11-01 | ", "established"),
    ("bench.md | low", "bench.md | ", "established"),
    ("bench.md | low", "bench.md | certain", "established"),
    ("matches logs.jsonl |  |", "matches logs.jsonl | high |", "confidence"),
    ("agent: routine, matches logs.jsonl", "code: src/store.py:1", "routine"),
    ("agent: routine, matches logs.jsonl", "agent: matches logs.jsonl", "routine"),
    ("| gzip weekly | agent:", "|  | agent:", "proposed"),
    ("agent: smallest change", "owner: delegation cr-1.3", "proposed"),
    ("| runs.jsonl | agent:", "|  | agent:", "answer"),
    ("Linux man page, 6.1, 2026-11-01", "Linux man page, 2026-11-01", "outside"),
    ("src/store.py:2", "src/missing.py:2", "code"),
    ("src/store.py:2", "src/store.py:4", "code"),
    ("src/store.py:2", "src/store.py:0", "code"),
    ("src/store.py:2", "../outside.py:1", "code"),
    ("reports/bench.md", "reports/none.md", "prototype"),
    ("count.py -> reports", "count.py reports", "computed"),
    ("scripts/count.py ->", "scripts/none.py ->", "computed"),
    ("-> reports/count.txt", "-> reports/none.txt", "computed"),
    ("count.txt | high", "count.txt | ", "established"),
    ("count.txt | high | established", "count.txt |  | proposed", "proposed"),
]
# Each must still pass: the other legal shapes of a rule.
PASSES = [
    GOOD.replace("src/store.py:2", "src/store.py:1-3"),
    GOOD.replace(
        "**Caller:** user\n", "**Caller:** user\n**Revises:** owner, 2026-11-11\n"
    ),
    GOOD.replace(
        "| 8 | Retention? |  |  |", "| 8 | Retention? | maybe 30 days | agent: guess |"
    ),
    GOOD.replace("| JSONL |", r"| JSONL \| CSV |"),
    GOOD.replace(
        "| 8 | Retention? |  |  |", "| 8 | Retention? |  | owner: delegation cr-9 |"
    ),
    GOOD.replace("src/store.py:2", "src/space name.py:1"),
    GOOD + "Notes right after the last row.\n",
]
# Not anchored by the `# Discovery record` title: a full valid record inside a comment.
COMMENTED_NOTES = "# Notes\n\nExample <!--\n" + GOOD + "\n-->\n"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    (tmp_path / "src").mkdir()
    (tmp_path / "src/store.py").write_text("a = 1\nb = 2\nc = 3\n")
    (tmp_path / "reports").mkdir()
    (tmp_path / "reports/bench.md").write_text("# Bench\n")
    (tmp_path / "src/space name.py").write_text("x = 1\n")
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/count.py").write_text("print(3)\n")
    (tmp_path / "reports/count.txt").write_text("3\n")
    return tmp_path


def run(*args: object) -> tuple[int, str]:
    out = subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )
    return out.returncode, out.stdout + out.stderr


def check(root: Path, text: str, name: str = "record.md") -> tuple[int, str]:
    path = root / name
    path.write_text(text)
    return run(path, "--root", root)


def test_good_record_passes(root: Path) -> None:
    expected = f"{root / 'record.md'}: {len(ROWS)} rows, 0 problems\n"
    assert check(root, GOOD) == (0, expected)


@pytest.mark.parametrize("text", PASSES)
def test_other_legal_shapes_pass(root: Path, text: str) -> None:
    assert check(root, text)[0] == 0


@pytest.mark.parametrize("name", HEADER_FIELDS)
@pytest.mark.parametrize("empty", [False, True])
def test_every_required_header_field(root: Path, name: str, empty: bool) -> None:
    line = next(x for x in GOOD.splitlines() if x.startswith(f"**{name}:**"))
    code, output = check(
        root, GOOD.replace(line + "\n", f"**{name}:**\n" if empty else "")
    )
    assert code == 1
    assert f"header: **{name}:** is missing or empty" in output, output


LATE_ROW = "| 9 | Late? | x | agent: late |  | settled |\n"


@pytest.mark.parametrize("gap", ["\n", "\n```note```\n\n", "```note```\n"])
def test_rows_past_the_table_end_are_not_silently_skipped(root: Path, gap: str) -> None:
    text = GOOD + gap + LATE_ROW
    line = text.count("\n")
    code, output = check(root, text)
    assert code == 1
    assert f"record.md:{line}: table: a row after the table ended at" in output, output


def test_prototype_report_outside_the_root_only_needs_to_exist(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    report = tmp_path_factory.mktemp("elsewhere") / "report.md"
    report.write_text("# Report\n")
    assert check(root, GOOD.replace("reports/bench.md", str(report)))[0] == 0
    report.unlink()
    code, output = check(root, GOOD.replace("reports/bench.md", str(report)))
    assert code == 1 and "prototype: " in output, output


def test_computed_output_outside_the_root_only_needs_to_exist(
    root: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    output = tmp_path_factory.mktemp("elsewhere") / "count.txt"
    output.write_text("3\n")
    assert check(root, GOOD.replace("reports/count.txt", str(output)))[0] == 0
    output.unlink()
    code, out = check(root, GOOD.replace("reports/count.txt", str(output)))
    assert code == 1 and "computed: output " in out, out


def test_a_record_needs_the_title_first(root: Path) -> None:
    assert check(root, COMMENTED_NOTES)[0] == 3
    assert check(root, "\n" + GOOD)[0] == 0


@pytest.mark.parametrize("old,new,rule", FAULTS)
def test_one_fault_is_named_with_rule_and_line(
    root: Path, old: str, new: str, rule: str
) -> None:
    assert old in GOOD
    text = GOOD.replace(old, new, 1)
    line = r"\d+"
    if new and "\n" not in new:
        line = str(text[: text.index(new)].count("\n") + 1)
    code, output = check(root, text)
    assert code == 1
    assert re.search(rf"record\.md:{line}: {rule}: ", output), output


def test_not_a_record_and_unreadable(root: Path) -> None:
    assert check(root, "# Notes\nNo table.\n")[0] == 3
    assert run(root / "absent.md", "--root", root)[0] == 2


def test_filled_template_passes(root: Path) -> None:
    fill = {
        "<the question this run settles>": "How should run state be stored?",
        "<area>": "general",
        "<topic>": "run-state",
        "<YYYY-MM-DD>": "2026-11-11",
        "<run id>": "s1-a",
        "<caller>": "user",
        "<outcome>": "JSONL settled.",
        "<question>": "Format?",
        "<answer>": "JSONL",
        "<source>": "code: src/store.py:2",
        "<confidence>": "high",
        "<status>": "established",
    }
    text = TEMPLATE.read_text()
    assert check(root, text)[0] == 1
    for old, new in fill.items():
        assert old in text, old
        text = text.replace(old, new)
    assert check(root, text) == (0, f"{root / 'record.md'}: 1 rows, 0 problems\n")


# Filing (plan 20 section 5 rule 5): a new run never replaces an earlier run's record.


def record_for(run_id: str) -> str:
    return GOOD.replace("**Run:** s1-a", f"**Run:** {run_id}")


def next_path(path: Path, run_id: str) -> Path:
    code, output = run("--next", path, "--run", run_id)
    assert code == 0, output
    return Path(output.strip())


@pytest.mark.parametrize("area", ["skill-curation", "general"])
def test_free_default_path_is_used_as_is(tmp_path: Path, area: str) -> None:
    path = tmp_path / f"docs/discovery/{area}/run-state/2026-11-11-store.md"
    assert next_path(path, "s1-a") == path


def test_two_runs_in_one_session_and_bead_file_beside(tmp_path: Path) -> None:
    path = tmp_path / "2026-11-11-store.md"
    path.write_text(record_for("s1-a"))
    assert next_path(path, "s1-a") == path
    second = tmp_path / "2026-11-11-store-2.md"
    assert next_path(path, "s1-b") == second
    second.write_text(record_for("s1-b"))
    assert next_path(path, "s1-b") == second
    assert next_path(path, "s2-c") == tmp_path / "2026-11-11-store-3.md"


def test_caller_path_held_by_a_non_record_is_not_replaced(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("# Someone's notes\n")
    assert next_path(path, "s1-a") == tmp_path / "notes-2.md"


def test_commented_example_and_dangling_link_are_occupied(tmp_path: Path) -> None:
    notes = tmp_path / "notes.md"
    notes.write_text(COMMENTED_NOTES)
    assert next_path(notes, "s1-a") == tmp_path / "notes-2.md"
    dangling = tmp_path / "dangling.md"
    dangling.symlink_to(tmp_path / "absent.md")
    assert next_path(dangling, "s1-c") == tmp_path / "dangling-2.md"


def test_index_lists_records_by_date_and_follows_a_move(tmp_path: Path) -> None:
    base = tmp_path / "docs/discovery"
    late = base / "general/run-state/2026-11-12-store.md"
    early = base / "skill-curation/naming/2026-11-10-name.md"
    for path, text in (
        (late, record_for("s1-a").replace("2026-11-11", "2026-11-12")),
        (early, record_for("s2-b").replace("2026-11-11", "2026-11-10")),
    ):
        path.parent.mkdir(parents=True)
        path.write_text(text)
    (base / "general/README.md").write_text("# Not a record\n")
    (base / "general/example.md").write_text(COMMENTED_NOTES)
    assert run("--index", base)[0] == 0
    index = (base / "INDEX.md").read_text()
    lines = [line for line in index.splitlines() if line.startswith("- ")]
    assert len(lines) == 2
    assert (
        "2026-11-10" in lines[0]
        and "skill-curation/naming/2026-11-10-name.md" in lines[0]
    )
    assert "How should run state be stored?" in lines[1] and "JSONL settled" in lines[1]
    moved = base / "general/storage/2026-11-12-store.md"
    moved.parent.mkdir()
    late.rename(moved)
    assert run("--index", base)[0] == 0
    index = (base / "INDEX.md").read_text()
    assert "general/storage/2026-11-12-store.md" in index
    assert "general/run-state" not in index


def test_index_of_a_root_not_yet_created_writes_an_empty_index(tmp_path: Path) -> None:
    base = tmp_path / "docs/discovery"
    assert run("--index", base)[0] == 0
    assert not (base / "INDEX.md").read_text().endswith("\n\n")
