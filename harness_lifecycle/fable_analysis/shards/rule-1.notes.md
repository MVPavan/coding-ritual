# rule-1 shard — worker notes

21 rows, all `kind: rule`. Sources: everything-claude-code (ECC, 15 rows), claude-code-best-practice (1 row), ours-only (.claude/.codex, 4 rows), mixed ours+ECC (2 rows: python coding-style, python testing).

## Evidence inspected

- ECC `rules/common/`: agents, development-workflow, git-workflow, hooks, performance, security, testing, code-review, coding-style, patterns (all read in full).
- ECC `rules/python/`: coding-style, hooks, patterns, security, testing (all read; each is a thin 20–40-line "extends common" file).
- ccbp `.claude/rules/markdown-docs.md` (read; has `paths:` lazy-load frontmatter).
- ECC `.claude/rules/everything-claude-code-guardrails.md`, plus `node.md` and ECC `CLAUDE.md` to confirm the "Prompt Defense Baseline" block is boilerplate stamped into every file.
- One `.cursor/rules/` mirror spot-checked (`common-agents`): identical body + Cursor frontmatter, with a slightly stale agent table — treated all `.cursor` paths as mirrors, not distinct capabilities.
- Local: `.claude/rules/core/01–03`, `.claude/rules/python/{coding-style,safety,testing}` (in loaded context) and diffed against `.codex` copies — byte-identical except one path-reference line in testing.md (`.claude/project/...` vs `.codex/project/...`, expected per-surface variance).

## Assumptions

- For **ours-only rows** (core/01, core/02, core/03, python/safety), the deep verdict answers "should this stay in the reusable harness?" — all four scored high, verdict `adopt` (retain). Fable's shallow "no — nothing to adopt" and gpt's "yes — useful" are both consistent with this reading.
- For **mixed rows** (python coding-style/testing appearing in both ours and ECC), scores rate the ECC variant; verdict `reject_after_review` means "keep ours, external adds nothing".
- Merge verdicts are deliberately narrow-scope per curation guardrails (borrow the smallest durable pattern).

## Verdict summary

| Verdict | Rows |
|---|---|
| adopt (keep ours) | python/safety, core/01-delegation, core/02-knowledge-discoverability, core/03-ak-guidelines |
| merge (narrow nugget) | common-agents (parallel + split-role → core/01), common-development-workflow (research-&-reuse step 0), common-git-workflow (commit format + PR procedure, one subsection), common-security (checklist form + rotation + incident protocol → python/safety), python-security (bandit one-liner only) |
| defer | common-performance (one durable context-window line; rest stale), common/code-review (good ladder but built-in /code-review + /security-review already cover it), python-hooks (idea → implement as real PostToolUse hook in mvp-plugin, rule text worthless) |
| reject_after_review | common-hooks, common-testing, markdown-docs, python-coding-style(ECC), python-patterns, python-testing(ECC), common-coding-style, common-patterns, ecc-guardrails |

## Weak rows / disagreements with shallow passes

- **ecc-guardrails**: gpt's "yes" is wrong — machine-generated, repo-specific, self-flagged as "review before treating as policy"; defense block is stamped boilerplate.
- **common-hooks, common-performance**: both shallow passes said yes, but content is largely restated platform docs with high staleness (stale model table, version-pinned thinking budget, keybindings).
- **common-coding-style**: fable's "maybe (redundant)" was more accurate than gpt's "yes" — naming section is JS-flavored (camelCase) and would conflict with our snake_case rule.
- **python-security (ECC)**: dotenv/os.environ pattern actively conflicts with our safety rule; merge scope is the bandit mention only.

## Cluster relationships

- `agent-delegation`: common-agents (external) + core/01-delegation (ours, merge target).
- `security-baseline`: common-security + python-security (external nuggets) + python/safety (ours, anchor).
- `testing-standards`: common-testing + python-testing(ECC) vs our python/testing.md — ours wins outright.
- `python-style`: python-coding-style(ECC) + python-patterns vs our coding-style.md — ours wins outright; note ECC dataclass-DTO advice conflicts with our Pydantic-frozen standard.
- `dev-workflow-pipeline` ↔ `design-patterns`: common-patterns' skeleton-project idea duplicates development-workflow's research-&-reuse step; routed once via the workflow row.
- `docs-conventions`: markdown-docs (rejected) vs core/02 (kept).
- Cross-shard hint: `code-review-core` and `security-baseline` items here likely cluster with skill/agent/command rows for review workflows in other shards.

## Bookkeeping

- Reading ECC/ccbp submodule files auto-injected their CLAUDE.md into context; treated as read-only reference, nothing edited under `reference_harnesses/`.
- Score staleness caveat: ECC common-performance names Sonnet as the best coding model and quotes a fixed 31,999-token thinking budget — dated as of 2026-07.
