"""Site selection and single-site editing for `scripts/checks/mutate.sh`.

Three subcommands, because the shell owns the expensive half (copy, baseline,
pytest) and this owns the steps a shell cannot do honestly:

- `sites BASE` reads the lines this round ADDED under `workflow_interpreter/`
  and picks at most `SITE_LIMIT` of them to mutate, one mutation per line.
- `apply SITES INDEX TREE` performs exactly one of those mutations in a copy of
  the tree and prints the human-readable description of what it did.
- `changed BASE` counts the EXECUTABLE lines those same files gained, so the
  shell can tell "this round added no code here" (a pass) from "this round
  added code the operator set could not touch" (a failure: zero mutants graded
  nothing). Comments, blank lines, docstrings and imports are not code a
  mutation can bite, and failing a round for them would fail it identically on
  every re-entry of the region.

Candidate operators are found with `tokenize`, not with a regular expression:
`<` inside a string literal or a comment is not code, and mutating it would
produce a mutant that CANNOT be killed — a survivor that says nothing about the
tests. Tokenizing also makes `<` and `<=` distinct tokens, so the two never
shadow each other.

stdlib only, and outside the `workflow_interpreter` package on purpose: it is
run by a §7.3 check in a throwaway copy of the tree under test, where the only
thing that can be assumed is the interpreter `uv run` provides.
"""

from __future__ import annotations

import argparse
import io
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Final

SITE_LIMIT: Final[int] = 8
"""How many mutants one run plants at most.

Each costs a full copy of the tree plus a unit-suite run, and the check has a
wall-clock timeout it shares with everything else the node declares."""

SOURCE_PREFIX: Final[str] = "workflow_interpreter/"
"""The only subtree whose changed lines are mutated: the product code."""

PYTHON_SUFFIX: Final[str] = ".py"
DIFF_DST_PREFIX: Final[str] = "b/"
"""What `--dst-prefix` pins the `+++` header to, whatever `diff.noprefix` says."""
DEV_NULL: Final[str] = "/dev/null"
"""The `+++` target of a DELETED file: nothing to mutate, and not a parse error."""
GIT_TIMEOUT_S: Final[float] = 120.0
ENCODING: Final[str] = "utf-8"
FIELD_SEPARATOR: Final[str] = "\t"
REMOVED: Final[str] = "(removed)"
"""How an empty replacement (`not` deletion) reads in a description."""

MUTATION_BY_TOKEN: Final[dict[str, str]] = {
    "==": "!=",
    "!=": "==",
    "<": "<=",
    "<=": "<",
    ">": ">=",
    ">=": ">",
    "and": "or",
    "or": "and",
    "True": "False",
    "False": "True",
    "not": "",
}
"""The fixed operator set (phase 7, C5 step 3).

Keyed by the exact token text, so no ordering or word-boundary rule is needed:
`tokenize` already decided where each operator starts and ends."""

EMPTY_TUPLE: Final[str] = "()"
"""What a single-line assignment's right-hand side becomes (cr-o85.34.25).

The D5 round rewrote three modules entirely in lines like
`deviations = decision.deviations` — no comparison, no boolean, no `not` — and
the operator table above found NOTHING to mutate in any of them. Emptying the
value a round assigns is the cheapest mutation that bites that shape."""

IMPORT_KEYWORDS: Final[frozenset[str]] = frozenset({"import", "from"})
"""A statement starting with either binds names; there is nothing to mutate."""

_NON_CODE_TOKEN_TYPES: Final[tuple[int, ...]] = (
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.NEWLINE,
    tokenize.INDENT,
    tokenize.DEDENT,
    tokenize.ENCODING,
    tokenize.ENDMARKER,
)
"""Layout, not code: none of these makes the line it sits on executable."""

ASSIGN: Final[str] = "="
OPEN_BRACKETS: Final[str] = "([{"
CLOSE_BRACKETS: Final[str] = ")]}"
_SKIPPED_TOKEN_TYPES: Final[tuple[int, ...]] = (
    tokenize.COMMENT,
    tokenize.NL,
    tokenize.INDENT,
    tokenize.DEDENT,
)
"""Not part of a logical line's code: a comment must not extend a mutated span."""

_MSG_NO_SITE: Final[str] = "site index {index} is out of range ({total} site(s))"
_MSG_UNREADABLE_HEADER: Final[str] = (
    "cannot read the diff header {header!r}: this checkout's git produced a "
    "shape the site picker does not parse, and silently finding no site would "
    "report a mutation pass that never planted a mutant"
)
_MSG_DRIFTED: Final[str] = (
    "{path}:{line} no longer reads {token!r} at column {col}; the tree the "
    "mutation was selected from is not the tree it is being applied to"
)

_SITES_HELP: Final[str] = "print the mutation sites of BASE..HEAD as TSV"
_APPLY_HELP: Final[str] = "apply one site of a TSV to a copy of the tree"
_CHANGED_HELP: Final[str] = "count the executable Python lines BASE..HEAD added"


@dataclass(frozen=True)
class Site:
    """One mutable source span: where it is and what it becomes.

    Usually a single operator token; for the assignment operator it is the
    whole right-hand side, which `apply_site` matches by exact text."""

    path: str
    line: int
    col: int
    token: str
    replacement: str

    def to_row(self) -> str:
        """The TSV row the shell passes back to `apply`."""
        fields = (
            self.path,
            str(self.line),
            str(self.col),
            self.token,
            self.replacement,
        )
        return FIELD_SEPARATOR.join(fields)

    @classmethod
    def from_row(cls, row: str) -> Site:
        """Parse one TSV row written by `to_row`."""
        path, line, col, token, replacement = row.split(FIELD_SEPARATOR)
        return cls(
            path=path,
            line=int(line),
            col=int(col),
            token=token,
            replacement=replacement,
        )

    def describe(self) -> str:
        """One line naming the site and the mutation, for stdout and the log."""
        becomes = self.replacement or REMOVED
        return f"{self.path}:{self.line} {self.token} -> {becomes}"


def changed_lines(base: str, root: Path) -> dict[str, list[int]]:
    """The line numbers this round ADDED under `SOURCE_PREFIX`, per file.

    `-U0` so a hunk header names exactly the added lines and no context: an
    unchanged line the round merely moved past is not this round's risk.

    The diff is asked for in ONE shape, whatever the checkout's git config says:
    `diff.noprefix=true` drops the `b/` this parser reads, `diff.external` hands
    the whole thing to a third-party program, and either one would yield zero
    sites and a silent PASS — a mutation check that grades nothing while
    reporting green. A header this parser cannot read is therefore an error, not
    an empty result.
    """
    diff = subprocess.run(
        [
            "git",
            "-c",
            "diff.noprefix=false",
            "diff",
            "--no-ext-diff",
            "--src-prefix=a/",
            "--dst-prefix=b/",
            "-U0",
            base,
            "HEAD",
            "--",
            SOURCE_PREFIX.rstrip("/"),
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=GIT_TIMEOUT_S,
    ).stdout
    added: dict[str, list[int]] = {}
    current: list[int] | None = None
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            target = raw[len("+++ ") :].strip()
            current = None
            if target == DEV_NULL:
                continue
            if not target.startswith(DIFF_DST_PREFIX):
                raise SystemExit(_MSG_UNREADABLE_HEADER.format(header=raw))
            if target.endswith(PYTHON_SUFFIX):
                current = added.setdefault(target[len(DIFF_DST_PREFIX) :], [])
        elif raw.startswith("@@") and current is not None:
            start, count = _hunk_range(raw)
            current.extend(range(start, start + count))
    return {path: lines for path, lines in added.items() if lines}


def _hunk_range(header: str) -> tuple[int, int]:
    """The `+start,count` of a unified hunk header, `count` defaulting to 1."""
    plus = header.split("+", 1)[1].split(" ", 1)[0]
    if "," in plus:
        start, count = plus.split(",", 1)
        return int(start), int(count)
    return int(plus), 1


def _operator_mutations(
    tokens: list[tokenize.TokenInfo],
) -> dict[int, tuple[int, str, str]]:
    """The FIRST mutable operator token of every line, by line number."""
    first: dict[int, tuple[int, str, str]] = {}
    for token in tokens:
        if token.type not in (tokenize.OP, tokenize.NAME):
            continue
        if token.string not in MUTATION_BY_TOKEN:
            continue
        line = token.start[0]
        if line not in first:
            first[line] = (
                token.start[1],
                token.string,
                MUTATION_BY_TOKEN[token.string],
            )
    return first


def _assignment_mutations(
    tokens: list[tokenize.TokenInfo], source_lines: list[str]
) -> dict[int, tuple[int, str, str]]:
    """The right-hand side of every assignment that fits on ONE line -> `()`.

    Only depth-zero `=` counts, so a keyword argument or a default is not an
    assignment, and only a logical line that starts and ends on the same
    physical line is offered: a span the diff reports as one added line is the
    only span `apply_site` can rewrite by column.
    """
    found: dict[int, tuple[int, str, str]] = {}
    depth = 0
    start_row: int | None = None
    equals: tuple[int, int] | None = None
    code_end: tuple[int, int] | None = None
    for token in tokens:
        if token.type in _SKIPPED_TOKEN_TYPES:
            continue
        if token.type == tokenize.NEWLINE:
            if equals is not None and code_end is not None and start_row == equals[0]:
                _add_assignment(found, source_lines, equals, code_end)
            depth, start_row, equals, code_end = 0, None, None, None
            continue
        if start_row is None:
            start_row = token.start[0]
        if token.type == tokenize.OP:
            if token.string in OPEN_BRACKETS:
                depth += 1
            elif token.string in CLOSE_BRACKETS:
                depth -= 1
            elif token.string == ASSIGN and depth == 0 and equals is None:
                equals = token.end
        code_end = token.end
    return found


def _add_assignment(
    found: dict[int, tuple[int, str, str]],
    source_lines: list[str],
    equals: tuple[int, int],
    code_end: tuple[int, int],
) -> None:
    """Record one right-hand side, unless mutating it would say nothing.

    A tab would split the TSV row the shell hands back, and a value that is
    ALREADY `()` would plant a mutant identical to the original — an
    unkillable survivor reported as a hole in tests that do not have one.
    """
    row, end_column = code_end
    if row != equals[0]:
        return
    span = source_lines[row - 1][equals[1] : end_column]
    column = equals[1] + len(span) - len(span.lstrip())
    text = span.strip()
    if not text or text == EMPTY_TUPLE or FIELD_SEPARATOR in text:
        return
    found[row] = (column, text, EMPTY_TUPLE)


def _line_mutations(path: Path) -> dict[int, tuple[int, str, str]]:
    """One candidate mutation per line of `path`: column, source span, result.

    Operators come first and the assignment operator only fills lines they left
    empty, so the cheap, long-standing mutants keep their sites and the new one
    reaches exactly the lines that used to yield nothing.

    A file that does not tokenize (a syntax error the round introduced) has no
    sites: the baseline run is what reports that, and it reports it better.
    """
    try:
        source = path.read_text(encoding=ENCODING)
    except OSError:
        return {}
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return {}
    mutations = _assignment_mutations(tokens, source.splitlines())
    mutations.update(_operator_mutations(tokens))
    return mutations


def select_sites(base: str, root: Path) -> list[Site]:
    """At most `SITE_LIMIT` sites, in the order the diff presents them."""
    sites: list[Site] = []
    for path, lines in changed_lines(base, root).items():
        mutable = _line_mutations(root / path)
        for line in lines:
            found = mutable.get(line)
            if found is None:
                continue
            col, token, replacement = found
            sites.append(
                Site(
                    path=path,
                    line=line,
                    col=col,
                    token=token,
                    replacement=replacement,
                )
            )
            if len(sites) == SITE_LIMIT:
                return sites
    return sites


def apply_site(site: Site, tree: Path) -> None:
    """Perform `site`'s one mutation in `tree`, or fail loudly if it drifted.

    A deleted `not` takes one following space with it, so `not  x` never
    becomes `  x` with a stray double space — cosmetic in Python, but the log
    line is read by a human comparing the mutant against the original.
    """
    target = tree / site.path
    lines = target.read_text(encoding=ENCODING).splitlines(keepends=True)
    original = lines[site.line - 1]
    end = site.col + len(site.token)
    if original[site.col : end] != site.token:
        raise SystemExit(
            _MSG_DRIFTED.format(
                path=site.path, line=site.line, token=site.token, col=site.col
            )
        )
    if not site.replacement and original[end : end + 1] == " ":
        end += 1
    lines[site.line - 1] = original[: site.col] + site.replacement + original[end:]
    target.write_text("".join(lines), encoding=ENCODING)


def _executable_lines(path: Path) -> set[int] | None:
    """The rows of `path` a mutation operator could ever bite, or None.

    A statement is code here unless it is a bare string (a docstring), an
    `import`, or nothing but comment and layout. None means the file did not
    tokenize: a file that cannot be read must not buy the empty-diff pass.
    """
    try:
        source = path.read_text(encoding=ENCODING)
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (OSError, tokenize.TokenError, SyntaxError, IndentationError):
        return None
    executable: set[int] = set()
    statement: list[tokenize.TokenInfo] = []
    for token in tokens:
        if token.type not in _NON_CODE_TOKEN_TYPES:
            statement.append(token)
        if token.type != tokenize.NEWLINE:
            continue
        executable.update(_statement_rows(statement))
        statement = []
    executable.update(_statement_rows(statement))
    return executable


def _statement_rows(statement: list[tokenize.TokenInfo]) -> set[int]:
    """The rows one logical line makes executable — empty when it makes none."""
    if not statement:
        return set()
    first = statement[0]
    if first.type == tokenize.NAME and first.string in IMPORT_KEYWORDS:
        return set()
    if all(token.type == tokenize.STRING for token in statement):
        return set()
    rows: set[int] = set()
    for token in statement:
        rows.update(range(token.start[0], token.end[0] + 1))
    return rows


def count_executable_added(base: str, root: Path) -> int:
    """How many of this round's added lines under `SOURCE_PREFIX` are code."""
    total = 0
    for path, lines in changed_lines(base, root).items():
        executable = _executable_lines(root / path)
        if executable is None:
            total += len(lines)
            continue
        total += sum(1 for line in lines if line in executable)
    return total


def _read_sites(path: Path) -> list[Site]:
    """Every site of a TSV written by the `sites` subcommand."""
    rows = path.read_text(encoding=ENCODING).splitlines()
    return [Site.from_row(row) for row in rows if row]


def _parser() -> argparse.ArgumentParser:
    """The three-subcommand CLI `mutate.sh` drives."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sites = sub.add_parser("sites", help=_SITES_HELP)
    sites.add_argument("base")
    changed = sub.add_parser("changed", help=_CHANGED_HELP)
    changed.add_argument("base")
    apply_parser = sub.add_parser("apply", help=_APPLY_HELP)
    apply_parser.add_argument("sites", type=Path)
    apply_parser.add_argument("index", type=int)
    apply_parser.add_argument("tree", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one subcommand; the repo root is the current directory."""
    args = _parser().parse_args(argv)
    if args.command == "sites":
        for site in select_sites(args.base, Path.cwd()):
            print(site.to_row())
        return 0
    if args.command == "changed":
        print(count_executable_added(args.base, Path.cwd()))
        return 0
    sites = _read_sites(args.sites)
    if not 0 <= args.index < len(sites):
        raise SystemExit(_MSG_NO_SITE.format(index=args.index, total=len(sites)))
    site = sites[args.index]
    apply_site(site, args.tree)
    print(site.describe())
    return 0


if __name__ == "__main__":
    sys.exit(main())
