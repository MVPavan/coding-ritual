# Evidence sources

Read by the `why` skill (Gather step 4). One row per outside source kind; the kinds
and how to search each are in `.claude/skills/why/references/outside-sources.md`.

| Source | Status | Detail |
|---|---|---|
| Analytics warehouse | not here | No deployed service produces product or usage data. Revisit when one ships. |
| Observability | not here | No deployed service emits metrics, traces or logs. Revisit when one ships. |
| Error tracker | not here | No deployed service reports errors. Revisit when one ships. |
| Incident records | alternative | Beads bugs: `bd search` and `bd list --type bug`, with their comments; defensive commits are already in the git search. |
| External ticket tracker | alternative | Beads, already searched in Gather step 4. |
| Document store | alternative | Documents live in the repository (`docs/`, `.repo-context/`, `harness_lifecycle/`), already searched as docs and decision records. |
| Team chat | alternative | Past agent sessions through `recall` (`/recall`), which only the person starts; list them as not searched unless the person ran it. |
