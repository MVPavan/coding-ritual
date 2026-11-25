# Where the chats are

Read when mining chats (`SKILL.md` step 3). Both stores below hold one JSON
record per line. In both, order files by modification time (`ls -t`, or
`stat`), never by file name, and search them with `rg` or `grep` before reading
any region. Modification time orders candidates; it never identifies the current
chat. Skip the current chat by its id: Claude Code exposes it as
`CLAUDE_CODE_SESSION_ID`, Codex as `CODEX_THREAD_ID`. A chat in the other tool's
store is never the current one. If the current id cannot be read, say so in the
coverage line instead of guessing which file is current.

## Claude Code

`~/.claude/projects/<workspace path with each "/" replaced by "-">/<session-id>.jsonl`,
one file per chat; the file name is the session id to cite. Helper chats sit
under `<session-id>/subagents/`: skip them.

## Codex

`~/.codex/sessions/<yyyy>/<mm>/<dd>/rollout-*.jsonl`, one file per chat. The first
line is a `session_meta` record whose `payload` holds the chat's `cwd` and `id`.
Keep only chats whose `cwd` is this workspace (another project's only when
asked). A helper chat has a non-empty `payload.parent_thread_id` (its
`payload.source` is then an object, not a plain string): skip it. Read the first
line alone to filter; open the rest only for chats that pass.

## Another tool, or a moved store

If a store is not at its path above, or the chats came from another tool, list
that store as unavailable in the coverage line and carry on with every store
that is there. Recall from the shared record alone only when no chat store is
available.
