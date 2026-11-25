# Claude CLI

Run Claude Code non-interactively with `claude -p`.

**Model list:** the CLI has no model-list command (checked on 2.1.309), and
`--effort` accepts every level for any model. With `ANTHROPIC_API_KEY` set,
`python3 scripts/models.py refresh claude-cli` records the Models API's active
models and their supported efforts. Without it, `models.json` here is the
fallback: a reviewed seed with sources, updated from the vendor's model and
effort documentation when a model ships. Check a pair before launch with
`python3 scripts/models.py check claude-cli <model> --effort <level>`.

```bash
# Writer (implementer).
claude -p "<brief>" --model <id> --effort <level> --output-format json \
  --permission-mode dontAsk --tools "Read,Glob,Grep,Edit,Write,Bash" \
  --allowedTools "Read,Glob,Grep,Edit,Write,Bash" > <result.json>
# Read-only role (explorer, reviewer, critic).
claude -p "<brief>" --model <id> --effort <level> --output-format json \
  --permission-mode dontAsk --strict-mcp-config --tools "Read,Glob,Grep" \
  --allowedTools "Read,Glob,Grep" > <result.json>
# Follow-up in the worker's own session: the same flags plus --resume.
claude -p "<follow-up>" --resume <session-id> --model <id> --effort <level> ...
```

- Put the prompt right after `-p`: `--tools` and `--allowedTools` take a list
  and would swallow a later prompt.
- `dontAsk` denies every tool not pre-approved, so a run never waits on a
  permission prompt.
- `--max-budget-usd <amount>` caps a run's spend. Do not pass
  `--fallback-model`: it lets another model answer.

**Read-only roles:** the tool list is enforced: without Edit, Write or Bash the
worker cannot change files. `--strict-mcp-config` without `--mcp-config` loads no
MCP servers. A reviewer that must run checks needs Bash, and from then on the
brief is the only read-only control.

**What ran:** `python3 scripts/models.py ran claude-cli <result.json>` reads the
JSON result: the models that served the run (`modelUsage`), `is_error` and the
session ID. Treat `is_error: true` as failure even with exit code 0: Claude has
failed and still exited 0. The result does not report effort, so record it as
requested-but-unverified.
