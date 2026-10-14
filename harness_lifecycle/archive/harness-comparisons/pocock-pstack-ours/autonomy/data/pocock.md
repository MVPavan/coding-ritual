# Matt Pocock skills (v1.3.1): autonomy map

Source: `reference_harnesses/mattpocock_skills` at tag v1.3.1, commit 24fe0ef. Version: reference_harnesses/mattpocock_skills/.claude-plugin/plugin.json:3 and reference_harnesses/mattpocock_skills/package.json:3.
Scope: 37 SKILL.md files outside `deprecated/` (the bucket is empty, reference_harnesses/mattpocock_skills/skills/deprecated/README.md:3). 27 are promoted (20 in `engineering/`, 7 in `productivity/`) and ship in the plugin (reference_harnesses/mattpocock_skills/CLAUDE.md:9; 27 entries in reference_harnesses/mattpocock_skills/.claude-plugin/plugin.json). 4 are in `misc/` and 6 are in `in-progress/`, marked **[IP]** below.

Citation shorthand: a bare `<skill>:N` means `reference_harnesses/mattpocock_skills/skills/<bucket>/<skill>/SKILL.md:N`. A bare `<FILE>.md:N` (for example ADR-FORMAT, DESIGN-IT-TWICE, PHASE-BOUNDARIES, AGENT-BRIEF, OUT-OF-SCOPE, SKILL-MECHANICS, mocking.md, tests.md, domain.md, issue-tracker-github.md) means the sibling reference file in that skill's folder. All other paths are relative to the repo root.

Corrections to the prior notes (`harness_lifecycle/harness-comparisons/pocock-pstack-ours/pocock-vs-pstack.md`):
- The repo has no `AGENTS.md`. Its steering file is reference_harnesses/mattpocock_skills/CLAUDE.md. The prior notes cite `mattpocock_skills/AGENTS.md` (pocock-vs-pstack.md:23).
- The promoted set is 27 skills, not 30. The plugin.json skills array has 27 entries and its version is 1.3.1.
- J: The other claims I re-checked hold: implement-spec, pr and retro are additions, and the "tell the user to run setup" carve-out exists.

Three inconsistencies inside the source:
- The README says setup offers "GitHub, Linear, or local files" (reference_harnesses/mattpocock_skills/README.md:78). The setup skill actually offers GitHub, GitLab, Local markdown and Other (reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/SKILL.md:44-47). Linear is reached only through "Other", as free-form prose.
- `implement` names its dependencies as bare `/tdd` and `/code-review` mentions (reference_harnesses/mattpocock_skills/skills/engineering/implement/SKILL.md:9,13). This breaks the house rule that a skill must say "call the Skill tool" (reference_harnesses/mattpocock_skills/.agents/invocation.md:16).
- ADR-0001 still uses the old skill name `diagnose` (reference_harnesses/mattpocock_skills/.agents/adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md:8).

## 1. Infrastructure assumptions

| Assumption | Evidence (path:line) | What breaks without it |
|---|---|---|
| **Harness with a Skill tool, plus a way to block the model from invoking a skill.** Claude Code `disable-model-invocation: true`; Codex `policy.allow_implicit_invocation: false` | reference_harnesses/mattpocock_skills/.agents/invocation.md:5,8,16 ; reference_harnesses/mattpocock_skills/CLAUDE.md:19 | Skill-to-skill dependencies are written as "call the Skill tool with X". Without the block, user-invoked orchestrators could fire on their own. |
| **Distribution.** A Claude Code plugin (read-only, auto-updating), or skills.sh copies (editable) for Codex and other agents | reference_harnesses/mattpocock_skills/README.md:27-71 ; reference_harnesses/mattpocock_skills/.agents/adr/0002-ship-as-a-claude-code-plugin.md:21-23 | A native Codex plugin is deferred because Codex `skills` takes one path and drops symlinks (adr/0002:13-17). |
| **Models.** No model is named. The skills are meant to work with any model | reference_harnesses/mattpocock_skills/README.md:19 | n/a. No per-role model routing. |
| **Subagents.** A generic subagent API, with background subagents for research and implement-spec | reference_harnesses/mattpocock_skills/skills/productivity/grilling/SKILL.md:26 ; reference_harnesses/mattpocock_skills/skills/engineering/code-review/SKILL.md:11,58 ; reference_harnesses/mattpocock_skills/skills/engineering/research/SKILL.md:6 ; reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:17 | code-review loses its isolated parallel axes. research cannot run in the background. implement-spec loses concurrency, which the docs call "the point" (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:22). |
| **Git worktrees, one per implementer** | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:27-28,40 ; reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:22 | No isolated parallel implementers. Tests that read gitignored fixtures skip silently inside a worktree (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:66-68). |
| **Branch model.** One **integration branch** per spec. Implementer branches merge onto it through a merger subagent | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:11,25,32 | No defined landing target for a multi-ticket build. |
| **Branch model.** Throwaway `prototype/<name>` and `research/<name>` branches kept out of main as primary sources | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:85 ; reference_harnesses/mattpocock_skills/skills/engineering/prototype/SKILL.md:26 ; reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:115 | The prototype and research evidence has no durable home. |
| **PRs are optional.** A draft PR opens only if the tracker closes work through PRs or the user asks for one. `pr` shapes the body | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:25,38 ; reference_harnesses/mattpocock_skills/skills/engineering/pr/SKILL.md:12-33 ; reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:32,44 | Nothing breaks. The run stops on the integration branch and works offline on a local tracker. |
| **No stacked PRs and no merge/release skill.** The merge-conflict skill was removed in v1.3.0 | reference_harnesses/mattpocock_skills/docs/engineering/resolving-merge-conflicts.md:1 | Merging and releasing the user's own work is left to the human or the harness. |
| **Issue tracker.** GitHub (`gh`), GitLab (`glab`), local markdown under `.scratch/<feature>/`, or a free-form "Other". Only mainstream trackers are supported | reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/SKILL.md:42-49 ; reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/issue-tracker-local.md:7-11 ; reference_harnesses/mattpocock_skills/.out-of-scope/mainstream-issue-trackers-only.md:3 | This is a hard dependency for to-spec, to-tickets and triage: output is "wrong, not just fuzzy" (reference_harnesses/mattpocock_skills/.agents/adr/0001-explicit-setup-pointer-only-for-hard-dependencies.md:7). implement-spec and wayfinder also stop. |
| **Blocking edges between tickets.** Native links / sub-issues (GitHub issue dependencies, GitLab `/blocked_by`) are one representation; local files and trackers without native links use a `Blocked by:` line | reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/issue-tracker-github.md:41-43 ; reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/issue-tracker-gitlab.md:43 ; reference_harnesses/mattpocock_skills/skills/engineering/to-tickets/SKILL.md:62-65 | The frontier cannot be computed, and implement-spec's task graph goes flat (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:21). Known gap: GitHub's blocked-by count only drops when the blocker closes, so it is stale mid-run (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:58-60). |
| **Triage labels.** Five canonical roles: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. Plus `wayfinder:map` and `wayfinder:<type>` | reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/triage-labels.md:5-11 ; reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:26-37 ; reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:21,65 | triage cannot apply states. AFK pickup has no `ready-for-agent` signal. |
| **Per-repo config.** `docs/agents/{issue-tracker,triage-labels,domain}.md`, plus an `## Agent skills` block in CLAUDE.md or AGENTS.md | reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/SKILL.md:49,63-112 | Hard-dependency skills tell the user to run `/setup-matt-pocock-skills` (reference_harnesses/mattpocock_skills/skills/engineering/to-spec/SKILL.md:9). |
| **Domain docs.** `GLOSSARY.md` (or `GLOSSARY-MAP.md` for several contexts) and `docs/adr/NNNN-slug.md`, all created lazily | reference_harnesses/mattpocock_skills/skills/engineering/domain-modeling/SKILL.md:10-40 ; reference_harnesses/mattpocock_skills/skills/engineering/domain-modeling/ADR-FORMAT.md:3-5 ; reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/domain.md:5-11 | Soft dependency: the skills proceed silently, and output is just less sharp (domain.md:11 ; adr/0001:8). |
| **Repo standards files.** `CODING_STANDARDS.md` / `CONTRIBUTING.md`, read at review time | reference_harnesses/mattpocock_skills/skills/engineering/code-review/SKILL.md:36 ; reference_harnesses/mattpocock_skills/skills/engineering/retro/SKILL.md:42 | The Standards axis falls back to the Fowler smell baseline only (code-review:38). |
| **CI / bots.** None are assumed for the user's repo. This repo's own CI only runs changesets versioning | reference_harnesses/mattpocock_skills/.github/workflows/release.yml:1-37 ; reference_harnesses/mattpocock_skills/skills/engineering/retro/SKILL.md:18 | n/a. retro treats a missing guardrail (no pre-commit, no CI) as a finding. |
| **Hooks.** None in the core set. The optional misc skill installs a PreToolUse hook that blocks `git push`, `reset --hard`, `clean`, and similar | reference_harnesses/mattpocock_skills/skills/misc/git-guardrails-claude-code/SKILL.md:8-18 ; reference_harnesses/mattpocock_skills/skills/misc/git-guardrails-claude-code/scripts/block-dangerous-git.sh:6-22 | Nothing enforces git safety by default. |
| **Human touchpoints.** Every user-invoked skill fires only when a human types it, and no skill can chain to one | reference_harnesses/mattpocock_skills/.agents/invocation.md:8,22 ; reference_harnesses/mattpocock_skills/README.md:186 | J: This is the structural limit on autonomy. The main flow is a series of human-typed steps. |
| **Persistence.** Tracker issues and comments, GLOSSARY/ADRs, `.out-of-scope/`, the wayfinder map, handoff files in the OS temp dir, research markdown, the teach workspace, and harness session logs (read by retro). No run ledger | reference_harnesses/mattpocock_skills/skills/engineering/triage/OUT-OF-SCOPE.md:3-6 ; reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:21-23 ; reference_harnesses/mattpocock_skills/skills/productivity/handoff/SKILL.md:8 ; reference_harnesses/mattpocock_skills/skills/engineering/retro/SKILL.md:13 | Cross-session state lives only in the tracker and docs. There is no machine-readable run state. |
| **Context budget.** A "smart zone" of about 150k tokens. Decide continue, clear, handoff, subagent or compact at phase boundaries only | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:36-38 ; reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/PHASE-BOUNDARIES.md:5,19-40 | Compacting mid-phase "makes the agent lose the thread" (PHASE-BOUNDARIES:5). |
| **Autonomy level.** Human-orchestrated by default. Autonomy is local: implement-spec within one session, AFK ticket types, `ready-for-agent` for external AFK runners. Truly AFK work is pointed at an external deterministic loop (Sandcastle, a script, CI) | reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:62-64 ; reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:75 ; reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:35 | See section 6. |

## 2. Nodes

Invocation is "user-only" when the skill has `disable-model-invocation: true` (it is also listed in the openai.yaml `allow_implicit_invocation: false` set). Otherwise it is "model", which means the model or the user can reach it.

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| ask-matt | skill (router) | user-only | Maps every user-reachable skill into a main flow, on-ramps, standalones and phase-boundary choices (reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:9-95) |
| setup-matt-pocock-skills | skill | user-only | Run once per repo. Writes the tracker, label and domain-doc config to `docs/agents/*` and adds an `## Agent skills` block (reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/SKILL.md:9-13) |
| grill-with-docs | skill (wrapper) | user-only | One line: call the Skill tool for grilling and for domain-modeling (reference_harnesses/mattpocock_skills/skills/engineering/grill-with-docs/SKILL.md:7) |
| to-spec | skill | user-only | Synthesises the conversation into a spec without re-interviewing, publishes it with `ready-for-agent` (reference_harnesses/mattpocock_skills/skills/engineering/to-spec/SKILL.md:7,19) |
| to-tickets | skill | user-only | Splits work into tracer-bullet tickets with blocking edges and publishes them `ready-for-agent` (reference_harnesses/mattpocock_skills/skills/engineering/to-tickets/SKILL.md:9,58-65) |
| implement | skill | user-only | Builds a spec or ticket with tdd, runs checks, reviews with code-review, then commits (reference_harnesses/mattpocock_skills/skills/engineering/implement/SKILL.md:7-15) |
| implement-spec | skill | user-only | Orchestrates a whole spec as a task graph: background implementer subagents in worktrees, a merger subagent, one integration branch, a final code-review (reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:11-40) |
| triage | skill | user-only | Moves incoming issues and external PRs through the triage-role state machine and writes agent briefs (reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:9-112) |
| wayfinder | skill | user-only | Plans foggy, multi-session efforts as a map of decision tickets, one ticket resolved per session (reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:7,105) |
| improve-codebase-architecture | skill | user-only | Surveys the codebase for deepening opportunities, writes an HTML report, then grills through the candidate the user picks (reference_harnesses/mattpocock_skills/skills/engineering/improve-codebase-architecture/SKILL.md:9-71) |
| retro | skill | user-only | Reviews a session and proposes improvements to the agent's environment, most severe first (reference_harnesses/mattpocock_skills/skills/engineering/retro/SKILL.md:7-25) |
| code-review | skill | model | Two-axis (Standards, Spec) review of the diff since a fixed point, using parallel subagents (reference_harnesses/mattpocock_skills/skills/engineering/code-review/SKILL.md:6-11) |
| tdd | skill | model | Red-to-green vertical slices at seams agreed with the user (reference_harnesses/mattpocock_skills/skills/engineering/tdd/SKILL.md:8,22) |
| diagnosing-bugs | skill | model | Six-phase bug and performance discipline, gated on a tight loop that goes red (reference_harnesses/mattpocock_skills/skills/engineering/diagnosing-bugs/SKILL.md:18-138) |
| prototype | skill | model | Throwaway code that answers one design question, either logic HTML or UI variants (reference_harnesses/mattpocock_skills/skills/engineering/prototype/SKILL.md:8-26) |
| research | skill | model | A background agent reads primary sources and writes a cited markdown file (reference_harnesses/mattpocock_skills/skills/engineering/research/SKILL.md:6-12) |
| domain-modeling | skill | model | Actively sharpens terms and updates GLOSSARY.md and ADRs inline (reference_harnesses/mattpocock_skills/skills/engineering/domain-modeling/SKILL.md:8,60-74) |
| codebase-design | skill (reference) | model | Deep-module vocabulary and principles, plus DEEPENING and DESIGN-IT-TWICE (reference_harnesses/mattpocock_skills/skills/engineering/codebase-design/SKILL.md:8,111-114) |
| pr | skill (template) | model | PR body template: Summary visual, before/after Evidence, Merge Danger (reference_harnesses/mattpocock_skills/skills/engineering/pr/SKILL.md:12-33) |
| wizard | skill | model | Generates an interactive bash script for steps only a human can do (reference_harnesses/mattpocock_skills/skills/engineering/wizard/SKILL.md:8-12) |
| grill-me | skill (wrapper) | user-only | Stateless interview. Calls the Skill tool with grilling (reference_harnesses/mattpocock_skills/skills/productivity/grill-me/SKILL.md:7) |
| grilling | skill (primitive) | model | Interviews the human in rounds over a design-tree frontier. Facts are the agent's to find, decisions are the user's (reference_harnesses/mattpocock_skills/skills/productivity/grilling/SKILL.md:6-28) |
| handoff | skill | user-only | Writes a portable handoff doc to the OS temp dir, with suggested skills (reference_harnesses/mattpocock_skills/skills/productivity/handoff/SKILL.md:8-16) |
| teach | skill | user-only | Multi-session tutoring with a stateful workspace (reference_harnesses/mattpocock_skills/skills/productivity/teach/SKILL.md:8-20) |
| to-questionnaire | skill | user-only | Writes a markdown questionnaire to pull a decision out of someone else (reference_harnesses/mattpocock_skills/skills/productivity/to-questionnaire/SKILL.md:7-16) |
| wait-what | skill | user-only | Re-pitches the last message in plain English using GLOSSARY.md vocabulary (reference_harnesses/mattpocock_skills/skills/productivity/wait-what/SKILL.md:7) |
| writing-for-agents | skill (reference) | model | Style guide for any document an agent consumes. SKILL-MECHANICS covers skills specifically (reference_harnesses/mattpocock_skills/skills/productivity/writing-for-agents/SKILL.md:6-8) |
| git-guardrails-claude-code (misc) | skill | model | Installs a PreToolUse hook that blocks dangerous git commands (reference_harnesses/mattpocock_skills/skills/misc/git-guardrails-claude-code/SKILL.md:8) |
| setup-pre-commit (misc) | skill | model | Husky + lint-staged + typecheck/test pre-commit hook (reference_harnesses/mattpocock_skills/skills/misc/setup-pre-commit/SKILL.md:8-14) |
| migrate-to-shoehorn (misc) | skill | model | Replaces `as` in tests with shoehorn (reference_harnesses/mattpocock_skills/skills/misc/migrate-to-shoehorn/SKILL.md:1-12) |
| scaffold-exercises (misc) | skill | model | Scaffolds course exercise directories (reference_harnesses/mattpocock_skills/skills/misc/scaffold-exercises/SKILL.md:8) |
| claude-handoff **[IP]** | skill | user-only | Hands off to `claude --bg` with a summary prompt (reference_harnesses/mattpocock_skills/skills/in-progress/claude-handoff/SKILL.md:8) |
| loop-me **[IP]** | skill | user-only | Stateful grilling whose only output is workflow specs in `workflows/*.md` (reference_harnesses/mattpocock_skills/skills/in-progress/loop-me/SKILL.md:8-14) |
| setup-ts-deep-modules **[IP]** | skill | user-only | Wires dependency-cruiser entry-point rules and proves they fail on a violation (reference_harnesses/mattpocock_skills/skills/in-progress/setup-ts-deep-modules/SKILL.md:9,79-87) |
| writing-fragments **[IP]** | skill | user-only | Writing "explore" step: grills the user for raw fragments (reference_harnesses/mattpocock_skills/skills/in-progress/writing-fragments/SKILL.md:9-11) |
| writing-shape **[IP]** | skill | user-only | Writing "exploit" step: shapes raw material into an article paragraph by paragraph (reference_harnesses/mattpocock_skills/skills/in-progress/writing-shape/SKILL.md:9-11) |
| writing-beats **[IP]** | skill | user-only | Writing "exploit" step: builds an article as a choose-your-own-adventure path of beats (reference_harnesses/mattpocock_skills/skills/in-progress/writing-beats/SKILL.md:9-19) |
| PHASE-BOUNDARIES | doc | code (read by ask-matt) | Ordered tree for the boundary choice: continue, /clear, /handoff, subagent, /compact (reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/PHASE-BOUNDARIES.md:7-40) |
| docs/agents/* config | doc (per-repo, generated) | code (read by skills) | issue-tracker.md, triage-labels.md, domain.md seeded from templates (reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/SKILL.md:104-112) |
| AGENT-BRIEF / OUT-OF-SCOPE | doc | code (read by triage) | Agent-brief contract and the rejected-request knowledge base (reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:21-22) |
| hitl-loop.template.sh | script | code | Structured human-in-the-loop repro loop for diagnosing-bugs (reference_harnesses/mattpocock_skills/skills/engineering/diagnosing-bugs/scripts/hitl-loop.template.sh:1-16) |
| wizard template.sh | script | code | Shared wizard library: stages, confirm gates, `.env` and `gh secret` writes (reference_harnesses/mattpocock_skills/skills/engineering/wizard/SKILL.md:10) |
| block-dangerous-git.sh | hook | always (once installed) | PreToolUse Bash matcher. Exits 2 on dangerous patterns (reference_harnesses/mattpocock_skills/skills/misc/git-guardrails-claude-code/scripts/block-dangerous-git.sh:6-22) |
| implementer subagent | agent (generic) | code (spawned) | One per ticket, in its own worktree. Drives tdd and merges the integration tip before reporting (reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:27-30) |
| merger subagent | agent (generic) | code (spawned) | Lands a finished implementer branch onto the integration branch (reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:32) |
| exploration subagent | agent (generic) | code (spawned, optional) | Saves exploration notes outside the repo for later implementers (reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:23) |
| Standards / Spec reviewer subagents | agent (generic) | code (spawned) | Parallel review axes, each answering in under 400 words (reference_harnesses/mattpocock_skills/skills/engineering/code-review/SKILL.md:58-72) |
| link-skills.sh | script (maintainer) | user-only | Symlinks non-misc, non-deprecated skills into `~/.claude/skills` and `~/.agents/skills` (reference_harnesses/mattpocock_skills/scripts/link-skills.sh:4-24) |

## 3. Edges

| from | to | relation | evidence (path:line) |
|---|---|---|---|
| ask-matt | grill-with-docs | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:17 |
| ask-matt | grill-me | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:17,83 |
| ask-matt | handoff | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:18-21,73 |
| ask-matt | prototype | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:20,85 |
| ask-matt | to-spec | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:23 |
| ask-matt | to-tickets | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:23 |
| ask-matt | implement | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:24,26 |
| ask-matt | implement-spec | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:25 |
| ask-matt | tdd | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:28 |
| ask-matt | code-review | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:28 |
| ask-matt | pr | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:30 |
| ask-matt | retro | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:32,36 |
| ask-matt | triage | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:44 |
| ask-matt | diagnosing-bugs | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:48 |
| ask-matt | wayfinder | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:50 |
| ask-matt | improve-codebase-architecture | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:58 |
| ask-matt | domain-modeling | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:64 |
| ask-matt | codebase-design | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:65 |
| ask-matt | grilling | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:84 |
| ask-matt | research | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:86 |
| ask-matt | to-questionnaire | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:87 |
| ask-matt | wizard | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:88 |
| ask-matt | wait-what | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:89 |
| ask-matt | teach | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:90 |
| ask-matt | writing-for-agents | routes-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:91 |
| ask-matt | setup-matt-pocock-skills | routes-to (precondition) | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:93-95 |
| ask-matt | PHASE-BOUNDARIES | reads | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:77 |
| wayfinder | to-spec | hands-off-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:52 |
| improve-codebase-architecture | grill-with-docs | hands-off-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:58 |
| research | grill-with-docs | hands-off-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:86 |
| to-questionnaire | grill-with-docs / to-spec | hands-off-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:87 |
| triage | implement | hands-off-to (agent-ready issues) | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:44 |
| diagnosing-bugs | retro | hands-off-to | reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:48 |
| grill-with-docs | grilling | invokes | reference_harnesses/mattpocock_skills/skills/engineering/grill-with-docs/SKILL.md:7 |
| grill-with-docs | domain-modeling | invokes | reference_harnesses/mattpocock_skills/skills/engineering/grill-with-docs/SKILL.md:7 |
| grill-me | grilling | invokes | reference_harnesses/mattpocock_skills/skills/productivity/grill-me/SKILL.md:7 |
| grilling | (fact-finding subagent) | invokes | reference_harnesses/mattpocock_skills/skills/productivity/grilling/SKILL.md:26 |
| domain-modeling | GLOSSARY.md / docs/adr | produces | reference_harnesses/mattpocock_skills/skills/engineering/domain-modeling/SKILL.md:40,62,74 |
| to-spec | setup-matt-pocock-skills | requires (tell the user) | reference_harnesses/mattpocock_skills/skills/engineering/to-spec/SKILL.md:9 |
| to-spec | spec issue + `ready-for-agent` | produces | reference_harnesses/mattpocock_skills/skills/engineering/to-spec/SKILL.md:19 |
| to-tickets | setup-matt-pocock-skills | requires (tell the user) | reference_harnesses/mattpocock_skills/skills/engineering/to-tickets/SKILL.md:11 |
| to-tickets | tickets with blocking edges + `ready-for-agent` | produces | reference_harnesses/mattpocock_skills/skills/engineering/to-tickets/SKILL.md:58-65 |
| implement | tdd | invokes (bare `/tdd` mention) | reference_harnesses/mattpocock_skills/skills/engineering/implement/SKILL.md:9 |
| implement | code-review | invokes (bare `/code-review` mention) | reference_harnesses/mattpocock_skills/skills/engineering/implement/SKILL.md:13 |
| implement | commit on current branch | produces | reference_harnesses/mattpocock_skills/skills/engineering/implement/SKILL.md:15 |
| implement-spec | setup-matt-pocock-skills | requires (tell the user) | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:9 |
| implement-spec | exploration subagent | invokes (optional) | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:23 |
| implement-spec | implementer subagent | invokes | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:27 |
| implementer subagent | tdd | invokes | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:29 |
| implement-spec | merger subagent | invokes | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:32 |
| implement-spec | code-review | invokes | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:36 |
| implement-spec | integration branch / draft PR | produces | reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:25,38 |
| code-review | docs/agents/* config | requires | reference_harnesses/mattpocock_skills/skills/engineering/code-review/SKILL.md:13,29 |
| code-review | Standards / Spec reviewer subagents | invokes | reference_harnesses/mattpocock_skills/skills/engineering/code-review/SKILL.md:58-72 |
| code-review | CODING_STANDARDS.md / CONTRIBUTING.md | reads | reference_harnesses/mattpocock_skills/skills/engineering/code-review/SKILL.md:36 |
| code-review | Fowler smell baseline | enforces | reference_harnesses/mattpocock_skills/skills/engineering/code-review/SKILL.md:38-56 |
| tdd | codebase-design | invokes | reference_harnesses/mattpocock_skills/skills/engineering/tdd/SKILL.md:26 |
| tdd | code-review | hands-off-to (refactoring belongs to review) | reference_harnesses/mattpocock_skills/skills/engineering/tdd/SKILL.md:38 |
| tdd | pre-agreed seams | enforces | reference_harnesses/mattpocock_skills/skills/engineering/tdd/SKILL.md:22 |
| retro | writing-for-agents | invokes | reference_harnesses/mattpocock_skills/skills/engineering/retro/SKILL.md:11 |
| retro | session logs | reads | reference_harnesses/mattpocock_skills/skills/engineering/retro/SKILL.md:13 |
| triage | setup-matt-pocock-skills | requires (tell the user) | reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:43 |
| triage | grilling | invokes | reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:76 |
| triage | domain-modeling | invokes | reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:76 |
| triage | AGENT-BRIEF / OUT-OF-SCOPE | reads | reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:21-22,70 |
| triage | agent brief / `.out-of-scope/` file | produces | reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:79,85 |
| wayfinder | setup-matt-pocock-skills | requires (tell the user; default is local) | reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:25 |
| wayfinder | grilling | invokes | reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:79,111,124 |
| wayfinder | domain-modeling | invokes | reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:79,111,124 |
| wayfinder | research | invokes (subagent per research ticket) | reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:77,115 |
| wayfinder | prototype | invokes | reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:78 |
| wayfinder | map issue + child decision tickets | produces | reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:113-114 |
| improve-codebase-architecture | codebase-design | invokes | reference_harnesses/mattpocock_skills/skills/engineering/improve-codebase-architecture/SKILL.md:13,71 |
| improve-codebase-architecture | grilling | invokes | reference_harnesses/mattpocock_skills/skills/engineering/improve-codebase-architecture/SKILL.md:64 |
| improve-codebase-architecture | domain-modeling | invokes | reference_harnesses/mattpocock_skills/skills/engineering/improve-codebase-architecture/SKILL.md:66 |
| improve-codebase-architecture | HTML report in temp dir | produces | reference_harnesses/mattpocock_skills/skills/engineering/improve-codebase-architecture/SKILL.md:39,58 |
| setup-matt-pocock-skills | docs/agents/* config + CLAUDE.md/AGENTS.md block | produces | reference_harnesses/mattpocock_skills/skills/engineering/setup-matt-pocock-skills/SKILL.md:49,74-112 |
| diagnosing-bugs | hitl-loop.template.sh | reads | reference_harnesses/mattpocock_skills/skills/engineering/diagnosing-bugs/SKILL.md:35,64 |
| diagnosing-bugs | red-capable loop before hypothesis | enforces | reference_harnesses/mattpocock_skills/skills/engineering/diagnosing-bugs/SKILL.md:57-66 |
| prototype | `prototype/<name>` branch + issue pointer | produces | reference_harnesses/mattpocock_skills/skills/engineering/prototype/SKILL.md:26 |
| wizard | wizard template.sh | reads | reference_harnesses/mattpocock_skills/skills/engineering/wizard/SKILL.md:10,35 |
| research | cited markdown file | produces | reference_harnesses/mattpocock_skills/skills/engineering/research/SKILL.md:11-12 |
| handoff | handoff doc in OS temp dir | produces | reference_harnesses/mattpocock_skills/skills/productivity/handoff/SKILL.md:8 |
| pr | GLOSSARY.md | reads | reference_harnesses/mattpocock_skills/skills/engineering/pr/SKILL.md:37 |
| wait-what | GLOSSARY.md / GLOSSARY-MAP.md | reads | reference_harnesses/mattpocock_skills/skills/productivity/wait-what/SKILL.md:7 |
| setup-ts-deep-modules [IP] | codebase-design | invokes | reference_harnesses/mattpocock_skills/skills/in-progress/setup-ts-deep-modules/SKILL.md:11 |
| loop-me [IP] | grilling | invokes (prose `/grilling`) | reference_harnesses/mattpocock_skills/skills/in-progress/loop-me/SKILL.md:8 |
| git-guardrails-claude-code | block-dangerous-git.sh | produces | reference_harnesses/mattpocock_skills/skills/misc/git-guardrails-claude-code/SKILL.md:26-35 |
| (any skill) | (any user-invoked skill) | **forbidden** | reference_harnesses/mattpocock_skills/.agents/invocation.md:8,22 ; reference_harnesses/mattpocock_skills/README.md:186 |

## 4. Main lifecycle

Canonical path, as stated in reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/SKILL.md:13-32. The docs give the same chain at reference_harnesses/mattpocock_skills/.agents/writing-docs.md:66 and reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:83.

0. **setup-matt-pocock-skills**, once per repo. The human types it. **Gate:** the human confirms or edits the drafted config (setup SKILL.md:63-70).
1. **ask-matt** (optional) to pick a route. Then **grill-with-docs**, which runs grilling and domain-modeling. **Gate:** every decision is the human's, and the session ends only when the frontier is empty and the user confirms shared understanding (grilling:26-28).
2. **Decision (human):** can every question be settled in conversation? If not: handoff, then prototype in a fresh session, then handoff back (ask-matt:18-21).
3. **Decision (human):** is this a multi-session build? (ask-matt:22-26)
   - No: go straight to **implement** in the same context.
   - Yes: **to-spec**. **Gate:** the human confirms the seams (to-spec:17). Then **to-tickets**. **Gate:** iterate until the human approves the breakdown and the edges (to-tickets:56). Keep steps 1 to 3 in one context window (ask-matt:36).
   - Then **decision (human):** either **implement** per ticket with `/clear` in between, or **implement-spec** for the whole graph (ask-matt:24-25).
4. Building: **tdd** (gate: seams confirmed with the user, tdd:22), then **code-review**. implement commits to the current branch. implement-spec lands on the integration branch and resolves tickets, or marks a draft PR ready (implement-spec:36-38).
5. **pr** shapes the PR body whenever one is written (ask-matt:30). Merging is not covered by any skill.
6. **retro**, in the same session before clearing. **Gate:** the human picks which suggested environment changes to apply (retro:25).

On-ramps that merge into this path: **triage** produces `ready-for-agent` issues for implement (ask-matt:44). **diagnosing-bugs** goes on to retro and then possibly improve-codebase-architecture (ask-matt:48). **wayfinder**, once its map clears, merges at to-spec (ask-matt:52).

## 5. Problem map

| problem id | node(s) used, in order | how it solves it (one line, mechanism) | gap? |
|---|---|---|---|
| P01 understand code | grilling (fact subagent), then implement-spec exploration subagent / improve-codebase-architecture explore | Facts are the agent's job, dispatched to a subagent (grilling:26). Exploration notes are shared as context pointers (implement-spec:23). | partial: no standalone "explain the code" skill |
| P02 understand why | domain-modeling (ADRs), then domain.md consumer rule, then prototype branch / diagnosing-bugs commit note | ADRs record hard-to-reverse trade-offs (ADR-FORMAT:29-37). Prototypes are kept as primary sources (prototype:26). The correct hypothesis goes in the commit (diagnosing-bugs:138). | partial: no git-history/blame skill |
| P03 clarify requirements | grill-with-docs or grill-me, then grilling. Also to-questionnaire, wait-what | Rounds over the design-tree frontier, with a recommended answer for each question (grilling:8-28). Questionnaires collect decisions held by other people (to-questionnaire:7-16). | no |
| P04 design / architecture | codebase-design (DEEPENING, DESIGN-IT-TWICE), improve-codebase-architecture | Deep-module vocabulary. Three or more parallel radically different interface designs (DESIGN-IT-TWICE:21-28). A deepening survey as an HTML report. | no |
| P05 plan / decompose | to-spec, then to-tickets. wayfinder for foggy work | Spec template. Tracer-bullet slices with blocking edges and expand-contract for wide refactors (to-tickets:27-40). Decision-ticket map with fog of war (wayfinder:82-93). | no |
| P06 implement a feature | implement or implement-spec, then tdd, then code-review | One red-green slice at a time. Parallel worktree implementers across the ready frontier (implement-spec:27-34). | no |
| P07 fix a bug | diagnosing-bugs, then tdd-style regression test, then retro | No hypothesis before a tight, red-capable loop. Minimise, then 3 to 5 falsifiable hypotheses, then one-variable probes (diagnosing-bugs:57-98). | no |
| P08 performance | diagnosing-bugs (perf branch) | Baseline measurement, then bisect. Measure first (diagnosing-bugs:112). | partial: one paragraph only |
| P09 write tests | tdd (tests.md, mocking.md) | Only at pre-agreed seams. Rules against implementation-coupled, tautological and horizontal tests. Mock only at system boundaries (tdd:22-33; mocking.md:3-14). | no |
| P10 review code or docs | code-review | Separate Standards and Spec subagents, never merged or reranked (code-review:58-87). | partial: no document review. Known recursive fan-out bug (reference_harnesses/mattpocock_skills/docs/engineering/code-review.md:56) |
| P11 verify / prove done | implement (typecheck + full suite), diagnosing-bugs Phase 6, pr Evidence, setup-ts-deep-modules [IP] "prove the rules bite" | Checklists and before/after evidence (implement:11; diagnosing-bugs:132-138; pr:158-164). | yes: no independent verifier or done-gate. A review/fix loop with no stop rule ran about 4h (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:48) |
| P12 land / ship | implement (commit), implement-spec (integration branch, draft PR then ready), pr | The PR body template includes a one-way/two-way door call (pr:166-170). | yes: no merge, release or conflict skill (the merge-conflict skill was archived, reference_harnesses/mattpocock_skills/docs/engineering/resolving-merge-conflicts.md:1) |
| P13 parallel / fan-out | implement-spec, code-review, DESIGN-IT-TWICE, research, wayfinder (parallel research subagents, concurrent sessions) | Frontier-driven background implementers. Claim-by-assignee lets several sessions work one map (wayfinder:67,127). | partial: collisions are postponed to merge time (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:54-56) |
| P14 long / unattended runs | implement-spec (one session). `ready-for-agent` for external AFK runners | The orchestrator runs a task graph with background subagents. The docs defer true AFK to Sandcastle, a script or CI (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:62-64). | yes: no loop runner, ledger or stop condition in the set |
| P15 session continuity | PHASE-BOUNDARIES, handoff, claude-handoff [IP], wayfinder map, triage resume | An ordered five-option tree at phase boundaries. Portable handoff doc. The tracker map is the cross-session index (PHASE-BOUNDARIES:19-40; wayfinder:23). | no |
| P16 learn from mistakes | retro, then setup-pre-commit / git-guardrails (misc) | Mechanical mistakes become deterministic checks. Judgement calls become CODING_STANDARDS (retro:19). | partial: suggestions only, a human applies them |
| P17 writing / docs / style | writing-for-agents, pr, wait-what, writing-fragments/shape/beats [IP], to-questionnaire | Context pointers, the information hierarchy, leading words, no-op pruning (writing-for-agents:10-81). | no |
| P18 domain language / ADRs | grill-with-docs, then domain-modeling | Challenges terms against GLOSSARY.md, writes inline. An ADR only when all three tests hold (domain-modeling:44-74). | no |
| P19 security | — (redaction lines in diagnosing-bugs:12-16 and handoff:14; optional git-guardrails hook) | — | yes |
| P20 track work / issues | setup-matt-pocock-skills, then triage / to-tickets / wayfinder | Tracker abstraction through docs/agents/issue-tracker.md, five triage roles, native blocking links (issue-tracker-github.md:5-45). | partial: no `blocked` or "awaiting verification" state (reference_harnesses/mattpocock_skills/docs/engineering/triage.md:77) |
| P21 author / maintain skills | writing-for-agents (SKILL-MECHANICS), retro. Repo-internal: reference_harnesses/mattpocock_skills/CLAUDE.md, reference_harnesses/mattpocock_skills/.agents/* | Invocation choice, router skills, and a docs-page template with a re-sync trigger (SKILL-MECHANICS:5-22; reference_harnesses/mattpocock_skills/CLAUDE.md:17-21). | partial: no skill test/eval harness |
| P22 prototype | prototype (LOGIC.md / UI.md) | Throwaway code that answers one question, kept on a `prototype/<name>` branch (prototype:8-26). | no |

## 6. Autonomy

**Runs without a human, step by step:**
1. **Inside a model-invoked skill.** The agent can fire tdd, code-review, diagnosing-bugs, prototype, research, domain-modeling, codebase-design, pr and wizard on its own (reference_harnesses/mattpocock_skills/.agents/invocation.md:6). diagnosing-bugs explicitly continues on its own hypothesis ranking "if the user is AFK" (reference_harnesses/mattpocock_skills/skills/engineering/diagnosing-bugs/SKILL.md:98). Its feedback loop must be "agent-runnable … unattended" (:64).
2. **implement-spec, once a human has typed it.** It reads the task graph, optionally runs an exploration subagent, then creates the integration branch. It runs background implementer subagents, each in a worktree driving tdd, across the ready frontier. A merger subagent lands each branch. New frontier tickets are re-dispatched. After that comes one code-review and one fix subagent. The run then resolves tickets or marks the draft PR ready and cleans up worktrees (reference_harnesses/mattpocock_skills/skills/engineering/implement-spec/SKILL.md:21-40). No human checkpoint is written into these steps, but each implementer calls `tdd`, which requires seams confirmed with the user before any test (reference_harnesses/mattpocock_skills/skills/engineering/tdd/SKILL.md:22). implement-spec has no interactive seam step, so the seams must be named in the spec or tickets beforehand (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:52).
3. **AFK vs HITL typing.** wayfinder types every ticket as HITL or AFK. Research is AFK and resolved by subagents fired in parallel at charting time. Grilling and prototype are HITL. Task tickets can be either, and the agent never stands in for the human's side of a HITL ticket (reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:75-80,115).
4. **Triage states as a hand-off to AFK runners.** `ready-for-agent` means "fully specified, ready for an AFK agent". `ready-for-human` means it needs a human, and must say why it can't be delegated (reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md:35-36,80). to-spec and to-tickets apply `ready-for-agent` automatically (to-spec:19; to-tickets:63). The agent brief is "the contract" for an AFK agent (reference_harnesses/mattpocock_skills/skills/engineering/triage/AGENT-BRIEF.md:3).
5. **Subagent at a phase boundary**, when a task "can be done AFK" (reference_harnesses/mattpocock_skills/skills/engineering/ask-matt/PHASE-BOUNDARIES.md:36).

**Where it must stop for a human:**
- Every user-invoked step. No skill can invoke a user-invoked skill (reference_harnesses/mattpocock_skills/.agents/invocation.md:8,22). The main flow is therefore a chain of human keystrokes: grill-with-docs, to-spec, to-tickets, implement or implement-spec, retro.
- Explicit gates:
  - grilling decisions and the confirmation of shared understanding (grilling:26-28)
  - to-spec seam check (:17)
  - to-tickets approval loop (:56)
  - tdd seam confirmation (:22)
  - code-review asks for the fixed point when none is given (:19) and for the spec location when none is found (:32)
  - triage "wait for direction" (:72)
  - improve-codebase-architecture "which would you like to explore?" (:60)
  - setup confirm and edit (:63-70)
  - retro presents candidates for the human to choose (:25)
  - diagnosing-bugs stops when no loop can be built (:55)
- Work only a human can do is routed to wizard (reference_harnesses/mattpocock_skills/skills/engineering/wizard/SKILL.md:8) or hitl-loop.template.sh.
- wayfinder resolves at most one ticket per session, research tickets excepted (reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md:105).

**Failure and recovery mechanisms:**
- Isolation: per-implementer worktrees. Each implementer resets onto the integration branch if mis-based and merges the integration tip before reporting (implement-spec:28,30).
- Claims: wayfinder claims a ticket by assignee before any work, so concurrent sessions skip it (wayfinder:67, 123).
- Dedup memory: triage's `.out-of-scope/` knowledge base (OUT-OF-SCOPE.md:3-6).
- Resumability: triage notes on the issue (triage:110-112). Phase-boundary handoff and compact.
- Optional guardrails: the PreToolUse git hook (exit 2) and the pre-commit hook (misc).
- There are no retries, budgets, run ledger, verdict schema, rollback, or stop rule for the review/fix loop.

**Known autonomy failures documented upstream:**
- code-review subagents can recurse. One report reached 50+ agents (reference_harnesses/mattpocock_skills/docs/engineering/code-review.md:56).
- implement-spec's review/fix loop has no stop rule. One report took about 4h (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:48).
- The GitHub blocked-by count is stale mid-run, so the orchestrator should track merges itself (:58-60).
- Implementers see neither each other's work nor seam agreement (:52-56).
- AFK pollers grab the parent spec, which also carries `ready-for-agent` (reference_harnesses/mattpocock_skills/docs/engineering/to-spec.md:42).
- No `blocked` or "awaiting verification" state, so AFK runners can re-queue finished tickets (reference_harnesses/mattpocock_skills/docs/engineering/triage.md:77).

J: The harness positions itself as human-orchestrated. Its stated stance is that truly AFK work belongs in an external deterministic loop such as Sandcastle, a shell script or a CI job, because "no part of the orchestration can wander off" (reference_harnesses/mattpocock_skills/docs/engineering/implement-spec.md:64). Its autonomy ceiling is therefore one implement-spec session per human keystroke. The issue tracker's labels are the only interface to outside AFK runners.
