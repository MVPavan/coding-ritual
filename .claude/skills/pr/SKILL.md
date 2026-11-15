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
```

Keep all three sections, in this order. A section with nothing real says so in one line.

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
evidence that does not exist.

## Merge danger

A one-way door is destructive or hard to reverse (data, schema, published interfaces,
deletions); a two-way door is cheap to roll back. Give the reason. For blast radius,
consider consumers, data, config and platforms, not only the files touched.

## Prose

No preamble, recap or closing line; short sentences. Full SHAs, full run logs and
checklists go in a linked artifact; Evidence keeps each check's short output.
