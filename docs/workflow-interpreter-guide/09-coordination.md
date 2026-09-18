# 09 — Coordination: decision policy and child workflows

**Status: built, dormant.** About 2,242 lines across `foreman/decisions.py`,
`foreman/children.py` and `foreman/replacement.py`. No shipping graph exercises any of
it — `feature-delivery` declares no `[node.decision]` blocks and no children.

This document describes machinery that has never met a real use. Treat every claim
here as "what the code intends", not "what has been proven".

## The shape: an owner root with slots

A root can be a **member** of another root. `root.metadata.coordination` is a
`CoordinationLink` holding `owner_id`, `slot`, `generation`, `reservation_id`,
`ceiling` and an optional `predecessor_id`. If that field is `None`, none of this
machinery runs.

All durable coordination stays in Beads: *"Bounded independent roots; all durable
coordination remains in Beads."* Children are genuinely independent roots with their
own graphs, ticks and wrappers.

## `foreman children`: eight verbs

| Verb | Arguments | What it does |
|---|---|---|
| `admit` | slot, `--graph`, `--input` | Register a child: graph and inputs, capacity reserved |
| `start` | slot, `--admission` | Create and launch the child root |
| `status` | — | Read the owner's coordination view |
| `collect` | slot, generation | Take the finished child's result |
| `cancel` | slot, generation, `--request-key`, `--reason` | Cancel, with a receipt |
| `recover` | slot, generation | Repair a crashed child |
| `drive` | `--max-concurrent`, `--max-wall` | Run the whole fan-out loop |
| `replace` | `--slot`, `--generation`, `--request` | Swap a member for a new generation |

`admit` and `start` are two steps on purpose: `MemberAdmission` holds *"everything
needed to repair `create_root` after a crash"* — graph body, config, inputs — so a
crash between them is repairable rather than ambiguous.

A `ChildRecord` moves `admitted → running → settled → collected`, or
`cancel_pending → cancelled`. It carries the child's pid, proc start time, session id,
terminal, outcome and evidence reference — enough for the owner to prove liveness of a
process it did not spawn.

`CollectedChildResult` is the receipt: terminal, graph hash, config signature, base
commit, outputs ref/commit/tree, artifact commit/tree, and `artifact_source`
(`computed-output` or `activation-input`). The owner never takes the child's word for
what it produced; it takes git object ids.

## Decision policy: escalation with a fixed answer space

How a **member** asks its **owner** a question it may not answer alone.

```python
DecisionTrigger = Literal["fail_plan", "doubt", "allowance_exhausted", "input_oversize"]
DecisionAction  = Literal["continue_declared", "replace", "human"]
```

A node declares `[node.decision]` with `triggers`, `actions`, a `decision_task` (its
own runner, model, instructions, verify, budgets) and an optional `replacement_input`.

**The identity is the point.** When a trigger fires, `queue_boundary`
(`foreman/decisions.py:64-99`) builds a `BoundaryIdentity` with eleven fields: owner,
root, generation, graph hash, config signature, source activation, trigger kind, route
digest, artifact commit, artifact tree, policy digest. A complete fingerprint of the
exact situation being asked about. A response arriving after any of it changed is
invalid — the question no longer exists.

**The request is a state machine**, not a message:
`requested → admitted → awaiting_output → consumed → applied`, with `human_attention`
and `invalidated` as exits. Each transition is durable, so a crash resumes rather than
re-asks.

**The response is constrained by construction.** `DecisionResponse` carries the
`request_digest`, `parent_generation`, producing root and activation, an `action` drawn
only from the actions the *author* granted, and a `rationale` of 1–2048 characters.
The docstring: *"Author-granted actions; responses cannot extend this set."* The
owner's model decides *which* permitted action, never *what the options are*.

**The three actions:** `continue_declared` follows the graph edge anyway; `replace`
swaps in a replacement member of a new generation; `human` escalates out of the machine.

## How it enters the tick

`advance_decision` wraps every tick (`foreman/decisions.py:427`):

1. No coordination link → plain local tick. The normal path.
2. A `prepared` successor exists → advance the replacement first, report `blocked`.
3. `state.human_attention` → halt.
4. The child is cancelled, collected, or carries blocking attention → halt.
5. A pending request exists → advance it one state, then tick locally.

A coordinated root does not get to do its own work while a question about it is
outstanding.

## Assessment

The design instinct matches the "LLM in the loop, not in the hot loop" rule: judgment
happens at a boundary, with the option space fixed by the graph author, the question
fingerprinted so a stale answer cannot apply, and every transition durable. That is a
strictly better shape than an agent free-forming a recovery.

The risk is that it was built before the thing that needs it. The obvious use is
parallel stages — an owner fanning out children and collecting them — which is exactly
what the epic serialization in [02-phase-bridge.md](02-phase-bridge.md) forbids today.
If that is the intent, the serialization limit is temporary scaffolding rather than a
design choice, and these 2,242 lines finally earn their place.
