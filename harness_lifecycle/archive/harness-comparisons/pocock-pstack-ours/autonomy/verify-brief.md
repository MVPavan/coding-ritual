You are an independent critic verifying a report you did not write. READ-ONLY: do not edit,
stage, commit, or run `bd`. Write nothing except your final answer.

Report: `harness_lifecycle/harness-comparisons/pocock-pstack-ours/autonomy/index.html` (17 Mermaid diagrams + tables in
<details>). It was generated from three model-written data files:
`harness_lifecycle/harness-comparisons/pocock-pstack-ours/autonomy/data/{pstack,pocock,ours}.md` (schema: data/SCHEMA.md),
which themselves summarise primary sources:
- pstack: `reference_harnesses/cursor_plugins/pstack/` (skills/, skills/poteto-mode/playbooks/, agents/)
- Pocock: `reference_harnesses/mattpocock_skills/` (v1.3.1)
- ours: `AGENTS.md`, `.repo-context/`, `.claude/skills/`, `.claude/agents/`, `.claude/hooks/`,
  `workflows/`, `docs/usage/`, `docs/adr/`, `config/`.

Verify at two levels:
1. Report vs data files: every diagram node/edge and every table claim must trace to a data file.
   Check ALL of section 4 (problem comparison, the J: relation labels) and section 6 (autonomy
   layers, gaps, smallest steps), and the section 0 summary. For sections 1-3 and 5, check at
   least 40 edges/claims spread across all three harnesses.
2. Data files vs primary sources: open the cited path:line for at least 30 claims (at least 10
   per harness), prioritising load-bearing ones: pstack's infrastructure assumptions and autonomy
   rules; Pocock's invocation rule and main flow; ours' ship gate, monitor hook_argv, contractor
   behaviour, and human stops.
Also flag: relation labels (alternative/complement/...) that the evidence does not support;
anything that overstates what ours or pstack can do autonomously; missing important skills.

Output (plain text):
1. Overall opinion (short paragraph): can the owner trust this report to decide autonomy direction?
2. Findings, numbered: severity (BLOCKER/MAJOR/MINOR), location (HTML section + diagram/table,
   and the source path:line), what's wrong, the correct fact, one-line fix. Report all findings.
3. Coverage: how many items you checked at each level, and how many passed.
4. Verdict: APPROVE (no open BLOCKER/MAJOR) or REVISE.
