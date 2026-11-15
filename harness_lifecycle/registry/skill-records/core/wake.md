---
skill: wake
domain: core
stage: X
substage: Continuity
secondary: []
family: handoff
aliases: []
status: active
---
# wake

Use when a calling playbook names it, or when asked to set one timer to close a run at a deadline: holds a run's limits and closed state, and says what the timer survives. Driving work to a condition is `autonomous-run`; waiting on a command, or a person typing the platform's own loop or goal command, needs none of this.

**Boundary:** Holds a run's bounds and its one closing timer; what a return does is its caller's, a run's log is `decision-trail`, and a run the engine owns uses the engine's monitor.

<!-- registry:generated traits -->
- `run-card-limits`: Hold a run's deadline, attempts, closed state and checkpoint in a card at a fresh path under a unique run id, refusing without them.
- `one-consuming-admit`: Count work once, by the caller, immediately before the unit; every other query changes nothing, and only exit 0 authorises work.
- `one-closing-timer`: Set at most one one-shot timer, at or after the deadline and only for a stated unattended run, and record the time the surface says it fires.
- `timer-positive-evidence`: Report a timer set only on the surface's named evidence; a listed tool alone is not evidence and uncertain means unavailable.
- `timer-identity-check`: On a timer fire ask the card only whether this run is open; a closed or other run does nothing, and everything else is the caller's closing step.
- `timer-close-cancels`: Close the card and cancel the timer on every exit, naming a cancel that failed.
- `woken-run-limits`: While a card is open: no push, publish, merge, message or history rewrite, no deleting what this run did not create, no costly opt-in the request does not name, and a missing answer takes the unit's no-answer exit without skipping its core.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
No adopted lineage recorded.
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-04` **add** (2026-11-04-batch-4:001): New skill, owner rulings of 2026-11-04 amending ruling 12: a card holding one run's limits, attempts, closed state and checkpoint for any run with a stated lim…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
