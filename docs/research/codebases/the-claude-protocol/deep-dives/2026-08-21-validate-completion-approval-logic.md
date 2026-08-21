Target(s): reference_harnesses/The-Claude-Protocol
Snapshot: af754ef (clean — verified at promotion, see Verification performed)   Date: 2026-08-21
Mode: deep-dive   Builds on: none

# How does `validate-completion.sh` decide to approve a completion?

## Question

How does The-Claude-Protocol's `validate-completion.sh` hook decide to
approve a completion? Asked directly against this one mechanism (no capability
survey or architecture map was authorized or run first); it matters because
this is the enforcement gate the harness relies on to keep supervisor-agent
work traceable (bead status, worktree, push, comment) before a subagent's
turn is allowed to end.

## Answer

**Confidence: high, `SOURCE-TRACED`.** The hook is registered unconditionally
on the `SubagentStop` event (no matcher) and runs after every subagent turn
(`templates/settings.json:52-58`). It approves in two very different ways:

1. **Fail-open / not-applicable exits** — most subagents hit one of these and
   are approved without any of the seven verification checks running at all:
   no agent transcript found, subagent type not "supervisor"-like and the
   response lacks both completion markers, or subagent type contains
   `"worker"` (unconditional exemption, checked before any real check runs).
2. **Full verification pass** — for a subagent that is (or looks like) a
   supervisor, it must clear seven sequential gate checks in order (bead
   comment logged, worktree exists, worktree clean, branch pushed if a remote
   exists, bead status is `inreview`, response ≤15 lines/≤800 chars). The
   *first* failing check blocks and exits immediately with a reason; only if
   all seven pass does it reach the final `{"decision":"approve"}` line.

There is no scoring or aggregation — it is a strict AND of gates, first
failure wins, and several early exits bypass the gates entirely by design
(fail-open on missing data, explicit `worker` exemption).

## Trace

Source: `templates/hooks/validate-completion.sh` (this is the template
copied to a consuming project's `.claude/hooks/validate-completion.sh`; this
harness repo's own `.claude/hooks/` only carries `block-branch-for-epic-child.sh`,
i.e. the repo does not currently dogfood this specific hook on itself —
`PRESENT`, not traced further, out of scope for this question).

Registration: `templates/settings.json:52-58` — `SubagentStop` event, no
`matcher` key, so it fires for every subagent stop, command
`.claude/hooks/validate-completion.sh`. Documented consistently in
`SKILL.md:255`, `skills/create-beads-orchestration/SKILL.md:255`, and
`docs/memory-architecture.md:103` ("SubagentStop hook (verifies work
completion)") — docs and source agree here (`WIRED`).

Execution order in `validate-completion.sh`:

1. **`:6-9`** — reads the hook's stdin JSON once (`INPUT=$(cat)`), pulls
   `agent_transcript_path`, `transcript_path` (the *main* orchestrator
   transcript), and `agent_id` via `jq -r ... // empty`.
2. **`:11`** — fail-open gate 1: if `agent_transcript_path` is empty or the
   file doesn't exist, immediately `echo '{"decision":"approve"}'` and
   `exit 0`. No further checks run.
3. **`:14-17`** — pulls the *last* assistant text block out of the last 200
   lines of the agent transcript (`tail -200 | jq -rs '...] | last'`),
   suppressing jq errors to `""`. This becomes `LAST_RESPONSE`, the only text
   several later checks look at.
4. **`:19-29`** (Layer 1, subagent-type detection) — if `agent_id` and the
   main transcript exist, greps the main transcript's raw JSON lines for
   `"agentId":"$AGENT_ID"` to get the `parentToolUseID`, then greps again for
   a line with that tool-use `id` *and* `"name":"Task"` to pull
   `.input.subagent_type` out of the `Task()` call that spawned this
   subagent. Every step is `2>/dev/null`-guarded and chained with `|| true`
   equivalents — any failure just leaves `SUBAGENT_TYPE=""` (explicit
   fail-open comment at `:19`).
5. **`:32-35`** (Layer 2, backup regex detection) — independent of Layer 1:
   does `LAST_RESPONSE` contain a line matching `BEAD.*COMPLETE` and a line
   matching `(Worktree:|Branch:).*bd-`? Counts (`HAS_BEAD_COMPLETE`,
   `HAS_WORKTREE_OR_BRANCH`) default to `0` if the grep/count comes back
   empty.
6. **`:38-43`** — `IS_SUPERVISOR` is true iff `SUBAGENT_TYPE` contains the
   substring `supervisor`. `NEEDS_VERIFICATION` is true if *either*
   `IS_SUPERVISOR` is true (Layer 1) *or* both Layer-2 markers are present
   (`HAS_BEAD_COMPLETE>=1 && HAS_WORKTREE_OR_BRANCH>=1`) — the two layers are
   OR'd, not AND'd, so a non-supervisor whose text happens to contain both
   markers also triggers verification.
7. **`:46`** — fail-open gate 2: if `NEEDS_VERIFICATION` is still false,
   approve and exit. Everything below this line only runs for
   supervisor-shaped or completion-shaped output.
8. **`:49`** — unconditional worker exemption: if `SUBAGENT_TYPE` contains
   `worker`, approve and exit — evaluated *after* the gate-2 skip but with no
   dependency on `IS_SUPERVISOR`/`NEEDS_VERIFICATION` at all. A subagent type
   string that happened to contain both `supervisor` and `worker` substrings
   would still hit this line and be approved unconditionally, bypassing every
   check below (an ordering subtlety, see Contracts and failure modes).
9. **`:53-59`** (Check 1 — completion format) — only for `IS_SUPERVISOR`:
   if either completion marker is missing, block with the reason
   `"Work verification failed: completion report missing."` and the required
   `BEAD ... COMPLETE / Worktree: / Files: / Tests: / Summary:` format.
10. **`:62-64`** — extracts `BEAD_ID_FROM_RESPONSE` via
    `grep -oE "BEAD [A-Za-z0-9._-]+"` on `LAST_RESPONSE` (first match only);
    `IS_EPIC_CHILD` is set if that id contains a `.`, but this flag is never
    read again below (dead value as of this snapshot).
11. **`:67-73`** (Check 2 — bead comment logged) — greps the *entire* agent
    transcript (not just the last response) for a `bd comment` command
    string; blocks with the exact `bd comment {BEAD_ID} "..."` remediation
    if none found. Note the scope mismatch: BEAD_ID (step 10) comes from the
    last response only, while this check scans the whole transcript.
12. **`:76-84`** (Check 3 — worktree exists) — resolves the repo root via
    `git rev-parse --git-common-dir` (so it works from inside a worktree),
    builds `$REPO_ROOT/.worktrees/bd-{BEAD_ID}`, blocks if that directory is
    missing.
13. **`:87-93`** (Check 4 — worktree clean) — `git -C "$WORKTREE_PATH" status
    --porcelain`; any output blocks with a `git add -A && git commit` hint.
14. **`:96-106`** (Check 5 — branch pushed) — only runs if the worktree has
    an `origin` remote configured; if it does, checks
    `git ls-remote --heads origin bd-{BEAD_ID}` and blocks if the branch
    isn't found on the remote. Skipped entirely (no block possible) when
    there is no `origin`.
15. **`:109-117`** (Check 6 — bead status) — `bd show {BEAD_ID} --json | jq
    '.[0].status'`; must equal `inreview` (comment notes "done status not
    supported in bd" — epic children use the same expected status); anything
    else blocks with the exact `bd update ... --status inreview` fix.
16. **`:120-129`** (Check 7 — verbosity) — decodes backslash escapes in
    `LAST_RESPONSE` via `printf '%b'`, counts lines and characters, blocks if
    `>15` lines or `>800` chars, citing the actual counts in the reason.
17. **`:131`** — reached only if none of checks 1–7 exited early:
    `echo '{"decision":"approve"}'`.

## Contracts and failure modes

- **Fail-open by default, not fail-closed.** Every detection step (Layer 1
  type lookup, Layer 2 regex, missing transcript) degrades to "no
  verification needed" rather than blocking on uncertainty — the hook trusts
  absence of evidence as evidence of a non-supervisor subagent. A malformed
  or truncated transcript silently skips enforcement (`:11`, `:19-29`).
- **Worker exemption is absolute and un-gated.** `:49` runs regardless of how
  `IS_SUPERVISOR`/`NEEDS_VERIFICATION` were computed; any `subagent_type`
  containing the substring `worker` (e.g. a hypothetical
  `"supervisor-worker"`) bypasses every check below it. This is a substring
  match, not an exact-type match — a naming collision anywhere in the agent
  roster would silently disable enforcement for that type.
- **Scope mismatch between BEAD_ID extraction and comment check.** BEAD_ID
  (`:62`) is taken only from the last response; Check 2 (`:67`) searches the
  whole agent transcript for *any* `bd comment`, not necessarily one
  referencing that same BEAD_ID. A comment on an unrelated bead would satisfy
  this check.
- **No aggregation of failures.** Each check `exit 0`s on its own first
  failure; a caller sees one reason per hook invocation and must retry to
  discover the next failing check (serial disclosure, not a full report).
- **Verbosity is checked last**, after every state-changing verification
  (bead comment, worktree, push, status) has already passed — a supervisor
  can do everything right and still be blocked purely for response length.
- **`printf '%b'` on model-generated text** (`:120`) interprets backslash
  escape sequences in `LAST_RESPONSE` before counting characters. Narrow
  surface (`%b` only expands backslash escapes, not arbitrary `%s`/`%d`
  format specifiers), but it is executing a decode step over
  untrusted-agent-authored text — noted as a minor hardening gap, not
  exploited further here (no execution attempted, per the trust boundary).
- **No test coverage found** for this hook: `tests/` in this repo contains
  only `test-validate-epic-close.sh`; no `validate-completion` test exists at
  this snapshot (`ABSENT`, ` PRESENT` ceiling not exceeded for a test
  artifact).

## Verification performed

Read (not executed) `templates/hooks/validate-completion.sh` in full,
`templates/settings.json` (hook registration), `SKILL.md`,
`skills/create-beads-orchestration/SKILL.md`, and `docs/memory-architecture.md`
for corroborating documentation; `grep`-searched the whole target tree for
other references to `validate-completion` (none beyond those cited); listed
`tests/` to check for existing coverage. No target script, hook, or `bd`/`git`
subcommand from the target was executed — static reading only, consistent
with the trust boundary (no `EXERCISED` claims here).

**Snapshot caveat (why this artifact is marked provisional):** this agent's
worktree (`.claude/worktrees/agent-a4fc226d09dcf82e4`) has
`reference_harnesses/The-Claude-Protocol` registered as a submodule but not
checked out — the directory is empty inside the worktree, and running `git
submodule update`/`init` there was out of scope (curation rule: never move a
pinned commit without an explicit, separate request; the sandbox also refused
`git` commands whose target reached outside the worktree). The parent
worktree's own git index confirms the pinned commit is
`af754ef63535a416af4894223edda1b2c730d3c2` (`git ls-tree HEAD --
reference_harnesses/The-Claude-Protocol`, run inside the worktree — a
same-repo, no-redirect command). All source content above was instead read
(via the `Read`/`Bash cat` tools, not `git`) from the sibling checkout at
`/data/codes/coding-ritual/reference_harnesses/The-Claude-Protocol`, whose
`.git` gitlink resolves to the shared `.git/modules/...` store for the same
submodule — i.e. the same pinned commit, on the balance of evidence, but its
`git status --porcelain` cleanliness was never independently re-verified from
within this worktree (that would require a `git` command targeting outside
the worktree, which the sandbox blocks). Treat the sha as correct and the
content as very likely matching that sha, but not independently
snapshot-verified end-to-end the way the skill's Snapshot coherence section
intends.

**Promotion verification (2026-08-21, coordinator):** this artifact was
produced in an isolated worktree whose submodule copy was uninitialized (the
caveat above). Before landing it in `docs/research/`, the primary checkout was
verified directly: `git -C reference_harnesses/The-Claude-Protocol rev-parse
--short HEAD` → `af754ef`; `git -C reference_harnesses/The-Claude-Protocol
status --porcelain` → empty (clean). The sibling checkout the content was read
from *is* that primary checkout, so the provisional qualifier is lifted; the
original caveat is retained above as the record of how the run handled it.

## Effect on prior artifacts

None — first artifact for this target; nothing to confirm, extend, or
supersede.
