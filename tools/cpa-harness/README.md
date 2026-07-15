# CLIProxyAPI Latest Harness

Complete CLI, VS Code, environment, model, context, and compaction option
reference: [`CLAUDEX-OPTIONS.md`](CLAUDEX-OPTIONS.md).

This is an isolated, local-development harness for evaluating the latest
CLIProxyAPI image and Management Center. It does not join Bodha's shared Docker
network and does not reuse Bodha's proxy auth, logs, or plugins.

## Start and verify

```sh
cd tools/cpa-harness
cp .env.example .env
./cpa.sh up
./cpa.sh status
./cpa.sh verify
```

The tracked `.env.example` and ignored local `.env` use these development
defaults:

| Item | Local value |
|---|---|
| API and management server | `http://HOST_IP:58317` |
| Management Center | `http://HOST_IP:58317/management.html` |
| Management key | `cpa-harness-local-management-1` |
| Client API key | `sk-cpa-harness-local-1` |
| Antigravity callback | `http://HOST_IP:15121` |

Compose publishes the API and callback on all host interfaces. The host and
network firewalls determine which remote clients can connect; restrict ports
`58317` and `15121` to trusted addresses. The harness does not publish ports
`8317`, `8085`, `54545`, `1455`, or `11451`. Change the two port variables in
`.env` before `./cpa.sh up` if the defaults are occupied.

## Management Center and plugins

Open the Management Center URL above. Enter
`http://HOST_IP:58317` as the server from a remote client, or
`http://127.0.0.1:58317` on the host, and use the management key from `.env`.
Configuration, usage statistics, control-panel updates, and plugins are enabled
for this harness. Install `gemini-cli` from the official plugin registry through
the Management Center; there is no built-in Gemini login command in `cpa.sh`.

State is kept separately in `auths/`, `logs/`, and `plugins/`. The helper creates
these directories during `up`.

## OAuth logins

```sh
./cpa.sh login codex
./cpa.sh login claude
./cpa.sh login antigravity
./cpa.sh login kimi
./cpa.sh login xai
```

Codex uses device login. Antigravity alone uses the mapped callback port from
`.env`. Claude's callback is hardcoded to port `54545`, which is intentionally
not mapped because it collides with the existing proxy; use the manual
copy/paste instructions printed by its no-browser flow. Kimi and xAI also run
their provider-specific no-browser flows. This harness makes no generic callback
port promise for other providers.

## Claude Code with a GPT model

The `claudex` wrapper launches the installed Claude Code harness against this
proxy's Anthropic-compatible endpoint. It uses GPT-5.6 Sol for the main session,
subagents, and lightweight background work with `xhigh` effort. Tool discovery
and tool concurrency are left at Claude Code's provider-aware defaults. Claude
Code is told that Sol has a 1,050,000-token context window and a 128,000-token
maximum output. It reads the first client credential under `api-keys` in
`config.yaml`; it does not use or expose the management password.

The default auto-compaction window is 270,000 tokens with an explicit 90%
trigger. With Claude Code 2.1.206's current output reserve and compaction
buffer, that starts compaction at roughly 225,000 tokens. The extra 47,000-token
headroom is intentional: OpenAI's published API price for a Sol request
increases for the entire request once input exceeds 272,000 tokens. This
threshold is a cost-aware default rather than a model limit; the proxy's OAuth
subscription metering can differ from API billing.

Claude Code 2.1.206 still prints `maxOutputTokens: 32000` for this custom model
in `--output-format json`. That result field uses Claude Code's built-in model
metadata, not the `CLAUDE_CODE_MAX_OUTPUT_TOKENS` request override; do not use it
to validate the configured 128,000-token ceiling.

Install the command for the current user:

```sh
mkdir -p "$HOME/.local/bin"
ln -sfn "$(pwd)/claudex" "$HOME/.local/bin/claudex"
```

Then start it from any project:

```sh
claudex
claudex "Inspect this repository and explain its architecture"
CLAUDEX_EFFORT=xhigh claudex
```

`ENABLE_TOOL_SEARCH` is intentionally not forced. When it is unset, Claude Code
uses its provider-aware behavior: direct Anthropic connections can defer MCP
tool definitions, while custom gateways load them up front unless gateway tool
search is explicitly enabled. Ordinary tools remain available either way. Do
not set it to `true` until the proxy has been verified to pass Claude's
`tool_reference` blocks and related beta headers end to end.

Override the token policy for a particular session when the task genuinely
benefits from retaining more raw history:

```sh
CLAUDEX_AUTO_COMPACT_WINDOW=500000 CLAUDEX_AUTO_COMPACT_PERCENT=90 claudex
CLAUDEX_MAX_OUTPUT_TOKENS=64000 claudex
```

Larger compaction windows use more of Sol's available context but cross its
long-context pricing tier. Run `/compact` at a natural task boundary when you
can provide a useful summary focus, and use `/clear` between unrelated tasks.

The wrapper accepts normal Claude Code arguments. A resumed session retains its
previous model, so use `claudex --continue` only for a session that was already
created through `claudex`.

## Claude VS Code extension for one repository

The native Claude extension does not launch the `claudex` shell command. Use the
repo-local switch instead. Install its command for the current user from the
harness directory:

```sh
cd /path/to/coding-ritual/tools/cpa-harness
mkdir -p "$HOME/.local/bin"
ln -sfn "$(pwd)/claudex-vscode" "$HOME/.local/bin/claudex-vscode"
```

Ensure `$HOME/.local/bin` is on `PATH`, then enable it from the repository you
want to use with the proxy:

```sh
cd /path/to/repository
claudex-vscode enable
claudex-vscode status

# Later, restore the normal Claude login and model behavior:
claudex-vscode disable
```

`status` reports the current mode. You may also pass the repository path as the
second argument. Enabled mode uses GPT-5.6 Sol for the main session, background
work, and subagents, with `xhigh` effort. It declares the native Codex app's
current 372,000-token catalog window, 128,000-token output ceiling, and 90%
auto-compaction policy. Claude Code applies its own output reserve and
compaction buffer, so the observed trigger can be earlier than Codex's 334,800
tokens. Tool search, concurrency, permissions, and attribution remain at Claude
Code's normal defaults.

The switch stores gateway environment variables in the ignored
`.claude/settings.local.json`; the client key is never written to the tracked
`.vscode/settings.json`. It adds only `claudeCode.disableLoginPrompt` to the VS
Code workspace settings. Exact pre-enable files are backed up under the current
user's XDG state directory and restored by `disable`. To avoid losing edits,
disable refuses to overwrite either managed file if it changed after enable.
After preserving those edits, `disable --force` can restore the original files.

Start the proxy before enabling:

```sh
cd /path/to/coding-ritual/tools/cpa-harness
./cpa.sh up
```

After either toggle, start a new Claude chat. If the extension is already
running, use **Developer: Reload Window** in VS Code. The repository's saved
normal Claude login is not deleted; it becomes active again after `disable`.

This is a third-party compatibility path: CLIProxyAPI translates Claude's
Messages protocol to the selected Codex/OpenAI model. Anthropic does not support
non-Claude models in Claude Code. Keep the published ports restricted to trusted
clients, and retest the wrapper after pulling a new `latest` image.

## Non-production warning

`eceasy/cli-proxy-api:latest` is pulled on every `up`, so the same files can run
different upstream builds over time. The static client and management keys are
development credentials. This harness is deliberately non-reproducible and must
not be used for production or as Bodha's normal proxy. `./cpa.sh restart` also
pulls and recreates the container so environment changes take effect.

## Firewall setup on Host

```powershell
New-NetFirewallRule `
  -DisplayName "CLIProxyAPI from Office Laptop" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalAddress 192.168.0.176 `
  -LocalPort 58317 `
  -RemoteAddress 192.168.0.199 `
  -Profile Private
```
