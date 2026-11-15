#!/usr/bin/env python3
"""Append one row to a decision trail, a TSV holding one row per decision.

Usage: log_row.py <file> [--extra a,b] phase=.. decision=.. why=.. evidence=.. result=.. a=.. b=..
A bad cell, a bad extra name or columns differing from the header exit non-zero and write nothing.
"""

import argparse
import fcntl
import re
import time
from pathlib import Path

CELLS = ("phase", "decision", "why", "evidence", "result")
NAME = re.compile(r"[a-z][a-z0-9_]*")
SIGNED_NUMBER = re.compile(r"[+-]\d+(\.\d+)?%?")


def clean(value: str) -> str:
    value = re.sub(r"[\t\r\n\v\f\x85\u2028\u2029]", " ", value)
    formula = value.lstrip()[:1] in ("=", "+", "-", "@")
    return f"'{value}" if formula and not SIGNED_NUMBER.fullmatch(value) else value


def main() -> None:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("file", type=Path)
    parser.add_argument("--extra")
    parser.add_argument("cells", nargs="*")
    args = parser.parse_intermixed_args()

    extra = [] if args.extra is None else args.extra.split(",")
    names = [*CELLS, *extra]
    columns = ["ts", *names]
    bad_name = not all(NAME.fullmatch(name) for name in extra)
    if bad_name or len(set(columns)) < len(columns):
        parser.error(f"malformed, duplicate or fixed column in --extra {args.extra!r}")
    pairs = [cell.partition("=") for cell in args.cells]
    given = {name: value for name, sep, value in pairs if sep}
    if len(pairs) != len(names) or set(given) != set(names):
        parser.error(f"want exactly one name=value for each of {names}")

    header = "\t".join(columns) + "\n"
    args.file.parent.mkdir(parents=True, exist_ok=True)
    # Append mode, so no path through here can overwrite a row.
    with open(args.file, "a+", encoding="utf-8", errors="surrogateescape") as log:
        fcntl.flock(log, fcntl.LOCK_EX)
        log.seek(0)
        first = log.readline()
        if first and first != header:
            parser.error(f"columns differ from {args.file}'s header: {first!r}")
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        row = [stamp, *(clean(given[name]) for name in names)]
        log.write(("" if first else header) + "\t".join(row) + "\n")


if __name__ == "__main__":
    main()
