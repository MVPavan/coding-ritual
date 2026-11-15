#!/usr/bin/env python3
"""Score Claude Code candidate runs from their stream-JSON logs.

usage: classify.py --patterns <patterns.json> [--out <results.json>] <log.jsonl>...

Every tool call is paired with its result by ID, and only evidence that the
intended file was read counts. The workspace is the `cwd` of the log's
`system/init` event; a run with none has no provable reads.

- a skill counts when its Skill call reports success;
- a `read` counts for a Read that succeeded with `file_path` exactly `<cwd>/<path>`
  and the signature in its output, or a Bash call whose first command is
  `[cd <cwd> ; | cd <cwd> && ]cat [--] <target>`, ended by `;`, `&&`, a newline or
  the end of the command. `<target>` is literally `<path>`, `./<path>` or
  `<cwd>/<path>`, in safe characters. The signature must be in the output, with no
  `cat: <target>:` or `cd: <cwd>:` error. That first command printed the file, so
  what follows it cannot make the credit false, and the whole command may exit
  non-zero;
- `unproven` is every other Bash call whose output holds the signature, including
  head, tail, sed, less, nl, a later `cat` and any quoted file name. A person reads
  these; they never join `reads`;
- an Edit or Write counts when it succeeded, and a shell write when its command
  matched and a result came back.

An event with a non-null `parent_tool_use_id` belongs to a delegate. Its calls
never enter `steps`, `skills`, `reads`, `unproven`, `edits` or `commands`; what it
provably read is reported as `delegate_reads`, and the parent's own call stays in
`subagents`.

`steps` follows call order. Calls in one assistant message ran in parallel, so
their order says nothing about which finished first.

The patterns describe one variant, so nothing here knows what is under test:

    {"reads": {"<label>": {"path": "<path relative to cwd>", "signature": "<text>"}},
     "edits": {"<label>": {"path": "<regex>", "bash_write": "<regex>"}},
     "commands": {"<label>": "<regex>"}}

Only `reads` is required; `bash_write` is optional. The first `edits` label whose
`path` matches wins. Loading refuses an empty signature, a `path` that is absolute
or holds `..`, a signature found in the `path` or the file's name, and two labels
where one signature contains the other. Take the signature from the part whose
reading matters: it proves that part was printed, not the whole unit.

Two limits remain. A signature that also occurs in another file adds `unproven`
entries, and in `cat target; cat other` it cannot say which file printed it: the
credit that target was printed holds, but not that the part you chose was. A bare
relative target assumes the shell is still in `<cwd>`, and Claude Code keeps a `cd`
between Bash calls, so a copy of the file at `sub/<path>` could score.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Iterable
from itertools import combinations
from pathlib import Path, PurePosixPath
from typing import Any

# What the shell takes as one literal word, whatever the working directory holds.
SAFE_WORD = re.compile(r"[/\w.][\w./-]*", re.ASCII)
LINE_NUMBER = re.compile(r"^\s*\d+(?:\t|→)", re.MULTILINE)
SUBAGENT_TOOLS = ("Task", "Agent")
EDIT_TOOLS = ("Edit", "Write", "NotebookEdit")


def read_events(path: Path) -> tuple[list[dict[str, Any]], int]:
    """The log's events, and how many lines were not JSON (a run cut off mid-line)."""
    events: list[dict[str, Any]] = []
    malformed = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            malformed += 1
    return events, malformed


def result_text(content: Any) -> str:
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return content or ""


def workspace(events: Iterable[dict[str, Any]]) -> str | None:
    """The run's working directory, from its `system/init` event."""
    for event in events:
        if event.get("type") == "system" and event.get("subtype") == "init":
            cwd = event.get("cwd")
            return cwd if isinstance(cwd, str) and cwd else None
    return None


def tool_calls(
    events: Iterable[dict[str, Any]], *, delegates: bool = False
) -> list[tuple[str, dict[str, Any], dict[str, Any] | None]]:
    """Ordered (tool name, input, result) of the candidate's own calls, or its
    delegates'; a call with no result gets None."""
    order: list[tuple[str, str, dict[str, Any]]] = []
    results: dict[str, dict[str, Any]] = {}
    for event in events:
        content = event.get("message", {}).get("content")
        if not isinstance(content, list):
            continue
        if event.get("type") == "assistant":
            if (event.get("parent_tool_use_id") is not None) == delegates:
                order += [
                    (c["id"], c["name"], c["input"])
                    for c in content
                    if c.get("type") == "tool_use"
                ]
        elif event.get("type") == "user":
            meta = event.get("tool_use_result")
            for c in content:
                if c.get("type") == "tool_result":
                    results[c["tool_use_id"]] = {
                        "error": bool(c.get("is_error")),
                        "text": result_text(c.get("content")),
                        "success": meta.get("success")
                        if isinstance(meta, dict)
                        else None,
                    }
    return [(name, inp, results.get(tid)) for tid, name, inp in order]


def skill_succeeded(result: dict[str, Any] | None) -> bool:
    return (
        result is not None
        and not result["error"]
        and (result["success"] is True or result["text"].startswith("Launching skill"))
    )


def shell_read_proven(command: str, path: str, cwd: str, output: str) -> bool:
    """The first command is a plain `cat` of the file, and no error says it failed."""
    if not (SAFE_WORD.fullmatch(cwd) and SAFE_WORD.fullmatch(path)):
        return False
    home, name = re.escape(cwd), re.escape(path)
    found = re.match(
        rf"(?:cd[ \t]+{home}[ \t]*(?:;|&&)[ \t]*)?"
        rf"cat[ \t]+(?:--[ \t]+)?((?:\./|{home}/)?{name})[ \t]*(?:;|&&|\n|\Z)",
        command,
    )
    return (
        found is not None
        and f"cat: {found.group(1)}:" not in output
        and f"cd: {cwd}:" not in output
    )


def read_evidence(
    name: str,
    inp: dict[str, Any],
    result: dict[str, Any] | None,
    pattern: dict[str, str],
    cwd: str | None,
) -> str | None:
    """`read`, `unproven`, or None when this call says nothing about the file."""
    if result is None or name not in ("Read", "Bash"):
        return None
    if name == "Read":
        if result["error"] or not cwd:
            return None
        if inp.get("file_path") != f"{cwd}/{pattern['path']}":
            return None
        text = LINE_NUMBER.sub("", result["text"])
        return "read" if pattern["signature"] in text else None
    if pattern["signature"] not in result["text"]:
        return None
    if cwd and shell_read_proven(
        inp.get("command", ""), pattern["path"], cwd, result["text"]
    ):
        return "read"
    return "unproven"


def edit_label(
    name: str,
    inp: dict[str, Any],
    result: dict[str, Any] | None,
    patterns: dict[str, Any],
) -> str | None:
    if result is None:
        return None
    for label, pattern in patterns.get("edits", {}).items():
        if name in EDIT_TOOLS:
            if not result["error"] and re.search(
                pattern["path"], inp.get("file_path", "")
            ):
                return str(label)
        elif name == "Bash" and "bash_write" in pattern:
            command = inp.get("command", "")
            if re.search(pattern["path"], command) and re.search(
                pattern["bash_write"], command
            ):
                return str(label)
    return None


def steps_of(events: Iterable[dict[str, Any]], patterns: dict[str, Any]) -> list[str]:
    """The candidate's own evidence in call order: `skill:`, `read:`, `unproven:`,
    `edit:`, `command:`, `subagent:`."""
    events = list(events)
    cwd = workspace(events)
    steps: list[str] = []
    for name, inp, result in tool_calls(events):
        if name == "Skill":
            if skill_succeeded(result):
                steps.append(f"skill:{inp.get('skill')}")
            continue
        if name in SUBAGENT_TOOLS:
            steps.append(f"subagent:{inp.get('subagent_type')}")  # (Claude Code input)
            continue
        for label, pattern in patterns["reads"].items():
            evidence = read_evidence(name, inp, result, pattern, cwd)
            if evidence is not None:
                steps.append(f"{evidence}:{label}")
        edit = edit_label(name, inp, result, patterns)
        if edit is not None:
            steps.append(f"edit:{edit}")
        if name == "Bash" and result is not None:
            steps += [
                f"command:{label}"
                for label, regex in patterns.get("commands", {}).items()
                if re.search(regex, inp.get("command", ""))
            ]
    return steps


def delegate_reads(
    events: Iterable[dict[str, Any]], patterns: dict[str, Any]
) -> dict[str, int]:
    """What delegates provably read, by label: not the candidate's own reads."""
    events = list(events)
    cwd = workspace(events)
    found = [
        label
        for name, inp, result in tool_calls(events, delegates=True)
        for label, pattern in patterns["reads"].items()
        if read_evidence(name, inp, result, pattern, cwd) == "read"
    ]
    return {label: found.count(label) for label in dict.fromkeys(found)}


def classify(path: Path, patterns: dict[str, Any]) -> dict[str, Any]:
    events, malformed = read_events(path)
    final = next((e for e in reversed(events) if e.get("type") == "result"), None)
    steps = steps_of(events, patterns)

    def values(kind: str) -> list[str]:
        return [s.split(":", 1)[1] for s in steps if s.startswith(f"{kind}:")]

    def counts(kind: str) -> dict[str, int]:
        found = values(kind)
        return {label: found.count(label) for label in dict.fromkeys(found)}

    return {
        "id": path.stem,
        "skills": values("skill"),
        "reads": counts("read"),
        "unproven": counts("unproven"),
        "delegate_reads": delegate_reads(events, patterns),
        "edits": counts("edit"),
        "commands": counts("command"),
        "subagents": values("subagent"),
        "steps": steps,
        "status": final.get("subtype", "unknown") if final else "no-result",
        "result_error": bool(final.get("is_error")) if final else None,
        "turns": final.get("num_turns") if final else None,
        "cost": final.get("total_cost_usd") if final else None,
        "malformed_lines": malformed,
    }


def validate(patterns: dict[str, Any]) -> None:
    """Refuse read patterns that could not bind evidence to one file."""

    def refuse(label: str, why: str) -> None:
        raise SystemExit(f"classify.py: pattern {label}: {why}")

    reads = patterns["reads"]
    for label, pattern in reads.items():
        path, signature = pattern.get("path", ""), pattern.get("signature", "").strip()
        if not signature:
            refuse(label, "empty signature")
        pure = PurePosixPath(path)
        if not path or pure.is_absolute() or ".." in pure.parts:
            refuse(label, f"path must be relative with no '..': {path!r}")
        if signature in path:
            refuse(label, "signature occurs in the path or the file's name")
    for (one, a), (two, b) in combinations(reads.items(), 2):
        if a["signature"] in b["signature"] or b["signature"] in a["signature"]:
            refuse(one, f"one signature contains the other, with label {two}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score candidate runs from logs.")
    parser.add_argument("--patterns", type=Path, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("logs", type=Path, nargs="+")
    args = parser.parse_args(argv)
    patterns = json.loads(args.patterns.read_text(encoding="utf-8"))
    validate(patterns)
    rows = [classify(log, patterns) for log in args.logs]
    for row in rows:
        print(json.dumps({k: v for k, v in row.items() if k != "steps"}))
    if args.out:
        args.out.write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
