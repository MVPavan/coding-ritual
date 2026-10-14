# Upstream review: agent-skills 0.6.6+30 → 0.6.13 (2026-10-14)

Submodule `reference_harnesses/agent-skills` (addyosmani/agent-skills) moved
from `7676817` to `aeac41d` (0.6.13, 2026-10-13): 170 commits, 132 files.
Three read-only reviewers compared the changes with our counterparts and the
46 earlier rulings in `ledger.json` (now the registry ledger); the gap claims for items 2–4 below
were re-checked by grep. Nothing was changed in our skills.

Paths are relative to the submodule unless they start with `.claude/`.

## Release themes

1. New skill `constraint-driven-development`, with the `/constraints` command
   and a `floor-guard` reference checker.
2. Severity labels unified as Critical/Required/Optional/Nit; `/review` runs
   in the main session instead of the persona.
3. Executable trigger evals (`evals/plugin/*`) and `evals/skill-impact.md`.
4. Large skills split into skill-local references (security, performance).
5. Hooks no longer wired by the plugin (`hooks/hooks.json` deleted);
   `simplify-ignore` and `sdd-cache` hardened.
6. More host docs (Copilot CLI, other hosts) and stricter linters.

## Worth acting on

| # | Upstream | Our gap | Suggestion |
|---|---|---|---|
| 1 | Trigger evals: per-skill "fires" and "stays quiet" cases, graded on the Skill tool call, with a control arm run without the skill (`evals/plugin/*/prompt.md`, `graders/*.md`); `evals/skill-impact.md` logs description changes the evals rejected | `.claude/skills/authoring-for-agents/references/testing-docs.md` prescribes this in prose; `.claude/scripts/skill-catalog.py` is static only | Build our own runner (their cases feed an upstream harness, not `scripts/run-evals.js`) |
| 2 | Security: destructive operations on derived paths: allowlisted root, depth floor, ownership evidence, TOCTOU caveat (`skills/security-and-hardening/SKILL.md:115-120`, `references/hardening-patterns.md:204-210`) | absent from `.claude/skills/security/` | Borrow into `references/boundary-controls.md` |
| 3 | Security: personal data and privacy: minimisation, retention, data-subject requests, consent (`SKILL.md:142-153`, `hardening-patterns.md:297-305`) | absent; ours names only a sensitive-data gate (`.claude/skills/security/SKILL.md:28`) | Borrow a short section |
| 4 | Performance: backend caching correctness: viewer/tenant/locale in the key, one invalidation strategy with a staleness window, stampede coalescing, never cache what must be fresh (`skills/performance-optimization/references/optimization-patterns.md:201-248`) | ours covers only HTTP `Cache-Control` (`.claude/skills/performance-optimization/references/frontend-performance.md`) | Borrow; a correctness class, not only speed |
| 5 | Performance: when an index will not help (`optimization-patterns.md:60-69`); connection-pool exhaustion (`:71-86`) | ours has only the positive index cases (`measurement-recipes.md:65-80`) | Borrow (small) |
| 6 | Planning: never overwrite an incomplete plan without asking (`skills/planning-and-task-breakdown/SKILL.md:171-176`) | not stated in `.claude/skills/planning/` | Borrow one line |

Optional: the shared-store rate-limit note (`hardening-patterns.md:259-271`)
for `.claude/skills/security/references/web.md`.

## No action; earlier rulings stand

- **`constraint-driven-development`** (`skills/constraint-driven-development/SKILL.md`):
  a `CONSTRAINTS.md` quality bar with an interview, ratchets and exception
  expiry, aimed at apps with coverage, accessibility and performance gates.
  It largely duplicates `.repo-context/invariants.md` and `verification.md`.
  One idea we lack: a diff-scoped check for a lowered bar (new suppressions,
  skipped or deleted tests, stubs). Low priority; candidate deferred spike.
- **Hooks**: no longer installed by default (better), but `simplify-ignore`
  still rewrites working files and depends on Stop restoration
  (`hooks/simplify-ignore.sh:11-13`), and `sdd-cache` still persists fetched
  content with an unversioned schema. Keep rejected.
- **spec-driven-development, interview-me**: added turn-stop rules and a scope
  check; our authority rules and `planning` decomposition already cover them.
- **idea-refine**: anatomy conformance only.
- **context-engineering**: new restartable-session checklist and context
  budget; the checklist is a possible borrow for a handoff reference, else
  still rejected.
- **documentation-and-adrs**: ADRs start `Proposed`; a prose-review rule
  (do not invent examples, keep qualifiers). Check `document-review` before
  borrowing.
- **api-and-interface-design** (idempotency keys), **observability**
  (entry-point field, runbooks), **shipping-and-launch** (error-budget gate):
  good content for surfaces this repo does not have. Rulings stand.
- **Ten small description edits** (TDD, debugging, git workflow and others):
  trigger phrases widened against the new evals. Evidence for item 1, not
  content to copy.
- **Severity relabel**: our `review` skill uses BLOCKER/MAJOR/MINOR; no
  change.

## Limits

The reviewers read the eval case and grader files; no eval was run. Control
arm behaviour is read from the declared `arm:` fields.
