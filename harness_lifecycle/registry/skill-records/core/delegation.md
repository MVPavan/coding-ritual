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

**Boundary:** Hands one piece of work to another agent or model: role, roster model, vendor, brief, dispatch and the check of what ran; whether to delegate is the calling workflow's choice, councils are model-council and perspective-council, and choosing a unit is mvp-mode.

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
- `background-dispatch-for-dialogue`: Run subagents in the background so the coordinator stays in live dialogue with the user.
- `brief-names-done-evidence`: A brief names what will show the work is finished, and a unit with nothing to name is scoped further or raised with the owner before dispatch.
- `read-worker-output`: Open the diff or artifact a worker produced and hold it to the evidence its brief named, instead of relying on its summary.
- `stalled-worker-by-output`: Stop or replace a worker that stalls or loops, judging it by what it has produced rather than its status text.
- `retry-by-cause`: Retry a failed worker according to why it failed, with a narrower unit, the same brief or another model, and after two retries drop the unit and plan around it.
- `fresh-context-subagent`: Start every subagent in a fresh context window rather than as a copy of the caller's conversation. (Delivers sealed rows 2026-11-09-pocock-4ae2317:156, :158, :160, :163, :165, :167, :170 and :179: a fresh window for each new worker, and a fork when the calling workflow asks for one, where the definition says every subagent; T5.)
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/in-progress/chief-of-staff#background-dispatch-for-dialogue** `skills/in-progress/chief-of-staff/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/code-review#fresh-context-subagent** `skills/engineering/code-review/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/engineering/codebase-design#fresh-context-subagent** `skills/engineering/codebase-design/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/engineering/implement-spec#fresh-context-subagent** `skills/engineering/implement-spec/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#fresh-context-subagent** `skills/engineering/improve-codebase-architecture/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/engineering/research#fresh-context-subagent** `skills/engineering/research/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/engineering/wayfinder#fresh-context-subagent** `skills/engineering/wayfinder/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/in-progress/chief-of-staff#fresh-context-subagent** `skills/in-progress/chief-of-staff/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/productivity/grilling#fresh-context-subagent** `skills/productivity/grilling/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-12` **adopt** (2026-11-12-pocock-4ae2317-delivery:022): Completes pending 2026-11-09-pocock-4ae2317:179: fresh-context-subagent is written at .claude/skills/delegation/SKILL.md:51-54, .repo-context/unit-kinds.md:317…
- `2026-11-12` **adopt** (2026-11-12-pocock-4ae2317-delivery:021): Completes pending 2026-11-09-pocock-4ae2317:170: fresh-context-subagent is written at .claude/skills/delegation/SKILL.md:51-54, .repo-context/unit-kinds.md:317…
- `2026-11-12` **adopt** (2026-11-12-pocock-4ae2317-delivery:020): Completes pending 2026-11-09-pocock-4ae2317:167: fresh-context-subagent is written at .claude/skills/delegation/SKILL.md:51-54, .repo-context/unit-kinds.md:317…
- `2026-11-12` **adopt** (2026-11-12-pocock-4ae2317-delivery:019): Completes pending 2026-11-09-pocock-4ae2317:165: fresh-context-subagent is written at .claude/skills/delegation/SKILL.md:51-54, .repo-context/unit-kinds.md:317…
- `2026-11-12` **adopt** (2026-11-12-pocock-4ae2317-delivery:018): Completes pending 2026-11-09-pocock-4ae2317:163: fresh-context-subagent is written at .claude/skills/delegation/SKILL.md:51-54, .repo-context/unit-kinds.md:317…
- `2026-11-12` **adopt** (2026-11-12-pocock-4ae2317-delivery:017): Completes pending 2026-11-09-pocock-4ae2317:160: fresh-context-subagent is written at .claude/skills/delegation/SKILL.md:51-54, .repo-context/unit-kinds.md:317…
- `2026-11-12` **adopt** (2026-11-12-pocock-4ae2317-delivery:016): Completes pending 2026-11-09-pocock-4ae2317:158: fresh-context-subagent is written at .claude/skills/delegation/SKILL.md:51-54, .repo-context/unit-kinds.md:317…
- `2026-11-12` **adopt** (2026-11-12-pocock-4ae2317-delivery:015): Completes pending 2026-11-09-pocock-4ae2317:156: fresh-context-subagent is written at .claude/skills/delegation/SKILL.md:51-54, .repo-context/unit-kinds.md:317…
- `2026-11-12` **update** (2026-11-12-pocock-4ae2317-delivery:014): Bead cr-r2pa.2.19, plan 53: delivers the eight pending fresh-context-subagent adopts of round 2026-11-09-pocock-4ae2317 (:156 :158 :160 :163 :165 :167 :170 :17…
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:179) *(superseded)*: Owner ruling 2026-11-09: Prevents: A worker that inherits the coordinator's whole conversation, so its result rests on context the brief never stated and a rev…
- `2026-11-09` **adopt-merged** (2026-11-09-pocock-4ae2317:178): Checkpoint at 4ae2317 for the owner's trait rulings: 3 adopt, 4 defer, 2 reject.
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:170) *(superseded)*: Owner ruling 2026-11-09: Prevents: A worker that inherits the coordinator's whole conversation, so its result rests on context the brief never stated and a rev…
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:167) *(superseded)*: Owner ruling 2026-11-09: Prevents: A worker that inherits the coordinator's whole conversation, so its result rests on context the brief never stated and a rev…
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:165) *(superseded)*: Owner ruling 2026-11-09: Prevents: A worker that inherits the coordinator's whole conversation, so its result rests on context the brief never stated and a rev…
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:163) *(superseded)*: Owner ruling 2026-11-09: Prevents: A worker that inherits the coordinator's whole conversation, so its result rests on context the brief never stated and a rev…
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:160) *(superseded)*: Owner ruling 2026-11-09: Prevents: A worker that inherits the coordinator's whole conversation, so its result rests on context the brief never stated and a rev…
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:158) *(superseded)*: Owner ruling 2026-11-09: Prevents: A worker that inherits the coordinator's whole conversation, so its result rests on context the brief never stated and a rev…
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:156) *(superseded)*: Owner ruling 2026-11-09: Prevents: A worker that inherits the coordinator's whole conversation, so its result rests on context the brief never stated and a rev…
- `2026-11-05` **update** (2026-11-05-delegation-principles:001): Owner ruling of 2026-11-05. A search of past sessions found the router's principle lines rarely led to a read, even where a principle's situation held, and mos…
- `2026-11-04` **update** (2026-11-04-pocock-pass:038): Owner ruling 17 (playbook map 2.17, 7.2): Orchestrate stays deferred and delegation grows by three rules from its Supervision section. A brief names what will …
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:009): Completes pending 2026-10-30-mattpocock_skills-5beb35b:421: background-dispatch-for-dialogue is written at .claude/skills/delegation/SKILL.md:49-51, in the sea…
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:580) *(superseded)*: Checkpoint at 5beb35b for the owner's trait rulings: 1 adopt, 23 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:421) *(superseded)*: AGENTS.md has the lead continue independent work while waiting (AGENTS.md:9-10) but delegation never says to dispatch in the background; CF-09 asks for exactly…
- `2026-10-30` **add** (2026-10-30-delegation:001): Owner 2026-10-30: one vendor-neutral skill for every handoff to another agent or model; roles in roles/, vendors in vendors/ (T3, Codex CLI, Claude CLI).
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-06-upstream-mattpocock_skills-4ae2317.md](../../reviews/2026-11-06-upstream-mattpocock_skills-4ae2317.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `background-dispatch-for-dialogue`:
  - `mattpocock_skills:skill:skills/in-progress/chief-of-staff#background-dispatch-for-dialogue` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `fresh-context-subagent`:
  - `mattpocock_skills:skill:skills/engineering/code-review#fresh-context-subagent` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
  - `mattpocock_skills:skill:skills/engineering/codebase-design#fresh-context-subagent` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
  - `mattpocock_skills:skill:skills/engineering/implement-spec#fresh-context-subagent` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
  - `mattpocock_skills:skill:skills/engineering/improve-codebase-architecture#fresh-context-subagent` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
  - `mattpocock_skills:skill:skills/engineering/research#fresh-context-subagent` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
  - `mattpocock_skills:skill:skills/engineering/wayfinder#fresh-context-subagent` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
  - `mattpocock_skills:skill:skills/in-progress/chief-of-staff#fresh-context-subagent` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
  - `mattpocock_skills:skill:skills/productivity/grilling#fresh-context-subagent` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
