# 01 — Components: who does what

Five actors. Each answers exactly one question, and none answers another's.

| Actor | Package | Its one question | Lives as |
|---|---|---|---|
| **Contractor** | `contractor/` | May this stage start, and where do its commits land? | A command that runs once |
| **Foreman** | `foreman/` | Given what is recorded, what happens next? | A process taking one decision per tick |
| **Inspector wrapper** | `inspector/` | Make one activation happen, and prove what happened. | A detached process per activation |
| **Crew** | vendor CLI | Do the task. | A child process inside bwrap |
| **Store** | `bdio/`, `ledger/` | What is true so far? | A library over bd or SQLite |

## How a step flows

Contractor admits the stage → foreman ticks, mints an activation and dispatches it in that
same tick → wrapper starts, sandboxes and runs the agent → wrapper grades the result
and calls `record_exit` → a later foreman tick reads that record, settles the
activation, and decides the next node.

Two rules make this trustworthy:

1. The wrapper's claim of success is never taken as proof — the foreman re-checks
   evidence (see [07-grading.md](07-grading.md)).
2. No actor writes state except through the store.

## The five confusable pairs

**1. Inspector and wrapper are one thing under two names.** `inspector/` is the
code; the *wrapper* is a running instance of it plus its directory
`wrapper_root/<root>/<activation>/`, its `wrapper.lock` and its `wrapper.json`. The
lock admits one live wrapper per activation. Its entry point is
`foreman/inspect.py:75-83`, which then drives the `inspector/` machinery.

**2. The foreman decides; the wrapper does.** The foreman never launches an agent and
never writes a worktree. The wrapper never chooses the next node. Separate OS
processes.

**3. `foreman tick` and `foreman inspector` are two verbs of one binary.**
`tick ROOT` takes one decision. `inspect ROOT ACT` *is* the wrapper process. The
foreman launches the second as a child of itself.

**4. The wrapper is the jailer, the crew the prisoner.** The crew writes only its
channels, its uv cache and the git paths the wrapper bound writable. Its claim of
success is evidence, never proof.

**5. The contractor owns the outside; the foreman owns the inside.** Epics,
dependencies, branches and the ship gate are the contractor's. Nodes, edges, rounds and
bounds are the foreman's. The contractor calls the foreman; the foreman knows nothing
about epics.

## Who owns the graph

The foreman, entirely. A grep of `inspector/*.py` for any graph reference returns
zero hits. Every use of `resolved_node` is in `foreman/inspect.py:143,165,266`.

- `foreman/inspect.py` resolves **one node** from the pinned graph into an execution
  spec: crew, model, instructions, inputs, verify checks, budgets, profile.
- `inspector/` receives that spec and executes it. It knows processes, sandboxes,
  locks and files. It does not know what a node, an edge or a region is.

The wrapper reads a single node and never an edge. Traversal — frontier, edge
matching, rounds, regions, bounds, fallbacks — lives in `foreman/frontier.py`,
`routing.py`, `cases.py`, `bounds.py`, `resolve.py`.

The graph is pinned into the root at `instantiate` time along with its hash. Editing
the graph file afterwards does not change a running root.

## Inside the wrapper

- **Dispatcher** — builds the workspace and sandbox, launches the crew through the
  fork barrier.
- **Monitor** — watches liveness by pid plus boot id plus `/proc` start time; flags
  stale, then breaches.
- **ExitObserver** — writes `exit.json`, pins artifacts and outputs, grades against
  the node's verify checks.
- **Recovery** — handles the seven ways a previous wrapper can have died
  ([06-recovery.md](06-recovery.md)).

## Is three levels too many?

The contractor is not a third loop. Only two things loop: the foreman's ticks and the
wrapper's monitor. The contractor is a transaction boundary that runs once and returns —
so the shape is **two loops plus one transaction**.

The process split between foreman and wrapper earns its keep on four counts: crash
isolation, liveness detection across a process boundary, sandbox scoping, and
concurrency. The contractor/foreman split earns its keep on **authority** — the contractor
moves `refs/heads/<target>` and closes beads, and keeping ref-moving power outside the
loop that spawns agents is worth something.

The seam that leaks: `foreman/tick.py:746` imports `INSTANCE_KEY_PREFIX` from
`contractor/models.py`, with a comment apologising for crossing the line, because the
foreman must know what a contractor root is in order to defer cleanup. That same seam
produced a real bug — see suspected defect 12 in [diagrams.md](diagrams.md) §16.2.
