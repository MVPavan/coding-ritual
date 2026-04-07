# Claude-Codex Collaboration

This file is specific to using Codex from inside Claude Code.

## Model

Claude is the orchestrator.
Codex is the one-way external critic and reviewer.

Do not assume a reverse Claude second-opinion loop exists in Codex.

## Default Gates

Use Codex for `standard` and `deep` work when available:

- brainstorm: challenge framing, assumptions, and omitted constraints
- plan: pressure-test sequencing, risks, rollback, and verification
- final implementation review: review the working tree or branch before calling work complete

## Conditional Gates

Use Codex only when it adds real leverage:

- document review when the doc did not already get a Codex pass or the doc is unusually risky
- adoption when the adoption work is `standard` or `deep`
- debugging when one hypothesis already failed or the bug crosses boundaries
- TDD when the test strategy is disputed

## Where Not To Use It

- small work by default
- mechanical verification
- invariant checks
- every worker subtask
- every red-green cycle

## Operating Pattern

Use an artifact loop, not free-form model chatter:

1. Claude writes the artifact.
2. Codex critiques it.
3. Claude accepts, rejects, or defers points with reasons.
4. Claude produces the final artifact.

## Useful Command Patterns

- brainstorm or plan critique: `/codex:rescue --wait --fresh <structured critique request>`
- standard review: `/codex:review --wait`
- high-risk challenge review: `/codex:adversarial-review --wait "<focus area>"`

If Codex is unavailable, say so and continue with local review.
