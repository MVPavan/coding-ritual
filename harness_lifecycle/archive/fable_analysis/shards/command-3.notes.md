# Shard notes — command-3 (evaluator: Codex GPT-5.6-Sol xhigh)

Assumption: rows were scored as reusable command surfaces, not as endorsements of their entire parent plugins. A high-quality plugin companion can therefore score well yet be deferred.

Evidence: read every available supplied source. Six stale Everything Claude Code paths were resolved under `legacy-command-shims/`; the Superpowers `execute-plan` command was confirmed removed through release notes. Delegated engines inspected included Hookify hooks/rule skill, continuous-learning-v2 and `instinct-cli.py`, GAN agents, the eval skill, and the 1,082-line harness-audit engine/tests. Local comparisons included Beads, planning, phase/subagent execution, verification, invariant checks, hook scripts, docs-researcher, harness lifecycle commands, and plugin documentation.

Weakest rows: the removed `execute-plan` alias; generic database/feature scaffolds; redundant legacy shims; and `evolve`, whose generation heuristic is not strong enough to create durable agent behavior. Strong but dependency-bound rows: the official Hookify configure command, Hookify list, MCP tunnel quickstart, and instinct status. `gan-build` and `harness-audit` contain reusable patterns but require substantial adaptation.

Cluster relationships: `gan-build` and `gan-design` share the generator-evaluator loop; all Hookify management rows depend on one runtime; instinct export/import form one portability pair, while evolve and status solve distinct promotion and audit problems. Git status was inspected; the worktree was already dirty, and no files were modified.
