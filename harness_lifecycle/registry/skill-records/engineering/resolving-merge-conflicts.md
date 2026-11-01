---
skill: resolving-merge-conflicts
domain: engineering
stage: Delivery
substage: Integration
secondary: []
family: git-mechanics
aliases: []
status: active
---
# resolving-merge-conflicts

Use when a git merge, rebase, or cherry-pick is already in a conflicted state and the conflicts need resolving. Trigger on merge-conflict / rebase-conflict phrases.

**Boundary:** Resolves a merge, rebase or cherry-pick already in conflict and finishes that operation; turning ordinary verified changes into commits is land.

<!-- registry:generated traits -->
- `capture-conflict-set`: Capture the conflicted file set up front from the version control's unmerged-paths listing.
- `trace-intent`: Find the primary source of each conflict via commit messages and requirements first, expanding to PRs or issues only when a disputed hunk needs that history.
- `resolve-preserve-both`: Resolve each hunk preserving both intents where possible, picking the one matching the merge's stated goal where incompatible and noting the trade-off, inventing no new behaviour.
- `resolve-over-abort`: Resolve rather than reflexively aborting, stopping to ask the user before aborting when intents cannot reconcile or the operation itself is wrong.
- `run-project-checks`: Discover and run the project's automated checks and fix what the merge broke.
- `explicit-staging`: Stage only the resolved files from the captured conflict set by explicit path.
- `commit-authority-gate`: Commit or continue the rebase only with granted authority, otherwise stop with the resolution staged and report what would be committed.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/resolving-merge-conflicts** `skills/engineering/resolving-merge-conflicts/SKILL.md` @ 84fdeff
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:138): Adopted nearly whole as a model-invocable skill — deviation from the comparison's rule-page recommendation, recorded per critic finding 8. Steps R1-R6 kept; 'i…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/git-agent-workflow](../../../archive/skill-comparisons/git-agent-workflow/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
