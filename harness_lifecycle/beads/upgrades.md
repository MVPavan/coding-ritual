# Upgrading Beads across projects

How to reason about a `bd` upgrade that touches every Beads-backed project on
a machine. The goal is the thinking that produces a safe procedure, not a
fixed procedure. Each upgrade gets its own concrete plan in its Bead, derived
from these principles and the release's own upgrade notes.

Owner: MVPavan. Written 2026-09-30 while reviewing the 1.1.0 → 1.3.0 plan
(vip-agent bead vip-8fw.1). Vendor facts below are dated; re-verify them for each upgrade.

## Why this needs care

A `bd` upgrade can apply schema migrations. These are one-way:

- an older binary refuses a database migrated past the schema it knows;
- once a migrated schema is pushed to a Dolt remote, every clone of that
  remote has to follow;
- if two clones migrate independently, the schema forks, and upstream
  documents some forks as unrecoverable.

One shared binary serves every project at once, so a mistake is not limited
to one project.

## Principles

### 1. Map the real topology before trusting any plan

Plans go wrong when they assume a topology. Before planning, list every
`.beads` directory on the machine and record for each:

- storage mode (embedded or server);
- which database it resolves to (`bd where`);
- its Dolt remote (`bd dolt remote list`);
- whether it is its own clone or a git worktree of another clone.

A worktree shares its main clone's database. It is not a second clone, and
running clone procedures in it (for example `bd bootstrap`) is wrong. Also
list every `bd` on `PATH` (`which -a bd`), every long-running `bd` process,
and every *other* machine or cloud session that holds a clone of each Dolt
remote. Those clones are outside the local inventory, and they are the
source of the unrecoverable failures.

*Evidence (checked 2026-09-30):* the first plan counted worktrees as clones
and planned to bootstrap them. It also missed a second `bd` from a global npm
install, a database without a remote, and a legacy server-mode workspace
inside a reference checkout.

### 2. Know exactly what triggers the irreversible step

Find out which commands cause the migration. Do not assume only `bd migrate`
does. In 1.3.0 embedded mode, any command that opens the store (including
reads such as `bd list` and `bd prime`) applies pending migrations, and the
migration freeze does not stop that (upstream #6686, open 2026-09-30).
`bd version` and `bd where` do not open the store.

So installing the new binary where hooks can find it means the next
session-start hook, git hook or agent command migrates whichever project it
touches. Pausing agents is therefore a correctness requirement, not a
courtesy. It covers:

- agent sessions (local and cloud);
- git operations, which run the Beads git hooks;
- scheduled jobs;
- IDE integrations.

### 3. Capture everything the old binary can see, using the old binary

A backup taken with the new binary is post-migration and protects nothing.
Two backups per database, both taken with the old binary and with no `bd`
process running:

- a copy of the whole `.beads` directory, which keeps Dolt history, config
  and clone-local tables. This is the real rollback;
- a `bd export --all` JSONL, which is issue-complete and importable by any
  version. This is the audit trail.

Record a baseline (`bd stats --json`, `bd doctor`) to compare against
afterwards. Keep the old binary, and check its hash.

### 4. Converge every source of truth before migrating

Migrating a database that is missing commits from elsewhere can strand the
database permanently. In 1.3.0, migration 0062 makes a migrated store unable
to merge any un-pulled pre-migration commits (upstream #6727, P0,
open 2026-09-30).

So before migrating:

- push and pull with the old binary;
- confirm a second pull has nothing new;
- absorb any Beads changes that arrive by other channels, such as committed
  `issues.jsonl` from cloud sessions (`beads` skill, `references/usage.md`
  §19).

Also check for uncommitted clone-local state: dirty ignored tables block
migration with no loss-free recovery (upstream #5816).

### 5. Rehearse on faithful copies with the exact binary

Pin the target release. Download the asset, check it against the published
`checksums.txt`, and use that same file for the rehearsal and the real run.
Never install from a moving `main` script.

Rehearse on copies of every database, with production-like conditions,
because the gate behaves differently with and without a remote. Point each
copy's Dolt remote at a scratch `file://` remote seeded from the copy, never
at the real remote. Confirm with `bd where` that the command targets the
copy before running anything. The rehearsal passes only if these match the
baseline:

- stats;
- a diff of issues exported before and after (issues, dependencies,
  comments, memories);
- `bd doctor`, where the storage mode supports it.

It must also show what the upgrade changes in tracked files: hooks and the
auto-exported `issues.jsonl`. Reproduce each project's hook wiring
(`core.hooksPath`) in the copy, or the rehearsal installs hooks somewhere else
and reports no change. In 2026-09-30 that is exactly what happened: the
rehearsal showed no hook diff, and production rewrote every tracked hook.

Compare meaning, not bytes. Treat every difference as unexplained until
traced to its cause, and check that the tool you are relying on actually
works in this storage mode.

*Evidence (checked 2026-09-30, 1.1.0 → 1.3.0):*

- Migrations re-keyed every comment and dependency ID, so exports differed
  byte-for-byte while content was identical.
- `bd doctor` prints "not yet supported in embedded mode" in both versions,
  so it cannot serve as a check there.
- One database's blocked count moved by two with identical dependency rows.
  The migration had left the derived `is_blocked` flag wrong for two
  issues. 1.3.0's own `bd recompute-blocked` corrected exactly those two back
  to the baseline, so it is now a required post-migration step.

### 6. Separate the point of no return, and put verification before it

On a machine with one clone per remote, migrating locally is reversible
(restore the `.beads` copy and the old binary). Pushing the migrated schema
is not. Run the new binary by explicit path, one database at a time:

1. Migrate one low-stakes database first, as a canary.
2. Verify it against its baseline before touching the next.
3. Push only after the database verifies.
4. Switch the shared binary on `PATH` last, and remove or upgrade every other
   `bd` on `PATH`.

If anything is unexpected, stop. Already-migrated databases that have not
been pushed can still be restored.

### 7. Prefer fail-closed states and upstream's own gates

Never force past a gate (`--force`, `BD_ALLOW_REMOTE_MIGRATE`, a disabled
smart gate) to get unstuck. The gates exist because the forced path corrupts
data. When a gate stops the run, read its guidance and bring the decision to
the owner. A stale binary refusing a migrated store is the safe failure;
silently migrating is the unsafe one.

### 8. Decide whether to upgrade at all, and to which release

Upgrade for a present requirement, not because a release exists. Before
choosing a target:

- read the release notes and open issues about migration, gates and
  bootstrap;
- check whether a patch release with relevant fixes is close, and compare
  the risk of waiting with the risk of going now.

*Example (2026-09-30):* 1.3.0 lacks the data-behind gate fix (#6575), which
ships in the 1.3.1 release candidates.

### 9. Changes to other repositories are part of the upgrade

`bd hooks install` rewrites hook files, and a new export format can rewrite
the tracked `issues.jsonl`. Both are tracked in each project, so the upgrade
produces a diff in every project. Plan per-project commits with the owner,
alongside those projects' own in-flight work. Expect new untracked files too. 1.3.0 creates a permanent
`<root>/.beads.gate.lock` that must be gitignored (`*.gate.lock*`) and never
deleted (checked 2026-09-30). Surface pre-existing anomalies
(for example a project whose active hooks live in `.git/hooks` while a stale tracked copy sits unused) rather than silently
fixing them.

## Keeping this document current

After each upgrade, add what surprised you as a principle or as evidence
under an existing one. Machine-specific inventories (project paths, clone
lists) belong in a gitignored `*.local.*` file or `scratchpad/`, never here.
This repository is public.
