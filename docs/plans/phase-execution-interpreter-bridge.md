# Phase-Execution Interpreter Bridge Plan

**Origin:** Bead cr-o85.39; graphs supply process, roadmaps supply ordered content
([docs/ideas/workflow-graphs.md:54-57](../ideas/workflow-graphs.md)).

**Goal:** Route eligible deep-phase stages through one interpreter instance each,
without graph-owned decomposition or a parallel prose stage loop.

## Owner rulings — 2026-09-07

### O1. Auto-land only a re-verified signed artifact through a scratch ref

A graph terminal follows the implementer checks, effects gate, reviewer accept,
and immutable human ship gate
([scripts/verify-feature.sh:34-47](../../scripts/verify-feature.sh),
[workflows/feature-delivery.toml:48-80](../../workflows/feature-delivery.toml),
[workflows/feature-delivery.toml:147-155](../../workflows/feature-delivery.toml)).
The signature binds the approved commit OID; the hash is a cross-check
([docs/specs/workflow-interpreter.md:811-818](../specs/workflow-interpreter.md)).

The bridge retrieves the serialized ship payload and signature and
cryptographically re-verifies them against the current allow-list; it then
compares the newly derived fingerprint and payload digest with the closed-gate
metadata. It does not merely trust recorded `verified_fingerprint` and
`payload_digest` ([workflow_interpreter/bdio/gates.py:330-364](../../workflow_interpreter/bdio/gates.py)).
The payload must name this root, gate, outcome, and exact artifact OID. The
bridge verifies that `refs/wf/<root_id>/artifact/<activation_id>` and
`refs/heads/wf/<root_id>` both dereference to that OID. Artifact, orphan, and
prereset are siblings; only artifact blesses a commit
([workflow_interpreter/supervisor/artifact.py:26-39](../../workflow_interpreter/supervisor/artifact.py)).

The branch-tip comparison is tamper detection: merging the signed OID already
prevents a moved instance branch from landing unsigned code. A mismatch therefore
causes a conservative false refusal, not prevention of a possible unsigned merge
([docs/adr/0001-allowed-paths-is-advisory.md:101-111](../adr/0001-allowed-paths-is-advisory.md)).

The bridge gates a detached scratch worktree, then fast-forwards the attached
coordinator checkout. It never moves the working branch with `update-ref`.
Conflict, a red gate, a changed branch, or a failed fast-forward leaves the
working branch untouched and reports the retained scratch ref. It never pushes,
force-pushes, rebases, auto-resolves, or rolls back.

### O2. One disposable substrate; real code only

There is no existing workstream or phase epic. A second supposed real backlog
phase would author a roadmap solely for this proof. Use one disposable
bridge-proof roadmap and epic. Roadmap, epic, and stage Beads are disposable
process scaffolding; every proof stage also implements one small, open,
independently worthwhile code Bead. Its landing closes that real source Bead.

Slice 0 selects three only when each real source Bead is open and implementable
within `workflow_interpreter/**` and/or `tests/**`. Stage 1 introduces a useful
named symbol. Stage 2's distinct Bead must require that fully qualified symbol
through a production call or extension and through a named test that fails when
the symbol is absent. Stage 3 has its own acceptance criteria plus the D11
one-line conflict contract. Current candidates are cr-o85.40, cr-o85.43, and
cr-o85.46, but none is preselected: no reviewed pair yet establishes the
Stage-1/Stage-2 dependency. If no three meet these conditions, do not invent
proof work.

After the proof report, close, never delete, the bridge epic and its stage Beads;
remove the generated roadmap and phase plan in a separate cleanup commit. The
successful code remains; D12 governs refs and worktrees.

### O3. Keep BdClient closed; use a narrow adapter

`BdClient` omits the needed ready-parent and claim interface
([workflow_interpreter/bdio/client.py:80-121](../../workflow_interpreter/bdio/client.py),
[workflow_interpreter/bdio/client.py:222-242](../../workflow_interpreter/bdio/client.py)).
A separate phase adapter performs exact ready-parent, exact-stage claim, metadata
update, and close with read-back verification. It accepts resolved ids, never
arbitrary `bd` argv or workflow-root operations.

## Decisions

### D1. One root per stage

`max_entries` is a graph ceiling, not a stage-list iterator
([workflow_interpreter/schema/models.py:192-201](../../workflow_interpreter/schema/models.py),
[docs/specs/workflow-interpreter.md:292-308](../specs/workflow-interpreter.md)).
Root reuse compares instance inputs byte-exact
([workflow_interpreter/bdio/roots.py:253-284](../../workflow_interpreter/bdio/roots.py)).
Roadmaps, not graphs, own work units and order.

### D2. Persist one `phase_bridge` relation and cap attempts

Typed metadata on the exact stage holds root id, attempt, pinned base,
authoritative brief digest, working-branch ref, source-Bead id, landing SHA,
scratch ref, scratch-worktree path, resolution gate id, and cleanup eligibility.
Do not add `wf_root_id` to product-stage metadata: `instance_beads` returns every
matching root id ([workflow_interpreter/bdio/reads.py:90-93](../../workflow_interpreter/bdio/reads.py)).

Each created root is one admission attempt. A red scratch gate, conflict, or
fast-forward race requires a new root and consumes the next attempt. A stage has
at most three attempts. At the cap the bridge returns `halted: attempt-cap`,
retains all attempt evidence, and requires an owner decision to abandon or
authorize a new quota. It never silently creates a fourth root. Escalated
attempts are retained until a human resolution closes them or explicitly abandons
them; they are not eligible for automatic D12 cleanup.

### D3. Identify the working branch, take the band, and never update it by ref

The working branch is the attached symbolic `refs/heads/<name>` read from the
coordinator checkout at first admission; detached HEAD refuses. Record that full
ref in D2 and require it on every entry. This is the Git Safety target-base
confirmation ([CLAUDE.md:81-88](../../CLAUDE.md)).

Take the existing non-blocking exclusive flock at `<wrapper_root>/repo-band.lock`
for base capture and the entire landing critical section: clean-tree check,
payload/ref checks, scratch creation/merge, scratch gate, coordinator clean-tree
recheck, coordinator fast-forward, relation write, and both closes. `BandLock`
refuses contention rather than queueing
([workflow_interpreter/supervisor/band.py:24-67](../../workflow_interpreter/supervisor/band.py));
the lock location is specified at
[docs/specs/workflow-interpreter.md:1075](../specs/workflow-interpreter.md).

Merge only in a detached scratch worktree until the final operation. At final
landing, the coordinator remains attached and clean at captured B and runs
`git merge --ff-only <scratch-ref>`. Git then moves the branch ref, index, and
working tree together; a changed tip or non-fast-forward refuses, supplying the
concurrency check. The bridge never uses `update-ref` on the working ref. It may
CAS the un-checked-out scratch ref from B to its detached scratch HEAD before
gating; that ref update does not desynchronize a checkout. A successful
coordinator merge is followed by a porcelain-clean check, not `reset --hard`.

Human or tooling landings during the bridge run must take this band. Raw Git
cannot be locked by convention, but cannot silently win the final fast-forward.

### D4. Pin recovery base and budget the required production seam

Use `phase-bridge/v1/<epic>/<stage>/<attempt>`. Under the admission lock capture
the working tip, pass and record it as `instance-base-commit`, and re-supply it
on every re-entry. A requested retry advances attempt first. Admit N+1 only after
N completes D7.

Slice 1 changes `foreman.resolve.instantiate` to accept an optional
`instance_base_commit`; it passes that value to `create_root`, falling back to
the current HEAD only when absent. This is a production change, not a CLI-only
flag: `instantiate` currently unconditionally reads HEAD
([workflow_interpreter/foreman/resolve.py:334-364](../../workflow_interpreter/foreman/resolve.py)),
and reuse compares the supplied base byte-exact
([workflow_interpreter/bdio/roots.py:253-284](../../workflow_interpreter/bdio/roots.py)).
The CLI validates and forwards `--instance-base-commit`. Slice 1 tests the
default, explicit pin, retry after an intervening commit, and reuse mismatch.

### D5. Bd owns brief bytes

Build `task_brief` from the stage, acceptance, dependencies, user notes, roadmap
row, plan tasks, and (for Stage 2) symbol contract. Pass these bytes to
`create_root`. Root metadata stores the input body and compares it byte-exact on
reuse ([workflow_interpreter/bdio/roots.py:125-154](../../workflow_interpreter/bdio/roots.py),
[workflow_interpreter/bdio/roots.py:253-284](../../workflow_interpreter/bdio/roots.py)).
A scratchpad/execution copy is convenience only: re-entry reads the bd body and
verifies its digest if the copy has gone.

### D6. One static `phase-delivery` graph, with the shared deep spine preserved

`workflows/phase-delivery.toml` has implement, code-review, immutable signed
ship, and shipped, plus triage/abandon. Writers grant only
`workflow_interpreter/**` and `tests/**`; bwrap derives writable grants directly
from `allowed_paths` ([workflow_interpreter/supervisor/sandbox.py:462-486](../../workflow_interpreter/supervisor/sandbox.py)).
Implement verifies `scripts/verify-feature.sh`; code review verifies that command
plus `scripts/review-checks.sh`. This strict superset is pinned, and the graph
definition test asserts `warnings == ()`, including absence of the
`judgment_verify_superset` warning
([workflows/feature-delivery.toml:48-80](../../workflows/feature-delivery.toml),
[workflow_interpreter/schema/rules_flow.py:432-462](../../workflow_interpreter/schema/rules_flow.py)).

The static graph replaces dispatch mechanics, not the execution skill's shared
spine. Admission records the roadmap's risk; this proof is deep. Before any
trust-boundary stage is admitted, the bridge invokes the security skill and
honors its Ask-First result. For each deep stage, an out-of-graph spec-reviewer
reviews the brief/plan contract and the graph's critic supplies the code review;
both artifacts and their dispositions are required before the signer can approve.
This preserves risk routing, security routing, and the deep two-role review
([.claude/skills/execution/SKILL.md:25-45](../../.claude/skills/execution/SKILL.md),
[.claude/skills/execution/references/task-engine.md:115-140](../../.claude/skills/execution/references/task-engine.md)).

The rendered ship view contains only a bounded diff-stat
([workflow_interpreter/foreman/__main__.py:270-285](../../workflow_interpreter/foreman/__main__.py)).
The critic artifact is therefore the content review of record. Before signing,
the human signer must open the full immutable artifact diff out of band and the
two review artifacts; the signed payload records their digests and the reviewed
artifact OID. A diff-stat alone cannot authorize an O2 code landing.

### D7. Scratch-gate, then coordinator fast-forward and close both Beads

Under D3, let B be the captured coordinator OID and S be
`refs/phase-bridge/<root_id>/<activation_id>`. Create S at B, create a detached
worktree below a fresh `mktemp -d` directory outside the repository tree, and
merge the re-verified signed OID there. CAS S from B to the resulting detached
scratch HEAD before the gate. A conflict preserves S and the worktree and reports
every conflicting path.

Before the full repository gate, provision that fresh checkout with `uv sync
--locked`; the project requires Python 3.13 and defines the dev test tools
([pyproject.toml:6-20](../../pyproject.toml)). The wrapper-owned UV cache remains
available to sandboxed work ([workflow_interpreter/supervisor/sandbox.py:490-494](../../workflow_interpreter/supervisor/sandbox.py)). A provisioning failure is
`stalled: environment-unavailable`, not a red gate and not a new attempt; it
preserves S and is retried after the environment is repaired. On provisioning
success, run the five-step repository gate at S.

Only if green, prove B is an ancestor of S, recheck that the attached coordinator
is clean at B, and run `git merge --ff-only S` in that coordinator checkout. A
ref change, dirty tree, or fast-forward refusal retains S and returns
`escalated` with the cause; it does not update the working ref. On success,
record landing SHA, full-gate evidence, signed payload digest/fingerprint, review
artifact digests, and S in D2. Then close both the bridge stage and its real
source code Bead through O3, placing the same landing evidence on each. Do not
select N+1 until read-back proves both are closed. If one close fails after the
irreversible merge, return `stalled: closure-pending` and retry only the
idempotent close/read-back, never the landing.

A red full gate after `shipped` cannot re-enter the terminal graph. It returns
`escalated: gate-red`, retains S, and requires a new attempt with a new root,
full review, and a new signature after the cause is fixed; the three-attempt cap
applies. This explicitly covers the `bd` and `nested_sandbox` checks omitted by
the in-graph verifier ([scripts/verify-feature.sh:34-43](../../scripts/verify-feature.sh),
[.claude/project/verification.md:46-64](../../.claude/project/verification.md)).

### D8. Report one status observation

One bridge call makes one tick/status observation and exits; it never calls the
eight-hour-default run ([workflow_interpreter/foreman/constants.py:137](../../workflow_interpreter/foreman/constants.py)).
It returns exactly one of:

- `running`: dispatchable/routable state; skill may reinvoke.
- `awaiting_approval`: ordinary open human gate; reinvoke after gate action.
- `halted`: audit/dead-end halt with gate id and one of `fail-code`,
  `branch-diverged`, `precondition-refused`, `inputs-unavailable`,
  `sandbox-unavailable`, or `bound-violated`; also `attempt-cap`.
- `stalled`: recoverable wrapper, transport, provisioning, or post-landing
  closure-pending state with reason.
- `escalated`: D7 conflict, red gate, or fast-forward race, with S.
- `abandoned` or `shipped`: graph terminal; only `shipped` proceeds to D7.
- `closed`: D7 recorded the landing and read back closure of both Beads.

The six dead-end kinds are fixed in the frontier enum
([workflow_interpreter/foreman/frontier.py:38-46](../../workflow_interpreter/foreman/frontier.py)); audit halts are surfaced by tick
([workflow_interpreter/foreman/tick.py:353-407](../../workflow_interpreter/foreman/tick.py)).
Pre-admission refusal is specifically `halted: precondition-refused`, not an
untyped claim to “fail closed.” Delegates may return evidence but never select,
claim, merge, or close stages.

### D9. Replace phase ownership at one CLI seam, after the retained gate is fixed

Add typed `phase_bridge.py` and one `phase-bridge` subcommand. Replace only
phase scope's select/claim/dispatch/close loop; retain context, deep-plan
approval, roadmap exit, and report. `phase-execution` remains the thin entry
point ([.claude/skills/phase-execution/SKILL.md:7-16](../../.claude/skills/phase-execution/SKILL.md)).

The pre-existing retained all-stages-closed gate is defective: without `--all`,
closed child stages are omitted, so its own `n > 0` predicate cannot pass. The
bridge proof depends on P2 bead `cr-dbk`: Slice 0 adds `cr-dbk` as a blocking
dependency of its proof epic and refuses dispatch until the fix is closed and
read back. Its replacement gate is:

    n=$(bd list --all --parent <epic> --json | jq 'length')
    u=$(bd list --all --parent <epic> --json | jq '[.[]|select(.status!="closed")]|length')
    [ "$n" -gt 0 ] && [ "$u" -eq 0 ]

On failure it prints unclosed children using the same `--all` query. This
preserves the execution skill's intended discipline gate while making it
satisfiable ([.claude/skills/execution/SKILL.md:89-99](../../.claude/skills/execution/SKILL.md)).

### D10. Execute the Stage-2 counterfactual

Slice 0 records Stage 1's module, exported symbol, and signature; Stage 2's
required production call/extension; and one named Stage-2 test with the expected
missing-symbol failure. Admission rejects a pair that cannot name this test.
Stage 2's brief carries all of those facts.

Before Stage 2 creation, the bridge verifies its base contains Stage 1's landing
SHA and the symbol exists there. After Stage 2 lands, Slice 3 proves causality:
create a temporary detached worktree at Stage 1's parent B0; apply the recorded,
binary-safe Stage-2 counterfactual patch (the Stage-2 consumer and named test,
generated as `git diff --binary <stage1-sha> <stage2-sha> -- <recorded-paths>`)
to B0; and run the named test there. Admission requires that patch to apply
cleanly. The test must fail with the recorded missing fully-qualified-symbol
diagnostic. A passing test, another failure, or a patch-apply failure rejects the
proof. Remove this temporary worktree after recording the command and result.

Thus the proof executes Stage 2 without Stage 1, rather than relying on review
judgment about ancestry or a cosmetic reference.

### D11. Deterministic conflict, then an OID-bound human resolution

Slice 0 creates the dedicated writable fixture
`tests/fixtures/phase_bridge_conflict.txt`; Slices 1–2 must not modify it.
Slice 0 records its path, complete preimage, and required Stage-3 replacement,
but not a blob OID or line number. At Stage-3 root creation, after Slices 1–2
have landed, the bridge re-pins the fixture's then-current blob OID and line
number at B and verifies the recorded complete preimage. The Stage-3 brief carries
the literal unified patch with context and requires `git apply --check`;
acceptance and review require that exact replacement. The fixture is within the
real `tests/**` bwrap grant
([workflow_interpreter/supervisor/sandbox.py:477-486](../../workflow_interpreter/supervisor/sandbox.py)).

After Stage 3 creates its root, an intentional interloper commit changes that
preimage on the working branch. Stage 3's signed artifact changes it to the
specified Stage-3 value. D7 must report a same-hunk conflict with S/path and
record the escalated attempt, B, signed artifact OID, scratch pre-conflict HEAD,
and expected conflict path.

The human resolves only in that retained detached scratch worktree, commits H
with parents B and the signed artifact OID, and asks the bridge to resume the
recorded attempt with H. Under the band, the bridge checks that relation,
re-verifies H's full repository gate, and requires a new immutable human
resolution gate whose re-verified payload binds root, attempt, B, original
artifact OID, conflict path, H, full-gate evidence digest, and full-diff/review
artifact digests. It then CASes the un-checked-out S from its recorded
pre-resolution value to H, proves B is ancestral to H, and lands only via the
same coordinator `git merge --ff-only S` and dual-Bead closure as a clean D7
landing. The relation records H and the resolution-gate OID/digest. A different
attempt, parent set, payload, or gate is refused. Every human-resolved landing
therefore has the same cryptographic, review, gate, and closure evidence as a
clean landing.

### D12. Retain evidence, then clean eligible attempts

After successful closure, remove the per-attempt scratch worktree immediately
but retain scratch ref, instance branch, all three `refs/wf` namespaces, and the
D2 OIDs for 30 days. After 30 days cleanup may delete only a closed attempt whose
recorded landing evidence still matches. It never deletes active, halted, or
escalated attempts. O2 teardown follows this retention rule.

## Landable slices

### Slice 0: admit one proof substrate (0.5–1 engineering day)

First read back that `cr-dbk` is closed and that its `--all` gate is present;
then create the disposable bridge-proof roadmap, `ws-bridge-proof` epic, approved
deep plan, dedicated D11 fixture, and exactly three child stages only after
O2/D10/D11 pass. The proof epic explicitly depends on `cr-dbk`. This changes no
interpreter code, so a repository gate would not prove bridge behavior. Its
admission check is this bd/plan join; the plan writes `Stage: <stage-id>` exactly
once per task:

    PLAN=docs/workstreams/bridge-proof/plans/bridge-proof.md
    epic="$(bd list -t epic -l ws-bridge-proof --json | jq -er 'if length == 1 then .[0].id else error("expected one bridge-proof epic") end')"
    rows="$(bd list --all --parent "$epic" --json)"
    actual="$(jq -c '[.[].id] | sort' <<<"$rows")"
    planned="$(rg -o 'Stage: [^[:space:]]+' "$PLAN" | sed -E 's/Stage: //' | sort | jq -Rsc 'split("\n") | map(select(length > 0))')"
    jq -en --argjson rows "$rows" --argjson actual "$actual" --argjson planned "$planned" '
      ($rows|length) == 3 and ($actual|length) == 3 and
      ($planned|length) == 3 and ($actual|unique|length) == 3 and
      ($planned|unique|length) == 3 and (($actual|sort) == ($planned|sort)) and
      all($rows[]; .issue_type == "task")'

Separately read back that Stage 2 depends directly on Stage 1 and Stage 3 depends
directly on Stage 2; reject any extra direct proof-stage dependency. Record the
Stage-1/Stage-2 symbol and counterfactual-test contract, plus the Stage-3 fixture
contract. `false` is an admission failure, not a graph run. Verify the generated
fixture's exact initial preimage and run `git diff --check`.

### Slice 1: identity, recovery, graph definition, and shared-spine preflight (1.5–2 engineering days)

Implement D2–D6, including the `instantiate` base parameter and CLI forwarding.
Test detached HEAD/ref changes, lock contention, explicit-base re-entry after an
intervening commit, bd brief reconstruction after scratchpad loss, exact-parent
claim refusal, attempt cap, security preflight, two-role review evidence, and the
phase-delivery strict-superset/no-warning pin.

**Verification:** focused bridge, identity, graph, and CLI tests; then repository
gate.

### Slice 2: scratch landing, human resolution, and status (2–3 engineering days)

Implement D7–D8. Test signed OID/artifact/instance-tip agreement and every
refusal; cryptographic re-verification; merge-by-OID only; coordinator index and
working-tree synchronization after fast-forward; conflict/red-gate/fast-forward
preservation; provisioning classification; branch immutability before green;
all statuses; dual-Bead closure recovery; D11's OID-bound resolution; retention;
and no push.

**Verification:** focused bridge, tick/status, merge, landing, and resolution
tests; then repository gate.

### Slice 3: phase routing and proof (1–1.5 engineering days plus graph time)

Implement D9, run the admitted proof sequentially, retain Stage-3 escalation
evidence until human-resolved closure, and execute D10's counterfactual. Re-run
the Slice-0 join with `--all`; verify the repaired all-stages-closed exit; run
skill catalog check and cold reread for skill docs.

**Verification:** Slice-0 join; Stage-1 dual closure; Stage-2 real consumption
and failing counterfactual; Stage-3 escalation then OID-bound human-resolved dual
closure; all-stages-closed exit; skill catalog; repository gate.

### Repository gate for every implementation slice

Run from repository root, per
[.claude/project/verification.md:46-64](../../.claude/project/verification.md):

1. `uv run pytest -q -m "not bd and not live"`
2. `uv run pytest -q -m bd`
3. `uv run pytest -q -m proc`
4. `uv run ruff check workflow_interpreter/ tests/` and `uv run ruff format --check workflow_interpreter/ tests/`
5. `MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/`

## Cost and limits

An engineering day is active human or agent engineering time, excluding
approval/signing wait. The amended slices are **5–7.5 engineering days**:
0.5–1 (Slice 0), 1.5–2 (Slice 1, including the new production base seam), 2–3
(Slice 2, including provisioning and resolution), and 1–1.5 (Slice 3).

Graph-time estimates use the feature-delivery live baseline, not the unrelated
phase-7 build-loop: a shipped two-round root measured about 36 minutes, $2.12
Claude, and 742k Codex input tokens; an abandoned three-round root measured
about 55 minutes, $4.16 Claude, and 311k Codex input tokens
([scratchpad/probes/phase6-live/BASELINE.md:20-35](../../scratchpad/probes/phase6-live/BASELINE.md)).
Assuming Stages 1–2 each take two rounds and deliberately conflicted Stage 3
takes three, the center estimate is about **2.1 graph hours, $8.40 Claude, and
1.80M Codex input tokens**. Allowing the observed variance and one bounded
re-attempt yields **1.8–2.8 graph hours, $6–$13 Claude, and 1–2.5M Codex input
tokens**, plus three signing ceremonies and Stage-3 resolution wait. Record
actuals before expansion.

## Deferred and invalidating evidence

- General small/standard routing, dynamic grants, graph-per-phase graphs,
  decomposition in graphs, automatic signing, gate timeouts, and spend limits.
- Signed-OID/ref mismatch, a non-green scratch gate, or fast-forward refusal
  never closes a Bead or selects N+1.
- A provisioning failure is recoverable `stalled`, not gate evidence; a red full
  gate is `escalated` and requires a new signed attempt within D2's cap.
- If `cr-dbk` is not closed, or no three Beads meet O2/D10/D11, do not create or
  dispatch a proof phase.
- Widening grants, bypassing the band, pushing, force/rebase, auto-resolution,
  deleting retained evidence, or raising the attempt quota needs a new owner
  ruling.
