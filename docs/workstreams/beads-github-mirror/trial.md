# Beads → GitHub mirror: live trial

Stage M4.1 (`cr-k88k.4.1`) writes this checklist; M4.2 runs it and fills in the **Result** and
**Evidence** columns; M4.3 replays the recordings and evidences what is left of the Check criterion.
Spec: `docs/specs/2026-11-20-beads-github-mirror.md` (Testing Decisions, second paragraph; Success
Criteria; Pull-request check; Activation). Roadmap: `docs/workstreams/beads-github-mirror/roadmap.md`, M4.

The spec makes this trial a prerequisite to activation in any project. Only the cases below need a live
repository. Every other Success Criterion is settled by `tests/mirror` against the fake `gh`.

Placeholders: `OWNER/TRIAL` is the throwaway repository, `HOST` its GitHub host, `OWNER` the owner's
login. `PR#n` and `#n` are numbers in the trial repository.

## One account

The trial has one GitHub account, the owner's; a second is deferred (owner, 2026-11-20). The mirror
account is therefore `OWNER`, and every issue, pull request, edit and merge below is by `OWNER`.

- Open no issue in `OWNER/TRIAL` by hand: the creator listing (T11) cannot tell a hand-made issue
  from one the command made except by its banner.
- The exempt-authors variable stays absent or empty for every case but C3, which sets it to `OWNER`
  and clears it again. A case expected to be blocked counts only if its last run started while the
  variable was empty.
- One account cannot settle F1 and F2. A fork into an organisation the owner controls does not help:
  its pull requests are still authored by `OWNER`, a collaborator, so the outside-contributor
  approval never applies. What stays unproven until the second account exists is stated after the
  merge-decision table. One account also cannot show the exemption is per login (that a pull request
  by an unlisted author is still checked while the variable names someone else); no criterion
  depends on it.

## 0. Gate

| # | Item | Who | Evidence | Pass |
|---|---|---|---|---|
| G0 | The owner's go-ahead for the live trial, recorded on `cr-k88k.4.1` before any network call | Owner | The bead comment or note, with its date | It exists, and its date is earlier than the first recorded call |

Nothing below runs until G0 passes. No agent records G0.

## 1. Setup (owner actions)

Each item is something the owner does on GitHub or in the trial clone. Record the `gh api` read as
evidence, or a screenshot where no API exposes the setting.

| # | Owner action | Evidence | Pass |
|---|---|---|---|
| S1 | Create the public throwaway repository `OWNER/TRIAL` with a default branch and issues enabled | `gh api repos/OWNER/TRIAL` (`node_id`, `default_branch`, `has_issues`) | The repository exists and issues are on |
| S2 | Enable all three merge methods: merge commit, squash and rebase | The same read: `allow_merge_commit`, `allow_squash_merge`, `allow_rebase_merge` | All three are true |
| S3 | Actions policy: Actions allowed and `pull_request_target` workflows run for this repository's pull requests, including pull requests from forks | `gh api repos/OWNER/TRIAL/actions/permissions` and the fork pull-request settings screen | Actions enabled; fork pull requests are not excluded |
| S4 | Require approval before workflows run for outside contributors' pull requests | `gh api repos/OWNER/TRIAL/actions/permissions/fork-pr-contributor-approval` if the API offers it, otherwise a settings screenshot | Approval is required for outside contributors (the strictest setting the plan offers) |
| S5 | Leave the exempt-authors repository variable (the name the workflow written by `install-check` reads) absent or empty | `gh api repos/OWNER/TRIAL/actions/variables` | The variable is absent or empty |
| S6 | In a clone of `OWNER/TRIAL`, initialise a fresh Beads store. Install the mirror residue by copying it from this repository at a recorded commit: `.claude/hooks/bead-mirror.py`, `.claude/hooks/bead-mirror-session.sh`, `.codex/hooks/bead-mirror-session.sh`, and the mirror's session-start entry from `.claude/settings.json` and from `.codex/hooks.json`, added beside the clone's other entries. Do not use `adopt` or `update`: the plugin template carries the residue only after the `cr-e0a` sync, so installation through `adopt`/`update` is proven at that sync | The commit; `sha256sum` of the three files in both places; the two entries in the clone; `bd context --json` showing the new store's `project_id` | The files are byte-identical, the entries match this repository's, and the store is new, not this repository's |
| S7 | Create the writer switch in that clone: host `HOST`, `OWNER/TRIAL` with the node ID from S1, mirror account `OWNER`, default scope, the store's `project_id`. Log `gh` in as `OWNER` | `bead-mirror outbound --dry-run` report | The dry run passes every authority check and writes nothing |
| S8 | Run `install-check`, commit and push the workflow to the default branch | The commit URL; `gh api repos/OWNER/TRIAL/contents/.github/workflows/bead-reference-check.yml` | The default branch carries the workflow exactly as the command wrote it |
| S9 | A branch protection rule or ruleset on the default branch requiring the check's job name from GitHub Actions; where the plan offers a ruleset that requires the specific workflow, use that instead | `gh api repos/OWNER/TRIAL/rulesets` and `.../rulesets/ID`, or `gh api repos/OWNER/TRIAL/branches/BRANCH/protection` | The required check names the fixed job and the GitHub Actions app; for a ruleset, enforcement is `active`, not `evaluate`, and `bypass_actors` is an empty list; for branch protection, `enforce_admins.enabled` is true, so the owner as an administrator cannot merge past the check |
| S10 | A second GitHub account that can fork `OWNER/TRIAL` and open pull requests | Its fork's URL | **Deferred until a second GitHub account exists (owner, 2026-11-20).** F1 and F2 wait for it |

The command runs as `bead-mirror SUBCOMMAND` below, meaning the command at
`.claude/hooks/bead-mirror.py` in the trial clone. The trial beads are created in the trial store by
the owner or the trial operator, never in this repository's store.

## 2. Cases

Mark each row's result as `pass`, `fail` (with the observed behaviour) or `deferred`. Evidence
links point at the trial repository or at a file under `tests/mirror/fixtures/recorded/`.

### Issues (outbound)

| # | Case | Steps | Evidence to capture | Pass | Result | Evidence |
|---|---|---|---|---|---|---|
| T1 | Create with read-back | Create an open feature bead with a description and acceptance; run `bead-mirror outbound` | The issue URL; `gh api graphql` read of the issue node (author, title, body, labels); `bd show` of the bead's `external_ref` | One issue, authored by `OWNER`, with the banner, title, description, acceptance and `bead-type:feature`; `external_ref` holds its URL | pass | https://github.com/MVPavan/bead-mirror-trial/issues/1; evidence/T1.md |
| T2 | Second run is quiet | Run `bead-mirror outbound` again | The command's report; the issue's `updatedAt` before and after | No write is reported and `updatedAt` is unchanged | pass | https://github.com/MVPavan/bead-mirror-trial/issues/1 (updatedAt unchanged, no mutation recorded); evidence/T2.md |
| T3 | Edit and converge | Edit the bead's title and description; run outbound. Then edit the issue's title and body on GitHub; run outbound | Read-back after each run | After the first run the issue matches the bead. After the second the bead's version replaces the GitHub edit | pass | https://github.com/MVPavan/bead-mirror-trial/issues/1; evidence/T3.md |
| T4 | Label | Add a label outside `bead-type:` on GitHub; change the bead's type within scope (for example feature to bug); run outbound | Read-back of the labels | The outside label is untouched; the type label changes; the label is created on first use | pass | https://github.com/MVPavan/bead-mirror-trial/issues/1 (bead-type:bug created, trial-outside kept); evidence/T4.md |
| T5 | Close and comment | Close the bead with a reason; run outbound; run it again | The issue's state and comments page | The issue is closed with one comment carrying the screened reason; the rerun adds none | pass | https://github.com/MVPavan/bead-mirror-trial/issues/1 (1 comment, `#1` neutralised); evidence/T5.md |
| T6 | Reopen and close again | Reopen the bead, close it with a different reason, run outbound | The comments page | Exactly one more comment | pass | https://github.com/MVPavan/bead-mirror-trial/issues/1 (2 comments); evidence/T6.md |
| T7 | Held state from GitHub | Reopen the T5 issue on GitHub; run outbound twice | Both reports | The difference is held and reported on each run; the issue is not closed again | pass | https://github.com/MVPavan/bead-mirror-trial/issues/1 (open-or-closed held both runs); evidence/T7.md |
| T8 | Title with surrounding spaces | Create a new feature bead for this case and run outbound, so it has its own issue `#t8`. If `bd` keeps a title's surrounding spaces, give the bead a title with leading and trailing spaces and run outbound (the command writes it). Otherwise write the bead's title with a leading and a trailing space to `#t8` directly with `gh api graphql` `updateIssue`. Read the issue back. Then run outbound twice | The `updateIssue` input, response and read-back, saved to `tests/mirror/fixtures/recorded/roundtrip_title.json`; which path was used; both later reports | The stored title is recorded exactly as returned. If it differs from what was sent only within the canonical forms (here, trimming), both later runs report no write and no not-storable component. Only when the read-back after the command's own write differs canonically from what it sent is the title reported as not storable, and it is not rewritten on the later run. After a direct write, a canonical difference is ordinary drift: the first later run writes the bead's title once and the second is quiet | pass (direct write: bd trims titles; GitHub kept the spaces; both later runs quiet) | https://github.com/MVPavan/bead-mirror-trial/issues/2; `roundtrip_title.json`; evidence/T8.md |
| T9 | CRLF body with a trailing newline | As T8 with a new bead and its issue `#t9`: either a bead description with CRLF line endings and a trailing newline, written by the command, or the command's own rendered body converted to CRLF with a trailing newline, written directly | As T8, in `tests/mirror/fixtures/recorded/roundtrip_crlf_body.json` | As T8; the canonical forms here are line endings normalised and trailing whitespace removed | pass (command write sends canonical LF; direct CRLF write stored as sent; both later runs quiet) | https://github.com/MVPavan/bead-mirror-trial/issues/3; `roundtrip_crlf_body.json`; evidence/T9.md |
| T10 | Body at the 60,000-character budget with multi-byte text | Two new beads, both written by the command (no direct write). Size the first one's description, including multi-byte characters (for example non-Latin letters and an emoji), so the body the command sends (banner, description and acceptance, read from the recorded `createIssue` input) is exactly 60,000 characters; size the second one just over the budget. Run outbound, read both issues back, then run outbound twice more | As T8, in `tests/mirror/fixtures/recorded/roundtrip_budget_body.json`, plus the sent and read-back lengths of each body in characters and in UTF-8 bytes | The first body is stored whole with no truncation note; the second is cut to the budget with the truncation note. Read-back differences are judged as in T8 | pass (60,000 chars / 105,804 bytes sent and stored, both; note only on #5) | https://github.com/MVPavan/bead-mirror-trial/issues/4, https://github.com/MVPavan/bead-mirror-trial/issues/5; `roundtrip_budget_body.json`; evidence/T10.md |
| T11 | Lost-response create recovered by listing | Put a pass-through wrapper for `gh` first on `PATH` that forwards every call to the real `gh`, but for the first `createIssue` discards the reply and exits as `errors.json`'s `lost_response` does. Create a new feature bead; run outbound. Remove this fault wrapper (the recording wrapper stays); run outbound again | The first run's report; the creator listing for `OWNER`; the second run's report and `external_ref` | GitHub holds exactly one issue for the bead. The first run records a pending create and does not resend; the second adopts the listed issue and links it | pass (run 1 exit 5, pending; run 2 adopted #6, no resend) | https://github.com/MVPavan/bead-mirror-trial/issues/6; evidence/T11.md |

### Merges and closing events (digest)

Each pull request below is opened from a branch in `OWNER/TRIAL` with `Closes #n` naming a mirrored
issue, and merged by the method named.

| # | Case | Steps | Evidence to capture | Pass | Result | Evidence |
|---|---|---|---|---|---|---|
| T12 | Squash merge | Open PR#a, merge with `gh pr merge --squash`; run `bead-mirror inbound` | The issue's closing event (`gh api graphql`, timeline `ClosedEvent` closer), recorded; the digest row | The closing event names PR#a; the digest names PR#a, the merge commit and the merger; the bead stays open | pass | https://github.com/MVPavan/bead-mirror-trial/pull/7 closed https://github.com/MVPavan/bead-mirror-trial/issues/2; digest linked-closed row, bead open; evidence/T12.md |
| T13 | Merge commit | As T12 with `--merge` | As T12 | As T12 | pass | https://github.com/MVPavan/bead-mirror-trial/pull/8 closed https://github.com/MVPavan/bead-mirror-trial/issues/3; digest linked-closed row, bead open; evidence/T13.md |
| T14 | Rebase merge | As T12 with `--rebase` | As T12 | As T12 | pass | https://github.com/MVPavan/bead-mirror-trial/pull/9 closed https://github.com/MVPavan/bead-mirror-trial/issues/4; digest linked-closed row, bead open; evidence/T14.md |

### Merge decisions (the required check)

`OWNER` opens and attempts to merge every case. Run C3 last; until then the exempt-authors variable
is absent or empty. Record the variable's state with each run: a blocked case whose last run started
while the variable named `OWNER` is a fail of the setup, not a pass. For each case, capture the run URL, `gh pr view N --json mergeStateStatus,statusCheckRollup` after the
latest run completes, and the result of an attempted `gh pr merge`. "Blocked" means GitHub refuses
the merge because the required check is failing or missing.

| # | Case | Steps | Pass | Result | Evidence |
|---|---|---|---|---|---|
| C1 | No reference | Open a pull request whose body has no reference | The check fails with the fix in its message; the merge is blocked | pass | https://github.com/MVPavan/bead-mirror-trial/pull/10, run https://github.com/MVPavan/bead-mirror-trial/actions/runs/44901298207 (fix in message); merge refused by gh's pre-check on BLOCKED (server refusal recorded for #10 in C7 and #17 in C6b, not for this PR); evidence/C1.md |
| C2 | One reference | Open a pull request with `Refs #n` | The check passes; the merge is allowed | pass | https://github.com/MVPavan/bead-mirror-trial/pull/11, run https://github.com/MVPavan/bead-mirror-trial/actions/runs/44901305267; CLEAN, merged; evidence/C2.md |
| C3 | Exempt author | After the other C cases, set the variable to `OWNER`'s login and open a pull request with no reference. Then clear the variable and edit the body, still with no reference | While the variable names `OWNER`, the check passes. After it is cleared, the edit's run fails and the merge is blocked, so the variable is read on each run; the variables read shows it absent or empty again | pass | https://github.com/MVPavan/bead-mirror-trial/pull/18, runs https://github.com/MVPavan/bead-mirror-trial/actions/runs/44901818283 (exempt, pass), https://github.com/MVPavan/bead-mirror-trial/actions/runs/44901867903 (cleared, fail); server refused the merge (REST merge: 405, required status check failing) after a reopen on the same head, run https://github.com/MVPavan/bead-mirror-trial/actions/runs/44918662332, variable absent; variable absent at end; evidence/C3.md; fresh sequence https://github.com/MVPavan/bead-mirror-trial/pull/22: exempt run passed, variable cleared, body edited, and the REST merge sent right after that edit's run failed (no other run between) got 405 |
| C4 | Green, then edited on the same head | Two passing pull requests, no new commits on either. On the first, edit the body to replace its reference with `Refs #m` for another mirrored issue, then at once edit it to remove the reference. On the second, edit the body to remove the reference, then at once restore it | Each edit reruns the check. Once the last run completes, the first pull request's verdict fails and its merge is blocked; the second's passes and its merge is allowed. Each final verdict matches that pull request's last body. Record each run's start and finish times and whether concurrency cancelled an older run, and say whether any pair finished in reverse order or was cancelled | pass (older run cancelled by concurrency in both pairs; no reverse-order finish, left to M4.3) | https://github.com/MVPavan/bead-mirror-trial/pull/12 (fail, server refused the merge (REST merge: 405, required status check failing) after a reopen on the same head, run https://github.com/MVPavan/bead-mirror-trial/actions/runs/44918703668, variable absent), https://github.com/MVPavan/bead-mirror-trial/pull/13 (pass, merged); evidence/C4.md; fresh sequence https://github.com/MVPavan/bead-mirror-trial/pull/19: passing run, body edited on the same head to drop the reference, and the REST merge sent right after that edit's run failed (no other run between) got 405 while mergeStateStatus still read UNKNOWN |
| C5 | New head | Push a commit to a pull request (the synchronize event) with no body change, once with a reference and once without | The check reruns on the new head and the verdict follows the body | pass | https://github.com/MVPavan/bead-mirror-trial/pull/14 (pass on new head; after a reopen on the same head, run https://github.com/MVPavan/bead-mirror-trial/actions/runs/44918808380 passed and the server merged it, REST merge 200), https://github.com/MVPavan/bead-mirror-trial/pull/15 (fail on new head, server refused the merge (REST merge: 405, required status check failing) after a reopen on the same head, run https://github.com/MVPavan/bead-mirror-trial/actions/runs/44918738792, variable absent); evidence/C5.md; fresh sequence, REST merge sent right after the synchronize run with no other run between: https://github.com/MVPavan/bead-mirror-trial/pull/20 (no reference) 405, https://github.com/MVPavan/bead-mirror-trial/pull/21 (reference) 200, merged |
| C6 | A pull request that edits the workflow | From a branch in `OWNER/TRIAL`, open a pull request with no reference whose only change is to `.github/workflows/bead-reference-check.yml`: its triggers stay as `install-check` wrote them and only the job's step is changed to always pass | The check runs from the default branch's workflow and fails; the merge is blocked | pass | https://github.com/MVPavan/bead-mirror-trial/pull/16, run https://github.com/MVPavan/bead-mirror-trial/actions/runs/44901688632 ran the default branch's step; server refused the merge (REST merge: 405, required status check failing) after a reopen on the same head, run https://github.com/MVPavan/bead-mirror-trial/actions/runs/44918774898, variable absent; evidence/C6.md |
| C6b | A same-name stand-in from a branch | From a branch in `OWNER/TRIAL`, open a pull request with no reference that adds a new workflow file with an `on: pull_request` trigger and one job with the check's name that always passes. Record which S9 setup is in use (ruleset requiring the workflow, or branch protection requiring the job name) | Either the stand-in cannot make the pull request mergeable (the merge is blocked), or the trial records that collaborator branches are outside the Supported setup for branch protection and names the part of the Check criterion this leaves unproven | pass (ruleset requires job name `bead-reference` from app 15368, which the stand-in also matches; server refused the merge (405) with the stand-in re-run to finish last and with it cancelling the real run via its concurrency group; the concurrent form rests on BLOCKED and gh's pre-check; the reading the evidence fits is that GitHub judges the latest run per workflow, so a separate workflow's success cannot override the real one (C4's #13 cancelled-then-success pair merged); unproven: a head where the real workflow leaves no check run of its own, for example cancelled before its job's check run exists) | https://github.com/MVPavan/bead-mirror-trial/pull/17, runs https://github.com/MVPavan/bead-mirror-trial/actions/runs/44903932259 (re-run last), https://github.com/MVPavan/bead-mirror-trial/actions/runs/44904091597 (real, cancelled); evidence/C6b.md |
| C7 | Enforcing, not evaluating | Read the ruleset or protection (S9) while C1 is open | Enforcement is active and the C1 merge attempt was refused, not merely reported | pass (C1's PR reopened, check failing: REST `PUT pulls/10/merge` got 405 "Required status check bead-reference is failing"; `gh pr merge --admin` got the same rule violation from `mergePullRequest`) | ruleset https://github.com/MVPavan/bead-mirror-trial/rules/27791832 active, bypass []; https://github.com/MVPavan/bead-mirror-trial/pull/10, run https://github.com/MVPavan/bead-mirror-trial/actions/runs/44903930244; evidence/C7.md |
| F1 | Fork pull request with a reference | From the second account's fork, open a pull request with `Refs #n`; approve its workflow run | The check runs under `pull_request_target` and passes; the merge is allowed. **Deferred until a second GitHub account exists (owner, 2026-11-20)** | deferred | |
| F2 | Fork pull request adding a same-name workflow | From the fork, open a pull request with no reference that adds a workflow whose job has the check's name and passes | The added workflow does not run before the owner approves it, and the pull request stays blocked. **Deferred until a second GitHub account exists (owner, 2026-11-20)** | deferred | |

Until F1 and F2 run with the second account, two things stay unproven: that the Supported setup's Actions policy runs the check
for fork pull requests (F1), and the Pull-request check's claim that a same-name check cannot stand in
(F2), which is the fork half of the Check criterion's "a pull request that edits the workflow does not
change its own verdict". C6 and C6b prove that claim only for a branch in the repository. Until F1 and F2 pass,
the trial has not passed and the activation prerequisite is unmet. Activating more narrowly, for
example only in repositories that take no fork pull requests, would be the owner's decision to record,
not something this checklist allows.

If C4 shows no pair of runs finishing in reverse order and no cancellation, the Check criterion's
"two edits on the same head whose runs finish in reverse order end with the verdict for the latest
body" stays unproven live. M4.3 takes it, with evidence such as a run deliberately held back by a
temporary delay so the later edit's run finishes first, or a replay of C4's two recorded event
payloads in reverse order, showing the final verdict is the latest body's.

**M4.3 result (2026-11-21): the reverse-order half is evidenced offline.** The test
`tests/mirror/test_mirror_references.py::test_check_two_edits_whose_runs_finish_in_reverse_order_end_with_the_latest_bodys_verdict`
replays C4's four recorded edits (`tests/mirror/fixtures/recorded/c4_edits.json`) against the
check's own step, extracted from the workflow `install-check` writes and run the way the runner
runs it. For each pull request, both edits are saved first. The newer edit's run then finishes
first and the older edit's run finishes last. Each run gets its own `edited` event payload, and
the older payload carries the older body. The verdict left last is the latest body's: the first
pull request ends failing and the second passing, as C4 ended live. The older body alone would have
given the other verdict. A mutation probe, a copy of the check that takes the body from the event
payload, fails this test (M4.3 evidence). What this proof does not cover is a run that read the body
before the later edit and still finished last. Only a cancellation that never happened allows that:
the workflow's concurrency group cancels the older run when the newer one is queued, and C4 showed
that cancellation live in both pairs.

### Session start (hooks)

| # | Case | Steps | Evidence to capture | Pass | Result | Evidence |
|---|---|---|---|---|---|---|
| H1 | Claude Code session start | In the trial clone, first save the baseline: the Beads context hook's output with the mirror hook entry absent (or `bd prime`'s output). Then, with the last background run more than fifteen minutes old, start one real Claude Code session | The baseline; the session-start output; the time the hook took; the mirror's log and the digest's timestamp after the session is up; any hook-trust prompt | The hook returns at once, the Beads context output matches the baseline, the digest summary prints, and the background run finishes after the hook returns with its outcome logged. Note any hook-trust prompt | pass (fix round 1, run due: hook 84 ms in session, exit 0; a `bd prime` SessionStart entry beside it printed output byte-identical to the baseline; launched run done 4 s after session exit; no trust prompt in `-p`) | evidence/H1.md |
| H2 | Codex session start | The same in Codex | As H1 | As H1 | pass (needs project and hook trust: per-invocation `-c` overrides; untrusted hook skipped silently, no prompt; fix round 1, run due: hook 71 ms in session (exit status not observable: `codex exec --json` emits no hook events); `bd prime` hook beside it printed output byte-identical to the baseline; run done) | evidence/H2.md |

H1 and H2 start sessions from the residue S6 copied. The spec's "after `update` installs the hook
entry" is proven at the `cr-e0a` sync, in a clone set up by `adopt`/`update`.

## 3. Recording plan

M4.3 replaces every file in `tests/mirror/fixtures/provisional/` with a recorded response under
`tests/mirror/fixtures/recorded/`, keeping the same file name. During the T cases, a pass-through
recording wrapper for `gh` saves each call's arguments, input, output, error output and exit status.
The wrapper is first on `PATH` from S7 onward, so the dry run and every later case are recorded.
The `since`-filtered creator listing that T2 and T3 send is recorded into `graphql_issues_page.json`
too. Two extra steps, run once C2 is open, record the `link` lookups:

1. `bead-mirror link BEAD N --actor ACTOR` for a trial bead with an empty `external_ref`, where `N`
   is C2's pull-request number. The command refuses it as a pull request; record the reply into
   `graphql_pull_node.json`.
2. The same with `N` an issue number in `OWNER/TRIAL`; record the lookup into `graphql_issue.json`.
The raw recordings stay under a gitignored `scratchpad/` directory and never go under `tests/`.

Before a recording is committed as a fixture, every identifying value is replaced: the values the fake
fills in (for example `$login`, `$repo_node_id`, `$issue_url`) go back to their placeholders, and
every other identifying value (logins, names, emails, company and location, numeric and node IDs,
every API or HTML URL naming an account or `OWNER/TRIAL`, avatar URLs, and timestamps if wanted)
becomes a placeholder or a fixed dummy. Fields the command does not read may be dropped or kept with
dummy values. Before the commit, a case-insensitive search of `tests/mirror/fixtures/recorded/` for
the owner's login, name and email, `OWNER/TRIAL` and the recorded node IDs finds
nothing.

| Provisional file | Record | From |
|---|---|---|
| `rest_user.json` | `gh api user` as `OWNER` | S7 dry run |
| `rest_repo.json` | `gh api repos/OWNER/TRIAL` | S7 dry run |
| `graphql_label.json` | `label(name:)` for a label that exists and for one that does not (the null reply) | T1, T4 |
| `graphql_createLabel.json` | `createLabel` for the first `bead-type:` label | T1 |
| `graphql_createIssue.json` | `createIssue` | T1 |
| `graphql_node.json` | `node(id:)` read-back of an issue | T1 |
| `graphql_issue_node.json` | The issue node with the fields the command selects, from that read-back, including a closed issue and one with an outside label | T1, T4, T5 |
| `graphql_issue.json` | `issueOrPullRequest(number:)` on an issue | The `link` step 2 |
| `graphql_pull_node.json` | `issueOrPullRequest(number:)` on a pull request number | The `link` step 1 |
| `graphql_issues_page.json` | `issues(filterBy: {createdBy})` listing, including a page with `hasNextPage` true if the trial has more issues than the command's page size | T2, T3 (the `since`-filtered listing), T11 |
| `graphql_comments_page.json` | The comments page | T5, T6 |
| `graphql_write.json` | `updateIssue`, `closeIssue`, `reopenIssue`, `addLabelsToLabelable`, `removeLabelsFromLabelable`, each one; they share this file's template only if their replies have the same shape | T3 to T7 |
| `graphql_addComment.json` | `addComment` | T5 |
| `errors.json` | See below | Separate fault runs |
| (new) `roundtrip_title.json`, `roundtrip_crlf_body.json`, `roundtrip_budget_body.json` | The round-trip writes and read-backs | T8, T9, T10 |

For `errors.json`, record what can be caused safely: `unauthenticated` (a `gh` with no login),
`not_found` (`gh api repos/OWNER/NO-SUCH-REPO`), `offline` (the network down), and a GraphQL error
reply (a query naming a field that does not exist), which shows how `gh` reports a GraphQL `errors`
body and what it exits with. `lost_response` comes from the wrapper in T11 and cannot be recorded
from GitHub. The rate limits (`rate_limited_403`, `rate_limited_429`, `graphql_rate_limited`,
`graphql_rate_limited_exit_0`, `graphql_rate_limited_partial`, `graphql_rate_limited_partial_exit_0`) and the server-side faults (`bad_gateway`, `error_after_write`,
`field_error_after_write`, `internal_error_after_write`) cannot be caused on purpose. They keep their
documented bodies and take the exit status and error format the safe recordings show; M4.3 notes them
as documented, not recorded. At its start M4.2 re-derives this list from the keys of
`tests/mirror/fixtures/provisional/errors.json`, so a key added later is not missed.

The closing-event and pull-request replies from T12 to T14, and any provisional fixture M2 or M3 adds
after this checklist, are recorded the same way. M4.2 lists the provisional directory again before it
starts.

### M4.3 replay

M4.3 (2026-11-21) built `tests/mirror/fixtures/recorded/` from M4.2's recordings, sanitised as
above, and deleted `tests/mirror/fixtures/provisional/`. `tests/mirror` now runs on the recorded
fixtures only. Its README lists the source of each file.

- **Recorded:** every provisional file. This includes the six that M2 and M3 added
  (`graphql_closed_by`, `graphql_high_water`, `graphql_inbound_issue`, `graphql_inbound_pull`,
  `graphql_pulls_page`, and `rest_pull`, read after the trial from C2's merged pull request,
  because the check's own read ran on GitHub's runner, outside the wrapper), the three round
  trips, C4's edits, the exact
  query text of every operation sent (`queries.json`, which the fake now enforces), and the
  `errors.json` keys `unauthenticated`, `not_found` and `offline`.
- **Documented, not recorded:** the other `errors.json` keys (the rate limits, the server-side
  faults and `lost_response`); and the `reopenIssue` reply, because the trial sent none.
- **Fake changes:** each mutation now returns its own recorded payload. Before, every write
  returned one shared shape, `addComment` returned a comment edge the command never selects, and
  `createIssue` returned the whole issue-node shape (labels, repository, `updatedAt`).
  Recorded operations must also send the recorded query text exactly. No recorded shape exposed a
  bug in the command.
