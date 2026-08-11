#!/usr/bin/env python3
"""Generate cluster_review.md and final_synthesis.md from clusters.json plus the
coordinator's per-cluster DECISIONS (authored judgment, recorded explicitly)."""
from __future__ import annotations

import json
from pathlib import Path

FA = Path(__file__).resolve().parent.parent

# decision: adopt_as_is | adapt | merge | replace_existing | defer | reject_after_review
# Fields: decision, priority, surface, problem, why, plan, risks, review
DECISIONS: dict[str, dict[str, str]] = {
    "C01": dict(decision="merge", priority="P0", surface="agent/skill",
        problem="Review diffs for correctness, reliability, maintainability, contracts and Python fit.",
        why="17 of 29 rows are merge-grade lenses; our code-reviewer/spec-reviewer agents already exist, so folding the strongest lens ideas (correctness, reliability, silent-failure, type-design) beats adding parallel reviewers.",
        plan="Fold 3-4 strongest lens checklists into the existing code-reviewer agent prompt; keep one adversarial pass; reject persona duplicates.",
        risks="Over-stuffing one reviewer prompt; keep lenses as short bullets, not essays.",
        review="Largest quality cluster. The lens agents (correctness-reviewer 4.83 avg, reliability-reviewer 4.83, maintainability-reviewer 4.67) are excellent but duplicate one another and our own reviewer; the santa-loop convergence idea is worth a note in the review skill. Python-specific reviewers overlap our rules."),
    "C02": dict(decision="defer", priority="P2", surface="command",
        problem="Resolve and triage GitHub PR review comments systematically.",
        why="Well-built (pr-comment-resolver 4.5) but we rarely run GitHub-PR-comment workflows in this repo today.",
        plan="Keep as backlog; revisit when PR-based collaboration becomes routine.",
        risks="None material while deferred.",
        review="Small, high-quality, low current relevance."),
    "C03": dict(decision="merge", priority="P2", surface="plugin",
        problem="Simplify code and remove dead code with behavior-preserving evidence.",
        why="We already ship a code-simplifier plugin; the two rewrite-grade rows only add cleanup-boundary rules.",
        plan="Fold 'clean only your own mess' boundaries into the existing code-simplifier plugin prompt.",
        risks="Aggressive simplification without tests; boundaries must stay explicit.",
        review="Redundant surfaces; keep ours, absorb boundary language."),
    "C04": dict(decision="merge", priority="P1", surface="skill",
        problem="Move from vague ideas to reviewed requirements, PRDs and scoped plans.",
        why="Our brainstorming/planning skills cover the spine; to-prd and product-capability contribute concrete requirement-shaping steps (3 adopts, 10 merges).",
        plan="Merge PRD-shaping prompts into the planning skill; keep discovery lenses (product-lens) as optional bullets; reject duplicate plan commands.",
        risks="Planning skill bloat — cap additions to a short PRD checklist.",
        review="Solid cluster with real ideas; most rejects are prp/rpi duplicates of workflows we already run via phase-execution."),
    "C05": dict(decision="merge", priority="P1", surface="skill/agent",
        problem="Review plans, specs and design docs for feasibility, scope, coherence and assumptions.",
        why="Highest-quality review cluster (avg 4.05; feasibility-reviewer 4.83, spec-flow-analyzer 4.83); our document-review skill exists but lacks these named lenses.",
        plan="Add feasibility / scope-guardian / coherence lenses to document-review; adopt grill-me-style interrogation as an optional mode; reject persona overlap.",
        risks="Lens overlap with spec-reviewer agent; define which surface owns which question.",
        review="The single richest source of borrowable review IP in the survey."),
    "C06": dict(decision="reject_after_review", priority="P3", surface="—",
        problem="End-to-end implementation execution workflows (feature-dev pipelines).",
        why="8 of 13 rejected: they re-implement what phase-execution + subagent-driven-development already do, with weaker verification gates.",
        plan="No action; our execution spine stays canonical.",
        risks="None.",
        review="Confirms our existing execution stack; nothing here beats it."),
    "C07": dict(decision="adopt_as_is", priority="P1", surface="skill (ours)",
        problem="Durable task tracking, phased workstreams and issue flows.",
        why="7 adopts are our own beads/phase-execution/prepare-phases/run-phases surface — validated as canonical; external trackers (jira/linear/asana) rejected or deferred.",
        plan="Keep ours; no imports. Wire the few defer'd integrations only when a real tracker need appears.",
        risks="None.",
        review="Self-audit outcome: our Beads-based stack scored highest in its own cluster."),
    "C08": dict(decision="merge", priority="P1", surface="skill",
        problem="Reproduce failures, isolate root causes, validate fixes before claiming done.",
        why="6 merge-grade rows orbit our systematic-debugging skill; reproduce-bug and diagnosing-bugs add concrete trigger/repro steps.",
        plan="Merge repro-first triggers and the bug-reproduction-validator gate into systematic-debugging.",
        risks="Minimal.",
        review="Coherent cluster, clear local owner."),
    "C09": dict(decision="merge", priority="P2", surface="rule/skill",
        problem="TDD, characterization, coverage and regression discipline.",
        why="Our python/testing rules + TDD skill cover the core; a few merge-grade rows (test-quality-review lenses) sharpen review of tests.",
        plan="Fold test-quality/coverage review bullets into the code-reviewer agent; reject zh/django/common variants.",
        risks="None material.",
        review="Mostly redundant with ours; the review-of-tests lenses are the durable bit."),
    "C10": dict(decision="adopt_as_is", priority="P1", surface="skill (ours)",
        problem="No completion claims without fresh verification evidence.",
        why="3 adopts are our verification-before-completion + check-invariants; terminal-ops' evidence-first pattern (4.5) reinforces the same doctrine.",
        plan="Keep ours canonical; add terminal-ops' 'evidence over recall' line to the skill if anything.",
        risks="None.",
        review="Self-audit: our verification doctrine is confirmed best-of-cluster."),
    "C11": dict(decision="defer", priority="P2", surface="skill/mcp",
        problem="Browser automation, E2E QA and demo recording.",
        why="Playwright MCP + agent-browser are capable but heavy; no active browser-QA workload in this repo.",
        plan="Defer; when a web UI needs testing, start from playwright MCP + browser-qa checklist.",
        risks="None while deferred.",
        review="Good tools, wrong time."),
    "C12": dict(decision="merge", priority="P0", surface="skill/rule",
        problem="Security review of plans, code and the harness itself.",
        why="9 merge-grade rows and strong single agents (security-auditor 4.83, security-lens-reviewer 5.0) versus our thin python/safety rule — the biggest genuine gap the survey found.",
        plan="Distill one security-review skill (plan lens + code lens + harness audit) from the top 3 sources; keep python/safety as the baseline rule; reject the JS hook pack implementations, keep their check ideas.",
        risks="Scope creep into a compliance framework; keep it a review skill, not a program.",
        review="Highest-leverage adoption target in the whole analysis."),
    "C13": dict(decision="adapt", priority="P1", surface="hook",
        problem="Block destructive commands, secret exposure and generated-file edits at tool time.",
        why="4 rewrite verdicts: the guard ideas are right but the implementations are Node/TS; our block-dangerous-commands.sh is the local pattern to extend.",
        plan="Port generated-file-protection and sensitive-data-guard checks as small shell hooks alongside block-dangerous-commands.sh.",
        risks="False positives blocking legitimate work — keep patterns conservative and logged.",
        review="Classic 'borrow the pattern, not the file' cluster."),
    "C14": dict(decision="adapt", priority="P2", surface="hook",
        problem="Post-edit formatting/typecheck and doc-sprawl warnings.",
        why="Ideas generalize (ruff/mypy on edit; warn on new stray .md), implementations are JS.",
        plan="One small PostToolUse hook running ruff format+check on edited .py files; doc-sprawl warn stays an idea until it hurts.",
        risks="Hook latency on every edit; keep it incremental-only.",
        review="Cheap wins if kept tiny."),
    "C15": dict(decision="defer", priority="P3", surface="—",
        problem="Declarative hook engines, dispatchers and hookify-style rule management.",
        why="13 rejects + 8 defers: engines add a config layer we don't need at our hook count.",
        plan="No action; revisit only if our hook count triples.",
        risks="None.",
        review="Over-engineering relative to our five hooks."),
    "C16": dict(decision="reject_after_review", priority="P3", surface="—",
        problem="Cost trackers, MCP health checks, desktop/chat notifications.",
        why="16 of 19 rejected: Node-specific, platform-duplicating, or observability we get from the harness itself.",
        plan="No action.",
        risks="None.",
        review="Session-report (5.0, ours) is the one keeper — already local."),
    "C17": dict(decision="defer", priority="P3", surface="—",
        problem="Context budgets, compaction strategy, model routing, cost control.",
        why="Platform-native compaction and our delegation rules cover the practical cases; the rest is niche.",
        plan="Keep strategic-compact's 'compact at phase boundaries' heuristic in mind; no imports.",
        risks="None.",
        review="Mostly solved a platform level."),
    "C18": dict(decision="merge", priority="P2", surface="skill",
        problem="Persist learnings, memories and project knowledge across sessions.",
        why="16 rejects (duplicative engines) but 6 merges point at real gaps in our learnings.md discipline (instinct export/import, learning-capture triggers).",
        plan="Merge capture-trigger language into our learnings.md header rules; skip all engine imports (bd memories already covers storage).",
        risks="Memory sprawl; keep the 'verified + likely-to-recur' bar.",
        review="Our two-layer setup (learnings.md + bd) survives contact with 26 alternatives."),
    "C19": dict(decision="reject_after_review", priority="P3", surface="—",
        problem="Session save/resume/handoff files.",
        why="Platform-native resume + compaction summaries made these obsolete (6 of 9 rejected).",
        plan="No action.",
        risks="None.",
        review="Historical pattern, superseded."),
    "C20": dict(decision="adopt_as_is", priority="P1", surface="skill/rule (ours)",
        problem="Coordinator/worker delegation, worktree isolation, parallel dispatch.",
        why="The 4 adopts are our subagent-driven-development, delegation rule and worktree patterns; GAN/fleet/team exotica rejected (11).",
        plan="Keep ours; the pending upstream subagent-driven-development selective merge (candidate A) remains the one open item.",
        risks="None new.",
        review="Confirms the earlier lifecycle finding: candidate A is still the only actionable upstream delta."),
    "C21": dict(decision="reject_after_review", priority="P3", surface="—",
        problem="Unsupervised autonomous loops (ralph-loop, GAN-style pipelines).",
        why="13 of 17 rejected: conflicts with this repo's supervised working mode and verification doctrine.",
        plan="No action.",
        risks="None.",
        review="Philosophically incompatible; deliberately not adopted."),
    "C22": dict(decision="adopt_as_is", priority="P1", surface="plugin (ours)",
        problem="Route bounded work to a second model (Codex) with roles and effort control.",
        why="6 adopts, avg 4.40 — our codex-adapter + use-codex routing scored best-in-class in its own cluster.",
        plan="Keep ours canonical; no imports needed.",
        risks="None.",
        review="Self-audit: strongest ours-owned cluster in the survey."),
    "C23": dict(decision="reject_after_review", priority="P3", surface="—",
        problem="Compatibility shims for other harnesses' command sets.",
        why="All 4 rejected — shims for ecosystems we don't run.",
        plan="No action.", risks="None.", review="Noise."),
    "C24": dict(decision="adopt_as_is", priority="P0", surface="tooling (ours)",
        problem="Scan reference harnesses, track drift, curate candidates, audit the surface.",
        why="11 adopts are our scan/gap/ledger/dashboard/curation surface — but 12 merge-grade rows (skill-stocktake, automation-audit-ops 4.67, harness-audit) offer audit angles ours lacks.",
        plan="Keep ours canonical; fold 'portfolio stocktake' (redundancy/trigger-quality audit) into the harness-evaluate skill as a periodic mode.",
        risks="Curation tooling creep; keep root-only rule.",
        review="Ours validated; one genuinely new idea (periodic portfolio stocktake) worth absorbing."),
    "C25": dict(decision="merge", priority="P1", surface="skill",
        problem="Author high-quality skills/agents/commands; evaluate trigger quality and portfolio health.",
        why="9 merges centered on writing-great-skills + skill-creator eval loops — directly applicable to how we write harness_learnings-derived skills.",
        plan="Merge trigger-description discipline and the eval-loop idea into our skill-authoring guidance; reject template/bundle imports.",
        risks="None material.",
        review="writing-great-skills is the single best external authoring doc surveyed."),
    "C26": dict(decision="merge", priority="P2", surface="rule",
        problem="Make products agent-operable (CLI-first, parity between human and agent interfaces).",
        why="A genuinely novel review lens (cli-agent-readiness 4.25) not present anywhere in ours.",
        plan="Add an 'agent-operability' bullet to the code-review lens set; skip the full audit skills.",
        risks="Niche until we build agent-facing products — keep it one bullet.",
        review="Small but new."),
    "C27": dict(decision="adopt_as_is", priority="P1", surface="agent/mcp (ours)",
        problem="Fetch current library docs and do cited, multi-source research.",
        why="4 adopts are our docs-researcher + context7 + deep-research; search-first adds a good trigger discipline (research before building).",
        plan="Keep ours; add search-first's 'check docs before inventing APIs' trigger line to docs-researcher guidance (already in CLAUDE.md — verify wording).",
        risks="None.",
        review="Ours confirmed; hygiene line worth one sentence."),
    "C28": dict(decision="defer", priority="P3", surface="—",
        problem="Doc maintenance automation (update-docs, deploy-docs, code-tours).",
        why="Mostly rejected/deferred; our docs-index + knowledge-discoverability rule cover the need at this repo's scale.",
        plan="No action.", risks="None.", review="Low value at current doc volume."),
    "C29": dict(decision="merge", priority="P2", surface="skill",
        problem="Teach the human what was built; quiz-based retention.",
        why="Our teach-session exists; quiz-me's retention-check idea is a cheap, real addition.",
        plan="Fold a short quiz mode into teach-session.",
        risks="None.", review="Nice-to-have, tiny merge."),
    "C30": dict(decision="merge", priority="P1", surface="skill",
        problem="Map architecture, domains and decision records before changing complex systems.",
        why="8 merges + 3 adopts: ADR discipline (4.33) and domain-modeling (4.17) fill a real gap between our brainstorming and planning stages.",
        plan="Add an ADR-lite step to the planning skill (decision + alternatives + consequence, one file per decision); borrow code-explorer's evidence-first exploration bullets for Explore-agent prompts.",
        risks="ADR ceremony for small changes — gate it to deep-scope work.",
        review="Substantive, actionable, bounded."),
    "C31": dict(decision="adopt_as_is", priority="P1", surface="plugin (ours)",
        problem="Semantic/graph code intelligence for navigation and impact analysis.",
        why="7 adopts, avg 4.25 — our code-intel plugin (+ serena as the external reference) validated.",
        plan="Keep ours; graph-first's query-before-grep doctrine is already how code-intel is prompted.",
        risks="None.", review="Self-audit pass."),
    "C32": dict(decision="reject_after_review", priority="P3", surface="—",
        problem="Commit/PR/release automation bundles.",
        why="16 of 25 rejected: our git-safety rules deliberately keep commits manual and explicit; automation bundles fight that.",
        plan="No action; keep git safety rules canonical.",
        risks="None.",
        review="Doctrine conflict resolved in favor of our explicit-staging rules."),
    "C33": dict(decision="defer", priority="P2", surface="skill-pack",
        problem="Legacy modernization: assess, extract rules, transform behavior-preservingly.",
        why="Second-highest cluster quality (4.23) — compound-engineering's modernize-* suite is excellent — but we have no active legacy-modernization workstream.",
        plan="Defer with a pointer: when a legacy Python migration lands, start from modernize-preflight/extract-rules/transform and the business-rules-extractor agent.",
        risks="Losing track of it; the ledger entry is the pointer.",
        review="Best 'wrong-time' cluster; explicitly parked, not rejected."),
    "C34": dict(decision="adapt", priority="P2", surface="rule/skill",
        problem="Schema migrations, backfills and data-integrity review.",
        why="7 rewrite verdicts: strong migration-safety review ideas wrapped in Rails/ORM-specific personas.",
        plan="Rewrite into one Python/SQL migration-safety checklist (expand-migrate-contract, rollback plan, integrity checks) appended to python/safety or a small skill.",
        risks="None material.",
        review="Consistent rewrite signal across both evaluators."),
    "C35": dict(decision="adopt_as_is", priority="P1", surface="rule (ours)",
        problem="LLM coding discipline: minimal diffs, surgical changes, verified completion.",
        why="3 adopts are ak-guide/core-03 (ours, 5.0) — the survey's other style packs are weaker duplicates.",
        plan="Keep ours; reject zh/common style packs; regex-vs-llm's decision boundary (code for deterministic transforms) is already rule 5 in core-03.",
        risks="None.", review="Self-audit pass; ak-guide is best-in-class."),
    "C36": dict(decision="defer", priority="P3", surface="—",
        problem="Deployment, IaC, containers, canary monitoring.",
        why="No deployment surface in this repo; firebase/terraform plugins irrelevant today.",
        plan="No action.", risks="None.", review="Out of scope."),
    "C37": dict(decision="reject_after_review", priority="P3", surface="—",
        problem="Media generation, hardware toys, payments, SEO, office suites.",
        why="10 of 13 rejected as off-domain for a Python engineering harness.",
        plan="No action.", risks="None.", review="Off-domain."),
    "C38": dict(decision="reject_after_review", priority="P3", surface="—",
        problem="Healthcare/Django/manufacturing/trading domain packs.",
        why="13 of 15 rejected: domains we don't work in; Django patterns conflict with our framework-agnostic rules.",
        plan="No action; pytorch-patterns noted for a future ML workstream.",
        risks="None.", review="Cleanly out of scope."),
    "C39": dict(decision="defer", priority="P3", surface="—",
        problem="Prose style, article writing, brand voice.",
        why="Personal-taste packs; our writing needs are covered by html-artifact + report conventions.",
        plan="No action.", risks="None.", review="Not engineering surface."),
    "C40": dict(decision="merge", priority="P2", surface="skill (ours)",
        problem="Readable HTML artifacts, dashboards, reports and their verification.",
        why="3 adopts are our html-artifact stack; the one real gap is a verification checklist — web/testing's viewport/keyboard/contrast/JS-off checks (as this analysis's rule-2 shard flagged).",
        plan="Fold a short artifact-verification checklist into the html-artifact skill; keep presets as-is; reject frontend-framework rows.",
        risks="None.", review="Ours validated; one concrete borrow identified."),
    "C41": dict(decision="defer", priority="P2", surface="skill",
        problem="Author MCP servers and plugins correctly.",
        why="7 defers: build-mcp-server (Anthropic-official, thorough) is the reference to reach for when we next build an MCP server — no current need.",
        plan="Defer with pointer to build-mcp-server + plugin-dev as the starting docs.",
        risks="None while deferred.", review="Good reference material, no active demand."),
}


def main() -> int:
    clusters = json.loads((FA / "clusters.json").read_text(encoding="utf-8"))["clusters"]
    rows = {r["source_id"]: r for r in
            (json.loads(l) for l in (FA / "row_evaluations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}

    missing = [c["cluster_id"] for c in clusters if c["cluster_id"] not in DECISIONS]
    if missing:
        print("DECISIONS missing for:", missing)
        return 1

    # --- cluster_review.md ---
    review_lines = [
        "# Cluster Review — Fable analysis",
        "",
        "One entry per primary cluster: composition, worker-verdict mix, and the",
        "coordinator's decision with reasoning. Decisions and priorities are mirrored",
        "in `final_synthesis.md`; every source row remains traceable via `clusters.json`.",
        "",
    ]
    for c in clusters:
        d = DECISIONS[c["cluster_id"]]
        v = c["verdicts"]
        vmix = ", ".join(f"{k} {v[k]}" for k in ("adopt", "merge", "rewrite", "defer", "reject_after_review") if v.get(k))
        review_lines += [
            f"## {c['cluster_id']} — {c['title']}",
            "",
            f"- **n:** {c['count']} · **kinds:** {', '.join(f'{k}:{n}' for k, n in sorted(c['kinds'].items()))} · **avg score:** {c['avg_score']}",
            f"- **worker verdicts:** {vmix}",
            f"- **strongest members:** {', '.join(c['best_source_ids'])}",
            f"- **decision:** `{d['decision']}` · **priority:** {d['priority']}",
            "",
            d["review"],
            "",
        ]
    (FA / "cluster_review.md").write_text("\n".join(review_lines), encoding="utf-8")

    # --- final_synthesis.md ---
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    syn = [
        "# Final Synthesis — Fable analysis",
        "",
        "One row per primary cluster, sorted by priority. Every recommendation links",
        "back to all of its source rows (see `clusters.json` for the full ID lists;",
        "row-level evidence in `row_evaluations.jsonl`).",
        "",
        "| recommended_capability | recommended_surface | decision | sources (n) | representative_sources | cluster_id | problem_solved | why_this_is_better | reuse_or_merge_plan | priority | risks_or_open_questions |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for c in sorted(clusters, key=lambda c: (order[DECISIONS[c["cluster_id"]]["priority"]], c["cluster_id"])):
        d = DECISIONS[c["cluster_id"]]
        rep = "<br>".join(f"`{sid}`" for sid in c["best_source_ids"])
        names = "<br>".join(rows[sid]["name"] for sid in c["best_source_ids"])
        syn.append(
            f"| {c['title']} | {d['surface']} | `{d['decision']}` | {c['count']} "
            f"| {rep}<br>({names}) | `{c['cluster_id']}` | {d['problem']} | {d['why']} "
            f"| {d['plan']} | `{d['priority']}` | {d['risks']} |")
    syn += [
        "",
        "## Reading guide",
        "",
        "- `adopt_as_is` rows are self-audit confirmations: the best-in-cluster capability is already ours.",
        "- `merge`/`adapt` rows are the actionable adoption backlog, smallest-durable-pattern style.",
        "- `defer` rows are parked with an explicit pointer; `reject_after_review` rows are closed.",
        "- Full per-cluster source_id lists: `clusters.json`. Per-row evidence: `row_evaluations.jsonl`.",
    ]
    (FA / "final_synthesis.md").write_text("\n".join(syn) + "\n", encoding="utf-8")

    from collections import Counter
    dc = Counter(d["decision"] for d in DECISIONS.values())
    pc = Counter(d["priority"] for d in DECISIONS.values())
    print(f"wrote cluster_review.md + final_synthesis.md ({len(clusters)} clusters)")
    print(f"decisions: {dict(dc)}")
    print(f"priorities: {dict(pc)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
