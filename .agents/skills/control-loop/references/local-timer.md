# Local timer: templates

Read at step 7 of `control-loop`, only when the owner asks for a schedule. The
timer runs the loop's run script on the owner's machine at the owner's
cadence; write it with the owner's values, install it only on their word, and
reply with how to stop it. Choose the form the machine has: a user timer
under a service manager when one runs, otherwise a cron entry.

**User timer** (two unit files in the service manager's per-user unit
directory):

```ini
# <loop>.service
[Unit]
Description=<loop> control loop: one run

[Service]
Type=oneshot
WorkingDirectory=<absolute path of the repository's main checkout>
ExecStart=<absolute path of the run script>
```

```ini
# <loop>.timer
[Unit]
Description=<loop> control loop schedule

[Timer]
OnCalendar=<the owner's cadence, for example Mon..Fri 09:00>
Persistent=true

[Install]
WantedBy=timers.target
```

Install: reload the user units, then enable and start the timer. Check its
next fire with the timer list. Stop: disable the timer (`--now`). A user timer
runs only while the user's service manager does; on a machine that starts it
at login only, say so in the reply.

**Cron entry** (the user's crontab):

```cron
# <loop> control loop, cadence set by the owner on <date>
<minute> <hour> <day> <month> <weekday> cd <main checkout> && <run script> >> <log path> 2>&1
```

Stop: remove the line.

The run script holds its own lock and its one-open-pull-request bound, so a
timer firing while a run is still going, or while the loop's pull request
waits for review, does no work. The headless agent must already be logged in
for the user the timer runs as; the timer stores no credential. The log (the
cron file, or the service manager's journal) holds only what the run script
prints: it prints no remote URL, and git's own push and fetch messages leave a
URL's credential out, so keep it that way: never add a command that echoes a
remote URL or a token to the script or the timer.
