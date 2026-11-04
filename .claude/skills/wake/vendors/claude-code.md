# Timer on Claude Code

Read on 2026-11-03; no real timer was created. Tags: [D] official documentation, [T] the
tool's own description here, [H] the installed CLI's help, [O] observed here, [I] inference,
[?] not verified. Under T3's host use `t3.md`. Source:
<https://code.claude.com/docs/en/scheduled-tasks>.

- **Evidence before setting:** the parent process line (`ps -o args= -p $PPID`) is `claude` with
  no `-p`, `--print`, `--output-format` or `--input-format` [O][I]. This is undocumented, so
  anything else is uncertain, and uncertain means `unavailable`.
- **Set:** `CronCreate`, one-shot, local time, one-minute grain. Use the first minute at or
  after the deadline that is not `:00` or `:30`, since those can run up to 90 seconds early [D]:
  a 06:00 deadline fires at 06:01. If busy, it waits for the turn to end [D].
- **Cancel:** `CronDelete`.
- **Survives:** it fires only while the session runs and is idle [D]. Closing the terminal stops
  it. Backgrounding carries the loop command's tasks over [D], plain cron tasks [?]. `--resume` does not
  restore a passed one-shot [D].
- **Gaps:** `CLAUDE_CODE_DISABLE_CRON` removes it [D]. `ScheduleWakeup` is for a person's loop command
  [T], so it is not used.
- **One prompt or SDK:** this fails the evidence above: tools can be listed there and never get
  a turn, and the timer would end with the run [I]. `unavailable`. `--max-budget-usd` exists
  only here [H].
