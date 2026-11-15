# Timer on Codex

Read on 2026-11-03; no real timer was created. Tags: [D] official documentation, [H] the
installed CLI's help, [?] not verified. Source:
<https://learn.chatgpt.com/docs/automations?surface=app>.

- **Codex CLI:** `unavailable`. "Codex CLI doesn't provide the Scheduled management interface" [D].
- **Codex app:** `unavailable` until verified: no model-side tool is verified [?]. It has
  in-chat scheduled tasks, and "Keep the computer on and the app running" [D]. Bug reports, not
  documentation: <https://github.com/openai/codex/issues/50777>,
  <https://github.com/openai/codex/issues/43252>.
- **Goals are not this timer.** The model can start and complete one [D], but pausing, clearing and
  budget changes are "controlled by the user or the system" [D], so a run at its limit cannot
  end its own goal. A person may type one. Source:
  <https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex>.
