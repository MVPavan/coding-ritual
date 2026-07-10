# hook-1 Row Evaluation Notes

## Scope

- Shard: `hook-1`
- Input: `harness_lifecycle/codex_analysis/shards/hook-1.input.jsonl`
- Output rows written: 68
- Owned outputs: `harness_lifecycle/codex_analysis/shards/hook-1.row_evaluations.jsonl`, `harness_lifecycle/codex_analysis/shards/hook-1.notes.md`
- No files outside the owned outputs were intentionally modified.

## Assumptions

- CSV/input row fields are the primary source of truth. Most hook descriptions are empty, so Fable/GPT reasons and the hook names carry most row-level signal.
- Reference harnesses were treated as read-only. Source files were inspected only where the row was ambiguous, duplicated, or needed overlap checks.
- `my_harness/` from the project map is not present in this working tree; the current code-intel hook lives under `mvp-harness/plugins/code-intel/hooks/`.
- `bd prime` could not be run because `bd` is not installed in this environment; no Beads issue state was changed.

## Evidence Inspected

- Local hook wiring and overlap: `.codex/hooks.json`, `.claude/hooks/`, `.codex/hooks/`, `mvp-harness/plugins/code-intel/hooks/`.
- Catalogs: `harness_lifecycle/catalogs/everything-claude-code.json`, `harness_lifecycle/catalogs/claude-plugins-official.json`, `harness_lifecycle/catalogs/claude-code-best-practice.json`.
- Representative reference source files inspected read-only:
  - `reference_harnesses/everything-claude-code/scripts/hooks/config-protection.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/cost-tracker.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/doc-file-warning.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/evaluate-session.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/mcp-health-check.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/quality-gate.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/pre-compact.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/session-start.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/suggest-compact.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/pre-bash-commit-quality.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/post-edit-format.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/post-edit-typecheck.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/post-edit-accumulator.js`
  - `reference_harnesses/everything-claude-code/scripts/hooks/run-with-flags.js`
  - `reference_harnesses/everything-claude-code/skills/continuous-learning-v2/hooks/observe.sh`
  - `reference_harnesses/everything-claude-code/.cursor/hooks/*.js` representative adapter files
  - `reference_harnesses/claude-plugins-official/plugins/hookify/hooks/pretooluse.py`, `posttooluse.py`, `userpromptsubmit.py`, `stop.py`
  - `reference_harnesses/claude-plugins-official/plugins/security-guidance/hooks/security_reminder_hook.py`, `review_api.py`, `patterns.py`, `session_state.py`
  - `reference_harnesses/claude-plugins-official/plugins/ralph-loop/hooks/stop-hook.sh`
  - `reference_harnesses/claude-code-best-practice/.claude/hooks/scripts/hooks.py`

## Weak Or Ambiguous Rows

- `hook:hookspy`: source inspection showed this is mainly sound notification plus hook-event logging, not the generic hook framework implied by the CSV reasons. Marked `reject_after_review`.
- `hook:initpy`, `hook:aftertabfileeditjs`, `hook:beforetabfilereadjs`, `hook:postbashbuildcompletejs`: not meaningful standalone capabilities after review.
- `hook:stophooksh`: useful only for the Ralph loop plugin; not a general stop hook for this harness.
- `hook:sessionstartbootstrapjs` and `hook:sessionstartmjs`: duplicate/weaker variants of the stronger `session-start.js` row.
- `hook:governancecapturejs`: process-heavy and not tied to a current local harness need.

## Likely Cluster Relationships

- Existing local keep/adopt cluster: `bd-prime.sh`, `block-dangerous-commands.sh`, generated-file guards, `freshness-check.sh`, and `harness-staleness-nudge.sh`.
- Hookify rule engine cluster: `pretooluse.py`, `posttooluse.py`, `userpromptsubmit.py`, `stop.py`.
- Security guidance cluster: `security_reminder_hook.py`, `review_api.py`, `patterns.py`, `session_state.py`, `_base.py`, `diffstate.py`, `gitutil.py`, `llm.py`, `extensibility.py`, `sg-python.sh`.
- Context continuity cluster: `pre-compact.js`, `session-start.js`, `suggest-compact.js`, plus weaker session start/end markers.
- Edit quality cluster: `quality-gate.js`, `post-edit-format.js`, `post-edit-typecheck.js`, `post-edit-accumulator.js`, and related after-file-edit adapters.
- Git workflow cluster: `pre-bash-commit-quality.js`, `pre-bash-git-push-reminder.js`, `post-bash-pr-created.js`.
- MCP observability cluster: `mcp-health-check.js`, `before-mcp-execution.js`, `after-mcp-execution.js`.
- Hook profile plumbing cluster: `run-with-flags.js`, `run-with-flags-shell.sh`, `check-hook-enabled.js`.
- Tmux/dev-server cluster: `pre-bash-dev-server-block.js`, `auto-tmux-dev.js`, `pre-bash-tmux-reminder.js`.

## Issues For Coordinator

- Several rows are implementation fragments rather than user-facing capabilities. They are marked `merge` when they are useful support for a larger cluster and `reject_after_review` when they have no independent value.
- The CSV reasons sometimes over-credit generic value from a file name; source inspection changed the verdict for `hook:hookspy` most clearly.
- Many `everything-claude-code` hooks are JavaScript/Node implementations. The shard evaluations generally preserve the pattern but recommend `rewrite`, `merge`, or `defer` rather than direct adoption unless the capability already exists locally.
