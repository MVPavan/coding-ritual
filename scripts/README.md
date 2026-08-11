# claudex-rc — remote-control session manager

`claudex-rc.sh` keeps **Claude** and **Codex** remote-control sessions running on this
machine as systemd **user** services, so you can drive them from claude.ai/code, the
Claude mobile app, or the Codex app without leaving a terminal open.

- **Claude** — one session per project, named `<project>-rc`
  (systemd template `claude-rc@<project>.service`).
- **Codex** — ONE global app-server daemon for all projects (`codex-rc.service`).

`setup-claudex-rc.sh` is a thin installer shim that calls `claudex-rc.sh setup`.

## How it works

```text
~/.config/claude-rc/<project>.env      source of truth: PROJECT_DIR + RC_NAME per project
~/.config/systemd/user/                claude-rc@.service · codex-rc.service · claudex-rc-heal.{service,timer}
~/.claude/projects/<slug>/             per-project state, incl. bridge-pointer.json (cached env + session)
```

Each Claude unit runs `cd $PROJECT_DIR && claude remote-control --name $RC_NAME`
with `Type=simple` + `Restart=always`. Codex runs bare `codex remote-control` from
`$HOME` (it runs in the foreground, hence the same unit shape).

Survives crashes, logout, and reboot via `Restart=always`, `loginctl enable-linger`,
and a Windows logon task (WSL) that boots the distro at logon.

**The bridge model.** A running bridge registers an *environment* with the server and
pre-creates one session, so you have somewhere to type. `bridge-pointer.json` caches
that `environmentId` + `sessionId`. On restart the bridge tries to re-attach them —
which is why a normal restart keeps your session instead of minting a new one.

## Everyday commands

Run from the repo root (or use an absolute path):

| Command | What it does |
| --- | --- |
| `scripts/claudex-rc.sh setup` | First-time install: all default projects + Codex + watchdog. Idempotent — never restarts a running session. |
| `scripts/claudex-rc.sh status` | Table of every managed session: state, restart count, project dir. **Start here.** |
| `scripts/claudex-rc.sh list` | List configured projects. |
| `scripts/claudex-rc.sh logs <name\|codex> [-f]` | Last 100 journal lines, or follow. |
| `scripts/claudex-rc.sh pair <name\|codex>` | Print the connect URL (Codex: prints the machine-name hint instead). |
| `scripts/claudex-rc.sh add <path>` | Add and start ONE project. |
| `scripts/claudex-rc.sh remove <name\|path\|codex>` | Stop, disable and forget one session. |
| `scripts/claudex-rc.sh restart <name\|codex\|all>` | Restart, keeping the cached env/session. |
| `scripts/claudex-rc.sh reset <name\|path\|all>` | **Recovery:** delete the bridge pointer + restart → fresh env and a brand-new session. |
| `scripts/claudex-rc.sh heal` | Watchdog pass (the timer runs this every 15 min). |
| `scripts/claudex-rc.sh help` | Usage summary. |

`<name>` accepts the project name, `<name>-rc`, or the project path.

### Start / stop

`setup`, `add`, `restart` and `reset` all start things. To stop, use systemd directly —
there is deliberately no `stop` subcommand, because stopping is rare and should be explicit:

```bash
systemctl --user stop claude-rc@bodha.service        # one project
systemctl --user stop claude-rc@{bodha,coding-ritual,multibaggers,orchestrators}.service
systemctl --user start claude-rc@bodha.service       # bring it back
```

A manual `stop` is **not** auto-revived: `Restart=always` only catches crashes, and
`heal` skips inactive units. But the unit stays *enabled*, so it returns after a reboot —
use `systemctl --user disable --now <unit>` to keep it down permanently, or `remove`
to forget it entirely.

Stopping a Claude session prints *"Environment preserved"* — the env survives, and a
restart re-attaches it (see the lifecycle below for the time limit).

## Session lifecycle (verified on CLI 2.1.207, 2026-07-18)

| Action | Result |
| --- | --- |
| Plain restart (short downtime) | **Re-attaches the same env and session.** No new session in the web UI. |
| Long downtime (~45 min+) | The server expires the session. On restart, revival fails — see *Recovery* below. |
| SIGKILL / crash | Nothing lost; the session resumes on restart. |
| `reset` (pointer deleted) | Fresh env + brand-new session. **The old web-UI session is orphaned** — this is the only action that causes session churn. |
| Old/orphaned session | Still resumable: `claude remote-control --session-id session_01…` from the project dir (id is in the claude.ai/code URL). |

**Never put `--continue` in the systemd unit.** It silently downgrades the bridge from
32-session server mode to single-session mode, and hard-errors (crash-looping under
`Restart=always`) whenever the pointer is missing. Bare invocation is correct.

Local transcripts are independent of all this — they live in
`~/.claude/projects/<slug>/*.jsonl` and are always resumable with `claude --resume`.

## The heal watchdog

`claudex-rc-heal.timer` runs `claudex-rc.sh heal` every 15 minutes. For each *active*
Claude unit that has been up longer than the grace period, it reads a 15-minute window
of the journal (the TUI re-renders its live state ~1×/sec, so a recent window reflects
current state) and:

- sees `Connected`/`Ready` → **healthy, skip**
- else sees ≥ `HEAL_TROUBLE_MIN` (default 3) sustained `Poll failed … timeout of Nms exceeded`
  lines → **wedged: plain `systemctl restart`** (env preserved, session re-attached)
- else (quiet, or only benign reconnect blips) → **leave alone**

It is deliberately **restart-only and never clears the bridge pointer**, because clearing
it orphans web-UI sessions. The destructive un-burn stays manual (`reset`).

Tuning knobs (env vars, mainly for testing): `HEAL_THRESHOLD_SECS` (default 900),
`HEAL_TROUBLE_MIN` (default 3).

```bash
systemctl --user list-timers claudex-rc-heal.timer   # is it armed?
journalctl --user -u claudex-rc-heal.service -n 50   # what has it done?
systemctl --user disable --now claudex-rc-heal.timer # turn it off for good
```

## Troubleshooting

**Always start with `status`, then `logs <name>`.** The TUI hides most real errors — for
anything that isn't obvious, run a bridge by hand with a debug file:

```bash
systemctl --user stop claude-rc@<project>.service
cd <project-dir> && claude remote-control --name <project>-rc --debug-file /tmp/rc.log
# reproduce, Ctrl-C, then:
grep -iE 'error|fail|status [0-9]{3}' /tmp/rc.log
systemctl --user start claude-rc@<project>.service   # don't forget to restore it
```

### Sessions visible in the app, but messages do nothing

The classic failure, seen twice (2026-07-18 and 2026-07-25). The TUI shows
`·✔︎· Ready` with **`Capacity: 0/32`**, and the journal has one
`Session failed: … cse_…` line right after startup.

**Cause:** the cached session died server-side (long downtime, or a boot-time auth race
where systemd starts the bridge before credentials are ready). On startup the bridge
tries to revive it, the server refuses, and **the bridge never falls back to creating a
fresh session** — so it sits there connected but sessionless forever. The dead entries
still render in the web UI, which is why messages appear to vanish.

Error strings seen: `ReconnectSession … 400: Session not found`,
`CCRClient: Epoch mismatch (409)`, `RemoteIO: transport closed permanently (code 401)`.

**Fix:** `scripts/claudex-rc.sh reset <name>` (or `reset all`) — clears the pointer so a
fresh session is pre-created. Gentler variant, if you want to try keeping the env:
stop the unit, remove **only** the `sessionId` key from
`~/.claude/projects/<slug>/bridge-pointer.json`, and start it again.

**Expect this after every long outage or reboot** — the bridge writes the current
`sessionId` back into the pointer whenever a session is created, so the trap re-arms
itself. The 15-minute watchdog does **not** catch it: a sessionless bridge reports
`Ready`, which heal reads as healthy.

### One project has no session while the others work

If a single project sits at `Ready · 0/32` with **no** `Session failed` line, the server
is refusing to create sessions for it. Only visible with `--debug-file`:

```text
Session creation failed with status 400:
GitHub repository access check failed — re-authorize GitHub in settings
```

This is server-side and unfixable from this machine. Grant the Claude GitHub App access
to that repo (github.com → Settings → Applications → Claude → Configure → Repository
access), or re-authorize GitHub in claude.ai settings. Seen on `multibaggers`.

### Other known issues

- **`Failed to connect to bus`** — the per-user systemd/D-Bus session did not initialize
  (a WSL race can spawn two `systemd --user` managers). Fix: `wsl --shutdown` in
  PowerShell, reopen WSL. `claudex-rc.sh` detects this and prints the remediation.
- **Untrusted workspace** — `claude remote-control` refuses to start in a project whose
  trust dialog was never accepted (common after renaming a folder, which orphans trust
  under the old path). Fix: `cd <dir> && claude`, accept the dialog once.
- **Network outage > ~10 min** — the session times out and the process exits;
  `Restart=always` brings it back. The 15-min watchdog interval is deliberately longer
  than this so normal outages self-recover first.
- **Codex is unaffected by all Claude session issues** — different transport, no bridge
  pointer, no heal logic. If Claude is broken and Codex is fine, the problem is
  Claude-side.

## Adding or changing projects

The default project list lives in the `DEFAULT_PROJECTS` array near the top of
`claudex-rc.sh` and is only consulted by `setup`. For one-offs, prefer
`claudex-rc.sh add <path>`. `status` warns about any running session that has no env
file ("orphan") and tells you how to remove it.
