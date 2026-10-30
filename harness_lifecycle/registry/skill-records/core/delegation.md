---
skill: delegation
domain: core
stage: X
substage: Coordination
secondary: []
family: 
aliases: []
status: active
---
# delegation

Use when handing work to another agent or model (an explorer, implementer, reviewer or critic) on any vendor, to choose its model, brief it, dispatch it and check its result. Work you do yourself needs none of this.

**Boundary:** Hands one piece of work to another agent or model: role, roster model, vendor, brief, dispatch and the check of what ran; whether to delegate is the calling workflow's choice, councils are model-council and perspective-council, and choosing a skill is skill-router.

<!-- registry:generated traits -->
- `role-contracts`: Give each delegated role a fixed contract of access, duties and report shape, and carry it inside the brief because the worker may not load the delegating instructions.
- `no-onward-delegation`: A delegated worker does not hand its work on to further agents unless its brief allows it.
- `preserve-role-prompt`: Keep role behaviour in one role prompt independent of the runtime metadata applied around it at invocation.
- `owner-roster`: Take each role's vendor, model and settings from the owner's roster, let a model the owner names override it for one dispatch, and ask the owner when neither exists rather than choosing.
- `cross-family-review`: Have work reviewed by a model from a different family than its author's, and get the owner's explicit approval before a same-family review.
- `vendor-model-list`: Take the selectable models and efforts from each vendor's own source (its live catalog, or a list generated from its command or API), falling back to a reviewed, sourced seed only when no such source is reachable.
- `model-list-freshness`: Refuse a generated model list when the vendor fetch behind it is missing or older than the allowed age, timing it by the vendor's fetch rather than by when the list was written.
- `validate-selection`: Validate every selected spawn dimension deterministically before spawning, rejecting any value the catalog does not declare rather than substituting a nearby one. (Against each vendor's own list; a model or setting it does not list stops the dispatch.)
- `vendor-owned-dispatch`: Dispatch through the chosen vendor's own tools and follow their rules, adding no process around a vendor's own orchestrator.
- `capable-native-subagent`: Use the harness's own subagent tool only when it can run the chosen model with its settings.
- `effective-run-record`: Record the model and settings a vendor reports actually ran for a dispatch, marking any it does not report as requested-but-unverified.
- `enforced-read-only`: Keep a read-only role read-only with the vendor's enforced control, such as a sandbox or tool list, where one exists, and state when the brief is the only control.
- `session-resume-followup`: Send a follow-up to a worker by resuming its own session rather than starting a fresh one.
- `codex-direct`: Call the Codex CLI directly rather than through the retired adapter plugin.
- `closed-stdin`: Close standard input when running an agent CLI non-interactively so it cannot wait for input with no timeout.
- `result-error-check`: Judge an agent CLI run by its structured result's error flag, never by its exit code alone.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
No adopted lineage recorded.
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-10-30` **add** (2026-10-30-delegation:001): Owner 2026-10-30: one vendor-neutral skill for every handoff to another agent or model; roles in roles/, vendors in vendors/ (T3, Codex CLI, Claude CLI).
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
