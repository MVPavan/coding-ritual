# bd CLI reference — bd version 1.3.0 (f45b249ce: HEAD@f45b249ce6b4)

Generated from `bd --help` output by `harness_lifecycle/beads/bd-cli-reference.py`; 292 commands. Regenerate after every bd upgrade and keep the version in the file name. Global flags apply to every command and are listed once below; each command lists only its own flags. Hidden internal commands in 1.3.0 (not shown by `--help`, so not covered here): `db-proxy-child`, `cursor-hook`, `codex-hook` and the metrics sender.

## Command tree

- [`bd assign`](#bd-assign) — Assign an issue to someone
- [`bd children`](#bd-children) — List child beads of a parent
- [`bd close`](#bd-close) — Close one or more issues
- [`bd comment`](#bd-comment) — Add a comment to an issue
- [`bd comments`](#bd-comments) — View or manage comments on an issue
  - [`bd comments add`](#bd-comments-add) — Add a comment to an issue
  - [`bd comments list`](#bd-comments-list) — Invalid — use bd comments <issue-id> to list comments
- [`bd create`](#bd-create) — Create a new issue (or batch from markdown/graph JSON)
- [`bd create-form`](#bd-create-form) — Create a new issue using an interactive form
- [`bd delete`](#bd-delete) — Delete one or more issues and clean up references
- [`bd edit`](#bd-edit) — Edit an issue field in $EDITOR
- [`bd gate`](#bd-gate) — Manage async coordination gates
  - [`bd gate add-waiter`](#bd-gate-add-waiter) — Add a waiter to a gate
  - [`bd gate check`](#bd-gate-check) — Evaluate gates and close resolved ones
  - [`bd gate create`](#bd-gate-create) — Create a gate that blocks an issue
  - [`bd gate discover`](#bd-gate-discover) — Discover await_id for gh:run gates
  - [`bd gate list`](#bd-gate-list) — List gate issues
  - [`bd gate resolve`](#bd-gate-resolve) — Manually resolve (close) a gate
  - [`bd gate show`](#bd-gate-show) — Show a gate issue
- [`bd heartbeat`](#bd-heartbeat) — Refresh the lease on an issue you hold in_progress
- [`bd label`](#bd-label) — Manage issue labels
  - [`bd label add`](#bd-label-add) — Add one or more labels to one or more issues
  - [`bd label list`](#bd-label-list) — List labels for an issue
  - [`bd label list-all`](#bd-label-list-all) — List all unique labels in the database
  - [`bd label propagate`](#bd-label-propagate) — Propagate a label from a parent issue to all its children
  - [`bd label remove`](#bd-label-remove) — Remove one or more labels from one or more issues
- [`bd link`](#bd-link) — Link two issues with a dependency
- [`bd list`](#bd-list) — List issues
- [`bd merge-slot`](#bd-merge-slot) — Manage merge-slot gates for serialized conflict resolution
  - [`bd merge-slot acquire`](#bd-merge-slot-acquire) — Acquire the merge slot
  - [`bd merge-slot check`](#bd-merge-slot-check) — Check merge slot availability
  - [`bd merge-slot create`](#bd-merge-slot-create) — Create a merge slot bead for the current rig
  - [`bd merge-slot release`](#bd-merge-slot-release) — Release the merge slot
- [`bd note`](#bd-note) — Append a note to an issue
- [`bd priority`](#bd-priority) — Set the priority of an issue
- [`bd promote`](#bd-promote) — Promote a wisp to a permanent bead
- [`bd provenance`](#bd-provenance) — Append-only provenance event log
  - [`bd provenance by-ref`](#bd-provenance-by-ref) — List provenance events bound to a ref
  - [`bd provenance log`](#bd-provenance-log) — List provenance events for an issue
  - [`bd provenance record`](#bd-provenance-record) — Record a provenance event (idempotent)
- [`bd q`](#bd-q) — Quick capture: create issue and output only ID
- [`bd query`](#bd-query) — Query issues using a simple query language
- [`bd reclaim`](#bd-reclaim) — Revert stale-lease in_progress issues back to ready (dead-worker recovery)
- [`bd reopen`](#bd-reopen) — Reopen one or more closed issues
- [`bd search`](#bd-search) — Search issues by text query
- [`bd set-state`](#bd-set-state) — Set operational state (creates event + updates label)
- [`bd show`](#bd-show) — Show issue details
- [`bd state`](#bd-state) — Query the current value of a state dimension
  - [`bd state list`](#bd-state-list) — List all state dimensions on an issue
- [`bd tag`](#bd-tag) — Add a label to an issue
- [`bd todo`](#bd-todo) — Manage TODO items (convenience wrapper for task issues)
  - [`bd todo add`](#bd-todo-add) — Add a new TODO item
  - [`bd todo done`](#bd-todo-done) — Mark TODO(s) as done
  - [`bd todo list`](#bd-todo-list) — List TODO items
- [`bd unclaim`](#bd-unclaim) — Release a claimed issue
- [`bd update`](#bd-update) — Update one or more issues
- [`bd count`](#bd-count) — Count issues matching filters
- [`bd diff`](#bd-diff) — Show changes between two commits or branches
- [`bd find-duplicates`](#bd-find-duplicates) — Find semantically similar issues using text analysis or AI
- [`bd history`](#bd-history) — Show version history for an issue
- [`bd lint`](#bd-lint) — Check issues for missing template sections
- [`bd stale`](#bd-stale) — Show stale issues (not updated recently)
- [`bd status`](#bd-status) — Show issue database overview and statistics
- [`bd statuses`](#bd-statuses) — List valid issue statuses
- [`bd types`](#bd-types) — List valid issue types
- [`bd dep`](#bd-dep) — Manage dependencies
  - [`bd dep add`](#bd-dep-add) — Add a dependency
  - [`bd dep cycles`](#bd-dep-cycles) — Detect dependency cycles
  - [`bd dep list`](#bd-dep-list) — List dependencies or dependents of one or more issues
  - [`bd dep relate`](#bd-dep-relate) — Create a bidirectional relates_to link between issues
  - [`bd dep remove`](#bd-dep-remove) — Remove a dependency
  - [`bd dep tree`](#bd-dep-tree) — Show dependency tree
  - [`bd dep unrelate`](#bd-dep-unrelate) — Remove a relates_to link between issues
- [`bd duplicate`](#bd-duplicate) — Mark an issue as a duplicate of another
- [`bd duplicates`](#bd-duplicates) — Find and optionally merge duplicate issues
- [`bd epic`](#bd-epic) — Epic management commands
  - [`bd epic status`](#bd-epic-status) — Show epic completion status
- [`bd graph`](#bd-graph) — Display issue dependency graph
  - [`bd graph check`](#bd-graph-check) — Check dependency graph integrity
- [`bd supersede`](#bd-supersede) — Mark an issue as superseded by a newer one
- [`bd swarm`](#bd-swarm) — Swarm management for structured epics
  - [`bd swarm create`](#bd-swarm-create) — Create a swarm molecule from an epic
  - [`bd swarm list`](#bd-swarm-list) — List all swarm molecules
  - [`bd swarm status`](#bd-swarm-status) — Show current swarm status
  - [`bd swarm validate`](#bd-swarm-validate) — Validate epic structure for swarming
- [`bd backup`](#bd-backup) — Back up your beads database
  - [`bd backup init`](#bd-backup-init) — Set up a Dolt backup destination
  - [`bd backup remove`](#bd-backup-remove) — Remove the configured backup destination
  - [`bd backup restore`](#bd-backup-restore) — Restore database from a Dolt backup
  - [`bd backup status`](#bd-backup-status) — Show last backup status
  - [`bd backup sync`](#bd-backup-sync) — Push database to configured Dolt backup
- [`bd branch`](#bd-branch) — List or create branches
- [`bd conflicts`](#bd-conflicts) — Inspect and resolve live merge conflicts
  - [`bd conflicts list`](#bd-conflicts-list) — List tables and issues with live merge conflicts
  - [`bd conflicts resolve`](#bd-conflicts-resolve) — Resolve merge conflicts with --ours or --theirs
  - [`bd conflicts show`](#bd-conflicts-show) — Show conflicted rows field by field (base/ours/theirs)
- [`bd export`](#bd-export) — Export issues to JSONL format
- [`bd federation`](#bd-federation) — Manage peer-to-peer federation with other workspaces
  - [`bd federation add-peer`](#bd-federation-add-peer) — Add a federation peer with optional SQL credentials
  - [`bd federation list-peers`](#bd-federation-list-peers) — List configured federation peers
  - [`bd federation status`](#bd-federation-status) — Show federation sync status
  - [`bd federation sync`](#bd-federation-sync) — Synchronize with a peer town
- [`bd import`](#bd-import) — Import issues from a JSONL file or stdin into the database
- [`bd restore`](#bd-restore) — Restore the pre-compaction content of a compacted issue
- [`bd sync`](#bd-sync) — Pull, check for conflicts, repair is_blocked, and push (the federation loop)
- [`bd vc`](#bd-vc) — Version control operations
  - [`bd vc commit`](#bd-vc-commit) — Create a commit with all staged changes
  - [`bd vc merge`](#bd-vc-merge) — Merge a branch into the current branch
  - [`bd vc status`](#bd-vc-status) — Show current branch and uncommitted changes
- [`bd bootstrap`](#bd-bootstrap) — Non-destructive database setup for fresh clones and recovery
- [`bd config`](#bd-config) — Manage configuration settings
  - [`bd config apply`](#bd-config-apply) — Reconcile system state to match configuration
  - [`bd config drift`](#bd-config-drift) — Detect config-vs-reality inconsistencies
  - [`bd config get`](#bd-config-get) — Get a configuration value
  - [`bd config list`](#bd-config-list) — List all configuration
  - [`bd config set`](#bd-config-set) — Set a configuration value
  - [`bd config set-many`](#bd-config-set-many) — Set multiple configuration values in one operation
  - [`bd config show`](#bd-config-show) — Show all effective configuration with provenance
  - [`bd config unset`](#bd-config-unset) — Delete a configuration value
  - [`bd config validate`](#bd-config-validate) — Validate sync-related configuration
- [`bd context`](#bd-context) — Show effective backend identity and repository context
- [`bd dolt`](#bd-dolt) — Configure Dolt database settings
  - [`bd dolt commit`](#bd-dolt-commit) — Create a Dolt commit from pending changes
  - [`bd dolt killall`](#bd-dolt-killall) — Kill all orphan Dolt server processes
  - [`bd dolt pull`](#bd-dolt-pull) — Pull commits from Dolt remote
  - [`bd dolt push`](#bd-dolt-push) — Push commits to Dolt remote
  - [`bd dolt remote`](#bd-dolt-remote) — Manage Dolt remotes
    - [`bd dolt remote list`](#bd-dolt-remote-list) — List all configured remotes
    - [`bd dolt remote add`](#bd-dolt-remote-add) — Add a Dolt remote
    - [`bd dolt remote remove`](#bd-dolt-remote-remove) — Remove a Dolt remote
    - [`bd dolt remote reset-data`](#bd-dolt-remote-reset-data) — Replace a remote's data plane in place after a history squash
  - [`bd dolt set`](#bd-dolt-set) — Set a Dolt configuration value
  - [`bd dolt show`](#bd-dolt-show) — Show current Dolt configuration with connection status
  - [`bd dolt start`](#bd-dolt-start) — Start the Dolt SQL server for this project
  - [`bd dolt status`](#bd-dolt-status) — Show Dolt engine status
  - [`bd dolt stop`](#bd-dolt-stop) — Stop the Dolt SQL server for this project
  - [`bd dolt test`](#bd-dolt-test) — Test connection to Dolt server
- [`bd forget`](#bd-forget) — Remove a persistent memory
- [`bd hooks`](#bd-hooks) — Manage git hooks for beads integration
  - [`bd hooks install`](#bd-hooks-install) — Install bd git hooks
  - [`bd hooks list`](#bd-hooks-list) — List installed git hooks status
  - [`bd hooks run`](#bd-hooks-run) — Execute a git hook (called by thin shims)
  - [`bd hooks uninstall`](#bd-hooks-uninstall) — Uninstall bd git hooks
- [`bd human`](#bd-human) — Show essential commands for human users
  - [`bd human dismiss`](#bd-human-dismiss) — Dismiss a human-needed bead
  - [`bd human list`](#bd-human-list) — List human-needed beads
  - [`bd human respond`](#bd-human-respond) — Respond to a human-needed bead
  - [`bd human stats`](#bd-human-stats) — Show summary statistics for human-needed beads
- [`bd info`](#bd-info) — Show database information
- [`bd init`](#bd-init) — Initialize bd in the current directory
- [`bd kv`](#bd-kv) — Key-value store commands
  - [`bd kv clear`](#bd-kv-clear) — Delete a key-value pair
  - [`bd kv get`](#bd-kv-get) — Get a value by key
  - [`bd kv list`](#bd-kv-list) — List all key-value pairs
  - [`bd kv set`](#bd-kv-set) — Set a key-value pair
- [`bd memories`](#bd-memories) — List or search persistent memories
- [`bd migrate-personal`](#bd-migrate-personal) — Move personal planning issues from the project database to your planning repo
- [`bd onboard`](#bd-onboard) — Display minimal snippet for agent instructions file
- [`bd prime`](#bd-prime) — Output AI-optimized workflow context
- [`bd quickstart`](#bd-quickstart) — Quick start guide for bd
- [`bd recall`](#bd-recall) — Retrieve a specific memory
- [`bd remember`](#bd-remember) — Store a persistent memory
- [`bd setup`](#bd-setup) — Setup integration with AI editors
- [`bd where`](#bd-where) — Show active beads location
- [`bd batch`](#bd-batch) — Run multiple write operations in a single database transaction
- [`bd compact`](#bd-compact) — Squash old Dolt commits to reduce history size
- [`bd doctor`](#bd-doctor) — Check and fix beads installation health (start here)
- [`bd events`](#bd-events) — Read and manage the durable events journal
  - [`bd events export`](#bd-events-export) — Print the entire journal from the beginning (JSON lines)
  - [`bd events prune`](#bd-events-prune) — Delete journal records below a sequence number (retention)
  - [`bd events tail`](#bd-events-tail) — Print journal records after a sequence number (JSON lines)
- [`bd flatten`](#bd-flatten) — Squash all Dolt history into a single commit
- [`bd gc`](#bd-gc) — Garbage collect: decay old issues, compact Dolt commits, run Dolt GC
- [`bd migrate`](#bd-migrate) — Database migration commands
  - [`bd migrate hooks`](#bd-migrate-hooks) — Plan git hook migration to marker-managed format
  - [`bd migrate issues`](#bd-migrate-issues) — Move issues between repositories
  - [`bd migrate schema`](#bd-migrate-schema) — Apply pending schema migrations (idempotent)
  - [`bd migrate sync`](#bd-migrate-sync) — Set up sync.branch workflow for multi-clone setups
  - [`bd migrate from-server-to-proxied-server`](#bd-migrate-from-server-to-proxied-server) — [EXPERIMENTAL] Switch server mode to proxied-server mode
  - [`bd migrate from-proxied-server-to-server`](#bd-migrate-from-proxied-server-to-server) — [EXPERIMENTAL] Switch proxied-server mode to server mode
  - [`bd migrate from-shared-server-to-proxied-server`](#bd-migrate-from-shared-server-to-proxied-server) — [EXPERIMENTAL] Switch shared-server mode to proxied-server mode
  - [`bd migrate from-proxied-server-to-shared-server`](#bd-migrate-from-proxied-server-to-shared-server) — [EXPERIMENTAL] Switch proxied-server mode to shared-server mode
  - [`bd migrate legacy-sqlite`](#bd-migrate-legacy-sqlite) — Read an authenticated legacy SQLite database as JSONL
- [`bd ping`](#bd-ping) — Check database connectivity
- [`bd preflight`](#bd-preflight) — Show PR readiness checklist
- [`bd prune`](#bd-prune) — Delete old closed beads to reclaim space and shrink exports
- [`bd purge`](#bd-purge) — Delete closed ephemeral beads to reclaim space
- [`bd rename-prefix`](#bd-rename-prefix) — Rename the issue prefix for all issues in the database
- [`bd rules`](#bd-rules) — Audit and compact Claude rules
  - [`bd rules audit`](#bd-rules-audit) — Scan rules for contradictions and merge opportunities
  - [`bd rules compact`](#bd-rules-compact) — Merge related rules into composites
- [`bd sql`](#bd-sql) — Execute raw SQL against the beads database
- [`bd upgrade`](#bd-upgrade) — Check and manage bd version upgrades
  - [`bd upgrade ack`](#bd-upgrade-ack) — Acknowledge the current bd version
  - [`bd upgrade review`](#bd-upgrade-review) — Review changes since last bd version
  - [`bd upgrade status`](#bd-upgrade-status) — Check if bd version has changed
- [`bd worktree`](#bd-worktree) — Manage git worktrees for parallel development
  - [`bd worktree create`](#bd-worktree-create) — Create a worktree
  - [`bd worktree info`](#bd-worktree-info) — Show worktree info for current directory
  - [`bd worktree list`](#bd-worktree-list) — List all git worktrees
  - [`bd worktree remove`](#bd-worktree-remove) — Remove a worktree with safety checks
- [`bd admin`](#bd-admin) — Administrative commands for database maintenance
  - [`bd admin cleanup`](#bd-admin-cleanup) — Delete closed issues (issue lifecycle)
  - [`bd admin compact`](#bd-admin-compact) — Compact old closed issues to save space (storage optimization)
  - [`bd admin reset`](#bd-admin-reset) — Remove all beads data and configuration (full reset)
- [`bd jira`](#bd-jira) — Jira integration commands
  - [`bd jira pull`](#bd-jira-pull) — Pull specific items from Jira
  - [`bd jira push`](#bd-jira-push) — Push specific beads to Jira
  - [`bd jira status`](#bd-jira-status) — Show Jira sync status
  - [`bd jira sync`](#bd-jira-sync) — Synchronize issues with Jira
- [`bd linear`](#bd-linear) — Linear integration commands
  - [`bd linear pull`](#bd-linear-pull) — Pull specific items from Linear
  - [`bd linear push`](#bd-linear-push) — Push specific beads to Linear
  - [`bd linear status`](#bd-linear-status) — Show Linear sync status
  - [`bd linear sync`](#bd-linear-sync) — Synchronize issues with Linear
  - [`bd linear teams`](#bd-linear-teams) — List available Linear teams
- [`bd repo`](#bd-repo) — Manage multiple repository configuration
  - [`bd repo add`](#bd-repo-add) — Add an additional repository to sync
  - [`bd repo list`](#bd-repo-list) — List all configured repositories
  - [`bd repo remove`](#bd-repo-remove) — Remove a repository from sync configuration
  - [`bd repo sync`](#bd-repo-sync) — Manually trigger multi-repo sync
- [`bd ado`](#bd-ado) — Azure DevOps integration commands
  - [`bd ado projects`](#bd-ado-projects) — List accessible Azure DevOps projects
  - [`bd ado pull`](#bd-ado-pull) — Pull specific items from Azure DevOps
  - [`bd ado push`](#bd-ado-push) — Push specific beads to Azure DevOps
  - [`bd ado status`](#bd-ado-status) — Show Azure DevOps sync status
  - [`bd ado sync`](#bd-ado-sync) — Sync issues with Azure DevOps
- [`bd audit`](#bd-audit) — Record and label agent interactions (append-only JSONL)
  - [`bd audit label`](#bd-audit-label) — Append a label entry referencing an existing interaction
  - [`bd audit record`](#bd-audit-record) — Append an audit interaction entry
- [`bd blocked`](#bd-blocked) — Show blocked issues
- [`bd completion`](#bd-completion) — Generate the autocompletion script for the specified shell
  - [`bd completion bash`](#bd-completion-bash) — Generate the autocompletion script for bash
  - [`bd completion fish`](#bd-completion-fish) — Generate the autocompletion script for fish
  - [`bd completion powershell`](#bd-completion-powershell) — Generate the autocompletion script for powershell
  - [`bd completion zsh`](#bd-completion-zsh) — Generate the autocompletion script for zsh
- [`bd cook`](#bd-cook) — Compile a formula into a proto (ephemeral by default)
- [`bd defer`](#bd-defer) — Defer one or more issues for later
- [`bd formula`](#bd-formula) — Manage workflow formulas
  - [`bd formula list`](#bd-formula-list) — List available formulas from all search paths
  - [`bd formula show`](#bd-formula-show) — Show formula details, steps, and composition rules
  - [`bd formula schema`](#bd-formula-schema) — Show the formula schema index (alias: primitives)
  - [`bd formula convert`](#bd-formula-convert) — Convert formula from JSON to TOML
- [`bd github`](#bd-github) — GitHub integration commands
  - [`bd github pull`](#bd-github-pull) — Pull specific items from GitHub
  - [`bd github push`](#bd-github-push) — Push specific beads to GitHub
  - [`bd github repos`](#bd-github-repos) — List accessible GitHub repositories
  - [`bd github status`](#bd-github-status) — Show GitHub sync status
  - [`bd github sync`](#bd-github-sync) — Sync issues with GitHub
- [`bd gitlab`](#bd-gitlab) — GitLab integration commands
  - [`bd gitlab projects`](#bd-gitlab-projects) — List accessible GitLab projects
  - [`bd gitlab pull`](#bd-gitlab-pull) — Pull specific items from GitLab
  - [`bd gitlab push`](#bd-gitlab-push) — Push specific beads to GitLab
  - [`bd gitlab status`](#bd-gitlab-status) — Show GitLab sync status
  - [`bd gitlab sync`](#bd-gitlab-sync) — Sync issues with GitLab
- [`bd init-safety`](#bd-init-safety) — Explain bd init flag semantics and the destroy-token format
- [`bd mail`](#bd-mail) — Delegate to mail provider (e.g., gt mail)
- [`bd metrics`](#bd-metrics) — Show or change anonymous usage-metrics settings
  - [`bd metrics example`](#bd-metrics-example) — Show real examples of the anonymous metrics bd sends
  - [`bd metrics off`](#bd-metrics-off) — Turn anonymous usage metrics off
  - [`bd metrics on`](#bd-metrics-on) — Turn anonymous usage metrics on
- [`bd mol`](#bd-mol) — Molecule commands (work templates)
  - [`bd mol show`](#bd-mol-show) — Show proto/molecule structure and variables
  - [`bd mol pour`](#bd-mol-pour) — Instantiate proto as persistent mol (liquid phase)
  - [`bd mol wisp`](#bd-mol-wisp) — Instantiate proto as ephemeral wisp (vapor phase)
    - [`bd mol wisp list`](#bd-mol-wisp-list) — List all wisps in current context
    - [`bd mol wisp gc`](#bd-mol-wisp-gc) — Garbage collect orphaned wisps
    - [`bd mol wisp create`](#bd-mol-wisp-create) — Instantiate a proto as a wisp (solid -> vapor)
  - [`bd mol bond`](#bd-mol-bond) — Polymorphic combine: proto+proto, proto+mol, mol+mol
  - [`bd mol squash`](#bd-mol-squash) — Condense molecule to digest
  - [`bd mol burn`](#bd-mol-burn) — Discard wisp
  - [`bd mol distill`](#bd-mol-distill) — Extract proto from ad-hoc epic
  - [`bd mol current`](#bd-mol-current) — Show current position in molecule workflow
  - [`bd mol progress`](#bd-mol-progress) — Show molecule progress summary
  - [`bd mol ready`](#bd-mol-ready) — Find molecules ready for gate-resume dispatch
  - [`bd mol seed`](#bd-mol-seed) — Verify formula accessibility
  - [`bd mol stale`](#bd-mol-stale) — Detect complete-but-unclosed molecules
- [`bd notion`](#bd-notion) — Notion integration commands
  - [`bd notion connect`](#bd-notion-connect) — Connect bd to an existing Notion database or data source
  - [`bd notion init`](#bd-notion-init) — Create a dedicated Beads database in Notion
  - [`bd notion pull`](#bd-notion-pull) — Pull specific items from Notion
  - [`bd notion push`](#bd-notion-push) — Push specific beads to Notion
  - [`bd notion status`](#bd-notion-status) — Show Notion sync status
  - [`bd notion sync`](#bd-notion-sync) — Sync issues with Notion
- [`bd orphans`](#bd-orphans) — Identify orphaned issues (referenced in commits but still open)
- [`bd ready`](#bd-ready) — Show ready work (open, no active blockers)
- [`bd rename`](#bd-rename) — Rename an issue ID
- [`bd schema`](#bd-schema) — Print the JSON Schema for bd's --json / export output
- [`bd serve`](#bd-serve) — Serve the beads HTTP API over loopback
- [`bd ship`](#bd-ship) — Publish a capability for cross-project dependencies
- [`bd undefer`](#bd-undefer) — Undefer one or more issues (restore to open)
- [`bd version`](#bd-version) — Print version information

## Global flags

| Flag | Short | Type | Description |
|---|---|---|---|
| `--actor` |  | string | Actor name for audit trail (default: $BEADS_ACTOR, git user.name, $USER) |
| `--cpu-profile` |  |  | Generate CPU profile for performance analysis |
| `--database` |  | string | Run against a different server database for this invocation, without changing the project's configured database (proxied-server mode only) |
| `--db` |  | string | Database path (default: auto-discover .beads/*.db). In proxied-server mode, a value that isn't an existing path is treated as a database name override (see --database) |
| `--directory` | `-C` | string | Change to this directory before running the command (like git -C) |
| `--dolt-auto-commit` |  | string | Dolt auto-commit policy (off\|on\|batch). 'on': commit after each write. 'batch': defer commits to bd dolt commit; uncommitted changes persist in the working set until then (a live batch-mode bd process also flushes on SIGTERM/SIGHUP). Applies to embedded and direct SQL-server modes; proxied-server routes are unaffected. Default: on. Override via config key dolt.auto-commit |
| `--global` |  |  | Use the global shared-server database (beads_global) |
| `--ignore-schema-skew` |  |  | Proceed despite forward schema drift (some queries may fail) |
| `--json` |  |  | Output in JSON format |
| `--mem-profile` |  | string | Write heap profile to FILE on exit (also respects BEADS_MEM_PROFILE) |
| `--no-color` |  |  | Disable color output (also: NO_COLOR=1 or CLICOLOR=0) |
| `--quiet` | `-q` |  | Suppress non-essential output (errors only) |
| `--readonly` |  |  | Read-only mode: block write operations (for worker sandboxes) |
| `--sandbox` |  |  | Sandbox mode: disables Dolt auto-push |
| `--verbose` | `-v` |  | Enable verbose/debug output |

## Commands

<a id="bd"></a>

## `bd`

```text
Issues chained together like beads. A lightweight issue tracker with first-class dependency support.
```

**Usage**

```text
bd [flags]
bd [command]
```

**Working With Issues**

- [`assign`](#bd-assign) — Assign an issue to someone
- [`children`](#bd-children) — List child beads of a parent
- [`close`](#bd-close) — Close one or more issues
- [`comment`](#bd-comment) — Add a comment to an issue
- [`comments`](#bd-comments) — View or manage comments on an issue
- [`create`](#bd-create) — Create a new issue (or batch from markdown/graph JSON)
- [`create-form`](#bd-create-form) — Create a new issue using an interactive form
- [`delete`](#bd-delete) — Delete one or more issues and clean up references
- [`edit`](#bd-edit) — Edit an issue field in $EDITOR
- [`gate`](#bd-gate) — Manage async coordination gates
- [`heartbeat`](#bd-heartbeat) — Refresh the lease on an issue you hold in_progress
- [`label`](#bd-label) — Manage issue labels
- [`link`](#bd-link) — Link two issues with a dependency
- [`list`](#bd-list) — List issues
- [`merge-slot`](#bd-merge-slot) — Manage merge-slot gates for serialized conflict resolution
- [`note`](#bd-note) — Append a note to an issue
- [`priority`](#bd-priority) — Set the priority of an issue
- [`promote`](#bd-promote) — Promote a wisp to a permanent bead
- [`provenance`](#bd-provenance) — Append-only provenance event log
- [`q`](#bd-q) — Quick capture: create issue and output only ID
- [`query`](#bd-query) — Query issues using a simple query language
- [`reclaim`](#bd-reclaim) — Revert stale-lease in_progress issues back to ready (dead-worker recovery)
- [`reopen`](#bd-reopen) — Reopen one or more closed issues
- [`search`](#bd-search) — Search issues by text query
- [`set-state`](#bd-set-state) — Set operational state (creates event + updates label)
- [`show`](#bd-show) — Show issue details
- [`state`](#bd-state) — Query the current value of a state dimension
- [`tag`](#bd-tag) — Add a label to an issue
- [`todo`](#bd-todo) — Manage TODO items (convenience wrapper for task issues)
- [`unclaim`](#bd-unclaim) — Release a claimed issue
- [`update`](#bd-update) — Update one or more issues

**Views & Reports**

- [`count`](#bd-count) — Count issues matching filters
- [`diff`](#bd-diff) — Show changes between two commits or branches
- [`find-duplicates`](#bd-find-duplicates) — Find semantically similar issues using text analysis or AI
- [`history`](#bd-history) — Show version history for an issue
- [`lint`](#bd-lint) — Check issues for missing template sections
- [`stale`](#bd-stale) — Show stale issues (not updated recently)
- [`status`](#bd-status) — Show issue database overview and statistics
- [`statuses`](#bd-statuses) — List valid issue statuses
- [`types`](#bd-types) — List valid issue types

**Dependencies & Structure**

- [`dep`](#bd-dep) — Manage dependencies
- [`duplicate`](#bd-duplicate) — Mark an issue as a duplicate of another
- [`duplicates`](#bd-duplicates) — Find and optionally merge duplicate issues
- [`epic`](#bd-epic) — Epic management commands
- [`graph`](#bd-graph) — Display issue dependency graph
- [`supersede`](#bd-supersede) — Mark an issue as superseded by a newer one
- [`swarm`](#bd-swarm) — Swarm management for structured epics

**Sync & Data**

- [`backup`](#bd-backup) — Back up your beads database
- [`branch`](#bd-branch) — List or create branches
- [`conflicts`](#bd-conflicts) — Inspect and resolve live merge conflicts
- [`export`](#bd-export) — Export issues to JSONL format
- [`federation`](#bd-federation) — Manage peer-to-peer federation with other workspaces
- [`import`](#bd-import) — Import issues from a JSONL file or stdin into the database
- [`restore`](#bd-restore) — Restore the pre-compaction content of a compacted issue
- [`sync`](#bd-sync) — Pull, check for conflicts, repair is_blocked, and push (the federation loop)
- [`vc`](#bd-vc) — Version control operations

**Setup & Configuration**

- [`bootstrap`](#bd-bootstrap) — Non-destructive database setup for fresh clones and recovery
- [`config`](#bd-config) — Manage configuration settings
- [`context`](#bd-context) — Show effective backend identity and repository context
- [`dolt`](#bd-dolt) — Configure Dolt database settings
- [`forget`](#bd-forget) — Remove a persistent memory
- [`hooks`](#bd-hooks) — Manage git hooks for beads integration
- [`human`](#bd-human) — Show essential commands for human users
- [`info`](#bd-info) — Show database information
- [`init`](#bd-init) — Initialize bd in the current directory
- [`kv`](#bd-kv) — Key-value store commands
- [`memories`](#bd-memories) — List or search persistent memories
- [`migrate-personal`](#bd-migrate-personal) — Move personal planning issues from the project database to your planning repo
- [`onboard`](#bd-onboard) — Display minimal snippet for agent instructions file
- [`prime`](#bd-prime) — Output AI-optimized workflow context
- [`quickstart`](#bd-quickstart) — Quick start guide for bd
- [`recall`](#bd-recall) — Retrieve a specific memory
- [`remember`](#bd-remember) — Store a persistent memory
- [`setup`](#bd-setup) — Setup integration with AI editors
- [`where`](#bd-where) — Show active beads location

**Maintenance**

- [`batch`](#bd-batch) — Run multiple write operations in a single database transaction
- [`compact`](#bd-compact) — Squash old Dolt commits to reduce history size
- [`doctor`](#bd-doctor) — Check and fix beads installation health (start here)
- [`events`](#bd-events) — Read and manage the durable events journal
- [`flatten`](#bd-flatten) — Squash all Dolt history into a single commit
- [`gc`](#bd-gc) — Garbage collect: decay old issues, compact Dolt commits, run Dolt GC
- [`migrate`](#bd-migrate) — Database migration commands
- [`ping`](#bd-ping) — Check database connectivity
- [`preflight`](#bd-preflight) — Show PR readiness checklist
- [`prune`](#bd-prune) — Delete old closed beads to reclaim space and shrink exports
- [`purge`](#bd-purge) — Delete closed ephemeral beads to reclaim space
- [`rename-prefix`](#bd-rename-prefix) — Rename the issue prefix for all issues in the database
- [`rules`](#bd-rules) — Audit and compact Claude rules
- [`sql`](#bd-sql) — Execute raw SQL against the beads database
- [`upgrade`](#bd-upgrade) — Check and manage bd version upgrades
- [`worktree`](#bd-worktree) — Manage git worktrees for parallel development

**Integrations & Advanced**

- [`admin`](#bd-admin) — Administrative commands for database maintenance
- [`jira`](#bd-jira) — Jira integration commands
- [`linear`](#bd-linear) — Linear integration commands
- [`repo`](#bd-repo) — Manage multiple repository configuration

**Additional Commands**

- [`ado`](#bd-ado) — Azure DevOps integration commands
- [`audit`](#bd-audit) — Record and label agent interactions (append-only JSONL)
- [`blocked`](#bd-blocked) — Show blocked issues
- [`completion`](#bd-completion) — Generate the autocompletion script for the specified shell
- [`cook`](#bd-cook) — Compile a formula into a proto (ephemeral by default)
- [`defer`](#bd-defer) — Defer one or more issues for later
- [`formula`](#bd-formula) — Manage workflow formulas
- [`github`](#bd-github) — GitHub integration commands
- [`gitlab`](#bd-gitlab) — GitLab integration commands
- `help` — Help about any command
- [`init-safety`](#bd-init-safety) — Explain bd init flag semantics and the destroy-token format
- [`mail`](#bd-mail) — Delegate to mail provider (e.g., gt mail)
- [`metrics`](#bd-metrics) — Show or change anonymous usage-metrics settings
- [`mol`](#bd-mol) — Molecule commands (work templates)
- [`notion`](#bd-notion) — Notion integration commands
- [`orphans`](#bd-orphans) — Identify orphaned issues (referenced in commits but still open)
- [`ready`](#bd-ready) — Show ready work (open, no active blockers)
- [`rename`](#bd-rename) — Rename an issue ID
- [`schema`](#bd-schema) — Print the JSON Schema for bd's --json / export output
- [`serve`](#bd-serve) — Serve the beads HTTP API over loopback
- [`ship`](#bd-ship) — Publish a capability for cross-project dependencies
- [`undefer`](#bd-undefer) — Undefer one or more issues (restore to open)
- [`version`](#bd-version) — Print version information

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for bd |
| `--version` | `-V` |  | Print version information Use "bd [command] --help" for more information about a command. |

<a id="bd-assign"></a>

## `bd assign`

```text
Assign an issue to someone.

Shorthand for 'bd update <id> --assignee <name>'.

Refuses to overwrite another actor's live in_progress claim without --force
(bd-98s5c); issues assigned to a claim.pools alias are exempt, matching
--claim. For a holder-aware transfer prefer
'bd update <id> --if-assignee <holder> -a <new>'.
```

**Usage**

```text
bd assign <id> <name> [flags]
```

**Examples**

```text
  bd assign bd-123 alice
  bd assign bd-123 ""      # unassign
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force` |  |  | Allow overwriting another actor's live in_progress claim (use only for abandoned claims — crashed agent, expired lease; prefer bd reclaim) |
| `--help` | `-h` |  | help for assign |

<a id="bd-children"></a>

## `bd children`

```text
List all beads that are children of the specified parent bead.

This is a convenience alias for 'bd list --parent <id> --status all'.
Unlike plain 'bd list', children includes closed issues by default,
since the primary use case is inspecting all work under a parent.
```

**Usage**

```text
bd children <parent-id> [flags]
```

**Examples**

```text
  bd children hq-abc123        # List all children of hq-abc123
  bd children hq-abc123 --json # List children in JSON format
  bd children hq-abc123 --pretty # Show children in tree format
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for children |
| `--pretty` |  |  | Show children in tree format |

<a id="bd-close"></a>

## `bd close`

```text
Close one or more issues.

If no issue ID is provided, closes the last touched issue (from most recent
create, update, show, or close operation). This fallback only applies in
interactive sessions (stdin is a terminal); in scripts and agent sessions a
missing ID is an error, so a command built from an empty variable cannot
silently close an unrelated issue. Set BD_LAST_TOUCHED_FALLBACK=1 to allow
the fallback anywhere, or =0 to disable it entirely.

When closing multiple issues, provide one --reason for all IDs or repeat
--reason once per ID. Reasons map positionally: the first --reason applies
to the first ID, the second --reason to the second ID, regardless of where
the flags appear in the command line.
```

**Usage**

```text
bd close [id...] [flags]
```

**Aliases:** `close, done`

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--claim-next` |  |  | Automatically claim the next highest priority available issue |
| `--continue` |  |  | Auto-advance to next step in molecule |
| `--force` | `-f` |  | Force close pinned issues or unsatisfied gates |
| `--help` | `-h` |  | help for close |
| `--no-auto` |  |  | With --continue, show next step but don't claim it |
| `--reason` | `-r` | string | Reason for closing |
| `--reason-file` |  | string | Read close reason from file (use - for stdin) |
| `--session` |  | string | Claude Code session ID (or set CLAUDE_SESSION_ID env var) |
| `--suggest-next` |  |  | Show newly unblocked issues after closing |

<a id="bd-comment"></a>

## `bd comment`

```text
Add a comment to an issue.

Shorthand for 'bd comments add <id> "text"'.
```

**Usage**

```text
bd comment <id> [text...] [flags]
```

**Examples**

```text
  bd comment bd-123 "Working on this now"
  bd comment bd-123 Working on this now
  echo "comment from pipe" | bd comment bd-123 --stdin
  bd comment bd-123 --file notes.txt

Note: "comment" (singular) only adds a comment — it has no "list" subcommand.
To list comments on an issue, use the plural form: bd comments <id>
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--file` |  | string | Read comment text from file |
| `--help` | `-h` |  | help for comment |
| `--stdin` |  |  | Read comment text from stdin |

<a id="bd-comments"></a>

## `bd comments`

```text
View or manage comments on an issue.
```

**Usage**

```text
bd comments [issue-id] [flags]
bd comments [command]
```

**Available Commands**

- [`add`](#bd-comments-add) — Add a comment to an issue
- [`list`](#bd-comments-list) — Invalid — use bd comments <issue-id> to list comments

**Examples**

```text
  # List all comments on an issue (issue id is required — there is no "comments list")
  bd comments bd-123

  # List comments in JSON format
  bd comments bd-123 --json

  # Add a comment
  bd comments add bd-123 "This is a comment"

  # Add a comment from a file
  bd comments add bd-123 -f notes.txt
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for comments |
| `--local-time` |  |  | Show timestamps in local time instead of UTC |

<a id="bd-comments-add"></a>

### `bd comments add`

```text
Add a comment to an issue.
```

**Usage**

```text
bd comments add [issue-id] [text...] [flags]
```

**Examples**

```text
  # Add a comment
  bd comments add bd-123 "Working on this now"

  # Add a comment from a file
  bd comments add bd-123 -f notes.txt
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--author` | `-a` | string | Add author to comment |
| `--file` | `-f` | string | Read comment text from file |
| `--help` | `-h` |  | help for add |

<a id="bd-comments-list"></a>

### `bd comments list`

```text
Invalid — use bd comments <issue-id> to list comments
```

**Usage**

```text
bd comments list [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-create"></a>

## `bd create`

```text
Create a new issue (or batch from markdown/graph JSON)
```

**Usage**

```text
bd create [title] [flags]
```

**Aliases:** `create, new`

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--acceptance` |  | string | Acceptance criteria |
| `--allow-empty-description` |  |  | Allow empty description input from stdin or file |
| `--append-notes` |  | string | Append to existing notes (with newline separator) |
| `--assignee` | `-a` | string | Assignee |
| `--body-file` |  | string | Read description from file (use - for stdin) |
| `--context` |  | string | Additional context for the issue |
| `--defer` |  | string | Defer until date (issue hidden from bd ready until then). Same formats as --due |
| `--deps` |  | strings | Dependencies as 'type:id' or bare 'id'. Bare 'id', 'depends-on:id', and 'blocked-by:id' all make THIS issue depend on id; 'blocks:id' reverses direction (id depends on this issue). E.g. 'blocked-by:bd-20,discovered-from:bd-15' |
| `--description` | `-d` | string | Issue description |
| `--design` |  | string | Design notes |
| `--design-file` |  | string | Read design from file (use - for stdin) |
| `--dry-run` |  |  | Preview what would be created without actually creating |
| `--due` |  | string | Due date/time. Formats: +6h, +1d, +2w, tomorrow, next monday, 2025-01-15 |
| `--ephemeral` |  |  | Create as ephemeral (short-lived, subject to TTL compaction) |
| `--estimate` | `-e` | int | Time estimate in minutes (e.g., 60 for 1 hour) |
| `--event-actor` |  | string | Entity URI who caused this event (requires --type=event) |
| `--event-category` |  | string | Event category (e.g., patrol.muted, agent.started) (requires --type=event) |
| `--event-payload` |  | string | Event-specific JSON data (requires --type=event) |
| `--event-target` |  | string | Entity URI or bead ID affected (requires --type=event) |
| `--external-ref` |  | string | External reference (e.g., 'gh-9', 'jira-ABC', Linear URL) |
| `--file` | `-f` | string | Create multiple issues from markdown file |
| `--force` |  |  | Force creation even if prefix doesn't match database prefix |
| `--graph` |  | string | Create a graph of issues with dependencies from JSON plan file |
| `--help` | `-h` |  | help for create |
| `--id` |  | string | Explicit issue ID (e.g., 'bd-42' for partitioning) |
| `--labels` | `-l` | strings | Labels (comma-separated) |
| `--metadata` |  | string | Set custom metadata (JSON string or @file.json to read from file) |
| `--mol-type` |  | string | Molecule type: swarm (multi-agent), patrol (recurring ops), work (default) |
| `--no-history` |  |  | Skip Dolt commit history without making GC-eligible (for permanent agent beads) |
| `--no-inherit-labels` |  |  | Don't inherit labels from parent issue |
| `--notes` |  | string | Additional notes |
| `--parent` |  | string | Parent issue ID for hierarchical child (e.g., 'bd-a3f8e9') |
| `--priority` | `-p` | string | Priority (0-4 or P0-P4, 0=highest) (default "2") |
| `--repo` |  | string | Target repository for issue (overrides auto-routing) |
| `--silent` |  |  | Output only the issue ID (for scripting) |
| `--skills` |  | string | Required skills for this issue |
| `--spec-id` |  | string | Link to specification document |
| `--status` | `-s` | string | Initial status |
| `--stdin` |  |  | Read description from stdin (alias for --body-file -) |
| `--storage-class` |  | string | Storage class: versioned, unversioned, or ephemeral (default: storage-class.<type> config, else versioned) |
| `--title` |  | string | Issue title (alternative to positional argument) |
| `--type` | `-t` | string | Issue type (bug\|feature\|task\|epic\|chore\|decision\|spike\|story\|milestone); custom types require types.custom config; aliases: enhancement/feat→feature, dec/adr→decision (default "task") |
| `--validate` |  |  | Validate description contains required sections for issue type |
| `--waits-for` |  | string | Spawner issue ID to wait for (creates waits-for dependency for fanout gate) |
| `--waits-for-gate` |  | string | Gate type: all-children (wait for all) or any-children (wait for first) (default "all-children") |
| `--wisp-type` |  | string | Wisp type for TTL-based compaction: heartbeat, ping, patrol, gc_report, recovery, error, escalation |

<a id="bd-create-form"></a>

## `bd create-form`

```text
Create a new issue using an interactive terminal form.

This command provides a user-friendly form interface for creating issues,
with fields for title, description, type, priority, labels, and more.

Use --parent to create a sub-issue under an existing parent issue.
The child will get an auto-generated hierarchical ID (e.g., parent-id.1).

The form uses keyboard navigation:
  - Tab/Shift+Tab: Move between fields
  - Enter: Submit the form (on the last field or submit button)
  - Ctrl+C: Cancel and exit
  - Arrow keys: Navigate within select fields
```

**Usage**

```text
bd create-form [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for create-form |
| `--parent` |  | string | Parent issue ID for creating a hierarchical child (e.g., 'bd-a3f8e9') |

<a id="bd-delete"></a>

## `bd delete`

```text
Delete one or more issues and clean up all references to them.

This command will:
1. Remove all dependency links (any type, both directions) involving the issues
2. Update text references to "[deleted:ID]" in directly connected issues
3. Permanently delete the issues from the database

This is a destructive operation that cannot be undone. Use with caution.

BATCH DELETION:


Delete multiple issues at once:
  bd delete bd-1 bd-2 bd-3 --force

Delete from file (one ID per line):
  bd delete --from-file deletions.txt --force

Preview before deleting:
  bd delete --from-file deletions.txt --dry-run

DEPENDENCY HANDLING (the same on a local database and against a team server):
Default: Fails if any issue has dependents not in deletion set
  bd delete bd-1 bd-2

Cascade: Recursively delete all dependents
  bd delete bd-1 --cascade --force

Force: Delete and orphan dependents
  bd delete bd-1 --force
```

**Usage**

```text
bd delete <issue-id> [issue-id...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--cascade` |  |  | Recursively delete all dependent issues |
| `--dry-run` |  |  | Preview what would be deleted without making changes |
| `--force` | `-f` |  | Actually delete (without this flag, shows preview) |
| `--from-file` |  | string | Read issue IDs from file (one per line) |
| `--help` | `-h` |  | help for delete |

<a id="bd-edit"></a>

## `bd edit`

```text
Edit an issue field using your configured $EDITOR.

By default, edits the description. Use flags to edit other fields.
```

**Usage**

```text
bd edit [id] [flags]
```

**Examples**

```text
  bd edit bd-42                    # Edit description
  bd edit bd-42 --title            # Edit title
  bd edit bd-42 --design           # Edit design notes
  bd edit bd-42 --notes            # Edit notes
  bd edit bd-42 --acceptance       # Edit acceptance criteria
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--acceptance` |  |  | Edit the acceptance criteria |
| `--description` |  |  | Edit the description (default) |
| `--design` |  |  | Edit the design notes |
| `--help` | `-h` |  | help for edit |
| `--notes` |  |  | Edit the notes |
| `--title` |  |  | Edit the title |

<a id="bd-gate"></a>

## `bd gate`

```text
Gates are async wait conditions that block workflow steps.

Gates are created automatically when a formula step has a gate field.
They must be closed (manually or via watchers) for the blocked step to proceed.

Gate types:
  human   - Requires manual bd close (Phase 1)
  timer   - Expires after timeout (Phase 2)
  gh:run  - Waits for GitHub workflow (Phase 3)
  gh:pr   - Waits for PR merge (Phase 3)
  bead    - Waits for another bead to close (Phase 4)

For bead gates, await_id is a bead ID in this rig's database (e.g., "bd-abc123").
The historical cross-rig form <rig>:<bead-id> can no longer be evaluated
(multi-rig routing removed) and stays pending until resolved manually.
```

**Usage**

```text
bd gate [command]
```

**Available Commands**

- [`add-waiter`](#bd-gate-add-waiter) — Add a waiter to a gate
- [`check`](#bd-gate-check) — Evaluate gates and close resolved ones
- [`create`](#bd-gate-create) — Create a gate that blocks an issue
- [`discover`](#bd-gate-discover) — Discover await_id for gh:run gates
- [`list`](#bd-gate-list) — List gate issues
- [`resolve`](#bd-gate-resolve) — Manually resolve (close) a gate
- [`show`](#bd-gate-show) — Show a gate issue

**Examples**

```text
  bd gate list           # Show all open gates
  bd gate list --all     # Show all gates including closed
  bd gate check          # Evaluate all open gates
  bd gate check --type=bead  # Evaluate only bead gates
  bd gate resolve <id>   # Close a gate manually
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for gate |

<a id="bd-gate-add-waiter"></a>

### `bd gate add-waiter`

```text
Register an agent as a waiter on a gate bead.

When the gate closes, the waiter will receive a wake notification via 'bd gate wake'.
The waiter is typically the worker's address (e.g., "my-project/workers/agent-1").

This is used by 'bd done --phase-complete' to register for gate wake notifications.
```

**Usage**

```text
bd gate add-waiter <gate-id> <waiter> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for add-waiter |

<a id="bd-gate-check"></a>

### `bd gate check`

```text
Evaluate gate conditions and automatically close resolved gates.

By default, checks all open gates. Use --type to filter by gate type.

Gate types:
  gh       - Check all GitHub gates (gh:run and gh:pr)
  gh:run   - Check GitHub Actions workflow runs
  gh:pr    - Check pull request merge status
  timer    - Check timer gates (auto-expire based on timeout)
  bead     - Check cross-rig bead gates
  all      - Check all gate types

GitHub gates use the 'gh' CLI to query status:
  - gh:run checks 'gh run view <id> --json status,conclusion'
  - gh:pr checks 'gh pr view <id> --json state,title'

A gate is resolved when:
  - gh:run: status=completed AND conclusion=success
  - gh:pr: state=MERGED
  - timer: current time > created_at + timeout
  - bead: target bead status=closed

A gate is escalated when:
  - gh:run: status=completed AND conclusion in (failure, canceled)
  - gh:pr: state=CLOSED
```

**Usage**

```text
bd gate check [flags]
```

**Examples**

```text
  bd gate check              # Check all gates
  bd gate check --type=gh    # Check only GitHub gates
  bd gate check --type=gh:run # Check only workflow run gates
  bd gate check --type=timer # Check only timer gates
  bd gate check --type=bead  # Check only cross-rig bead gates
  bd gate check --dry-run    # Show what would happen without changes
  bd gate check --escalate   # Escalate expired/failed gates
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would happen without making changes |
| `--escalate` | `-e` |  | Escalate failed/expired gates |
| `--help` | `-h` |  | help for check |
| `--limit` | `-l` | int | Limit results (default 100) (default 100) |
| `--type` | `-t` | string | Gate type to check (gh, gh:run, gh:pr, timer, bead, all) |

<a id="bd-gate-create"></a>

### `bd gate create`

```text
Create an ad-hoc gate issue that blocks another issue until resolved.

The blocked issue will not appear in 'bd ready' until the gate is resolved
via 'bd gate resolve'.

Gate types:
  human   - Requires manual 'bd gate resolve' (default)
  timer   - Auto-resolves after --timeout duration
  gh:run  - Waits for GitHub Actions workflow
  gh:pr   - Waits for PR merge
```

**Usage**

```text
bd gate create [flags]
```

**Examples**

```text
  bd gate create --blocks bd-abc
  bd gate create --type=human --blocks bd-abc --reason="Need design review"
  bd gate create --type=timer --blocks bd-abc --timeout=2h
  bd gate create --type=gh:pr --blocks bd-abc --await-id=42
  bd gate create --blocks bd-abc --title="Gate: awaiting owner sign-off"
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--await-id` |  | string | Condition identifier (run ID, PR number, etc.) |
| `--blocks` |  | string | Issue ID to block (required) |
| `--help` | `-h` |  | help for create |
| `--reason` | `-r` | string | Reason for the gate |
| `--timeout` |  | string | Timeout duration (e.g., 2h, 30m) |
| `--title` |  | string | Custom gate title (default: "Gate: <type>") |
| `--type` | `-t` | string | Gate type (human, timer, gh:run, gh:pr) (default "human") |

<a id="bd-gate-discover"></a>

### `bd gate discover`

```text
Discovers GitHub workflow run IDs for gates awaiting CI/CD completion.

This command finds open gates with await_type="gh:run" that don't have an await_id,
queries recent GitHub workflow runs, and matches them using heuristics:
  - Branch name matching
  - Commit SHA matching
  - Time proximity (runs within 5 minutes of gate creation)

Once matched, the gate's await_id is updated with the GitHub run ID, enabling
subsequent polling to check the run's status.

A gate whose metadata.repo targets another repository is only matched
against runs queried from that repository, never against the current
repository's runs of a same-named workflow.
```

**Usage**

```text
bd gate discover [flags]
```

**Examples**

```text
  bd gate discover           # Auto-discover run IDs for all matching gates
  bd gate discover --dry-run # Preview what would be matched (no updates)
  bd gate discover --branch main --limit 10  # Only match runs on 'main' branch
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--branch` | `-b` | string | Filter runs by branch (default: current branch) |
| `--dry-run` | `-n` |  | Preview mode: show matches without updating |
| `--help` | `-h` |  | help for discover |
| `--limit` | `-l` | int | Max runs to query from GitHub (default 10) |
| `--max-age` | `-a` | duration | Max age for gate/run matching (default 30m0s) |

<a id="bd-gate-list"></a>

### `bd gate list`

```text
List gate issues.

With no argument, lists all gate issues in the current beads database.
With an [issue-id] argument, lists ONLY the gates that block that issue
(its own dependency gates) — not every gate in the database.

By default, shows only open gates. Use --all to include closed gates.
```

**Usage**

```text
bd gate list [issue-id] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` | `-a` |  | Show all gates including closed |
| `--help` | `-h` |  | help for list |
| `--limit` | `-n` | int | Limit results (default 50) (default 50) |

<a id="bd-gate-resolve"></a>

### `bd gate resolve`

```text
Close a gate issue to unblock the step waiting on it.

This is equivalent to 'bd close <gate-id>' but with a more explicit name.
Use --reason to provide context for why the gate was resolved.
```

**Usage**

```text
bd gate resolve <gate-id> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for resolve |
| `--reason` | `-r` | string | Reason for resolving the gate |

<a id="bd-gate-show"></a>

### `bd gate show`

```text
Display details of a gate issue including its waiters.

This is similar to 'bd show' but validates that the issue is a gate.
```

**Usage**

```text
bd gate show <gate-id> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for show |

<a id="bd-heartbeat"></a>

## `bd heartbeat`

```text
Refresh the lease on an issue you currently hold in_progress.

A claim carries a lease that expires after a TTL. A worker keeps its claim alive
by heartbeating faster than the TTL; once it stops (because it died), the lease
goes stale and 'bd reclaim' reverts the issue to ready so another worker can pick
it up. Heartbeat pushes lease_expires_at forward and stamps heartbeat_at = now.

Only the current owner may heartbeat. If the lease has already been reclaimed or
the issue closed, heartbeat fails so the worker learns to stop.

Leases live in an ephemeral, node-local table: heartbeats write no Dolt commit
and no history, so any cadence comfortably below the TTL is fine. Leases are
only enforceable on the node that granted them; cross-machine claim visibility
rides the issue's status and assignee, which do commit.
```

**Usage**

```text
bd heartbeat <id> [flags]
```

**Aliases:** `heartbeat, hb`

**Examples**

```text
  bd heartbeat bd-123
  bd hb bd-123
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for heartbeat |

<a id="bd-label"></a>

## `bd label`

```text
Manage issue labels
```

**Usage**

```text
bd label [command]
```

**Available Commands**

- [`add`](#bd-label-add) — Add one or more labels to one or more issues
- [`list`](#bd-label-list) — List labels for an issue
- [`list-all`](#bd-label-list-all) — List all unique labels in the database
- [`propagate`](#bd-label-propagate) — Propagate a label from a parent issue to all its children
- [`remove`](#bd-label-remove) — Remove one or more labels from one or more issues

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for label |

<a id="bd-label-add"></a>

### `bd label add`

```text
Add labels to issues. Issue IDs come first; the final argument is the label. Pass multiple labels comma-separated: bd label add bd-123 label1,label2
```

**Usage**

```text
bd label add [issue-id...] [label[,label...]] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for add |

<a id="bd-label-list"></a>

### `bd label list`

```text
List labels for an issue
```

**Usage**

```text
bd label list [issue-id] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-label-list-all"></a>

### `bd label list-all`

```text
List all unique labels in the database
```

**Usage**

```text
bd label list-all [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list-all |

<a id="bd-label-propagate"></a>

### `bd label propagate`

```text
Push a label from a parent down to all direct children that don't already have it. Useful for applying branch: labels across an epic's subtasks.
```

**Usage**

```text
bd label propagate [parent-id] [label] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for propagate |

<a id="bd-label-remove"></a>

### `bd label remove`

```text
Remove labels from issues. Issue IDs come first; the final argument is the label. Pass multiple labels comma-separated: bd label remove bd-123 label1,label2
```

**Usage**

```text
bd label remove [issue-id...] [label[,label...]] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for remove |

<a id="bd-link"></a>

## `bd link`

```text
Link two issues with a dependency.

Shorthand for 'bd dep add <id1> <id2>'. By default creates a "blocks"
dependency (id2 blocks id1). Use --type to specify a different relationship.
```

**Usage**

```text
bd link <id1> <id2> [flags]
```

**Examples**

```text
  bd link bd-123 bd-456                    # bd-456 blocks bd-123
  bd link bd-123 bd-456 --type related     # bd-123 related to bd-456
  bd link bd-123 bd-456 --type parent-child
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for link |
| `--type` | `-t` | string | Dependency type (blocks\|tracks\|related\|parent-child\|discovered-from) (default "blocks") |

<a id="bd-list"></a>

## `bd list`

```text
List issues
```

**Usage**

```text
bd list [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` |  |  | Show all issues including closed (overrides default filter) |
| `--assignee` | `-a` | string | Filter by assignee |
| `--brief` |  |  | Omit the free-form text (description, design, acceptance criteria, notes, payload, waiters) from each row. Filters that read those fields, such as --desc-contains, still select on them. An omitted field is indistinguishable from an empty one in --json; fetch a whole issue with bd show. |
| `--closed-after` |  | string | Filter issues closed after date (YYYY-MM-DD or RFC3339) |
| `--closed-before` |  | string | Filter issues closed before date (YYYY-MM-DD or RFC3339) |
| `--created-after` |  | string | Filter issues created after date (YYYY-MM-DD or RFC3339) |
| `--created-before` |  | string | Filter issues created before date (YYYY-MM-DD or RFC3339) |
| `--defer-after` |  | string | Filter issues deferred after date (supports relative: +6h, tomorrow) |
| `--defer-before` |  | string | Filter issues deferred before date (supports relative: +6h, tomorrow) |
| `--deferred` |  |  | Show only issues with defer_until set |
| `--deps` |  | string[="scheduling"] | Annotate tree with dependency edges and order siblings by them: 'scheduling' (bare --deps) or 'all' |
| `--desc-contains` |  | string | Filter by description substring (case-insensitive) |
| `--due-after` |  | string | Filter issues due after date (supports relative: +6h, tomorrow) |
| `--due-before` |  | string | Filter issues due before date (supports relative: +6h, tomorrow) |
| `--empty-description` |  |  | Filter issues with empty or missing description |
| `--exclude-label` |  | strings | Exclude issues that have ANY of these labels |
| `--exclude-type` |  | strings | Exclude issue types from results (comma-separated or repeatable, e.g., --exclude-type=convoy,epic) |
| `--external-contains` |  | string | Filter by external ref substring (case-insensitive) |
| `--external-ref` |  | string | Filter by exact external_ref value |
| `--flat` |  |  | Disable tree format and use legacy flat list output |
| `--format` |  | string | Output format: 'digraph' (for golang.org/x/tools/cmd/digraph), 'dot' (Graphviz), or Go template |
| `--has-metadata-key` |  | string | Filter issues that have this metadata key set |
| `--help` | `-h` |  | help for list |
| `--id` |  | string | Filter by specific issue IDs (comma-separated, e.g., bd-1,bd-5,bd-10) |
| `--include-gates` |  |  | Include gate issues in output (normally hidden) |
| `--include-infra` |  |  | Include infrastructure beads (agent/role/message) in output |
| `--include-templates` |  |  | Include template molecules in output |
| `--label` | `-l` | strings | Filter by labels (AND: must have ALL). Can combine with --label-any |
| `--label-any` |  | strings | Filter by labels (OR: must have AT LEAST ONE). Can combine with --label |
| `--label-pattern` |  | string | Filter by label glob pattern (e.g., 'tech-*' matches tech-debt, tech-legacy) |
| `--label-regex` |  | string | Filter by label regex pattern (e.g., 'tech-(debt\|legacy)') |
| `--limit` | `-n` | int | Limit results (default 50, use 0 for unlimited) (default 50) |
| `--long` |  |  | Show detailed multi-line output for each issue |
| `--max-rows` |  | int | Hard upper bound on rows returned. Returns a non-zero exit (code 2) and an error to stderr if exceeded. 0 disables (the default). Overrides BEADS_MAX_ROWS for this invocation. Useful in CI/agent rigs that want a circuit breaker against pathological queries. Honored on both the direct and the --proxied-server route. |
| `--metadata-field` |  | stringArray | Filter by metadata field (key=value, repeatable) |
| `--mol-type` |  | string | Filter by molecule type: swarm, patrol, or work |
| `--no-assignee` |  |  | Filter issues with no assignee |
| `--no-labels` |  |  | Filter issues with no labels |
| `--no-pager` |  |  | Disable pager output |
| `--no-parent` |  |  | Exclude child issues (show only top-level issues) |
| `--no-pinned` |  |  | Exclude pinned issues |
| `--notes-contains` |  | string | Filter by notes substring (case-insensitive) |
| `--offset` |  | int | Skip the first N matching results (0-based). Only supported under --proxied-server. |
| `--overdue` |  |  | Show only issues with due_at in the past (not closed) |
| `--parent` |  | string | Filter by parent issue ID (shows children of specified issue) |
| `--pinned` |  |  | Show only pinned issues |
| `--pretty` |  |  | Display issues in a tree format with status/priority symbols |
| `--priority` | `-p` | string | Priority (0-4 or P0-P4, 0=highest) |
| `--priority-max` |  | string | Filter by maximum priority (inclusive, 0-4 or P0-P4) |
| `--priority-min` |  | string | Filter by minimum priority (inclusive, 0-4 or P0-P4) |
| `--ready` |  |  | Show only ready issues (no active blockers, same semantics as bd ready) |
| `--reverse` | `-r` |  | Reverse sort order |
| `--skip-labels` |  |  | Skip label hydration. The labels field in output will be empty regardless of actual labels. Use only when the caller does not depend on label data. Cannot combine with --label, --label-any, --label-pattern, --label-regex, --exclude-label, or --no-labels. |
| `--sort` |  | string | Sort by field: priority, created, updated, closed, status, id, title, type, assignee |
| `--spec` |  | string | Filter by spec_id prefix |
| `--status` | `-s` | string | Filter by stored status (open, in_progress, blocked, deferred, closed). Comma-separated for multiple: --status open,in_progress. Note: repeating -s/--status silently overwrites the previous value — always use the comma-separated form for multi-status filters. |
| `--title` |  | string | Filter by title text (case-insensitive substring match) |
| `--title-contains` |  | string | Filter by title substring (case-insensitive) |
| `--tree` |  |  | Hierarchical tree format (default: true; use --flat to disable) (default true) |
| `--type` | `-t` | string | Filter by type (bug, feature, task, epic, chore, decision, merge-request, molecule, gate, convoy). Aliases: mr→merge-request, feat→feature, mol→molecule, dec/adr→decision |
| `--updated-after` |  | string | Filter issues updated after date (YYYY-MM-DD or RFC3339) |
| `--updated-before` |  | string | Filter issues updated before date (YYYY-MM-DD or RFC3339) |
| `--watch` | `-w` |  | Watch for changes and auto-update display (implies --pretty) |
| `--wisp-type` |  | string | Filter by wisp type: heartbeat, ping, patrol, gc_report, recovery, error, escalation |

<a id="bd-merge-slot"></a>

## `bd merge-slot`

```text
Merge-slot gates serialize conflict resolution in the merge queue.

A merge slot is an exclusive access primitive: only one agent can hold it at a time.
This prevents "monkey knife fights" where multiple polecats race to resolve conflicts
and create cascading conflicts.

Each rig has one merge slot bead: <prefix>-merge-slot (labeled gt:slot).

The slot uses:
  - status=open: slot is available
  - status=in_progress: slot is held
  - metadata.holder: who currently holds the slot
  - metadata.waiters: priority-ordered queue of waiters
```

**Usage**

```text
bd merge-slot [command]
```

**Available Commands**

- [`acquire`](#bd-merge-slot-acquire) — Acquire the merge slot
- [`check`](#bd-merge-slot-check) — Check merge slot availability
- [`create`](#bd-merge-slot-create) — Create a merge slot bead for the current rig
- [`release`](#bd-merge-slot-release) — Release the merge slot

**Examples**

```text
  bd merge-slot create              # Create merge slot for current rig
  bd merge-slot check               # Check if slot is available
  bd merge-slot acquire             # Try to acquire the slot
  bd merge-slot release             # Release the slot
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for merge-slot |

<a id="bd-merge-slot-acquire"></a>

### `bd merge-slot acquire`

```text
Attempt to acquire the merge slot for exclusive access.

If the slot is available (status=open), it will be acquired:
  - status set to in_progress
  - holder set to the requester

If the slot is held (status=in_progress), the command fails unless
--wait is passed, which adds the requester to the waiters queue.

Use --holder to specify who is acquiring (default: BEADS_ACTOR env var).
```

**Usage**

```text
bd merge-slot acquire [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for acquire |
| `--holder` |  | string | Who is acquiring the slot (default: BEADS_ACTOR) |
| `--wait` |  |  | Add to waiters list if slot is held |

<a id="bd-merge-slot-check"></a>

### `bd merge-slot check`

```text
Check if the merge slot is available or held.

Returns:
  - available: slot can be acquired
  - held by <holder>: slot is currently held
  - not found: no merge slot exists for this rig
```

**Usage**

```text
bd merge-slot check [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for check |

<a id="bd-merge-slot-create"></a>

### `bd merge-slot create`

```text
Create a merge slot bead for serialized conflict resolution.

The slot ID is automatically generated based on the beads prefix (e.g., gt-merge-slot).
The slot is created with status=open (available).
```

**Usage**

```text
bd merge-slot create [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for create |

<a id="bd-merge-slot-release"></a>

### `bd merge-slot release`

```text
Release the merge slot after conflict resolution is complete.

Sets status back to open and clears the holder field.
If there are waiters, the highest-priority waiter should then acquire.
```

**Usage**

```text
bd merge-slot release [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for release |
| `--holder` |  | string | Who is releasing the slot (for verification) |

<a id="bd-note"></a>

## `bd note`

```text
Append a note to an issue's notes field.

Shorthand for 'bd update <id> --append-notes "text"'.
```

**Usage**

```text
bd note <id> [text...] [flags]
```

**Examples**

```text
  bd note gt-abc "Fixed the flaky test"
  bd note gt-abc Fixed the flaky test
  echo "note from pipe" | bd note gt-abc --stdin
  bd note gt-abc --file notes.txt

Note: "note" has NO subcommands — it only appends.
To read notes on an issue, use: bd show <id>
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--file` |  | string | Read note text from file |
| `--help` | `-h` |  | help for note |
| `--stdin` |  |  | Read note text from stdin |

<a id="bd-priority"></a>

## `bd priority`

```text
Set the priority of an issue.

Shorthand for 'bd update <id> --priority <n>'.

Priority levels:
  0 - Critical (security, data loss, broken builds)
  1 - High (major features, important bugs)
  2 - Medium (default)
  3 - Low (polish, optimization)
  4 - Backlog (future ideas)
```

**Usage**

```text
bd priority <id> <n> [flags]
```

**Examples**

```text
  bd priority bd-123 0    # Critical
  bd priority bd-123 2    # Medium
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for priority |

<a id="bd-promote"></a>

## `bd promote`

```text
Promote a wisp (ephemeral issue) to a permanent bead.

This copies the issue from the wisps table (dolt_ignored) to the permanent
issues table (Dolt-versioned), preserving labels, dependencies, events, and
comments. The original ID is preserved so all links keep working.

A comment is added recording the promotion and optional reason.
```

**Usage**

```text
bd promote <wisp-id> [flags]
```

**Examples**

```text
  bd promote bd-wisp-abc123
  bd promote bd-wisp-abc123 --reason "Worth tracking long-term"
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for promote |
| `--reason` | `-r` | string | Reason for promotion |

<a id="bd-provenance"></a>

## `bd provenance`

```text
Record and read provenance events: typed bindings from an issue to an
opaque external artifact (a git SHA, PR, work-id, transcript, or branch).

The log is append-only — there is no update or delete. bd never interprets the
actor or ref; only kind and ref-kind are structurally validated. Recording is
idempotent on a deterministic id, so a producer firing twice is harmless.
```

**Usage**

```text
bd provenance [command]
```

**Available Commands**

- [`by-ref`](#bd-provenance-by-ref) — List provenance events bound to a ref
- [`log`](#bd-provenance-log) — List provenance events for an issue
- [`record`](#bd-provenance-record) — Record a provenance event (idempotent)

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for provenance |

<a id="bd-provenance-by-ref"></a>

### `bd provenance by-ref`

```text
List provenance events bound to a ref
```

**Usage**

```text
bd provenance by-ref <ref> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for by-ref |

<a id="bd-provenance-log"></a>

### `bd provenance log`

```text
List provenance events for an issue
```

**Usage**

```text
bd provenance log <issue-id> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for log |
| `--kind` |  | string | filter by kind (optional) |

<a id="bd-provenance-record"></a>

### `bd provenance record`

```text
Record a provenance event. The event is appended idempotently: a
deterministic id is computed from source:issue:kind:(ref or --at), so re-running
the same record is a no-op.

An event recorded without --ref requires --at so the id is caller-owned.
```

**Usage**

```text
bd provenance record --issue <id> --kind <k> --source <s> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--actor` |  | string | opaque actor identifier (optional) |
| `--at` |  | string | event-time as RFC3339 (required for ref-less kinds) |
| `--help` | `-h` |  | help for record |
| `--issue` |  | string | issue id (required) |
| `--kind` |  | string | event kind: cut\|claim\|suspend\|resume\|handoff\|commit\|land\|used (required) |
| `--payload` |  | string | opaque payload, e.g. JSON (optional) |
| `--ref` |  | string | opaque external reference, e.g. a SHA or PR url (optional) |
| `--ref-kind` |  | string | ref kind: git-sha\|pr\|work-id\|transcript\|branch (optional) |
| `--source` |  | string | producer of the event, e.g. git-hook, orchestrator (required) |

Local definitions override the global flags `--actor` for this command.

<a id="bd-q"></a>

## `bd q`

```text
Quick capture creates an issue and outputs only the issue ID.
Designed for scripting and AI agent integration.

Example:
  bd q "Fix login bug"           # Outputs: bd-a1b2
  ISSUE=$(bd q "New feature")    # Capture ID in variable
  bd q "Task" | xargs bd show    # Pipe to other commands
  bd q "Subtask" --parent=bd-a1b2  # Hierarchical child (outputs: bd-a1b2.1)
```

**Usage**

```text
bd q [title] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for q |
| `--labels` | `-l` | strings | Labels |
| `--parent` |  | string | Parent issue ID for hierarchical child (e.g., 'bd-a3f8e9') |
| `--priority` | `-p` | string | Priority (0-4 or P0-P4) (default "2") |
| `--type` | `-t` | string | Issue type (default "task") |

<a id="bd-query"></a>

## `bd query`

```text
Query issues using a simple query language that supports compound filters,
boolean operators, and date-relative expressions.

The query language enables complex filtering that would otherwise require
multiple flags or piping through jq.

Syntax:
  field=value       Equality comparison
  field!=value      Inequality comparison
  field>value       Greater than
  field>=value      Greater than or equal
  field<value       Less than
  field<=value      Less than or equal

Boolean operators (case-insensitive):
  expr AND expr     Both conditions must match
  expr OR expr      Either condition can match
  NOT expr          Negates the condition
  (expr)            Grouping with parentheses

Supported fields:
  status            Stored status (open, in_progress, blocked, deferred, closed). Note: dependency-blocked issues stay "open"; use 'bd blocked' to find them
  priority          Priority level (0-4)
  type              Issue type (bug, feature, task, epic, chore, decision)
  assignee          Assigned user (use "none" for unassigned)
  owner             Issue owner
  label             Issue label (use "none" for unlabeled)
  title             Search in title (contains)
  description       Search in description (contains, "none" for empty)
  notes             Search in notes (contains)
  created           Creation date/time
  updated           Last update date/time
  started           Date/time issue first transitioned to in_progress
  closed            Close date/time
  id                Issue ID (supports wildcards: bd-*)
  spec              Spec ID (supports wildcards)
  pinned            Boolean (true/false)
  ephemeral         Boolean (true/false)
  template          Boolean (true/false)
  parent            Parent issue ID
  mol_type          Molecule type (swarm, patrol, work)

Date values:
  Relative durations: 7d (7 days ago), 24h (24 hours ago), 2w (2 weeks ago)
  Absolute dates: 2025-01-15, 2025-01-15T10:00:00Z
  Natural language: tomorrow, "next monday", "in 3 days"
```

**Usage**

```text
bd query [expression] [flags]
```

**Examples**

```text
  bd query "status=open AND priority>1"
  bd query "status=open AND priority<=2 AND updated>7d"
  bd query "(status=open OR status=blocked) AND priority<2"
  bd query "type=bug AND label=urgent"
  bd query "NOT status=closed"
  bd query "assignee=none AND type=task"
  bd query "created>30d AND status!=closed"
  bd query "label=frontend OR label=backend"
  bd query "title=authentication AND priority=0"
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` | `-a` |  | Include closed issues (default: exclude closed) |
| `--help` | `-h` |  | help for query |
| `--limit` | `-n` | int | Limit results (default: 50, 0 = unlimited) (default 50) |
| `--long` |  |  | Show detailed multi-line output for each issue |
| `--offset` |  | int | Skip the first N matching results (0-based). Only supported under --proxied-server. |
| `--parse-only` |  |  | Only parse the query and show the AST (for debugging) |
| `--reverse` | `-r` |  | Reverse sort order |
| `--sort` |  | string | Sort by field: priority, created, updated, closed, status, id, title, type, assignee |

<a id="bd-reclaim"></a>

## `bd reclaim`

```text
Revert in_progress issues whose lease has gone stale back to ready.

When a worker claims an issue it takes a lease that expires after a TTL, kept
alive by 'bd heartbeat'. A worker that dies stops heartbeating, so its lease
expires and its issue would otherwise stay in_progress forever. reclaim is the
reaper: it finds in_progress issues whose lease expired more than --older-than
ago, clears the assignee, and sets them back to open so another worker can
claim them. The previous owner's stale lease is recorded as a recovery event.

--older-than is a grace window past lease expiry: only leases that expired at
least this long ago are reclaimed, so a worker briefly paused (GC, clock skew)
is not robbed of live work. Run it from a supervisor on a timer with a window
of roughly 2× the claim TTL.

By default reclaim covers every stale lease THIS replica granted. The scope
filters below narrow it further, using the same label surface claiming is
scoped by (--label / --label-any / --exclude-label), plus --assignee and --id.
Filters AND-combine and never widen the set: a reclaimed lease must still be
stale.

Replicas and leases (federated deployments)
-------------------------------------------
A lease is only meaningful on the replica that granted it. Every other
replica's view of the holder's liveness is stale by up to one sync interval,
so a reaper elsewhere can revert a unit that is very much alive over there.
reclaim therefore records the granting replica on each lease and SKIPS a lease
another replica granted, summarizing what it declined on stderr (one line per
run; 'bd -v' expands it to the first 20 leases individually). Reap it where it
was granted; use --any-replica only when that replica is permanently gone (or
when this node was renamed and its own old leases now look foreign — an
ordinary heartbeat keeps a lease alive but does not re-home it to the node
heartbeating it). Prefer the narrow form '--any-replica --id <id>': bare
--any-replica reverts EVERY foreign stale lease, live peers included.

Two invariants the guard cannot enforce for you:
  grace window > sync interval, and lease TTL > sync interval.

A TTL or grace shorter than the cadence at which replicas exchange state is
meaningless across the bridge — the remote view is a full interval old by
construction. Raise the TTL/grace above the sync interval, never the reverse.
The guard is opt-in: set BEADS_NODE_ID, or run 'bd config set node_id <name>'
(which writes the per-machine ~/.config/bd/config.yaml — never commit a node_id
to the git-tracked .beads/config.yaml, or every clone reads the same name and
the guard goes armed-but-inert). One id per STORE, not per host: machines that
are clients of the same dolt sql-server are ONE replica and must share one value
or leave it unset. There is no hostname fallback — the hostname names the client
process's machine, not the store — so an unnamed deployment keeps the old,
unguarded behavior instead of stranding its own work.
```

**Usage**

```text
bd reclaim [flags]
```

**Examples**

```text
  bd reclaim                       # default grace window (2× the lease TTL)
  bd reclaim --older-than 10m      # reclaim leases expired >10m ago
  bd reclaim --older-than 0s       # reclaim every currently-expired lease
  bd reclaim --label lane-a        # only this machine's claim partition
  bd reclaim --label-any lane-a,lane-b --exclude-label pinned
  bd reclaim --assignee zelda --assignee epona   # only these workers' leases
  bd reclaim --id wy-abc --id wy-def             # exactly these issues
  bd reclaim --any-replica         # also reap leases granted by a departed replica
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--any-replica` |  |  | Also reclaim leases granted by ANOTHER replica (unsafe unless that replica is gone; see 'Replicas and leases') |
| `--assignee` | `-a` | strings | Only reclaim leases held by these assignees (repeatable) |
| `--exclude-label` |  | strings | Never reclaim issues carrying ANY of these labels |
| `--help` | `-h` |  | help for reclaim |
| `--id` |  | strings | Only reclaim these issue IDs (repeatable) |
| `--label` | `-l` | strings | Only reclaim issues with ALL these labels (AND). Can combine with --label-any |
| `--label-any` |  | strings | Only reclaim issues with AT LEAST ONE of these labels (OR). Can combine with --label |
| `--older-than` |  | duration | Only reclaim leases that expired at least this long ago (grace window) (default 10m0s) |

<a id="bd-reopen"></a>

## `bd reopen`

```text
Reopen closed issues by setting status to 'open' and clearing the closed_at timestamp.
This is more explicit than 'bd update --status open' and emits a Reopened event.
```

**Usage**

```text
bd reopen [id...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for reopen |
| `--reason` | `-r` | string | Reason for reopening |

<a id="bd-search"></a>

## `bd search`

```text
Search issues across title and ID (all statuses, including closed).

ID-like queries (e.g., "bd-123", "hq-319") use fast exact/prefix matching.
Text queries search titles. Use --desc-contains for description search.
Use --status open (etc.) to narrow; closed issues are included by default
so "was this already filed/fixed?" cannot silently answer no. Matches
beyond --limit are dropped status-blind, so when hunting live work in a
large DB, narrow with --status open or raise --limit.
```

**Usage**

```text
bd search [query] [flags]
```

**Examples**

```text
  bd search "authentication bug"
  bd search "login" --status open
  bd search "database" --label backend --limit 10
  bd search --query "performance" --assignee alice
  bd search "bd-5q" # Search by partial ID (fast prefix match)
  bd search "security" --priority-min 0 --priority-max 2
  bd search "bug" --created-after 2025-01-01
  bd search "refactor" --status open  # Only open issues
  bd search "bug" --sort priority
  bd search "task" --sort created --reverse
  bd search "api" --desc-contains "endpoint"
  bd search "cleanup" --no-assignee --no-labels
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--assignee` | `-a` | string | Filter by assignee |
| `--closed-after` |  | string | Filter issues closed after date (YYYY-MM-DD or RFC3339) |
| `--closed-before` |  | string | Filter issues closed before date (YYYY-MM-DD or RFC3339) |
| `--created-after` |  | string | Filter issues created after date (YYYY-MM-DD or RFC3339) |
| `--created-before` |  | string | Filter issues created before date (YYYY-MM-DD or RFC3339) |
| `--desc-contains` |  | string | Filter by description substring (case-insensitive) |
| `--empty-description` |  |  | Filter issues with empty or missing description |
| `--external-contains` |  | string | Filter by external ref substring (case-insensitive) |
| `--has-metadata-key` |  | string | Filter issues that have this metadata key set |
| `--help` | `-h` |  | help for search |
| `--label` | `-l` | strings | Filter by labels (AND: must have ALL) |
| `--label-any` |  | strings | Filter by labels (OR: must have AT LEAST ONE) |
| `--limit` | `-n` | int | Limit results (default: 50) (default 50) |
| `--long` |  |  | Show detailed multi-line output for each issue |
| `--metadata-field` |  | stringArray | Filter by metadata field (key=value, repeatable) |
| `--no-assignee` |  |  | Filter issues with no assignee |
| `--no-labels` |  |  | Filter issues with no labels |
| `--notes-contains` |  | string | Filter by notes substring (case-insensitive) |
| `--priority-max` |  | string | Filter by maximum priority (inclusive, 0-4 or P0-P4) |
| `--priority-min` |  | string | Filter by minimum priority (inclusive, 0-4 or P0-P4) |
| `--query` |  | string | Search query (alternative to positional argument) |
| `--reverse` | `-r` |  | Reverse sort order |
| `--sort` |  | string | Sort by field: priority, created, updated, closed, status, id, title, type, assignee |
| `--status` | `-s` | string | Filter by stored status (comma-separated for OR; open, in_progress, blocked, deferred, closed, all). Default searches all statuses including closed. Note: dependency-blocked issues use 'bd blocked' |
| `--type` | `-t` | string | Filter by type (bug, feature, task, epic, chore, decision, merge-request, molecule, gate) |
| `--updated-after` |  | string | Filter issues updated after date (YYYY-MM-DD or RFC3339) |
| `--updated-before` |  | string | Filter issues updated before date (YYYY-MM-DD or RFC3339) |

<a id="bd-set-state"></a>

## `bd set-state`

```text
Atomically set operational state on an issue.

This command:
1. Creates an event bead recording the state change (source of truth)
2. Removes any existing label for the dimension
3. Adds the new dimension:value label (fast lookup cache)

State labels follow the convention <dimension>:<value>, for example:
  patrol:active, patrol:muted
  mode:normal, mode:degraded
  health:healthy, health:failing
```

**Usage**

```text
bd set-state <issue-id> <dimension>=<value> [flags]
```

**Examples**

```text
  bd set-state agent-abc patrol=muted --reason "Investigating stuck worker"
  bd set-state agent-abc mode=degraded --reason "High error rate detected"
  bd set-state agent-abc health=healthy

The --reason flag provides context for the event bead (recommended).
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for set-state |
| `--reason` |  | string | Reason for the state change (recorded in event) |

<a id="bd-show"></a>

## `bd show`

```text
Show issue details
```

**Usage**

```text
bd show [id...] [--id=<id>...] [--current] [flags]
```

**Aliases:** `show, view`

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--as-of` |  | string | Show issue as it existed at a specific commit hash or branch (requires Dolt) |
| `--brief-deps` |  |  | Reduce each dependency to its identity fields in JSON output (--json only; drops description, design, notes and acceptance criteria) |
| `--children` |  |  | Show only the children of this issue |
| `--current` |  |  | Show the currently active issue (in-progress, hooked, or last touched) |
| `--help` | `-h` |  | help for show |
| `--id` |  | stringArray | Issue ID (use for IDs that look like flags, e.g., --id=gt--xyz) |
| `--include-comments` |  |  | Stream full comment bodies in JSON output (--json only; may be slow on issues with many comments) |
| `--include-dependents` |  |  | Stream full dependent issues in JSON output (--json only; may be slow on hub beads) |
| `--local-time` |  |  | Show timestamps in local time instead of UTC |
| `--long` |  |  | Show all available fields (extended metadata, agent identity, gate fields, etc.) |
| `--refs` |  |  | Show issues that reference this issue (reverse lookup) |
| `--short` |  |  | Show compact one-line output per issue |
| `--thread` |  |  | Show full conversation thread (for messages) |
| `--watch` | `-w` |  | Watch for changes and auto-refresh display |

<a id="bd-state"></a>

## `bd state`

```text
Query the current value of a state dimension from an issue's labels.

State labels follow the convention <dimension>:<value>, for example:
  patrol:active
  mode:degraded
  health:healthy

This command extracts the value for a given dimension.
```

**Usage**

```text
bd state <issue-id> <dimension> [flags]
bd state [command]
```

**Available Commands**

- [`list`](#bd-state-list) — List all state dimensions on an issue

**Examples**

```text
  bd state witness-abc patrol     # Output: active
  bd state witness-abc mode       # Output: normal
  bd state witness-abc health     # Output: healthy
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for state |

<a id="bd-state-list"></a>

### `bd state list`

```text
List all state labels (dimension:value format) on an issue.

This filters labels to only show those following the state convention.

Example:
  bd state list witness-abc
  # Output:
  #   patrol: active
  #   mode: normal
  #   health: healthy
```

**Usage**

```text
bd state list <issue-id> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-tag"></a>

## `bd tag`

```text
Add a label to an issue.

Shorthand for 'bd update <id> --add-label <label>'.
```

**Usage**

```text
bd tag <id> <label> [flags]
```

**Examples**

```text
  bd tag bd-123 bug
  bd tag bd-123 needs-review
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for tag |

<a id="bd-todo"></a>

## `bd todo`

```text
Manage TODO items as lightweight task issues.

TODOs are regular task-type issues with convenient shortcuts:
  bd todo add "Title"    -> bd create "Title" -t task -p 2
  bd todo                -> bd list --type task --status open
  bd todo done <id>      -> bd close <id>

TODOs can be promoted to full issues by changing type or priority:
  bd update todo-123 --type bug --priority 0
```

**Usage**

```text
bd todo [flags]
bd todo [command]
```

**Available Commands**

- [`add`](#bd-todo-add) — Add a new TODO item
- [`done`](#bd-todo-done) — Mark TODO(s) as done
- [`list`](#bd-todo-list) — List TODO items

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for todo |

<a id="bd-todo-add"></a>

### `bd todo add`

```text
Add a new TODO item
```

**Usage**

```text
bd todo add <title> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--description` | `-d` | string | Description |
| `--help` | `-h` |  | help for add |
| `--priority` | `-p` | int | Priority (0-4, default 2) (default 2) |

<a id="bd-todo-done"></a>

### `bd todo done`

```text
Mark TODO(s) as done
```

**Usage**

```text
bd todo done <id> [<id>...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for done |
| `--reason` |  | string | Reason for closing (default: Completed) |

<a id="bd-todo-list"></a>

### `bd todo list`

```text
List TODO items
```

**Usage**

```text
bd todo list [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` |  |  | Show all TODOs including completed |
| `--help` | `-h` |  | help for list |

<a id="bd-unclaim"></a>

## `bd unclaim`

```text
Release a claimed issue by clearing the assignee and resetting status to 'open'.

Use this when an agent crashes mid-work or you need to abandon a claimed task.
The issue becomes available for re-claiming by other agents.

Only the current assignee can release its own claim. Releasing another
actor's claim requires --force and should be coordinated with the holder
first — their claim may be live even if the issue looks idle. Prefer
letting lease expiry reclaim genuinely abandoned work.

With --if-assignee, the release is an atomic compare-and-swap (the inverse of
claim): the issue is released only while it is still assigned to the given
assignee. If the holder differs — e.g. the claim was already reclaimed and
re-taken by another worker — nothing is changed and bd exits nonzero with an
error naming the current holder. Use this from supervisors that must return a
specific worker's issue without ever clobbering someone else's live claim.
--if-assignee requires a non-empty assignee and cannot be combined with --force
(they encode contradictory intent).

Exit status: 0 when every issue was released; 1 when any release failed
(including an --if-assignee mismatch).
```

**Usage**

```text
bd unclaim [id...] [flags]
```

**Examples**

```text
  bd unclaim bd-123
  bd unclaim bd-123 --reason "Agent crashed"
  bd unclaim bd-123 bd-456
  bd unclaim bd-123 --if-assignee worker-7   # only if still held by worker-7
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force` |  |  | Release the claim even if held by a different actor (admin/reaper use) |
| `--help` | `-h` |  | help for unclaim |
| `--if-assignee` |  | string | Only release if still assigned to this assignee (atomic compare-and-swap; exits nonzero without changing the issue when the holder differs) |
| `--reason` | `-r` | string | Reason for unclaiming |

<a id="bd-update"></a>

## `bd update`

```text
Update one or more issues.

If no issue ID is provided, updates the last touched issue (from most recent
create, update, show, or close operation). This fallback only applies in
interactive sessions (stdin is a terminal); in scripts and agent sessions a
missing ID is an error, so a command built from an empty variable cannot
silently mutate an unrelated issue. Set BD_LAST_TOUCHED_FALLBACK=1 to allow
the fallback anywhere, or =0 to disable it entirely.

Updates are applied per issue ID, not atomically across IDs: when some IDs
fail, the remaining issues are still updated, every failed ID is reported on
stderr, and the command exits nonzero.

Exit codes: 1 for general failures; 13 when every failure is a stale
--if-assignee/--if-status guard (the precondition no longer held, nothing was
written — another actor won the race, so retrying the same guard is
pointless).
```

**Usage**

```text
bd update [id...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--acceptance` |  | string | Acceptance criteria |
| `--add-label` |  | strings | Add labels (repeatable) |
| `--allow-empty-description` |  |  | Allow empty description replacement when reading from stdin or file |
| `--append-notes` |  | string | Append to existing notes (with newline separator) |
| `--assignee` | `-a` | string | Assignee |
| `--await-id` |  | string | Set gate await_id (e.g., GitHub run ID for gh:run gates) |
| `--body-file` |  | string | Read description from file (use - for stdin) |
| `--claim` |  |  | Atomically claim the issue (sets assignee to you, status to in_progress; idempotent if already claimed by you; issues assigned to a pool alias listed in the claim.pools config are claimable too) |
| `--defer` |  | string | Defer until date (empty to clear). Issue hidden from bd ready until then, then auto-wakes to open |
| `--description` | `-d` | string | Issue description |
| `--design` |  | string | Design notes |
| `--design-file` |  | string | Read design from file (use - for stdin) |
| `--due` |  | string | Due date/time (empty to clear). Formats: +6h, +1d, +2w, tomorrow, next monday, 2025-01-15 |
| `--ephemeral` |  |  | Mark issue as ephemeral (wisp) - not exported to JSONL |
| `--estimate` | `-e` | int | Time estimate in minutes (e.g., 60 for 1 hour) |
| `--external-ref` |  | string | External reference (e.g., 'gh-9', 'jira-ABC', Linear URL) |
| `--force` |  |  | Override two refusals: let -a/--assignee overwrite another actor's live in_progress claim (use only for abandoned claims — crashed agent, expired lease; prefer bd reclaim), and let -s/--status move the issue into closed (or a configured done status) despite open children or a live blocker (same as bd close --force) |
| `--help` | `-h` |  | help for update |
| `--history` |  |  | Clear no-history flag (re-enable Dolt commit history) |
| `--if-assignee` |  | string | Apply the update only if the current assignee equals this value (--if-assignee '' requires unassigned); a mismatch writes nothing and exits 13 (vs 1 for other failures). Requires a field update; cannot combine with --claim |
| `--if-status` |  | string | Apply the update only if the current status equals this value; a mismatch writes nothing and exits 13 (vs 1 for other failures). Requires a field update; cannot combine with --claim |
| `--metadata` |  | string | Set custom metadata (JSON string or @file.json to read from file) |
| `--no-history` |  |  | Mark issue as no-history (skip Dolt commits, not GC-eligible) |
| `--notes` |  | string | Additional notes (replaces existing notes; use --append-notes to append) |
| `--parent` |  | string | New parent issue ID (reparents the issue, use empty string to remove parent) |
| `--persistent` |  |  | Mark issue as persistent (promote wisp to regular issue) |
| `--priority` | `-p` | string | Priority (0-4 or P0-P4, 0=highest) |
| `--remove-label` |  | strings | Remove labels (repeatable) |
| `--session` |  | string | Claude Code session ID for status=closed (or set CLAUDE_SESSION_ID env var) |
| `--set-labels` |  | strings | Set labels, replacing all existing (repeatable) |
| `--set-metadata` |  | stringArray | Set metadata key=value (repeatable, e.g., --set-metadata team=platform) |
| `--spec-id` |  | string | Link to specification document |
| `--status` | `-s` | string | New status |
| `--stdin` |  |  | Read description from stdin (alias for --body-file -) |
| `--title` |  | string | New title |
| `--type` | `-t` | string | New type (bug\|feature\|task\|epic\|chore\|decision\|spike\|story\|milestone); custom types require types.custom config; aliases: enhancement/feat→feature, dec/adr→decision |
| `--unset-metadata` |  | stringArray | Remove metadata key (repeatable, e.g., --unset-metadata team) |

<a id="bd-count"></a>

## `bd count`

```text
Count issues matching the specified filters.

By default, returns the total count of issues matching the filters.
Use --by-* flags to group counts by different attributes.
```

**Usage**

```text
bd count [flags]
```

**Examples**

```text
  bd count                          # Count all issues
  bd count --status open            # Count open issues
  bd count --by-status              # Group count by status
  bd count --by-priority            # Group count by priority
  bd count --by-type                # Group count by issue type
  bd count --by-assignee            # Group count by assignee
  bd count --by-label               # Group count by label
  bd count --assignee alice --by-status  # Count alice's issues by status
  bd count --include-infra          # Count issues + wisps tier (matches 'bd list --include-infra --all' cardinality)
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--assignee` | `-a` | string | Filter by assignee |
| `--by-assignee` |  |  | Group count by assignee |
| `--by-label` |  |  | Group count by label |
| `--by-priority` |  |  | Group count by priority |
| `--by-status` |  |  | Group count by status |
| `--by-type` |  |  | Group count by issue type |
| `--closed-after` |  | string | Filter issues closed after date (YYYY-MM-DD or RFC3339) |
| `--closed-before` |  | string | Filter issues closed before date (YYYY-MM-DD or RFC3339) |
| `--created-after` |  | string | Filter issues created after date (YYYY-MM-DD or RFC3339) |
| `--created-before` |  | string | Filter issues created before date (YYYY-MM-DD or RFC3339) |
| `--desc-contains` |  | string | Filter by description substring |
| `--empty-description` |  |  | Filter issues with empty description |
| `--help` | `-h` |  | help for count |
| `--id` |  | string | Filter by specific issue IDs (comma-separated) |
| `--include-infra` |  |  | Include infrastructure beads and the wisps tier (matches 'bd list --include-infra --all' cardinality) |
| `--label` | `-l` | strings | Filter by labels (AND: must have ALL) |
| `--label-any` |  | strings | Filter by labels (OR: must have AT LEAST ONE) |
| `--no-assignee` |  |  | Filter issues with no assignee |
| `--no-labels` |  |  | Filter issues with no labels |
| `--notes-contains` |  | string | Filter by notes substring |
| `--priority` | `-p` | int | Filter by priority (0-4: 0=critical, 1=high, 2=medium, 3=low, 4=backlog) |
| `--priority-max` |  | int | Filter by maximum priority (inclusive) |
| `--priority-min` |  | int | Filter by minimum priority (inclusive) |
| `--status` | `-s` | string | Filter by stored status (open, in_progress, blocked, deferred, closed). Note: dependency-blocked issues use 'bd blocked' |
| `--title` |  | string | Filter by title text (case-insensitive substring match) |
| `--title-contains` |  | string | Filter by title substring |
| `--type` | `-t` | string | Filter by type (bug, feature, task, epic, chore, decision, merge-request, molecule, gate) |
| `--updated-after` |  | string | Filter issues updated after date (YYYY-MM-DD or RFC3339) |
| `--updated-before` |  | string | Filter issues updated before date (YYYY-MM-DD or RFC3339) |

<a id="bd-diff"></a>

## `bd diff`

```text
Show the differences in issues between two commits or branches.

The refs can be:
- Commit hashes (e.g., abc123def)
- Branch names (e.g., main, feature-branch)
- Special refs like HEAD, HEAD~1
```

**Usage**

```text
bd diff <from-ref> <to-ref> [flags]
```

**Examples**

```text
  bd diff main feature-branch   # Compare main to feature branch
  bd diff HEAD~5 HEAD           # Show changes in last 5 commits
  bd diff abc123 def456         # Compare two specific commits
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for diff |

<a id="bd-find-duplicates"></a>

## `bd find-duplicates`

```text
Find issues that are semantically similar but not exact duplicates.

Unlike 'bd duplicates' which finds exact content matches, find-duplicates
uses text similarity or AI to find issues that discuss the same topic
with different wording.

Approaches:
  mechanical  Token-based text similarity (default, no API key needed)
  ai          LLM-based semantic comparison (requires ANTHROPIC_API_KEY, MINIMAX_API_KEY, or ai.api_key)

The mechanical approach tokenizes titles and descriptions, then computes
Jaccard similarity between all issue pairs. It's fast and free but may
miss semantically similar issues with very different wording.

The AI approach sends candidate pairs to an Anthropic-compatible model for semantic comparison.
It first uses mechanical pre-filtering to reduce the number of API calls,
then asks the LLM to judge whether the remaining pairs are true duplicates.
```

**Usage**

```text
bd find-duplicates [flags]
```

**Aliases:** `find-duplicates, find-dups`

**Examples**

```text
  bd find-duplicates                       # Mechanical similarity (default)
  bd find-duplicates --threshold 0.4       # Lower threshold = more results
  bd find-duplicates --method ai           # Use AI for semantic comparison
  bd find-duplicates --status open         # Only check open issues
  bd find-duplicates --limit 20            # Show top 20 pairs
  bd find-duplicates --json                # JSON output
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for find-duplicates |
| `--limit` | `-n` | int | Maximum number of pairs to show (default 50) |
| `--max-rows` |  | int | Hard upper bound on rows fetched from storage. Returns a non-zero exit (code 2) and an error to stderr if exceeded. 0 disables (the default). Overrides BEADS_MAX_ROWS for this invocation. Useful in CI/agent rigs that want a circuit breaker against pathological queries. Not supported under --proxied-server: an explicit --max-rows or BEADS_MAX_ROWS cap errors out rather than silently going unenforced. |
| `--method` |  | string | Detection method: mechanical, ai (default "mechanical") |
| `--model` |  | string | AI model to use (only with --method ai; default from config ai.model) |
| `--status` | `-s` | string | Filter by status (default: non-closed) |
| `--threshold` |  | float | Similarity threshold (0.0-1.0, lower = more results) (default 0.5) |

<a id="bd-history"></a>

## `bd history`

```text
Show the complete version history of an issue, including all commits
where the issue was modified.
```

**Usage**

```text
bd history <id> [flags]
```

**Examples**

```text
  bd history bd-123           # Show all history for issue bd-123
  bd history bd-123 --limit 5 # Show last 5 changes
  bd history bd-123 --events  # Show database audit events
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--events` |  |  | Show database audit events instead of commit snapshots |
| `--help` | `-h` |  | help for history |
| `--limit` |  | int | Limit number of history entries (0 = all) |

<a id="bd-lint"></a>

## `bd lint`

```text
Check issues for missing recommended sections based on issue type.

By default, lints all open issues. Specify issue IDs to lint specific issues.

Section requirements by type:
  bug:      Steps to Reproduce, Acceptance Criteria
  task:     Acceptance Criteria
  feature:  Acceptance Criteria
  epic:     Success Criteria (or Acceptance Criteria)
  chore:    (none)

Additional per-type sections can be required via config; they are ADDITIVE
to the built-ins above (built-in requirements are never relaxed):

  bd config set lint.sections.epic "Standards scorecard, Cost"
```

**Usage**

```text
bd lint [issue-id...] [flags]
```

**Examples**

```text
  bd lint                    # Lint all open issues
  bd lint bd-abc             # Lint specific issue
  bd lint bd-abc bd-def      # Lint multiple issues
  bd lint --type bug         # Lint only bugs
  bd lint --status all       # Lint all issues (including closed)
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for lint |
| `--status` | `-s` | string | Filter by status (default: open, use 'all' for all) |
| `--type` | `-t` | string | Filter by issue type (bug, task, feature, epic, decision, spike, story, chore, milestone) |

<a id="bd-stale"></a>

## `bd stale`

```text
Show issues that haven't been updated recently and may need attention.

This helps identify:
- In-progress issues with no recent activity (may be abandoned)
- Open issues that have been forgotten
- Issues that might be outdated or no longer relevant
```

**Usage**

```text
bd stale [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--days` | `-d` | int | Issues not updated in this many days (default 30) |
| `--exclude-label` |  | strings | Exclude issues that have ANY of these labels |
| `--help` | `-h` |  | help for stale |
| `--label` | `-l` | strings | Filter by labels (AND: must have ALL). Can combine with --label-any |
| `--label-any` |  | strings | Filter by labels (OR: must have AT LEAST ONE). Can combine with --label |
| `--limit` | `-n` | int | Maximum issues to show (default 50) |
| `--status` | `-s` | string | Filter by status (open\|in_progress\|blocked\|deferred) |

<a id="bd-status"></a>

## `bd status`

```text
Show a quick snapshot of the issue database state and statistics.

This command provides a summary of issue counts by state (open, in_progress,
blocked, closed), ready work, extended statistics (pinned issues,
average lead time), and recent activity over the last 24 hours from git history.

Similar to how 'git status' shows working tree state, 'bd status' gives you
a quick overview of your issue database without needing multiple queries.

Use cases:
  - Quick project health check
  - Onboarding for new contributors
  - Integration with shell prompts or CI/CD
  - Daily standup reference
  - Fast CI status checks that don't need blocked-count accuracy
```

**Usage**

```text
bd status [flags]
```

**Aliases:** `status, stats`

**Examples**

```text
  bd status                    # Show summary with activity
  bd status --no-activity      # Skip git activity (faster)
  bd status --no-blocked       # Skip slow blocked-count scan (faster)
  bd stats --no-blocked --json # JSON output without blocked count
  bd status --json             # JSON format output
  bd status --assigned         # Show issues assigned to current user
  bd stats                     # Alias for bd status
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` |  |  | Show all issues (default behavior) |
| `--assigned` |  |  | Show issues assigned to current user |
| `--help` | `-h` |  | help for status |
| `--no-activity` |  |  | Skip git activity summary (faster) |
| `--no-blocked` |  |  | Skip blocked-count computation (faster on large rigs; not supported in proxied-server mode) |

<a id="bd-statuses"></a>

## `bd statuses`

```text
List all valid issue statuses and their categories.

Built-in statuses (open, in_progress, blocked, etc.) are always valid.
Additional statuses can be configured via status.custom:

  bd config set status.custom "in_review:active,qa_testing:wip,on_hold:frozen"

Categories control behavior:
  active  — appears in 'bd ready' and default 'bd list'
  wip     — excluded from 'bd ready', visible in default 'bd list'
  done    — excluded from 'bd ready' and default 'bd list'
  frozen  — excluded from 'bd ready' and default 'bd list'

Statuses without a category (legacy format) are valid but excluded from 'bd ready'.
```

**Usage**

```text
bd statuses [flags]
```

**Examples**

```text
  bd statuses            # List all statuses with icons and categories
  bd statuses --json     # Output as JSON
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for statuses |

<a id="bd-types"></a>

## `bd types`

```text
List all valid issue types that can be used with bd create --type.

Core work types (bug, task, feature, chore, epic, decision, spike, story, milestone) are always valid.
Additional types require configuration via types.custom in .beads/config.yaml.
```

**Usage**

```text
bd types [flags]
```

**Examples**

```text
  bd types              # List all types with descriptions
  bd types --sections   # List required sections for each type
  bd types --json       # Output as JSON
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for types |
| `--sections` |  |  | Show required sections for each issue type |

<a id="bd-dep"></a>

## `bd dep`

```text
Manage dependencies between issues.

When called with an issue ID and --blocks flag, creates a blocking dependency:
  bd dep <blocker-id> --blocks <blocked-id>

This is equivalent to:
  bd dep add <blocked-id> <blocker-id>
```

**Usage**

```text
bd dep [issue-id] [flags]
bd dep [command]
```

**Available Commands**

- [`add`](#bd-dep-add) — Add a dependency
- [`cycles`](#bd-dep-cycles) — Detect dependency cycles
- [`list`](#bd-dep-list) — List dependencies or dependents of one or more issues
- [`relate`](#bd-dep-relate) — Create a bidirectional relates_to link between issues
- [`remove`](#bd-dep-remove) — Remove a dependency
- [`tree`](#bd-dep-tree) — Show dependency tree
- [`unrelate`](#bd-dep-unrelate) — Remove a relates_to link between issues

**Examples**

```text
  bd dep bd-xyz --blocks bd-abc    # bd-xyz blocks bd-abc
  bd dep add bd-abc bd-xyz         # Same as above (bd-abc depends on bd-xyz)
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--blocks` | `-b` | string | Issue ID that this issue blocks (shorthand for: bd dep add <blocked> <blocker>) |
| `--help` | `-h` |  | help for dep |
| `--no-cycle-check` |  |  | Skip per-edge cycle checks for speed (bulk wiring); bulk --file adds still run one final whole-graph check before commit |

<a id="bd-dep-add"></a>

### `bd dep add`

```text
Add a dependency between two issues.

The depends-on-id can be provided as:
  - A positional argument: bd dep add issue-123 issue-456
  - A flag: bd dep add issue-123 --blocked-by issue-456
  - A flag: bd dep add issue-123 --depends-on issue-456

The --blocked-by and --depends-on flags are aliases and both mean "issue-123
depends on (is blocked by) the specified issue."

The depends-on-id can be:
  - A local issue ID (e.g., bd-xyz)
  - An external reference: external:<project>:<capability>

For bulk wiring, pass newline-delimited JSON with --file. Each line must be an
object with "from" and "to" fields, and may include "type". The aliases
"issue_id" and "depends_on_id" are also accepted. Use --file - to read stdin.

External references are stored as-is and resolved at query time using
the external_projects config. They block the issue until the capability
is "shipped" in the target project.

With no -t/--type the edge is created as type=blocks, which excludes the
dependent from bd ready. When stderr is an interactive terminal, an advisory
note says so once per command; it is silent for scripted and agent callers
(non-TTY stderr) and can be turned off with --quiet or BD_NO_DEP_TYPE_WARNING=1.
```

**Usage**

```text
bd dep add [issue-id] [depends-on-id] [flags]
```

**Examples**

```text
  bd dep add bd-42 bd-41                              # Positional args
  bd dep add bd-42 --blocked-by bd-41                 # Flag syntax (same effect)
  bd dep add bd-42 --depends-on bd-41                 # Alias (same effect)
  bd dep add gt-xyz external:beads:mol-run-assignee   # Cross-project dependency
  bd dep add bd-42 bd-41 --no-cycle-check             # Skip cycle check (bulk wiring)
  bd dep add --file deps.jsonl                        # Bulk JSONL: {"from":"bd-42","to":"bd-41"}
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--blocked-by` |  | string | Issue ID that blocks the first issue (alternative to positional arg) |
| `--depends-on` |  | string | Issue ID that the first issue depends on (alias for --blocked-by) |
| `--file` |  | string | Read dependency edges from JSONL file, or '-' for stdin |
| `--help` | `-h` |  | help for add |
| `--no-cycle-check` |  |  | Skip per-edge cycle checks for speed (bulk wiring); bulk --file adds still run one final whole-graph check before commit |
| `--type` | `-t` | string | Dependency type (blocks\|tracks\|related\|parent-child\|discovered-from\|until\|caused-by\|validates\|relates-to\|supersedes); 'blocked-by' and 'depends-on' are accepted as aliases for 'blocks' (default "blocks") |

<a id="bd-dep-cycles"></a>

### `bd dep cycles`

```text
Detect dependency cycles
```

**Usage**

```text
bd dep cycles [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for cycles |

<a id="bd-dep-list"></a>

### `bd dep list`

```text
List dependencies or dependents of one or more issues with optional type filtering.

By default shows dependencies (what issues depend on). Use --direction to control:
  - down: Show dependencies (what this issue depends on) - default
  - up:   Show dependents (what depends on this issue)

Multiple IDs can be provided for batch dep listing. With --json, the output
is a flat array of dependency records across all requested issues.

Use --type to filter by dependency type (e.g., tracks, blocks, parent-child).
```

**Usage**

```text
bd dep list [issue-id...] [flags]
```

**Examples**

```text
  bd dep list gt-abc                     # Show what gt-abc depends on
  bd dep list gt-abc gt-def              # Batch: deps for both issues
  bd dep list gt-abc --direction=up      # Show what depends on gt-abc
  bd dep list gt-abc --direction=up -t tracks  # Show what tracks gt-abc (convoy tracking)
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--direction` |  | string | Direction: 'down' (dependencies), 'up' (dependents) (default "down") |
| `--help` | `-h` |  | help for list |
| `--type` | `-t` | string | Filter by dependency type (e.g., tracks, blocks, parent-child) |

<a id="bd-dep-relate"></a>

### `bd dep relate`

```text
Create a loose 'see also' relationship between two issues.

The relates_to link is bidirectional - both issues will reference each other.
This enables knowledge graph connections without blocking or hierarchy.
```

**Usage**

```text
bd dep relate <id1> <id2> [flags]
```

**Examples**

```text
  bd relate bd-abc bd-xyz    # Link two related issues
  bd relate bd-123 bd-456    # Create see-also connection
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for relate |

<a id="bd-dep-remove"></a>

### `bd dep remove`

```text
Remove a dependency
```

**Usage**

```text
bd dep remove [issue-id] [depends-on-id] [flags]
```

**Aliases:** `remove, rm`

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for remove |

<a id="bd-dep-tree"></a>

### `bd dep tree`

```text
Show dependency tree rooted at the given issue.

By default, shows dependencies (what blocks this issue). Use --direction to control:
  - down: Show dependencies (what blocks this issue) - default
  - up:   Show dependents (what this issue blocks)
  - both: Show full graph in both directions
```

**Usage**

```text
bd dep tree [issue-id] [flags]
```

**Examples**

```text
  bd dep tree gt-0iqq                    # Show what blocks gt-0iqq
  bd dep tree gt-0iqq --direction=up     # Show what gt-0iqq blocks
  bd dep tree gt-0iqq --status=open      # Only show open issues
  bd dep tree gt-0iqq --depth=3          # Limit to 3 levels deep

A node reached by two paths is shown ONCE, under the first path that got
there, and a cycle simply ends the descent. --show-all-paths is a deprecated
no-op; use 'bd dep cycles' to find circular dependencies.

--max-rows / BEADS_MAX_ROWS caveat: the tree walk has no query filter to
thread the cap through, so the full tree is always built first and the
node count is checked afterward (post-hoc), not during the walk. The cap is
honored on the --proxied-server route too, which it was not before.
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--direction` |  | string | Tree direction: 'down' (dependencies), 'up' (dependents), or 'both' |
| `--format` |  | string | Output format: 'mermaid' for Mermaid.js flowchart |
| `--help` | `-h` |  | help for tree |
| `--max-depth` | `-d` | int | Maximum tree depth to display (safety limit) (default 50) |
| `--max-rows` |  | int | Hard upper bound on rows returned. Returns a non-zero exit (code 2) and an error to stderr if exceeded. 0 disables (the default). Overrides BEADS_MAX_ROWS for this invocation. Useful in CI/agent rigs that want a circuit breaker against pathological queries. Honored on both the direct and the --proxied-server route. |
| `--reverse` |  |  | Show dependent tree (deprecated: use --direction=up) |
| `--show-all-paths` |  |  | Deprecated no-op: accepted and ignored. A node reached by two paths is shown once, under the first. |
| `--status` |  | string | Filter to only show issues with this status (open, in_progress, blocked, deferred, closed) |

<a id="bd-dep-unrelate"></a>

### `bd dep unrelate`

```text
Remove a relates_to relationship between two issues.

Removes the link in both directions.

Example:
  bd unrelate bd-abc bd-xyz
```

**Usage**

```text
bd dep unrelate <id1> <id2> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for unrelate |

<a id="bd-duplicate"></a>

## `bd duplicate`

```text
Mark an issue as a duplicate of a canonical issue.

The duplicate issue is automatically closed with a reference to the canonical.
This is essential for large issue databases with many similar reports.
```

**Usage**

```text
bd duplicate <id> --of <canonical> [flags]
```

**Examples**

```text
  bd duplicate bd-abc --of bd-xyz    # Mark bd-abc as duplicate of bd-xyz
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for duplicate |
| `--of` |  | string | Canonical issue ID (required) |

<a id="bd-duplicates"></a>

## `bd duplicates`

```text
Find issues with identical content (title, description, design, acceptance criteria).
Groups issues by content hash and reports duplicates with suggested merge targets.

The merge target is chosen by:
1. Reference count (most referenced issue wins)
2. Lexicographically smallest ID if reference counts are equal
Only groups issues with matching status (open with open, closed with closed).

Example:
  bd duplicates                    # Show all duplicate groups
  bd duplicates --auto-merge       # Automatically merge all duplicates
  bd duplicates --dry-run          # Show what would be merged
```

**Usage**

```text
bd duplicates [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--auto-merge` |  |  | Automatically merge all duplicates |
| `--dry-run` |  |  | Show what would be merged without making changes |
| `--help` | `-h` |  | help for duplicates |

<a id="bd-epic"></a>

## `bd epic`

```text
Epic management commands
```

**Usage**

```text
bd epic [command]
```

**Available Commands**

- [`status`](#bd-epic-status) — Show epic completion status

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for epic |

<a id="bd-epic-status"></a>

### `bd epic status`

```text
Show epic completion status
```

**Usage**

```text
bd epic status [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--eligible-only` |  |  | Show only epics eligible for closure |
| `--help` | `-h` |  | help for status |

<a id="bd-graph"></a>

## `bd graph`

```text
Display a visualization of an issue's dependency graph.

For epics, shows all children and their dependencies.
For regular issues, shows the issue and its direct dependencies.

With --all, shows all open issues grouped by connected component.
With --open, filters to only open/actionable issues (compact layer format).

Display formats:
  (default)        DAG with columns and box-drawing edges (terminal-native)
  --box            ASCII boxes showing layers, more detailed
  --compact        Tree format, one line per issue, more scannable
  --dot            Graphviz DOT format (pipe to dot -Tsvg > graph.svg)
  --html           Self-contained interactive HTML with D3.js visualization
  --open           Open issues only, compact layers (LLM-friendly)

The graph shows execution order:
- Layer 0 / leftmost = no dependencies (can start immediately)
- Higher layers depend on lower layers
- Nodes in the same layer can run in parallel

Status icons: ○ open  ◐ in_progress  ● blocked  ✓ closed  ❄ deferred
```

**Usage**

```text
bd graph [issue-id] [flags]
bd graph [command]
```

**Available Commands**

- [`check`](#bd-graph-check) — Check dependency graph integrity

**Examples**

```text
  bd graph issue-id              # Terminal DAG visualization (default)
  bd graph --box issue-id        # ASCII boxes with layer grouping
  bd graph --dot issue-id | dot -Tsvg > graph.svg  # SVG via Graphviz
  bd graph --dot issue-id | dot -Tpng > graph.png  # PNG via Graphviz
  bd graph --html issue-id > graph.html  # Interactive browser view
  bd graph --all --html > all.html       # All issues, interactive
  bd graph --open issue-id       # Open issues only, layered by blocking order
  bd graph --all --open          # All open issues, compact layers

--max-rows / BEADS_MAX_ROWS caveat: the cap is checked differently per mode.
Single-issue graphs (no --all) check the connected-component node count
after the BFS traversal completes — the whole subgraph is always walked
first, then rejected if it's over cap. --all checks each status
(open/in_progress/blocked) independently, so up to 3x the cap can be loaded
in total before any individual status trips it.
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` |  |  | Show graph for all open issues |
| `--box` |  |  | ASCII boxes showing layers |
| `--compact` |  |  | Tree format, one line per issue, more scannable |
| `--dot` |  |  | Output Graphviz DOT format (pipe to: dot -Tsvg > graph.svg) |
| `--help` | `-h` |  | help for graph |
| `--html` |  |  | Output self-contained interactive HTML (redirect to file) |
| `--max-rows` |  | int | Hard upper bound on rows fetched from storage. Returns a non-zero exit (code 2) and an error to stderr if exceeded. 0 disables (the default). Overrides BEADS_MAX_ROWS for this invocation. Useful in CI/agent rigs that want a circuit breaker against pathological queries. Not supported under --proxied-server: an explicit --max-rows or BEADS_MAX_ROWS cap errors out rather than silently going unenforced. |
| `--open` |  |  | Show only open issues (filters out closed/deferred), forces compact layer format |

<a id="bd-graph-check"></a>

### `bd graph check`

```text
Check the dependency graph for cycles, orphans, and other integrity issues.

Returns exit code 0 if the graph is clean, 1 if issues are found.
```

**Usage**

```text
bd graph check [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for check |

<a id="bd-supersede"></a>

## `bd supersede`

```text
Mark an issue as superseded by a newer version.

The superseded issue is automatically closed with a reference to the replacement.
Useful for design docs, specs, and evolving artifacts.
```

**Usage**

```text
bd supersede <id> --with <new> [flags]
```

**Examples**

```text
  bd supersede bd-old --with bd-new    # Mark bd-old as superseded by bd-new
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for supersede |
| `--with` |  | string | Replacement issue ID (required) |

<a id="bd-swarm"></a>

## `bd swarm`

```text
Swarm management commands for coordinating parallel work on epics.

A swarm is a structured body of work defined by an epic and its children,
with dependencies forming a DAG (directed acyclic graph) of work.
```

**Usage**

```text
bd swarm [command]
```

**Available Commands**

- [`create`](#bd-swarm-create) — Create a swarm molecule from an epic
- [`list`](#bd-swarm-list) — List all swarm molecules
- [`status`](#bd-swarm-status) — Show current swarm status
- [`validate`](#bd-swarm-validate) — Validate epic structure for swarming

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for swarm |

<a id="bd-swarm-create"></a>

### `bd swarm create`

```text
Create a swarm molecule to orchestrate parallel work on an epic.

The swarm molecule:
- Links to the epic it orchestrates
- Has mol_type=swarm for discovery
- Specifies a coordinator (optional)
- Can be picked up by any coordinator agent

If given a single issue (not an epic), it will be auto-wrapped:
- Creates an epic with that issue as its only child
- Then creates the swarm molecule for that epic
```

**Usage**

```text
bd swarm create [epic-id] [flags]
```

**Examples**

```text
  bd swarm create bd-epic-123                          # Create swarm for epic
  bd swarm create bd-epic-123 --coordinator=observer/   # With specific coordinator
  bd swarm create bd-task-456                          # Auto-wrap single issue
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--coordinator` |  | string | Coordinator address (e.g., my-project/witness) |
| `--force` |  |  | Create new swarm even if one already exists |
| `--help` | `-h` |  | help for create |

<a id="bd-swarm-list"></a>

### `bd swarm list`

```text
List all swarm molecules with their status.

Shows each swarm molecule with:
- Progress (completed/total issues)
- Active workers
- Epic ID and title
```

**Usage**

```text
bd swarm list [flags]
```

**Examples**

```text
  bd swarm list         # List all swarms
  bd swarm list --json  # Machine-readable output
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-swarm-status"></a>

### `bd swarm status`

```text
Show the current status of a swarm, computed from beads.

Accepts either:
- An epic ID (shows status for that epic's children)
- A swarm molecule ID (follows the link to find the epic)

Displays issues grouped by state:
- Completed: Closed issues
- Active: Issues currently in_progress (with assignee)
- Ready: Open issues with all dependencies satisfied
- Blocked: Open issues waiting on dependencies

The status is COMPUTED from beads, not stored separately.
If beads changes, status changes.
```

**Usage**

```text
bd swarm status [epic-or-swarm-id] [flags]
```

**Examples**

```text
  bd swarm status gt-epic-123       # Show swarm status by epic
  bd swarm status gt-swarm-456      # Show status via swarm molecule
  bd swarm status gt-epic-123 --json  # Machine-readable output
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-swarm-validate"></a>

### `bd swarm validate`

```text
Validate an epic's structure to ensure it's ready for swarm execution.

Checks for:
- Correct dependency direction (requirement-based, not temporal)
- Orphaned issues (roots with no dependents)
- Missing dependencies (leaves that should depend on something)
- Cycles (impossible to resolve)
- Disconnected subgraphs

Reports:
- Ready fronts (waves of parallel work)
- Estimated worker-sessions
- Maximum parallelism
- Warnings for potential issues
```

**Usage**

```text
bd swarm validate [epic-id] [flags]
```

**Examples**

```text
  bd swarm validate gt-epic-123           # Validate epic structure
  bd swarm validate gt-epic-123 --verbose # Include detailed issue graph
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for validate |
| `--verbose` |  |  | Include detailed issue graph in output |

Local definitions override the global flags `--verbose` for this command.

<a id="bd-backup"></a>

## `bd backup`

```text
Back up your beads database for off-machine recovery.

This is a Dolt-native database backup. It preserves the database state,
including tables, branches, commit history, and working-set data. This is
different from 'bd export', which writes issue records to JSONL for migration
and interoperability.

Commands:
  bd backup init <path>    Set up a backup destination (filesystem or DoltHub)
  bd backup sync           Push to configured backup destination
  bd backup restore [path] Restore from a backup directory
  bd backup remove         Remove backup destination
  bd backup status         Show backup status

DoltHub is recommended for cloud backup:
  bd backup init https://doltremoteapi.dolthub.com/<user>/<repo>
  Set DOLT_REMOTE_USER and DOLT_REMOTE_PASSWORD for authentication.

Auto-backup default:
  When backup.enabled is unset, auto-backup turns ON in embedded mode if a
  git remote exists, and stays OFF in sql-server / shared-server mode. In
  server mode many bd clients share one Dolt server, and each would register
  a server-side backup remote under the same name pointing at its own local
  dir and full-sync the whole database — a self-amplifying storm. To back up
  a shared server, run 'bd backup' explicitly (or set backup.enabled=true and
  coordinate destinations). 'bd config get backup.enabled' shows the effective
  value and its source.
```

**Usage**

```text
bd backup [command]
```

**Available Commands**

- [`init`](#bd-backup-init) — Set up a Dolt backup destination
- [`remove`](#bd-backup-remove) — Remove the configured backup destination
- [`restore`](#bd-backup-restore) — Restore database from a Dolt backup
- [`status`](#bd-backup-status) — Show last backup status
- [`sync`](#bd-backup-sync) — Push database to configured Dolt backup

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for backup |

<a id="bd-backup-init"></a>

### `bd backup init`

```text
Configure a filesystem path or URL as a backup destination.

The path can be a local directory (external drive, NAS, Dropbox folder) or a
DoltHub remote URL. If the destination was previously configured, it is
updated to the new path.

Filesystem examples:
  bd backup add /mnt/usb/beads-backup
  bd backup add ~/Dropbox/beads-backup

DoltHub (recommended for cloud backup):
  bd backup add https://doltremoteapi.dolthub.com/myuser/beads-backup

After adding, run 'bd backup sync' to push your data.
```

**Usage**

```text
bd backup init <path> [flags]
```

**Aliases:** `init, add`

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for init |

<a id="bd-backup-remove"></a>

### `bd backup remove`

```text
Remove the configured backup destination.

This unregisters the backup remote from Dolt and removes the local
backup configuration. The backup data at the destination is not deleted.
```

**Usage**

```text
bd backup remove [flags]
```

**Aliases:** `remove, rm`

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for remove |

<a id="bd-backup-restore"></a>

### `bd backup restore`

```text
Restore the beads database from a Dolt-native backup.

By default, reads from .beads/backup/ (or the configured backup directory).
Optionally specify a path to a directory containing a Dolt backup.

This restores a full database backup created by 'bd backup sync' or an
equivalent Dolt backup. JSONL files produced by 'bd export' are issue exports,
not restore targets for this command.

Use --force to overwrite an existing database with the backup contents.

The database must already be initialized (run 'bd init' first if needed).
To initialize and restore in one step, use: bd init && bd backup restore
```

**Usage**

```text
bd backup restore [path] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force` |  |  | Overwrite existing database with backup contents |
| `--help` | `-h` |  | help for restore |

<a id="bd-backup-status"></a>

### `bd backup status`

```text
Show last backup status
```

**Usage**

```text
bd backup status [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-backup-sync"></a>

### `bd backup sync`

```text
Sync the current beads database to the configured Dolt backup destination.

This pushes the entire database state (all branches, full history) to the
backup location configured with 'bd backup init'.

The backup is atomic — if the sync fails, the previous backup state is preserved.

Run 'bd backup init <path>' first to configure a destination.
```

**Usage**

```text
bd backup sync [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for sync |

<a id="bd-branch"></a>

## `bd branch`

```text
List all branches or create a new branch.

This command requires the Dolt storage backend. Without arguments,
it lists all branches. With an argument, it creates a new branch.
```

**Usage**

```text
bd branch [name] [flags]
```

**Examples**

```text
  bd branch                    # List all branches
  bd branch feature-xyz        # Create a new branch named feature-xyz
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for branch |

<a id="bd-conflicts"></a>

## `bd conflicts`

```text
Inspect and resolve the merge conflicts sitting in the working set.

Conflicts appear when a pull or merge brought in changes that collide with
local ones and could not be settled automatically. These commands present them
per issue and per field, and resolve them without the raw dolt CLI.
```

**Usage**

```text
bd conflicts [command]
```

**Available Commands**

- [`list`](#bd-conflicts-list) — List tables and issues with live merge conflicts
- [`resolve`](#bd-conflicts-resolve) — Resolve merge conflicts with --ours or --theirs
- [`show`](#bd-conflicts-show) — Show conflicted rows field by field (base/ours/theirs)

**Examples**

```text
  bd conflicts list                          # which tables and issues are conflicted
  bd conflicts show                          # every conflicted row, field by field
  bd conflicts show bd-1234                  # one issue
  bd conflicts resolve bd-1234 --ours        # keep our side of one issue
  bd conflicts resolve --all --theirs        # take their side of everything
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for conflicts |

<a id="bd-conflicts-list"></a>

### `bd conflicts list`

```text
List tables and issues with live merge conflicts
```

**Usage**

```text
bd conflicts list [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-conflicts-resolve"></a>

### `bd conflicts resolve`

```text
Resolve live merge conflicts, then conclude the merge with a commit.

Named issue IDs are resolved row by row, leaving every other conflicted row
alone. --all resolves whole tables at once (dolt's own table-level
resolution). The merge is committed only once NO conflicts remain, so a
partial resolution leaves the merge open for the next pass.

Row-by-row resolution requires the row to exist on both sides: when one side
deleted it, resolve that table wholesale or edit the row directly.
```

**Usage**

```text
bd conflicts resolve [<issue-id>...] [flags]
```

**Examples**

```text
  bd conflicts resolve bd-1234 --ours              # keep our side of one issue
  bd conflicts resolve bd-1234 bd-5678 --theirs    # take their side of two
  bd conflicts resolve --all --ours                # every conflicted table
  bd conflicts resolve --all --table config --theirs
  bd conflicts resolve --conclude                  # commit an already-resolved merge
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` |  |  | Resolve whole tables instead of named issues |
| `--conclude` |  |  | Commit a merge whose conflicts are already resolved |
| `--help` | `-h` |  | help for resolve |
| `--no-commit` |  |  | Resolve without committing the merge |
| `--ours` |  |  | Keep our side |
| `--strategy` |  | string | Resolution strategy: ours\|theirs |
| `--table` |  | string | Table to resolve (default: issues) |
| `--theirs` |  |  | Take their side |

<a id="bd-conflicts-show"></a>

### `bd conflicts show`

```text
Show each conflicted row with its fields side by side.

Only fields where our side and their side disagree are shown; --all-fields
shows every column. Without an issue ID, every conflicted row of every
conflicted table is shown.
```

**Usage**

```text
bd conflicts show [<issue-id>] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all-fields` |  |  | Show every column, not just the fields that diverged |
| `--help` | `-h` |  | help for show |
| `--table` |  | string | Restrict to one conflicted table (default: all) |

<a id="bd-export"></a>

## `bd export`

```text
Export all issues to JSONL (newline-delimited JSON) format.

Each line is a complete JSON object representing one issue, including its
labels, dependencies, and comments.

This command is for issue export, migration, and interoperability. It exports
records from the issues table; it is not a full database backup and does not
capture Dolt branches, commit history, working-set state, or non-issue tables.
For supported full backup/restore flows, use 'bd backup init', 'bd backup sync',
and 'bd backup restore'.

By default, exports only regular issues (excluding infrastructure beads
like agents, roles, and messages). Use --all to include everything.

Memories (from 'bd remember') are excluded by default because they may
contain sensitive agent context. Use --include-memories or --all to
include them.

EXAMPLES:
  bd export                              # Export issues to stdout
  bd export -o issues.jsonl              # Export issues to file
  bd export --include-memories           # Export issues + memories
  bd export --all -o full.jsonl          # Include infra + templates + gates + memories
  bd export --scrub -o clean.jsonl       # Exclude test/pollution records
```

**Usage**

```text
bd export [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` |  |  | Include all records (infra, templates, gates, memories) |
| `--exclude-owner` |  | stringArray | Exclude issues created by this identity (repeatable; also reads export.exclude_owners config) |
| `--help` | `-h` |  | help for export |
| `--include-infra` |  |  | Include infrastructure beads (agents, roles, messages) |
| `--include-memories` |  |  | Include persistent memories (from 'bd remember') in the export |
| `--output` | `-o` | string | Output file path (default: stdout) |
| `--scrub` |  |  | Exclude test/pollution records |
| `--verbose` |  |  | Print filtered issue count when owners are excluded |

Local definitions override the global flags `--verbose` for this command.

<a id="bd-federation"></a>

## `bd federation`

```text
Manage peer-to-peer federation between Dolt-backed beads databases.

Federation enables synchronized issue tracking across multiple workspaces,
each maintaining their own Dolt database while sharing updates via remotes.

Requires the Dolt storage backend.
```

**Usage**

```text
bd federation [command]
```

**Available Commands**

- [`add-peer`](#bd-federation-add-peer) — Add a federation peer with optional SQL credentials
- [`list-peers`](#bd-federation-list-peers) — List configured federation peers
- [`status`](#bd-federation-status) — Show federation sync status
- [`sync`](#bd-federation-sync) — Synchronize with a peer town

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for federation |

<a id="bd-federation-add-peer"></a>

### `bd federation add-peer`

```text
Add a new federation peer remote with optional SQL user authentication.

The URL can be:
  - dolthub://org/repo      DoltHub hosted repository
  - host:port/database      Direct dolt sql-server connection
  - file:///path/to/repo    Local file path (for testing)

Credentials are encrypted and stored locally. They are used automatically
when syncing with the peer. If --user is provided without --password,
you will be prompted for the password interactively.
```

**Usage**

```text
bd federation add-peer <name> <url> [flags]
```

**Examples**

```text
  bd federation add-peer town-beta dolthub://acme/town-beta-beads
  bd federation add-peer town-gamma 192.168.1.100:3306/beads --user sync-bot
  bd federation add-peer partner https://partner.example.com/beads --user admin --password secret
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for add-peer |
| `--password` | `-p` | string | SQL password (prompted if --user set without --password) |
| `--sovereignty` |  | string | Sovereignty tier (T1, T2, T3, T4) |
| `--user` | `-u` | string | SQL username for authentication |

<a id="bd-federation-list-peers"></a>

### `bd federation list-peers`

```text
List configured federation peers
```

**Usage**

```text
bd federation list-peers [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list-peers |

<a id="bd-federation-status"></a>

### `bd federation status`

```text
Show synchronization status with peer towns.

Displays:
  - Configured peers and their URLs
  - Commits ahead/behind each peer
  - Whether there are unresolved conflicts
```

**Usage**

```text
bd federation status [--peer name] [flags]
```

**Examples**

```text
  bd federation status                    # Status for all peers
  bd federation status --peer town-beta   # Status for specific peer
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |
| `--peer` |  | string | Specific peer to check |

<a id="bd-federation-sync"></a>

### `bd federation sync`

```text
Pull from and push to peer towns.

Without --peer, syncs with all configured peers.
With --peer, syncs only with the specified peer.

Handles merge conflicts using the configured strategy:
  --strategy ours    Keep local changes on conflict
  --strategy theirs  Accept remote changes on conflict

If no strategy is specified and conflicts occur, the sync will pause
and report which tables have conflicts for manual resolution.
```

**Usage**

```text
bd federation sync [--peer name] [flags]
```

**Examples**

```text
  bd federation sync                      # Sync with all peers
  bd federation sync --peer town-beta     # Sync with specific peer
  bd federation sync --strategy theirs    # Auto-resolve using remote values
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for sync |
| `--peer` |  | string | Specific peer to sync with |
| `--strategy` |  | string | Conflict resolution strategy (ours\|theirs) |

<a id="bd-import"></a>

## `bd import`

```text
Import issues from a JSONL file (newline-delimited JSON) into the database.

If no file is specified, imports from the configured import.path under .beads/
(default: issues.jsonl). Use "-" to read from stdin; redirecting stdin without
"-" or a file argument is an error, so a typo'd 'bd import < file' cannot
silently import the default file instead. This is the incremental counterpart to
'bd export': new issues are created and existing issues are updated (upsert
semantics).

Memory records (lines with "_type":"memory") are automatically detected and
imported as persistent memories (equivalent to 'bd remember'). This makes
'bd export | bd import' a full round-trip for both issues and memories.

Each JSONL line should map to an issue. The importer accepts every field
'bd export' emits — see 'bd export' output for the canonical schema. Only
"title" is required; everything else is optional.

Common fields:
  title                  Required. Short summary.
  description            Long-form body.
  design, notes,         Additional content sections.
    acceptance_criteria
  issue_type             bug | feature | task | epic | chore | ...
  priority               0-4 (0 = critical). 0 is preserved (no omitempty).
  status                 open | in_progress | blocked | closed | ...
                         (rows with status "tombstone" are skipped)
  assignee, owner,       Ownership metadata.
    created_by
  labels                 Array of strings.
  dependencies           Array of {issue_id, depends_on_id, type, ...}.
  comments               Array of comment objects.
  external_ref,          Cross-system identifiers (e.g. "gh-9").
    source_system
  due_at, defer_until    RFC3339 timestamps for scheduling.
  metadata               Arbitrary JSON object preserved verbatim.

Timestamps (created_at, updated_at, started_at, closed_at) are preserved
when present in the JSONL and otherwise filled in by the importer. The
legacy "wisp" boolean is accepted as an alias for "ephemeral".

By default a row only rewrites an existing local issue when its
updated_at is strictly newer. Older rows are skipped (reported as
stale_skipped_ids) and rows with the same updated_at keep every local
column — updated_at has second granularity, so a timestamp tie can be
two distinct same-second updates, and the local row wins the tie
(reported as tie_kept_local_ids; the row's labels/comments/dependencies
still merge). The guard is also enforced inside the upsert itself, so a
local update that lands while the import is running is preserved rather
than overwritten. Existing issues that the import did rewrite are listed
with a field-level summary (updated_issues), so local state changed by
an import is visible. To deliberately restore an older snapshot, pass
--allow-stale, which imports every row even when it overwrites newer
local state.

Large imports are written in bounded transactions (a few hundred issues
each, with a short pause between commits) with progress on stderr, so
concurrent bd commands keep working while the import runs instead of
stalling on one batch-wide write lock. Rows land in dependency order
with their blocking edges in the same transaction, so a half-finished
import never shows a blocked issue as ready. If an import fails partway,
the already-committed chunks are durable and the command exits nonzero;
re-running the same import is safe and converges (rows upsert,
labels/comments/dependencies deduplicate).

EXAMPLES:
  bd import                        # Import from configured import.path
  bd import backup.jsonl           # Import from a specific file
  bd import -i backup.jsonl        # Legacy alias for a specific file
  bd import -                      # Read JSONL from stdin
  cat issues.jsonl | bd import -   # Pipe JSONL from another tool
  bd import --dry-run              # Show what would be imported
  bd import --dedup                # Skip issues with duplicate titles
  bd import --allow-stale old.jsonl # Restore an older snapshot (overwrites newer local rows)
  bd import --json                 # Structured output with created and skipped IDs
```

**Usage**

```text
bd import [file|-] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--allow-stale` |  |  | Import rows even when older than the local issue (required to restore an older snapshot) |
| `--dedup` |  |  | Skip lines whose title matches an existing open issue |
| `--dry-run` |  |  | Show what would be imported without importing |
| `--help` | `-h` |  | help for import |
| `--input` | `-i` | string | Read JSONL from a specific file |

<a id="bd-restore"></a>

## `bd restore`

```text
Restore the pre-compaction content of a compacted issue.

When an issue is compacted, its description/design/notes/acceptance criteria
are summarized and the originals are archived to a compaction snapshot. This
command recovers that original content.

By default it is read-only: it displays the archived content without modifying
the database. Pass --apply to write the original content back into the issue
and step its compaction level back down.

If no archived snapshot exists (e.g. the issue was compacted by an older bd
before snapshot archiving), restore falls back to a best-effort reconstruction
from Dolt version history, which can only be displayed, not applied.
```

**Usage**

```text
bd restore <issue-id> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--apply` |  |  | Write the restored content back into the issue (default: display only) |
| `--help` | `-h` |  | help for restore |
| `--json` |  |  | Output restore results in JSON format |

Local definitions override the global flags `--json` for this command.

<a id="bd-sync"></a>

## `bd sync`

```text
Run one full synchronization cycle against the Dolt remote.

This is the loop every multi-machine beads deployment otherwise hand-rolls in
shell:

  1. pull from the remote
  2. check for merge conflicts POSITIVELY, from the merge's own conflict rows
     and from Dolt's conflict tables — never inferred from the pull's exit
     status, which is not a trustworthy conflict signal in either direction
  3. recompute the denormalized is_blocked flag, so dependency edges merged in
     from another replica do not leave 'bd ready' stale
  4. push, retrying a bounded number of times when another replica wins the
     push race

The repair in step 3 refuses to run while another writer has uncommitted changes
to issues/dependencies. That is transient and not this sync's doing, so it is
retried on the same budget as a push race rather than failing the run. A working
set that is NOT transient exits 4 instead, because no amount of retrying will
ever publish and only an operator can clear it. Two kinds of evidence say so:
constraint violations on the dirty tables are detected positively and escalate
on the very attempt that finds them; an abandoned uncommitted edit has no such
positive signal, so it is only inferred once the same pending graph edits have
blocked every attempt of several consecutive runs.

Conflicts sync cannot resolve safely are NEVER auto-resolved: it halts before
recomputing or pushing and exits 2, and repeated runs keep halting the same way
until an operator resolves the divergence. (The pull underneath does auto-settle
the conflict classes it can settle convergently — machine-local metadata,
audit-only dependency rows, and last-write-wins on issue cells. Anything beyond
those halts here.) Whether the halted merge was aborted or left live in the
working set depends on the pull route, so the halt message reports which.

Exit codes (a sync timer can branch on these without parsing output):

  0  synced, or nothing to do
  1  error (transport, auth, storage)
  2  merge conflict — halted, nothing pushed, resolve it by hand
  3  retries exhausted (push race, or a concurrent writer's dirty working set)
     — transient, nothing pushed, retry on the next tick
  4  the dirty working set is stuck, not busy: identical pending graph edits
     blocked every attempt of several consecutive runs — nothing pushed, and no
     later tick will publish until an operator clears it

On the default-remote path, a rig with no Dolt remote yet but a git origin
configured adopts that origin as its Dolt remote first, exactly as 'bd dolt push'
does — so 'bd sync' works as a first-time federation bring-up step instead of
reporting 'no remote' and doing nothing. Passing --remote never adopts anything.

This is not 'bd federation sync', which syncs with named peer towns and takes a
--strategy ours|theirs to resolve whatever conflicts it meets. 'bd sync' targets
the configured remote and has no such switch: what it cannot settle, it halts on.
```

**Usage**

```text
bd sync [flags]
```

**Examples**

```text
  bd sync                        # sync with the default remote
  bd sync --remote mini          # sync with a specific remote
  bd sync --attempts 5           # allow more push-race retries
  bd sync --json                 # machine-parseable outcome
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--attempts` |  | int | Maximum pull/push attempts before reporting a transient retry exhaustion (exit 3) (default 3) |
| `--help` | `-h` |  | help for sync |
| `--no-adopt` |  |  | Never derive a Dolt remote from git origin (also BD_NO_REMOTE_ADOPT=1) |
| `--remote` |  | string | Sync with a specific named remote instead of the default |
| `--yes` | `-y` |  | Consent to adopting a Dolt remote derived from git origin when none is configured |

<a id="bd-vc"></a>

## `bd vc`

```text
Version control operations for the beads database.

These commands provide git-like version control for your issue data, including branching, merging, and
viewing history.

Note: 'bd history', 'bd diff', and 'bd branch' also work for quick access.
This subcommand provides additional operations like merge and commit.
```

**Usage**

```text
bd vc [command]
```

**Available Commands**

- [`commit`](#bd-vc-commit) — Create a commit with all staged changes
- [`merge`](#bd-vc-merge) — Merge a branch into the current branch
- [`status`](#bd-vc-status) — Show current branch and uncommitted changes

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for vc |

<a id="bd-vc-commit"></a>

### `bd vc commit`

```text
Create a new Dolt commit with all current changes.
```

**Usage**

```text
bd vc commit [flags]
```

**Examples**

```text
  bd vc commit -m "Added new feature issues"
  bd vc commit --message "Fixed priority on several issues"
  echo "Multi-line message" | bd vc commit --stdin
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for commit |
| `--message` | `-m` | string | Commit message |
| `--stdin` |  |  | Read commit message from stdin |

<a id="bd-vc-merge"></a>

### `bd vc merge`

```text
Merge the specified branch into the current branch.

If there are merge conflicts, they will be reported. You can resolve
conflicts with --strategy.
```

**Usage**

```text
bd vc merge <branch> [flags]
```

**Examples**

```text
  bd vc merge feature-xyz                    # Merge feature-xyz into current branch
  bd vc merge feature-xyz --strategy ours    # Merge, preferring our changes on conflict
  bd vc merge feature-xyz --strategy theirs  # Merge, preferring their changes on conflict
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for merge |
| `--strategy` |  | string | Conflict resolution strategy: 'ours' or 'theirs' |

<a id="bd-vc-status"></a>

### `bd vc status`

```text
Show the current branch, commit hash, and any uncommitted changes.
```

**Usage**

```text
bd vc status [flags]
```

**Examples**

```text
  bd vc status
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-bootstrap"></a>

## `bd bootstrap`

```text
Bootstrap sets up the beads database without destroying existing data.
Unlike 'bd init --force', bootstrap will never delete existing issues.

Bootstrap auto-detects the right action:
  • If sync.remote is configured: clones from the remote
  • If git origin has Dolt data (refs/dolt/data): clones from git and wires origin for future push/pull
  • If .beads/backup/*.jsonl exists: restores from backup
  • If .beads/issues.jsonl exists: imports from git-tracked JSONL
  • If no database exists: creates a fresh one
  • If database already exists: validates and reports status

If sync.remote points at a git repository, bootstrap verifies refs/dolt/data
before cloning. Bootstrap exits non-zero when it cannot set up a database.

This is the recommended command for:
  • Setting up beads on a fresh clone
  • Recovering after moving to a new machine
  • Repairing a broken database configuration

Non-interactive mode (--non-interactive, --yes/-y, or BD_NON_INTERACTIVE=1):
  Skips the confirmation prompt before executing the bootstrap plan.
  Also auto-detected when stdin is not a terminal or CI=true is set.
```

**Usage**

```text
bd bootstrap [flags]
```

**Examples**

```text
  bd bootstrap              # Auto-detect and set up
  bd bootstrap --dry-run    # Show what would be done
  bd bootstrap --json       # Output plan as JSON
  bd bootstrap --yes        # Skip confirmation prompt
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would be done without doing it |
| `--help` | `-h` |  | help for bootstrap |
| `--non-interactive` |  |  | Alias for --yes |
| `--yes` | `-y` |  | Skip confirmation prompts (for CI/automation) |

<a id="bd-config"></a>

## `bd config`

```text
Manage configuration settings for external integrations and preferences.

Configuration is stored per-project in the beads database and is version-control-friendly.

Common namespaces:
  - export.*          Auto-export settings (stored in config.yaml)
  - import.*          JSONL import settings (stored in config.yaml)
  - jira.*            Jira integration settings
  - linear.*          Linear integration settings
  - github.*          GitHub integration settings
  - gitlab.*          GitLab integration settings
  - ado.*             Azure DevOps integration settings
  - notion.*          Notion integration settings
  - custom.*          Custom integration settings
  - status.*          Issue status configuration
  - claim.*           Claim arbitration settings (pool-aware claiming)
  - doctor.suppress.* Suppress specific bd doctor warnings (GH#1095)
  - lint.*            Additional per-type lint sections (stored in config.yaml)

Auto-Export (config.yaml):
  Optional JSONL export to .beads/issues.jsonl after write commands (throttled).
  Useful for viewers (bv), interchange, and issue-level migration; not a backup.
  It is not cross-machine sync; use bd dolt push/pull with a Dolt remote.
  Disabled by default. Enable only for integrations that need fresh JSONL.
  Auto-staging is separate and disabled by default.

  Keys:
    export.auto       Enable/disable auto-export (default: false)
    export.path       Output filename relative to .beads/ (default: issues.jsonl)
    export.interval   Minimum time between exports (default: 60s)
    export.git-add    Auto-stage the export file (default: false)

Auto-Import (config.yaml):
  Reads .beads/issues.jsonl by default when a JSONL import path is implied.
  Use a relative filename/path so the import stays within the project .beads/
  directory and remains portable across machines.

  Keys:
    import.path       Input filename relative to .beads/ (default: issues.jsonl)

Custom Status States:
  You can define custom status states for multi-step pipelines using the
  status.custom config key. Statuses should be comma-separated.

  Example:
    bd config set status.custom "awaiting_review,awaiting_testing,awaiting_docs"

  This enables issues to use statuses like 'awaiting_review' in addition to
  the built-in statuses (open, in_progress, blocked, deferred, closed).

Claim Pools:
  A dispatcher can pre-assign issues to a pool pseudo-assignee (e.g.
  "fable-crew") and let any actor take them with --claim. List the pool
  aliases in the claim.pools config key, comma-separated:

    bd config set claim.pools "fable-crew,night-crew"

  Issues assigned to a real actor (or to an alias not in the list) keep
  their anti-steal protection. Pool takes carry the normal lease; note
  that if a taker's lease expires, bd reclaim returns the issue to the
  unassigned pool, not to the pool alias it was dispatched to.

Suppressing Doctor Warnings:
  Suppress specific bd doctor warnings by check name slug:
    bd config set doctor.suppress.pending-migrations true
    bd config set doctor.suppress.git-hooks true
  Check names are converted to slugs: "Git Hooks" → "git-hooks".
  Only warnings are suppressed (errors and passing checks always show).
  To unsuppress: bd config unset doctor.suppress.<slug>
```

**Usage**

```text
bd config [command]
```

**Available Commands**

- [`apply`](#bd-config-apply) — Reconcile system state to match configuration
- [`drift`](#bd-config-drift) — Detect config-vs-reality inconsistencies
- [`get`](#bd-config-get) — Get a configuration value
- [`list`](#bd-config-list) — List all configuration
- [`set`](#bd-config-set) — Set a configuration value
- [`set-many`](#bd-config-set-many) — Set multiple configuration values in one operation
- [`show`](#bd-config-show) — Show all effective configuration with provenance
- [`unset`](#bd-config-unset) — Delete a configuration value
- [`validate`](#bd-config-validate) — Validate sync-related configuration

**Examples**

```text
  bd config set export.auto true                       # Enable auto-export for viewer integrations
  bd config set export.path "beads.jsonl"              # Custom export filename
  bd config set import.path "beads.jsonl"              # Custom import filename
  bd config set export.git-add true                    # Also stage the export file
  bd config set jira.url "https://company.atlassian.net"
  bd config set jira.project "PROJ"
  bd config set status.custom "awaiting_review,awaiting_testing"
  bd config set claim.pools "fable-crew,night-crew"    # Pool aliases claimable by any actor
  bd config set doctor.suppress.pending-migrations true
  bd config set dolt.debug true                        # Enable Dolt sql-server debug mode (loglevel=debug, --prof cpu)
  bd config set dolt.local-only true                   # Skip wiring a Dolt sync remote during bd init
  bd config set lint.sections.epic "Standards scorecard, Cost"   # Extra sections bd lint requires for epics
  bd config get export.auto
  bd config list
  bd config unset jira.url
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for config |

<a id="bd-config-apply"></a>

### `bd config apply`

```text
Reconcile actual system state to match declared configuration.

Runs drift detection and then fixes any mismatches it finds:
  - hooks     Reinstall git hooks if missing or outdated
  - remote    Add/update Dolt origin remote to match federation.remote
  - server    Start Dolt server if dolt.shared-server is enabled

This command is idempotent — safe to run multiple times. Use --dry-run
to preview what would change without making modifications.
```

**Usage**

```text
bd config apply [flags]
```

**Examples**

```text
  bd config apply
  bd config apply --dry-run
  bd config apply --json
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would change without making modifications |
| `--help` | `-h` |  | help for apply |

<a id="bd-config-drift"></a>

### `bd config drift`

```text
Detect drift between declared configuration and actual system state.

This is a read-only diagnostic that answers "is my environment consistent
with my config?" — no mutations are performed.

Checks:
  - hooks     Git hooks installed and up-to-date
  - remote    Dolt remote matches federation.remote config
  - server    Server state matches dolt.shared-server config

Exit codes:
  0  No drift detected (all checks ok/info/skipped)
  1  Drift detected (at least one check has status "drift")
```

**Usage**

```text
bd config drift [flags]
```

**Examples**

```text
  bd config drift
  bd config drift --json
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for drift |

<a id="bd-config-get"></a>

### `bd config get`

```text
Get a configuration value
```

**Usage**

```text
bd config get <key> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for get |

<a id="bd-config-list"></a>

### `bd config list`

```text
List all configuration
```

**Usage**

```text
bd config list [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-config-set"></a>

### `bd config set`

```text
Set a configuration value
```

**Usage**

```text
bd config set <key> <value> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force-git-tracked` |  |  | Allow writing secret keys to git-tracked config files (use with caution) |
| `--help` | `-h` |  | help for set |

<a id="bd-config-set-many"></a>

### `bd config set-many`

```text
Set multiple configuration values at once with a single auto-commit and auto-push.

Each argument must be in key=value format. All values are validated before
any writes occur. This is faster and less noisy than separate 'bd config set'
calls, especially in CI.
```

**Usage**

```text
bd config set-many <key=value>... [flags]
```

**Examples**

```text
  bd config set-many ado.state_map.open=New ado.state_map.closed=Closed
  bd config set-many jira.url=https://example.atlassian.net jira.project=PROJ
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force-git-tracked` |  |  | Allow writing secret keys to git-tracked config files (use with caution) |
| `--help` | `-h` |  | help for set-many |

<a id="bd-config-show"></a>

### `bd config show`

```text
Display a unified view of all effective configuration across all sources
with annotations showing where each value comes from.

Sources (by precedence for Viper-managed keys):
  - env          Environment variable (BD_* or BEADS_*)
  - config.yaml  Project config file (.beads/config.yaml)
  - default      Built-in default value

Additional sources:
  - metadata     Connection settings from .beads/metadata.json
  - database     Integration config stored in the Dolt database
  - git          Git config (e.g., beads.role)
```

**Usage**

```text
bd config show [flags]
```

**Examples**

```text
  bd config show
  bd config show --json
  bd config show --source config.yaml
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for show |
| `--source` |  | string | Filter by source (e.g., config.yaml, env, default, metadata, database, git) |

<a id="bd-config-unset"></a>

### `bd config unset`

```text
Delete a configuration value
```

**Usage**

```text
bd config unset <key> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for unset |

<a id="bd-config-validate"></a>

### `bd config validate`

```text
Validate sync-related configuration settings.

Checks:
  - federation.sovereignty is valid (T1, T2, T3, T4, or empty)
  - federation.remote is set for Dolt sync
  - Remote URL format is valid (dolthub://, gs://, s3://, az://, file://)
  - routing.mode is valid (auto, maintainer, contributor, explicit)

	Examples:
	  bd config validate
	  bd config validate --json
```

**Usage**

```text
bd config validate [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for validate |

<a id="bd-context"></a>

## `bd context`

```text
Show the effective backend identity information including repository paths,
backend configuration, and sync settings.

This command reads directly from config files and does not require the
database to be open, making it useful for diagnostics in degraded states.
```

**Usage**

```text
bd context [flags]
```

**Examples**

```text
  bd context           # Show context information
  bd context --json    # Output in JSON format
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for context |

<a id="bd-dolt"></a>

## `bd dolt`

```text
Configure and manage Dolt database settings and server lifecycle.

Beads runs Dolt embedded (in-process) by default: there is no sql-server and
nothing is auto-started. A database only uses a dolt sql-server when it is
configured for one: shared-server mode, an explicit server mode, or a
non-localhost dolt_server_host. The server-only commands below fail with
"not supported in embedded mode (no Dolt server)" on an embedded database.

Server lifecycle (server mode only):
  bd dolt start        Start the Dolt server for this project
  bd dolt stop         Stop the Dolt server for this project

Diagnostics (both modes):
  bd dolt status       Show Dolt engine status (embedded: in-process, data dir)
  bd dolt show         Show current Dolt configuration with connection test

Configuration (server mode only):
  bd dolt set <k> <v>  Set a configuration value
  bd dolt test         Test server connection

Version control:
  bd dolt commit       Commit pending changes
  bd dolt push         Push commits to Dolt remote
  bd dolt pull         Pull commits from Dolt remote

Remote management:
  bd dolt remote add <name> <url>   Add a Dolt remote
  bd dolt remote list                List configured remotes
  bd dolt remote remove <name>       Remove a Dolt remote

Configuration keys for 'bd dolt set':
  database  Database name (default: issue prefix or "beads")
  host      Server host (default: 127.0.0.1)
  port      Server port (auto-detected; override with bd dolt set port <N>)
  user      MySQL user (default: root)
  data-dir  Custom dolt data directory (absolute path; default: .beads/dolt)

Remote server authentication (password + TLS) is NOT stored via 'bd dolt set'
(keeps secrets out of metadata.json). Configure them with:

  BEADS_DOLT_PASSWORD       Server password (highest priority)
  BEADS_DOLT_SERVER_TLS     Enable TLS (set to "1" or "true")
  BEADS_DOLT_SERVER_USER    MySQL user override (else use 'bd dolt set user')
  BEADS_CREDENTIALS_FILE    Optional path to credentials file

  Default credentials file: ~/.config/beads/credentials (Linux/macOS)
                            %APPDATA%\beads\credentials (Windows)
  Format (INI, section = host:port of the resolved connection):
    [127.0.0.1:3307]
    password = secret

  Password resolution: BEADS_DOLT_PASSWORD → credentials [host:port] → empty.
  Full reference: docs/architecture/dolt.md (Environment Variables / Credentials).

Flags for 'bd dolt set':
  --update-config  Also write to config.yaml for team-wide defaults
```

**Usage**

```text
bd dolt [command]
```

**Available Commands**

- [`commit`](#bd-dolt-commit) — Create a Dolt commit from pending changes
- [`killall`](#bd-dolt-killall) — Kill all orphan Dolt server processes
- [`pull`](#bd-dolt-pull) — Pull commits from Dolt remote
- [`push`](#bd-dolt-push) — Push commits to Dolt remote
- [`remote`](#bd-dolt-remote) — Manage Dolt remotes
- [`set`](#bd-dolt-set) — Set a Dolt configuration value
- [`show`](#bd-dolt-show) — Show current Dolt configuration with connection status
- [`start`](#bd-dolt-start) — Start the Dolt SQL server for this project
- [`status`](#bd-dolt-status) — Show Dolt engine status
- [`stop`](#bd-dolt-stop) — Stop the Dolt SQL server for this project
- [`test`](#bd-dolt-test) — Test connection to Dolt server

**Examples**

```text
  bd dolt set database myproject
  bd dolt set host 192.168.1.100 --update-config
  bd dolt set data-dir /home/user/.beads-dolt/myproject
  export BEADS_DOLT_PASSWORD=... BEADS_DOLT_SERVER_TLS=1
  bd dolt test
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for dolt |

<a id="bd-dolt-commit"></a>

### `bd dolt commit`

```text
Create a Dolt commit from any uncommitted changes in the working set.

This is the primary commit point for batch mode. When auto-commit is set to
"batch", changes accumulate in the working set across multiple bd commands and
are committed together here with a descriptive summary message.

Also useful before push operations that require a clean working set, or when
auto-commit was off or changes were made externally.

For more options (--stdin, custom messages), see: bd vc commit
```

**Usage**

```text
bd dolt commit [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for commit |
| `--message` | `-m` | string | Commit message (default: auto-generated) |

<a id="bd-dolt-killall"></a>

### `bd dolt killall`

```text
Find and kill orphan dolt sql-server processes not tracked by the
canonical PID file for the current repo's Dolt data directory.

Under an orchestrator, the canonical server lives at $GT_ROOT/.beads/. Any other
dolt sql-server processes using that shared data directory are considered
orphans and will be killed.

In standalone mode, only dolt sql-server processes using the current
project's Dolt data directory are eligible for cleanup. Other projects'
servers are preserved.
```

**Usage**

```text
bd dolt killall [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for killall |

<a id="bd-dolt-pull"></a>

### `bd dolt pull`

```text
Pull commits from the configured Dolt remote into the local database.

Requires a Dolt remote to be configured in the database directory.
For Hosted Dolt, set DOLT_REMOTE_USER and DOLT_REMOTE_PASSWORD environment
variables for authentication.

Use --remote to pull from a specific named remote instead of the default.
The remote must already exist (see 'bd dolt remote add').

Use --strategy ours|theirs to resolve conflicts the auto-resolver declines
(e.g. both sides edited the same issue since the last sync) instead of
aborting the pull for manual resolution. Embedded storage only (#4992); on
server-mode/sql-server storage use 'bd conflicts resolve' after a pull that
reports conflicts.
```

**Usage**

```text
bd dolt pull [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for pull |
| `--remote` |  | string | Pull from a specific named remote instead of the default |
| `--strategy` |  | string | Conflict resolution strategy for conflicts the auto-resolver declines: 'ours' or 'theirs' (embedded storage only, #4992) |

<a id="bd-dolt-push"></a>

### `bd dolt push`

```text
Push local Dolt commits to the configured remote.

Requires a Dolt remote to be configured in the database directory. With no
remote configured, bd can adopt one derived from git origin — only with
consent: interactively, or via --yes; --no-adopt or BD_NO_REMOTE_ADOPT=1
disables adoption entirely.
For Hosted Dolt, set DOLT_REMOTE_USER and DOLT_REMOTE_PASSWORD environment
variables for authentication.

Use --force to overwrite remote changes (e.g., when the remote has
uncommitted changes in its working set).

Use --remote to push to a specific named remote instead of the default.
The remote must already exist (see 'bd dolt remote add').
```

**Usage**

```text
bd dolt push [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force` |  |  | Force push (overwrite remote changes) |
| `--help` | `-h` |  | help for push |
| `--no-adopt` |  |  | Never derive a Dolt remote from git origin (also BD_NO_REMOTE_ADOPT=1) |
| `--remote` |  | string | Push to a specific named remote instead of the default |
| `--yes` | `-y` |  | Consent to adopting a Dolt remote derived from git origin when none is configured |

<a id="bd-dolt-remote"></a>

### `bd dolt remote`

```text
Manage Dolt remotes for push/pull replication.
```

**Usage**

```text
bd dolt remote [command]
```

**Subcommands**

- [`list`](#bd-dolt-remote-list) — List all configured remotes

**Available Commands**

- [`add`](#bd-dolt-remote-add) — Add a Dolt remote
- [`remove`](#bd-dolt-remote-remove) — Remove a Dolt remote
- [`reset-data`](#bd-dolt-remote-reset-data) — Replace a remote's data plane in place after a history squash

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for remote |

<a id="bd-dolt-remote-list"></a>

#### `bd dolt remote list`

```text
List configured Dolt remotes
```

**Usage**

```text
bd dolt remote list [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-dolt-remote-add"></a>

#### `bd dolt remote add`

```text
Add a Dolt remote
```

**Usage**

```text
bd dolt remote add <name> <url> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--allow-git-origin` |  |  | Allow adding a Dolt remote whose URL matches the git origin (proceed with a warning instead of aborting) |
| `--help` | `-h` |  | help for add |

<a id="bd-dolt-remote-remove"></a>

#### `bd dolt remote remove`

```text
Remove a Dolt remote
```

**Usage**

```text
bd dolt remote remove <name> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for remove |

<a id="bd-dolt-remote-reset-data"></a>

#### `bd dolt remote reset-data`

```text
Replace a Dolt remote's stored data with a fresh copy of local HEAD.

After a history squash (see the History Bloat recovery runbook), a plain
'bd dolt push --force' re-points the remote's refs but deletes nothing:
Dolt remotes accumulate chunks monotonically, so the remote keeps the full
pre-squash store. This command rebuilds the remote's data plane so it holds
only live chunks:

  - Git-backed remotes (issue data riding a git remote under refs/dolt/data):
    deletes the Dolt data refs on the git remote, then force-pushes to
    rebuild a fresh store. Code branches are untouched.
  - Native file remotes (file:// paths): clears the store directory, then
    force-pushes to rebuild it.
  - Cloud/hosted remotes (aws://, gs://, dolthub://, ...): bd cannot clear
    the stored data safely — replace the remote with a fresh URL or prefix:
      bd dolt remote remove <name>
      bd dolt remote add <name> <fresh-url>
      bd dolt push --force

This rewrites the remote's data plane. Every other clone must re-clone from
the reset remote (that is already true after the squash itself). Refuses to
run with uncommitted working-set changes: the rebuilt remote holds exactly
HEAD, and anything uncommitted would not be part of it.
```

**Usage**

```text
bd dolt remote reset-data <name> [flags]
```

**Examples**

```text
  bd dolt remote reset-data origin          # prompts for confirmation
  bd dolt remote reset-data origin --yes    # no prompt (scripts, agents)
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for reset-data |
| `--yes` | `-y` |  | Skip the confirmation prompt (required in non-interactive use) |

<a id="bd-dolt-set"></a>

### `bd dolt set`

```text
Set a Dolt configuration value in metadata.json.

Keys:
  database  Database name (default: issue prefix or "beads")
  host      Server host (default: 127.0.0.1)
  port      Server port (auto-detected; override with bd dolt set port <N>)
  user      MySQL user (default: root)
  data-dir  Custom dolt data directory (absolute path; default: .beads/dolt)

There is no 'password' or 'tls' key here on purpose — secrets and TLS must
not land in metadata.json. Use environment variables or the credentials file:

  BEADS_DOLT_PASSWORD     Server password (highest priority)
  BEADS_DOLT_SERVER_TLS   Enable TLS ("1" or "true")
  BEADS_CREDENTIALS_FILE  Optional override path for credentials

  Default credentials file: ~/.config/beads/credentials
  Format:
    [host:port]
    password = secret

  See: bd dolt --help and docs/architecture/dolt.md

Use --update-config to also write to config.yaml for team-wide defaults.
```

**Usage**

```text
bd dolt set <key> <value> [flags]
```

**Examples**

```text
  bd dolt set database myproject
  bd dolt set host 192.168.1.100
  bd dolt set port 3307 --update-config
  bd dolt set data-dir /home/user/.beads-dolt/myproject
  export BEADS_DOLT_PASSWORD=... BEADS_DOLT_SERVER_TLS=1
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for set |
| `--update-config` |  |  | Also write to config.yaml for team-wide defaults |

<a id="bd-dolt-show"></a>

### `bd dolt show`

```text
Show current Dolt configuration with connection status
```

**Usage**

```text
bd dolt show [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for show |

<a id="bd-dolt-start"></a>

### `bd dolt start`

```text
Start a dolt sql-server for the current beads project.

The server runs in the background on a per-project port derived from the
project path. PID and logs are stored in .beads/.

The server auto-starts transparently when needed, so manual start is rarely
required. Use this command for explicit control or diagnostics.
```

**Usage**

```text
bd dolt start [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for start |

<a id="bd-dolt-status"></a>

### `bd dolt status`

```text
Show the status of the Dolt engine for the current project.

In embedded mode, reports that the Dolt engine runs in-process and shows
the on-disk data directory. For beads-managed (local) servers, displays
PID, port, and data directory from the local PID file. For externally-
managed servers — a shared server (dolt.shared-server: true), a remote
dolt_server_host, or a local server managed outside bd (dolt.auto-start:
false, e.g. an orchestrator-shared sql-server) — pings the configured
endpoint via SQL and reports reachability, server version, and database.
```

**Usage**

```text
bd dolt status [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-dolt-stop"></a>

### `bd dolt stop`

```text
Stop the dolt sql-server managed by beads for the current project.

This sends a graceful shutdown signal. The server will restart automatically
on the next bd command unless auto-start is disabled.

For a managed proxied server, --force can recover unverifiable or legacy
process records (both the proxy and its backend) only after each live process
executable is matched to bd or dolt and its command line ties it to this
workspace. In that recovery path, force still refuses to signal a process
whose executable identity cannot be matched to bd or dolt, or whose workspace
scope cannot be established.
```

**Usage**

```text
bd dolt stop [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force` |  |  | Force stop (proxied recovery still requires a bd/dolt executable match) |
| `--help` | `-h` |  | help for stop |

<a id="bd-dolt-test"></a>

### `bd dolt test`

```text
Test the connection to the configured Dolt server.

This verifies that:
  1. The server is reachable at the configured host:port
  2. The connection can be established

Use this before switching to server mode to ensure the server is running.
```

**Usage**

```text
bd dolt test [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for test |

<a id="bd-forget"></a>

## `bd forget`

```text
Remove a memory by its key.

Use 'bd memories' to see available keys.
```

**Usage**

```text
bd forget <key> [flags]
```

**Examples**

```text
  bd forget dolt-phantoms
  bd forget auth-jwt
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for forget |

<a id="bd-hooks"></a>

## `bd hooks`

```text
Install, uninstall, or list git hooks for beads integration.

The hooks provide:
- pre-commit: Run chained hooks before commit
- post-merge: Run chained hooks after pull/merge
- pre-push: Run chained hooks before push
- post-checkout: Run chained hooks after branch checkout
- prepare-commit-msg: Add agent identity trailers for forensics
```

**Usage**

```text
bd hooks [command]
```

**Available Commands**

- [`install`](#bd-hooks-install) — Install bd git hooks
- [`list`](#bd-hooks-list) — List installed git hooks status
- [`run`](#bd-hooks-run) — Execute a git hook (called by thin shims)
- [`uninstall`](#bd-hooks-uninstall) — Uninstall bd git hooks

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for hooks |

<a id="bd-hooks-install"></a>

### `bd hooks install`

```text
Install git hooks for beads integration.

By default, hooks are installed to .git/hooks/ in the current repository.
Use --beads to install to .beads/hooks/ (recommended for Dolt backend).
Use --shared to install to a versioned directory (.beads-hooks/) that can be
committed to git and shared with team members.

Hooks use section markers to coexist with existing hooks — any user content
outside the markers is preserved across installs and upgrades.

Installed hooks:
  - pre-commit: Run chained hooks before commit
  - post-merge: Run chained hooks after pull/merge
  - pre-push: Run chained hooks before push
  - post-checkout: Run chained hooks after branch checkout
  - prepare-commit-msg: Add agent identity trailers (for orchestrator agents)
```

**Usage**

```text
bd hooks install [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--beads` |  |  | Install hooks to .beads/hooks/ (recommended for Dolt backend) |
| `--chain` |  |  | No-op, kept for compatibility (existing hook content always runs alongside the bd section) |
| `--force` |  |  | No-op, kept for compatibility (section markers always preserve non-bd content) |
| `--help` | `-h` |  | help for install |
| `--shared` |  |  | Install hooks to .beads-hooks/ (versioned) instead of .git/hooks/ |

<a id="bd-hooks-list"></a>

### `bd hooks list`

```text
Show the status of bd git hooks (installed, outdated, missing).
```

**Usage**

```text
bd hooks list [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-hooks-run"></a>

### `bd hooks run`

```text
Execute the logic for a git hook. This command is typically called by
thin shim scripts installed in .git/hooks/.

Supported hooks:
  - pre-commit: Run chained hooks before commit
  - post-merge: Run chained hooks after pull/merge
  - pre-push: Run chained hooks before push
  - post-checkout: Run chained hooks after branch checkout
  - prepare-commit-msg: Add agent identity trailers for forensics

The thin shim keeps delegated hook logic in sync with the installed bd
version. Upgrading bd updates that delegated behavior. To adopt changes to the
shim's generated shell policy, refresh it with 'bd hooks install'.
```

**Usage**

```text
bd hooks run <hook-name> [args...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for run |

<a id="bd-hooks-uninstall"></a>

### `bd hooks uninstall`

```text
Remove bd git hooks from .git/hooks/ directory.
```

**Usage**

```text
bd hooks uninstall [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for uninstall |

<a id="bd-human"></a>

## `bd human`

```text
Display a focused help menu showing only the most common commands.

bd has 70+ commands - many for AI agents, integrations, and advanced workflows.
This command shows the ~15 essential commands that human users need most often.

For the full command list, run: bd --help

SUBCOMMANDS:
  human list              List human-needed beads (issues with 'human' label; hides closed by default)
  human respond <id>      Respond to a human-needed bead (adds comment and closes)
  human dismiss <id>      Dismiss a human-needed bead permanently
  human stats             Show summary statistics for human-needed beads
```

**Usage**

```text
bd human [flags]
bd human [command]
```

**Available Commands**

- [`dismiss`](#bd-human-dismiss) — Dismiss a human-needed bead
- [`list`](#bd-human-list) — List human-needed beads
- [`respond`](#bd-human-respond) — Respond to a human-needed bead
- [`stats`](#bd-human-stats) — Show summary statistics for human-needed beads

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for human |

<a id="bd-human-dismiss"></a>

### `bd human dismiss`

```text
Dismiss a human-needed bead permanently without responding.

The issue is closed with a "Dismissed" reason and optional note.
The reason can be given as positional arguments or --reason.
```

**Usage**

```text
bd human dismiss <issue-id> [reason...] [flags]
```

**Examples**

```text
  bd human dismiss bd-123
  bd human dismiss bd-123 "No longer applicable"
  bd human dismiss bd-123 --reason "No longer applicable"
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for dismiss |
| `--reason` |  | string | Reason for dismissal (optional) |

<a id="bd-human-list"></a>

### `bd human list`

```text
List issues labeled with 'human' tag.

These are issues that require human intervention or input. Every
human-labeled bead shows regardless of type (including gates and wisps).
By default closed, pinned, and other done/frozen beads are hidden; use
--status to select specific statuses, or --status=all to include every
status.
```

**Usage**

```text
bd human list [flags]
```

**Examples**

```text
  bd human list
  bd human list --status=closed
  bd human list --status=all
  bd human list --json
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |
| `--status` | `-s` | string | Filter by status (open, closed, etc.; comma-separated for multiple, 'all' for every status) |

<a id="bd-human-respond"></a>

### `bd human respond`

```text
Respond to a human-needed bead by adding a comment and closing it.

The response is added as a comment and the issue is closed with reason "Responded".
The response text can be given as positional arguments, --response, --file, or --stdin.
```

**Usage**

```text
bd human respond <issue-id> [response...] [flags]
```

**Examples**

```text
  bd human respond bd-123 "Use OAuth2 for authentication"
  bd human respond bd-123 -r "Approved, proceed with implementation"
  bd human respond bd-123 --file response.md
  echo "Approved" | bd human respond bd-123 --stdin
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--file` |  | string | Read response text from file |
| `--help` | `-h` |  | help for respond |
| `--response` | `-r` | string | Response text |
| `--stdin` |  |  | Read response text from stdin |

<a id="bd-human-stats"></a>

### `bd human stats`

```text
Display summary statistics for human-needed beads.

Shows counts for total, pending (open), responded (closed without dismiss),
and dismissed beads.

Example:
  bd human stats
```

**Usage**

```text
bd human stats [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for stats |

<a id="bd-info"></a>

## `bd info`

```text
Display information about the current database.

This command helps debug issues where bd is using an unexpected database. It shows:
  - The absolute path to the database file
  - Database statistics (issue count)
  - Schema information (with --schema flag)
  - What's new in recent versions (with --whats-new flag)
```

**Usage**

```text
bd info [flags]
```

**Examples**

```text
  bd info
  bd info --json
  bd info --schema --json
  bd info --whats-new
  bd info --whats-new --json
  bd info --thanks
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for info |
| `--schema` |  |  | Include schema information in output |
| `--thanks` |  |  | Show thank you page for contributors |
| `--whats-new` |  |  | Show agent-relevant changes from recent versions |

<a id="bd-init"></a>

## `bd init`

```text
Initialize bd in the current directory by creating a .beads/ directory
and its storage (a Dolt database by default). Optionally specify a custom issue prefix.

Dolt is the default and only supported storage backend, with full version
control (history, branching, sync).

Use --database to specify an existing server database name, overriding the
default prefix-based naming. This is useful when an external tool (e.g. an orchestrator)
has already created the database.

With --stealth: configures per-repository git settings for invisible beads usage:
  • .git/info/exclude to prevent beads files from being committed
  Perfect for personal use without affecting repo collaborators.
  To set up a specific AI tool, run: bd setup <claude|cursor|aider|...> --stealth

By default, beads uses an embedded Dolt engine (no external server needed).
Pass --server to use an external dolt sql-server instead. In server mode,
set connection details with --server-host, --server-port, and --server-user.
Password should be set via BEADS_DOLT_PASSWORD environment variable.

Auto-export is optional. When enabled, bd exports issues to
.beads/issues.jsonl after write commands (throttled to once per 60s). This is
for viewers (bv), interchange, and issue-level migration; not backup.
Cross-machine sync and backups use Dolt remotes/backups, not JSONL import/export.
To enable: bd config set export.auto true

Non-interactive mode (--non-interactive or BD_NON_INTERACTIVE=1):
  Skips all interactive prompts, using sensible defaults:
  • Role defaults to "maintainer" (override with --role)
  • Fork exclude auto-configured when fork detected
  • Auto-export left at default (disabled)
  • --contributor and --team flags are rejected (wizards require interaction)
  Also auto-detected when stdin is not a terminal or CI=true is set.
```

**Usage**

```text
bd init [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--agents-file` |  | string | Custom filename for agent instructions (default: AGENTS.md) |
| `--agents-profile` |  | string | AGENTS.md profile: 'minimal' (default, pointer to bd prime) or 'full' (complete command reference) |
| `--agents-template` |  | string | Path to custom AGENTS.md template (overrides embedded default) |
| `--backend` |  | string | Storage backend: dolt (default). Removed backends (postgres, mysql, sqlite) print migration guidance. |
| `--contributor` |  |  | Run OSS contributor setup wizard |
| `--debug` |  |  | Run the managed Dolt sql-server with --loglevel=debug and CPU profiling (--prof cpu). Persisted to config.yaml as dolt.debug. No effect on externally-managed servers. |
| `--destroy-token` |  | string | Explicit confirmation token for destructive re-init in non-interactive mode (format: 'DESTROY-<prefix>') |
| `--discard-remote` |  |  | Authorize discarding the configured remote's Dolt history when re-initializing. Requires --destroy-token in non-interactive mode; see 'bd help init-safety'. |
| `--external` |  |  | Server is externally managed (skip server startup); use with --shared-server or --server |
| `--force` |  |  | Deprecated alias for --reinit-local. Bypasses only the LOCAL data-safety guard; does NOT authorize remote divergence (see 'bd help init-safety'). |
| `--from-jsonl` |  |  | Import issues from configured import.path; refuses remote history unless --discard-remote authorizes replacement |
| `--help` | `-h` |  | help for init |
| `--init-if-missing` |  |  | If the workspace is already initialized, skip init and exit 0 instead of failing (idempotent init for scaffolds) |
| `--non-interactive` |  |  | Skip all interactive prompts (auto-detected in CI or non-TTY environments) |
| `--prefix` | `-p` | string | Issue prefix (default: current directory name) |
| `--proxied-server` |  |  | [EXPERIMENTAL] Use a per-workspace proxied dolt sql-server (proxy + child dolt) rooted at .beads/dolt |
| `--proxied-server-config-path` |  | string | [EXPERIMENTAL] Absolute path to an existing dolt sql-server YAML config (proxied-server mode only). When set, bd uses this file instead of auto-generating one. Relative paths are rejected. Managed mode requires listener.host to be a numeric loopback IP (hostnames including localhost, non-loopback addresses, listener.socket, remotesapi, and cluster config are rejected); the same policy applies to BEADS_PROXIED_SERVER_CONFIG. |
| `--proxied-server-external-host` |  | string | [EXPERIMENTAL] Hostname or IP of an externally-managed dolt sql-server the proxy should front (proxied-server mode only). Mutually exclusive with --proxied-server-external-socket-path. |
| `--proxied-server-external-keep-alive` |  | duration | [EXPERIMENTAL] TCP keepalive period for the proxy→external connection. Zero uses the package default (30s). |
| `--proxied-server-external-port` |  | int | [EXPERIMENTAL] TCP port of the externally-managed dolt sql-server (proxied-server mode only). Required when --proxied-server-external-host is set. |
| `--proxied-server-external-socket-path` |  | string | [EXPERIMENTAL] Absolute unix socket path of the externally-managed dolt sql-server (proxied-server mode only). Mutually exclusive with --proxied-server-external-host. Relative paths are rejected. |
| `--proxied-server-external-tls` |  |  | [EXPERIMENTAL] Require TLS when connecting to the externally-managed dolt sql-server (proxied-server mode only). |
| `--proxied-server-external-tls-ca-cert-path` |  | string | [EXPERIMENTAL] Absolute path to a CA certificate (PEM) used to verify the externally-managed dolt sql-server. Empty uses the system trust store. Relative paths are rejected. |
| `--proxied-server-external-tls-cert-path` |  | string | [EXPERIMENTAL] Absolute path to a client TLS certificate (for mTLS to the externally-managed dolt sql-server). Must be paired with --proxied-server-external-tls-key-path. Relative paths are rejected. |
| `--proxied-server-external-tls-key-path` |  | string | [EXPERIMENTAL] Absolute path to the client TLS private key (for mTLS to the externally-managed dolt sql-server). Must be paired with --proxied-server-external-tls-cert-path. Relative paths are rejected. |
| `--proxied-server-external-tls-server-name` |  | string | [EXPERIMENTAL] Server name to verify in the external dolt sql-server's TLS certificate. Defaults to the external host. Required with a unix socket unless --proxied-server-external-tls-skip-verify is set. |
| `--proxied-server-external-tls-skip-verify` |  |  | [EXPERIMENTAL] Skip TLS certificate verification for the external dolt sql-server. Insecure; testing only. |
| `--proxied-server-external-user` |  | string | [EXPERIMENTAL] MySQL user for the externally-managed dolt sql-server (proxied-server mode only). Defaults to "root" when empty. Password is read at runtime from $BEADS_PROXIED_SERVER_EXTERNAL_PASSWORD and is never persisted to disk. |
| `--proxied-server-idle-timeout` |  | duration | [EXPERIMENTAL] Idle duration after which the proxy shuts down its loopback listener and backend (proxied-server mode only). Omit for the built-in default (30s); 0 keeps the proxy and backend alive indefinitely; a positive value sets the window. |
| `--proxied-server-log-path` |  | string | [EXPERIMENTAL] Absolute path to the proxied dolt sql-server log file (proxied-server mode only). Default: <beadsDir>/dolt/server.log. Relative paths are rejected. |
| `--proxied-server-port` |  | int | [EXPERIMENTAL] Fixed TCP port for the proxy's loopback listener (proxied-server mode only). Default 0 = an OS-assigned free port. Startup fails if the port is already in use. |
| `--proxied-server-root-path` |  | string | [EXPERIMENTAL] Absolute directory holding the proxied dolt sql-server's lockfiles, pidfiles, and child .dolt repository (proxied-server mode only). Default: <beadsDir>/dolt. May not exist yet — bd will create it. Relative paths are rejected. |
| `--quiet` | `-q` |  | Suppress output (quiet mode) |
| `--reinit-local` |  |  | Re-initialize local .beads/ over existing local data. Does NOT authorize remote divergence; see --discard-remote. |
| `--remote` |  | string | Dolt remote URL to clone from and persist as sync.remote |
| `--role` |  | string | Set beads role without prompting: "maintainer" or "contributor" |
| `--server` |  |  | Use external dolt sql-server instead of embedded engine |
| `--server-host` |  | string | Dolt server host (default: 127.0.0.1) |
| `--server-port` |  | int | Dolt server port (default: 3307) |
| `--server-socket` |  | string | Unix domain socket path (overrides host/port; pass '' to ignore an ambient BEADS_DOLT_SERVER_SOCKET and use TCP) |
| `--server-tls` |  |  | Require TLS for the init-time Dolt server connection (overrides BEADS_DOLT_SERVER_TLS for this run; not persisted - set the env var or credentials file for later commands) |
| `--server-user` |  | string | Dolt server MySQL user (default: root) |
| `--setup-exclude` |  |  | Configure .git/info/exclude to keep beads files local (for forks) |
| `--shared-server` |  |  | Enable shared Dolt server mode (all projects share one server at ~/.beads/shared-server/) |
| `--skip-agents` |  |  | Skip AGENTS.md and Claude/Codex/Cursor setup generation |
| `--skip-hooks` |  |  | Skip git hooks installation |
| `--stealth` |  |  | Enable stealth mode: global gitattributes and gitignore, no local repo tracking |
| `--team` |  |  | Run team workflow setup wizard |
| `--team-server` |  |  | [EXPERIMENTAL] The shared database's schema is managed by beads-team-server (bts): bd never creates the database or runs schema migrations, only verifies the schema version (proxied-server mode only). Not related to --team. |

Local definitions override the global flags `--quiet` for this command.

<a id="bd-kv"></a>

## `bd kv`

```text
Commands for working with the beads key-value store.

The key-value store is useful for storing flags, environment variables,
or other user-defined data that persists across sessions.
```

**Usage**

```text
bd kv [command]
```

**Available Commands**

- [`clear`](#bd-kv-clear) — Delete a key-value pair
- [`get`](#bd-kv-get) — Get a value by key
- [`list`](#bd-kv-list) — List all key-value pairs
- [`set`](#bd-kv-set) — Set a key-value pair

**Examples**

```text
  bd kv set mykey myvalue    # Set a value
  bd kv get mykey            # Get a value
  bd kv clear mykey          # Delete a key
  bd kv list                 # List all key-value pairs
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for kv |

<a id="bd-kv-clear"></a>

### `bd kv clear`

```text
Delete a key from the beads key-value store.
```

**Usage**

```text
bd kv clear <key> [flags]
```

**Examples**

```text
  bd kv clear feature_flag
  bd kv clear api_endpoint
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for clear |

<a id="bd-kv-get"></a>

### `bd kv get`

```text
Get a value from the beads key-value store.
```

**Usage**

```text
bd kv get <key> [flags]
```

**Examples**

```text
  bd kv get feature_flag
  bd kv get api_endpoint
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for get |

<a id="bd-kv-list"></a>

### `bd kv list`

```text
List all key-value pairs in the beads key-value store.
```

**Usage**

```text
bd kv list [flags]
```

**Examples**

```text
  bd kv list
  bd kv list --json
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-kv-set"></a>

### `bd kv set`

```text
Set a key-value pair in the beads key-value store.

This is useful for storing flags, environment variables, or other
user-defined data that persists across sessions.
```

**Usage**

```text
bd kv set <key> <value> [flags]
```

**Examples**

```text
  bd kv set feature_flag true
  bd kv set api_endpoint https://api.example.com
  bd kv set max_retries 3
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for set |

<a id="bd-memories"></a>

## `bd memories`

```text
List all memories, or search by keyword.
```

**Usage**

```text
bd memories [search] [flags]
```

**Examples**

```text
  bd memories              # list all memories
  bd memories dolt         # search for memories about dolt
  bd memories "race flag"  # search for a phrase
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for memories |

<a id="bd-migrate-personal"></a>

## `bd migrate-personal`

```text
Identify issues you created in the project database and move them to your
personal planning repository (~/.beads-planning by default).

This is a one-time migration for contributors who created personal planning
issues before contributor routing was configured.

The command:
  1. Finds all issues in the project database created by your git identity
  2. Shows you the list and asks for confirmation
  3. Moves them to the planning repo configured in routing.contributor

EXAMPLES:
  bd migrate-personal        # Interactive: show list and prompt
  bd migrate-personal -y     # Non-interactive: skip confirmation
```

**Usage**

```text
bd migrate-personal [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for migrate-personal |
| `--yes` | `-y` |  | Skip confirmation prompt |

<a id="bd-onboard"></a>

## `bd onboard`

```text
Display a minimal snippet to add to your agent instructions file for bd integration.

By default, the agent instructions file is AGENTS.md. Use 'bd init --agents-file'
to configure a different filename (e.g. BEADS.md).

This outputs a small (~10 line) snippet that points to 'bd prime' for full
workflow context. This is the same minimal profile that 'bd init' generates
by default. This approach:

  • Keeps your agent file lean (doesn't bloat with instructions)
  • bd prime provides dynamic, always-current workflow details
  • Hooks auto-inject bd prime at session start

For agents or environments that do not auto-inject hook output, use
'bd init --agents-profile=full' to embed the complete command reference.
```

**Usage**

```text
bd onboard [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for onboard |

<a id="bd-prime"></a>

## `bd prime`

```text
Output essential Beads workflow context in AI-optimized markdown format.

Automatically detects if MCP server is active and adapts output:
- MCP mode: Brief workflow reminders (~50 tokens)
- CLI mode: Full command reference (~1-2k tokens)

Designed for Claude Code, Gemini CLI, and Codex SessionStart hooks to prevent
agents from forgetting bd workflow after context compaction.

Config options:
- no-git-ops: When true, outputs stealth mode (no git commands in session close protocol).
  Set via: bd config set no-git-ops true
  Useful when you want to control when commits happen manually.
- agent.profile: Explicit policy profile for git/commit authority wording
  (conservative | minimal | team-maintainer; default conservative).
  Set via: bd config set agent.profile team-maintainer
  Or per-session: BD_AGENT_PROFILE=team-maintainer (env var takes precedence).
  See docs/getting-started/ide-setup.md#policy-profiles for what each profile means.

	Workflow customization:
	- Place a .beads/PRIME.md file in the local clone or resolved workspace to override the default workflow text. Persistent memories (from bd remember) are still appended so memory injection keeps working under a custom template.
	- Use --export to dump the default content for customization.
	- Use --memories-only for hook contexts that should inject only persistent memories; this returns only the memories section even when a custom PRIME.md is present.
	- Use --no-memories to omit the persistent memories section (useful when the memories section is large and would dominate a context budget). --memories-only takes precedence if both are set.

Memory injection caps:
	Large memory sets can exceed what a session-start hook host will ingest,
	and hosts truncate silently. Cap what prime injects with --max-memories N
	and/or --max-memory-chars N (or the prime.max-memories /
	prime.max-memory-chars config keys; an explicit flag wins, and an explicit
	0 forces unlimited). Caps apply at whole-memory boundaries, at least one
	memory is always emitted, and a banner ahead of the entries reports how
	many were elided and how to browse the rest with bd memories.
	--max-memory-chars caps the total bytes of the injected memory entries;
	the section header and elision banner are excluded from the budget.
```

**Usage**

```text
bd prime [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--export` |  |  | Output default content (ignores PRIME.md override) |
| `--full` |  |  | Force full CLI output (ignore MCP detection) |
| `--help` | `-h` |  | help for prime |
| `--hook-json` |  |  | Wrap output in the SessionStart hook JSON envelope (Claude Code, Gemini CLI, Codex) |
| `--max-memories` |  | int | Cap injected persistent memories to N entries (0 = unlimited; falls back to the prime.max-memories config key) |
| `--max-memory-chars` |  | int | Cap the total bytes of injected memory entries, at whole-memory boundaries; section header and banner are not counted (0 = unlimited; falls back to the prime.max-memory-chars config key) |
| `--mcp` |  |  | Force MCP mode (minimal output) |
| `--memories-only` |  |  | Output only persistent memories for compact hook contexts |
| `--no-memories` |  |  | Omit the persistent memories section (ignored when --memories-only is set, which wins) |
| `--stealth` |  |  | Stealth mode (no git operations, flush only) |

<a id="bd-quickstart"></a>

## `bd quickstart`

```text
Display a quick start guide showing common bd workflows and patterns.
```

**Usage**

```text
bd quickstart [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for quickstart |

<a id="bd-recall"></a>

## `bd recall`

```text
Retrieve the full content of a memory by its key.
```

**Usage**

```text
bd recall <key> [flags]
```

**Examples**

```text
  bd recall dolt-phantoms
  bd recall auth-jwt
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for recall |

<a id="bd-remember"></a>

## `bd remember`

```text
Store a memory that persists across sessions and account rotations.

Memories are injected at prime time (bd prime) so you have them
in every session without manual loading.

The positional arg is the memory CONTENT (the key is auto-generated from it
unless --key is given). As a convenience, if the arg is a bare key naming an
existing memory, it is RECALLED instead of stored (same as 'bd recall');
a bare key naming nothing is refused. Use --key to store slug-like content.
```

**Usage**

```text
bd remember "<insight>" [flags]
```

**Examples**

```text
  bd remember "always run tests with -race flag"
  bd remember "Dolt phantom DBs hide in three places" --key dolt-phantoms
  bd remember "auth module uses JWT not sessions" --key auth-jwt
  bd remember dolt-phantoms        # bare existing key: reads it (= bd recall)
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for remember |
| `--key` |  | string | Explicit key for the memory (auto-generated from content if not set). If a memory with this key already exists, it will be updated in place |

<a id="bd-setup"></a>

## `bd setup`

```text
Setup integration files for AI editors and coding assistants.

Recipes define where beads workflow instructions are written. Built-in recipes
include cursor, claude, copilot, gemini, aider, factory, codex, mux, opencode, junie, kiro, windsurf, cody, and kilocode.
```

**Usage**

```text
bd setup [recipe] [flags]
```

**Examples**

```text
  bd setup cursor          # Install Cursor IDE integration (rules + agent hooks)
  bd setup cursor --global # Install global Cursor hooks (~/.cursor/hooks.json)
  bd setup kiro            # Install Kiro steering guidance
  bd setup codex           # Install Codex skill + AGENTS.md guidance + native hooks
  bd setup codex --global  # Install global Codex skill + guidance + native hooks
  bd setup copilot         # Install Copilot CLI plugin + repository instructions
  bd setup mux --project   # Install Mux workspace layer (.mux/AGENTS.md)
  bd setup mux --global    # Install Mux global layer (~/.mux/AGENTS.md)
  bd setup mux --project --global  # Install both Mux layers
  bd setup --list          # Show all available recipes
  bd setup --print         # Print the template to stdout
  bd setup -o rules.md     # Write template to custom path
  bd setup --add myeditor .myeditor/rules.md  # Add custom recipe

Use 'bd setup <recipe> --check' to verify installation status.
Use 'bd setup <recipe> --remove' to uninstall.
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--add` |  | string | Add a custom recipe with given name |
| `--check` |  |  | Check if integration is installed |
| `--global` |  |  | Install globally (claude/codex/cursor/mux; writes to ~/.claude/settings.json, $CODEX_HOME/AGENTS.md or ~/.codex/AGENTS.md, ~/.cursor/hooks.json, or ~/.mux/AGENTS.md) |
| `--help` | `-h` |  | help for setup |
| `--list` |  |  | List all available recipes |
| `--output` | `-o` | string | Write template to custom path |
| `--print` |  |  | Print the template to stdout |
| `--project` |  |  | Install for this project only (gemini/mux) |
| `--remove` |  |  | Remove the integration |
| `--stealth` |  |  | Use stealth mode (claude/gemini) |

Local definitions override the global flags `--global` for this command.

<a id="bd-where"></a>

## `bd where`

```text
Show the active beads database location, including redirect information.

	This command is useful for debugging when using redirects, to understand
	which beads workspace is actually being used.
```

**Usage**

```text
bd where [flags]
```

**Examples**

```text
  bd where           # Show active beads location
  bd where --json    # Output in JSON format
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for where |

<a id="bd-batch"></a>

## `bd batch`

```text
Run multiple write operations in a single database transaction.

Commands are read from stdin (one per line) or from a file via -f/--file.
All operations execute inside a single dolt transaction: on any error the
whole batch is rolled back, otherwise it is committed with one DOLT_COMMIT.

This is intended for shell scripts that currently invoke 'bd' many times in
a loop, which causes severe write amplification on a dolt sql-server backed
by btrfs+compression. Batching collapses N invocations into one transaction
and one dolt commit.

Grammar (one command per line):
  close <id> [reason...]
  update <id> <key>=<value> [<key>=<value> ...]
  create <type> <priority> <title...>
  dep add <from-id> <to-id> [type]
  dep remove <from-id> <to-id>
  #comment  (blank lines and '# ...' comments are ignored)

Supported 'update' keys: status, priority, title, assignee, force
Supported dependency types: see 'bd dep add --help' (default: blocks)

'force' is not a field. An update whose status moves the issue into closed
(or a configured done status) is refused when it still has open children or
a live blocker, the same as 'bd close'; 'force=true' overrides that refusal.
Because the batch is one transaction, an unforced refusal rolls back EVERY
operation in the batch, not just the offending line. Note the asymmetry with
'close <id>', which does not apply that policy at all.

Tokens are whitespace-separated. Double-quoted strings ("like this") may
contain spaces; use \" to embed a quote and \\ for a backslash.
```

**Usage**

```text
bd batch [flags]
```

**Examples**

```text
  # From a pipe
  bd list --status stale -q | awk '{print "close",$1," stale"}' | bd batch

  # From a file
  bd batch -f operations.txt

  # Inline
  printf 'close bd-1 done\nupdate bd-2 status=in_progress\n' | bd batch

On success, exits 0 and prints a summary (or JSON with --json). On any error,
rolls back the entire transaction and exits non-zero with the failing line.

NOTE: This is a narrow subset. Commands like 'show', 'list', 'ready', 'sync',
complex create flows, or any flag not listed above are NOT accepted. Use
normal 'bd' subcommands for interactive/read operations.
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Parse input and echo commands without executing |
| `--file` | `-f` | string | Read commands from file instead of stdin |
| `--help` | `-h` |  | help for batch |
| `--message` | `-m` | string | DOLT_COMMIT message (default: 'bd: batch N ops by <actor>') |

<a id="bd-compact"></a>

## `bd compact`

```text
Squash Dolt commits older than N days into a single commit.

Recent commits (within the retention window) are preserved via cherry-pick.
This reduces Dolt storage overhead from auto-commit history while keeping
recent change tracking intact.

For semantic issue compaction (summarizing closed issues), use 'bd admin compact'.
For full history squash, use 'bd flatten'.

How it works:
  1. Identifies commits older than --days threshold
  2. Creates a squashed base commit from all old history
  3. Cherry-picks recent commits on top
  4. Swaps main branch to the compacted version
  5. Prunes remote-tracking refs (they would keep the old history alive;
     the next push or fetch re-creates them at the new tip)
  6. Runs a full Dolt GC (all storage generations) to reclaim the old history

The GC pass is a full collection: Dolt storage is generational, and a default
GC never revisits data an earlier GC moved to the old generation. On any store
that has been GC'd before (bd gc, or a previous flatten or compact), only a
full collection reclaims the squashed history. A full GC can take minutes on
multi-gigabyte stores.
```

**Usage**

```text
bd compact [flags]
```

**Examples**

```text
  bd compact --dry-run               # Preview: show commit breakdown
  bd compact --force                 # Squash commits older than 30 days
  bd compact --days 7 --force        # Keep only last 7 days of history
  bd compact --days 90 --force       # Conservative: squash 90+ day old commits
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--days` |  | int | Keep commits newer than N days (default 30) |
| `--dry-run` |  |  | Preview without making changes |
| `--force` | `-f` |  | Confirm commit squash |
| `--help` | `-h` |  | help for compact |

<a id="bd-doctor"></a>

## `bd doctor`

```text
Sanity check the beads installation for the current directory or specified path.

This command checks:
  - If .beads/ directory exists
  - Database version and migration status
  - Schema compatibility (all required tables and columns present)
  - Whether using hash-based vs sequential IDs
  - If CLI version is current (checks GitHub releases)
  - If Claude plugin is current (when running in Claude Code)
  - File permissions
  - Circular dependencies
  - Git hooks (pre-commit, post-merge, pre-push)
  - .beads/.gitignore up to date
  - Metadata.json version tracking (LastBdVersion field)

Storage Availability:
  Full diagnostics, --perf, --deep, --server, --migration, and
  --check=validate currently require Dolt server mode. Embedded Dolt
  supports --check=artifacts, --check=conventions, and
  --check=pollution. --check-health has a limited hook-health fallback.
  Unsupported combinations return a notice without changing storage.

Performance Mode (--perf):
  Run performance diagnostics on your database:
  - Times key operations (bd ready, bd list, bd show, etc.)
  - Collects system info (OS, arch, database stats)
  - Generates CPU profile for analysis
  - Outputs shareable report for bug reports

Export Mode (--output):
  Save diagnostics to a JSON file for historical analysis and bug reporting.
  Includes timestamp and platform info for tracking intermittent issues.

Specific Check Mode (--check):
  Run a specific check in detail. Available checks:
  - artifacts: Detect and optionally clean beads classic artifacts
    (stale JSONL, SQLite files, cruft .beads dirs). Use with --clean.
  - conventions: Check for convention drift (lint warnings, stale
    issues, orphaned issues). Advisory only - warns, never blocks.
  - pollution: Detect and optionally clean test issues from database
  - validate: Run focused data-integrity checks (duplicates, orphaned
    deps, test pollution, git conflicts). Use with --fix to auto-repair.

Deep Validation Mode (--deep):
  Validate full graph integrity. May be slow on large databases.
  Additional checks:
  - Parent consistency: All parent-child deps point to existing issues
  - Dependency integrity: All deps reference valid issues
  - Epic completeness: Find epics ready to close (all children closed)
  - Agent bead integrity: Agent beads have valid state values
  - Mail thread integrity: Thread IDs reference existing issues
  - Molecule integrity: Molecules have valid parent-child structures

Server Mode (--server):
  Run health checks for Dolt server mode connections (bd-dolt.2.3):
  - Server reachable: Can connect to configured host:port?
  - Dolt version: Is it a Dolt server (not vanilla MySQL)?
  - Database exists: Does the 'beads' database exist?
  - Schema compatible: Can query beads tables?
  - Connection pool: Pool health metrics

Legacy Dolt Migration Validation Mode (--migration):
  Retained for older SQLite-to-Dolt migration workflows and available only in
  Dolt server mode. It is not the migration path for removed backends
  (PostgreSQL, MySQL, SQLite); those fail closed with export/import guidance.
  Combine
  with --json for machine-parseable diagnostic output.

Agent Mode (--agent):
  Output diagnostics designed for AI agent consumption. Instead of terse
  pass/fail messages, each issue includes:
  - Observed state: what the system actually looks like
  - Expected state: what it should look like
  - Explanation: full prose context about the issue and why it matters
  - Commands: exact remediation commands to run
  - Source files: where in the codebase to investigate further
  - Severity: blocking (prevents operation), degraded (partial function),
    or advisory (informational only)
  ZFC-compliant: Go observes and reports, the agent decides and acts.
  Combine with --json for structured agent-facing output.

Suppressing Warnings:
  Suppress specific warnings by setting doctor.suppress.<check-slug> config:
    bd config set doctor.suppress.pending-migrations true
    bd config set doctor.suppress.git-hooks true
  Check names are converted to slugs: "Git Hooks" → "git-hooks".
  Only warnings are suppressed; errors and passing checks always show.
  To unsuppress: bd config unset doctor.suppress.<slug>
```

**Usage**

```text
bd doctor [path] [flags]
```

**Examples**

```text
  bd doctor              # Check current directory
  bd doctor /path/to/repo # Check specific repository
  bd doctor --json       # Machine-readable output
  bd doctor --agent      # Agent-facing diagnostic output
  bd doctor --agent --json  # Structured agent diagnostics (JSON)
  bd doctor --fix        # Automatically fix issues (with confirmation)
  bd doctor --fix --yes  # Automatically fix issues (no confirmation)
  bd doctor --fix -i     # Confirm each fix individually
  bd doctor --fix --fix-child-parent  # Also fix child→parent deps (opt-in)
  bd doctor --fix --force # Force repair even when database can't be opened
  bd doctor --fix --source=jsonl # Rebuild database from a JSONL export
  bd doctor --dry-run    # Preview what --fix would do without making changes
  bd doctor --perf       # Performance diagnostics
  bd doctor --output diagnostics.json  # Export diagnostics to file
  bd doctor --check=artifacts           # Show classic artifacts (JSONL, SQLite, cruft dirs)
  bd doctor --check=artifacts --clean  # Delete safe-to-delete artifacts (with confirmation)
  bd doctor --check=conventions        # Convention drift check (lint, stale, orphans)
  bd doctor --check=pollution          # Show potential test issues
  bd doctor --check=pollution --clean  # Delete test issues (with confirmation)
  bd doctor --check=validate         # Data-integrity checks only
  bd doctor --check=validate --fix   # Auto-fix data-integrity issues
  bd doctor --deep             # Full graph integrity validation
  bd doctor --server           # Dolt server mode health checks
  bd doctor --migration=pre    # Legacy Dolt-server migration diagnostic
  bd doctor --migration=post   # Legacy Dolt-server completion diagnostic
  bd doctor --migration=pre --json  # Machine-parseable legacy diagnostic
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--agent` |  |  | Agent-facing diagnostic mode: rich context for AI agents (ZFC-compliant) |
| `--check` |  | string | Run specific check in detail (e.g., 'pollution') |
| `--check-health` |  |  | Quick health check for git hooks (silent on success) |
| `--clean` |  |  | For pollution check: delete detected test issues |
| `--deep` |  |  | Validate full graph integrity |
| `--dry-run` |  |  | Preview fixes without making changes |
| `--fix` |  |  | Automatically fix issues where possible |
| `--fix-child-parent` |  |  | Remove child→parent dependencies (opt-in) |
| `--help` | `-h` |  | help for doctor |
| `--interactive` | `-i` |  | Confirm each fix individually |
| `--migration` |  | string | Run legacy Dolt-server migration diagnostics: 'pre' or 'post' |
| `--orchestrator` |  |  | Running in orchestrator multi-workspace mode (routes.jsonl is expected, higher duplicate tolerance) |
| `--orchestrator-duplicates-threshold` |  | int | Duplicate tolerance threshold for orchestrator mode (wisps are ephemeral) (default 1000) |
| `--output` | `-o` | string | Export diagnostics to JSON file |
| `--perf` |  |  | Run performance diagnostics and generate CPU profile |
| `--server` |  |  | Run Dolt server mode health checks (connectivity, version, schema) |
| `--verbose` | `-v` |  | Show all checks (default shows only warnings/errors) |
| `--yes` | `-y` |  | Skip confirmation prompt (for non-interactive use) |

Local definitions override the global flags `--verbose` for this command.

<a id="bd-events"></a>

## `bd events`

```text
Read and manage the durable events journal (bd_events_journal).

The journal records every committed issue mutation as an ordered, replayable
row. Enable it with 'bd config set events-journal true' (or
BD_EVENTS_JOURNAL=1). Records are emitted only while it is enabled.

Retention is automatic: an enabled journal is bounded to the retention floors
(events-journal-retain-days / -rows, 7 days / 100k rows by default) without
anyone running a command. Disable both floors for an unbounded ledger, or
events-journal-auto-prune for manual control; 'bd events prune' remains for an
earlier, on-demand cut below the floors.

Coverage and scope:
  - Every mutation through bd's normal write paths (create, update, close,
    reopen, delete, claim, dependency add/remove, label add/remove, comment) is
    journaled in the same transaction as the change. Raw DML run through
    'bd sql' bypasses those paths and is NOT journaled — a known non-coverage.
  - The journal is per-branch working-set state (dolt_ignored): it records the
    mutations committed on the writer's active branch. Rows arrive by direct
    write, not by merge, so a consumer must read the journal on the same branch
    the writer commits to; a branch checkout or merge does not carry journal
    rows across branches.
  - For the same reason the journal is per REPLICA. 'bd dolt pull' and the
    changes a merge settles into this clone are not journaled: those rows
    arrived as data, not as local mutations, and nothing on this clone wrote
    them through the mutation seam. A consumer that mirrors a synced workspace
    must re-baseline (a fresh export or a full re-read) after a sync, because
    the journal describes only what THIS clone mutated.
    Each replica also has its OWN seq space, counted from its own first
    mutation. A checkpoint taken against one replica is meaningless against
    another — the same seq names a different record, and a seq above the other
    replica's head reads as "caught up" and stalls forever. Track a checkpoint
    per replica, and re-baseline rather than carry one across.
  - A few writes that happen while a store is being OPENED are unjournaled by
    design: schema migrations and the version reconciliation that runs before
    the workspace's configuration has been applied to the store. They touch
    schema and clone-local metadata, never a bead, so a replaying consumer has
    nothing to apply them to.
  - Dependency records are not symmetric, in two ways.
    Count: a dep_add is emitted for every accepted add, INCLUDING an idempotent
    same-type re-add that only refreshes the edge's metadata. The audit 'events'
    table deduplicates that case and writes nothing; the journal does not. Treat
    dep_add as an upsert of the edge, not as proof the edge is new. A dep_remove
    naming an edge that is already gone emits nothing at all.
    Payload: dep.metadata differs in provenance between the two ops. On dep_add
    it is the value being written, as the caller supplied it; on dep_remove it is
    the raw stored column read back just before the delete. The two can differ
    byte for byte while meaning the same thing, so compare parsed values.

Structural dependency edits — the ones bd wires up itself rather than a 'bd dep'
verb — write no audit event but DO journal, by design: a replaying consumer
needs the edge either way.
```

**Usage**

```text
bd events [command]
```

**Available Commands**

- [`export`](#bd-events-export) — Print the entire journal from the beginning (JSON lines)
- [`prune`](#bd-events-prune) — Delete journal records below a sequence number (retention)
- [`tail`](#bd-events-tail) — Print journal records after a sequence number (JSON lines)

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for events |

<a id="bd-events-export"></a>

### `bd events export`

```text
Print every events journal record from seq 1, in order, as JSON lines.

Equivalent to 'bd events tail --since 0'. Like tail, it FAILS rather than
present a pruned journal's surviving suffix as a complete history.
```

**Usage**

```text
bd events export [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for export |
| `--limit` |  | int | maximum number of records to return (0 = no limit) |

<a id="bd-events-prune"></a>

### `bd events prune`

```text
Delete events journal records with seq less than --before.

Retention is already enforced automatically: after a mutating command commits,
and on a timer in 'bd serve', bd deletes everything the floors below do not
protect. This command is for an EARLIER, on-demand cut BELOW the floors — after
a consumer has durably processed a span you do not want to wait out. It cannot
cut deeper than the floors: shrinking the retained window itself means lowering
them. The journal is clone-local operational state, so pruning never affects
issue data.

Two retention floors compose onto --before and can only reduce what a prune
removes. They bound the automatic prune and this one identically:
  events-journal-retain-days   keep every row younger than N days (default 7)
  events-journal-retain-rows   always keep the newest N rows (default 100000)

Set BOTH floors to 0 for an unbounded ledger: automatic pruning then does
nothing, and this command becomes the only thing that deletes a record. To keep
the floors but own deletion yourself, set events-journal-auto-prune false.

Note the floors are time-based and count-based — they are NOT a consumer
watermark. They protect only the recent window; a consumer that has fallen
further behind than both floors allow will be pruned past and lose records.
Consumers are responsible for tracking their own watermark (the highest seq they
have durably processed) and for sizing the floors to the longest outage they
intend to survive. Pruned history cannot be recovered from the workspace — the
journal is the only local copy. Pruning frees rows, not disk: pair it with
'dolt gc' to reclaim the space, since the table is working-set (dolt_ignored)
state that ordinary Dolt commits never garbage-collect.
```

**Usage**

```text
bd events prune [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--before` |  | int | delete records with seq less than this value |
| `--help` | `-h` |  | help for prune |

<a id="bd-events-tail"></a>

### `bd events tail`

```text
Print events journal records with seq greater than --since, in order.

Each line is a JSON record:
  {"seq":N,"ts":"...","op":"create|update|close|delete|dep_add|dep_remove|comment",
   "issue_id":"...","actor":"...","issue":{...|null},"dep":{"kind":..,"target":..,"metadata":..},"comment":{...}}

Record contract (stable for external consumers):
  seq       int64   counter-assigned inside the mutation's transaction; gapless,
                    strictly increasing in commit order, never reused or reset
  ts        string  UTC insert time, stamped inside the committing transaction
  op        string  one of the seven ops above
  issue_id  string  the mutated issue's id
  actor     string  the acting identity that performed the mutation, as resolved
                    for the audit-events table (on a comment row: the comment's
                    author). A delete — and the dep_remove rows a cascading
                    delete produces — carries the identity that REQUESTED it.
                    Empty (omitted) only when the path genuinely has no actor:
                    derived maintenance, system cleanup with no request behind
                    it, and rows older than the column. Never user attribution
                    when empty.
  issue     object  full issue state AFTER the mutation; null on delete
  dep       object  {"kind","target","metadata"} for dep_add / dep_remove; omitted otherwise
  comment   object  {"id","author","text","created_at","source"} for comment; omitted otherwise

Poll with the highest seq seen to consume new mutations incrementally, or pass
--follow to keep printing new records as they are committed (Ctrl-C to stop).

Retention boundary: if --since is below the oldest retained record — the prefix
you asked for was pruned — the read FAILS instead of silently skipping ahead or
returning an empty success. With --json the failure carries
{"code":"events_journal_truncated","since":N,"floor":F,"head":H}: floor is the
oldest seq still retained, head the highest ever assigned. Resume from floor-1
to continue with a known gap, or rebuild from a full export.
```

**Usage**

```text
bd events tail [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--follow` |  |  | keep printing new records as they are committed (Ctrl-C to stop) |
| `--help` | `-h` |  | help for tail |
| `--limit` |  | int | maximum number of records to return (0 = no limit) |
| `--since` |  | int | return records with seq greater than this value |

<a id="bd-flatten"></a>

## `bd flatten`

```text
Nuclear option: squash ALL Dolt commit history into a single commit.

This uses the Tim Sehn recipe:
  1. Create a new branch from the current state
  2. Soft-reset to the initial commit (preserving all data)
  3. Commit everything as a single snapshot
  4. Swap main branch to the new flattened branch
  5. Prune remote-tracking refs (they would keep the old history alive;
     the next push or fetch re-creates them at the new tip)
  6. Run a full Dolt GC (all storage generations) to reclaim the old history

The GC pass is a full collection: Dolt storage is generational, and a default
GC never revisits data an earlier GC moved to the old generation. On any store
that has been GC'd before (bd gc, or a previous flatten or compact), only a
full collection reclaims the squashed history. A full GC can take minutes on
multi-gigabyte stores.

This is irreversible — all commit history is lost. The resulting database
has exactly one commit containing all current data.

Use this when:
  - Your .beads/dolt directory has grown very large
  - You don't need commit-level history (time travel)
  - You want to start fresh with minimal storage
```

**Usage**

```text
bd flatten [flags]
```

**Examples**

```text
  bd flatten --dry-run               # Preview: show commit count and disk usage
  bd flatten --force                 # Actually squash all history
  bd flatten --force --json          # JSON output
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview without making changes |
| `--force` | `-f` |  | Confirm irreversible history squash |
| `--help` | `-h` |  | help for flatten |

<a id="bd-gc"></a>

## `bd gc`

```text
Full lifecycle garbage collection for standalone Beads databases.

Runs three phases in sequence:
  1. DECAY   — Delete closed issues older than N days (default 90)
  2. COMPACT — Squash old Dolt commits into fewer commits (bd compact)
  3. GC      — Run Dolt garbage collection to reclaim disk space

Each phase can be skipped individually. Use --dry-run to preview all phases
without making changes.

Phase 3 runs Dolt's default, generational GC: it only examines data written
since the last GC. Data that survived an earlier GC lives in the old generation
and is never revisited, so on a long-lived store the space freed by decay may
not be reclaimed. Use --full to collect all generations (slower on large
stores).
```

**Usage**

```text
bd gc [flags]
```

**Examples**

```text
  bd gc                              # Full GC with defaults (90 day decay)
  bd gc --dry-run                    # Preview what would happen
  bd gc --older-than 30              # Decay issues closed 30+ days ago
  bd gc --skip-decay                 # Skip issue deletion, just compact+GC
  bd gc --skip-dolt                  # Skip Dolt GC, just decay+compact
  bd gc --full                       # Collect all storage generations
  bd gc --force                      # Skip confirmation prompt
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview without making changes |
| `--force` | `-f` |  | Skip confirmation prompts |
| `--full` |  |  | Run a full Dolt GC (all generations; slower, reclaims space default passes cannot) |
| `--help` | `-h` |  | help for gc |
| `--older-than` |  | int | Delete closed issues older than N days (default 90) |
| `--skip-decay` |  |  | Skip issue deletion phase |
| `--skip-dolt` |  |  | Skip Dolt garbage collection phase |

<a id="bd-migrate"></a>

## `bd migrate`

```text
Database migration and data transformation commands.

Without subcommand, checks and updates database metadata to current version.
```

**Usage**

```text
bd migrate [flags]
bd migrate [command]
```

**Subcommands**

- [`hooks`](#bd-migrate-hooks) — Plan git hook migration to marker-managed format
- [`issues`](#bd-migrate-issues) — Move issues between repositories
- [`schema`](#bd-migrate-schema) — Apply pending schema migrations (idempotent)
- [`sync`](#bd-migrate-sync) — Set up sync.branch workflow for multi-clone setups
- [`from-server-to-proxied-server`](#bd-migrate-from-server-to-proxied-server) — [EXPERIMENTAL] Switch server mode to proxied-server mode
- [`from-proxied-server-to-server`](#bd-migrate-from-proxied-server-to-server) — [EXPERIMENTAL] Switch proxied-server mode to server mode
- [`from-shared-server-to-proxied-server`](#bd-migrate-from-shared-server-to-proxied-server) — [EXPERIMENTAL] Switch shared-server mode to proxied-server mode
- [`from-proxied-server-to-shared-server`](#bd-migrate-from-proxied-server-to-shared-server) — [EXPERIMENTAL] Switch proxied-server mode to shared-server mode

**Available Commands**

- [`legacy-sqlite`](#bd-migrate-legacy-sqlite) — Read an authenticated legacy SQLite database as JSONL

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would be done without making changes |
| `--force` |  |  | Bypass the remote-migrate gate as the single designated migrator (equivalent to BD_ALLOW_REMOTE_MIGRATE=1) |
| `--help` | `-h` |  | help for migrate |
| `--inspect` |  |  | Show migration plan and database state for AI agent analysis |
| `--json` |  |  | Output migration statistics in JSON format |
| `--update-repo-id` |  |  | Update repository ID (use after changing git remote) |
| `--yes` |  |  | Auto-confirm prompts |

Local definitions override the global flags `--json` for this command.

<a id="bd-migrate-hooks"></a>

### `bd migrate hooks`

```text
Analyze git hook files and sidecar artifacts for migration to marker-managed format.

Modes:
  --dry-run  Preview migration operations without changing files
  --apply    Apply migration operations
```

**Usage**

```text
bd migrate hooks [path] [flags]
```

**Examples**

```text
  bd migrate hooks --dry-run
  bd migrate hooks --apply
  bd migrate hooks --apply --yes
  bd migrate hooks --dry-run --json
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--apply` |  |  | Apply planned hook migration changes |
| `--dry-run` |  |  | Show what would be done without making changes |
| `--help` | `-h` |  | help for hooks |
| `--json` |  |  | Output in JSON format |
| `--yes` |  |  | Skip confirmation prompt for --apply |

Local definitions override the global flags `--json` for this command.

<a id="bd-migrate-issues"></a>

### `bd migrate issues`

```text
Move issues from one source repository to another with filtering and dependency preservation.

This command updates the source_repo field for selected issues, allowing you to:
- Move contributor planning issues to upstream repository
- Reorganize issues across multi-phase repositories
- Consolidate issues from multiple repos
```

**Usage**

```text
bd migrate issues [flags]
```

**Examples**

```text
  # Preview migration from planning repo to current repo
  bd migrate-issues --from ~/.beads-planning --to . --dry-run

  # Move all open P1 bugs
  bd migrate-issues --from ~/repo1 --to ~/repo2 --priority 1 --type bug --status open

  # Move specific issues with their dependencies
  bd migrate-issues --from . --to ~/archive --id bd-abc --id bd-xyz --include closure

  # Move issues with label filter
  bd migrate-issues --from . --to ~/feature-work --label frontend --label urgent
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show plan without making changes |
| `--from` |  | string | Source repository (required) |
| `--help` | `-h` |  | help for issues |
| `--id` |  | strings | Specific issue IDs to migrate (can specify multiple) |
| `--ids-file` |  | string | File containing issue IDs (one per line) |
| `--include` |  | string | Include dependencies: none/upstream/downstream/closure (default "none") |
| `--label` |  | strings | Filter by labels (can specify multiple) |
| `--priority` |  | int | Filter by priority (0-4) (default -1) |
| `--status` |  | string | Filter by status (open/closed/all) |
| `--strict` |  |  | Fail on orphaned dependencies or missing repos |
| `--to` |  | string | Destination repository (required) |
| `--type` |  | string | Filter by issue type (bug/feature/task/epic/chore/decision) |
| `--within-from-only` |  |  | Only include dependencies from source repo (default true) |
| `--yes` |  |  | Skip confirmation prompt |

<a id="bd-migrate-schema"></a>

### `bd migrate schema`

```text
Apply pending schema migrations idempotently.

Schema migrations also run automatically on store open, so this subcommand
is typically a no-op. It exists to make migration explicit and observable
in CI, release gates, and recovery scenarios.

Example:
  bd migrate schema
  bd migrate schema --json
```

**Usage**

```text
bd migrate schema [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force` |  |  | Bypass the remote-migrate gate as the single designated migrator (equivalent to BD_ALLOW_REMOTE_MIGRATE=1) |
| `--help` | `-h` |  | help for schema |
| `--json` |  |  | Output in JSON format |

Local definitions override the global flags `--json` for this command.

<a id="bd-migrate-sync"></a>

### `bd migrate sync`

```text
Configure separate branch workflow for multi-clone setups.

This sets the sync.branch config value so that issue data is committed
to a dedicated branch, keeping your main branch clean.

Example:
  bd migrate sync beads-sync
```

**Usage**

```text
bd migrate sync <branch> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would be done without making changes |
| `--help` | `-h` |  | help for sync |
| `--json` |  |  | Output in JSON format |

Local definitions override the global flags `--json` for this command.

<a id="bd-migrate-from-server-to-proxied-server"></a>

### `bd migrate from-server-to-proxied-server`

```text
Switch a repo from server mode (bd init --server) to proxied-server mode.

Both modes root their dolt sql-server at the same .beads/dolt directory, so this
only rewrites .beads/metadata.json (dolt_mode) and writes the proxied-server
sidecar — no Dolt data is copied or moved. Stop the running server first with
'bd dolt stop'.

Note: dolt_mode lives in the committed metadata.json, so this change propagates
to clones on the next push.
```

**Usage**

```text
bd migrate from-server-to-proxied-server [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would be done without making changes |
| `--help` | `-h` |  | help for from-server-to-proxied-server |
| `--idle-timeout` |  | duration | Proxy idle timeout; omit for the 30s default, 0 for indefinite uptime |

<a id="bd-migrate-from-proxied-server-to-server"></a>

### `bd migrate from-proxied-server-to-server`

```text
Switch a repo from proxied-server mode to server mode (bd init --server).

Both modes root their dolt sql-server at the same .beads/dolt directory, so this
only rewrites .beads/metadata.json (dolt_mode) and removes the proxied-server
sidecar — no Dolt data is copied or moved. Stop the running proxy first with
'bd dolt stop'.

Note: dolt_mode lives in the committed metadata.json, so this change propagates
to clones on the next push.
```

**Usage**

```text
bd migrate from-proxied-server-to-server [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would be done without making changes |
| `--help` | `-h` |  | help for from-proxied-server-to-server |

<a id="bd-migrate-from-shared-server-to-proxied-server"></a>

### `bd migrate from-shared-server-to-proxied-server`

```text
Switch a repo from shared-server mode to proxied-server mode.

The proxied server is rooted at the shared dolt directory
(~/.beads/shared-server/dolt), so no Dolt data is copied or moved; this rewrites
.beads/metadata.json (dolt_mode), turns off dolt.shared-server for this repo, and
writes the proxied-server sidecar. Stop the running shared server first with
'bd dolt stop' — note that stops it for every project sharing it.
```

**Usage**

```text
bd migrate from-shared-server-to-proxied-server [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would be done without making changes |
| `--help` | `-h` |  | help for from-shared-server-to-proxied-server |
| `--idle-timeout` |  | duration | Proxy idle timeout; omit for the 30s default, 0 for indefinite uptime |

<a id="bd-migrate-from-proxied-server-to-shared-server"></a>

### `bd migrate from-proxied-server-to-shared-server`

```text
Switch a repo from proxied-server mode back to shared-server mode.

Only applies to a proxied-server repo rooted at the shared dolt directory
(~/.beads/shared-server/dolt) — the reverse of from-shared-server-to-proxied-server.
This rewrites .beads/metadata.json (dolt_mode), re-enables dolt.shared-server, and
removes the proxied-server sidecar; no Dolt data is copied or moved. Stop the
running proxy first with 'bd dolt stop'.
```

**Usage**

```text
bd migrate from-proxied-server-to-shared-server [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would be done without making changes |
| `--help` | `-h` |  | help for from-proxied-server-to-shared-server |

<a id="bd-migrate-legacy-sqlite"></a>

### `bd migrate legacy-sqlite`

```text
Read an authenticated legacy SQLite database as JSONL
```

**Usage**

```text
bd migrate legacy-sqlite --source-db PATH --output PATH|- [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for legacy-sqlite |
| `--output` |  | string | JSONL output path, or - for stdout |
| `--source-db` |  | string | Legacy SQLite database (read-only) |

<a id="bd-ping"></a>

## `bd ping`

```text
Lightweight health check that confirms bd can reach its database.

Steps:
  1. Resolve the .beads workspace
  2. Open the store (embedded or server)
  3. Run a trivial query (issue count)
  4. Report timing

Exit 0 on success, exit 1 on failure.
```

**Usage**

```text
bd ping [flags]
```

**Examples**

```text
  bd ping              # Quick connectivity check
  bd ping --json       # Structured output for automation
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for ping |

<a id="bd-preflight"></a>

## `bd preflight`

```text
Display a checklist of common pre-PR checks for contributors.

This command helps catch common issues before pushing to CI:
- Tests not run locally
- Lint errors
- Unformatted Go files
- .beads/issues.jsonl pollution
- Stale nix vendorHash
- Version mismatches
```

**Usage**

```text
bd preflight [flags]
```

**Examples**

```text
  bd preflight              # Show checklist
  bd preflight --check      # Run checks automatically
  bd preflight --check --json  # JSON output for programmatic use
  bd preflight --check --skip-lint  # Explicitly skip lint check
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--check` |  |  | Run checks automatically |
| `--fix` |  |  | Auto-fix issues where possible (vendorHash, version sync) |
| `--help` | `-h` |  | help for preflight |
| `--json` |  |  | Output results as JSON |
| `--skip-lint` |  |  | Skip lint check explicitly |

Local definitions override the global flags `--json` for this command.

<a id="bd-prune"></a>

## `bd prune`

```text
Permanently delete closed non-ephemeral beads and their associated data.

Use this to trim closed regular beads (tasks, features, bugs, chores, etc.)
that are no longer useful. The common case is a long-lived repo where
closed work has piled up and is bloating auto-export or slowing queries.

Requires --older-than or --pattern. The flag is a safety gate — without
it, a muscle-memory `--force` could wipe every closed bead in the repo.
Use `--pattern '*'` if you really do want to sweep everything closed.

Deletes: issues, dependencies, labels, events, and comments for matching beads.
Skips: pinned beads (protected), open/in-progress beads, and ephemeral beads.

Also skips closed beads whose ID appears in the description, notes, or
comments of any open / in-progress bead. This protects ADR / decision /
verification trails that downstream beads still cite. Use
--ignore-references to override (e.g., when bulk-decommissioning a
retired label across the rig).

To delete closed ephemeral beads (wisps, transient molecules) use
`bd purge` instead.

For full Dolt storage reclaim after deleting many rows, follow with `bd flatten`
so history can be collapsed and old chunks can be garbage-collected.

EXAMPLES:
  bd prune --older-than 30d              # Preview closed beads >30d old
  bd prune --older-than 30d --force      # Delete them
  bd prune --older-than 90d --dry-run    # Detailed preview with stats
  bd prune --pattern "*" --force         # Delete all closed regular beads
  bd prune --pattern "gm-temp-*" --force # Scope to a pattern
```

**Usage**

```text
bd prune [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview what would be pruned with stats |
| `--force` | `-f` |  | Actually prune (without this, shows preview) |
| `--help` | `-h` |  | help for prune |
| `--ignore-references` |  |  | Delete closed beads even when referenced by open beads (use with care; see --help for details) |
| `--older-than` |  | string | Only prune beads closed more than N ago (e.g., 30d, 2w, 60) |
| `--pattern` |  | string | Only prune beads matching ID glob pattern (e.g., 'gm-old-*') |

<a id="bd-purge"></a>

## `bd purge`

```text
Permanently delete closed ephemeral beads and their associated data.

Closed ephemeral beads (wisps, transient molecules) accumulate rapidly and
have no value once closed. This command removes them to reclaim storage.

Deletes: issues, dependencies, labels, events, and comments for matching beads.
Skips: pinned beads (protected).

To delete closed non-ephemeral beads (regular tasks, features, bugs, etc.)
use `bd prune` instead.

For full Dolt storage reclaim after deleting many rows, follow with `bd flatten`
so history can be collapsed and old chunks can be garbage-collected.

EXAMPLES:
  bd purge                           # Preview what would be purged
  bd purge --force                   # Delete all closed ephemeral beads
  bd purge --older-than 7d --force   # Only purge items closed 7+ days ago
  bd purge --pattern "*-wisp-*"      # Only purge matching ID pattern
  bd purge --dry-run                 # Detailed preview with stats
```

**Usage**

```text
bd purge [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview what would be purged with stats |
| `--force` | `-f` |  | Actually purge (without this, shows preview) |
| `--help` | `-h` |  | help for purge |
| `--older-than` |  | string | Only purge beads closed more than N ago (e.g., 7d, 2w, 30) |
| `--pattern` |  | string | Only purge beads matching ID glob pattern (e.g., *-wisp-*) |

<a id="bd-rename-prefix"></a>

## `bd rename-prefix`

```text
Rename the issue prefix for all issues in the database.
This will update all issue IDs and all text references across all fields.

USE CASES:
- Shortening long prefixes (e.g., 'knowledge-work-' → 'kw-')
- Rebranding project naming conventions
- Consolidating multiple prefixes after database corruption
- Migrating to team naming standards

Prefix validation rules:
- Allowed characters: lowercase letters, numbers, hyphens
- Must start with a letter
- Must end with a hyphen (e.g., 'kw-', 'work-')
- Cannot be empty or just a hyphen

Multiple prefix detection and repair:
If issues have multiple prefixes (corrupted database), use --repair to consolidate them.
The --repair flag will rename all issues with incorrect prefixes to the new prefix,
preserving issues that already have the correct prefix.

EXAMPLES:
  bd rename-prefix kw-                # Rename from 'knowledge-work-' to 'kw-'
  bd rename-prefix mtg- --repair      # Consolidate multiple prefixes into 'mtg-'
  bd rename-prefix team- --dry-run    # Preview changes without applying

NOTE: This is a rare operation. Most users never need this command.
```

**Usage**

```text
bd rename-prefix <new-prefix> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview changes without applying them |
| `--help` | `-h` |  | help for rename-prefix |
| `--repair` |  |  | Repair database with multiple prefixes by consolidating them |

<a id="bd-rules"></a>

## `bd rules`

```text
Audit and compact Claude rules
```

**Usage**

```text
bd rules [command]
```

**Available Commands**

- [`audit`](#bd-rules-audit) — Scan rules for contradictions and merge opportunities
- [`compact`](#bd-rules-compact) — Merge related rules into composites

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for rules |

<a id="bd-rules-audit"></a>

### `bd rules audit`

```text
Scan rules for contradictions and merge opportunities
```

**Usage**

```text
bd rules audit [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for audit |
| `--path` |  | string | Path to rules directory (default ".claude/rules/") |
| `--threshold` |  | float | Jaccard similarity threshold (default 0.6) |

<a id="bd-rules-compact"></a>

### `bd rules compact`

```text
Merge related rules into composites
```

**Usage**

```text
bd rules compact [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--auto` |  |  | Apply audit suggestions |
| `--dry-run` |  |  | Preview without applying |
| `--group` |  | strings | Rule names to merge |
| `--help` | `-h` |  | help for compact |
| `--path` |  | string | Path to rules directory (default ".claude/rules/") |

<a id="bd-sql"></a>

## `bd sql`

```text
Execute a raw SQL query against the underlying database (Dolt).

Useful for debugging, maintenance, and working around bugs in higher-level commands.
```

**Usage**

```text
bd sql <query> [flags]
```

**Examples**

```text
  bd sql 'SELECT COUNT(*) FROM issues'
  bd sql 'SELECT id, title FROM issues WHERE status = "open" LIMIT 5'
  bd sql 'DELETE FROM dirty_issues WHERE issue_id = "bd-abc123"'
  bd sql --csv 'SELECT id, title, status FROM issues'

The query is passed directly to the database. SELECT queries return results as a
table (or JSON/CSV with --json/--csv). Non-SELECT queries (INSERT, UPDATE, DELETE)
report the number of rows affected.

In proxied-server mode, multiple statements separated by ';' run as a single
committed batch and report "OK", and --database runs the query against a
different server database (equivalent to a session USE) without changing the
project's configured database.

WARNING: Direct database access bypasses the storage layer. Use with caution.
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--csv` |  |  | Output results in CSV format |
| `--help` | `-h` |  | help for sql |

<a id="bd-upgrade"></a>

## `bd upgrade`

```text
Commands for checking bd version upgrades and reviewing changes.

The upgrade command helps you stay aware of bd version changes:
  - bd upgrade status: Check if bd version changed since last use
  - bd upgrade review: Show what's new since your last version
  - bd upgrade ack: Acknowledge the current version

Version tracking is automatic - bd updates metadata.json on every run.
```

**Usage**

```text
bd upgrade [command]
```

**Available Commands**

- [`ack`](#bd-upgrade-ack) — Acknowledge the current bd version
- [`review`](#bd-upgrade-review) — Review changes since last bd version
- [`status`](#bd-upgrade-status) — Check if bd version has changed

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for upgrade |

<a id="bd-upgrade-ack"></a>

### `bd upgrade ack`

```text
Mark the current bd version as acknowledged.

This updates metadata.json to record that you've seen the current
version. Mainly useful after reviewing upgrade changes to suppress
future upgrade notifications.

Note: Version tracking happens automatically, so you don't need to
run this command unless you want to explicitly mark acknowledgement.
```

**Usage**

```text
bd upgrade ack [flags]
```

**Examples**

```text
  bd upgrade ack
  bd upgrade ack --json
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for ack |

<a id="bd-upgrade-review"></a>

### `bd upgrade review`

```text
Show what's new in bd since the last version you used.

Unlike 'bd info --whats-new' which shows the last 3 versions,
this command shows ALL changes since your specific last version.

If you're upgrading from an old version, you'll see the complete
changelog of everything that changed since then.
```

**Usage**

```text
bd upgrade review [flags]
```

**Examples**

```text
  bd upgrade review
  bd upgrade review --json
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for review |

<a id="bd-upgrade-status"></a>

### `bd upgrade status`

```text
Check if bd has been upgraded since you last used it.

This command uses the version tracking that happens automatically
at startup to detect if bd was upgraded.
```

**Usage**

```text
bd upgrade status [flags]
```

**Examples**

```text
  bd upgrade status
  bd upgrade status --json
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-worktree"></a>

## `bd worktree`

```text
Manage git worktrees with proper beads configuration.

Worktrees allow multiple working directories sharing the same git repository,
enabling parallel development (e.g., multiple agents or features).

Worktrees automatically share the same beads database as the main repository
via git common directory discovery — no manual redirect configuration needed.
```

**Usage**

```text
bd worktree [command]
```

**Available Commands**

- [`create`](#bd-worktree-create) — Create a worktree
- [`info`](#bd-worktree-info) — Show worktree info for current directory
- [`list`](#bd-worktree-list) — List all git worktrees
- [`remove`](#bd-worktree-remove) — Remove a worktree with safety checks

**Examples**

```text
  bd worktree create feature-auth           # Create worktree
  bd worktree create bugfix --branch fix-1  # Create with specific branch name
  bd worktree list                          # List all worktrees
  bd worktree remove feature-auth           # Remove worktree (with safety checks)
  bd worktree info                          # Show info about current worktree
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for worktree |

<a id="bd-worktree-create"></a>

### `bd worktree create`

```text
Create a git worktree for parallel development.

This command:
1. Creates a git worktree at ./<name> (or specified path)
2. Adds the worktree path to .gitignore (if inside repo root)

The worktree automatically shares the same beads database as the main
repository via git common directory discovery — no redirect file needed.
```

**Usage**

```text
bd worktree create <name> [--branch=<branch>] [flags]
```

**Examples**

```text
  bd worktree create feature-auth           # Create at ./feature-auth
  bd worktree create bugfix --branch fix-1  # Create with branch name
  bd worktree create ../agents/worker-1     # Create at relative path
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--branch` |  | string | Branch name for the worktree (default: same as name) |
| `--help` | `-h` |  | help for create |

<a id="bd-worktree-info"></a>

### `bd worktree info`

```text
Show information about the current worktree.

If the current directory is in a git worktree, shows:
- Worktree path and name
- Branch
- Beads configuration (redirect or main)
- Main repository location
```

**Usage**

```text
bd worktree info [flags]
```

**Examples**

```text
  bd worktree info          # Show current worktree info
  bd worktree info --json   # JSON output
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for info |

<a id="bd-worktree-list"></a>

### `bd worktree list`

```text
List all git worktrees and their beads configuration state.

Shows each worktree with:
- Name (directory name)
- Path (full path)
- Branch
- Beads state: "redirect" (uses shared db), "shared" (is main), "none" (no beads)
```

**Usage**

```text
bd worktree list [flags]
```

**Examples**

```text
  bd worktree list          # List all worktrees
  bd worktree list --json   # JSON output
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |

<a id="bd-worktree-remove"></a>

### `bd worktree remove`

```text
Remove a registered git worktree with fail-closed safety checks.

Without --force, the target must be clean and its pinned HEAD must be contained
in either the configured upstream or the single comparator selected by
--merged-into. Comparators may be full refs, unambiguous short ref names, or
full commit object IDs. Revision expressions and worktree-local pseudorefs such
as HEAD and ORIG_HEAD are rejected.

--force skips cleanliness and containment requirements, but it does not skip
registered-identity and concurrent-change checks. --force and --merged-into
are mutually exclusive, and each flag may be specified at most once.

Worktree removal and .gitignore cleanup are not atomic. If removal succeeds but
cleanup fails, this command returns an error that explicitly reports the
worktree as removed; it does not claim or attempt a rollback.
```

**Usage**

```text
bd worktree remove <name> [flags]
```

**Examples**

```text
  bd worktree remove feature-auth                    # Check the configured upstream
  bd worktree remove feature-auth --merged-into main # Check containment in main
  bd worktree remove feature-auth --force            # Skip clean/containment checks
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force` |  |  | Skip cleanliness and containment checks |
| `--help` | `-h` |  | help for remove |
| `--merged-into` |  | string | Require worktree HEAD to be contained in this ref |

<a id="bd-admin"></a>

## `bd admin`

```text
Administrative commands for beads database maintenance.

Available Commands:
  cleanup     Delete closed issues to reduce database size
  compact     Compact old closed issues to save space
  reset       Remove all beads data and configuration
```

**Usage**

```text
bd admin [command]
```

**These commands are for advanced users and should be used carefully**

- [`cleanup`](#bd-admin-cleanup) — Delete closed issues (issue lifecycle)
- [`compact`](#bd-admin-compact) — Compact old closed issues to save space (storage optimization)
- [`reset`](#bd-admin-reset) — Remove all beads data and configuration (full reset)

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for admin |

<a id="bd-admin-cleanup"></a>

### `bd admin cleanup`

```text
Delete closed issues to reduce database size.

This command permanently removes closed issues from the database.

NOTE: This command only manages issue lifecycle (closed -> deleted). For general
health checks and automatic repairs, use 'bd doctor --fix' instead.

By default, deletes ALL closed issues. Use --older-than to only delete
issues closed before a certain date.

EXAMPLES:
  bd admin cleanup --force                          # Delete all closed issues
  bd admin cleanup --older-than 30 --force          # Only issues closed 30+ days ago
  bd admin cleanup --ephemeral --force              # Only closed wisps (transient molecules)
  bd admin cleanup --dry-run                        # Preview what would be deleted

SAFETY:
- Requires --force flag to actually delete (unless --dry-run)
- Supports --cascade to delete dependents
- Shows preview of what will be deleted
- Use --json for programmatic output

SEE ALSO:
  bd doctor --fix    Automatic health checks and repairs (recommended for routine maintenance)
  bd admin compact   Compact old closed issues to save space
```

**Usage**

```text
bd admin cleanup [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--cascade` |  |  | Recursively delete all dependent issues |
| `--dry-run` |  |  | Preview what would be deleted without making changes |
| `--ephemeral` |  |  | Only delete closed wisps (transient molecules) |
| `--force` | `-f` |  | Actually delete (without this flag, shows error) |
| `--help` | `-h` |  | help for cleanup |
| `--older-than` |  | int | Only delete issues closed more than N days ago (0 = all closed issues) |

<a id="bd-admin-compact"></a>

### `bd admin compact`

```text
Compact old closed issues using semantic summarization.

Compaction reduces database size by summarizing closed issues that are no longer
actively referenced. This is permanent graceful decay - original content is discarded.

Modes:
  - Analyze: Export candidates for agent review (no API key needed)
  - Apply: Accept agent-provided summary (no API key needed)
  - Auto: AI-powered compaction (requires ANTHROPIC_API_KEY, MINIMAX_API_KEY, or ai.api_key)
  - Dolt: Run Dolt garbage collection (for Dolt-backend repositories)

Tiers:
  - Tier 1: Semantic compression (30 days closed, 70% reduction)
  - Tier 2: Ultra compression (90 days closed) - planned, not yet implemented

Dolt Garbage Collection:
  With auto-commit per mutation, Dolt commit history grows over time. Use
  --dolt to run Dolt garbage collection and reclaim disk space.

  --dolt: Run Dolt GC on .beads/dolt directory to free disk space.
          This removes unreachable commits and compacts storage.
```

**Usage**

```text
bd admin compact [flags]
```

**Examples**

```text
  # Dolt garbage collection
  bd compact --dolt                        # Run Dolt GC
  bd compact --dolt --dry-run              # Preview without running GC

  # Agent-driven workflow (recommended)
  bd compact --analyze --json              # Get candidates with full content
  bd compact --apply --id bd-42 --summary summary.txt
  bd compact --apply --id bd-42 --summary - < summary.txt

  # AI-powered workflow
  bd compact --auto --dry-run              # Preview candidates
  bd compact --auto --all                  # Compact all eligible issues
  bd compact --auto --id bd-42             # Compact specific issue
  MINIMAX_API_KEY=... bd compact --auto --all

  # Statistics
  bd compact --stats                       # Show statistics
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--actor` |  | string | Actor name for audit trail (default "agent") |
| `--all` |  |  | Process all candidates |
| `--analyze` |  |  | Analyze mode: export candidates for agent review |
| `--apply` |  |  | Apply mode: accept agent-provided summary |
| `--auto` |  |  | Auto mode: AI-powered compaction |
| `--batch-size` |  | int | Issues per batch (default 10) |
| `--dolt` |  |  | Dolt mode: run Dolt garbage collection on .beads/dolt |
| `--dry-run` |  |  | Preview without compacting |
| `--force` |  |  | Force compact (bypass checks, requires --id) |
| `--help` | `-h` |  | help for compact |
| `--id` |  | string | Compact specific issue |
| `--json` |  |  | Output JSON format |
| `--limit` |  | int | Limit number of candidates (0 = no limit) |
| `--stats` |  |  | Show compaction statistics |
| `--summary` |  | string | Path to summary file (use '-' for stdin) |
| `--tier` |  | int | Compaction tier (only tier 1 is implemented) (default 1) |
| `--workers` |  | int | Parallel workers (default 5) |

Local definitions override the global flags `--actor`, `--json` for this command.

<a id="bd-admin-reset"></a>

### `bd admin reset`

```text
Reset beads to an uninitialized state, removing all local data.

This command removes:
  - The .beads directory (database, JSONL, config)
  - Git hooks installed by bd
  - Sync branch worktrees

By default, shows what would be deleted (dry-run mode).
Use --force to actually perform the reset.
```

**Usage**

```text
bd admin reset [flags]
```

**Examples**

```text
  bd reset              # Show what would be deleted
  bd reset --force      # Actually delete everything
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--force` |  |  | Actually perform the reset (required) |
| `--help` | `-h` |  | help for reset |

<a id="bd-jira"></a>

## `bd jira`

```text
Synchronize issues between beads and Jira.

Configuration:
  bd config set jira.url "https://company.atlassian.net"
  bd config set jira.project "PROJ"
  bd config set jira.projects "PROJ1,PROJ2"   # Multiple projects
  bd config set jira.api_token "YOUR_TOKEN"
  bd config set jira.username "your_email@company.com"  # For Jira Cloud
  bd config set jira.push_prefix "hippo"       # Only push hippo-* issues to Jira
  bd config set jira.push_prefix "proj1,proj2" # Multiple prefixes (comma-separated)

Environment variables (alternative to config):
  JIRA_API_TOKEN  - Jira API token
  JIRA_USERNAME   - Jira username/email
  JIRA_PROJECTS   - Comma-separated project keys
```

**Usage**

```text
bd jira [command]
```

**Available Commands**

- [`pull`](#bd-jira-pull) — Pull specific items from Jira
- [`push`](#bd-jira-push) — Push specific beads to Jira
- [`status`](#bd-jira-status) — Show Jira sync status
- [`sync`](#bd-jira-sync) — Synchronize issues with Jira

**Examples**

```text
  bd jira sync --pull         # Import issues from Jira
  bd jira sync --push         # Export issues to Jira
  bd jira sync                # Bidirectional sync (pull then push)
  bd jira sync --dry-run      # Preview sync without changes
  bd jira status              # Show sync status
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for jira |

<a id="bd-jira-pull"></a>

### `bd jira pull`

```text
Pull one or more items from Jira.

Accepts bead IDs or external references as positional arguments.
Equivalent to: bd jira sync --pull --issues <refs>
```

**Usage**

```text
bd jira pull [refs...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview pull without making changes |
| `--help` | `-h` |  | help for pull |

<a id="bd-jira-push"></a>

### `bd jira push`

```text
Push one or more beads issues to Jira.

Accepts bead IDs as positional arguments.
Equivalent to: bd jira sync --push --issues <ids>
```

**Usage**

```text
bd jira push [bead-ids...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview push without making changes |
| `--help` | `-h` |  | help for push |

<a id="bd-jira-status"></a>

### `bd jira status`

```text
Show the current Jira sync status, including:
  - Last sync timestamp
  - Configuration status
  - Number of issues with Jira links
  - Issues pending push (no external_ref)
```

**Usage**

```text
bd jira status [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-jira-sync"></a>

### `bd jira sync`

```text
Synchronize issues between beads and Jira.

Modes:
  --pull         Import issues from Jira into beads
  --push         Export issues from beads to Jira
  (no flags)     Bidirectional sync: pull then push, with conflict resolution

Conflict Resolution:
  By default, newer timestamp wins. Override with:
  --prefer-local   Always prefer local beads version
  --prefer-jira    Always prefer Jira version
```

**Usage**

```text
bd jira sync [flags]
```

**Examples**

```text
  bd jira sync --pull                # Import from Jira
  bd jira sync --push --create-only  # Push new issues only
  bd jira sync --dry-run             # Preview without changes
  bd jira sync --prefer-local        # Bidirectional, local wins
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--create-only` |  |  | Only create new issues, don't update existing |
| `--dry-run` |  |  | Preview sync without making changes |
| `--help` | `-h` |  | help for sync |
| `--issues` |  | string | Comma-separated bead IDs to sync selectively (e.g., bd-abc,bd-def). Mutually exclusive with --parent. |
| `--parent` |  | string | Limit push to this bead and its descendants (push only). Mutually exclusive with --issues. |
| `--prefer-jira` |  |  | Prefer Jira version on conflicts |
| `--prefer-local` |  |  | Prefer local version on conflicts |
| `--project` |  | strings | Project key(s) to sync (overrides configured project/projects) |
| `--pull` |  |  | Pull issues from Jira |
| `--push` |  |  | Push issues to Jira |
| `--state` |  | string | Issue state to sync: open, closed, all (default "all") |

<a id="bd-linear"></a>

## `bd linear`

```text
Synchronize issues between beads and Linear.

Configuration:
  bd config set linear.api_key "YOUR_API_KEY"
  bd config set linear.team_id "TEAM_ID"
  bd config set linear.team_ids "TEAM_ID1,TEAM_ID2"  # Multiple teams (comma-separated)
  bd config set linear.project_id "PROJECT_ID"  # Optional: sync only this project

Environment variables (alternative to config):
  LINEAR_API_KEY  - Linear API key (for individual developers)
  LINEAR_TEAM_ID  - Linear team ID (UUID, singular)
  LINEAR_TEAM_IDS - Linear team IDs (comma-separated UUIDs)

OAuth (for CI workers / automated sync):
  LINEAR_OAUTH_CLIENT_ID     - OAuth app client ID
  LINEAR_OAUTH_CLIENT_SECRET - OAuth app client secret

  When both OAuth env vars are set, OAuth client_credentials flow is used
  instead of the API key. This allows CI workers to authenticate as an
  application (actor=application) rather than impersonating a user.
  Precedence: OAuth > LINEAR_API_KEY > config file.

Data Mapping (optional, sensible defaults provided):
  Priority mapping (Linear 0-4 to Beads 0-4):
    bd config set linear.priority_map.0 4    # No priority -> Backlog
    bd config set linear.priority_map.1 0    # Urgent -> Critical
    bd config set linear.priority_map.2 1    # High -> High
    bd config set linear.priority_map.3 2    # Medium -> Medium
    bd config set linear.priority_map.4 3    # Low -> Low

  State mapping (Linear state type to Beads status):
    bd config set linear.state_map.backlog open
    bd config set linear.state_map.unstarted open
    bd config set linear.state_map.started in_progress
    bd config set linear.state_map.completed closed
    bd config set linear.state_map.canceled closed
    bd config set linear.state_map.my_custom_state in_progress  # Custom state names

  Label to issue type mapping:
    bd config set linear.label_type_map.bug bug
    bd config set linear.label_type_map.feature feature
    bd config set linear.label_type_map.epic epic

  Relation type mapping (Linear relations to Beads dependencies):
    bd config set linear.relation_map.blocks blocks
    bd config set linear.relation_map.blockedBy blocks
    bd config set linear.relation_map.duplicate duplicates
    bd config set linear.relation_map.related related

  ID generation (optional, hash IDs to match bd/Jira hash mode):
    bd config set linear.id_mode "hash"      # hash (default)
    bd config set linear.hash_length "6"     # hash length 3-8 (default: 6)
```

**Usage**

```text
bd linear [command]
```

**Available Commands**

- [`pull`](#bd-linear-pull) — Pull specific items from Linear
- [`push`](#bd-linear-push) — Push specific beads to Linear
- [`status`](#bd-linear-status) — Show Linear sync status
- [`sync`](#bd-linear-sync) — Synchronize issues with Linear
- [`teams`](#bd-linear-teams) — List available Linear teams

**Examples**

```text
  bd linear sync --pull         # Import issues from Linear
  bd linear sync --push         # Export issues to Linear
  bd linear sync                # Bidirectional sync (pull then push)
  bd linear sync --dry-run      # Preview sync without changes
  bd create "Fix login" --external-ref https://linear.app/team/issue/TEAM-123
                              # Link a local issue to an existing Linear issue
  bd linear status              # Show sync status
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for linear |

<a id="bd-linear-pull"></a>

### `bd linear pull`

```text
Pull one or more items from Linear.

Accepts bead IDs or external references as positional arguments.
Equivalent to: bd linear sync --pull --issues <refs>
```

**Usage**

```text
bd linear pull [refs...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview pull without making changes |
| `--help` | `-h` |  | help for pull |
| `--relations` |  |  | Import Linear relations as bd dependencies when pulling |

<a id="bd-linear-push"></a>

### `bd linear push`

```text
Push one or more beads issues to Linear.

Accepts bead IDs as positional arguments.
Equivalent to: bd linear sync --push --issues <ids>
```

**Usage**

```text
bd linear push [bead-ids...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview push without making changes |
| `--help` | `-h` |  | help for push |

<a id="bd-linear-status"></a>

### `bd linear status`

```text
Show the current Linear sync status, including:
  - Last sync timestamp
  - Configuration status
  - Number of issues with Linear links
  - Issues pending push (no external_ref)
```

**Usage**

```text
bd linear status [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-linear-sync"></a>

### `bd linear sync`

```text
Synchronize issues between beads and Linear.

Modes:
  --pull              Import issues from Linear into beads
  --push              Export issues from beads to Linear
  --pull-if-stale     Pull only if data is stale (skip if fresh)
  (no flags)          Bidirectional sync: pull then push, with conflict resolution

Staleness (--pull-if-stale):
  --threshold 20m     How old data must be before pulling (default 20m)
  A 5-minute debounce prevents agent loops: if a pull completed within 5 minutes,
  data is always treated as fresh regardless of the threshold.

Team Selection:
  --team ID1,ID2  Override configured team IDs for this sync
  Multiple teams can be configured via linear.team_ids (comma-separated).
  Falls back to linear.team_id for backward compatibility.
  Push requires explicit --team when multiple teams are configured.

Pull Options:
  --milestones       Reconstruct Linear project milestones as local epic parents

Type Filtering (--push only):
  --type task,feature       Only sync issues of these types
  --exclude-type wisp       Exclude issues of these types
  --include-ephemeral       Include ephemeral issues (wisps, etc.); default is to exclude
  --parent TICKET           Only push this ticket and its descendants
  --relations               Import Linear relations as bd dependencies on pull

Persistent push-direction ID filters (workflow artifacts, sandbox beads, etc.):
  bd config set linear.exclude_id_prefix "hw-mol-"
  bd config set linear.exclude_id_patterns "-wisp-,sandbox-,scratch-"

  exclude_id_prefix is a single case-sensitive prefix on the bead ID.
  exclude_id_patterns is a comma-separated list of case-sensitive substrings
  (matched anywhere in the ID). Both are combined as a union: a bead
  matching either rule is skipped from push (no create, no update). Beads
  with an existing external_ref that NOW match are silently skipped on
  future syncs; the Linear-side issue persists — archive/delete it manually
  if desired.

Conflict Resolution:
  By default, newer timestamp wins. Override with:
  --prefer-local    Always prefer local beads version
  --prefer-linear   Always prefer Linear version
```

**Usage**

```text
bd linear sync [flags]
```

**Examples**

```text
  bd linear sync --pull                         # Import from Linear
  bd linear sync --pull-if-stale                # Pull only if data is stale
  bd linear sync --pull-if-stale --threshold 5m # Pull if older than 5 minutes
  bd linear sync --pull --relations             # Import Linear blocking relations as bd deps
  bd linear sync --push --create-only           # Push new issues only
  bd linear sync --push --type=task,feature     # Push only tasks and features
  bd linear sync --push --exclude-type=wisp     # Push all except wisps
  bd linear sync --push --parent=bd-abc123      # Push one ticket tree
  bd linear sync --dry-run                      # Preview without changes
  bd linear sync --prefer-local                 # Bidirectional, local wins
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--create-only` |  |  | Only create new issues, don't update existing |
| `--dry-run` |  |  | Preview sync without making changes |
| `--exclude-type` |  | strings | Exclude issues of these types (can be repeated) |
| `--help` | `-h` |  | help for sync |
| `--include-ephemeral` |  |  | Include ephemeral issues (wisps, etc.) when pushing to Linear |
| `--issues` |  | string | Comma-separated bead IDs to sync selectively (e.g., bd-abc,bd-def). Mutually exclusive with --parent. |
| `--milestones` |  |  | Reconstruct Linear project milestones as local epic parents when pulling |
| `--no-wait` |  |  | Fail immediately if another sync is running instead of waiting |
| `--parent` |  | string | Limit push to this beads ticket and its descendants |
| `--prefer-linear` |  |  | Prefer Linear version on conflicts |
| `--prefer-local` |  |  | Prefer local version on conflicts |
| `--pull` |  |  | Pull issues from Linear |
| `--pull-if-stale` |  |  | Pull only if Linear data is stale (skip if fresh) |
| `--push` |  |  | Push issues to Linear |
| `--relations` |  |  | Import Linear relations as bd dependencies when pulling |
| `--state` |  | string | Issue state to sync: open, closed, all (default "all") |
| `--team` |  | strings | Team ID(s) to sync (overrides configured team_id/team_ids) |
| `--threshold` |  | duration | Staleness threshold for --pull-if-stale (default 20m) (default 20m0s) |
| `--type` |  | strings | Only sync issues of these types (can be repeated) |
| `--update-refs` |  |  | Update external_ref after creating Linear issues (default true) |

<a id="bd-linear-teams"></a>

### `bd linear teams`

```text
List all teams accessible with your Linear API key.

Use this to find the team ID (UUID) needed for configuration.

Example:
  bd linear teams
  bd config set linear.team_id "12345678-1234-1234-1234-123456789abc"
```

**Usage**

```text
bd linear teams [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for teams |

<a id="bd-repo"></a>

## `bd repo`

```text
Configure and manage multiple repository support for multi-repo hydration.

Multi-repo support allows hydrating issues from multiple beads repositories
into a single database for unified cross-repo issue tracking.

Configuration is stored in .beads/config.yaml under the 'repos' section:

  repos:
    primary: "."
    additional:
      - ~/beads-planning
      - ~/work-repo
```

**Usage**

```text
bd repo [command]
```

**Available Commands**

- [`add`](#bd-repo-add) — Add an additional repository to sync
- [`list`](#bd-repo-list) — List all configured repositories
- [`remove`](#bd-repo-remove) — Remove a repository from sync configuration
- [`sync`](#bd-repo-sync) — Manually trigger multi-repo sync

**Examples**

```text
  bd repo add ~/beads-planning       # Add planning repo
  bd repo add ../other-repo          # Add relative path repo
  bd repo list                       # Show all configured repos
  bd repo remove ~/beads-planning    # Remove by path
  bd repo sync                       # Sync from all configured repos
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for repo |

<a id="bd-repo-add"></a>

### `bd repo add`

```text
Add a repository path to the repos.additional list in config.yaml.

The path should point to a directory containing a .beads folder.
Paths can be absolute or relative (they are stored as-is).

This modifies .beads/config.yaml, which is version-controlled and
shared across all clones of this repository.
```

**Usage**

```text
bd repo add <path> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for add |
| `--json` |  |  | Output JSON |

Local definitions override the global flags `--json` for this command.

<a id="bd-repo-list"></a>

### `bd repo list`

```text
List all repositories configured in .beads/config.yaml.

Shows the primary repository (always ".") and any additional
repositories configured for hydration.
```

**Usage**

```text
bd repo list [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |
| `--json` |  |  | Output JSON |

Local definitions override the global flags `--json` for this command.

<a id="bd-repo-remove"></a>

### `bd repo remove`

```text
Remove a repository path from the repos.additional list in config.yaml.

The path must exactly match what was added (e.g., if you added "~/foo",
you must remove "~/foo", not "/home/user/foo").

This command also removes any previously-hydrated issues from the database
that came from the removed repository.
```

**Usage**

```text
bd repo remove <path> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for remove |
| `--json` |  |  | Output JSON |

Local definitions override the global flags `--json` for this command.

<a id="bd-repo-sync"></a>

### `bd repo sync`

```text
Synchronize issues from all configured additional repositories.

Reads issues.jsonl from each additional repository and imports them into
the primary database with their original prefixes and source_repo set.
Uses mtime caching to skip repos whose JSONL hasn't changed.

Also triggers Dolt push/pull if a remote is configured.
```

**Usage**

```text
bd repo sync [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for sync |
| `--json` |  |  | Output JSON |
| `--verbose` |  |  | Show detailed sync progress |

Local definitions override the global flags `--json`, `--verbose` for this command.

<a id="bd-ado"></a>

## `bd ado`

```text
Commands for syncing issues between beads and Azure DevOps.

Configuration can be set via 'bd config' or environment variables:
  ado.org / AZURE_DEVOPS_ORG              - Organization name
  ado.project / AZURE_DEVOPS_PROJECT      - Project name (single)
  ado.projects / AZURE_DEVOPS_PROJECTS    - Project names (comma-separated)
  ado.pat / AZURE_DEVOPS_PAT              - Personal access token
  ado.url / AZURE_DEVOPS_URL              - Custom base URL (on-prem)
```

**Usage**

```text
bd ado [command]
```

**Available Commands**

- [`projects`](#bd-ado-projects) — List accessible Azure DevOps projects
- [`pull`](#bd-ado-pull) — Pull specific items from Azure DevOps
- [`push`](#bd-ado-push) — Push specific beads to Azure DevOps
- [`status`](#bd-ado-status) — Show Azure DevOps sync status
- [`sync`](#bd-ado-sync) — Sync issues with Azure DevOps

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for ado |

<a id="bd-ado-projects"></a>

### `bd ado projects`

```text
List Azure DevOps projects that the configured token has access to.
```

**Usage**

```text
bd ado projects [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for projects |

<a id="bd-ado-pull"></a>

### `bd ado pull`

```text
Pull one or more items from Azure DevOps.

Accepts bead IDs or external references as positional arguments.
Equivalent to: bd ado sync --pull-only --issues <refs>
```

**Usage**

```text
bd ado pull [refs...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview pull without making changes |
| `--help` | `-h` |  | help for pull |

<a id="bd-ado-push"></a>

### `bd ado push`

```text
Push one or more beads issues to Azure DevOps.

Accepts bead IDs as positional arguments.
Equivalent to: bd ado sync --push-only --issues <ids>
```

**Usage**

```text
bd ado push [bead-ids...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview push without making changes |
| `--help` | `-h` |  | help for push |

<a id="bd-ado-status"></a>

### `bd ado status`

```text
Display current Azure DevOps configuration and sync status.
```

**Usage**

```text
bd ado status [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-ado-sync"></a>

### `bd ado sync`

```text
Synchronize issues between beads and Azure DevOps.

By default, performs bidirectional sync:
- Pulls new/updated work items from Azure DevOps to beads
- Pushes local beads issues to Azure DevOps

Use --pull-only or --push-only to limit direction.

Filters (--area-path, --iteration-path, --types, --states) restrict
which work items are synced. On pull, they limit the WIQL query. On push,
--types and --states filter local beads before pushing to ADO. Use
--no-create with push to skip creating new ADO work items (only update
existing linked items). Filters can also be persisted via config:
  ado.filter.area_path, ado.filter.iteration_path,
  ado.filter.types, ado.filter.states
CLI flags override config values when both are set.
```

**Usage**

```text
bd ado sync [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--area-path` |  | string | Filter to ADO area path (e.g., "Project\Team") |
| `--bootstrap-match` |  |  | Enable heuristic matching for first sync |
| `--dry-run` |  |  | Show what would be synced without making changes |
| `--help` | `-h` |  | help for sync |
| `--issues` |  | string | Comma-separated bead IDs to sync selectively (e.g., bd-abc,bd-def). Mutually exclusive with --parent. |
| `--iteration-path` |  | string | Filter to ADO iteration path (e.g., "Project\Sprint 1") |
| `--no-create` |  |  | Never create new items in either direction (pull or push) |
| `--parent` |  | string | Limit push to this bead and its descendants (push only). Mutually exclusive with --issues. |
| `--prefer-ado` |  |  | On conflict, use Azure DevOps version |
| `--prefer-local` |  |  | On conflict, keep local beads version |
| `--prefer-newer` |  |  | On conflict, use most recent version (default) |
| `--project` |  | strings | Project name(s) to sync (overrides configured project/projects) |
| `--pull-only` |  |  | Only pull issues from Azure DevOps |
| `--push-only` |  |  | Only push issues to Azure DevOps |
| `--reconcile` |  |  | Force reconciliation scan for deleted items |
| `--states` |  | string | Filter to ADO states, comma-separated (e.g., "New,Active,Resolved") |
| `--types` |  | string | Filter to work item types, comma-separated (e.g., "Bug,Task,User Story") |

<a id="bd-audit"></a>

## `bd audit`

```text
Record explicit agent/tool interaction audit entries in .beads/interactions.jsonl.

This optional JSONL sidecar is disabled by default. Enable it with:

  bd config set audit.enabled true

Issue history is always recorded in the database and is visible with
bd history <id> --events. The JSONL sidecar is for explicit interaction capture:
- auditing ("why did the agent do that?")
- dataset generation (SFT/RL fine-tuning)

Entries are append-only. Labeling creates a new "label" entry that references a parent entry.
```

**Usage**

```text
bd audit [command]
```

**Available Commands**

- [`label`](#bd-audit-label) — Append a label entry referencing an existing interaction
- [`record`](#bd-audit-record) — Append an audit interaction entry

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for audit |

<a id="bd-audit-label"></a>

### `bd audit label`

```text
Append a label entry referencing an existing interaction
```

**Usage**

```text
bd audit label <entry-id> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for label |
| `--label` |  | string | Label value (e.g. "good" or "bad") |
| `--reason` |  | string | Reason for label |

<a id="bd-audit-record"></a>

### `bd audit record`

```text
Append an audit interaction entry
```

**Usage**

```text
bd audit record [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--error` |  | string | Error string (llm_call/tool_call) |
| `--exit-code` |  | int | Exit code (tool_call) (default -1) |
| `--help` | `-h` |  | help for record |
| `--issue-id` |  | string | Related issue id (bd-...) |
| `--kind` |  | string | Entry kind (e.g. llm_call, tool_call, label) |
| `--model` |  | string | Model name (llm_call) |
| `--prompt` |  | string | Prompt text (llm_call) |
| `--response` |  | string | Response text (llm_call) |
| `--stdin` |  |  | Read a JSON object from stdin (must match audit.Entry schema) |
| `--tool-name` |  | string | Tool name (tool_call) |

<a id="bd-blocked"></a>

## `bd blocked`

```text
Show blocked issues
```

**Usage**

```text
bd blocked [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--exclude-label` |  | strings | Exclude issues that have ANY of these labels |
| `--help` | `-h` |  | help for blocked |
| `--label` | `-l` | strings | Filter by labels (AND: must have ALL). Can combine with --label-any |
| `--label-any` |  | strings | Filter by labels (OR: must have AT LEAST ONE). Can combine with --label |
| `--parent` |  | string | Filter to descendants of this bead/epic |

<a id="bd-completion"></a>

## `bd completion`

```text
Generate the autocompletion script for bd for the specified shell.
See each sub-command's help for details on how to use the generated script.
```

**Usage**

```text
bd completion [command]
```

**Available Commands**

- [`bash`](#bd-completion-bash) — Generate the autocompletion script for bash
- [`fish`](#bd-completion-fish) — Generate the autocompletion script for fish
- [`powershell`](#bd-completion-powershell) — Generate the autocompletion script for powershell
- [`zsh`](#bd-completion-zsh) — Generate the autocompletion script for zsh

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for completion |

<a id="bd-completion-bash"></a>

### `bd completion bash`

```text
Generate the autocompletion script for the bash shell.

This script depends on the 'bash-completion' package.
If it is not installed already, you can install it via your OS's package manager.

To load completions in your current shell session:
	source <(bd completion bash)

To load completions for every new session, execute once:

#### Linux:

	bd completion bash > /etc/bash_completion.d/bd

#### macOS:

	bd completion bash > $(brew --prefix)/etc/bash_completion.d/bd

You will need to start a new shell for this setup to take effect.
```

**Usage**

```text
bd completion bash
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for bash |
| `--no-descriptions` |  |  | disable completion descriptions |

<a id="bd-completion-fish"></a>

### `bd completion fish`

```text
Generate the autocompletion script for the fish shell.

To load completions in your current shell session:
	bd completion fish | source

To load completions for every new session, execute once:

	bd completion fish > ~/.config/fish/completions/bd.fish

You will need to start a new shell for this setup to take effect.
```

**Usage**

```text
bd completion fish [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for fish |
| `--no-descriptions` |  |  | disable completion descriptions |

<a id="bd-completion-powershell"></a>

### `bd completion powershell`

```text
Generate the autocompletion script for powershell.

To load completions in your current shell session:
	bd completion powershell | Out-String | Invoke-Expression

To load completions for every new session, add the output of the above command
to your powershell profile.
```

**Usage**

```text
bd completion powershell [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for powershell |
| `--no-descriptions` |  |  | disable completion descriptions |

<a id="bd-completion-zsh"></a>

### `bd completion zsh`

```text
Generate the autocompletion script for the zsh shell.

If shell completion is not already enabled in your environment you will need
to enable it.  You can execute the following once:

	echo "autoload -U compinit; compinit" >> ~/.zshrc

To load completions in your current shell session:
	source <(bd completion zsh)

To load completions for every new session, execute once:

#### Linux:

	bd completion zsh > "${fpath[1]}/_bd"

#### macOS:

	bd completion zsh > $(brew --prefix)/share/zsh/site-functions/_bd

You will need to start a new shell for this setup to take effect.
```

**Usage**

```text
bd completion zsh [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for zsh |
| `--no-descriptions` |  |  | disable completion descriptions |

<a id="bd-cook"></a>

## `bd cook`

```text
Cook transforms a .formula.json file into a proto.

By default, cook outputs the resolved formula as JSON to stdout for
ephemeral use. The output can be inspected, piped, or saved to a file.

Two cooking modes are available:
  COMPILE-TIME (default, --mode=compile):
    Produces a proto with {{variable}} placeholders intact.
    Use for: modeling, estimation, contractor handoff, planning.
    Variables are NOT substituted - the output shows the template structure.

  RUNTIME (--mode=runtime or when --var flags provided):
    Produces a fully-resolved proto with variables substituted.
    Use for: final validation before pour, seeing exact output.
    Requires all variables to have values (via --var or defaults).

Formulas are high-level workflow templates that support:
  - Variable definitions with defaults and validation
  - Step definitions that become issue hierarchies
  - Composition rules for bonding formulas together
  - Inheritance via extends

The --persist flag enables the legacy behavior of writing the proto
to the database. This is useful when you want to reuse the same
proto multiple times without re-cooking.

For most workflows, prefer ephemeral protos: pour and wisp commands
accept formula names directly and cook inline.
```

**Usage**

```text
bd cook <formula-file> [flags]
```

**Examples**

```text
  bd cook mol-feature.formula.json                    # Compile-time: keep {{vars}}
  bd cook mol-feature --var name=auth                 # Runtime: substitute vars
  bd cook mol-feature --mode=runtime --var name=auth  # Explicit runtime mode
  bd cook mol-feature --dry-run                       # Preview steps
  bd cook mol-release.formula.json --persist          # Write to database
  bd cook mol-release.formula.json --persist --force  # Replace existing

Output (default):
  JSON representation of the resolved formula with all steps.

Output (--persist):
  Creates a proto bead in the database with:
  - ID matching the formula name (e.g., mol-feature)
  - The "template" label for proto identification
  - Child issues for each step
  - Dependencies matching depends_on relationships
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview what would be created |
| `--force` |  |  | Replace existing proto if it exists (requires --persist) |
| `--help` | `-h` |  | help for cook |
| `--mode` |  | string | Cooking mode: compile (keep placeholders) or runtime (substitute vars) |
| `--persist` |  |  | Persist proto to database (legacy behavior) |
| `--prefix` |  | string | Prefix to prepend to proto ID (e.g., 'gt-' creates 'gt-mol-feature') |
| `--search-path` |  | strings | Additional paths to search for formula inheritance |
| `--var` |  | stringArray | Variable substitution (key=value), enables runtime mode |

<a id="bd-defer"></a>

## `bd defer`

```text
Defer issues to put them on ice for later.

Deferred issues are deliberately set aside - not blocked by anything specific,
just postponed for future consideration. Unlike blocked issues, there's no
dependency keeping them from being worked. Unlike closed issues, they will
be revisited.

Deferred issues don't show in 'bd ready' but remain visible in 'bd list'.

A defer WITH a date is a snooze: once --until passes, the next ready-front
read returns the issue to open automatically (same shape as 'bd undefer').
A defer WITHOUT a date is the indefinite icebox: it stays deferred until
someone runs 'bd undefer'.
```

**Usage**

```text
bd defer [id...] [flags]
```

**Examples**

```text
  bd defer bd-abc                  # Icebox indefinitely (until bd undefer)
  bd defer bd-abc --until=tomorrow # Snooze: auto-wakes once the date passes
  bd defer bd-abc --reason="waiting on API access"
  bd defer bd-abc bd-def           # Defer multiple issues
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for defer |
| `--reason` |  | string | Record why this issue is being deferred (appended to notes) |
| `--until` |  | string | Defer until specific time (e.g., +1h, tomorrow, next monday) |

<a id="bd-formula"></a>

## `bd formula`

```text
Manage workflow formulas - the source layer for molecule templates.

Formulas are TOML/JSON files that define workflows with composition rules.
Define formulas, cook them into protos, then pour or wisp them into work.

Search paths (in order):
  1. <resolved-beads-dir>/formulas/ (active project)
  2. <checkout-root>/.beads/formulas/ (repo-local formulas)
  3. ~/.beads/formulas/ (user)
  4. $GT_ROOT/.beads/formulas/ (shared workspace root, if GT_ROOT set)

Discovering primitives:
  bd formula schema                 # list every declared formula struct
  bd formula schema loop            # show LoopSpec fields, types, and tags
  bd formula primitives gate        # alias; same handler as 'schema'
  examples/formulas/primitives/     # curated, smoke-tested wired fixtures
  docs/workflows/formulas.md          # narrative reference
```

**Usage**

```text
bd formula [command]
```

**Commands**

- [`list`](#bd-formula-list) — List available formulas from all search paths
- [`show`](#bd-formula-show) — Show formula details, steps, and composition rules
- [`schema`](#bd-formula-schema) — Show the formula schema index (alias: primitives)

**Available Commands**

- [`convert`](#bd-formula-convert) — Convert formula from JSON to TOML

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for formula |

<a id="bd-formula-list"></a>

### `bd formula list`

```text
List all formulas from search paths.

Search paths (in order of priority):
  1. <resolved-beads-dir>/formulas/ (active project - highest priority)
  2. <checkout-root>/.beads/formulas/ (repo-local formulas)
  3. ~/.beads/formulas/ (user)
  4. $GT_ROOT/.beads/formulas/ (shared workspace root, if GT_ROOT set)

Formulas in earlier paths shadow those with the same name in later paths.

To list the declared formula schema structs an agent can write inside a .formula.toml,
use 'bd formula schema' (alias: 'bd formula primitives').
```

**Usage**

```text
bd formula list [flags]
```

**Examples**

```text
  bd formula list
  bd formula list --json
  bd formula list --type workflow
  bd formula list --type convoy
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for list |
| `--type` |  | string | Filter by type (workflow, expansion, aspect, convoy) |

<a id="bd-formula-show"></a>

### `bd formula show`

```text
Show detailed information about a formula.

Displays:
  - Formula metadata (name, type, description)
  - Variables with defaults and constraints
  - Steps with dependencies
  - Composition rules (extends, aspects, expansions)
  - Bond points for external composition

To inspect the structure of an individual primitive (e.g. LoopSpec, Gate)
rather than a user-authored formula, use 'bd formula schema <primitive>'.
```

**Usage**

```text
bd formula show <formula-name> [flags]
```

**Examples**

```text
  bd formula show shiny
  bd formula show rule-of-five
  bd formula show security-audit --json
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for show |

<a id="bd-formula-schema"></a>

### `bd formula schema`

```text
Show the formula schema index: every exported struct declared
in a .formula.toml/.formula.json, with field names, types, and tags.

The index is generated from internal/formula/types.go via go:generate; the
struct definitions are the source of truth, so this list cannot drift. It is
structural reference, not proof that every declared runtime behavior is wired.
```

**Usage**

```text
bd formula schema [primitive] [flags]
```

**Aliases:** `schema, primitives`

**Examples**

```text
  bd formula schema                 # list every declared schema struct
  bd formula schema loop            # show LoopSpec fields
  bd formula primitives gate        # alias; shows Gate fields
  bd formula schema --json          # machine-readable index

Curated smoke-tested fixtures for wired primitives live in
examples/formulas/primitives/ (with a smoke harness that proves they work).
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for schema |

<a id="bd-formula-convert"></a>

### `bd formula convert`

```text
Convert formula files from JSON to TOML format.

TOML format provides better ergonomics:
  - Multi-line strings without \n escaping
  - Human-readable diffs
  - Comments allowed

The convert command reads a .formula.json file and outputs .formula.toml.
The original JSON file is preserved (use --delete to remove it).
```

**Usage**

```text
bd formula convert <formula-name|path> [--all] [flags]
```

**Examples**

```text
  bd formula convert shiny              # Convert shiny.formula.json to .toml
  bd formula convert ./my.formula.json  # Convert specific file
  bd formula convert --all              # Convert all JSON formulas
  bd formula convert shiny --delete     # Convert and remove JSON file
  bd formula convert shiny --stdout     # Print TOML to stdout
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` |  |  | Convert all JSON formulas |
| `--delete` |  |  | Delete JSON file after conversion |
| `--help` | `-h` |  | help for convert |
| `--stdout` |  |  | Print TOML to stdout instead of file |

<a id="bd-github"></a>

## `bd github`

```text
Commands for syncing issues between beads and GitHub.

Configuration can be set via 'bd config' or environment variables:
  github.token / GITHUB_TOKEN           - Personal access token
  github.owner / GITHUB_OWNER           - Repository owner
  github.repo / GITHUB_REPO             - Repository name
  github.repository / GITHUB_REPOSITORY - Combined "owner/repo" format
  github.url / GITHUB_API_URL           - Custom API URL (GitHub Enterprise)
```

**Usage**

```text
bd github [command]
```

**Available Commands**

- [`pull`](#bd-github-pull) — Pull specific items from GitHub
- [`push`](#bd-github-push) — Push specific beads to GitHub
- [`repos`](#bd-github-repos) — List accessible GitHub repositories
- [`status`](#bd-github-status) — Show GitHub sync status
- [`sync`](#bd-github-sync) — Sync issues with GitHub

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for github |

<a id="bd-github-pull"></a>

### `bd github pull`

```text
Pull one or more items from GitHub.

Accepts bead IDs or external references as positional arguments.
Equivalent to: bd github sync --pull-only --issues <refs>
```

**Usage**

```text
bd github pull [refs...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview pull without making changes |
| `--help` | `-h` |  | help for pull |

<a id="bd-github-push"></a>

### `bd github push`

```text
Push one or more beads issues to GitHub.

Accepts bead IDs as positional arguments.
Equivalent to: bd github sync --push-only --issues <ids>
```

**Usage**

```text
bd github push [bead-ids...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview push without making changes |
| `--help` | `-h` |  | help for push |

<a id="bd-github-repos"></a>

### `bd github repos`

```text
List GitHub repositories that the configured token has access to.
```

**Usage**

```text
bd github repos [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for repos |

<a id="bd-github-status"></a>

### `bd github status`

```text
Display current GitHub configuration and sync status.
```

**Usage**

```text
bd github status [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-github-sync"></a>

### `bd github sync`

```text
Synchronize issues between beads and GitHub.

By default, performs bidirectional sync:
- Pulls new/updated issues from GitHub to beads
- Pushes local beads issues to GitHub

Use --pull-only or --push-only to limit direction.
```

**Usage**

```text
bd github sync [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Show what would be synced without making changes |
| `--help` | `-h` |  | help for sync |
| `--issues` |  | string | Comma-separated bead IDs to sync selectively (e.g., bd-abc,bd-def). Mutually exclusive with --parent. |
| `--parent` |  | string | Limit push to this bead and its descendants (push only). Mutually exclusive with --issues. |
| `--prefer-github` |  |  | On conflict, use GitHub version |
| `--prefer-local` |  |  | On conflict, keep local beads version |
| `--prefer-newer` |  |  | On conflict, use most recent version (default) |
| `--pull-only` |  |  | Only pull issues from GitHub |
| `--push-only` |  |  | Only push issues to GitHub |

<a id="bd-gitlab"></a>

## `bd gitlab`

```text
Commands for syncing issues between beads and GitLab.

Configuration can be set via 'bd config' or environment variables:
  gitlab.url / GITLAB_URL                         - GitLab instance URL
  gitlab.token / GITLAB_TOKEN                     - Personal access token
  gitlab.project_id / GITLAB_PROJECT_ID           - Project ID or path
  gitlab.group_id / GITLAB_GROUP_ID               - Group ID for group-level sync
  gitlab.default_project_id / GITLAB_DEFAULT_PROJECT_ID - Project for creating issues in group mode
```

**Usage**

```text
bd gitlab [command]
```

**Available Commands**

- [`projects`](#bd-gitlab-projects) — List accessible GitLab projects
- [`pull`](#bd-gitlab-pull) — Pull specific items from GitLab
- [`push`](#bd-gitlab-push) — Push specific beads to GitLab
- [`status`](#bd-gitlab-status) — Show GitLab sync status
- [`sync`](#bd-gitlab-sync) — Sync issues with GitLab

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for gitlab |

<a id="bd-gitlab-projects"></a>

### `bd gitlab projects`

```text
List GitLab projects that the configured token has access to.
```

**Usage**

```text
bd gitlab projects [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for projects |

<a id="bd-gitlab-pull"></a>

### `bd gitlab pull`

```text
Pull one or more items from GitLab.

Accepts bead IDs or external references as positional arguments.
Equivalent to: bd gitlab sync --pull-only --issues <refs>
```

**Usage**

```text
bd gitlab pull [refs...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview pull without making changes |
| `--help` | `-h` |  | help for pull |

<a id="bd-gitlab-push"></a>

### `bd gitlab push`

```text
Push one or more beads issues to GitLab.

Accepts bead IDs as positional arguments.
Equivalent to: bd gitlab sync --push-only --issues <ids>
```

**Usage**

```text
bd gitlab push [bead-ids...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview push without making changes |
| `--help` | `-h` |  | help for push |

<a id="bd-gitlab-status"></a>

### `bd gitlab status`

```text
Display current GitLab configuration and sync status.
```

**Usage**

```text
bd gitlab status [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-gitlab-sync"></a>

### `bd gitlab sync`

```text
Synchronize issues between beads and GitLab.

By default, performs bidirectional sync:
- Pulls new/updated issues from GitLab to beads
- Pushes local beads issues to GitLab

Use --pull-only or --push-only to limit direction.
```

**Usage**

```text
bd gitlab sync [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--assignee` |  | string | Filter by assignee username |
| `--dry-run` |  |  | Show what would be synced without making changes |
| `--exclude-type` |  | string | Exclude these issue types from sync (comma-separated) |
| `--help` | `-h` |  | help for sync |
| `--issues` |  | string | Comma-separated bead IDs to sync selectively (e.g., bd-abc,bd-def). Mutually exclusive with --parent. |
| `--label` |  | string | Filter by labels (comma-separated, AND logic) |
| `--milestone` |  | string | Filter by milestone title |
| `--no-ephemeral` |  |  | Exclude ephemeral/wisp issues from push (default: true) (default true) |
| `--parent` |  | string | Limit push to this bead and its descendants (push only). Mutually exclusive with --issues. |
| `--prefer-gitlab` |  |  | On conflict, use GitLab version |
| `--prefer-local` |  |  | On conflict, keep local beads version |
| `--prefer-newer` |  |  | On conflict, use most recent version (default) |
| `--project` |  | string | Filter to issues from this project ID (group mode) |
| `--pull-only` |  |  | Only pull issues from GitLab |
| `--push-only` |  |  | Only push issues to GitLab |
| `--type` |  | string | Only sync these issue types (comma-separated, e.g. 'epic,feature,task') |

<a id="bd-init-safety"></a>

## `bd init-safety`

```text
bd init flag safety contract.

Every bd init invocation resolves project_id from exactly one explicitly
named source (local reinit, remote adoption, or a fresh mint). When the
source is ambiguous, bd init refuses.

FLAG SURFACE

  bd init                       Mint a new identity. Bootstraps from
                                origin if it has refs/dolt/data.

  bd init --reinit-local        Re-initialize local .beads/ over existing
                                local data. Does NOT authorize discarding
                                remote history. If origin has Dolt data
                                this will refuse — pair with
                                --discard-remote to override.

  bd init --reinit-local \      Discard the remote's Dolt history and
      --discard-remote          replace it with the local reinit. First
                                bd dolt push after this will be a
                                history-replacing force-push.

  bd init --force               Deprecated alias for --reinit-local.
                                Kept working for ≥2 releases.

  bd init --from-jsonl          Import from configured import.path. If
                                origin has Dolt data, this refuses unless
                                --discard-remote authorizes replacing that
                                remote history.

ADOPTING A REMOTE

  If you want to use the remote's existing history, use:

      bd bootstrap

  bd init will automatically suggest this when a remote is detected.

DESTROY-TOKEN (non-interactive only)

  When running with no TTY (CI, agents, piped input), a destructive
  re-init requires an explicit --destroy-token value. That covers both
  --discard-remote and --reinit-local over existing issues. The token
  format is:

      DESTROY-<issue-prefix>

  For example, if your issue prefix is "bd", the token is "DESTROY-bd":

      bd init --reinit-local --discard-remote --destroy-token=DESTROY-bd

  In interactive (TTY) mode you confirm via a typed prompt instead. The
  token is not echoed by bd's runtime error messages — this is a
  deliberate guard against pattern-matched one-liners (see
  engdocs/adr/0002-init-safety-invariants.md).

EXIT CODES

  10    refused: remote has Dolt history and you selected local history
        without --discard-remote
  11    refused: existing local data and you declined the destroy confirm
        (interactive mode only)
  12    refused: destructive re-init (--discard-remote, or --reinit-local
        over existing issues) without a valid --destroy-token
        (non-interactive mode); also returned when the interactive
        --discard-remote typed-token confirmation is declined

RECOVERY

  If you hit a refusal, see docs/recovery/init-safety.md for step-by-step recovery
  playbooks for each exit code.
```

**Usage**

```text
bd init-safety [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for init-safety |

<a id="bd-mail"></a>

## `bd mail`

```text
Delegates mail operations to an external mail provider.

Agents often type 'bd mail' when working with beads, but mail functionality
is typically provided by the orchestrator. This command bridges that gap
by delegating to the configured mail provider.

Configuration (checked in order):
  1. BEADS_MAIL_DELEGATE or BD_MAIL_DELEGATE environment variable
  2. 'mail.delegate' config setting (bd config set mail.delegate "gt mail")
```

**Usage**

```text
bd mail [subcommand] [args...] [flags]
```

**Examples**

```text
  # Configure delegation (one-time setup)
  export BEADS_MAIL_DELEGATE="gt mail"
  # or
  bd config set mail.delegate "gt mail"

  # Then use bd mail as if it were gt mail
  bd mail inbox                    # Lists inbox
  bd mail send mayor/ -s "Hi"      # Sends mail
  bd mail read msg-123             # Reads a message
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for mail |

<a id="bd-metrics"></a>

## `bd metrics`

```text
Show whether anonymous usage metrics are on, see exactly what is sent, and
turn them on or off.

bd shares anonymous usage metrics to learn how people actually use it — just
which commands get run, plus the bd version and OS platform. That's how we decide
what to polish next. We never collect your issues, paths, remotes, identity, or
any user-supplied text.

  bd metrics            show the current status and what is collected
  bd metrics on         turn metrics on
  bd metrics off        turn metrics off
  bd metrics example    show real examples of the events bd sends
```

**Usage**

```text
bd metrics [flags]
bd metrics [command]
```

**Available Commands**

- [`example`](#bd-metrics-example) — Show real examples of the anonymous metrics bd sends
- [`off`](#bd-metrics-off) — Turn anonymous usage metrics off
- [`on`](#bd-metrics-on) — Turn anonymous usage metrics on

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for metrics |

<a id="bd-metrics-example"></a>

### `bd metrics example`

```text
Show real examples of the anonymous metrics bd sends
```

**Usage**

```text
bd metrics example [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for example |

<a id="bd-metrics-off"></a>

### `bd metrics off`

```text
Turn anonymous usage metrics off
```

**Usage**

```text
bd metrics off [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for off |

<a id="bd-metrics-on"></a>

### `bd metrics on`

```text
Turn anonymous usage metrics on
```

**Usage**

```text
bd metrics on [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for on |

<a id="bd-mol"></a>

## `bd mol`

```text
Manage molecules - work templates for agent workflows.

Protos are template epics with the "template" label. They define a DAG of work
that can be spawned to create real issues (molecules).

The molecule metaphor:
  - A proto is an uninstantiated template (reusable work pattern)
  - Spawning creates a molecule (real issues) from the proto
  - Variables ({{key}}) are substituted during spawning
  - Bonding combines protos or molecules into compounds
  - Distilling extracts a proto from an ad-hoc epic
```

**Usage**

```text
bd mol [command]
```

**Aliases:** `mol, protomolecule`

**Commands**

- [`show`](#bd-mol-show) — Show proto/molecule structure and variables
- [`pour`](#bd-mol-pour) — Instantiate proto as persistent mol (liquid phase)
- [`wisp`](#bd-mol-wisp) — Instantiate proto as ephemeral wisp (vapor phase)
- [`bond`](#bd-mol-bond) — Polymorphic combine: proto+proto, proto+mol, mol+mol
- [`squash`](#bd-mol-squash) — Condense molecule to digest
- [`burn`](#bd-mol-burn) — Discard wisp
- [`distill`](#bd-mol-distill) — Extract proto from ad-hoc epic

**Available Commands**

- [`current`](#bd-mol-current) — Show current position in molecule workflow
- [`progress`](#bd-mol-progress) — Show molecule progress summary
- [`ready`](#bd-mol-ready) — Find molecules ready for gate-resume dispatch
- [`seed`](#bd-mol-seed) — Verify formula accessibility
- [`stale`](#bd-mol-stale) — Detect complete-but-unclosed molecules

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for mol |

<a id="bd-mol-show"></a>

### `bd mol show`

```text
Show molecule structure and details.

The --parallel flag highlights parallelizable steps:
  - Steps with no blocking dependencies can run in parallel
  - Shows which steps are ready to start now
  - Identifies parallel groups (steps that can run concurrently)

Example:
  bd mol show bd-patrol --parallel
```

**Usage**

```text
bd mol show <molecule-id> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for show |
| `--parallel` | `-p` |  | Show parallel step analysis |

<a id="bd-mol-pour"></a>

### `bd mol pour`

```text
Pour a proto into a persistent mol - like pouring molten metal into a mold.

This is the chemistry-inspired command for creating PERSISTENT work from templates.
The resulting mol is stored as persistent beads in the issue database and
syncs like any other bead (bd dolt push / pull).

Phase transition: Proto (solid) -> pour -> Mol (liquid)

WHEN TO USE POUR vs WISP:
  pour (liquid): Persistent work that needs audit trail
    - Feature implementations spanning multiple sessions
    - Work you may need to reference later
    - Anything worth preserving in git history

  wisp (vapor): Ephemeral work that auto-cleans up
    - Release workflows (one-time execution)
    - Operational loops and recurring cycles
    - Health checks and diagnostics
    - Any operational workflow without audit value

TIP: Formulas can specify phase:"vapor" to recommend wisp usage.
     If you pour a vapor-phase formula, you'll get a warning.
```

**Usage**

```text
bd mol pour <proto-id> [flags]
```

**Examples**

```text
  bd mol pour mol-feature --var name=auth    # Persistent feature work
  bd mol pour mol-review --var pr=123        # Persistent code review
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--assignee` |  | string | Assign the root issue to this agent/user |
| `--attach` |  | strings | Proto to attach after spawning (repeatable) |
| `--attach-type` |  | string | Bond type for attachments: sequential, parallel, or conditional (default "sequential") |
| `--dry-run` |  |  | Preview what would be created |
| `--help` | `-h` |  | help for pour |
| `--var` |  | stringArray | Variable substitution (key=value) |

<a id="bd-mol-wisp"></a>

### `bd mol wisp`

```text
Create or manage wisps - EPHEMERAL molecules for operational workflows.

When called with a proto-id argument, creates a wisp from that proto.
When called with a subcommand (list, gc), manages existing wisps.

Wisps are issues with Ephemeral=true in the main database. They're stored
locally but NOT synced via git.

WHEN TO USE WISP vs POUR:
  wisp (vapor): Ephemeral work that auto-cleans up
    - Release workflows (one-time execution)
    - Operational loops and recurring cycles
    - Health checks and diagnostics
    - Any operational workflow without audit value

  pour (liquid): Persistent work that needs audit trail
    - Feature implementations spanning multiple sessions
    - Work you may need to reference later
    - Anything worth preserving in git history

TIP: Formulas can specify phase:"vapor" to recommend wisp usage.
     If you use pour on a vapor-phase formula, you'll get a warning.

The wisp lifecycle:
  1. Create: bd mol wisp <proto> or bd create --ephemeral
  2. Execute: Normal bd operations work on wisp issues
  3. Squash: bd mol squash <id> (clears Ephemeral flag, promotes to persistent)
  4. Or burn: bd mol burn <id> (deletes without creating digest)
```

**Usage**

```text
bd mol wisp [proto-id] [flags]
bd mol wisp [command]
```

**Subcommands**

- [`list`](#bd-mol-wisp-list) — List all wisps in current context
- [`gc`](#bd-mol-wisp-gc) — Garbage collect orphaned wisps

**Available Commands**

- [`create`](#bd-mol-wisp-create) — Instantiate a proto as a wisp (solid -> vapor)

**Examples**

```text
  bd mol wisp beads-release --var version=1.0  # Release workflow
  bd mol wisp mol-my-workflow                  # Ephemeral operational cycle
  bd mol wisp list                             # List all wisps
  bd mol wisp gc                               # Garbage collect old wisps
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview what would be created |
| `--help` | `-h` |  | help for wisp |
| `--root-only` |  |  | Create only the root issue (no child step issues) |
| `--var` |  | stringArray | Variable substitution (key=value) |

<a id="bd-mol-wisp-list"></a>

#### `bd mol wisp list`

```text
List all wisps (ephemeral molecules) in the current context.

Wisps are issues with Ephemeral=true in the main database. They are stored
locally but not synced via git.

The list shows:
  - ID: Issue ID of the wisp
  - Title: Wisp title
  - Status: Current status (open, in_progress, closed)
  - Started: When the wisp was created
  - Updated: Last modification time

Old wisp detection:
  - Old wisps haven't been updated in 24+ hours
  - Use 'bd mol wisp gc' to clean up old/abandoned wisps
```

**Usage**

```text
bd mol wisp list [flags]
```

**Examples**

```text
  bd mol wisp list              # List all wisps
  bd mol wisp list --json       # JSON output for programmatic use
  bd mol wisp list --all        # Include closed wisps
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` |  |  | Include closed wisps |
| `--help` | `-h` |  | help for list |
| `--type` |  | string | Filter by issue type (e.g., agent, task, patrol) |

<a id="bd-mol-wisp-gc"></a>

#### `bd mol wisp gc`

```text
Garbage collect old or abandoned wisps from the database.

A wisp is considered abandoned if:
  - It hasn't been updated in --age duration and is not closed
  - AND it is not live work: blocked steps (waiting on a dependency), pinned
    beads, and any step whose status category is wip (in_progress, blocked,
    hooked) or frozen (deferred, pinned) are never reclaimed by age, no matter
    how long they have been waiting (GH#4394). Custom statuses count by their
    configured category, so only plain open (active) and closed (done) steps
    are age-reclaimable. If the blocked set or the custom-status list cannot be
    read, the GC aborts rather than risk reclaiming live steps.

Abandoned wisps are deleted without creating a digest. Use 'bd mol squash'
if you want to preserve a summary before garbage collection.

Use --closed to purge ALL closed wisps (regardless of age). This is the
fastest way to reclaim space from accumulated wisp bloat. Safe by default:
requires --force to actually delete.

Note: This uses time-based cleanup, appropriate for ephemeral wisps.
For graph-pressure staleness detection (blocking other work), see 'bd mol stale'.
```

**Usage**

```text
bd mol wisp gc [flags]
```

**Examples**

```text
  bd mol wisp gc                                    # Clean abandoned wisps (default: 1h threshold)
  bd mol wisp gc --dry-run                          # Preview what would be cleaned
  bd mol wisp gc --age 24h                          # Custom age threshold
  bd mol wisp gc --all                              # Also clean closed wisps older than threshold
  bd mol wisp gc --closed                           # Preview closed wisp deletion
  bd mol wisp gc --closed --force                   # Delete all closed wisps
  bd mol wisp gc --closed --dry-run                 # Explicit dry-run (same as no --force)
  bd mol wisp gc --exclude-type agent,rig           # Protect agent and rig wisps from GC
  bd mol wisp gc --closed --force --exclude-type mol # Delete closed wisps except mol type
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--age` |  | string | Age threshold for abandoned wisp detection (default "1h") |
| `--all` |  |  | Also clean closed wisps older than threshold |
| `--closed` |  |  | Delete all closed wisps (ignores --age threshold) |
| `--dry-run` |  |  | Preview what would be cleaned |
| `--exclude-type` |  | strings | Exclude wisps of these types from GC (comma-separated, e.g., agent,rig) |
| `--force` | `-f` |  | Actually delete (default: preview only) |
| `--help` | `-h` |  | help for gc |

<a id="bd-mol-wisp-create"></a>

#### `bd mol wisp create`

```text
Create a wisp from a proto - sublimation from solid to vapor.

This is the chemistry-inspired command for creating ephemeral work from templates.
The resulting wisp is stored in the main database with Ephemeral=true and NOT synced via git.

Phase transition: Proto (solid) -> Wisp (vapor)

Use wisp for:
  - Operational loops and recurring cycles
  - Health checks and monitoring
  - One-shot orchestration runs
  - Routine operations with no audit value

The wisp will:
  - Be stored in main database with Ephemeral=true flag
  - NOT be synced via git
  - Either evaporate (burn) or condense to digest (squash)
```

**Usage**

```text
bd mol wisp create <proto-id> [flags]
```

**Examples**

```text
  bd mol wisp create mol-patrol                    # Ephemeral patrol cycle
  bd mol wisp create mol-health-check              # One-time health check
  bd mol wisp create mol-diagnostics --var target=db  # Diagnostic run
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview what would be created |
| `--help` | `-h` |  | help for create |
| `--root-only` |  |  | Create only the root issue (no child step issues) |
| `--var` |  | stringArray | Variable substitution (key=value) |

<a id="bd-mol-bond"></a>

### `bd mol bond`

```text
Bond two protos or molecules to create a compound.

The bond command is polymorphic - it handles different operand types:

  formula + formula → cook both, compound proto
  formula + proto   → cook formula, compound proto
  formula + mol     → cook formula, spawn and attach
  proto + proto     → compound proto (reusable template)
  proto + mol       → spawn proto, attach to molecule
  mol + proto       → spawn proto, attach to molecule
  mol + mol         → join into compound molecule

Formula names (e.g., mol-polecat-arm) are cooked inline as ephemeral protos.
This avoids needing pre-cooked proto beads in the database.

Bond types:
  sequential (default) - B runs after A completes
  parallel            - B runs alongside A
  conditional         - B runs only if A fails

Phase control:
  By default, spawned protos follow the target's phase:
  - Attaching to mol (Ephemeral=false) → spawns as persistent (Ephemeral=false)
  - Attaching to ephemeral issue (Ephemeral=true) → spawns as ephemeral (Ephemeral=true)

  Override with:
  --pour  Force spawn as liquid (persistent, Ephemeral=false)
  --ephemeral  Force spawn as vapor (ephemeral, Ephemeral=true, excluded from Dolt sync via dolt_ignore)

Dynamic bonding (Christmas Ornament pattern):
  Use --ref to specify a custom child reference with variable substitution.
  This creates IDs like "parent.child-ref" instead of random hashes.

  Example:
    bd mol bond mol-worker-arm bd-patrol --ref arm-{{worker_name}} --var worker_name=ace
    # Creates: bd-patrol.arm-ace (and children like bd-patrol.arm-ace.capture)

Use cases:
  - Found important bug during patrol? Use --pour to persist it
  - Need ephemeral diagnostic on persistent feature? Use --ephemeral
  - Spawning per-worker arms on a patrol? Use --ref for readable IDs
```

**Usage**

```text
bd mol bond <A> <B> [flags]
```

**Aliases:** `bond, fart`

**Examples**

```text
  bd mol bond mol-feature mol-deploy                    # Compound proto
  bd mol bond mol-feature mol-deploy --type parallel    # Run in parallel
  bd mol bond mol-feature bd-abc123                     # Attach proto to molecule
  bd mol bond bd-abc123 bd-def456                       # Join two molecules
  bd mol bond mol-critical-bug wisp-patrol --pour       # Persist found bug
  bd mol bond mol-temp-check bd-feature --ephemeral          # Ephemeral diagnostic
  bd mol bond mol-arm bd-patrol --ref arm-{{name}} --var name=ace  # Dynamic child ID
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--as` |  | string | Custom title for compound proto (proto+proto only) |
| `--dry-run` |  |  | Preview what would be created |
| `--ephemeral` |  |  | Force spawn as vapor (ephemeral, Ephemeral=true) |
| `--help` | `-h` |  | help for bond |
| `--pour` |  |  | Force spawn as liquid (persistent, Ephemeral=false) |
| `--ref` |  | string | Custom child reference with {{var}} substitution (e.g., arm-{{polecat_name}}) |
| `--type` |  | string | Bond type: sequential, parallel, or conditional (default "sequential") |
| `--var` |  | stringArray | Variable substitution for spawned protos (key=value) |

<a id="bd-mol-squash"></a>

### `bd mol squash`

```text
Squash a molecule's ephemeral children into a single digest issue.

This command collects all ephemeral child issues of a molecule (Ephemeral=true),
generates a summary digest, and promotes the wisps to persistent by
clearing their Wisp flag (or optionally deletes them).

The squash operation:
  1. Loads the molecule and all its children
  2. Filters to only wisps (ephemeral issues with Ephemeral=true)
  3. Generates a digest (summary of work done)
  4. Creates a permanent digest issue (Ephemeral=false)
  5. Clears Wisp flag on children (promotes to persistent)
     OR keeps them with --keep-children (default: delete)

AGENT INTEGRATION:
Use --summary to provide an AI-generated summary. This keeps bd as a pure
tool - the calling agent (orchestrator worker, Claude Code, etc.) is responsible
for generating intelligent summaries. Without --summary, a basic concatenation
of child issue content is used.

This is part of the wisp workflow: spawn creates wisps,
execution happens, squash compresses the trace into an outcome (digest).

Example:
  bd mol squash bd-abc123                    # Squash and promote children
  bd mol squash bd-abc123 --dry-run          # Preview what would be squashed
  bd mol squash bd-abc123 --keep-children    # Keep wisps after digest
  bd mol squash bd-abc123 --summary "Agent-generated summary of work done"
```

**Usage**

```text
bd mol squash <molecule-id> [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview what would be squashed |
| `--help` | `-h` |  | help for squash |
| `--keep-children` |  |  | Don't delete ephemeral children after squash |
| `--summary` |  | string | Agent-provided summary (bypasses auto-generation) |

<a id="bd-mol-burn"></a>

### `bd mol burn`

```text
Burn a molecule, deleting it without creating a digest.

Unlike squash (which creates a permanent digest before deletion), burn
completely removes the molecule with no trace. Use this for:
  - Abandoned patrol cycles
  - Crashed or failed workflows
  - Test/debug molecules you don't want to preserve

The burn operation differs based on molecule phase:
  - Wisp (ephemeral): Direct delete
  - Mol (persistent): Cascade delete (syncs to remotes)

CAUTION: This is a destructive operation. The molecule's data will be
permanently lost. If you want to preserve a summary, use 'bd mol squash'.

Example:
  bd mol burn bd-abc123              # Delete molecule with no trace
  bd mol burn bd-abc123 --dry-run    # Preview what would be deleted
  bd mol burn bd-abc123 --force      # Skip confirmation
  bd mol burn bd-a1 bd-b2 bd-c3      # Batch delete multiple wisps
```

**Usage**

```text
bd mol burn <molecule-id> [molecule-id...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview what would be deleted |
| `--force` |  |  | Skip confirmation prompt |
| `--help` | `-h` |  | help for burn |

<a id="bd-mol-distill"></a>

### `bd mol distill`

```text
Distill a molecule by extracting a reusable formula from an existing epic.

This is the reverse of pour: instead of formula → molecule, it's molecule → formula.

The distill command:
  1. Loads the existing epic and all its children
  2. Converts the structure to a .formula.json file
  3. Replaces concrete values with {{variable}} placeholders (via --var flags)

Use cases:
  - Team develops good workflow organically, wants to reuse it
  - Capture tribal knowledge as executable templates
  - Create starting point for similar future work

Variable syntax (both work - we detect which side is the concrete value):
  --var branch=feature-auth    Spawn-style: variable=value (recommended)
  --var feature-auth=branch    Substitution-style: value=variable

Output locations (first writable wins):
  1. <resolved-beads-dir>/formulas/ (project-level, default)
  2. <checkout-root>/.beads/formulas/ (repo-local formulas)
  3. ~/.beads/formulas/     (user-level, if project not writable)
```

**Usage**

```text
bd mol distill <epic-id> [formula-name] [flags]
```

**Examples**

```text
  bd mol distill bd-o5xe my-workflow
  bd mol distill bd-abc release-workflow --var feature_name=auth-refactor
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview what would be created |
| `--help` | `-h` |  | help for distill |
| `--output` |  | string | Output directory for formula file |
| `--var` |  | stringArray | Replace value with {{variable}} placeholder (variable=value) |

<a id="bd-mol-current"></a>

### `bd mol current`

```text
Show where you are in a molecule workflow.

If molecule-id is given, show status for that molecule.
If not given, infer from in_progress issues assigned to current agent.

The output shows all steps with status indicators:
  [done]     - Step is complete (closed)
  [current]  - Step is in_progress (you are here)
  [ready]    - Step is ready to start (unblocked)
  [blocked]  - Step is blocked by dependencies
  [pending]  - Step is waiting

For large molecules (>100 steps), a summary is shown instead.

Use --limit or --range to view specific steps:
  bd mol current <id> --limit 50       # Show first 50 steps
  bd mol current <id> --range 100-150  # Show steps 100-150
```

**Usage**

```text
bd mol current [molecule-id] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--for` |  | string | Show molecules for a specific agent/assignee |
| `--help` | `-h` |  | help for current |
| `--limit` |  | int | Maximum number of steps to display (0 = auto, use 'all' threshold) |
| `--range` |  | string | Display specific step range (e.g., '1-50', '100-150') |

<a id="bd-mol-progress"></a>

### `bd mol progress`

```text
Show efficient progress summary for a molecule.

This command uses indexed queries to count progress without loading all steps,
making it suitable for very large molecules (millions of steps).

If no molecule-id is given, shows progress for any molecule you're working on.

Output includes:
  - Progress: completed / total (percentage)
  - Current step: the in-progress step (if any)
  - Rate: steps/hour based on closure times
  - ETA: estimated time to completion

Example:
  bd mol progress bd-hanoi-xyz
```

**Usage**

```text
bd mol progress [molecule-id] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for progress |

<a id="bd-mol-ready"></a>

### `bd mol ready`

```text
Find molecules where a gate has closed and the workflow is ready to resume.

This command discovers molecules waiting at a gate step where:
1. The molecule has a gate bead that blocks a step
2. The gate bead is now closed (condition satisfied)
3. The blocked step is now ready to proceed
4. No agent currently has this molecule hooked

This enables discovery-based resume without explicit waiter tracking.
The patrol system uses this to find and dispatch gate-ready molecules.
```

**Usage**

```text
bd mol ready --gated [flags]
```

**Examples**

```text
  bd mol ready --gated           # Find all gate-ready molecules
  bd mol ready --gated --json    # JSON output for automation
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--gated` |  |  | Find molecules ready for gate-resume dispatch (always on for this subcommand) |
| `--help` | `-h` |  | help for ready |

<a id="bd-mol-seed"></a>

### `bd mol seed`

```text
Verify that a formula is accessible and can be cooked.

The seed command checks formula search paths to ensure a formula exists
and can be loaded. This is useful for verifying system health before
attempting to spawn work from a formula.

Formula search paths (checked in order):
  1. <resolved-beads-dir>/formulas/ (active project)
  2. <checkout-root>/.beads/formulas/ (repo-local formulas)
  3. ~/.beads/formulas/ (user level)
  4. $GT_ROOT/.beads/formulas/ (shared workspace root, if GT_ROOT set)
```

**Usage**

```text
bd mol seed <formula-name> [flags]
```

**Examples**

```text
  bd mol seed mol-feature                 # Verify specific formula
  bd mol seed mol-review --var name=test  # Verify with variable substitution
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for seed |
| `--var` |  | stringArray | Variable substitution for condition filtering (key=value) |

<a id="bd-mol-stale"></a>

### `bd mol stale`

```text
Detect molecules (epics with children) that are complete but still open.

A molecule is considered stale if:
  1. All children are closed (Completed == Total)
  2. Root issue is still open
  3. Not assigned to anyone (optional, use --unassigned)
  4. Is blocking other work (optional, use --blocking)

By default, shows all complete-but-unclosed molecules.
```

**Usage**

```text
bd mol stale [flags]
```

**Examples**

```text
  bd mol stale              # List all stale molecules
  bd mol stale --json       # Machine-readable output
  bd mol stale --blocking   # Only show those blocking other work
  bd mol stale --unassigned # Only show unassigned molecules
  bd mol stale --all        # Include molecules with 0 children
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--all` |  |  | Include molecules with 0 children |
| `--blocking` |  |  | Only show molecules blocking other work |
| `--help` | `-h` |  | help for stale |
| `--unassigned` |  |  | Only show unassigned molecules |

<a id="bd-notion"></a>

## `bd notion`

```text
Commands for syncing issues between beads and Notion.
```

**Usage**

```text
bd notion [command]
```

**Available Commands**

- [`connect`](#bd-notion-connect) — Connect bd to an existing Notion database or data source
- [`init`](#bd-notion-init) — Create a dedicated Beads database in Notion
- [`pull`](#bd-notion-pull) — Pull specific items from Notion
- [`push`](#bd-notion-push) — Push specific beads to Notion
- [`status`](#bd-notion-status) — Show Notion sync status
- [`sync`](#bd-notion-sync) — Sync issues with Notion

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for notion |

<a id="bd-notion-connect"></a>

### `bd notion connect`

```text
Connect bd to an existing Notion database or data source
```

**Usage**

```text
bd notion connect [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for connect |
| `--url` |  | string | Existing Notion database or data source URL |

<a id="bd-notion-init"></a>

### `bd notion init`

```text
Create a dedicated Beads database in Notion
```

**Usage**

```text
bd notion init [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for init |
| `--parent` |  | string | Parent page ID |
| `--title` |  | string | Database title (default "Beads Issues") |

<a id="bd-notion-pull"></a>

### `bd notion pull`

```text
Pull one or more items from Notion.

Accepts bead IDs or external references as positional arguments.
Equivalent to: bd notion sync --pull --issues <refs>
```

**Usage**

```text
bd notion pull [refs...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview pull without making changes |
| `--help` | `-h` |  | help for pull |

<a id="bd-notion-push"></a>

### `bd notion push`

```text
Push one or more beads issues to Notion.

Accepts bead IDs as positional arguments.
Equivalent to: bd notion sync --push --issues <ids>
```

**Usage**

```text
bd notion push [bead-ids...] [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview push without making changes |
| `--help` | `-h` |  | help for push |

<a id="bd-notion-status"></a>

### `bd notion status`

```text
Show Notion sync status
```

**Usage**

```text
bd notion status [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for status |

<a id="bd-notion-sync"></a>

### `bd notion sync`

```text
Synchronize issues between beads and Notion.

By default this performs bidirectional sync. Use --pull or --push to limit direction.
```

**Usage**

```text
bd notion sync [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--create-only` |  |  | Only create missing remote pages, do not update existing ones |
| `--dry-run` |  |  | Preview changes without making mutations |
| `--help` | `-h` |  | help for sync |
| `--issues` |  | string | Comma-separated bead IDs to sync selectively (e.g., bd-abc,bd-def). Mutually exclusive with --parent. |
| `--parent` |  | string | Limit push to this bead and its descendants (push only). Mutually exclusive with --issues. |
| `--prefer-local` |  |  | On conflict, keep the local beads version |
| `--prefer-notion` |  |  | On conflict, use the Notion version |
| `--pull` |  |  | Only pull issues from Notion |
| `--push` |  |  | Only push issues to Notion |
| `--state` |  | string | Issue state to sync: open, closed, or all (default "all") |

<a id="bd-orphans"></a>

## `bd orphans`

```text
Identify orphaned issues - issues that are referenced in commit messages but remain open or in_progress in the database.

This helps identify work that has been implemented but not formally closed.
```

**Usage**

```text
bd orphans [flags]
```

**Examples**

```text
  bd orphans              # Show orphaned issues
  bd orphans --json       # Machine-readable output
  bd orphans --details    # Show full commit information
  bd orphans --fix        # Close orphaned issues with confirmation
  bd orphans --label theme:personal             # Only orphans with this label
  bd orphans --label-any theme:personal,theme:ventures  # Orphans with either label
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--details` |  |  | Show full commit information |
| `--fix` | `-f` |  | Close orphaned issues with confirmation |
| `--help` | `-h` |  | help for orphans |
| `--label` | `-l` | strings | Filter by labels (AND: must have ALL). Can combine with --label-any |
| `--label-any` |  | strings | Filter by labels (OR: must have AT LEAST ONE). Can combine with --label |

<a id="bd-ready"></a>

## `bd ready`

```text
Show ready work (open issues with no active blockers).

Excludes in_progress, blocked, deferred, and hooked issues. This uses the
GetReadyWork API which applies blocker-aware semantics to find truly claimable work.

Note: 'bd list --ready' uses the same blocker-aware ready-work semantics.

Use --mol to filter to a specific molecule's steps:
  bd ready --mol bd-patrol   # Show ready steps within molecule

Use --gated to find molecules ready for gate-resume dispatch:
  bd ready --gated           # Find molecules where a gate closed

Use --claim to atomically claim the first ready issue matching the filters:
  bd ready --claim --json

This is useful for agents executing molecules to see which steps can run next.
```

**Usage**

```text
bd ready [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--assignee` | `-a` | string | Filter by assignee |
| `--brief` |  |  | Omit the free-form text (description, design, acceptance criteria, notes, payload, waiters) from each row. Filters that read those fields still select on them. An omitted field is indistinguishable from an empty one; fetch a whole issue with bd show. Requires --json, and cannot be combined with --claim, --gated, --mol or --explain. |
| `--claim` |  |  | Atomically claim the first ready issue matching the filters |
| `--exclude-label` |  | strings | Exclude issues that have ANY of these labels |
| `--exclude-type` |  | strings | Exclude issue types from results (comma-separated or repeatable, e.g., --exclude-type=convoy,epic) |
| `--explain` |  |  | Show dependency-aware reasoning for why issues are ready or blocked |
| `--gated` |  |  | Find molecules ready for gate-resume dispatch |
| `--has-metadata-key` |  | string | Filter issues that have this metadata key set |
| `--help` | `-h` |  | help for ready |
| `--include-deferred` |  |  | Include issues with future defer_until timestamps |
| `--include-ephemeral` |  |  | Include ephemeral issues (wisps) in results |
| `--label` | `-l` | strings | Filter by labels (AND: must have ALL). Can combine with --label-any |
| `--label-any` |  | strings | Filter by labels (OR: must have AT LEAST ONE). Can combine with --label |
| `--label-pattern` |  | string | Filter by label glob pattern (e.g., 'tech-*' matches tech-debt, tech-legacy) |
| `--label-regex` |  | string | Filter by label regex pattern (e.g., 'tech-(debt\|legacy)') |
| `--limit` | `-n` | int | Maximum issues to show (use 0 for unlimited) (default 100) |
| `--max-rows` |  | int | Hard upper bound on rows fetched from storage. Returns a non-zero exit (code 2) and an error to stderr if exceeded. 0 disables (the default). Overrides BEADS_MAX_ROWS for this invocation. Useful in CI/agent rigs that want a circuit breaker against pathological queries. Not supported under --proxied-server: an explicit --max-rows or BEADS_MAX_ROWS cap errors out rather than silently going unenforced. |
| `--metadata-field` |  | stringArray | Filter by metadata field (key=value, repeatable) |
| `--mol` |  | string | Filter to steps within a specific molecule |
| `--mol-type` |  | string | Filter by molecule type: swarm, patrol, or work |
| `--offset` |  | int | Skip the first N matching results (0-based). Only supported under --proxied-server. |
| `--parent` |  | string | Filter to descendants of this bead/epic |
| `--plain` |  |  | Display issues as a plain numbered list |
| `--pretty` |  |  | Display issues in a tree format with status/priority symbols (default true) |
| `--priority` | `-p` | int | Filter by priority |
| `--sort` | `-s` | string | Sort policy: priority (default), hybrid, oldest (default "priority") |
| `--type` | `-t` | string | Filter by issue type (task, bug, feature, epic, decision, merge-request). Aliases: mr→merge-request, feat→feature, mol→molecule, dec/adr→decision |
| `--unassigned` | `-u` |  | Show only unassigned issues |

<a id="bd-rename"></a>

## `bd rename`

```text
Rename an issue from one ID to another.

This updates:
- The issue's primary ID
- All references in other issues (descriptions, titles, notes, etc.)
- Dependencies pointing to/from this issue
- Labels, comments, and events
```

**Usage**

```text
bd rename <old-id> <new-id> [flags]
```

**Examples**

```text
  bd rename bd-w382l bd-dolt     # Rename to memorable ID
  bd rename gt-abc123 gt-auth    # Use descriptive ID

Note: The new ID must use a valid prefix for this database.
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for rename |

<a id="bd-schema"></a>

## `bd schema`

```text
Print the JSON Schema for bd's canonical output record types.

The schema is reflected from the same Go structs bd serializes, so it stays in
lockstep with the actual --json / export output. Use it to generate typed
consumer models (datamodel-code-generator, quicktype, ...) rather than
hand-maintaining them.

  bd schema | jq '.types.issue'        # the issue record schema
  bd schema | jq '.types.dependency'   # the dependency record schema
```

**Usage**

```text
bd schema [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for schema |

<a id="bd-serve"></a>

## `bd serve`

```text
Serve the beads HTTP API — the same work surface the CLI answers, for
automation clients that would otherwise fork a bd subprocess per call.

The wire contract is described by an OpenAPI document (/v0); GET
/v0/beads/context reports which operations this build actually implements.

DEPLOYMENT

  Pass an explicit port. The default 127.0.0.1:0 takes an ephemeral one, which
  is right for ad-hoc and test use — where the bound address printed on stdout
  is read immediately — but carries no mutual exclusion: two serves against one
  workspace then run side by side on different ports with no way to enumerate
  them. On a fixed port the second one fails to bind, which is the intended
  behavior. Concurrent serves are data-safe either way; claims are arbitrated
  in the SQL server.

  Run it under a supervisor. bd shuts down gracefully on SIGHUP as well as
  SIGINT and SIGTERM, so closing the terminal of a foreground bd serve stops it.

PROBES

  GET /healthz is LIVENESS only: it answers from the process and never touches
  the database, so it stays green while the database is unreachable. For
  readiness use GET /v0/beads/ready?limit=1 — a real query, where 200 means
  ready and 503 means live but not ready.

AUTHENTICATION

  Optional, and off by default on loopback — where the trust model is the
  loopback boundary itself, the same one the database behind it already relies
  on. --auth-token-file turns it on: every operation except GET /healthz then
  requires an "Authorization: Bearer <token>" header, GET /v0/beads/context
  included, because it reports the repo root, beads directory and database name.

  The file holds ONE TOKEN PER LINE and every line is accepted. That is the
  rotation mechanism: write the new token alongside the old, roll the clients
  over, then delete the old line. The file is re-read while the server runs, so
  both the addition and the removal take effect within about a second and
  neither needs a restart. Write it atomically (a temp file plus rename; a
  Kubernetes secret mount already does this).

  There is deliberately no --auth-token flag. A credential passed as an
  argument is readable by every local user in the process listing.

  --allow-non-loopback REQUIRES a token file. Beyond loopback, reaching the
  address would otherwise be the whole authorization: any peer could read every
  issue and claim work as any actor. --insecure-no-auth is the explicit,
  auditable way to say you meant that anyway.

  The Host allowlist is what a service deployment usually trips over first. The
  DNS-rebinding check answers only to loopback spellings and the bind address,
  so a client dialing a service name gets 400 on every request; enumerate the
  names it dials with --allowed-host (repeatable). Matching is exact — no
  wildcards — and the startup log line prints the effective allowlist.

WHAT THIS DOES NOT DO

  No TLS. Even with a token, the credential and every issue body travel in
  plaintext, so a deployment beyond loopback has to supply confidentiality
  itself — a service mesh, or a network boundary you already trust.

  Hooks do not fire. A hook is a user-controlled subprocess per mutation: in a
  concurrent server that is an unbounded latency multiplier and an orphaned
  child at shutdown, and its working-directory-derived hook lookup is
  meaningless in a server process. A CLI claim runs on_update; an HTTP claim
  does not.

  The per-command auto-commit machinery does not run. Durability is per request:
  a successful claim commits inside its own transaction, exactly as a proxied
  CLI claim does today.

  An actor on an HTTP request is caller-asserted provenance for the audit trail,
  not authenticated identity — the same thing it has always been on the CLI,
  where any local process can pass any --actor.

  It does not run under --readonly, and refuses to start rather than binding.
  Every server it binds publishes the issue-claim operation, and the capability
  set it advertises is a property of the build rather than of the flags on the
  process that started it — so a read-only server would advertise a write it
  could never land.

DESTRUCTIVE OPERATIONS

  POST /v0/beads/issues:sweep deletes closed beads in bulk — the operation
  behind bd purge and bd prune — and nothing it deletes comes back. It shares
  the library surface those commands call, so it inherits their guards: pinned
  beads are never swept, and a durable sweep with neither a cutoff nor an id
  pattern is refused rather than clearing every closed bead in the workspace.
  Combined with the trust model above, that means anyone who can reach this
  address can erase closed work; bind it accordingly.
```

**Usage**

```text
bd serve [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--addr` |  | string | Address to bind as IP:PORT; the host must be a numeric IP literal, and port 0 takes an ephemeral port (default "127.0.0.1:0") |
| `--allow-non-loopback` |  |  | Permit a bind beyond loopback. Requires --auth-token-file, since reaching the address would otherwise be the whole authorization |
| `--allowed-host` |  | stringArray | Additional Host header value to answer to, e.g. a service DNS name. Repeatable; matched exactly, with no wildcards |
| `--auth-token-file` |  | string | Require an Authorization: Bearer token from this file, one token per line, all accepted. Re-read while running, so rewriting it rotates tokens without a restart (env BEADS_SERVE_TOKEN_FILE) |
| `--help` | `-h` |  | help for serve |
| `--insecure-no-auth` |  |  | Serve a non-loopback bind with NO authentication. Every peer that can reach the address gets full read and claim access |

<a id="bd-ship"></a>

## `bd ship`

```text
Ship a capability to satisfy cross-project dependencies.

This command:
  1. Finds issue with export:<capability> label
  2. Validates issue is closed (or --force to override)
  3. Adds provides:<capability> label

External projects can depend on this capability using:
  bd dep add <issue> external:<project>:<capability>

The capability is resolved when the external project has a closed issue
with the provides:<capability> label.
```

**Usage**

```text
bd ship <capability> [flags]
```

**Examples**

```text
  bd ship mol-run-assignee              # Ship the mol-run-assignee capability
  bd ship mol-run-assignee --force      # Ship even if issue is not closed
  bd ship mol-run-assignee --dry-run    # Preview without making changes
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--dry-run` |  |  | Preview without making changes |
| `--force` |  |  | Ship even if issue is not closed |
| `--help` | `-h` |  | help for ship |

<a id="bd-undefer"></a>

## `bd undefer`

```text
Undefer issues to restore them to open status.

This brings issues back from the icebox so they can be worked on again.
Issues will appear in 'bd ready' if they have no blockers.
```

**Usage**

```text
bd undefer [id...] [flags]
```

**Examples**

```text
  bd undefer bd-abc        # Undefer a single issue
  bd undefer bd-abc bd-def # Undefer multiple issues
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for undefer |

<a id="bd-version"></a>

## `bd version`

```text
Print version information
```

**Usage**

```text
bd version [flags]
```

**Flags**

| Flag | Short | Type | Description |
|---|---|---|---|
| `--help` | `-h` |  | help for version |
