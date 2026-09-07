# Phase-Execution Interpreter Bridge Plan

**Origin:** Bead `cr-o85.39`; graphs supply process while roadmaps supply ordered
content ([`docs/ideas/workflow-graphs.md:54-57`](../ideas/workflow-graphs.md)).

**Goal:** Prove `/phase-execution` on one prepared, eligible multi-stage deep
phase, without making the graph own decomposition or retaining a prose stage
loop.

## 0. Decisions the owner must take before slice 1

| # | Decision | What the code shows | Recommendation |
| --- | --- | --- | --- |
| O1 | How shipped code lands | `advance_instance_branch` moves only `refs/wf/<root>` ([`workflow_interpreter/supervisor/workspace.py:482-496`](../../workflow_interpreter/supervisor/workspace.py)); its other consumers detect divergence only ([`workflow_interpreter/foreman/close.py:220-240`](../../workflow_interpreter/foreman/close.py), [`workflow_interpreter/foreman/frontier.py:110-120`](../../workflow_interpreter/foreman/frontier.py), [`workflow_interpreter/foreman/events.py:220-235`](../../workflow_interpreter/foreman/events.py)). | **After `shipped`, an authorized operator runs `git merge --no-ff refs/wf/<root>` on the working branch; only then can the bridge close the stage or root N+1.** The bridge returns `awaiting_landing` and verifies the recorded landing SHA is reachable from `HEAD`. The operator resolves and commits a conflict normally, then re-enters; the stage stays claimed. This composes stages without a branch-writing interpreter privilege. |
| O2 | What substrate the proof uses | Phase scope needs one `ws-<name>` epic ([`.claude/skills/execution/SKILL.md:65-70`](../../.claude/skills/execution/SKILL.md)); this checkout has no roadmap, `ws-` epic, or open epic. A deep phase also needs an approved plan ([`.claude/skills/execution/SKILL.md:72-74`](../../.claude/skills/execution/SKILL.md)). | **Use a disposable `bridge-proof` workstream as Slice 0:** roadmap, `ws-bridge-proof` epic, five flat stages, one-to-one `Stage:` mappings, and approved deep plan. Estimate **one engineering day excluding approval wait**; this is not formula seeding. |
| O3 | Who selects, claims, and closes product stages | `BdClient.list_beads` only filters metadata/type ([`workflow_interpreter/bdio/client.py:305-329`](../../workflow_interpreter/bdio/client.py)); its closed sets omit `ready`, `--parent`, and `--claim` ([`workflow_interpreter/bdio/client.py:80-121`](../../workflow_interpreter/bdio/client.py)), deliberately refusing them ([`workflow_interpreter/bdio/client.py:222-242`](../../workflow_interpreter/bdio/client.py)). | **Keep that allow-list closed.** Add a separate phase-boundary adapter for exact `ready --parent`, exact-stage claim, metadata update, and close, each read-back verified. It accepts resolved ids, never arbitrary `bd` argv or workflow-root operations. This costs a narrow, testable trust boundary rather than weakening interpreter writes. |

## Decisions

### D1. Use a separate bridge relation

Store typed `phase_bridge` metadata on a stage: root id, attempt, pinned base,
brief digest, and landing SHA. Do not add `wf_root_id` to a product stage; the
bridge reads its relation only from the exact selected stage.

`instance_beads` returns every matching `wf_root_id`
([`workflow_interpreter/bdio/reads.py:90-93`](../../workflow_interpreter/bdio/reads.py)), and convergence calls it through
`_owns_instance_beads` ([`workflow_interpreter/bdio/roots.py:239-240`](../../workflow_interpreter/bdio/roots.py)). This avoids an
identity-sensitive reader change with eight production callers.

### D2. Admit only a deliberately code-only proof phase

Every proof stage is deep, has exactly one plan mapping, writes only
`workflow_interpreter/**` and `tests/**`, and uses the graph verifier. A phase
with docs, skills, specs, scripts, or another ineligible stage returns to
planning; it is not hybrid and does not widen grants. The phase-skill edits to
`.claude/skills` are consequently outside this proof.

### D3. Pin the base commit for recovery

Use `phase-bridge/v1/<epic>/<stage>/<attempt>`. Before creation record attempt
1 and `pinned_base_commit`; add `create --instance-base-commit SHA` and
re-supply that SHA on every re-entry. A user-requested retry advances attempt
first; it is never automatic.

`instantiate` reads `HEAD` at every call
([`workflow_interpreter/foreman/resolve.py:334-356`](../../workflow_interpreter/foreman/resolve.py)), while reuse compares
`instance_base_commit` byte-exact ([`workflow_interpreter/bdio/roots.py:251-295`](../../workflow_interpreter/bdio/roots.py)). An intervening human commit
or prior landing otherwise refuses recovery.

### D4. Pin byte-deterministic brief bytes

Before creation, write/digest one brief under
`scratchpad/execution/<slug>/briefs/<stage>-<attempt>.md`. Include only stage
id, title, description, acceptance, dependencies, and user-authored notes
captured before bridge mutation; the resolved roadmap row; and plan tasks whose
`Stage:` matches, with interfaces, verification, and dependencies. Exclude
status, assignee, close reason, all metadata including `phase_bridge` and
`wf_root_id`, evidence, and bridge-generated notes. Re-entry uses stored bytes,
not recomposition.

Reuse also compares `instance_inputs` byte-exact
([`workflow_interpreter/bdio/roots.py:251-295`](../../workflow_interpreter/bdio/roots.py)); mutation-derived briefs are unsound. The CLI accepts named file
inputs ([`workflow_interpreter/foreman/__main__.py:124-129`](../../workflow_interpreter/foreman/__main__.py)), and an absent/multiple `Stage:` join is
already a plan defect ([`.claude/skills/execution/SKILL.md:78-83`](../../.claude/skills/execution/SKILL.md)).

### D5. Add one static-grant graph definition

Author `workflows/phase-delivery.toml` with `task_brief`, human gate, and
`shipped` lifecycle, a writing grant of `workflow_interpreter/**` and
`tests/**`, and pinned `scripts/verify-feature.sh`. This is one new graph
**definition**, not a graph type or graph-per-phase format.

`build-loop` is not this contract: `write_tests` is `tests/acceptance/**`
([`workflows/build-loop.toml:45-49`](../../workflows/build-loop.toml)), while `implement` has both relevant trees
([`workflows/build-loop.toml:112-122`](../../workflows/build-loop.toml)). Do
not edit `feature-delivery` because semantic edits move
`FEATURE_DELIVERY_CONTENT_HASH` ([`tests/test_canonical_and_pinning.py:138-142`](../../tests/test_canonical_and_pinning.py)) and may invalidate live pinned
roots—not because its two copies cannot be changed together. Dynamic per-stage
grants remain a resolved-configuration/spec feature
([`docs/specs/workflow-interpreter.md:391-405`](../specs/workflow-interpreter.md)).

### D6. Land, then close, then select N+1

A `shipped` root becomes `awaiting_landing`. After O1's merge is recorded and
verified, close the exact stage with root, terminal, graph evidence, and landing
SHA. Only then select N+1, whose D3 base is the new `HEAD`. `refs/wf` alone
cannot compose code.

### D7. Define delegate ownership after CLI exit

The bridge claims the exact stage through O3 before returning. For graph work it
returns `running`, `awaiting_approval`, `awaiting_landing`, `stalled`, or
`abandoned`, and it alone closes under D6. For permitted small/standard work it
returns `delegated(stage_id, work_packet)` and exits; the skill gives that
packet to one agent. The agent returns outcome/evidence to a re-entered bridge
command; the bridge verifies acceptance and closes the claimed stage, or leaves
it open on failure. Delegates never select, claim, or close stages.

### D8. Poll and return

One bridge invocation performs one `tick`/status observation and exits; the
skill re-invokes after agent completion, signed-gate placement, or landing. It
does not call blocking `run`. `awaiting_approval` contains only root, stage,
gate, inbox, and unsigned template until a dedicated tested report adds more.

`run` defaults to eight hours ([`workflow_interpreter/foreman/constants.py:137`](../../workflow_interpreter/foreman/constants.py)) and loops until a gate,
terminal, stall, or expiry ([`workflow_interpreter/foreman/tick.py:515-545`](../../workflow_interpreter/foreman/tick.py)). Do not claim diff statistics
or findings from `_open_gates` without explicit reporting code and tests.

### D9. Replace phase ownership through one CLI seam

Add typed `phase_bridge.py` and one `phase-bridge` module subcommand. Update the
public-command docstring and `_parser()` coverage: it says seven forms
([`workflow_interpreter/foreman/__main__.py:114-148`](../../workflow_interpreter/foreman/__main__.py)) and parser behaviour is tested
([`tests/test_foreman_main.py:711-728`](../../tests/test_foreman_main.py)).
Replace only phase scope's select/claim/dispatch/close loop; retain context
loading, deep-plan approval, all-stages-closed gate, roadmap exit, and report.
`phase-execution/SKILL.md` remains a thin entry point to phase scope/bridge,
not a second executor. The existing loop is
[`.claude/skills/execution/SKILL.md:74-99`](../../.claude/skills/execution/SKILL.md).

## Landable slices

### Slice 0: proof substrate (about 1 engineering day, excluding approval wait)

Perform O2: the disposable roadmap, epic, five direct-child stages, approved
plan, and D2 admission audit. It changes no interpreter code.

**Verification:** phase-scope joins find exactly that epic and one mapping per
stage; none runs before approval, then end with the repository gate below.

### Slice 1: bridge identity and admission (about 1.5 days)

Create `phase-delivery`, separate relation, deterministic brief storage,
pinned-base create seam, and O3 adapter. Test recovery after an intervening
commit, stored-brief reuse despite relation/evidence mutation, retry generation,
exact-parent claim refusal, and no `wf_root_id` collision. Do not alter skills
or `bdio/reads.py`.

**Files:** create the graph, `phase_bridge.py`, and bridge tests; modify only
the create/CLI and narrow adapter seams required by D3/O3.

**Verification:** focused bridge, identity, and CLI tests, then end with the
repository gate below.

### Slice 2: poll, gate, land, and close (about 1.5 days)

Expose the subcommand and implement D6-D8. Test one-tick return, valid external
approval re-entry, no automatic signing, `shipped` to `awaiting_landing`,
conflict retention, verified landing before closure, and every non-closing
outcome; include parser/docstring coverage.

**Files:** modify `foreman/__main__.py`, bridge/tests, and the narrow
owner-approved landing/adapter seam.

**Verification:** focused bridge, main, tick/run, and landing tests, then end
with the repository gate below.

### Slice 3: route phase scope and run proof (about 1 engineering day plus proof time)

Replace only D9's phase/epic-variant instructions and execute the prepared
five-stage proof. Do not put Markdown assertions about `.claude/skills/*.md`
in `tests`: `scripts/verify-feature.sh` runs tests for pinned graph
activations, so unrelated skill edits must not fail an in-flight graph. Use the
skill catalog check and cold reread for those docs.

**Files:** modify `.claude/skills/execution/SKILL.md` and
`.claude/skills/phase-execution/SKILL.md`; interpreter tests cover bridge
behaviour, not skill text.

**Proof cost:** about **6 active graph hours, $60, and 15M Codex tokens** for
five stages, plus **five human signing ceremonies** that may wait indefinitely
([`docs/specs/workflow-interpreter.md:811-821`](../specs/workflow-interpreter.md)). This replaces the prior estimate; record actuals
before expansion.

**Verification:** skill catalog check and proof showing verified landing between
every stage, then end with the repository gate below.

### Repository gate required at the end of every implementation slice

Run from repo root, per [`.claude/project/verification.md:50-58`](../../.claude/project/verification.md):

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

- Without verified O1 landing, this cannot claim multi-stage composition.
- O3's adapter must remain exact-stage and read-back verified; widening
  `BdClient` is a new owner decision.
- Missing pinned base or changed stored brief must fail closed, never create an
  extra root under one attempt.
- A stage outside the two-tree grant returns to planning, not a wider graph or
  prose fallback.
- Cost, tokens, and indefinite human waits may limit this to a deep-only proof.
