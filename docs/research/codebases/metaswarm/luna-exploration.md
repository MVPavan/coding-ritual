# metaswarm — Luna High exploration (raw report)

> GPT-5.6-Luna, effort high, read-only, 2026-09-11. Verbatim reply to the question set
> below, over the pinned `reference_tools/metaswarm/` submodule. Not independently verified:
> every `file:line` is Luna's claim — check before acting on one. Absolute paths were
> rewritten repo-relative; nothing else was edited.
>
> Resume this exploration with its context intact:
> `codex-run.mjs --resume 01a08fe2-82fe-7913-93d2-596cdf14d073 -m gpt-5.6-luna -e high -s read-only "<question>"`
> (`--resume` ignores `-C`; the session keeps its original cwd, which is the right repo.)

## Question set as sent

```text
Explore this repository thoroughly and answer the questions below. READ-ONLY: make no edits,
no commits, no git operations that mutate anything. This repo is a read-only reference.

WHY I AM ASKING. I am building a "phase bridge" in a different repository: a deterministic
interpreter that runs ONE unit of work to completion while an LLM decides which unit comes
next. Its properties: durable admission written before any claim so a crash cannot orphan
work; exactly one compare-and-swap to land a signed artifact; human approval gates crossed
before anything lands; per-unit retry with a full attempt history; and a CLI returning a
machine-readable state which is a FACT for the LLM to act on, never an instruction.

This repo describes itself as a self-improving multi-agent orchestration framework with 18
agent personas, 13 skills, a 9-phase workflow, a 4-phase execution loop per work unit, a
parallel design review gate with a 3-iteration cap before human escalation, and an
orchestrator that "validates independently, never trusts subagent self-reports". That last
property is exactly the discipline I have been enforcing by hand. I want to know how much of
it is MECHANISM and how much is PROSE.

Answer these. Cite file:line for every substantive claim — I will check them.

1. PROSE VERSUS MECHANISM. For each of the headline claims above, is it enforced by code (a
   script, a hook, an exit code) or asserted in a markdown instruction an agent may ignore?
   Give me the split honestly, claim by claim. This is my most important question.

2. "NEVER TRUSTS SELF-REPORTS". Show exactly how the orchestrator validates independently.
   What does it re-run or re-read? What happens when a subagent's claim and the
   orchestrator's check disagree?

3. THE WORK UNIT. How is work decomposed into units, what is a unit's durable
   representation, and what carries state between the 4 phases (IMPLEMENT / VALIDATE /
   ADVERSARIAL REVIEW / COMMIT)? If a run dies between phases, what does the next run see?

4. THE ITERATION CAP. The 3-iteration cap before human escalation — where is it counted, what
   is the counter stored in, and can an agent reset or evade it? I deliberately CUT a numeric
   retry cap from my own design in favour of requiring a human gate on the path, so I am
   very interested in whether a numeric cap survives contact with reality here.

5. REVIEW GATES. How do the parallel review agents actually gate anything? What blocks
   progress when a reviewer objects — a check, a human, or an instruction to stop?

6. HUMAN ESCALATION. What does escalation look like mechanically? How does the human's answer
   re-enter the run, and is it bound to the thing they approved?

7. THE KNOWLEDGE BASE. It claims a git-native knowledge base and self-improvement. What is
   actually written back, by whom, when, and what stops it from accumulating noise or acting
   on a stale lesson?

8. AGENT AUTHORING. 18 personas and 13 skills is a large surface. How are they kept
   consistent, is there a catalog or lint, and what stops two agents' instructions from
   contradicting each other?

9. FAILURE MODES. Read CHANGELOG.md, docs/, guides/ and any retrospective material for
   reversals and warnings. What did they try that did not work? What did they remove?

10. THE ONE THING. If I could borrow exactly one durable pattern — not a feature, a pattern —
    what should it be and why? And name the single biggest thing this project does that my
    design above is missing.

FORMAT: answer each numbered question in order, with citations. Where a claim turns out to be
prose rather than mechanism, say so plainly — that is the most useful answer you can give me,
not a criticism of the project. Where something does not exist, say so rather than
constructing something plausible. End with a short list of anything you found that I did not
think to ask about.
```

## Luna's reply

> **INCOMPLETE — the capture was truncated, not the answer.** The dispatch piped Luna's
> stdout through `tail`, so the reply below begins mid-answer to question 4. **Answers to
> questions 1, 2 and 3 were lost** — including question 1 (prose versus mechanism), which the
> prompt names as the most important one. The Luna session still holds the full context, so
> re-asking recovers them: resume with the id in the header. Nothing here is wrong; it is
> partial.

The counter is not protected. It is stored in ordinary Markdown, labels, and variables inside instructions. There is no monotonic database field, signed transition, or verifier that rejects a reset.

An agent can reset or evade it through documented paths:

- Starting fresh abandons the existing plan. `commands/start-task.md:17-22`
- Troubleshooting explicitly permits resetting a failed task to open and removing its failure label. `skills/start/SKILL.md:747-759`
- The plan-review gate does not apply to trivial work under its stated thresholds. `skills/plan-review-gate/SKILL.md:24-31`
- Human escalation includes “Override,” which allows continuation after the cap. `skills/design-review-gate/SKILL.md:110-130`

The external-tools skill introduces another inconsistency: it documents up to five attempts when two external tools are available, rather than the headline three. `skills/external-tools/SKILL.md:176-218`

There is no complete durable attempt ledger. The escalation report contains a manually populated failure-history table, but that is a reporting format rather than an append-only record. `skills/orchestrated-execution/SKILL.md:780-802`

## 5. Review gates

The review agents can be launched in parallel if the host LLM follows the instructions. The design gate specifies five roles and requires all to approve; the plan gate specifies three independent reviewers. `skills/design-review-gate/SKILL.md:1-23`, `skills/plan-review-gate/SKILL.md:91-104`

When a reviewer objects, the documented action is:

- consolidate the objections,
- revise the plan or design,
- rerun the reviewers,
- escalate after the iteration limit. `skills/design-review-gate/SKILL.md:110-130`, `skills/plan-review-gate/SKILL.md:129-186`

That blocks progress only through instruction-following. There is no executable aggregator whose nonzero exit code prevents the next phase.

The external adapter provides real process-level gating for invocation failures and timeouts, but not semantic review rejection. A reviewer can emit FAIL in the raw log while the adapter still returns success if the model process itself exited zero. `skills/external-tools/adapters/codex.sh:291-318`, `skills/external-tools/adapters/codex.sh:366-387`

There are genuine exit-code gates elsewhere:

- Generated CI can fail on lint, type checking, tests, or coverage. `templates/ci.yml:1-54`
- The PR comment checker exits nonzero for unresolved review comments. `bin/pr-comments-check.sh:79-85`
- The GTG workflow maps failures to blocked readiness states. `templates/gtg-workflow.yml:42-88`

Those gates protect CI/PR readiness, not the complete design-review or per-unit state machine.

## 6. Human escalation

The documented escalation mechanisms are:

- After three failed design iterations, ask the human to override, defer, or cancel. `skills/design-review-gate/SKILL.md:110-130`
- After three failed plan-review iterations, present remaining objections and ask the human to choose Override, Revise, Simplify, or Cancel. `skills/plan-review-gate/SKILL.md:155-186`
- For a work-unit checkpoint, report the decision, evidence, risks, and options, then explicitly wait. `skills/orchestrated-execution/SKILL.md:601-646`
- For issue orchestration, mark the task blocked, add `waiting:human`, create a GitHub issue, and accept a reply such as `@beads approve <task-id>`. `agents/issue-orchestrator.md:529-568`

The human’s answer re-enters through conversation, issue comments, or a manually updated plan. The approved plan is represented by metadata such as `user-approved: true`. `skills/plan-review-gate/SKILL.md:396-415`

That approval is logically associated with a task or plan ID, but it is not cryptographically bound to:

- a specific specification hash,
- a specific diff,
- a specific artifact,
- a specific commit,
- or a specific reviewer identity.

More seriously, the ordinary work-unit flow commits before its optional human checkpoint. `skills/orchestrated-execution/SKILL.md:327-352`

So human escalation exists as a protocol, but not as a tamper-resistant approval gate before artifact landing.

## 7. The knowledge base

The knowledge base is JSONL with fields for:

- lesson content,
- provenance,
- confidence,
- usage count,
- helpful count,
- outdated reports,
- affected files,
- timestamps. `knowledge/README.md:27-75`

The intended contributors are humans, agents, and the Knowledge Curator. `knowledge/README.md:89-108`

The intended write paths are:

- pre-PR self-reflection,
- post-merge or epic-close curation,
- manual additions after incidents or reviews. `skills/orchestrated-execution/SKILL.md:717-735`, `agents/issue-orchestrator.md:375-386`, `skills/start/agents/knowledge-curator-agent.md:1-33`

Noise controls are described, not enforced:

- reject PR-specific or personality-based observations,
- reject duplicates,
- require provenance,
- assign confidence,
- ask the user to approve or edit candidate learnings,
- use similarity-based deduplication. `commands/self-reflect.md:11-60`, `commands/self-reflect.md:107-180`, `skills/start/agents/knowledge-curator-agent.md:181-206`

The old custom self-reflection script was removed in favor of `bd compact`. `CHANGELOG.md:9-25`

Staleness handling is also procedural. The schema has `outdatedReports`, timestamps, and affected files, and the curator is instructed to review stale or low-confidence entries, but there is no automatic rule preventing a stale lesson from being injected into a run. `knowledge/README.md:27-75`, `skills/start/agents/knowledge-curator-agent.md:198-206`

The checked-in knowledge files are mostly schemas and example entries, not a substantial accumulated lesson corpus. `knowledge/README.md:1-25`, `knowledge/agents.jsonl:1-4`, `knowledge/patterns.jsonl:1-4`

## 8. Agent authoring

Authoring consistency is handled through conventions:

- put agents in `agents/`,
- give them Role, Responsibilities, Process, Output, and Integration sections,
- update ORCHESTRATION and USAGE when adding one. `CONTRIBUTING.md:15-29`

Skill consistency has a small automated check: required files and frontmatter names are validated. `tests/codex/test-codex-skills.sh:52-79`

There is no contradiction lint across agent instructions. The test checks file presence and metadata, not whether two agents define incompatible policies. `tests/codex/test-codex-skills.sh:52-79`

The surface is visibly inconsistent:

- README: 18 agents and 13 skills. `README.md:3-5`
- `AGENTS.md`: 19 agents and 13 skills. `AGENTS.md:1-3`
- Codex and Claude manifests: 19 agents and 14 skills. `.codex-plugin/plugin.json:1-4`, `.claude-plugin/plugin.json:1-4`
- `USAGE.md` describes the design gate as six agents, while the current design-review skill defines five. `USAGE.md:122-135`, `skills/design-review-gate/SKILL.md:1-23`

There are also duplicated or migrated resource locations. The migration plan explicitly discusses removing redundant mirrors while preserving compatibility paths, and the resource-sync map covers many resource types but does not establish semantic consistency among all agent files. `docs/plans/2026-02-26-plugin-migration-plan.md:1417-1458`, `lib/sync-resources.js:10-77`

Nothing prevents two persona files from contradicting each other except the supervising LLM’s judgment.

## 9. Failure modes, reversals, and removals

The repository’s clearest retrospective evidence is in the changelog and migration design notes.

- The original npm distribution caused stale versions, manual friction, and ecosystem misalignment, so the project moved toward marketplace/plugin distribution. `CHANGELOG.md:63-83`, `docs/plans/2026-02-26-plugin-migration-design.md:7-28`
- Copying more than 60 files and requiring 30–60 minutes of manual setup was treated as a failure, leading to a thinner CLI plus guided setup. `docs/plans/2026-02-26-guided-setup-design.md:1-13`
- Aspirational YAML triggers were removed and replaced with documentation describing the actual three-layer instruction model. `CHANGELOG.md:92-109`
- `EnterPlanMode` was identified as bypassing the project’s gates, so an interception rule was added. That is direct evidence that the workflow could be bypassed by the host agent. `CHANGELOG.md:99-103`
- Advisory quality gates were rewritten as “blocking state transitions,” but the implementation remained largely in skills and prompts. `CHANGELOG.md:188-201`
- The custom `beads-self-reflect.ts` machinery was removed in favor of standalone BEADS compaction. `CHANGELOG.md:9-25`
- External-tool limitations include unreliable hangs at timeout boundaries, approximate cost accounting, and no pre-execution cost cap. `docs/plans/2026-02-14-external-tools-design.md:468-474`
- A command-injection issue in the CI template’s `eval` path was fixed by switching to an argument array, an allowlist, and metacharacter rejection. `docs/plans/2026-02-26-plugin-migration-design.md:518-546`
- The current pre-push template still uses `eval` for configured commands, although it is guarded by the local configuration format. `templates/pre-push:38-54`
- The migration review found broken paths, a phantom `typescript-patterns.md` reference, stale counts, missing status functionality, and resource-discovery gaps. `docs/plans/2026-02-26-plugin-migration-design.md:699-720`
- The migration removed redundant mirror directories created by the previous installer. `docs/plans/2026-02-26-plugin-migration-plan.md:1417-1458`

The recurring lesson is that the project repeatedly moved complexity out of brittle automation and into documented host-agent behavior. That reduced packaging and maintenance problems, but it also means the central guarantees remain vulnerable to instruction-following failures.

## 10. The one thing

Borrow this pattern:

> Make the verifier, not the implementer, own the transition predicate.

The implementer should emit facts only. A verifier should reread the specification and artifact, rerun the checks, inspect the scope, and produce the only admissible transition evidence. A fresh reviewer should receive the specification, DoD, and diff rather than the implementer’s report. That is the strongest reusable idea in this repository. `skills/orchestrated-execution/SKILL.md:237-271`, `skills/orchestrated-execution/SKILL.md:287-325`, `skills/external-tools/SKILL.md:147-159`

The biggest thing your phase bridge appears to be missing is a final cross-unit integration/reconciliation gate. This repository explicitly performs a final review over the complete diff, full tests, type checks, lint, coverage, Git history, cross-unit contracts, imports, scopes, and service inventory. `skills/orchestrated-execution/SKILL.md:650-687`

A one-unit interpreter can make every individual unit correct while still producing an incompatible aggregate. Your LLM can choose the next unit, but an outer verifier still needs to establish that the accumulated artifact remains coherent before publication.

Additional findings:

- The repository has real resource-drift detection: `sync-resources.js --check` compares hashes and exits nonzero on drift. `lib/sync-resources.js:304-375`
- Session-start recovery is partly real, but setup and `bd prime` errors are deliberately swallowed with `|| true`, so recovery can report success despite setup failure. `hooks/session-start.sh:63-107`, `hooks/session-start.sh:137-145`
- Team Mode and Task Mode have materially different persistence semantics: Team teammates retain context, while Task-mode subagents are fire-and-forget with no persistent state between invocations. `guides/agent-coordination.md:55-83`
- The external implement path commits inside its worktree before the orchestration skill’s validation and review phases, which is an important mismatch with a “nothing lands before approval” model. `skills/external-tools/adapters/codex.sh:74-185`


