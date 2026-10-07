# Beads usage

How projects that use this harness track work with Beads (`bd`, release
1.3.0). The core rules are in `prime.md`, which every session receives at
start and after compaction. This file holds the detail behind them. Installing
and adopting Beads in a project is in `setup.md`.

Behavior claims come from the tested capabilities guide
(`harness_lifecycle/beads/capabilities-1.3.0.md`). §19 lists
the behaviors most likely to catch an agent out. Owner decisions are dated
2026-10-06 unless stated.

## 1. Scope

- Beads holds durable work items: anything that must survive a reset, a
  compaction, a handoff or a multi-agent run, with its dependencies, blockers
  and follow-ups.
- One bead is one durable unit of work, not every step. Checklists for the
  current turn stay outside Beads.
- Knowledge (facts, decisions, preferences) lives in files: memory files,
  `docs/`, `.repo-context/learnings.md`. Do not use `bd remember`,
  `bd memories` or `bd kv`. Bd = work items only.
- Create a child bead only when the work benefits from separate ownership or
  acceptance; otherwise reuse the existing bead.

## 2. Identity

- Every write names its actor: `--actor "<coding-agent>:<unique-id>"`.
  - **Coding agent:** `cc` (Claude Code), `codex`, `opencode`, `pi`, and so on.
  - **Unique ID:** a session ID or session name.
    - cc: `${CLAUDE_CODE_SESSION_ID:0:8}` (set in every shell; checked on
      Claude Code 2.1.289);
    - codex: `${CODEX_THREAD_ID:0:8}` (owner-supplied, 2026-10-06).
  - A subagent or worker appends its role to its parent's actor
    (`cc:3f9a2c1d-review`). A review must come from a different actor than
    the author (§12).
- Use one actor for the whole session. A claim belongs to its actor: another
  actor's `close`, `assign` or `unclaim` is refused while the claim holds, so
  a session that switches actors cannot close its own claims.
- The plain git user name (bd's fallback when no actor is given) means the
  owner working by hand.
- Precedence: `--actor`, then `$BEADS_ACTOR`, then git `user.name`, then
  `$USER`. Claude Code does not keep environment variables between shell
  commands, so pass `--actor` on every write unless a hook sets
  `BEADS_ACTOR` for the session.

## 3. Types and hierarchy

Six types; no others:

| Type | Is | Parent | Children | Sections `bd lint` expects |
|---|---|---|---|---|
| `epic` | A body of work with one outcome: a phase or a slice of a workstream | none (always top level) | feature, task, bug, spike, decision | Success Criteria (the acceptance field counts) |
| `feature` | A capability the owner would accept | epic | task, bug, spike, decision | Acceptance Criteria |
| `task` | A unit of work one agent can finish in a session or two; also used for maintenance, reviews and owner actions | epic or feature; or a task (a subtask) | task (subtasks, one level) | Acceptance Criteria |
| `bug` | A defect | epic, feature, or none until triaged | none | Steps to Reproduce, Acceptance Criteria |
| `spike` | Anything not yet committed: a question to investigate or an idea to evaluate | epic or feature, or none (an idea) | none | Goal, Findings |
| `decision` | An architecture-level choice; the ADR text lives in `docs/adr/` | epic or feature, or none | none | Decision, Rationale, Alternatives Considered |

- Never create `story`, `chore`, `milestone` or custom types. Bd cannot remove
  its built-in types, so this is policy, not enforcement.
- Feature or task: a feature is something you would accept as a capability; a
  task is a step of work. A feature never contains an epic.
- An epic is top level: nothing sits above it. A bead may have no parent
  until triage gives it one (an idea, an external bug report).
- Only `epic` changes how bd behaves (`bd epic status`, `close-eligible`,
  `swarm`). The other types differ only in name and in the sections `bd lint`
  expects. Required sections are headings in the description, except
  Acceptance Criteria, which the acceptance field satisfies.
- Create multi-section descriptions with `--stdin` and a quoted heredoc, or
  `--body-file <file>`. A spike starts with `## Goal` (the question) and an
  empty `## Findings`; its findings go in the close reason, with long ones in
  a document linked from a comment.
- `bd create --parent <id>` gives dotted IDs (`p-abc.1`, `p-abc.1.1`). Beads
  created through `--graph` or reparented later keep plain IDs.
- Small decisions do not need a decision bead: record them in `design` or as
  a comment on the bead they affect. Use a decision bead when the choice
  outlives one work item, governs several beads or needs its own approval.
  Revise one with `bd supersede`.

## 4. Status

| Status | Means | Set by |
|---|---|---|
| `open` | available | default |
| `in_progress` | someone is working on it now | `--claim` |
| `deferred` | not now: ideas and backlog alike | `bd defer` |
| `closed` | done, rejected or replaced | `bd close`, `duplicate`, `supersede` |
| `pinned` | permanent; refuses edits and close without `--force` | rarely needed |

- **Deferred is the backlog.** There are no `idea` or `backlog` labels. An
  idea is a deferred spike; accepted-but-not-now work is any other deferred
  bead. `bd defer <id>` with no date parks it until `bd undefer`.
  `bd defer <id> --until +2w` snoozes it: there is no timer, and the next
  `bd ready` after that date returns it to open.
- `bd list --status deferred` shows the whole backlog; add `-t spike` for
  ideas.
- Never set `blocked` by hand. A stored `blocked` status with no dependency is
  invisible to both `bd ready` and `bd blocked`. Record every wait as an edge
  (§9).

## 5. Labels

- `human` is the only label. Bd's `bd human list`, `respond` and `dismiss`
  are built on it. It marks a bead the owner must act on: a decision, an
  answer or an action.
- Do not create other labels. Existing labels on old beads stay; nothing new
  relies on them.
- A child created with `--parent` copies all of its parent's labels
  (`--no-inherit-labels` stops it). A child of a `human` bead would inherit
  `human`, so give `human` beads no children.

## 6. Fields

Each field has one job:

| Field | Holds | Write with | Notes |
|---|---|---|---|
| title | the outcome, in a few words | `create` | |
| description | why and what: the request, scope, non-goals; the type's required headings | `-d`, `--body-file`, `--stdin` | rewrite only to correct it |
| `spec_id` | the document that anchors the bead (§7) | `--spec-id` | one path or URL; filter with `bd list --spec <prefix>`; children do not inherit it; bd never opens it |
| design | how: the approach; on phase epics, the governing spec's path (§7) | `--design`, `--design-file` | `--design-file` copies the file's text at that moment; it is not a link |
| acceptance | testable done-when, with the check commands | `--acceptance` | no file input |
| notes | running state: progress, open questions, what triage settled, the plan path (`plan: <path>`), the resume line | `bd note` (`--file`, `--stdin`); `create --notes` for the first line | appends; entries carry no author or time |
| comments | anything someone may need to trust later: review findings, owner answers and approvals, evidence, incident timelines | `bd comment` (`--file`, `--stdin`) | append-only; each records its author and time |
| close reason | the outcome and its evidence | `close --reason`, `--reason-file` | `bd reopen` erases it; only `bd history` keeps it |

- Never use `update --notes`: it replaces every note. Use `bd note`.
- Never use `bd edit`: it opens an editor and blocks agents.
- `--context` and `--skills` only append `## Context` / `## Required Skills`
  sections to the description at create time.
- Evidence that must survive a reopen goes in a comment as well as the close
  reason.

Which field carries what, by lifecycle stage:

| Stage | description | spec_id | design | acceptance | notes | comments | close reason |
|---|---|---|---|---|---|---|---|
| Discovery | research question (spike Goal); epic purpose | phase epic: the roadmap; other: governing spec or vision doc | phase epic: the governing spec's path | epic success criteria | progress | findings, experiment results | spike: Findings summary |
| Intake | request, scope, non-goals | intent doc for larger work | — | success measures | open questions; what triage settled | owner answers | rejection: `wontfix: …` |
| Design | bug: repro steps; decision: the record | spec | approach | criteria and checks | `plan: <path>`, dossier pointer, baseline | approvals | decision outcome |
| Building | — | — | updated approach | — | progress, resume line | mid-course decisions | evidence |
| Verification | — | — | — | the bar being checked | — | test evidence, review findings | verdict and evidence |
| Delivery | — | — | — | — | — | PR, CI, release links; approvals | outcome, residual risk |
| Operations | finding or incident | — | — | fix criteria | investigation state | incident timeline | resolution |
| Improvement | the lesson | — | — | when it counts as codified | — | — | where it was codified |

## 7. Epics, specs and workstreams

- Before creating an epic, look for a governing document and attach it with
  `--spec-id`. An epic without one says why in its description.
- **Phase epics** belong to a workstream and follow the status-file
  renderer's contract (§16):
  - title starts `[<phase-id>]`;
  - `spec_id` is the workstream's roadmap, `docs/workstreams/<name>/roadmap.md`
    (the anchor that names the workstream);
  - `design` is the path of the governing spec or brainstorm;
  - each stage's acceptance matches the roadmap's Verify contract.
- Find a workstream's epics with
  `bd list -t epic --all --spec docs/workstreams/<name>/ --json`. Exactly one
  epic per phase may carry the `[<phase-id>]` title.
- Other beads: `spec_id` is the governing spec; `design` holds the approach
  text.
- A plan's path goes in notes as a `plan: <path>` line, never in `design`
  (on phase epics, `design` belongs to the spec).
- `bd ready --parent <epic>` returns every descendant, not only direct
  children. To pick a stage, filter to direct children:

  ```bash
  bd ready --parent <epic> --json | jq '[.[] | select(.parent == "<epic>")]'
  ```

- `bd list --parent <epic>` and `bd children <epic>` list direct children
  only; `bd children` includes closed ones.
- Epics never close themselves. Close one when its close gate holds;
  `bd epic close-eligible --dry-run` lists candidates.
- Keep children as flat as the work allows.

## 8. Creating work

- Search first. `bd search "<terms>"` matches titles and IDs and includes
  closed beads, so earlier rejections and duplicates show up. Add
  `--desc-contains` to search descriptions; narrow with `--status open`.
- Priority: 0 is the highest (drop everything), 1 this phase, 2 the default,
  3 later, 4 the lowest (backlog). Never high, medium or low.
- Work found while doing other work is a new bead with
  `--deps discovered-from:<origin>`, not scope creep in the current bead.
- Whole plans: `bd create --graph plan.json` builds an epic, its children
  and their edges in one call (children get plain IDs). Flat lists:
  `bd create -f plan.md` (one bead per `## Title`; it refuses `--parent`).
- Quick capture for scripts: `bd q -t spike "…"` prints only the new ID.
- Ideas: `bd create -t spike -s deferred "…"`. An idea created open appears
  in `bd ready`, where an agent could claim it.

## 9. Dependencies and waits

- `bd dep add X Y` means **X needs Y**; Y blocks X. `bd link X Y` is the same.
  Write it that way: "Y comes before X" wording is how edges end up backwards.
- Add an edge only when the work truly needs the other's output, not because
  it happens to come later.
- Every wait is an edge, so `bd ready` stays truthful:

  | Waiting on | Record as |
  |---|---|
  | other work | a `blocks` edge |
  | the owner | a task labelled `human` that the work depends on. Its description is the decision: options, recommendation, evidence. `bd human respond` records the answer as a comment and closes it, which frees the work |
  | CI or a PR | a gate: `bd gate create --type gh:run` or `gh:pr --await-id <id> --blocks <bead>` |
  | a duration | a gate: `--type timer --timeout 2h` (Go durations; `1d` is invalid) |
  | a condition you define | a gate with a free-form type: `--type ext:<name> --await-id <what to check> --title … --reason …`; your checker resolves it (below) |
  | another project | not expressible: `external:` edges never block in 1.3.0. Write it in the description |

- **Gates.** A gate blocks one bead and never appears in `bd ready` itself.
  `bd gate check` evaluates timer, GitHub and bead gates and closes the
  resolved ones; nothing runs it automatically, so schedule it (cron, CI, a
  hook) wherever gates exist. It ignores `human` and `ext:*` gates. A checker
  for your own conditions finds them with
  `bd gate list --json | jq '.[] | select(.await_type|startswith("ext:"))'`,
  evaluates each, and resolves with evidence:
  `bd gate resolve <gate> --reason "<evidence>"`. Bd accepts any type name,
  so the checker must report `ext:*` types it does not recognise.
- Owner decisions use `human` beads, not `human` gates: gates do not appear in
  `bd human list`.
- Context-only edges (`related`, `relates-to`, `discovered-from`,
  `caused-by`, `validates`, `supersedes`) never block.
- A blocked parent blocks all its descendants. An open, in-progress,
  deferred, pinned or closed parent does not affect them.

## 10. Triage and parking

There are no intake labels. Triage reads the bead and decides one of:

| Outcome | Action |
|---|---|
| Agent can do it | acceptance criteria present (add them if missing), a parent epic or feature, status open |
| The owner must do it | label `human` |
| Questions for the owner | a separate `human` task holding the questions, which the bead depends on |
| Real, not now | `bd defer` (with `--until` for a real date) |
| An idea worth exploring later | a deferred spike |
| Not doing it | `bd close --reason "wontfix: <why>"` |
| Duplicate | `bd duplicate <id> --of <canonical>` |

- Record what was settled with `bd note <id> "Established: …"`, so the next
  session does not ask again.
- **Two kinds of ready.** `bd ready` means unblocked. A bead an agent may
  take must also have acceptance criteria. Inside a phase, the roadmap's
  deliverable row specifies the stage.
- Closed beads are the durable rejection record; check them before filing
  similar work.

## 11. Claiming and working

- Claim when you start: `bd update <id> --claim`, or `bd ready --claim` for
  the first match. Keep one bead in progress per actor.
- When you pause or hand off, run `bd unclaim <id>` and append a resume line:
  `bd note <id> "resume with: <skills/approach>, <where it stands>"`.
- Do not take another actor's claim. Take over with
  `bd update <id> --assignee <you> --force` only when the holder is finished
  or dead.
- Compare-and-swap guards: `--if-assignee <expected>` and `--if-status
  <expected>` exit 13 with nothing written on a mismatch. Never retry them
  blindly.
- A claim's lease is a fixed 5 minutes, and expiry changes nothing: only
  `bd reclaim` returns an expired claim to `ready`. Interactive sessions need
  no heartbeats. An orchestrator running unattended workers heartbeats for
  them (`bd heartbeat`) and runs `bd reclaim --older-than 15m` itself, since
  only it knows which workers are dead.

## 12. Reviews

- Bd has no review field.
- A review that must pass before work continues is its own task, which the
  work depends on, claimed by an actor other than the author.
- Findings go on the reviewed bead as comments by the reviewer's actor. A
  finding that needs work becomes a bead linked `discovered-from` the
  reviewed bead.
- The review task closes with the verdict as its reason.

## 13. Closing

- Close only when the acceptance criteria hold, with the evidence in
  `--reason`. Close several at once with `bd close <id> <id> …`.
- Close as the actor that claimed the bead.
- Open children refuse a close at any level. Close or re-parent them; do not
  `--force` past them (`--force` closes only the parent and leaves the
  children open). Being dependency-blocked does not stop a close.
- `--suggest-next` shows what the close released.
- Replaced work: `bd supersede <id> --with <new>`. Duplicates:
  `bd duplicate <id> --of <canonical>`. Both leave the close reason empty and
  add an edge.

## 14. Session start and close

**Start.** The prime hook injects `prime.md`. Then check beads in progress
(`bd list --status in_progress`) and resume from the last note.

**Close**, before reporting completion:

1. Close finished beads with evidence (§13).
2. Unclaim unfinished beads and append their resume lines (§11).
3. Run the repository's quality gates.
4. If beads changed, make sure `.beads/issues.jsonl` is current and goes in
   the next commit (§15).
5. Run `git status` and report: changed files, checks run, beads touched.
6. Commit, push, `bd dolt push` or `bd dolt pull` only with the owner's
   authority or an active workflow's. Otherwise report them as pending.

## 15. Durability, sync and git authority

- The Dolt database under `.beads/` is the source of truth. Every write is
  a Dolt commit.
- Copies:
  - **Dolt remote**: `bd dolt push` / `pull`, stored on the git remote under
    `refs/dolt/data`. A `git push` carries no beads, and until a Dolt push
    the beads exist on one machine.
  - **Auto-backup**: on by default when a git remote exists, local to the
    machine.
  - **`.beads/issues.jsonl`**: a mirror for review in git, not a backup. With
    `export.auto: true` (`setup.md`), bd keeps it current. Where it is off,
    run `bd export -o .beads/issues.jsonl` before committing.
- On a fresh clone or new machine, run `bd bootstrap`, never `bd init`.
- Conservative git authority: no commits, pushes or Dolt sync unless the
  owner or an active workflow grants it.

## 16. Generated status files

- `docs/workstreams/{status,ideas,backlog}.md` and
  `docs/workstreams/*/tracking/*.md` are generated from Beads.
- Update Beads, then regenerate:
  `BD_RENDER=1 bash .claude/skills/beads/scripts/bd-render-tracking.sh [<name>]`.
- Never hand-edit them; a hook blocks it. A missing renderer is a reported
  limitation, not permission to edit by hand.
- `README.md`, `roadmap.md` and `plans/*.md` in the same tree stay
  hand-written.
- The ideas board lists deferred spikes; the backlog board lists every other
  deferred bead.

## 17. Hygiene

A weekly pass, run by an agent and reported to the owner, not fixed
silently:

| Check | Command |
|---|---|
| claims older than a day | `bd list --status in_progress` |
| ideas created open | `bd list -t spike --status open --no-parent` |
| untouched for 30 days | `bd stale` |
| finished epics | `bd epic close-eligible --dry-run` |
| hand-set blocked | `bd list --status blocked` |
| missing sections | `bd lint` |
| owner queue | `bd human list` |

- Health in embedded mode: `bd where`, `bd ping`, `bd lint`. `bd doctor` does
  not run in embedded mode, and `bd preflight` checks the beads project's own
  toolchain.
- Never run `bd gc`, `bd prune`, `bd purge` or `bd admin cleanup`: their
  defaults delete closed beads (`gc` deletes those older than 90 days,
  `admin cleanup` all of them). To reclaim space while keeping every bead:
  `bd compact --days 90 --force`, then `bd gc --skip-decay --full`.

## 18. Repeated procedures

- Short routine runs: `bd mol wisp <formula>`. Wisps are local and never
  exported. When a run is done, `bd mol squash` it if it found something
  (leaving one closed digest bead), or `bd mol burn` it if not.
- Procedures repeated with fixed steps (an upgrade, a release): a formula in
  `.beads/formulas/<name>.formula.toml`, poured with `bd mol pour`. Unknown
  keys are dropped silently, so check what bd parsed with
  `bd formula show <name> --json`. Human sign-off inside a formula is
  `[steps.gate] type = "human"`.

## 19. Traps

| Trap | Instead |
|---|---|
| `bd show` rewrites `.beads/last-touched`, even under `--readonly`; a later `bd close` or `bd update` with no ID in a terminal targets that bead | always pass IDs; tools reading other projects use `list` or `export`, never `show` |
| `bd list` stops at 50 and `bd ready` at 100, silently dropping the rest | `--limit 0`; `--max-rows` for a hard cap (exit 2) |
| repeating `-s` keeps only the last value | `-s open,in_progress` |
| `bd query` dates are points in the past: `updated>7d` means updated within 7 days | check with `--parse-only` |
| `bd config set` accepts unknown keys silently, and `bd config show` prints stored defaults rather than code defaults (it shows `backup.enabled` false while auto-backup runs) | read the capabilities guide before relying on a key |
| `bd init` runs agent setup recipes: a second Claude SessionStart prime hook, four `bd codex-hook` events and an AGENTS.md block that says to use `bd remember` | `bd init --skip-agents`; never `bd setup` in a harness repo (`setup.md`) |
| `bd init` inside a checkout nested in another Beads repo resolves to the parent's database, and so do `BEADS_DIR` and `--directory` | a second database needs its own git repo with a seeded `.beads/config.yaml` (`setup.md`) |
| `bd init` over an existing database aborts; on a fresh clone `bd ready` says "no beads database found" and suggests `bd init` | `bd bootstrap` |
| a git worktree has no database of its own: `bd where` resolves to the main clone's | treat worktrees as the same clone in sync and upgrade plans |
| a fresh HOME starts bd usage metrics on | `bd metrics off` on every new machine, container or sandbox |
| Codex review sandboxes (`-s read-only`) cannot open the Beads database | paste the relevant notes into the review brief |
| Claude Code cloud sessions get HTTP 403 on `bd dolt push` from the session's git proxy | carry changes back through the committed `.beads/issues.jsonl`; sync Dolt locally |
| `bd repo sync` reads its repo list only from the tracked `.beads/config.yaml` | do not use `bd repo` in public repos |
| `external:<project>:<capability>` dependencies never block | describe cross-project waits in the description |
| GitHub issue sync is slow on every pull and has open correctness bugs (#6605, #6806, #6773) | do not use it on 1.3.0 |
| `bd serve` and `bd sql` need server mode | use the CLI with `--json` |
| `bd prime`'s built-in text tells agents to use `bd remember`, `git add .` and `bd doctor` | `.beads/PRIME.md` replaces it with `prime.md` (`setup.md`) |

## 20. Not used

`bd remember`, `bd memories`, `bd kv`; GitHub, GitLab, Jira, Linear, ADO and
Notion sync; `external:` dependencies; `bd repo`; `bd serve`, `bd sql`; due
dates and estimates; `bd edit`; `bd setup`; `bd mail`; `bd audit`; story,
chore, milestone and custom types; labels other than `human`.

## 21. Commands

| Goal | Command |
|---|---|
| Context, recovery | `bd prime`; `bd where` if it prints nothing |
| Ready work | `bd ready`; `--parent <epic>` (all descendants); `--claim` |
| List | `bd list -s open,in_progress`; `-t <type>`; `--parent <id>`; `--spec <prefix>`; `--all` includes closed |
| One bead | `bd show <id>`; `bd children <id>`; `bd history <id>` |
| Search | `bd search "<terms>"` (closed included); `--status open`; `--desc-contains` |
| Create | `bd create "<title>" -t <type> -p <0-4> -d "<why/what>" --acceptance "<done-when>" [--parent <id>] [--spec-id <path>] [--design <text or path>] [--deps discovered-from:<id>] --actor <a>` |
| Idea | `bd create -t spike -s deferred "<idea>" --actor <a>` |
| Plan in one call | `bd create --graph plan.json` |
| Claim, release | `bd update <id> --claim`; `bd unclaim <id>` |
| Progress | `bd note <id> "<text>"` |
| Discussion, evidence | `bd comment <id> "<text>"` (or `--file`) |
| Change fields | `bd update <id> --title/-d/--design/--acceptance/-p/--spec-id/--parent` |
| Dependencies | `bd dep add <needs> <needed>`; `bd dep tree <id>`; `bd blocked`; `bd dep cycles` |
| Owner queue | `bd label add <id> human`; `bd human list`; `bd human respond <id> "<answer>"`; `bd human dismiss <id>` |
| Gates | `bd gate create --type <t> --blocks <id> [--await-id] [--timeout]`; `bd gate list`; `bd gate check`; `bd gate resolve <id> --reason "<evidence>"` |
| Defer | `bd defer <id> [--until <date>]`; `bd undefer <id>`; `bd list --status deferred` |
| Close | `bd close <id> [<id>…] --reason "<evidence>"`; `--suggest-next` |
| Replace, duplicate | `bd supersede <id> --with <new>`; `bd duplicate <id> --of <canonical>` |
| Epics | `bd epic status`; `bd epic close-eligible --dry-run` |
| Graph | `bd graph <id>`; `bd graph check`; `bd swarm validate <epic>` |
| Health | `bd lint`; `bd stale`; `bd where`; `bd ping` |

Add `--json` to parse output. Check `bd <command> --help` for anything not
listed here.

## 22. Repository exceptions

- **The workflow engine's label.** `workflow_interpreter/`'s tracker port
  adds and removes the `wf:attention` label on the beads it works on
  (`workflow_interpreter/tracker/constants.py`). It is machine-owned: never
  add, remove or reuse it by hand. Since ADR 0006 the engine keeps its own
  records in its ledger, not in Beads.
- **Deferred export.** When the owner restricts which paths a session may
  write and `.beads/issues.jsonl` is outside them, do not write it; report the
  export as pending in the session close.
