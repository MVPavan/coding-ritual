#!/usr/bin/env python3
"""Check a skeleton plan's structure, never its substance. Reads only the named file.

Usage: check_plan.py <plan.md>
Exit 0: holds. 1: problems, each `<path>:<line>: <problem>`. 2: cannot read.
3: no `## How to run this`: not a skeleton plan, nothing checked, not a pass.
Fences and headings are read as execution's task-brief.sh reads them.
"""

import graphlib
import re
import sys
from collections import Counter
from pathlib import Path

HEADING, SECTION = re.compile(r"#+[ \t]"), re.compile(r"##[ \t]+(.*)")
TASK = re.compile(r"### Task ([1-9][0-9]*): \S")
ANY_TASK = re.compile(r"#+[ \t]+Task[ \t]+[0-9]+:")
FIELD = re.compile(
    r"(Goal|Stage|Files|Interfaces|Approach|Verification|Test seams|Dependencies"
    r"|Risks|Blocked by|Evidence):(.*)"
)
BOX = re.compile(r"- \[[ xX]\] (Check|Live|Measure):(.*)")
NOT_APPLICABLE = re.compile(r"- (Live|Measure): n/a:(.*)")
CODE = re.compile(r"`[^`]+`")
PLACEHOLDER = re.compile(
    r"\bTBD\b|\bTODO\b|<(?!http)[^<>\s][^<>]*>|(?i:implement later|fill in details"
    r"|add appropriate error handling|add validation|handle edge cases"
    r"|write tests for the above|similar to task \d)"
)
STRAY = re.compile("[\r\v\f\x1c\x1d\x1e\x85\u2028\u2029]")
RUN = re.compile(r"Run with: execution, (task|phase|workstream) scope\.")
TICK = "The coordinator ticks a box only when its evidence exists."
ORDER = ["How to run this", "Tasks", "Open questions", "Appendix A", "Appendix B"]
HEADER = ["Origin", "Goal", "Out of scope", "Constraints"]
REQUIRED = ["Goal", "Files", "Approach", "Dependencies", "Evidence"]


def read_tasks(body, say):
    tasks, field = [], None
    for number, text in body:
        found = FIELD.fullmatch(text.rstrip())
        if heading := TASK.match(text):
            tasks.append({"id": int(heading[1]), "line": number, "fields": {}})
            field = None
        elif HEADING.match(text):
            say(number, "heading inside a task: task-brief.sh ends the task here")
        elif tasks and found:
            if found[1] in tasks[-1]["fields"]:
                say(number, f"duplicate field {found[1]}")
            field = (number, found[2].strip(), [])
            tasks[-1]["fields"][found[1]] = field
        elif field:
            field[2].append((number, text))
    return tasks


def check_evidence(name, line, rows, say):
    found = Counter()
    for number, text in rows:
        if row := NOT_APPLICABLE.fullmatch(text):
            found[row[1], "n/a"] += 1
            if not row[2].strip():
                say(number, f"task {name}: {row[1]} n/a gives no reason")
        elif row := BOX.fullmatch(text):
            found[row[1], "box"] += 1
            words = CODE.sub("", row[2])
            if not re.search(r"Pass when\s+\S", words):
                say(number, f"task {name}: {row[1]} box has no Pass when")
            if row[1] != "Live" and not CODE.search(row[2]):
                say(number, f"task {name}: {row[1]} box has no command in backticks")
            if row[1] == "Measure" and not re.search(r"\d", words):
                say(number, f"task {name}: Measure box has no number")
    if not found["Check", "box"]:
        say(line, f"task {name}: needs a Check box")
    for kind in ("Live", "Measure"):
        if bool(found[kind, "box"]) == bool(found[kind, "n/a"]):
            say(line, f"task {name}: {kind} needs a box or an n/a, not both or neither")


def check_tasks(tasks, scope, questions, say):
    ids = [task["id"] for task in tasks]
    if not ids or ids != list(range(1, len(ids) + 1)):
        say(tasks[0]["line"] if ids else 1, f"tasks must be numbered 1 to n: {ids}")
    graph, named = {}, set()
    for task in tasks:
        name, start, fields = task["id"], task["line"], task["fields"]
        for field in REQUIRED:
            row = fields.get(field)
            if not row or not (row[1] or any(text.strip() for _, text in row[2])):
                say(start, f"task {name}: {field} is missing or empty")
        if "Verification" in fields:
            say(
                fields["Verification"][0],
                f"task {name}: Evidence replaces Verification",
            )
        stage = fields.get("Stage", (0, ""))[1]
        if scope == "phase" and not re.fullmatch(r"\S+\.\d+", stage):
            say(start, f"task {name}: phase scope needs Stage: <epic>.N")
        line, depends, _ = fields.get("Dependencies", (start, "None", []))
        if not re.fullmatch(r"None|\d+(, *\d+)*", depends):
            say(line, f"task {name}: Dependencies must be None or task numbers")
        graph[name] = {int(other) for other in re.findall(r"\d+", depends)}
        if graph[name] - set(ids):
            say(line, f"task {name}: depends on unknown {graph[name] - set(ids)}")
        if name in graph[name]:
            say(line, f"task {name}: depends on itself")
        graph[name].discard(name)
        if "Blocked by" in fields:
            line, value, _ = fields["Blocked by"]
            names = set(re.findall(r"Q\d+", value))
            named |= names
            if not names or names - questions:
                say(line, f"task {name}: Blocked by names no open question: {value}")
        row = fields.get("Evidence", (start, "", []))
        check_evidence(name, row[0], row[2], say)
    try:
        graphlib.TopologicalSorter(graph).prepare()
    except graphlib.CycleError as error:
        say(tasks[0]["line"], f"dependency cycle: {error.args[1]}")
    return named


def check(lines):
    message = "line separator other than LF or CRLF: task-brief.sh splits on LF only"
    stray = [(n, message) for n, text in enumerate(lines, 1) if STRAY.search(text)]
    if stray:
        return stray, 0
    problems, rows, opened, sections, body = [], [], 0, {}, []
    say = lambda number, message: problems.append((number, message))
    ranks = []
    front = body
    for number, text in enumerate(lines, 1):
        if text.startswith(("```", "~~~")):
            opened = 0 if opened else number
        elif not opened:
            rows.append((number, text))
            if section := SECTION.fullmatch(text):
                key, body = section[1].split(".")[0].strip(), []
                sections.setdefault(key, (number, body))
                ranks.append(ORDER.index(key) if key in ORDER else 5)
                if key not in ORDER and not key.startswith("Appendix "):
                    say(number, f'section "{key}" is not part of the skeleton')
            else:
                body.append((number, text))
    if "How to run this" not in sections:
        return None, 0
    if opened:
        say(opened, "fence never closes, which hides what follows")
    fixed = [rank for rank in ranks if rank < 5]
    if ranks != sorted(ranks) or len(fixed) != len(set(fixed)):
        say(1, "fixed sections are duplicated or out of order")
    for key in ORDER:
        where = sections.get(key)
        if key != "Open questions" and not where:
            say(1, f'no "## {key}" section')
        elif where and not any(text.strip() for _, text in where[1]):
            say(where[0], f'section "{key}" is empty; an appendix may say None')
    if sum(bool(re.match(r"#[ \t]", text)) for _, text in rows) != 1:
        say(1, "needs exactly one H1 title")
    for name in HEADER:
        if not any(re.match(rf"\*\*{name}:\*\*\s*\S", text) for _, text in front):
            say(1, f"header field {name} is missing or empty")
    start, how = sections["How to run this"]
    runs = [text for _, text in how if text.startswith("Run with:")]
    scope = RUN.fullmatch(runs[0].rstrip()) if len(runs) == 1 else None
    if not scope:
        say(start, "needs one line: Run with: execution, <scope> scope.")
    if not any(re.match(r"Authority:\s*\S", text) for _, text in how):
        say(start, "needs a non-empty Authority: line")
    if TICK not in " ".join(text for _, text in how):
        say(start, f'lacks the sentence "{TICK}"')
    task_rows = sections.get("Tasks", (1, []))[1]
    tasks = read_tasks(task_rows, say)
    start, open_rows = sections.get("Open questions", (1, []))
    questions = {f"Q{m[1]}" for _, t in open_rows if (m := re.match(r"Q(\d+)\. ", t))}
    named = check_tasks(tasks, scope and scope[1], questions, say)
    for question in sorted(questions - named):
        say(start, f"{question} holds no task; name it in a Blocked by")
    for number, text in rows:
        if ANY_TASK.match(text) and (number, text) not in task_rows:
            say(number, "a task heading outside ## Tasks")
        if PLACEHOLDER.search(CODE.sub("", text)):
            say(number, "placeholder text")
    return sorted(set(problems)), len(tasks)


def main():
    if len(sys.argv) != 2:
        print("usage: check_plan.py <plan.md>", file=sys.stderr)
        return 2
    try:
        text = Path(sys.argv[1]).read_bytes().decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        print(f"{sys.argv[1]}: cannot read: {error}", file=sys.stderr)
        return 2
    problems, count = check(text.replace("\r\n", "\n").split("\n"))
    if problems is None:
        print(f'{sys.argv[1]}: not a skeleton plan, no "## How to run this"; unchecked')
        return 3
    for number, message in problems:
        print(f"{sys.argv[1]}:{number}: {message}")
    print(f"{count} tasks, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
