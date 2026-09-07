# Phase-Execution Interpreter Bridge Plan

**Origin:** Bead `cr-o85.39`; graphs supply process while roadmaps supply ordered
content ([`docs/ideas/workflow-graphs.md:54-57`](../ideas/workflow-graphs.md)).

**Goal:** Prove `/phase-execution` on prepared, eligible deep-phase stages,
without making the graph own decomposition or retaining a prose stage loop.

## 0. Settled owner decisions — 2026-09-07

### O1. Auto-merge with mechanical escalation

**Settled.** The owner supplies taste and direction, not the internal context of
every parallel unit, so a human merge for every stage is the wrong default.
`shipped` follows the implementer's five checks
([`scripts/verify-feature.sh:43-47`](../../scripts/verify-feature.sh)), the effects
gate, reviewer `accept`, and a signed human `ship` gate; the delivery lifecycle
makes `accept → ship → shipped` explicit
([`workflows/feature-delivery.toml:62-71`](../../workflows/feature-delivery.toml),
[`workflows/feature-delivery.toml:82-98`](../../workflows/feature-delivery.toml),
[`workflows/feature-delivery.toml:130-150`](../../workflows/feature-delivery.toml)).
Those gates do not test the merge: they ran against the root's pinned base, not
parallel landings.

After a verified `shipped` terminal, the bridge merges only
`refs/wf/<root_id>` into the working branch and re-runs the repository gate on
the merged result. This follows Git Safety's standing rule to re-run verification
after a merge and stop red with everything intact
([`CLAUDE.md:81-86`](../../CLAUDE.md)). Escalate only when:

1. The merge conflicts: report every conflicting path.
2. The post-merge gate is red: report the failing check.

In either case the stage remains claimed, nothing closes, and the conflicted or
merged result remains intact for the human. A red gate can result from an
unrelated parallel landing, so the bridge neither attributes blame nor rolls
anything back.

This grants the bridge write access to the working branch. It is a Git capability,
not a bd operation, so O3's adapter boundary does not cover it. Bound it to a
clean starting tree, a verified `shipped` terminal, and that root's `refs/wf/`
ref; it never force-pushes, rebases, or auto-resolves a conflict.

### O2. Run both proof substrates, in order

**Settled.** First run a disposable `bridge-proof` workstream: failures are
free and establish the mechanism cheaply. Then run one real eligible backlog
phase: it tests owner-relevant work, real briefs, and real surrounding history.
The second result cannot be inferred from the first; it shows whether an actual
phase's existing plan/mappings and concurrent branch history satisfy admission
and landing contracts.

Estimate the disposable three-stage proof at about **one engineering day** to
prepare, plus **3.6 active graph hours, $36, 9M Codex tokens, and three signing
ceremonies**. Estimate the real phase at about **one engineering day** for
admission/routing plus **1.2 active graph hours, $12, 3M tokens, and one signing
ceremony per selected stage**.

### O3. Keep BdClient closed; use a separate adapter

**Settled; unchanged.** `BdClient.list_beads` only filters metadata/type
([`workflow_interpreter/bdio/client.py:305-329`](../../workflow_interpreter/bdio/client.py));
its closed command and flag sets omit `ready`, `--parent`, and `--claim`
([`workflow_interpreter/bdio/client.py:80-121`](../../workflow_interpreter/bdio/client.py),
[`workflow_interpreter/bdio/client.py:222-242`](../../workflow_interpreter/bdio/client.py)).
The separate phase-boundary adapter performs exact `ready --parent`, exact-stage
claim, metadata update, and close with read-back verification. It accepts resolved
ids, never arbitrary `bd` argv or workflow-root operations.

## Decisions

### D1. One graph instance per stage, not per phase

**Settled by the owner on 2026-09-07.** A region's `max_entries` is a fixed
integer authored into the graph
([`workflow_interpreter/schema/models.py:192-201`](../../workflow_interpreter/schema/models.py));
rounds are counted at its `entry_node`
([`docs/specs/workflow-interpreter.md:292-308`](../specs/workflow-interpreter.md)).
It is a ceiling, not “iterate until a stage list is exhausted.” Instance inputs
are supplied once at `create_root` and reuse rejects byte-different inputs
([`workflow_interpreter/bdio/roots.py:110-136`](../../workflow_interpreter/bdio/roots.py),
[`workflow_interpreter/bdio/roots.py:253-284`](../../workflow_interpreter/bdio/roots.py)),
so one root cannot receive a different stage brief per round.

A per-phase graph is nevertheless expressible: a `pick_next_stage` producer
could emit a different brief each round, since consumers bind a producer's latest
proved output for that round
([`workflow_interpreter/foreman/inputs.py:48-97`](../../workflow_interpreter/foreman/inputs.py)).
It is rejected because that picker decides what work exists — decomposition —
while roadmaps, not graphs, own units and order
([`docs/ideas/workflow-graphs.md:54-57`](../ideas/workflow-graphs.md)). A pinned
epic also cannot be reordered, extended, or trimmed mid-instance; per-stage
roots give each successful merge its natural home between instances.

### D2. Use a separate bridge relation

Store typed `phase_bridge` metadata on the exact stage: root id, attempt, pinned
base, brief digest, and landing SHA. Do not add `wf_root_id` to a product stage.
`instance_beads` returns every matching `wf_root_id`
([`workflow_interpreter/bdio/reads.py:90-93`](../../workflow_interpreter/bdio/reads.py)),
so this avoids an identity-sensitive reader change.

### D3. Admit only a deliberately code-only proof phase

Every proof stage is deep, has exactly one plan mapping, writes only
`workflow_interpreter/**` and `tests/**`, and uses the graph verifier. A phase
with docs, skills, specs, scripts, or an ineligible stage returns to planning;
it is not hybrid and does not widen grants.

### D4. Pin the post-merge base commit for recovery

Use `phase-bridge/v1/<epic>/<stage>/<attempt>`. Before creation record attempt
1 and `pinned_base_commit`; add `create --instance-base-commit SHA` and
re-supply that SHA on every re-entry. A user-requested retry advances attempt
first; it is never automatic. Stage N+1 starts only after stage N has merged
and passed its post-merge repository gate; its base is that **post-merge `HEAD`**,
not the pre-merge head.

`instantiate` reads `HEAD` at every call
([`workflow_interpreter/foreman/resolve.py:334-356`](../../workflow_interpreter/foreman/resolve.py)),
while reuse compares `instance_base_commit` byte-exact
([`workflow_interpreter/bdio/roots.py:253-284`](../../workflow_interpreter/bdio/roots.py)).

### D5. Pin byte-deterministic brief bytes

Before creation, write/digest one brief under
`scratchpad/execution/<slug>/briefs/<stage>-<attempt>.md`: stage id, title,
description, acceptance, dependencies, pre-mutation user notes, resolved roadmap
row, and matching plan tasks. Exclude status, assignee, close reason, all
metadata, evidence, and bridge notes. Re-entry uses stored bytes, not
recomposition, because instance inputs are byte-exact on reuse
([`workflow_interpreter/bdio/roots.py:253-284`](../../workflow_interpreter/bdio/roots.py)).

### D6. Add one static-grant graph definition

Author `workflows/phase-delivery.toml` with `task_brief`, effects gate, reviewer
accept, signed human ship gate, and `shipped` lifecycle; grant writes only to
`workflow_interpreter/**` and `tests/**`; pin `scripts/verify-feature.sh`. This
is one graph **definition**, not a graph type or graph-per-phase format. The
existing delivery graph provides the required verifier/reviewer/ship pattern
([`workflows/feature-delivery.toml:18-46`](../../workflows/feature-delivery.toml),
[`workflows/feature-delivery.toml:48-98`](../../workflows/feature-delivery.toml)).

### D7. Merge, re-gate, then close before selecting N+1

At verified `shipped`, the bridge checks for a clean working tree, merges only
`refs/wf/<root_id>` into the working branch without force or rebase, and runs
the full repository gate against the merged result. On success it records the
landing SHA and graph evidence, closes the exact claimed stage through O3, and
only then selects N+1 under D4's post-merge `HEAD`. `refs/wf` alone cannot
compose code.

On conflict, preserve the conflicted tree and report every conflicting path.
On a red post-merge gate, preserve the merged result and report the failed
check; it may be unrelated to this stage. Neither path closes the stage or
selects N+1. Tests cover both conditions, clean-tree refusal, ref/root mismatch
refusal, and no rollback or automatic conflict resolution.

### D8. Define delegate ownership after CLI exit

The bridge claims the exact stage through O3 before returning. For graph work it
returns `running`, `awaiting_approval`, `escalated`, `stalled`, or `abandoned`,
and it alone closes under D7. Delegates may return evidence to a re-entered
bridge command, but never select, claim, merge, or close stages.

### D9. Poll and return

One bridge invocation performs one `tick`/status observation and exits; the
skill re-invokes after agent completion, signed-gate placement, or human action
on an escalation. It does not call blocking `run`, which defaults to eight hours
([`workflow_interpreter/foreman/constants.py:137`](../../workflow_interpreter/foreman/constants.py)).

### D10. Replace phase ownership through one CLI seam

Add typed `phase_bridge.py` and one `phase-bridge` subcommand. Replace only
phase scope's select/claim/dispatch/close loop; retain context loading,
deep-plan approval, all-stages-closed gate, roadmap exit, and report.
`phase-execution/SKILL.md` remains a thin entry point, not a second executor
([`.claude/skills/execution/SKILL.md:74-99`](../../.claude/skills/execution/SKILL.md)).

## Landable slices

### Slice 0: prepare both proof substrates (about 1 engineering day, excluding approval wait)

Perform O2 in order. First create the disposable `bridge-proof` roadmap,
`ws-bridge-proof` epic, approved deep plan, D3 admission audit, and exactly
three direct-child stages. Then select and audit one real eligible backlog phase
for the second run; do not run it until the disposable proof has a report. This
changes no interpreter code.

**Proof stages:**

1. Stage 1 is ordinary: prove brief construction, graph/effects/review/ship
   gates, `shipped`, auto-merge, post-merge gate, and closure.
2. Stage 2 is ordinary: prove it sees stage 1's merged code and that D4 pins
   its root to the post-merge `HEAD`.
3. Stage 3 deliberately exercises escalation. Seed a tracked proof fixture with
   one marker line in the base. After stage 3 creates its root but before it
   ships, land a separate working-branch commit changing that line to
   `interloper`; make stage 3 change it to `stage-3`. The common-base, same-hunk
   edits deterministically conflict on bridge merge. Assert the path-naming
   escalation report, retained claim, no close, and intact conflicted tree.

**Verification:** phase-scope joins find exactly that epic and one mapping per
stage; none runs before approval; finish with the repository gate below.

### Slice 1: bridge identity and admission (about 1.5 days)

Create `phase-delivery`, separate relation, deterministic brief storage,
post-merge pinned-base create seam, and O3 adapter. Test recovery after an
intervening commit, stored-brief reuse despite relation/evidence mutation, retry
generation, exact-parent claim refusal, and no `wf_root_id` collision. Do not
alter skills or `bdio/reads.py`.

**Verification:** focused bridge, identity, and CLI tests, then end with the
repository gate below.

### Slice 2: poll, gate, merge, re-gate, and close (about 1.5 days)

Expose the subcommand and implement D7-D9. Test one-tick return, valid external
approval re-entry, no automatic signing, `shipped` to auto-merge, post-merge
gate before closure, stage N+1's post-merge base, conflict-path reporting and
retention, red-gate reporting and retention (including an unrelated parallel
failure), clean-tree refusal, and every non-closing outcome.

**Verification:** focused bridge, main, tick/run, merge, and landing tests, then
end with the repository gate below.

### Slice 3: route phase scope and run both substrates (about 1 engineering day plus proof time)

Replace only D10's phase/epic-variant instructions. Run the three-stage
disposable proof first, stopping stage 3 at its required escalation report;
then run the selected real backlog phase and compare its admission, post-merge
composition, and escalation behaviour with the disposable result. Use the skill
catalog check and cold reread for skill docs; do not put Markdown assertions
about them in interpreter tests.

**Proof cost:** the disposable proof is about **3.6 active graph hours, $36,
and 9M Codex tokens** for three stages, plus **three human signing ceremonies**
that may wait indefinitely
([`docs/specs/workflow-interpreter.md:811-821`](../specs/workflow-interpreter.md)).
This linearly rescales the former five-stage estimate; record actuals before
expansion. The real backlog run uses its separate O2 per-stage estimate and
records actual stage count, cost, tokens, and signing wait.

**Verification:** skill catalog check; disposable proof evidence for stage 1
closure, stage 2 post-merge visibility/base, and stage 3 escalation; then real
phase evidence; end with the repository gate below.

### Repository gate required at the end of every implementation slice

Run from repo root, per
[`.claude/project/verification.md:46-56`](../../.claude/project/verification.md):

1. `uv run pytest -q -m "not bd and not live"`
2. `uv run pytest -q -m bd`
3. `uv run pytest -q -m proc`
4. `uv run ruff check workflow_interpreter/ tests/` and `uv run ruff format --check workflow_interpreter/ tests/`
5. `MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/`

## Deferred

- General small/standard graph routing until delegate evidence is measured.
- New graph **types**, graph-per-phase graphs, loops in the phase format, and
  decomposition inside a graph. One `phase-delivery` definition is in scope.
- Formula seeding, bd hierarchy changes, and per-stage dynamic grants.
- Concurrent graphs and merge-slot scheduling beyond O1's sequential landing.
- Gate timeouts, automatic signing, in-repo keys, chat approval shortcuts, and
  enforced graph cost budgets.

## Risks and invalidating evidence

- Without verified D7 merge and post-merge gate, this cannot claim multi-stage
  composition; a red gate may expose unrelated branch health, not the stage.
- O1's Git capability is outside O3: widening its allowed ref, accepting an
  unclean start, or adding force/rebase/auto-resolution needs a new owner ruling.
- O3's adapter must remain exact-stage and read-back verified; widening
  `BdClient` is a new owner decision.
- Missing pinned post-merge base or changed stored brief must fail closed.
- A stage outside the two-tree grant returns to planning, not a wider graph or
  prose fallback.
