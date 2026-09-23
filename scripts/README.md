# Codex remote control

One `codex remote-control` daemon serves every project on this machine. In the
Codex app, pick this machine, then the project. It runs as a systemd user unit:

```ini
# ~/.config/systemd/user/codex-rc.service
[Unit]
Description=Codex remote-control app-server (single instance, all projects)
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=/bin/bash -lc 'cd "$HOME" && exec codex remote-control'
Restart=always
RestartSec=15

[Install]
WantedBy=default.target
```

```bash
systemctl --user daemon-reload && systemctl --user enable --now codex-rc   # install
systemctl --user status codex-rc                                           # health
journalctl --user -u codex-rc -n 100                                       # logs
```

Bare `codex remote-control` runs in the foreground, so the unit is
`Type=simple` with `Restart=always`, not the daemonizing `start`/`stop` subcommands.

Claude Code has no per-machine equivalent. `claude remote-control` is bound to the
directory it starts in, so start it on demand (`/remote-control` in a session, or
`claude --remote-control`) instead of running always-on per-repo services.
