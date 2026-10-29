---
skill: harness-publish
domain: core
stage: Delivery
substage: Release
secondary: []
family: 
aliases: []
status: active
---
# harness-publish

## Capability

Publish this repo's harness into the mvp-plugin (the mvp-harness submodule) — copy the shippable skills and agents, run the provider-neutrality and leak audits, regenerate the shipped router and Codex sidecars, rebuild the residue template, validate both manifests, bump the version. Root-only; never runs in adopted repos.

<!-- registry:generated traits -->
- `manual-root-only`: Run publishing as a manual, user-run step only in the source workshop, never in an adopted repo.
- `prerequisites-scope`: Confirm the plugin submodule is initialized with its publish script present, reporting a missing prerequisite rather than pretending publication ran.
- `repo-context-check`: Verify the plugin-owned template, installer, updater and doctor use the shared repo-context location and preserve the glossary.
- `authority-separation`: Confirm publication and commit authority separately, treating a no-commit instruction as binding.
- `preflight-gates`: Before publishing, run the catalog check and require a clean tree unless an explicitly authorized dirty-tree mode applies.
- `dry-run`: Run the publish script's check mode to preview the gates, neutrality audit and rsync diff while writing nothing, fixing anything it reports in the source repo rather than the shipped plugin.
- `publish-bump`: Run the publish bump at the level chosen from what changed, with an optional throwaway smoke install and a dirty-tree override only on explicit consent.
- `plugin-repo-review`: Review the separate plugin repository, stage explicit paths, and commit naming the plugin version and source commit only when commit authority was granted, never pushing.
- `submodule-pointer`: Bump and commit the submodule pointer only when authorized, otherwise report the prepared state and proposed update with an update command verified against the consumer's current CLI.
- `failure-table`: Map each publish-script failure line to its cause and fix.
- `never-edit-build-output`: Never hand-edit the shipped plugin's skills or agents, which are build output; edit plugin-owned skills and scripts in the plugin itself.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/git-workflow-and-versioning** `reference_harnesses/agent-skills/skills/git-workflow-and-versioning/SKILL.md` @ aeac41d
  - merged from: git-workflow-and-versioning (semver and changelog sections)
  - modified: semver and changelog become harness-publish release steps
  - dropped: commit cadence
  - dropped: trunk-based and Conventional Commit defaults
  - dropped: destructive recovery guidance
  - dropped: merge-conflict and worktree content
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-10-14` **adopt-merged** (2026-10-14-owner-review:001): Owner ruling: the 2026-08-11 merge target was never built, and the 2026-07-15 objections still hold (commit cadence, trunk and Conventional Commit defaults, de…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
