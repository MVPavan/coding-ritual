# Claudex CLI and VS Code option reference

Snapshot: 2026-07-15 · Claude Code CLI 2.1.207 · Claude Code VS Code extension
2.1.210.

This file distinguishes four configuration surfaces:

1. Claude Code environment variables shared by the CLI and VS Code extension.
2. `CLAUDEX_*` and `CPA_*` inputs understood by this harness.
3. Native `claude` command-line flags, all of which `claudex` passes through.
4. Native VS Code extension settings under `claudeCode.*`.

Claude Code changes frequently. Recheck `claude --help`, the installed
extension manifest, and the official environment-variable reference after an
upgrade. Undocumented internal variables are intentionally excluded.

Official references:

- <https://code.claude.com/docs/en/env-vars>
- <https://code.claude.com/docs/en/configuration>
- <https://code.claude.com/docs/en/model-config>
- <https://code.claude.com/docs/en/llm-gateway-connect>
- <https://code.claude.com/docs/en/ide-integrations>

## Which surface should hold a setting?

| Desired scope | Put the setting here |
|---|---|
| One `claudex` CLI invocation | Prefix the command with `CLAUDEX_*=...` |
| Every `claudex` CLI invocation | Export `CLAUDEX_*` in a shell profile or wrapper |
| One repository, CLI and VS Code | `.claude/settings.local.json` → `env` |
| Every repository, CLI and VS Code process | `~/.claude/settings.json` → `env` |
| VS Code extension UI only | VS Code `claudeCode.*` settings |
| Temporary native CLI override | A native `claude --flag` passed through `claudex` |

Configuration precedence is: managed policy, CLI flags, local project settings,
shared project settings, and user settings. Gateway credentials take precedence
over a saved claude.ai login while present.

## Recommended GPT-5.6 Sol project profile

This is the full profile when the 1.05M context declaration, 128K output ceiling,
and cost-aware compaction policy are wanted in both the CLI and VS Code:

```json
{
  "model": "gpt-5.6-sol",
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:58317",
    "ANTHROPIC_AUTH_TOKEN": "YOUR_CPA_CLIENT_KEY",
    "ANTHROPIC_MODEL": "gpt-5.6-sol",
    "ANTHROPIC_CUSTOM_MODEL_OPTION": "gpt-5.6-sol",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "gpt-5.6-sol",
    "CLAUDE_CODE_SUBAGENT_MODEL": "gpt-5.6-sol",
    "CLAUDE_CODE_ALWAYS_ENABLE_EFFORT": "1",
    "CLAUDE_CODE_EFFORT_LEVEL": "xhigh",
    "CLAUDE_CODE_MAX_CONTEXT_TOKENS": "1050000",
    "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "128000",
    "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "270000",
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "90"
  }
}
```

Store this only in ignored `.claude/settings.local.json`, never in a committed
`.claude/settings.json`. Use the actual proxy IP instead of `127.0.0.1` from a
remote client; keep `127.0.0.1` when Claude runs on the proxy host.

`ENABLE_TOOL_SEARCH`, `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY`, and
`CLAUDE_CODE_ATTRIBUTION_HEADER` are deliberately absent so Claude Code uses its
provider-aware defaults.

## Shared Claude Code environment variables used by this setup

These variables can be placed in a shell environment or in the `env` object of
a Claude settings file. Values in JSON must be strings.

| Variable | Current claudex value | Purpose and cautions |
|---|---:|---|
| `ANTHROPIC_BASE_URL` | `http://127.0.0.1:58317` | Anthropic-format gateway root; do not append `/v1`. |
| `ANTHROPIC_AUTH_TOKEN` | First CPA client key | Sends `Authorization: Bearer`. This is a CPA `api-keys` entry, not the management password or OAuth credential. |
| `ANTHROPIC_MODEL` | Not exported by `claudex`; `--model` is used | Default main model for surfaces without a CLI model flag. The VS Code profile sets it. |
| `ANTHROPIC_CUSTOM_MODEL_OPTION` | `gpt-5.6-sol` | Adds an arbitrary gateway model ID and bypasses built-in model validation. |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | `gpt-5.6-sol` | Replaces the lightweight/background model mapping. |
| `CLAUDE_CODE_SUBAGENT_MODEL` | `gpt-5.6-sol` | Forces all subagents and agent teams to this model; overrides agent frontmatter. |
| `CLAUDE_CODE_ALWAYS_ENABLE_EFFORT` | `1` | Sends effort controls for a custom gateway model. Translation still depends on CPA. |
| `CLAUDE_CODE_EFFORT_LEVEL` | `xhigh` | Default effort: `low`, `medium`, `high`, `xhigh`, or `max`. A CLI `--effort` can override it. |
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | `1050000` in `claudex` | Declares the context window for an unknown custom model. The VS Code switch currently leaves it unset unless added manually to project settings. |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | `128000` in `claudex` | Requested output-token ceiling. It cannot exceed proxy/upstream support. The VS Code switch currently leaves it unset unless added manually. |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | `270000` in `claudex` | Context window used for automatic compaction. The cost-aware harness value is not a native Claude default. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | `90` in `claudex` | Compaction trigger percentage, from `1` to `100`; values above Claude's native threshold have no effect. |
| `ENABLE_TOOL_SEARCH` | Unset | Unset uses provider-aware behavior. `false` loads MCP definitions up front; `true` requires gateway `tool_reference` compatibility. This does not enable or disable ordinary tools. |
| `CLAUDE_CODE_MAX_TOOL_USE_CONCURRENCY` | Unset | Maximum concurrent tool uses. Native default is currently `10`; this harness does not override it. |
| `CLAUDE_CODE_ATTRIBUTION_HEADER` | Unset | Controls Claude Code attribution. This harness leaves the native behavior unchanged. |
| `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS` | Unset | Set `1` only when a gateway rejects experimental beta fields. It can disable features. |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | Unset | Set `1` to suppress most nonessential traffic. It does not disable all safety-related network checks. |

Behind `ANTHROPIC_BASE_URL`, Anthropic does not support routing Claude Code to a
non-Claude model. Every custom-model field above remains dependent on CPA's
Anthropic-to-OpenAI translation.

## `claudex` wrapper inputs

Syntax:

```sh
NAME=value claudex [native Claude CLI flags] [prompt]
```

| Input | Default | Mapped behavior |
|---|---:|---|
| `CPA_CONFIG_FILE` | `config.yaml` beside `claudex` | File from which the first `api-keys` entry is read. |
| `CPA_CLIENT_API_KEY` | Unset | Direct CPA client-key override; avoids needing a local `config.yaml`. Required on a remote machine unless another config file is supplied. |
| `CPA_API_PORT` | `.env`, then `58317` | Local gateway port used when `CLAUDEX_BASE_URL` is unset. |
| `CLAUDEX_BASE_URL` | `http://127.0.0.1:$CPA_API_PORT` | Full gateway root URL. |
| `CLAUDEX_MODEL` | `gpt-5.6-sol` | Main model passed as `claude --model`. |
| `CLAUDEX_BACKGROUND_MODEL` | Main model | Value exported as `ANTHROPIC_DEFAULT_HAIKU_MODEL`. |
| `CLAUDEX_SUBAGENT_MODEL` | Main model | Value exported as `CLAUDE_CODE_SUBAGENT_MODEL`. |
| `CLAUDEX_EFFORT` | `xhigh` | Value exported as `CLAUDE_CODE_EFFORT_LEVEL`. |
| `CLAUDEX_CONTEXT_TOKENS` | `1050000` | Value exported as `CLAUDE_CODE_MAX_CONTEXT_TOKENS`; positive integer. |
| `CLAUDEX_MAX_OUTPUT_TOKENS` | `128000` | Value exported as `CLAUDE_CODE_MAX_OUTPUT_TOKENS`; positive integer. |
| `CLAUDEX_AUTO_COMPACT_WINDOW` | `270000` | Value exported as `CLAUDE_CODE_AUTO_COMPACT_WINDOW`; positive integer. |
| `CLAUDEX_AUTO_COMPACT_PERCENT` | `90` | Value exported as `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`; integer `1`–`100`. |

Example:

```sh
CLAUDEX_MODEL=gpt-5.6-sol \
CLAUDEX_EFFORT=max \
CLAUDEX_CONTEXT_TOKENS=1050000 \
CLAUDEX_MAX_OUTPUT_TOKENS=128000 \
CLAUDEX_AUTO_COMPACT_WINDOW=500000 \
CLAUDEX_AUTO_COMPACT_PERCENT=90 \
claudex
```

## `claudex-vscode` commands and inputs

Commands:

| Command | Purpose |
|---|---|
| `claudex-vscode enable [REPOSITORY]` | Back up the repository's settings and install the gateway profile. |
| `claudex-vscode status [REPOSITORY]` | Report disabled, enabled, or enabled-but-modified. |
| `claudex-vscode disable [REPOSITORY]` | Restore the exact pre-enable settings when managed files are unchanged. |
| `claudex-vscode disable --force [REPOSITORY]` | Restore backups over settings modified after enable. Preserve wanted edits first. |
| `claudex-vscode --help` | Show command usage. |

Inputs read during `enable`:

| Input | Default | Notes |
|---|---:|---|
| `CPA_CONFIG_FILE` | `config.yaml` beside the script | Use only when the proxy config is present locally. |
| `CPA_CLIENT_API_KEY` | Unset | Required when the script is copied alone to a remote machine. |
| `CPA_API_PORT` | `.env`, then `58317` | Used only to construct the default base URL. |
| `CLAUDEX_BASE_URL` | `http://127.0.0.1:$CPA_API_PORT` | Use the proxy IP or an HTTPS URL for a direct remote connection. |
| `CLAUDEX_MODEL` | `gpt-5.6-sol` | Main model written to project settings. |
| `CLAUDEX_BACKGROUND_MODEL` | Main model | Background model written to project settings. |
| `CLAUDEX_SUBAGENT_MODEL` | Main model | Global subagent model written to project settings. |
| `CLAUDEX_EFFORT` | `xhigh` | Effort written to project settings. |
| `CLAUDEX_VSCODE_STATE_HOME` | `$XDG_STATE_HOME/claudex-vscode` | Override for private backup/state storage; mainly useful for tests. |

The current VS Code switch does **not** read `CLAUDEX_CONTEXT_TOKENS`,
`CLAUDEX_MAX_OUTPUT_TOKENS`, `CLAUDEX_AUTO_COMPACT_WINDOW`, or
`CLAUDEX_AUTO_COMPACT_PERCENT`. Add their mapped `CLAUDE_*` variables to the
generated `.claude/settings.local.json` when those overrides are required. A
post-enable edit makes `status` report modified, so use `disable --force` after
preserving any wanted changes.

Remote-machine example:

```sh
CPA_CLIENT_API_KEY='YOUR_REMOTE_CPA_CLIENT_KEY' \
CLAUDEX_BASE_URL='http://PROXY_PRIVATE_IP:58317' \
claudex-vscode enable /path/to/repository
```

After `enable` or `disable`, start a new Claude conversation. For the native VS
Code panel, run **Developer: Reload Window** when an old process is still open.

## Native Claude CLI flags passed through by `claudex`

`claudex` ends with `claude --model "$CLAUDEX_MODEL" "$@"`, so all current
top-level native flags below can follow `claudex`. This list is from
`claude --help` in CLI 2.1.207.

### Session, model, and workspace

| Flag | Purpose |
|---|---|
| `[prompt]` | Start a session with an initial prompt. |
| `--model <model>` | Select the session model. Prefer `CLAUDEX_MODEL` with this wrapper to avoid duplicate model flags. |
| `--effort <level>` | Override effort for the session: `low`, `medium`, `high`, `xhigh`, or `max`. |
| `--fallback-model <models>` | Comma-separated fallbacks for `--print`; the primary is retried each turn. |
| `--agent <agent>` | Use a named agent for the current session. |
| `--agents <json>` | Define ephemeral custom agents as JSON. |
| `--add-dir <directories...>` | Add directories Claude tools may access. |
| `-c`, `--continue` | Continue the most recent conversation in the current directory. |
| `-r`, `--resume [value]` | Resume by session ID or open the session picker. |
| `--fork-session` | Fork instead of reusing the resumed session ID. |
| `--session-id <uuid>` | Start with a specific valid conversation UUID. |
| `--from-pr [value]` | Resume a session linked to a pull request. |
| `-n`, `--name <name>` | Give the session a display name. |
| `-w`, `--worktree [name]` | Create and use a Git worktree. |
| `--tmux[=classic]` | Run a worktree session in tmux or supported native panes. |
| `--bg`, `--background` | Start as a background agent. |
| `--remote-control [name]` | Enable Remote Control for an interactive session. |
| `--remote-control-session-name-prefix <prefix>` | Change the prefix for generated Remote Control names. |
| `--ide` | Auto-connect to the one available supported IDE. |

### Permissions, tools, MCP, and browser

| Flag | Purpose |
|---|---|
| `--permission-mode <mode>` | Start in `manual`, `plan`, `acceptEdits`, `auto`, `dontAsk`, or `bypassPermissions`. |
| `--allow-dangerously-skip-permissions` | Make bypass mode available without selecting it initially. |
| `--dangerously-skip-permissions` | Bypass all permission checks; use only in a strongly isolated sandbox. |
| `--allowedTools`, `--allowed-tools <tools...>` | Allow specified tool patterns. |
| `--disallowedTools`, `--disallowed-tools <tools...>` | Deny specified tool patterns. |
| `--tools <tools...>` | Select built-in tools, `default`, or an empty set. |
| `--mcp-config <configs...>` | Load MCP configuration files or inline JSON. |
| `--strict-mcp-config` | Ignore all MCP sources except `--mcp-config`. |
| `--chrome` | Enable Claude in Chrome integration. |
| `--no-chrome` | Disable Claude in Chrome integration. |
| `--disable-slash-commands` | Disable all skills/slash commands. |
| `--brief` | Enable the `SendUserMessage` agent-to-user tool. |

### Prompt and configuration

| Flag | Purpose |
|---|---|
| `--system-prompt <prompt>` | Replace the default system prompt. |
| `--append-system-prompt <prompt>` | Append to the default system prompt. |
| `--exclude-dynamic-system-prompt-sections` | Move machine-specific prompt sections into the first user message for cache reuse. |
| `--settings <file-or-json>` | Load additional settings from a file or inline JSON. |
| `--setting-sources <sources>` | Limit settings to comma-separated `user`, `project`, and/or `local`. |
| `--plugin-dir <path>` | Load a plugin directory or zip for this session; repeatable. |
| `--plugin-url <url>` | Fetch a plugin zip for this session; repeatable. |
| `--file <specs...>` | Download file resources as `file_id:relative_path`. |
| `--betas <betas...>` | Add API beta headers for API-key users. |
| `--json-schema <schema>` | Validate structured output against a JSON Schema. |

### Non-interactive input and output

| Flag | Purpose |
|---|---|
| `-p`, `--print` | Run non-interactively and print a result. Workspace trust is skipped; use only in trusted directories. |
| `--input-format <format>` | With `--print`, accept `text` or `stream-json`. |
| `--output-format <format>` | With `--print`, emit `text`, `json`, or `stream-json`. |
| `--include-partial-messages` | Include streaming partials with `--print --output-format=stream-json`. |
| `--include-hook-events` | Include hook lifecycle events in stream JSON. |
| `--replay-user-messages` | Echo streaming user messages for acknowledgement. |
| `--no-session-persistence` | Do not save a non-interactive session. |
| `--max-budget-usd <amount>` | Cap API cost in `--print` mode. Gateway subscription accounting may differ. |
| `--prompt-suggestions [boolean]` | Emit a predicted next prompt in print/SDK mode. |

### Diagnostics and reduced modes

| Flag | Purpose |
|---|---|
| `-d`, `--debug [filter]` | Enable debug logging, optionally filtered. |
| `--debug-file <path>` | Write debug logs to a file. |
| `--verbose` | Override verbose mode from settings. |
| `--bare` | Minimal mode without hooks, LSP, plugin sync, attribution, auto-memory, prefetches, keychain reads, or automatic CLAUDE.md discovery. |
| `--safe-mode` | Disable customizations while retaining auth, model selection, built-in tools, permissions, and managed policy. |
| `--ax-screen-reader` | Use screen-reader-friendly rendering. |
| `-h`, `--help` | Print help. |
| `-v`, `--version` | Print the Claude Code version. |

### Native CLI subcommands

| Command | Purpose |
|---|---|
| `agents` | Manage background agents. |
| `auth` | Manage authentication. |
| `auto-mode` | Inspect the auto-mode classifier. |
| `doctor` | Diagnose the current installation and project settings. |
| `gateway` | Run the enterprise authentication/telemetry gateway. |
| `install [target]` | Install stable, latest, or a specific Claude Code build. |
| `mcp` | Configure MCP servers. |
| `plugin`, `plugins` | Manage plugins. |
| `project` | Manage Claude Code project state. |
| `setup-token` | Create a long-lived Claude subscription token. |
| `ultrareview [target]` | Run cloud multi-agent code review. |
| `update`, `upgrade` | Update Claude Code. |

Subcommands have their own flags. Run `claude <command> --help` for the live
subcommand surface.

## VS Code extension settings

These are the full `claudeCode.*` settings contributed by installed extension
2.1.210. `machine` settings cannot be overridden per repository; `window`
settings can be placed in `.vscode/settings.json` for a workspace.

| Setting | Default | Scope | Purpose |
|---|---:|---|---|
| `claudeCode.environmentVariables` | `[]` | machine | Environment variables passed when the extension launches Claude. Officially the most reliable place for gateway credentials during the extension's pre-launch login check, but it affects every repository on that machine. |
| `claudeCode.useTerminal` | `false` | window | Use terminal UI instead of the native graphical panel. |
| `claudeCode.allowDangerouslySkipPermissions` | `false` | window | Add bypass-permissions mode; use only in an isolated sandbox. |
| `claudeCode.claudeProcessWrapper` | unset | machine | Executable used to wrap or replace the bundled Claude process. |
| `claudeCode.respectGitIgnore` | `true` | window | Exclude ignored paths from file search. |
| `claudeCode.initialPermissionMode` | `default` | window | Initial permission mode for new conversations. |
| `claudeCode.disableLoginPrompt` | `false` | window | Skip the extension login prompt for externally authenticated/provider sessions. The repo-local switch sets this to `true` while enabled. |
| `claudeCode.autosave` | `true` | window | Save files before Claude reads or writes them. |
| `claudeCode.useCtrlEnterToSend` | `false` | window | Require Ctrl/Cmd+Enter to send. |
| `claudeCode.preferredLocation` | `panel` | window | Open in a panel/editor tab or sidebar. |
| `claudeCode.enableNewConversationShortcut` | `false` | window | Let Ctrl/Cmd+N create a Claude conversation while focused. |
| `claudeCode.enableReopenClosedSessionShortcut` | `true` | window | Let Ctrl/Cmd+Shift+T reopen the last closed Claude session where applicable. |
| `claudeCode.hideOnboarding` | `false` | window | Hide the onboarding checklist. |
| `claudeCode.usePythonEnvironment` | `true` | window | Activate the workspace Python environment when supported. |

Example user-level gateway settings for a fresh VS Code installation:

```json
{
  "claudeCode.environmentVariables": [
    { "name": "ANTHROPIC_BASE_URL", "value": "https://gateway.example.com" },
    { "name": "ANTHROPIC_AUTH_TOKEN", "value": "YOUR_CPA_CLIENT_KEY" }
  ],
  "claudeCode.disableLoginPrompt": true
}
```

This user-level form is officially documented and reliable for the extension's
login check, but it is global to the VS Code machine. The repo-local switch uses
`.claude/settings.local.json` plus workspace `disableLoginPrompt` to keep routing
repository-specific.

## Native defaults retained by this harness

Unless explicitly listed above, this harness leaves Claude Code unchanged:

- ordinary built-in tools and permission prompts remain enabled;
- tool concurrency remains at the current native default of `10`;
- dynamic MCP tool search follows provider-aware behavior;
- VS Code autosave, ignore handling, location, shortcuts, and Python activation
  remain at extension defaults;
- the VS Code profile leaves token limits and compaction at native defaults
  unless their shared `CLAUDE_*` variables are added manually;
- the CLI wrapper retains its explicit 1.05M/128K/270K/90 token policy.

## Security rules

- Never commit `ANTHROPIC_AUTH_TOKEN` or `CPA_CLIENT_API_KEY`.
- Never use the CPA management password as the Claude client token.
- Never copy CPA `auths/` OAuth files to a client machine.
- Prefer an SSH tunnel, private VPN, or authenticated HTTPS gateway over plain
  HTTP across an untrusted network.
- Do not enable bypass-permissions mode outside a strongly isolated sandbox.
- Do not force `ENABLE_TOOL_SEARCH=true` until CPA has passed an end-to-end
  `tool_reference` compatibility test.
