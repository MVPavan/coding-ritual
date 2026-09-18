# 05 — Supervisor wrapper

One detached OS process per activation, started by the foreman as
`foreman supervise <root_id> <activation_id>`. It owns exactly one activation from
launch to exit record, then dies. You never invoke it yourself.

The code spans two places: `foreman/supervise.py` is the entry point that resolves the
node and decides *what* to run; `supervisor/` is the machinery that runs it and knows
nothing about graphs.

## What one wrapper does, in order

From `foreman/supervise.py:234-300` and `supervisor/run.py:178-275`:

1. **Take `wrapper.lock`.** Held means another wrapper is alive on this activation →
   exit `LOCKED`. This is what makes double-dispatch impossible.
2. **Check it is still ours.** Load the activation, assert it belongs to this root,
   assert its lifecycle is still `minted`. Anything else exits `STALE`.
3. **Resolve the effective node** from the graph the *root pinned*, not the file on
   disk. Then pick the runner profile.
4. **Prove the precondition** — the workspace must be clean at the expected base
   commit. A writing node's continuation is reset to the steered attempt's
   `pre_attempt_commit` first.
5. **Dispatch** — mint idempotently, build the sandbox, cross the fork barrier, exec.
6. **Watch** — monitor liveness and heartbeats until a terminal verdict.
7. **Observe the exit** — write `exit.json`, pin artifacts and outputs, run the verify
   checks, grade ([07-grading.md](07-grading.md)).
8. **`record_exit`** as the final act, then release the lock and die.

Order of store writes during dispatch: `record_precondition`, then `record_envelope`,
then `record_dispatch`.

## The fork barrier

Launching is not just `Popen`. `supervisor/fork_launcher.py` implements a handshake so
"did this child ever start?" always has an answer:

- Child forks, sets itself up, writes **`R`** (ready).
- Parent reads `R`, writes the exec-ledger line, replies **`A`** (ack).
- Child reads `A`, then `execve`s the runner.

Four exit codes carry the failure modes: `120` setup failed, `121` barrier closed,
`122` no receipt, `127` exec failed. The ledger line is written *before* the ack, so a
crash anywhere leaves a durable trace of intent.

## Three launch outcomes

`dispatch()` is idempotent; its results are all about crash windows
(`supervisor/models.py:128-138`):

| Outcome | Meaning |
|---|---|
| `LAUNCHED` | A child crossed the barrier and appended one exec-ledger line. |
| `REATTACHED` | A receipt and ledger line already existed — the previous wrapper died between exec and `record_dispatch`. Repair forward; do **not** exec twice. |
| `ALREADY_DISPATCHED` | The store already records a handle. Another wrapper may be watching; return without adopting. |

`REATTACHED` is adopted deliberately: nobody else is watching that child, so leaving it
would mean no `max_wall` enforcement and no exit record. But adoption cannot make it a
real child — it was reparented to init, so `waitpid` returns `ECHILD` and the exit
*status* is recorded as `EXIT_STATUS_UNOBSERVABLE_REATTACHED`. The wrapper is honest
about what it cannot know.

## The sandbox

`bwrap`, with `--die-with-parent`. Bind order matters:

1. Read-only roots: `repo_root`, `wrapper_root`, `checkout`.
2. Git read-write, writers only. Worktree shape: objects, `refs/heads/wf/<root>`,
   that ref's reflog, the worktree gitdir. In-repo shape: all of `.git`, because
   `index.lock` is created directly in `.git/` and a runner that cannot take it cannot
   commit.
3. Grants from `allowed_paths`, writers only.
4. The activation's `channels/`.
5. The toolchain uv-cache.
6. Vendor state, app-server only.
7. Read-only pins **last** — the `wf` fence, seed roots, and everything that makes git
   run a program: `config`, `config.worktree`, `hooks/`, `info/`, `modules/*/config`,
   `refs/wf`, and the whole `worktrees/` directory (pinned wholesale so a sibling
   created after planning is not writable).

Known gap: `packed-refs` stays writable in the in-repo shape, so a loose-ref pin
protects evidence refs only partially. Suspected defect 10.

## The monitor

Limits come from the node (`max_wall`, `stale_after`). Liveness is proved by **pid +
boot_id + `/proc` start time** together, so a recycled pid cannot masquerade. No
heartbeat for `stale_after` sets a stale flag; twice that is a breach and the child is
killed.

Two watch paths: an `RpcSession` when the runner speaks stdio-RPC (the app-server
transport), and a plain `monitor.watch` otherwise.

## Steer

`foreman steer` lets a human intervene mid-run. The intent is written **durably to
disk before the kill**, which makes the rule unambiguous: a child found dead with a
steer intent on disk died *because of* the steer. The wrapper then returns without
observing the exit, because the steerer owns that closure — otherwise two parties
would race to grade the same death.

## What it does not do

- Does not choose the next node, or read an edge.
- Does not trust the runner's verdict; the host's verification governs.
- Does not clean up the worktree — that is the foreman's terminal cleanup.
