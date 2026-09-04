"""Site selection and single-site editing for `scripts/checks/mutate.sh`.

Two subcommands, because the shell owns the expensive half (copy, baseline,
pytest) and this owns the two steps a shell cannot do honestly:

- `sites BASE` reads the lines this round ADDED under `workflow_interpreter/`
  and picks at most `SITE_LIMIT` of them to mutate, one mutation per line.
- `apply SITES INDEX TREE` performs exactly one of those mutations in a copy of
  the tree and prints the human-readable description of what it did.

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


@dataclass(frozen=True)
class Site:
    """One mutable operator token: where it is and what it becomes."""

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


def _mutable_tokens(path: Path) -> dict[int, tuple[int, str]]:
    """The FIRST mutable token of every line of `path`, by line number.

    A file that does not tokenize (a syntax error the round introduced) has no
    sites: the baseline run is what reports that, and it reports it better.
    """
    first: dict[int, tuple[int, str]] = {}
    try:
        source = path.read_text(encoding=ENCODING)
    except OSError:
        return first
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return first
    for token in tokens:
        if token.type not in (tokenize.OP, tokenize.NAME):
            continue
        if token.string not in MUTATION_BY_TOKEN:
            continue
        line = token.start[0]
        if line not in first:
            first[line] = (token.start[1], token.string)
    return first


def select_sites(base: str, root: Path) -> list[Site]:
    """At most `SITE_LIMIT` sites, in the order the diff presents them."""
    sites: list[Site] = []
    for path, lines in changed_lines(base, root).items():
        mutable = _mutable_tokens(root / path)
        for line in lines:
            found = mutable.get(line)
            if found is None:
                continue
            col, token = found
            sites.append(
                Site(
                    path=path,
                    line=line,
                    col=col,
                    token=token,
                    replacement=MUTATION_BY_TOKEN[token],
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


def _read_sites(path: Path) -> list[Site]:
    """Every site of a TSV written by the `sites` subcommand."""
    rows = path.read_text(encoding=ENCODING).splitlines()
    return [Site.from_row(row) for row in rows if row]


def _parser() -> argparse.ArgumentParser:
    """The two-subcommand CLI `mutate.sh` drives."""
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sites = sub.add_parser("sites", help=_SITES_HELP)
    sites.add_argument("base")
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
    sites = _read_sites(args.sites)
    if not 0 <= args.index < len(sites):
        raise SystemExit(_MSG_NO_SITE.format(index=args.index, total=len(sites)))
    site = sites[args.index]
    apply_site(site, args.tree)
    print(site.describe())
    return 0


if __name__ == "__main__":
    sys.exit(main())
