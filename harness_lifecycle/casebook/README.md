# Casebook

The permanent record of which reference-harness skills we adopted, which we
rejected, and exactly why. Each bucket accumulates its own case history.

It answers one question that nothing else in this repo can: **"we looked at this
skill before — what did we decide, and has it changed since?"**

## Why it exists separately from `ledger.json`

`gap.py ledger add` **replaces** the entry for a given skill
([`gap.py:326`](../gap.py)) and records a content hash **only for adopted**
entries ([`gap.py:319`](../gap.py)). So the ledger is a mutable snapshot of the
current position, with two consequences: the reasoning behind a superseded
decision is gone, and a *rejected* skill can change completely upstream without
anything noticing.

The casebook is the authored history; the ledger stays the current-state index.
Keep them in that order and neither has to lie.

## Layout

```text
casebook/
  rounds/<round-id>.jsonl   the log — immutable, one file per analysis round
  rounds/MANIFEST.json      sha256 of every sealed round, so edits get caught
  current.json              GENERATED — effective ruling per skill
  views/bucket-NN.md        GENERATED — one readable page per bucket
  views/INDEX.md            GENERATED — the summary table
  casebook.py               validate · build · query
```

Only `rounds/*.jsonl` is authored. Everything else is rebuilt from it, so a
generated file is never worth editing and never worth resolving a merge conflict
in — regenerate instead.

## Append-only, and actually enforced

A round file is sealed by recording its sha256. `validate` fails if a sealed file
is modified or deleted, so history cannot be quietly rewritten:

```text
error: round-001-....jsonl: recorded round file has been MODIFIED — the log is append-only
```

**Changing your mind never means editing an old event.** Append a new one naming
the events it replaces in `supersedes`. The old ruling stays readable with its
original reasoning; `current.json` and the views show only the latest.

One file per round rather than one shared log, so two people analysing different
things add different files instead of colliding at the same last line.

## Adding a round

1. Re-sync pins, re-run `scan.py`, then `export_csv.py`.
2. Compare each skill's `content_hash` against `current.json`. Unchanged skills
   need no new event — the old ruling still stands.
3. For skills that are new or whose hash moved, run the analysis
   (`docs/plans/skill-consolidation-plan.md` has the procedure).
4. Write `rounds/round-NNN-<slug>.jsonl`: a `harness-curation-round/v1` header
   first, then one `harness-curation-event/v1` per reconsidered skill.
5. `python3 harness_lifecycle/casebook/casebook.py build --seal`

Only write events for what you actually reconsidered. A round is a delta, not a
restatement.

## Records

Round header — scope, upstream pins, method, evidence paths, and any debts the
round leaves behind.

Event — one ruling on one skill:

| Field | Holds |
|---|---|
| `event_id`, `round_id`, `recorded_at` | identity and when |
| `bucket`, `bucket_name` | which bucket it was judged in |
| `subject_id` | stable local id — survives upstream renames |
| `source` | repo, name, path, `content_hash`, `commit_sha` |
| `verdict` | `adopt` · `adopt-merged` · `reject` · `defer` · `out-of-scope` · `superseded` |
| `reasoning` | why. Required and non-empty — validation rejects a blank one |
| `adaptation.merged_from` | skills whose content was folded in |
| `adaptation.modifications` | exactly what changed when adopting |
| `adaptation.deliberately_dropped` | what was cut, so the loss is on the record |
| `supersedes` | event ids this ruling replaces |

`subject_id` is the key because no upstream field is durable — names get renamed,
paths get moved, hashes change on every edit. A pure rename shows up as the same
`content_hash` under a new name; a rename *plus* an edit needs a human to link it
to the existing `subject_id`. Never fuzzy-match that automatically.

## Commands

```bash
python3 harness_lifecycle/casebook/casebook.py validate       # integrity + schema
python3 harness_lifecycle/casebook/casebook.py build --seal   # regenerate, seal new rounds
python3 harness_lifecycle/casebook/casebook.py query grilling # ruling + full history
```

## Rounds so far

**001 — council consolidation.** 63 skills, 14 buckets, 41 adopted. Two models
analysed every skill independently and blind (Opus 5, gpt-5.6-sol high); a third
judged and adjudicated 11 conflicts (fable-xhigh). Full reports under
`docs/research/skill-consolidation/`.

**002 — UI out of scope.** Not a re-analysis: this harness has no UI work, so
UI-specific capability is dropped regardless of quality. `frontend-ui-engineering`
and `browser-testing-with-devtools` rejected, `performance-optimization` trimmed
of its Core Web Vitals sections. **41 → 39 adopted.** Round 001's reasoning stays
readable in the log — the two skills were adopted on merit and are restorable from
it if UI work ever appears.

This round is also the worked example of supersession: three events, each naming
the round-001 event it replaces. Nothing in round 001 was touched.

Two debts recorded in the round header that no roster choice avoids:

- **agent-skills `references/*.md`** — 7 shared files referenced by 11 skills, 9
  of them adopted. `doubt-driven-development`'s constraints are written against
  `orchestration-patterns.md`. Porting them is real adoption work.
- **Trigger evals** — ~9 adopted skills are merges, and the upstream evals cover
  the originals, not the merges.
