# Fable analysis vs Codex analysis — row-level diff

Common evaluated rows: **629** (ours-only: 0, codex-only: 0).

**Provenance caveat:** in this analysis 148 rows were evaluated by Fable-5 xhigh
workers and 481 by Codex GPT-5.6-Sol xhigh workers (user-directed pivot after
Claude session limits; per-row `evaluated_by` records which). So for most rows
this diff compares GPT-5.6-Sol against the earlier GPT-5.5 analysis — the
*coordination, clustering and synthesis* are Fable's, the row verdicts are mixed.

## Agreement

- Exact verdict agreement: **302/629** (48%)
- Within one step on the adopt→reject scale: **455/629** (72%)

## Verdict cross-table (codex → this analysis)

| codex \ ours | adopt | merge | rewrite | defer | reject_after_review |
|---|---|---|---|---|---|
| **adopt** | 59 | 14 | 4 | 0 | 5 |
| **merge** | 12 | 102 | 31 | 24 | 96 |
| **rewrite** | 0 | 4 | 9 | 8 | 22 |
| **defer** | 2 | 14 | 15 | 31 | 64 |
| **reject_after_review** | 0 | 4 | 3 | 5 | 101 |

## Average scores on common rows

| dimension | this analysis | codex |
|---|---|---|
| effectiveness | 3.01 | 3.33 |
| instruction_quality | 3.43 | 3.55 |
| clarity | 4.24 | 4.02 |
| precision | 3.28 | 3.59 |
| concision | 3.42 | 3.94 |
| structural_efficiency | 3.25 | 3.43 |

Row-evaluator provenance (this analysis): {'gpt-5.6-sol-xhigh': 481, 'fable-5-xhigh': 148}

## Sharpest divergences (≥3 steps apart): 107

- `agent:harnessoptimizer` (harness-optimizer): codex=**adopt** vs ours=**reject_after_review** — ours: The workflow depends on an undefined `/harness-audit` score and provides no measurement model, so its before/after claims are not operationa
- `mcp:exa` (exa): codex=**adopt** vs ours=**reject_after_review** — ours: Disagree with both shallow yeses on adoption: the capability class is valuable but already saturated locally — host WebSearch/WebFetch plus 
- `mcp:github` (github): codex=**adopt** vs ours=**reject_after_review** — ours: Disagree with both shallow yeses: the capability is core but our harness already standardizes on the gh CLI for exactly these operations (CL
- `skill:resolvingmergeconflicts` (resolving-merge-conflicts): codex=**adopt** vs ours=**reject_after_review** — ours: “Always resolve,” “never abort,” stage everything, and commit are unsafe defaults that violate explicit scope and Git authority rules.
- `skill:securityreview` (security-review): codex=**adopt** vs ours=**reject_after_review** — ours: It is predominantly TypeScript/Next/Supabase/Solana guidance with unsafe blanket prescriptions, so rewriting it would cost more than extendi
- `agent:architect` (architect): codex=**merge** vs ours=**reject_after_review** — ours: The prompt is bloated, prescriptive, frontend-biased, and contains unsupported scaling recipes that encourage speculative architecture.
- `agent:architecturestrategist` (architecture-strategist): codex=**merge** vs ours=**reject_after_review** — ours: Most guidance is generic SOLID and architecture-checklist material already required locally, with little unique operational technique.
- `agent:codesimplifier` (code-simplifier): codex=**merge** vs ours=**reject_after_review** — ours: Automatic post-task mutation adds risk and ceremony, while two variants hard-code JavaScript/React conventions that are poor fits for this P
- `agent:developmentworkflowsresearchagent` (development-workflows-research-agent): codex=**merge** vs ours=**reject_after_review** — ours: The prompt claims read-only behavior while granting write/edit and bypass permissions, uses incentive language, and relies on mutable counts
- `agent:docslookup` (docs-lookup): codex=**merge** vs ours=**reject_after_review** — ours: The installed docs researcher already provides the same workflow with better repo-version detection, tighter queries, and stronger non-fabri
- `agent:documentationanalystwriter` (documentation-analyst-writer): codex=**merge** vs ours=**reject_after_review** — ours: It is a verbose generic writing persona whose useful rules—read project guidance, match precedent, and verify against source—are already bas
- `agent:patternrecognitionspecialist` (pattern-recognition-specialist): codex=**merge** vs ours=**reject_after_review** — ours: The broad checklist encourages pattern cataloging, TODO counting, and speculative abstraction work without strong evidence or false-positive
- `agent:performanceoracle` (performance-oracle): codex=**merge** vs ours=**reject_after_review** — ours: Universal limits such as 200 ms responses, 5 KB bundles, and no algorithms worse than O(n log n) are context-free and would generate prematu
- `agent:pythonreviewer` (python-reviewer): codex=**merge** vs ours=**reject_after_review** — ours: Its useful checks already exist locally, while mandatory invocation, arbitrary size limits, blanket comprehension advice, and whole-repo dia
- `agent:reporesearchanalyst` (repo-research-analyst): codex=**merge** vs ours=**reject_after_review** — ours: The 257-line multi-ecosystem survey is too broad and repetitive; the local repo-map and architecture-research paths provide more focused ori
- `agent:requirementparser` (requirement-parser): codex=**merge** vs ours=**reject_after_review** — ours: It mostly duplicates the local brainstorming stage while adding a heavyweight serial-agent pipeline and potentially false precision around i
- `agent:securitysentinel` (security-sentinel): codex=**merge** vs ours=**reject_after_review** — ours: The review is primarily JavaScript/Rails grep recipes and generic compliance checklists, with insufficient Python coverage or evidence stand
- `agent:tddguide` (tdd-guide): codex=**merge** vs ours=**reject_after_review** — ours: Blanket 80% coverage, npm commands, mandatory test categories, and indiscriminate mocking/edge-case checklists are less reliable than the ex
- `command:aside` (aside): codex=**merge** vs ours=**reject_after_review** — ours: The behavior is useful, but a 164-line wrapper around normal conversational continuation adds ceremony without providing durable state prese
- `command:checkpoint` (checkpoint): codex=**reject_after_review** vs ours=**merge** — ours: Merge the checkpoint intent into Beads and verification workflows; the log stores no test or coverage baseline, while stash-or-commit behavi
- … and 87 more (grep row_evaluations.jsonl).
