# 04 — Graph and nodes

The schema lives in `schema/models.py`. The shipping graph is
`workflows/feature-delivery.toml`.

## The nine components

1. **GraphMeta** — id, semver version, entry node, description.
2. **Node** — `name`, `kind` (`task` / `gate` / `terminal`), optional `region`, plus
   per-kind fields below.
3. **Edge** — `from`, `on` (one outcome), `to`. That is the whole routing language:
   no conditions, no expressions.
4. **Outcome** — a closed set of 14 (below).
5. **Region** — `name`, `mode`, `entry_node`, `max_entries`, `on_exhausted`.
6. **VerifyCheck** — `cmd`, `timeout`, `cwd`. Relative paths, never shell strings.
7. **InstanceBounds** — `max_total_activations`, coordination limits, retry terminals.
8. **FallbackRoute** — where a node goes when no edge matches.
9. **DecisionPolicy** — `triggers`, `actions`, `decision_task`. The one place the
   graph asks for a judgment call ([09-coordination.md](09-coordination.md)).

Two things the graph cannot express: conditions on edges, and who may approve a gate.

## The three node kinds

**Task** — does work. Parameters below.

**Gate** — waits for a signed payload.
- `gate_type = "human"` is the only value; native gate types are deferred.
- `binds = "immutable" | "mutable"`. Immutable binds the approval to a fixed digest;
  mutable re-hashes the artifact at approval time, so an approval cannot be reused
  after the content changed.
- A gate declares `outcomes` too: `ship` allows `approve`/`abandon`, `triage` allows
  `rebudget`/`abandon`.

**Terminal** — the root's final state. No parameters; the whole declaration is two
lines. Reaching one triggers `_settle_terminal` (`foreman/tick.py:708-731`), which
settles the root first (idempotent, durable), drains attention, then *tries* cleanup.
Cleanup may fail; a settled root still reports terminal, so a later tick retries.

The terminal name is what the caller reads: the contractor lands only when
`terminal_node == "shipped"`. `abandoned` is a fully recorded ending that does not
land. A run that stops any other way has no terminal, and settles nothing — the root
must not close on a guess.

## Task parameters, grouped

Using the real `implement` node:

**Who runs it** — `crew = "profile:implementer"`, `model`, `execution_profile`,
`session_mode` (`"fresh"` or `"resume"`; node > role binding > `fresh`; legacy
`session_reuse` decodes only on pinned app-server bodies).

**What it may touch** — `isolation`, `writes`, `allowed_paths`.

**What it is given** — `instructions` (≤8192 chars), `inputs`,
`artifact_input_mode`, `context_budget_bytes`, `token_budget`.

**How long** — `max_wall = "45m"` (hard limit), `stale_after = "10m"` (no heartbeat
for this long flags stale; twice that is a breach).

**Failure handling** — `max_infra_retries = 2` (infra only, never consumes a round),
`max_steers = 2`, `fallback`.

**How it is judged** — `verify = [{cmd = "scripts/verify-feature.sh", timeout = "10m"}]`,
`outcomes = ["done", "no_diff", "fail_plan", "fail_code"]`.

### isolation versus allowed_paths

The common misreading. **The checkout is mounted read-only**
(`inspector/sandbox.py:611-624`):

```python
ro_roots = (repo_root, wrapper_root, checkout)
grants  = tuple(_grant_path(g, checkout) for g in task.allowed_paths) if task.writes else ()
git_rw, ro_pins = _git_binds(checkout, task.root_id) if task.writes else ((), ())
```

- **`isolation`** decides *which* directory the agent works in — `worktree` (private
  git worktree) or `in-repo`. It grants no write rights.
- **`allowed_paths`** decides *what inside it is writable*, bind-mounted read-write
  over the read-only base.
- **`writes`** is the master switch. False → no grants, no git write mounts: three
  read-only roots plus the channels directory.

| Node | isolation | allowed_paths | Can write |
|---|---|---|---|
| `implement` | worktree | `["src/**", "tests/**"]` | those trees, git objects, its own branch ref |
| `debrief` | worktree | `["docs/workstreams/**"]` | that tree only |
| `review` | worktree | `[]` | nothing in the repo; findings go to `$WF_ARTIFACT_DIR` |

A grant is **disclosure**; containment is the verifier's job (ADR 0001). The grant
makes a path writable; only the verifier proves nothing else was touched.

## Inputs and sources

`inputs` names entries from the graph's `[[source]]` blocks:

| Source | Producer | Meaning |
|---|---|---|
| `task_brief` | `instance` | The bead description, written to a file at root creation |
| `diff_artifact` | `node:implement` | The commit implement produced |
| `review_findings` | `node:review` | What the critic rejected; absent on round 1 |
| `ledger_render` | `engine:ledger_render` | The engine's account of every round so far, pinned as a commit before the consuming activation is minted |
| `verify_failure` | `engine:verify_failure` | Host diagnostics, bound only to the check that failed |

The two `engine:` sources are the loop's memory — produced by the interpreter, not by
any agent, and how round 2 knows what round 1 did and why a check went red.

**`artifact_input_mode`**: `inline` puts evidence content in the envelope;
`references` puts pointers plus an instruction to open each `index_path`. References
mode refuses to launch with the sandbox off (`inspector/launch.py:674-678`) —
pointers are only trustworthy when the mount set is enforced.

## Outcomes: ten routable, four system

**Routable by edges:** `done`, `no_diff`, `accept`, `reject`, `fail_code`,
`fail_plan`, `doubt`, `approve`, `rebudget`, `abandon`.

**System-assigned:** `error_crew`, `error_transport`, `steered`, `superseded`.
Never edge-routed; the wrapper and foreman handle them, which is why an infra retry
does not consume a round.

The distinction between the three success-ish outcomes is **who is speaking**:

| Outcome | Speaker | Meaning |
|---|---|---|
| `done` | The worker, about itself | "I finished." The weakest claim. |
| `accept` | A reviewer, about another's work | "I examined it and it passes." |
| `approve` | A human, via a signed gate | "I authorize this." Authorization, not assessment. |

`accept` triggers an anti-drift cross-check on any node declaring it. `rebudget` is
the only outcome permitted to carry a back-edge across a region boundary.

`doubt` and `fail_plan` both mean "I will not proceed on my own judgment" —
`fail_plan` says the brief is wrong, `doubt` says the worker is unsure. Both try
`queue_boundary` first (`foreman/cases.py:463-472`); with no decision policy they
route by ordinary edge.

## Regions: bounded loops with a declared escape

```toml
[[region]]
name         = "build-review"
mode         = "bounded-cycle"
entry_node   = "implement"
max_entries  = 3
on_exhausted = "triage"
```

Four things it buys:

1. **A loop that provably terminates.** Implement → review → reject → implement is a
   cycle; `max_entries` caps it.
2. **A definition of "round."** Every arrival at `entry_node` opens the next one.
3. **A declared escape.** Hitting the bound routes to `on_exhausted` — a human gate
   that can `rebudget` or `abandon`. The failure mode is designed, not a crash.
4. **A single entry point.** `acyclic` regions cannot loop; for `bounded-cycle`,
   every cross-region arrival must land on `entry_node`, which makes counting honest.

The subtlety: `implement`'s own `fail_code` edge points back at `implement`. That is
an arrival at the entry node, so it opens a new round and consumes one of the three —
the same budget a review rejection uses.

`fail_code` means the agent ran its checks and they are still red. It is honest
failure, not a crash; `error_crew` covers the crash case. `debrief`'s `fail_code`
routes to `triage` instead, because a debrief that wrote outside its directory is a
containment breach that must never reach `ship`.

## Budgets: one enforced, one dead

- **`context_budget_bytes`** is the only enforced budget. It caps the composed
  envelope, defaulting to **262144 bytes** when unset (`foreman/inputs.py:465`).
  `compose_envelope` (`foreman/envelope.py:64-110`) measures the whole framed text,
  drops optional sections in `trim_priority` order until it fits, records each drop in
  an omissions manifest with a sha256, and raises `EnvelopeRefusal` if only mandatory
  sections remain — which becomes the `input_oversize` decision trigger.
- **`token_budget` is ignored.** It only emits `legacy_token_budget_ignored`. No
  feature-delivery node sets `context_budget_bytes`, so all three run on the default
  and their `token_budget` lines do nothing.
- **`context_cap_tokens`** caps the crew's own context, and only for Claude. It is a
  role-binding field in the foreman config (no node field), passed unchanged as
  `--autocompact <n>` on launch and resume. A value outside Claude's accepted
  100000–1000000 range is refused at config load, naming the role. Unset
  passes no flag. A Codex role that sets it is refused at config load; Codex keeps
  its vendor-default window.

Three unrelated units with confusable names. Tracked as bead **cr-e94f**.

## Instance bounds: a ceiling on the run, not on tool calls

```toml
[instance]
max_total_activations = 26   # counts every activation AND gate bead
contractor_retry_terminals = ["shipped", "abandoned"]
```

`max_total_activations` bounds how many times the interpreter may start something; it
has no visibility into what an agent does inside one activation. Hitting it opens a
`HALT_CEILING` halt gate. `coordination_limits` bounds sub-workflows.
`test_force_first_reject` only works when test flags are allowed, which the contractor
never allows.

Three nested budgets: rounds per region (3), activations per root (26), wall time per
node (45m/15m/30m). None reaches inside an agent's own loop.

## Verify checks appear in three places

Same `{cmd, timeout, cwd}` type, three moments:

1. **`node.verify`** — the host gate after a task returns.
2. **`DecisionTask.verify`** — required, minimum one.
3. **`contractor_checks`** — not in the graph; pinned by the contractor at admission and run
   at landing with `PATH=/usr/bin:/bin`.

The scripts are hand-written and checked into the repo under review. The wrapper runs
them with argv[0] as `/proc/self/fd/<n>`, no arguments, and cwd set to a clean
detached checkout of the commit under test.
