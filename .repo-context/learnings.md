# Scoped Lessons

Search for the affected component; read only matching evidence. Revalidate when
its implementation, CLI version, or execution environment changes. Update durable
guidance only within the authorization in `AGENTS.md`.

## Interpreter and test work

| Area | Apply | Evidence / revisit condition |
|---|---|---|
| Foreman test timing | Use advancing real time for process-liveness tests; arm crashes before dispatch and requeue scripts after lab rebuilds. | `tests/_foreman.py` (`ForemanLab`), `tests/test_inspector_run.py`; revisit clock/rebuild changes. |
| Process termination | Assert death when termination is promised, before a barrier or timeout could make natural exit look successful. | `tests/test_foreman_steer.py`; archived liveness mutation. |
| Validated model updates | Reconstruct through validation when updates affect cross-field invariants; do not assume `model_copy(update=...)` validates them. Recheck field-disjointness arguments when validators change. | `workflow_interpreter/foreman/cases.py` (`_request`), `workflow_interpreter/bdio/wire.py`; archived Pydantic incident. |
| Real Beads test rigs | Use an isolated workspace outside the repository and verify database resolution before mutation. Unexpected “already initialized” requires inspection. | Temporary-workspace test fixtures; archived cr-o85.32 incident. |
| Instructions to real agents | A compliant test double does not prove the production brief teaches the outcome/artifact protocol. Check the composed brief; obtain live evidence when the change requires it. | `workflow_interpreter/foreman/inputs.py`, `tests/test_foreman_functional.py`; cr-0zc. |
| Capability probes | Exercise and record the production argv/API path. Results through another interface do not prove its limits. | `docs/adr/0003-large-payloads-and-shared-methods.md`; archived payload probe. |
| Pinned verifier execution | Derive paths from Git in cwd; `$0` names a file descriptor, with no `$WF_*` protocol guaranteed. | `workflow_interpreter/inspector/verify.py`, `scripts/verify-feature.sh`; revisit launch-contract changes. |
| Report size limits | Bound added fields at their producer; transcript truncation may not cover them. | `workflow_interpreter/foreman/__main__.py` (`_emit`); revisit report-format changes. |
| Interpreter Codex profile | Its Git-write restriction is specific to this profile/sandbox. Follow approved graph routing; do not generalize it to interactive Codex sessions. | `workflow_interpreter/profiles/codex.py`, `tests/test_profiles_git_isolation.py`, `docs/adr/0004-deterministic-routing.md`. |
| Worker worktrees | Name and verify the intended base before editing or landing. Reconcile mismatches under existing Git authority. | Archived 2026-09-04 incident; revisit worktree-creation changes. |
| Gate failure evidence | Save each gate's full output to a separate log, then show the summary and `FAILED` lines. A last-line-only recipe hid a nonreproducing failure's test name. | 2026-09-11, cr-l4a; retain logs through the slice. |
| Marked pytest lanes | A file-scoped green run does not prove its marker lane: one 34-test file run missed failures among 66 acceptance tests. Brief workers with the marker expression from `.repo-context/verification.md`. | 2026-09-11, cr-l4a; rerun the actual lane. |
| Assembled briefs | Check the final brief for a distinctive string from every required section before dispatch. Extracting from the first item dropped two prior design rulings. | 2026-09-11, Slice 2b dispatches 3–5. |
| Backend identity | Keep status bounded, but prove model identity from activation pins and actual runner/native session records; validate saved identities against fresh durable state on resume. | 2026-09-11, cr-thh.1 and agent-bridge P5 verification. |
| Flaky-test claims | Require repeated isolated runs on unchanged code showing both outcomes before labeling a test flaky; re-prove before relying on the label. A store-seam regression was hidden by a stale list. | 2026-09-21, store-restructure epic cr-nwy9. |
| Seam deletion gates | Run both pytest lanes and the full five-stage repo gate after deleting or replacing a seam; report any lane that cannot run. The skipped Beads lane caught a cutover regression. | 2026-09-21, cr-nwy9; `.repo-context/verification.md`. |
| Typecheck after renames | If mypy reports removed modules after a package rename, rerun once with `--cache-dir=/dev/null` before treating errors as current. | 2026-09-21, cr-nwy9 S0; stale `.mypy_cache`. |
| Time-based tests | Inject a frozen clock at construction and advance it while using real child processes to cover expiry and staleness without sleeps. | 2026-09-21, cr-nwy9 lab rig. |

## Historical CLI observations

Original evidence: `docs/research/repo-context-history/2026-09-10/learnings.md`.

- Codex configuration parsing and hidden flags: CLI 0.144.1 (2026-07-10).
  Probe the installed version before changing a wrapper allowlist.
- `codex exec -c` silently accepted invalid keys or values on CLI 0.144.1,
  including a bogus effort value. Validate safety-critical overrides before
  dispatch; prefer native `-s` for plain `exec`. `exec resume` and `exec review`
  did not accept `-s`; verify current CLI behavior before changing a wrapper.
- Beads initialization and plugin scope/hooks: 2026-08-19 observations.
  Verify current behavior in an isolated environment before installer work.
- Claude API failure with exit 0: observed 2026-09-03. Check the runtime result
  protocol as well as exit status; output length or its first line alone is
  not reliable proof of success.

Incident narratives and old audit counts are preserved there, not asserted as
current state. Historical adoption and code-intelligence assessments are adjacent
archive files; they do not authorize installations or policy changes.
