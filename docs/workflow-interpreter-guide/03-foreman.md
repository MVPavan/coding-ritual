# 03 — Foreman

Deterministic code that decides what happens next. No LLM client exists in the package
(ADR 0004 D4).

```
foreman tick <root_id>     one decision, then exit
foreman run  <root_id>     tick repeatedly until it must stop
foreman status <root_id>   read-only view
```

`run` is what the bridge calls. `tick` is what you call by hand when a run stopped and
you want exactly one more step.

## The tick ladder

A tick is a pure function of durable state plus git. Nothing is remembered between
ticks. It walks this ladder and stops at the first rung that applies
(`foreman/tick.py:422-560`):

1. **Take the band.** A non-blocking `flock`. Busy → report `contended`, do nothing.
2. **Check ground truth.** Store canary, load root, assert membership, ensure
   ownership. Then `audit` re-reads the records; a violation opens a halt gate.
3. **Reconcile against git.** A recorded commit missing from the repository halts. A
   root that cannot progress reports `stalled`.
4. **Repair.** Clean finished toolchains, and close any activation that completed but
   was never closed — the crash between `record_exit` and `close`.
5. **Take in gates.** For every open gate, look for a signed payload in its inbox and
   verify it. Closures and refusals both end the tick.
6. **Advance what is already running**, before starting anything new: minted, then
   dispatched, then exit-recorded, then evidence-recorded. First match wins.
7. **Otherwise route the head** — the finished activation with no successor. Match an
   edge, mint the successor, dispatch it in the same tick. Or open a gate, reach a
   terminal, or halt.

Rungs 6 and 7 are the important pair: the foreman always finishes what is in flight
before considering what comes next, so a run only ever has one thing to advance.

A tick takes **at most one branch**, which is one decision. A branch may still make
several durable writes — mint plus dispatch, or evidence plus close.

## Tick frequency: there is no clock

Nothing schedules ticks. A tick happens because someone called `foreman tick`, or
because `run`'s loop came round (`foreman/tick.py:660-680`):

| Situation | The loop |
|---|---|
| Progress made (dispatched, settled, gate closed) | Tick again **immediately** |
| An agent is still running (`blocked`) | Sleep `poll_s`, **30 s** default |
| Another tick holds the band (`contended`) | Sleep `poll_s` |
| Halted, terminal, gate opened, stalled, refusals | **Stop**, hand back control |

So while a 20-minute agent works, the foreman wakes roughly every 30 s, confirms the
wrapper is alive, and sleeps again. Confirmed at `foreman/cases.py:360-366` — a
dispatched activation with a live wrapper returns `blocked`.

Exceeding the 8 h wall limit is reported as a stall, so one field answers "why did
this stop".

A faster clock exists but does not tick: `foreman monitor` polls every 5 s, flags a
stale heartbeat at 120 s, fires its host hook at most every 30 s. That is
notification, not decision.

Two known defects make this worse than designed: a dropped `blocked` and an unreported
opened gate both turn "sleep or hand back" into "spin until the wall limit". See
[diagrams.md](diagrams.md) §16.2 items 1 and 2.

## Routing, in one place

`route` checks in order: no-progress breaker, undeclared `fail_code`, first matching
edge, then fallback. It fails closed on gate-to-gate routes and on a mutable gate
without a bound artifact.

Two details that surprise readers:

- A bound refusal whose fallback is a **task** never mints that task. It opens a
  `HALT_CEILING` halt instead (`foreman/cases.py:276-328`).
- The **store**, not the router, derives the round: any edge mint landing on a
  region's `entry_node` opens the next round and counts against `max_entries`
  (`bdio/mint.py:286-334`).

## The other verbs

1. **`create`** — instantiate a graph as a root directly, no bridge. Takes
   `--instance-key`, `--input NAME=PATH`, and two test flags.
2. **`supervise`** — the wrapper process. The foreman spawns this at itself.
3. **`inspect`**, **`monitor`** — read one activation, or watch a root live.
4. **`steer`** — intervene in a running activation: `--acknowledge-uncertain`,
   `--instructions-file`, or the experimental `--in-place`. Always needs `--reason`.
5. **`integration`**, **`children`** — the coordination machinery
   ([09-coordination.md](09-coordination.md)).

Worth connecting to gates: `foreman create` accepts `--allow-unsigned-gates`, but the
bridge passes `allow_test_flags=False`, so a bridge-admitted root can never set it.
The escape hatch exists and is closed on the path that matters.

## What it returns

A `TickReport`: `contended`, `halted`, `stalled`, `blocked`, `dispatched`, `settled`,
`opened_gate`, `closed_gates`, `waiting_gate`, `refusals`, `terminal`, `terminal_node`,
`events_backfilled`. `run` wraps it in a `RunReport` with a tick count.

## What it does not do

- **No LLM.** No model client in the package.
- **No agent execution.** It spawns the wrapper and forgets it until a record appears.
- **No branch writing.** It never moves the target ref; only the bridge does.
- **No memory.** Kill it mid-run and the next tick reconstructs everything.
