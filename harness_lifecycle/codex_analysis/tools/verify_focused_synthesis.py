#!/usr/bin/env python3
"""Read-only verification for the focused three-harness Codex synthesis."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[3]
ANALYSIS = ROOT / "harness_lifecycle/codex_analysis"
FOCUSED = ANALYSIS / "focused-three-harnesses"
CSV_PATH = ROOT / "harness_lifecycle/capability_usefulness.csv"
GLOBAL_EVAL_PATH = ANALYSIS / "row_evaluations.jsonl"
GLOBAL_CLUSTER_PATH = ANALYSIS / "clusters.json"
GLOBAL_EXCLUDED_PATH = ANALYSIS / "excluded_both_rejected.jsonl"

WANTED = ("agent-skills", "mattpocock_skills", "superpowers")
EXPECTED_PER_REPO = {
    "agent-skills": 44,
    "mattpocock_skills": 36,
    "superpowers": 19,
}
EXPECTED_EXCLUDED = (
    "skill:migratetoshoehorn",
    "skill:setupmattpocockskills",
    "skill:setupprecommit",
)
EXPECTED_UNIQUE = 97
EXPECTED_INCLUDED = 94
EXPECTED_CLUSTERS = 30

PROTECTED_SHA256 = {
    "harness_lifecycle/capability_usefulness.csv": "81874dcaf09fb92f80f82dabd26093b184341b5bdd81a62bb012a46d8b83e05c",
    "harness_lifecycle/ledger.json": "b7cbb49a4b8fe8e0bd4e1cf6e085387ab98cd42a7e57d6ab85c3b5e833384d82",
    "harness_lifecycle/codex_analysis/excluded_both_rejected.jsonl": "5c7ffd8336ffcd543386992aba38ad2faf67f8311d865ce3d9be73ae8357b8d7",
    "harness_lifecycle/codex_analysis/row_evaluations.jsonl": "e74710f99b4b034b25703f5de7a56e8ad0327a0a85b0d36c1a1761ad7913be13",
    "harness_lifecycle/codex_analysis/clusters.json": "3ac6d3da1cca4819d801b93c0d1cbe0fc48d62dda60392198568a46916c37ccc",
    "harness_lifecycle/codex_analysis/cluster_review.md": "983eae0a96518c8082f6f138a25fa781a13633d373a70aa7b9991a056272a373",
    "harness_lifecycle/codex_analysis/final_synthesis.md": "100bc55ff2ddace0e6797e7c830ad84776f48e4ed32cf9eba9b5315a770e49d7",
    "harness_lifecycle/codex_analysis/shard_manifest.json": "662b1c285b90a7ec540dc7ffe0f4ec73e6f83f1c5751fc01ea2d43c35de9f4d8",
    "harness_lifecycle/codex_analysis/run-notes.md": "c0ca53f57562902d8d2a074a6514fa6b667c1754ca041a6c0f1e4076af37fbce",
    "harness_lifecycle/codex_analysis/session-board.md": "1dfa43f73569740cc140eaaa4772b2c5ddc35100a49470bb6357b65717163f26",
    "harness_lifecycle/codex_analysis/session-goal.md": "e6a08f54f63af9d6dcd436c79eb7b5247c673816a1dea3d7d10e9fb875394175",
}

REQUIRED_QUALITATIVE_FIELDS = (
    "recommended_capability",
    "recommended_surface",
    "decision",
    "priority",
    "problem_solved",
    "why_this_is_better",
    "reuse_or_merge_plan",
    "risks_or_open_questions",
    "selection_mode",
)
DERIVED_FIELDS = (
    "source_ids",
    "source_names",
    "source_harnesses",
    "source_count",
    "kinds",
    "verdict_counts",
    "candidate_cluster_keys",
    "average_score",
    "best_source_ids",
)
SCORE_FIELDS = (
    "effectiveness",
    "instruction_quality",
    "clarity",
    "precision",
    "concision",
    "structural_efficiency",
)
DECISIONS = {
    "adopt_as_is",
    "adapt",
    "merge",
    "defer",
    "reject_after_review",
}
PRIORITIES = {"P0", "P1", "P2", "P3"}
MACHINE_PATH_RE = re.compile(r"(?:/(?:home|Users|data)/[^/\s]+/|[A-Za-z]:\\Users\\)")


class VerifyError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerifyError(message)


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerifyError(f"missing file: {path.relative_to(ROOT)}") from exc
    except json.JSONDecodeError as exc:
        raise VerifyError(f"invalid JSON: {path.relative_to(ROOT)}: {exc}") from exc


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise VerifyError(f"missing file: {path.relative_to(ROOT)}") from exc
    rows = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise VerifyError(
                f"invalid JSONL: {path.relative_to(ROOT)}:{number}: {exc}"
            ) from exc
        require(isinstance(value, dict), f"non-object JSONL row: {path}:{number}")
        rows.append(value)
    return rows


def load_csv() -> list[dict[str, str]]:
    raw = CSV_PATH.read_bytes()
    require(raw.endswith(b"\r\n"), "canonical CSV no longer ends with CRLF")
    require(raw.count(b"\n") == raw.count(b"\r\n"), "canonical CSV is not CRLF-only")
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"), newline="")))


def harnesses(value: str) -> set[str]:
    return {part.strip() for part in value.split(";") if part.strip()}


def selected_harnesses(value: str) -> list[str]:
    values = harnesses(value)
    return [repo for repo in WANTED if repo in values]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_protected() -> None:
    for relative, expected in PROTECTED_SHA256.items():
        require(sha256(ROOT / relative) == expected, f"protected artifact changed: {relative}")


def row_average(row: dict[str, Any]) -> float:
    return sum(int(row[field]) for field in SCORE_FIELDS) / len(SCORE_FIELDS)


def derive_cluster(
    source_ids: Sequence[str], eval_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    rows = [eval_by_id[source_id] for source_id in source_ids]
    kinds = Counter(str(row["kind"]) for row in rows)
    verdicts = Counter(str(row["actual_usefulness_verdict"]) for row in rows)
    candidate_keys = sorted({str(row["candidate_cluster_key"]) for row in rows})
    average = round(
        sum(int(row[field]) for row in rows for field in SCORE_FIELDS)
        / (len(rows) * len(SCORE_FIELDS)),
        2,
    )
    best = sorted(
        source_ids,
        key=lambda source_id: (-row_average(eval_by_id[source_id]), source_id),
    )[:3]
    return {
        "source_ids": list(source_ids),
        "source_names": [str(row["name"]) for row in rows],
        "source_harnesses": {
            str(row["source_id"]): selected_harnesses(str(row["harnesses"]))
            for row in rows
        },
        "source_count": len(rows),
        "kinds": dict(sorted(kinds.items())),
        "verdict_counts": dict(sorted(verdicts.items())),
        "candidate_cluster_keys": candidate_keys,
        "average_score": average,
        "best_source_ids": best,
    }


def md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def render_review(clusters: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# Focused Cluster Review",
        "",
        "Codex coordinator review of the 30 problem clusters occupied by the 94 eligible capabilities from `agent-skills`, `mattpocock_skills`, and `superpowers`.",
        "",
        "| Cluster | Decision | Priority | Source IDs | Source Names | Best Candidates | Selection Mode |",
        "|---|---|---|---|---|---|---|",
    ]
    for cluster in clusters:
        lines.append(
            "| "
            + " | ".join(
                (
                    md(f"`{cluster['cluster_id']}` {cluster['recommended_capability']}"),
                    md(f"`{cluster['decision']}`"),
                    md(f"`{cluster['priority']}`"),
                    md("<br>".join(f"`{source_id}`" for source_id in cluster["source_ids"])),
                    md("<br>".join(cluster["source_names"])),
                    md(", ".join(cluster["best_source_ids"])),
                    md(cluster["selection_mode"]),
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_synthesis(
    clusters: Sequence[dict[str, Any]],
    csv_by_id: dict[str, dict[str, str]],
    excluded_ids: Sequence[str],
) -> str:
    decisions = Counter(str(cluster["decision"]) for cluster in clusters)
    priorities = Counter(str(cluster["priority"]) for cluster in clusters)
    lines = [
        "# Focused Final Synthesis: Agent Skills, Matt Pocock Skills, And Superpowers",
        "",
        "This synthesis considers only canonical capabilities whose provenance includes `agent-skills`, `mattpocock_skills`, or `superpowers`. It covers 97 unique canonical rows: 94 deep evaluations across 30 problem clusters and three explicit prior exclusions. Recommendations are analysis inputs, not adoption-ledger decisions.",
        "",
        "## Recommendation Summary",
        "",
        "| Dimension | Value | Count |",
        "|---|---|---:|",
    ]
    for decision, count in sorted(decisions.items()):
        lines.append(f"| Decision | `{decision}` | {count} |")
    for priority, count in sorted(priorities.items()):
        lines.append(f"| Priority | `{priority}` | {count} |")
    lines.extend(
        [
            "",
            "## Cluster Recommendations",
            "",
            "| recommended_capability | recommended_surface | decision | source_ids | source_names | cluster_id | problem_solved | why_this_is_better | reuse_or_merge_plan | priority | risks_or_open_questions |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for cluster in clusters:
        values = (
            cluster["recommended_capability"],
            cluster["recommended_surface"],
            f"`{cluster['decision']}`",
            "<br>".join(f"`{source_id}`" for source_id in cluster["source_ids"]),
            "<br>".join(cluster["source_names"]),
            f"`{cluster['cluster_id']}`",
            cluster["problem_solved"],
            cluster["why_this_is_better"],
            cluster["reuse_or_merge_plan"],
            f"`{cluster['priority']}`",
            cluster["risks_or_open_questions"],
        )
        lines.append("| " + " | ".join(md(value) for value in values) + " |")
    lines.extend(
        [
            "",
            "## Explicit Prior Exclusions",
            "",
            "These in-scope canonical rows remain outside deep clustering because both historical shallow reviews rejected them. This focused run records rather than silently promotes them.",
            "",
            "| Source ID | Name | Harness | Fable Reason | Codex Reason |",
            "|---|---|---|---|---|",
        ]
    )
    for source_id in excluded_ids:
        row = csv_by_id[source_id]
        values = (
            f"`{source_id}`",
            row["name"],
            ", ".join(selected_harnesses(row["harnesses"])),
            row["fable_reason"],
            row["gpt_reason"],
        )
        lines.append("| " + " | ".join(md(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def render_notes(clusters: Sequence[dict[str, Any]], excluded_ids: Sequence[str]) -> str:
    decisions = Counter(str(cluster["decision"]) for cluster in clusters)
    priorities = Counter(str(cluster["priority"]) for cluster in clusters)
    lines = [
        "# Focused Synthesis Run Notes",
        "",
        "## Scope",
        "",
        "- Requested harnesses: `agent-skills`, `mattpocock_skills`, and `superpowers`.",
        "- Repository row counts: 44, 36, and 19 respectively.",
        "- Unique canonical union: 97 rows; two rows are shared by `agent-skills` and `superpowers`.",
        "- Included deep evaluations: 94.",
        "- Explicit prior exclusions: 3.",
        "- Focused problem clusters: 30.",
        "",
        "## Method",
        "",
        "- Filtered exact semicolon-delimited provenance tokens, not substrings.",
        "- Reused the existing Codex row evaluations without changing scores or verdicts.",
        "- Preserved existing problem-cluster assignments while removing every out-of-scope source.",
        "- Recomputed all cluster aggregates from the 94 selected rows.",
        "- Rewrote qualitative recommendations from only the selected row evidence.",
        "- Kept the canonical CSV, all-harness analysis, exclusion artifact, and ledger unchanged.",
        "",
        "## Assumptions",
        "",
        "- A shared canonical row is included when any requested harness appears in its provenance.",
        "- Existing Codex row scores and verdicts are reused; this run changes synthesis scope, not row judgments.",
        "- Existing cluster IDs are problem-space anchors, not adoption decisions.",
        "- Focused recommendations remain analysis inputs and do not update the ledger.",
        "",
        "## Recommendation Counts",
        "",
        "| Decision | Clusters |",
        "|---|---:|",
    ]
    for decision, count in sorted(decisions.items()):
        lines.append(f"| `{decision}` | {count} |")
    lines.extend(["", "| Priority | Clusters |", "|---|---:|"])
    for priority, count in sorted(priorities.items()):
        lines.append(f"| `{priority}` | {count} |")
    lines.extend(
        [
            "",
            "## Exclusions",
            "",
            *[f"- `{source_id}`" for source_id in excluded_ids],
            "",
            "These exclusions were not reinterpreted as adoption decisions. They remain traceable in `scope.json` and the final synthesis.",
        ]
    )
    return "\n".join(lines) + "\n"


def assert_text_hygiene(paths: Iterable[Path]) -> None:
    for path in paths:
        text = path.read_text(encoding="utf-8")
        require("\r" not in text, f"CR characters found: {path.relative_to(ROOT)}")
        require(
            not any(line.endswith((" ", "\t")) for line in text.splitlines()),
            f"trailing whitespace found: {path.relative_to(ROOT)}",
        )
        match = MACHINE_PATH_RE.search(text)
        require(not match, f"machine-local path found: {path.relative_to(ROOT)}")


def verify() -> None:
    assert_protected()
    csv_rows = load_csv()
    csv_by_id = {row["id"]: row for row in csv_rows}
    selected_csv = [row for row in csv_rows if selected_harnesses(row["harnesses"])]
    selected_ids = {row["id"] for row in selected_csv}
    require(len(selected_ids) == EXPECTED_UNIQUE, "focused union is not 97 rows")
    per_repo = {
        repo: sum(repo in harnesses(row["harnesses"]) for row in csv_rows)
        for repo in WANTED
    }
    require(per_repo == EXPECTED_PER_REPO, "per-repository counts changed")

    global_rows = load_jsonl(GLOBAL_EVAL_PATH)
    expected_rows = [row for row in global_rows if row["source_id"] in selected_ids]
    focused_rows = load_jsonl(FOCUSED / "row_evaluations.jsonl")
    require(focused_rows == expected_rows, "focused evaluations differ from global source or order")
    focused_ids = {str(row["source_id"]) for row in focused_rows}
    require(len(focused_ids) == len(focused_rows) == EXPECTED_INCLUDED, "included count is not 94")
    excluded_ids = tuple(sorted(selected_ids - focused_ids))
    require(excluded_ids == EXPECTED_EXCLUDED, "focused exclusions differ from expected three")
    global_excluded = {row["id"] for row in load_jsonl(GLOBAL_EXCLUDED_PATH)}
    require(set(excluded_ids) <= global_excluded, "focused exclusions absent from global exclusion set")

    patterns = Counter(
        "+".join(selected_harnesses(row["harnesses"])) for row in selected_csv
    )
    inventory = [
        {
            "source_id": row["id"],
            "name": row["name"],
            "selected_harnesses": selected_harnesses(row["harnesses"]),
            "synthesis_status": (
                "included" if row["id"] in focused_ids else "excluded_both_rejected"
            ),
        }
        for row in selected_csv
    ]
    expected_scope = {
        "schema": "codex-focused-synthesis-scope/v1",
        "requested_harnesses": list(WANTED),
        "repository_row_counts": per_repo,
        "provenance_pattern_counts": dict(sorted(patterns.items())),
        "unique_canonical_rows": EXPECTED_UNIQUE,
        "included_evaluation_rows": EXPECTED_INCLUDED,
        "excluded_rows": len(EXPECTED_EXCLUDED),
        "focused_clusters": EXPECTED_CLUSTERS,
        "excluded_source_ids": list(EXPECTED_EXCLUDED),
        "inventory": inventory,
        "inputs": {
            "capability_csv": "harness_lifecycle/capability_usefulness.csv",
            "global_evaluations": "harness_lifecycle/codex_analysis/row_evaluations.jsonl",
            "global_clusters": "harness_lifecycle/codex_analysis/clusters.json",
            "global_exclusions": "harness_lifecycle/codex_analysis/excluded_both_rejected.jsonl",
        },
        "protected_sha256": PROTECTED_SHA256,
    }
    require(load_json(FOCUSED / "scope.json") == expected_scope, "scope.json is stale")

    global_cluster_data = load_json(GLOBAL_CLUSTER_PATH)
    expected_membership = [
        (
            cluster["cluster_id"],
            [source_id for source_id in cluster["source_ids"] if source_id in focused_ids],
        )
        for cluster in global_cluster_data["clusters"]
        if any(source_id in focused_ids for source_id in cluster["source_ids"])
    ]
    cluster_data = load_json(FOCUSED / "clusters.json")
    clusters = cluster_data.get("clusters", [])
    require(cluster_data.get("schema") == "codex-focused-capability-clusters/v1", "bad schema")
    require(cluster_data.get("requested_harnesses") == list(WANTED), "bad cluster scope")
    require(cluster_data.get("total_clusters") == EXPECTED_CLUSTERS, "cluster total is not 30")
    require(cluster_data.get("total_source_ids") == EXPECTED_INCLUDED, "source total is not 94")
    require(len(clusters) == EXPECTED_CLUSTERS, "cluster list is not 30")
    require(
        [(cluster["cluster_id"], cluster["source_ids"]) for cluster in clusters]
        == expected_membership,
        "focused cluster membership differs from filtered global assignments",
    )

    eval_by_id = {str(row["source_id"]): row for row in focused_rows}
    covered: list[str] = []
    for cluster in clusters:
        source_ids = [str(source_id) for source_id in cluster["source_ids"]]
        expected = derive_cluster(source_ids, eval_by_id)
        for field in DERIVED_FIELDS:
            require(cluster.get(field) == expected[field], f"stale {field}: {cluster['cluster_id']}")
        for field in REQUIRED_QUALITATIVE_FIELDS:
            require(str(cluster.get(field, "")).strip(), f"empty {field}: {cluster['cluster_id']}")
        require(cluster["decision"] in DECISIONS, f"bad decision: {cluster['cluster_id']}")
        require(cluster["priority"] in PRIORITIES, f"bad priority: {cluster['cluster_id']}")
        prose = " ".join(str(cluster[field]) for field in REQUIRED_QUALITATIVE_FIELDS)
        require(
            "Evaluate and route this narrower capability cluster" not in prose,
            f"placeholder synthesis remains: {cluster['cluster_id']}",
        )
        covered.extend(source_ids)
    require(len(covered) == len(set(covered)) == EXPECTED_INCLUDED, "cluster coverage is not unique")
    require(set(covered) == focused_ids, "cluster coverage differs from focused evaluations")

    review = (FOCUSED / "cluster_review.md").read_text(encoding="utf-8")
    synthesis = (FOCUSED / "final_synthesis.md").read_text(encoding="utf-8")
    notes = (FOCUSED / "run-notes.md").read_text(encoding="utf-8")
    require(review == render_review(clusters), "cluster_review.md is stale")
    require(
        synthesis == render_synthesis(clusters, csv_by_id, excluded_ids),
        "final_synthesis.md is stale",
    )
    require(notes == render_notes(clusters, excluded_ids), "run-notes.md is stale")
    assert_text_hygiene(path for path in FOCUSED.iterdir() if path.is_file())
    assert_protected()
    print(
        "PASS focused synthesis: "
        "repos=44/36/19 unique=97 included=94 excluded=3 clusters=30"
    )


def main() -> int:
    try:
        verify()
    except (OSError, UnicodeError, VerifyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
