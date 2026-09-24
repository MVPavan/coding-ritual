# 06 — Recovery

For an eligible infra retry of a crashed resumed writer, the inspector pins
that failed activation's proved recovery tree and resumes its registered vendor
session, within `max_infra_retries`. A changed family/model/effort or policy
digest forces `MODEL_CHANGED`; a changed CLI version forces `VERSION_DRIFT`;
both start fresh only after preserving the crash tree under `prereset`. A crash
source with no recorded CLI version starts fresh with `UNQUALIFIED_SOURCE`.
If the crash never registered a session, its own source registration may be
used only when the proved recovery tree equals the crashed turn's expected
tree; missing identity or tree proof refuses the retry. See
[model-catalog design](../workstreams/model-catalog/design.md) §7; older
fresh/root-source rules in the interpreter spec are superseded there.

`inspector/recover.py`, 561 lines. It answers one question about a
dispatched-but-not-closed activation: **did this run finish, is it still running, or
is it gone?**

Its module docstring is the best design document in the codebase.

## Seven cases

The spec defines three. The code has seven, because four situations the spec's three
cannot express (`inspector/models.py:174-193`):

| Case | When | What happens |
|---|---|---|
| `ABORT_PENDING` | The launch receipt says the abort never finished | Finish the abort |
| `NOT_LAUNCHED` | Lifecycle still `minted` | Nothing was exec'd; dispatch can proceed |
| `STEER_PENDING` | A durable steer intent exists, no close | Finish the steer, mint the continuation |
| `EXIT_RECORDED` | The store or the wrapper dir holds an exit record | Re-run grading if it did not finish |
| `RUNNING` | pid present **and** boot id equal **and** start time equal | Leave it alone |
| `INDETERMINATE` | Liveness could not be answered at all | Write nothing, hand back |
| `DEAD_WITHOUT_EXIT` | Everything else, including identity mismatch | Pin evidence, then close `error_transport` |

The ordering is the design (`inspector/recover.py:290-310`):

```python
if intent is not None:            return STEER_PENDING
if recorded is not None:          return EXIT_RECORDED
if proof.status is INDETERMINATE: return INDETERMINATE
if proof.alive:                   return RUNNING
return DEAD_WITHOUT_EXIT
```

## Five rules worth stealing

**1. The steer intent outranks the exit record.** The steerer writes the exit file
between the kill and the close, so a crash in that window leaves both. Reading the exit
record first would hand a deliberate kill to grading, which finds no completion marker
and calls it `fail_code` — a human's intervention scored as the agent's failure.

**2. Two out of three is not liveness.** pid, boot id and `/proc` start time must all
match. Two matching is a reused pid.

**3. Malformed input classifies; it never raises.** A truncated exit file or corrupt
JSONL tail is recorded in `malformed` and treated as absent, walking toward
`DEAD_WITHOUT_EXIT`. The stated reason: *"a crash loop is strictly worse than a
conservative `error_transport`."*

**4. The pin is a precondition of the close, not a best effort beside it.** For a dead
activation, any ahead commit is pinned **first**, then the close happens — because the
close is what releases the next attempt to reset the tree. Swallowing a pin failure and
closing anyway left a real commit with no ref, for a reset to orphan and a gc to
collect. A pin that can neither succeed nor be shown unnecessary leaves the activation
open for the next tick.

**5. Preserving a commit is not the same as claiming it.** Recovery runs the same
attribution checks as live pinning. It used to run none — and in-repo it would name
*whatever the human had committed since the wrapper died* as this activation's
artifact, which then became the lineage authorizing the next reset to destroy it. That
was probed, not theorized. An unattributable ahead commit goes to `orphan/` quarantine:
reachable forever, claimed by nobody.

## The two fail-closed cases

`STEER_PENDING` and `INDETERMINATE` never close an activation; they hand it back for
another tick or a human.

`INDETERMINATE` is the sharper one — if `/proc` is unreadable for any reason other than
"gone", recovery refuses to guess, because *"a guess here lets a retry run beside a
survivor."* Two agents writing one worktree is the failure this prevents.

One consequence: an `INDETERMINATE` classification stalls the root until the
environment is fixed. That is intentional, and the right trade, but it means a broken
`/proc` becomes a stuck run rather than a noisy one.

## Why this module reads the way it does

Every rule is a scar, and the docstrings name the incidents: "probed", "drill 18",
"drill 22's exit-127 sentinel", and bead `cr-o85.18` for the open question of whether
steer continuations should be exempt from the reset precondition.

This is where "claim is not proof" is enforced hardest, because it deals exclusively
with situations where nobody is left to ask.
