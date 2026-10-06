# ADLC document model

This file defines which documents a project keeps across the lifecycle in
`GUIDE.md` §1, where each one lives, and what it holds. Any harness or skill
that writes lifecycle documents should follow it. It is design guidance: this
repository has not yet moved to this layout.

Two layers track work:

- **Documents** hold the why, the what, the decisions, and the evidence.
- **The tracker** (Beads) holds requests, tasks, status, and triage fields.

Neither layer repeats the other (A-02).

## 1. Rules

**A document is mandatory only if something downstream breaks without it.** It
must pass at least one of these tests:

| Test | Meaning | Principle |
|---|---|---|
| R | The next sub-stage reads it | A-01 |
| G | A human approves at it | A-08 |
| O | It is the oracle that judges the work | A-04 |
| U | It is needed to undo or audit | A-13 |
| C | It is needed to resume after a break | — |

**Merge documents into sections of one file unless merging would break one of
these:**

1. **A frozen oracle.** The agent doing the work must not be able to edit its
   own acceptance tests (A-04).
2. **Independent authorship.** A reviewer's verdict must not sit where the
   author can edit it (A-03).
3. **The scope unit.** Project, direction, workstream, release and incident each
   get their own documents.
4. **The audience.** Anything published to users stays separate from internal
   material.

"Mandatory" means the information must exist and be findable. It can be a
section, a line, or a tracker field.

## 2. Layout

Paths are relative to the project root. ◆ marks a document a human approves.

```text
vision/
  VISION.md                    # stable north star; changes need approval ◆
  STATUS.md                    # coarse progress per component; updated only at workstream closure
research/
  <yyyy-mm-dd>-<kind>-<slug>/  # kind = the producing skill: research, brainstorm, council, codebase-research…
    README.md                  # question → conclusion → evidence → used by
    …                          # raw member files and sources (committed: they are evidence)
adr/
  NNNN-<slug>.md               # one hard-to-reverse decision each
workstreams/
  <tracker-id>-<slug>/         # one per epic, for example cr-3411-run-ledger
    spec.md                    # intent ◆ + acceptance ◆ (frozen)
    roadmap.md                 # design + increments ◆
    log.md                     # current state + append-only history + closure
    design.md                  # optional: only when the design outgrows roadmap.md
    reviews/                   # gitignored: raw review and council rounds
improvement/
  lessons.md                   # lesson register with occurrence counts
  evals/                       # eval cases and rubric, frozen per version
```

Add these only when the project ships something that runs:

```text
releases/<version>.md          # release record plus notes for users ◆
incidents/<date>-<slug>.md     # timeline plus postmortem
```

## 3. Documents

| Document | Sections | Written in | Read by |
|---|---|---|---|
| `VISION.md` | Purpose and users; components (core, supporting, optional, extras); **non-goals** (each rejected idea with date and reason); alignment check (how to judge a new request) | Charting | Triage, Clarification |
| `STATUS.md` | One line per component: achieved, partial or not started, linked to its workstreams | Closure | Charting, humans |
| `research/…/README.md` | Question, conclusion, sources, confidence, used by (links to workstreams and ADRs) | Research; brainstorms and councils from Clarification or Charting | Charting, Architecture |
| `adr/NNNN-<slug>.md` | Context, decision, alternatives, consequences, status (accepted, or superseded by NNNN) | Architecture, Charting | Everyone, before changing that area |
| `spec.md` | **Intent** ◆ (the vision component it serves, goal, non-goals, success outcomes in the human's words); **Acceptance** ◆ (criteria, verification commands, links to failing tests, a reproduction for defects). Frozen once approved | Clarification, Specification | Grounding, Testing, Validation |
| `roadmap.md` | **Design** (structure, interfaces, ADR links); **increments** ◆ (each with goal, check, undo, dependencies, tracker ID) | Architecture, Decomposition | Building, Orchestration |
| `log.md` | **Current state** at the top (where we are, next step, blockers); dated entries below; **Closure** at the end (see below) | Building, Verification, Closure | Resumption, Retrospective, `STATUS.md` |
| `lessons.md` | Lesson, evidence, occurrence count, codified in (link to the changed skill, rule or hook) | Retrospective, Codification | Codification |
| `evals/` | Cases and rubric; a dated result for each agent change | Evaluation | Codification |

**Dated entries in `log.md`** record four things:

- each increment completed: what changed, deviations from the roadmap, and
  evidence (command → result → commit SHA);
- each diagnosis: the root cause and its evidence;
- the essence of each review round: who reviewed, the verdict, and how each
  finding was handled;
- each decision the agent made on its own.

**The Closure section** at the end of `log.md` records:

- the disposition: done, rejected or cancelled;
- each intended outcome, and whether it was met;
- residual risk;
- follow-up tracker IDs;
- lesson candidates.

## 4. What is not a document

| Thing | Where it lives |
|---|---|
| Requests, backlog, triage fields (risk tier, priority), tasks, status, close reasons | The tracker |
| Commit messages, the pull request, merge records | git and the pull request |
| Approvals ◆ | One line in the approved document: who approved, when, and which version |
| Policy (what needs approval, autonomy levels, budgets) | `AGENTS.md` |
| Raw review and council rounds | `reviews/`, gitignored; their essence goes in `log.md` |
| Status reports | Generated from the documents and the tracker; never a source of truth |

## 5. Design choices

1. **Intent and acceptance share `spec.md`, with separate approvals.** A human
   approves intent before Grounding and acceptance after it. The real frozen
   oracle is the test code, pinned by its commit; `spec.md` links to it.
2. **The review verdict survives in `log.md`.** Raw rounds are gitignored, so
   the log is the only proof that someone other than the author reviewed the
   work (A-03). Gitignored files also exist only on the machine that made them.
3. **Closure updates the vision.** A workstream's Closure section is the only
   input to `STATUS.md`, which keeps the vision's status in step with the
   tracker.
4. **Research is filed by where it lives, not by lifecycle stage.** Brainstorms
   and councils serve Clarification or Charting, but they go in `research/`
   whenever they stand on their own. A review *of* a workstream's spec,
   roadmap or code belongs to that workstream.
5. **The folder name links the two tracking layers.** A workstream folder name
   starts with its tracker epic ID, so neither layer repeats the other.

## 6. Alternatives considered

| Set | Size | Why it was not chosen |
|---|---|---|
| Exhaustive | 45 documents, one per independent thing | Most of them pass none of the five tests on their own; they work as sections or tracker fields |
| Minimal | 9 documents | Puts both approvals (intent and plan) and the whole work history into one change file |
| **This model** | 2 vision + 3 per workstream, plus research, ADRs and improvement | Each file maps to one approval, one author, or one reader |
