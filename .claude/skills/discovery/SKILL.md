---
name: discovery
description: Use when material scope or behavior decisions are still open and need settling, or the user requests a brainstorm. Skip a single factual lookup or one routine detail, which need no run; writing settled decisions up as a spec is to-spec; settling them on the way to a plan is the plan playbook, which calls this.
---

# Discovery

Settle open scope or behavior questions before committing to an approach: sort
each by who can answer it, answer what code, sources or a run can, ask the owner
the rest, and write a checked record.

## Route first

- Clear, bounded behavior: return to the task; no run or record is needed.
- One factual lookup or one routine missing detail: infer it from the relevant
  code or ask one focused question, then continue independent work.
- Decisions already settled: do not reopen them; a durable spec of them is `to-spec`.
- Requested interview: use `grilling`. A written critique is a review, not
  permission to interview or edit documents.
- Decisions that will span sessions as a tracked map: `wayfinder`.

Read only the relevant code, authoritative docs and constraints needed to tell
the live choices apart, and name the closest existing solution before proposing
a new one. Establish outcome, intended user, success criteria, constraints and
exclusions. Carry prior decisions and authorization forward: a decision is
prior only with the owner's authority (an owner answer, an approved spec, plan
or ADR, a delegation); an unconfirmed precedent is evidence, cited in a row
that stays `proposed` unless code, sources or a run settle it. Several live
directions: diverge and converge with `references/exploration.md`. A choice
between options, or a decision in a known domain: the one fitting section of
`references/frameworks.md`.

## Triage each question by who can answer it

| Answerer | Action | Source | Status |
|---|---|---|---|
| This project's code | read it; `how` for a walkthrough, `why` for history; for a count, join or search, save a script that reruns as is and its output beside the record | `code: <path>:<line>`, or `computed: <script path> -> <output path>` | established |
| Outside sources | call `research` | `outside: <source>, <version>, <date>` | established |
| A run | call `prototype` | `prototype: <report path>` | established |
| A routine pick | decide it | `agent: routine, <basis>` | routine |
| The owner | ask, last | `owner: "<quote>" (YYYY-MM-DD)` or `owner: delegation <ref>` | decided |

Give every established row a Confidence of `high`, `medium` or `low`: how far
the cited line, sources, run or computation actually settle it. `high` only when
the cited source shows the answer by itself, as a saved computation's output
shows its count. An answer you put together from several lines, or from a search
that found nothing (no caller, no other reader), is `medium` or `low`: cite the
most direct line, and name the other lines or the search and the inference in
the answer. If together they do not settle it, it stays `proposed`.
`check_record.py` notes a `high` answer that names another location: confirm its
source shows that answer by itself, or grade it `medium`. A `computed:` answer
names what the script selects; two counts compared must cover the same
population. Write a fact and a choice made on it as separate rows: the code can
establish what exists and what it lacks, but lines that only allow or favour one
option settle nothing, so that choice is `proposed`, with them as its basis. A
consequence that holds once a proposed choice is made can be established when
code or a run settles it: its answer starts `If row <n> is chosen,` and row
`<n>` stays `proposed`. A prototype's recommendation among its variants is
evidence, never a decision; a cited report holds what the `prototype` skill says
to record. A material choice the owner has not answered is `proposed`, with your
recommendation as its answer, or `open`.

## Ask the owner

Ask only what the other answerers cannot settle, in rounds over the frontier:
batch independent questions whose prerequisites are settled, hold dependent ones,
and wait for a round's answers before asking the next. Present materially
different options with their tradeoffs, and label the recommendation's assumptions.
Ask each question as one fixed block, with no emoji: `**Q<n>. <title>**: <question; options if any>`, then `Recommended: <answer>. Reply yes to accept, or give yours.`
Interview technique and reading approval: `references/interviewing.md`. A
question about structure, flow or layout: `references/visuals.md`.

## Stop

Recompute the open questions after each answer. Stop when the decisions the next
step needs are settled, deferred or blocked; do not invent questions or variants
to fill a quota. If the owner is unavailable, their rows stay `proposed` or `open`
and are reported.

## Write the record

Always write the record, from `templates/record.md`; presenting options may stay
in chat. A filled example is `references/record-example.md`.

1. Path: the one a calling skill or playbook names; otherwise
   `docs/discovery/<area>/<topic>/<YYYY-MM-DD>-<slug>.md`. `<area>` is the
   `docs/workstreams/<name>` folder the work belongs to, else the top-level
   directory the question is about, kebab-cased (when it spans several, the one
   holding the code the answer would change; still several, `general`), else
   `general`. Other `docs/` folders, such as `docs/research/<name>`, do not set it; `<topic>` is a
   short kebab subject. Area and Topic describe the question, so they follow this
   rule even when a caller names a path elsewhere. Reuse an existing folder before
   creating one; never go deeper.
2. `Caller:` names who started the run: `user request`, the calling unit and
   step (`plan playbook, step 3`), or `delegated: <brief path>`, optionally with a
   short note in parentheses.
3. `Run:` is fresh per run, `<session id>-<nonce>`, reused only to continue that
   run; write to the path
   `scripts/check_record.py --next <path> --run <id>` prints. Never replace an
   earlier run's record without the owner or the caller naming it to revise,
   noted as `Revises: <authority>`.
4. Run `scripts/check_record.py <file>` and fix every line it prints; for a record
   under `docs/discovery/`, then run `scripts/check_record.py --index docs/discovery`.

## End

Report an unresolved direction as a blocker to whoever started the run. The run
ends at the record and its report; a caller sequences what follows. At top level,
work that goes on to a spec or a plan returns to `mvp-mode`; in a delegated task,
report that route. A discovery-only request does not authorize code changes.
Discovery writes no Beads and never calls `tracker`; a decision bead or ADR
follows only where existing rules require one, and links the record. A fact
that corrects a bead goes in a row and in the report, naming the bead, for
whoever started the run to correct.
