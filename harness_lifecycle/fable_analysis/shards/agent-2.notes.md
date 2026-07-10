# Shard notes — agent-2 (evaluator: Codex GPT-5.6-Sol xhigh)

Assumptions: scores reflect the current live capability bodies, not the shallow labels. Relocated Compound files were read under `skills/ce-*/references/`; the removed Kieran persona was recovered from git history.

Evidence: inspected every row's source body, both variants for planner, PR-test analyzer, and security reviewer, plus local planning, review, research, Python-rule, delegation, knowledge, and harness-curation capabilities.

Weakest rows: `harness-optimizer`, `loop-operator`, and `performance-oracle` are operationally underspecified or actively noisy. `issue-intelligence-analyst` and `repo-research-analyst` solve real problems but need major structural reduction or deterministic preprocessing.

Cluster relationships: retain `performance-reviewer` over `performance-oracle`; reject both imported Python reviewers because the local Python-first reviewer already covers their useful checks; treat security audit, plan security, and diff security as three distinct scopes; group PR comment resolution and prior-comment checking into one future PR-feedback lifecycle.

No mutation commands were run. Final `git status --short` was not clean, so no clean-worktree claim is made.
