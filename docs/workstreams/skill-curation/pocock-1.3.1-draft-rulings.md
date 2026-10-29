# Pocock 1.3.1: draft rulings (never recorded)

Saved 2026-10-22. These rulings were proposed to the owner but never recorded
in the ledger. The owner chose to build idea-level tracking first (see
"Mechanism decision" below), then bump Pocock to its latest upstream and redo
the review and rulings on the new mechanism. Reuse this file wherever upstream
has not changed since `49dd158`.

## Inputs

- Pins: `84fdeff` → `49dd158` (125 commits, 39 `gap` items).
- Review: `docs/workstreams/skill-curation/pocock-1.3.1-draft-review.md`.
  Author: Opus medium. Critic: Sol high, two rounds. Round 1 REVISE (12
  findings, all applied); round 2 left one MAJOR (wizard verdict) plus
  citation fixes, applied by hand. Sol never re-checked those last edits.
- Catalog `harness_lifecycle/catalogs/mattpocock_skills.json` regenerated at
  `49dd158`.
- Bead: `cr-z1hk` (spike, the upstream review).

## Proposed rulings

**A. Take (adopt-merged; one edit bead each, `discovered-from` `cr-z1hk`):**

| Upstream | Idea | Into ours |
|---|---|---|
| `pr` | PR-body template: before/after evidence, merge danger | `show-me` or a delivery skill |
| `retro` | environment-improvement categories; mechanical findings become checks | playbook §7 and `.repo-context/learnings.md` |
| `code-review` | standards-file discovery | `review` |
| `diagnosing-bugs` | prove-the-red | `systematic-debugging` |
| `wait-what` | multi-glossary map | `i-have-adhd` |
| `tdd` | per-seam catches/misses note | `test-driven-development` |
| `grilling` | "yes accepts the recommendation" | `grilling` |
| `teach` | answer-position variation | `teach` |

**B. Reject:** `implement-spec`, `chief-of-staff`, `setup-matt-pocock-skills`.

**C. Keep the existing ruling at the new hash:** the other 27.

**D. `wizard`:** D1 (recommended) re-record its adoption at the new hash,
noting the script changes are deferred; D2 record `defer` per the playbook
table, which buries the earlier adoption.

## Known weaknesses of the old mechanism (why we stopped)

1. Migrated rulings often have `source.sha: null` (e.g. Pocock `tdd`), so
   "what changed since we ruled" falls back to the previous pin.
2. What we took and dropped is mostly prose in `why`; only 9 Pocock events
   carry a structured `adaptation`.
3. `gap` says a skill changed, not what changed or which earlier decision it
   touches (bead `cr-zo2f`).

## Mechanism decision (owner, 2026-10-22)

Track rulings per idea, not per skill:

- **Reference records** per upstream skill: hand-written idea list, each idea
  with a stable ID (`tdd.seams`); each idea's status, target skill and review
  are generated from the ledger.
- **Ledger events** gain per-idea rulings; whole-skill rulings remain for
  rejected and out-of-scope skills.
- **Our skill records:** Capability becomes hand-written "covers" bullets,
  plus generated "declined upstream ideas", plus a stored skill hash that
  `check` uses to flag a stale Capability.
- Files are created lazily, when a skill is reviewed; skills rejected or out
  of scope as a whole get none.

Risks weighed: two sources of truth (status is generated, never hand-kept);
unstable bullets (stable IDs; reviewers map onto existing IDs); volume (~400
upstream capabilities, so lazy creation); stale our-side bullets (hash check);
detail creep (one line per distinct gate, rule or artifact; about 3 to 10 per
skill).
