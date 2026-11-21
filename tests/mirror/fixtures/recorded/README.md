# Recorded `gh` fixtures

Recorded in the live trial (stage M4.2, 2026-11-21, `gh` 2.103.0, github.com), with the mirror
residue copied from commit `79b93f9`. A pass-through wrapper saved every real `gh` call; stage M4.3
turned those recordings into these files. The checklist and its results are in
`docs/workstreams/beads-github-mirror/trial.md` (Recording plan). They replace the hand-written
provisional fixtures, file for file, under the same names.

## How the fake uses them

String values of the form `$name` are filled by `tests/mirror/_fake_gh.py` from its state (for
example `$login`, `$repo_node_id`, `$issue_url`). Keys starting with one `_` are notes
(`_recorded`, `_documented`; GraphQL's `__typename` stays) and are stripped before a response is
served. Each file keeps the structure of the recorded reply; only the values the fake fills in
became placeholders.

`queries.json` holds the exact query text of each operation the trial sent, which GitHub answered
without an error. The fake refuses a query for one of those operations unless its text is that
text, on top of its name checks. A command change to a query therefore needs a new recording.

## What was sanitised

Before anything was saved here, the trial account's login, name, email, company, location and
avatar, the trial repository's name, every numeric ID and node ID, every API or HTML URL that names
the account or the repository, opaque pagination cursors and the trial store's `project_id` were
replaced. Values the fake fills went back to their `$placeholders`. Every other value became a
fixed dummy: `OWNER`, `OWNER/TRIAL`, node IDs of the form `I_kwDOdummy0001`, user IDs 1000001 and
1000002, and the store `00000000-0000-4000-8000-000000000000`. Profile fields the command does not
read are null. The issue reads in the round-trip files that the later runs made of other issues
were dropped; their summaries stay. The two 60,000-character bodies in `roundtrip_budget_body.json`
keep their first and last 300 characters, their length in characters and UTF-8 bytes, and a
SHA-256 hash of each copy (sent, create reply, read-back), taken after sanitising.

## Recorded, and documented only

| File | Source |
|---|---|
| `rest_user.json`, `rest_repo.json` | S7 dry run |
| `graphql_label.json` (an existing label; T1's reply for a missing one is `null`), `graphql_createLabel.json`, `graphql_createIssue.json` | T1, T8 |
| `graphql_node.json`, `graphql_issue_node.json` | T6 read of a closed issue that carries an outside label |
| `graphql_issues_page.json`, `graphql_comments_page.json` | T8, T6 |
| `graphql_write.json` | One reply per mutation: `updateIssue` (T3), `closeIssue` (T5), the two label mutations (T4) |
| `graphql_addComment.json` | T5 |
| `graphql_issue.json`, `graphql_pull_node.json` | The `link` steps, on an issue and on a pull request |
| `graphql_high_water.json`, `graphql_inbound_issue.json`, `graphql_inbound_pull.json`, `graphql_pulls_page.json`, `graphql_closed_by.json` | The inbound run after T12 to T14 |
| `roundtrip_title.json`, `roundtrip_crlf_body.json`, `roundtrip_budget_body.json` | T8, T9, T10 |
| `c4_edits.json` | C4's four body edits, in the order sent |
| `rest_pull.json` | `GET repos/OWNER/TRIAL/pulls/N` of C2's merged pull request, read after the trial (the check's own read ran on GitHub's runner, outside the wrapper); the derived API URLs, the repositories under `head` and `base` and the commit SHAs were dropped |
| `errors.json`: `unauthenticated`, `not_found`, `offline` | Safe fault runs (`gh` with no login, a missing repository, no network) |

Documented, not recorded:

- `errors.json`: `rate_limited_403`, `rate_limited_429`, `graphql_rate_limited`,
  `graphql_rate_limited_exit_0`, `graphql_rate_limited_partial`,
  `graphql_rate_limited_partial_exit_0`, `bad_gateway`, `error_after_write`,
  `field_error_after_write` and `internal_error_after_write` cannot be caused on purpose.
  `lost_response` comes from the T11 fault wrapper. They keep GitHub's documented bodies and the
  exit status and error format the safe recordings show (exit 1, the body on stdout,
  `gh: <message>` on stderr). A recorded GraphQL validation error showed that format.
- `graphql_write.json`'s `reopenIssue` reply: the trial sent no `reopenIssue`, because T7 holds
  instead of writing. The command selects `issue { id }`, as it does for `closeIssue`, so the reply
  copies `closeIssue`'s recorded reply.
- The `MirrorItem` query (inbound's lookup of one number) was not sent in the trial. Its reply uses
  `graphql_issue.json`'s recorded envelope and the recorded inbound node shapes.
