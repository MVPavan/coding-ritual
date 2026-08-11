# Shard notes — hook-2 (evaluator: Codex GPT-5.6-Sol xhigh)

Assumptions: scores describe the implemented capability, while verdicts describe fit for this Python-centric, dual Claude/Codex reusable harness. JavaScript was penalized only where behavior was ecosystem-specific or introduced avoidable vendor/runtime coupling.

Evidence: inspected every supplied source path; followed thin wrappers into adapter.js, doc-file-warning.js, post-edit helpers, hook-flags.js, and the full session-start implementation. Local comparison covered AGENTS.md, the project overlay, hook registrations and scripts, Python rules, code-reviewer, run-phases, html-artifact, the adoption report, and the harness-design canon. External tests were not executed, but relevant test inventories and selected assertions were inspected. The working tree was already dirty; this review made no writes.

Weakest rows: the empty __init__.py is not a capability; before/after MCP adapters are log-only rather than governance; Cursor Tab and JS formatter hooks are out of scope; ensure_agent_sdk.py is operationally disproportionate. observe.sh is test-rich but rejected for privacy, latency, and subsystem complexity.

Cluster relationships: patterns.py, _base.py, diffstate.py, extensibility.py, and gitutil.py should be assessed as one automated-security-review candidate and merged together if pursued; none merits isolated adoption. ensure_agent_sdk.py belongs to that cluster but should be excluded. The three sensitive-data hooks need one cross-surface rewrite. The MCP pair should be rejected together. Post-edit and shell-lifecycle adapters are mostly Node/Cursor-specific.
