# Shared skill audit

Date: 2026-09-10. Status: historical pre-implementation analysis.

The approved rewrite was subsequently applied under `.claude/skills` in Beads
`cr-zlo`: shared workflow owners, thin manual compatibility entrypoints, narrower
triggers, and conditional references. The original findings and inventory below
describe the audited pre-rewrite snapshot; their line numbers and hashes are not
claims about the current files. Model-behavior trials remain unperformed.
Scope: all 45 top-level repository skills, selected supporting references, the
Claude/Codex exposure mapping. Account-installed plugin comparisons are outside
this repository skill audit, per the user's clarification.
Beads: `cr-ygw`. Source revision: `4b53e6b89b4fa7dbeac2f279379500d254ba9ca0`,
with the existing uncommitted instruction changes included in this audit.

The library needs fewer compulsory workflows, clearer entry conditions, and a
single owner for each policy. Most specialized capabilities are worth keeping.
The strongest removal candidates are the standalone completion-verification
skill, the current cost-estimation methodology, and redundant interview/review
entrypoints. The greatest likely savings come from removing forced review and
approval chains, not shaving words from every small skill.

The recommendations follow the user's shared AGENTS.md policy and intended
model roles: GPT-5.6/Opus for implementation, Astra/Fable for substantive
planning and review. They are not claims that any family has been benchmarked
against this library.

## Evidence and limits

- **Verified:** repository text, file sizes, invocation metadata, symlink
  coverage, selected dependency chains, and the structural catalog check.
- **Inferred:** which prompts are vulnerable to unnecessary skill loading and
  which rules would cause extra work if followed. Examples below are static
  walkthroughs, not observed invocation frequencies.
- **Observed usage:** Claude Code's local aggregate counters were inspected
  during review reconciliation; see the usage section below. These do not
  measure repository-specific activation rates or unnecessary invocations.
- **Not measured:** actual token billing, latency savings, or comparative
  quality across the four model families. A skill's age or length alone does
  not establish that it is useless.
- Two bounded Codex CLI reviews were planned. Automatic approval review
  rejected the first launch because it would transmit private repository
  files to an external model service without specific payload/destination
  approval. Neither child review ran. The user subsequently supplied an
  independent text review in [review.md](review.md); its findings have been
  checked against local evidence. No behavioral model validation ran.
- Supporting scripts were inventoried, not comprehensively code-audited or
  executed. The two parked `in-progress` entrypoints were inspected separately.
  Account-installed plugins are excluded from the revised audit.

The [inventory](inventory.json) records each skill's path, size, description,
invocation mode, supporting-script paths, and entrypoint SHA-256. Counts are
whitespace-delimited words, including frontmatter; they are not token counts.

## What is actually loaded

| Surface | Current finding | Meaning |
|---|---|---|
| Canonical `.claude/skills/*/SKILL.md` | 45: 27 automatic, 18 manual | The shared source library |
| Codex-linked top-level skills | 39: 25 automatic, 14 manual | Six canonical entries are not linked |
| Entrypoint text | 38,035 words | Loaded selectively, not all at session start |
| Descriptions | 2,036 words total; 1,343 for automatic canonical entries | Discovery cost before bodies/references |
| Markdown including supporting references | 90 files, 69,472 words | On-disk inventory, not resident context |
| Largest description | `html-artifact`: 143 words, 992 characters | Its exclusions come after a long list of attractions |

OpenAI documents description-based selection and progressive loading, and
recommends concise, discriminating triggers. Codex invocation policy uses
`agents/openai.yaml`'s `allow_implicit_invocation`.
[OpenAI skill documentation](https://learn.chatgpt.com/docs/build-skills)
(retrieved 2026-09-10).

Claude documents `disable-model-invocation: true` for user-only invocation and
exclusion of that description from normal discovery context. It also documents
that loaded skill instructions persist across later turns. These mechanics
make accidental loading consequential beyond the first response.
[Claude skill documentation](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill)
(retrieved 2026-09-10). Exact listing/truncation behavior remains host-dependent;
do not treat all on-disk descriptions as exact current prompt content.

The catalog currently passes: 45 skills, 69 slash references, 62 `.claude/`
path references, and 45 matching Codex sidecars. Its ambiguity warning checks
matching **quoted phrases**, not semantic overlap or process amplification
(`.claude/scripts/skill-catalog.py:296`). Passing this check does not validate
behavior, cross-provider discovery, or external script availability.

## Observed Claude usage, added after review

The local `skillUsage` object has exact-name entries for 17 of the 45 skills;
28 have no matching entry. The [snapshot](claude-usage-snapshot.json) records
only these skill names, counts, and timestamps. It contains no session text.

| Skill | Recorded count | Last recorded date (UTC) |
|---|---|---|
| run-phases | 23 | 2026-07-07 |
| phase-execution | 15 | 2026-07-07 |
| i-have-adhd | 11 | 2026-09-03 |
| show-me | 11 | 2026-09-07 |
| html-artifact | 8 | 2026-08-03 |
| brainstorming | 4 | 2026-04-14 |
| model-council | 4 | 2026-08-24 |
| planning | 4 | 2026-04-14 |
| design-evolve | 2 | 2026-04-07 |
| grill-me | 2 | 2026-06-01 |
| teach-session | 2 | 2026-07-03 |
| authoring-for-agents | 1 | 2026-08-12 |
| codebase-research | 1 | 2026-08-21 |
| cost-estimate | 1 | 2026-06-10 |
| document-review | 1 | 2026-04-08 |
| harness-skill-compare | 1 | 2026-08-13 |
| systematic-debugging | 1 | 2026-07-18 |

These are local aggregate dispatch counters across projects, not a complete
usage history of this library revision. They omit direct file reads, do not
cover Codex, and do not distinguish deliberate from unnecessary invocation.
The supplied review itself reports five recent `model-council` invocations
against an aggregate count of four; its recent-session sample was not
recomputed here. This discrepancy reinforces that the aggregate must not be
labelled a complete lifetime total or treated as a denominator for use rates.

The counts strengthen the case for preserving convenient wrappers such as
`run-phases`, `phase-execution`, `show-me`, and the personal communication
skill. `grill-me` and `teach-session` have recorded use, so preserve their
manual aliases if merging their implementations. An absent completion-skill
counter does not prove the skill is unused: its callers can read or follow
it directly. Retirement still rests on duplicated policy and harmful
message-based verification, not zero usage. The low `cost-estimate` count is
secondary to its unsupported estimation method.

## Highest-priority findings

### 1. Small execution still reaches two final reviewers

`execution/SKILL.md:35` says small work is inline with a self-check, but
`execution/SKILL.md:118` routes even inline task work into Final review.
`execution/references/task-engine.md:186` then requires a code reviewer on the
strongest available model **and** a separate critic. Standard units also
require an implementer dispatch regardless of whether delegation helps.
All paths in this section are under `.claude/skills/`.

A small, fully specified, planless `ready-for-agent` typo task can therefore
inherit two child reviews. For one task with no findings, the prescribed
child calls are: small = 2, standard = 3, deep = 5. A deep task consuming all
five fix/re-review rounds plus the final fix/re-review can reach 17 calls,
excluding planning, retries, or other nested skill calls. This is a static
count of the prescribed path, not an observed run or cost estimate.

**Recommendation:** let small tasks finish with scoped local verification.
For substantive changes, use one independent review when its expected value
justifies it. Reserve separate spec and quality reviewers for changes with
distinct risks that benefit from both. Runtime configuration selects the
model; remove the universal strongest-model requirement. Preserve bounded
dispatches, owned files, review snapshots, acceptance criteria, and stage gates.

### 2. Review findings become authoritative before they are verified

The deep task engine requires findings to be relayed into fixes and permits
adjudication only at the five-round cap (`task-engine.md:133`, `:148`, `:176`).
`receiving-code-review/SKILL.md:16` repeats this exception even though its
normal method is to verify feedback before implementing it.

An incorrect reviewer claim can drive repeated incorrect edits. This
conflicts with AGENTS.md's requirement to verify consequential agent claims
and change approach when repetitions produce no evidence. Calling this
"independent review" does not make its output authoritative.

**Recommendation:** verify and disposition findings immediately: confirmed,
refuted with evidence, or unresolved. Fix confirmed defects; escalate real
scope/authority decisions. Keep a bounded loop as a ceiling, not a minimum
number of attempts before judgment. A disputed finding does not authorize a
scope change.

### 3. Verification is tied to messages instead of changed state

`verification-before-completion/SKILL.md:8` requires a fresh run in the same
message as a claim. Its table at `:29` rejects an earlier run. AGENTS.md
already requires applicable checks and limits repetition to new changes,
failures, or unresolved risk.

**Recommendation:** retire this as an independently triggered skill. Preserve
any unique claim/evidence examples as a short conditional reference in the
project verification guide. Evidence remains usable while the relevant code,
environment, and scope are unchanged; report what actually ran. Do not turn
"Can you summarize the finished change?" into another test run.

Before retirement, update these five referring files: `execution/SKILL.md:96`
and `:120`, `systematic-debugging/SKILL.md:146`,
`performance-optimization/SKILL.md:140`, `skill-router/SKILL.md:47`, and
`authoring-for-agents/references/skill-anatomy.md:69` (all under
`.claude/skills/`). Regenerate the router and remove the retired entrypoint's
sidecar/link only as part of that approved change. Prose references need an
explicit search; slash-reference validation alone will miss them.

### 4. Small ambiguity can trigger a specification and approval pipeline

Brainstorming has a useful small-explicit-task exit, but only after its
mandatory grounding reads (`brainstorming/SKILL.md:12`, `:31`). It still
requires a saved spec for a small ambiguous ask (`:70`). Planning's bounded
route reads the full orientation set, locks a file map, writes a plan, and
ends with a handoff and stop (`planning/SKILL.md:24`, `:36`, `:69`, `:100`).
The planning body allows small work on stated assumptions, while its final
rules and `references/plan-format.md` demand matching approval before Beads
writes. These branches do not express one consistent small-task policy.

**Recommendation:** route before reading. Clarify a material missing detail
locally; use a durable spec when multiple decisions, sessions, or downstream
implementers need one. A clear authorized task should not need a synthetic
plan to qualify for implementation. Retain spec/roadmap/stage contracts for
workstreams. Reuse existing approval and continue through authorized execution.

### 5. Cheap lookup and feedback cases require costly workflows

- `research/SKILL.md:18` mandates a docs-researcher for one API/CLI fact;
  `:37` repeats this for incidental facts. A direct official lookup is often
  sufficient. Source-count ranges at `:48` should guide, not impose quotas.
- `grilling/SKILL.md:20` mandates a child even for an environment fact the
  parent can read cheaply. Its whole-frontier questioning can also become
  an overwhelming batch.
- `test-driven-development/SKILL.md:48` asks the user to approve the test seam
  for attended, planless work, even when the seam is an obvious implementation
  detail. `:74` and `:130` demand a full suite on the test-first path.
- `receiving-code-review/SKILL.md:25` blocks all implementation if any item
  is unclear, even when other items are independent.

**Recommendation:** direct lookup for bounded facts; delegation only for an
independent useful unit. Ask about materially disputed behavior, not routine
test placement. Run the repo's applicable gate. Continue independent fixes
while blocked items await clarification.

### 6. Several recipes replace judgment with arbitrary numbers

`systematic-debugging/SKILL.md:10` prohibits hypotheses before a reproduction
command exists, then usually demands complete minimization and 3–5 hypotheses
(`:74`, `:86`). Forming a provisional hypothesis from code or logs is often
how one designs the reproducer. Three failed fixes do not, by themselves,
prove an architectural fault (`:126`). Preserve the distinction between a
hypothesis and a confirmed cause.

`performance-optimization/SKILL.md:30` mandates 5+ repetitions, profiling
before ranking any bottleneck, and a regression guard for every win. These
are useful for uncertain performance claims, excessive for every simple
measurement or deterministic removal of repeated work. Measurement design
should match noise, cost, and the decision.

**Recommendation:** retain controlled reproduction, evidence before claiming
a fix, realistic baselines, and comparable measurements. Make minimization,
multiple hypotheses, repeated trials, and new guards conditional. Remove
unsupported success percentages and slogans presented as empirical facts.

### 7. The shared source is not yet a shared exposed catalog

The six missing Codex links are `harness-evaluate`, `harness-publish`,
`harness-scan`, `harness-skill-compare`, `harness-status`, and `show-me`.
`.codex/README.md:7` intentionally excludes `harness-*`; the router still
lists them. Root-only distribution scope does not itself explain why Codex
working in this root cannot discover them. No reason for `show-me`'s absence
was found in that README.

**Recommendation:** explicitly choose the exposed set for this root and the
distributed plugin separately. If the goal is both harnesses doing the same
work here, link supported root skills into both and check discovery. Keep
provider metadata as generated adapters, not separate workflow bodies.

The publishing submodule is currently uninitialized: `git submodule status
-- mvp-harness` begins with `-`; publishing scripts referenced by the skills
are absent here. This is an environment prerequisite, not proof the
publishing skill is obsolete. The root catalog does not catch it.

### 8. Some specialized skills need substantive corrections

- **Cost estimate:** `cost-estimate/SKILL.md:148` derives AI active hours from
  commit windows, file timestamps, or LOC/350. Its rates reference labels
  uncited LOC/hour tables "industry standards." These proxies do not measure
  active work or a counterfactual human cost; replacement cost also is not
  business value. Retire the current method. If retained as a capability,
  rebuild around explicit scope, comparable work, uncertainty, and actual
  telemetry; do not present invented ROI as measurement.
- **Perspective council:** five first-round agents plus five peer reviewers
  and a chair is 11 child calls (`perspective-council/SKILL.md:27`). Its rule
  that sequential dispatch causes contamination is incorrect: information
  sharing causes it. Same-model agreement is not independent evidence for
  correctness. Keep as a deliberate expensive option; preserve isolation,
  calibrate confidence, and permit bounded scheduling.
- **Model council:** `model-council/SKILL.md:18` hardcodes provider aliases,
  an old bridge retirement, and effort in prompt text. Preserve user member
  selection and failure reporting; resolve actual runtime support and effort
  through configuration/adapters, without silent substitution.
- **Prototype:** the general trigger routes every logic question to HTML,
  every UI question to variants, says no tests/error handling, and asks to
  fold validated decisions into real code (`prototype/SKILL.md:14`, `:24`,
  `:26`). Allow a small script or experiment; preserve necessary safety and
  checks that answer the question. A prototype request alone does not
  authorize production integration.
- **Beads/memory:** `beads/SKILL.md:47` and `.beads/beads.md:13` direct durable
  knowledge to `MEMORY.md`; the injected runtime hook prescribes the opposite.
  This is a deliberate repository override, not accidental drift: the local
  files explicitly reject the hook's memory policy. Preserve that recorded
  choice unless a separate decision changes it. State the override once in
  the project policy and reference it; neither wording grants automatic
  memory-writing authority. AGENTS.md still requires an explicit request,
  and higher-priority runtime memory restrictions still apply.

### 9. Review packaging can omit or absorb the wrong changes

Without a supplied package, `code-review/SKILL.md:45` falls back to
`git diff BASE..HEAD`, which covers committed revisions, not unstaged,
staged-but-uncommitted, or untracked changes. For an ad-hoc request to review
local edits, that can miss the actual work. Conversely, the task engine's
scope snapshot defines all changes since HEAD as the review surface
(`execution/references/task-engine.md:61`), and its final package omits owned
path arguments (`:191`). In a dirty checkout, that can include unrelated work.
Workstream mode records a dirty baseline; that does not by itself repair all
ad-hoc/task review paths.

**Recommendation:** resolve the intended review surface first: committed
range, current working changes, or explicitly supplied artifact. Record the
initial dirty state and owned paths for any implementation scope. Include
new files deliberately and flag mixed pre-existing edits. Preserve useful
snapshot tooling; do not equate a passing packaging command with correct
scope. This finding follows the documented commands; the packaging script's
implementation was not comprehensively audited here.

## Per-skill disposition

Each linked entry is the audited source. "Keep + trim" preserves the
capability, not every current instruction. "Merge" retires an independent
entrypoint only after its useful material and inbound references are handled.
Manual convenience wrappers are not automatically waste: most cost no
automatic trigger load and preserve useful user habits.

### Shared engineering and instruction skills

| Skill | Decision | Keep; change |
|---|---|---|
| [authoring-for-agents](../../../../.claude/skills/authoring-for-agents/SKILL.md) | Keep + trim | Keep named failure, conditional pointers, proportional evaluation. Trigger on instruction behavior changes, not a punctuation correction. Replace mandatory three new rules per failed pressure case with revising the smallest effective instruction. Treat writing heuristics as heuristics, not universal psychological laws. |
| [beads](../../../../.claude/skills/beads/SKILL.md) | Keep + trim | Keep actor tags, spec/roadmap/plan-field meanings, recovery and renderer. Narrow broad session/task trigger; let AGENTS.md and runtime context cover routine tracking. Disclose the command table only when needed; align memory policy. |
| [code-review](../../../../.claude/skills/code-review/SKILL.md) | Keep + restructure | Keep evidence, severity, scoped re-review and read-only boundary. Main file selects inline/review mode; detailed dispatch contracts become a reference. Do not force self-checks through full preflight. Permit a useful review with declared failing checks. Infer an obvious supplied diff/base rather than always asking. Remove mandatory praise/pristine-output rules. |
| [codebase-design](../../../../.claude/skills/codebase-design/SKILL.md) | Keep + narrow | Keep deep-module and testability vocabulary for real interface decisions. Remove the ban on normal words such as API/service/boundary and hard claims that two adapters are required to justify every interface. Make design-it-twice optional, not an automatic three-agent exercise. |
| [document-review](../../../../.claude/skills/document-review/SKILL.md) | Keep, small correction | Already only 175 words and a useful contract. Remove unconditional secondary critic for standard/deep docs: a dispatched independent reviewer should not recursively need another reviewer. |
| [domain-modeling](../../../../.claude/skills/domain-modeling/SKILL.md) | Keep | Good distinction between reading and changing the domain model; lazy files and a selective ADR gate. Persist terms only when the task authorizes that, not during an analysis-only conversation. |
| [performance-optimization](../../../../.claude/skills/performance-optimization/SKILL.md) | Keep + trim | Keep measured user outcome, comparable baseline, noise awareness and correctness. Move tool recipes behind symptom routes. Make repetition/profiling/guard costs proportional; do not trigger on editing prose containing "optimize." |
| [receiving-code-review](../../../../.claude/skills/receiving-code-review/SKILL.md) | Merge into code-review | Preserve per-item disposition and evidence-based disagreement in a feedback mode. Remove etiquette bans, whole-review blocking for independent items, and the fix-loop exception that delays verification. |
| [research](../../../../.claude/skills/research/SKILL.md) | Keep + trim | Keep open-question synthesis, primary evidence and counterarguments. Directly answer bounded facts with an appropriate lookup. Drop compulsory source quotas, incidental docs-agent calls, and fixed report sections for every task. |
| [resolving-merge-conflicts](../../../../.claude/skills/resolving-merge-conflicts/SKILL.md) | Keep | Already 218 words with a real trigger: an active conflict. Preserve both intents, checks, named staging paths and commit authority. Scale history/PR archaeology to disputed hunks. |
| [security](../../../../.claude/skills/security/SKILL.md) | Keep + restructure | Keep changed-boundary analysis and code-enforced controls. Narrow "dependency changes"/"LLM features" to material security changes. Route to relevant controls instead of a broad checklist. Preserve recognition of already-approved actions. Distinguish permissions documented in prompts from permissions enforced in code. |
| [systematic-debugging](../../../../.claude/skills/systematic-debugging/SKILL.md) | Keep + major trim | Keep reproduction, localization, causal evidence, regression proof and the polluter script. Allow provisional hypotheses, an obvious-error path, and proportionate minimization. Remove arbitrary hypothesis/retry explanations and the blanket ban on independently validated remedies mentioned by logs. |
| [test-driven-development](../../../../.claude/skills/test-driven-development/SKILL.md) | Keep + narrow modes | Preserve test-first vs characterization distinction and independent expectations. Route test-only edits straight to the quality reference. Remove routine seam approval and generic full-suite demands; keep required repository gates. Do not treat internal tests or partial fakes as inherently invalid. |
| [verification-before-completion](../../../../.claude/skills/verification-before-completion/SKILL.md) | Retire standalone | AGENTS.md already owns truthful, proportional verification. Move only unique useful evidence examples to the project verification reference; update all callers before removal. |
| [skill-router](../../../../.claude/skills/skill-router/SKILL.md) | Keep + update | Useful index for manual capabilities. Add an explicit ordinary-task/no-skill route; align it with the actually exposed catalog. Do not make it a mandatory read on every task. |

### Planning, design and deliberation

| Skill | Decision | Keep; change |
|---|---|---|
| [brainstorming](../../../../.claude/skills/brainstorming/SKILL.md) | Keep + simplify | Own unresolved scope and the decision-to-spec transition. Route before grounding; one missing detail need not produce a spec. Make durable output and independent review depend on handoff/risk. |
| [idea-refine](../../../../.claude/skills/idea-refine/SKILL.md) | Merge into brainstorming reference | Keep divergence, assumptions and excluded options as an optional exploration mode. Remove the compulsory 5–8 ideas, fixed questions, saved one-pager, and forced phases when direction is already clear. |
| [planning](../../../../.claude/skills/planning/SKILL.md) | Keep + restructure | Valuable workstream/stage contracts and just-in-time plans. Separate a short direct-task path from decomposition/elaboration. Preserve outputs and dependencies, but allow implementation to discover file-level details. Reuse approval and continue when execution is authorized. |
| [execution](../../../../.claude/skills/execution/SKILL.md) | Keep + major correction | Keep state machine, acceptance gates, scope selection, safe snapshots and recovery. Remove forced small-task final reviewers and delayed finding adjudication. Standard delegation must pass the shared benefit test. Fix providers' compaction/model assumptions. |
| [design-evolve](../../../../.claude/skills/design-evolve/SKILL.md) | Keep + large trim | Valuable precision/invariant/source-preservation workflow. At 2,385 words, move templates and large-document mechanics out of the entrypoint. Replace the <5KB/1–2-file dispatch threshold with contextual judgment. Avoid repeated approval of supplied paths and routine grouping. Verify consequential summaries against source sections. |
| [grilling](../../../../.claude/skills/grilling/SKILL.md) | Keep + narrow | Own explicitly requested interviewing. Keep dependency-aware questions and absent-respondent questionnaire mode. Bound the material decision frontier; allow ordinary lookups inline and manageable question batches. A request for written critique is not automatically an interview. |
| [grill-me](../../../../.claude/skills/grill-me/SKILL.md) | Merge into grilling | Same decision-tree interview, different verbosity and pacing rules. Keep only a thin manual alias if used; retire its independent 1,317-word recipe. |
| [grill-with-docs](../../../../.claude/skills/grill-with-docs/SKILL.md) | Merge option; alias optional | Compose grilling plus authorized domain documentation. Remove "strictly better whenever a directory exists": a repo does not mean every conversation should edit its glossary. Its 85-word wrapper is not an urgent cost problem. |
| [model-council](../../../../.claude/skills/model-council/SKILL.md) | Keep, explicit opt-in | User-selected independent solutions and a judge are distinct from normal review. Update runtime member resolution; preserve member attribution and no silent replacement. Consider native manual invocation if slash/dollar invocation suits the user's habits. |
| [perspective-council](../../../../.claude/skills/perspective-council/SKILL.md) | Keep as expensive opt-in | Already excludes ordinary decisions well. Make five-plus-five-plus-chair an explicit full mode; allow a smaller declared council. Preserve informational independence rather than requiring simultaneous dispatch. No confidence inflation from agreement. |
| [prototype](../../../../.claude/skills/prototype/SKILL.md) | Keep + widen artifact choices | Keep a named question, runnable experiment and recorded answer. Select script/HTML/UI by the question. Avoid automatic production changes, mandatory variant galleries, or removal of safety checks. |
| [wayfinder](../../../../.claude/skills/wayfinder/SKILL.md) | Keep manual + trim | Distinct value for multi-session decision dependencies; not equivalent to an implementation plan. Preserve frontier and resolution pointers. Remove arbitrary 100K-token task sizing and one-ticket-per-session limits. Align tracker fallback and persistent decisions with Beads/AGENTS.md. |

### Repository operations

| Skill | Decision | Keep; change |
|---|---|---|
| [check-invariants](../../../../.claude/skills/check-invariants/SKILL.md) | Keep manual | 69-word wrapper for explicit executable invariants. No need for a larger replacement. |
| [codebase-research](../../../../.claude/skills/codebase-research/SKILL.md) | Keep manual + trim | Preserve snapshot, documented/present/wired/exercised distinctions and foreign-code trust boundary. Narrow mechanism questions should not need a whole-repo report. Clarify that explaining local code is not an architecture-improvement request. |
| [improve-codebase-architecture](../../../../.claude/skills/improve-codebase-architecture/SKILL.md) | Keep manual + narrow | Preserve evidence-backed architectural friction and scoped candidate selection. Make the HTML report and follow-on interview optional outcomes; a review alone should not update the glossary. Reuse shared visualization guidance rather than duplicating its styling rules. |
| [harness-evaluate](../../../../.claude/skills/harness-evaluate/SKILL.md) | Keep + update | Unique adoption ledger and dependency-boundary choices. Update old dual-source/template workflow assumptions; separate analysis/decision from authorized adoption and publication. Make root Codex discoverability intentional. |
| [harness-publish](../../../../.claude/skills/harness-publish/SKILL.md) | Keep manual | Deterministic publish, neutrality/leak audits and versioning justify a skill. Add a clear submodule/tool prerequisite check and preserve explicit publication/commit authority. Current scripts cannot run in this uninitialized checkout. |
| [harness-scan](../../../../.claude/skills/harness-scan/SKILL.md) | Keep manual | Useful drift/gap script wrapper; preserve pins. Ensure scan/report does not silently turn into ledger mutation/adoption beyond its authorization. |
| [harness-skill-compare](../../../../.claude/skills/harness-skill-compare/SKILL.md) | Keep + scale depth | The component matrix is useful for actual curation. Remove the unconditional subagent-choice question and reading every shipped file for a simple overlap question. Keep full inventories for a full behavioral comparison. |
| [harness-status](../../../../.claude/skills/harness-status/SKILL.md) | Keep manual | Cheap operational summary and offline fallback. Describe fetch as a network/ref-cache update while pins remain fixed, rather than completely read-only. |
| [migrate-claude-to-codex](../../../../.claude/skills/migrate-claude-to-codex/SKILL.md) | Keep manual + update | Bundled dry-run/apply/verify tooling has real value. Shared policy should not be duplicated into provider-specific Markdown rules. Update mappings and runtime discovery proof; preserve generic migration of other repositories rather than deleting the capability. |
| [phase-execution](../../../../.claude/skills/phase-execution/SKILL.md) | Keep manual wrapper | 75 words; useful explicit phase entrypoint. Inherit corrected engine behavior and carry previously granted authorization. |
| [run-phases](../../../../.claude/skills/run-phases/SKILL.md) | Keep manual wrapper | 87 words; meaningful unattended opt-in. Preserve declared scope and commit semantics, while eliminating unconditional `/compact` and provider-specific assumptions in the reference. |
| [triage](../../../../.claude/skills/triage/SKILL.md) | Keep manual | Repository intake states and readiness gate are specialized. Respect an explicit bulk-triage authorization instead of asking item by item. "Could not reproduce" should remain unresolved, not be silently rejected. |

### Human-facing outputs and optional personal workflows

| Skill | Decision | Keep; change |
|---|---|---|
| [html-artifact](../../../../.claude/skills/html-artifact/SKILL.md) | Keep + shorten trigger/body | Keep standalone, offline, accessible output and preset routing. Trigger on an HTML deliverable or a visualization that materially helps, not the words report/plan/one-pager. Move aesthetic catalogs into optional references. Use available browser checks rather than always assigning them to the user. |
| [show-me](../../../../.claude/skills/show-me/SKILL.md) | Keep manual | A small in-chat visual contract, distinct from an HTML document. Restore or explain missing Codex exposure. |
| [teach](../../../../.claude/skills/teach/SKILL.md) | Keep optional/manual + trim | Useful for deliberate multi-session learning. Do not assume every explanation authorizes a root-level teaching workspace or permanent preference notes. Make course artifacts conditional; remove exact equal-character quiz-answer constraints. |
| [teach-session](../../../../.claude/skills/teach-session/SKILL.md) | Merge into teach | A session-walkthrough mode is enough. Keep retrieval questions; remove "master everything before ending" as an unbounded completion condition. |
| [i-have-adhd](../../../../.claude/skills/i-have-adhd/SKILL.md) | Keep personal/manual + trim | User-selected communication preferences can be valuable. Remove categorical claims about every reader's memory or dopamine, fabricated time precision, and mandatory recaps every turn. Do not infer a diagnosis from installing a skill. |
| [cost-estimate](../../../../.claude/skills/cost-estimate/SKILL.md) | Retire current method | Unsupported LOC/commit-based ROI creates false precision. Rebuild only if estimation is a recurring need; explicit assumptions and calibrated evidence should replace the current calculation recipe. |

### Parked surfaces

`in-progress/agent-matrix` and `in-progress/use-codex` are outside the top-level
catalog and are not linked into Codex. Keep them parked; their static provider
facts are not current runtime proof. Do not re-enable them as part of cleanup.

The system OpenAI documentation/skill-creation tools need not be copied into
the repository. This audit judges the maintained repository library, not
account-installed external capabilities.

## Static routing examples

These are proposed acceptance cases for a later behavior evaluation. They
identify a plausible current failure path; they are not executed model tests.
Ordinary tasks still follow AGENTS.md, Beads requirements, and applicable gates.

| Request | Desired skill behavior | Current risk |
|---|---|---|
| Fix punctuation in AGENTS.md | Direct edit, reread/diff | Authoring loads on any agent-document edit |
| Fix a typo in a ready Beads task | Direct task execution and scoped check | Small path reaches two final reviewers |
| What command runs one pytest test? | Read project verification/official docs as needed | Research description mandates a docs child for one fact |
| Explain this function | Read the function and needed callers | Architecture/design keywords can attract an unrelated workflow |
| Shorten this plan's wording | Direct editorial edit | Planning/authoring/HTML triggers can compete |
| Review this plan for gaps | One document review | Review adds another critic even if it is already the independent pass |
| Implement this clear two-file change | Brief local plan only if useful; execute | Planning document, broad grounding, handoff stop |
| Rename a test for readability | Test-quality mode only if needed; scoped check | TDD entrypoint loads an entire test-first workflow |
| Fix this failing null-input case | Focused reproduction, fix, proving test | Minimization/hypothesis count/seam approval can expand it |
| Summarize the verified change | Reuse valid evidence with its scope | Verification skill demands a fresh run for another claim |
| Here are three fixes; one needs clarification | Verify all, do independent clear items | Feedback skill blocks every implementation |
| Brainstorm two alternatives; no file needed | Brief divergence in chat | Mandatory 5–8 variants, fixed phases, saved one-pager |
| Grill me about this architecture | Bounded material decision interview | Three interview variants have different pacing/persistence rules |
| Compare two tools for adoption | Research, sources proportional to decision | Fixed source counts and incidental child lookups |
| Reduce measured service p95 | Performance workflow and realistic baseline | Appropriate trigger; preserve this positive case |
| Change authorization for tenant data | Security lens and abuse tests | Appropriate trigger; do not trim away actual controls |
| Run a named model council | Resolve configured models, independent reports, judge | Appropriate explicit costly workflow; old provider table may block |
| Create design v3 from these decisions | Design integration, provenance and complete output | Mandatory per-file children and repeated routine approvals |
| Run all remaining roadmap phases | Execution workstream mode | Preserve opt-in, dependencies and acceptance gates |
| Show the call flow inline | Small diagram using show-me | Local Codex link absent; HTML routes can compete |

## Shared design rules for the next revision

Keep **one semantic workflow per job**, shared by all four families. A skill
should contain the unusual contract, necessary inputs/outputs, decision
boundary, essential safeguards and conditional references. It need not teach
an experienced coding model how to be conscientious in ten different ways.

Candidate descriptions, not applied changes:

| Skill | Shorter trigger |
|---|---|
| authoring-for-agents | Use when creating or changing agent instructions or their activation behavior. Skip edits that only correct spelling or formatting. |
| brainstorming | Use when material scope or behavior decisions must be resolved before work can proceed. Handle a single routine ambiguity directly. |
| planning | Use when settled work needs a durable implementation plan, dependency graph, or workstream decomposition. |
| execution | Use to execute tracked multi-step work or a roadmap. Carry clear bounded requests directly through implementation and verification. |
| code-review | Use for a substantive code review or to verify and act on review findings. Routine final diff inspection is not a separate review workflow. |
| systematic-debugging | Use when a failure's cause is unclear or an attempted fix failed. Handle an obvious localized error with a focused reproduction and fix. |
| research | Use when a decision needs multiple sources gathered and weighed. Answer a single factual lookup directly from an appropriate source. |
| security | Use for a material change to trust boundaries, sensitive data, permissions, or execution of untrusted input, and for requested security reviews. |
| html-artifact | Use for standalone HTML documents or interactive explanations when that format materially helps the reader. |

Specific runtime model IDs, effort controls, delegation APIs, manual-invocation
metadata, sandbox capabilities, and compaction belong in configuration or a
small adapter. The shared skill states what a worker/reviewer must establish.
Do not duplicate the skill for Astra/Fable/Opus/GPT-5.6 or mandate the strongest
model for every review. Use the configured workhorse for bounded implementation;
reserve planner/critic capacity for unresolved architecture, cross-cutting
changes, and consequential final review. This is a role policy, not a claim
that one family is always superior.

OpenAI's current skill-creator guidance explicitly favors non-obvious
instructions, task-scoped specialist workflows, and preserving operational
invariants while removing generic advice and speculative edge cases.
[Official skill-creator source](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/SKILL.md)
(retrieved 2026-09-10). The user's
[Eric Provencher article](../../../prompting-guides/articles/eric-provencher.txt)
supports the same audit direction. Its model-behavior claims remain guidance,
not a local ablation result.

## Suggested implementation order and evaluation

1. Correct harmful interactions first: immediate finding verification,
   proportionate final review, evidence reuse, approval carry-through, and
   scope-preserving prototype behavior.
2. Consolidate duplicate repository entrypoints. Preserve
   useful references and manual aliases; update callers, generated sidecars,
   symlinks, router and publish mappings together. This is not an instruction
   to remove anything during this analysis.
3. Trim high-cost bodies: execution/task engine, code-review, debugging,
   design-evolve, planning, research, security, HTML. Keep branch-common text
   inline; relocate substantial conditional content. Avoid replacing one
   large file with a chain of mandatory reference reads.
4. Check the effective catalog in both harnesses. The five root curation
   exclusions are a product choice to reconcile, not silently undo. Treat the
   publishing submodule as a separately verified prerequisite.
5. Evaluate changed triggers on the positive/negative examples above in fresh
   contexts, plus realistic execution cases. Compare current and reduced
   guidance on representative tasks for all four families as available.

Track task success, missed requirements, regressions, unauthorized scope
changes, unnecessary user interruptions, child calls, repeated checks, loaded
instruction volume and elapsed work. Measure tokens from actual telemetry;
do not equate word reduction or cached input with a billing reduction.
Hold repository, tools, model/effort and task constant within each comparison.
Use repeated cases where routing varies; do not substitute a large arbitrary
test quota for a meaningful coverage set.

The acceptance bar is maintained quality with less unnecessary work, not the
fewest skills or shortest prompt. Keep safety-critical and repository-specific
contracts until there is evidence that their replacement preserves behavior.
Small deterministic wrappers need no elaborate model experiment when only
their documentation is unchanged.

Strongest counterargument: some rigid-looking rules may encode past failures
of smaller models or long unattended runs. Removing them everywhere at once
could regress those workflows. Preserve the specialized gates and test
high-impact reductions first; do not interpret this audit as proof that
advanced models never need steering.

## Verification of this audit

- The existing catalog check passed; no active skill or runtime configuration
  was changed for this audit.
- Inventory covers exactly the 45 top-level skills, with parked skills and
  external-plugin sampling explicitly separated.
- Final artifact checks verify inventory consistency, cited path/line
  existence, and whitespace; no application tests are needed for a report.
- Behavioral invocation tests remain unperformed. The supplied independent
  text review is reconciled in [review-response.md](review-response.md).
  Performance/quality improvements require the later comparison above.
