# Scoped Lessons

Search for the affected component; read only matching evidence. Revalidate when
its implementation, CLI version, or execution environment changes. Update durable
guidance only within the authorization in `AGENTS.md`.

## Interpreter and test work

| Area | Apply | Evidence / revisit condition |
|---|---|---|
| Foreman test timing | Use advancing real time for process-liveness tests; arm crashes before dispatch and requeue scripts after lab rebuilds. | `tests/_foreman.py` (`ForemanLab`), `tests/test_supervisor_run.py`; revisit clock/rebuild changes. |
| Process termination | Assert death when termination is promised, before a barrier or timeout could make natural exit look successful. | `tests/test_foreman_steer.py`; archived liveness mutation. |
| Validated model updates | Reconstruct through validation when updates affect cross-field invariants; do not assume `model_copy(update=...)` validates them. Recheck field-disjointness arguments when validators change. | `workflow_interpreter/foreman/cases.py` (`_request`), `workflow_interpreter/bdio/wire.py`; archived Pydantic incident. |
| Real Beads test rigs | Use an isolated workspace outside the repository and verify database resolution before mutation. Unexpected “already initialized” requires inspection. | Temporary-workspace test fixtures; archived cr-o85.32 incident. |
| Instructions to real agents | A compliant test double does not prove the production brief teaches the outcome/artifact protocol. Check the composed brief; obtain live evidence when the change requires it. | `workflow_interpreter/foreman/inputs.py`, `tests/test_foreman_functional.py`; cr-0zc. |
| Capability probes | Exercise and record the production argv/API path. Results through another interface do not prove its limits. | `docs/adr/0003-large-payloads-and-shared-methods.md`; archived payload probe. |
| Pinned verifier execution | Derive paths from Git in cwd; `$0` names a file descriptor, with no `$WF_*` protocol guaranteed. | `workflow_interpreter/supervisor/verify.py`, `scripts/verify-feature.sh`; revisit launch-contract changes. |
| Report size limits | Bound added fields at their producer; transcript truncation may not cover them. | `workflow_interpreter/foreman/__main__.py` (`_emit`); revisit report-format changes. |
| Interpreter Codex profile | Its Git-write restriction is specific to this profile/sandbox. Follow approved graph routing; do not generalize it to interactive Codex sessions. | `workflow_interpreter/profiles/codex.py`, `tests/test_profiles_git_isolation.py`, `docs/adr/0004-deterministic-routing.md`. |
| Worker worktrees | Name and verify the intended base before editing or landing. Reconcile mismatches under existing Git authority. | Archived 2026-09-04 incident; revisit worktree-creation changes. |

## Historical CLI observations

Original evidence: `docs/research/repo-context-history/2026-09-10/learnings.md`.

- Codex configuration parsing and hidden flags: CLI 0.144.1 (2026-07-10).
  Probe the installed version before changing a wrapper allowlist.
- Beads initialization and plugin scope/hooks: 2026-08-19 observations.
  Verify current behavior in an isolated environment before installer work.
- Claude API failure with exit 0: observed 2026-09-03. Check the runtime result
  protocol as well as exit status; output length or its first line alone is
  not reliable proof of success.

Incident narratives and old audit counts are preserved there, not asserted as
current state. Historical adoption and code-intelligence assessments are adjacent
archive files; they do not authorize installations or policy changes.
