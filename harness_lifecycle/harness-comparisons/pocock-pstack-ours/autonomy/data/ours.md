# Harness map — ours (coding-ritual, branch dws-workflow)

Evidence is `path:line`, relative to the repo root. `J:` marks judgement. Read-only
survey of `AGENTS.md`, `.repo-context/*`, `.claude/{skills,agents,hooks,scripts,settings.json}`,
`.beads/beads.md`, `.codex/README.md`, `docs/usage/*`, `docs/adr/*`, `workflows/`,
`config/foreman.example.toml` and `workflow_interpreter/` package docstrings.

Two layers sit in one repo and need to be read separately:

- **Prose harness**: skills, agents and hooks that steer an interactive Claude Code or Codex session.
- **Engine** (`workflow_interpreter/`): deterministic Python made of the foreman, contractor, inspector, crew profiles, ledger and tracker. The prose harness calls it from the execution skill's phase loop (`.claude/skills/execution/SKILL.md:65-66`).

## 1. Infrastructure assumptions

| Assumption | Evidence (path:line) | What breaks without it |
|---|---|---|
| **No CI.** The local host gate is the only quality gate. | `AGENTS.md:74-75`; `.repo-context/verification.md:8-9` | Nothing re-checks work after it lands. Gate discipline depends entirely on agents running the five-stage gate (`.repo-context/verification.md:57-65`). |
| **No PR flow.** Landing is a local compare-and-swap (CAS) on a target branch ref. The contractor needs a clean coordinator attached to the target branch, then verifies, lands and closes. | `docs/usage/contractor.md:9`; `docs/usage/contractor.md:29-37` | Nothing in the harness models review-on-PR or merge queues. J: the only "merge" human touchpoint is the signed ship gate. |
| **The engine never pushes.** Its Git operations are local and confined: `gitio` has no `push`, `remote` or `fetch`. Push is user-authorized only. | `workflow_interpreter/inspector/__init__.py:15-16`; `AGENTS.md:64-65`; `.beads/beads.md:20-22` | Publication stays a human act, by design. |
| **Local branches and worktrees.** Workers use worktrees with a verified base. Crews run in owned worktrees or an in-repo band. Recovery refs are `refs/wf/<root>/recovery/<activation>`. | `.repo-context/learnings.md:20`; `docs/usage/node-contract-recovery.md:29-40`; `.claude/skills/agent-matrix/SKILL.md:34-37` (Agent tool `isolation`) | Without the base check, workers edit the wrong base (an archived incident). Without recovery refs, an interrupted writer loses its content. |
| **Beads (`bd`) is the issue tracker.** Dolt DB is the source of truth. `.beads/issues.jsonl` is a committed mirror. Actor attribution on every write. | `AGENTS.md:109-111`; `.beads/beads.md:9-28` | Execution can't claim, close or gate phases (`.claude/skills/execution/SKILL.md:38-39,57-61`). Mirrors can't render. |
| **Tracker is a contractor-only port.** The SQLite ledger is the only engine record store. bd is mirrored through a durable outbox. | `docs/adr/0006-ledger-only-record-store.md:26-46`; `workflow_interpreter/tracker/__init__.py:1-8` | The engine still runs on `file`/`null` trackers (`config/foreman.example.toml:60-66`). J: so bd is optional to the engine but required by the skills. |
| **SQLite run ledger** at `<repo>/.wf/ledger.db`, gitignored. A task closes only after its export is a git blob. | `workflow_interpreter/ledger/paths.py:36-38`; `docs/adr/0005-run-ledger.md:15-18`; `docs/adr/0006-ledger-only-record-store.md:47-51` | No durable engine facts, no closure latch, no `ledger verify/reconcile/restore` (`workflow_interpreter/ledger/__main__.py:117-182`). |
| **Vendor CLIs as crews.** `claude`, `codex` (exec plus an experimental app-server) and `opencode` sit behind one contract. Role bindings map models to crews. | `workflow_interpreter/profiles/__init__.py:1-22`; `.repo-context/CONTEXT.md:60-61`; `config/foreman.example.toml:107-109`; `docs/usage/engine-bundle.md:216-229` | No work gets done inside an activation. opencode is refused for lack of an enforcement mechanism (`workflow_interpreter/profiles/__init__.py:17-20`). |
| **Codex is called directly from Claude** with `codex exec` / `codex exec resume`. The old codex-adapter is retired. | `.repo-context/running-codex.md:5-19`; `.claude/skills/model-council/SKILL.md:16-17` | No cross-vendor critic or council member is available. |
| **Sandbox is bwrap.** The crew's only writable mounts are its grants. Codex runs with network denied. Claude's network is `not_enforced`. | `workflow_interpreter/inspector/sandbox.py:1-8`; `docs/usage/engine-bundle.md:98-104`; `workflows/README.md:9-11` | Named writer/reviewer profiles refuse to launch (`docs/usage/engine-bundle.md:93-95`). The process lane can't verify mount bounds (`.repo-context/verification.md:63,71-75`). |
| **Offline toolchain seeding.** Each activation gets a private uv cache and managed Python. | `docs/usage/engine-bundle.md:3-51` | Preparation is refused before the vendor launches (`docs/usage/engine-bundle.md:62-66`). |
| **Signed human gates.** Approval uses an ssh-keygen ed25519 signature. The allow-list must sit outside the bd workspace and the wrapper home. | `config/foreman.example.toml:72-86`; `scripts/approve-gate.sh:2-16` | Root creation refuses unless `--allow-unsigned-gates` is passed, and that root then "will never be approved" (`workflow_interpreter/foreman/__main__.py:91-96`). |
| **Runtime features (Claude Code).** Hooks: PreToolUse on Bash and on Write/Edit, plus SessionStart. Agent tool fields: `subagent_type`, `model` (alias enum), `run_in_background`, `isolation`. Definition-layer frontmatter carries effort, tools and permission. | `.claude/settings.json:1-46`; `.claude/skills/agent-matrix/SKILL.md:34-48` | Effort and tool restrictions can't be promised per spawn (`.claude/skills/agent-matrix/SKILL.md:46-48`). |
| **Codex twin.** Skills are symlinked, `openai.yaml` carries the implicit-invocation policy, and hooks are mirrored. | `.codex/README.md:6-14`; `.codex/hooks.json` (SessionStart bd-prime; PreToolUse Bash and apply_patch/Edit/Write) | The Codex session has no guards or routing. J: `.codex/README.md:16` points to `.repo-context/delegation.md`, which does not exist. |
| **Models.** The runtime roster owns them. Agent definitions pin `claude-opus-4-8` (implementer at medium; reviewers at `extra`) and sonnet for docs-researcher. | `AGENTS.md:72-73`; `.claude/agents/implementer.md:5-6`; `.claude/agents/code-reviewer.md:5-6`; `.claude/agents/docs-researcher.md:5`; `.claude/skills/review/SKILL.md:12` ("the user chooses its model") | Values must validate against the agent-matrix registry (`.claude/skills/agent-matrix/SKILL.md:8-27`). |
| **Human touchpoints.** Commit/push/publish authority; spec and plan approval; the signed `ship` and `triage` gates; the halt gate when a death can't be confirmed; triage decisions; merge-conflict abort. | `AGENTS.md:11-12,64-65`; `.claude/skills/brainstorming/SKILL.md:44-50`; `.claude/skills/planning/SKILL.md:36-40`; `workflows/feature-delivery.toml:180-191`; `docs/usage/node-contract-recovery.md:111-113`; `.claude/skills/triage/SKILL.md:36-39`; `.claude/skills/resolving-merge-conflicts/SKILL.md:11` | See §6. |
| **Persistence.** <br>• Beads (work) <br>• `MEMORY.md` (knowledge; `bd remember` is banned) <br>• `.repo-context/learnings.md` <br>• `scratchpad/execution/<slug>/progress.md` <br>• ledger and exports <br>• `debrief` written into `docs/workstreams/**` <br>• heartbeat, refusal journal and wake events | `.beads/beads.md:13-16`; `AGENTS.md:27-29`; `.claude/skills/execution/references/task-engine.md:8-18`; `docs/adr/0005-run-ledger.md:19-23`; `docs/usage/engine-bundle.md:136-185` | Sessions can't resume (`.beads/beads.md:98-100`). |
| **Autonomy level** (J). <br>• Prose layer: human-in-loop by default; `/run-phases` is the explicit unattended opt-in. <br>• Engine: unattended between gates, bounded by activation and round caps. Every landing needs a signed human ship approval. | `.claude/skills/run-phases/SKILL.md:13-15`; `workflows/feature-delivery.toml:7-17,180-184`; `docs/usage/contractor.md:9` | — |

## 2. Nodes

### Prose harness

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| AGENTS.md | doc | always | Shared policy: authority, context, effort/delegation, verification, Git safety, Beads (`AGENTS.md:1-111`) |
| repo-context | doc | always (repo-map, docs-index), else on demand | Repo map, reading index, verification, invariants, learnings, glossary, coding style, running-codex (`AGENTS.md:83-98`) |
| verification.md | doc | model | Claim→evidence table, structural checks, five-stage interpreter host gate (`.repo-context/verification.md:11-83`) |
| beads.md | doc | model | Beads policy: intake states, ready-for-agent gate, epics/specs, mirrors, session close (`.beads/beads.md:1-101`) |
| skill-router | skill | model | Routes to the narrowest skill; holds the generated catalog (`.claude/skills/skill-router/SKILL.md:8-69`) |
| brainstorming | skill | model | Resolves material scope/behavior decisions; outputs decisions or a draft/approved spec (`.claude/skills/brainstorming/SKILL.md:8-53`) |
| grilling | skill | model (explicit request) | Decision interview of the user (`.claude/skills/grilling/SKILL.md:8-32`) |
| wayfinder | skill | user-only | Multi-session decision graph as a Beads map + tickets (`.claude/skills/wayfinder/SKILL.md:9-50`) |
| planning | skill | model | Decompose a spec into workstream/phases/stages; elaborate durable plans (`.claude/skills/planning/SKILL.md:8-69`) |
| execution | skill | model | Task / phase / workstream scopes; task loop, phase loop via contractor, child workflows (`.claude/skills/execution/SKILL.md:8-100`) |
| execution/task-engine | doc (ref) | model | Delegation, scoped snapshots, review paths, ≤5-round fix loop (`.claude/skills/execution/references/task-engine.md:1-116`) |
| execution/workstream-mode | doc (ref) | model (after `/run-phases`) | Unattended multi-phase walk, preflight, recovery (`.claude/skills/execution/references/workstream-mode.md:1-39`) |
| phase-execution | skill (thin entry) | user-only | `/phase-execution <id> --roadmap` → execution phase scope (`.claude/skills/phase-execution/SKILL.md:9-17`) |
| run-phases | skill (thin entry) | user-only | `/run-phases <roadmap>` → execution workstream scope; is the unattended opt-in (`.claude/skills/run-phases/SKILL.md:9-19`) |
| review | skill | model | Critic contract, severity, code/document/feedback modes (`.claude/skills/review/SKILL.md:6-43`) |
| review/code, review/review-contract, review/feedback | doc (ref) | model | Code-review modes, dispatched output formats, incoming-feedback disposition (`.claude/skills/review/SKILL.md:29-34`) |
| test-driven-development | skill | model | Test-first / characterization / test-quality modes (`.claude/skills/test-driven-development/SKILL.md:8-55`) |
| systematic-debugging | skill | model | Reproduce → hypothesize → probe → fix confirmed cause → regression check (`.claude/skills/systematic-debugging/SKILL.md:8-56`) |
| performance-optimization | skill | model | Baseline → locate → change one factor → compare (`.claude/skills/performance-optimization/SKILL.md:8-37`) |
| security | skill | model | Threat scoping, authority, evidence for trust-boundary changes (`.claude/skills/security/SKILL.md:6-45`) |
| codebase-design | skill | model | Module depth/seam/interface lens (`.claude/skills/codebase-design/SKILL.md:6-41`) |
| improve-codebase-architecture | skill | user-only | Evidence-backed architecture improvement survey (`.claude/skills/improve-codebase-architecture/SKILL.md:7-30`) |
| codebase-research | skill | user-only | L1/L2/deep-dive reports on external codebases (`.claude/skills/codebase-research/SKILL.md:7-60`) |
| research | skill | model | Multi-source evidence for a decision (`.claude/skills/research/SKILL.md:6-40`) |
| design-evolve | skill | model | Integrate decisions into a self-contained next design version (`.claude/skills/design-evolve/SKILL.md:6-36`) |
| domain-modeling | skill | model | Glossary (`.repo-context/CONTEXT.md`) + ADRs (`.claude/skills/domain-modeling/SKILL.md:8-52`) |
| prototype | skill | model | Throwaway runnable experiment for one design question (`.claude/skills/prototype/SKILL.md:6-28`) |
| resolving-merge-conflicts | skill | model | Resolve an in-progress conflicted merge/rebase (`.claude/skills/resolving-merge-conflicts/SKILL.md:6-15`) |
| triage | skill | user-only | Move Beads issues into intake states (`.claude/skills/triage/SKILL.md:7-60`) |
| beads | skill | model | Beads conventions and recovery (`.claude/skills/beads/SKILL.md:7-39`) |
| check-invariants | skill | user-only | Run `.repo-context/invariants.md` checks (`.claude/skills/check-invariants/SKILL.md:7-16`) |
| model-council | skill | model (explicit request) | Named models answer independently, then a judge (`.claude/skills/model-council/SKILL.md:6-33`) |
| perspective-council | skill | model (explicit request) | Five-lens council with peer review and chair (`.claude/skills/perspective-council/SKILL.md:6-40`) |
| agent-matrix | skill | model | Validate subagent model/effort/capability before spawn (`.claude/skills/agent-matrix/SKILL.md:6-60`) |
| authoring-for-agents | skill | model | Write/change agent instructions; choose surface; verify activation (`.claude/skills/authoring-for-agents/SKILL.md:6-50`) |
| harness-status / harness-scan | skill | user-only | Upstream drift and gap scan of reference harnesses (`.claude/skills/harness-status/SKILL.md:7-25`; `.claude/skills/harness-scan/SKILL.md:7-22`) |
| harness-evaluate / harness-skill-compare | skill | model | Adopt/reject/defer curation; skill comparisons (`.claude/skills/harness-evaluate/SKILL.md:6-40`; `.claude/skills/harness-skill-compare/SKILL.md:6-29`) |
| harness-publish | skill | user-only | Publish into mvp-plugin with audits and version bump (`.claude/skills/harness-publish/SKILL.md:7-60`) |
| migrate-claude-to-codex | skill | user-only | Adapt Claude assets to Codex (`.claude/skills/migrate-claude-to-codex/SKILL.md:7-33`) |
| html-artifact | skill | model | Standalone offline HTML documents (`.claude/skills/html-artifact/SKILL.md:6-48`) |
| show-me | skill | user-only | Inline visual (trees, diff-shaped, mermaid) (`.claude/skills/show-me/SKILL.md:7-35`) |
| teach | skill | user-only | Concept / session walkthrough / course (`.claude/skills/teach/SKILL.md:8-38`) |
| i-have-adhd | skill | user-only | ADHD-shaped output style (`.claude/skills/i-have-adhd/SKILL.md:7-60`) |
| document-review | skill (alias → review document mode) | user-only | Legacy entry (`.claude/skills/document-review/SKILL.md:7-10`) |
| receiving-code-review | skill (alias → review feedback mode) | user-only | Legacy entry (`.claude/skills/receiving-code-review/SKILL.md:7-11`) |
| idea-refine | skill (alias → brainstorming exploration) | user-only | Legacy entry (`.claude/skills/idea-refine/SKILL.md:7-13`) |
| grill-me | skill (alias → grilling) | user-only | Legacy entry (`.claude/skills/grill-me/SKILL.md:7-12`) |
| grill-with-docs | skill (alias → grilling + domain-modeling) | user-only | Documented interview (`.claude/skills/grill-with-docs/SKILL.md:7-12`) |
| teach-session | skill (alias → teach session mode) | user-only | Legacy entry (`.claude/skills/teach-session/SKILL.md:7-12`) |
| verification-before-completion | skill (stub → AGENTS.md Verification) | user-only | Retired workflow pointer (`.claude/skills/verification-before-completion/SKILL.md:7-12`) |
| cost-estimate | skill (stub, method retired) | user-only | Retired method; manual guidance only (`.claude/skills/cost-estimate/SKILL.md:7-17`) |
| in-progress/use-codex | skill (parked) | not loaded | Parked Codex workflow (`.claude/skills/in-progress/README.md:1-6`) |
| implementer | agent | model (dispatch) | Bounded file-scoped implementer with DONE/…/BLOCKED status (`.claude/agents/implementer.md:1-54`) |
| spec-reviewer | agent | model (dispatch) | Spec-compliance reviewer; reads the review skill first (`.claude/agents/spec-reviewer.md:1-18`) |
| code-reviewer | agent | model (dispatch) | Quality / re-review reviewer; reads the review skill first (`.claude/agents/code-reviewer.md:1-20`) |
| docs-researcher | agent | model (dispatch) | Context7-only API docs lookup (`.claude/agents/docs-researcher.md:1-51`) |

### Hooks

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| block-dangerous-commands | hook | always (PreToolUse Bash) | Exit 2 on force-push, reset --hard, clean, branch -D, checkout/restore ., --no-verify, `bd init --force/--reinit`, `rm -r` outside /tmp, and shell writes to mirrors (`.claude/hooks/block-dangerous-commands.sh:18-87`) |
| block-generated-edits | hook | always (PreToolUse Write\|Edit) | Exit 2 on edits to `docs/workstreams/**/tracking/*.md` and the board files (`.claude/hooks/block-generated-edits.sh:22-26`) |
| bd-prime | hook | always (SessionStart) | Injects `bd prime --hook-json`; no-op if bd is missing (`.claude/hooks/bd-prime.sh:25-26`) |
| harness-staleness-nudge | hook | always (SessionStart) | Nudges `/harness-status` when catalogs are older than 30 days (`.claude/hooks/harness-staleness-nudge.sh:11-13`) |

### Scripts

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| skill-catalog.py | script | code / manual gate | Generates the router catalog and `openai.yaml` policy; lints slash/path pointers (`.claude/scripts/skill-catalog.py:2-20`) |
| review-package.sh / task-brief.sh | script | model | Scoped review snapshots without commits; extract a plan task brief (`.claude/skills/execution/references/task-engine.md:20-40`) |
| bd-render-tracking.sh | script | model | The only sanctioned writer of mirrors (`BD_RENDER=1`) (`.beads/beads.md:86-88`) |
| find-polluter.sh | script | model | Order-dependent test polluter search (`.claude/skills/systematic-debugging/SKILL.md:33-34`) |
| harness_lifecycle scan.py / gap.py | script | model | Drift, gap and ledger for reference curation (`.claude/skills/harness-scan/SKILL.md:11-12`; `.claude/skills/harness-evaluate/SKILL.md:21`) |
| approve-gate.sh | script | user | Signs one gate approval into its inbox (`scripts/approve-gate.sh:2-16`) |
| make-foreman-config.sh | script | user | Renders the machine-specific foreman config (`config/foreman.example.toml:3-11`) |
| verify-feature.sh / verify-debrief.sh | script | code | Pinned host verifiers in graphs and contractor checks (`workflows/feature-delivery.toml:55,110,166-168`; `config/foreman.example.toml:40-46`) |

### Engine

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| foreman | engine | code (CLI) | One decision per tick. CLI: `create`, `tick`, `status`, `run`, `monitor`, `contract`, `inspect`, `steer`, `phase abandon`, `integration`, `children` (`.repo-context/CONTEXT.md:54`; `workflow_interpreter/foreman/__main__.py:398-473`) |
| contractor | engine | code (`foreman contract`) | Claims a stage, runs the pinned graph, consumes the signed ship approval, runs checks, CAS-lands, closes with a receipt (`docs/usage/contractor.md:3-9`; `.repo-context/CONTEXT.md:51-52`) |
| inspector | engine | code | Contains and watches one activation; exit grading; recovery classification (`workflow_interpreter/inspector/__init__.py:1-21`) |
| crew (profiles) | engine | code | Vendor CLI adapters claude / codex / codex-appserver / opencode (`workflow_interpreter/profiles/__init__.py:1-22`) |
| ledger | engine | code (`python -m workflow_interpreter.ledger`) | SQLite record store; export / pin / restore / reconcile / verify / archive (`workflow_interpreter/ledger/__init__.py:1-6`; `workflow_interpreter/ledger/__main__.py:117-182`) |
| tracker | engine | code (contractor only) | Four-operation tracker port (bd / file / null) with outbox (`workflow_interpreter/tracker/__init__.py:1-8`) |
| bdio (gates) | engine | code | Typed store API and §9 human-gate signature check (`workflow_interpreter/bdio/__init__.py:1-15`) |
| monitor | engine | code (separate process) | Heartbeat staleness and wake events to bd; optional `hook_argv` (`docs/usage/engine-bundle.md:159-206`) |
| feature-delivery graph | engine (graph) | code | implement → debrief → review → **ship (human gate)** → shipped. A bounded region of 3 entries leads to triage (`workflows/feature-delivery.toml:1-17,180-191`) |
| other graphs | engine (graph) | code | `basic` (no gate), `design-spec` (docs, ship gate), `integration`, `build-loop` (TDD) (`workflows/README.md:14-29`; `config/foreman.example.toml:22-29`) |
| ADRs | doc | model | 0001 allowed_paths advisory; 0002 node instructions; 0003 payloads; 0004 deterministic routing (model router rejected); 0005 run ledger + debrief; 0006 ledger-only store (`docs/adr/README.md:6-13`) |
| usage docs | doc | model | contractor, children, verification-in-task, node-contract-recovery, engine-bundle, pointer-handoff, task-cost, mvp-plugin (`docs/usage/*`) |

## 3. Edges

| from | to | relation | evidence (path:line) |
|---|---|---|---|
| AGENTS.md | verification.md | requires | `AGENTS.md:51` |
| AGENTS.md | beads.md | requires | `AGENTS.md:109-111` |
| AGENTS.md | execution | routes-to | `AGENTS.md:95-96` |
| AGENTS.md | repo-context (repo-map, docs-index) | reads | `AGENTS.md:85-87` |
| bd-prime | beads (`bd prime`) | invokes | `.claude/hooks/bd-prime.sh:25`; `.claude/settings.json:25-34` |
| skill-router | brainstorming / planning / execution / review / grilling / wayfinder / improve-codebase-architecture / codebase-research / triage / show-me | routes-to | `.claude/skills/skill-router/SKILL.md:12-23` |
| brainstorming | grilling | routes-to | `.claude/skills/brainstorming/SKILL.md:17-18` |
| brainstorming | spec (`docs/specs/…`, draft/approved) | produces | `.claude/skills/brainstorming/SKILL.md:39-47` |
| brainstorming | review | requires (material-risk spec) | `.claude/skills/brainstorming/SKILL.md:48-49` |
| brainstorming | planning / execution | hands-off-to (when authorized) | `.claude/skills/brainstorming/SKILL.md:52-53` |
| idea-refine | brainstorming (exploration.md) | routes-to | `.claude/skills/idea-refine/SKILL.md:9-11` |
| planning | brainstorming | routes-to (unresolved behavior) | `.claude/skills/planning/SKILL.md:14` |
| planning | execution | hands-off-to | `.claude/skills/planning/SKILL.md:15,18,21-22`; `.claude/skills/planning/references/decompose.md:94-96` |
| planning | review | requires (material-risk plan) | `.claude/skills/planning/SKILL.md:55-56` |
| planning | Beads epics/stages + roadmap | produces (after approval) | `.claude/skills/planning/SKILL.md:36-40`; `.claude/skills/planning/references/decompose.md:50-77` |
| planning | bd-render-tracking.sh | invokes | `.claude/skills/planning/references/decompose.md:78-81` |
| phase-execution | execution (phase scope) | invokes | `.claude/skills/phase-execution/SKILL.md:9-10` |
| run-phases | execution (workstream scope) → workstream-mode | invokes | `.claude/skills/run-phases/SKILL.md:9-15` |
| execution | workstream-mode | reads | `.claude/skills/execution/SKILL.md:15` |
| execution | task-engine | reads | `.claude/skills/execution/SKILL.md:31` |
| execution | planning / brainstorming | routes-to (unresolved scope) | `.claude/skills/execution/SKILL.md:19` |
| execution | test-driven-development / security / systematic-debugging | routes-to | `.claude/skills/execution/SKILL.md:40-42` |
| execution | contractor (`foreman contract <epic> <stage>`) | invokes | `.claude/skills/execution/SKILL.md:65-70` |
| execution | bd-render-tracking.sh | invokes | `.claude/skills/execution/SKILL.md:73-74` |
| execution | Beads (claim / close / epic close gate) | requires | `.claude/skills/execution/SKILL.md:38-39,50,79-82` |
| execution | children (admit / drive / collect) → integration prepare → contractor | invokes | `.claude/skills/execution/SKILL.md:91-99` |
| workstream-mode | execution phase loop | invokes | `.claude/skills/execution/references/workstream-mode.md:17-19` |
| task-engine | review-package.sh / task-brief.sh | invokes | `.claude/skills/execution/references/task-engine.md:26-27,40` |
| task-engine | implementer (dispatch, status values) | invokes | `.claude/skills/execution/references/task-engine.md:45-52` |
| task-engine | review (spec / quality / combined) | invokes | `.claude/skills/execution/references/task-engine.md:65-66` |
| review | review/code, review/review-contract, review/feedback | reads | `.claude/skills/review/SKILL.md:29-34` |
| spec-reviewer / code-reviewer | review | requires | `.claude/agents/spec-reviewer.md:11-12`; `.claude/agents/code-reviewer.md:11-12` |
| implementer | test-driven-development | invokes (when test-first) | `.claude/agents/implementer.md:22` |
| implementer | verification.md | reads | `.claude/agents/implementer.md:23` |
| document-review | review (document mode) | routes-to | `.claude/skills/document-review/SKILL.md:9` |
| receiving-code-review | review (feedback mode) | routes-to | `.claude/skills/receiving-code-review/SKILL.md:9-11` |
| verification-before-completion | AGENTS.md Verification | routes-to | `.claude/skills/verification-before-completion/SKILL.md:9-10` |
| grill-me | grilling | routes-to | `.claude/skills/grill-me/SKILL.md:9` |
| grill-with-docs | grilling + domain-modeling | routes-to | `.claude/skills/grill-with-docs/SKILL.md:9-10` |
| grilling | domain-modeling | routes-to (when docs requested) | `.claude/skills/grilling/SKILL.md:31-32` |
| teach-session | teach | routes-to | `.claude/skills/teach-session/SKILL.md:9` |
| teach | html-artifact | routes-to (optional) | `.claude/skills/teach/SKILL.md:34-35` |
| show-me | html-artifact | routes-to | `.claude/skills/show-me/SKILL.md:29` |
| wayfinder | Beads map/tickets; prototype; grilling | requires / routes-to | `.claude/skills/wayfinder/SKILL.md:15,26-27` |
| triage | beads.md intake states | reads | `.claude/skills/triage/SKILL.md:9-11` |
| triage | `ready-for-agent` label | produces | `.claude/skills/triage/SKILL.md:44,57-58` |
| systematic-debugging | review (critic when hypotheses run out) | routes-to | `.claude/skills/systematic-debugging/SKILL.md:45-47` |
| systematic-debugging | performance-optimization | routes-to | `.claude/skills/systematic-debugging/SKILL.md:38-40` |
| performance-optimization | systematic-debugging | routes-to | `.claude/skills/performance-optimization/SKILL.md:9-10` |
| security | review (severity/output) | routes-to | `.claude/skills/security/SKILL.md:43-45` |
| research | codebase-research | routes-to | `.claude/skills/research/SKILL.md:11` |
| improve-codebase-architecture | codebase-design | reads | `.claude/skills/improve-codebase-architecture/SKILL.md:15-16` |
| harness-status | scan.py; harness-scan | invokes / routes-to | `.claude/skills/harness-status/SKILL.md:14,18` |
| harness-scan | scan.py, gap.py; harness-evaluate | invokes / routes-to | `.claude/skills/harness-scan/SKILL.md:11-15` |
| harness-evaluate | harness-skill-compare; gap.py ledger | routes-to / invokes | `.claude/skills/harness-evaluate/SKILL.md:15,21` |
| harness-publish | skill-catalog.py; publish-plugin.sh | invokes | `.claude/skills/harness-publish/SKILL.md:29,37,47` |
| model-council | Codex CLI (`codex exec`) | invokes | `.claude/skills/model-council/SKILL.md:16-17` |
| check-invariants | invariants.md | reads | `.claude/skills/check-invariants/SKILL.md:9` |
| harness-staleness-nudge | harness-status | routes-to | `.claude/hooks/harness-staleness-nudge.sh:12` |
| block-dangerous-commands | Git safety / bd store / mirrors | enforces | `.claude/hooks/block-dangerous-commands.sh:18-87`; `.claude/settings.json:4-13` |
| block-generated-edits | generated mirrors read-only | enforces | `.claude/hooks/block-generated-edits.sh:22-26`; `.claude/settings.json:14-23` |
| skill-catalog.py | skill-router catalog + openai.yaml | produces / enforces | `.claude/scripts/skill-catalog.py:9-20`; `.repo-context/invariants.md:7-9` |
| contractor | feature-delivery graph (pinned `contractor_graph`) | invokes | `config/foreman.example.toml:22-25`; `docs/usage/contractor.md:9` |
| contractor | ship gate approval | requires | `docs/usage/contractor.md:9`; `workflows/feature-delivery.toml:180-184` |
| contractor | `[[contractor_checks]]` | requires | `docs/usage/contractor.md:13-23` |
| contractor | tracker (claim / close) | invokes | `docs/adr/0006-ledger-only-record-store.md:12-21` |
| contractor | landing receipt / CAS on target | produces | `docs/usage/contractor.md:9,29-37` |
| foreman | inspector → crew | invokes | `.repo-context/CONTEXT.md:54-61`; `workflow_interpreter/profiles/__init__.py:10-13` |
| foreman | ledger | produces | `docs/adr/0006-ledger-only-record-store.md:26-31` |
| feature-delivery debrief node | `docs/workstreams/**` knowledge | produces | `docs/adr/0005-run-ledger.md:19-23`; `workflows/feature-delivery.toml:203-206` |
| bdio gates | signed approvals (allowed_signers) | enforces | `workflow_interpreter/bdio/__init__.py:3-5`; `config/foreman.example.toml:72-86` |
| approve-gate.sh | gate inbox | produces | `scripts/approve-gate.sh:4-8,13` |
| monitor | bd wake events / hook_argv | produces | `docs/usage/engine-bundle.md:176-206` |
| inspector | recovery refs `refs/wf/<root>/recovery/<act>` | produces | `docs/usage/node-contract-recovery.md:24-40` |

## 4. Main lifecycle

Canonical path for durable feature work. Gates are marked ◆.

1. **Request arrives.** SessionStart hooks inject `bd prime` (`.claude/settings.json:25-34`). AGENTS.md routes the work (`AGENTS.md:83-98`). skill-router is optional (`.claude/skills/skill-router/SKILL.md:8-10`).
2. **Size check.** A clear bounded task goes straight to execution's task loop with no plan (`.claude/skills/execution/SKILL.md:17-18`; `.claude/skills/planning/SKILL.md:15`). Otherwise:
3. **brainstorming** produces a draft spec.
   - ◆ A material-risk spec gets a critic **review** (`.claude/skills/brainstorming/SKILL.md:48-49`).
   - ◆ **Human approval** marks the spec `approved` (`.claude/skills/brainstorming/SKILL.md:44-47`).
4. **planning / Decompose** writes the roadmap, phases and stages.
   - ◆ **Human approval of the structure** comes before any Beads write (`.claude/skills/planning/SKILL.md:36-37`; `.claude/skills/planning/references/decompose.md:38-48`).
   - It then seeds epics (`[<phase>]`, `ws-<name>`) and stages with acceptance, and renders mirrors (`.claude/skills/planning/references/decompose.md:55-81`).
5. **planning / Elaborate** writes a just-in-time phase plan (`.claude/skills/planning/SKILL.md:39-40,42-61`).
   - ◆ A material-risk plan gets a critic **review** (`.claude/skills/planning/SKILL.md:55-56`).
6. **Execution entry.** One of:
   - `/phase-execution <id>` (`.claude/skills/phase-execution/SKILL.md:9-17`)
   - `/run-phases <roadmap>` (`.claude/skills/run-phases/SKILL.md:9-19`). ◆ This invocation is the unattended opt-in.
7. **Phase loop** (`.claude/skills/execution/SKILL.md:57-82`):
   1. Resolve exactly one epic.
   2. Claim the phase.
   3. Select a ready stage.
   4. Run **contractor**: `foreman contract <epic> <stage>`. Inside the engine:
      - pin the check policy, then claim (tracker)
      - foreman ticks: implement → debrief → review (bounded region, 3 entries) (`workflows/feature-delivery.toml:12-17,198-266`)
      - host verify after each node (`docs/usage/verification.md:3-7`)
      - ◆ **signed human `ship` gate** (`workflows/feature-delivery.toml:180-184,254-255`)
      - contractor checks run on a detached candidate, CAS-land onto the target branch, write the receipt, close the stage (`docs/usage/contractor.md:9,13-23`)
   5. Read the contractor's JSON:
      - `result`: render mirrors and pick the next stage.
      - `blocked`, `refused` or `phase-exhausted`: handle as named (`.claude/skills/execution/SKILL.md:71-78`).
8. ◆ **Epic close gate.** All stages must be closed and the roadmap exit criterion must pass (`.claude/skills/execution/SKILL.md:79-82`).
9. **Workstream mode** only (`.claude/skills/execution/references/workstream-mode.md:20-27`):
   - Regenerate tracking and refresh the export.
   - Commit per phase only if the invocation covers it. No push.
   - Move to the next eligible phase.
10. **Session close** (`.beads/beads.md:90-101`):
    - Close issues with evidence, run gates and refresh `issues.jsonl`.
    - Record `git status` and a `resume with:` note.
    - ◆ **Commit/push only when authorized** (`AGENTS.md:64-65`).

The task-scope alternative to step 7 (`.claude/skills/execution/SKILL.md:36-53`; `.claude/skills/execution/references/task-engine.md:38-111`):

- claim the task
- implement inline, or dispatch the **implementer** with a brief
- run checks and inspect the diff
- optional **spec-reviewer / code-reviewer** via review, with a ≤5-round fix loop
- close with `--reason`

No contractor and no ship gate on this path; landing is a normal authorized commit.

## 5. Problem map

| problem id | node(s) used, in order | how it solves it (one line, mechanism) | gap? |
|---|---|---|---|
| P01 | show-me → teach → codebase-research (external) | Inline structural visuals; explanations; L1/L2/deep-dive reports with reachability ladder (`.claude/skills/codebase-research/SKILL.md:12-52`) | partial. J: there is no local-codebase explainer skill; it is direct source reading by policy (`.claude/skills/skill-router/SKILL.md:21`) |
| P02 | docs/adr → learnings.md → resolving-merge-conflicts (history) | ADRs hold rationale (`docs/adr/README.md:3-4`); learnings carry evidence and revisit conditions (`.repo-context/learnings.md:1-5`); conflicts use commit intent (`.claude/skills/resolving-merge-conflicts/SKILL.md:8-9`) | partial. J: no git-archaeology / blame workflow |
| P03 | brainstorming → grilling (grill-me, grill-with-docs) → wayfinder → triage | Option/tradeoff exploration; batched interview; Beads decision graph; intake states (`.claude/skills/brainstorming/SKILL.md:25-35`; `.claude/skills/wayfinder/SKILL.md:15-50`) | no |
| P04 | brainstorming → codebase-design → improve-codebase-architecture → design-evolve → domain-modeling (ADR) | Depth/seam lens; evidence-backed survey; versioned design integration (`.claude/skills/codebase-design/SKILL.md:24-41`) | no |
| P05 | planning (Decompose → Elaborate) → beads | Phases/stages with acceptance and real dependency edges; Stage-mapped plan tasks (`.claude/skills/planning/SKILL.md:24-61`) | no |
| P06 | execution (task or phase) → implementer / contractor | Task loop with claim, implement, verify and close; phase loop via contractor landing (`.claude/skills/execution/SKILL.md:36-82`) | no |
| P07 | systematic-debugging → (review critic) | Repro → hypothesis → probe → confirmed-cause fix → regression check; stop after 2 failed fixes (`.claude/skills/systematic-debugging/SKILL.md:12-47`) | no |
| P08 | performance-optimization | Baseline, profile, one-factor change, compare under same conditions (`.claude/skills/performance-optimization/SKILL.md:12-28`) | no |
| P09 | test-driven-development; build-loop graph | Test-first / characterization. In the build-loop graph, `write_tests` must record the red-test command, result and semantic reason (an agent claim, judged at test review). The host runs only `scripts/checks/tests-parse.sh`, which "does not establish semantic red evidence" (`.claude/skills/test-driven-development/SKILL.md:8-44`; `workflows/build-loop.toml:41-47,67`; `docs/usage/verification.md:32-40`) | no |
| P10 | review (code / document / feedback) → spec-reviewer / code-reviewer; engine review node | Critic contract, APPROVE/REVISE, severity; dispatched output formats (`.claude/skills/review/SKILL.md:10-43`; `.claude/skills/review/references/review-contract.md:13-41`) | partial. J: agents point at sections ("Evidence discipline", "Do not trust the report", "Severity calibration") that do not exist under those names in the renamed review skill (`.claude/agents/code-reviewer.md:14-20`; `.claude/agents/spec-reviewer.md:14-16`) |
| P11 | AGENTS Verification → verification.md → check-invariants → engine host verify + contractor checks | Claim→evidence table; five-stage host gate; pinned host checks gate advancement and landing (`.repo-context/verification.md:11-75`; `docs/usage/contractor.md:13-23`) | no |
| P12 | contractor (CAS land) → harness-publish | Local signed-ship-gated landing; plugin publish script (`docs/usage/contractor.md:9`; `.claude/skills/harness-publish/SKILL.md:33-60`) | partial. No PR / release / push flow (`workflow_interpreter/inspector/__init__.py:15-16`; `AGENTS.md:64-65`) |
| P13 | AGENTS delegation → task-engine dispatch → children admit/drive/collect → integration prepare → contractor; model-council / perspective-council | Bounded workers; independent child graphs with a concurrency cap and owner budget (`docs/usage/children.md:1-21`; `docs/usage/contractor.md:48-60`) | no |
| P14 | run-phases → workstream-mode → contractor; `foreman run` / monitor | Unattended phase walk; tick loop up to an 8 h default wall; monitor wakes (`.claude/skills/execution/references/workstream-mode.md:13-39`; `workflow_interpreter/foreman/constants.py:181`) | partial. A human ship gate is required per stage (see §6) |
| P15 | bd-prime hook → beads.md session close → task-engine progress.md → workstream-mode recovery; codex exec resume | `resume with:` notes; ledger re-read after recovery; Codex resume (`.beads/beads.md:98-100`; `.claude/skills/execution/references/task-engine.md:14-18`; `.repo-context/running-codex.md:13-19`) | no |
| P16 | learnings.md → debrief node → harness-evaluate | Record verified recurring patterns; feature-delivery runs write a debrief into the repo; the `basic` graph has no debrief node (`AGENTS.md:27-28`; `docs/adr/0005-run-ledger.md:19-23`; `workflows/feature-delivery.toml:203-206`; `workflows/basic.toml:1-83`) | partial. J: no automated feedback loop from debriefs into skills/harness |
| P17 | authoring-for-agents → i-have-adhd → html-artifact → show-me | Instruction-writing rules; output style; standalone/inline visuals | partial. J: no general prose / commit-message style skill |
| P18 | domain-modeling (grill-with-docs) → `.repo-context/CONTEXT.md` → docs/adr | Glossary and sparing ADRs (`.claude/skills/domain-modeling/SKILL.md:24-52`) | no |
| P19 | security → block-dangerous-commands → bwrap sandbox / signed gates | Threat scoping and controls; hook blocks; mount bound; allow-list outside workspace (`.claude/skills/security/SKILL.md:12-45`; `workflow_interpreter/inspector/sandbox.py:1-8`) | partial. Claude crew network is `not_enforced` (`docs/usage/engine-bundle.md:100-102`) |
| P20 | beads (beads.md) → triage → wayfinder → bd-render-tracking | Durable items, intake states, ready-for-agent gate, generated mirrors (`.beads/beads.md:9-88`) | no. J: renderer limitation `cr-tew` remains (`docs/workstreams/agent-bridge/state.md:30`) |
| P21 | authoring-for-agents → skill-catalog.py → harness-status/scan/evaluate/skill-compare → migrate-claude-to-codex → harness-publish | Surface selection and activation tests; catalog lint; reference curation ledger; publish (`.claude/skills/authoring-for-agents/SKILL.md:11-50`) | no |
| P22 | prototype | Throwaway artifact for one named question; promotion is separate work (`.claude/skills/prototype/SKILL.md:8-28`) | no |

## 6. Autonomy

### What lets it run without a human, step by step

1. **Opt-in.** `/run-phases <roadmap>` is the explicit authorization for unattended walking and, if the invocation covers it, per-phase commits (`.claude/skills/run-phases/SKILL.md:13-15`; `.claude/skills/execution/references/workstream-mode.md:3-5,20-25`). `/phase-execution` grants one phase only (`.claude/skills/phase-execution/SKILL.md:15-17`).
2. **Preflight.** Capture the base and dirty baseline, then reconcile each roadmap phase to exactly one epic (`.claude/skills/execution/references/workstream-mode.md:7-11`).
3. **Selection.** The LLM picks the first eligible phase and a ready stage. The contractor never chooses the next stage (`docs/usage/contractor.md:9`; `.claude/skills/execution/SKILL.md:65`). Within a phase, `bd ready --parent` is enough; standalone AFK work needs `ready-for-agent` (`.beads/beads.md:59-62`).
4. **Deterministic inner loop.**
   - `foreman run <root>` ticks one decision at a time. Routing is a table lookup; the model router was rejected (`docs/adr/0004-deterministic-routing.md:29-39`; `.repo-context/CONTEXT.md:54`).
   - Inspector-contained crews run in bwrap with pinned briefs (`docs/usage/node-contract-recovery.md:3-22`).
   - Host verification after every node overrides model claims (`docs/usage/verification.md:3-7`).
   - A red check routes `fail_code` → implement as rework, not a human halt (`workflows/feature-delivery.toml:209-212`).
5. **Bounded decisions.** Ordinary model decisions (`continue_declared`, `replace`, `human`) run without a human when declared. Malformed or stale output needs human attention (`workflows/README.md:31-45`).
6. **Coordinator observation without polling.**
   - The driver writes a heartbeat and a refusal journal.
   - A separate `monitor` emits bd wake events. `hook_argv` "can enqueue a new coordinator turn" (`docs/usage/engine-bundle.md:136-206`).
   - The monitor is a separately started, operator-managed host process. It wakes on gate opening, root terminal, refusal, unexpected driver exit or loss, and stale heartbeat. "Expected stops at a gate, terminal, wall limit, or acknowledged operator interruption use no wake slot." Hook delivery is at-least-once, so receivers must deduplicate `fire_key` (`docs/usage/engine-bundle.md:159-179,196-206`).
   - J: nothing in the repo ships such a hook. `hook_argv` is commented out (`config/foreman.example.toml:55-56`), so re-waking the LLM orchestrator is unwired.
7. **Parallelism.** `children drive --max-concurrent N --max-wall S` runs independent graphs under one owner budget (`docs/usage/children.md:8,17-21`).

### Where it must stop for a human

- **Ship gate per stage.**
  - `feature-delivery` and `design-spec` reach `shipped` only through a signed human `ship` gate (`workflows/feature-delivery.toml:180-184,270-272`; `workflows/README.md:24-27`). The contractor consumes that approval before landing (`docs/usage/contractor.md:9`).
  - The signed payload binds the exact artifact (`commit_oid`, `tree_oid` or sha256). For `binds = "immutable"`, the signature over the commit OID is the authority (`docs/specs/workflow-interpreter.md:1058-1095`). A grant signed before the candidate exists would lose that binding. The coordination spec preserves human ship approval by default and allows graphs to explicitly permit attributable model decisions where supported (`docs/specs/2026-09-11-workflow-coordination.md:36`).
  - Approval means signing the rendered template with `scripts/approve-gate.sh` and a key whose allow-list lives outside the workspace (`scripts/approve-gate.sh:2-16`; `config/foreman.example.toml:72-86`).
  - J: **`/run-phases` is therefore not end-to-end unattended on the contractor path.** Each stage parks at `ship` and the contractor returns the waiting run result (`docs/usage/contractor.md:9`). Live proofs used fixture signatures, "not production human approval" (`docs/workstreams/agent-bridge/state.md:20`).
  - J: the protection is against the foreman/crew forging approvals (`config/foreman.example.toml:80-82`). It is not technically against an interactive orchestrator with host key access; that boundary is policy (`AGENTS.md:61`).
- **Triage gate (human).** Region exhaustion (3 entries), `fail_plan`, `no_diff`, debrief failure and graph fallback all route to `triage`, whose only outcomes are `rebudget` or `abandon` (`workflows/feature-delivery.toml:12-17,187-191,289-290`).
- **Halt gate when a process death can't be confirmed** (`docs/usage/node-contract-recovery.md:111-113`). Also any `DEAD_END` (`docs/adr/0004-deterministic-routing.md:34-39`).
- **Prose-layer gates:**
  - spec approval (`.claude/skills/brainstorming/SKILL.md:44-47`)
  - decompose/plan approval before Beads writes (`.claude/skills/planning/SKILL.md:36-37`)
  - new behavior, safety-boundary or scope changes, which are outside unattended authority (`.claude/skills/execution/references/workstream-mode.md:17-19`)
  - commit/push/publish (`AGENTS.md:11-12,64-65`; `.claude/skills/execution/references/workstream-mode.md:22-25`)
  - deferral that accepts material risk (`.claude/skills/execution/references/task-engine.md:80-82`)
  - merge abort (`.claude/skills/resolving-merge-conflicts/SKILL.md:11`)
- **Advancement stops** on a failed phase gate, a failed exit criterion or a material blocker (`.claude/skills/execution/references/workstream-mode.md:37-39`; `.claude/skills/execution/SKILL.md:84-86`).
- **Hooks force an ask.** Dangerous Git/rm/bd-reinit commands exit 2 with "Ask the user" (`.claude/hooks/block-dangerous-commands.sh:31-47`).

### Failure and recovery mechanisms

**Bounds**

- `max_total_activations = 26` (`workflows/feature-delivery.toml:8`)
- region `max_entries = 3` (`workflows/feature-delivery.toml:16`)
- per node: `max_infra_retries = 2` and `max_steers` (`workflows/feature-delivery.toml:59-60`)
- prose fix loop: ≤5 rounds, stop earlier without new evidence (`.claude/skills/execution/references/task-engine.md:92-99`)
- debugging: stop after 2 failed fixes (`.claude/skills/systematic-debugging/SKILL.md:44-45`)

**Retries**

- Infrastructure retry on `error_transport` (`docs/usage/node-contract-recovery.md:60-63`).
- `contract --retry` mints a new attempt for an eligible terminal (`docs/usage/contractor.md:39`).
- `contract --retry-landing` re-runs checks and the same CAS. It never runs agents (`docs/usage/contractor.md:27-37`).
- `integration retry` (`docs/usage/contractor.md:60`).
- `children recover` / `replace` (`docs/usage/children.md:17-24,47-57`).
- Bounded transient retry for dispatched workers (`.claude/skills/execution/references/task-engine.md:54-57`).

**Idempotent resume**

- Rerunning `contract` reads durable state first and never moves a ref by default (`docs/usage/contractor.md:29`).
- A closed stage replays its receipt without re-executing (`docs/usage/contractor.md:45`).

**Recovery tree**

- Dirty writer content after a confirmed death is pinned at `refs/wf/<root>/recovery/<activation>` with chained snapshots.
- A failed pin leaves the activation open and retryable.
- `foreman inspect` shows the recovery record read-only (`docs/usage/node-contract-recovery.md:24-91`).

**Ledger**

- Closure is derived and latched (LANDED plus export anchor) (`docs/adr/0006-ledger-only-record-store.md:22-26`).
- Mirrors drain through the outbox at driver exit or via `ledger reconcile` (`docs/adr/0006-ledger-only-record-store.md:18-21`).
- `ledger verify` re-verifies signed bytes from the committed export (`docs/adr/0005-run-ledger.md:24-31`).
- `restore` and `archive` exist (`workflow_interpreter/ledger/__main__.py:130-182`).

**Observation**

- Heartbeat, a deduplicated refusal journal, and `status` showing the latest refusal and heartbeat age.
- `run`/`contract` exit nonzero on refusal (`docs/usage/engine-bundle.md:136-157`).
- In-place steer with uncertain-delivery acknowledgment (`docs/usage/engine-bundle.md:267-291`).

**Prose-layer recovery**

- `progress.md` ledger with `SCOPE_BASE`; on recovery, re-read the ledger, Beads and Git (`.claude/skills/execution/references/task-engine.md:8-18`; `.claude/skills/execution/references/workstream-mode.md:29-35`).
- Beads `resume with:` notes (`.beads/beads.md:98-100`).
- `codex exec resume` (`.repo-context/running-codex.md:13-19`).
- The Beads store wipe is guarded by a hook; `issues.jsonl` is the fallback mirror (`.claude/hooks/block-dangerous-commands.sh:38-47`; `.beads/beads.md:23-26`).

**No rollback.** There is no automatic restore or rollback (`docs/usage/node-contract-recovery.md:101-104`). On failure, completed work is preserved, not reverted (`.claude/skills/execution/SKILL.md:85`; `AGENTS.md:66-68`).
