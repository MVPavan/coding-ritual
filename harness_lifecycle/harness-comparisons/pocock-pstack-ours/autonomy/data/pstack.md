# pstack harness map (v0.15.9)

Source: `reference_harnesses/cursor_plugins/pstack/` (plugin manifest `reference_harnesses/cursor_plugins/pstack/.cursor-plugin/plugin.json` declares `"skills": "./skills/"`, `"agents": "./agents/"`; version 0.15.9). Short ids below: `PM` = the `poteto-mode` skill, `pb:<name>` = `reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/<name>.md`, `p:<name>` = `principle-<name>` skill, `ext:` = something pstack references but does not ship.

## 1. Infrastructure assumptions

pstack is a Cursor plugin written for Cursor's own engineering setup: every change is a GitHub PR from a worktree, PRs are stacked, CI plus Bugbot and an "agentic security review" bot comment on every PR, cloud agents are a cheap fan-out target, and a sibling plugin (`cursor-team-kit`) supplies `deslop` and the `control-ui` / `control-cli` live-drive skills. Running "like pstack in full autonomy" means reproducing most of the rows below.

| Assumption | Evidence (path:line) | What breaks without it |
|---|---|---|
| **VCS: everything ships as a PR.** "Opening a PR" is invoked at the end of every other playbook; every reply ends with a GitHub PR link. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:3; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:113; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:147 | No terminal step for any build playbook; babysit/shipping/autopilot have nothing to drive. (J: investigation, forensics, prototype explicitly do not PR, so "every" is overstated: reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/investigation.md:12.) |
| **Worktree per task, one writer per worktree/branch.** Work from a worktree off main; parallel Task calls on one branch each get a worktree. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:5; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:17; reference_harnesses/cursor_plugins/pstack/skills/arena/SKILL.md:29; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/hillclimb.md:12; reference_harnesses/cursor_plugins/pstack/docs/guide/10-recipes-and-pitfalls.md:85 | Parallel agents overwrite each other; arena/hillclimb fan-out unsafe. worktree-cleanup playbook exists because these accumulate (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/worktree-cleanup.md:5). |
| **Stacked PRs (base-branch chains).** "Prefer five narrow PRs to one large PR. A stack is a base-branch chain." Child PR targets parent branch; root targets trunk. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:30; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-stack.md:10; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:8 | Babysit's "merge frontier" (lowest unmerged PR) and Shipping's "contiguous verified run from the root" have no meaning; commit-ordering advice (each commit is a future PR) loses its point (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:7). |
| **Forge = GitHub via `gh` CLI (default) or Cursor-internal `origin` CLI; never require Graphite `gt`.** | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:26; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:7; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:7; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:6 | All PR create/view/merge/retarget steps; `watch-pr` shells out to `gh api graphql` and `gh pr view` (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/scripts/watch-pr/github.ts:439). |
| **Graphite `gt` IS required by Orchestrate's frontier.** Contradiction with the rows above: "Recompute frontier.json from gt after every merge"; one stacker per stack runs gt; `orch frontier` execs `gt info`. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:79-80; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/scripts/orch/orch.ts:475; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/scripts/orch/store.ts:1075 | `orch frontier set` errors; Orchestrate's stack-safety section cannot run on a gh-only repo. J: Orchestrate is older/heavier than the autopilots and was not migrated off gt. |
| **Built-in PR tool when the run provides one** (Cursor cloud-agent PR tool) takes precedence over the CLI. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:28 | Falls back to forge CLI; minor. |
| **PRs open ready, never draft.** | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:32; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:6 | Draft PRs may not trigger CI/bots the babysit loop waits on (J). Note benny automation opens draft PRs only (reference_harnesses/cursor_plugins/pstack/automations/benny/FOR_AGENTS.md:21,36), the one exception. |
| **CI on every PR with required checks + merge-when-ready / auto-merge / merge queue.** | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:12-21; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:11,14; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/scripts/watch-pr/cli.ts:100-109 (`--queued-stack`, `--stack-prs`) | Babysit's CI classification, watcher verdicts (READY/WAITING merge-queue/ADVANCE/COMPLETE) and Shipping's `--auto` arming are inert. |
| **Review bots: Cursor Bugbot and an "agentic security review" comment on PRs.** watch-pr detects them by token. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:34; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/references/bugbot-triage.md:3-13; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/scripts/watch-pr/policy.ts:49-54; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:60 | Bugbot triage, pass counting, and the shared dismissal rubric have no input. These bots are inputs to triage, not prerequisites for the autonomy path (see the §6 judgement note). J: an external reviewer is the only independent code review in the default single-PR path besides `interrogate`. |
| **Repo pre-review gates named in AGENTS.md / rules; git hooks on.** | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:6 ("pre-review checks that the repo's AGENTS.md files and rules name"; "hooks on"); reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:58 | Owners push without local gates; pstack ships no hooks of its own. |
| **Cursor-team-kit plugin installed** for `/deslop` (before commit), `control-ui` (browser/Electron/web) and `control-cli` (CLI/TUI) live driving. | reference_harnesses/cursor_plugins/pstack/README.md:233-241; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:28,30; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:9 | Pre-commit slop strip skipped; every "verify on the matching surface" step (bug-fix 1/4, feature 5, prototype 5, perf 1, visual-parity 4, shipping 1, autopilot live lane) has no driver. The live lane is "the floor" of a clean verdict (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:8). |
| **Project-local `verify-<app>` skill** as an alternative/extension of the control skills, generated by pstack. | reference_harnesses/cursor_plugins/pstack/skills/setup-pstack/SKILL.md:72-75; reference_harnesses/cursor_plugins/pstack/skills/create-verification-skill/SKILL.md:9,25; reference_harnesses/cursor_plugins/pstack/docs/guide/01-setup.md:29-33 | Same as above; live verification degrades to unit tests, which multi-phase-plan says are "not sufficient" (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:13). |
| **Cursor `Task` tool subagent API**: `subagent_type`, `model`, `readonly`, `run_in_background`, `environment: "cloud"/"local"`, `cloud_base_branch`, nested spawn to depth 3. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:93-99; reference_harnesses/cursor_plugins/pstack/skills/swarm/SKILL.md:30-32; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:15-17 | Every delegation, panel, and fan-out. `readonly` "strips MCP" so MCP-backed investigators must run in agent mode (reference_harnesses/cursor_plugins/pstack/skills/why/SKILL.md:85). |
| **Cursor cloud agents** as cheap, durable workers/verifiers (one VM per lane; survive local Cursor restart; status in Cursor dashboard). | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:7; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:6; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:17,95,101; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:71 | Per-PR independent verifiers, 10-lane live swarms, and autopilot owners all assume cloud concurrency; locally they contend for one machine (orchestrate: "A local restack at this scale takes the laptop down", reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:80). |
| **Cursor `/loop` built-in** (dynamic mode, `/loop 1h`) is the only wake/heartbeat mechanism. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:6; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:12; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:10; reference_harnesses/cursor_plugins/pstack/README.md:93 | No unattended iteration; babysit `drive`, shipping watch, autopilot audit ticks all stop after one turn. |
| **Cursor modes / rules / built-ins**: `mode: true` sticky mode with `reminder:` frontmatter; `AskQuestion` tool; built-in `create-skill`; built-in `/babysit` (overridden); plan mode; `~/.cursor/rules/pstack-models.mdc` always-applied rule; `disable-model-invocation`. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:4-8,20,26; reference_harnesses/cursor_plugins/pstack/README.md:239,245; reference_harnesses/cursor_plugins/pstack/skills/setup-pstack/SKILL.md:8,39-44 | PM is not sticky; model roles fall back to hard-coded defaults; skill authoring/reflect routing has no `create-skill`. |
| **Cursor local stores**: `agent-transcripts/` directory (path from system prompt), the agent store (path in system prompt) for orchestrate/plan files. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/session-pickup.md:5; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/eval.md:22; reference_harnesses/cursor_plugins/pstack/skills/show-me-your-work/SKILL.md:57; reference_harnesses/cursor_plugins/pstack/skills/recall/SKILL.md:15; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:23; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:8 | Session pickup, eval chain-grading, trail audit, reflect, recall, automate-me, worktree-audit's "last chat" column (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/scripts/worktree-audit.sh:26-27). |
| **Other Cursor product tools**: `update_state` routines, `SendToUser` secret-request, webhook automations (Grok Bot); image-generation tool; Cursor automations triggered from Slack. | reference_harnesses/cursor_plugins/pstack/skills/make-bot-ui/SKILL.md:15,43-49; reference_harnesses/cursor_plugins/pstack/skills/teach/SKILL.md:17; reference_harnesses/cursor_plugins/pstack/automations/benny/FOR_AGENTS.md:5-36 | make-bot-ui and benny are unusable outside Cursor; teach falls back to mermaid. |
| **MCPs, discovered at run time**: issue tracker (Linear/Jira/GH Issues), docs (Notion/Confluence), chat (Slack), infra observability (Datadog/Grafana), error tracking (Sentry), analytics warehouse (Databricks/Snowflake). "Use any MCP tool." | reference_harnesses/cursor_plugins/pstack/skills/why/SKILL.md:64-76,100-112; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:83; reference_harnesses/cursor_plugins/pstack/skills/recall/SKILL.md:20 | `why` degrades to git+gh only and must record each missing category as a gap (reference_harnesses/cursor_plugins/pstack/skills/why/SKILL.md:118). Source control is the only guaranteed source (reference_harnesses/cursor_plugins/pstack/skills/why/SKILL.md:100). |
| **Issue tracker**: none required by core pstack. Orchestrate keeps its own `overview.md` PR/issue DB; reflect files backlog to "whatever devex / backlog tracker your team uses"; benny requires a configured tracker. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:26; reference_harnesses/cursor_plugins/pstack/skills/reflect/SKILL.md:55; reference_harnesses/cursor_plugins/pstack/automations/benny/FOR_AGENTS.md:11 | Nothing in the core lifecycle; work tracking is PRs + TSV files. |
| **Models: multi-family panel.** Defaults `grok-4.7-xhigh-fast` (code delegates, explorers, swarm workers), `claude-opus-5-5-max` (judgment, prose, hardest tasks), `gpt-5.6-sol-max` (panel seat); per-role overrides in `pstack-models.mdc`. Orchestrate runs a unit's verifier on a different family from its worker (orchestrate.md:17). Shipping requires only a verifier "that did not write the code", with no family rule (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:7). | reference_harnesses/cursor_plugins/pstack/README.md:30; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:95; reference_harnesses/cursor_plugins/pstack/skills/setup-pstack/SKILL.md:49-65; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:17; reference_harnesses/cursor_plugins/pstack/skills/show-me-your-work/SKILL.md:67 | arena/interrogate/architect lose "diversity of model" signal; cross-model trail review impossible. `inherit-parent`/`auto` aliases let a single-model setup run (reference_harnesses/cursor_plugins/pstack/skills/setup-pstack/SKILL.md:31). |
| **Bun + Node runtime** for the bundled scripts (`orch.ts`, `watch-pr`, `check-plan.mjs`); scripts self-install deps via `bun install --frozen-lockfile`. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/scripts/package.json:1-17; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/scripts/bootstrap.ts:33-36; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:23; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:10 | Orchestrate bookkeeping, PR watcher, and plan linter unavailable. |
| **pstack source lives in the target repo at `pstack/`** (cursor/plugins monorepo): audit ticks re-read playbooks with `git show origin/main:pstack/skills/...`. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:10; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-stack.md:6; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:10,35-40 | The "re-read playbook from trunk every tick" drift guard fails in any repo that installs pstack as a plugin. J: must be adapted to the installed path. |
| **Human touchpoints.** Always-pause list (force-push shared branches, deploys, data deletion, customer messages); operator-named items; state-then-wait "go"; interaction-changing PRs review-gated with screenshots + video; Bugbot `ask` class; reflect edits approval; merge only on explicit "land/ship/merge"; worktree `wip:` deletions. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:85; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:5; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:13,120-124; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/references/bugbot-triage.md:11,75-82; reference_harnesses/cursor_plugins/pstack/skills/reflect/SKILL.md:53; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:18,23; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/worktree-cleanup.md:8 | See section 6. |
| **Persistence = files + git, no DB.** `decisions.tsv` trail (uncommitted by default), `children.tsv`, orchestrate store (`preferences.md`, `units.tsv`, `ledger.tsv`, `frontier.json`, `inbox/`, `gates.md`, `status.md`), `wip:` commits, `/tmp/<slug>-resume.md`, shared `bugbot-triage.md` rubric. | reference_harnesses/cursor_plugins/pstack/skills/show-me-your-work/SKILL.md:13-22,46; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:6; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:23-32; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/pause-safely.md:7-8; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:23 | No cross-session memory beyond transcripts + git; recall/session-pickup reconstruct from transcripts. |
| **Autonomy level: high by default.** "Just do it. Use any MCP tool. Reversible work and external actions (team chat, ticket updates, kicking off evals) proceed without asking"; "going to bed"/"be fully autonomous" overrides. | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:83-87; reference_harnesses/cursor_plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md:9-20 | J: posting to team chat and tickets without asking is more permissive than most harnesses; the never-block principle itself lists "send external messages" as needing confirmation (reference_harnesses/cursor_plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md:18), a direct tension. |

## 2. Nodes

Invocation key. All skills except `setup-pstack` carry `disable-model-invocation: true` (verified by grep), so the model does not auto-pick them from descriptions; they run when the user types the slash command or when PM / a playbook / another skill names them. That is written below as `user-only (+routed)`.

### Entry, agents, config

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| poteto-mode (PM) | skill | user-only, then sticky mode (`mode: true`, `reminder:`) | Router: match a playbook, copy its steps verbatim into the todo list, fire triggers, enforce reply style, autonomy and subagent defaults. |
| poteto-agent | agent | model (Task `subagent_type: "poteto-agent"`, `is_background: true`) | Default subagent for any playbook step; must read PM in full first. |
| Comment Sicko | agent | model (spawned by no-comments) | Comment hater: deletes non-exempt comments, flags `MUST KILL` symbols, never writes app code. (README calls it read-only, reference_harnesses/cursor_plugins/pstack/README.md:195; its body reports deletions, reference_harnesses/cursor_plugins/pstack/agents/comment-sicko.md:32.) |
| setup-pstack | skill | model + user (only skill without the disable flag) | Detect models, ask budget, write `~/.cursor/rules/pstack-models.mdc`; offer create-verification-skill. |
| pstack-models.mdc | rule (generated) | always (`alwaysApply: true`) | Per-role model map read by every routed skill. |

### Playbooks (23, all `model`: matched by PM)

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| pb:investigation | playbook | model | Read-only cited answer via how/why; no PR. |
| pb:bug-fix | playbook | model | Repro on real surface, binary-search cause, delegate fix, failing-repro-first commits, PR. |
| pb:perf-issue | playbook | model | Baseline trace, mantras, delegated fix, post-trace, cite number in PR. |
| pb:hillclimb | playbook | model | Frozen harness, one-hypothesis loop, keep/revert, decision.tsv, PR of accepted commits. |
| pb:runtime-forensics | playbook | model | Diagnose live symptom from instrumentation; diagnosis only. |
| pb:trace-forensics | playbook | model | Diagnose captured profile artifact via sqlite; diagnosis only. |
| pb:feature | playbook | model | how, architect, throughput checkpoint, delegate (arena mandatory when shapes vary), verify, interrogate if contested, PR. |
| pb:refactoring | playbook | model | Pin behavior, subtract, reshape in small green steps, equivalence proof, reader-load check, PR. |
| pb:prototype | playbook | model | Throwaway scratch variants behind a switcher to settle a decision empirically; hand to Feature. |
| pb:visual-parity | playbook | model | Baseline screenshot harness, per-component migration until image diff is zero. |
| pb:authoring-a-skill | playbook | model | create-skill, validate frontmatter/links, PR. |
| pb:eval | playbook | model | Blinded multi-model candidate run + blinded judge, transcript-graded. |
| pb:babysit | playbook | model (PR-status phrasing) | Drive the merge frontier to merge-ready: conflicts, threads, CI; modes drive/background/threads-only/check. |
| pb:shipping | playbook | model (land/ship request) | Independent per-PR cloud verdicts, land contiguous verified run bottom-up with patch-id checks. |
| pb:autonomous-run | playbook | model | Checkable predicate + /loop wake; iterate, commit or discard, never relax predicate. |
| pb:orchestrate | playbook | model | Multi-day program: coordinator writes briefs, never code; orch store, ledger, drains, stack safety. |
| pb:autopilot-full | playbook | model | One cloud owner per independent PR through merge; root swarm verdict per round; hourly audit tick. |
| pb:autopilot-stack | playbook | model | Same owner loop; root appends verified PRs into one linear stack; operator lands. |
| pb:session-pickup | playbook | model | Resume from transcript / cloud URL / branch; trust the trail; route remaining work. |
| pb:pause-safely | playbook | model (explicit only) | Safe boundary, `wip:` commit, off-context resume note. |
| pb:multi-phase-plan | playbook | model | Produce a checklist plan (fixed skeleton, 10 live lanes/PR), lint with check-plan, stop for operator go. |
| pb:worktree-cleanup | playbook | model | Audit and prune worktrees/simulators behind safety gates. |
| pb:opening-a-pr | playbook | model (end of other playbooks) | Worktree, ordered commits, deslop/no-comments/technical-writing/unslop, Conventional title, briefing body, forge, stack bases, ready. |

### Workflow skills (24; with PM, setup-pstack and 24 principles = 50)

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| how | skill | user-only (+routed) | 2-4 readonly explorers + explainer subagent; Overview/Key Concepts/How It Works/Where/Gotchas. |
| why | skill | user-only (+routed) | Git/gh code anchor, one investigator per discovered MCP category, synthesizer with epistemics. |
| recall | skill | user-only | Rebuild recent working context from transcripts + why-style shared-record sweep; capsule brief. |
| teach | skill | user-only | Run how + why, weave one plain explanation built diagram by diagram. |
| blast-radius | skill | user-only | Find what a change breaks beyond the diff; prove the one safety fact by running code. |
| architect | skill | user-only (+routed) | Ground (how/why), sketch via arena (≥2 distinct designs), optional checkpoint, implement, scrap on pattern friction. |
| arena | skill | user-only (+routed) | N parallel candidates, cross-judge, pick base, graft, verify. |
| swarm | skill | user-only (+routed) | N parallel cloud workers (slices or races), aggregate one PASS/ISSUES/BLOCKED report. |
| interrogate | skill | user-only (+routed) | One readonly reviewer per model, same rubric + code-quality lens, lead judgment Act on/Consider/Noted/Dismissed. |
| no-comments | skill | user-only (+routed) | Spawn Comment Sicko, audit its diff, fix accepted flags, offer encodings for constraint comments. |
| tdd | skill | user-only (+routed) | Failing test first only when cheap; else closest executable check. |
| benchmark-checklist | skill | user-only (+routed) | Seven questions to vet a measured number before reporting. |
| figure-it-out | skill | user-only (+routed) | Design a bespoke auditable playbook (frame, workflow, hypothesis loop, trail, verify). |
| show-me-your-work | skill | user-only (+routed) | Append-only `decisions.tsv` trail, transcript audit, cross-model "Attention" review. |
| reflect | skill | user-only | Three reviewers over transcript, synthesizer, structural check, user-approved skill edits. |
| correct | skill | user-only | Mine repeated mistakes, fix each at highest level (architecture > types/lint/CI > tests > docs), keep rule table. |
| automate-me | skill | user-only | Mine transcripts + AskQuestion, draft `<handle>-mode` skill via create-skill + unslop, PR. |
| create-verification-skill | skill | user-only (+offered by setup-pstack) | Generate `.cursor/skills/verify-<app>/` with Launch/Doctor/Drive/Evidence/Cleanup + feature map; prove once. |
| maintain-verification-skill | skill | user-only | Source wave + one live pass over the feature map; ≤1 PR of proven corrections. |
| make-bot-ui | skill | user-only | Local page whose buttons wake a Grok Bot routine over a webhook; Tailscale exposure. |
| unslop | skill | user-only (+routed; "Must always apply") | Numbered AI-tell catalog for any prose. |
| technical-writing | skill | user-only (+routed) | Diátaxis + Google style + STE + Global English for docs, PRs, commits. |
| bro | skill | user-only | Restate last message in plain language. |
| typescript-best-practices | skill | user-only (has `paths: **/*.ts(x)` glob but also disable flag) | TS rules grounding type-system-discipline. |

### Principle skills (24, all user-only, read by name from PM's inline index, reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:38-79)

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| p:laziness-protocol | skill | routed | Smallest change, bias to deletion. |
| p:foundational-thinking | skill | routed | Data structures and scaffold-first sequencing before logic. |
| p:redesign-from-first-principles | skill | routed | Redesign as if requirement were day-one. |
| p:attack-the-premise | skill | routed | After ≥2 same-premise fixes fail one gate, census actors and question the premise. |
| p:subtract-before-you-add | skill | routed | Delete dead weight first. |
| p:minimize-reader-load | skill | routed | Count layers/hidden state; collapse one-caller wrappers. |
| p:outcome-oriented-execution | skill | routed | Converge on target architecture; no throwaway compat states. |
| p:experience-first | skill | routed | User delight over implementation convenience. |
| p:exhaust-the-design-space | skill | routed | 2-3 competing prototypes before committing. |
| p:build-the-lever | skill | routed | Build the tool (codemod/script) that does or proves the work. |
| p:model-the-domain | skill | routed | Encode domain in structure, not scattered conditionals. |
| p:boundary-discipline | skill | routed | Guards at boundaries, pure core. |
| p:type-system-discipline | skill | routed | Illegal states unrepresentable, brand, parse at boundaries. |
| p:make-operations-idempotent | skill | routed | Converge regardless of partial prior runs. |
| p:migrate-callers-then-delete-legacy-apis | skill | routed | Migrate and delete old API in one wave. |
| p:separate-before-serializing-shared-state | skill | routed | Remove sharing before adding locks; one writer per worktree. |
| p:prove-it-works | skill | routed | Verify against the real artifact, not a proxy; script the check. |
| p:fix-root-causes | skill | routed | Reproduce, trace to root, no symptom guards. |
| p:sequence-verifiable-units | skill | routed | Small units each ending in a check; order commits/PRs to prove themselves. |
| p:test-behavior-not-implementation | skill | routed | Call like users, assert literal values; delete tests that pass with undefined imports. |
| p:explain-the-number | skill | routed | Find the limiter before trusting a measurement. |
| p:guard-the-context-window | skill | routed | Bulk to subagents, summaries in main thread. |
| p:never-block-on-the-human | skill | routed | Proceed on reversible work; confirm only irreversible. |
| p:encode-lessons-in-structure | skill | routed | Repeated instruction becomes a lint/flag/check/script. |

### Scripts, references, external dependencies

| id | kind | invocation | one-line purpose |
|---|---|---|---|
| orch (`scripts/orch/orch.ts`) | script | code (Bun CLI called by coordinator) | Plain-file orchestrate store: `unit`, `ledger`, `inbox`, `gate`, `frontier` (via gt), `standing`; never spawns or waits (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:15). |
| watch-pr (`scripts/watch-pr/watch-pr`) | script | code (Bun CLI) | GitHub PR/stack/queued-stack watcher via `gh`; NDJSON verdicts READY/WAITING/ADVANCE/COMPLETE; Bugbot pass counts; `--status-only`. |
| check-plan (`scripts/check-plan.mjs`) | script | code (node) | Lints a multi-phase plan against the skeleton (sub-blocks, verification rule sentence, ten lanes, perf items, program markers). |
| worktree-audit (`scripts/worktree-audit.sh`) | script | code | Read-only table of worktrees: size, age, merged, dirty, PR, last chat, suggested bucket. |
| bootstrap (`scripts/bootstrap.ts`) | script | code | Self-installs pinned deps (commander) for the Bun scripts and re-execs. |
| log.sh (`skills/show-me-your-work/scripts/log.sh`) | script | code | Append a sanitized TSV row to a decision log. |
| bugbot-triage | doc (reference) | read by babysit/autopilot/plan | fix/dismiss/ask rubric + learned skip-pattern registry, grown from babysit sweeps. |
| ext:deslop | external skill (cursor-team-kit) | routed | Strip slop from diff before commit. |
| ext:control-ui / ext:control-cli | external skills (cursor-team-kit) | routed | Drive browser/Electron/web or CLI/TUI for live repro and proof. |
| ext:verify-<app> | project skill (generated) | routed | Project-local launch/doctor/drive/evidence/cleanup + feature map. |
| ext:create-skill | Cursor built-in skill | routed | Author/optimize SKILL.md files. |
| ext:/loop | Cursor built-in command | user/model | Event or heartbeat wake for long runs. |
| ext:AskQuestion | Cursor tool | model | Structured question to the human; PM restricts it. |
| benny | automation pack (dormant) | code (Cursor automations, Slack-triggered) | Triage Slack issue reports to tracker; reproduce confirmed bugs with UI evidence; draft PR only. |

## 3. Edges

### Router (PM) to playbooks, skills, agents

| from | to | relation | evidence (path:line) |
|---|---|---|---|
| user `/poteto-mode` | PM | invokes | reference_harnesses/cursor_plugins/pstack/README.md:34 |
| PM | each pb:* (23) | routes-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:121-147 |
| PM | figure-it-out | routes-to (large/cross-cutting or step-away work, or no playbook fits) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:123 |
| PM | pb:orchestrate | routes-to (standing program) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:123,140 |
| PM | all 24 principle skills | reads (index; cite only leaves read) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:15,38-79 |
| PM | how | routes-to (nontrivial change, "are we sure?") | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:19 |
| PM | pb:prototype | routes-to (AskQuestion fork answerable by observation) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:20 |
| PM | p:model-the-domain | enforces (any code: name data shape) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:21 |
| PM | architect | routes-to (code crossing a function boundary) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:22 |
| PM | swarm, arena | routes-to (parallel fan-out / bakeoffs) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:23 |
| PM | interrogate | routes-to (contested design before shipping) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:24 |
| PM | unslop, ext:create-skill | enforces (any prose; agent-facing prose) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:26 |
| PM | technical-writing | enforces (docs, PRs, commits) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:27 |
| PM | ext:deslop | enforces (before commit) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:28 |
| PM | no-comments | enforces (before review) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:29 |
| PM | ext:control-ui / ext:control-cli | requires (shipping UI/CLI; bug repro) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:30 |
| PM | benchmark-checklist | enforces (any measured number) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:31 |
| PM | pb:babysit | routes-to (any PR-status request; overrides Cursor built-in babysit) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:32 |
| PM | pb:shipping | routes-to (land/ship a green stack) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:33 |
| PM | bugbot-triage | reads (Bugbot/security-review comments) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:34 |
| PM | show-me-your-work | enforces (long/autonomous/step-away work) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:36 |
| PM | poteto-agent | invokes (every subagent in a playbook step) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:93 |
| PM | pstack-models.mdc | reads (model per role) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:95 |
| poteto-agent | PM | reads (in full before work) | reference_harnesses/cursor_plugins/pstack/agents/poteto-agent.md:9 |
| user `/setup-pstack` | setup-pstack | invokes | reference_harnesses/cursor_plugins/pstack/README.md:25 |
| setup-pstack | pstack-models.mdc | produces | reference_harnesses/cursor_plugins/pstack/skills/setup-pstack/SKILL.md:8,39 |
| setup-pstack | create-verification-skill | invokes (offer, on yes) | reference_harnesses/cursor_plugins/pstack/skills/setup-pstack/SKILL.md:75 |
| how, why, arena, swarm, architect, interrogate, reflect | pstack-models.mdc | reads | reference_harnesses/cursor_plugins/pstack/skills/how/SKILL.md:11; reference_harnesses/cursor_plugins/pstack/skills/why/SKILL.md:13; reference_harnesses/cursor_plugins/pstack/skills/arena/SKILL.md:28; reference_harnesses/cursor_plugins/pstack/skills/swarm/SKILL.md:25; reference_harnesses/cursor_plugins/pstack/skills/architect/SKILL.md:33; reference_harnesses/cursor_plugins/pstack/skills/interrogate/SKILL.md:36; reference_harnesses/cursor_plugins/pstack/skills/reflect/SKILL.md:33 |

### Playbook to playbook hand-offs

| from | to | relation | evidence (path:line) |
|---|---|---|---|
| pb:bug-fix | pb:opening-a-pr | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/bug-fix.md:13 |
| pb:feature | pb:opening-a-pr | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/feature.md:17 |
| pb:refactoring | pb:opening-a-pr | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/refactoring.md:14 |
| pb:perf-issue | pb:opening-a-pr | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/perf-issue.md:21 |
| pb:hillclimb | pb:opening-a-pr | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/hillclimb.md:19 |
| pb:visual-parity | pb:opening-a-pr | hands-off-to (per component or batch) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/visual-parity.md:9 |
| pb:authoring-a-skill | pb:opening-a-pr | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/authoring-a-skill.md:8 |
| (all others) | pb:opening-a-pr | hands-off-to (blanket claim) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:3; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:147 |
| pb:investigation | pb:bug-fix / pb:feature | hands-off-to (only if a code change follows; "No PR, no babysit") | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/investigation.md:12 |
| pb:runtime-forensics | pb:bug-fix / pb:perf-issue | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/runtime-forensics.md:11 |
| pb:trace-forensics | pb:bug-fix / pb:perf-issue | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/trace-forensics.md:12 |
| pb:prototype | pb:feature (or architect) | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/prototype.md:7,12 |
| pb:refactoring | pb:feature | routes-to (named redesign / found feature) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/refactoring.md:5 |
| pb:perf-issue | pb:hillclimb | routes-to (sustained metric work) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/perf-issue.md:23 |
| pb:hillclimb | pb:perf-issue | reads (mantra order only) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/hillclimb.md:10 |
| pb:hillclimb | pb:autonomous-run | reads (wake mechanism only) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/hillclimb.md:16 |
| pb:opening-a-pr | pb:babysit | hands-off-to (only on user ask after stack exists, or autopilot owner) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:34,36 |
| pb:babysit | pb:shipping | hands-off-to (land/ship/merge request) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:3,18,25 |
| pb:autopilot-full | pb:babysit | invokes (owner's loop to green) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:6 |
| pb:autopilot-full | pb:shipping | reads (patch-id rule) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:8-9 |
| pb:autopilot-stack | pb:autopilot-full | reads (steps 2, 4, 6 reused) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-stack.md:5-8 |
| pb:autopilot-stack | pb:babysit | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-stack.md:5 |
| pb:autopilot-stack | pb:shipping | reads (patch-id rule) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-stack.md:11 |
| pb:orchestrate | pb:autonomous-run | routes-to (if one agent could finish in budget) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:3,60 |
| pb:orchestrate | pb:babysit | invokes (one babysitter per stack) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:81 |
| pb:multi-phase-plan | pb:prototype | invokes (each open question) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:6 |
| pb:multi-phase-plan | pb:autopilot-full / pb:autopilot-stack / pb:orchestrate | hands-off-to (plan names its execution playbook; starts on operator go) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:8,11 |
| pb:multi-phase-plan | pb:shipping | reads (patch-id rule in merge box) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:66-67 |
| pb:session-pickup | matching pb:* | routes-to | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/session-pickup.md:8 |
| pb:pause-safely | pb:session-pickup | hands-off-to (complement) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:144 |

### Playbook to skill / script / agent

| from | to | relation | evidence (path:line) |
|---|---|---|---|
| pb:opening-a-pr | ext:deslop, no-comments, technical-writing, unslop | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:9 |
| pb:opening-a-pr | interrogate | invokes (subagent that opens a PR) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:36 |
| pb:babysit | watch-pr | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:12 |
| pb:babysit | ext:/loop | requires (dynamic mode for drive/background) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:12 |
| pb:babysit | bugbot-triage | reads; produces (new dismissal patterns as own PR) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:22-23 |
| pb:shipping | ext:control-ui / ext:control-cli | requires (one cloud verifier per PR) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:7 |
| pb:shipping | watch-pr | invokes (`--queued-stack` event wake) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:14 |
| pb:shipping | ext:/loop | requires | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:14 |
| pb:autonomous-run | ext:/loop | requires | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:6 |
| pb:autonomous-run | p:sequence-verifiable-units | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:8 |
| pb:autonomous-run | PM | invokes (mid-run side fixes "via poteto-mode", own PR) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:9 |
| pb:autonomous-run | show-me-your-work | invokes (row per iteration) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:10 |
| pb:orchestrate | orch | invokes (`init`, `inbox push/drain`, `unit add/set`, `ledger record/check`, `status`, `frontier set`) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:15,23,61,70-73,89 |
| pb:orchestrate | show-me-your-work | invokes (decisions.tsv; audit at close) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:31,61,66 |
| pb:orchestrate | arena | invokes (contested decomposition / one-way door) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:60 |
| pb:orchestrate | ext:control-ui / ext:control-cli | requires (local-only verification exception) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:17 |
| pb:orchestrate | p:separate-before-serializing-shared-state, p:encode-lessons-in-structure | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:17,25 |
| pb:autopilot-full | p:prove-it-works, bugbot-triage, ext:deslop, no-comments, show-me-your-work | invokes (owner lifecycle) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:6 |
| pb:autopilot-full | swarm | invokes (verdict per round: gates, live, regression-vs-trunk, ≥2 audit lanes) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:8 |
| pb:autopilot-full | ext:control-ui / ext:control-cli | requires (live lane is the floor) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:8 |
| pb:autopilot-full | ext:/loop | requires (`/loop 1h` audit tick) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:10 |
| pb:autopilot-stack | bugbot-triage, ext:deslop, no-comments, show-me-your-work | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-stack.md:5 |
| pb:multi-phase-plan | poteto-agent | invokes (explorers) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:7 |
| pb:multi-phase-plan | technical-writing, unslop | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:9 |
| pb:multi-phase-plan | check-plan | invokes (fix every printed line) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:10 |
| pb:multi-phase-plan | swarm, ext:control-ui/cli | requires (ten live lanes per PR) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:13,15 |
| pb:multi-phase-plan | p:never-block-on-the-human, p:guard-the-context-window, p:sequence-verifiable-units, p:prove-it-works | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:6,7,8,13 |
| pb:multi-phase-plan | ext:deslop, no-comments, bugbot-triage | invokes (PR mechanics boxes) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:59-60 |
| pb:investigation | how, why, unslop | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/investigation.md:7,10 |
| pb:bug-fix | ext:control-ui / ext:control-cli | requires (repro yourself) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/bug-fix.md:7 |
| pb:bug-fix | how, why | invokes (seed hypotheses) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/bug-fix.md:8 |
| pb:bug-fix | ext:/loop | invokes (long hunt) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/bug-fix.md:8 |
| pb:bug-fix | architect | invokes (if fix crosses function boundary) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/bug-fix.md:9 |
| pb:bug-fix | tdd, p:sequence-verifiable-units | invokes / enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/bug-fix.md:11-12 |
| pb:feature | how, architect | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/feature.md:5-6 |
| pb:feature | p:separate-before-serializing-shared-state, p:model-the-domain | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/feature.md:10,12 |
| pb:feature | arena | invokes (mandatory when multiple valid shapes) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/feature.md:12 |
| pb:feature | p:sequence-verifiable-units | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/feature.md:15 |
| pb:feature | interrogate | invokes (contested design) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/feature.md:16 |
| pb:refactoring | figure-it-out | routes-to (large/cross-cutting) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/refactoring.md:5 |
| pb:refactoring | how, architect | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/refactoring.md:7,9 |
| pb:refactoring | p:model-the-domain, p:foundational-thinking, p:redesign-from-first-principles, p:subtract-before-you-add, p:laziness-protocol, p:migrate-callers-then-delete-legacy-apis, p:prove-it-works, p:minimize-reader-load, p:sequence-verifiable-units | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/refactoring.md:8-14 |
| pb:perf-issue | benchmark-checklist, how, architect | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/perf-issue.md:5,6,17 |
| pb:perf-issue | p:sequence-verifiable-units | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/perf-issue.md:18 |
| pb:hillclimb | how, benchmark-checklist, show-me-your-work | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/hillclimb.md:7,8,9 |
| pb:hillclimb | p:prove-it-works, p:build-the-lever, p:guard-the-context-window, p:separate-before-serializing-shared-state, p:sequence-verifiable-units, p:laziness-protocol | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/hillclimb.md:5,8,12,16,17 |
| pb:prototype | p:exhaust-the-design-space | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/prototype.md:10 |
| pb:prototype | ext:control-ui / ext:control-cli | requires (screenshot variants) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/prototype.md:11 |
| pb:visual-parity | p:separate-before-serializing-shared-state, ext:/loop | enforces / invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/visual-parity.md:7-8 |
| pb:runtime-forensics, pb:trace-forensics | p:guard-the-context-window | enforces (parse artifacts in subagent) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/runtime-forensics.md:6; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/trace-forensics.md:7 |
| pb:authoring-a-skill | ext:create-skill, p:encode-lessons-in-structure | invokes / enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/authoring-a-skill.md:5,10 |
| pb:eval | arena (Phase B candidates, Phase C judge) | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/eval.md:20-21 |
| pb:session-pickup | p:guard-the-context-window, p:prove-it-works | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/session-pickup.md:5,9 |
| pb:pause-safely | show-me-your-work | reads (point at trail) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/pause-safely.md:8 |
| pb:worktree-cleanup | worktree-audit | invokes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/worktree-cleanup.md:5 |
| pb:worktree-cleanup | p:build-the-lever, p:encode-lessons-in-structure, p:prove-it-works, p:guard-the-context-window | enforces | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/worktree-cleanup.md:5-7 |

### Skill to skill

| from | to | relation | evidence (path:line) |
|---|---|---|---|
| architect | how (Phase A, and on scrap), why (if ownership/layering changes) | invokes | reference_harnesses/cursor_plugins/pstack/skills/architect/SKILL.md:23,25,76 |
| architect | arena (Phase B sketch) | invokes | reference_harnesses/cursor_plugins/pstack/skills/architect/SKILL.md:31 |
| architect | interrogate (optional pressure on sketch) | invokes | reference_harnesses/cursor_plugins/pstack/skills/architect/SKILL.md:49 |
| architect | p:exhaust-the-design-space, p:foundational-thinking, p:outcome-oriented-execution, p:redesign-from-first-principles, p:fix-root-causes, p:subtract-before-you-add | enforces | reference_harnesses/cursor_plugins/pstack/skills/architect/SKILL.md:35,49,61,78 |
| arena | p:separate-before-serializing-shared-state, p:redesign-from-first-principles, p:prove-it-works | enforces | reference_harnesses/cursor_plugins/pstack/skills/arena/SKILL.md:29,57,65 |
| figure-it-out | PM (read Principles first) | reads | reference_harnesses/cursor_plugins/pstack/skills/figure-it-out/SKILL.md:13 |
| figure-it-out | architect (one-way doors) | invokes | reference_harnesses/cursor_plugins/pstack/skills/figure-it-out/SKILL.md:30 |
| figure-it-out | show-me-your-work | invokes | reference_harnesses/cursor_plugins/pstack/skills/figure-it-out/SKILL.md:47 |
| figure-it-out | p:prove-it-works, p:never-block-on-the-human, p:foundational-thinking, p:laziness-protocol, p:separate-before-serializing-shared-state, p:sequence-verifiable-units, p:encode-lessons-in-structure | enforces | reference_harnesses/cursor_plugins/pstack/skills/figure-it-out/SKILL.md:19,23,27,30,31,39,51 |
| teach | how, why | invokes (in parallel) | reference_harnesses/cursor_plugins/pstack/skills/teach/SKILL.md:11,14 |
| teach | unslop | enforces | reference_harnesses/cursor_plugins/pstack/skills/teach/SKILL.md:19 |
| recall | pb:session-pickup, automate-me | routes-to (classification) | reference_harnesses/cursor_plugins/pstack/skills/recall/SKILL.md:17 |
| recall | why (source investigators, re-aimed) | invokes | reference_harnesses/cursor_plugins/pstack/skills/recall/SKILL.md:20 |
| recall | unslop | enforces | reference_harnesses/cursor_plugins/pstack/skills/recall/SKILL.md:33 |
| blast-radius | why (step 2 to pull PR/commits) | invokes | reference_harnesses/cursor_plugins/pstack/skills/blast-radius/SKILL.md:33 |
| blast-radius | arena (big/wide change) | invokes | reference_harnesses/cursor_plugins/pstack/skills/blast-radius/SKILL.md:38 |
| blast-radius | unslop | enforces | reference_harnesses/cursor_plugins/pstack/skills/blast-radius/SKILL.md:48 |
| no-comments | Comment Sicko | invokes | reference_harnesses/cursor_plugins/pstack/skills/no-comments/SKILL.md:19 |
| no-comments | how / why (verify IMPORTANT keeps) | invokes | reference_harnesses/cursor_plugins/pstack/skills/no-comments/SKILL.md:20 |
| no-comments | architect (stop at sketch) | invokes | reference_harnesses/cursor_plugins/pstack/skills/no-comments/SKILL.md:21 |
| no-comments | p:fix-root-causes, p:redesign-from-first-principles | reads (intent only) | reference_harnesses/cursor_plugins/pstack/skills/no-comments/SKILL.md:22 |
| Comment Sicko | how, why | invokes | reference_harnesses/cursor_plugins/pstack/agents/comment-sicko.md:26 |
| show-me-your-work | log.sh | invokes | reference_harnesses/cursor_plugins/pstack/skills/show-me-your-work/SKILL.md:38 |
| show-me-your-work | unslop, p:encode-lessons-in-structure | enforces | reference_harnesses/cursor_plugins/pstack/skills/show-me-your-work/SKILL.md:36,53 |
| reflect | ext:create-skill (substantive edits, new skills, description tuning) | hands-off-to | reference_harnesses/cursor_plugins/pstack/skills/reflect/SKILL.md:60-62 |
| reflect | p:encode-lessons-in-structure (move enforceable items to Backlog) | enforces | reference_harnesses/cursor_plugins/pstack/skills/reflect/SKILL.md:49 |
| automate-me | ext:create-skill, unslop | invokes | reference_harnesses/cursor_plugins/pstack/skills/automate-me/SKILL.md:11,67,77 |
| automate-me | PM (shape reference) | reads | reference_harnesses/cursor_plugins/pstack/skills/automate-me/SKILL.md:63 |
| create-verification-skill | ext:verify-<app> | produces | reference_harnesses/cursor_plugins/pstack/skills/create-verification-skill/SKILL.md:25 |
| create-verification-skill | maintain-verification-skill | hands-off-to (offer) | reference_harnesses/cursor_plugins/pstack/skills/create-verification-skill/SKILL.md:44 |
| maintain-verification-skill | create-verification-skill (if no target) | routes-to | reference_harnesses/cursor_plugins/pstack/skills/maintain-verification-skill/SKILL.md:25 |
| technical-writing | unslop | enforces | reference_harnesses/cursor_plugins/pstack/skills/technical-writing/SKILL.md:93 |
| benchmark-checklist | p:explain-the-number | reads | reference_harnesses/cursor_plugins/pstack/skills/benchmark-checklist/SKILL.md:9 |
| benchmark-checklist | pb:opening-a-pr (one number in PR body) | reads | reference_harnesses/cursor_plugins/pstack/skills/benchmark-checklist/SKILL.md:34 |
| typescript-best-practices | p:type-system-discipline, p:boundary-discipline | reads | reference_harnesses/cursor_plugins/pstack/skills/typescript-best-practices/SKILL.md:10,25 |
| p:explain-the-number | benchmark-checklist, p:prove-it-works | reads | reference_harnesses/cursor_plugins/pstack/skills/principle-explain-the-number/SKILL.md:19,23 |
| p:attack-the-premise | p:build-the-lever, p:fix-root-causes, p:laziness-protocol, p:redesign-from-first-principles | reads | reference_harnesses/cursor_plugins/pstack/skills/principle-attack-the-premise/SKILL.md:15-17,23 |
| p:build-the-lever | p:laziness-protocol, p:encode-lessons-in-structure, p:prove-it-works | reads | reference_harnesses/cursor_plugins/pstack/skills/principle-build-the-lever/SKILL.md:21,23 |
| p:prove-it-works | show-me-your-work | reads | reference_harnesses/cursor_plugins/pstack/skills/principle-prove-it-works/SKILL.md:22 |
| p:sequence-verifiable-units | p:prove-it-works, p:build-the-lever | reads | reference_harnesses/cursor_plugins/pstack/skills/principle-sequence-verifiable-units/SKILL.md:17 |
| p:type-system-discipline | p:boundary-discipline, p:encode-lessons-in-structure | reads | reference_harnesses/cursor_plugins/pstack/skills/principle-type-system-discipline/SKILL.md:18,21 |
| p:minimize-reader-load | p:guard-the-context-window | reads | reference_harnesses/cursor_plugins/pstack/skills/principle-minimize-reader-load/SKILL.md:13 |

Skills with no outgoing skill edges (leaf procedures): how, why, swarm, interrogate, tdd, correct, unslop, bro, make-bot-ui, and most principles. how, why, swarm, interrogate, reflect only spawn `generalPurpose` Task subagents with configured models (reference_harnesses/cursor_plugins/pstack/skills/how/SKILL.md:26; reference_harnesses/cursor_plugins/pstack/skills/why/SKILL.md:83; reference_harnesses/cursor_plugins/pstack/skills/swarm/SKILL.md:30; reference_harnesses/cursor_plugins/pstack/skills/interrogate/SKILL.md:45; reference_harnesses/cursor_plugins/pstack/skills/reflect/SKILL.md:31).

## 4. Main lifecycle

Canonical single-task path, Feature shape (bug-fix, refactoring, perf differ only in steps 3-6):

1. **Request arrives** as `/poteto-mode <task>` (PM is sticky afterwards). Optional precondition, run once: `setup-pstack` writes the model rule.
2. **PM matches a playbook** and copies its steps into the todo list verbatim. *Decision (model):* narrow playbook vs `figure-it-out` (large, cross-cutting, or step-away) vs `pb:orchestrate` (multi-day program) vs `pb:autonomous-run`. (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:121-123)
3. `how` over the subsystem (and `why` when rationale matters).
4. `architect`: how → `arena` sketch (3 model families) → *Decision:* optional human checkpoint only if asked (reference_harnesses/cursor_plugins/pstack/skills/architect/SKILL.md:45-47) → optional `interrogate` on the sketch.
5. Throughput checkpoint (4 todo items). *Gate:* any `AskQuestion` impulse is first classified. If an experiment can answer it, run `pb:prototype` instead of asking (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:20).
6. Delegate code to `poteto-agent` on the code model (or `arena` when several shapes are valid), in its own worktree. The parent reviews the diff.
7. Verify on the real surface via `ext:control-ui` / `ext:control-cli` / `ext:verify-<app>`. *Gate:* "inconclusive" or wrong-surface is a fail (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/feature.md:13).
8. Rebase into small ordered commits (`p:sequence-verifiable-units`). *Decision:* contested design → `interrogate`.
9. `pb:opening-a-pr`: `ext:deslop` → `no-comments` (Comment Sicko) → technical-writing + unslop for title/body → resolve forge (`gh` or `origin`) → ready PR (stack child targets parent). Post the URL and keep building the rest of the stack. **No babysit yet.** (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:34)
10. Reply (unslopped, PR link, principles named).
11. *Human decision:* ask for babysit → `pb:babysit` (declare mode; `watch-pr`; conflicts, then threads, then CI; Bugbot triage fix/dismiss/**ask**) → stops at `READY` / merge-ready. *Gate:* owner approval is a wait; babysit never merges (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:23).
12. *Human decision:* "land / ship / merge" → `pb:shipping`: one cloud verifier per PR (PASS / PASS+NOTES / FAIL), contiguous verified run from the bottom, patch-id recheck, retarget, squash-merge or arm `--auto` one PR at a time, recompute after each merge, stop at the ceiling.
13. Done = verified run merged. Optional: `reflect` / `correct` to encode lessons, babysit sweep adds dismissal patterns to `bugbot-triage.md`.

Full-autonomy variant (the "autopilot"): `pb:multi-phase-plan` (plan + `check-plan`; **stop for operator go**) → `pb:autopilot-full` (or `-stack`): one cloud owner per PR runs steps 6-11 itself, the root runs a `swarm` verdict per round at the code-ready SHA, and the owner merges on a clean verdict under the operator's grant (`-stack`: the root appends to a linear stack and the operator lands) → hourly `/loop 1h` audit tick until the queue drains.

## 5. Problem map

| problem id | node(s) used, in order | how it solves it | gap? |
|---|---|---|---|
| P01 understand code | how → (teach) ; pb:investigation; blast-radius | Parallel readonly explorers plus an explainer subagent give a fixed 5-section output; teach builds it up diagram by diagram. | no |
| P02 understand why | why → teach | Code anchor from git blame/log/`gh pr view`, then one investigator per discovered MCP evidence category, then a synthesizer under an epistemics framework that records nulls. | partial (quality depends on MCPs available) |
| P03 clarify requirements with the human | PM AskQuestion classification → pb:prototype; p:never-block-on-the-human; architect Phase C opt-in | Deliberately minimizes asking. Observable forks get a prototype. Only product/preference calls reach the human; under the autonomy grant a default is applied and reported. | yes (no requirements-interview skill; J: by design) |
| P04 design / architecture | architect → arena → interrogate; p:exhaust-the-design-space; pb:prototype | At least 2 structurally distinct multi-model sketches, a cross-judge, base plus grafts, a red-flag screen, and an adversarial review. | no |
| P05 plan / decompose | pb:feature throughput checkpoint; figure-it-out Phase B; pb:multi-phase-plan + check-plan | Checkpoint todos for small work. Bespoke phase list for large work. A linted checklist plan with per-PR evidence boxes for programs. README: "i don't believe in planning" (reference_harnesses/cursor_plugins/pstack/README.md:245). | no |
| P06 implement a feature | pb:feature → poteto-agent / arena → pb:opening-a-pr | Named data shape first. Delegate to the code model with tight scope. Arena when shapes vary. Verify on the real surface. | no |
| P07 fix a bug | pb:bug-fix (control skill repro → how/why → binary search → architect → delegate → tdd) ; p:fix-root-causes; p:attack-the-premise; pb:runtime-forensics | Reproduce on the real surface, eliminate hypotheses with runtime evidence, land the failing repro commit before the fix. | no |
| P08 performance | pb:perf-issue; pb:hillclimb; benchmark-checklist; pb:trace-forensics; pb:runtime-forensics; p:explain-the-number | Baseline trace, ordered mantras, vetted numbers (7 questions), frozen harness with keep/revert loop. | no |
| P09 write tests | tdd; p:test-behavior-not-implementation; pb:refactoring step 1 (characterization pin) | Failing-first only when cheap. Behavior assertions against literal values. Pin before reshaping. | no |
| P10 review code or documents | interrogate; no-comments (Comment Sicko); blast-radius; pb:babysit + bugbot-triage; pb:autopilot-full audit lanes | Multi-model adversarial verdict with lead judgment. Comment purge. Proof of the one safety fact. Skeptical bot triage. | partial (no document-review mode; docs only get technical-writing/unslop) |
| P11 verify / prove done | p:prove-it-works; ext:control-ui/cli; create-/maintain-verification-skill (verify-<app>); pb:shipping verdicts; swarm live lanes; orchestrate ledger | Real-surface proof by an agent that did not write the code. Verdict keyed to head SHA plus patch-id. CI green is "not a verdict". | partial (live driving depends on external cursor-team-kit or a generated verify skill) |
| P12 land / ship | pb:opening-a-pr → pb:babysit → pb:shipping; pb:autopilot-full / -stack | Ready stacked PRs. Watcher-driven babysit to READY. Contiguous verified run landed bottom-up with patch-id rechecks. | no |
| P13 parallel / fan-out | swarm; arena; interrogate; pb:orchestrate; pb:autopilot-full; poteto-agent | Cloud workers per slice/race. Panels across model families. Rolling window of about 10 per drain. One writer per worktree. | no |
| P14 long / unattended runs | pb:autonomous-run + ext:/loop; figure-it-out; pb:autopilot-full/-stack audit tick; pb:orchestrate; show-me-your-work | Checkable predicate, event or heartbeat wake, per-iteration trail, stuck-lane replacement by side-effect test, retry-by-mode, durable store. | no |
| P15 session continuity / context | pb:session-pickup; pb:pause-safely; recall; show-me-your-work; p:guard-the-context-window; orchestrate store + restart recovery | Transcripts and trails are authoritative. `wip:` commit plus resume note. Bulk goes to subagents. Cloud work reattached by PR/branch. | no |
| P16 learn from mistakes | reflect; correct; p:encode-lessons-in-structure; babysit step 9 → bugbot-triage.md; orchestrate close → preferences.md | Transcript-mined learnings routed to approved skill edits. Repeated mistakes fixed at the highest enforcement level with a rule table. | no |
| P17 writing / style | unslop; technical-writing; bro; teach; PM "Writing the reply" | Numbered AI-tell catalog. Layered doc standard. Reply rules: no long dash, no mid-sentence colon, evidence label per claim. | no |
| P18 domain language / glossary / ADRs | — (p:model-the-domain is code structure, not vocabulary; technical-writing "the codebase is the word list", reference_harnesses/cursor_plugins/pstack/skills/technical-writing/SKILL.md:17) | No glossary or ADR artifact. Rationale is recovered after the fact by `why`, not recorded up front. | yes |
| P19 security | bugbot-triage "ask by default" for security/auth/billing/data; babysit escalation; Always-pause list; benny fail-closed | Relies on the external agentic security-review bot plus escalation rules. No pstack security-review skill. | yes (partial) |
| P20 track work / issues | orchestrate `units.tsv`/`overview.md`/`gates.md`; autopilot `children.tsv`; PRs; reflect backlog → team tracker; benny (Slack → tracker) | Work state is PRs plus TSV/markdown files. No issue-tracker integration in the core flow. | partial |
| P21 author / maintain the harness | pb:authoring-a-skill → ext:create-skill; pb:eval; reflect; correct; automate-me; setup-pstack; PM "broken skill mid-task → own PR" (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:35) | Built-in authoring flow plus validation, blinded evals before promotion, transcript-mined edits, personal mode skills. | no |
| P22 prototype / experiment | pb:prototype; p:exhaust-the-design-space; pb:eval; pb:hillclimb | Throwaway scratch variants behind one switcher, observed on the real surface. Prototypes also replace questions to the human. | no |

## 6. Autonomy

### What lets it run without a human, step by step

1. **Grant parsing.** "Don't stop" / "going to bed" / "run until done" / "be fully autonomous" switch on keep-going (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:87). Under a full-autonomy grant, calls the grant covers are decided and reported. Calls only the operator can make get a default plus a plain-words explanation of the alternative (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:20).
2. **Default posture is already autonomous.** Reversible work and external actions (team chat, ticket updates, evals) proceed without asking (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:83). p:never-block-on-the-human: proceed, present, let the human correct (reference_harnesses/cursor_plugins/pstack/skills/principle-never-block-on-the-human/SKILL.md:14). AskQuestion is gated: observable forks become prototypes (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:20). Mid-run discoveries (broken skills, flaky verifiers, review noise) are fixed by the agent in their own PRs, not parked (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:9).
3. **Checkable exit predicate** before iteration 1. A duration is not a predicate (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:5; reference_harnesses/cursor_plugins/pstack/docs/guide/07-overnight.md:79). The predicate is never relaxed and a plateau is not a stop (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:11).
4. **Wake mechanism = Cursor `/loop`.** Event watcher subagent plus a long heartbeat fallback (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:6). PR events come from `watch-pr` NDJSON verdicts, re-armed after each push wave, "never add a second sleep loop" (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:12).
5. **Isolation.** A fresh worktree per run and per parallel agent. One writer per branch (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/opening-a-pr.md:5; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:17).
6. **Self-verification that is not self-report.** p:prove-it-works on the real artifact. A verdict must come "from an agent that did not write the code". CI green and bot approval are not verdicts (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:7). The autopilot swarm runs gates + live + regression-vs-trunk + ≥2 audit lanes, and "a verdict without [the live lane] is not clean" (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:8). In Orchestrate, the verifier runs on a different model family from the worker (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:17).
7. **Merge authority from grant + verdict (autopilot-full only; in autopilot-stack the operator lands, see §6 stops).** "The operator's full-autonomy grant plus the root's clean verdict is the merge authorization that babysitting alone never has" (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:9). Merge only from a freshly rebased head with green CI, a clean `git merge-tree`, no trunk change to touched/CI paths, and a matching patch-id.
8. **Supervision loop.** The root arms `/loop 1h`. Each tick re-reads the playbook from trunk, audits drift, probes owners, counts only side effects (commits, pushes, PR/check deltas) as progress, and replaces stuck lanes at once (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:10). Owners keep `children.tsv` with expected runtimes for the stuck test (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:6).
9. **Program scale (Orchestrate).** Standing orders pasted verbatim into every spawn/resume. Completions are queue events drained at fixed points through `orch`. The ledger is keyed by PR + head SHA. Landing is continuous; spawning stops at ~70% of budget (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:9-11,60,65,89).
10. **Audit trail for morning review.** show-me-your-work `decisions.tsv`, a transcript audit, and a cross-model "Attention" section (reference_harnesses/cursor_plugins/pstack/skills/show-me-your-work/SKILL.md:55-74).

### Where it must stop for a human

- Always-pause irreversible writes: force-push to shared branches, deploys, data deletion, customer messages (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:85). Orchestrate adds closing someone else's PR, product/preference calls, a standing order contradicted by reality, and program-level dead ends. These are parked in `gates.md` with a default and batched (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:105).
- Operator gates the operator names (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:20). Operator-named items stop at merge-ready for the operator's click (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:5,9).
- State-then-wait: a request to state the plan is not a go (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:5; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-stack.md:7; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:11,34).
- Interaction-changing PRs in a plan are review-gated: screenshots plus a 30-60 s video, wait for the click (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:13,120-124).
- Merging outside autopilot needs an explicit "merge / land / ship / merge when ready" (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:18,23). Autopilot-stack never merges; the operator lands (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-stack.md:9,12).
- Bugbot `ask` class: novel, high-severity, security/privacy/data, migrations (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/references/bugbot-triage.md:11,75-82). Babysit escalates "security, auth, billing, data, or migrations" rather than dismissing them (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:22).
- A conflict needing a rebase is reported, not resolved, inside a babysit (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:11).
- Skill edits from `reflect` wait for explicit approval (reference_harnesses/cursor_plugins/pstack/skills/reflect/SKILL.md:53). Constraint-comment encodings in `no-comments` wait for approval; unattended runs need caller pre-approval (reference_harnesses/cursor_plugins/pstack/skills/no-comments/SKILL.md:23).
- `wip:` worktrees and in-use worktrees pause before deletion (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/worktree-cleanup.md:8). A wrong-looking visual-parity baseline: stop and ask (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/visual-parity.md:6).
- Bug repro handed to the user only with a specific reason the control surface cannot reach it (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/bug-fix.md:7).
- Genuine dead end: surface it rather than spin (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:11).
- Stand-down: the operator's stop reaches every owner as an immediate zero-writes order (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:11).
- Root countersign (not human) for a new raise of a pinned gate/budget value. The root never bypasses a forge-enforced approval (reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:10).

### Failure and recovery mechanisms

| Mechanism | Evidence |
|---|---|
| Keep-or-revert per iteration; "might help" changes are reverted | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autonomous-run.md:7; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/hillclimb.md:14 |
| CI: classify before retrigger; one fresh build for flake; identical second failure → reclassify; stale base checked with `git merge-base --is-ancestor` | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/babysit.md:21 |
| watch-pr query-error budget (`--max-query-errors`, default 5) and optional timeout | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/scripts/watch-pr/cli.ts:117-128 |
| Verdict invalidation by patch-id; rebuild twice at verdict SHA to separate noise; re-run CI/mergeability at new head | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:9 |
| Contiguous-run landing: stop at the first unverified PR; recompute after every merge; hard-fail conditions enumerated | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/shipping.md:8,13-14 |
| Swarm: drop results missing SHAs/method, respawn once, then record a gap (gap ≠ pass) | reference_harnesses/cursor_plugins/pstack/skills/swarm/SKILL.md:40 |
| Arena/swarm dropout: proceed with N-1 and note it | reference_harnesses/cursor_plugins/pstack/skills/arena/SKILL.md:37; reference_harnesses/cursor_plugins/pstack/skills/swarm/SKILL.md:36 |
| Stuck-lane test by side effects + expected runtime; immediate replacement; "a stall never proves or drops the work" | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/autopilot-full.md:10 |
| Orchestrate retry-by-mode (cap/oom → smaller scope; network → as-is; tool-error → other model; unknown → once; two retries then abandon and replan) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:97 |
| Synthetic postmortem row for silent deaths; zombie reconciliation against frontier + ledger | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:96,98 |
| Tree-wide stop line in standing orders; bounded own-infra retries → terminal handoff to durable state | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:99-100 |
| Cursor restart recovery: cloud work survives; reattach by PR/branch; `orch` lock replaced if holder pid gone | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:101 |
| Ledger as source of truth for "was this verified" (`verifier-blocked` ≠ pass; `verifier-failed` → fix unit; new SHA voids row) | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:89 |
| Fresh subagent with consolidated scope for every fix round/retry; never interrupt-chained resumes | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/SKILL.md:99; reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/orchestrate.md:56 |
| Pause safely: safe boundary, `wip:` commit, resume note at `/tmp/<slug>-resume.md` | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/pause-safely.md:5-8 |
| Append-only trail; supersede wrong rows; cross-model trail review | reference_harnesses/cursor_plugins/pstack/skills/show-me-your-work/SKILL.md:52,63,67 |
| attack-the-premise after two same-premise failures; architect "scrap" on repeated friction | reference_harnesses/cursor_plugins/pstack/skills/principle-attack-the-premise/SKILL.md:3; reference_harnesses/cursor_plugins/pstack/skills/architect/SKILL.md:59-79 |
| Plan lint: `check-plan.mjs` prints every structural defect | reference_harnesses/cursor_plugins/pstack/skills/poteto-mode/playbooks/multi-phase-plan.md:10 |

### Judgement notes for reproducing "pstack full autonomy" elsewhere

- J: The minimum infrastructure for the autopilot path is a GitHub repo with PR CI, the `gh` CLI, a parallel worker runtime with isolated checkouts (cloud agents or worktrees), a heartbeat/wake primitive (`/loop`), a live-drive verification skill per surface, and at least two model families. Bugbot / security-review bots are inputs, not requirements. Without them babysit's thread triage is a no-op.
- J: The harness enforces nothing in code. There are no hooks and no gate engine. Every stop rule is prose the model must obey. The only deterministic pieces are `watch-pr` (PR state), `orch` (bookkeeping), `check-plan` (plan structure), and `worktree-audit`. Ledgers and trails are append-by-convention.
- J: Internal inconsistencies to resolve before adopting: Orchestrate needs `gt` while every other playbook forbids requiring it; "opening-a-pr at the end of every playbook" vs read-only playbooks; README calls Comment Sicko read-only though it deletes comments; benny opens draft PRs against the "never draft" rule; audit ticks hard-code `origin/main:pstack/...`; the Autonomy section allows team-chat posts without asking while p:never-block-on-the-human lists external messages as needing confirmation.
