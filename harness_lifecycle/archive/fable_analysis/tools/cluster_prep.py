#!/usr/bin/env python3
"""Group merged row evaluations by candidate_cluster_key into raw clusters and emit
a compact consolidation input for the coordinator to merge into primary clusters.
Deterministic; no judgment here. Paths resolve relative to this file."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

FA = Path(__file__).resolve().parent.parent
SCORES = ["effectiveness", "instruction_quality", "clarity", "precision", "concision", "structural_efficiency"]


def norm_key(k: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (k or "uncategorized").lower()).strip("-") or "uncategorized"


def main() -> int:
    rows = [json.loads(l) for l in (FA / "row_evaluations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        r["_avg"] = round(sum(r[s] for s in SCORES) / len(SCORES), 2)
        groups[norm_key(r.get("candidate_cluster_key"))].append(r)

    raw = []
    for key, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        raw.append({
            "cluster_key": key,
            "count": len(members),
            "kinds": dict(Counter(m["kind"] for m in members)),
            "verdicts": dict(Counter(m["actual_usefulness_verdict"] for m in members)),
            "avg_score": round(sum(m["_avg"] for m in members) / len(members), 2),
            "source_ids": [m["source_id"] for m in members],
            "sample_names": [m["name"] for m in members[:8]],
        })
    (FA / "raw_clusters.json").write_text(json.dumps(raw, indent=2))

    lines = [f"{len(raw)} raw cluster keys over {len(rows)} rows. Consolidate into "
             "primary clusters (group keys that solve the SAME problem).", ""]
    for c in raw:
        kinds = ",".join(f"{k}:{n}" for k, n in c["kinds"].items())
        lines.append(f'- {c["cluster_key"]} (n={c["count"]}, {kinds}, avg={c["avg_score"]}) '
                     f'e.g. {", ".join(c["sample_names"][:6])}')
    (FA / "cluster_consolidation_input.md").write_text("\n".join(lines) + "\n")

    print(f"rows={len(rows)} raw_cluster_keys={len(raw)}")
    print(f"top keys: {[(c['cluster_key'], c['count']) for c in raw[:12]]}")
    print(f"singletons: {sum(1 for c in raw if c['count'] == 1)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
