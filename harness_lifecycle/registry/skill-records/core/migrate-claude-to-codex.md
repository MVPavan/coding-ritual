---
skill: migrate-claude-to-codex
domain: core
stage: Improvement
substage: Codification
secondary: []
family: 
aliases: []
status: active
---
# migrate-claude-to-codex

## Capability

Adapt Claude harness assets for Codex while preserving shared AGENTS.md policy and canonical skills.

<!-- registry:generated traits -->
- `dry-run-default`: Preview all planned changes by default and write only under an explicit apply flag.
- `skill-symlinking`: Expose canonical skills to the target runtime via relative symlinks without copying, preserving legacy filename casing at the destination.
- `destination-protection`: Never overwrite an existing skill destination even under force, which applies only to generated scaffolds.
- `command-conversion`: Convert source commands into target skill scaffolds, reporting any name collision with an existing skill.
- `agent-conversion`: Convert source agents into conservative target config scaffolds, inferring a sandbox mode and flagging that model identifiers do not carry over.
- `hook-conversion`: Copy hooks and rewrite hook registrations into the target format, flagging that fixtures must validate before enforcement is trusted.
- `config-scaffold`: Write a target runtime config file and a migration-notes document as scaffolds.
- `shared-policy-untouched`: Leave shared policy canonical and rule or execution-policy routing manual, generating no rule files, execution policy or policy-document edits.
- `structural-verify`: Provide a verify command that parses the generated assets and optionally runs discovery, disclosing that structural success proves neither semantic parity nor routing.
- `non-destructive`: Never delete, stage or commit the source assets.
- `test-before-reliance`: Run the migrator's own tests and trial it in a disposable target before relying on changed behavior.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
No adopted lineage recorded.
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
No ledger history recorded.
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
