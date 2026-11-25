---
name: wake
description: "Use when a calling playbook names it, or when asked to set one timer to close a run at a deadline: holds a run's limits and closed state, and says what the timer survives. Driving work to a condition is `autonomous-run`; waiting on a command, or a person typing the platform's own loop or goal command, needs none of this."
---

# Wake

Deliverable: one run's bounds and its closing timer, set or honestly not. One whole call stays
open through the caller's closeout. A timer fire always means closing; every other decision
about a return is the caller's. With no stated limit and no unattended words there is no card.

## Open

1. **Open the card** with the caller's limits, at a fresh path:
   `run=<slug>-$(date -u +%Y%m%dT%H%M%SZ)`, card `<dir>/<run>.json`, where `<dir>` is the
   caller's artifact directory or, with none, `$(git rev-parse --git-common-dir)/wake/`.
   `scripts/run_card.py open <card> --run <run> --deadline <ISO with zone> --max-attempts <n>`;
   `--allow-long` only when the request's own words ask for over 24 hours. A caller with a
   checkpoint writes it now, before any timer.
2. **Stated unattended only: set one timer.** Read only this surface's file:
   `vendors/t3.md`, `vendors/claude-code.md` or `vendors/codex.md`; any other surface is
   `unavailable`. Set it only on the positive evidence that file names. A listed tool alone
   is not evidence, and uncertain means `unavailable`. It is one-shot, never recurring.
   Record the time the surface says it will fire: `run_card.py timer <card> --run <run>
   --handle <h> --evidence <text> --fires-at <ISO>`. A refusal here: cancel it, `unavailable`.
3. **The timer's prompt carries** the run id, the card path, the caller's closing step with the
   absolute path of any reference it names, the limits below, and: "This is a closing return. Start
   no new work." So it survives a compaction.

| Open returns | Meaning |
|---|---|
| `card only` | a stated limit, attended: no timer |
| `timer: <handle>, fires <actual time>, survives: <surface's words>` | stated unattended, evidence recorded; the caller's reply repeats what it survives |
| `unavailable: <reason>` | stated unattended, card open, no timer here; the run works in its turn and its reply says no timer was set |
| `refused: <reason>` | the card refused: no limits, a deadline past, over 24 hours, an existing path; the caller's Not started, refused |
| `owed to parent` | inside a delegated task: nothing set |

## While it is open

The caller runs these. Only exit 0 authorises work. Exit 2 is refused or damaged with nothing
changed, 3 a limit or under one second left, 4 closed or another run, 5 an unexpected failure. On
2 or 5 start nothing and take the caller's stopped exit, naming it.

| `run_card.py <cmd> <card> --run <run>` | Does | Exits |
|---|---|---|
| `check` | changes nothing: open and within limits? prints seconds left | 0, 3, 4 |
| `admit` | the one consuming call, by the caller, immediately before one unit of work; prints seconds left | 0, 3, 4 |
| `note [--phase P] [--set k=v] [--unset k] [--require a,b]` | merges; refuses if a required field is then missing | 0, 2, 4 |
| `close --reason R` | stops admission; idempotent; prints the timer to cancel | 0, 2, 4 |
| `show` (no `--run`) | prints the card | 0, 2 |

**On a timer fire, first** `check`. Exit 4: nothing, one line. Exit 0 or 3: hand to the caller's
closing step, which never admits. This skill owns nothing beyond that.

**Limits while a card is open:** no push, publish, deploy, merge, message, amend or history
rewrite. No deleting anything this run did not create, unless the request names it; removing
this run's own verified disposable edits (undo, instrumentation) is allowed. No costly opt-in
the request does not name: a council, `interrogate`, Eval or any real session. A request naming
one of these acts authorises that act; "run overnight" alone authorises none. Nobody replies in
a stated unattended run, so where a called unit needs an answer, take that unit's stated
no-answer exit. With none, stop that branch and whatever depends on it, and report it
unfinished. This never skips a unit's core and never reports completion.

**Close, on every exit:** `close`, then cancel the handle it prints. Report `closed: <attempts>,
<elapsed>, cancelled`, or `could not cancel <handle>`, which the reply names; the card still ignores that timer.
