"""The skeleton plan lint, and that what it accepts survives execution's extractor."""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[2] / ".claude/skills/planning/scripts/check_plan.py"
BRIEF = Path(__file__).parents[2] / ".claude/skills/execution/scripts/task-brief.sh"
HEAD = """# Move the store
**Origin:** docs/plans/x.md
**Goal:** Move the store.
**Out of scope:** The CLI.
**Constraints:** Python 3.12.
"""
HOW = """## How to run this
Run with: execution, task scope.
Authority: owner's word.
The coordinator ticks a box only when its evidence exists.
"""
ONE = """## Tasks
### Task 1: Add the schema
Goal: The schema loads.
Stage: cr-1.1
Files: store/schema.py
Approach: Add the table.
Dependencies: None
Evidence:
- [ ] Check: `pytest a`. Pass when it exits 0.
- Live: n/a: nothing runs.
- Measure: n/a: no number moves.
"""
TWO = """### Task 2: Move the rows
Goal: The rows move.
Stage: cr-1.2
Files: store/move.py
Approach: Copy them.
Dependencies: 1
Blocked by: Q1
Evidence:
- [ ] Check: `pytest b`. Pass when it exits 0.
- [ ] Live: Run the sample. Pass when it prints ok.
- [ ] Measure: `load` over 1000 rows. Pass when under 2 s.
"""
TAIL = """## Open questions
Q1. Which index?
## Appendix A. Settled questions
None.
## Appendix B. Alternatives rejected
None.
"""
GOOD = HEAD + HOW + ONE + TWO + TAIL
FIELDS = ("Goal:", "Files:", "Approach:", "Dependencies:", "Evidence:", "- [ ] Check:")
VALUES = {
    1: ("The schema loads.", "store/schema.py", "Add the table.", "`pytest a`"),
    2: ("The rows move.", "store/move.py", "Copy them.", "`pytest b`"),
}
SEPARATORS = [
    c for c in map(chr, range(0x10000)) if c != "\n" and len(f"a{c}b".splitlines()) == 2
]
PHASE = "execution, phase scope."
NOTES = "#### Implementation notes\n"
FAULTS = [
    ("Approach: Add the table.", "TBD", "placeholder"),
    ("Approach: Add the table.", "Approach: Add <thing>.", "placeholder"),
    ("Approach: Add the table.", "Approach: handle edge cases", "placeholder"),
    ("- [ ] Check: `pytest a`. Pass when it exits 0.\n", "", "needs a Check box"),
    ("- [ ] Check: `pytest a`.", "- [ ] Check: pytest a.", "no command"),
    ("`pytest a`. Pass when it exits 0.", "`pytest a`.", "no Pass when"),
    ("- Live: n/a: nothing runs.\n", "", "Live needs"),
    ("- Live: n/a: nothing runs.", "- Live: n/a:", "no reason"),
    ("- Measure: n/a: no number moves.\n", "- Live: n/a: x\n", "Measure needs"),
    ("over 1000 rows. Pass when under 2 s.", "rows. Pass when quick.", "no number"),
    ("Pass when it prints ok.", "", "no Pass"),
    ("### Task 2:", "### Task 1:", "numbered 1 to n"),
    ("Dependencies: None", "Dependencies: 1", "itself"),
    ("Dependencies: None", "Dependencies: 2", "cycle"),
    ("Dependencies: None", "Dependencies: 7", "unknown"),
    ("Dependencies: None", "Dependencies: soon", "must be None"),
    ("Blocked by: Q1", "Blocked by: Q9", "no open question"),
    ("Blocked by: Q1", "Blocked by: none", "no open question"),
    ("Blocked by: Q1\n", "", "holds no task"),
    ("execution, task scope.", PHASE + "\nRun with: " + PHASE, "one line"),
    ("execution, task scope.", "execution, everything.", "one line"),
    ("Authority: owner's word.", "Authority:", "Authority"),
    ("The coordinator ticks", "Someone ticks", "lacks the sentence"),
    ("Dependencies: None\n", "Dependencies: None\n" + NOTES, "heading inside"),
    ("Files: store/schema.py", "Files: a\nFiles: b", "duplicate field"),
    ("Files: store/schema.py\n", "", "Files is missing"),
    ("Goal: The schema loads.", "Goal:", "Goal is missing"),
    ("Approach: Add the table.", "Verification: x\nApproach: y", "Verification"),
    ("## Open questions", "### Task 3: Late\n## Open questions", "Evidence is missing"),
    ("None.\n## Appendix B", "### Task 3: Late\n## Appendix B", "outside ## Tasks"),
    ("None.\n## Appendix B", "None.\n## Tasks\nx\n## Appendix B", "out of order"),
    ("## Appendix B. Alternatives rejected\nNone.\n", "", "Appendix B"),
    ("Settled questions\nNone.", "Settled questions", "is empty"),
    ("## Open questions", "## Notes\nx\n## Open questions", "not part of"),
    ("# Move the store\n", "", "one H1"),
    ("**Goal:** Move the store.", "**Goal:**", "field Goal"),
    ("**Origin:** docs/plans/x.md\n", "", "field Origin"),
    ("Stage: cr-1.1\n", "```\nunclosed\n", "never closes"),
]


def lint(path):
    run = subprocess.run(
        [sys.executable, SCRIPT, *path], capture_output=True, text=True, check=False
    )
    return run.returncode, run.stdout + run.stderr


def write(tmp_path, text):
    plan = tmp_path / "plan.md"
    plan.write_bytes(text.encode())
    return [str(plan)]


def fenced(mark):
    return GOOD.replace(
        "Files: store/schema.py\n", f"Files: store/schema.py\n{mark}\n# c\n{mark}\n"
    )


@pytest.mark.parametrize(
    "text",
    [GOOD, fenced("```"), fenced("~~~"), GOOD.replace("\n", "\r\n"), "\ufeff" + GOOD],
)
def test_accepted_plan_survives_the_extractor(tmp_path, text):
    plan = write(tmp_path, text)[0]
    assert lint([plan]) == (0, "2 tasks, 0 problems\n")
    for number, other in ((1, 2), (2, 1)):
        subprocess.run(["bash", BRIEF, plan, str(number), tmp_path], check=True)
        brief = (tmp_path / f"task-{number}-brief.md").read_text()
        assert all(field in brief for field in FIELDS)
        assert all(value in brief for value in VALUES[number])
        assert not any(value in brief for value in VALUES[other])


@pytest.mark.parametrize("old,new,message", FAULTS)
def test_one_fault_is_named(tmp_path, old, new, message):
    assert old in GOOD
    code, output = lint(write(tmp_path, GOOD.replace(old, new, 1)))
    assert code == 1 and message in output


def test_phase_scope_needs_a_stage(tmp_path):
    text = GOOD.replace("execution, task scope.", PHASE)
    assert lint(write(tmp_path, text))[0] == 0
    code, output = lint(write(tmp_path, text.replace("Stage: cr-1.1\n", "")))
    assert code == 1 and "needs Stage" in output


def test_duplicate_fixed_section_and_no_tasks(tmp_path):
    code, output = lint(write(tmp_path, GOOD.replace(TAIL, TAIL + "## Tasks\nx\n")))
    assert code == 1 and "duplicated" in output
    code, output = lint(write(tmp_path, HEAD + HOW + "## Tasks\nx\n" + TAIL))
    assert code == 1 and "numbered 1 to n" in output
    code, output = lint(write(tmp_path, HEAD + HOW + TAIL))
    assert code == 1 and 'no "## Tasks"' in output


@pytest.mark.parametrize(
    "text",
    [
        GOOD.replace(
            "Files: store/schema.py\n",
            "Files: a\n```\n### Task 7: x\n- [ ] Check: y\n```\n",
        ),
        GOOD.replace("\n", "\r\n"),
        "\ufeff" + GOOD,
        GOOD.replace("Add the table", "Add `<T>`"),
    ],
)
def test_hostile_text_reads_normally(tmp_path, text):
    assert lint(write(tmp_path, text))[0] == 0


@pytest.mark.parametrize("separator", SEPARATORS)
def test_stray_separator_is_named_with_its_line(tmp_path, separator):
    text = GOOD.replace("\n### Task 2:", f"{separator}### Task 2:")
    line = GOOD[: GOOD.index("### Task 2:")].count("\n")
    code, output = lint(write(tmp_path, text))
    assert code == 1 and f":{line}: line separator" in output


def test_cr_only_plan_is_a_problem_and_not_exit_3(tmp_path):
    code, output = lint(write(tmp_path, GOOD.replace("\n", "\r")))
    assert code == 1 and ":1: line separator" in output


def test_indented_fence_hides_nothing(tmp_path):
    text = GOOD.replace(
        "Files: store/schema.py\n", "Files: a\n  ```\n# comment\n  ```\n"
    )
    assert "heading inside" in lint(write(tmp_path, text))[1]


def test_unreadable_is_two_and_not_a_skeleton_is_three(tmp_path):
    assert (
        lint([])[0] == lint([str(tmp_path)])[0] == lint([str(tmp_path / "no")])[0] == 2
    )
    bad = tmp_path / "bad.md"
    bad.write_bytes(b"\xff\xfe")
    assert lint([str(bad)])[0] == 2
    no_how = GOOD.replace(HOW, "")
    hidden = GOOD.replace(HOW, "```\n" + HOW + "```\n")
    for text in ("", no_how, hidden, "# P\n### Task 1: x\nGoal: y\n"):
        assert lint(write(tmp_path, text))[0] == 3
