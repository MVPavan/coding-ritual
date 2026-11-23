---
name: pr
description: "Use when writing or revising a pull request's body: why, a visual of the change, before-and-after evidence and merge danger. Commits and their titles are land; pushing and merging are not this skill."
---

# PR

Write a pull request's body for a reviewer reading the diff. Opening, pushing or
editing the PR needs publish authority; without it, return the body as text.

```markdown
## Summary
<why, in a sentence or two; then the smallest visual of the change>

## Evidence
- **Before:** <screenshot, or the check and its failing output>
  **After:** <screenshot, or the same check and its passing output>

## Merge danger
**Door:** <one-way or two-way>, because <reason>
**Blast radius:** <who or what this can break>

<Refs|Closes> #<issue>
```

Keep all three sections, in this order. A section with nothing real says so in one line.
The reference line appears only where the project mirrors beads (Issue reference).

## Issue reference

Where the project mirrors beads to GitHub issues, the reference line names the
issue of the bead this pull request delivers. Tell the state first:

- **Writer clone:** `.claude/hooks/bead-mirror.py` exists and `python3
  .claude/hooks/bead-mirror.py map` prints anything or exits non-zero.
- **Opted in, not the writer:** otherwise, and the workflow is committed in
  `HEAD` or in the branch the pull request targets: `git cat-file -e
  <ref>:.github/workflows/bead-reference-check.yml` succeeds for either (a
  staged copy does not count).
- **Not opted in:** neither. Write no reference line.

Find the issue before writing the body. A bead's issue is its `external_ref` when that
names an issue in this repository. Read the bead and its ancestors from `bd list
--all -n 0 --json --brief` (its `external_ref` and `parent` fields), not `bd
show`, which writes. Take the bead's own issue; with none, walk `parent` upward
and take the nearest ancestor's.
With none on the whole chain, and only when you hold the authority to open or edit
the pull request, in the writer clone run `python3 .claude/hooks/bead-mirror.py
outbound --bead <id>`, which creates a public issue: its last line is the new
issue's URL, and a non-zero exit is reported with its message as a stop. When you
only return the body as text, keep `<Refs|Closes> #<issue>` as a placeholder and
say the bead has no issue yet. In any other clone, stop with "ask the writer clone
to mirror this bead". No bead for the work: ask which one.

Write `Closes #<n>` only when `#<n>` is the bead's own issue and this pull request
completes the bead; every other case, an ancestor's issue included, is `Refs #<n>`,
because merging closes whatever a closing keyword names.

## Summary

Say why the change exists and, when a reviewer would ask, what it leaves out. Then pick
the smallest visual that makes the change clear, usually one, never a gallery; a change
with no shape to show gets none. Put it right after the sentence it supports, with real
names and only the calls, files or states this change touches:

- Pseudocode for logic: control flow only, in a `text` block, indentation as structure.
- Call tree for runtime flow: caller above, callees indented, one call per line.
- Component tree for UI or module structure: the file path and the state that matters on the owning line.
- File tree for layout: shallow, a short role comment per entry, only the touched directories.
- Mermaid for interaction or data flow, only where it renders, under about ten nodes.
- Whole block of real code when the change is mostly new code.
- A `diff` against one of those shapes when the shape already exists: `+` and `-` on the
  components, files, calls or branches that change, not on raw source.

For the same forms on request, the person can call `show-me`.

## Evidence

Show before and after from real runs. Prefer a screenshot when the change is visible and
the environment can capture one; otherwise give the exact check with its short output,
failing before and passing after. If a check was not run, say which; never describe
evidence that does not exist. For a performance change, lead with one primary number and
link its supporting evidence.

A count or a file tree anywhere in the body (files changed, tests added, a layout)
holds at the commit that lands and gives the command that reproduces it.

## Merge danger

A one-way door is destructive or hard to reverse (data, schema, published interfaces,
deletions); a two-way door is cheap to roll back. Give the reason. For blast radius,
consider consumers, data, config and platforms, not only the files touched.

## Prose

No preamble, recap or closing line; short sentences. Full SHAs, full run logs and
checklists go in a linked artifact; Evidence keeps each check's short output.
