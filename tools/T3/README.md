# T3 Code on this machine

How T3 Code is wired on `$T3_HOST_NAME` (Windows desktop app + WSL backend), how the
phone reaches it through T3 Connect, and how to recover when the phone shows
`Connection failed: Relay rejected the environment connection request
(endpoint_provider_not_managed)`.

Last verified 2026-10-04 on `t3 v0.0.46-nightly.20261004.2644`. T3 Code changes
fast; re-check the [issues](#upstream-issues) before trusting an old workaround.

Machine-specific values (`$T3_HOST_NAME`, `$T3_ENV_ID_WSL`, …) live in
`tools/T3/.env`, which is not committed; `.env.example` lists them. Load them
before running the commands below: `set -a; . tools/T3/.env; set +a`.

## How it works

```
 Windows                              WSL (Ubuntu)
┌────────────────────┐   starts via  ┌──────────────────────────────────────┐
│ T3 Code desktop app│── wsl.exe ───▶│ t3 backend  (port 3773)              │
│ (Electron, UI only)│◀── 172.25.x ──│  ├─ projects, threads, statev2.sqlite│
└────────────────────┘    :3773      │  ├─ claude / codex / opencode CLIs   │
                                     │  │    (agent sessions; they call     │
                                     │  │     back via MCP 127.0.0.1:3773)  │
 Phone                               │  └─ cloudflared (managed tunnel)     │
┌────────────┐   relay.t3.codes      └───────────────▲──────────────────────┘
│ T3 mobile  │──▶ (auth + routing) ──▶ Cloudflare ────┘
└────────────┘
```

- **One backend: WSL.** It owns projects, threads and agent runs. The desktop
  app and the phone are both clients of it.
- **Desktop app** is UI only. `desktop-settings.json` has `wslOnly: true`, so it
  starts no Windows backend; it launches the WSL backend through `wsl.exe` and
  talks to it on the distro's `172.x` address.
- **Phone** never reaches the PC directly. It signs in to `relay.t3.codes`,
  which checks that it may reach environment `$T3_ENV_ID_WSL` and routes it
  through the Cloudflare tunnel that `cloudflared` holds open from WSL.
- **Agent sessions** (Claude Code, Codex, …) are child processes of the
  backend. They use its MCP endpoint for orchestration, so restarting the
  desktop app ends them.

### Closing the desktop app

Stops everything. The backend's parent is the desktop app's `wsl.exe`
launcher and no background service is installed, so closing the app stops the
backend, running agents and `cloudflared`. The phone then shows the
environment offline. Data stays on disk; reopening the app brings it all back.

`t3 service install` would run the backend under systemd in WSL so the phone
works without the desktop app. Not enabled: the desktop app also starts its
own backend on port 3773, and how the two coexist under WSL is unverified.

### Two environments, one in use

| Environment ID | Where | Data dir | Status |
|---|---|---|---|
| `$T3_ENV_ID_WSL` | WSL | `~/.t3/userdata` | In use. Managed tunnel. Terminal icon on the phone. |
| `$T3_ENV_ID_WINDOWS` | Windows native | `$T3_WIN_USERDATA` | Retired when the desktop switched to WSL-only. Was registered publish-only; deregistered from T3 Connect on 2026-10-04. |

If a second entry ever reappears on the phone, check which ID it is before
touching anything.

## Recovery: `endpoint_provider_not_managed`

**What it means.** The relay only routes phone connections to links whose
endpoint kind is `cloudflare_tunnel` (managed). This error means the relay
holds the link as `manual` (publish-only) while the local machine may still
believe it is managed. The environment stays listed but cannot be reached.

**How it gets there.** Turning T3 Connect off in the desktop app while
"Publish agent activity" is on relinks as publish-only instead of unlinking.
Relinking also writes the relay record before six local secret files, with no
rollback if one fails. After that, the desktop toggle cannot repair it: it only
relinks when local state differs from the toggle.

**Never use the desktop T3 Connect toggle on this setup.** It reads "off" even
when the link is healthy, switching it on hits the WSL
`Invalid managed endpoint origin` bug, and switching it off breaks the link.

Run in the WSL shell as the normal user, no `sudo`:

```bash
# 1. Use the CLI bundled with the desktop build, not ~/.local/bin/t3
T3="$(ls -td ~/.t3/wsl-runtime/*/ | head -1)t3"
"$T3" --version                       # must match the desktop app version

# 2. Back up secrets (undo path)
cp -a ~/.t3/userdata/secrets ~/.t3/userdata/secrets.bak-$(date +%Y%m%d-%H%M%S)

# 3. Publishing off first, or unlink degrades to a publish-only relink
"$T3" connect publish --disable

# 4. True unlink; expect "Revoked the relay-side environment record."
"$T3" connect unlink

# 5. Relink managed (never --publish-only)
"$T3" connect link --headless
"$T3" connect status                  # expect: pending server startup
```

6. Quit the desktop app fully, including the tray icon, and start it again.
   The backend links itself over `127.0.0.1` within about 30 s, which avoids
   the WSL origin bug.
7. Verify and restore publishing:

   ```bash
   "$T3" connect status               # expect: Environment link: provisioned
   pgrep -a cloudflared               # expect: a running tunnel
   "$T3" connect publish              # re-enable push / Live Activities
   ```

8. Account menu → **T3 Connect**: the environment should say **Managed
   tunnel**. Deregister any other entry (it works even for offline
   environments). On the phone, remove stale entries under
   **Settings → Environments**.

If step 5 fails with "already linked to a different cloud account": close T3
Code, delete `~/.t3/userdata/secrets/cloud-linked-user-id.bin`, repeat from 5.
If status sticks at `pending server startup`, look in the backend log under
`~/.t3/userdata/logs` for `Failed to reconcile T3 Connect desired link on
startup` and report it on #5210.

Fallback that skips the relay entirely: the PC is on the tailnet
(`$TAILNET_IP`); run `"$T3" pair --tailscale` and scan the QR on a phone
running Tailscale.

## How this was diagnosed

Repeat these to check a similar problem from scratch.

| Question | Command / source | What it showed |
|---|---|---|
| Known bug? | `gh search issues "endpoint_provider_not_managed"`, `gh search code "endpoint_provider_not_managed"` | #6568, #11898, #11899; code in `infra/relay/src/environments/EnvironmentConnector.ts` (`resolveManagedEndpoint`) |
| Root cause and fix | `gh issue view <n> -R pingdotgg/t3code --comments` | Maintainer triage on #11898 / #11899; verified workaround |
| WSL-specific bug | Same, on #5210 (dup #11567) | Desktop toggle sends the link proof to the WSL IP; server only accepts loopback. CLI path works. |
| Official docs | `gh api repos/pingdotgg/t3code/contents/docs/user/remote-access.md -H "Accept: application/vnd.github.raw"` | `t3 connect` subcommands, troubleshooting table, Deregister |
| Local link state | `"$T3" connect status`, `"$T3" connect <sub> --help` | Saved state only, not a live check |
| Local vs relay drift | `ls ~/.t3/userdata/secrets` | `cloud-endpoint-runtime-config.bin` present ⇒ local thinks managed. Present while the phone gets `endpoint_provider_not_managed` ⇒ drift. |
| Is the tunnel up | `pgrep -a cloudflared` | Managed tunnel process |
| Which backend is live | `ps -o pid,ppid,etime,cmd -p $(pgrep -f "wsl-runtime.*t3 --bootstrap")`, `ss -ltnp \| grep 3773` | WSL backend, parent `/init` (desktop's `wsl.exe`), port 3773 |
| Background service | `"$T3" service status` | Not installed ⇒ backend lives and dies with the desktop app |
| How many environments | `cat ~/.t3/userdata/environment-id`; `cat "$T3_WIN_USERDATA_WSL/environment-id"`; `ls` both `secrets/` dirs | Two IDs. Windows one had a relay credential but no `cloud-endpoint-runtime-config.bin` ⇒ publish-only ⇒ the rejected phone entry |
| Desktop backend mode | `cat "$T3_WIN_USERDATA_WSL/desktop-settings.json"` | `wslBackendEnabled: true`, `wslOnly: true` |
| Windows backend alive | `tasklist.exe \| grep -i t3`, pid from `server-runtime.json` | Not running |

The T3 MCP tools (`orchestrator_capabilities`, `t3_environment_read`) give the
environment ID, label and server version from inside an agent session.

## Upstream issues

- [#6568](https://github.com/pingdotgg/t3code/issues/6568): discoverable but `endpoint_provider_not_managed` (umbrella)
- [#11898](https://github.com/pingdotgg/t3code/issues/11898): `applyCloudRelayConfig` not atomic, creates the drift
- [#11899](https://github.com/pingdotgg/t3code/issues/11899): Connections UI cannot detect or repair the drift
- [#6628](https://github.com/pingdotgg/t3code/issues/6628): toggle shows off after startup restore
- [#5210](https://github.com/pingdotgg/t3code/issues/5210): WSL `Invalid managed endpoint origin` (user commented as MVPavan)
- [remote-access.md](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md): official remote access docs

When these close, re-test whether the desktop toggle works on WSL and trim
this page.
