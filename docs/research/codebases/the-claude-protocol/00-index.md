Target(s): reference_harnesses/The-Claude-Protocol
Created: 2026-08-21

# The-Claude-Protocol — Research Index

## Purpose

Answer a specific, user-asked mechanism question about this reference
harness's completion-enforcement hook, in the context of this repo's
reference-harness curation workflow (`.claude/rules/harness-lifecycle/curation.md`).
No capability survey (L1) or architecture map (L2) has been run yet — this
index exists only to register the one deep dive below, per the skill's Step 0
contract ("create it in the same run as the first artifact").

## Evidence legend

- **documented?** — prose (README, docs, comments) claims it.
- **declared?** — a manifest, config, or schema declares it.
- Reachability ladder: `ABSENT` (no artifact found) → `PRESENT` (artifact
  located) → `WIRED` (registration/call path traced) → `SOURCE-TRACED` (full
  behavior read, `file:line` cited) → `EXERCISED` (a run demonstrated it,
  requires separate runtime authorization).
- `INFERENCE` marks interpretation, carrying the reachability of what it was
  inferred from.

## Artifact registry

| Artifact | Mode | Snapshot sha | Clean/dirty | State | Date |
|---|---|---|---|---|---|
| `deep-dives/2026-08-21-validate-completion-approval-logic.md` | deep-dive | `af754ef` | clean — verified at promotion (`rev-parse` → `af754ef`, `status --porcelain` empty in the primary checkout); the run itself was provisional, see the deep dive's Verification performed | current | 2026-08-21 |

## Current synthesis

- `validate-completion.sh` is a `SubagentStop` hook (`templates/settings.json:52-58`,
  no matcher — fires on every subagent stop) that gates completion approval
  for supervisor-shaped subagents only.
- It fails open by default: missing transcript, undetectable subagent type,
  or a subagent type matching `*worker*` all short-circuit straight to
  `{"decision":"approve"}` before any of the seven verification checks run.
- For a detected supervisor (subagent_type contains `supervisor`) or any
  response matching both completion-marker regexes, it enforces seven
  sequential AND'd gates in fixed order: completion-format present → bead
  commented → worktree exists → worktree clean → branch pushed (only if a
  remote exists) → bead status is `inreview` → response ≤15 lines/≤800 chars.
- The first failing gate blocks immediately with a specific remediation
  string and exits; there is no aggregation of multiple failures in one run.
- The worker-substring exemption (`:49`) is unconditional and runs
  regardless of how `IS_SUPERVISOR` was computed — a subagent type
  containing both `supervisor` and `worker` substrings would still be
  exempted, bypassing every check.
- Two scope/ordering subtleties worth knowing: BEAD_ID is extracted from the
  *last response only* while the "bead commented" check scans the *whole*
  transcript for any `bd comment` (not necessarily on that bead); and the
  verbosity check runs last, after all state checks, so a fully-compliant
  supervisor can still be blocked purely for response length.
- Docs (`SKILL.md:255`, `skills/create-beads-orchestration/SKILL.md:255`,
  `docs/memory-architecture.md:103`) describe the hook consistently with the
  source at this snapshot — no docs-vs-source discrepancy found for this
  mechanism.
- No test file exercises this hook (`tests/` only has
  `test-validate-epic-close.sh`) — untested at this snapshot.
- This repo's own `.claude/hooks/` does not currently install
  `validate-completion.sh` (only `block-branch-for-epic-child.sh` is
  present) — the harness does not appear to dogfood this specific hook on
  itself; not traced further, out of scope for this question.

## Reading map

- Mechanism question ("how does approval get decided") →
  `deep-dives/2026-08-21-validate-completion-approval-logic.md`.
- No capability survey or architecture map exists yet for this target.

## Staleness, contradictions, and risks

- **Snapshot verified at promotion (2026-08-21):** the deep dive was produced
  in an isolated worktree whose submodule copy was uninitialized, so its run
  was marked provisional; before landing in `docs/research/` the primary
  checkout was verified clean at `af754ef` and the qualifier lifted. The
  original caveat is preserved in the deep dive's "Verification performed"
  section.
- No other artifacts exist yet, so no cross-artifact contradictions to
  report.
- No L1/L2 run yet — the deep dive's "Contracts and failure modes" section
  carries the only risk findings so far (fail-open defaults, unconditional
  worker exemption, BEAD_ID scope mismatch, no test coverage).
