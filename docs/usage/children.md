# Independent child sessions

Use the normal CLI with an existing coordination owner and its finite capacity:

```sh
uv run python -m workflow_interpreter.foreman --config <config.toml> children admit <owner> alpha --graph workflows/basic.toml --input task_brief=<alpha-brief.md>
uv run python -m workflow_interpreter.foreman --config <config.toml> children admit <owner> beta --graph workflows/basic.toml --input task_brief=<beta-brief.md>
uv run python -m workflow_interpreter.foreman --config <config.toml> children drive <owner> --max-concurrent 2 --max-wall 600
uv run python -m workflow_interpreter.foreman --config <config.toml> children status <owner>
uv run python -m workflow_interpreter.foreman --config <config.toml> children collect <owner> alpha 0
```

`admit` resolves the graph, role/model configuration, named inputs, verifier pins and current base through the normal loader. Its response includes the admission digest and member receipt. The owner must already have a coordination ledger; a root ID alone does not create a budget. `start --admission FILE` remains the lower-level form for a complete pinned admission. `cancel` and `recover` address a slot and exact generation.

Children are independent graphs. The orchestrator chooses them and selects which collected receipts to integrate. Collection returns immutable evidence; it does not land changes or automatically start another graph.

`drive OWNER --max-concurrent N --max-wall SECONDS` holds the canonical owner
session lock. The concurrency cap bounds that drive session, including already
active child decision tasks. It is not a persistent owner quota. `recover OWNER
SLOT GENERATION` performs an ordinary Foreman tick and may launch work independently
of a drive session; serialize recovery with drive when maintaining a session cap.
Recovery retries transient runtime attention after repair, consumes signed gate
resolutions, and retains explicit human decision attention and cancellation intent.

Cancellation covers both the child and its decision tasks. A valid persisted
process handle or launch receipt permits termination and proof of death. A ledger
without either identity cannot establish whether a process started before its
publisher died. That case remains `cancel_pending`: preserve the ledger, wrapper
files and receipts for reconciliation. Repeating recovery can use a subsequently
published receipt; it cannot safely infer a PID or declare an unknown process dead.
Late completion evidence remains available after cancellation.

Owner, member, launch and driver locks live under the canonical Beads workspace's
`.beads/coordination/` directory. Standard Beads metadata ignores `*.lock`
recursively, keeping consuming repositories clean. Configure every driver for an owner with the same canonical Beads workspace;
Beads worktree `redirect` files are not automatically resolved for lock identity.
Wrapper homes do not change
lock identity; each child retains its authoritative wrapper location. A mismatched
child reports attention while healthy siblings can progress.

Earlier unreleased builds used `.wf-coordination/`. Existing legacy lock files
cause explicit refusal, even if currently unlocked. Stop every old driver and
wrapper before deliberately archiving that legacy directory offline. The runtime
never deletes old lock files or silently creates a competing namespace.


## Explicit replacement

For a trusted graph or model change, supply a request file containing `request_key`, `reason`, `graph`, and an `inputs` mapping from declared input names to files. Select the desired role/model settings through the command's normal configuration:

```sh
uv run python -m workflow_interpreter.foreman --config <successor-config.toml> children replace <owner> --slot <slot> --generation <current-generation> --request <replacement.json>
```

Replacement reserves a complete successor against the original owner's remaining capacity and retains the predecessor's evidence. It preserves existing input, review, verification, write-scope and approval obligations. An open human gate, unresolved process, cancellation, consumed integration source or pending landing can prevent replacement; it is not a way to bypass those states. Ordinary model-requested replacement retains its admitted graph/model pins. Changed pins require this explicit trusted operation.

Use a stable request key and retain the original request for recovery. An unrelated pending decision elsewhere under the same owner conservatively blocks replacement; let that decision settle first. Follow the returned current slot/generation; a superseded predecessor cannot advance the bridge. Integration retry and pending-landing recovery have separate meanings described in [phase bridge usage](phase-bridge.md).
