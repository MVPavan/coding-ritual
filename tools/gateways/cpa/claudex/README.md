# claudex: Claude Code on GPT models through CLIProxyAPI

Not in use. Kept because it works and the option reference is expensive to
rebuild. Everything here drives the installed Claude Code against
CLIProxyAPI's Anthropic-compatible endpoint with a GPT model. Full CLI, VS
Code, environment, model, context, and compaction option reference:
[`CLAUDEX-OPTIONS.md`](CLAUDEX-OPTIONS.md).

This is a third-party compatibility path: CLIProxyAPI translates Claude's
Messages protocol to the selected Codex model. Anthropic does not support
non-Claude models in Claude Code. The wrappers read the client key from
[`../config.yaml`](../config.yaml) and the API port from the project's
`.env`; start the `cpa` service with `../../gw.sh up cpa` first.

## `claudex`: CLI wrapper

Launches Claude Code against the proxy with GPT-5.6 Sol for the main
session, subagents, and background work at `xhigh` effort. Claude Code is
told that Sol has a 1,050,000-token context window and a 128,000-token
maximum output. Tool discovery and tool concurrency stay at Claude Code's
provider-aware defaults.

The default auto-compaction window is 270,000 tokens with an explicit 90%
trigger, which starts compaction at roughly 225,000 tokens after Claude
Code's output reserve and compaction buffer. The headroom is intentional:
OpenAI's published API price for a Sol request rises for the whole request
once input exceeds 272,000 tokens. The proxy's OAuth subscription metering
can differ from API billing.

Claude Code prints `maxOutputTokens: 32000` for this custom model in
`--output-format json`; that field comes from built-in model metadata, not
the request override, so do not use it to validate the 128,000 ceiling.

Install for the current user, then run from any project:

```sh
mkdir -p "$HOME/.local/bin"
ln -sfn "$(pwd)/claudex" "$HOME/.local/bin/claudex"

claudex
claudex "Inspect this repository and explain its architecture"
CLAUDEX_EFFORT=xhigh claudex
CLAUDEX_AUTO_COMPACT_WINDOW=500000 CLAUDEX_AUTO_COMPACT_PERCENT=90 claudex
CLAUDEX_MAX_OUTPUT_TOKENS=64000 claudex
```

`ENABLE_TOOL_SEARCH` is intentionally not forced. Do not set it to `true`
until the proxy has been verified to pass Claude's `tool_reference` blocks
and related beta headers end to end. Larger compaction windows cross Sol's
long-context pricing tier. A resumed session keeps its model, so use
`claudex --continue` only for a session created through `claudex`.

## `claudex-vscode`: repository switch for the VS Code extension

The native Claude extension does not launch the `claudex` shell command, so
this switch writes the same gateway profile into one repository:

```sh
mkdir -p "$HOME/.local/bin"
ln -sfn "$(pwd)/claudex-vscode" "$HOME/.local/bin/claudex-vscode"

cd /path/to/repository
claudex-vscode enable
claudex-vscode status
claudex-vscode disable      # restore the normal Claude login and model
```

Enabled mode uses GPT-5.6 Sol for the main session, background work, and
subagents at `xhigh` effort, declaring the native Codex app's 372,000-token
window, 128,000-token output ceiling, and 90% auto-compaction. Gateway
variables go into the ignored `.claude/settings.local.json`; the client key
is never written to the tracked `.vscode/settings.json`, which only gains
`claudeCode.disableLoginPrompt`. Pre-enable files are backed up under the
user's XDG state directory and restored by `disable`, which refuses to
overwrite a managed file that changed after enable unless given `--force`.

After either toggle, start a new Claude chat or run **Developer: Reload
Window**. While a repository is enabled, its local settings outrank the
user-level Claude relay profile; disable it before using the relay there.
