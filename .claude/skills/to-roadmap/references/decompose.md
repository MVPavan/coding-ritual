# Decompose — roadmap content and approval

Consulted from `to-roadmap`. The roadmap's per-phase content and the approval-gate
format live here; the decision steps live in SKILL.md; the workstream layout,
seeding and rendering are the `tracker` skill's.

## Roadmap per phase

`docs/workstreams/<name>/roadmap.md` is the phased plan. Per phase: Goal ·
deliverables table `| # | Stage | Create/modify paths | Verify |` · spec
references · `Exit (phase):` line · test focus · risk (standard/deep, defined in
`.claude/skills/implement/SKILL.md` under Scope selector) · for review phases,
which original phases they modify. Give each phase an identifier `tracker` can
carry as the epic's `[<phase-id>]` prefix.

## Extending an existing workstream

Append the new phases to the existing `roadmap.md`, continuing its phase
numbering; do not renumber or rewrite existing phases. Name any old phase a new
one genuinely depends on.

## Approval gate — what to present

For material structure not already authorized, present before seeding:

- the phase list in execution order, one line each: name · goal · risk
- stage counts per phase
- every dependency edge (epic→epic and stage→stage), each with its reason
- open questions

Use existing approval covering the concrete structure or delegated routine
choices. Clarify only material ambiguity; do not demand a repeated approval phrase.

## Summary format

Report: workstream path · phases/stages seeded by `tracker` · execution order ·
risk per phase · the next command (phase execution for one phase; the autonomous
workstream walk only when the user asks for it).

Conservative git: report the proposed commands; do not commit.
