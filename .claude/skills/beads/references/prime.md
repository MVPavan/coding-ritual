# Beads: core rules

Durable work is tracked in Beads (`bd`). These rules replace bd's built-in
prime text; the detail is in the `beads` skill (`references/usage.md`).

**Actor.** Add `--actor "<coding-agent>:<unique-id>"` to every write, the
same one all session. Claims belong to the actor that made them.

- **Coding agent:** `cc` (Claude Code), `codex`, `opencode`, `pi`, and so on.
- **Unique ID:** a session ID or session name.
  - cc: `${CLAUDE_CODE_SESSION_ID:0:8}`;
  - codex: `${CODEX_THREAD_ID:0:8}`.

## Scope

- One bead per durable unit of work: anything that must survive a reset,
  compaction or handoff. Turn-level checklists stay out.
- Knowledge goes in files, never `bd remember` or `bd kv`.
- Search before creating: `bd search "<terms>"`, which includes closed beads.

## Types

```text
epic                       top level
├── feature                a capability the owner would accept
│   └── task, bug, spike, decision
├── task                   a step one agent can finish
│   └── task               subtask, one level only
└── bug, spike, decision   may also be parentless until triaged
```

Create: `bd create "<title>" -t <type> [--parent <id>] -d "<why and what>"
--acceptance "<done-when>" [-p <0-4>]`. Priority 0 is the highest, 2 the
default, 4 the lowest.

- **bug:** the description has `## Steps to Reproduce`.
- **spike:** a question or an idea. The description has `## Goal` and an
  empty `## Findings`, and the findings go in the close reason. For an idea,
  add `-s deferred`.
- **decision:** a choice that outlives one bead. The description has
  `## Decision`, `## Rationale` and `## Alternatives Considered`. Small
  decisions are a comment. Revise one with `bd supersede <old> --with <new>`.
- **Multi-section text:** `--stdin <<'EOF'` … `EOF`.
- **Found while working:** a new bead with `--deps discovered-from:<origin>`.

## Fields

- **Replaced on write** (change with `bd update <id> …`):
  - description `-d`: why and what;
  - design `--design`: how;
  - acceptance `--acceptance`: done-when;
  - spec `--spec-id <path>`.
- **Notes:** `bd note <id> "…"` appends running state, `plan: <path>` and the
  resume line. Never `bd update --notes`, which replaces every note.
- **Comments:** `bd comment <id> "…"`, signed and dated. For findings,
  answers, approvals and evidence.
- **Close reason:** the evidence. `bd reopen` erases it, so lasting evidence
  also goes in a comment.
- Never `bd edit`.

## Labels, status, waits

- **The only label is `human`** (`-l human`): the owner must decide, answer
  or do it. The queue is `bd human list`.
- **Not now:** `bd defer <id> [--until +2w]`; bring it back with
  `bd undefer <id>`. Deferred is the backlog: `bd list --status deferred`.
- Never set `blocked` by hand.
- **Waits are edges.** `bd dep add <needs> <needed>`.
  - Owner decision: a `-l human` task the work depends on. The owner answers
    with `bd human respond <id> "…"`, which frees the work.
  - CI, PR, timer or external waits: gates (`usage.md` §9).

## Work and close

- **Pick:** `bd ready` lists open, unblocked beads. Take only beads with
  acceptance criteria.
- **Inside an epic:** `bd ready --parent <epic> --json`, keeping
  `.parent == "<epic>"` for direct children.
- **Read:** `bd show <id>`.
- **Children:**
  - create with `--parent <id>`;
  - list with `bd children <id>`;
  - move with `bd update <id> --parent <new>`, which keeps the ID.

  A parent closes only after all its children are closed.
- **Claim:** `bd update <id> --claim`, one bead at a time.
- **Pause:** `bd unclaim <id>`, then `bd note <id> "resume with: …"`.
- **Review:** a separate task done by another actor. Findings are comments;
  work they reveal becomes `discovered-from` beads.
- **Close** when acceptance holds: `bd close <id> [<id>…] --reason
  "<evidence>"`.
  - Never `--force` past open children.
  - Epics never close themselves: `bd epic close-eligible --dry-run`.
  - Rejected: `--reason "wontfix: <why>"`. Duplicate:
    `bd duplicate <id> --of <canonical>`.

## Never

- `bd gc`, `prune`, `purge` or `admin cleanup`: they delete closed beads.
- `bd init` on an existing project: use `bd bootstrap`.
- `bd setup`.
- `bd doctor`.
- A command without an ID: it targets the last bead `bd show` touched.

## Session

- **Start:** `bd list --status in_progress`, then resume from the last note.
- **End:**
  1. Close finished beads.
  2. Unclaim the rest, each with a resume line.
  3. Run the quality gates.
  4. Make sure `.beads/issues.jsonl` is current.
  5. Run `git status` and report.
  6. Commit, push or `bd dolt push` only with the owner's authority.
