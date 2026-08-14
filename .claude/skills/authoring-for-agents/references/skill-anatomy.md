# Skill anatomy

Structure and mechanics when the document is a skill or command in this
harness — only what changes because of the packaging.

## Layout

```text
.claude/skills/<name>/
  SKILL.md          # required
  references/       # only when SKILL.md alone is not enough
  scripts/          # only for runnable helpers
```

- Keep `SKILL.md` lean — this harness's skills run near 100 lines. The real
  bound is branch relevance, not a line count: inline what every run needs,
  push into `references/` what only some branches reach. As a rough gauge,
  material under ~50 lines that every run touches stays inline; reference
  consulted on demand earns its own file as it grows past that.
- References stay one level deep: `SKILL.md` points at a file; that file never
  chains to another.
- Prefer a script over inline code the agent must retype — executing costs no
  context, only the output does.
- No empty `scripts/` or `references/` directories to mirror other skills.

## Frontmatter

`name` (kebab-case, matches the directory) and `description` are required.
House-used optional fields: `disable-model-invocation: true` makes a skill
user-invoked (see below); `license` when the content is imported under one.

The description is the skill's always-loaded pointer — the pointer-writing
rules apply in full, plus one hard rule of its own:

- **Triggers only, never a workflow summary.** A description that summarises
  the process becomes a shortcut: the agent follows the summary and skips the
  body. (Observed: "code review between tasks" in a description produced one
  review where the skill's body required two.)
- Third person, starting "Use when…", naming symptoms and situations the
  agent will actually see — error text, task shapes, tool names.
- When routing between neighbours is ambiguous, name them: "To open up a raw
  idea first, use idea-refine; to interrogate a plan that is already written,
  use grill-me."

```yaml
# bad — summarises the workflow; the agent may execute this line instead of the body
description: Use for TDD — write a failing test first, then minimal code, then refactor

# good — triggering conditions only
description: Use for risky behavior changes, bug fixes, or legacy edits where test-first execution is the safest path
```

## Body pattern

Recommended shape, not a rigid template — equivalent headings are fine:

- a purpose line: what the skill turns into what
- the process, as steps with completion criteria ("done when…")
- rules the process must hold to
- verification / done-when for the whole skill

A discipline skill — one enforcing a rule the agent will want to skip — adds
two sections, both built from excuses observed in testing, never invented:

- a rationalization table: `| Excuse | Reality |`
- a red-flags list: the thoughts that mean "stop, start over"

House examples: `idea-refine` (red flags), `test-driven-development`,
`verification-before-completion`.

## Invocation: three reaches

| Reach | Mechanics | Cost |
| --- | --- | --- |
| **Model-invoked skill** — the agent fires it on its own; other skills can route to it | a description carrying the trigger branches | the description is permanent context load |
| **User-invoked skill** — only the human typing `/name` fires it; no skill can route to it | `disable-model-invocation: true`; the description turns human-facing — a one-line summary, trigger lists stripped | zero trigger load, but the human is the index that must remember it |
| **Command** (`.claude/commands/<name>.md`) — the human launches a workflow, optionally with arguments | a prompt file, not a skill | no standing description |

Pick model-invocation only when the agent must reach the document unprompted
or another skill routes to it. House examples of user-invoked skills:
`grill-me`, `i-have-adhd`, `teach-session`.

When human-only surfaces multiply past what the human can remember, a
**router** — one surface that names the others and when to reach for each —
trades one description for many memorized names. It can only hint at
user-invoked skills, never fire them.

## Cross-references

- Name other skills by name in prose — "the `planning` skill" — and route to
  them; never duplicate a neighbour's content.
- Before creating a skill, search the catalog; extending the nearest existing
  skill beats a near-duplicate directory.
- Discoverability is the frontmatter's job: a skill is found through its
  description, a command through its name. `.claude/project/docs-index.md`
  indexes durable docs, not the skill catalog.
