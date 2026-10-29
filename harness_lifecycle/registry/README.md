# Registry

The registry records every skill we own and every capability we have looked at
in a reference harness: what each one does, where it sits in the lifecycle,
what it was built from, and every decision and change, with reasons. It
replaces `../ledger.json`, `../aliases.json`, `../gap.py`, `../export_csv.py`,
`inventory/` CSVs and `casebook/casebook.py` (all in git history).

It lives under `harness_lifecycle/`, so it is never shipped to adopted repos.

## 1. Layout

```text
registry/
├── README.md                      # this method
├── registry.py                    # the tool (§6)
├── ledger/
│   ├── <yyyy-mm-dd>-<slug>.jsonl  # one file per round (§5)
│   └── MANIFEST.json              # sha256 of every sealed round
├── skill-records/<domain>/<skill>.md   # our skills (§3)
├── trait-definitions.yaml         # the trait vocabulary (§4a)
├── traits.yaml                    # which skill, ours or upstream, has which traits (§4a)
├── references/<harness>.md        # generated: their capabilities and our ruling (§4)
├── reviews/<yyyy-mm-dd>-<type>-<slug>.md  # evidence behind rulings (§5a)
├── TRAITS.md                      # generated: every skill's traits, and every trait's holders
└── INDEX.md                       # generated: domain → stage → sub-stage
```

The skills themselves stay in `.claude/skills/`, the only source. Records
describe them; they never copy them.

## 2. Coordinates

Every skill has one primary home: **domain · stage · sub-stage**.

- **Domain**: the kind of outcome the skill produces.
  - `core`: works in any domain (orchestration, continuity, tracking,
    communication, tutoring, web research, writing for agents).
  - `engineering`: software work.
  - New domains (`design`, `marketing`, `sales`, `media`, …) are added when
    their first skill arrives. A domain is also the natural plugin boundary.
- **Stage**: one of the shared backbone in `../adlc/GUIDE.md` §1: Discovery,
  Intake, Design, Building, Verification, Delivery, Operations, Improvement,
  plus X Crosscutting and U Utilities.
- **Sub-stage**: defined per domain in the ADLC guide. Engineering uses the
  existing table; a new domain adds its own sub-stages when its first skill
  arrives.

Rules:

1. **One primary home.** A skill that serves every stage belongs to X
   Crosscutting or U Utilities; it does not span stages.
2. **Secondary tags** record partial fit for search; they never decide
   ownership.
3. **Two active skills in one domain · sub-stage** must each state the
   boundary in their record, or they are merge candidates. `INDEX.md` flags
   them.
4. **Split by method, not by domain.** When the method is the same across
   domains, keep one `core` skill with a reference file per domain; when the
   method differs, use a domain skill.
5. **Aliases and legacy stubs** get no record. They are listed in their
   target's `aliases`. A stub with no target is listed in `INDEX.md` under
   "stubs".

The 14 buckets of `../archive/inventory/skill-buckets.md` are frozen history. They map
onto coordinates as follows:

| Old bucket | Coordinate |
|---|---|
| 1 Discovery, requirements and decisions | Intake · Clarification; Design · Specification |
| 2 Planning · 3 Architecture | Design · Decomposition, Architecture |
| 4 Implementation · 6 Debugging | Building · Implementation, Diagnosis |
| 5 Testing · 7 Review | Verification · Testing, Review |
| 8 Version control · 9 Release, operations | Delivery · Integration, Release; Operations |
| 10 Orchestration, handoff | X · Coordination, Continuity |
| 11 Harness authoring | Improvement · Codification |
| 12 Tooling, guardrails | X · Governance; U · Tooling |
| 13 Research, documentation · 14 Learning, content | Discovery · Research; X · Communication; U · Tutoring |

## 3. Skill records

`skill-records/<domain>/<skill>.md`, one per real skill:

```markdown
---
skill: planning                 # the .claude/skills/<name> folder
domain: engineering
stage: Design
substage: Decomposition
secondary: [Coordination]
family: task-decomposition      # capability family shared with reference skills
aliases: []                     # alias and stub entrypoints that route here
status: active                  # active | retired
---
# planning

## Capability
What it does, when it fires, and where it ends and its neighbours begin.
(Written by hand.)

<!-- registry:generated traits -->
The skill's traits from `traits.yaml`, with their definitions.
<!-- /registry:generated traits -->

<!-- registry:generated sources -->
Per trait, the upstream traits adopted into it; withdrawn, retired and
replaced-upstream adoptions stay, labelled.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
Upstream traits considered for this skill and rejected or deferred, with why.
<!-- /registry:generated declined -->

<!-- registry:generated lineage -->
Each part, and the harness, path and commit it came from, with what was
modified or deliberately dropped. Generated from adopt and adopt-merged
records.
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
Every ledger record about this skill, newest first.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
Every review a ledger record about this skill cites.
<!-- /registry:generated reviews -->
```

Only the frontmatter and Capability are written by hand; `registry.py build`
rewrites the generated blocks. What the skill does, trait by trait, lives in
`traits.yaml` (§4a), not in the record.

## 4. Reference pages

`references/<harness>.md` is generated from the harness catalog
(`../catalogs/<harness>.json`) and the ledger. One row per capability the
harness ships:

| Their capability | Status | Into ours | Last ruled at | Changed upstream since? |
|---|---|---|---|---|

Status is the effective ruling, or `present, unruled` (we have a same-named
capability but never ruled), or `not reviewed`. Once a harness has entries
in `traits.yaml`, a `Traits` column counts each skill's effective trait
rulings (`3 adopt · 1 reject`, removed traits excluded), and capabilities
removed upstream are listed with their last ruling.

## 4a. Traits

A **trait** is one distinct gate, rule, method, template, artifact or output
quality that a skill gives the agent. Every skill, ours or upstream, is
described as a list of traits drawn from one shared vocabulary, so "which
skills have X" and "what have we declined" are lookups. Rulings stay in the
ledger; the two files only describe.

**`trait-definitions.yaml`**, the vocabulary:

```yaml
seam-selection:
  definition: Choose the smallest boundary that exercises the real contract.
  placement: {domain: engineering, stage: Design, substage: Specification}
  secondary: [Implementation]
independent-expectations:
  definition: Expected values are derived independently, never copied from the code under test.
  placement: {domain: engineering, stage: Building, substage: Implementation}
  distinct_from: [good-test]
  note: Split from good-test; the two are ruled separately upstream.
```

| Field | Required | Meaning |
|---|---|---|
| `definition` | yes | one sentence, in our words (rule 4) |
| `placement` | yes | where the trait usually sits (§2 coordinates); may differ from the skill's home |
| `secondary` | no | other sub-stages it often serves |
| `distinct_from`, `note` | no | near traits it must not be confused with, and how it differs (`note` required with `distinct_from`) |
| `retired` | no | `{date, replaced_by: [ids]}`, only for a malformed definition (a bundle to split, a duplicate to merge) |

A definition no skill lists is valid: it records a trait we declined.

**`traits.yaml`**, who has what:

```yaml
ours:test-driven-development:
  tree_hash: "efbff4…"
  traits: [mode-selection, good-test, independent-expectations, seam-selection]
mattpocock_skills:skill:skills/engineering/tdd:
  reviewed_sha: "5beb35b"
  tree_hash: "e3e0f7…"
  placement: {domain: engineering, stage: Design, substage: Specification}
  traits: [good-test, seam-selection, public-only-seams, seam-preconfirmation]
  notes: {seam-preconfirmation: a live human confirmation, not a plan field}
```

| Field | Ours | Upstream | Meaning |
|---|---|---|---|
| key | `ours:<skill>` | the catalog id `<repo>:<logical_id>` | the record exists / the capability is in the catalog or ruled "removed upstream" |
| `tree_hash` | yes | yes | the skill folder's tree hash when the list was written; for ours, `check` fails when the folder has changed since |
| `reviewed_sha` | — | yes | the upstream commit the list describes |
| `placement` | — (the record's frontmatter) | yes | where the upstream skill sits |
| `traits` | yes | yes | trait IDs; defined, no repeats |
| `added`, `removed` | — | no | `{trait: sha}`: appeared after the first trait-level review / dropped upstream (kept for history, out of the counts) |
| `notes` | no | no | `{trait: text}`: nuance the shared definition omits |

Both files are read with strict parsing: a duplicate key, an unknown field or
a value of the wrong type (YAML reads `no` as false and an all-digit sha as a
number) fails `check`. Quote shas and hashes. No tool writes these files, so
comments are safe. Entries are created when a skill is first reviewed at
trait level. Agents, commands, hooks and other kinds keep one ruling per
capability.

**Rules for traits.**

1. One trait is one mechanism. Parts that could be ruled or adopted
   differently are separate traits.
2. Exclusive. No two traits of one skill cover the same mechanism, and no two
   definitions describe the same mechanism. A looser or stricter variant is
   its own trait with `distinct_from` and `note`.
3. Exhaustive. A skill's list covers every material mechanism in its whole
   folder. Not traits: restated `AGENTS.md` policy; wording that adds no
   mechanism; routing (the skill's activation trigger, or a bare "hand this
   to skill X"). A gate the agent applies during the work is a trait.
4. A definition is one sentence in our words. It names no reference harness,
   and names a tool only when the mechanism is specific to that tool.
5. A definition's meaning never changes. Wording fixes are edits; a new
   meaning is a new ID, and the old ID stays live for whoever still has that
   mechanism.
6. IDs are kebab case and name the mechanism, never the skill
   (`seam-selection`, not `tdd-seams`).

**Extract blind, then map** (the procedure is in `../playbook.md` §4): the
agent listing a skill's traits reads only the skill folder, never these two
files; a separate pass maps each extracted trait to an existing ID (same
mechanism), splits it (partial match) or defines a new one. The review keeps
both lists, so a critic can see nothing was forced.

**Retirement.** A retired definition is never deleted and always resolves,
so old events stay valid. A new subject may not use it; a ruling continuing
an existing subject may. While a skill still lists it, `check` warns. An
adoption into it is satisfied while the holder lists it or every
`replaced_by` trait.

**Overlap.** A trait listed by two of our active skills is an overlap;
`check` warns with the shared IDs.

## 5. Ledger

The ledger follows `.repo-context/coding-style.md` §Ledgers: JSON Lines, one
file per round, append only, sealed when complete.

**First line of every round file: the round header.**

```json
{"type": "round", "round_id": "2026-10-14-agent-skills-0.6.13", "date": "2026-10-14", "scope": "…", "pins": {"agent-skills": "aeac41d"}, "method": "…", "evidence": ["upstream-reviews/…"], "excluded": [{"rule": "…", "why": "…", "count": 0}], "carried_debts": ["…"]}
```

An upstream review round sets `"trait_level": true` (§5b).

**Every other line: one event.**

| Field | Required | Meaning |
|---|---|---|
| `type` | yes | `"event"` |
| `id` | yes | unique across the ledger: `<round_id>:<n>` |
| `date` | yes | ISO 8601 |
| `kind` | yes | see below |
| `subject` | yes | `ours:<skill>`, `<repo>:<logical_id>`, or a trait: `<repo>:<logical_id>#<trait id>` |
| `why` | yes | the reason; never empty |
| `evidence` | yes | list of `path:line`, URLs, comparison folders, commits |
| `skill` | for our skills and adoptions | our target: a skill folder name, `<kind>:<name>` for a non-skill capability (`agent:code-reviewer`), or `doc:<repo-relative path>` for a method document. On a trait `reject` or `defer`, optional: the skill it was considered for |
| `source` | for reference rulings | `{repo, logical_id, path, sha, content_hash, tree_hash}`; `record` fills the hashes from the catalog |
| `adaptation` | for `adopt-merged` | `{merged_from: [], modifications: [], deliberately_dropped: []}`. Outside trait-level rounds, fill it; never leave the parts only in `why` |
| `into`, `modification` | trait `adopt`, optional | `into`: a different trait our skill provides instead (a modified adoption; that trait names the upstream one in `distinct_from`, and `modification` is required). Absent: the same trait ID |
| `pending` | trait `adopt`, optional | the bead for the edit that will deliver it (§5b) |
| `carried_from` | optional, trait events | earlier trait subjects whose ruling this restates, when upstream moved the skill or replaced a trait |
| `withdraws` | optional, ours-side `update` | upstream trait subjects adopted into this skill that it no longer provides |
| `family`, `relation` | optional | capability family; `substitutes`, `complements`, `pipeline`, `genus` or `singleton` |
| `commit`, `bead` | optional | the change's commit and tracker ID |
| `supersedes` | optional | list of event IDs this replaces |

**Kinds.**

| On a reference capability | On our skill |
|---|---|
| `adopt`: taken as a whole into `skill` | `add`: new skill |
| `adopt-merged`: parts merged into `skill` (with `adaptation`) | `update`: changed for our own reasons |
| `reject`: not taken, on merit | `merge`: folded into another skill (`skill` = the survivor) |
| `defer`: not now | `split`: divided (`evidence` names the new skills) |
| `out-of-scope`: not our kind of work; never a candidate | `rename`: new name (old name in `why`) |
| | `retire`: removed or reduced to a stub |

The effective ruling on a subject is its latest event not superseded.
"Superseded" is computed, never recorded. Every reference ruling records the
`content_hash` at the time, whatever its kind, so `gap` notices when a
rejected or deferred capability changes upstream.

`skill` is required on an effective `adopt`/`adopt-merged` ruling (it must name
an existing skill record, alias, stub, non-skill `kind:name` or existing
`doc:` file, resolved through our `rename` and `merge` events), and optional on
a superseded historical one, which may name a skill we no longer have.

## 5b. Trait rulings

Upstream skills are ruled trait by trait; the ledger stays the only source of
status, and the trait files only describe.

- **Trait events** have a trait subject (`<repo>:<logical_id>#<trait id>`,
  the trait listed in that upstream entry of `traits.yaml`) and kind `adopt`,
  `reject`, `defer` or `out-of-scope`. An `adopt` names `skill` (a skill or
  `doc:<path>`); the target skill must list the trait, or `into`, unless the
  adopt is pending.
- **Checkpoint.** Each reviewed skill also gets a capability-level event at the
  reviewed pin, carrying the hashes `gap` compares. Its kind must agree with
  its effective trait rulings (removed traits excluded):

  | Trait rulings | Checkpoint kind |
  |---|---|
  | all `adopt` | `adopt` |
  | some `adopt` | `adopt-merged` |
  | none `adopt`, all one kind | that kind |
  | none `adopt`, mixed | `reject` |

  Its `skill` must be one of the traits' targets; views list every target.
- **Trait-level rounds** (`"trait_level": true`). A checkpoint not
  grandfathered (below) is trait-level when its round is trait-level, its
  subject has an upstream entry in `traits.yaml`, or its subject has any
  trait ruling. For every effective trait-level checkpoint, whatever its
  kind: the entry exists with the same `reviewed_sha` and `tree_hash`, and
  every listed trait not removed has an effective ruling. Every effective
  trait ruling needs an effective checkpoint on its skill. A checkpoint with
  neither an entry nor trait rulings stays a whole-skill ruling. Superseded
  checkpoints are never re-checked, so a later release never breaks a sealed
  round.
- **Awaiting trait ruling.** The rounds sealed before traits existed are
  listed in the config (`pre_trait_rounds`, closed). Their checkpoints, for a
  subject with an upstream entry and no trait rulings, are grandfathered:
  `gap` lists them as awaiting a trait ruling and `check` does not fail.
- **Pending adoptions.** A gap (we will add it) is an `adopt` with `pending:
  <bead>`. It is intent, not delivery: the target need not list the trait
  yet, and it never counts as a delivered adoption or clears a withdrawal.
  When the edit lands, record a new `adopt` on the same subject without
  `pending`, copying `source` from the pending event. To cancel, supersede it
  with `reject` or `defer`. `check` fails when the target already lists the
  trait but the completing `adopt` is missing.
- **Re-review.** Update the upstream entry, record a new checkpoint at the
  new pin, and trait events only for new or changed traits.
- **Upstream replaces trait A with B** (a different mechanism): move A to
  `removed`, list B, and give B's ruling `carried_from: [<subject>#A]`. A
  keeps its ruling, and our skill keeps A; the `sources` block shows
  "upstream replaced it with B".
- **Adopted, then a changed version declined** (same trait, re-ruled): the
  effective ruling describes upstream's current version; our skill keeps
  what it adopted. The `sources` block shows the last delivered adoption,
  labelled with the current ruling. Only an ours-side `update` with
  `withdraws` removes it, and a later delivered `adopt`, in ledger order,
  makes it live again. This holds even when a later event supersedes the
  `adopt`: the skill must keep the trait listed until it is withdrawn.
  Withdrawal is per source: withdrawing one upstream subject never forces
  removing a trait another adoption still needs.
- **Corrections.** Superseded events never operate: a superseded `merge`,
  `retire` or withdrawing `update` has no effect on current checks, though
  the history block still shows it. After a `merge`, adoptions into the
  merged skill resolve to the survivor, which must list the trait.

**Change detection** (`gap`), per ruled capability, first that applies:

1. the event has `tree_hash`: compare with the catalog (a skill's tree hash
   covers every file in its folder, as raw bytes);
2. it has `sha`: `git diff` of the folder from that commit to the pin;
3. neither: from the pin in the event's own round header, labelled
   "baseline inferred from round pin";
4. otherwise: "baseline unknown, review".

## 5a. Reviews

A review is the evidence behind one or more rulings. One flat folder,
`reviews/`, named `<yyyy-mm-dd>-<type>-<slug>.md`, with two types:

| Type | When | Covers |
|---|---|---|
| `upstream` | A reference harness release; the submodule pointer moves in the same change | Every changed capability: what changed, our counterpart, what is worth taking. Slug: `<harness>-<version>` |
| `skill` | Deciding a merge, upgrade or rebuild of one of our skills | That skill against its upstream counterparts: a component matrix with `file:line` citations, the stronger mechanism per row, and a verdict. Slug: our skill name |

Ledger events cite a review in `evidence`. `build` lists, in each skill
record, every review cited by an event about that skill; there are no
hand-kept links. The earlier per-family comparisons are in
`../archive/skill-comparisons/`.

## 6. `registry.py`

Run with `uv run python harness_lifecycle/registry/registry.py <command>`.
It imports `../scan.py` for catalogs.

| Command | Does |
|---|---|
| `gap <harness> [--kind K] [--beads]` | Lists capabilities never ruled on, those ruled on whose upstream content changed since (§5b, with the `git diff` command and the traits or adaptation already ruled), and those removed upstream. Capabilities we already have under the same logical ID or normalized name, but never ruled on, are listed separately as `present, unruled`. `--beads` prints `bd create` lines for review; it never runs them |
| `ours` | Catalogs our capabilities: root `.claude/` and `.codex/` plus every `mvp-harness/plugins/*`, excluding each plugin's `template/` copy |
| `round open <slug>` / `round seal <round_id>` | Starts a round file with its header; seals it into `MANIFEST.json` |
| `record …` | Appends one validated event to the open round |
| `build` | Regenerates `INDEX.md`, `TRAITS.md`, `references/*.md`, and the generated blocks of every skill record |
| `check` | Validates every record (schema, unique IDs, `supersedes` targets exist, sealed rounds unchanged), every skill record's frontmatter, that every `.claude/skills/` folder has a record or is an alias or stub, the trait files (§4a: strict schema, defined IDs, `tree_hash`, retirement) and trait-level rules (§5b: checkpoints, completeness, pending, `carried_from`, `withdraws`), and that generated files are current. Warnings (retired traits still listed, overlaps among our skills) do not fail it |

## 7. Changing skills

The method for every change (placing, upstream reviews, comparisons,
evaluations, updates and retirement) is in `../playbook.md`.
