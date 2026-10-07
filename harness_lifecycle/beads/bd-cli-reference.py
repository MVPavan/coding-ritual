#!/usr/bin/env python3
"""Generate a Markdown reference of the full bd CLI from its own --help output.

Walks every command and subcommand recursively and records usage, aliases,
examples, local flags and global flags. `--help` never opens a database.

    python3 harness_lifecycle/beads/bd-cli-reference.py > harness_lifecycle/beads/cli-<version>.md
"""
import os
import re
import subprocess
import sys

BD = sys.argv[1] if len(sys.argv) > 1 else "bd"
# Headings in cobra help that are not command groups.
NON_COMMAND = {"Usage", "Aliases", "Examples", "Flags", "Global Flags"}
FLAG_RE = re.compile(r"^\s+(?:(-\w), )?(--[\w-]+)(?: (\S+))?\s{2,}(.*)$")
ENTRY_RE = re.compile(r"^  ([a-z][\w-]*)\s{2,}(.*)$")
GLOBAL_NAMES = set()


def help_text(path):
    out = subprocess.run([BD, *path, "--help"], capture_output=True, text=True,
                         env={**os.environ, "NO_COLOR": "1", "TERM": "dumb"})
    return out.stdout + (out.stderr if not out.stdout else "")


def split_sections(text):
    """Return (description, [(heading, [lines])]) using cobra's layout."""
    desc, sections, cur = [], [], None
    for line in text.splitlines():
        m = re.match(r"^([A-Z][\w &/-]*):\s*$", line)
        if m:
            cur = (m.group(1), [])
            sections.append(cur)
        elif cur is None:
            desc.append(line)
        else:
            cur[1].append(line)
    return "\n".join(desc).strip(), sections


def parse_flags(lines):
    flags, last = [], None
    for line in lines:
        m = FLAG_RE.match(line)
        if m:
            short, long_, typ, text = m.groups()
            last = {"short": short or "", "long": long_, "type": typ or "", "desc": text.strip()}
            flags.append(last)
        elif last and line.strip():
            last["desc"] += " " + line.strip()
    return flags


def crawl(path, seen):
    text = help_text(path)
    desc, sections = split_sections(text)
    usage = next((s for h, s in sections if h == "Usage"), [])
    usage = [u.strip() for u in usage if u.strip()]
    # The help really belongs to this path only if its usage line names it.
    if path and not any(u.startswith(" ".join(["bd", *path])) for u in usage):
        return None
    node = {"path": path, "desc": desc, "usage": usage, "groups": [], "children": [],
            "aliases": "", "examples": "", "flags": [], "global": []}
    for heading, lines in sections:
        if heading == "Aliases":
            node["aliases"] = " ".join(l.strip() for l in lines if l.strip())
        elif heading == "Examples":
            node["examples"] = "\n".join(lines).strip("\n")
        elif heading == "Flags":
            node["flags"] = parse_flags(lines)
        elif heading == "Global Flags":
            node["global"] = parse_flags(lines)
        elif heading not in NON_COMMAND:
            entries = [ENTRY_RE.match(l) for l in lines]
            entries = [(m.group(1), m.group(2).strip()) for m in entries if m]
            node["groups"].append((heading, entries, lines))
    groups = []
    for heading, entries, lines in node["groups"]:
        kept = []
        for name, text in entries:
            child = [*path, name]
            key = " ".join(child)
            if name == "help":
                kept.append((name, text))
                continue
            if key in seen:
                continue
            seen.add(key)
            sub = crawl(child, seen)
            if sub:
                node["children"].append(sub)
                kept.append((name, text))
        if kept:
            groups.append((heading, kept))
        else:  # a field or value list in the long description, not commands
            node["desc"] += f"\n\n{heading}:\n" + "\n".join(lines).rstrip()
    node["groups"] = groups
    return node


def md_escape(s):
    return s.replace("|", "\\|")


def flag_table(flags):
    rows = ["| Flag | Short | Type | Description |", "|---|---|---|---|"]
    for f in flags:
        rows.append(f"| `{f['long']}` | {'`' + f['short'] + '`' if f['short'] else ''} | "
                    f"{f['type']} | {md_escape(f['desc'])} |")
    return "\n".join(rows)


def slug(path):
    return "bd-" + "-".join(path) if path else "bd"


def toc(node, depth=0, out=None):
    out = [] if out is None else out
    for c in node["children"]:
        summary = next((d for _, es in node["groups"] for n, d in es if n == c["path"][-1]), "")
        out.append(f"{'  ' * depth}- [`bd {' '.join(c['path'])}`](#{slug(c['path'])}) — {md_escape(summary)}")
        toc(c, depth + 1, out)
    return out


def render(node, out):
    name = " ".join(["bd", *node["path"]])
    level = min(2 + len(node["path"]) - 1, 6) if node["path"] else 2
    out.append(f'<a id="{slug(node["path"])}"></a>\n\n{"#" * level} `{name}`\n')
    if node["desc"]:
        out.append("```text\n" + node["desc"] + "\n```\n")
    if node["usage"]:
        out.append("**Usage**\n\n```text\n" + "\n".join(node["usage"]) + "\n```\n")
    if node["aliases"]:
        out.append(f"**Aliases:** `{node['aliases']}`\n")
    for heading, entries in node["groups"]:
        out.append(f"**{heading}**\n\n" + "\n".join(
            f"- [`{n}`](#{slug([*node['path'], n])}) — {md_escape(d)}" if n != "help" else f"- `help` — {md_escape(d)}"
            for n, d in entries) + "\n")
    if node["examples"]:
        out.append("**Examples**\n\n```text\n" + node["examples"] + "\n```\n")
    if node["flags"]:
        out.append("**Flags**\n\n" + flag_table(node["flags"]) + "\n")
    shadowed = [f["long"] for f in node["flags"] if f["long"] in GLOBAL_NAMES and node["path"]]
    if shadowed:
        out.append("Local definitions override the global flags " +
                   ", ".join(f"`{x}`" for x in shadowed) + " for this command.\n")
    for c in node["children"]:
        render(c, out)


def count(node):
    return 1 + sum(count(c) for c in node["children"])


def main():
    root = crawl([], set())
    # Children print the root's persistent flags under "Global Flags".
    globals_ = root["children"][0]["global"]
    global_names = {f["long"] for f in globals_}
    GLOBAL_NAMES.update(global_names)
    version = subprocess.run([BD, "version"], capture_output=True, text=True).stdout.split("\n")[0].strip()
    out = [f"# bd CLI reference — {version}\n",
           f"Generated from `bd --help` output by `harness_lifecycle/beads/bd-cli-reference.py`; "
           f"{count(root) - 1} commands. Regenerate after every bd upgrade and keep the "
           f"version in the file name. Global flags apply to every command and are "
           f"listed once below; each command lists only its own flags. Hidden internal "
           f"commands in 1.3.0 (not shown by `--help`, so not covered here): `db-proxy-child`, "
           f"`cursor-hook`, `codex-hook` and the metrics sender.\n",
           "## Command tree\n", "\n".join(toc(root)) + "\n",
           "## Global flags\n", flag_table(globals_) + "\n",
           "## Commands\n"]
    render(dict(root, flags=[f for f in root["flags"] if f["long"] not in global_names]), out)
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
