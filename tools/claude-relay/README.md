# Claude relay

A dumb reverse relay on the home box that forwards Claude Code's model traffic
to `api.anthropic.com` unchanged. It exists so Claude Code and the Claude VS
Code extension on machines without internet can reach Anthropic through the
home box, the same way Codex on those machines reaches CLIProxyAPI in
[`../cpa-harness`](../cpa-harness/README.md).

Only Claude Code's model calls are routed, via `ANTHROPIC_BASE_URL`. There is
no `HTTPS_PROXY`, so no other process on the hub or a leaf is affected, and no
`NO_PROXY` list is ever needed. The relay holds no credentials: each client
carries its own one-year token minted by `claude setup-token`.

Verified 2026-09-04 with Claude Code 2.1.258: a `claude -p` run against this
relay with the token in `ANTHROPIC_AUTH_TOKEN` returned a successful result, and the
relay log showed the bearer arriving on the custom base URL. That run used a
`/login` token; the first hub run is the proof for a `setup-token` token.

## Topology

- **Home box**: the only machine with internet. Runs this relay and, for
  Codex, CLIProxyAPI.
- **Hub** (first offline machine): reaches the home box over the LAN and
  holds SSH sessions into each leaf.
- **Leaf** (any further offline machine): reaches only the hub. The hub's
  `tunnelctl` opens a loopback port on the leaf that lands on the relay.

## Home box

```sh
cd tools/claude-relay
cp .env.example .env
docker compose up -d
curl -sS -o /dev/null -w '%{http_code}\n' \
  -H 'anthropic-version: 2023-06-01' http://127.0.0.1:58380/v1/models
```

`401` from that curl is the success case: it proves the request reached
Anthropic through the relay and was refused only for lack of a credential.

Mint the client token here, where a browser is available:

```sh
claude setup-token
```

It prints a one-year subscription OAuth token once and stores nothing. Copy
it to the hub and leaf settings files below. It can only make model requests,
which is all the relay carries. Put it in `ANTHROPIC_AUTH_TOKEN`, not
`CLAUDE_CODE_OAUTH_TOKEN`: the `/model` picker validates a model with a
client that only reads the API-key and auth-token variables, so with the
OAuth-token variable it fails with "could not resolve authentication
method" (seen on 2.1.260). Model requests work with either.

Allow the hub, and only the hub, to reach the relay port. Same shape as the
existing CLIProxyAPI rule:

```powershell
New-NetFirewallRule `
  -DisplayName "Claude relay from hub" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalAddress HOME_IP `
  -LocalPort 58380 `
  -RemoteAddress HUB_IP `
  -Profile Private
```

## Hub

Put the base URL and the token in Claude Code's user settings, which the CLI
and the VS Code extension both read. Merge into any existing `env` block:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://HOME_IP:58380",
    "ANTHROPIC_AUTH_TOKEN": "sk-ant-oat01-..."
  },
  "skipWebFetchPreflight": true
}
```

Add `"ANTHROPIC_MODEL": "claude-fable-5-1"` to the `env` block to make Fable
the default; through a token the session otherwise starts on Sonnet.

The file is `~/.claude/settings.json` on Linux and macOS, or
`%USERPROFILE%\.claude\settings.json` on Windows. Start a new terminal, or
run **Developer: Reload Window** in VS Code, then verify:

```sh
claude -p "Reply with exactly the word OK"
```

`/status` inside a session should show the relay address on the
`Anthropic base URL` row.

## Leaf

On the hub, open one loopback port on the leaf that lands on the relay:

```sh
tunnelctl add claude-relay --ssh-host LEAF --listen 58380 --target HOME_IP:58380
tunnelctl test claude-relay
```

On the leaf, use the same settings block as the hub with the loopback
address:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:58380",
    "ANTHROPIC_AUTH_TOKEN": "sk-ant-oat01-..."
  },
  "skipWebFetchPreflight": true
}
```

The Claude extension's CLI process runs on the leaf under VS Code Remote, so
the leaf's settings file and loopback port are the ones that count. Each
further leaf is one more `tunnelctl add` and the same settings block.

## What changes, and what does not

- Nothing but Claude Code's model calls is routed. Codex, CLIProxyAPI, the
  existing tunnels, and every other process stay as they are. If a machine
  later gains restricted internet, nothing here interferes with it.
- `skipWebFetchPreflight` is needed because WebFetch's domain check calls
  Anthropic directly rather than the base URL. Fast mode and telemetry also
  call Anthropic directly; on an offline machine they fail quietly.
- Features that need a live claude.ai login are unavailable through a token:
  Remote Control, claude.ai connectors, `/schedule`.
- Fable through a setup-token is unresolved (parked 2026-09-04). The hub
  could not use Fable while Opus and Sonnet worked. Working hypothesis from
  the operator, not yet verified: a setup-token session does not carry the
  extra-usage entitlement that Fable requires, whereas a `/login` session
  does. What is verified: Fable works through this relay with a `/login`
  token, and the earlier "could not resolve authentication method" error was
  the picker-variable issue above, not a server refusal. Next probe when
  picked up again: read the status Anthropic returns in the relay log.
- The token expires after one year. Mint a new one on the home box and
  replace it in both settings files.
- Between hub and home box the token travels over plain HTTP on the LAN,
  the same exposure as the CLIProxyAPI client key. Keep the firewall rule
  scoped to the hub. TLS on the relay is a possible later upgrade.
- Never commit the token. It belongs only in the user-level settings file on
  each machine.
- To undo on a machine, delete the two `env` lines and the preflight setting
  and reload. Nothing else was changed.
