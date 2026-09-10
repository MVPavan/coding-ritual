# Phase-Execution Interpreter Bridge Plan (v12)

**Purpose.** Prove one real multi-stage roadmap phase through the interpreter,
entered from `/phase-execution`, with graph-owned gate rendering and stage closure,
and without a prose stage loop running alongside it. The proof is reproducible from
Beads, Git, and the wrapper directory.

In this plan, the target ref is the attached mainline branch of the coordinator
checkout; it is not the interpreter's per-instance branch (`INSTANCE_BRANCH_REF`).

**Scope.** This is the **sequential bridge only** (owner ruling 2026-09-10).
It runs one named stage, returns evidence and computed phase state to the LLM, and
lands its signed artifact only while the target remains at its recorded base. It is
not a selector, scheduler, automatic signer, general merge tool, or a solution for
two graphs landing to one branch. It does not commit, push, rebase, reset, or delete
evidence.

**Acceptance criterion.** Stage 1 lands and closes through the graph; Stage 2 starts
from that landed state and does the same. The LLM invokes each named stage separately;
the bridge never advances the phase itself. A changed target ref is a clean refusal,
not an opportunity to construct or resolve a merge.

**Status.** v12, 2026-09-10. Every `file:line` citation below was read in this
worktree. Citations describe observed code; implementation requirements are marked
as such.

## Numbered decisions

### D1. The LLM owns phase advancement; the interpreter owns the stage loop

`phase-bridge <epic> <stage> [--retry] [--trace]` validates one open, direct-child
stage; it never selects one. It returns stage evidence plus computed state:
`phase-exhausted` when every direct child is closed, `blocked` when open work prevents
the requested stage, otherwise that stage's result. This is a fact for the LLM, not a
decision to continue.

Keep the execution skill's phase-loop header, but replace only its stage-loop body
with a call for the LLM-selected stage and handling of the returned state. The present
body selects and claims direct children at `.claude/skills/execution/SKILL.md:74-88`.
`Foreman.run` remains the hidden hot loop: it repeats ticks until a halt, terminal,
gate, stall, or wall limit (`workflow_interpreter/foreman/tick.py:518-547`).

The bridge validates attached, clean coordinator state; direct-child membership;
the named stage's open state; and that no other direct child has unfinished bridge
admission. It uses a narrow phase adapter for list/show, metadata merge/read-back,
claim, dependency inspection, and closure with fixed argv and an actor on every
write. It does not expand `BdClient` into a phase scheduler.

### D2. Admit durably before claim, then repair owner-first

Store typed `phase_bridge` metadata on the stage. Before claim, write and read back:

```text
schema = "phase-bridge/3"
state = "prepared" | "admitted" | "landing" | "landed" | "gate-red" | "closed"
epic_id, stage_id, attempt, instance_key
target_ref, expected_base_commit, root_id?
landed_oid?, tree?, gate_receipt_digest?, landing_receipt_digest?
previous_attempts[]
```

`prepared` and `admitted` are stage-metadata writes, each read back; `landing` is
recorded by the durable wrapper-directory landing intent before CAS and is the
authoritative record that CAS may be in flight; `landed` is the stage-metadata
write/read-back after a successful CAS and durable receipt.

The prepared intent makes a crash between metadata write and claim discoverable by
scanning all direct children, not by `bd ready`. It records the target ref and expected
base before root creation. The root remains authoritative for pinned graph, inputs,
configuration, terminal, and its persisted base; the stage relation is a bridge
journal, not a duplicate root record.

For attempt 1, derive `instance_key` as
`phase-bridge:<epic_id>:<stage_id>:attempt:<attempt>`; recovery reuses the recorded
key. An eligible `--retry` creates the next attempt number and its distinct key, never
a second root for the prior attempt's key.

On every entry, before a new claim or root, run this five-row repair table. Its first
row deliberately requires `HEAD == expected_base_commit`: `instantiate` currently
captures repository HEAD as its root base (`workflow_interpreter/foreman/resolve.py:350-381`).

| Observed evidence | Required action |
| --- | --- |
| Prepared intent, no root for its key, and `HEAD == expected_base_commit`, with recorded branch/stage still valid | Create the recorded root and continue. |
| Root without a self-link | Use existing raw-record convergence, which repairs the self-link before parsing (`workflow_interpreter/bdio/roots.py:247-265`). |
| Valid root, missing instance branch | Re-create the branch from the root's persisted base, without reading current HEAD (`workflow_interpreter/foreman/resolve.py:280-289`). |
| Root and branch exist, but relation is incomplete | Validate key, stage, target ref, expected base, and root identity; complete and read back the relation. |
| Conflicting identity, two roots with instance beads, or evidence selecting no unique action | Return evidence for human attention; create no root and move no ref. |

Never resurrect “lowest ID wins” as the primary rule. Existing convergence prefers the
root that owns instance beads and refuses two owners (`workflow_interpreter/bdio/roots.py:268-305`).
An unavailable Beads store or missing metadata halts recovery rather than creating a
second journal.

### D3. Graph terminal and gate evidence are the closure authority

The selected stage supplies the root's brief; the bridge runs the approved graph and
requires a closed, accepted immutable `ship` gate before landing. The current
`feature-delivery` graph has a bounded implement/review region and immutable human
`ship` and `triage` gates (`workflows/feature-delivery.toml:11-16,18-94,119-165`).
Its writer is explicitly allowed production and test changes
(`workflows/feature-delivery.toml:29-40`).

Re-verify the gate payload and signature; require its root, gate, outcome, artifact
OID, tree OID, fingerprint, digest, and artifact reference to agree. Gate verification
precedes carrier repair (`workflow_interpreter/bdio/gates.py:318-341`), and immutable
gates compare payload commit and tree OIDs with recorded artifact values
(`workflow_interpreter/bdio/gates.py:484-508`). The standard signed payload has root,
gate, outcome, artifact, and nonce—not a bridge-specific review schema
(`workflow_interpreter/bdio/signing.py:196-214`).

`--retry` cannot outrank a halt. `Foreman.tick` already returns an unresolved halt as
halted (`workflow_interpreter/foreman/tick.py:400-410`); before the bridge considers a
new root, it must load the old root and make the equivalent check. Keep the numeric
retry cap **cut**. Record `attempt` and `previous_attempts` in the bridge gate view that
the human reads before signing; the human must be able to see whether this is a new root
and the evidence for all prior attempts.

Make the no-cap reasoning executable. Add an explicit
`[instance].phase_bridge_retry_terminals` schema field, listing the only terminal names
for which this bridge may create a new root; for this proof it names `shipped` and
`abandoned`. `gate-red` is eligible only when it arose after the declared `shipped`
terminal and its approved `ship` gate. The phase-bridge CLI rejects `--retry` from any
other terminal or unlisted event.

Add a semantic rule that reverse-walks every entry-to-listed-terminal path and errors
unless each path crosses a `gate_type = "human"` node. The rule belongs in the existing
semantic validator and normal graph loader, which already turn semantic errors into
`GraphValidationError` (`workflow_interpreter/schema/validator.py:85-97`,
`workflow_interpreter/schema/loader.py:199-231,252-264`). The invalidating trigger is
therefore mechanically enforced: **any path reaching a new root without a human
signature**. A graph that lacks the declaration or fails the traversal is ineligible
for the bridge rather than silently retaining no cap.

### D4. Landing is one signed fast-forward, protected by a durable intent

Let `H` be the recorded `expected_base_commit` and `A` the signed artifact OID. Before
moving the target ref, require the ref still names `H`, `H` is an ancestor of `A`, and
the verified immutable gate names `A` and its recorded tree. Thus `A` is both the
signed commit and the landed commit. Run the five-item/six-command repository gate in
a detached checkout at `A`; only complete, green results naming `A` and its tree may
proceed. A red, incomplete, or mismatched result leaves the target unchanged and does
not authorize a new landing attempt.

Persist **and read back** a landing intent in the wrapper directory before the ref
move:

```text
schema = "phase-bridge-landing/1"
ref, expected_base = H, artifact_oid = A, tree
gate_receipt_digest, stage, attempt
```

Use durable old-or-new writes for this intent and the later receipt; `write_durable`
flushes the new file and directory so a crash yields a complete old or new record,
never a partial one (`workflow_interpreter/supervisor/paths.py:114-130`). Then call
the existing `update_ref_cas(ref, A, H)`, whose contract is “advance `ref` only when
it still names `old`” (`workflow_interpreter/supervisor/gitio.py:555-562`). A failed
CAS leaves every Bead open and returns `halted: branch-moved` with the intent and
observed target. It does not retry, merge, or select another stage.

Only after a successful CAS: write the durable landing receipt, update/read back stage
metadata, then close/read back the stage. The pre-close receipt includes the intent
digest, target ref, expected base, signed/landed OID, tree, gate digest, repo-gate
results, and `closure_state = "pending"`; the close reason names its digest. The
post-close read-back is the closure evidence and changes the stage relation to `closed`.

Recovery reconciles unfinished landing intent **before any other bridge action**.
After re-verifying immutable gate and repository-gate evidence, it may reconstruct a
missing pre-close receipt from the durable intent and finish closure only when the
target is exactly `A`, or when `A` is an ancestor of the current target.
An intact intent with the target still exactly `H` is the benign `intent-before-CAS`
case: an operator may resume it manually after revalidation, but recovery refuses for
human attention rather than automatically re-attempting CAS because v12 makes ref
motion a one-shot landing boundary.
Unrelated history, a target that does not contain `A`, a mismatched tree or gate digest,
or ambiguous stage/attempt identity refuses for human attention. No recovery path moves
a ref.

v11's “no CAS needed because the lock guarantees one writer” rationale is withdrawn.
There is no lock in v12; CAS is the mechanism for “move only if still `H`.” This is a
fast-forward-only bridge—not a construction policy for any other commit shape.

### D5. The landing gate has an explicit, large trust assumption

**T1 — trusted gate code.** The landing gate executes candidate-controlled tests and
their dependencies as trusted code. They may change host-visible shared refs, wrapper
receipts, or other filesystem state; the bridge does not claim to contain them. This is
the largest trust assumption in this plan and must appear in operator output before a
landing gate runs.

The full repository gate contains five numbered items and six commands, including
pytest (`.claude/project/verification.md:48-56`). The verifier executes a hashed
program through argv only, but uses `subprocess.run` with inherited `os.environ` and
no sandbox (`workflow_interpreter/supervisor/verify.py:386-418`). A detached clean
checkout does not change that host-process trust boundary
(`workflow_interpreter/supervisor/verify.py:137-167`). Do not describe argv-only
execution as containment.

**Supported-writer contract.** The bridge guarantees safety only for cooperative callers
that invoke one bridge stage at a time: expected-base validation, CAS, durable intent,
and recovery/refusal. The direct-child admission check detects a persisted unfinished
admission; it is not a lock or CAS across two simultaneous calls. Concurrent bridge
calls and arbitrary interlopers are outside v12's guarantee and belong to `cr-g3e`.
A write-capable runner receives shared object, `refs`, log, and `packed-refs` paths read-write
(`workflow_interpreter/supervisor/sandbox.py:385-425,477-486`); it can also be
candidate-controlled gate code under T1. External writers that move the target are
detected only at CAS or recovery and are not blocked or resolved.

### D6. The proof is two real stages in recorded order

Use `cr-7rp` as Stage 1 and `cr-0yc` as Stage 2 only after live eligibility confirms
they are open, real, independently worthwhile work and have no genuine output
dependency. Add **no** fabricated `bd dep`: policy permits dependencies only when one
task relies on another's output, not merely because it is sequenced
(`.beads/beads.md:73-74`).

Prove the sequence with (1) Stage 2's admission-intent record after Stage 1's landing
and closure evidence, and (2) `git merge-base --is-ancestor <stage1-landed-oid>
<stage2-instance-base-commit>`. Those prove order and inherited Git state; they do
not pretend to prove dependency enforcement. The stage/epic record, the two committed
landings, and the wrapper intents/receipts are the reproduction package.

## Landable slices

### Slice 0 — substrate and live probes (no interpreter code)

Create the disposable bridge-proof roadmap and phase only after rechecking the two
source Beads. Record their proof order and trust-boundary decision; do not create a
Stage 1 → Stage 2 dependency. Probe and retain direct-child listing, metadata-before-
claim read-back, claim/metadata atomicity if available, and a real dependency fixture.

**Verify:** roadmap-to-epic-to-stage join resolves; both admission records remain
discoverable before and after claim; no fabricated dependency exists; the fixture shows
a genuine dependency blocks; and T1 is displayed in the landing-gate operator output.

### Slice 1 — vertical admission-to-closure slice (test first)

First write a test using `FakeBd`, a temporary Git repository, and signing fixtures.
It persists intent, admits one stage, interrupts, rediscovers, resumes, fast-forwards
the signed artifact with CAS, writes receipt evidence, and closes the stage. `FakeBd`
already provides deterministic crash injection (`tests/_fake_bd.py:1-18`), and the
real transport is available through the `fake_client` fixture
(`tests/conftest.py:213-222`). Use injected composition seams; do not add a supported
`--fault` CLI surface.

Run three separate fault experiments:

1. Interrupt admission across root creation, self-link, branch, and relation writes;
   prove the five D2 rows, exactly one recoverable root, and owner-first refusal.
2. Interrupt after CAS and before landing receipt/closure; prove recovery finalizes only
   the recorded artifact (or a target containing it) and never moves the ref again.
3. Move the target after interruption to history that does not contain the artifact;
   prove recovery refuses with no closure and no bridge ref mutation. A descendant that
   contains the artifact is the separate D4 finalization case.

**Verify:** focused tests exercise immutable gate selection, the graph-load no-bypass
validator, halt-over-retry, gate-view `attempt`/`previous_attempts`, receipt completeness,
and all three fault experiments against real temporary Git history. Run the repository
gate after the slice.

### Slice 2 — routing and the two-stage proof

Add `phase-bridge`, trace rendering, and the surgical execution-skill body replacement.
The trace reads current stage relation, root/base/terminal, gate evidence, landing intent,
receipt digest, closure result, and computed phase state. It never selects the next stage.
Run the LLM-selected Stage 1 to closure; only then call Stage 2.

**Verify:** both stages reach graph-rendered human gates, resume under their recorded
roots, land their signed OIDs, and close with read-back receipts; the ordering and
ancestry commands in D6 pass; the phase's all-closed exit gate passes; and the five
numbered/six-command repository gate runs. If the execution skill changes, also run its
catalog check prescribed by `.claude/project/verification.md`.

## Cost and measurement

No human-engineering-day estimates are used. Planning estimates separate AI execution
from AI integration/review:

| Slice | AI execution | AI integration/review |
| --- | ---: | ---: |
| 0 | 30–45 min | about 15 min |
| 1 | 4–6 h | 2–3 h, bounded review rounds |
| 2 | 1–2 h | about 1 h, plus live proof |

Measured graph baseline carried from the prior live runs: a shipped two-round root was
about 36 minutes, $2.12 Claude, and 742k Codex input tokens; an abandoned three-round
root was about 55 minutes, $4.16, and 311k tokens. Record graph hours, dollars, and
Codex tokens separately from AI execution, AI integration/review, and the repository
gate. For the two-stage proof, retain the actual values rather than treating the
baseline as a promise.

## Cut from v11, and what it protected

| Cut from v11 | What it protected then; v12 disposition |
| --- | --- |
| Landing queue, lock, and batching | Serialized competing landings and reduced repeated gates; deferred to `cr-g3e`. |
| Scratch merge construction and merge-commit paths | Admitted an artifact after target movement; sequential proof instead requires signed fast-forward. |
| Parked collisions, collision records, decomposition signal, resolution graph | Retained and routed concurrent conflicts; v12 refuses before conflict resolution exists. |
| “Clean merge needs no new signature” | Justified an unsigned constructed merge; moot because v12 lands the signed OID only. |
| Three landing paths | Modeled unchanged, clean-merge, and conflicted target states; v12 has one CAS fast-forward path. |
| No-CAS-under-lock reasoning | Assumed a sole writer; explicitly withdrawn because v12 has no lock. |
| Production `--fault` | Exposed test-only failure controls; replaced by injected seams and three isolated experiments. |
| Automatic bridge-owned phase advancement | Hid the stage boundary from the LLM; retain LLM-owned advancement. |
| False Stage 1 → Stage 2 `bd dep` | Misrepresented sequence as a dependency; preserve intent ordering plus Git ancestry instead. |
| Numeric retry cap | Tried to bound retries procedurally; replace with graph-load enforcement of human-signature dominance. |

## Deferred work and invalidating evidence

**Concurrency is `cr-g3e`.** Its trigger is **“more than one graph may land to the
same branch.”** The deferred design is a merge queue, established prior art: GitHub
Merge Queue, GitLab Merge Trains, Bors-NG, Zuul/Prow, Mergify, and Aviator. Its standard
shape is a temporary branch that merges a candidate onto a target snapshot, re-runs
required checks there, speculatively batches candidates, and bisects to eject an
offender while innocent candidates proceed. The earlier independent design matched
that pattern point for point.

The open decision is build our own queue or adopt GitHub's; that is fundamentally a
choice about remote and CI dependence. Do not pre-empt it here. Sol's four contracts
and eight corrections live in `cr-g3e` and its children; S1 crash-atomic landing,
S2 gate-code trust, and S3 cooperative-writer safety are the three that apply here.

The following invalidate or stop v12 rather than expanding it:

- A target move before CAS, or an unfinished intent whose target excludes the artifact:
  refuse and hand evidence to a human; it is the `cr-g3e` trigger, not a local merge task.
  A post-CAS descendant containing the artifact instead follows D4's closure-only recovery.
- Any graph path that could reach a new root without a human signature: loader rejection
  and owner review; do not reintroduce a cap silently.
- Gate code that cannot be trusted under T1: stop landing and seek a separate containment
  design; do not claim detached checkout or argv-only invocation is a sandbox.
- Missing/ambiguous Beads, root, gate, intent, tree, stage identity, or a receipt that
  cannot be reconstructed from durable evidence: do not close a stage or create a new root.
- A need for orchestrator signatures: defer to `cr-bwo`; v12 uses the graph's existing
  human-gate model.
