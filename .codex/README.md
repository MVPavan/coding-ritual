# .codex — the Codex view of this repo's harness

Shared skills live in `.agents/skills/`, where Codex discovers them directly;
`.claude/skills` is a link to that folder for Claude. Every skill carries
`agents/openai.yaml` with `policy.allow_implicit_invocation`, the Codex twin of
`disable-model-invocation`. Repository guidance lives in `.repo-context/`.
Under `.codex/`:

- `rules/default.rules` — native Codex command policy. Shared behavioral
  instructions live in `AGENTS.md`; conditional conventions live in `.repo-context/`.
- `agents/*.toml` — hand-maintained Codex twins of `.claude/agents/*.md`.
- `config.toml`, `hooks.json`, `hooks/` — Codex wiring and hook scripts (real;
  the Python generated-edit guard differs from the bash one by payload schema).

Delegation and independent critique follow `.repo-context/delegation.md`.
Distribution of this harness to other repos is the
`mvp-plugin` (`mvp-harness/plugins/mvp-plugin`) — published with `/harness-publish`.
