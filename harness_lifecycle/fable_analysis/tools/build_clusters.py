#!/usr/bin/env python3
"""Apply the coordinator's consolidation mapping (raw candidate_cluster_key ->
primary cluster) to raw_clusters.json, producing clusters.json.

The MAPPING below is the Fable coordinator's judgment, recorded explicitly so the
consolidation is auditable and re-runnable. The script itself is deterministic:
it verifies every raw key is mapped exactly once and every evaluated source_id
lands in exactly one primary cluster.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

FA = Path(__file__).resolve().parent.parent

TITLES = {
    "C01": "Code review lenses & change quality",
    "C02": "PR feedback resolution & triage",
    "C03": "Code simplification & cleanup",
    "C04": "Planning, requirements & product discovery",
    "C05": "Plan / spec / design document review",
    "C06": "Implementation execution workflows",
    "C07": "Workstreams, tasks & issue tracking",
    "C08": "Debugging & root-cause analysis",
    "C09": "Testing, TDD & regression",
    "C10": "Verification before completion",
    "C11": "Browser automation & E2E QA",
    "C12": "Security review & baselines",
    "C13": "Safety guardrails (destructive actions & data)",
    "C14": "Edit/commit-time quality gates",
    "C15": "Hook infrastructure & authoring",
    "C16": "Observability & notifications",
    "C17": "Context, cost & model routing",
    "C18": "Memory, learning & knowledge continuity",
    "C19": "Session continuity & handoff",
    "C20": "Subagent orchestration & delegation",
    "C21": "Autonomous loops & pipelines",
    "C22": "Codex / second-model delegation",
    "C23": "Compatibility shims",
    "C24": "Harness lifecycle & curation",
    "C25": "Harness authoring & skill quality",
    "C26": "Agent-native readiness",
    "C27": "Docs & research lookup",
    "C28": "Documentation maintenance",
    "C29": "Teaching & onboarding people",
    "C30": "Architecture & codebase understanding",
    "C31": "Code intelligence indexing",
    "C32": "Git, GitHub & release workflows",
    "C33": "Legacy modernization",
    "C34": "Data & database safety",
    "C35": "Coding discipline & standards",
    "C36": "Deployment & DevOps",
    "C37": "External integrations & media tools",
    "C38": "Domain-specific packs",
    "C39": "Writing craft",
    "C40": "HTML artifacts, frontend & reporting",
    "C41": "MCP & plugin development",
}

MAPPING = {
    # C01 code review lenses
    "code-review-core": "C01", "python-code-review": "C01", "performance-code-review": "C01",
    "adversarial-code-review": "C01", "api-contract-review": "C01", "maintainability-code-review": "C01",
    "reliability-code-review": "C01", "security-code-review": "C01", "silent-failure-review": "C01",
    "type-invariant-review": "C01", "comment-accuracy-review": "C01", "code-pattern-consistency": "C01",
    "python-review": "C01", "adversarial-review": "C01",
    # C02 PR feedback
    "pr-feedback-lifecycle": "C02", "review-feedback-resolution": "C02", "pr-triage": "C02",
    # C03 simplification
    "code-simplicity": "C03", "code-simplification": "C03", "dead-code-cleanup": "C03",
    # C04 planning & requirements
    "implementation-planning": "C04", "product-requirements-planning": "C04",
    "requirements-discovery": "C04", "requirements-brainstorming": "C04",
    "requirements-engineering": "C04", "requirements-capture": "C04", "product-validation": "C04",
    "product-document-review": "C04", "project-ideation": "C04", "feature-viability": "C04",
    "refactor-planning": "C04",
    # C05 document/spec/design review
    "adversarial-document-review": "C05", "document-review": "C05", "document-coherence-review": "C05",
    "spec-flow-review": "C05", "spec-compliance-review": "C05", "ux-spec-review": "C05",
    "plan-feasibility-review": "C05", "plan-scope-review": "C05", "project-standards-review": "C05",
    "principle-compliance-review": "C05", "design-interrogation": "C05", "adversarial-design-review": "C05",
    "workflow-specification": "C05", "design-critique": "C05", "design-doc-evolution": "C05",
    "multi-perspective-decision": "C05",
    # C06 implementation execution
    "bounded-implementation": "C06", "plan-execution": "C06", "plan-execution-compat": "C06",
    "implementation-workflow": "C06", "implementation-execution": "C06", "delegated-implementation": "C06",
    "feature-development-workflow": "C06", "feature-dev-workflow": "C06", "dev-workflow-pipeline": "C06",
    "development-workflow-core": "C06",
    # C07 workstreams & tasks
    "durable-task-tracking": "C07", "phased-execution": "C07", "beads-phase-execution": "C07",
    "phased-workstream-execution": "C07", "workstream-bootstrap": "C07", "workstream-planning": "C07",
    "workstream-decomposition": "C07", "workstream-seeding": "C07", "issue-triage": "C07",
    "issue-filing": "C07", "external-ticketing-integration": "C07", "issue-tracker-integration": "C07",
    "workflow-checkpointing": "C07", "external-pm-integration": "C07", "issue-tracking-integration": "C07",
    "issue-landscape-analysis": "C07", "beads-context-priming": "C07",
    # C08 debugging
    "systematic-debugging": "C08", "pytorch-runtime-debugging": "C08", "state-transition-debugging": "C08",
    # C09 testing
    "test-driven-development": "C09", "test-first-development": "C09", "tdd-core": "C09",
    "testing-standards": "C09", "testing-core": "C09", "regression-testing": "C09",
    "test-coverage-analysis": "C09", "python-testing": "C09", "performance-benchmarking": "C09",
    "performance-profiling": "C09", "test-coverage-review": "C09", "test-quality-review": "C09",
    # C10 verification
    "completion-verification": "C10", "verification-before-completion": "C10",
    "invariant-checking": "C10", "repository-invariant-checking": "C10",
    "evidence-first-terminal-ops": "C10", "completion-gate": "C10",
    # C11 browser & e2e
    "browser-e2e-testing": "C11", "browser-automation": "C11", "browser-qa": "C11",
    "browser-testing": "C11", "browser-demo-recording": "C11",
    # C12 security
    "automated-security-review": "C12", "security-review": "C12", "security-baseline": "C12",
    "security-audit": "C12", "security-plan-review": "C12", "application-security-baseline": "C12",
    "application-security-review": "C12", "harness-security-audit": "C12", "security-hardening": "C12",
    "llm-security-review": "C12", "agentic-security-review": "C12", "governance-security-audit": "C12",
    "security-review-state": "C12", "prompt-defense": "C12", "security-review-core": "C12",
    # C13 safety guardrails
    "sensitive-data-guard": "C13", "generated-file-protection": "C13", "config-edit-protection": "C13",
    "publication-safety": "C13", "destructive-operation-guard": "C13", "long-running-process-safety": "C13",
    "dangerous-command-guard": "C13",
    # C14 edit/commit quality gates
    "post-edit-quality": "C14", "post-edit-formatting": "C14", "post-edit-typechecking": "C14",
    "batched-edit-quality": "C14", "quality-gates": "C14", "formatter-quality-gate": "C14",
    "commit-quality-gate": "C14", "write-time-quality-hooks": "C14", "doc-sprawl-guard": "C14",
    "documentation-sprawl-control": "C14",
    # C15 hook infrastructure
    "declarative-hook-rules": "C15", "hook-profile-dispatch": "C15", "hook-feature-flags": "C15",
    "hook-bootstrap": "C15", "python-hook-launcher": "C15", "package-plumbing": "C15",
    "stop-hook-dispatch": "C15", "hooks-governance": "C15", "hook-safety-and-tracking": "C15",
    "python-automation-hooks": "C15", "hooks-configuration": "C15", "policy-hook-authoring": "C15",
    "hookify-rule-management": "C15", "hook-authoring": "C15", "hook-rule-inventory": "C15",
    "permission-allowlist-tuning": "C15",
    # C16 observability & notifications
    "mcp-observability": "C16", "mcp-reliability": "C16", "cost-observability": "C16",
    "command-audit-logging": "C16", "build-completion-notice": "C16", "pr-workflow-notice": "C16",
    "agent-event-notifications": "C16", "subagent-observability": "C16", "shell-lifecycle": "C16",
    "chat-notification-bridge": "C16", "notifications-ops": "C16", "agent-ops-observability": "C16",
    "agent-session-observability": "C16",
    # C17 context & cost
    "context-compaction": "C17", "context-compaction-continuity": "C17", "context-management": "C17",
    "context-management-compat": "C17", "context-budget": "C17", "response-budgeting": "C17",
    "conversational-context-control": "C17", "model-routing": "C17", "llm-cost-control": "C17",
    "software-cost-estimation": "C17", "context-retrieval": "C17", "agent-runtime-management": "C17",
    # C18 memory & learning
    "learning-memory-lifecycle": "C18", "continuous-learning": "C18", "continuous-learning-observation": "C18",
    "session-learning": "C18", "session-learning-guardrails": "C18", "learned-guidance-portability": "C18",
    "learned-guidance-audit": "C18", "learned-capability-promotion": "C18", "learning-capture": "C18",
    "learning-compounding": "C18", "project-learning-capture": "C18", "project-learning-maintenance": "C18",
    "persistent-learnings": "C18", "prior-learnings-retrieval": "C18", "agent-memory": "C18",
    "project-memory": "C18", "knowledge-management": "C18", "personal-notes": "C18",
    "observer-lifecycle": "C18",
    # C19 session continuity
    "session-continuity": "C19", "session-handoff-continuity": "C19", "cross-session-history": "C19",
    "session-history-retrieval": "C19",
    # C20 orchestration & delegation
    "agent-delegation": "C20", "multi-agent-orchestration": "C20", "agent-fleet-orchestration": "C20",
    "agent-orchestration": "C20", "subagent-driven-development": "C20", "max-effort-generalist": "C20",
    "generalist-delegation-tier": "C20", "multi-model-development-workflow": "C20",
    "workspace-isolation": "C20", "git-worktree-isolation": "C20", "reasoning-scaffold": "C20",
    # C21 autonomous loops
    "generator-evaluator-loop": "C21", "autonomous-loop-operations": "C21",
    "autonomous-loop-supervision": "C21", "autonomous-agent-loop": "C21", "autonomous-looping": "C21",
    "autonomous-pipeline": "C21", "autonomous-execution": "C21", "autonomous-agent-operations": "C21",
    "continuous-agent-execution": "C21", "ralph-loop-control": "C21", "autonomous-loop-control": "C21",
    # C22 codex delegation
    "codex-invocation": "C22", "codex-invocation-routing": "C22", "codex-delegation": "C22",
    "codex-readiness": "C22", "second-model-delegation": "C22", "codex-command-migration": "C22",
    "claude-codex-migration": "C22",
    # C23 compat shims
    "legacy-command-shims": "C23", "nanoclaw-repl-compat": "C23", "repl-tooling": "C23",
    # C24 harness lifecycle & curation
    "harness-curation": "C24", "harness-adoption": "C24", "harness-update": "C24",
    "harness-health-audit": "C24", "harness-repository-research": "C24",
    "reference-harness-comparison": "C24", "reference-catalog-freshness": "C24",
    "capability-curation": "C24", "harness-catalog-bundle": "C24", "harness-installation": "C24",
    "harness-setup-recommendation": "C24", "harness-automation-audit": "C24", "harness-optimization": "C24",
    "harness-surface-audit": "C24", "automation-surface-audit": "C24", "capability-quality-audit": "C24",
    "skill-compliance-evaluation": "C24", "repo-audit": "C24", "plugin-self-update": "C24",
    "claude-code-docs-drift": "C24", "claude-platform-doc-drift": "C24", "environment-diagnostics": "C24",
    "core-dev-methodology": "C24",
    # C25 harness authoring & skill quality
    "skill-authoring": "C25", "skill-authoring-templates": "C25", "agent-authoring": "C25",
    "harness-command-authoring": "C25", "skill-quality-review": "C25", "skill-output-evaluation": "C25",
    "skill-portfolio-observability": "C25", "spec-output-grading": "C25", "skill-routing": "C25",
    "skill-routing-bootstrap": "C25", "prompt-authoring": "C25", "instruction-file-maintenance": "C25",
    "claude-md-hygiene": "C25", "rules-distillation": "C25", "harness-rule-maintenance": "C25",
    "language-rules": "C25", "rule-pack-installation": "C25", "coding-agent-benchmarking": "C25",
    "agent-evaluation": "C25", "eval-harness": "C25", "agent-tooling-design": "C25", "output-style": "C25",
    # C26 agent-native readiness
    "agent-native-architecture": "C26", "agent-interface-parity": "C26", "cli-agent-readiness": "C26",
    # C27 docs & research
    "docs-research": "C27", "web-research": "C27", "documentation-lookup": "C27",
    "documentation-research": "C27", "framework-doc-research": "C27", "live-docs-lookup": "C27",
    "docs-lookup": "C27", "decision-grade-research": "C27", "current-evidence-research": "C27",
    "research-before-building": "C27", "research-reporting": "C27", "organizational-context-research": "C27",
    # C28 documentation maintenance
    "documentation-maintenance": "C28", "docs-conventions": "C28", "documentation-source-sync": "C28",
    "docs-deployment": "C28", "codebase-onboarding-artifacts": "C28", "learning-artifact-sync": "C28",
    # C29 teaching
    "teaching-learning": "C29", "teaching-and-retention": "C29", "learning-tutor": "C29",
    "codebase-teaching": "C29", "course-authoring": "C29",
    # C30 architecture & codebase understanding
    "codebase-understanding": "C30", "codebase-exploration": "C30", "codebase-orientation": "C30",
    "repository-orientation": "C30", "git-archaeology": "C30", "architecture-design": "C30",
    "architecture-critique": "C30", "architecture-review": "C30", "architecture-mapping": "C30",
    "architecture-assessment": "C30", "architecture-patterns": "C30", "architecture-decisions": "C30",
    "architecture-decision-review": "C30", "module-design": "C30", "interface-design": "C30",
    "domain-modeling": "C30", "domain-glossary": "C30", "rest-api-design": "C30",
    "api-connector-development": "C30", "codebase-onboarding": "C30",
    # C31 code intelligence
    "semantic-code-intel": "C31", "code-intelligence": "C31", "code-intelligence-indexing": "C31",
    "code-intelligence-setup": "C31", "code-intel-lifecycle": "C31", "graph-first-code-intelligence": "C31",
    "code-index-readiness": "C31",
    # C32 git & release
    "git-commit-workflow": "C32", "git-change-publishing": "C32", "git-publish-workflow": "C32",
    "safe-commit-workflow": "C32", "pr-creation": "C32", "git-branch-cleanup": "C32",
    "git-branch-finish": "C32", "git-workflow": "C32", "git-workflow-core": "C32",
    "git-conventions": "C32", "git-safety-guardrails": "C32", "merge-conflict-resolution": "C32",
    "git-hosting-integration": "C32", "github-integration": "C32", "github-repository-operations": "C32",
    "pr-evidence-capture": "C32", "open-source-release-prep": "C32", "open-source-release": "C32",
    "changelog-generation": "C32",
    # C33 modernization
    "legacy-modernization": "C33", "legacy-system-assessment": "C33", "legacy-system-rebuild": "C33",
    "modernization-planning": "C33", "modernization-readiness": "C33", "modernization-status": "C33",
    "behavior-preserving-modernization": "C33", "runtime-version-uplift": "C33",
    "business-rule-extraction": "C33", "legacy-business-rule-extraction": "C33",
    "stack-version-migration": "C33", "code-modernization-scaffolding": "C33",
    "legacy-codebase-analysis": "C33",
    # C34 data & database
    "database-change-safety": "C34", "data-migration-review": "C34", "postgres-review": "C34",
    "database-deployment-readiness": "C34", "database-migration": "C34", "database-migrations": "C34",
    "postgres-engineering": "C34", "clickhouse-data-engineering": "C34", "scheduled-data-collection": "C34",
    # C35 coding discipline
    "coding-discipline": "C35", "llm-coding-guardrails": "C35", "coding-style-core": "C35",
    "coding-standards-core": "C35", "python-style": "C35", "python-coding-standards": "C35",
    "design-patterns": "C35", "application-design-patterns": "C35", "deterministic-text-parsing": "C35",
    "prototyping": "C35", "content-addressed-cache": "C35", "agentic-engineering-operating-model": "C35",
    # C36 deployment & devops
    "deployment-containers": "C36", "post-deploy-monitoring": "C36", "iac-tooling": "C36",
    "platform-integration": "C36", "cloud-file-transfer": "C36",
    # C37 external integrations & media
    "office-suite-ops": "C37", "hardware-onboarding": "C37", "cardputer-device-development": "C37",
    "blockchain-domain": "C37", "agent-payments": "C37", "media-generation": "C37",
    "media-processing": "C37", "media-explainers": "C37", "document-processing": "C37",
    "web-seo": "C37", "seo-audit": "C37",
    # C38 domain packs
    "healthcare-domain": "C38", "healthcare-safety-review": "C38", "manufacturing-domain": "C38",
    "business-domain-persona": "C38", "pytorch-training": "C38", "django-application-patterns": "C38",
    "django-security": "C38", "django-testing": "C38", "django-verification": "C38",
    "domain-security-niche": "C38",
    # C39 writing craft
    "writing-craft": "C39", "prose-editing": "C39", "long-form-writing": "C39", "brand-voice": "C39",
    # C40 html artifacts & frontend
    "html-artifact-design-quality": "C40", "html-artifact-performance": "C40",
    "html-artifact-verification": "C40", "html-artifact-tooling": "C40",
    "human-readable-html-artifacts": "C40", "html-design-quality": "C40", "html-presentations": "C40",
    "interactive-html-playground": "C40", "observability-dashboard-design": "C40",
    "visual-design-audit": "C40", "frontend-application-architecture": "C40",
    "figma-fidelity-review": "C40", "ui-visual-iteration": "C40", "ux-requirements": "C40",
    "remotion-text-layout": "C40", "presentation-delegation": "C40", "presentation-repo-specific": "C40",
    "status-reporting": "C40", "project-status-reporting": "C40", "doc-sharing-service": "C40",
    # C41 mcp & plugin development
    "mcp-app-development": "C41", "mcp-server-development": "C41", "mcp-server-dev": "C41",
    "mcp-local-distribution": "C41", "mcp-plugin-integration": "C41", "remote-mcp-connectivity": "C41",
    "private-mcp-tunnel": "C41", "plugin-authoring": "C41", "plugin-authoring-reference": "C41",
    "plugin-scaffolding": "C41", "plugin-configuration": "C41", "plugin-validation": "C41",
    "plugin-help": "C41", "agent-sdk-scaffolding": "C41", "python-agent-sdk-verification": "C41",
    "anthropic-api-reference": "C41",
}

SCORES = ["effectiveness", "instruction_quality", "clarity", "precision", "concision", "structural_efficiency"]


def main() -> int:
    raw = json.loads((FA / "raw_clusters.json").read_text(encoding="utf-8"))
    rows = {r["source_id"]: r for r in
            (json.loads(l) for l in (FA / "row_evaluations.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}

    unmapped = [c["cluster_key"] for c in raw if c["cluster_key"] not in MAPPING]
    unknown = sorted(set(MAPPING) - {c["cluster_key"] for c in raw})
    if unmapped or unknown:
        print(f"UNMAPPED raw keys ({len(unmapped)}): {unmapped[:20]}")
        print(f"MAPPING keys not in raw ({len(unknown)}): {unknown[:20]}")
        return 1

    clusters: dict[str, dict] = {}
    for c in raw:
        cid = MAPPING[c["cluster_key"]]
        cl = clusters.setdefault(cid, {
            "cluster_id": cid, "title": TITLES[cid], "raw_keys": [], "source_ids": [],
        })
        cl["raw_keys"].append(c["cluster_key"])
        cl["source_ids"].extend(c["source_ids"])

    out = []
    for cid in sorted(clusters):
        cl = clusters[cid]
        members = [rows[sid] for sid in cl["source_ids"]]
        avg = round(sum(sum(m[s] for s in SCORES) / len(SCORES) for m in members) / len(members), 2)
        best = sorted(members, key=lambda m: -sum(m[s] for s in SCORES))[:3]
        out.append({
            "cluster_id": cid, "title": cl["title"], "count": len(members),
            "kinds": dict(Counter(m["kind"] for m in members)),
            "verdicts": dict(Counter(m["actual_usefulness_verdict"] for m in members)),
            "avg_score": avg,
            "best_source_ids": [m["source_id"] for m in best],
            "raw_keys": sorted(cl["raw_keys"]),
            "source_ids": sorted(cl["source_ids"]),
        })

    (FA / "clusters.json").write_text(json.dumps({"clusters": out}, indent=2), encoding="utf-8")

    all_ids = [sid for c in out for sid in c["source_ids"]]
    dupes = [k for k, v in Counter(all_ids).items() if v > 1]
    print(f"clusters={len(out)} rows_covered={len(all_ids)} (rows={len(rows)}) dupes={len(dupes)}")
    for c in out:
        v = c["verdicts"]
        print(f'  {c["cluster_id"]} {c["title"][:44]:44} n={c["count"]:3} avg={c["avg_score"]:.2f} '
              f'adopt={v.get("adopt",0):2} merge={v.get("merge",0):3} rewrite={v.get("rewrite",0):2} '
              f'defer={v.get("defer",0):2} reject={v.get("reject_after_review",0):3}')
    ok = len(all_ids) == len(rows) and not dupes
    print("CLUSTER COVERAGE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
