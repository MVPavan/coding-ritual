#!/usr/bin/env python3
"""Compare this analysis's row verdicts against codex_analysis's, per source_id.
Writes fable_vs_codex_diff.md with agreement stats and the sharpest divergences."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

FA = Path(__file__).resolve().parent.parent
CODEX = FA.parent / "codex_analysis"
SCORES = ["effectiveness", "instruction_quality", "clarity", "precision", "concision", "structural_efficiency"]
RANK = {"adopt": 0, "merge": 1, "rewrite": 2, "defer": 3, "reject_after_review": 4}


def load(path: Path) -> dict[str, dict]:
    return {r["source_id"]: r for r in
            (json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip())}


def main() -> int:
    ours = load(FA / "row_evaluations.jsonl")
    codex = load(CODEX / "row_evaluations.jsonl")
    common = sorted(set(ours) & set(codex))
    only_ours, only_codex = sorted(set(ours) - set(codex)), sorted(set(codex) - set(ours))

    exact = sum(1 for s in common if ours[s]["actual_usefulness_verdict"] == codex[s]["actual_usefulness_verdict"])
    within1 = sum(1 for s in common
                  if abs(RANK[ours[s]["actual_usefulness_verdict"]] - RANK[codex[s]["actual_usefulness_verdict"]]) <= 1)
    pairs = Counter((codex[s]["actual_usefulness_verdict"], ours[s]["actual_usefulness_verdict"]) for s in common)

    diverg = sorted(
        (s for s in common
         if abs(RANK[ours[s]["actual_usefulness_verdict"]] - RANK[codex[s]["actual_usefulness_verdict"]]) >= 3),
        key=lambda s: -abs(RANK[ours[s]["actual_usefulness_verdict"]] - RANK[codex[s]["actual_usefulness_verdict"]]))

    avg_ours = {s: round(sum(ours[i][s] for i in common) / len(common), 2) for s in SCORES}
    avg_codex = {s: round(sum(codex[i][s] for i in common) / len(common), 2) for s in SCORES}
    prov = Counter(ours[s].get("evaluated_by", "?") for s in common)

    L = [
        "# Fable analysis vs Codex analysis — row-level diff",
        "",
        f"Common evaluated rows: **{len(common)}** (ours-only: {len(only_ours)}, codex-only: {len(only_codex)}).",
        "",
        "**Provenance caveat:** in this analysis 148 rows were evaluated by Fable-5 xhigh",
        "workers and 481 by Codex GPT-5.6-Sol xhigh workers (user-directed pivot after",
        "Claude session limits; per-row `evaluated_by` records which). So for most rows",
        "this diff compares GPT-5.6-Sol against the earlier GPT-5.5 analysis — the",
        "*coordination, clustering and synthesis* are Fable's, the row verdicts are mixed.",
        "",
        "## Agreement",
        "",
        f"- Exact verdict agreement: **{exact}/{len(common)}** ({round(exact / len(common) * 100)}%)",
        f"- Within one step on the adopt→reject scale: **{within1}/{len(common)}** ({round(within1 / len(common) * 100)}%)",
        "",
        "## Verdict cross-table (codex → this analysis)",
        "",
        "| codex \\ ours | " + " | ".join(RANK) + " |",
        "|---|" + "---|" * len(RANK),
    ]
    for cv in RANK:
        L.append(f"| **{cv}** | " + " | ".join(str(pairs.get((cv, ov), 0)) for ov in RANK) + " |")
    L += [
        "",
        "## Average scores on common rows",
        "",
        "| dimension | this analysis | codex |",
        "|---|---|---|",
    ]
    for s in SCORES:
        L.append(f"| {s} | {avg_ours[s]} | {avg_codex[s]} |")
    L += [
        "",
        f"Row-evaluator provenance (this analysis): {dict(prov)}",
        "",
        f"## Sharpest divergences (≥3 steps apart): {len(diverg)}",
        "",
    ]
    for s in diverg[:20]:
        L.append(f"- `{s}` ({ours[s]['name']}): codex=**{codex[s]['actual_usefulness_verdict']}** vs "
                 f"ours=**{ours[s]['actual_usefulness_verdict']}** — ours: {ours[s]['rationale'][:140]}")
    if len(diverg) > 20:
        L.append(f"- … and {len(diverg) - 20} more (grep row_evaluations.jsonl).")
    (FA / "fable_vs_codex_diff.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"common={len(common)} exact={exact} ({round(exact/len(common)*100)}%) "
          f"within1={within1} ({round(within1/len(common)*100)}%) sharp_divergences={len(diverg)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
