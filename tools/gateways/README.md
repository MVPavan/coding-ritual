# Home-box gateways

Two small gateways on the home box, the only machine with internet, so that
Codex and Claude Code on offline machines can reach their providers. One
compose project, two independent containers, one script that acts on one
service at a time.

| Service | Container | Host port | What it is |
|---|---|---|---|
| `cpa` | `cpa` | 58317 | [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI), holding the Codex OAuth credential. Codex on the leaf talks to it. |
| `claude-relay` | `claude-relay` | 58380 | nginx relay that forwards Claude Code's model traffic to `api.anthropic.com` unchanged. Holds no credential. |

Both images are pinned in [`compose.yaml`](compose.yaml). A recreate never
changes the running version; upgrades are a deliberate step (see Operations).

The two paths are shaped alike on purpose: each client points its own base
URL at a port on the home box, and only that client's model traffic moves.
No `HTTPS_PROXY`, nothing else on any machine is affected, and no
`NO_PROXY` list is ever needed.

Claude Code deliberately does **not** go through CLIProxyAPI. Anthropic's
terms reserve subscription OAuth for Claude Code itself and prohibit tools
that hold or relay those tokens, so Claude uses the transparent relay with a
token that Claude Code minted. Running Claude Code on GPT models through
CLIProxyAPI is possible but not in use; see [`cpa/claudex/`](cpa/claudex/README.md).

## Topology

- **Home box** (`HOME_IP` on the LAN): runs both services. Only machine with
  internet.
- **Hub**: the first offline machine. Reaches the home box over the LAN and
  holds SSH sessions into each leaf. Runs no gateway and, today, no client;
  it exists to relay.
- **Leaf**: any further offline machine. Reaches only the hub. The hub's
  [`tunnelctl`](tunnelctl) opens loopback ports on the leaf that land on the
  home box's gateway ports. Codex and the Claude VS Code extension run here.

## Home box

```sh
cd tools/gateways
cp .env.example .env        # first time only
./gw.sh up                  # both services
./gw.sh verify              # both services
./gw.sh status
```

`verify` checks the CLIProxyAPI management API and Management Center, and
sends one unauthenticated request through the relay expecting Anthropic's
`401`, which proves the path end to end.

### Codex credential (CLIProxyAPI)

```sh
./gw.sh login codex
```

Device-code login; the credential lands in `cpa/auths/` and CLIProxyAPI
refreshes it on its own. `./gw.sh verify cpa` reports how many auth files are
registered. The Management Center at `http://HOME_IP:58317/management.html`
shows credential health; use the management password from `.env`.

### Claude credential (setup-token)

```sh
claude setup-token
```

Prints a one-year subscription token once and stores nothing. It goes into
the leaf's Claude Code settings (below). Nothing on the home box holds it.

### Firewall

Allow the hub, and only the hub, to reach the two gateway ports. One rule per
port, same shape:

```powershell
New-NetFirewallRule -DisplayName "CLIProxyAPI from hub" -Direction Inbound -Action Allow `
  -Protocol TCP -LocalAddress HOME_IP -LocalPort 58317 -RemoteAddress HUB_IP -Profile Private
New-NetFirewallRule -DisplayName "Claude relay from hub" -Direction Inbound -Action Allow `
  -Protocol TCP -LocalAddress HOME_IP -LocalPort 58380 -RemoteAddress HUB_IP -Profile Private
```

Compose publishes both ports on all host interfaces; the firewall is what
limits who can connect. Ports `8317`, `8085`, `54545`, `1455`, and `11451`
are not published.

## Hub

The hub holds one `tunnelctl` entry per gateway per leaf. Each opens a
loopback port on the leaf and forwards it, over the existing key-based SSH
session, to the home box:

```sh
tunnelctl add codex        --ssh-host LEAF --listen 18317 --target HOME_IP:58317
tunnelctl add claude-relay --ssh-host LEAF --listen 58380 --target HOME_IP:58380
tunnelctl test codex
tunnelctl test claude-relay
```

Each entry is a supervised systemd user service that restarts on its own and
survives logout. Another leaf is two more `add` lines. If the hub ever runs a
client itself, it points at `HOME_IP` directly instead of a loopback port.

## Leaf

### Codex

`~/.codex/config.toml`, as currently in use on the leaf:

```toml
model_provider = "cliproxyapi"
model = "gpt-5.6-sol"
model_reasoning_effort = "high"

[model_providers.cliproxyapi]
base_url = "http://127.0.0.1:18317/v1"
experimental_bearer_token = "sk-cpa-harness-local-1"   # the client key from cpa/config.yaml
name = "OpenAI"
wire_api = "responses"
requires_openai_auth = true
supports_websockets = true

[tui.model_availability_nux]
"gpt-5.5" = 2
"gpt-5.6-sol" = 4
```

`127.0.0.1:18317` is the loopback port the hub's `codex` tunnel opens. Any
model the proxy lists at `/v1/models` works as `model`.

### Claude Code and the Claude VS Code extension

`~/.claude/settings.json` (Linux and macOS) or
`%USERPROFILE%\.claude\settings.json` (Windows). Merge into any existing
`env` block:

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "http://127.0.0.1:58380",
    "ANTHROPIC_AUTH_TOKEN": "sk-ant-oat01-...",
    "ANTHROPIC_MODEL": "claude-fable-5-1"
  }
}
```

- `127.0.0.1:58380` is the loopback port the hub's `claude-relay` tunnel
  opens.
- The token goes in `ANTHROPIC_AUTH_TOKEN`, not `CLAUDE_CODE_OAUTH_TOKEN`.
  The `/model` picker validates a model with a client that only reads the
  API-key and auth-token variables; with the OAuth-token variable it fails
  with "could not resolve authentication method" (seen on 2.1.260). Model
  requests work with either.
- `ANTHROPIC_MODEL` sets the default; through a token the session otherwise
  starts on Sonnet. Fable through a setup-token is parked, see Known issues.
- The extension's CLI process runs on the leaf under VS Code Remote, so the
  leaf's file and loopback port are the ones that count.

Start a new terminal, or **Developer: Reload Window** in VS Code, then:

```sh
claude -p "Reply with exactly the word OK"
```

`/status` inside a session shows the relay address on the `Anthropic base
URL` row. If a repository was ever switched to CLIProxyAPI with
`claudex-vscode`, its `.claude/settings.local.json` outranks the user file;
run `claudex-vscode disable` there first.

## Operations

```sh
./gw.sh status
./gw.sh logs cpa                 # or claude-relay
./gw.sh restart claude-relay     # recreates one service, the other is untouched
./gw.sh verify cpa               # or claude-relay, or all
./gw.sh version                  # running CLIProxyAPI version
./gw.sh down all                 # the only command that touches both
```

### Upgrade CLIProxyAPI

```sh
# 1. pick a tag from https://hub.docker.com/r/eceasy/cli-proxy-api/tags
# 2. set CPA_IMAGE_TAG=vX.Y.Z in .env
./gw.sh pull cpa
./gw.sh restart cpa
./gw.sh version
./gw.sh verify cpa
```

The relay stays up throughout. Check the release notes between the two tags
for config changes first; the keys used in [`cpa/config.yaml`](cpa/config.yaml)
all exist as of v7.2.149. To upgrade the relay, change the nginx tag in
`compose.yaml` and `./gw.sh restart claude-relay`.

### Reading the relay log

`./gw.sh logs claude-relay` prints one line per request: method, path,
status, whether a bearer token was present (never its value), and the client
version. A refused model or a bad token shows up here as a 4xx from
Anthropic; a `502` with a `connect() failed` line above it is a transient
upstream refusal that Claude Code retries by itself.

## Known issues and notes

- **Fable through a setup-token** is unresolved (parked 2026-09-04). The leaf
  could not use Fable while Opus and Sonnet worked. Operator's working
  hypothesis, not yet verified: a setup-token session does not carry the
  extra-usage entitlement Fable requires, whereas a `/login` session does.
  Verified: Fable works through the relay with a `/login` token, and the
  earlier "could not resolve authentication method" error was the variable
  issue above, not a server refusal. Next probe: the status in the relay log.
- **Token lifetimes.** CLIProxyAPI refreshes the Codex credential itself. The
  Claude setup-token lasts one year; mint a new one on the home box and
  replace it on the leaf.
- **Side calls.** WebFetch's domain safety check, fast-mode detection, and
  telemetry call Anthropic directly rather than the base URL, so on an
  offline leaf they fail quietly. Features needing a live claude.ai login
  (Remote Control, claude.ai connectors, `/schedule`) are unavailable through
  a token.
- **Transport.** Between hub and home box both client keys travel over plain
  HTTP on the LAN. The firewall scope to the hub is what protects them; TLS on
  the gateways is a possible later upgrade.
- **Secrets.** `.env`, `cpa/auths/`, `cpa/logs/`, and `cpa/plugins/` are
  ignored. Never commit the Claude token or the Codex auth file.
- **Claude via CLIProxyAPI** is intentionally not configured. `./gw.sh login
  claude` still exists for experiments; Anthropic's terms are the reason it
  is not the path, see the top of this file.
