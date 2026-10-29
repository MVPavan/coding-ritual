# Trait registry: design

Status: approved for build, 2026-10-28, after four Sol high rounds
(dispositions at the end). Owner decisions, 2026-10-28: rename
"idea" to **trait**; one shared trait vocabulary that every skill, ours and
upstream, maps to; two hand-written YAML files parsed with strict Pydantic; a
rulebook for creating traits; blind extraction before mapping.

This design amends `idea-level-design.md` (approved 2026-10-22). It replaces
that design's Terms, §1 (reference records) and §3's Covers list. The ledger
model (§2), tree hash and change detection (§4), `gap` (§5) and reference
pages (§6) stay, with the renames below. No sealed round contains an
idea-level event, so the rename touches no sealed data.

## Problem

1. Idea IDs are local to one skill. Our 36 Covers lists and Pocock's 25 idea
   lists use separate slugs, so "which skills provide X" or "what did we
   reject across harnesses" cannot be asked, and five slugs already collide
   across our skills with different meanings.
2. An adoption maps an upstream idea to the nearest Covers slug of ours. For
   a gap (we will add it) the pilot pointed `into` at a neighbouring slug,
   which records a looser mechanism than the one adopted.
3. Nothing stops a reviewer from inventing a new name for a mechanism that
   already has one, or bending a new mechanism onto an existing name.

## Principles

- The ledger stays the only source of rulings. The trait files hold what a
  trait means and which skill has it; every ruling, target and count shown
  anywhere is generated.
- One trait is one mechanism, named once, in our words.
- Traits are extracted blind, then mapped (§4).
- Sealed rounds are never re-validated (unchanged).

## Terms

- **Trait**: one distinct gate, rule, method, template, artifact or output
  quality that a skill gives the agent. Replaces "idea" and the Covers entry.
- **Trait ID**: kebab slug, unique across the registry
  (`^[a-z0-9]+(-[a-z0-9]+)*$`). Ledger subject of an upstream trait ruling:
  `<repo>:<logical_id>#<trait_id>`.
- **Capability** keeps its catalog meaning: a whole skill, agent, command,
  hook, rule, MCP server or plugin.
- Trait lists apply to `skill` capabilities only; other kinds keep
  capability-level rulings.

## 1. `registry/trait-definitions.yaml` (the vocabulary)

```yaml
# Trait definitions. Rules: registry README §Traits.
# Map to these only after a blind extraction (playbook §4).
good-test:
  definition: Tests assert meaningful behaviour at a stable boundary and survive refactors.
  placement: {domain: engineering, stage: Building, substage: Implementation}
independent-expectations:
  definition: Expected values are derived independently, never copied from the code under test.
  placement: {domain: engineering, stage: Building, substage: Implementation}
  distinct_from: [good-test]
  note: Split from good-test; Pocock adopts one and differs on the other.
seam-selection:
  definition: Choose the smallest boundary that exercises the real contract.
  placement: {domain: engineering, stage: Design, substage: Specification}
  secondary: [Implementation]
```

Fields (strict; unknown keys are errors):

| Field | Required | Meaning |
|---|---|---|
| `definition` | yes | one sentence, our words (rule 4) |
| `placement` | yes | `{domain, stage, substage}` from README §2: where the trait usually sits |
| `secondary` | no | other sub-stages it often serves |
| `distinct_from` | no | near traits it must not be confused with; requires `note` |
| `note` | no | why it is separate, or other context a reader needs |
| `retired` | no | `{date, replaced_by: [ids]}`; set only when the definition itself was malformed (a bundle to split, a duplicate to merge) |

A definition no skill lists is valid: it records a trait we declined.

**Retirement is rare and keeps history valid.** A meaning change never
retires anything: the old trait stays live for every skill that still has it,
and the new meaning is a new ID (rule 5). `retired` is only for a definition
that was malformed, a bundle to split or a duplicate to merge, so no correct
mapping can target it again. A retired definition is never deleted and always
resolves, so sealed events naming it stay valid. Then:

- a **new** subject (one with no earlier event) using a retired ID fails
  `check`; a ruling that supersedes an event on the same subject (a
  re-review, or a pending adoption's completion) may still name it;
- while any `traits.yaml` entry lists it, `check` warns and names the
  holders; they switch to `replaced_by` as they are re-reviewed;
- a retained adoption into it is satisfied while the holder lists the retired
  ID or every ID in `replaced_by`; otherwise the holder needs an ours-side
  `update` with `withdraws`. Generated sources show "adopted as <old>, now
  <new…>".

## 2. `registry/traits.yaml` (which skill has which traits)

```yaml
# Which skill has which traits. Rules: registry README §Traits.
ours:test-driven-development:
  tree_hash: "efbff4…"
  traits: [mode-selection, good-test, independent-expectations, seam-selection]
mattpocock_skills:skill:skills/engineering/tdd:
  reviewed_sha: "5beb35b"
  tree_hash: "e3e0f7…"
  placement: {domain: engineering, stage: Design, substage: Specification}
  traits: [good-test, seam-selection, public-only-seams, seam-preconfirmation]
  removed: {}
  notes:
    seam-preconfirmation: a live human confirmation, not a plan field
```

| Field | Ours | Upstream | Meaning |
|---|---|---|---|
| key | `ours:<skill>` | `<repo>:<logical_id>` (the catalog id) | the record must exist / the subject must be in the catalog or ruled "removed upstream" |
| `tree_hash` | required | required | §4 of idea-level-design; for ours `check` errors when it differs from the skill's current tree hash (was `covers_hash`) |
| `reviewed_sha` | — | required | upstream commit the list describes |
| `placement` | — (from the skill record frontmatter, the single source for ours) | required | where the upstream skill sits |
| `traits` | required | required | trait IDs; each defined, no repeats (retired IDs warn, §1) |
| `removed` | — | optional | `{trait_id: sha}`: upstream dropped it; history kept, excluded from counts |
| `added` | — | optional | `{trait_id: sha}`: appeared after the first trait-level review (carries the reference records' `(added <sha>)` markers) |
| `notes` | optional | optional | `{trait_id: text}`: skill-specific nuance the shared definition omits |

Entries are lazy: created when a skill is first reviewed at trait level.
Ours entries replace the Covers section and `covers_hash` in skill records;
upstream entries replace `registry/reference-records/`, which is deleted.

## 3. Parsing

- `yaml.safe_load` through a loader that **errors on duplicate keys**
  (PyYAML silently keeps the last one, which would drop a definition).
- Pydantic models with `strict=True, extra="forbid", frozen=True`. Strict
  strings reject YAML's guessed types (`no` → bool, `0123` → int, an
  all-digit sha → int). Shas and hashes are quoted in the files.
- `build` and `check` only read these files; no tool writes them. A future
  writer must preserve comments (ruamel.yaml) or append text.

## 4. Rulebook (README §Traits) and procedure (playbook §4)

Rules:

1. One trait is one mechanism. Parts that could be ruled differently are
   separate traits.
2. Exclusive: no two traits of one skill cover the same mechanism; no two
   definitions describe the same mechanism. A looser or stricter variant is
   its own trait with `distinct_from` and `note`.
3. Exhaustive: a skill's list covers every material mechanism in its whole
   folder. Not traits: restated AGENTS.md policy; wording that adds no
   mechanism; routing, meaning the skill's activation trigger (its
   description) and a bare "hand this to skill X". A gate the agent applies
   during the work is a trait.
4. A definition is one sentence in our words. It names no reference
   harness, and names a tool only when the mechanism is specific to that
   tool.
5. A definition's meaning never changes. Wording fixes are edits; a new
   meaning is a new ID, and the old ID stays live for whoever still has that
   mechanism. `retired` is only for a malformed definition (§1).

Procedure for every new or changed skill, ours or upstream:

1. **Extract blind.** The extracting agent reads only the skill folder. Its
   brief does not name `trait-definitions.yaml` or `traits.yaml`.
2. **Map**, as a separate pass: same mechanism → existing ID; partial match →
   split; no match → new definition.
3. The review file keeps the blind list and the mapping table (extracted
   trait → ID, marked match / split / new), so the critic can check nothing
   was forced.

`check` enforces the mechanical part (IDs exist, no repeats per skill,
`distinct_from` resolves and requires `note`, retirement rules in §1).
Overlap in meaning and completeness are checked by the critic.

## 5. Ledger changes

- Round header `idea_level` → `trait_level`. Idea events → trait events;
  subject `<repo>:<logical_id>#<trait_id>`; the trait ID must be listed (or
  `removed`) in that upstream entry of `traits.yaml`.
- `into` becomes optional and defaults to the subject's trait ID. Set it only
  for a modified adoption: our skill provides a different trait (which must
  name the upstream trait in `distinct_from`), and `modification` is
  required.
- **`pending`** (new, on `adopt`): a bead ID for the edit that will deliver
  it. This replaces pointing a gap at a neighbouring slug.
  - A pending adopt is **intent, not delivery.** It never enters the
    retained-adoption fold (`retained_adoptions`, sources provenance) and
    never replaces an earlier delivered adoption there. The fold reads only
    `adopt` events without `pending`. A pending revision after a delivered
    adoption therefore leaves the delivered obligation in force.
  - Recorded: while a pending adopt is the effective event on its subject,
    the target need not list the trait; views show "adopt, pending <bead>".
  - Fulfilled: when the edit lands, a new `adopt` on the same subject
    supersedes it, without `pending`, copying `source` from the pending event
    (not re-read from the catalog). That event enters the fold, so a later
    removal of the trait is caught.
  - Cancelled: a `reject` or `defer` on the same subject supersedes it. No
    obligation remains, because the pending event never entered the fold.
  - Withdrawal resolution ignores pending adopts too: only a delivered
    (non-pending) adopt after a withdrawal makes that adoption live again.
    So delivered → withdrawn → pending keeps the withdrawal in force until
    the completing adopt.
  - `check` errors when an effective pending adopt's target already lists the
    trait ("fulfilled: record the completing adopt").
- `doc:<path>` targets: the upstream trait is still mapped in the upstream
  entry like any other. `pending` works the same way; only the skill-list
  membership checks are skipped, because a document has no traits entry.
- `withdraws` keeps its per-source meaning (one upstream subject, one
  destination). Withdrawing one source never requires removing the trait
  from the list, since another adoption or our own design may still need
  it. Removing a trait from a skill's list requires that every retained
  adoption landing on it be withdrawn first (the existing retention check
  enforces this).
- **Completeness applies to every trait-level review, whatever the
  checkpoint kind.** An effective capability checkpoint is trait-level when
  it is not grandfathered (below) and its round is `trait_level`, its
  subject has an upstream entry in `traits.yaml`, or its subject has any
  trait ruling (`<subject>#…`). Every effective trait ruling needs an
  effective capability checkpoint on its skill. For a trait-level
  checkpoint: the entry must exist, its
  `reviewed_sha` and `tree_hash` must equal the checkpoint's, and every
  listed trait (not `removed`) needs an effective trait ruling. Today's
  check covers only `adopt`/`adopt-merged`; `reject` and `defer`
  checkpoints get the same rules. A checkpoint with neither an entry nor
  trait rulings stays checkpoint-only (whole-skill reject or out-of-scope).
  Superseded checkpoints are never checked.
- **Awaiting trait ruling** (amended 2026-10-28, migration; revised after
  Sol's code review, finding 3): the rounds sealed before traits existed are
  listed by ID in the registry config (`pre_trait_rounds`: the two
  2026-10-14 rounds). An effective checkpoint in one of those rounds, for a
  subject with an upstream entry and no trait rulings, is grandfathered: not
  an error, and `gap` lists it as awaiting a trait ruling. Every later
  checkpoint uses the trait-level predicate above, so a newer whole-skill
  ruling over an older inventory fails on the sha or hash mismatch. The list
  is closed: a round sealed after the migration is never added to it.
- **Upstream replaces trait A with B** (a different mechanism, so a
  different ID): the entry moves A to `removed: {A: <sha>}` and lists B; B's
  ruling carries `carried_from: [<subject>#A]`. A's effective ruling is
  untouched (removed traits need no new ruling), so our skill keeps A.
  Generated sources render A as "adopted at <sha>; upstream replaced it with
  B (<B's kind>)", found through B's `carried_from`. A rewording of the same
  mechanism keeps the ID and is re-ruled on the same subject; if that
  re-ruling declines it, the existing "adopted at <sha>; current upstream
  revision <kind>" rendering applies unchanged.
- **`covers_map` is removed.** Trait IDs are global, so a merge needs no
  slug map: adoptions into a merged skill resolve to the survivor, whose
  list must contain the trait (or the adoption carries `pending`). No sealed
  event uses `covers_map`, `withdraws` or `carried_from`.
- Checkpoint table, re-review and `carried_from` rules unchanged, with
  "idea" read as "trait".

## 6. Overlap among our skills

A trait listed by two active skills of ours is an overlap. `check` prints a
count and the shared IDs as a warning, not an error, while bead `cr-talb`
(15 known overlaps) is open. Once it closes, a second listing needs
`shared: [skill]` acknowledgement or fails (decided then, not built now).

## 7. Generated views

- `registry/TRAITS.md` (replaces `CAPABILITIES.md`):
  1. **By skill**: source → domain · stage · sub-stage → skill → its traits
     with definitions; upstream traits carry the ruling suffix
     (` — adopt → <skill>`, ` — adopt, pending cr-x`, ` — reject`).
  2. **By trait**: domain · stage · sub-stage → trait ID: definition, then
     the skills that list it (ours, then each upstream with its ruling).
- Skill records: the Covers section is removed; a generated `traits` block
  lists the skill's traits from `traits.yaml`. `sources` and `declined`
  blocks stay, keyed by trait ID.
- Reference pages: the `Ideas` column becomes `Traits`.

## 8. Migration (one-time)

The existing lists are inputs, not a vocabulary: they bundle mechanisms
(`test-driven-development#good-test` contains independent expectations,
which `#anti-patterns` repeats) and contain routing lines. So:

1. **Normalize ours.** Each of the 36 Covers lists is rewritten to the §4
   rules against its skill folder: split bundles, drop routing and restated
   policy, remove repeated mechanisms, rewrite definitions that name tools.
   Placement seeded from the skill's record, then corrected where the
   trait's usual home differs. This yields the first vocabulary.
2. **Normalize Pocock.** The 25 idea lists get the same treatment against
   the upstream folders at `5beb35b`.
3. **Map Pocock onto ours**, idea by idea, by the §4 mapping step. The
   pilot's `covered` class is a hint, not a mapping: several covered ideas
   point at one coarse Covers slug (`core.jsonl:48-50` all land on
   `break-rules-overrides`), so every many-to-one mapping gets a semantic
   check, and separate mechanisms get separate traits.
4. **Mapping table, kept as evidence:**
   `docs/workstreams/skill-curation/trait-migration-2026-10-28.md`, one row
   per old item (`ours:<skill>#<slug>` or the pilot idea subject) → new
   trait ID(s), marked match / split / merge / new / dropped (with reason).
   Each pilot draft ruling is re-keyed through this table with its `why`,
   `evidence` and `modification` kept; a split item's ruling is restated per
   part and re-checked; `(added <sha>)` markers move to `added`.
5. Gaps get `pending` placeholders filled when the owner's ruling creates
   the beads. Document-targeted ideas (four covered, seven gaps) are mapped
   to traits like any other.
6. **Critic review of the migrated data** (Sol): all 36 ours lists, the 25
   Pocock lists and every many-to-one or split row in the mapping table.

Honest limit: the Pocock lists were written while the authors also read our
skills, so they are not strictly blind. They were extracted from upstream
text and Sol-reviewed for bundling; the next harness follows §4 exactly.

## Build order

1. Code (Opus implementer): loaders and models, checks, ledger field changes,
   `TRAITS.md`, record and reference-page blocks, removal of reference-record
   and Covers parsing, tests.
2. Migration (§8): normalization and mapping by Opus authors under the §4
   rules, briefed per batch; the orchestrator resolves disputes and owns the
   mapping table; Sol reviews the migrated data.
3. README (§Traits rulebook, §§1, 3, 4a, 5, 5b), playbook §4 (orchestrator).
4. Sol code review; then resume the Pocock ruling (`cr-axdt.4`).

## Acceptance

- `registry.py check` prints `ok` with the migrated data; `build` is a
  fixed point (a second run changes nothing).
- `reference-records/` and every Covers section are gone; nothing reads them.
- Lean tests:
  1. duplicate YAML key, unknown field, unquoted all-digit sha, undefined
     trait ID, repeated ID in one skill, `distinct_from` without `note`:
     each fails `check`;
  2. stale ours `tree_hash` fails `check`;
  3. trait-level round: an upstream trait listed but unruled fails, under a
     `reject` checkpoint too; a `reject` checkpoint whose entry has a
     different `tree_hash` fails; an adopt into a skill that lacks the trait
     fails without `pending` and passes with it;
  4. pending lifecycle: pending adopt whose trait is now listed fails;
     after the completing adopt, removing the trait from the list fails;
     a cancelled pending adopt leaves no obligation; a delivered adopt
     followed by a pending revision keeps the delivered obligation;
     delivered → withdrawn → pending keeps the withdrawal, and the
     completing adopt revives the obligation; a
     doc-targeted pending adopt passes with no membership check;
  5. modified adoption: `into` a different trait without `modification`
     fails;
  6. merge: an adoption into the merged skill resolves to the survivor;
  7. withdrawal is per source: two upstream subjects adopted into one trait,
     one withdrawn, the trait still listed: passes; trait removed with one
     adoption still retained: fails;
  8. retirement: a retired trait still listed warns; a retained adoption
     into it passes when the holder lists every replacement; a new subject
     using it fails; completing a pending adoption into it passes;
  9. upstream A → B: sources show "upstream replaced it with B (<kind>)";
  10. a trait listed by two of our skills shows in the overlap warning;
  11. `TRAITS.md` by-trait view lists ours and upstream holders with rulings.
- Existing tests that covered reference records, Covers or `covers_map` are
  rewritten or deleted, not left skipped.

## Review round 1 dispositions (Sol high, REVISE)

| # | Finding | Disposition |
|---|---|---|
| 1 | Covered → `into` shortcut collapses 234 ideas to 219 subjects | Accepted: §8 steps 3-4, semantic check of every many-to-one row, mapping table |
| 2 | Copied Covers violate exclusivity | Accepted: §8 step 1 normalizes all 36 lists; step 6 critic review |
| 3 | Retirement breaks retained adoptions | Accepted: §1 retirement rules (resolvable forever, `replaced_by`, warn not error) |
| 4 | A → B decline not representable | Accepted: §5 "Upstream replaces trait A with B" |
| 5 | `pending` exempts forever | Accepted: §5 pending lifecycle by same-subject supersession; error when fulfilled but not recorded |
| 6 | Doc adoptions fall through | Accepted: §5 doc targets, §8 step 5 |
| 7 | Mandatory removal on withdrawal | Accepted: §5 `withdraws` stays per source |
| 8 | Completeness skips reject/defer checkpoints | Accepted: §5 completeness for every trait-level review |
| 9 | `(added <sha>)` lost | Accepted: `added` field, §8 step 4 |
| — | Orchestrator addition | Rule 3: routing lines (activation trigger, bare hand-off) are not traits |

## Review round 2 dispositions (Sol high, REVISE)

| # | Finding | Disposition |
|---|---|---|
| 1 | Pending events enter the raw retention fold | Accepted: §5 pending is intent; the fold reads only non-pending adopts; tests for cancellation and delivered-then-pending |
| 2 | Retirement blocks exact matches and completions | Accepted: §1 meaning changes never retire; retirement only for malformed definitions; only new subjects are blocked |
| 3 | Stale inventory bypasses reject/defer completeness | Accepted: §5 trait-level checkpoint definition; entry and hash required for every kind; stale-hash reject test |

## Review round 3 dispositions (Sol high, REVISE)

| # | Finding | Disposition |
|---|---|---|
| 1 | A pending re-adoption clears a withdrawal | Accepted: §5 withdrawal resolution ignores pending adopts; test added |
| 2 | Rule 5 still retires on meaning change | Accepted: rule 5 keeps the old ID live; retirement only for malformed definitions |

Round 4 (narrow confirmation): both closed, no contradictions. **APPROVE.**
