#!/usr/bin/env python3
"""Check a discovery record's structure and bounded citations, never whether an answer is right.

Usage:
  check_record.py <record.md> [--root R]   check one record
  check_record.py --next <path> --run <id> print the path this run writes to
  check_record.py --index <root>           rewrite <root>/INDEX.md from every record under it
Check exit 0: holds. 1: problems, each `<path>:<line>: <rule>: <problem>`. 2: cannot read.
3: not a record, unchecked: the first non-blank line is not `# Discovery record`, or no
`| # | Question | Answer | Source | Confidence | Status |` table follows the header fields.
`--root` (default: the record's Git top level): `code:` paths must lie under it; a relative
`prototype:` report is read from it, and any `prototype:` report need only exist.
`computed: <script> -> <output>` resolves both paths the same way; each need only exist.
The table ends at its first non-row line; any later line starting with `|` is a problem,
whatever surrounds it. Fences and comments are not read: nothing can hide a row.
"""

import argparse
import datetime
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

TITLE = "# Discovery record"
TABLE = ["#", "Question", "Answer", "Source", "Confidence", "Status"]
HEADER = ["Question", "Area", "Topic", "Date", "Run", "Caller", "Outcome"]
FIELD = re.compile(r"\*\*(\w+):\*\*(.*)")
STATUSES = {"decided", "established", "routine", "proposed", "open"}
CONFIDENCE = {"high", "medium", "low"}
KINDS = {"code", "outside", "prototype", "computed", "agent", "owner"}
CELL = re.compile(r"(?<!\\)\|")
SEPARATOR = re.compile(r":?-+:?")
OWNER = re.compile(r'owner: (?:"[^"]+" \((\d{4}-\d{2}-\d{2})\)|delegation \S.*)')
CODE = re.compile(r"code: (\S.*):(\d+)(?:-(\d+))?")
COMPUTED = re.compile(r"computed: (\S.*?) -> (\S.*)")
INDEX = "INDEX.md"

Say = Callable[[str, str], None]
Problem = tuple[int, str, str]
Fields = dict[str, tuple[int, str]]
Row = tuple[int, list[str]]


class Record(NamedTuple):
    fields: Fields
    rows: list[Row]
    problems: list[Problem]


def is_date(text: str) -> bool:
    try:
        datetime.date.fromisoformat(text)
    except ValueError:
        return False
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", text))


def read(lines: list[str]) -> Record | None:
    """Header fields, table rows and table-shape problems; None when not a record."""
    fields: Fields = {}
    rows: list[Row] = []
    problems: list[Problem] = []
    start = end = 0
    separated = False
    if next((text.strip() for text in lines if text.strip()), "") != TITLE:
        return None
    for number, text in enumerate(lines, 1):
        row = cells(text)
        if not start:
            if found := FIELD.fullmatch(text.strip()):
                fields.setdefault(found[1], (number, found[2].strip()))
            elif row == TABLE:
                start = number
            elif row is not None:
                problems.append((number, "table", "a row before the table header"))
        elif end:
            if row is not None:
                problems.append(
                    (number, "table", f"a row after the table ended at {end}")
                )
        elif row is None:
            end = number
        elif number == start + 1 and is_separator(row):
            separated = True
        else:
            rows.append((number, row))
    if not start:
        return None
    if not separated:
        problems.append(
            (start + 1, "table", "needs the |---| separator under the header")
        )
    return Record(fields, rows, problems)


def is_separator(row: list[str]) -> bool:
    return len(row) == len(TABLE) and all(SEPARATOR.fullmatch(cell) for cell in row)


def cells(text: str) -> list[str] | None:
    """A table line's cells, at most one outer pipe dropped at each end; None if no table line."""
    text = text.strip()
    if not text.startswith("|"):
        return None
    text = text[1:]
    if text.endswith("|") and not text.endswith("\\|"):
        text = text[:-1]
    return [cell.strip().replace("\\|", "|") for cell in CELL.split(text)]


def inside(root: Path, name: str) -> Path | None:
    path = (root / name).resolve()
    return path if path.is_relative_to(root.resolve()) else None


def check_source(root: Path, source: str, say: Say) -> None:
    """The source's form for its kind, then the bounded citation (Dec-6); form only."""
    kind, _, rest = source.partition(":")
    rest = rest.strip()
    if kind == "code":
        found = CODE.fullmatch(source)
        if not found:
            return say("code", "needs code: <path>:<line> or <path>:<first>-<last>")
        path = inside(root, found[1].strip())
        first, last = int(found[2]), int(found[3] or found[2])
        if not path or not path.is_file():
            return say("code", f"{found[1]} is not a file under the root")
        count = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        if not 1 <= first <= last <= count:
            say("code", f"{found[1]} has {count} lines; {found[2]} is out of range")
    elif kind == "outside":
        parts = [part.strip() for part in rest.split(",")]
        if len(parts) != 3 or not all(parts):
            say("outside", "needs outside: <source>, <version>, <date>")
    elif kind == "prototype":
        report = root / rest if rest else None
        if not report or not report.is_file():
            say("prototype", f"report {rest or '(none)'} does not exist")
    elif kind == "computed":
        found = COMPUTED.fullmatch(source)
        if not found:
            return say("computed", "needs computed: <script path> -> <output path>")
        for label, name in (("script", found[1].strip()), ("output", found[2].strip())):
            if not (root / name).is_file():
                say("computed", f"{label} {name} does not exist")
    elif kind == "agent":
        if not rest:
            say("agent", "needs agent: <basis>")
    elif kind == "owner":
        owner = OWNER.fullmatch(source)
        if not owner:
            say(
                "owner",
                'needs owner: "<quote>" (YYYY-MM-DD) or owner: delegation <ref>',
            )
        elif owner[1] and not is_date(owner[1]):
            say("owner", f"{owner[1]} is not an ISO date")


def check_row(
    root: Path, number: int, row: list[str], add: Callable[[int, str, str], None]
) -> None:
    def say(rule: str, problem: str) -> None:
        add(number, rule, problem)

    if len(row) != len(TABLE):
        return say("cells", f"has {len(row)} cells, needs {len(TABLE)}")
    _, _, answer, source, confidence, status = row
    kind = source.split(":", 1)[0] if ":" in source else ""
    if status not in STATUSES:
        return say(
            "status",
            f"{status or '(empty)'} is not one of {', '.join(sorted(STATUSES))}",
        )
    if kind in KINDS:
        check_source(root, source, say)
    elif source or status != "open":
        say("source", "needs code:, outside:, prototype:, computed:, agent: or owner:")
    if not answer and status != "open":
        say("answer", f"a {status} row needs an answer")
    if status == "decided" and kind != "owner":
        say("decided", 'needs owner: "<quote>" (YYYY-MM-DD) or owner: delegation <ref>')
    if status == "established":
        if kind not in {"code", "outside", "prototype", "computed"}:
            say(
                "established", "needs a code:, outside:, prototype: or computed: source"
            )
        if confidence not in CONFIDENCE:
            say("established", "needs Confidence high, medium or low")
    elif confidence:
        say(
            "confidence",
            f"only an established row has a Confidence, not a {status} row",
        )
    if status == "routine" and not re.fullmatch(r"agent: routine, *\S.*", source):
        say("routine", "needs agent: routine, <basis>")
    if status == "proposed" and kind != "agent":
        say("proposed", "needs an agent: source with the recommendation")
    if status == "proposed" and not answer:
        say("proposed", "needs the recommendation as its answer")


def check(lines: list[str], root: Path) -> tuple[list[Problem], int] | None:
    record = read(lines)
    if record is None:
        return None
    fields, rows = record.fields, record.rows
    problems = list(record.problems)

    def say(number: int, rule: str, problem: str) -> None:
        problems.append((number, rule, problem))

    for name in HEADER:
        number, value = fields.get(name, (1, ""))
        if not value:
            say(number, "header", f"**{name}:** is missing or empty")
    number, value = fields.get("Date", (1, ""))
    if value and not is_date(value):
        say(number, "header", f"Date {value} is not YYYY-MM-DD")
    if "Revises" in fields and not fields["Revises"][1]:
        say(fields["Revises"][0], "header", "**Revises:** names no authority")
    for number, row in rows:
        check_row(root, number, row, say)
    return sorted(problems), len(rows)


def load(path: Path) -> list[str]:
    return path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n").split("\n")


def header(path: Path) -> dict[str, str] | None:
    """The record's header fields, or None when the file is absent or not a record."""
    try:
        record = read(load(path))
    except (OSError, UnicodeDecodeError):
        return None
    return {key: value for key, (_, value) in record.fields.items()} if record else None


def next_path(path: Path, run: str) -> Path:
    """Plan 20 section 5 rule 5: free, or this run's own record; else the first free -N beside."""
    for n in range(1, 10_000):
        candidate = path if n == 1 else path.with_name(f"{path.stem}-{n}{path.suffix}")
        taken = candidate.is_symlink() or candidate.exists()
        if not taken or (header(candidate) or {}).get("Run") == run:
            return candidate
    raise SystemExit(f"{path}: no free name")


def write_index(base: Path) -> int:
    entries: list[tuple[str, str, str, str]] = []
    problems: list[str] = []
    base.mkdir(parents=True, exist_ok=True)
    for path in sorted(base.rglob("*.md")):
        if path == base / INDEX:
            continue
        fields = header(path)
        if fields is None:
            continue
        missing = [k for k in ("Date", "Question", "Outcome") if not fields.get(k)]
        if missing:
            problems.append(
                f"{path}:1: header: {', '.join(missing)} missing; not indexed"
            )
            continue
        rel = path.relative_to(base).as_posix()
        entries.append((fields["Date"], rel, fields["Question"], fields["Outcome"]))
    lines = [
        "# Discovery records",
        "",
        "<!-- Generated by check_record.py --index; hand edits are overwritten. -->",
        *([""] if entries else []),
        *(
            f"- {d}: {q} Outcome: {o} ([{rel}]({rel}))"
            for d, rel, q, o in sorted(entries)
        ),
    ]
    (base / INDEX).write_text("\n".join(lines) + "\n", encoding="utf-8")
    for problem in problems:
        print(problem)
    print(f"{base / INDEX}: {len(entries)} records")
    return 1 if problems else 0


def git_root(path: Path) -> Path | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=path.parent if path.parent.is_dir() else Path.cwd(),
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return Path(out.stdout.strip()) if out.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("record", nargs="?", type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--next", type=Path)
    parser.add_argument("--run")
    parser.add_argument("--index", type=Path)
    args = parser.parse_args()
    if args.next:
        if not args.run or args.record or args.index:
            parser.error("--next needs --run and nothing else")
        print(next_path(args.next, args.run))
        return 0
    if args.index:
        if args.record or args.run:
            parser.error("--index takes only its root")
        return write_index(args.index)
    if not args.record:
        parser.error("name a record, --next or --index")
    try:
        lines = load(args.record)
    except (OSError, UnicodeDecodeError) as error:
        print(f"{args.record}: cannot read: {error}", file=sys.stderr)
        return 2
    root = args.root or git_root(args.record)
    if root is None:
        print(
            f"{args.record}: no --root and not inside a Git checkout", file=sys.stderr
        )
        return 2
    result = check(lines, root)
    if result is None:
        print(f"{args.record}: not a discovery record (title or table); unchecked")
        return 3
    problems, count = result
    for number, rule, problem in problems:
        print(f"{args.record}:{number}: {rule}: {problem}")
    print(f"{args.record}: {count} rows, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
