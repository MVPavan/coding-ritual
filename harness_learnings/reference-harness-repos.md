# Reference Harness Repos

These are the local third-party reference repos used to study harness patterns. They live under `reference_harnesses/` and should remain read-only sources.

| Repo | Local Path | Upstream | Best At | Do Not Cargo-Cult |
| --- | --- | --- | --- | --- |
| Compound Engineering | `reference_harnesses/compound-engineering-plugin` | `https://github.com/EveryInc/compound-engineering-plugin.git` | Brainstorming, planning, document review, onboarding, knowledge discoverability | Large persona lattices, connector-heavy assumptions, deep workflow ceremony |
| Everything Claude Code | `reference_harnesses/everything-claude-code` | `https://github.com/affaan-m/everything-claude-code.git` | Python review, layered rules, broad harness coverage | Large catalogs, install detail, heavy command inventory |
| Matt Pocock Skills | `reference_harnesses/mattpocock_skills` | `https://github.com/mattpocock/skills.git` | TDD discipline, interface design, adversarial questioning, domain language | Converting every task into a teaching workflow |
| Superpowers | `reference_harnesses/superpowers` | `https://github.com/obra/superpowers.git` | Subagent-driven execution, verification rigor, debugging, skill routing | Over-broad skill enforcement and too much ceremony for small work |

## Fast Usage

- Need better brainstorm or plan structure: start with Compound Engineering.
- Need execution loops, task packets, or review sequencing: start with Superpowers.
- Need Python review or layered rules: start with Everything Claude Code.
- Need stronger test-first or design pressure: start with Matt Pocock Skills.

## Borrowing Heuristic

- Borrow the smallest durable pattern that improves the harness.
- Prefer repo-agnostic workflow logic over tool- or org-specific packaging.
- If two repos say the same thing, keep the simpler form.
