# Git & Agent Workflow — component inventory (level 3)

Companion to [README.md](README.md). Every claim below carries a `file:line`
citation. Paths are relative to the repo root; reference-skill paths are
abbreviated after their first full mention.

Column keys used in the matrix:

| Key | Skill / asset |
|---|---|
| **DPA** | `reference_harnesses/superpowers/skills/dispatching-parallel-agents/SKILL.md` |
| **FDB** | `reference_harnesses/superpowers/skills/finishing-a-development-branch/SKILL.md` |
| **UGW** | `reference_harnesses/superpowers/skills/using-git-worktrees/SKILL.md` |
| **RMC** | `reference_harnesses/mattpocock_skills/skills/engineering/resolving-merge-conflicts/` |
| **GGC** | `reference_harnesses/mattpocock_skills/skills/misc/git-guardrails-claude-code/` |
| **Ours** | `.claude/` harness: hook, rules, invariants, execution skill, agents |

---

## Component inventory

### DPA — `dispatching-parallel-agents`

Ships one file: `SKILL.md` (168 lines).

| # | Component | Cite |
|---|---|---|
| D1 | **Context-isolation principle** — agents get isolated context, never inherit session history; the coordinator constructs exactly what they need, which also preserves coordinator context | `SKILL.md:10` |
| D2 | **Core principle** — one agent per independent problem domain, run concurrently | `:14` |
| D3 | **Independence decision graph** (dot digraph): multiple failures? → independent? → parallelizable? → parallel dispatch vs sequential vs single agent | `:18-34` |
| D4 | **Use-when list** — 3+ test files failing with different root causes, independently broken subsystems, each understandable alone, no shared state | `:36-41` |
| D5 | **Don't-use list (short form)** — related failures, need full system state, agents would interfere | `:42-45` |
| D6 | **Step 1 — domain identification** by grouping failures by what is broken | `:49-56` |
| D7 | **Step 2 — per-agent packet**: specific scope, clear goal, constraints, expected output | `:58-65` |
| D8 | **Step 3 — the parallelism mechanic**: several dispatch calls in one response run concurrently; one per response is sequential | `:66-77` |
| D9 | **Step 4 — integration close**: read each summary, verify fixes don't conflict, run full suite, integrate | `:79-86` |
| D10 | **Prompt-quality rubric** — focused / self-contained / specific about output, plus a full worked prompt including "Do NOT just increase timeouts" | `:87-113` |
| D11 | **Anti-pattern table** (❌/✅): too broad, no context, no constraints, vague output | `:115-127` |
| D12 | **Don't-use list (expanded)** — adds exploratory debugging and shared-state interference | `:129-134` |
| D13 | **Worked session record** — 6 failures / 3 files, the dispatch, per-agent outcomes, "no conflicts, full suite green" | `:136-159` |
| D14 | **Verification after return** — review summaries, check for conflicts, run full suite, **spot check because agents make systematic errors** | `:161-168` |

### FDB — `finishing-a-development-branch`

Ships one file: `SKILL.md` (202 lines).

| # | Component | Cite |
|---|---|---|
| F1 | **Pipeline principle** — verify tests → detect environment → present options → execute choice → clean up | `SKILL.md:10` |
| F2 | **Announce-at-start** line | `:12` |
| F3 | **Step 1 — green-suite precondition**; on red, report failures and stop before the menu | `:14-26` |
| F4 | **Step 2 — environment detection**: `GIT_DIR` vs `GIT_COMMON`, plus `WORKTREE_PATH` captured early with an inline note that Step 5 changes directory before Step 6 needs it | `:28-36` |
| F5 | **State → menu → cleanup table**, including detached HEAD = externally managed, leave in place | `:40-44` |
| F6 | **Step 3 — base-branch determination**, confirm before merging ("merging into the wrong base is expensive to undo") | `:46-51` |
| F7 | **Step 4 — fixed 3-option menu** (merge locally / push+PR / keep as-is), presented exactly as written, then wait | `:53-66`, `:78-82` |
| F8 | **Reduced 2-option menu on detached HEAD** (no merge option) | `:67-76` |
| F9 | **Option 1 — merge locally**: cd to main repo root for CWD safety, checkout/pull/merge | `:86-96` |
| F10 | **Post-merge re-verification** — run tests on the merged result; on red, stop, leave worktree and branch in place, nothing has been pushed | `:98-107` |
| F11 | **Branch deletion after green merge** — `git branch -d` (safe form), after worktree cleanup | `:108-111` |
| F12 | **Option 2 — push + PR** via forge tooling or the printed URL, follow repo PR template, report the URL; keep the worktree for PR feedback | `:113-126` |
| F13 | **Option 3 — keep as-is**, report branch and worktree path | `:128-130` |
| F14 | **Discard path** — reachable only on explicit human request; enumerate branch, commits, worktree; require the literally typed word `discard`; then `git branch -D` | `:132-157` |
| F15 | **Step 6 — provenance-based cleanup**: run from outside the worktree, using Step 2's captured values; normal repo → nothing; under `.worktrees/`/`worktrees/` → `git worktree remove` + `git worktree prune`; otherwise the host owns it, leave it | `:159-178` |
| F16 | **Quick-reference matrix** (option × merge/push/keep-worktree/cleanup-branch) | `:180-187` |
| F17 | **Rationalization table** — 9 rows, incl. "tests passed earlier this session", "they obviously want it merged", "'yeah, get rid of it' counts as confirmation", "force-push will fix it", "the merged-result failure is probably flaky" | `:189-201` |

### UGW — `using-git-worktrees`

Ships one file: `SKILL.md` (167 lines).

| # | Component | Cite |
|---|---|---|
| U1 | **Core principle** — detect existing isolation, then native tools, then git; "never fight the harness" | `SKILL.md:12` |
| U2 | **Announce-at-start** line | `:14` |
| U3 | **Step 0 — isolation detection** via `GIT_DIR` / `GIT_COMMON` / `BRANCH` | `:16-24` |
| U4 | **Submodule false-positive guard** — `GIT_DIR != GIT_COMMON` is also true inside submodules; check `git rev-parse --show-superproject-working-tree` and treat a hit as a normal repo | `:26-32` |
| U5 | **Skip-creation rule + branch-state report** (on a branch vs detached HEAD, the latter flagged as needing branch creation at finish time) | `:33-37` |
| U6 | **Consent gate** — ask before creating unless a preference was declared; honour declared preference without asking; on decline, work in place | `:39-45` |
| U7 | **Native-tool-first (Step 1a)** — use `EnterWorktree`/`WorktreeCreate`/`/worktree`/`--worktree` if available; rationale: raw `git worktree add` creates phantom state the harness cannot see or manage | `:51-57` |
| U8 | **Directory-selection priority (Step 1b)** — declared preference > existing `.worktrees` > existing `worktrees` > default `.worktrees/`; `.worktrees` wins if both exist | `:63-76` |
| U9 | **gitignore safety verification** — `git check-ignore` must pass before creating; if not ignored, add to `.gitignore` and **commit** that change first; rationale: an unignored worktree commits the whole tree | `:78-88` |
| U10 | **Creation command** — `git worktree add "$path" -b "$BRANCH_NAME"` under the chosen location | `:90-98` |
| U11 | **Sandbox fallback** — permission error on create → tell the user, work in the current directory, run setup and baseline in place | `:100` |
| U12 | **Step 2 — ecosystem setup detection** (npm / cargo / pip / poetry / go mod) | `:102-119` |
| U13 | **Step 3 — clean-baseline test run** before implementing; on failure report and ask whether to proceed | `:121-132` |
| U14 | **Ready report template** — path, test count, feature name | `:134-140` |
| U15 | **Quick-reference table** — 12 situation→action rows | `:142-157` |
| U16 | **Rationalization table** — 5 rows, incl. "I'm obviously not in a worktree", "`git worktree add` is quicker than hunting for a native tool" (called the #1 mistake), "the directory is surely ignored already", "baseline tests can wait" | `:159-167` |

### RMC — `resolving-merge-conflicts`

Ships two files: `SKILL.md` (14 lines) and `agents/openai.yaml` (4 lines).

| # | Component | Cite |
|---|---|---|
| R1 | **Step 1 — state survey**: git history and the conflicting files | `SKILL.md:6` |
| R2 | **Step 2 — intent recovery from primary sources** per conflict: commit messages, PRs, original issues/tickets; "understand deeply why each change was made" | `:8` |
| R3 | **Step 3a — hunk policy**: preserve both intents where possible; where incompatible pick the one matching the merge's stated goal and note the trade-off | `:10` |
| R4 | **Step 3b — invent no new behaviour** | `:10` |
| R5 | **Step 3c — never `--abort`**; always resolve | `:10` |
| R6 | **Step 4 — discover and run the project's automated checks** in order (typecheck → tests → format), fix what the merge broke | `:12` |
| R7 | **Step 5 — finish the operation**: stage everything, commit, and continue a rebase until all commits are rebased | `:14` |
| R8 | **Interface metadata only** — no `policy.allow_implicit_invocation: false`, so the skill is model-invocable | `agents/openai.yaml:1-4` |

### GGC — `git-guardrails-claude-code`

Ships three files: `SKILL.md` (95 lines), `scripts/block-dangerous-git.sh`
(26 lines), `agents/openai.yaml` (4 lines).

| # | Component | Cite |
|---|---|---|
| G1 | **Declared block list** — `git push` (all variants), `reset --hard`, `clean -f`/`-fd`, `branch -D`, `checkout .`/`restore .` | `SKILL.md:11-17` |
| G2 | **Install-scope question** — project `.claude/settings.json` vs global `~/.claude/settings.json` | `:22-24` |
| G3 | **Script install** — copy to `.claude/hooks/` or `~/.claude/hooks/`, `chmod +x` | `:26-34` |
| G4 | **Hook wiring** — `PreToolUse` with `matcher: "Bash"`, both project and global JSON given verbatim | `:36-79` |
| G5 | **Merge-don't-overwrite rule** for an existing settings file | `:81` |
| G6 | **Customization ask** — offer to add/remove patterns before finishing | `:83-85` |
| G7 | **Install verification** — pipe `{"tool_input":{"command":"git push origin main"}}` into the script, expect exit 2 and a BLOCKED message on stderr | `:87-95` |
| G8 | **Payload extraction** — read stdin, `jq -r '.tool_input.command'` | `scripts/block-dangerous-git.sh:3-4` |
| G9 | **Pattern array** — 9 entries, including bare `git push` and both `push --force` / `reset --hard` duplicates | `:6-16` |
| G10 | **Regex match loop** — `grep -qE "$pattern"` over the command | `:18-19` |
| G11 | **Block message + exit code** — stderr "BLOCKED: … The user has prevented you from doing this", `exit 2` | `:20-21` |
| G12 | **Interface metadata only** — no invocation policy block, so the installer is model-invocable | `agents/openai.yaml:1-4` |

### Ours — installed baseline

| # | Component | Cite |
|---|---|---|
| O1 | **Enforced git denylist** — `git push --force`/`-f`, `reset --hard`, `clean -f`/`-fd`, `branch -D`, `checkout .`, `restore .`, `--no-verify` | `.claude/hooks/block-dangerous-commands.sh:19-29` |
| O2 | **Fixed-string matching** — `grep -qF`, not regex | `hook:32` |
| O3 | **Actionable block message** — "BLOCKED: … Ask the user before proceeding", `exit 2` | `hook:33-34` |
| O4 | **jq-optional payload extraction** with a grep/sed fallback and an empty-command early exit | `hook:10-16` |
| O5 | **Beads store re-init guard** — order-independent `bd … init … --force/--reinit` block with a data-loss rationale | `hook:42-47` |
| O6 | **Recursive-remove guard** — per-`rm`-segment parsing, allow only when every target is provably under `/tmp/`, reject `..` escapes | `hook:49-76` |
| O7 | **Generated-mirror write guard** — block shell redirect / `tee` / `sed -i` writes to bd-rendered workstream files unless `BD_RENDER=1` is present | `hook:78-87` |
| O8 | **Hook wiring** — `PreToolUse` Bash matcher for the denylist plus a `Write|Edit` matcher for generated files | `.claude/settings.json:3-23` |
| O9 | **Prose git safety** — explicit staging only, small reversible commits, no amend, don't overwrite unrelated user changes, no scratchpad commits | `CLAUDE.md:83-87` |
| O10 | **Explicit-staging invariant** — violating it is a defect | `.claude/project/invariants.md:17-18` |
| O11 | **Implementer git constraints** — one small reversible commit if requested, explicit files only; never `git add .`/`-A`, `--no-verify`, or amend | `.claude/agents/implementer.md:26,30-33` |
| O12 | **Delegation rules** — coordinator/worker split, fresh worker per task, no raw session history to workers, **no parallel implementers against the same files** | `.claude/rules/core/01-delegation.md:5-10` |
| O13 | **Dispatch packet** — brief path, report path, owned *and forbidden* files, invariants, required tests, verification commands, commit policy, test-first and trust-boundary flags; paths not contents | `.claude/skills/execution/references/task-engine.md:73-84` |
| O14 | **Status contract** — `DONE` / `DONE_WITH_CONCERNS` / `NEEDS_CONTEXT` / `BLOCKED` plus 529-retry handling, each with a routing rule | `task-engine.md:85-97` |
| O15 | **Task sizing** — one deliverable per dispatch, capped prompt, capped result, no parallel implementers on the same files, no session history to workers | `task-engine.md:210-218` |
| O16 | **Snapshot review model** — implementers do not commit; `SCOPE_BASE` + `review-package.sh` package the working tree instead of a commit range | `task-engine.md:54-69` |
| O17 | **Review gate + bounded fix loop + breaker** — spec/code reviewers, 5-round cap with model escalation, park-with-ruling adjudication only at the cap | `task-engine.md:118-179` |
| O18 | **Final review** — whole-scope package, deferred/parked triage, one fix dispatch, one scoped re-review | `task-engine.md:181-208` |
| O19 | **Commit policy** — `git status` and *do not commit unless asked*, outside workstream scope | `.claude/skills/execution/SKILL.md:96-98` |
| O20 | **Workstream commit rule** — stage only files the phase actually touched, explicit paths, never `git add .`; no push | `.claude/skills/execution/references/workstream-mode.md:36-43` |
| O21 | **Dirty-tree baseline** — `git status --porcelain` recorded before an unattended walk; pre-existing dirty files belong to the user | `workstream-mode.md:18-20` |
| O22 | **Sequential-by-design** — one phase at a time even when deps would allow parallelism; independent phases run as separate sessions | `workstream-mode.md:8-11` |
| O23 | **Reviewer worktree escape hatch** — reviews are read-only on the checkout; to see another revision, check it out into a temporary `git worktree`, never move HEAD | `.claude/skills/code-review/SKILL.md:51-54` |
| O24 | **Worktree isolation as a definition field** — `isolation` in the subagent-capability mapping | `.claude/skills/agent-matrix/SKILL.md:83` |
| O25 | **Advisory parallel fan-outs** — design-it-twice sub-agents, council members, per-file scanners, research subagents; all read-only or write-to-scratch, none edit shared source | `.claude/skills/codebase-design/DESIGN-IT-TWICE.md:19-30`; `.claude/skills/model-council/SKILL.md:26`; `.claude/skills/perspective-council/SKILL.md:27-28,43`; `.claude/skills/design-evolve/SKILL.md:70`; `.claude/skills/wayfinder/SKILL.md:115` |
| O26 | **Dependency-honest decomposition** — independent stages stay unchained "so it can run in any order or in parallel" (permission, with no dispatch procedure attached) | `.claude/skills/planning/references/decompose.md:62-65` |
| O27 | **Rationalization table** — execution-scoped excuses (fix-it-myself, one-more-round, skip-the-re-review, drop-the-finding, close-enough, close-now-verify-later) | `.claude/skills/execution/SKILL.md:120-129` |

---

## Cross-skill matrix

`✓` present · `~` variant (differs in mechanism or strength) · `—` absent.

### Workspace isolation

| Component | DPA | FDB | UGW | RMC | GGC | Ours |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Detect existing isolation before creating | — | ~ | ✓ | — | — | — |
| Submodule false-positive guard | — | — | ✓ | — | — | — |
| Consent gate before creating a worktree | — | — | ✓ | — | — | — |
| Native tool preferred over raw `git worktree add` | — | — | ✓ | — | — | ~ |
| Worktree directory selection priority | — | — | ✓ | — | — | — |
| gitignore verified before creation | — | — | ✓ | — | — | — |
| Sandbox-denial fallback | — | — | ✓ | — | — | — |
| Ecosystem dependency setup | — | — | ✓ | — | — | — |
| Clean-baseline check before work starts | — | — | ✓ | — | — | ~ |
| Worktree cleanup by provenance | — | ✓ | — | — | — | — |
| Isolation as a subagent config field | — | — | — | — | — | ✓ |

### Branch integration

| Component | DPA | FDB | UGW | RMC | GGC | Ours |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Green suite required before integrating | — | ✓ | — | ~ | — | ~ |
| Base-branch confirmation | — | ✓ | — | — | — | — |
| Fixed human-choice menu, then wait | — | ✓ | — | — | — | — |
| Environment-conditional menu | — | ✓ | — | — | — | — |
| Re-verify **after** the merge | — | ✓ | — | ~ | — | — |
| PR creation + report URL | — | ✓ | — | — | — | — |
| Typed-confirmation destructive path | — | ✓ | — | — | — | ~ |
| Safe vs force branch deletion (`-d`/`-D`) | — | ✓ | — | — | — | — |
| Integration decision belongs to the human | — | ✓ | — | — | — | ~ |

### Conflict resolution

| Component | DPA | FDB | UGW | RMC | GGC | Ours |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Conflict-state survey | — | — | — | ✓ | — | — |
| Intent recovery from primary sources | — | — | — | ✓ | — | ~ |
| Hunk policy (preserve both / pick per goal) | — | — | — | ✓ | — | — |
| Invent no new behaviour | — | — | — | ✓ | — | ~ |
| Never `--abort` | — | — | — | ✓ | — | — |
| Post-resolution automated checks | — | ~ | — | ✓ | — | ~ |
| Finish the merge/rebase (stage, commit, continue) | — | ~ | — | ✓ | — | ~ |

### Parallel dispatch

| Component | DPA | FDB | UGW | RMC | GGC | Ours |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Independence test before fanning out | ✓ | — | — | — | — | ~ |
| One agent per independent domain | ✓ | — | — | — | — | ✓ |
| Same-response dispatch = concurrency (mechanic named) | ✓ | — | — | — | — | — |
| Workers never inherit session context | ✓ | — | — | — | — | ✓ |
| Per-agent packet (scope/goal/constraints/output) | ✓ | — | — | — | — | ✓ |
| Prompt anti-pattern table | ✓ | — | — | — | — | ~ |
| No two agents on the same files | ✓ | — | — | — | — | ✓ |
| Post-return cross-agent conflict scan | ✓ | — | — | — | — | — |
| Post-return full-suite run | ✓ | — | — | — | — | ~ |
| Spot-check for systematic agent error | ✓ | — | — | — | — | ~ |
| Review gate / bounded fix loop / breaker | — | — | — | — | — | ✓ |

### Guardrails

| Component | DPA | FDB | UGW | RMC | GGC | Ours |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Enforced destructive-git denylist | — | — | — | — | ✓ | ~ |
| PreToolUse Bash hook wiring | — | — | — | — | ✓ | ✓ |
| Block message framing to the agent | — | — | — | — | ✓ | ~ |
| Install-scope choice (project vs global) | — | — | — | — | ✓ | — |
| Settings merge-not-overwrite | — | — | — | — | ✓ | — |
| Post-install hook verification | — | — | — | — | ✓ | — |
| Non-git destructive coverage (`rm -r`, bd, generated files) | — | — | — | — | — | ✓ |
| Prose-level git safety rules | — | ~ | ~ | — | — | ✓ |
| Explicit-staging rule | — | — | — | ✗ | — | ✓ |

`✗` = the skill states the **opposite** (RMC:14 instructs "stage everything").

### Cross-cutting

| Component | DPA | FDB | UGW | RMC | GGC | Ours |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Announce-at-start | — | ✓ | ✓ | — | — | — |
| Rationalization table | ~ | ✓ | ✓ | — | — | ✓ |
| Quick-reference table | — | ✓ | ✓ | — | — | ~ |
| Worked example / session record | ✓ | — | — | — | ~ | — |

---

## Shared-component differences

### Detect existing isolation before creating (UGW ✓ · FDB ~ · Ours —)

UGW runs the check as a **precondition on creation**: `GIT_DIR`/`GIT_COMMON`
compared, then a submodule guard, then "Do NOT create another worktree"
(`UGW:16-37`). FDB runs the *same two commands* but for a different purpose —
to pick which menu to show and which cleanup applies (`FDB:28-44`) — and it has
no submodule guard, so a submodule checkout would be classed as a worktree and
routed to provenance-based cleanup. **UGW is stronger** because it is the only
one whose detection cannot misclassify a submodule. That matters concretely
here: this repo keeps every reference harness as a submodule under
`reference_harnesses/` (`invariants.md:7-9`), so the unguarded form misfires on
a large fraction of this tree.

### Native tool preferred over raw git (UGW ✓ · Ours ~)

UGW states the preference *and* its failure mode: a native tool owns placement,
branching, and cleanup, so bypassing it "creates phantom state your harness
can't see or manage", and it labels this the #1 mistake (`UGW:51-57`, `:164`).
Ours has the *capability* mapped — `isolation` as a subagent definition field
(`agent-matrix:83`) — and one raw-git instruction pointing the other way:
code-review tells a reviewer to "check it out into a temporary `git worktree`"
(`code-review:51-54`) with no mention of the native tool. **UGW's is stronger**:
ours names a config field without a usage rule, and our one usage rule
prescribes exactly the mechanism UGW argues against.

### Clean-baseline check before work starts (UGW ✓ · Ours ~)

UGW runs the **test suite** before implementing and reports failures with an
explicit ask (`UGW:121-132`); the rationale is attributability — "a dirty
baseline makes every later failure ambiguous" (`:167`). Ours records two
different baselines: `SCOPE_BASE` as a diff anchor (`task-engine:58-60`) and
`baseline-dirty.txt` as a file-ownership record (`workstream-mode:18-20`).
Neither establishes that the tests were green. **UGW is stronger on this axis
alone**; ours is stronger for the purposes it actually serves (diff scoping and
not committing the user's edits), so the two are complementary rather than
competing.

### Green suite before integrating (FDB ✓ · Ours ~ · RMC ~)

FDB makes it a hard gate with the menu behind it and a rationalization row
closing the obvious loophole: "tests passed earlier this session" → "a green run
only proves the tree it ran on" (`FDB:14-26`, `:193`). Ours gates *completion*
rather than integration — the phase discipline gate plus exit criterion plus the
verification-before-completion skill (`execution:88-95`) — and then explicitly
does **not** integrate (`execution:96-98`, "do not commit unless asked"). RMC
runs checks but positions them as post-resolution repair, not as a gate on
proceeding (`RMC:12`). **FDB is stronger at the integration boundary**, which is
precisely the boundary our harness declines to cross; the gap is real but only
bites once a human or a workstream commit takes the work further.

### Re-verify after the merge (FDB ✓ · RMC ~)

FDB re-runs the suite **on the merged result** and, on red, stops with the
worktree and branch intact and nothing pushed (`FDB:98-107`). RMC also runs
checks after resolving (`RMC:12`), but its instruction is "fix anything the
merge broke" and then finish — there is no stop-and-preserve state, and Step 3's
"never `--abort`" (`RMC:10`) removes the retreat FDB implicitly leaves open.
**FDB is stronger**: it separates "the merge is wrong" from "the merge needs
repair", and preserves the recoverable state while that question is open. RMC's
combination — always resolve, never abort, then fix breakage — assumes the merge
is always repairable in place.

### Typed-confirmation destructive path (FDB ✓ · Ours ~)

FDB requires the literal string `discard`, after printing branch, commit list,
and worktree path, and refuses paraphrases: "'Yeah, get rid of it' counts as
confirmation" → "Only the typed word `discard` authorizes deletion"
(`FDB:132-157`, `:196`). Ours is enforcement-based rather than
confirmation-based: the hook blocks `git branch -D`, `reset --hard`, `clean -f`
and tells the agent to ask (`hook:19-29`, `:33`). **These are different
mechanisms, and ours is stronger for what it covers** — a hook cannot be
rationalized away, while a typed-confirmation rule lives only in the agent's
attention. But ours has no *content* requirement: nothing makes the agent
enumerate what will be destroyed before asking. FDB's enumeration step is the
borrowable half.

### Intent recovery from primary sources (RMC ✓ · Ours ~)

RMC requires reading commit messages, PRs, and original issues to recover why
each side changed, before touching a hunk (`RMC:8`). Ours has the same *instinct*
in a different place: the final review's simplification look invokes
Chesterton's Fence — answer why the code is the way it is, `git blame` if
needed, can't answer → don't touch (`task-engine:199-205`). **RMC's is stronger
for conflicts** because it is a precondition on every hunk rather than a caveat
on an optional pass, and it names the sources to consult. Ours is stronger as a
general refactoring brake. They do not collide; RMC's belongs to a phase our
harness has no coverage of at all.

### Invent no new behaviour (RMC ✓ · Ours ~)

RMC forbids it flatly at the hunk level (`RMC:10`). Our nearest equivalents are
scope rules, not conflict rules: "every changed line should trace directly to
the user's request" (`.claude/rules/core/03-ak-guidelines.md:45`) and the
implementer's "stay inside the assigned scope" (`implementer:15`). **RMC's is stronger in context**: a
conflicted hunk is exactly where an agent's synthesis instinct produces a third
variant that neither branch contained and no reviewer asked for, and a general
scope rule does not obviously bind there.

### Finish the merge (RMC ✓ · Ours ✗ on staging)

RMC:14 says "Stage everything and commit." Ours forbids that shape twice at
invariant strength (`invariants.md:17-18`, `CLAUDE.md:83`) and once at agent
level (`implementer:30`), and the hook blocks the adjacent destructive forms.
**Ours is stronger and this is a genuine contradiction, not a variant** — any
borrow of RMC must rewrite Step 5 to stage the conflicted paths explicitly.
Note the practical wrinkle: `git add -A` is idiomatic for finishing a merge
precisely because the conflict set is already known to git, so the rewrite
should name `git add <conflicted paths>` from `git diff --name-only
--diff-filter=U` rather than simply forbidding the step.

### Independence test before fanning out (DPA ✓ · Ours ~)

DPA gates fan-out on a stated test rendered as a decision graph — independent?
parallelizable? no shared state? — with both a use-when and a don't-use list
(`DPA:18-45`, `:129-134`). Ours has the *conclusion* without the test: "no
parallel implementers on the same files" (`01-delegation.md:9`,
`task-engine:217`) and decomposition that leaves independent stages unchained
"so it can run in any order or in parallel" (`decompose:64-65`), while the
unattended runner goes sequential by design regardless (`workstream-mode:8-11`).
**DPA is stronger** because ours states a prohibition and a permission but never
a procedure for deciding between them; nothing in our harness tells a
coordinator when two implementers may run at once, so in practice they never do.

### Per-agent packet (DPA ✓ · Ours ✓, ours stronger)

DPA's packet is four fields — scope, goal, constraints, expected output
(`DPA:58-65`) — with a prompt rubric and anti-pattern table around it
(`:87-127`). Ours is a superset: brief path, report path, owned **and
forbidden** files, invariants, required tests, verification commands, commit
policy, test-first flag, trust-boundary flag, and the rule that paths are passed
rather than contents because pasted content stays resident in coordinator
context (`task-engine:73-84`). **Ours is stronger** on completeness and on
context economy; DPA's only distinctive contribution here is the ❌/✅ framing,
which our rationalization table (`execution:120-129`) already covers in a
different register.

### Post-return integration close (DPA ✓ · Ours ~)

DPA closes with four steps: read each summary, check whether agents edited the
same code, run the full suite, spot-check because "agents can make systematic
errors" (`DPA:79-86`, `:161-168`). Ours has the *review* half far stronger —
spec and code reviewers, a bounded fix loop, a breaker, and a whole-scope final
review that also triages deferred and parked findings
(`task-engine:118-208`) — and it explicitly refuses to trust the implementer's
report. But it has no **cross-agent conflict scan**, because it never runs two
implementers at once. **Ours is stronger per agent; DPA is the only one with a
between-agents step.** That single missing check is what would have to exist
before our engine could safely fan out.

### Denylist matching mechanism (GGC ✓ · Ours ~, ours stronger)

GGC loops `grep -qE "$pattern"` over unescaped patterns (`block-dangerous-git.sh:18-19`)
against a list that includes `git checkout \.` and `git restore \.` — the
backslashes are escaped in the array (`:12-13`) but `git clean -f` and
`git push` are not anchored, so `git push` blocks every push including
`git push --dry-run`, and regex evaluation of user-supplied text is a needless
surface. Ours uses fixed-string `grep -qF` (`hook:32`), which cannot
over-match, and restricts the push block to `--force`/`-f` (`hook:19-21`) so
ordinary pushes remain possible under the explicit-approval rule
(`CLAUDE.md:83`). **Ours is stronger on precision**; GGC is broader on `git
push` alone, which is a policy difference rather than a quality one — GGC's
author wants pushes blocked outright, ours wants them approved.

### Block message framing (GGC ✓ · Ours ~, ours stronger)

GGC emits "The user has prevented you from doing this"
(`block-dangerous-git.sh:20`), which terminates the agent's reasoning: nothing
suggests a legitimate next move, so an agent that genuinely needs the operation
either abandons it or looks for a workaround. Ours emits "Ask the user before
proceeding" (`hook:33`), and each specialised guard states *why* and *what
instead* — the bd guard explains the Dolt wipe and the recovery dependency
(`hook:45`), the mirror guard names the sanctioned writer and the `BD_RENDER=1`
route (`hook:85`). **Ours is stronger**: prohibition-plus-alternative is the
same shape the ledger already credited when adopting the worktree escape hatch
from `requesting-code-review` (`ledger.json:628-631`).

### Post-install verification (GGC ✓ · Ours —)

GGC ends by piping a crafted payload into the installed script and asserting
exit 2 plus a stderr BLOCKED line (`SKILL.md:87-95`). We have no equivalent:
`verification.md`'s checkable subset covers manifests parsing, `bash -n` on
changed shell scripts, `py_compile`, machine-local paths, and the skill catalog
(`invariants.md:25-27`) — `bash -n` proves our hook *parses*, never that it
*blocks*. **GGC is stronger here**, and this is the one component in that skill
we do not already own in better form.

### Rationalization tables (FDB ✓ · UGW ✓ · Ours ✓ · DPA ~)

FDB (9 rows) and UGW (5 rows) both pre-refute excuses tied to the exact step
they follow, naming the excuse in the agent's own voice
(`FDB:189-201`, `UGW:159-167`). Ours does the same for execution discipline
(`execution:120-129`). DPA's is the same idea in a weaker register — a ❌/✅
prompt-quality table (`DPA:115-127`) that critiques artifacts rather than
motives. **FDB's is the strongest in the set** because each row pairs a specific
temptation with a mechanical reason it fails, and several of its rows
("force-push will fix it", "tests passed earlier this session") name failures our
Git Safety prose asserts against without explaining.
