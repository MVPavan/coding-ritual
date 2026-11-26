# Beads → GitHub mirror

> The live trial (`docs/workstreams/beads-github-mirror/trial.md`) passed: its one-account cases on
> 2026-11-21 and its fork cases F1 and F2, with a second account, on 2026-11-22. Activation step 1
> still waits for real session starts after `update` installs the hook, checked at the plugin sync
> (`cr-e0a`). Activating sooner is the owner's decision; this guide does not make it.

This is the owner's guide to the mirror. The design is in
`docs/specs/2026-11-20-beads-github-mirror.md`. The command is `.claude/hooks/bead-mirror.py`, and
every command below runs from the top level of the clone as
`python3 .claude/hooks/bead-mirror.py SUBCOMMAND`.

## What it does

One clone, the one holding the writer switch, publishes a project's public-facing beads as GitHub
issues and keeps their title, body, type label and open-or-closed state following the bead. The only
thing it writes to Beads is the URL of an issue it created or adopted, in that bead's `external_ref`.
Everything that happens on GitHub (a merged pull request, an outside issue, a hand-closed issue) goes
into a digest for an agent or the owner to act on, and a required check makes every pull request
reference an issue.

## Project states

| State | How it is recognised | Session start | `pr` and `tracker` skills |
|---|---|---|---|
| Not opted in | No `.github/workflows/bead-reference-check.yml` committed and no switch in this clone | Prints nothing | Behave as without the mirror |
| Opted in, not the writer | The workflow is committed; no switch in this clone | Prints nothing | `pr` references an issue already linked to the bead or an ancestor, and otherwise stops with "ask the writer clone to mirror this bead"; `tracker` skips outbound and says so in one line |
| Writer clone | The switch is present | Prints the digest summary and starts the background run | Run the mirror as described below |

Every adopted project carries the command and its session-start hooks. Without a switch, every
subcommand exits 0, prints nothing and creates nothing; only `--help` answers. Links the writer
records reach other clones through the ordinary Beads sync or the committed `.beads/issues.jsonl`.

## The writer switch

The switch is `bead-mirror/switch.json` under the clone's git common directory (the path
`git rev-parse --git-common-dir` prints), so every linked worktree of that clone shares it. It is
never committed. The owner creates and edits it; nothing else does.

| Field | Meaning | Default |
|---|---|---|
| `host` | The GitHub host, a bare hostname (an optional `:port` is allowed) | Required |
| `repo` | The repository as `owner/name` | Required |
| `repo_node_id` | The repository's permanent node ID; a repository at `repo` with another node ID gets no writes | Required |
| `account` | The GitHub login the mirror writes as (the mirror account); the `gh` login must match | Required |
| `store_project_id` | The `project_id` of the Beads store it publishes from, as `bd context --json` reports it | Required |
| `scope` | The bead types eligible for creation | `["epic", "feature", "bug"]` |
| `pr_enrol` | Whether the `pr` path (`outbound --bead`) may enrol a bead whose type is outside `scope` | `true` |

An example with placeholder values:

```json
{
  "host": "github.com",
  "repo": "OWNER/REPO",
  "repo_node_id": "REPO_NODE_ID",
  "account": "MIRROR_ACCOUNT",
  "store_project_id": "STORE_PROJECT_ID",
  "scope": ["epic", "feature", "bug"],
  "pr_enrol": true
}
```

An unreadable or invalid switch stops every subcommand, `--help` included, with exit 3 and the
reason; the session-start hook prints the reason and exits 0. Exit 3 also means the command could not
write its own files beside the switch (below), for example after a permission or disk problem.

### Files beside the switch

The command keeps its own files in the same `bead-mirror/` directory. None is committed.

| File | Holds |
|---|---|
| `state.json` | Enrolled, pending, held, tracking-only, retired and set-aside beads; checkpoints; the digest's rows and facts. Bound to the store, repository node ID and account |
| `digest.json`, `digest.md` | The latest digest, as data and as text |
| `lock` | The clone-wide lock every state-changing entry point takes |
| `launch`, `background.json` | The background run's reservation, last outcome and rate-limit back-off |
| `log` (and `log.1`) | The background run's output, moved to `log.1` past about a megabyte |

## Activation

Activation is owner-controlled and goes in this order. Every step is the owner's action; an agent
does not take any of them on its own.

1. **The live trial passes** (owner). `docs/workstreams/beads-github-mirror/trial.md` is the
   checklist. Every one-account case passed on 2026-11-21 and the fork cases (F1, F2) on 2026-11-22.
   The trial's session-start cases (H1, H2) used copied hook files,
   so real session starts after `update` installs the hook are still checked at the plugin sync
   (cr-e0a); step 1 is not cleared until then either.
2. **Set the exempt-authors variable** (owner). The workflow reads the repository variable
   `BEAD_REF_EXEMPT`, a comma-separated list of logins whose pull requests pass without a
   reference. Leave it absent or empty to exempt no one, or set it, for example with
   `gh variable set BEAD_REF_EXEMPT --repo OWNER/REPO --body "LOGIN1,LOGIN2"`. The variable is read
   on every run, so the workflow file never changes for it.
3. **Create the writer switch in one clone** (owner). Gather the values: `bd context --json` for
   `store_project_id`, `gh api repos/OWNER/REPO --jq .node_id` for `repo_node_id`, `host` as the
   GitHub host, and `account` as the mirror account's login. Log `gh` in as the mirror account;
   `account` must be the same login `gh auth status` shows. Write the JSON above to `bead-mirror/switch.json` under the git common
   directory by hand. No subcommand writes it. Only one clone per repository holds a switch. In a
   new clone that has no Beads store yet, `bd init` makes its own git commit. Check `git log`
   before pushing.
4. **Dry run** (owner): `python3 .claude/hooks/bead-mirror.py outbound --dry-run`. It runs every
   authority check (the store's identity, the `gh` login, the repository's node ID, the state's
   binding), reports what it would do, and writes nothing.
5. **First run in the foreground, and read-back** (owner):
   `python3 .claude/hooks/bead-mirror.py both`. This makes the state, which records the opt-in time,
   writes the first digest and creates the issues for eligible beads. Read it back: open the issues on
   GitHub (author, banner, title, body, `bead-type:` label), run
   `python3 .claude/hooks/bead-mirror.py map` and read `digest.md`. The run fills `external_ref` on the
   linked beads, which changes `.beads/issues.jsonl`; commit it under the Beads session-close rule.
6. **Write and commit the check's workflow** (owner):
   `python3 .claude/hooks/bead-mirror.py install-check` writes
   `.github/workflows/bead-reference-check.yml` after the same authority checks and prints the path.
   It refuses to replace a differing file unless given `--force`. Commit and push it to the default
   branch; that commit marks the project as opted in for every clone. To find a drifted workflow
   later, re-run `install-check` without `--force`: it prints `unchanged:` when the file matches and
   refuses (exit 9) when it differs. In an adopted repository the plugin's `doctor` does this without
   the authority checks: it compares the committed file with the plugin's `bead-mirror.py print-check`
   (which reads and writes nothing) when the installed command is byte-identical to the plugin's copy,
   reports the comparison incomplete (exit 3) when it is not, and reports a failing, stale or held
   mirror from the local state.
7. **Set the protection and the Actions policy** (owner, in the repository settings). Allow Actions,
   with `pull_request_target` workflows running for the repository's pull requests, including pull
   requests from forks. Require approval before workflows run for outside contributors' pull
   requests, so a workflow a pull request adds does not run unseen. The check itself runs on a
   fork's pull request without that approval, because `pull_request_target` runs the default
   branch's workflow (trial F1). Protect the default branch with a
   branch protection rule or a ruleset; a ruleset must be enforcing (`active`, not `evaluate`) with no
   bypass actors, and a branch protection rule must apply to administrators. The trial, on a
   personal repository, used a ruleset.
8. **Make the check required** (owner). Require the job `bead-reference` from GitHub Actions. Where the
   plan offers a ruleset that requires a specific workflow, require the workflow instead, since a
   name-based requirement can be met by a same-name check from another workflow. The trial's
   personal repository used a required-status-check rule in its ruleset: the check
   `bead-reference` with the GitHub Actions app as its source, enforcement `active` and no bypass
   actors. It did not try a workflow rule, which it understood to be offered only in organization
   rulesets. A private repository needs a plan that allows required checks there; without one the
   check runs but cannot block.

   In the trial, a pull request from a branch in the repository added a workflow with a job of the
   same name that always passed. The merge was still blocked, because the real check also ran on
   that head and failed (case C6b). The trial did not cover a head on which the real workflow leaves
   no check run of its own, for example because it was cancelled before its job's check run existed.
   From a fork, the same stand-in waited for the owner's approval while the real check ran and
   failed; once approved it ran and passed, and the merge was still refused (case F2).

### Codex hooks need trust

Codex runs a project's hook only after the user trusts both the project and that hook entry. It
skips an untrusted hook silently and prints no prompt or message, so in Codex the mirror's session
start does nothing until both are trusted. The hook's trust is tied to the hook file's contents, so
trust it again after `.codex/hooks.json` changes. In the trial, Claude Code in print mode (`-p`)
ran the hook without a trust prompt.

## Daily use

### Session start

In the writer clone, each session start or resume prints, within 2,000 characters: the latest
digest's time and whether it was a full comparison, its counts by row type, at most five rows and the
path to the rest, and the last background run's outcome when it did not finish cleanly. It reads only
local files, makes no network call, takes no lock and exits 0 within about three seconds. It then
starts the background run (`both --no-create`) when the last one started more than fifteen minutes
ago and no rate-limit back-off (one hour) is running. The background run updates and closes issues
but never creates one; it stops itself after ten minutes, and its supervisor stops it after twelve.
Unfinished work waits for the next run.

Digest rows carry only numbers, bead IDs, states, commit SHAs, validated logins and links; titles,
bodies and comments from GitHub never appear.

### Digest rows

| Row | Means | Who acts |
|---|---|---|
| `linked-closed` | A linked issue is closed and its bead is open; names the merged pull request, merge commit and merger, or says "closed on GitHub, no pull request" or "cause unknown" | An agent through `tracker`: close the bead with that evidence when its acceptance, reviews and owner decisions allow, or comment and leave it open |
| `reopened` | An enrolled issue was reopened on GitHub while its bead is closed | The owner: reopen the bead, or `overwrite` |
| `tracking-open` | A tracking-only issue is still open while its bead is closed | `triage`, with the owner's authorization to comment or close on GitHub; or `dismiss` |
| `held` | A held create, link, retirement or open-or-closed state, or a not-storable or screened component, with why | The owner: fix the bead, exclude it, or `overwrite`; see Recovery |
| `untracked-issue` | An open issue no bead links | `triage`: create a bead and `link` it, `dismiss`, or decline on GitHub with the owner's authorization |
| `untracked-closed` | An issue no bead links, closed since opt-in by a merged pull request | `triage`: link it to a bead and close that with evidence, or `dismiss` |
| `untracked-pull` | An open pull request, or one merged since opt-in, none of whose references is a linked issue; each reference is listed as missing, a pull request or not linked | `triage`, as above |
| `link-problem` | An issue named by several beads, or enrolled for a bead missing from Beads | The owner: fix the links, or `retire` |
| `unpublished` | The count of eligible beads not yet published | Run `outbound` in the foreground |

A row clears on the next run once Beads agrees, even if nothing changed on GitHub.

### Subcommands

The global option `--lock-wait SECONDS` (before the subcommand, default 60) bounds the wait for the
clone-wide lock before a run reports busy.

| Subcommand | Does |
|---|---|
| `outbound` | Publishes beads: creates issues for eligible beads and converges enrolled ones. `--dry-run` checks and reports only; `--bead ID` enrols and publishes one bead (the `pr` path); `--no-create` never creates |
| `inbound` | Compares GitHub with Beads and writes the digest; writes nothing to Beads or GitHub |
| `both` | Inbound, then outbound; `--no-create` is the background run |
| `full` | `both` with the full comparison over every issue and pull request (otherwise due weekly); takes `--no-create` |
| `map` | Prints bead, issue, link, kind and the pull requests that reference or closed each issue, from the state and the links; no GitHub call |
| `link BEAD NUMBER --actor ACTOR` | Records issue `NUMBER` as a tracking-only link on `BEAD`, as `ACTOR`, only if the field is empty; used by `triage` in the writer clone |
| `dismiss NUMBER` | Acknowledges an issue or pull request so its `untracked-*` or `tracking-open` row clears |
| `overwrite BEAD [title\|body\|label\|state]` | Reads the enrolled issue fresh and writes the bead's values for every, or the named, component, ignoring holds and not-storable marks; `state` includes the closing comment. Needs the owner's authorization |
| `retire BEAD` | The owner's action. Stops managing the bead's issue, leaving it open or closed, and marks its banner retired on GitHub |
| `resolve BEAD --adopt NUMBER` | The owner's action. Adopts the mirror account's issue `NUMBER` for a bead whose create is held |
| `resolve BEAD --create` | The owner's action. Releases a pending or held create so the next foreground outbound may create the issue |
| `reset-state` | The owner's action. Discards the state file; the next run rebuilds it from GitHub's listing |
| `install-check` | Writes the pull-request check's workflow; `--force` replaces a differing file |
| `session`, `supervise`, `worker` | The session-start hook, the background supervisor and the background run; not for manual use |

To keep one bead off GitHub, set `bd update BEAD --set-metadata mirror=never`. On an enrolled bead,
this retires its issue.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Done. Holds are reported on standard output, not as failures. Also every subcommand with no switch |
| 2 | Usage |
| 3 | The switch is unreadable or invalid, or the command cannot write its files beside it (lock, state, digest) |
| 4 | An authority check failed (store, account, repository node ID or state binding); the report is on standard error. A state mismatch persists until the owner runs `reset-state` |
| 5 | GitHub unavailable: `gh` missing, unauthenticated, rate-limited, offline or failing, or the issues listing incomplete. A run that meets this late keeps what it already recorded and leaves the rest pending |
| 6 | Beads unavailable |
| 7 | Busy: another run held the lock past the wait bound |
| 9 | Refused: the `pr` path, `link`, `resolve`, `install-check`, `dismiss`, `overwrite` or `retire` declined, with the reason |
| 10, 11 | The background worker only: rate-limited; its own deadline passed |

The session-start hook always exits 0, printing the last digest and the cause when GitHub cannot be
reached.

## Recovery

Each subcommand here changes the state or GitHub. These are the owner's actions (or an agent's acting
on the owner's explicit authorization); run them from the writer clone.

- **`reset-state`** after exit 4 for a state bound to another store, repository or account, or an
  unreadable state. The next run lists every issue the mirror account created, adopts by banner,
  holds every open-or-closed state that differs from Beads, and reports them.
- **`resolve`** for a held create. `--adopt NUMBER` takes a live issue the mirror account created for
  this bead in this store. `--create` releases the hold, sets aside the candidates seen, and is
  refused while the listing shows exactly one live issue for the bead (adopt that one instead).
- **`overwrite`** when GitHub and the bead disagree and the owner wants the bead's version written,
  for an open-or-closed hold or a not-storable component.
- **`retire`** for an issue the mirror should stop managing, including one enrolled for a bead
  missing from Beads. A retired issue is tracking-only from then on and is never managed or adopted
  again, even after `reset-state`.
- **`dismiss`** for an untracked issue or pull request, or a tracking-only issue, that needs no bead.

### Holds and how to clear each

| Hold | Cause | Clear it by |
|---|---|---|
| `screen` | The title or body has private material (a home or workspace path, a file URL, an internal hostname, or what the plugin's leak check flags); nothing is written | Fixing the bead's text, or excluding the bead |
| `screened` | A close reason failed the screen and was posted as "Closed in Beads." | Nothing to clear; it is reported |
| `candidates` | Several mirror-authored issues name the bead, or one names it with a missing or different store | The owner: `resolve BEAD --adopt NUMBER` for the right one, or `resolve BEAD --create` |
| `pending` | A create was sent and no issue for it has appeared in the listing for a day | The owner: `resolve BEAD --adopt NUMBER` if the issue exists, else `resolve BEAD --create` |
| `refused` | GitHub rejected this bead's create or its label; tried again each run | Fixing the bead's input |
| `link-conflict` | The bead's `external_ref` already holds a different value | Fixing the link in Beads |
| `bad-link` | `external_ref` names this repository but not an issue (a pull request, or no such number) | Fixing the link in Beads |
| `open-closed` | The issue's open-or-closed state differs from the bead's, changed on GitHub or of unknown origin | Updating the bead to agree, or `overwrite BEAD state` with the owner's authorization |
| `not-storable` | GitHub stores a component differently from what was sent; it is not rewritten until the bead's value changes | Changing the bead, or `overwrite BEAD COMPONENT` |
| `retire` | Retiring an excluded bead's issue failed; tried again every run | Restoring GitHub access; removing the exclusion also drops it |

## Stated limits

From the spec:

- A collaborator's edit to an issue's text is replaced by the bead's version; GitHub keeps the edit
  history.
- A check result can be stale between a body edit and the completion of its run.
- A link written by `triage` outside the writer clone can race the mirror's link write through Beads
  sync.
- A create can be duplicated only if the state file is lost while a create's issue is still missing
  from GitHub's listing.
- A collaborator who edits a mirror-authored banner can misdirect adoption; collaborators already have
  write access.
- The private-material screen is best-effort, not an approval of what is public.
- Not supported in this version: merge queues, direct pushes, roles allowed to bypass protection, and
  pull requests into a branch other than the default.

From the command:

- An issue whose banner was deleted outright is not recognised as the mirror's.
- Two closes Beads records with the same time and reason share one closing comment.
- A deleted issue's digest row stays until dismissed.
- Codex's hook entry finds the checkout with git before any deadline starts; git discovery is local,
  and Codex's hook runner bounds the entry.
- Without `/proc` (macOS), a background descendant that ignores the stop signal can outlive the
  worker's own cleanup; the supervisor stops it, unless the supervisor was killed too.

From the trial: a same-name check from a separate workflow did not make a pull request mergeable,
either from a branch (C6b) or from a fork, even after the owner approved the fork's run (F2). What
stays unproven is C6b's residue, a head where the real workflow leaves no check run of its own.
