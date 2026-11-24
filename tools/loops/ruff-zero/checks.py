#!/usr/bin/env python3
"""Checks the ruff-zero run script applies to a run's data, none of them over the network.

usage: checks.py forge --fetch URL --push URL [--push URL ...] [--issue URL]
       checks.py open-prs --prefix PREFIX --limit N     < gh pr list JSON
       checks.py suppressions                           < git diff --cached
       checks.py fixed --before FILE --after FILE --rules JSON --count N
       checks.py body                                   < the pull request body

forge: print the one repository, as HOST/OWNER/REPO, that the remote's fetch
URL, its effective push URLs and the loop issue all name. Exit 1, printing each
problem, when a URL cannot be read, names a port other than its scheme's default
(an explicit default port is the implicit one), the remote has no or several
push destinations, or any two of them differ (host included). Problems name
counts and HOST/OWNER/REPO identities only, never a URL, so no credential in
one is printed.

open-prs: print the address of each open pull request whose branch starts with
PREFIX/. Exit 2 when the listing is not a JSON list or holds LIMIT entries (the
read may have been cut short): the caller stops rather than count it as none.

suppressions: exit 1, printing each offending line, when the staged diff adds
or changes a line that carries a Ruff directive in any form (`noqa`, or any
`ruff:` comment: `ruff: noqa`, `ruff: ignore`, `ruff: file-ignore`,
`ruff: disable`, `ruff: enable`, ...), or touches a Ruff configuration file.
Judged line by line, never netted across the file; a line that only removes a
directive passes. The diff must be plain (`git -c color.ui=never diff --cached
--no-color --no-ext-diff --no-textconv --text`): a diff holding a terminal escape
code is refused, since colour hides the added-line marker.

fixed: exit 1 unless, counted with --ignore-noqa before and after the change
(Ruff JSON output in the two files), no rule's count rose and the selected
rules' count dropped by at least COUNT, so a hidden finding is neither counted
as fixed nor allowed in as a new one.

body: exit 1, printing each match, when the body holds an issue-closing keyword
(close, closes, closed, fix, fixes, fixed, resolve, resolves, resolved) followed
by an issue reference, anywhere, so merging the pull request closes nothing.
"""

import argparse
import json
import re
import sys
from collections import Counter

CONFIG_FILES = re.compile(r"(^|/)(pyproject\.toml|ruff\.toml|\.ruff\.toml)$")
DIRECTIVE = re.compile(r"#\s*(?:noqa\b|ruff\s*:)", re.IGNORECASE)
ISSUE_REF = r"(?:[\w.-]+/[\w.-]+)?#\d+|https?://\S+/issues/\d+"
CLOSING = re.compile(
    rf"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\b\s*:?\s*(?:{ISSUE_REF})",
    re.IGNORECASE,
)
# Host and path parts admit only name characters, so a query string, fragment or other stray
# text makes a URL unreadable and is never echoed as part of an identity.
URL_FORMS = [
    # https://[user@]host[:port]/owner/repo[.git][/]  and  ssh://[user@]host[:port]/owner/repo[.git]
    re.compile(
        r"^(?P<scheme>https?|ssh|git)://(?:[^@/]+@)?(?P<host>[A-Za-z0-9.-]+)(?::(?P<port>\d+))?"
        r"/(?P<path>[\w.-]+/[\w.-]+?)(?:\.git)?/?$",
        re.IGNORECASE,
    ),
    # [user@]host:owner/repo[.git]  (scp-like, so ssh on its default port)
    re.compile(
        r"^(?:[^@/]+@)?(?P<host>[A-Za-z0-9.-]+):(?P<path>[\w.-]+/[\w.-]+?)(?:\.git)?/?$"
    ),
]
ISSUE_URL = re.compile(
    r"^(?P<scheme>https?)://(?P<host>[A-Za-z0-9.-]+)(?::(?P<port>\d+))?"
    r"/(?P<path>[\w.-]+/[\w.-]+)/issues/\d+$",
    re.IGNORECASE,
)
DEFAULT_PORTS = {"https": 443, "http": 80, "ssh": 22, "git": 9418}
ESCAPE = "\x1b"


def repo_identity(url, forms=URL_FORMS):
    """HOST[:PORT]/OWNER/REPO of a remote or issue URL, lowercased; None when unreadable.

    The port is kept unless it is the scheme's default, so an explicit default
    port names the same repository as the implicit one and any other port a
    different one. No userinfo is ever part of the identity. A URL holding a
    query or fragment delimiter is unreadable: a URL parser can take an `@`
    after one as ending the userinfo and so read another host.
    """
    if "?" in url or "#" in url:
        return None
    for form in forms:
        m = form.match(url.strip())
        if m:
            groups = m.groupdict()
            scheme = (groups.get("scheme") or "ssh").lower()
            port = groups.get("port")
            host = m["host"].lower()
            if port is not None and int(port) != DEFAULT_PORTS[scheme]:
                host = f"{host}:{int(port)}"
            return f"{host}/{m['path'].lower()}"
    return None


def forge_problems(fetch, pushes, issue=None):
    """(repository, problems): the one HOST/OWNER/REPO every URL names, or what disagrees."""
    problems = []
    named = {"fetch URL": repo_identity(fetch)}
    for i, push in enumerate(pushes, start=1):
        named[f"push URL {i}"] = repo_identity(push)
    if issue is not None:
        named["loop issue"] = repo_identity(issue, [ISSUE_URL])
    if len(pushes) != 1:
        problems.append(
            f"{len(pushes)} push destinations, not exactly one: "
            + ("; ".join(f"{k} {v or '(unreadable)'}" for k, v in named.items()))
        )
    problems += [
        f"cannot read a repository from the {k}" for k, v in named.items() if v is None
    ]
    problems += [
        f"the {k} names {v.split('/', 1)[0]}, a port other than its scheme's default"
        for k, v in named.items()
        if v and ":" in v.split("/", 1)[0]
    ]
    seen = sorted({v for v in named.values() if v})
    if len(seen) > 1:
        problems.append(
            "they name different repositories: "
            + "; ".join(f"{k} {v or '(unreadable)'}" for k, v in named.items())
        )
    return (seen[0] if len(seen) == 1 and not problems else None), problems


def open_loop_prs(listing, prefix, limit):
    """Addresses of the open pull requests on PREFIX/ branches; None when the read is incomplete."""
    if not isinstance(listing, list) or len(listing) >= limit:
        return None
    return [p["url"] for p in listing if p["headRefName"].startswith(prefix + "/")]


def added_suppressions(diff):
    """Added or changed lines carrying a Ruff directive, and touched Ruff configuration files."""
    bad = []
    for line in diff.splitlines():
        if ESCAPE in line:
            bad.append(
                f"terminal escape code in the diff (read it with --no-color): {line!r}"
            )
        elif line.startswith(("+++ ", "--- ")):
            path = line[4:].split("/", 1)[-1] if line[4:] != "/dev/null" else ""
            if CONFIG_FILES.search(path):
                bad.append(f"configuration file changed: {path}")
        elif line.startswith("+") and DIRECTIVE.search(line):
            bad.append(line)
    return bad


def rule_counts(findings):
    return Counter(f.get("code") or "syntax-error" for f in findings)


def fix_problems(before, after, rules, count):
    """Why the change is not a real fix (suppressions ignored): rules that rose, too small a drop."""
    b, a = rule_counts(before), rule_counts(after)
    problems = [
        f"{code} rose from {b[code]} to {a[code]}"
        for code in sorted(a)
        if a[code] > b[code]
    ]
    dropped = sum(b[c] for c in rules) - sum(a[c] for c in rules)
    if dropped < count:
        problems.append(f"the selected rules dropped by {dropped}, not {count}")
    return problems


def closing_directives(body):
    return [m.group(0) for m in CLOSING.finditer(body)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("forge")
    p.add_argument("--fetch", required=True)
    p.add_argument("--push", action="append", default=[])
    p.add_argument("--issue")
    p = sub.add_parser("open-prs")
    p.add_argument("--prefix", required=True)
    p.add_argument("--limit", type=int, required=True)
    sub.add_parser("suppressions")
    p = sub.add_parser("fixed")
    p.add_argument("--before", required=True)
    p.add_argument("--after", required=True)
    p.add_argument("--rules", required=True)
    p.add_argument("--count", type=int, required=True)
    sub.add_parser("body")
    args = ap.parse_args(argv)

    if args.cmd == "forge":
        repo, problems = forge_problems(
            args.fetch, [u for u in args.push if u], args.issue
        )
        print(repo if repo else "\n".join(problems))
        return 0 if repo else 1
    if args.cmd == "open-prs":
        try:
            listing = json.load(sys.stdin)
        except ValueError:
            listing = None
        urls = open_loop_prs(listing, args.prefix, args.limit)
        if urls is None:
            print("incomplete read of open pull requests", file=sys.stderr)
            return 2
        print(" ".join(urls))
        return 0
    if args.cmd == "suppressions":
        bad = added_suppressions(sys.stdin.read())
        print("\n".join(bad))
        return 1 if bad else 0
    if args.cmd == "fixed":
        rules = set(json.loads(args.rules))
        with open(args.before) as fh:
            before = json.load(fh)
        with open(args.after) as fh:
            after = json.load(fh)
        problems = fix_problems(before, after, rules, args.count)
        b, a = rule_counts(before), rule_counts(after)
        print(
            f"suppressions ignored: selected rules {sum(b[c] for c in rules)} before, "
            f"{sum(a[c] for c in rules)} after; all rules {sum(b.values())} before, "
            f"{sum(a.values())} after"
            + ("; " + "; ".join(problems) if problems else "; no rule rose")
        )
        return 1 if problems else 0
    bad = closing_directives(sys.stdin.read())
    print("\n".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
