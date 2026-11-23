# Reading Index

Read only relevant rows; this is not a checklist. Paths are repo-relative.
Archived research is evidence, not operating policy.

## Shared guidance

| Need | Source |
|---|---|
| Orientation | `.repo-context/repo-map.md` |
| Domain terminology | `.repo-context/GLOSSARY.md` |
| Python conventions; ledger format | `.repo-context/coding-style.md` |
| Checks and prerequisites | `.repo-context/verification.md` |
| Checks an unattended run makes before every commit | `.repo-context/commit-gate.toml` |
| Architecture/contracts | `.repo-context/invariants.md`, `docs/adr/README.md` |
| Investigation | Search `.repo-context/learnings.md`; open matching evidence |
| Answering why with the `why` skill, or adding an outside system | `.repo-context/evidence-sources.md` |
| Grilling summaries and questionnaires, saved or looked up | `docs/interviews/` (`README.md`) |
| Beads the tool: policy, setup, closeout, `bd` behavior and flags, upgrades | `beads` skill, `.claude/skills/beads/SKILL.md` (its table routes to the reference) |
| Workstreams, phase epics, plan records, tracking files | `tracker` skill, `.claude/skills/tracker/SKILL.md` |

## Component work

| Need | Source |
|---|---|
| Interpreter behavior | `docs/specs/workflow-interpreter.md`; relevant accepted ADRs |
| Graph authoring | `workflows/README.md` |
| Build-loop enforcement | `docs/graph-loops/build-loop-tdd-enforcement.md` |
| Codex remote-control daemon (`codex-rc` systemd unit) | `scripts/README.md` |
| Harness design | `harness_learnings/coding-harness-best-practices.md` |
| Cross-runtime collaboration | `harness_learnings/claude-codex-collaboration.md` |
| Reference curation; skill records and rulings | `harness_lifecycle/README.md`; `harness_lifecycle/registry/README.md` |
| Adding, reviewing, comparing or updating a skill | `.claude/skills/mvp-mode/playbooks/skill-curation.md` |
| Principle, skill or playbook: which kind, its rules, traits and steps | `.repo-context/unit-kinds.md` |
| Designing autonomy features or lifecycle-level skills | `harness_lifecycle/adlc/GUIDE.md` |
| Reference adoption/updates | `harness_learnings/reference-harness-workflow.md` |
| Reference comparisons | `harness_learnings/harness-patterns-by-capability.md`, `harness_learnings/reference-harness-repos.md` |
| Publication and installation | `docs/usage/mvp-plugin.md`; initialized plugin's README |
| Beads → GitHub mirror: activation, daily use, recovery | `docs/usage/bead-mirror.md` (draft until the live trial); `docs/workstreams/beads-github-mirror/roadmap.md` |
| Workflow coordination spec | `docs/specs/2026-09-11-workflow-coordination.md` |
| Contractor implementation status and gates | `docs/workstreams/agent-bridge/state.md`, `docs/workstreams/agent-bridge/roadmap.md` |
| Run ledger design and slices | `docs/workstreams/run-ledger/roadmap.md` |
| Store and tracker seam cutover record | `docs/workstreams/store-restructure/roadmap.md`, `docs/workstreams/store-restructure/release-note.md` |
| Ledger-only record store and tracker port decision | `docs/adr/0006-ledger-only-record-store.md` |
| Orchestration reference research | `docs/research/codebases/cli-agent-orchestrator/luna-exploration.md`, `docs/research/codebases/metaswarm/luna-exploration.md` |
| Herdr and Orca comparison | `docs/research/codebases/comparison-herdr-orca.md` |
| Past decisions | `docs/decisions/INDEX.md` |
| Outside answers | `docs/research/<area>/<topic>/` |
| Model catalog design | `docs/workstreams/model-catalog/design.md` |

External inventories for `/codebase-research` live in
`harness_lifecycle/catalogs/<repo>.json`. Historical adoption, code-intelligence,
and incident evidence lives in `docs/research/repo-context-history/`; read it
only for relevant investigation and revalidate changing claims.
