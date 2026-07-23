#!/usr/bin/env python3
"""Read-only verification for the agent-skills Codex reconciliation.

The script does not generate judgments or mutate canonical artifacts. It checks
the final CSV, row evaluations, clusters, manifest, rendered synthesis, and
protected-file invariants against the reviewed reconciliation contract.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Sequence


ANALYSIS_DIR = Path(__file__).resolve().parents[1]
HL_DIR = ANALYSIS_DIR.parent
REPO_ROOT = HL_DIR.parent
SHARDS_DIR = ANALYSIS_DIR / "shards"

CSV_PATH = HL_DIR / "capability_usefulness.csv"
CATALOG_PATH = HL_DIR / "catalogs" / "agent-skills.json"
LEDGER_PATH = HL_DIR / "ledger.json"
EXCLUDED_PATH = ANALYSIS_DIR / "excluded_both_rejected.jsonl"
GLOBAL_EVAL_PATH = ANALYSIS_DIR / "row_evaluations.jsonl"
CLUSTERS_PATH = ANALYSIS_DIR / "clusters.json"
MANIFEST_PATH = ANALYSIS_DIR / "shard_manifest.json"
CLUSTER_REVIEW_PATH = ANALYSIS_DIR / "cluster_review.md"
FINAL_SYNTHESIS_PATH = ANALYSIS_DIR / "final_synthesis.md"

NEW_INPUT_PATHS = (
    SHARDS_DIR / "agent-skills-skills.input.jsonl",
    SHARDS_DIR / "agent-skills-other.input.jsonl",
)

# Preserve the historical merged-evaluation order so the incremental run does
# not rewrite hundreds of unchanged JSONL lines. New shards are appended.
SHARD_ORDER = (
    "skill-1",
    "skill-2",
    "skill-3",
    "skill-4",
    "agent-1",
    "agent-2",
    "plugin-mcp-1",
    "rule-1",
    "hook-1",
    "command-1",
    "command-2",
    "agent-skills-skills",
    "agent-skills-other",
)

LEDGER_SHA256 = "b7cbb49a4b8fe8e0bd4e1cf6e085387ab98cd42a7e57d6ab85c3b5e833384d82"
EXCLUDED_SHA256 = "5c7ffd8336ffcd543386992aba38ad2faf67f8311d865ce3d9be73ae8357b8d7"

EXPECTED_CSV_ROWS = 907
EXPECTED_HISTORICAL_ROWS = 868
EXPECTED_CATALOG_ROWS = 44
EXPECTED_OVERLAPS = 5
EXPECTED_NEW_ROWS = 39
EXPECTED_EXCLUDED_ROWS = 239
EXPECTED_INCLUDED_ROWS = 668
EXPECTED_CLUSTERS = 75

HISTORICAL_SHALLOW_FIELDS = (
    "fable_useful",
    "fable_reason",
    "fable_tag",
    "gpt_useful",
    "gpt_reason",
    "gpt_tag",
    "consensus",
    "agree",
)
HISTORICAL_SHALLOW_SHA256 = (
    "6f481a2b497c88c95a129b5f066588cdb63832d398f2d2bf768b3cdb5a8345b9"
)

CSV_FIELDS = (
    "id",
    "kind",
    "category",
    "name",
    "harnesses",
    "in_ours",
    "fable_useful",
    "fable_reason",
    "fable_tag",
    "gpt_useful",
    "gpt_reason",
    "gpt_tag",
    "consensus",
    "agree",
    "description",
)

EVAL_FIELDS = (
    "source_id",
    "kind",
    "category",
    "name",
    "harnesses",
    "fable_useful",
    "fable_reason",
    "fable_tag",
    "gpt_useful",
    "gpt_reason",
    "gpt_tag",
    "consensus",
    "agree",
    "description",
    "problem_solved",
    "effectiveness",
    "instruction_quality",
    "clarity",
    "precision",
    "concision",
    "structural_efficiency",
    "actual_usefulness_verdict",
    "rationale",
    "overlap_with_existing",
    "candidate_cluster_key",
    "evidence_notes",
)

SCORE_FIELDS = (
    "effectiveness",
    "instruction_quality",
    "clarity",
    "precision",
    "concision",
    "structural_efficiency",
)

VERDICTS = {"adopt", "merge", "rewrite", "defer", "reject_after_review"}

OVERLAP_IDS = {
    "agent:codereviewer",
    "agent:securityauditor",
    "agent:testengineer",
    "command:plan",
    "skill:testdrivendevelopment",
}

# Every affected canonical row has exactly one primary cluster assignment.
CLUSTER_ASSIGNMENTS = {
    "agent:codereviewer": "C001-code-review-and-change-quality",
    "agent:securityauditor": "C033-security-and-privacy-review",
    "agent:testengineer": "C035-testing-verification-and-regression",
    "agent:webperformanceauditor": "C075-web-quality-performance-and-growth",
    "command:build": "C068-legacy-command-shims",
    "command:codesimplify": "C032-safe-refactor-and-code-simplification",
    "command:plan": "C028-planning-prd-and-implementation-workflows",
    "command:review": "C001-code-review-and-change-quality",
    "command:ship": "C027-multi-review-convergence-gates",
    "command:spec": "C028-planning-prd-and-implementation-workflows",
    "command:test": "C035-testing-verification-and-regression",
    "command:webperf": "C075-web-quality-performance-and-growth",
    "hook:sddcachepostsh": "C018-code-intelligence-context-and-cost-controls",
    "hook:sddcachepresh": "C018-code-intelligence-context-and-cost-controls",
    "hook:sessionstartsh": "C053-hook-session-lifecycle-and-memory",
    "hook:sessionstarttestsh": "C066-hook-authoring-policy-and-plumbing",
    "hook:simplifyignoresh": "C032-safe-refactor-and-code-simplification",
    "hook:simplifyignoretestsh": "C066-hook-authoring-policy-and-plumbing",
    "plugin:agentskills": "C034-skill-authoring-evaluation-and-portfolio",
    "rule:skillscontributing": "C034-skill-authoring-evaluation-and-portfolio",
    "skill:apiandinterfacedesign": "C016-architecture-codebase-and-domain-modeling",
    "skill:browsertestingwithdevtools": "C035-testing-verification-and-regression",
    "skill:cicdandautomation": "C050-deployment-devops-and-operations",
    "skill:codereviewandquality": "C001-code-review-and-change-quality",
    "skill:codesimplification": "C032-safe-refactor-and-code-simplification",
    "skill:contextengineering": "C018-code-intelligence-context-and-cost-controls",
    "skill:debugginganderrorrecovery": "C002-debugging-and-bug-reproduction",
    "skill:deprecationandmigration": "C056-legacy-modernization-and-business-rule-extraction",
    "skill:documentationandadrs": "C020-documentation-research-and-reporting",
    "skill:doubtdrivendevelopment": "C027-multi-review-convergence-gates",
    "skill:frontenduiengineering": "C052-frontend-ui-design-and-visual-artifacts",
    "skill:gitworkflowandversioning": "C022-git-github-and-release-workflows",
    "skill:idearefine": "C030-product-discovery-validation",
    "skill:incrementalimplementation": "C010-phased-implementation-with-validation",
    "skill:interviewme": "C030-product-discovery-validation",
    "skill:observabilityandinstrumentation": "C050-deployment-devops-and-operations",
    "skill:performanceoptimization": "C041-performance-benchmarking",
    "skill:planningandtaskbreakdown": "C028-planning-prd-and-implementation-workflows",
    "skill:securityandhardening": "C033-security-and-privacy-review",
    "skill:shippingandlaunch": "C050-deployment-devops-and-operations",
    "skill:sourcedrivendevelopment": "C013-codex-cited-research",
    "skill:specdrivendevelopment": "C028-planning-prd-and-implementation-workflows",
    "skill:testdrivendevelopment": "C035-testing-verification-and-regression",
    "skill:usingagentskills": "C034-skill-authoring-evaluation-and-portfolio",
}

# Coordinator-reviewed qualitative changes. All fields absent from this map are
# preserved from the current cluster object.
QUALITATIVE_OVERRIDES: dict[str, dict[str, Any]] = {
    "C010-phased-implementation-with-validation": {
        "decision": "merge",
        "priority": "P1",
        "recommended_capability": "Incremental implementation with validation",
        "recommended_surface": "skill",
        "problem_solved": (
            "Execute approved work in thin, risk-first slices with explicit tests, "
            "verification, and review checkpoints."
        ),
        "why_this_is_better": (
            "Combines the existing implementation command with stronger vertical-slice and "
            "feedback-loop guidance without adopting automatic commit behavior."
        ),
        "reuse_or_merge_plan": (
            "Fold thin-slice selection and per-slice validation into the existing phase and "
            "subagent execution workflows; retain repository-specific commit authority."
        ),
        "risks_or_open_questions": (
            "Generic slice-size heuristics and unconditional commits must not override the "
            "target repository's workflow or user authority."
        ),
        "selection_mode": "merge complementary candidates",
    },
    "C013-codex-cited-research": {
        "decision": "merge",
        "priority": "P1",
        "recommended_capability": "Official-documentation-grounded research and development",
        "recommended_surface": "skill/command",
        "problem_solved": (
            "Research current official documentation and ground implementation "
            "decisions in cited, version-aware sources."
        ),
        "why_this_is_better": (
            "Combines cited Codex research with source-driven development so official "
            "documentation informs both recommendations and implementation."
        ),
        "reuse_or_merge_plan": (
            "Keep the existing cited-research command and merge the source-selection, "
            "version-detection, and citation discipline into the routed research skill."
        ),
        "risks_or_open_questions": (
            "Official sources can still drift; verify versions and avoid treating citations "
            "as proof that an implementation is correct."
        ),
        "selection_mode": "merge complementary candidates",
    },
    "C027-multi-review-convergence-gates": {
        "decision": "merge",
        "priority": "P2",
        "recommended_capability": "Bounded adversarial review and convergence",
        "recommended_surface": "skill",
        "problem_solved": (
            "Challenge consequential claims and release decisions with bounded independent "
            "review, then reconcile findings against an explicit contract."
        ),
        "why_this_is_better": (
            "Keeps the useful claim, artifact, adversarial-review, and reconciliation loop "
            "while rejecting mandatory reviewers and cross-model ceremony for routine work."
        ),
        "reuse_or_merge_plan": (
            "Merge the bounded doubt cycle into existing deep review paths and use release "
            "fan-out only when the deployment scope actually warrants it."
        ),
        "risks_or_open_questions": (
            "Overuse creates review theater and latency; triggers must stay risk-based and "
            "the coordinator must independently classify reviewer findings."
        ),
        "selection_mode": "merge complementary candidates",
    },
    "C030-product-discovery-validation": {
        "decision": "merge",
        "priority": "P2",
        "recommended_capability": "Idea refinement and product discovery",
        "recommended_surface": "skill",
        "problem_solved": (
            "Turn an ambiguous idea into tested assumptions, alternative directions, explicit "
            "non-goals, and a decision-ready concept before implementation planning."
        ),
        "why_this_is_better": (
            "Combines product validation with structured divergent/convergent refinement and "
            "targeted intent questions without duplicating the planning phase."
        ),
        "reuse_or_merge_plan": (
            "Fold the best idea-refine and interview patterns into brainstorming/product-lens, "
            "keeping one-question-at-a-time elicitation optional rather than obstructive."
        ),
        "risks_or_open_questions": (
            "Confidence thresholds and mandatory confirmation loops can block progress; stop "
            "once assumptions and success criteria are sufficient for planning."
        ),
        "selection_mode": "merge complementary candidates",
    },
    "C033-security-and-privacy-review": {
        "decision": "merge",
        "priority": "P1",
        "why_this_is_better": (
            "Adds a threat-model-first security pass and stronger hardening guidance to the "
            "existing review lenses without creating another uncoordinated review surface."
        ),
        "risks_or_open_questions": (
            "Security review must stay evidence-based and must not imply that a checklist "
            "or model review proves the system secure."
        ),
    },
    "C041-performance-benchmarking": {
        "decision": "defer",
        "priority": "P2",
        "recommended_capability": "Evidence-driven performance optimization",
        "recommended_surface": "skill",
        "problem_solved": (
            "Profile a real performance problem, isolate the bottleneck, make a bounded "
            "change, and compare representative before/after measurements."
        ),
        "why_this_is_better": (
            "Combines the existing benchmark discipline with a measure, improve, and "
            "re-measure workflow while keeping stack-specific budgets optional."
        ),
        "reuse_or_merge_plan": (
            "Keep as an on-demand performance workflow; reuse profiling and regression "
            "evidence, but derive budgets and tools from the target repository."
        ),
        "risks_or_open_questions": (
            "Premature optimization, unrepresentative benchmarks, and fixed web thresholds "
            "can produce confident but irrelevant improvements."
        ),
        "selection_mode": "defer",
    },
    "C050-deployment-devops-and-operations": {
        "decision": "defer",
        "priority": "P2",
        "recommended_capability": "Optional production operations pack",
        "why_this_is_better": (
            "Groups CI/CD, observability, staged rollout, and launch checks as an optional "
            "production pack instead of loading them into every repository."
        ),
        "reuse_or_merge_plan": (
            "Keep the evidence as a routed optional pack and activate it only for repositories "
            "with real deployment and production-operations needs."
        ),
        "risks_or_open_questions": (
            "Provider-specific examples and operational assumptions require validation against "
            "the target repository before use."
        ),
        "selection_mode": "defer",
    },
    "C056-legacy-modernization-and-business-rule-extraction": {
        "decision": "merge",
        "priority": "P2",
        "recommended_capability": "Deprecation, migration, and legacy modernization",
        "recommended_surface": "skill",
        "problem_solved": (
            "Plan deprecation, incremental migration, business-rule preservation, and legacy "
            "modernization with explicit compatibility and rollback evidence."
        ),
        "why_this_is_better": (
            "Combines the new general deprecation workflow with the existing legacy-analysis "
            "and equivalence-testing evidence instead of treating modernization as a rewrite."
        ),
        "reuse_or_merge_plan": (
            "Merge deprecation decision gates and expand-contract migration patterns into one "
            "repo-grounded modernization skill."
        ),
        "risks_or_open_questions": (
            "Migration safety is domain-specific; require compatibility tests, rollback plans, "
            "and explicit approval for irreversible steps."
        ),
        "selection_mode": "merge complementary candidates",
    },
    "C075-web-quality-performance-and-growth": {
        "decision": "defer",
        "priority": "P2",
        "recommended_capability": "Focused web performance and quality",
        "recommended_surface": "agent/skill",
        "problem_solved": (
            "Measure and review browser-facing performance, Core Web Vitals, and web-specific "
            "quality with sourced metrics and explicit quick/deep modes."
        ),
        "why_this_is_better": (
            "The new auditor provides a focused, metric-honest web-performance workflow while "
            "keeping unrelated growth and generic browser tasks out of the core path."
        ),
        "reuse_or_merge_plan": (
            "Keep as an optional web-project capability and reuse the quick/deep audit split, "
            "metric provenance rules, and ranked findings format."
        ),
        "risks_or_open_questions": (
            "Defer until a browser-facing project needs it; quick-mode findings must remain "
            "clearly labeled as potential impact rather than measured regressions."
        ),
        "selection_mode": "defer",
    },
}

DERIVED_CLUSTER_FIELDS = {
    "source_ids",
    "source_names",
    "source_count",
    "kinds",
    "verdict_counts",
    "candidate_cluster_keys",
    "average_score",
    "best_source_ids",
}

MACHINE_PATH_RE = re.compile(r"(?:/(?:home|Users|data)/[^/\s]+/|[A-Za-z]:\\\\Users\\\\)")


class ReconcileError(RuntimeError):
    """A clear, user-actionable reconciliation failure."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReconcileError(message)


def relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_protected_hashes() -> None:
    require(sha256_file(LEDGER_PATH) == LEDGER_SHA256, "ledger.json hash changed")
    require(
        sha256_file(EXCLUDED_PATH) == EXCLUDED_SHA256,
        "excluded_both_rejected.jsonl hash changed",
    )


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReconcileError(f"missing required file: {relative(path)}") from exc
    except json.JSONDecodeError as exc:
        raise ReconcileError(f"invalid JSON in {relative(path)}: {exc}") from exc


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ReconcileError(f"missing required file: {relative(path)}") from exc
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ReconcileError(
                f"invalid JSONL in {relative(path)}:{number}: {exc}"
            ) from exc
        require(
            isinstance(value, dict),
            f"expected object in {relative(path)}:{number}",
        )
        rows.append(value)
    return rows


def read_csv_rows() -> tuple[list[str], list[dict[str, str]], bytes]:
    raw = CSV_PATH.read_bytes()
    text = raw.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    require(reader.fieldnames == list(CSV_FIELDS), "unexpected capability CSV columns")
    rows = [dict(row) for row in reader]
    return list(reader.fieldnames), rows, raw


def assert_crlf(raw: bytes) -> None:
    require(raw.endswith(b"\r\n"), "capability CSV must end with CRLF")
    require(raw.count(b"\n") == raw.count(b"\r\n"), "capability CSV is not CRLF-only")


def normalized_name(name: str) -> str:
    return "".join(character for character in name.lower() if character.isalnum())


def canonical_id(capability: dict[str, Any]) -> str:
    kind = str(capability.get("kind", ""))
    name = str(capability.get("name", ""))
    require(kind and name, "catalog capability is missing kind or name")
    return f"{kind}:{normalized_name(name)}"


def catalog_mappings() -> tuple[dict[str, str], list[str]]:
    catalog = load_json(CATALOG_PATH)
    capabilities = catalog.get("capabilities", [])
    require(isinstance(capabilities, list), "agent-skills catalog capabilities is not a list")
    require(
        len(capabilities) == EXPECTED_CATALOG_ROWS,
        f"expected {EXPECTED_CATALOG_ROWS} catalog capabilities, found {len(capabilities)}",
    )
    mappings: dict[str, str] = {}
    ordered_ids: list[str] = []
    canonical_ids: set[str] = set()
    for capability in capabilities:
        raw_id = str(capability.get("logical_id", ""))
        require(raw_id and raw_id not in mappings, f"duplicate catalog logical ID: {raw_id}")
        mapped = canonical_id(capability)
        require(mapped not in canonical_ids, f"duplicate canonical catalog ID: {mapped}")
        mappings[raw_id] = mapped
        ordered_ids.append(mapped)
        canonical_ids.add(mapped)
    require(
        set(CLUSTER_ASSIGNMENTS) == canonical_ids,
        "cluster assignment map does not exactly cover the agent-skills catalog",
    )
    require(
        len(OVERLAP_IDS & canonical_ids) == EXPECTED_OVERLAPS,
        "catalog overlap count is not five",
    )
    require(
        len(canonical_ids - OVERLAP_IDS) == EXPECTED_NEW_ROWS,
        "catalog new-row count is not 39",
    )
    return mappings, ordered_ids


def load_new_input_rows(new_ids: set[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in NEW_INPUT_PATHS:
        for raw in load_jsonl(path):
            require(set(raw) == set(CSV_FIELDS), f"unexpected input schema in {relative(path)}")
            rows.append({field: str(raw[field]) for field in CSV_FIELDS})
    by_id = {row["id"]: row for row in rows}
    require(len(by_id) == len(rows), "duplicate IDs across new agent-skills input rows")
    require(set(by_id) == new_ids, "new shard inputs do not exactly cover the 39 new IDs")
    return [by_id[source_id] for source_id in sorted(by_id)]


def shard_ids_in_order() -> list[str]:
    input_ids = {path.name.removesuffix(".input.jsonl") for path in SHARDS_DIR.glob("*.input.jsonl")}
    output_ids = {
        path.name.removesuffix(".row_evaluations.jsonl")
        for path in SHARDS_DIR.glob("*.row_evaluations.jsonl")
    }
    require(input_ids == output_ids, "shard input/output file sets differ")
    require(input_ids == set(SHARD_ORDER), "shard files differ from the expected order set")
    return list(SHARD_ORDER)


def validate_eval(row: dict[str, Any], location: str) -> None:
    require(set(row) == set(EVAL_FIELDS), f"{location} does not have the 26-field schema")
    require(str(row["source_id"]), f"{location} has an empty source_id")
    for field in SCORE_FIELDS:
        value = row[field]
        require(
            isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 5,
            f"{location} has invalid {field}: {value!r}",
        )
    require(
        row["actual_usefulness_verdict"] in VERDICTS,
        f"{location} has invalid verdict: {row['actual_usefulness_verdict']!r}",
    )


def load_shards() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    all_rows: list[dict[str, Any]] = []
    shard_records: list[dict[str, Any]] = []
    seen: set[str] = set()
    for shard_id in shard_ids_in_order():
        input_path = SHARDS_DIR / f"{shard_id}.input.jsonl"
        output_path = SHARDS_DIR / f"{shard_id}.row_evaluations.jsonl"
        inputs = load_jsonl(input_path)
        outputs = load_jsonl(output_path)
        for index, row in enumerate(inputs, 1):
            require(
                set(row) == set(CSV_FIELDS),
                f"{relative(input_path)}:{index} does not have the 15-field input schema",
            )
        input_ids = [str(row.get("id", "")) for row in inputs]
        output_ids = [str(row.get("source_id", "")) for row in outputs]
        require(len(input_ids) == len(set(input_ids)), f"duplicate input IDs in shard {shard_id}")
        require(
            set(input_ids) == set(output_ids) and len(inputs) == len(outputs),
            f"input/output coverage differs in shard {shard_id}",
        )
        for index, row in enumerate(outputs, 1):
            validate_eval(row, f"{relative(output_path)}:{index}")
            source_id = str(row["source_id"])
            require(source_id not in seen, f"source ID appears in multiple shards: {source_id}")
            seen.add(source_id)
            all_rows.append(row)

        kind_counts = Counter(str(row["kind"]) for row in outputs)
        shard_records.append(
            {
                "first_source_id": output_ids[0] if output_ids else "",
                "input": input_path.relative_to(ANALYSIS_DIR).as_posix(),
                "kinds": [[kind, count] for kind, count in sorted(kind_counts.items())],
                "last_source_id": output_ids[-1] if output_ids else "",
                "notes_output": f"shards/{shard_id}.notes.md",
                "row_output": output_path.relative_to(ANALYSIS_DIR).as_posix(),
                "rows": len(outputs),
                "shard_id": shard_id,
            }
        )
    require(len(all_rows) == EXPECTED_INCLUDED_ROWS, f"expected 668 shard rows, found {len(all_rows)}")
    return all_rows, shard_records


def row_average(row: dict[str, Any]) -> float:
    return sum(int(row[field]) for field in SCORE_FIELDS) / len(SCORE_FIELDS)


def derived_cluster_fields(source_ids: Iterable[str], eval_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ids = list(source_ids)
    require(len(ids) == len(set(ids)), "cluster source IDs are not unique")
    rows = [eval_by_id[source_id] for source_id in ids]
    require(rows, "cluster cannot be empty")
    kinds = Counter(str(row["kind"]) for row in rows)
    verdicts = Counter(str(row["actual_usefulness_verdict"]) for row in rows)
    keys = sorted({str(row["candidate_cluster_key"]) for row in rows if row["candidate_cluster_key"]})
    best = sorted(ids, key=lambda source_id: (-row_average(eval_by_id[source_id]), source_id))[:3]
    average = round(
        sum(int(row[field]) for row in rows for field in SCORE_FIELDS)
        / (len(rows) * len(SCORE_FIELDS)),
        2,
    )
    return {
        "source_ids": ids,
        "source_names": [str(eval_by_id[source_id]["name"]) for source_id in ids],
        "source_count": len(ids),
        "kinds": {kind: count for kind, count in sorted(kinds.items())},
        "verdict_counts": {verdict: count for verdict, count in sorted(verdicts.items())},
        "candidate_cluster_keys": keys,
        "average_score": average,
        "best_source_ids": best,
    }


COUNT_CLAIM_RE = re.compile(r"(Consolidates )\d+( related candidate\(s\))")


def build_manifest(
    csv_row_count: int,
    eval_rows: Sequence[dict[str, Any]],
    shard_records: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    kinds = Counter(str(row["kind"]) for row in eval_rows)
    return {
        "csv_path": "harness_lifecycle/capability_usefulness.csv",
        "excluded_rows": EXPECTED_EXCLUDED_ROWS,
        "included_by_kind": {kind: count for kind, count in sorted(kinds.items())},
        "included_rows": len(eval_rows),
        "shards": list(shard_records),
        "total_rows": csv_row_count,
    }


def md_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def render_cluster_review(clusters: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# Cluster Review",
        "",
        "Coordinator-owned review of all primary clusters generated from `row_evaluations.jsonl`. Every included source row appears in exactly one primary cluster in `clusters.json`.",
        "",
        "| Cluster | Decision | Review Result | Sources | Best Candidates | Rationale |",
        "|---|---|---|---:|---|---|",
    ]
    for cluster in clusters:
        verdicts = repr(cluster["verdict_counts"])
        rationale = (
            f"{cluster['selection_mode']}; average score {cluster['average_score']}; "
            f"verdicts {verdicts}"
        )
        lines.append(
            "| "
            + " | ".join(
                (
                    md_cell(f"`{cluster['cluster_id']}` {cluster['recommended_capability']}"),
                    md_cell(f"`{cluster['decision']}`"),
                    md_cell(cluster["selection_mode"]),
                    str(cluster["source_count"]),
                    md_cell(", ".join(cluster["best_source_ids"])),
                    md_cell(rationale),
                )
            )
            + " |"
        )
    return "\n".join(lines) + "\n"


def render_final_synthesis(clusters: Sequence[dict[str, Any]]) -> str:
    lines = [
        "# Final Synthesis",
        "",
        "This table is intentionally traceable: each row is a primary cluster recommendation and every source ID used by that recommendation is listed in full.",
        "",
        "| recommended_capability | recommended_surface | decision | source_ids | source_names | cluster_id | problem_solved | why_this_is_better | reuse_or_merge_plan | priority | risks_or_open_questions |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for cluster in clusters:
        source_ids = "<br>".join(f"`{source_id}`" for source_id in cluster["source_ids"])
        source_names = "<br>".join(str(name) for name in cluster["source_names"])
        values = (
            cluster["recommended_capability"],
            cluster["recommended_surface"],
            f"`{cluster['decision']}`",
            source_ids,
            source_names,
            f"`{cluster['cluster_id']}`",
            cluster["problem_solved"],
            cluster["why_this_is_better"],
            cluster["reuse_or_merge_plan"],
            f"`{cluster['priority']}`",
            cluster["risks_or_open_questions"],
        )
        lines.append("| " + " | ".join(md_cell(value) for value in values) + " |")
    return "\n".join(lines) + "\n"


def historical_shallow_sha256(rows: Sequence[dict[str, Any]]) -> str:
    payload = [
        [row["id"], *(row[field] for field in HISTORICAL_SHALLOW_FIELDS)]
        for row in rows[:EXPECTED_HISTORICAL_ROWS]
    ]
    rendered = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def assert_sentinel_rows(
    rows_by_id: dict[str, dict[str, Any]], new_ids: set[str]
) -> None:
    for source_id in sorted(new_ids):
        row = rows_by_id[source_id]
        require(row["fable_useful"] == "not_evaluated", f"bad Fable sentinel: {source_id}")
        require(bool(row["fable_reason"]), f"missing Fable sentinel reason: {source_id}")
        require(row["fable_tag"] == "", f"fabricated Fable tag: {source_id}")
        require(row["consensus"] == "codex_only", f"bad consensus sentinel: {source_id}")
        require(row["agree"] == "n/a", f"bad agreement sentinel: {source_id}")


def assert_machine_paths_absent(named_contents: Iterable[tuple[str, str]]) -> None:
    for name, content in named_contents:
        match = MACHINE_PATH_RE.search(content)
        require(not match, f"machine-local path found in {name}: {match.group(0) if match else ''}")


def verify_state(*, quiet: bool = False) -> None:
    assert_protected_hashes()
    _, catalog_order = catalog_mappings()
    catalog_ids = set(catalog_order)
    new_ids = catalog_ids - OVERLAP_IDS
    new_input_rows = load_new_input_rows(new_ids)

    _, csv_rows, raw_csv = read_csv_rows()
    assert_crlf(raw_csv)
    require(len(csv_rows) == EXPECTED_CSV_ROWS, f"expected 907 CSV rows, found {len(csv_rows)}")
    require(
        historical_shallow_sha256(csv_rows) == HISTORICAL_SHALLOW_SHA256,
        "historical Fable/GPT shallow judgments changed",
    )
    csv_by_id = {row["id"]: row for row in csv_rows}
    require(len(csv_by_id) == len(csv_rows), "CSV IDs are not unique")
    expected_new_order = [source_id for source_id in catalog_order if source_id in new_ids]
    require(
        [row["id"] for row in csv_rows[-EXPECTED_NEW_ROWS:]] == expected_new_order,
        "appended CSV rows do not preserve agent-skills catalog order",
    )
    provenance_ids = {
        source_id
        for source_id, row in csv_by_id.items()
        if "agent-skills" in {part.strip() for part in row["harnesses"].split(";")}
    }
    require(provenance_ids == catalog_ids, "CSV agent-skills provenance does not cover exactly 44 rows")
    assert_sentinel_rows(csv_by_id, new_ids)
    for row in new_input_rows:
        require(csv_by_id[row["id"]] == row, f"CSV differs from new shard input: {row['id']}")

    excluded = load_jsonl(EXCLUDED_PATH)
    require(len(excluded) == EXPECTED_EXCLUDED_ROWS, "excluded row count is not 239")
    excluded_ids = {str(row.get("id", "")) for row in excluded}
    require(len(excluded_ids) == len(excluded), "excluded IDs are not unique")

    shard_rows, shard_records = load_shards()
    shard_by_id = {str(row["source_id"]): row for row in shard_rows}
    require(not (excluded_ids & set(shard_by_id)), "excluded IDs appear in shard evaluations")
    require(set(shard_by_id) & catalog_ids == catalog_ids, "deep analysis lacks agent-skills rows")
    assert_sentinel_rows(shard_by_id, new_ids)
    for source_id in catalog_ids:
        row = shard_by_id[source_id]
        harnesses = {part.strip() for part in str(row["harnesses"]).split(";")}
        require("agent-skills" in harnesses, f"deep evaluation lacks provenance: {source_id}")
        require("agent-skills" in str(row["evidence_notes"]), f"evidence lacks provenance: {source_id}")

    global_rows = load_jsonl(GLOBAL_EVAL_PATH)
    require(len(global_rows) == EXPECTED_INCLUDED_ROWS, "global evaluation count is not 668")
    global_by_id = {str(row.get("source_id", "")): row for row in global_rows}
    require(len(global_by_id) == len(global_rows), "global evaluation IDs are not unique")
    for index, row in enumerate(global_rows, 1):
        validate_eval(row, f"{relative(GLOBAL_EVAL_PATH)}:{index}")
    require(
        global_rows == shard_rows,
        "global evaluations differ from the exact shard objects or shard order",
    )

    cluster_data = load_json(CLUSTERS_PATH)
    clusters = cluster_data.get("clusters", [])
    require(len(clusters) == EXPECTED_CLUSTERS, "cluster count is not 75")
    require(cluster_data.get("total_clusters") == EXPECTED_CLUSTERS, "stale total_clusters")
    require(cluster_data.get("total_source_ids") == EXPECTED_INCLUDED_ROWS, "stale total_source_ids")
    cluster_ids = [str(cluster.get("cluster_id", "")) for cluster in clusters]
    require(len(cluster_ids) == len(set(cluster_ids)), "cluster IDs are not unique")
    clustered_ids: list[str] = []
    for cluster in clusters:
        source_ids = [str(source_id) for source_id in cluster.get("source_ids", [])]
        missing_ids = set(source_ids) - set(global_by_id)
        require(not missing_ids, f"unknown source IDs in {cluster['cluster_id']}: {sorted(missing_ids)}")
        expected = derived_cluster_fields(source_ids, global_by_id)
        for field in DERIVED_CLUSTER_FIELDS:
            require(cluster.get(field) == expected[field], f"stale {field} in {cluster['cluster_id']}")
        override = QUALITATIVE_OVERRIDES.get(str(cluster["cluster_id"]), {})
        for field, value in override.items():
            require(cluster.get(field) == value, f"missing qualitative override {field} in {cluster['cluster_id']}")
        count_claim = COUNT_CLAIM_RE.search(str(cluster.get("why_this_is_better", "")))
        if count_claim:
            require(
                int(count_claim.group(0).split()[1]) == len(source_ids),
                f"stale source-count claim in {cluster['cluster_id']}",
            )
        clustered_ids.extend(source_ids)
    require(len(clustered_ids) == len(set(clustered_ids)), "source ID appears in multiple clusters")
    require(set(clustered_ids) == set(global_by_id), "cluster coverage differs from global evaluations")
    primary = {
        source_id: str(cluster["cluster_id"])
        for cluster in clusters
        for source_id in cluster["source_ids"]
        if source_id in catalog_ids
    }
    require(primary == CLUSTER_ASSIGNMENTS, "agent-skills primary cluster assignments differ")

    manifest = load_json(MANIFEST_PATH)
    expected_manifest = build_manifest(len(csv_rows), shard_rows, shard_records)
    require(manifest == expected_manifest, "shard_manifest.json is not derived from current shards")

    review = CLUSTER_REVIEW_PATH.read_text(encoding="utf-8")
    synthesis = FINAL_SYNTHESIS_PATH.read_text(encoding="utf-8")
    require(review == render_cluster_review(clusters), "cluster_review.md is stale")
    require(synthesis == render_final_synthesis(clusters), "final_synthesis.md is stale")

    scan_contents = [
        (relative(CSV_PATH), raw_csv.decode("utf-8")),
        (relative(GLOBAL_EVAL_PATH), GLOBAL_EVAL_PATH.read_text(encoding="utf-8")),
        (relative(CLUSTERS_PATH), CLUSTERS_PATH.read_text(encoding="utf-8")),
        (relative(MANIFEST_PATH), MANIFEST_PATH.read_text(encoding="utf-8")),
        (relative(CLUSTER_REVIEW_PATH), review),
        (relative(FINAL_SYNTHESIS_PATH), synthesis),
    ]
    for path in SHARDS_DIR.glob("*.jsonl"):
        scan_contents.append((relative(path), path.read_text(encoding="utf-8")))
    assert_machine_paths_absent(scan_contents)
    assert_protected_hashes()

    if not quiet:
        print(
            "PASS reconciliation: "
            "csv=907 catalog=44 overlap=5 new=39 excluded=239 "
            "included=668 clusters=75"
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the reviewed agent-skills Codex reconciliation without writing files."
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        required=True,
        help="verify canonical artifacts without writing",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    parse_args(argv)
    try:
        verify_state()
    except (OSError, ReconcileError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
