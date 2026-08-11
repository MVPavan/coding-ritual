#!/usr/bin/env python3
"""Merge shard row-evaluations into row_evaluations.jsonl and verify coverage.

Asserts: every included source_id evaluated exactly once, no excluded id present,
all scores 1-5, all verdicts valid. Prints distributions (incl. per-evaluator
provenance). Run from anywhere; paths resolve relative to this file.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

FA = Path(__file__).resolve().parent.parent
HL = FA.parent
SCORES = ["effectiveness", "instruction_quality", "clarity", "precision", "concision", "structural_efficiency"]
VERDICTS = {"adopt", "merge", "rewrite", "defer", "reject_after_review"}
REQUIRED = {
    "source_id", "kind", "category", "name", "harnesses", "fable_useful", "fable_reason",
    "fable_tag", "gpt_useful", "gpt_reason", "gpt_tag", "consensus", "agree", "description",
    "problem_solved", *SCORES, "actual_usefulness_verdict", "rationale",
    "overlap_with_existing", "candidate_cluster_key", "evidence_notes",
}


def included_excluded() -> tuple[set[str], set[str]]:
    inc, exc = set(), set()
    for r in csv.DictReader((HL / "capability_usefulness.csv").open(encoding="utf-8")):
        (exc if r["fable_useful"] == "no" and r["gpt_useful"] == "no" else inc).add(r["id"])
    return inc, exc


def main() -> int:
    inc, exc = included_excluded()
    rows: list[dict] = []
    problems: list[str] = []
    seen: Counter = Counter()

    for f in sorted((FA / "shards").glob("*.row_evaluations.jsonl")):
        for ln, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError as e:
                problems.append(f"{f.name}:{ln} JSON error {e}")
                continue
            miss = REQUIRED - set(r)
            if miss:
                problems.append(f"{f.name}:{ln} {r.get('source_id', '?')} missing {sorted(miss)}")
            for s in SCORES:
                v = r.get(s)
                if not isinstance(v, int) or not 1 <= v <= 5:
                    problems.append(f"{r.get('source_id', '?')} bad {s}={v!r}")
            if r.get("actual_usefulness_verdict") not in VERDICTS:
                problems.append(f"{r.get('source_id', '?')} bad verdict {r.get('actual_usefulness_verdict')!r}")
            # rows evaluated before provenance stamping were Fable wave-1 workers
            r.setdefault("evaluated_by", "fable-5-xhigh")
            seen[r["source_id"]] += 1
            rows.append(r)

    dupes = [sid for sid, n in seen.items() if n > 1]
    missing = inc - set(seen)
    excluded_present = exc & set(seen)

    rows.sort(key=lambda r: (r["kind"], r["name"].lower(), r["source_id"]))
    (FA / "row_evaluations.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

    print(f"included={len(inc)} excluded={len(exc)} evaluated_unique={len(seen)} rows_written={len(rows)}")
    print(f"missing (included not evaluated): {len(missing)} {sorted(missing)[:10]}")
    print(f"duplicates: {len(dupes)} {dupes[:10]}")
    print(f"excluded-but-present: {len(excluded_present)} {sorted(excluded_present)[:10]}")
    print(f"schema problems: {len(problems)}")
    for p in problems[:15]:
        print("  -", p)
    print(f"verdicts: {dict(Counter(r['actual_usefulness_verdict'] for r in rows))}")
    print(f"evaluated_by: {dict(Counter(r['evaluated_by'] for r in rows))}")
    avg = {s: round(sum(r[s] for r in rows if isinstance(r.get(s), int)) / max(1, len(rows)), 2) for s in SCORES}
    print(f"avg scores: {avg}")
    ok = not missing and not dupes and not excluded_present and not problems
    print("COVERAGE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
