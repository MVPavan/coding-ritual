# Where the sessions are

Read when a log's location is unknown or a delegated run's sessions must be
listed (`SKILL.md` step 2). Both stores hold one JSON record per line. Order
files by modification time (`ls -t` or `stat`), never by file name. Identify a
file from its name and first line; read further only in the sessions in scope.

The current session's id is `CLAUDE_CODE_SESSION_ID` in Claude Code and
`CODEX_THREAD_ID` in Codex. Modification time never identifies it; if the id
cannot be read, say so instead of guessing which file is current.

## Claude Code

`~/.claude/projects/<workspace path with each "/" replaced by "-">/<session-id>.jsonl`,
one file per session. The helper sessions it dispatched are
`<session-id>/subagents/agent-*.jsonl`, each beside a `.meta.json` file.

## Codex

`~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-*.jsonl`, one file per session. The
first line is a `session_meta` record whose `payload` holds the session's `id`
and `cwd`; keep only sessions whose `cwd` is this workspace. A dispatched
session's `payload.parent_thread_id` is its parent's `id`: follow these links
down from the run's top session to list every session it dispatched, nested
ones included.

## Links the logs do not hold

When a worker's session cannot be linked to its parent from the logs (a thread
started through another tool, a store moved or missing), use the sessions the
person names or the run's own record lists, and name each link that could not
be followed in the reply's coverage.
