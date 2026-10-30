# T3 Code

T3 Code has its own orchestrator. Inside T3 Code, delegate through its `t3-code`
tools (`orchestrator_capabilities`, `delegate_task` and their companions) and
follow their own descriptions and server instructions: they own launching,
tracking, follow-up rounds and results. Add no process of your own around them.

This skill supplies only what T3 cannot know:

- **Target:** the role's `model` and `options` (T3's own option IDs), passed
  as written, with the provider T3's catalog lists for that model.
- **Brief:** the role contract and the task.

**Model list:** T3's live catalog through `orchestrator_capabilities`; its own
description says how to find models its short list omits and which targets
`delegate_task` accepts. No local copy is kept.

**Read-only roles:** T3 has no read-only switch, and its documentation says a
narrower runtime mode is not one; the brief is the only control.

**What ran:** the task result names the provider, model and options.
