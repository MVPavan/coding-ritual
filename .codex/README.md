# .codex — the Codex view of this repo's harness

`.claude/` is the canonical harness for both tools. Under `.codex/`:

- `skills/*` — symlinks to `../../.claude/skills/<name>` (every skill carries
  `agents/openai.yaml` with `policy.allow_implicit_invocation`, the Codex twin of
  `disable-model-invocation`). The `harness-*` curation skills and
  `skills/in-progress/` are root-only and not linked.
- `project` — symlink to `../.claude/project` (one overlay).
- `rules/core`, `rules/python` — symlinks; `rules/default.rules` is the Codex
  exec-policy file (real).
- `agents/*.toml` — hand-maintained Codex twins of `.claude/agents/*.md`.
- `config.toml`, `hooks.json`, `hooks/` — Codex wiring and hook scripts (real;
  the Python generated-edit guard differs from the bash one by payload schema).

Codex is retired as the critic in this repo (2026-08-14); see `AGENTS.md`
§Codex And Claude. Distribution of this harness to other repos is the
`mvp-plugin` (`mvp-harness/plugins/mvp-plugin`) — published with `/harness-publish`.
