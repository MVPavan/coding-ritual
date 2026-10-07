# bd capabilities — bd 1.3.0

What `bd` can do and how it actually behaves, grouped by capability, with
every command and subcommand and what we can use it for. This is the single
source of truth for bd capabilities in this repository; the companion
[full CLI reference](cli-1.3.0.md) holds usage, examples and every flag.

Sources and labels:

- Command lists come from the 1.3.0 `--help` text (2026-09-30).
- **(tested)** marks behavior observed on bd 1.3.0 in a throwaway database
  (2026-10-01 to 2026-10-06). **(source)** marks behavior read in the v1.3.0
  source. **(reported)** marks an upstream issue or doc claim we did not
  reproduce. Unlabelled behavior comes from the help text.
- The official docs at beads.gascity.com lag 1.3.0 and contradict its help
  text in many places; where they disagree with a tested or source claim
  here, this document wins. Nothing here was re-checked on v1.3.1.
- *Our use* notes are recommendations, not bd behavior. The policy agents
  follow is the `beads` skill (`references/usage.md`).

## The model in one page

- **Bead (issue).** The unit of work. Its ID is a hash with the project
  prefix (`vip-8fw`) that grows with the database: 4 characters up to 500
  beads, 5 up to 1,500, then 6 (reported). `issue_id_mode counter` switches to `vip-1`,
  `vip-2`. A child gets a dotted ID (`vip-8fw.1`) only when created with
  `bd create --parent`; children created through `--graph` or attached later
  keep plain IDs (tested).
- **Fields**, grouped by job:
  - text sections, one rewritable value each: title, description, design,
    acceptance criteria, notes, close reason;
  - comments: a separate append-only thread with author and time;
  - classifiers: type, priority 0–4, status, assignee, owner, created_by;
  - time: due, defer_until, estimate in minutes, started and closed times;
  - tags: labels, and `dimension:value` state labels;
  - links out: external ref (the join key for tracker sync) and spec ID;
  - metadata: arbitrary JSON; keys starting `bd:` or `_` are reserved.
  `--context` and `--skills` are not fields: they append `## Context` and
  `## Required Skills` sections to the description (source).
- **Types.** `task`, `bug`, `feature`, `chore`, `epic`, `decision` (ADR),
  `spike`, `story`, `milestone`, plus custom types (`types.custom`). Most are
  labels for filtering plus suggested description sections checked by
  `bd lint` and `create --validate`. Only these have mechanics (source):
  `epic` (`bd epic status`/`close-eligible`, epic titles in `ready`); the
  internal `gate` (only `bd gate` acts on it), `molecule` (its root closes
  itself when the last step closes) and `message`/`agent`/`role` (stored in
  the local, unsynced wisps table, set by `types.infra`); `event`, written by
  `set-state`.
- **Statuses and categories.** `open` (active); `in_progress`, `blocked` and
  `hooked` (wip); `deferred` and `pinned` (frozen); `closed` (done). Only
  active beads can be ready. Custom statuses (`status.custom`) take a
  category, which decides how bd treats them. A pinned bead refuses close and
  edits without `--force` (tested).
- **Hierarchy.** A child is a bead with a `parent-child` edge to its parent;
  any bead can have children, of any depth (the documented 3-level limit is
  not enforced: `CheckHierarchyDepth` has no caller, source; 5 levels tested).
  A blocked parent blocks every descendant; an open, in-progress, deferred
  or closed parent does not affect them. A bead with open children cannot be
  closed without `--force`, at any level, and `--force` closes only that
  bead. A closed parent accepts new children. Epics never close themselves
  (tested).
- **Dependencies.** Typed edges; `bd dep add X Y` means "X needs Y" (Y
  blocks X). Only four types affect readiness: `blocks` (the default),
  `parent-child` (inherited from a blocked parent), `conditional-blocks` (B
  runs only if A fails) and `waits-for` (B waits for A's dynamic children).
  The last two are created by formulas and molecules, not by `dep add`. These
  leave the dependent ready (tested): `related`, `relates-to`, `tracks`,
  `discovered-from`, `caused-by`, `validates`, `supersedes`, `until`.
  `external:<project>:<capability>` is meant to block across projects but
  never does in 1.3.0 (tested; section 8). Cycles are refused at write time.
- **Ready front.** Open beads with no open blocker of a gating type, not
  deferred into the future, not wisps. In-progress, stored-`blocked`,
  deferred, hooked and pinned beads are excluded, and so are gate beads and
  molecule roots (tested). Open epics do appear.
- **Two meanings of "blocked".** Stored status `blocked` is set by hand and
  shown by `list --status blocked` and `count`. Dependency-blocked is
  computed and shown by `bd blocked` and the `bd status` summary. A bead with
  status `blocked` and no dependency appears in neither `ready` nor
  `bd blocked` (tested).
- **Claims and leases.** Claiming sets the assignee, `in_progress`, the start
  time and a 5-minute lease atomically. Another actor's claim, `assign`,
  `unclaim` or `close` is refused while the claim holds. An expired lease
  changes nothing by itself: only `bd reclaim` returns the bead to the ready
  front (tested). The lease length is fixed in 1.3.0 (source).
- **Actor.** Every write is attributed to `--actor`, else `$BEADS_ACTOR`,
  git `user.name`, `$USER`. Claims belong to the actor, so mixing actors in
  one session blocks your own closes (tested).
- **Storage.** A Dolt database (embedded by default, single writer) with full
  history, branches and merges. Every write is a Dolt commit by default. Sync
  is `bd dolt push/pull` to `refs/dolt/data` on the git remote; a plain
  `git push` or `git clone` carries no beads. `.beads/issues.jsonl` is only
  an export. Wisps are ephemeral beads kept locally and excluded from sync
  and export.
- **Templates.** Formulas (TOML/JSON) compile into protos (templates), then
  are poured into persistent molecules or spawned as ephemeral wisps.
- **Agent memory.** Persistent memories (`bd remember`) that `bd prime`
  injects into every agent session. The separate key-value store (`bd kv`)
  is not injected (tested).
- **Machine interfaces.** `--json` on every command, a JSON Schema
  (`bd schema`), an HTTP API (`bd serve`), raw SQL (`bd sql`) and an ordered
  events journal (`bd events`). `bd serve` and `bd sql` need server mode.

## Fields, types, labels and gates in detail

**Text and link fields** (schema from `bd schema`, flags from `--help`):

| Field | Input | From a file | Writes | Author and time per entry |
|---|---|---|---|---|
| description | `-d` | `--body-file`, `--stdin` | replaces | no |
| design | `--design` | `--design-file` (copies the text; not a link) | replaces | no |
| acceptance_criteria | `--acceptance` | none | replaces | no |
| notes | `bd note`, `--append-notes` | `bd note --file`, `--stdin` | appends (`--notes` replaces) | no |
| comments | `bd comment`, `comments add` | `--file`, `--stdin` | append-only (no edit or delete command) | yes (`author`, `created_at`) |
| close_reason | `close --reason` | `--reason-file` | set at close; `reopen` clears it (tested) | no |
| spec_id | `--spec-id` | — | replaces; shown as "Spec:", filtered by `list --spec <prefix>`, nothing else reads it (source) | no |
| external_ref, source_system | `--external-ref` | — | the tracker-sync join key | no |
| metadata | `--metadata` JSON, `--set-metadata k=v` | `--metadata @file.json` | merge or replace; `bd:` and `_` keys reserved | no |
| closed_by_session | `--session`, `CLAUDE_SESSION_ID` | — | set at close | — |

There are no attachments. A file reaches a bead only as a text copy (the file
flags above) or as a path or URL in a text or link field. Records kept beside
beads:

- **provenance:** kinds `cut`, `claim`, `suspend`, `resume`, `handoff`,
  `commit`, `land`, `used`; ref kinds `git-sha`, `pr`, `branch`, `work-id`,
  `transcript`; idempotent;
- **audit:** `llm_call`, `tool_call`, `label` entries in
  `.beads/interactions.jsonl`;
- **event beads:** `event_kind`, `actor`, `target`, `payload`; created
  closed (checked: 101 of 101 in the hub);
- **gate beads:** `await_type`, `await_id`, `timeout`, `waiters`.

**Types.** `bd lint` and `create --validate` expect these description
headings (source, `types.go`):

| Type | Expected headings |
|---|---|
| bug | Steps to Reproduce, Acceptance Criteria |
| task, feature, story | Acceptance Criteria |
| epic | Success Criteria (Acceptance Criteria also accepted) |
| decision | Decision, Rationale, Alternatives Considered |
| spike | Goal, Findings |
| chore, milestone, custom types | none |

A non-empty acceptance field satisfies the Acceptance Criteria (or Success
Criteria) heading (source, `LintIssue`). `lint.sections.<type>` adds headings
but never removes built-in ones. Custom types (`types.custom`) are accepted
by `-t`, and an open bead of a custom type appears in `bd ready` (tested
2026-10-06). Built-in types cannot be removed.

**Statuses.** `deferred` applies to any type; `create -s deferred` creates a
bead already deferred (tested). A `pinned` parent does not block its
children (tested 2026-10-06).

**Labels.** Free-form, case-sensitive strings with no registry. The only label
bd's own code acts on is `human`, used by `bd human list`, `respond` and
`dismiss` (source, `human.go`). `backlog` has no meaning in bd; it appears
only in the Linear and Notion state mappings (source). Children created with
`--parent` copy all of the parent's labels (tested). `set-state` writes
exclusive `dimension:value` labels.

**Gates.** Types and how each resolves:

| Type | `bd gate check` resolves it when | Escalates when |
|---|---|---|
| `timer` | now is later than created + timeout | — |
| `gh:run` | the run completed with success | it failed or was cancelled |
| `gh:pr` | the PR merged | the PR closed unmerged |
| `bead` | the target bead closed (tested) | — |
| `human` | never: `bd gate resolve` only | — |
| any other name | never: accepted without validation, ignored by `check` (tested 2026-10-06) | — |

`bd gate resolve <id> --reason` records the reason as the gate's close
reason. The blocked bead returns to `ready` only when its last open gate
closes (tested). A `human` gate does not appear in `bd human list`.

## 1. Capture and edit work

Create beads in any granularity, from one-line captures to whole dependency
graphs, and change any field later.

- `bd create` — Create a bead with any field set. It can also wire
  dependencies, parent, labels, due/defer dates, estimates, spec links and
  ephemeral storage in one call, and validate required description sections.
  A child copies its parent's labels unless `--no-inherit-labels`; the copy
  chains to grandchildren (tested). Two batch forms (tested):
  - `-f plan.md` — One bead per `## Title`, with optional `### Priority`,
    `Type`, `Description`, `Design`, `Acceptance Criteria`, `Assignee`,
    `Labels` and `Dependencies` sections. It refuses `--parent`, and its
    dependencies can only name beads that already exist.
  - `--graph plan.json` — Nodes with local `key`s and almost every field,
    `parent` by key, and `edges` (`from_key` needs `to_key`). Builds an epic,
    its children and their dependencies in one call; children get plain IDs.
- `bd create-form` — Interactive terminal form for creating a bead (humans
  only).
- `bd q` — Quick capture that prints only the new ID, for scripts and agents
  that need to chain commands.
- `bd todo` — Lightweight TODOs as ordinary task beads.
  - `bd todo add` — Add a TODO (a priority-2 task).
  - `bd todo done` — Close TODOs.
  - `bd todo list` — List open TODOs.
- `bd update` — Change any field on one or more beads: status, priority,
  assignee, labels, metadata, parent, dates and text sections. `--claim` takes
  work atomically. The `--if-assignee` and `--if-status` guards make it a
  compare-and-swap that exits 13 with nothing written if another actor got
  there first (tested). `--notes` replaces all notes; `--append-notes` (=
  `bd note`) appends. `--parent P` reparents and keeps the old ID; `--parent ""`
  removes the edge but the dotted ID stays, and `bd children` still lists the
  bead under its old parent by ID prefix (tested). With no ID it targets the
  last-touched bead only in an interactive terminal.
- `bd edit` — Edit a text field (description, design, notes, acceptance) in
  `$EDITOR` (humans only; agents must not use it).
- `bd note` — Append to a bead's notes, for progress logs without
  overwriting.
- `bd comment` — Add a comment (shorthand for `bd comments add`).
- `bd comments` — View a bead's comment thread.
  - `bd comments add` — Add a comment, optionally as another author or from a
    file.
  - `bd comments list` — Not a working command: it only points you to
    `bd comments <id>`.
- `bd priority` — Set priority 0 (critical) to 4 (backlog).
- `bd assign` — Set the assignee. It refuses to overwrite another actor's
  live claim without `--force` (tested).
- `bd tag` — Add one label (shorthand).
- `bd label` — Manage labels, which are the main axis for scoping queries
  and claims.
  - `bd label add` — Add labels to beads.
  - `bd label remove` — Remove labels from beads.
  - `bd label list` — Labels on one bead.
  - `bd label list-all` — Every label in the database; useful for building
    filters.
  - `bd label propagate` — Copy a parent's label to its direct children only,
    for example to tag an epic's subtasks with a branch. Labels added to a
    parent after its children exist do not flow down otherwise (tested).
- `bd set-state` — Set an operational state dimension (`health:failing`,
  `mode:degraded`) atomically: it records an event bead as the audit trail
  and swaps the `dimension:value` label.
- `bd state` — Read the current value of one state dimension.
  - `bd state list` — All state dimensions on a bead.
- `bd rename` — Change a bead's ID and rewrite every reference, dependency,
  label, comment and event.
- `bd delete` — Permanently delete beads: remove every link to them and turn
  mentions in linked beads into `[deleted:<id>]`. It refuses if dependents
  exist, unless `--cascade` (delete them too) or `--force` (leave them). The
  old rows stay in Dolt history until history is compacted.
- `bd promote` — Turn an ephemeral wisp into a permanent bead, keeping its ID
  and links.

*Our use:* `bd create --graph` for whole plans; `-f` for flat lists only.

## 2. Lifecycle and status

Move beads through their life and record why.

- `bd close` — Close beads with reasons (one for all, or one per ID by
  position). It can then show newly unblocked work (`--suggest-next`), claim
  the next ready bead (`--claim-next`), or advance to the next molecule step
  (`--continue`), and can record the Claude Code session ID. Refusals
  (tested): open children or a pinned bead (each needs `--force`), and a
  claim held by another actor. Being dependency-blocked does
  not stop a close. With no ID it closes the last-touched bead only in an
  interactive terminal; in scripts it is an error.
- `bd reopen` — Reopen closed beads, clear the close time and reason, and
  emit a Reopened event (tested).
- `bd defer` — Put beads on ice; they leave `bd ready` but stay in `bd list`.
  `--reason` is appended to the notes (tested).
  - With `--until` (`+2d`, `tomorrow`, `next monday`, a date): a snooze. No
    timer runs; the next ready-front read sets it back to `open` once the
    date has passed, so direct reads such as `list --status deferred` or an
    export can still show `deferred` until something runs `bd ready` (tested).
  - Without a date: the icebox, until `bd undefer`.
- `bd undefer` — Bring deferred beads back to open.
- `bd duplicate` — Close a bead as a duplicate of a canonical one: an empty
  close reason and a `duplicates` edge (tested).
- `bd supersede` — Close a bead as replaced by a newer one: an empty close
  reason and a `supersedes` edge (tested); suited to evolving designs.
- `bd statuses` — List valid statuses and their categories, including custom
  ones.
- `bd types` — List valid bead types, including custom ones, and the
  sections each type requires.

## 3. Find the next work

Decide what to do now, and notice work that has stalled or slipped. Only
`ready`, `list --ready` and `blocked` understand dependencies; every other
read filters on stored status.

- `bd ready` — The ready front (see the model). Default limit 100 (`--limit 0`
  for all). Filters: labels, type (`--exclude-type epic` hides epics),
  priority, molecule, metadata, assignee; `--parent P` covers every
  descendant, recursively (tested). `--claim` takes the first match
  atomically. `--explain` shows the dependency reasoning but ignores
  `--parent` (tested). `--include-deferred` and `--include-ephemeral` widen
  it. Reading the ready front is also what wakes expired snoozes.
- `bd blocked` — Beads waiting on open blockers, and the blockers. It does not
  list beads whose stored status is `blocked` (tested).
- `bd stale` — Beads not updated in 30 days by default (`--days`), such as
  abandoned claims or forgotten work.
- `bd orphans` — Beads referenced in commit messages but still open: work
  that shipped without being closed.
- `bd human` — A short menu of the ~15 essential commands for humans, plus
  the queue of beads labelled `human` that need a person.
  - `bd human list` — Beads labelled `human`, of any type; closed, pinned and
    other done or frozen beads hidden by default.
  - `bd human respond` — Answer one: add the response as a comment and close
    it with reason "Responded".
  - `bd human dismiss` — Close one with reason "Dismissed".
  - `bd human stats` — Counts of pending, responded and dismissed beads.

*Our use:* `bd human list` is the natural source for the dashboard's "needs
you" panel. The dashboard needs both blocked views, since stored-`blocked`
beads without dependencies are otherwise invisible.

## 4. Search, view and report

Look at any slice of the data, now or in the past.

- `bd list` — The general filterable listing: every field, date ranges, text
  contains, labels (any, all, pattern, regex), metadata, parent, overdue,
  deferred and pinned. It can render a tree, a Graphviz or digraph graph, or
  a Go template, and can watch and refresh live. Defaults: closed beads
  excluded (`--all`), limit 50 with the rest dropped silently. `--parent P`
  lists direct children only, unless combined with `--ready`. Repeating `-s`
  overwrites; use `-s open,blocked`. `--brief` omits the long text fields and
  `--max-rows` is a hard cap (exit 2) for agents.
- `bd show` — Full detail of beads. It can also show the bead as of any
  commit or branch (`--as-of`), its children, beads that reference it
  (`--refs`), its dependents, the currently active bead, or a message thread,
  and can watch for changes. It rewrites `.beads/last-touched` even under
  `--readonly` (tested 2026-09-30).
- `bd children` — Direct children of a parent, closed included (`list
  --parent --status all`); it also matches by dotted ID prefix (tested).
- `bd search` — Text search over titles and IDs (descriptions only with
  `--desc-contains`), closed beads included by default. Matches beyond
  `--limit` are dropped regardless of status, so narrow with `--status open`
  when hunting live work.
- `bd query` — A small query language with comparisons, AND/OR/NOT,
  parentheses, fields and relative dates, for filters flags cannot express.
  Closed beads excluded unless `-a`; limit 50. Relative dates are points in
  the past, so `updated>7d` means "updated within the last 7 days" and
  `updated<7d` "not updated for 7 days" (reported); `--parse-only` prints how
  a query was read.
- `bd count` — Counts matching filters, grouped by status, type, priority,
  assignee or label.
- `bd status` — A `git status`-like overview: counts by state, ready work,
  pinned count, lead time and the last 24 hours of activity from git history.
  `bd stats` is the same command.
- `bd epic` — Epic reporting.
  - `bd epic status` — Completion of each epic, counting direct children, and
    which epics are eligible to close.
- `bd history` — Every committed version of a bead, or its audit events.
- `bd diff` — What changed in the issue data between two Dolt commits or
  branches (`HEAD~5 HEAD`), not git commits.

*Our use:* `count --by-*`, `status`, `epic status` and `history` cover most
of the dashboard's overview page.

## 5. Dependencies and structure

Model how work relates, and check that the graph makes sense.

- `bd dep` — Manage dependency edges; `bd dep Y --blocks X` is shorthand for
  `bd dep add X Y`. Write "X needs Y", not "Y comes before X": temporal
  wording is the common way to get an edge backwards.
  - `bd dep add` — Add a typed edge (`--blocked-by`/`--depends-on` are
    aliases). `--type` accepts `blocks`, `tracks`, `related`, `parent-child`,
    `discovered-from`, `until`, `caused-by`, `validates`, `relates-to`,
    `supersedes`; see the model for which of them gate readiness. It accepts
    `external:<project>:<capability>` targets (which do not block in 1.3.0)
    and bulk JSONL wiring with `--file` (`{"from":..,"to":..}` per line).
  - `bd dep remove` — Remove an edge.
  - `bd dep list` — Dependencies or dependents (`--direction=up`) of beads,
    filterable by type.
  - `bd dep tree` — Tree of what blocks a bead, what it blocks, or both;
    Mermaid output available.
  - `bd dep relate` — A bidirectional "see also" link that neither blocks nor
    nests.
  - `bd dep unrelate` — Remove that link.
  - `bd dep cycles` — Find dependency cycles (new cycles are already refused
    at write time, tested).
- `bd link` — Shorthand for `bd dep add`: `bd link X Y` stores the same edge
  (tested).
- `bd graph` — Visualise the graph: a terminal DAG, boxes, compact tree,
  Graphviz DOT, self-contained interactive HTML (D3), or an LLM-friendly
  view of open beads only. Layers show execution order: layer 0 can start
  now, and beads in one layer can run in parallel.
  - `bd graph check` — Integrity check for cycles and orphans; exit code 1 if
    problems are found.
- `bd swarm` — Treat an existing epic's DAG as parallel work for several
  agents; it computes waves and does not template.
  - `bd swarm create` — Create a swarm molecule that coordinates an epic.
  - `bd swarm list` — Swarms with progress and active workers.
  - `bd swarm status` — Completed, active, ready and blocked children,
    computed live from the beads.
  - `bd swarm validate` — Check that an epic is ready to swarm (dependency
    direction, orphans, cycles, disconnected parts) and report the waves of
    parallel work and maximum parallelism.

## 6. Multi-agent coordination

Let several agents share one database without stepping on each other.

- `bd update --claim` / `bd ready --claim` — Atomic claiming: assignee,
  `in_progress`, start time and a lease in one step; a second actor's claim
  exits 1 (tested). Claim pools (`claim.pools`, read from the database only)
  let a dispatcher pre-assign work to a pool.
- `bd unclaim` — Release a claim. Only the holder can do it without
  `--force` (tested), and it has a compare-and-swap form for supervisors.
- `bd heartbeat` (alias `hb`) — Keep your claim's lease alive. The lease is 5
  minutes and fixed in 1.3.0: `DefaultLeaseTTL`, with no CLI or config
  override (source); `bd config set claim.lease-ttl` is accepted and ignored
  (tested). Heartbeat more often than every 5 minutes.
- `bd reclaim` — The reaper: return in-progress beads whose lease expired at
  least `--older-than` ago to the ready front, clearing the assignee. Nothing
  else does this: an expired claim stays in-progress, out of `ready` and
  unclaimable until reclaim runs (tested). It reverts every stale claim it
  finds; run it on a timer with a window of about twice the lease. Leases are
  per replica and never sync; it is replica-aware for federated setups.
- `bd gate` — Asynchronous wait conditions: a gate is a bead that blocks
  another until something happens. Gate beads never appear in `ready`
  (tested).
  - `bd gate create` — Block a bead on a new gate: `human` (default), `timer`
    (`--timeout 2h`, Go durations, so `1d` is invalid), `gh:run` or `gh:pr`
    (`--await-id`). Cross-rig `<rig>:<bead>` gates can no longer be evaluated.
  - `bd gate list` — Open gates, or the gates on one bead.
  - `bd gate show` — A gate and its waiters.
  - `bd gate check` — Evaluate timer and GitHub gates and close the resolved
    ones (it queries GitHub through `gh`). It is a command, not a service:
    schedule it (cron, CI or a hook). It never resolves `human` gates
    (tested).
  - `bd gate resolve` — Close a gate by hand; the only way to clear a `human`
    gate (tested).
  - `bd gate discover` — Find the GitHub run ID for CI gates that lack one.
  - `bd gate add-waiter` — Register an agent to be woken when a gate closes.
- `bd merge-slot` — A one-holder lock, stored in a bead, that serialises
  merge-conflict resolution between agents.
  - `bd merge-slot create` — Create the project's slot.
  - `bd merge-slot acquire` — Take it, or join the wait queue (`--wait`).
  - `bd merge-slot check` — Available, or who holds it.
  - `bd merge-slot release` — Give it back. It does not hand the slot to the
    next waiter; the waiter must acquire again.
- `bd mail` — Delegate to an external mail provider configured with
  `mail.delegate` (for example an orchestrator's mail); bd has none of its
  own. Agents talk through comments and `human` beads instead.

*Our use:* give every agent its own `BEADS_ACTOR`, have workers
`ready --claim` and heartbeat, and run `bd reclaim` on a timer; otherwise a
crashed agent's bead looks in-progress forever.

## 7. Templates and repeatable workflows

Capture a workflow once and stamp out real beads from it.

- `bd formula` — Workflow templates in TOML or JSON
  (`.beads/formulas/<name>.formula.toml`), with variables, steps, `needs`,
  gates, composition and inheritance. Traps (reported, consistent with help):
  unknown keys are dropped silently; an unknown step `type` becomes `task`;
  human sign-off is `[steps.gate] type = "human"`, not a step type. Check
  what bd understood with `bd formula show <name> --json`.
  - `bd formula list` — Formulas across the project, repo, user and shared
    search paths.
  - `bd formula show` — A formula's variables, steps, dependencies and
    composition rules.
  - `bd formula schema` — The formula file schema (alias `primitives`).
  - `bd formula convert` — Convert JSON formulas to TOML.
- `bd cook` — Compile a formula into a proto, with placeholders kept or
  variables substituted. It prints JSON and writes nothing unless `--persist`
  (tested); `mol pour` and `mol wisp` cook inline, so cooking is usually
  unnecessary.
- `bd mol` — Molecules: real beads spawned from templates.
  - `bd mol show` — A proto's or molecule's structure, highlighting steps
    that can run in parallel.
  - `bd mol pour` — Instantiate a template as persistent, synced work. Tested
    result: a root of type `molecule`, one child bead per step and a gate bead
    per `[steps.gate]`, with `<prefix>-mol-` IDs; `needs` become `blocks`
    edges. Steps without `needs` run in parallel.
  - `bd mol wisp` — Instantiate a template as ephemeral local work
    (`<prefix>-wisp-` IDs, absent from `list` and `export`, tested), or manage
    wisps.
    - `bd mol wisp create` — Spawn a wisp from a proto.
    - `bd mol wisp list` — Wisps here, flagging old ones.
    - `bd mol wisp gc` — Delete abandoned wisps; live, blocked and frozen
      steps are never reclaimed.
  - `bd mol bond` — Combine protos and molecules sequentially, in parallel
    or conditionally, with readable child IDs.
  - `bd mol squash` — Condense a molecule's ephemeral steps into one
    permanent digest bead (an agent can supply the summary). Tested: the wisp
    steps are deleted, and one closed digest bead plus the closed root remain
    as persistent beads.
  - `bd mol burn` — Delete a molecule without a trace (irreversible).
  - `bd mol distill` — Reverse direction: extract a reusable formula from an
    epic that grew organically.
  - `bd mol current` — Where you are in a workflow: done, current, ready and
    pending steps, and the next bead to claim.
  - `bd mol progress` — Completed/total, rate and ETA, even for very large
    molecules.
  - `bd mol ready` — Molecules whose gate has closed and can resume.
  - `bd mol seed` — Check that a formula can be found and cooked.
  - `bd mol stale` — Molecules whose children are all closed but whose root
    is still open.

*Our use:* pour for work that matters later (releases, upgrades); wisps for
high-volume routine runs, squashing only runs that found something and
burning clean ones, since each squash still leaves two beads in the hub.

## 8. Cross-project work

Link work between projects and move beads between them.

- `bd ship` — Publish a capability: it refuses until the bead labelled
  `export:<capability>` is closed, then adds `provides:<capability>`
  (tested). The consuming side does not enforce it in 1.3.0: an
  `external:<project>:<capability>` dependency leaves the bead ready whether
  or not the capability shipped, and `ready --explain` calls it a resolved
  blocker (tested with `external_projects` in `config.yaml` and in
  `config.local.yaml`); `ResolveExternalProjectPath` has no caller (source).
- `bd repo` — Hydrate beads from several projects into one database for a
  unified view.
  - `bd repo add` — Add a project to hydrate from (writes the tracked
    `config.yaml`).
  - `bd repo list` — Configured projects.
  - `bd repo remove` — Remove one and its hydrated beads.
  - `bd repo sync` — Import each project's `issues.jsonl` now.
- Routing — Not a command: `routing.mode`, `routing.default` and
  `beads.role` decide which repo `bd create` writes to; `--repo` always wins.
  Off by default. `bd init --contributor` sets up a private planning repo so
  planning beads stay out of upstream PRs. The `beads.role` warning on stderr
  means the role is unset.
- `bd migrate issues` — Move beads to another repository, keeping their
  dependencies.
- `bd migrate-personal` — Move your personal planning beads out of a shared
  project into your own planning repo.
- `bd federation` — Peer-to-peer sync between separate Beads databases, with
  privacy tiers T1 to T4; wisps never federate.
  - `bd federation add-peer` — Add a peer (DoltHub, a SQL server or a file
    path) with stored credentials.
  - `bd federation list-peers` — Configured peers.
  - `bd federation status` — Commits ahead/behind each peer and conflicts.
  - `bd federation sync` — Pull from and push to peers with a conflict
    strategy.

*Our use:* `bd repo` only reads the other projects, but it lists their paths
in the hub's tracked `config.yaml` (it reads no other file for this; checked
in the 1.3.0 source), and `repo sync` pushes through the hub's Dolt remote.
In a public hub that publishes the project list and every project's beads.
It also reads the exported JSONL, which is often stale (section 12), rather
than the live database. Cross-project gating cannot rely on `external:`
dependencies; the hub (`docs/hub.md`) sees every project and is the place to
evaluate it.

## 9. Provenance, audit and change feeds

Know who changed what, why, and tie beads to the artifacts they produced.

- `bd provenance` — An append-only log binding beads to external artifacts:
  commits, PRs, branches, transcripts.
  - `bd provenance record` — Record a binding; running it twice is harmless.
  - `bd provenance log` — Bindings for one bead.
  - `bd provenance by-ref` — Beads bound to one artifact (for example which
    beads a commit touched).
- `bd audit` — An optional log of agent interactions (prompts, responses,
  tool calls) in `.beads/interactions.jsonl`, for "why did the agent do
  that?" and for training datasets. Off by default in 1.3.0.
  - `bd audit record` — Append an interaction entry.
  - `bd audit label` — Label an earlier entry (for example good or bad).
- `bd events` — An ordered, gapless journal of every mutation, for consumers
  that follow changes incrementally. Off until `events-journal` is enabled,
  and specific to this clone and branch. Reported limits: it records only
  writes made where it is enabled, so every writer must enable it, and an
  empty journal looks identical to a caught-up one; pulls, `bd sql` writes,
  `admin compact` and `restore --apply` are not journaled; retention keeps 7
  days or 100k rows, and a consumer that falls behind gets
  `events_journal_truncated`.
  - `bd events tail` — Records after a sequence number, or follow live.
  - `bd events export` — The whole journal from the start.
  - `bd events prune` — Cut old records earlier than retention would.
- `bd metrics` — bd's anonymous usage metrics: command names, bd version, OS
  and a hashed machine ID. On by default for a new HOME (tested), so every
  new machine, container or sandbox needs `bd metrics off`.
  - `bd metrics on` / `bd metrics off` — Opt in or out.
  - `bd metrics example` — Show exactly what is sent.

*Our use:* `bd events tail --follow` could feed a live dashboard only if every
writer enables the journal; until then the hub's periodic export is the
reliable feed.

## 10. Agent integration and memory

Keep agents oriented across sessions and compactions.

- `bd prime` — Beads workflow context formatted for agents (about 900 words),
  plus persistent memories. It is what session-start hooks inject
  (`--hook-json`), replaceable through `.beads/PRIME.md` (memories still
  appended), and capped with `--max-memories`/`--max-memory-chars` because
  hosts truncate long hook output silently. `agent.profile`
  (`conservative` default, `minimal`, `team-maintainer`) sets how much git
  authority the text grants.
- `bd onboard` — Prints a short snippet for `AGENTS.md` that points agents at
  `bd prime`; it writes nothing. Its claim that `bd hooks install` injects
  `bd prime` at session start is wrong: that installs git hooks (tested).
- `bd setup` — Install Beads instructions for an AI tool (Claude, Codex,
  Cursor, Copilot, Gemini, Aider and others), per project or globally.
  Tested output: Claude gets a SessionStart hook running
  `bd prime --hook-json` and a managed CLAUDE.md block; Codex gets a
  `.agents/skills/beads` skill, an AGENTS.md block and four `bd codex-hook`
  events (SessionStart, PreCompact, PostCompact, UserPromptSubmit). The plugin
  or MCP server route costs 10–50k tokens against about 1–2k for CLI plus
  hooks (reported).
- `bd quickstart` — A guide to common workflows.
- `bd remember` — Store a memory that is injected into every future session.
  `bd remember <existing-key>` alone reads it instead of storing (tested).
- `bd recall` — Read one memory in full.
- `bd memories` — List or search memories.
- `bd forget` — Delete a memory.
- `bd kv` — A general key-value store for flags and settings that persist
  across sessions; not injected by `prime` (tested).
  - `bd kv set` / `bd kv get` / `bd kv list` / `bd kv clear` — Write, read,
    list and delete keys.
- `bd hooks` — Git hooks that run Beads logic on commit, merge, push and
  checkout, and add agent identity trailers to commit messages. The
  pre-commit JSONL export runs only when `export.auto` is on (source).
  - `bd hooks install` — Install into `.git/hooks`, `.beads/hooks` or a shared
    directory, preserving other hook content.
  - `bd hooks list` — Installed, outdated or missing.
  - `bd hooks run` — The hook logic that the thin hook scripts call.
  - `bd hooks uninstall` — Remove them.
- `bd rules` — Maintain Claude rule files.
  - `bd rules audit` — Find contradictions and merge opportunities.
  - `bd rules compact` — Merge related rules into composites.

*Our use:* this harness has its own prime hooks (`.claude/hooks/bd-prime.sh`,
`.codex/hooks/bd-prime.sh`) and keeps persistent knowledge in files, not
`bd remember` (AGENTS.md). Do not run `bd setup` or `bd init` in a repo with
this harness: tested over copies of our files, it added a second Claude
SessionStart hook (double injection), merged the four Codex events beside
ours and appended an AGENTS.md block that says to use `bd remember`.

## 11. Sync, versioning and branches

Treat the issue data like a git repository.

- `bd dolt` — The storage engine and its remote.
  - `bd dolt push` / `bd dolt pull` — Publish and fetch commits through the
    Dolt remote, which can ride your git origin as `refs/dolt/data` plus a
    `__dolt_remote_info__` branch (checked with `git ls-remote`). Beads
    exist only on this machine until pushed.
  - `bd dolt commit` — Commit pending changes (the commit point in batch
    auto-commit mode).
  - `bd dolt remote` — Manage remotes; use it rather than raw `dolt remote
    add`, which a running server does not see.
    - `bd dolt remote add` / `list` / `remove` — Add, show and remove.
    - `bd dolt remote reset-data` — Rebuild a remote's store after a history
      squash, so it drops the old data.
  - `bd dolt status` / `bd dolt show` — Engine status and configuration.
  - `bd dolt start` / `bd dolt stop` / `bd dolt test` — Start, stop and test
    a SQL server (server mode only).
  - `bd dolt set` — Server connection settings (server mode only; secrets
    stay in environment variables or the credentials file).
  - `bd dolt killall` — Kill orphaned SQL-server processes.
- `bd sync` — One full cycle: pull, detect conflicts reliably, repair
  blocked flags, push with retries. Exit codes for timers: 0 ok, 1 error, 2
  conflict (alert a person), 3 retries exhausted, 4 stuck uncommitted
  changes. It stops on a conflict and never resolves it.
- `bd vc` — Git-like operations on the issue data.
  - `bd vc status` — Branch, commit and uncommitted changes.
  - `bd vc commit` — Commit with a message.
  - `bd vc merge` — Merge a branch.
- `bd branch` — List or create branches of the issue data, for example to
  plan speculatively and merge later.
- `bd conflicts` — Handle merge conflicts without the raw Dolt CLI.
  - `bd conflicts list` — What is conflicted.
  - `bd conflicts show` — Base, ours and theirs, field by field.
  - `bd conflicts resolve` — Take ours or theirs per bead or per table, then
    conclude the merge.
- `bd bootstrap` — Set up the database on a fresh clone or new machine
  without destroying data: clones from the remote, or restores from a backup
  or JSONL. A fresh `git clone` has no database: `bd ready` fails with "no
  beads database found" and hints at `bd init`, which would create a new
  empty one; `bootstrap` is the right step (tested).

Worktrees share the main clone's database (section 15), and replicas need a
per-store `node_id` that is never committed to the tracked config, with lease
and reclaim windows longer than the sync interval (reported).

## 12. Import, export and backup

Move beads in and out, and keep recoverable copies. These three are not
interchangeable:

| | Contains | Restorable |
|---|---|---|
| copy of `.beads` | everything, as raw files | only if nothing was writing |
| `bd backup` | the full database with history | yes, with `backup restore` |
| `bd export` | bead rows; no history, wisps or memories | partly, through `import` |

- `bd export` — Beads as JSONL, with comments, labels and dependencies
  embedded (checked). Memories only with `--include-memories` and wisps never
  (tested); infrastructure beads only with `--all` (reported). An interchange format,
  not a backup. `.beads/issues.jsonl` is refreshed by the pre-commit hook only
  when `export.auto` is on, which is off by default, so a tracked copy goes
  stale (checked on vip-agent).
- `bd import` — Upsert JSONL into the database. A row replaces a local one
  only when its `updated_at` is strictly newer (ties keep local;
  `--allow-stale` forces), it never deletes, and a re-run is safe.
  Re-importing unchanged rows still adds a Dolt commit (tested).
- `bd backup` — Dolt-native backups that keep full history. Auto-backup runs
  when `backup.enabled` is unset, the mode is not SQL server and a git
  remote exists, although `bd config show` prints `false (default)` (source;
  vip-agent has fresh `.beads/backup` files).
  - `bd backup init` — Set a destination (a directory or DoltHub).
  - `bd backup sync` — Take a backup (atomic).
  - `bd backup status` — The last backup.
  - `bd backup restore` — Restore a database from a backup.
  - `bd backup remove` — Forget the destination (the data stays).
- `bd restore` — Recover the original text of a bead summarised by
  `admin compact`; it only previews unless `--apply`. It does not undo a
  delete.
- `bd schema` — The JSON Schema of bd's `--json` and export records, for
  generating typed models.

## 13. External trackers

Two-way sync with other issue trackers; each has the same shape: `pull` and
`push` specific items, `status`, and a bidirectional `sync` with a conflict
preference. Beads and remote issues are joined through `external_ref`.

- `bd github` — GitHub Issues, configured with `github.repository` and
  `github.token` (or `GITHUB_REPOSITORY`, `GITHUB_TOKEN`). Maps open/closed
  plus `status::`, `priority::` and `type::` labels, title, description and
  labels; not comments (#7053) or assignees (#6775), and relationships only
  on unreleased main (#5970).
  - `bd github sync` / `pull` / `push` / `status` / `repos` — Sync, pull
    items, push beads, show state, list accessible repos.
- `bd gitlab` — GitLab issues (project or group level).
  - `bd gitlab sync` / `pull` / `push` / `status` / `projects` — As above;
    list accessible projects.
- `bd jira` — Jira.
  - `bd jira sync` / `pull` / `push` / `status` — As above.
- `bd linear` — Linear, including priority, state, label and relation
  mappings and milestones.
  - `bd linear sync` / `pull` / `push` / `status` / `teams` — As above;
    list teams for configuration.
- `bd ado` — Azure DevOps work items with area/iteration filters.
  - `bd ado sync` / `pull` / `push` / `status` / `projects` — As above.
- `bd notion` — Notion databases.
  - `bd notion init` — Create a dedicated Beads database in Notion.
  - `bd notion connect` — Connect to an existing one.
  - `bd notion sync` / `pull` / `push` / `status` — As above.

GitHub sync behavior, evaluated 2026-10-05:

- Design (source): after the first full sync, pull fetches only issues changed
  since `last_sync`, and push skips unchanged linked beads through a stored
  content hash (the fix for #4214, which re-pushed the whole backlog every
  run). `last_sync` and the hashes are clone-local, so a new clone or machine
  starts with a full sync.
- Measured (tested, read-only pull of a public repo with 398 issues): the
  first pull took 25 s; each pull with nothing changed took 174–178 s, CPU 34
  s. This matches open #6605 (one history scan per linked issue on embedded
  Dolt). Imported beads get IDs
  like `gl-1791170797566-396-d3a23171` (#6814).
- Open correctness bugs (reported, priority 1 upstream on 2026-10-05): #6806,
  an issue written on GitHub just before a sync is never pulled; #6773, a
  closed bead is created as an open GitHub issue and never closed; #5486,
  close status is sometimes not pushed, without an error.

*Our use:* do not adopt GitHub sync on 1.3.0; revisit when a release fixes
#6605, #6806 and #6773.

## 14. Programmatic access

Drive bd from programs instead of by hand.

- Global `--json` — Structured output on every command (`BD_JSON_ENVELOPE=1`
  gives the wrapped shape that becomes the default in v2.0). Other global
  flags: `--actor` (attribution), `--readonly`, `--sandbox` (no auto-push),
  `--db` / `--directory` (target another project), `--quiet`, `--verbose`,
  `--no-color`. Exit codes worth handling: 13 (compare-and-swap mismatch), 14
  (migration freeze), 2 (`--max-rows` exceeded).
- `bd serve` — An HTTP API (OpenAPI at `/v0`) over the same operations as
  the CLI, for clients that would otherwise spawn bd per call. Loopback only
  unless given a token file; no TLS; hooks do not fire. Requires a Dolt SQL
  server: embedded workspaces refuse it (checked 2026-09-30).
- `bd sql` — Raw SQL against the database, for debugging or queries the CLI
  cannot express. Writes through it bypass the events journal. Not supported
  in embedded mode (checked 2026-09-30).
- `bd batch` — Many writes (close, update, create, dep add/remove) in one
  transaction and one commit, all-or-nothing.
- `bd completion` — Shell completion scripts.
  - `bd completion bash` / `zsh` / `fish` / `powershell` — One per shell.

*Our use:* our projects run embedded Dolt, so `bd serve` and `bd sql` are
unavailable. The dashboard reads through `--readonly --directory <project>`
CLI calls with `--json` or `export`, typed with `bd schema`. Even under
`--readonly`, `bd show` rewrites `.beads/last-touched`, the fallback target
of an interactive `bd close` or `bd update` with no ID, so the dashboard
must not call it (checked 2026-09-30).

## 15. Setup, configuration and diagnostics

Initialise projects, configure them, and find out what bd is actually using.

- `bd init` — Create `.beads/` and its database: embedded or server,
  prefix, role, stealth mode (invisible to collaborators), agent files and
  hooks. Without `--skip-agents` it also runs the Claude, Codex and Cursor
  setup recipes (tested). Over an existing database it aborts and suggests
  `export` then `--reinit-local` (tested); a destructive re-init without a
  terminal needs `--destroy-token=DESTROY-<prefix>` and returns exit codes 10
  to 12. Inside another repo it resolves to the parent's `.beads` unless the
  folder has its own git repo and a seeded `.beads/config.yaml`
  (tested 2026-09-30).
- `bd init-safety` — Explains `init`'s safety rules, the destroy-token
  format and refusal exit codes.
- `bd config` — Project settings (integrations, custom statuses and types,
  claim pools, lint sections, export/import, doctor suppressions).
  Precedence: flags, then environment, then config files merged in order
  (`~/.beads`, `~/.config/bd/config.yaml`, `.beads/config.yaml`,
  `$BEADS_DIR`, `config.local.yaml`), then defaults; database-only keys have
  no environment override (reported).
  - `bd config get` / `set` / `unset` / `list` — Read and write keys. `set`
    accepts unknown keys silently, so success does not mean bd uses the key
    (tested).
  - `bd config set-many` — Set several keys in one commit.
  - `bd config show` — Every effective value and where it came from. For
    keys whose default is decided in code it prints the stored default, not
    the behavior (`backup.enabled`, section 12).
  - `bd config validate` — Check sync-related settings.
  - `bd config drift` — Read-only check that hooks, remote and server match
    the config.
  - `bd config apply` — Fix that drift (idempotent).
- `bd context` — Backend identity, paths and sync settings, readable even
  when the database cannot open.
- `bd where` — Which `.beads` directory and database are actually in use.
- `bd info` — Database path, counts, schema and what's new.
- `bd ping` — Quick check that the database opens and answers.
- `bd doctor` — Health checks and repairs. In embedded mode (ours) it prints
  "not yet supported in embedded mode" and only the `artifacts`,
  `conventions` and `pollution` checks work (tested), so doc runbooks that
  start with `bd doctor --fix` assume server mode. Use `where`, `lint`,
  `recompute-blocked`, `stale` and `orphans` instead.
- `bd version` — The installed version.
- `bd upgrade` — Track bd version changes.
  - `bd upgrade status` — Has bd changed since last use?
  - `bd upgrade review` — Everything that changed since the version you last
    used.
  - `bd upgrade ack` — Mark the current version as seen.
- `bd worktree` — Git worktrees that share the main clone's database.
  - `bd worktree create` — Create one (and gitignore it).
  - `bd worktree list` — All worktrees and their Beads state.
  - `bd worktree info` — The current worktree.
  - `bd worktree remove` — Remove one only if it is clean and merged.

## 16. Quality and hygiene

Keep the data trustworthy as it grows.

- `bd lint` — Beads missing required sections for their type (for example
  acceptance criteria), extendable per type in config.
- `bd duplicates` — Beads with identical content, with optional automatic
  merging.
- `bd find-duplicates` — Beads about the same thing in different words, by
  text similarity or an LLM.
- `bd preflight` — A pre-PR checklist aimed at contributors to the beads
  project itself (Go tests, lint, nix hash); of little use elsewhere.
- `bd recompute-blocked` — Rebuild the stored blocked flags that `ready`
  trusts; run it after a migration (needed in our 1.3.0 upgrade).

## 17. Maintenance and storage

Keep the database small and fast, and fix structural problems. From mildest
to most severe:

- `bd compact` — Squash Dolt commits older than N days (default 30),
  keeping recent history. Preview by default; `--force` acts.
- `bd flatten` — Squash all history into one commit (irreversible). On a
  pushed database this is a history rewrite: every other clone must
  `bootstrap` again and never pull from an old clone.
- `bd gc` — Three phases: delete closed beads older than 90 days (default),
  compact history, then Dolt GC. To reclaim space without deleting beads:
  `bd gc --skip-decay --full`. `compact` and `flatten` free little disk until
  Dolt GC runs (`--full`).
- `bd prune` — Delete old closed regular beads; requires `--older-than` or
  `--pattern`. It skips pinned beads and beads still cited by open work.
- `bd purge` — Delete closed ephemeral beads (wisps).
- `bd admin` — Administrative operations.
  - `bd admin cleanup` — Delete closed beads; all of them by default, by age
    with `--older-than`.
  - `bd admin compact` — Replace old closed beads' text with summaries
    (agent-supplied or AI; the original is discarded, `bd restore` recovers
    it), or garbage-collect Dolt.
  - `bd admin reset` — Remove all Beads data and hooks from a project.
- `bd rename-prefix` — Change the ID prefix everywhere, or consolidate mixed
  prefixes.
- `bd migrate` — Schema and layout changes; procedure and principles in
  [upgrades](upgrades.md).
  - `bd migrate schema` — Apply pending schema migrations explicitly.
  - `bd migrate hooks` — Convert hook files to the marker-managed format.
  - `bd migrate sync` — Commit issue data to a dedicated branch.
  - `bd migrate issues` — Move beads between repositories (see section 8).
  - `bd migrate legacy-sqlite` — Read an old SQLite database out as JSONL.
  - `bd migrate from-server-to-proxied-server`,
    `bd migrate from-proxied-server-to-server`,
    `bd migrate from-shared-server-to-proxied-server`,
    `bd migrate from-proxied-server-to-shared-server` — Experimental
    switches between server modes; no data moves.

*Our use:* any deletion here also removes the beads from the hub and the
dashboard. To reclaim space while keeping every closed bead:
`bd compact --days 90 --force`, then `bd gc --skip-decay --full`.

## Capabilities most worth adopting

*Our use*, as recommendations for the owner:

- **Claims and leases** (`ready --claim`, `heartbeat`, a scheduled `reclaim`)
  with one `BEADS_ACTOR` per agent, so parallel agents never double-take
  work and crashed agents release theirs.
- **Gates** for waits on CI, PRs or a human, with `bd gate check` scheduled,
  so blocked work is explicit and `ready` stays honest.
- **`bd human`** as the single queue of questions for the owner.
- **Provenance** to tie beads to the commits and PRs that closed them.
- **Formulas and molecules** for workflows we repeat (reviews, releases,
  upgrades like the 1.3.0 one).
- **`bd create --graph`** to write a whole plan, hierarchy and dependencies
  in one step.
- **`bd --readonly` with `export` and `--json` reads, typed by
  `bd schema`,** as the dashboard's data interface.

Not yet: cross-project `external:` dependencies and GitHub issue sync, until
the 1.3.0 defects above are fixed.
