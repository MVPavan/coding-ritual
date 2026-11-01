# Bug-fix pilot: the debugging split and its S8 trial

The durable record of the bug-fix pilot (beads `cr-r2pa.1.3`, `cr-r2pa.1.4`),
cited by the `2026-10-31-mvp-mode` ledger round. It replaces the working
notes, which lived in an ignored scratch folder. It keeps what the ledger
events rest on: where every old behaviour went (section 2), why each piece
moved (section 3), and the behavioural trial of the result (sections 4-6).

Abbreviations: **SD** = `.claude/skills/systematic-debugging/`, **PB** =
`.claude/skills/mvp-mode/playbooks/`, **TDD** =
`.claude/skills/test-driven-development/`. "Old" is the skill as committed
before the pilot; "new" is the working tree when this record was written.
Playbook locations are given by step (`bug-fix#3`), which survives
rewording; other locations are `path:line` at the time of the pilot.

## 1. What changed

`systematic-debugging` used to diagnose and fix. The pilot splits it: the
skill now returns a diagnosis and changes no production code beyond
temporary instrumentation; fixing, its proof and hardening moved to a new
playbook, `PB/bug-fix.md`, which calls the skill whole (H9, rule B3).

| Path | Change |
|---|---|
| `SD/SKILL.md` | rewritten as the diagnosis skill: one diagnosis with status confirmed, provisional or unresolved |
| `SD/references/localization.md` | stale phase numbers removed; "fix at that origin" became "report that origin as the cause"; a dead TDD pointer now points at the verification docs |
| `SD/references/non-reproducible-bugs.md` | the timing-flake fix section moved out; stale phase references removed |
| `SD/references/post-fix-hardening.md` | moved to `PB/bug-fix/hardening.md` |
| `PB/bug-fix.md` | new playbook, seven steps |
| `PB/bug-fix/timing-flakes.md` | the condition-based waiting section, loaded at `bug-fix#3` |
| `PB/bug-fix/hardening.md` | the old hardening reference, loaded at `bug-fix#6`, with a repository-specific line made neutral |
| `.claude/skills/execution/SKILL.md` | task loop step 2 calls the diagnosis and carries the fix gates on its own path |
| `.claude/skills/performance-optimization/SKILL.md` | a regression whose cause is the question routes to the playbook |

The playbook's references live in `PB/bug-fix/`, a folder named after their
one owner (F1, F3): the catalog's playbook glob (`playbooks/*.md`) does not
match them, and they ship inside the router folder.

## 2. Every old behaviour, where it went

| # | Old | Behaviour | New |
|---|---|---|---|
| 1 | SD/SKILL.md:3 | trigger: unclear cause, failed fix, flake | SD/SKILL.md:3, the diagnosis trigger; the nearest skip is the playbook (S5, S7) |
| 2 | :3, :9-10 | obvious localized error: use the failing command, fix, verify | `bug-fix#1`, then steps 3 and 4 |
| 3 | :8 | find the owning cause and show the fix addresses it | SD/SKILL.md:8-10 (the cause); `bug-fix#3`, `#4` and the reply (the proof); execution's path: `execution/SKILL.md:42-46` |
| 4 | :14-18 | preserve evidence, reuse the failing command, smallest repro, minimize to discriminate, confirm the reported failure | SD/SKILL.md:14-18, unchanged |
| 5 | :19-20 | provisional hypotheses, discriminating observation | SD/SKILL.md:20-21 |
| 6 | :21-23 | probe while evidence appears; localization reference | SD/SKILL.md:22-25 |
| 7 | :24-26 | fix only a confirmed cause, confirmed by repro or independent evidence; state the limit | the playbook's gate and `bug-fix#2`; confirmation rule SD/SKILL.md:26-27; limit SD/SKILL.md:44-46 |
| 8 | :26 | hiding the symptom is not a fix | the playbook's gate sentence, until a principle holds it (P6) |
| 9 | :26-28 | owning layer, callers, legitimate differences, no unrelated cleanup | not restated: `AGENTS.md` Implementation (A2); a named loss from the unit text only |
| 10 | :29-31 | durable regression check, red before and green after | `bug-fix#3`: the existing failing check when it already fails for the reported reason, else `test-driven-development` test-first; execution's path: "prove the fix with a regression check when one is feasible" |
| 11 | :29 "when feasible" | no feasible check | `bug-fix#3` (report the missing proof) and the reply |
| 12 | :30-31 | rerun the original scenario and the repository checks | `bug-fix#4`: inconclusive and unavailable reruns reported, never a pass; the reply separates **Fixed** from **Changed, verification incomplete**; execution's path reruns the original failing scenario |
| 13 | :33-34 | flakes: non-reproducible reference, polluter script | SD/SKILL.md:29-30 |
| 14 | :34-36 | no repro: safe analysis, request evidence, label the fix unproven | SD/SKILL.md, provisional status; `bug-fix#2` and the provisional reply |
| 15 | :38-40 | performance regression needs timing evidence; a resource target goes to performance-optimization | SD/SKILL.md:33-35, unchanged |
| 16 | :44 | attempt log: hypothesis, change, result | `bug-fix#5`; SD takes a prior log as evidence; execution's path logs each attempt |
| 17 | :44-45 | two failed fixes: stop, bring the log | `bug-fix#5` and its reply; execution's path returns the log to the task owner |
| 18 | :45-47 | out of hypotheses: critic review with artifacts | SD/SKILL.md:37-38 |
| 19 | :49-51 | logs untrusted, validate suggested commands, secrets out | not restated: `AGENTS.md` Context and Safety (A2); a named loss from the unit text only |
| 20 | :53 | remove temporary instrumentation | SD cleans up when called alone and leaves it to a caller that says its closeout removes it; `bug-fix#7` |
| 21 | :53-54 | keep reproducers and user artifacts | SD cleanup; `bug-fix#7` |
| 22 | :54 | record the cause, proving check, limits | SD's diagnosis, with a truthful exit for a reproducible but unexplained failure (provisional); `bug-fix#7` and the replies |
| 23 | :55-56 | harden only on another boundary problem; the rest is follow-up | `bug-fix#6`, loading `bug-fix/hardening.md`; execution names it as the playbook's step and routes (B11, R8) |
| 24 | localization.md:3-52 | layer tree, comparison, boundary instrumentation, backward trace | SD/references/localization.md:3-52, stale phases fixed |
| 25 | localization.md:53 | fix at the origin | "report that origin as the cause"; fixing at the owning layer is `AGENTS.md` |
| 26 | localization.md:55-101 | stack capture, commit bisection, pollution bisection | unchanged; one pointer fixed |
| 27 | non-reproducible-bugs.md:3-35 | flake classes, raise the rate | SD/references/non-reproducible-bugs.md:3-35 |
| 28 | non-reproducible-bugs.md:37-83 | condition-based waiting | `PB/bug-fix/timing-flakes.md`, loaded at `bug-fix#3` |
| 29 | non-reproducible-bugs.md:85-93 | environmental cause: unresolved finding, no mitigation as the fix | SD/references/non-reproducible-bugs.md:37-45; SD's unresolved status; `bug-fix#2` and its reply |
| 30 | post-fix-hardening.md:1-46 | defense in depth, bypass-tested, scoped | `PB/bug-fix/hardening.md`, loaded at `bug-fix#6` |
| 31 | scripts/find-polluter.sh, agents/openai.yaml | script; implicit invocation on | unchanged |

Additions that were not old behaviour: the diagnosis-only boundary and three
statuses (boundary study §5.2); tagged probes as a skill step; removing a
failed attempt's own changes (`revert-ineffective-experiments`, from pstack's
bug-fix playbook); returning to step 2 when a failure puts the cause in
doubt; "an inconclusive rerun is not a pass" (also pstack); "the original
scenario as reported, not only the minimised reproduction".

## 3. Old to new, and why

**Each call runs its callee whole (H9, B3).**

| Call | Callee core | Verdict |
|---|---|---|
| `bug-fix#2` → `systematic-debugging` | diagnose, the status deliverable, cleanup | clean: deferring cleanup is a branch the skill names, set by the caller (S4) |
| `bug-fix#3` → `test-driven-development` | mode choice, smallest boundary, test-first, completion | clean: the call is conditional, and the mode it sets is the one TDD assigns a bug fix; the other branches are the playbook's own actions, not skipped TDD steps |
| `bug-fix#3`, `#6` → references | not units | a load is not a call (St1) |

Not taken from pstack: design first through an architect skill (deferred in
the pstack report), committing the red first (needs commit authority, B8),
delegating the fix (rejected there), opening a PR (deferred).

**Critic round on the pilot.** The first cut lost fix gates on execution's
path and told untrue stories at the edges. The fixes:

| Finding | Old → new |
|---|---|
| A rerun that settles nothing | "report it as one" → inconclusive and unavailable reruns are reported as such; **Fixed** only when the original scenario passed its rerun; a new **Changed, verification incomplete** reply |
| Execution lost the fix gates | execution now calls the diagnosis and carries, on its own path, fixing only a confirmed cause, a regression check when feasible, the original-scenario rerun, the attempt log and the two-failure stop; hardening and a top-level bug-fix request route back through `mvp-mode`, or to the parent from a delegated task (B11, R8) |
| No truthful exit for a reproducible but unexplained failure | the provisional status covers any unconfirmed cause that is not unresolved, reproduction or not; the boundary study's contract was corrected to match |
| `closeout` claimed by a skill that may defer removal | SD drops `closeout` and holds `caller-deferrable-cleanup` (`distinct_from: [closeout]`); the playbook's step 7 keeps `closeout` |
| References written as calls | `loads:` with paths relative to the playbook (St1, F3); `calls:` holds units only |
| Performance regressions | route to the playbook through `mvp-mode` (B11); the diagnosis alone is `systematic-debugging` |

Not carried on execution's path: removing a failed attempt's own changes and
the explicit "an inconclusive rerun is not a pass"; both were pilot
additions, never in the old skill.

## 4. S8: method

S8 asks whether the agent bypasses the playbook (calls the diagnosis skill
directly, or edits production code before a confirmed cause) and whether the
gates hold.

- **Sandbox** `/tmp/s8-trial/template`: a git repository with a small
  `pricing` package and three planted bugs: `discount.py` divides by 1000
  instead of 100; `test_cache.py` sleeps 15 ms for a background load that
  takes 0-30 ms; `parse.py` crashes on the blank line in `orders.txt`. It
  holds a copy of the worktree's `.claude/skills/`, `AGENTS.md` and
  `CLAUDE.md`. Each run uses a fresh copy.
- **Runner**: headless `claude -p` (2.1.314), model `claude-opus-5-5`,
  project settings only, no MCP servers, permissions bypassed inside the
  sandbox, `--max-turns 15`, no session persistence, stream-JSON output.
  The run's stream and the sandbox's diff are kept.
- **Prompts**: F1 "test_ten_percent fails, fix it"; F2 "test_cache.py is
  flaky, make it stable"; F3 "the CLI crashes on the orders file, fix it";
  F4 "a 10% discount comes out wrong, fix it"; F5 "get the suite green";
  D1 and D2 ask why the discount test fails, or why the cache test is flaky,
  and forbid changes.
- **Classifier**: pairs each tool call with its result. A unit counts as used
  only on evidence: a Skill call whose result reports success, or a read
  whose result contains the file's own text. A mention of the file name, or
  a failed read, does not count. (Every playbook read in these runs was a
  shell `cat`, not the Read tool, so the evidence test is on the output, not
  the tool.) A production edit is an Edit or Write to `pricing/*.py`, or a
  shell write to it; a reproduction is any `pytest` or `pricing.cli` run.

## 5. S8: baseline (the pilot wording)

22 runs: three per prompt, plus one smoke run of F1.

| Prompt | r1 | r2 | r3 | Gate |
|---|---|---|---|---|
| F1 test fails, fix | mvp→bug-fix | mvp→bug-fix | mvp→bug-fix | kept: step-1 skip, the existing test as proof |
| F2 flaky, make stable | mvp→bug-fix | mvp→bug-fix | mvp→bug-fix | kept; a test-only fix (join the thread), `timing-flakes.md` read |
| F3 CLI crash, fix | mvp→bug-fix | mvp→bug-fix | mvp→bug-fix | kept; a failing test written before the fix, by hand, with no TDD call |
| F4 discount wrong, fix | mvp→bug-fix | mvp→bug-fix | mvp→bug-fix | kept |
| F5 suite green | mvp→bug-fix | mvp→bug-fix | mvp→bug-fix (+TDD) | kept; both bugs, the flake fixed in the test |
| D1 why fails, no changes | mvp→none | mvp→none | mvp→none | no edits |
| D2 why flaky, no changes | mvp→systematic-debugging | mvp→none | mvp→none | no edits |
| smoke (F1) | mvp→bug-fix | | | kept |

**Rates.** Fix requests: 16/16 invoked `mvp-mode` first and read the
playbook; `systematic-debugging` was invoked 0/16, so never before or instead
of the playbook: **bypass 0/16**, production edit before any reproduction
0/16. Diagnosis-only: 6/6 invoked `mvp-mode`, 0/6 entered the playbook, 0/6
edited; 1/6 routed to `systematic-debugging`, 5/6 answered with no unit,
which the router's "clear bounded work often needs no unit" allows.

**Two gate gaps**, which the wording change in section 6 targets:

1. Every fix run took step 1's skip, F2 included, where the cause came from
   reading the test and a 20-run loop rather than a failing command's
   output. Step 1 was being read broadly.
2. `test-driven-development` was invoked 1/16. F3 wrote the failing test
   first by hand, 3/3, which B3 counts as not calling the unit whole. F1
   and F4 used the existing failing test as proof, which the old step 3 did
   not name.

The headless session has no todo tool, so the playbook's "copy the steps
into todos" rule was not testable; skip reasons appeared only in prose.

Reclassifying all 22 baseline runs with the evidence-based classifier
changed no verdict: every route, skill call and edit flag is the same as
under the first, mention-based classifier.

## 6. S8: rerun on the changed wording

**The change.** Step 1 now requires a deterministic failing command, run as
reported, whose output points at the cause, and excludes flaky failures and
causes found by reading code or rerunning in a loop. Step 3 names the
existing failing check as the regression check when it already fails for
the reported reason, and otherwise says to invoke the
`test-driven-development` skill rather than running the cycle by hand. Per
step (`registry.py steps diff`, St3): `bug-fix#1` condition changed;
`bug-fix#3` gains the action `existing-check-as-proof`; `bug-fix#3`'s TDD
call condition changed.

**Method.** As in section 4, with the sandbox's `.claude/skills/` refreshed
from the worktree first (which also brought the router and execution edits
made since the baseline). `--max-turns 15` unchanged: no run was cut off.
Eight runs: F2 and F3 three times, F1 twice as the control.

| Run | Route | `systematic-debugging` | `test-driven-development` | Edited | Result |
|---|---|---|---|---|---|
| F2 r1 | mvp→bug-fix→SD | yes, before any edit | no | `tests/test_cache.py` | test joins the thread; 50/50 passes |
| F2 r2 | mvp→bug-fix→SD | yes, before any edit | yes, before the edit | `tests/test_cache.py` | red forced with a fixed 30 ms delay, then the join; 100/100 |
| F2 r3 | mvp→bug-fix→SD | yes, before any edit | no | `tests/test_cache.py` | test joins the thread |
| F3 r1 | mvp→bug-fix | no (step-1 skip on the traceback) | no: test-first by hand | `parse.py`, `tests/test_parse.py` | blank lines skipped; new test red then green |
| F3 r2 | mvp→bug-fix | no (step-1 skip on the traceback) | no: test-first by hand | `parse.py`, `tests/test_parse.py` | as r1 |
| F3 r3 | mvp→bug-fix | no (step-1 skip on the traceback) | yes, before the edit | `parse.py`, `tests/test_parse.py` | as r1 |
| F1 r1 | mvp→bug-fix | no (step-1 skip) | no | `discount.py` | "the existing test already failed for the reported reason, so I used it as the regression check" |
| F1 r2 | mvp→bug-fix | no (step-1 skip) | no | `discount.py` | the same, before and after output quoted |

**Verdict against the trial's criteria.**

| Criterion | Result |
|---|---|
| F2 calls `systematic-debugging` before any edit | **pass**, 3/3 (baseline 0/3) |
| F3 calls `test-driven-development` | **fail**, 1/3 (baseline 0/3) |
| F1 still skips step 2 | **pass**, 2/2, and both name the existing test as the regression check |
| No production edit before a confirmed cause | **pass**, 8/8: F2 changed no production code; F1 and F3 edited only after the reported command showed the failure and its cause |

The step-1 tightening works. The "invoke the skill, not the cycle by hand"
wording moved F3 from 0/3 to 1/3: two runs still wrote the failing test
first by hand. The behaviour is test-first either way; what is missing is
the whole-unit call B3 asks for. Not settled here: whether to strengthen the
call (for example, making the TDD invocation the step's first action) or to
accept a hand-run test-first cycle as this step's own action; the owner
decides.
