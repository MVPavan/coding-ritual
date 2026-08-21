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

**003 — humanlayer_skills first curation.** New submodule, 5 single-skill
plugins, all new subjects (sk-064 … sk-068). No council; one analyst, three
family comparisons under `skill-comparisons/` (`agentic-control-loops`,
`agent-doc-authoring`, `visual-explanation`). Verdicts: 3 defer
(`design-control-loop`, `improve-claude-md`, `show-me` — each with a named
re-open precondition), 1 reject (`build-iterated-agentic-loop`, superseded by
its sibling), 1 out-of-scope (`narrow-react-prop-types`, UI). **Adopted count
unchanged at 39.** The control-loop comparison also carries the orchestrator
analysis the user asked for (loop skills vs `docs/ideas/workflow-graphs.md`).

**004 — visual-explanation additions.** Two new single-skill repos, both in
one family: `diagram-design` (cathrynlavery) and `html-artifacts` (dogum —
96 % name match to our `html-artifact`). Two Opus 5 (medium) analysts, one per
repo, coordinator-verified citations; family folder extended to 4 skills
rather than forked. Both **defer** (sk-069, sk-070) — diagram-design's
geometry grammar and dogum's SVG-craft/merge borrows are named in the ledger;
the diagram borrow is one combined decision across both repos.
The-Claude-Protocol was cataloged in the same batch but not ruled. **Adopted
count unchanged at 39.**

**005 — visual-explanation merge executed.** User approved Package 2 + show-me
as a user-invoked skill. `svg-craft.md` created (diagram-design grammar + dogum
craft + honest-data), html-artifact SKILL.md and all four presets revised, four
REMOVEs executed, `.claude/skills/show-me/` added (slash-only). Independent
critic: 6 MAJOR + 12 MINOR, all applied (one non-issue). Three defers
superseded → **39 → 42 adopted.** Parked: the executable verifier (Package 3)
and the harvest §G out-of-skill items. Plugin republish pending.

**006 — diagram-design adopted in full, slash-only.** User ruling upgraded
sk-069 from adopt-in-part to adopt: the whole skill directory (2.9MB, MIT +
icon licenses) installed at `.claude/skills/diagram-design` with
`disable-model-invocation: true` — only `/diagram-design` fires it, so its own
design system (Google Fonts, branded skin) never leaks into html-artifact
documents, which keep `svg-craft.md`. Four minimal SKILL.md modifications;
references/assets byte-identical to upstream (six slash tokens allowlisted in
`skill-catalog.py` instead). Commands + plugin wrapper stay deferred.
**Adopted count unchanged at 42.** Debts: publish-manifest ruling for the
2.9MB asset tree; stale `inventory/ours/` mirror.

**007 — round-006 reversed.** The user stopped the full diagram-design
install before push: 2.9MB is too big for this harness. Local copy deleted,
unpushed commits rebuilt without it, catalog back to 45 skills; the ledger
returns to round-005's adopt-in-part, which stays shipped (`svg-craft.md` +
html-artifact merges). Round-006 remains in the log as history. Debt: a
slimmed packaging (no assets tree) is the only sanctioned reopening path.
**Adopted count unchanged at 42.**

**008 — The-Claude-Protocol first ruling.** Cataloged in the round-004 batch,
ruled here: 4 logical skills, 7 agents, 15 hooks at pin `af754ef`. Two Opus 5
(medium) analysts (orchestration core; discipline/memory/delegator),
hook-contract facts checked against the Claude Code docs, coordinator-verified
citations; reports under `docs/research/the-claude-protocol/`. Headline: a
third of TCP's hooks are wired to hook-API mechanisms that don't exist,
including both flagship gates (fail-open completion validator, dead epic-close
env var). Verdicts: `subagents-discipline` **adopt-merged** (sk-072 — FEATURE
row + PARTIAL format into verification-before-completion, look-at-real-data
bullet into the discipline rule, `Source:` line into learnings.md); 6 defers
with named re-open paths, 4 of them as beads cr-n0v / cr-ghw / cr-iqu
(dispatch-brief logging, epic-close + reclaim guard, bd-prime surfacing);
everything else rejected or out-of-scope, including all 7 agents and the
uncataloged mcp-provider-delegator. **42 → 43 adopted.**

Round-002 debts recorded in its header that no roster choice avoids:

- **agent-skills `references/*.md`** — 7 shared files referenced by 11 skills, 9
  of them adopted. `doubt-driven-development`'s constraints are written against
  `orchestration-patterns.md`. Porting them is real adoption work.
- **Trigger evals** — ~9 adopted skills are merges, and the upstream evals cover
  the originals, not the merges.
