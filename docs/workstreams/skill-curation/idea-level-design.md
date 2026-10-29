# Idea-level rulings: design

> **Amended 2026-10-28 by `traits-design.md`:** ideas are now traits from one
> shared vocabulary; reference records and Covers are replaced by
> `trait-definitions.yaml` and `traits.yaml`. The ledger model, tree hash,
> change detection and `gap` below still hold, read with that rename.

Status: approved for build, 2026-10-22, after three Sol high review rounds
(dispositions at the end). Owner decision: rule on
upstream skills idea by idea, so each release review only covers what changed
and never re-decides what we already took or declined. Draft Pocock rulings
and the decision record: `pocock-1.3.1-draft-rulings.md`.

## Problem

1. A ruling covers a whole upstream skill, but adoptions are partial. What we
   took and dropped is mostly prose in `why`; only 9 of Pocock's events carry
   a structured `adaptation`.
2. `gap` says a skill changed, not what changed or which earlier decision the
   change touches.
3. `content_hash` covers `SKILL.md` only (`scan.py` `_entry_for`). A change
   confined to a skill's `references/`, `scripts/` or other assets is
   invisible to `gap`.
4. Our skill records' Capability is a one-line description, so nothing states
   what a skill covers and which upstream ideas it declined.

## Principles

- **The ledger is the only source of status.** Files hold hand-written
  descriptions; every status, target and count shown in them is generated.
- **Sealed rounds are never re-validated against today's files.** Checks that
  compare the ledger with reference records or Covers apply to effective
  events only.
- **Our Covers is the truth of what we provide now; adoptions are provenance.**
  A later upstream ruling never silently withdraws something we adopted.

## Terms

- **Idea**: one distinct gate, rule, method, template or artifact inside a
  skill, stated in one line. About 3 to 10 per skill.
- **Idea ID**: a short kebab slug, unique within its skill (`seams`). Global
  form: `<repo>:<logical_id>#<slug>` upstream, `ours:<skill>#<slug>` ours.
  A slug survives wording changes; a move or split uses `carried_from` (§2).
- **Idea-level**: applies to `skill` capabilities only. Agents, commands,
  hooks and other kinds keep capability-level rulings.

## 1. Reference records (upstream skills)

`registry/reference-records/<repo>/<logical_id path>.md`, mirroring the full
logical ID so names never collide (catalogs already hold duplicate names:
`subagents-discipline` in The-Claude-Protocol, `pr-review-canvas` in
cursor_plugins). Example:
`reference-records/mattpocock_skills/skill/skills/engineering/tdd.md`.

```markdown
---
subject: mattpocock_skills:skill:skills/engineering/tdd
reviewed_sha: 5beb35b      # upstream commit the idea list describes
tree_hash: <hash>          # §4; the tree the idea list describes
---
# mattpocock_skills · tdd

## Ideas
- `seams`: agree the public test boundaries before writing tests.
- `per-seam-note` (added 5beb35b): each seam states what it catches and misses.
- `old-idea` (removed 5beb35b): …

<!-- registry:generated ideas -->
| Idea | Effective ruling | Adopted into ours | Round | Review |
<!-- /registry:generated ideas -->
```

- Ideas are hand-written; the table is generated. `check` rejects a record
  whose `subject` duplicates another or does not match its path.
- An idea upstream deletes stays listed with `(removed <sha>)`. It is
  excluded from counts and needs no new ruling; its history stays.
- `(added <sha>)` marks ideas that appeared after the first idea-level
  review.
- Created lazily, when a skill capability is first reviewed at idea level. A
  capability ruled `reject`, `defer` or `out-of-scope` as a whole needs none.

## 2. Ledger

### Idea events

```json
{"type": "event", "id": "…", "date": "…", "kind": "adopt",
 "subject": "mattpocock_skills:skill:skills/engineering/tdd#seams",
 "why": "…", "evidence": ["harness_lifecycle/registry/reviews/…"],
 "source": {"repo": "mattpocock_skills", "logical_id": "skill:skills/engineering/tdd",
            "path": "…", "sha": "5beb35b", "content_hash": "…", "tree_hash": "…"},
 "skill": "test-driven-development", "into": "seams",
 "modification": "moved from a live human gate to the plan's Test seams field"}
```

- Kinds: `adopt`, `reject`, `defer`, `out-of-scope`.
- `adopt` needs `skill` (a skill, or `doc:<repo-relative path>` for a method
  document such as `harness_lifecycle/playbook.md`; the file must exist) and,
  when `skill` is a skill, `into` naming an ID in that skill's Covers.
  `modification` is an optional one-line note.
- On `reject` and `defer`, `skill` is optional and means "considered for";
  it feeds the declined list in our record (§3).
- `carried_from`: optional list of earlier idea subjects. Used when upstream
  moves a capability (every idea's subject changes) or splits an idea. The
  new event restates the carried ruling; the reviewer judges only the part
  the predecessor did not cover. `check` requires each `carried_from` subject
  to exist. Same-subject `supersedes` is unchanged; cross-subject supersession
  stays forbidden.

### Capability checkpoint events

The capability-level event stays: it records the reviewed `sha`,
`content_hash` and `tree_hash`, and is what `gap` compares. When idea events
exist for it, its kind and target must agree with them:

| Effective idea rulings (removed ideas excluded) | Capability kind | Capability `skill` |
|---|---|---|
| all `adopt` | `adopt` | one of the idea targets |
| some `adopt` | `adopt-merged` | one of the idea targets |
| none `adopt`, all the same kind | that kind | optional |
| none `adopt`, mixed | `reject` | optional |

`adaptation` is optional on an `adopt-merged` checkpoint that has idea
events. Generated views list every destination from the ideas, not the single
`skill`.

### Idea-level rounds

The round header gains `"idea_level": true`. For each effective capability
checkpoint recorded in an idea-level round on a `skill` capability with kind
`adopt` or `adopt-merged`:

- a reference record exists, and its `tree_hash` equals the checkpoint's;
- every non-removed idea in it has an effective idea event;
- every target skill has Covers and a current `covers_hash` (§3).

Superseded checkpoints are never re-checked, so a later release round never
invalidates an earlier sealed round.

### Re-review at a new hash

Update the idea list (add, mark removed), record a new checkpoint at the new
hash superseding the old, and record idea events only for new ideas and for
ideas whose content changed. Unchanged ideas keep their ruling.

### Adopted, then a changed version declined

If idea A was adopted and upstream rewrites it into B, which we reject or
defer, the effective ruling describes upstream's current B. Our skill keeps
A: the sources block (§3) lists the last `adopt` event for each idea, even
when superseded, labelled "adopted at <sha>; current upstream revision
<kind>". Removing A from our skill is never implied by an upstream ruling;
it is an ours-side `update` event carrying `withdraws` (below) plus the
Covers edit.

### Withdrawing an adopted idea from our skill

An ours-side `update` event may carry `withdraws`: a list of upstream idea
subjects whose adoption into this skill we no longer provide. Effect:

- `check` requires each listed subject to have an `adopt` event targeting
  this skill (directly or through rename/merge);
- the adoption is excluded from the `into`, Covers and coverage checks;
- the sources block keeps it as history, labelled "withdrawn <date>";
- a later upstream re-adoption (an `adopt` event after the withdrawal in
  ledger order: round file order, then line order; never by date, which
  has day precision) makes it live again.

## 3. Our skill records

```markdown
---
skill: test-driven-development
…
covers_hash: <our tree_hash when Covers was last checked>
---
# test-driven-development

## Capability
One-line purpose.

### Covers
- `red-first`: write a failing test and watch it fail before code.
- `seams`: test seams fixed in the plan before building.

<!-- registry:generated sources -->
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
<!-- /registry:generated declined -->
```

- Covers is hand-written and lists only what the skill does today.
- `sources`: per Covers ID, the upstream ideas adopted into it (§2 rule for
  later declines).
- `declined`: upstream ideas whose effective ruling is `reject` or `defer`
  with this skill as "considered for", with the reason.
- `check` errors when `covers_hash` differs from the skill's current tree
  hash. Covers and `covers_hash` are required only for skills targeted by an
  effective idea `adopt` in an idea-level round; other records stay lazy and
  `check` reports them as a count.
- **Our lifecycle.** Targets resolve through our `rename` and `merge` events
  to the current skill. A rename keeps every Covers ID. A `merge` event may
  carry `covers_map: {old_id: new_id}`; unmapped IDs keep their slug in the
  survivor, and `check` errors when an unmapped ID collides with an existing
  survivor ID, so two different ideas never share a slug. An `into` ID is
  resolved through these maps and validated only against an active target; a target that was retired shows as "adopted, no longer provided" and
  is not counted as covered. Retired records need no `covers_hash`.
- Every generated block uses its own paired markers; `build` preserves
  hand-written text around them.

## 4. Tree hash and change detection

- `scan.py` adds `tree_hash` for skills: sha256 over each file in the skill
  folder, sorted by relative path, framed as `<path>\0<byte length>\0<raw
  bytes>`. No text normalization. Other kinds: `tree_hash = content_hash`.
- `Source` gains optional `tree_hash`; `record` autofills it from the catalog.
- **Changed-since-ruled**, in order:
  1. the effective event has `tree_hash`: compare with the catalog;
  2. it has a `sha`: `git -C <submodule> diff --quiet <sha> <pin> --
     <skill folder>` (exact for assets, no hash needed);
  3. neither: use the pin in the header of the event's own round, labelled
     "baseline inferred from round pin";
  4. no usable baseline (the commit is absent from the submodule): report
     "baseline unknown, review".
  Legacy rulings therefore catch asset-only changes without rewriting sealed
  rounds.

## 5. `gap` output (absorbs `cr-zo2f`)

```text
~ skill:skills/engineering/tdd  (ruled adopt-merged in 2026-10-30-pocock-x)
    diff: git -C reference_harnesses/mattpocock_skills diff 49dd158 5beb35b -- skills/engineering/tdd/
    ideas: seams adopt→test-driven-development#seams · refactor-outside-loop reject
```

- The diff base is the baseline from §4 steps 2 and 3, with its label.
- Ideas come from the reference record; with no record, print the
  checkpoint's `adaptation` or trimmed `why`.
- New section **removed upstream**: subjects with an effective ruling but no
  catalog entry, with their last ruling and destinations. Reference pages
  list them too, marked "removed upstream".
- README §5 gains the rule: new `adopt-merged` capability events outside
  idea-level rounds must fill `adaptation`.

## 6. Reference pages

`references/<repo>.md` gains an `Ideas` column (`3 adopt · 1 reject`,
removed ideas excluded) linking the reference record, and lists removed
capabilities.

## Out of scope

- Backfilling idea records for past rulings; they arrive as each harness is
  re-reviewed (Pocock first).
- Automatic idea extraction. Ideas are written by the reviewer; `gap` points
  at the diff.
- Mapping the same idea across harnesses. Each harness keeps its own IDs; our
  Covers lists every upstream idea adopted into it.

## Build and order

1. `cr-zo2f` folds into this epic.
2. `scan.py` tree hash, `Source.tree_hash`, catalogs regenerated.
3. `registry.py`: idea subjects, `carried_from`, `withdraws`, `covers_map`,
   `doc:` targets, round flag,
   reference records, Covers, `covers_hash`, checkpoint consistency, lifecycle
   resolution, `build` blocks, `gap` baselines and output, removed subjects,
   reference column.
4. README §§1, 3, 5, 6 and playbook §4 (orchestrator).
5. Pilot: Pocock bumped to its latest upstream, catalog regenerated, review
   redone at idea level reusing `pocock-1.3.1-draft-rulings.md`, rulings
   recorded in one idea-level round. `retro` ideas target `doc:` paths.

## Acceptance

- `registry.py check` prints `ok` on the current tree, with no edits to
  sealed rounds.
- Lean tests:
  1. an idea event round-trips;
  2. idea-level round: missing reference record, unruled idea, stale
     `covers_hash`, and a checkpoint kind that disagrees with its ideas each
     fail `check`;
  3. two releases: a second idea-level round leaves the first round valid;
  4. asset-only upstream change shows in `gap` for both a `tree_hash` event
     and a legacy event with only `sha`;
  5. null-sha fallback uses the event's own round pin after a newer round
     exists;
  6. a removed capability appears under "removed upstream";
  7. adopt A then reject revised B: sources still show A;
  8. an `into` on a renamed skill resolves; on a retired skill it shows "no
     longer provided";
  9. two capabilities with the same name get distinct record paths;
  10. adopt, then an ours-side `update` with `withdraws` and the Covers ID
      removed: `check` passes and sources show "withdrawn"; a same-day
      re-adoption after it is live again;
  11. a merge whose unmapped Covers ID collides with the survivor fails
      `check`; with `covers_map` it passes and `into` resolves.
- `gap mattpocock_skills` after the bump prints a diff line and an ideas line
  for each changed item.

## Review round 1 dispositions (Sol high)

| # | Finding | Disposition |
|---|---|---|
| 1 | later rounds invalidate sealed rounds | accepted: checks on effective checkpoints only (§2) |
| 2 | capability vs idea status disagree | accepted: consistency table (§2) |
| 3 | record filenames collide | accepted: path mirrors logical ID (§1) |
| 4 | moves and splits lose identity | accepted: `carried_from` (§2) |
| 5 | our rename/merge/retire | accepted: lifecycle resolution (§3) |
| 6 | declining B hides adoption of A | accepted: sources keep last adopt (§2) |
| 7 | null-sha baseline drifts | accepted: own round pin, labelled (§4) |
| 8 | legacy events miss asset changes | accepted: git diff on `sha` (§4) |
| 9 | removed capabilities vanish | accepted: removed-upstream section (§5, §6) |
| 10 | normalized hashing unsafe | accepted: raw bytes, framed (§4) |
| 11 | optional mappings unverifiable | accepted: required for targeted skills (§2, §3) |
| 12 | `retro` into documents; non-skill kinds | accepted: `doc:` target; idea-level skills only |
| 13 | block markers | accepted: paired markers (§3) |

Round 2: 12 closed. #5 reopened (Covers IDs across merges): fixed with
`covers_map` and a collision check (§3). New MAJOR (ours-side removal vs a
live adoption): fixed with `withdraws` on ours-side `update` (§2).

Round 3: both closed. New MAJOR (same-day re-adoption stayed withdrawn):
fixed by ordering on ledger position, not date (§2). Design approved for
build after this mechanical fix.
