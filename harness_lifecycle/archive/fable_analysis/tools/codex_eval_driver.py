#!/usr/bin/env python3
"""Codex (GPT-5.5 xhigh) deep row-evaluation workers for the fable_analysis.

One `codex exec` per shard, read-only sandbox, strict --output-schema. Codex reads
the capability source files itself (repo cwd); the driver validates the returned
evaluations, joins them back onto the input rows (echo fields come from the input,
so Codex cannot corrupt them), stamps provenance, and writes the shard artifacts:

  shards/<sid>.row_evaluations.jsonl   (evaluated_by: gpt-5.5-xhigh)
  shards/<sid>.notes.md

Resumable: a shard whose output file already has all input source_ids is skipped.
"""
from __future__ import annotations
import concurrent.futures as cf
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FA = Path(__file__).resolve().parent.parent
SP = FA / "tools" / "scratch"
SP.mkdir(parents=True, exist_ok=True)
SCHEMA = Path(__file__).resolve().parent / "eval_schema.json"
WORKERS = 5
TIMEOUT_S = 2400
SCORES = ["effectiveness", "instruction_quality", "clarity", "precision", "concision", "structural_efficiency"]
VERDICTS = {"adopt", "merge", "rewrite", "defer", "reject_after_review"}

CONTRACT = """You are a row-evaluation worker for a harness-capability usefulness analysis.
You run inside the repo at the current working directory. Your sandbox is read-only:
you can read any repo file (cat/sed/rg) but MUST NOT write or modify anything.

Each input row below is one distinct capability (skill / agent / command / rule /
hook / plugin / MCP) from external agent-harness repos or from our own harness. It
carries two prior SHALLOW verdicts (fable_useful, gpt_useful). Your job is the DEEP
review those passes did not do.

The developer works primarily in Python (+ shell, HTML, SQL); capabilities specific
to other major languages (TS/JS/Rust/C/C++/Go/Java/...) are low value. Generic /
language-neutral agent-coding capabilities are judged on their merit for a
Python-centric agentic workflow. The end use: decide what to adopt, merge, rewrite,
defer, or reject for this repo's reusable harness.

Per row:
1. Understand what it is and what concrete problem it solves. Use the row fields
   first; when thin or ambiguous, or to judge overlap, READ the file(s) in its
   source_paths (repo-relative). If a path is stale, find the capability by name
   under reference_harnesses/, .claude/, .codex/, mvp-harness/.
2. Score 1-5 (1 poor/harmful, 3 adequate-with-revision, 5 excellent/reusable):
   effectiveness, instruction_quality, clarity, precision, concision,
   structural_efficiency.
3. actual_usefulness_verdict: adopt | merge | rewrite | defer | reject_after_review.
   reject_after_review is allowed even though the row passed the shallow filter.
4. overlap_with_existing: does it duplicate/overlap an existing local capability in
   .codex/, .claude/, or mvp-harness/? Name the local capability if so.
5. candidate_cluster_key: short kebab-case key grouping items that solve the SAME
   problem (e.g. code-review-core, systematic-debugging, harness-adoption).
6. evidence_notes: what you inspected (files read, or why not needed).
   rationale: one line justifying the verdict.

Judge each item on its own merit; the shallow fable/gpt labels are prioritization
signals, not truth — disagree freely.

Output STRICTLY per the enforced JSON schema: {"evaluations": [...one object per
input row, echoing its source_id, in input order...], "notes_markdown": "short
shard notes: assumptions, evidence inspected, weak rows, cluster relationships"}.
"""


def shard_ids() -> list[str]:
    manifest = json.loads((FA / "shard_manifest.json").read_text())
    return [s["shard_id"] for s in manifest["shards"]]


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def valid_eval(r: dict) -> bool:
    return (r.get("actual_usefulness_verdict") in VERDICTS
            and all(isinstance(r.get(s), int) and 1 <= r[s] <= 5 for s in SCORES))


def run_shard(sid: str) -> str:
    inp = load_jsonl(FA / "shards" / f"{sid}.input.jsonl")
    out_path = FA / "shards" / f"{sid}.row_evaluations.jsonl"
    done_ids = {r["source_id"] for r in load_jsonl(out_path) if valid_eval(r)}
    todo = [r for r in inp if r["source_id"] not in done_ids]
    if not todo:
        return f"{sid}: already complete ({len(inp)} rows)"

    # compact input rows: keep judgment-relevant fields only
    lines = []
    for r in todo:
        lines.append(json.dumps({
            "source_id": r["source_id"], "kind": r["kind"], "category": r["category"],
            "name": r["name"], "harnesses": r["harnesses"], "in_ours": r.get("in_ours", ""),
            "fable_useful": r["fable_useful"], "fable_reason": r["fable_reason"],
            "gpt_useful": r["gpt_useful"], "gpt_reason": r["gpt_reason"],
            "description": r["description"], "source_paths": r.get("source_paths", []),
        }, ensure_ascii=False))
    prompt = CONTRACT + "\nINPUT ROWS (" + str(len(todo)) + "):\n" + "\n".join(lines)

    last = SP / f"codex_eval_{sid}.last.txt"
    cmd = ["codex", "exec", "-m", "gpt-5.6-sol", "-c", "model_reasoning_effort=xhigh",
           "-s", "read-only", "--skip-git-repo-check",
           "--output-schema", str(SCHEMA), "-o", str(last), prompt]
    try:
        subprocess.run(cmd, cwd=REPO, capture_output=True, text=True,
                       timeout=TIMEOUT_S, check=True)
        obj = json.loads(last.read_text(encoding="utf-8"))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError, FileNotFoundError) as exc:
        return f"{sid}: FAILED {type(exc).__name__}"

    by_id = {e["source_id"]: e for e in obj.get("evaluations", []) if valid_eval(e)}
    rows_out, missing = [], []
    for r in todo:
        e = by_id.get(r["source_id"])
        if e is None:
            missing.append(r["source_id"])
            continue
        merged = {
            "source_id": r["source_id"], "kind": r["kind"], "category": r["category"],
            "name": r["name"], "harnesses": r["harnesses"],
            "fable_useful": r["fable_useful"], "fable_reason": r["fable_reason"],
            "fable_tag": r["fable_tag"], "gpt_useful": r["gpt_useful"],
            "gpt_reason": r["gpt_reason"], "gpt_tag": r["gpt_tag"],
            "consensus": r["consensus"], "agree": r["agree"], "description": r["description"],
            "problem_solved": e["problem_solved"],
            **{s: e[s] for s in SCORES},
            "actual_usefulness_verdict": e["actual_usefulness_verdict"],
            "rationale": e["rationale"], "overlap_with_existing": e["overlap_with_existing"],
            "candidate_cluster_key": e["candidate_cluster_key"],
            "evidence_notes": e["evidence_notes"], "evaluated_by": "gpt-5.6-sol-xhigh",
        }
        rows_out.append(merged)

    with out_path.open("a", encoding="utf-8") as fh:
        for r in rows_out:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    notes_path = FA / "shards" / f"{sid}.notes.md"
    header = f"# Shard notes — {sid} (evaluator: Codex GPT-5.6-Sol xhigh)\n\n"
    with notes_path.open("a", encoding="utf-8") as fh:
        fh.write(header + obj.get("notes_markdown", "").strip() + "\n")
    status = f"{sid}: wrote {len(rows_out)}/{len(todo)}"
    if missing:
        status += f" MISSING={missing[:5]}"
    return status


def main(argv: list[str]) -> int:
    targets = argv or [s for s in shard_ids()]
    results = []
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {ex.submit(run_shard, s): s for s in targets}
        for f in cf.as_completed(futs):
            r = f.result()
            results.append(r)
            print(r, flush=True)
    fails = [r for r in results if "FAILED" in r or "MISSING" in r]
    print(f"\n{len(results) - len(fails)}/{len(results)} shards clean; issues: {fails or 'none'}")
    return 0 if not fails else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
