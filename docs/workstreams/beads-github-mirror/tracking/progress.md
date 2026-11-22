<!-- BD:GENERATED START -->
# Progress — beads-github-mirror
_generated from bd @ 2026-11-22T04:04:25Z — DO NOT EDIT (run: BD_RENDER=1 bash <tracker-skill-dir>/scripts/bd-render-tracking.sh)_
_Roadmap: [roadmap.md](../roadmap.md) · Brainstorm: [2026-11-20-beads-github-mirror.md](../../../../docs/specs/2026-11-20-beads-github-mirror.md)_
## [M1] Outbound command
- `cr-k88k.1.1` M1.1 Test seam, skeleton, authority and lock — 877ad3e: tests/mirror 165 passed offline (pytest -q -p no:cacheprovider tests/mirror); ruff, mypy --strict clean; 3 verifier lenses per stage + 3 Sol rounds, last finding fixed red/green.  (2026-11-21T03:59:36Z)
- `cr-k88k.1.2` M1.2 Create and link — 877ad3e: tests/mirror 165 passed offline (pytest -q -p no:cacheprovider tests/mirror); ruff, mypy --strict clean; 3 verifier lenses per stage + 3 Sol rounds, last finding fixed red/green.  (2026-11-21T03:59:36Z)
- `cr-k88k.1.3` M1.3 Update, close and retire — 877ad3e: tests/mirror 165 passed offline (pytest -q -p no:cacheprovider tests/mirror); ruff, mypy --strict clean; 3 verifier lenses per stage + 3 Sol rounds, last finding fixed red/green.  (2026-11-21T03:59:36Z)

## [M2] Digest and pull-request check
- `cr-k88k.2.1` M2.1 Reference grammar and check workflow — 5beeb31 + eb29da2: tests/mirror 233 passed offline; ruff, mypy --strict clean; verifier lenses per stage; Sol REVISE findings fixed (two declined as stated limits).  (2026-11-21T08:19:38Z)
- `cr-k88k.2.2` M2.2 Inbound digest — 5beeb31 + eb29da2: tests/mirror 233 passed offline; ruff, mypy --strict clean; verifier lenses per stage; Sol REVISE findings fixed (two declined as stated limits).  (2026-11-21T08:19:38Z)

## [M3] Hooks and skill guidance
- `cr-k88k.3.1` M3.1 Supervisor and session-start hooks — 5c9f4d2 + a923cee + b2d903d: tests/mirror 251 passed (both real launchers: return time, lock contention, supervisor killed, deadline cleanup, failures, output cap, unchanged Beads context with no switch); bash -n, json.tool, ruff, mypy --strict clean; shellcheck not installed; two Sol rounds, one finding declined as a stated limit.  (2026-11-21T10:04:09Z)
- `cr-k88k.3.2` M3.2 Skill guidance for each project state — be8bf48: skill-catalog --check and registry check pass; state x skill map in scratchpad M3.2/state-skill-map.md; Sol REVISE findings fixed and verified.  (2026-11-21T04:11:50Z)

## [M4] Live trial and activation guide
- `cr-k88k.4.1` M4.1 Trial checklist and owner gate — Checklist committed (be8bf48, docs/workstreams/beads-github-mirror/trial.md); G0 recorded 2026-11-21T11:34Z (owner go-ahead, comment on this bead); setup delegated to the operator  (2026-11-21T11:36:44Z)
- `cr-k88k.4.2` M4.2 Run the live trial — Trial run 2026-11-21 on MVPavan/bead-mirror-trial; results and evidence in trial.md (4bd3e23); all one-account cases pass, S10/F1/F2 deferred; raw recordings in scratchpad/mvp-stack/mirror/trial/recordings (sanitised into fixtures in M4.3); hook-trust: none in Claude print mode, Codex skips untrusted hooks silently (noted in H2); 2 verify rounds, no open blocker/major  (2026-11-21T14:03:32Z)
- `cr-k88k.4.3` M4.3 Replay and hand-over — Recorded fixtures replace provisional (c25543d); tests/mirror 255 passed on recorded fixtures only; reverse-order half proven offline (test_check_two_edits_whose_runs_finish_in_reverse_order_end_with_the_latest_bodys_verdict); server merge decisions recorded live (541e9d6, dd21ecb); guide lists the 8 activation steps in order, each the owner's, and waits for F1/F2. Sol M4 r1 REVISE (4 findings) -> all fixed; r2 left one (server decision right after the flipping run) -> closed by fresh live sequences PR 19-22 in dd21ecb.  (2026-11-21T15:44:04Z)
- `cr-k88k.4.4` Second GitHub account for the mirror's fork cases, or a ruling to activate without them — Owner provided a second account on 2026-11-22 (LazyChads); see comment.  (2026-11-22T03:58:47Z)
- `cr-k88k.4.5` M4.5 Run fork cases F1 and F2 on the trial repository — F1 pass (PR #23: pull_request_target run 44983030038 passed without approval, REST merge 200) and F2 pass (PR #24: stand-in action_required, real run failed, REST merge 405 before and after approving the stand-in). trial.md rows and evidence; commit 80f88fa.  (2026-11-22T04:04:07Z)


<!-- BD:GENERATED END -->

<!-- Human notes below this line are preserved across renders. Everything above is bd-generated; do not hand-edit it. -->
