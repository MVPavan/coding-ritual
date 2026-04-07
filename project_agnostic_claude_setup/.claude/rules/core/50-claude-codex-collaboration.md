# Claude and Codex Collaboration

This rule applies only when the active environment is Claude Code and the Codex plugin is available.

- `small` tasks skip Codex by default.
- `standard` and `deep` brainstorms should get a Codex critique before the framing is finalized.
- `standard` and `deep` plans should get a Codex critique before execution starts.
- `standard` and `deep` implementation work should get Codex review before completion.

Suggested command patterns:

- brainstorm or plan critique: `/codex:rescue --wait --fresh <structured critique request>`
- standard review: `/codex:review --wait`
- adversarial review for risky changes: `/codex:adversarial-review --wait "<focus area>"`

If Codex is unavailable, say so explicitly and continue with local review.
Do not assume a reverse Claude second-opinion loop exists in Codex.
