# Store restructure — orchestration contract

How epic `cr-nwy9` is run, start to finish. The orchestrator reads this at the start
of every session on this workstream, then `state.md`, then nothing else until a
trigger in §5 fires. Roadmap: `roadmap.md` (design, R1–R13, slices S0–S7).

## 1. Scope

Everything in the roadmap, in order: **S0** rename → **S1** export integrity →
**S2** derived closed → **S3** identity → **S4** contractor in the ledger → **S5** tracker
port → **S6** cutover → **S7** checkpoint export (`cr-h498`, promoted from follow-up
to final slice) → **close-out** (§7). Done means: every slice bead closed, the branch
merged to `main` as one, roadmap cleaned to a record, guide and ADR written.

## 2. Roles

| Role | Who | Effort | How spawned | Sees |
|---|---|---|---|---|
| Orchestrator | this session (Fable) | — | — | briefs, shaped reports, verdicts. Not diffs, not logs, not test output |
| Implementer | Opus 5 | **medium** | `Agent` type `implementer`, fresh per slice and per fix round | the brief, the roadmap section, the acceptance rows, the repo |
| Reviewer | Opus 5 | **high** | `claude -p --model claude-opus-5 --effort high`, read-only, fresh per slice | the diff range, the roadmap section, the bead, the repo |
| Critic | Fable 5.1 | **high** | `claude -p --model claude-fable-5-1 --effort high`, read-only | **only at the two gates in §6** |

No other model, no other effort level, no standing agents. Never Terra, Sol or
Codex on this epic. Implementers never run `bd` against the repo database; test labs
never touch `.beads/`.

## 3. The orchestrator's token discipline

The orchestrator is the only party with cross-slice context; that is the only thing it
spends tokens on. Concretely:

1. **Answers, not evidence.** The implementer runs the gate and reports the exit
   status and failing test *names*. The reviewer reads the diff and reports numbered
   findings. The orchestrator reads neither the diff nor the output.
2. **One brief per dispatch, ≤60 lines**, pointing at roadmap sections and bead ids
   rather than restating them. No session history in a brief.
3. **Report templates are mandatory** (§4). A report that does not follow the template
   is sent back once with the template, not read around.
4. **Fix rounds are accepted by probe, not re-review.** Full skepticism on the first
   review of a slice only; a fix round is accepted when the reviewer's own probe (the
   failing case it named) passes and the gate is green. ≤3 rounds, then escalate.
5. **≤10 lines with a covering test → the orchestrator edits inline.** Everything
   else is dispatched.
6. **The orchestrator never runs the canonical gate itself.** If a claim needs
   checking, it asks a fresh implementer to run one command and report one line.

Health metric: context re-sent per call. Above ~250k, stop and shape the brief down.

## 4. The per-slice loop

```text
1. brief         orchestrator writes scratchpad/briefs/S<n>.md from the roadmap row + bead
2. implement     Opus 5 medium, worktree wf/store-restructure, runs the gate, commits
                 on the branch with explicit files, returns the IMPLEMENTER REPORT
3. review        Opus 5 high, read-only over the slice's commit range, returns the
                 REVIEWER REPORT
4. route         orchestrator: SHIP → 6; fixes → 5; REJECT or trigger (§5) → read + decide
5. fix           fresh Opus 5 medium with the numbered findings only; back to 4 by probe
6. close         orchestrator closes the bead with the report's gate line as reason,
                 updates state.md, moves on
```

**IMPLEMENTER REPORT** (≤12 lines, nothing else):

```text
bead: cr-nwy9.N            commits: <first>..<last> on wf/store-restructure
files: <count> changed, <count> tests added/changed
gate: uv run pytest -q -m "not bd and not live" → exit <n>, <passed> passed, <failed> failed
failing: <test names, or none>          (flaky-known: test_profiles_steer[*])
acceptance: <each roadmap row → met | not met | not testable, one word each>
open: <questions the brief did not answer, or none>
NOTICED BUT NOT TOUCHING: <or none>
```

**REVIEWER REPORT**: numbered findings, each `BLOCKER|MAJOR|MINOR`, `file:line`, one
sentence why, one failure scenario, `verified|inferred`; then `VERDICT: SHIP | SHIP
WITH FIXES | REJECT` with two sentences. ≤1500 words. Reviewers never edit.

Acceptance tests go first whenever the roadmap row names the slice's public seam
(S1 export bytes, S2 `closed()`, S3 id grammar, S5 the port): a first implementer
turns the acceptance rows into failing tests, a second makes them pass without
editing the tests.

## 5. When the orchestrator reads an artifact

Only on one of these, and then only the artifact named:

| Trigger | Read |
|---|---|
| gate red after two fix rounds | the failing test names + the implementer's `open:` line, then a diagnostician subagent returns one paragraph |
| reviewer says BLOCKER or REJECT | that finding's `file:line` — verify the claim in code before acting on it |
| implementer report and reviewer report contradict | both reports' relevant lines, nothing more |
| any party proposes changing a decision R1–R13 | the roadmap decision row; then stop and ask the user (§8) |
| the report's `open:` line is non-empty | that line |
| a Fable gate (§6) | Fable's full report — the one time the orchestrator reads everything |

Everything else is taken at its word and checked by the next stage's gate.

## 6. The two Fable gates

Fable 5.1 high, read-only, fresh context, exactly twice. Findings go to beads as
children of the slice, never fixed in chat.

**Gate A — after S0.** Brief: the rename is complete and correct. Attack: any old name
left outside the sanctioned notes; a renamed identifier that changed meaning; CLI,
config-key, log-event and wire-key surfaces; the guide and `diagrams.md` still
coherent; the run-ledger roadmap and ADRs untouched beyond their naming note. Verdict
blocks S1.

**Gate B — after S7.** Brief: the whole design, as built, against R1–R13 and the
roadmap's stated evidence for R6. Attack: closure monotonic under a schema bump; a
task rebuilt in a clone at another path; a full cycle with `NullTracker`; claim-first
window; a shipped task refusing retry; abandoned tasks retiring; no `BackendKind`,
no `epic_segment`, no `COUNT(roots)` anywhere; ADR 0006 and guide 08/11 truthful to
the code. Verdict blocks the merge.

## 7. Close-out

After Gate B ships:

1. `roadmap.md` becomes a record: status `DONE <date> <merge commit>`; §7 open
   questions each resolved inline or moved to a bead and linked; nothing left that
   says "decide before".
2. `state.md` marked DONE; `orchestration.md` left as is — it is the record of how.
3. `.claude/project/docs-index.md` row updated; `.claude/project/learnings.md` gets
   only patterns that recurred across ≥2 slices.
4. Merge `wf/store-restructure` to `main` as one (user confirms target); re-run the
   canonical gate on the merged result; push only on the user's word.
5. Close `cr-nwy9` with the merge commit and the two Fable verdicts as the reason.

## 8. What reaches the user

Only these, each as one short message with a recommendation:

- a decision R1–R13 needs changing (with the evidence line that forces it)
- a Fable gate returns REJECT
- three fix rounds failed on one slice
- merge target confirmation, and push
- anything destructive outside the worktree

Slice completions are one line each in `state.md`, not a message. A session that ends
mid-slice writes `state.md` first.

## 9. Standing constraints (unchanged)

Stage explicit files only; no `add .`, `-A`, `--no-verify`, force-push, `reset --hard`,
`clean`, `restore`, `checkout` rewrites. Commits via `git -c core.hooksPath=/dev/null`.
No amend. `scratchpad/` never committed. No machine-local absolute paths in repo files.
`reference_harnesses/` and `reference_tools/` read-only. Beads writes carry `--actor`.
Do not weaken `scripts/verify-dws-pilot.py`.
