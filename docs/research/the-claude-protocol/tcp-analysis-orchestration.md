# The-Claude-Protocol — orchestration core: curation analysis

Subject: `reference_harnesses/The-Claude-Protocol` @ `af754ef` (2026-02-06, npm
`beads-orchestration` v2.2.0 — `package.json:3`). Read-only inspection; nothing
under `reference_harnesses/` was modified.

Citation convention: `path:line` is relative to the submodule root
`reference_harnesses/The-Claude-Protocol/` unless it starts with `.claude/`,
`.beads/`, or `harness_lifecycle/`, which are ours.

**Verified upstream-contract facts** used throughout §2–§3 come from the Claude Code
hooks documentation (https://code.claude.com/docs/en/hooks.md), retrieved this
session via the `claude-code-guide` agent:

- Hook input is **JSON on stdin only**. There is **no documented `CLAUDE_TOOL_INPUT`
  env var**; documented hook env vars are `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT`,
  `CLAUDE_PLUGIN_DATA`, `CLAUDE_EFFORT`, `CLAUDE_CODE_REMOTE`,
  `CLAUDE_CODE_BRIDGE_SESSION_ID`.
- Plain-text stdout on exit 0 is added to the model's context **only** for
  `UserPromptSubmit`, `UserPromptExpansion`, `SessionStart`. For other events
  (including `PreToolUse`) it is debug-logged only.
- `PostToolUse` honored JSON fields: `systemMessage`, `additionalContext`,
  `terminalSequence`, `continue`. `hookSpecificOutput` is **not documented** for
  `PostToolUse`.
- `SubagentStop` input carries `agent_id`, `agent_type`, `last_assistant_message`,
  `transcript_path` — **no documented `agent_transcript_path`**. Blocking is
  `continue:false` or exit 2 + stderr; `{"decision":"block"}` is **not documented**
  for `SubagentStop`.

I flag below where those facts collide with TCP's implementation. Where the doc
contract may lag actual runtime behaviour I say so rather than asserting.

---

## 1. What the framework actually is

**Architecture (fact, from the files).** TCP is an installer plus a template set that
converts a repo into a single-orchestrator / many-supervisor delegation system anchored
on the `bd` (beads) CLI. `bootstrap.py` installs the `bd` binary (brew → npm → curl →
go, `bootstrap.py:231-278`), runs `bd init`, registers a custom bead status `inreview`
(`bootstrap.py:316-327`), then copies 7 core agents to `.claude/agents/`
(`bootstrap.py:442-499`), 14 hooks to `.claude/hooks/` (`bootstrap.py:541-573`), a
`settings.json` wiring all 14 (`bootstrap.py:580-598`, `templates/settings.json`), a
`CLAUDE.md` orchestrator persona (`bootstrap.py:607-619`), a knowledge store
`.beads/memory/knowledge.jsonl` + `recall.sh` (`bootstrap.py:346-365`), and `.beads/` +
`.mcp.json` gitignore entries (`bootstrap.py:626-672`). The installed `CLAUDE.md`
declares the session-level Claude to be an **orchestrator that never writes code**
(`templates/CLAUDE.md:13-18`): it investigates with Read/Grep/Glob, must read the actual
source before delegating (`templates/CLAUDE.md:49-66`), creates a bead, and dispatches
via `Task(subagent_type="<tech>-supervisor", prompt="BEAD_ID: …")`
(`templates/CLAUDE.md:74-81`). **Supervisors** are not shipped: a `discovery` agent
detects the stack, WebFetches third-party specialist agents from
`sub-agents.directory`, strips their code examples, prepends a beads-workflow snippet,
and writes them into `.claude/agents/` with a mandatory `-supervisor` filename suffix
(`templates/agents/discovery.md:39-80, 83-107, 152-183, 256-270`). Each supervisor
creates its own git worktree at `.worktrees/bd-{BEAD_ID}` on branch `bd-{BEAD_ID}`,
implements there, commits, pushes, comments the bead, sets status `inreview`, and emits
a fixed completion report (`templates/beads-workflow-injection-git.md:9-100`).
Cross-domain work becomes a bead **epic** with dot-suffixed children carrying `--deps`,
optionally governed by an architect-written design doc under `.designs/`
(`SKILL.md:215-249`). **Enforcement** is meant to come from hooks at five lifecycle
events (`templates/settings.json:3-79`): pre-dispatch checks (bead present, bead not
closed, blockers resolved, design doc exists), pre-edit branch/worktree checks, a
pre-`bd close` epic gate, post-dispatch auto-logging of the dispatch prompt onto the
bead, and a `SubagentStop` completion validator. The human merges every PR; the
orchestrator never merges (`templates/beads-workflow-injection-git.md:102-107`).

**Judgment: the enforcement claim is substantially overstated.** README:39/121 claims
"13 hooks that physically block bad actions … They don't warn — they block." Measured
against the documented hook contract, **four** hooks reliably deny
(`block-orchestrator-tools.sh`, `enforce-bead-for-supervisor.sh`,
`enforce-sequential-dispatch.sh`, `enforce-branch-before-edit.sh`), a fifth denies only
via a fallback path (`block-branch-for-epic-child.sh`), and the two most-advertised
gates — `validate-completion.sh` (SubagentStop) and `validate-epic-close.sh` (bd close)
— are built on undocumented input/output mechanisms and are structured to **fail open**.
Details in §2.

---

## 2. Component inventory

### 2.1 Agents (7 — all copied by `bootstrap.py:464-468`; `CORE_AGENTS` at `bootstrap.py:42`)

| Agent | Model | Tools | Mechanism (one line) |
|---|---|---|---|
| `scout` | haiku (`templates/agents/scout.md:4`) | Read/Glob/Grep/LSP (`:5-9`) | Read-only locator: find files, map structure, report `EXPLORATION/FINDINGS/SUMMARY/RECOMMENDED_ACTION` (`:78-92`); explicitly forbidden to edit or decide architecture (`:34-39`). |
| `detective` | opus (`templates/agents/detective.md:4`) | +Bash, playwright, context7 (`:5-12`) | Read-only root-cause analysis; fixed report with `ROOT_CAUSE` and `EVIDENCE` as `file:line` (`:74-93`); must not fix (`:37-41`). |
| `architect` | opus (`templates/agents/architect.md:4`) | Read/Glob/Grep + context7/github (`:5-10`) | Produces a design doc (Overview/Requirements/Constraints/Design/API Contracts/Tasks) that epic children treat as contract (`:70-93`); no Write tool — so it **cannot write the `.designs/` file** that `enforce-sequential-dispatch.sh:55-57` demands exist (see §2.3 note). |
| `scribe` | haiku (`templates/agents/scribe.md:4`) | Read/Write/Edit/Glob (`:5-9`) | Docs-only writer; banned from application code (`:43-48`). |
| `code-reviewer` | **haiku** (`templates/agents/code-reviewer.md:5`) | Read/Glob/Grep/Bash (`:5-9`) | 3-phase gate: Phase 0 **re-runs the implementer's DEMO commands** and fails on mismatch (`:42-85`), Phase 1 spec compliance (`:87-101`), Phase 2 quality (`:103-116`); verdict APPROVED / NOT APPROVED written back as a `bd comment` (`:118-131, 154-158`); anti-rubber-stamp rules demand file:line evidence (`:185-211`). |
| `discovery` | sonnet (`templates/agents/discovery.md:4`) | +Write, Bash, **WebFetch** (`:5-12`) | Stack-detection tables → WebFetch third-party agent markdown → filter out code blocks >3 lines (`:109-148`) → prepend `.claude/beads-workflow-injection.md` (+ UI constraints + RAMS/WIG requirement for frontend) → write `.claude/agents/<x>-supervisor.md` with `tools: *` (`:152-183, 338-391`). |
| `merge-supervisor` | opus (`templates/agents/merge-supervisor.md:4`) | Read/Write/Edit/Bash/Glob/Grep (`:5-12`) | Conflict-resolution protocol: read full files not just markers, classify Independent/Overlapping/Contradictory, remove all markers, run tests (`:48-82`); exempt from the BEAD_ID requirement (`templates/hooks/enforce-bead-for-supervisor.sh:22`). |

### 2.2 Hooks — the 5 that work as intended

| Hook | Event / matcher | Matches on | Block or nudge |
|---|---|---|---|
| `block-orchestrator-tools.sh` | PreToolUse, **no matcher** — fires on every tool (`templates/settings.json:3-8`) | tool_name; exits early for `Task` (`:12`) and for detected subagent contexts (`:20-30`) | **Block + ask.** Edit/Write on `main`/`master` → `permissionDecision:deny` (`:69-74`); on a feature branch → `permissionDecision:ask` with file name and estimated change size (`:78-96`); `.worktrees/`, `.claude/plans/`, `CLAUDE.md`, `git-issues.md`, memory paths are allowlisted (`:32-63`); `NotebookEdit` hard-denied (`:99-105`); `bd create` without `-d`/`--description` denied (`:154-161`); `git commit --no-verify` denied (`:136-143`). |
| `enforce-bead-for-supervisor.sh` | PreToolUse:Task (`settings.json:9-12`) | `subagent_type =~ supervisor`, minus `merge-supervisor` (`:18-22`) | **Block.** Prompt lacking `BEAD_ID:` → deny with a remediation script (`:25-30`). |
| `enforce-sequential-dispatch.sh` | PreToolUse:Task (`settings.json:13`) | supervisor dispatches carrying a `BEAD_ID:` (`:19-26`) | **Block, three rules.** Bead already `closed`/`done` → deny, instructing `bd create` + `bd dep relate` (`:29-35`); epic child (id contains a dot) with unresolved non-parent deps → deny listing blockers (`:38-50`); epic whose `design` field names a file that doesn't exist → deny with a stop-and-think + AskUserQuestion branch (`:53-60`). |
| `enforce-branch-before-edit.sh` | PreToolUse:Edit **and** :Write (`settings.json:18-29`) | file_path / cwd not under `.worktrees/`, current branch is `main`/`master` (`:19-40`) | **Block.** Deny with "supervisors must work in worktrees" and a Kanban-API worktree recipe (`:41-49`). Note this duplicates the `block-orchestrator-tools.sh` main-branch deny for the orchestrator; its distinct job is catching supervisors that left their worktree. |
| `clarify-vague-request.sh` | UserPromptSubmit (`settings.json:66-71`) | raw prompt length: `<50` chars, `<200` chars (`:12, 25`) | **Nudge (effective).** Injects a `<system-reminder>` ordering AskUserQuestion before any work, plus an unconditional "cross-domain = epic" reminder on every single prompt (`:34-38`). UserPromptSubmit stdout **is** added to context, so this one lands. Judgment: a raw character count is a crude ambiguity proxy — "revert the last commit on main" (34 chars) is unambiguous and would be gated; a 250-char rambling request would not. |
| `session-start.sh` | SessionStart (`settings.json:59-64`) | n/a | **Nudge (effective).** Warns on a dirty main worktree (`:22-30`), suggests cleanup for worktrees whose branch is merged (`:35-48`), lists open PRs via `gh` (`:53-60`), prints `bd list --status in_progress` / `bd ready` / `bd blocked` / `bd stale --days 3` (`:66-101`), then the 5 most recent dedup'd knowledge entries with a `recall.sh` pointer (`:106-119`). SessionStart stdout **is** context-added. |

### 2.3 Hooks — side-effect hooks (work regardless of output contract)

| Hook | Event / matcher | Matches on | Mechanism |
|---|---|---|---|
| `log-dispatch-prompt.sh` | PostToolUse:Task, timeout 10 (`settings.json:37-43`) | `subagent_type` contains `supervisor` and prompt contains `BEAD_ID:` (`:20-28`) | **Side effect, no block.** Runs `bd comment "$BEAD_ID" "DISPATCH_PROMPT […]: <first 2048 chars>"`, errors swallowed (`:30-37`). This is the single most valuable mechanism in the framework: the exact instruction given to a worker becomes a durable, greppable tracker artifact with zero agent cooperation required. |
| `memory-capture.sh` | PostToolUse:Bash, timeout 10 (`settings.json:45-50`) | executed command matches `bd comment` **and** `LEARNED:` (`:20-21`) | **Side effect.** Parses bead id + comment body out of the command string, keyword-tags the content against a hardcoded 30-term list (`:56-64`), appends a JSON line to `.beads/memory/knowledge.jsonl`, and rotates at 1000 lines by archiving the oldest 500 (`:95-102`). Fragile: the body is recovered by regex over the shell command (`:28`), so a heredoc, a `$(…)`, or a differently-quoted comment silently yields nothing. |
| `nudge-claude-md-update.sh` | PreCompact (`settings.json:73-79`) | `## Current State` section of `CLAUDE.md` empty vs non-empty (`:17-19`) | **Nudge.** Prints one of two reminder texts to update `CLAUDE.md` before compaction. Whether PreCompact stdout reaches the model was not in the doc facts I verified — treat its effectiveness as unconfirmed. |

### 2.4 Hooks — the 5 that are broken, no-ops, or advisory-only

| Hook | Event / matcher | Intended | Actual (with evidence) |
|---|---|---|---|
| `validate-completion.sh` | SubagentStop (`settings.json:52-57`) | The flagship gate: for supervisors, verify completion format, a `bd comment` was made, the worktree exists, no uncommitted changes, branch pushed, bead status `inreview`, response ≤15 lines / ≤800 chars (`:53-129`) | **Almost certainly a no-op.** Line 7 reads `.agent_transcript_path`; per the documented SubagentStop input that field does not exist (`agent_id`, `agent_type`, `last_assistant_message`, `transcript_path` do). Line 11 then **fails open**: `[[ -z "$AGENT_TRANSCRIPT" … ]] && echo '{"decision":"approve"}' && exit 0`. Separately its blocking output `{"decision":"block","reason":…}` is not a documented SubagentStop output (documented: `continue:false`, or exit 2 + stderr). Two independent failure modes, both silent. Layer-1 subagent-type detection additionally greps the raw session transcript for `"agentId"` / `parentToolUseID` (`:21-29`) — undocumented internal file layout. |
| `validate-epic-close.sh` | PreToolUse:Bash (`settings.json:30-35`) | Deny `bd close` when the branch has no merged PR (`:34-55`) or when an epic still has open children (`:57-81`); `--force` overrides (`:23-25`) | **No-op.** Line 8 reads `TOOL_INPUT="${CLAUDE_TOOL_INPUT:-}"` — an env var Claude Code does not set. Line 11 then exits 0 (allow) because `jq -e '.command'` fails on empty input. Corroborating internal evidence: **every other** template hook reads `INPUT=$(cat)` from stdin; this is the only one that doesn't. Their own test drives it the same wrong way — `tests/test-validate-epic-close.sh:37` runs `CLAUDE_TOOL_INPUT="$tool_input" … bash "$HOOK"` — so the test suite passes while the hook never fires in production. This is a textbook case of a test that validates the mock, not the integration. |
| `remind-inprogress.sh` | PreToolUse:Task (`settings.json:14`) | Remind the orchestrator to set `bd update … --status in_progress` before dispatch (`:10-12`) | **Never reaches the model.** Plain-text stdout on a PreToolUse hook is debug-logged only, not context-added. |
| `inject-discipline-reminder.sh` | PreToolUse:Task (`settings.json:15`) | Inject `<system-reminder>` telling the supervisor to invoke `/subagents-discipline` (`:19-26`) | **Never reaches the model**, same reason. Harmless in practice only because the same instruction is duplicated inside the injected workflow (`templates/beads-workflow-injection-git.md:39-42`). |
| `enforce-concise-response.sh` | PostToolUse:Task (`settings.json:41`) | Warn when a subagent's Task result exceeds 10 lines / 500 chars (`:24-37`) | **Ignored.** Emits `hookSpecificOutput.warning`, which is undocumented for PostToolUse (honored fields: `systemMessage`, `additionalContext`, `terminalSequence`, `continue`). Also self-described as advisory: "PostToolUse can't deny" (`:29`). Would have been a one-word fix to `systemMessage`. |
| `block-branch-for-epic-child.sh` (repo's own, not templated — `bootstrap.py` never copies it; wired only in TCP's own `.claude/settings.json:5-12`) | PreToolUse:Bash | Deny `git checkout -b` / `switch -c` / `branch <name>` for epic children, forcing them onto the shared `bd-{EPIC_ID}` branch (`:53-63`) | **Half-broken.** Primary detection reads `.conversation_context` from hook input (`:26`) — not a field Claude Code supplies. Falls back to parsing the current branch name for `bd-<id>` (`:37-42`); if neither yields an id it exits 0 (`:45`). So it fires only when the agent is *already* on a `bd-*` branch whose id contains a dot. |

### 2.5 Supporting templates

- `templates/beads-workflow-injection-git.md` / `-api.md` — the worker contract injected
  into every generated supervisor. Identical except worktree creation: `-api` POSTs to
  `http://localhost:3008/api/git/worktree` with a git fallback (diff of `:9-24`), `-git`
  uses `git worktree add` directly. `bootstrap.py:472-478` picks one based on
  `--with-kanban-ui` and writes it as `.claude/beads-workflow-injection.md`.
- `templates/beads-workflow-injection.md` — **dead file**; `bootstrap.py` never copies it
  (only the `-api`/`-git` variants at `:473, 476`). It differs by making the `LEARNED:`
  comment mandatory and claiming the SubagentStop hook verifies it (`:74-77, 102`) —
  a claim `validate-completion.sh` does not implement (its Check 2 at `:67` greps only
  for `bd comment`, any content).
- `templates/ui-constraints.md` — 76 lines of Tailwind/React MUST/NEVER rules; injected
  into frontend supervisors only (`discovery.md:216-218`).
- `templates/frontend-reviews-requirement.md` — mandates RAMS + Web-Interface-Guidelines
  skill runs before `inreview` and claims "Failure to run BOTH reviews … will BLOCK your
  completion via SubagentStop hook" (`:60`). **False**: no hook reads
  `.claude/frontend-supervisors.txt` (grep across `templates/hooks/` and `.claude/`
  returns nothing), and `validate-completion.sh` contains no RAMS/WIG check.

---

## 3. Head-to-head vs our harness

### 3.a Hook-enforced discipline vs our prompt-stated rules

Our enforcement surface is three hooks (`.claude/settings.json`): `block-dangerous-commands.sh`
(PreToolUse:Bash — git destroyers, `--no-verify`, `bd init --force/--reinit`, recursive
`rm` outside `/tmp`, shell writes to generated mirrors; `:19-87`),
`block-generated-edits.sh` (PreToolUse:Write|Edit — hand-edits to bd-generated mirrors;
`:23-26`), and two SessionStart context injectors (`bd-prime.sh`,
`harness-staleness-nudge.sh`). All read stdin JSON and block with exit 2 + stderr —
mechanisms the documented contract honors.

**Where their hooks would genuinely catch failures our rules only ask for** (judgment,
restricted to their 4–5 working hooks):

1. **`enforce-bead-for-supervisor.sh` — dispatch without a tracked work item.** Our
   execution skill says work is anchored in bd (`execution/SKILL.md:27-31`) and that the
   coordinator claims the stage before implementing (`:76-77`), but nothing stops a
   dispatch of the `implementer` agent with no bead id in the brief. A PreToolUse:Task
   deny would. **This is a real gap, and it is cheap to close.**
2. **`enforce-sequential-dispatch.sh` closed-bead guard (`:29-35`).** Our `beads.md:56-57`
   treats closed issues as the durable rejection record but has no mechanism preventing
   a re-claim or re-dispatch against a closed id. Their deny message even prescribes the
   correct recovery (`bd create` + `bd dep relate`). **Real gap.**
3. **`enforce-sequential-dispatch.sh` blocker check (`:38-50`).** Weaker case for us: our
   execution skill selects work through `bd ready --parent <epic>` (`execution/SKILL.md:76-77`),
   which is dependency-truth by construction. Their hook exists because their orchestrator
   is instructed to dispatch from human judgment. Marginal for us.
4. **`block-orchestrator-tools.sh` `bd create` description check (`:154-161`).** Our
   `ready-for-agent` gate (`beads.md:52-54`) requires acceptance criteria + current/desired
   behaviour and is enforced entirely by an agent reading a prose gate. A mechanical
   floor would help — but see §4 risk: our `idea` flow deliberately creates one-line
   beads with no `-d` (`beads.md:38-39`), so their exact rule would misfire.
5. **`validate-epic-close.sh` epic-children check.** Conceptually the strongest match to
   a gap of ours — our identical gate exists as prose plus a jq snippet the agent is
   asked to run (`execution/SKILL.md:89-93`). Theirs is broken (§2.4), but the *idea*
   ports. **Real gap.**

**Where their hooks would buy us nothing**: `enforce-branch-before-edit.sh` and the
main-branch deny in `block-orchestrator-tools.sh` presuppose worktree-per-task, which we
do not use (our review model explicitly packages the **working tree** because implementers
don't commit — `task-engine.md:53-58`). `clarify-vague-request.sh`'s length heuristic
would fire constantly on our short slash-command invocations.

### 3.b Orchestrator-context protection vs our delegation rule

**Their mechanism**: `block-orchestrator-tools.sh` denies the session-level agent every
write tool outside a small allowlist, with subagent detection to exempt workers
(`:20-30`) and a `permissionDecision:ask` escape hatch on feature branches
(`:78-96`). Plus `enforce-concise-response.sh` (10 lines / 500 chars) and
`validate-completion.sh` Check 7 (15 lines / 800 chars) intended to cap what a worker's
report costs the orchestrator's context.

**Our mechanism**: `.claude/rules/core/01-delegation.md` states the coordinator/worker
split as policy; `task-engine.md:228-234` caps the dispatch prompt ("only the files and
spec sections the task needs") and the result ("short status contract inline … Full file
contents never enter the coordinator"); `task-engine.md:86-89` forbids pasting prior-task
history because "everything pasted stays resident in your context."

**Assessment (judgment).** Their tool-level block is the stronger mechanism *for their
design*, and it is genuinely enforced — it is the one place where TCP's "enforcement not
suggestions" claim holds. But it is a poor fit for us and, on its own terms, leaky:

- It contradicts our Working Mode, which explicitly routes `small` tasks to inline
  execution (`CLAUDE.md` §Working Mode; `execution/SKILL.md:36`). A blanket write-deny
  would force every typo fix through the "quick fix" ask-prompt — which is exactly the
  ceremony our harness is designed to avoid.
- Their context-cap hooks are the two that don't work (§2.4). So the half of orchestrator
  protection that matters most for long sessions — bounding what comes *back* — is
  unenforced, and ours is prose-only too. Neither harness actually enforces it; ours at
  least states a richer contract (`task-engine.md:230-234`).
- Their `git` allowlist has no default-deny arm: `case "$SECOND_WORD"` at `:128-146`
  matches read-ish verbs and `commit`, and everything else falls through to `exit 0`
  at `:167`. **`git push --force`, `git reset --hard`, and `git clean -fd` are all
  permitted by their orchestrator hook** — commands our `block-dangerous-commands.sh:19-29`
  blocks outright. Their "sequential dispatch" enforcement is likewise narrower than the
  name suggests: it enforces *dependency order*, not one-at-a-time; there is no hook
  preventing concurrent Task calls, and their own docs disagree about whether parallel
  dispatch is allowed (see §3.d).

**Also a real defect in their allowlist**: the `--no-verify` check is
`[[ "$COMMAND" == *"-n"* ]]` (`:138`), an unanchored substring. `git commit -m "add
--dry-run flag"` is denied. Our equivalent uses a fixed-string list including
`"--no-verify"` (`block-dangerous-commands.sh:28`) with the same false-positive class
avoided by matching the full flag.

### 3.c `validate-completion` / `validate-epic-close` vs our verification skill

Set aside that both are broken (§2.4) and compare the **designs**, which is the fair
comparison:

| Dimension | TCP | Ours |
|---|---|---|
| What is checked | Process artifacts: worktree exists, working tree clean, branch on remote, bead status == `inreview`, response length (`validate-completion.sh:76-129`) | Claims vs evidence: a claim→command table binding "tests pass", "lint clean", "build succeeds", "bug fixed", "agent completed", "requirements met" each to its own fresh command output (`verification-before-completion/SKILL.md:29-39`) |
| Do tests factor in | **No.** "Tests: pass" is a literal line in the template the worker fills in (`beads-workflow-injection-git.md:98`); nothing re-runs or parses it | Yes — the named test command with 0 failures, in the same message as the claim (`:31, :14-24`) |
| Trusting the agent's report | Structurally trusts it: the completion report is regex-matched for shape (`validate-completion.sh:32-33, 54-59`) | Explicitly distrusts it: "Agent/subagent completed" requires the diff, not the report (`:37`); "The agent said success → Reports are claims; the diff is evidence" (`:61`) |
| Where the teeth are | A hook (deterministic, but only for what a hook can see) | A skill (semantic, but only as strong as the agent's compliance) |
| Epic/phase close gate | `validate-epic-close.sh:57-81` — deny close while children are open, plus a merged-PR requirement | `execution/SKILL.md:89-96` — the same children-closed jq check, stated as prose the agent runs, plus the roadmap exit criterion and the verification skill |

**Verdict (judgment).** Ours is the better *specification* of completion and theirs is
the better *delivery mechanism*, and the two are almost perfectly complementary. Their
gate can only ever check bookkeeping — a hook cannot know whether the right test was
run. Our gate can check meaning but evaporates the moment an agent skips the skill.
The genuinely borrowable idea is narrow: **make the mechanically-checkable subset of our
gate mechanical.** The epic/phase children-closed check is exactly that subset — it is
a pure `bd` query with a boolean answer, currently living in prose where an agent under
context pressure can skip it.

Note also their merged-PR requirement (`validate-epic-close.sh:34-55`) is
out-of-scope for us: `beads.md:20-22` withholds commit/push authority by default, so
gating a bead close on a merged PR would deadlock our normal flow.

### 3.d Where our design is clearly stronger (mechanism-level)

1. **Review depth and loop termination.** Our `code-review` skill defines four modes with
   bound sections and required inputs (`code-review/SKILL.md:17-22`), a mechanical
   preflight that bounces red gates *before* judgment is spent (`:26-33`), evidence
   discipline including read-only-checkout rules (`:37-70`), severity calibration with a
   plan-mandated escape (`:154-173`), and an explicit re-review contract (`:175-185`).
   Around it, `task-engine.md:141-184` specifies a **bounded 5-round fix loop** with a
   precise definition of what consumes a round (`:143-146`), model escalation at rounds
   4–5 (`:150-155`), and an adjudication breaker with three rulings. TCP has none of
   this: `code-reviewer.md:181-182` ends at "ORCHESTRATOR ACTION REQUIRED: Return to
   supervisor with these issues. Re-review after fixes." — no cap, no ledger, no
   adjudication, no defined re-review scope. Their loop can spin forever.
2. **Reviewer model allocation.** TCP pins the adversarial gate to **haiku**
   (`code-reviewer.md:5`) while giving opus to `architect`, `detective`, and
   `merge-supervisor`, and `tools: *` + sonnet to implementers
   (`discovery.md:160-168`). The cheapest model in the fleet guards the most
   judgment-heavy step. Ours requires the model be named on every dispatch and reserves
   strong models for initial reviews (`task-engine.md:21-24`).
3. **Two-verdict review with role separation.** We require both a spec verdict and a
   quality verdict, and a task is never complete with one missing
   (`task-engine.md:127-130`); role boundaries lift only on re-review
   (`code-review/SKILL.md:21, 175-180`). TCP folds spec and quality into one haiku pass.
4. **Non-destructive installation.** `bootstrap.py` overwrites unconditionally:
   `copy_claude_md` → `dest.write_text` clobbers an existing project `CLAUDE.md`
   (`:117-122, 612-616`); `copy_settings` → `shutil.copy2` replaces `.claude/settings.json`
   wholesale (`:594`), destroying any existing hooks or permissions; `copy_skills`
   `rmtree`s a same-named existing skill directory (`:527-529`). It also pipes three
   third-party URLs into bash (`:259, 386, 421`). Our harness has no installer that
   touches a user's config, and our curation rule already forbids importing whole
   catalogs (`.claude/rules/harness-lifecycle/curation.md`).
5. **Correctness of our own hooks.** All three of ours use stdin JSON + exit 2 + stderr.
   Five of TCP's fifteen use mechanisms the documented contract does not support.
6. **Workspace/ledger for recoverability.** `task-engine.md:26-53` mandates saving every
   review verbatim and re-reading `progress.md` after compaction. TCP's continuity story
   is the bead comment thread plus `knowledge.jsonl`; there is no round/finding state.

### 3.e Where their design is genuinely stronger

1. **The dispatch prompt is a durable artifact.** `log-dispatch-prompt.sh` captures it
   automatically onto the tracker. Ours writes briefs to
   `scratchpad/execution/<slug>/` — gitignored (`execution/SKILL.md:50-51`) and
   explicitly "disposable after the epic/task closes" (`task-engine.md:226`). After a
   workstream closes, **we cannot reconstruct what any worker was actually told**; the
   bd `--reason` holds evidence of outcome, not of instruction. Their mechanism costs
   ~40 lines of bash and requires zero agent cooperation.
2. **Worker isolation via worktree-per-task.** A supervisor physically cannot touch
   another task's files. Our `01-delegation.md` forbids parallel implementers on shared
   files *by rule*, and `task-engine.md:234` repeats it — a prohibition we accept
   precisely because we have no isolation. Note this is a genuine trade-off, not a
   free win: their isolation is what forces the whole PR/merge apparatus, and our
   snapshot-based review packaging (`task-engine.md:53-70`) is simpler because of it.
3. **A closed knowledge loop.** capture (`memory-capture.sh`) → store
   (`knowledge.jsonl`) → surface at session start (`session-start.sh:106-119`) → search
   (`recall.sh`). Ours is `learnings.md` with a prose instruction to write to it
   (`CLAUDE.md` §Learnings); `bd-prime.sh` surfaces bd state only, never learnings. The
   *surfacing* half is the part we lack, and it is nearly free.
4. **Session-start operational hygiene.** Dirty-main warning (`session-start.sh:22-30`)
   and stale-bead surfacing (`:91-96`) are two lines each and we have neither.
5. **Escape hatches on hard blocks.** Both `validate-epic-close.sh:23-25` (`--force`)
   and the quick-fix `ask` path (`block-orchestrator-tools.sh:78-96`) ship a documented
   override. Our `block-dangerous-commands.sh` has none — a blocked command's only
   recourse is a settings edit. Their pattern (block by default, name the override in
   the deny message) is better hook ergonomics.

### 3.f Internal contradictions in TCP (relevant to any adoption)

Listing these because they are the evidence that this framework has not been run through
its own review discipline:

- **Parallel vs sequential epic dispatch.** `SKILL.md:237-238` says dispatch sequentially
  and "Wait for child's PR to merge before dispatching next." `templates/CLAUDE.md:126`
  says "`bd ready` to find unblocked children → **dispatch ALL ready in parallel**."
  Both are installed into the same repo.
- **Branch model for epic children.** `beads-workflow-injection-git.md:16` has every
  worker create `bd-{BEAD_ID}` (children included);
  `.claude/hooks/block-branch-for-epic-child.sh:53-62` blocks exactly that and demands
  children share `bd-{EPIC_ID}`; `validate-completion.sh:98` then checks the remote for
  `bd-{BEAD_ID}` — which under the shared-branch model would never exist.
- **Git-native tickets that aren't in git.** README:70 sells beads as "tracked in your
  repo, not a third-party service", while `bootstrap.py:634` adds `.beads/` to
  `.gitignore` as "ephemeral task data". Our policy is the opposite and deliberate:
  the Dolt store is truth and `.beads/issues.jsonl` is a committed mirror
  (`beads.md:23-26`).
- **Architect cannot write its own deliverable.** `enforce-sequential-dispatch.sh:53-60`
  blocks dispatch until the epic's design file exists and tells the orchestrator to
  dispatch `architect` to create it — but `templates/agents/architect.md:5-10` grants no
  Write tool. The orchestrator is also forbidden to write it (`SKILL.md:249`). Deadlock
  unless the orchestrator uses the quick-fix `ask` path.
- **Stale dogfooded skill.** `.claude/skills/create-beads-orchestration/SKILL.md` (208
  lines) is an older revision: it passes `--claude-only` to bootstrap (`:92`), a flag
  `bootstrap.py:779-782` no longer defines (current flags: `--external-providers`,
  `--with-kanban-ui`) — argparse would reject it. `scripts/cli.js:27` carries the same
  stale flag in its help text. The shipped root `SKILL.md` and
  `skills/create-beads-orchestration/SKILL.md` are byte-identical (verified by `diff`).
- **The npm package cannot do what its docs offer.** `package.json:29-37` `files` omits
  `mcp-provider-delegator/`, so `--external-providers` on an npm install hits
  `bootstrap.py:155-158` (source missing) → `sys.exit(1)`.
- **Documented enforcement that does not exist.**
  `frontend-reviews-requirement.md:60` and `beads-workflow-injection.md:102` both promise
  SubagentStop enforcement that no hook implements.

---

## 4. Borrow candidates (ranked; curation default is reject/defer)

Ranked by (durable value to us) ÷ (effort + risk). All are pattern-level borrows —
none copies TCP code, per `.claude/rules/harness-lifecycle/curation.md`.

**1. Auto-log the dispatch brief onto the bead (pattern from `log-dispatch-prompt.sh`).**
*What exactly*: a PostToolUse:Task hook that, when a dispatch's prompt names a bead id
and a brief path, appends one `bd comment <id> "DISPATCH [<agent>]: <brief path> —
<first N chars>"` with our actor tag. Cheaper variant: log the **brief path plus the
first ~500 chars**, not the whole prompt, since our briefs are files.
*Attaches to*: new `.claude/hooks/log-dispatch.sh` + a PostToolUse `Task` entry in
`.claude/settings.json`; conceptually closes the gap named in `task-engine.md:226`
(disposable workspace).
*Effort*: S — ~40 lines of bash, one settings entry, plus a `verification.md` row.
*Risk*: **Medium.** (a) It writes to bd from a hook, which sits oddly with our
"conservative git authority" posture (`beads.md:20-22`) — `bd comment` is a local Dolt
write, not a push, so I judge it in-bounds, but it should be a user decision. (b) Comment
volume on epics with many stages. (c) Our dispatch prompts are constructed by the
coordinator and may embed user content — logging them verbatim to a committed mirror is
a small disclosure surface; truncation + path-only mitigates.

**2. Make the epic/phase children-closed gate mechanical (pattern from
`validate-epic-close.sh` CHECK 2 — reimplemented correctly, not copied).**
*What exactly*: a PreToolUse:Bash hook that intercepts `bd close <id>`, and when `<id>`
is an epic with non-closed children, denies with the list of open children and names a
documented override.
*Attaches to*: either a new hook or an added stanza in
`.claude/hooks/block-dangerous-commands.sh`; makes `execution/SKILL.md:89-93` enforced
rather than requested.
*Effort*: S–M — the jq query already exists verbatim in `execution/SKILL.md:91`; the work
is the hook wrapper, the override token, and tests that exercise it through **stdin**
(their test's exact failure — `tests/test-validate-epic-close.sh:37` — is the anti-pattern
to avoid).
*Risk*: Low–Medium. Must not block legitimate closes: our wontfix path is a close
(`beads.md:56`), and a child closed as wontfix already counts as closed, so that's fine.
The real risk is a hook that fires on any Bash line containing `bd close` inside a
heredoc or comment. Needs the override.

**3. Closed-bead reopen guard (pattern from `enforce-sequential-dispatch.sh:29-35`).**
*What exactly*: deny `bd update <id> --claim` / `--status in_progress` when `<id>` is
closed, with a deny message prescribing `bd create` + `bd dep relate`.
*Attaches to*: same hook as (2); complements `beads.md:56-57` (closed issues are the
durable rejection record).
*Effort*: S — one `bd show --json` call in an existing hook.
*Risk*: Low. Costs one `bd` invocation per matching Bash call; must fail open if `bd` is
absent (our `bd-prime.sh:9-25` already shows the PATH fragility on this machine).

**4. Surface learnings at session start (pattern from `session-start.sh:106-119`).**
*What exactly*: extend `.claude/hooks/bd-prime.sh` (or add a sibling) to print the last
N entries of `.claude/project/learnings.md`, plus a dirty-worktree warning
(`session-start.sh:22-30`) and stale-bead line (`:91-96`) if `bd stale` is cheap.
*Attaches to*: `.claude/hooks/bd-prime.sh`; makes `CLAUDE.md` §Learnings a read loop
rather than a write-only file.
*Effort*: S — ~10 lines. SessionStart stdout is context-added, so this works.
*Risk*: Low, but real: it spends context on **every** session including trivial ones.
Cap hard (3–5 entries, one line each) and keep it behind a size check.

**5. `bd create` minimum-content floor (adopt-in-part, from
`block-orchestrator-tools.sh:154-161`).**
*What exactly*: deny `bd create` that has neither `-d`/`--description` nor
`--acceptance`, **except** when `-l idea` is present.
*Attaches to*: `block-dangerous-commands.sh`; gives the `ready-for-agent` gate
(`beads.md:52-54`) a mechanical floor.
*Effort*: S.
*Risk*: **Medium-high friction.** Our `idea` and `backlog` flows create intentionally
thin beads (`beads.md:36-40`), and the triage skill moves beads between states. A rule
that misfires on idea capture would train agents to route around the hook. Defer unless
we have evidence of thin beads actually causing rework.

**6. Documented override tokens on hard blocks (pattern from
`validate-epic-close.sh:23-25`).**
*What exactly*: every deny message from our hooks names its escape (e.g. a
`HOOK_OVERRIDE=<reason>` prefix) so a blocked agent has a legible, auditable path.
*Attaches to*: `block-dangerous-commands.sh`, `block-generated-edits.sh`.
*Effort*: S per hook.
*Risk*: **High — recommend against for `block-dangerous-commands.sh`.** That hook guards
`git reset --hard`, force-push, and `bd init --reinit`; a self-serviceable override
converts a hard stop into a speed bump, and the whole point is that a human sees the
command first. Worth it at most for `block-generated-edits.sh`, whose failure mode is
inconvenience rather than data loss.

**Explicitly not borrowing** (judgment): worktree-per-task and the PR/merge apparatus
(conflicts with our snapshot review model, `task-engine.md:53-70`, and with conservative
git authority); orchestrator write-blocking (conflicts with Working Mode's inline `small`
path); `discovery`'s WebFetch-and-inject supervisor generation (untrusted third-party
prompt text written into `.claude/agents/` with `tools: *` — a prompt-injection vector,
`discovery.md:83-107, 160-168`); persona names; DEMO-block review (our `code-review`
skill's evidence discipline is strictly stronger and does not require the reviewer to
re-run suites — `code-review/SKILL.md:61-68`); response-length hooks (both broken, and
`task-engine.md:230-234` already states the contract); the quick-fix `ask` prompt.

---

## 5. Verdict per cataloged capability

Catalog reference: `harness_lifecycle/catalogs/The-Claude-Protocol.json` — 7 agents, 15
hooks, 5 physical / 4 logical skills at `af754ef`. Bucket 10 placement per
`harness_lifecycle/inventory/skill-buckets.md:49`. No prior TCP ledger entry exists
(`harness_lifecycle/ledger.json` contains zero `The-Claude-Protocol` mentions), except
that `react-best-practices` was already ruled out-of-scope in round-002
(`skill-buckets.md:31-33`).

### Skill

| Capability | Verdict | Reasoning |
|---|---|---|
| `create-beads-orchestration` (3 copies: root `SKILL.md`, `skills/…` — byte-identical; `.claude/skills/…` — a stale 208-line revision passing a removed `--claude-only` flag) | **reject** | It is a whole-framework installer that overwrites `CLAUDE.md` and `.claude/settings.json` (`bootstrap.py:594, 612-616`), gitignores `.beads/` against our policy (`bootstrap.py:634` vs `beads.md:23-26`), and mandates a restart + WebFetch-driven agent generation — everything our curation rule calls importing a whole catalog. |
| *(context)* `subagents-discipline` — not in the assigned scope but load-bearing for their loop; root and `templates/` copies differ | **reject** | Its Rules 1–3 (look at real data, close the loop, use your tools) are already covered by our `verification-before-completion` claim→evidence table and `test-driven-development`; Rule 0 is beads-workflow-specific. |

### Agents (7)

| Capability | Verdict | Reasoning |
|---|---|---|
| `scout` | **reject** | Our `Explore` agent already covers read-only fan-out search, and the persona/report scaffolding adds tokens without adding a check. |
| `detective` | **reject** | Our `systematic-debugging` skill owns root-cause work with a stronger protocol than a 101-line report template. |
| `architect` | **reject** | Duplicates our `planning` + `codebase-design` + `domain-modeling` surface, and is internally broken (no Write tool for the design doc its own hook requires — `architect.md:5-10` vs `enforce-sequential-dispatch.sh:53-60`). |
| `scribe` | **reject** | A docs-writing agent with Write/Edit and no review gate is a regression against `authoring-for-agents` plus normal dispatch. |
| `code-reviewer` | **reject** | Strictly weaker than our `code-review` skill: one haiku pass (`code-reviewer.md:5`), no mode contract, no severity calibration, no bounded fix loop, no re-review scope. Its one distinctive idea — re-run the implementer's demo commands — our skill deliberately declines (`code-review/SKILL.md:61-68`) in favour of trusting the reported run and spending reviewer effort on judgment. |
| `discovery` | **reject** | WebFetches third-party agent markdown and writes it into `.claude/agents/` with `tools: *` (`discovery.md:83-107, 160-168`) — untrusted text becoming a privileged system prompt. Security-disqualifying regardless of utility. |
| `merge-supervisor` | **reject** | Our `resolving-merge-conflicts` skill covers the same ground; the "never blindly accept one side, read 20+ lines of context, remove all markers, run tests" protocol (`merge-supervisor.md:48-82`) is the only content worth a glance, and it is not new to us. |

### Hooks (15)

| Capability | Verdict | Reasoning |
|---|---|---|
| `log-dispatch-prompt.sh` | **adopt-in-part** | The pattern (dispatch instruction → durable tracker comment, automatic, no agent cooperation) closes a real gap left by our disposable workspace (`task-engine.md:226`); reimplement against our brief-path model, not copy. Borrow #1. |
| `validate-epic-close.sh` | **adopt-in-part** | Adopt only CHECK 2 (epic with open children → deny) as a correctly-written stdin hook, giving teeth to `execution/SKILL.md:89-93`; reject CHECK 1 (merged-PR gate) as incompatible with `beads.md:20-22`. The shipped implementation is a no-op (`:8`) and its test validates the wrong interface (`tests/test-validate-epic-close.sh:37`) — do not copy either. Borrow #2. |
| `enforce-sequential-dispatch.sh` | **adopt-in-part** | Adopt only the closed-bead guard (`:29-35`); reject the blocker check (our `bd ready --parent` selection already gives dependency truth) and the design-doc check (presupposes their `.designs/` + architect flow, which deadlocks). Borrow #3. |
| `session-start.sh` | **adopt-in-part** | Adopt the learnings-surfacing, dirty-worktree, and stale-bead lines into `bd-prime.sh`; reject the worktree-cleanup and `gh pr list` sections (no worktree model, and a network call on every session start). Borrow #4. |
| `enforce-bead-for-supervisor.sh` | **defer** | The gap is real (nothing stops an untracked `implementer` dispatch) but the fix depends on a convention we don't have yet — a bead id in every dispatch brief. Revisit if/when the execution skill mandates that field. |
| `block-orchestrator-tools.sh` | **reject** (with one `defer` carve-out) | Blanket orchestrator write-blocking contradicts Working Mode's inline `small` path; its git allowlist has no default-deny arm and permits `push --force` / `reset --hard` (`:126-147, 167`) — worse than our existing guard; the `-n` substring test (`:138`) is a false-positive bug. Carve-out: the `bd create` description floor (`:154-161`) → **defer** pending the `-l idea` exemption (Borrow #5). |
| `enforce-branch-before-edit.sh` | **out-of-scope** | Presupposes worktree-per-task, which we do not use. |
| `block-branch-for-epic-child.sh` | **out-of-scope** | Same, plus it enforces a branch model (`:53-62`) that contradicts TCP's own worker template (`beads-workflow-injection-git.md:16`) and completion validator (`validate-completion.sh:98`). |
| `validate-completion.sh` | **reject** | Design checks only bookkeeping and never touches test results (`:76-129`; "Tests: pass" is a template string at `beads-workflow-injection-git.md:98`); implementation fails open on an undocumented input field (`:7, 11`) and blocks via an undocumented output shape. Our `verification-before-completion` gate is a strictly better specification. |
| `enforce-concise-response.sh` | **reject** | Emits an undocumented PostToolUse field so it is ignored, and self-describes as non-blocking (`:29`); `task-engine.md:230-234` already states our result-size contract. |
| `remind-inprogress.sh` | **reject** | PreToolUse plain-text stdout never reaches the model; the content is a one-line reminder our execution skill already mandates (`execution/SKILL.md:76-77`). |
| `inject-discipline-reminder.sh` | **reject** | Same broken mechanism; the payload duplicates text already inside the injected worker contract (`beads-workflow-injection-git.md:39-42`). |
| `clarify-vague-request.sh` | **reject** | The mechanism works, but a raw character count is a bad ambiguity proxy and it injects an unconditional epic reminder on **every** prompt (`:34-38`). Our `brainstorming` / `skill-router` routing handles ambiguity semantically. |
| `memory-capture.sh` | **defer** | The capture→store→surface loop is the right idea, but this implementation reconstructs the comment body by regex over the shell command string (`:28`) and hardcodes a Swift/AppKit-flavoured tag vocabulary (`:57-60`). If we want capture, write it against our `learnings.md` format; the *surfacing* half (Borrow #4) delivers most of the value alone. |
| `nudge-claude-md-update.sh` | **reject** | PreCompact stdout effectiveness unconfirmed, and our durable-state story is bd + `learnings.md` + `MEMORY.md`, not a `## Current State` section in `CLAUDE.md`. |

**Summary:** 1 skill rejected; 7 agents rejected; of 15 hooks — 4 adopt-in-part, 3 defer,
6 reject, 2 out-of-scope. Net borrow surface: roughly 100–150 lines of new bash across
two hook files plus settings entries, none of it copied from upstream.

---

## Overall assessment (judgment, graded harshly)

TCP's thesis — *constraints beat instructions; enforce workflow at the tool boundary*
— is correct and is the thing worth taking from it. Its execution does not hold up.
A third of its hooks are wired to input or output mechanisms Claude Code does not
support, and the two the README leads with (completion validation, epic-close gating)
are precisely the broken ones, with a test suite that mocks the wrong interface and
therefore reports green. Its documentation asserts enforcement that no code implements
in at least three places. Its own dogfooded copy of its flagship skill invokes a flag
its bootstrap removed, and its npm package omits the directory its advertised
`--external-providers` mode requires. On design, it puts haiku on the adversarial
review gate while spending opus on scouting and merges, ships an unbounded fix loop,
and gives a WebFetch-driven agent generator permission to write untrusted markdown into
privileged agent files.

Against that, our harness has a materially stronger review and completion
*specification* and correct hook plumbing, and a materially weaker record of turning
mechanically-checkable rules into mechanisms. The honest read of this comparison is not
"we win" — it is that we have four cheap, well-scoped mechanizations available (dispatch
logging, epic-close gate, closed-bead guard, learnings surfacing) that we have been
asking agents to do politely instead.
