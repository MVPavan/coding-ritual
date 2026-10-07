<!-- BD:GENERATED START -->
# Checklist — dws
_generated from bd @ 2026-10-07T05:00:44Z — DO NOT EDIT (run: BD_RENDER=1 bash <beads-skill-dir>/scripts/bd-render-tracking.sh)_
_Roadmap: [roadmap.md](../roadmap.md) · Brainstorm: [DWS_PRD.md](../../../../docs/brainstorms/dws/DWS_PRD.md)_
## [P10] Operations and recovery
- [x] `cr-tnv.1` Retention, freshness and expiry policy
- [x] `cr-tnv.2` Pin, unpin and bounded export
- [x] `cr-tnv.3` Garbage collection, tombstones and disk pressure
- [x] `cr-tnv.4` Quiesced backup and verified restore
- [x] `cr-tnv.5` Maintenance interruption recovery
- [x] `cr-tnv.6` Upgrade, rollback and schema compatibility

## [P11] Release qualification
- [x] `cr-e0k.1` Compose bootstrap, readiness and restart
- [x] `cr-e0k.2` Sanitized diagnostics and structured logging
- [x] `cr-e0k.3` Adversarial input and bounded-output qualification
- [x] `cr-e0k.4` Host CLI workflow template
- [x] `cr-e0k.5` Measured concurrency qualification
- [x] `cr-e0k.6` Release gate and acceptance matrix

## [P12] MCP adapter (Delivery B)


## [P1] Foundation: runtime qualification and frozen contracts
- [x] `cr-0km.1` Package boundary and tooling
  - 📝 Pilot approved 2026-09-12: Opus 5 high implementer, GPT-5.6 Terra high reviewer; coordinator may approve/disapprove exact candidate and escalate material uncertainty. Target wf/dws-pilot only.  /  Pilot stopped before review: Opus candidate 27ecc265 preserved under cr-717; Terra activation cr-75c refused 32KB input budget, raw diff 78608 bytes. Halt cr-1edk retained; coordinator withholds approval. Evidence: scratchpad/execution/dws-pilot/result.md in wf/dws-pilot worktree; follow-up recovery issue recorded.
- [x] `cr-0km.2` QMD lexical qualification
  - 📝 Coordinator approved one bounded repair attempt, preserving candidate2118ccf and original evidence. Minimal launcher heartbeat replaces repeated transcript polling.  /  User authorized one bounded lint/format cleanup after recovery cr-5apz; preserve c78d556 and require all gates.  /  User moving to another session. Resume handoff: scratchpad/execution/dws-qmd-qualification/HANDOFF-2026-09-15.md. Latest snapshot: attempt3 rootcr-9av3 activationcr-6zhw running; read cleanup-heartbeat.json first and do not duplicate launch. Handoff paths locally verified; optional external fresh-context check rejected by automatic approval review, not run.
- [x] `cr-0km.3` Lock and child-process qualification
  - 📝 At two-round cap: reviewer formatter-count MAJOR disproven by actual locked Ruff0.16.7 on22411a3:8formatted =7Python +README.md. Confirmed negative-control cleanup missing exit wait and safe-path duplicate wait. Signed abandon; one-entry maintenance successor authorized by coordinator under delegated triage authority, keeping code changes inside workflow. No manual source fixes.  /  Landed15de351b7415853d4e138f8963d5335b63f03b3b on wf/dws-lock-qualification via Terra high/Opus medium.6real-process qualification tests, parent-only negative control, inherited-lock lifetime, observed ext4 target. Host DWS acceptance exit0 after nodes and final bridge. No coordinator source fixes. Initial2rounds exhausted on evidence/cleanup findings; one bounded successor fixed real cleanup defect, reviewer count MAJOR adjudicated false with executed Ruff proof(7Python+README=8). FinalOpus accept0blocker0major. LocalLinux/ext4 Python-prototype only; actualQMD/deployed volume/G03 not claimed. Evidence scratchpad/execution/dws-lock-qualification/. Feedbackcr-02ze.15; nonblockingpolishcr-52h8.
- [x] `cr-0km.4` Image, volume and browser egress qualification
  - 📝 Application image accepted. SearXNG fix1 ACCEPTED: fresh Sol high COMPLIANT/APPROVE F1-F3 addressed;6 frozen hashes unchanged, coordinator inspected central plugin config/exact failure assertions/cleanup code+receipts. Limits live-provider/distribution not claimed. Browser review BLOCK two Important test gaps: missing executable receipt predicates, no calibrated forbidden HTTPS WebTransport/QUIC attempt. Actual detailed leaf report recovered scratchpad/dws/browser-containment/candidate-review-findings.md. Coordinator verified source; original Astra resumed fix1 handle29246, scratchpad/dws/browser-containment/fix1/. Fresh xhigh re-review required. .4 remains open.
- [x] `cr-0km.5` Pinned runtime manifest and distribution review
- [x] `cr-0km.6` Delivery-order record in PRD and design
  - 📝 Astra medium edits complete; frozen PRD/design candidate under independent Sol high read-only review handle 30797. Snapshot/result scratchpad/dws/reviews/delivery-{snapshot.json,result.md}. Resume execution + code-review; verify candidate and disposition review before closure. No commits.
- [x] `cr-0km.7` Domain contracts, provider ports and policy
- [x] `cr-0km.8` Recover DWS package candidate through independent pointer review
  - 📝 Recovery successor for cr-0km.1. Original stage superseded, not successfully landed; historical phase bridge metadata/root cr-717 untouched. New stage must independently earn review/check/ship/landing receipt. Initial admission blocked by unfinished predecessor before any model dispatch.
- [x] `cr-0km.9` Prepare DWS orchestrated implementation goal
  - 📝 plan: docs/plans/dws/implementation-goal.md
- [x] `cr-0km.10` Integrate reviewed DWS pilot artifacts into current DWS branch
  - 📝 Imported source-identical pilot candidate; Astra worker finished. Independent Sol high read-only review live handle 46289. Snapshot/result scratchpad/dws/reviews/integration-{snapshot.json,result.md}; report docs/verification/dws/pilot-integration.md. Package checks pass, 16 tests pass, 4 QMD setup errors: runtime missing. G02/G03 not closed. Resume execution + code-review from scratchpad/dws/orchestration-state.json; collect review and verify hashes before acceptance. No commits.
- [x] `cr-0km.11` Requalify pinned QMD runtime in current DWS environment
  - 📝 Independent Sol high supports four actual lexical tests and exact runtime/hash integrity, but two minor evidence defects: UTC duration contradicts pytest; registry fetch absent structured receipts. Astra medium correction running handle80499; scratchpad/dws/qmd-requalification/fix/. One measured monotonic rerun, no test/source changes or weakened isolation. Coordinator verify exact evidence delta before close; original logs preserved.
- [x] `cr-0km.12` Reconcile DWS source and tracking references
  - 📝 Twelve DWS spec/design fields corrected to canonical PRD/roadmap; README/roadmap edits done. Independent Sol high reviewer handle51639, snapshot/result scratchpad/dws/tracking-references/review-{snapshot.json,result.md}. Known renderer conflict remains: shared renderer expects roadmap spec_id and writes global boards; not run or changed. Resume execution/code-review from compact orchestration state; do not hand edit generated mirrors.
- [x] `cr-0km.13` Qualify actual QMD child lock lifetime on the application volume
  - 📝 Changed stdin-carrier author completed real proof: same worker retains lock after controller+launcher death; unsafe parent-only early release; exact output and reaping;14 containers/2 volumes cleaned.4 candidate files frozen under fresh Sol xhigh leaf review handle88694, scratchpad/dws/qmd-child-qualification/stdin-carrier/review/result.md. No further delegation allowed. Actual mechanism acceptance pending independent review and snapshot/evidence verification. Public launcher preserved; noninteractive internal stdin reserved, upgrade requalification required.
- [x] `cr-0km.14` Collect accepted application and SearXNG distribution inventory
  - 📝 P1 stage5 input only: accepted application/SearXNG immutable inventory can proceed independently while browser final qualification remains open; no full runtime freeze or dependency changes. Astra medium explicit leaf handle36841; brief/result scratchpad/dws/accepted-inventory/. Own only accepted-components-inventory docs/JSON/notices. Existing measured manifests primary, no private image uploads or broad tooling installs. Independent review after candidate. cr-0km.5 waits this input and remaining browser stage.
- [x] `cr-0km.15` Decide retrieval backend before resuming DWS implementation
  - 📝 Owner requested 2026-10-02: do this before anything else. Resume with research and prototype; use bounded independent review. Existing qualification evidence is retained, not discarded. Codex Ultra readiness is being assessed separately.

## [P2] Evidence core
- [x] `cr-42y.1` Schema, migrations and transaction ownership
- [x] `cr-42y.2` Artifact publication and structure sidecar
- [x] `cr-42y.3` Document, snapshot, acquisition and membership records
- [x] `cr-42y.4` Bounded direct read
- [x] `cr-42y.5` Metadata-plus-outbox commit
- [x] `cr-42y.6` Publication crash recovery

## [P3] Command surface: daemon and CLI
- [x] `cr-3ah.1` Local command API transport
- [x] `cr-3ah.2` CLI parsing, output and exit classes
- [x] `cr-3ah.3` Configuration discovery and local access policy
- [x] `cr-3ah.4` Workspace and run administration
- [x] `cr-3ah.5` Administrative DTO reservation and diagnostics
- [x] `cr-3ah.6` Process entry points and bootstrap mode

## [P4] Runtime controls
- [x] `cr-wxi.1` Cross-process acquisition slots
- [x] `cr-wxi.2` Store-maintenance and index-lifecycle gates
- [x] `cr-wxi.3` Supervised child execution
- [x] `cr-wxi.4` Admission, backpressure and fairness
- [x] `cr-wxi.5` Residual provider work reconciliation

## [P5] Static acquisition
- [x] `cr-a9a.1` Outbound URL safety policy
- [x] `cr-a9a.2` Static HTTP acquisition
- [x] `cr-a9a.3` HTML extraction and line map
- [x] `cr-a9a.4` PDF extraction and page map
- [x] `cr-a9a.5` Freshness reuse and acquisition coalescing

## [P6] Rendered acquisition
- [x] `cr-u0m.1` Crawl4AI adapter and escalation signals
- [x] `cr-u0m.2` Browser egress and isolation enforcement
- [x] `cr-u0m.3` Rendered acquisition under shared limits

## [P7] Discovery
- [x] `cr-b7e.1` SearXNG adapter
- [x] `cr-b7e.2` DDGS fallback and capability routing
- [x] `cr-b7e.3` Outcome typing and search history
- [x] `cr-b7e.4` Effective dependency recording

## [P8] Retrieval
- [x] `cr-ggx.1` Indexer ownership and collection views
- [x] `cr-ggx.2` Outbox batch algorithm and generations
- [x] `cr-ggx.3` Restricted QMD adapter
- [x] `cr-ggx.4` Per-path verification of index updates
- [x] `cr-ggx.5` Index rebuild from canonical artifacts
- [x] `cr-ggx.6` Scoped candidate resolution and passage construction
- [x] `cr-ggx.7` Cursor and generation consistency
- [x] `cr-ggx.8` Coverage and index-state honesty

## [P9] Durable crawl
- [x] `cr-o71.1` Job records, submission and idempotency
- [x] `cr-o71.2` Claiming, leases and fencing
- [x] `cr-o71.3` Restart recovery scan
- [x] `cr-o71.4` DWS-owned frontier and scope enforcement
- [x] `cr-o71.5` Budgets and reconciling counters
- [x] `cr-o71.6` Cancellation and deadline separation
- [x] `cr-o71.7` Bounded crawl manifest
- [x] `cr-o71.8` Crawl and indexing coexistence in one worker


<!-- BD:GENERATED END -->

<!-- Human notes below this line are preserved across renders. Everything above is bd-generated; do not hand-edit it. -->
