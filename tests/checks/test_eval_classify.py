"""`playbooks/eval/classify.py`: only a successful content read or skill call scores."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / ".claude/skills/mvp-mode/playbooks/eval/classify.py"
)
CWD = "/x"
PLAYBOOK = ".claude/skills/mvp-mode/playbooks/example.md"
BODY = "---\ntrigger: x\n---\n\n# Example\n\nFor a request"
PATTERNS: dict[str, Any] = {
    "reads": {"playbook": {"path": PLAYBOOK, "signature": "\n# Example\n"}},
    "edits": {"prod": {"path": r"src/.*\.py", "bash_write": r"sed -i"}},
    "commands": {"repro": "pytest"},
}
INIT = {"type": "system", "subtype": "init", "cwd": CWD}


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("eval_classify", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # No bytecode beside the script: that folder ships.
    writes_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    sys.dont_write_bytecode = writes_bytecode
    return module


classify = _load()


def call(
    n: int,
    name: str,
    inp: dict[str, Any],
    text: str,
    *,
    error: bool = False,
    parent: str | None = None,
) -> list[dict[str, Any]]:
    """One tool call and its result, as the stream-JSON log holds them."""
    tid = f"t{n}"
    use = {"type": "tool_use", "id": tid, "name": name, "input": inp}
    result = {
        "type": "tool_result",
        "tool_use_id": tid,
        "is_error": error,
        "content": text,
    }
    return [
        {
            "type": "assistant",
            "parent_tool_use_id": parent,
            "message": {"content": [use]},
        },
        {
            "type": "user",
            "parent_tool_use_id": parent,
            "message": {"content": [result]},
        },
    ]


def steps(*events: list[dict[str, Any]]) -> list[str]:
    return list(classify.steps_of([INIT, *(e for es in events for e in es)], PATTERNS))


def bash(command: str, text: str = BODY, *, error: bool = False) -> list[str]:
    return steps(call(1, "Bash", {"command": command}, text, error=error))


def numbered(text: str) -> str:
    return "\n".join(f"{i}\t{line}" for i, line in enumerate(text.split("\n"), 1))


READ = {"file_path": f"{CWD}/{PLAYBOOK}"}


def test_mentions_and_failures_are_no_read() -> None:
    assert bash(f"test -f {PLAYBOOK} && echo yes", "yes") == []
    assert (
        steps(call(1, "Grep", {"pattern": "example.md"}, f"{PLAYBOOK}\n{BODY}")) == []
    )
    assert steps(call(1, "Read", READ, "No such file", error=True)) == []
    assert steps(call(1, "Read", READ, BODY, error=True)) == []


def test_another_directorys_file_is_no_read() -> None:
    other = {"file_path": f"/other-variant/{PLAYBOOK}"}
    assert steps(call(1, "Read", other, numbered(BODY))) == []
    assert bash(f"cat /other-variant/{PLAYBOOK}") == ["unproven:playbook"]
    assert bash(f"cd /other-variant; cat {PLAYBOOK}") == ["unproven:playbook"]


@pytest.mark.parametrize(
    "command",
    [
        f"cat notes.md # {PLAYBOOK}",
        f"cat <<EOF # {PLAYBOOK}\n{BODY}\nEOF",
        f"cat {PLAYBOOK}.bak",
        f"cat notes.md; test -f {PLAYBOOK}",
        f"cat notes.md\ntest -f {PLAYBOOK}",
        f"echo $(cat {PLAYBOOK})",
        f"echo `cat {PLAYBOOK}`",
        f"F={PLAYBOOK}; cat $F",
        f"python3 -c 'print(open(\"{PLAYBOOK}\").read())'",
        f"grep -n Example {PLAYBOOK}",
        f'cat "{PLAYBOOK}',
        f"cat notes.md > {PLAYBOOK}",
        f"cat < {PLAYBOOK}",
        f"cat {PLAYBOOK} > /dev/null; cat other",
        f"cat {PLAYBOOK} 2>/dev/null; cat other",
        f"echo ';' cat {PLAYBOOK}",
        f"(cd /x/sub; true); cat ../{PLAYBOOK}",
        # The signature came from `other`, and the target was not what printed it.
        f"cat {PLAYBOOK} | wc -l; cat other",
        f"false && cat {PLAYBOOK}; cat other",
        f"false &&\ncat {PLAYBOOK}; cat other",
        f"cat other && cat {PLAYBOOK}",
        f"cat other || cat {PLAYBOOK}",
        f"cat other; cat {PLAYBOOK}",
        f"# about to read\ncat {PLAYBOOK}",
        f'cat "{PLAYBOOK}"',
        f"head -n 5 {PLAYBOOK}",
        f"tail -5 {PLAYBOOK}",
        f"sed -n 1,5p {PLAYBOOK}",
        f"sed -n 'r other' {PLAYBOOK}",
        f"nl -s {PLAYBOOK}; cat other",
        f"less -p {PLAYBOOK}; cat other",
        f"PATH=/nonexistent; cat {PLAYBOOK}; /bin/cat other",
        f"cat -- {PLAYBOOK} -x",
        f"cat --version {PLAYBOOK}; cat other",
        f"alias cat=/bin/true; cat {PLAYBOOK}; /bin/cat other",
        f"cat link/../{PLAYBOOK}",
        f"cat {PLAYBOOK} || cat other",
        f"cat {PLAYBOOK} # x",
        f"cat not\\\n{PLAYBOOK}; cat other",
        f"cat 'not\\\n{PLAYBOOK}'; cat other",
        f"cat {PLAYBOOK} other",
        f"if false\nthen\ncat {PLAYBOOK}\nfi\ncat other",
        f"sed -n 1p {PLAYBOOK} other",
        f"sed -n -e {PLAYBOOK}; cat other",
        f"for i in 1 2; do cat {PLAYBOOK}; done",
        f"cat other; exit; cat {PLAYBOOK}",
        f"cat {PLAYBOOK} & cat other",
        f"VAR=x cat {PLAYBOOK}",
        f"cd sub || cd /x; cat {PLAYBOOK}",
        f"cd sub; pushd /x; cat {PLAYBOOK}",
        f"cd ~/..; cat x/{PLAYBOOK}",
    ],
)
def test_ambiguous_shell_evidence_is_unproven_never_read(command: str) -> None:
    assert bash(command) == ["unproven:playbook"]


@pytest.mark.parametrize(
    ("path", "command"),
    [
        ("1p", "sed -n 1p other"),
        ("1", "awk 1 other"),
        ("1000", "head -c 1000 other"),
    ],
)
def test_program_text_and_option_values_are_not_the_file(
    path: str, command: str
) -> None:
    patterns = {"reads": {"f": {"path": path, "signature": "UNIQUE"}}}
    events = [INIT, *call(1, "Bash", {"command": command}, "UNIQUE\n")]
    assert classify.steps_of(events, patterns) == ["unproven:f"]


@pytest.mark.parametrize("error", ["No such file or directory", "Permission denied"])
def test_a_cat_whose_file_did_not_open_is_unproven(error: str) -> None:
    output = f"cat: {PLAYBOOK}: {error}\n{BODY}"
    assert bash(f"cat {PLAYBOOK}; cat other", output) == ["unproven:playbook"]


@pytest.mark.parametrize("separator", [";", " &&"])
def test_a_cd_that_failed_is_unproven(separator: str) -> None:
    output = f"{BODY}\n/bin/bash: line 1: cd: {CWD}: Permission denied"
    command = f"cd {CWD}{separator} cat {PLAYBOOK}; cat other"
    assert bash(command, output) == ["unproven:playbook"]


def test_no_signature_in_the_output_is_nothing() -> None:
    assert bash(f"head -2 {PLAYBOOK}", "---\ntrigger: x") == []


def test_call_with_no_result_is_no_read() -> None:
    assert steps(call(1, "Read", READ, numbered(BODY))[:1]) == []


def test_a_run_with_no_cwd_has_no_provable_reads() -> None:
    events = call(1, "Read", READ, numbered(BODY))
    events += call(2, "Bash", {"command": f"cat {PLAYBOOK}"}, BODY)
    assert classify.steps_of(events, PATTERNS) == ["unproven:playbook"]


def test_successful_read_scores_with_its_real_line_numbers() -> None:
    assert steps(call(1, "Read", READ, numbered(BODY))) == ["read:playbook"]
    padded = "\n".join(f"{i:6}\t{x}" for i, x in enumerate(BODY.split("\n"), 1))
    assert steps(call(1, "Read", READ, padded)) == ["read:playbook"]


def test_a_read_path_is_compared_exactly() -> None:
    for path in (PLAYBOOK, f"{CWD}/./{PLAYBOOK}", f"{CWD}/link/../{PLAYBOOK}"):
        assert steps(call(1, "Read", {"file_path": path}, numbered(BODY))) == []


@pytest.mark.parametrize(
    "command",
    [
        f"cat {PLAYBOOK}",
        f"cat {PLAYBOOK}; cat other",
        f"cd {CWD}; cat {PLAYBOOK}; echo ----; git ls-files | grep -v -E '^(a|b/)' | head -50",
        f"cd {CWD} && cat {PLAYBOOK}",
        f"cat -- {PLAYBOOK}",
        f"cat {CWD}/{PLAYBOOK}",
        f"cat ./{PLAYBOOK}",
    ],
)
def test_the_one_scoring_form(command: str) -> None:
    assert bash(command) == ["read:playbook"]


def test_shell_read_scores_even_when_the_compound_command_fails() -> None:
    assert bash(f"cat {PLAYBOOK}; cat nope", error=True) == ["read:playbook"]


def test_shell_output_keeps_its_own_line_shape() -> None:
    patterns = {"reads": {"f": {"path": "f.txt", "signature": "1\tfoo"}}}
    events = [INIT, *call(1, "Bash", {"command": "cat f.txt"}, "1\tfoo\n")]
    assert classify.steps_of(events, patterns) == ["read:f"]


def test_failed_then_retried_read_scores_once() -> None:
    got = steps(
        call(1, "Read", READ, "not found", error=True),
        call(2, "Read", READ, numbered(BODY)),
    )
    assert got == ["read:playbook"]


def test_skill_invocation_counts_only_on_success() -> None:
    ok = call(1, "Skill", {"skill": "mvp-mode"}, "Launching skill: mvp-mode")
    assert steps(ok) == ["skill:mvp-mode"]
    bad = call(1, "Skill", {"skill": "nope"}, "Unknown skill: nope", error=True)
    assert steps(bad) == []


def test_failed_edit_is_no_edit() -> None:
    inp = {"file_path": "/x/src/a.py"}
    assert steps(call(1, "Edit", inp, "must read first", error=True)) == []
    assert steps(call(1, "Edit", inp, "ok")) == ["edit:prod"]


def test_a_delegates_read_is_not_the_candidates(tmp_path: Path) -> None:
    events = [INIT]
    events += call(1, "Task", {"subagent_type": "helper"}, "done")
    events += call(2, "Read", READ, numbered(BODY), parent="t1")
    events += call(
        3, "Bash", {"command": f"cat notes; test -f {PLAYBOOK}"}, BODY, parent="t1"
    )
    events += call(
        4, "Skill", {"skill": "other"}, "Launching skill: other", parent="t1"
    )
    events += call(5, "Edit", {"file_path": "/x/src/a.py"}, "ok", parent="t1")
    log = tmp_path / "run.jsonl"
    log.write_text("\n".join(json.dumps(e) for e in events))

    row = classify.classify(log, PATTERNS)

    assert row["steps"] == ["subagent:helper"]
    assert row["subagents"] == ["helper"]
    assert (row["reads"], row["unproven"], row["skills"]) == ({}, {}, [])
    assert row["edits"] == {}
    assert row["delegate_reads"] == {"playbook": 1}


@pytest.mark.parametrize(
    ("reads", "label"),
    [
        ({"a": {"path": "a.md", "signature": " "}}, "a"),
        ({"a": {"path": "/abs/a.md", "signature": "x"}}, "a"),
        ({"a": {"path": "../a.md", "signature": "x"}}, "a"),
        ({"a": {"path": "dir/a.md", "signature": "a.md"}}, "a"),
        ({"a": {"path": "dir/a.md", "signature": "dir"}}, "a"),
        (
            {
                "a": {"path": "a.md", "signature": "# Title"},
                "b": {"path": "b.md", "signature": "# Title two"},
            },
            "a",
        ),
    ],
)
def test_weak_patterns_are_refused_at_load(
    tmp_path: Path, reads: dict[str, Any], label: str
) -> None:
    patterns = tmp_path / "patterns.json"
    patterns.write_text(json.dumps({"reads": reads}))
    log = tmp_path / "run.jsonl"
    log.write_text("")

    with pytest.raises(SystemExit) as refused:
        classify.main(["--patterns", str(patterns), str(log)])

    assert refused.value.code not in (0, None)
    assert f"pattern {label}" in str(refused.value.code)


def test_patterns_are_parameters(tmp_path: Path) -> None:
    other = {"reads": {"guide": {"path": "docs/guide.md", "signature": "# Guide"}}}
    patterns = tmp_path / "patterns.json"
    patterns.write_text(json.dumps(other))
    log = tmp_path / "run-7.jsonl"
    events = [INIT]
    events += call(1, "Bash", {"command": "cat docs/guide.md"}, "# Guide\n")
    events += call(2, "Bash", {"command": f"cat {PLAYBOOK}"}, BODY)
    events.append({"type": "result", "subtype": "success", "total_cost_usd": 0.5})
    log.write_text("\n".join(json.dumps(e) for e in events) + '\n{"cut off')
    out = tmp_path / "results.json"

    assert (
        classify.main(["--patterns", str(patterns), "--out", str(out), str(log)]) == 0
    )

    row = json.loads(out.read_text())[0]
    assert row["id"] == "run-7"
    assert row["reads"] == {"guide": 1}
    assert (row["status"], row["cost"], row["malformed_lines"]) == ("success", 0.5, 1)
