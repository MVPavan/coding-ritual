# ADLC tracker model

This file defines how the tracker (Beads, `bd` 1.3.0) represents work across
the lifecycle in `GUIDE.md` §1: how big each bead type is, how a bead shows
where it stands, and what is deliberately not tracked. It is the tracker half
of the model; `document-model.md` is the document half.

It is design guidance from the 2026-10-07 to 2026-10-14 discussions. Only the
`review` status (§3) is in the `beads` skill today. The rest waits until the
skills (`beads` `usage.md` §7 and `prime.md`, `planning` `decompose.md`, and
the status renderer) are updated together; §8 lists what that needs.

## 1. Two layers

| Layer | Holds | Dictionary term |
|---|---|---|
| Documents | why, what, decisions, evidence | **spec**: a handoff artifact for work that spans sessions |
| Tracker | requests, tasks, status, waits, close evidence | **ticket**: a handoff artifact scoped to one session |

The terms come from the AI Coding Dictionary (aicodingdictionary.com, Matt
Pocock's AI Hero). Neither layer repeats the other (A-02). Our `spec.md`
holds only intent and acceptance, so the dictionary's "spec" corresponds to a
whole workstream folder; the word clash is open (§8).

## 2. Statuses

bd 1.3.0 has seven built-in statuses (`bd statuses`) and accepts custom ones.

| Status | bd category | Our use |
|---|---|---|
| `open` | active | open, not started |
| `in_progress` | wip | claimed and being worked (`--claim`) |
| `review` | wip (custom) | built; waiting for its verification (§3) |
| `deferred` | frozen | the backlog; a deferred spike is an idea |
| `closed` | done | done, rejected (`wontfix:`) or duplicate |
| `blocked` | wip | never set by hand: a stored `blocked` with no dependency drops out of `bd ready` and `bd blocked` |
| `pinned` | frozen | allowed, rarely needed |
| `hooked` | wip | not used (bd's agent-hook coordination) |

Without `review`, the lifecycle runs only `open → in_progress → closed`, plus
`deferred`.

## 3. The `review` status

**Flow.** When the build is done, the author sets
`bd update <id> -s review` and links the check with
`bd dep add <id> <check>`. The check says which kind of verification it is:

| The bead depends on | Sub-stage |
|---|---|
| a review task claimed by another actor | Review |
| a CI gate | Testing |
| a `human` task | Validation |

Pass: the author closes the bead. Fail: the bead returns to `in_progress`.

**Tested behaviour** (throwaway trackers, bd 1.3.0, 2026-10-07 and
2026-10-14):

| Check | Result |
|---|---|
| `bd config set status.custom "review:wip"` | accepted; listed by `bd statuses` |
| `bd ready` | excludes a bead in `review` |
| default `bd list` | shows it |
| claim from a custom status | works; moves it to `in_progress` |
| close from `review` | works |
| `issues.jsonl` export | keeps `review` |
| parent epic | `bd epic close-eligible` keeps it open while a child is in `review` |
| `bd show` / `bd children` | `[P2 · REVIEW]` / its own icon ◇ |
| fresh clone via `bd bootstrap` | receives the status with the database |
| custom status of category **`active`** | **not** in `bd ready`, although bd's help says it should be |

**Scope.** `status.custom` is a **project setting** stored in the project's
database: not in `config.yaml` and not in the bd install. Installing bd sets
nothing; each new project runs the command once (`beads` `setup.md` §2); a
clone joined with `bd bootstrap` receives it. The renderer marks these beads
`🔍 in review` (it showed them as blocked before). Adopted in commit
`966483c`.

**No custom statuses before building** ("triaged", "specified"): a custom
status hides the bead from `bd ready`, even with category `active`.

## 4. Where a bead stands

For a task, bug or spike, the built-in fields plus `review` show the position
without labels:

| Position | Signal | ADLC sub-stage |
|---|---|---|
| Parked | `deferred` (a spike = an idea) | Triage outcome; Charting backlog |
| Not triaged | `open`, acceptance empty | Intake · Triage |
| Waiting on the owner | depends on an open `human` task, or is labelled `human` | Clarification; Governance gate |
| Ready | `open`, acceptance set, no open blocker | Decomposition done; Building next |
| Being built | `in_progress`; type `bug` = Diagnosis, `spike` = Research | Building |
| Waiting on CI or a PR | depends on a gate (`gh:run`, `gh:pr`) | Testing; Integration |
| Being verified | `review`, plus the check it depends on (§3) | Verification |
| Finished | `closed`; the close reason says done, `wontfix:` or duplicate | Delivery · Closure; Triage rejection |
| A decision | type `decision`: `open` = deciding, `closed` = decided | Design · Architecture |

Other fields add detail but are not positions: an empty `design` means no
approach yet; a `plan:` note means the work is decomposed; comments hold
evidence; `discovered-from` marks work found by a review or a diagnosis.

**An epic's position is read from its documents** (is `spec.md` approved,
does the roadmap have increments) and its children's counts. Charting,
Grounding, Specification, Architecture, Decomposition, Release, Retrospective
and the other area-level sub-stages describe an epic or workstream, not a
task.

**No stage labels.** Labels are not exclusive (a bead could carry two
stages); a child copies its parent's labels at creation, so an epic's label
would spread to every new task; nothing removes a stale label; and they would
repeat state the status and fields already hold. `human` stays the only label.

## 5. Sizing: outcomes, not phases

Features and phases are two axes, not two sizes:

| Axis | Answers | Stability |
|---|---|---|
| Feature / outcome | **what** the owner gets | stable |
| Phase | **when** a part is built | re-planned as you learn |

The parent–child tree follows the stable axis. Order follows dependency
edges, which `bd ready` turns into "what is next". If phases are containers,
every re-plan rebuilds epics; if outcomes are containers, a re-plan only
moves edges.

**Epic tests.** An epic must pass all four:

1. **End**: it can be closed. An ongoing area cannot.
2. **Accept**: the owner can accept it on its own.
3. **Oracle**: it has one acceptance (one spec, one Validation).
4. **Cancel**: it can be dropped without leaving half of something else.

**The ladder.**

```text
Workstream (area)  ongoing; not a bead. Its epics share a spec_id path:
                   bd list -t epic --all --spec docs/workstreams/<area>/
└── epic           one outcome with an end: spec, Validation, Closure
    ├── feature    a vertical slice the owner could use (a well-cut phase); optional
    │   └── task   one session's work (a ticket); subtasks one level only
    └── task       small epics skip the feature layer
Order = dependency edges, never nesting.
```

This matches `GUIDE.md`'s units: direction = workstream; request → change =
epic; increment = feature or task.

**Rules.**

1. Epic = one outcome that passes the four tests.
2. Feature = a vertical slice the owner could use. Small epics skip it.
3. Task = one session's work.
4. Workstream = an area, grouped by the `spec_id` path, never a bead.
5. Order is edges (`bd dep add`), never nesting. A roadmap's phases become
   edges.
6. Risky foundation work still goes first, but as the first feature (a thin
   end-to-end slice) or as tasks later features depend on, not as a
   container.
7. A check is a task, not a container: a review task, a CI gate, or a `human`
   validation task. The epic's own `human` validation task is what lets the
   epic close.
8. Not epics: a question is a spike; a pile of loosely related items stays
   as separate deferred beads; a wrapper around an existing bead is not
   needed.
9. A bead's position is its status plus `review` (§4); never stage labels.

**Across the lifecycle.**

| Stage | Works on |
|---|---|
| Charting | workstreams: which outcomes come next |
| Intake, Design | one epic: its spec and roadmap |
| Decomposition | features, tasks and the edges that order them |
| Building, Verification | tasks (`review` lives here) |
| Delivery | features ship; the epic closes after its validation task |
| Closure | the epic's line in `STATUS.md` updates its workstream |

**Options considered.** One epic per workstream fails test 1: an area never
closes. Several phase epics per workstream (the current practice) cuts on the
unstable axis. The model keeps several epics per workstream but cuts and
names each as an outcome.

## 6. Audit of the current epics (2026-10-14)

Audit only, to test §5. Closed epics stay as they are.

**The 18 phase epics** (12 DWS, 6 agent-bridge; all closed):

| Phase | Kind | Epic tests |
|---|---|---|
| DWS P5 fetch/read, P6 rendered, P7 search, P8 retrieval, P9 crawl, P10 operations/recovery | vertical slices: each is a command a user can run | pass: these are features |
| DWS P12 MCP adapter | a separate delivery; the engine works without it | pass strongly: it could be its own epic |
| DWS P1 foundation, P2 evidence core, P3 command shell, P4 runtime controls | horizontal layers ("before any provider capability exists") | fail accept and cancel |
| DWS P11 release qualification | checks the whole engine | fail: it is DWS's Validation, a task |
| Bridge P1–P4 (sequential stages, bounded decisions, child coordination, integration) | engine capabilities | pass: features |
| Bridge P0 baseline, P5 live proof | setup; integration plus validation | fail: the same two patterns |

11 of 18 pass; the 7 that fail are the setup and checking phases that rules 6
and 7 cover.

**Findings that support the model:**

1. No bead stands for "DWS" itself, so no bead records that DWS as a whole
   was validated or finished: Validation and Closure had nowhere to live.
2. Re-planning cut across outcomes: `cr-o85.39` ("the central vision gap", an
   outcome) became phase `[P1]`, and a scaffold epic `cr-vdg` was then created
   to prove that phase.
3. Unrelated work collected in containers: `cr-vdg` ("disposable proof
   scaffolding") holds `cr-0yc`, an unrelated feature about recording model
   usage.
4. Epics outside workstreams: `cr-903g` and `cr-wdzb` ("Evaluate herdr/orca",
   "Evaluate traycer") are questions, so spikes by rule 8; `cr-wi82`,
   `cr-7uhd` and `cr-s8xg` ("Execute approved …") wrap beads that already
   existed. Outcome epics such as `cr-3411` (run ledger), `cr-nwy9` (store
   restructure), `cr-31ex` (crew sessions) and `cr-98c8` (model catalog)
   already fit.

**Open epics: suggestions, not applied.**

| Epic | Suggestion |
|---|---|
| `cr-vdg` Bridge proof (its phase is closed) | move `cr-0yc` to where it belongs, then close with "superseded: P1 closed" |
| `cr-w53s` VIA cross-harness CLI | a real outcome epic, but no acceptance, no children, untouched since 2026-09-24: defer until planned |
| `cr-k88e` Run-ledger remediation | leave; close when `cr-vmgq` closes |
| `cr-02ze` live run feedback (deferred, 23 children) | leave; a bucket, but already parked |

## 7. Integration choices (proposed)

These depend on §5 and are not yet decided:

| Question | Proposal |
|---|---|
| Decision beads vs ADRs | the decision bead exists only while the choice is open (as a wait); it closes with the ADR path as its reason; the ADR holds the reasoning |
| Close reason vs `log.md` | the close reason holds the evidence (command, result, commit SHA); `log.md` records the increment, the bead ID and any deviation |
| Approvals | the record is one line in the approved document; the `human` task is the wait, and it closes naming the document and commit it approved |
| Folder layout | `workstreams/<area>/` holds the area roadmap; each epic gets `<epic-id>-<slug>/` inside it with `spec.md` and `log.md`. This replaces `document-model.md`'s one `workstreams/<tracker-id>-<slug>/` folder per epic, where "workstream" meant an outcome. Mapped to sub-stages in `document-model.md` §7 |

## 8. Adopting the rest

The model becomes policy only when these change together:

1. `beads` `usage.md` §7 (rules 1–8 replace the phase-epic text) and one
   `prime.md` line for rule 1.
2. `planning` `references/decompose.md`: a pointer to `usage.md` §7, not a
   copy.
3. `bd-render-tracking.sh`: group by `spec_id` and show features, instead of
   reading `[<phase-id>]` epic titles.
4. `document-model.md` §2 to the folder layout in §7, and the word "spec"
   reconciled with the dictionary's (a `CONTEXT.md` note or a rename).
5. The open-epic suggestions in §6, if accepted.
