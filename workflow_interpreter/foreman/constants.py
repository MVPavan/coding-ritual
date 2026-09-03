"""Names and immutable vocabulary owned by the foreman."""

from typing import Final

from workflow_interpreter.bdio.constants import (
    DEVIATION_INSTANCE_BRANCH_DIVERGED,
    DEVIATION_PRECONDITION_REFUSED,
    DEVIATION_UNDECLARED_EFFECTS_ACCEPTED,
    DEVIATION_UNDECLARED_EFFECTS_DISCARDED,
)
from workflow_interpreter.supervisor import INSTANCE_BRANCH_REF

__all__ = [
    "DEVIATION_INSTANCE_BRANCH_DIVERGED",
    "DEVIATION_PRECONDITION_REFUSED",
    "DEVIATION_UNDECLARED_EFFECTS_ACCEPTED",
    "DEVIATION_UNDECLARED_EFFECTS_DISCARDED",
    "DISPATCH_REQUEST",
    "EFFECTS_NODE",
    "FACT_FRAME",
    "FACT_FRAME_NO_PATHS",
    "FORCED_FIRST_REJECT",
    "GATES_DIR",
    "HALT_AUDIT",
    "HALT_BRANCH_DIVERGED",
    "HALT_CEILING",
    "HALT_FAIL_CLOSED",
    "HALT_FAIL_CODE",
    "HALT_INDETERMINATE",
    "HALT_MISSING_COMMIT",
    "HALT_NODE",
    "HALT_PRECONDITION_REFUSED",
    "INPUT_LABEL",
    "INSTANCE_BRANCH",
    "MAX_GATE_DIFF_BYTES",
    "MAX_TRANSCRIPT_BYTES",
    "NO_ARTIFACT",
    "NO_ARTIFACT_OID",
    "RUNNER_PROTOCOL",
    "RUNNER_PROTOCOL_NO_WRITE_STEP",
    "RUNNER_PROTOCOL_WRITE_STEP",
    "RUN_DEFAULT_MAX_WALL_S",
    "RUN_DEFAULT_POLL_S",
    "RUN_MAX_WALL",
    "WRAPPER_HANDLE",
    "WRAPPER_LOCK",
]

EFFECTS_NODE: Final[str] = "effects"
HALT_NODE: Final[str] = "halt"
NO_ARTIFACT_OID: Final[str] = "0" * 40
WRAPPER_LOCK: Final[str] = "wrapper.lock"
DISPATCH_REQUEST: Final[str] = "dispatch-request.json"
WRAPPER_HANDLE: Final[str] = "wrapper.json"
FORCED_FIRST_REJECT: Final[str] = (
    "§13 test switch: this is the first review round of the instance — return "
    "the outcome `reject` with findings, whatever the artifact looks like"
)
RUNNER_PROTOCOL: Final[str] = """## How this run is judged (§6)

Your work is read from three files whose paths are in your environment, never
from what you say in your reply. Skip any step and the run grades `fail_code`
however good the work was.

{write_step}- Write the repository paths you changed to `$WF_EFFECTS_FILE`, as JSON:
  `{{"paths": ["a/b.py"]}}`. Write `{{"paths": []}}` if you changed none.
- Write EXACTLY ONE JSON object to `$WF_OUTCOME_FILE`:
  `{{"outcome": "<one of: {outcomes}>", "note": "<one line>"}}`. Zero markers,
  two markers, or an outcome outside that list all grade `fail_code`.
- Put structured output that is not a repository change — findings, notes — in
  `$WF_ARTIFACT_DIR`.
"""
"""The §6 channel contract, told to the runner in its own brief.

§6 defines the three channels and their fail-closed semantics but assigns
nobody the duty of COMMUNICATING them, so nothing did: a real runner did the
task, passed verify, and exited 0 having written neither channel (cr-0zc,
found by the live DRILL-27 run). It is composed per node because the legal
outcome set and the write permission are both the node's own.
"""
RUNNER_PROTOCOL_WRITE_STEP: Final[str] = (
    "- `git add` and `git commit` what you change in the repository. "
    "Uncommitted\n  work does not exist to this harness.\n"
)
RUNNER_PROTOCOL_NO_WRITE_STEP: Final[str] = (
    "- Do NOT write to the repository. This node is `writes = false`, so any "
    "change\n  it leaves in the tree is out of scope and is flagged for a "
    "human to read.\n"
)
FACT_FRAME: Final[str] = """## What this node is (pinned, §3.1)

- node: `{node}` in graph `{graph_id}` v{graph_version}
- round: {round_no}
- repository writes: {writes}
- paths whose changes are expected here: {allowed_paths}
- checks that will run against your work: {verify}

These facts come from the pinned graph and decide how the run is graded. Where
the instructions below disagree with them, the declared facts win.
"""
"""The activation-level facts a runner cannot derive from its inputs (ADR 0002).

Separate from `RUNNER_PROTOCOL`, which states the §6 channel contract: that is
per-node and stable, this is per-activation. `allowed_paths` is described as
what §7.5 makes it — an exemption from undeclared-effect reporting — never as a
containment bound, which ADR 0001 records it is not.
"""
FACT_FRAME_NO_PATHS: Final[str] = "none declared"
INPUT_LABEL: Final[str] = "## Input `{name}` (from {producer})"
"""Inputs arrive concatenated; without a label two of them are one wall of text."""
GATES_DIR: Final[str] = "gates"
MAX_TRANSCRIPT_BYTES: Final[int] = 4096
MAX_GATE_DIFF_BYTES: Final[int] = 1024
"""A rendered gate diff is bounded HERE, not by `_emit`: `_emit` truncates only
its `tail` and `stalled` fields and otherwise drops the whole report for
`{"truncated": true}`, so an unbounded `--stat` would cost the approver the
inbox path and template as well as the diff."""
NO_ARTIFACT: Final[str] = "(no artifact)"
"""What a gate with no committed artifact renders instead of a diff: every halt
gate, and any transition gate whose source pinned nothing."""
RUN_DEFAULT_POLL_S: Final[float] = 30.0
RUN_DEFAULT_MAX_WALL_S: Final[float] = 8 * 60 * 60
RUN_MAX_WALL: Final[str] = "run max_wall"
INSTANCE_BRANCH: Final[str] = INSTANCE_BRANCH_REF
HALT_AUDIT: Final[str] = "audit:{reason}"
HALT_MISSING_COMMIT: Final[str] = "missing_commit intended_base_commit {commit}"
HALT_CEILING: Final[str] = "ceiling:{detail}"
HALT_INDETERMINATE: Final[str] = "indeterminate:{detail}"
HALT_FAIL_CLOSED: Final[str] = "fail_closed:{reason}"
HALT_FAIL_CODE: Final[str] = "fail_code:{node}:{activation_id}"
HALT_BRANCH_DIVERGED: Final[str] = "instance_branch_diverged:{node}:{activation_id}"
HALT_PRECONDITION_REFUSED: Final[str] = "precondition_refused:{node}:{activation_id}"
