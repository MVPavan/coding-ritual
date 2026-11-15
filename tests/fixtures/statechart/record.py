"""Record what the real jar prints for each fixture model, once, so the parser
and chart tests replay it without Java.

    JAVA=... TLA2TOOLS=... python3 tests/fixtures/statechart/record.py [CASE ...]

Writes recorded/<case>.json: every TLC run the check and the property-level
probes made, in order, with its request, exit code, output and dot dump,
absolute paths replaced by placeholders.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / ".claude/skills/statechart/scripts"))

from statechart_lib import tlc

MODELS = HERE / "models"
# case: (spec, with its configuration beside it as SPEC.cfg; rerun bound)
CASES: dict[str, tuple[str, int]] = {
    name: (f"{name}.tla", tlc.BOUND)
    for name in (
        "Light", "Ghost", "Counter", "Stuck", "Named", "Checkout", "Loop", "Stall",
        "Fence", "Bad", "Undef", "DivZero", "Asrt", "InitOnly", "NoInit", "Outside",
        "Doors", "Swap", "Big", "Upload", "Retry", "InitialWarning", "Frontier",
        "Collision", "InitialProperty", "AfterError", "Quoted", "Escapes",
        "RegionMarks", "Joint", "StartBad", "UnusedTemporal", "TrailingTheorem",
        "UnusedArgument", "Partial", "CompactInfix", "MultilineHead", "SameLine",
        "TopArgument", "Temporals", "InitSlowRepeat", "BoxFirst", "BoxLater",
        "BoxManySolo", "Untraced", "UntracedStart", "UntracedPartial", "UntracedDeadlock",
        "PathExtra", "Hidden",
    )
} | {
    "UsesHelper": ("sib/UsesHelper.tla", tlc.BOUND),
    "Big-bound": ("Big.tla", 100),
}  # fmt: skip


def normalise(text: str, work: Path) -> str:
    text = text.replace(str(work), "<work>").replace(str(MODELS), "<models>")
    text = re.sub(r"Parsing file /tmp/(\w+\.tla)", r"Parsing file <tmp>/\1", text)
    return re.sub(r"\[pid: \d+\]", "[pid: 0]", text)


def record(case: str, java: str, jar: Path) -> Path:
    spec_name, bound = CASES[case]
    spec = MODELS / spec_name
    config = tlc.parse_config(spec.with_suffix(".cfg"))
    runs: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        runner = tlc.JavaRunner(java, jar, spec, config, work, bound)

        def recording(request: tlc.Request) -> tlc.Result:
            result = runner(request)
            runs.append({
                "request": request.describe(),
                "code": result.code,
                "output": normalise(result.output, work),
                "dot": result.dot,
            })  # fmt: skip
            return result

        try:
            dot = tlc.check(config, recording, bound).dot
            tlc.property_levels(config, recording)  # TLC's level probes
        except (tlc.InputError, tlc.CheckError) as stopped:
            print(f"{case}: {type(stopped).__name__}: {str(stopped).splitlines()[0]}")
            dot = ""
    # Keep only the dot dump the check draws; the others would only add size.
    for run in runs:
        if run["dot"] != dot:
            run["dot"] = ""
    target = HERE / "recorded" / f"{case}.json"
    target.parent.mkdir(exist_ok=True)
    body = {"spec": spec_name, "bound": bound, "runs": runs}
    target.write_text(json.dumps(body, indent=1) + "\n")
    return target


def main() -> None:
    java = os.environ.get("JAVA", "java")
    jar = Path(os.environ["TLA2TOOLS"])
    for case in sys.argv[1:] or sorted(CASES):
        path = record(case, java, jar)
        codes = [run["code"] for run in json.loads(path.read_text())["runs"]]
        print(f"{case}: {len(codes)} runs, exit codes {codes}")


if __name__ == "__main__":
    main()
