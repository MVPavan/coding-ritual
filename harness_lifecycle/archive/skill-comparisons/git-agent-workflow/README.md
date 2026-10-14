# Git & Agent Workflow — skill comparison

Capability family: **isolating, dispatching, reconciling, and landing agent work
through Git.** Five reference skills against our installed harness. Levels 1–2
here; component inventory, cross-skill matrix, and shared-component differences
in [components.md](components.md).

Compared set (every shipped file read: `SKILL.md`, `agents/openai.yaml`,
`scripts/`):

- `superpowers/skills/dispatching-parallel-agents/`
- `superpowers/skills/finishing-a-development-branch/`
- `superpowers/skills/using-git-worktrees/`
- `mattpocock_skills/skills/engineering/resolving-merge-conflicts/`
- `mattpocock_skills/skills/misc/git-guardrails-claude-code/`

## Level 1 — placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `dispatching-parallel-agents` | S | 10 · Orchestration, Handoff & Context Continuity — family `subagent-dispatch` (`skill-buckets.md:175`) | Description says "2+ independent tasks … without shared state or sequential dependencies" (`SKILL.md:3`), but every worked example is **multiple independent test/subsystem failures** (`:12`, `:36-41`, `:136-159`). The description over-fires: read literally it also claims any two independent *plan* tasks, which our task engine already routes and explicitly serializes on shared files (`task-engine.md:217`). |
| `finishing-a-development-branch` | S | 8 · Version Control & Change Integration — family `branch-integration`, also 9 (`skill-buckets.md:151`) | Implementation done and the human must choose how the work lands. Description says "all tests pass" (`SKILL.md:3`) but Step 1 re-runs the suite and stops on red (`:14-26`) — so it is safe to fire on *believed* green, and is designed to. |
| `using-git-worktrees` | S | 8 · Version Control & Change Integration — family `workspace-isolation`, also 10 (`skill-buckets.md:152`) | "Starting feature work that needs isolation … or before executing implementation plans" (`SKILL.md:3`). The second clause is very broad — taken literally it fires ahead of *every* execution run, including our light-path standard units where a worktree is pure overhead. |
| `resolving-merge-conflicts` | M | 8 · Version Control & Change Integration — family `git-mechanics` (`skill-buckets.md:150`) | A merge or rebase is **already conflicted** (`SKILL.md:3`). The tightest trigger in the set: state-conditioned, unambiguous, no misfire surface. |
| `git-guardrails-claude-code` | M | 12 · Repository Tooling & Guardrails — family `guardrail-install`, also 8 (`skill-buckets.md:195`) | User wants destructive git commands blocked (`SKILL.md:3`). **Taxonomy marks it excluded / `adoption_scope=out-of-scope`** — it lives in upstream's unpromoted `misc/` staging area (`skill-buckets.md:24-31`). It is also *model*-invocable: its `agents/openai.yaml:1-4` carries interface metadata only, with no `policy.allow_implicit_invocation: false`, so an agent can decide on its own to rewrite `settings.json`. |

Repo key: **S** = superpowers, **M** = mattpocock_skills.

### Our baseline (not skills — a spread of rules, hook, and engine)

| Our asset | What it covers in this family |
|---|---|
| `.claude/hooks/block-dangerous-commands.sh` + `.claude/settings.json:3-13` | Enforced PreToolUse denylist: git working-tree/history destroyers, `--no-verify`, bd store re-init, recursive `rm` outside `/tmp`, generated-mirror writes (`hook:19-29`, `:42-47`, `:49-76`, `:78-87`) |
| `CLAUDE.md:83-87` + `.claude/project/invariants.md:17-18` + `.claude/agents/implementer.md:26,30-33` | Prose-level git safety: explicit staging, small reversible commits, no amend, no scratchpad commits |
| `.claude/rules/core/01-delegation.md:5-10` | Coordinator/worker split, fresh worker per task, no session history to workers, no parallel implementers on shared files |
| `.claude/skills/execution/` + `references/task-engine.md` | Dispatch packet, status contract, review gate, bounded fix loop, breaker, final review, commit policy (`SKILL.md:96-98`; `workstream-mode.md:36-43`) |
| `.claude/skills/code-review/SKILL.md:51-54` | The only worktree instruction we own: reviewers may check another revision out into a temporary worktree instead of moving HEAD |
| `.claude/skills/agent-matrix/SKILL.md:83` | Worktree isolation as a subagent *definition field* (`isolation`) — configuration, not a git procedure |

**Absent from our harness entirely** (verified by grep across `.claude/`,
`AGENTS.md`, `CLAUDE.md`): any merge/rebase conflict procedure; any
branch-finishing, merge, or PR-creation procedure; any worktree *creation*
procedure. The only `git merge`-adjacent hit is `planning/SKILL.md:117`
("keep the sequence on a shared integration branch"), which is a decomposition
instruction, not an integration one.

## Level 2 — capability profiles

### `dispatching-parallel-agents` (S)

**Achieves** — turns N independent failures into N concurrently-running,
context-isolated investigations instead of one serial crawl.

**Can do**
- Gate parallelism on an explicit independence test, expressed as a decision
  graph, before any dispatch (`SKILL.md:18-34`, `:36-45`).
- Name the *mechanical* fact that makes parallelism happen: several dispatch
  calls in one response run concurrently; one per response is sequential
  (`:66-77`).
- Specify the per-agent packet — scope, goal, constraints, expected output
  (`:58-65`) — with a full worked prompt (`:94-113`).
- Teach prompt failure modes as a ❌/✅ table: too broad, no context, no
  constraints, vague output (`:115-127`).
- Close the loop after return: read summaries, check for cross-agent edit
  conflicts, run the full suite, spot-check for systematic agent error
  (`:79-86`, `:161-168`).

**Pros** — the only skill in the set that treats *fan-out* as a decision with a
falsifiable precondition rather than an optimization; its "check for conflicts,
then run the full suite" close (`:161-168`) is the piece our engine most
plainly lacks for multi-agent work. Its context-isolation principle (`:10`)
matches our delegation rule almost word for word, which is evidence the
principle is durable rather than idiosyncratic.

**Cons** — versus our task engine it is thin where we are thick: no review
gate, no bounded fix loop, no ledger, no status contract, no model selection.
Its example domain is debugging, but our `systematic-debugging` skill has no
fan-out step to attach it to, so adopting it wholesale would create a second,
weaker dispatch doctrine competing with `task-engine.md`.

### `finishing-a-development-branch` (S)

**Achieves** — converts "the code is done" into a *human-chosen*, verified,
cleanly-cleaned-up landing.

**Can do**
- Refuse to show the integration menu until the suite is green on the tree
  about to be integrated (`SKILL.md:14-26`).
- Detect whether it is in a normal repo, a named-branch worktree, or an
  externally-managed detached HEAD, and vary both the menu and the cleanup
  accordingly (`:28-44`).
- Force base-branch confirmation before merging (`:46-51`).
- Present a *fixed* menu and wait — the integration decision is the human's
  (`:53-82`).
- Re-run tests on the **merged result** and stop with everything intact if it
  is red (`:96-107`).
- Gate destruction behind a literal typed `discard` after listing exactly what
  dies (`:132-157`).
- Apply a provenance rule to cleanup: remove only worktrees under
  `.worktrees/`/`worktrees/`; anything else belongs to the host (`:159-178`).
- Pre-refute nine specific rationalizations, including "tests passed earlier",
  "they obviously want it merged", and "force-push will fix the rejected push"
  (`:189-201`).

**Pros** — the strongest *stop-and-ask* discipline in the set, and the only
skill anywhere in this comparison that re-verifies **after** integration rather
than before (`:96-107`); that check catches the semantic-merge class of bug that
a green feature branch cannot. Its rationalization table is directly aimed at
the failure our Git Safety prose only asserts against.

**Cons** — heavily coupled to the worktree model: Steps 2 and 6 assume the
`using-git-worktrees` layout, and the ledger already **rejected** exactly that
coupling (`ledger.json:638-641`, `subagent-driven-development`, adopted with
"Rejected: worktree isolation + finishing-a-development-branch coupling"). It
also assumes per-branch feature work with commits in hand, whereas our engine
runs on an uncommitted working-tree snapshot (`task-engine.md:54-69`) and
implementers do not commit at all.

### `using-git-worktrees` (S)

**Achieves** — guarantees an isolated workspace exists before implementation,
without duplicating isolation the harness already provided.

**Can do**
- Detect existing isolation *first* and skip creation (`SKILL.md:16-37`).
- Guard the one false positive that detection has: submodules also satisfy
  `GIT_DIR != GIT_COMMON`, so check `--show-superproject-working-tree`
  (`:26-32`).
- Ask consent before creating a worktree, and honour a pre-declared preference
  without asking (`:39-45`).
- Prefer a native harness worktree tool over raw `git worktree add`, with the
  reason stated: bypassing it creates phantom state the harness cannot manage
  (`:51-57`, `:164`).
- Resolve the worktree directory by a stated priority (`:63-76`) and refuse to
  create until `git check-ignore` proves it ignored (`:78-88`).
- Degrade gracefully when the sandbox denies worktree creation (`:100`).
- Run ecosystem setup and a clean-baseline test run, so later failures are
  attributable (`:102-132`).

**Pros** — its detect-before-create and submodule guard are the highest-value
components for *us specifically*: this repo is full of submodules under
`reference_harnesses/`, so a naive `GIT_DIR != GIT_COMMON` isolation check
would misfire here in a way the guard fixes (`:26-32`). The clean-baseline rule
(`:121-132`) is a genuine gap — our engine records `SCOPE_BASE` and a
dirty-tree baseline (`workstream-mode.md:18-20`) but never establishes that the
*tests* were green before work started.

**Cons** — the whole isolation premise is at odds with how our engine works:
implementers edit the coordinator's working tree and never commit
(`task-engine.md:54-58`), so moving them into worktrees would break
`review-package.sh`'s snapshot model. `git check-ignore` failure is resolved by
"Add to .gitignore, **commit** the change" (`:86`) — an unrequested commit,
which our Git Safety rules forbid without approval (`CLAUDE.md:83-84`). Step 2's
setup block hardcodes `poetry install` for `pyproject.toml` (`:115`), which is
wrong for this repo's `uv`-only rule (`.claude/rules/python/coding-style.md`,
Package Management).

### `resolving-merge-conflicts` (M)

**Achieves** — resolves an in-progress conflict by recovering *intent* on both
sides rather than by picking a side.

**Can do**
- Survey the merge/rebase state and the conflicting files first (`SKILL.md:6`).
- Recover each side's original intent from primary sources — commit messages,
  PRs, issues (`:8`).
- Apply an explicit hunk policy: preserve both intents where possible; where
  incompatible, pick the one matching the merge's stated goal and record the
  trade-off; invent no new behaviour (`:10`).
- Forbid `--abort` as an escape (`:10`).
- Discover and run the project's own checks in order — typecheck, tests, format
  — and fix what the merge broke (`:12`).
- Finish the operation, including continuing a rebase to completion (`:14`).

**Pros** — the highest gap-to-size ratio in the set: five lines, no
harness assumptions, and it addresses a capability our harness has **zero**
coverage of. Two components are load-bearing and non-obvious: *no new
behaviour* (`:10`) blocks the characteristic LLM conflict failure of writing a
plausible third variant that neither branch ever contained, and *never
`--abort`* blocks the other one, silently discarding a hard merge.

**Cons** — Step 5 says "Stage everything and commit" (`:14`), which directly
violates our explicit-staging invariant (`invariants.md:17-18`,
`CLAUDE.md:83`) and our hook's spirit; that line must be rewritten, not
borrowed. It also has no conflict-*prevention* or escalation path: no rule for
when a conflict is too semantically deep to resolve without the author, and no
verification-evidence requirement beyond "run the checks".

### `git-guardrails-claude-code` (M)

**Achieves** — installs a PreToolUse hook so destructive git commands are
blocked by the harness rather than by the agent's good intentions.

**Can do**
- Ship a working denylist script: stdin JSON → `jq -r '.tool_input.command'` →
  pattern loop → stderr message → `exit 2`
  (`scripts/block-dangerous-git.sh:3-23`).
- Block nine patterns including **bare `git push`** and both `--force`
  spellings (`:6-16`).
- Ask install scope, project vs global, and wire the matching `settings.json`
  (`SKILL.md:22-24`, `:36-81`), merging into an existing `PreToolUse` array
  rather than overwriting (`:81`).
- Verify the install by piping a fake payload and asserting exit 2 (`:87-95`).
- Offer pattern customization at install time (`:83-85`).

**Pros** — it is the only skill in the set whose control is *enforced* rather
than *instructed*, and its verify-the-hook step (`:87-95`) is a real completion
gate that install-type instructions usually omit.

**Cons** — we already run a strict superset of it
(`.claude/hooks/block-dangerous-commands.sh`), so nearly everything here is
duplicate. Where it differs it is also weaker: `grep -qE` treats patterns as
regexes so `git checkout .` matches *any* `git checkout X` (`:19` with `:12`),
which is an unintended over-block, while ours uses fixed-string `grep -qF`
(`hook:32`). Its message "The user has prevented you from doing this" (`:20`)
is a dead end; ours says "Ask the user before proceeding" (`hook:33`), which
routes the agent to the unblock path. And the skill has no `bd`, `rm -r`, or
generated-file coverage at all. Its installer half is also a live risk for us:
a model-invocable skill that edits `settings.json` conflicts with our config
being coordinator-owned.

### Verdict

**Duplicates.** `git-guardrails-claude-code` duplicates our installed hook and
loses on every axis where the two differ — fixed-string vs regex matching,
actionable vs dead-end block message, and a much narrower pattern set. No
ledger entry exists for it, and the taxonomy already marks it out-of-scope
(`skill-buckets.md:24-31`). The only thing it holds that we do not is **bare
`git push`** in the denylist and the **pipe-a-payload install verification**
(`SKILL.md:87-95`); the smallest durable borrowable pattern is that
verification snippet as a check on our own hook, not the skill.

**Extends.** `dispatching-parallel-agents` extends our delegation rule rather
than competing with it: `01-delegation.md:8-9` already owns context isolation
and the no-shared-files rule, and `task-engine.md:73-84,211-218` already owns a
richer per-agent packet than this skill's. What it adds that we genuinely lack
is the **fan-out decision and its close**: an explicit independence test before
dispatching concurrently, and the post-return integration check — cross-agent
conflict scan, full-suite run, spot-check for systematic agent error
(`:79-86`, `:161-168`). Our engine is strictly serial per scope
(`workstream-mode.md:8-11`), and the parallel patterns we do run
(`DESIGN-IT-TWICE.md:19-30`, `model-council/SKILL.md:26`,
`perspective-council/SKILL.md:27-28`) are all *advisory* fan-outs where nobody
edits files, so none of them needed a conflict scan. Smallest durable
borrowable pattern: a three-line independence precondition plus the
conflict-scan/full-suite/spot-check close, added to the task engine as the
condition for ever dispatching two implementers at once — not a new skill.

**Extends, with a rejected coupling.** `finishing-a-development-branch` is
partly gap-filling (we have no landing procedure at all) and partly re-litigating
a settled decision: the ledger's `subagent-driven-development` entry
(`ledger.json:638-641`) adopted that skill while explicitly rejecting "worktree
isolation + finishing-a-development-branch coupling". That rejection covered
the *coupling*, not the two components that stand alone: **re-verify on the
merged result, and stop with everything intact if it is red** (`:96-107`), and
**typed-`discard` confirmation before any destructive branch operation**
(`:132-157`). Both are harness-independent and both cover holes our prose Git
Safety only asserts against. Smallest durable borrowable pattern: those two
rules, plus the base-branch confirmation line (`:46-51`), as Git Safety bullets
or an execution-skill landing step — never the menu machinery, which assumes
committed feature branches our implementers never produce.

**Fills a gap — narrowly.** `using-git-worktrees` fills a real gap only in its
*detection* half. Its creation half fights our snapshot model
(`task-engine.md:54-69`), forbids-by-implication our commit rules (`:86`), and
hardcodes non-`uv` Python setup (`:113`). Its detection half, by contrast, is
directly useful here: the **submodule guard** (`:26-32`) is the correct fix for
a check that would otherwise misfire everywhere under `reference_harnesses/`,
and the **native-tool-first rule** (`:51-57`) is the right doctrine given we
have `EnterWorktree`/`isolation` available (`agent-matrix/SKILL.md:83`). The
**clean-baseline test run** (`:121-132`) is a separate, self-contained gap.
Smallest durable borrowable pattern: the submodule-guarded isolation check plus
"use the native tool, never raw `git worktree add`", attached to the one place
we already send an agent into a worktree — `code-review/SKILL.md:51-54`.

**Fills a gap — cleanly.** `resolving-merge-conflicts` is the clearest
gap-filler in the set: our harness has no conflict guidance whatsoever, the
skill carries no harness assumptions, and its two prohibitions (*invent no new
behaviour*, *never `--abort`*, both `:10`) target exactly the failures an agent
makes in a conflicted tree. Smallest durable borrowable pattern: the five steps
with Step 5's "stage everything" replaced by our explicit-staging rule
(`invariants.md:17-18`) — small enough to live as a reference page or a rule,
and it needs no new dispatch surface.

No prior ledger decision exists for any of the five skills compared here; the
two adjacent entries that constrain them are `requesting-code-review`
(`ledger.json:628-631`, which adopted the git-worktree escape hatch now at
`code-review/SKILL.md:51-54`) and `subagent-driven-development`
(`ledger.json:638-641`, which rejected the worktree/branch-finishing coupling).
