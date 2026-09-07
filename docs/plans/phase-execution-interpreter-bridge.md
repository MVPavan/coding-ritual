# Phase-Execution Interpreter Bridge Plan

**Origin:** Bead cr-o85.39; graphs supply process, roadmaps supply ordered content
([docs/ideas/workflow-graphs.md:54-57](../ideas/workflow-graphs.md)).

**Goal:** Route eligible deep-phase stages through one interpreter instance each,
without graph-owned decomposition or a parallel prose stage loop.

## Owner rulings — 2026-09-07

### O1. Auto-land only a signed artifact through a scratch ref

A shipped terminal follows the implementer checks, effects gate, reviewer accept,
and signed human ship gate ([scripts/verify-feature.sh:43-47](../../scripts/verify-feature.sh),
[workflows/feature-delivery.toml:48-80](../../workflows/feature-delivery.toml),
[workflows/feature-delivery.toml:147-155](../../workflows/feature-delivery.toml)).
The signature binds the approved commit OID; the hash is a cross-check
([docs/specs/workflow-interpreter.md:811-818](../specs/workflow-interpreter.md)).

The bridge merges the exact OID in the verified ship payload, never a branch name
or a ref prefix. Before it creates a scratch merge, it verifies:

1. The terminal is shipped and its ship gate has verified fingerprint, payload
   digest, and signed payload naming this root, gate, outcome, and OID.
2. refs/wf/<root_id>/artifact/<activation_id> dereferences to that OID.
3. refs/heads/wf/<root_id>, the instance branch, dereferences to that same OID.

Artifact, orphan, and prereset are siblings; only artifact blesses a commit
([workflow_interpreter/supervisor/artifact.py:26-39](../../workflow_interpreter/supervisor/artifact.py)).
The third check refuses the accepted residual that a runner can move its instance
branch, instead of merging unsigned code from a moved tip
([docs/adr/0001-allowed-paths-is-advisory.md:101-111](../adr/0001-allowed-paths-is-advisory.md)).

The bridge merges the signed OID on a scratch ref and gates a detached scratch
worktree. It advances the working branch only after green. Conflict, red gate,
changed branch, or failed compare-and-swap leaves the working branch untouched and
reports the scratch ref. It never pushes, force-pushes, rebases, auto-resolves, or
rolls back.

### O2. One disposable substrate; real code only

There is no docs/workstreams/, roadmap, or existing phase epic. A second supposed
real backlog phase would author a second roadmap solely for this proof. Use one
disposable bridge-proof roadmap and epic. Roadmap, epic, and stage Beads are
disposable process scaffolding; each proof stage implements a small, open,
genuinely wanted code-only Bead because its eventual landing changes the branch.

Slice 0 selects three only when each is open, independently worthwhile, and fully
implementable in workflow_interpreter/** and/or tests/**; Stage 1 introduces a
useful named symbol; Stage 2's distinct Bead naturally requires that exact fully
qualified symbol through a production call/extension and a failing-when-absent
test; and Stage 3 has an approved exact one-line change for D11 while delivering
its own acceptance criteria. Current candidates are cr-o85.40, cr-o85.43, and
cr-o85.46, but none is preselected: no reviewed pair yet establishes the required
Stage 1/2 dependency. If no three meet the test, do not invent proof work.

After the proof report, close, never delete, its epic and stage Beads and remove
the generated bridge-proof roadmap/phase plan in a separate cleanup commit. The
successful code remains; D12 governs refs and worktrees.

### O3. Keep BdClient closed; use a narrow adapter

BdClient omits the needed ready-parent and claim interface
([workflow_interpreter/bdio/client.py:80-121](../../workflow_interpreter/bdio/client.py),
[workflow_interpreter/bdio/client.py:222-242](../../workflow_interpreter/bdio/client.py)).
A separate phase adapter performs exact ready-parent, exact-stage claim, metadata
update, and close with read-back verification. It accepts resolved ids, never
arbitrary bd argv or workflow-root operations.

## Decisions

### D1. One root per stage

max_entries is a graph ceiling, not a stage-list iterator
([workflow_interpreter/schema/models.py:192-201](../../workflow_interpreter/schema/models.py),
[docs/specs/workflow-interpreter.md:292-308](../specs/workflow-interpreter.md)).
Root reuse compares instance inputs byte-exact
([workflow_interpreter/bdio/roots.py:253-284](../../workflow_interpreter/bdio/roots.py)).
Roadmaps, not graphs, own work units and order.

### D2. Persist one phase_bridge relation

Typed metadata on the exact stage holds root id, attempt, pinned base,
authoritative brief digest, working-branch ref, landing SHA, scratch ref, and
cleanup eligibility. Do not add wf_root_id to product-stage metadata:
instance_beads returns every matching root id
([workflow_interpreter/bdio/reads.py:90-93](../../workflow_interpreter/bdio/reads.py)).

### D3. Identify the working branch and take the band

The working branch is the attached symbolic refs/heads/<name> read from the
coordinator checkout at first admission; detached HEAD refuses. Record that full
ref in D2 and require it on every entry. This is the Git Safety target-base
confirmation ([CLAUDE.md:81-88](../../CLAUDE.md)).

Take the existing non-blocking exclusive flock at
<wrapper_root>/repo-band.lock for base capture and the entire landing critical
section: clean-tree check, payload/ref checks, scratch creation/merge, scratch
gate, final clean-tree recheck, CAS, relation write, and close. BandLock refuses
contention rather than queueing ([workflow_interpreter/supervisor/band.py:24-67](../../workflow_interpreter/supervisor/band.py));
the lock lives at the wrapper root
([docs/specs/workflow-interpreter.md:1075-1077](../specs/workflow-interpreter.md)).

Merge in a detached scratch worktree, never the coordinator checkout. The final
update-ref CASes from the captured branch tip, so an outside commit refuses
landing; the bridge also rechecks the coordinator tree immediately before it.
Human/tooling landings during the bridge run must take this band. Raw Git cannot
be locked by convention, but cannot silently win the ref race.

### D4. Pin recovery base, not a Stage-2 demonstration

Use phase-bridge/v1/<epic>/<stage>/<attempt>. Under the admission lock capture the
working tip, pass and record it as instance-base-commit, and re-supply it on every
re-entry. A requested retry advances attempt first. On first entry this equals
instantiate's ordinary HEAD base
([workflow_interpreter/foreman/resolve.py:344-362](../../workflow_interpreter/foreman/resolve.py));
the explicit value matters only after an intervening commit. Admit N+1 only after
N passes D7. Slice 1 proves re-entry base retention; Slice 3 does not call a
byte-identical default/base pin independent evidence.

### D5. bd owns brief bytes

Build task_brief from the stage, acceptance, dependencies, user notes, roadmap
row, plan tasks, and (for Stage 2) symbol contract. Pass these bytes to create_root.
Root metadata stores the input body and compares it byte-exact on reuse
([workflow_interpreter/bdio/roots.py:125-154](../../workflow_interpreter/bdio/roots.py),
[workflow_interpreter/bdio/roots.py:253-284](../../workflow_interpreter/bdio/roots.py)).
A scratchpad/execution copy is convenience only: re-entry reads the bd body and
verifies its digest if the copy has gone.

### D6. One static phase-delivery graph

workflows/phase-delivery.toml has implement, review, immutable signed ship, and
shipped, plus triage/abandon. Writers grant only workflow_interpreter/** and
tests/**. Implement verifies scripts/verify-feature.sh; judgment review verifies
that command plus scripts/review-checks.sh, a strict superset as in feature-delivery
([workflows/feature-delivery.toml:18-80](../../workflows/feature-delivery.toml)).
Its definition test pins warnings == (), including absence of the judgment
superset warning ([workflow_interpreter/schema/rules_flow.py:432-462](../../workflow_interpreter/schema/rules_flow.py)).

### D7. Scratch-gate, then fast-forward and close

Under D3, let B be the captured working OID and S be
refs/phase-bridge/<root_id>/<activation_id>. Create S at B, add a detached
worktree at B, and merge the verified signed OID there. Compare-and-swap S from B
to the resulting scratch HEAD before the gate. A conflict preserves S and the
worktree and reports every conflicting path. On a clean merge, run the full
repository gate at that scratch HEAD.

Only if green, prove B is an ancestor of S and CAS the recorded working ref from
B to S. This fast-forwards the working branch. Record landing SHA/evidence, close
the exact stage through O3, then select N+1. A red gate, changed ref, dirty
coordinator tree, or CAS failure retains S, leaves the working branch unchanged,
and returns escalated with failed check or changed ref. No path closes before a
green scratch gate.

### D8. Report halts, not running

One bridge call makes one tick/status observation and exits; it never calls the
eight-hour-default run ([workflow_interpreter/foreman/constants.py:137](../../workflow_interpreter/foreman/constants.py)).
It returns exactly one of:

- running: dispatchable/routable state; skill may reinvoke.
- awaiting_approval: ordinary open human gate; reinvoke after gate action.
- halted: audit/dead-end halt with gate id and fail-code, branch-diverged,
  precondition-refused, inputs-unavailable, sandbox-unavailable, or bound-violated.
- stalled: recoverable wrapper/transport state with reason.
- escalated: D7 conflict, red gate, or ref race, with scratch ref.
- abandoned or shipped: graph terminal; only shipped proceeds to D7.
- closed: D7 landed and closed the stage.

branch-diverged is a durable dead end
([workflow_interpreter/foreman/frontier.py:38-46](../../workflow_interpreter/foreman/frontier.py),
[workflow_interpreter/foreman/frontier.py:106-127](../../workflow_interpreter/foreman/frontier.py));
audit halts are surfaced by tick
([workflow_interpreter/foreman/tick.py:353-407](../../workflow_interpreter/foreman/tick.py)).
Delegates may return evidence but never select, claim, merge, or close stages.

### D9. Replace phase ownership at one CLI seam

Add typed phase_bridge.py and one phase-bridge subcommand. Replace only phase
scope's select/claim/dispatch/close loop; retain context, deep-plan approval,
all-stages-closed gate, roadmap exit, and report. phase-execution is the thin
entry point ([.claude/skills/phase-execution/SKILL.md:9-16](../../.claude/skills/phase-execution/SKILL.md));
the all-stages rule remains in execution
([.claude/skills/execution/SKILL.md:89-99](../../.claude/skills/execution/SKILL.md)).

### D10. Make Stage 2 consume Stage 1

Slice 0 records Stage 1's module, exported symbol, signature, and Stage 2's
required call/extension and failing test. Stage 2's brief carries those facts.
Before its creation, the bridge verifies its base includes Stage 1's landing SHA
and the symbol exists there. The review brief rejects an artifact that bypasses
the symbol. A green Stage 2 cannot be evidence for an unseen Stage 1.

### D11. Deterministic conflict, then human resolution

Stage 3's admission record identifies an existing literal in
tests/test_phase_bridge.py, within the writable tests/** mount, with path, base
blob OID, line number, complete preimage, and required stage-3 replacement. Its
brief carries a literal unified patch with context and requires git apply --check;
acceptance and review require that exact replacement. An adjacent edit cannot
reach ship.

After Stage 3 creates its root, an intentional interloper commit changes the same
preimage to interloper on the working branch. Stage 3's signed artifact changes it
to the specified stage-3 value. D7 must report a same-hunk conflict with S/path.
A human then resolves the named scratch merge, runs the repository gate there,
explicitly authorizes landing, and the bridge CASes and closes Stage 3. Thus every
child closes before the ordinary epic exit gate; escalation is proof evidence, not
a permanently open stage.

### D12. Retain evidence, then clean attempts

After successful close, remove the per-attempt scratch worktree immediately but
retain scratch ref, instance branch, and all three refs/wf namespaces for 30 days,
with OIDs in D2. After 30 days cleanup may delete only a closed attempt whose
recorded landing evidence still matches. It never deletes active, halted, or
escalated attempts. O2 teardown uses this retention rule.

## Landable slices

### Slice 0: admit one proof substrate (0.5–1 engineering day)

Create the disposable bridge-proof roadmap, ws-bridge-proof epic, approved deep
plan, and exactly three child stages only after O2/D10/D11 pass. This changes no
interpreter code, so a repo gate would prove nothing. Its real check after
creation is this bd/plan join; the plan writes Stage: <stage-id> once per task:

    PLAN=docs/workstreams/bridge-proof/plans/bridge-proof.md
    epic="$(bd list -t epic -l ws-bridge-proof --json | jq -er 'if length == 1 then .[0].id else error("expected one bridge-proof epic") end')"
    actual="$(bd list --parent "$epic" --json | jq -r '.[].id' | sort | jq -Rsc 'split("\n") | map(select(length > 0))')"
    planned="$(rg -o 'Stage: [^[:space:]]+' "$PLAN" | sed -E 's/Stage: //' | sort | jq -Rsc 'split("\n") | map(select(length > 0))')"
    jq -en --argjson actual "$actual" --argjson planned "$planned" '($actual|length) == 3 and ($actual|unique|length) == 3 and ($planned|unique|length) == 3 and (($actual|sort) == ($planned|sort))'

Record the Stage 1/2 symbol contract and Stage 3 literal patch. False is an
admission failure, not a graph run.

### Slice 1: identity, recovery, graph definition (1–1.5 engineering days)

Implement D2–D6. Test detached HEAD/ref changes, lock contention, re-entry after
an intervening commit, bd brief reconstruction after scratchpad loss, exact-parent
claim refusal, and phase-delivery strict-superset/no-warning.

**Verification:** focused bridge, identity, graph, and CLI tests; then repo gate.

### Slice 2: scratch landing and status (1.5–2 engineering days)

Implement D7–D8. Test signed OID/artifact/instance-tip agreement and each refusal;
merge-by-OID only; conflict/red-gate/CAS preservation; branch immutability before
green scratch gate; all halt statuses including audit and branch-diverged; retention;
and no push.

**Verification:** focused bridge, tick/status, merge, landing tests; then repo gate.

### Slice 3: phase routing and proof (0.5–1 engineering day plus graph time)

Implement D9, run the admitted proof sequentially, retain Stage 3 escalation
evidence until human resolution/close, and verify Stage 2's real symbol use and
failing dependency test. Run skill catalog check and cold reread for skill docs.

**Verification:** Slice 0 join; Stage 1 close; Stage 2 consumption; Stage 3
escalation then human-resolved close; all-stages-closed exit; skill catalog; repo gate.

### Repository gate for every implementation slice

Run from repository root, per
[.claude/project/verification.md:46-64](../../.claude/project/verification.md):

1. uv run pytest -q -m "not bd and not live"
2. uv run pytest -q -m bd
3. uv run pytest -q -m proc
4. uv run ruff check workflow_interpreter/ tests/ and uv run ruff format --check workflow_interpreter/ tests/
5. MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/

## Cost and limits

An engineering day is active human or agent engineering time, excluding
approval/signing wait. Slices 0–3 are **3.5–5.5 engineering days**, including
implementation-agent work. Proof execution is separate: one round is only n=1
calibration, while max_entries = 3
([workflows/feature-delivery.toml:11-16](../../workflows/feature-delivery.toml)).
Budget **4.8–9.6 active graph hours, $48–$96, and 12–24M Codex tokens**, plus
three signing ceremonies and Stage 3 resolution wait. It covers one/two rounds
for Stages 1–2 and two/three for deliberately conflicted Stage 3; record actuals
before expansion.

## Deferred and invalidating evidence

- General small/standard routing, dynamic grants, graph-per-phase graphs,
  decomposition in graphs, automatic signing, gate timeouts, and spend limits.
- Signed OID/artifact ref/instance-tip mismatch, non-green scratch gate, or failed
  CAS is fail-closed: do not close or select N+1.
- If no three Beads meet O2/D10/D11, do not manufacture a proof phase.
- Widening grants, bypassing the band, pushing, force/rebase, auto-resolution, or
  deleting retained evidence needs a new owner ruling.
