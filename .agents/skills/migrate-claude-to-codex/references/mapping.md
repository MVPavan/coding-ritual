# Shared-policy migration mapping

| Source | Destination / handling |
|---|---|
| Canonical skill directory with SKILL.md | Relative directory link under .codex/skills |
| Legacy SKILL.MD | Linked children with SKILL.md destination casing; source unchanged |
| Claude commands | Converted Codex skill scaffold; review invocation metadata and behavior |
| Claude agents | Conservative Codex TOML scaffold; model IDs require current runtime selection |
| Shared repository guidance | Preserve its declared location, including .repo-context; no Codex copy |
| Claude Markdown rules | Manual routing into AGENTS.md or conditional shared docs; no copied .codex/rules |
| Hooks/settings hook registrations | Runtime-specific copied/converted scaffold; fixture validation required |

Existing skill targets are not overwritten, including with --force. Generated
command names can collide with existing skills; preserve the destination and
report that collision. Symlink support is required; where unavailable, report the
limitation and select an explicit integration strategy rather than silently
creating divergent policy copies.

The helper leaves rule activation semantics and shared-policy editing to the
reviewer. Codex execution-policy files are a separate runtime mechanism, not
Markdown instruction files, and are not generated here. Never infer enforcement
from a converted hook or model access from an agent TOML file.

Structural verification parses assets; real discovery must be checked against
expected names and invocation metadata in the current runtime. Preserve canonical
sources until removal is explicitly requested. No Git commit is implied.

This helper does not relocate existing project documentation. Prefer
`.repo-context/` for new shared guidance; moving a legacy overlay or root
glossary requires an authorized reference migration, not just a new pointer.
