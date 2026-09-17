<!-- BD:GENERATED START -->
# Checklist — dws
_generated from bd @ 2026-09-17T11:28:10Z — DO NOT EDIT (run: BD_RENDER=1 bash <beads-skill-dir>/scripts/bd-render-tracking.sh)_
_Roadmap: [roadmap.md](../roadmap.md) · Brainstorm: [cli-engine-implementation-plan.md](../../../../docs/plans/dws/cli-engine-implementation-plan.md)_
## [P10] Operations and recovery
- [ ] `cr-tnv.1` Retention, freshness and expiry policy  (blocked)
- [ ] `cr-tnv.2` Pin, unpin and bounded export  (blocked)
- [ ] `cr-tnv.3` Garbage collection, tombstones and disk pressure  (blocked)
- [ ] `cr-tnv.4` Quiesced backup and verified restore  (blocked)
- [ ] `cr-tnv.5` Maintenance interruption recovery  (blocked)
- [ ] `cr-tnv.6` Upgrade, rollback and schema compatibility  (blocked)

## [P11] Release qualification
- [ ] `cr-e0k.1` Compose bootstrap, readiness and restart  (blocked)
- [ ] `cr-e0k.2` Sanitized diagnostics and structured logging  (blocked)
- [ ] `cr-e0k.3` Adversarial input and bounded-output qualification  (blocked)
- [ ] `cr-e0k.4` Host CLI workflow template  (blocked)
- [ ] `cr-e0k.5` Measured concurrency qualification  (blocked)
- [ ] `cr-e0k.6` Release gate and acceptance matrix  (blocked)

## [P12] MCP adapter (Delivery B)


## [P1] Foundation: runtime qualification and frozen contracts
- [x] `cr-0km.1` Package boundary and tooling
  - 📝 Pilot approved 2026-09-12: Opus 5 high implementer, GPT-5.6 Terra high reviewer; coordinator may approve/disapprove exact candidate and escalate material uncertainty. Target wf/dws-pilot only.  /  Pilot stopped before review: Opus candidate 27ecc265 preserved under cr-717; Terra activation cr-75c refused 32KB input budget, raw diff 78608 bytes. Halt cr-1edk retained; coordinator withholds approval. Evidence: scratchpad/execution/dws-pilot/result.md in wf/dws-pilot worktree; follow-up recovery issue recorded.
- [x] `cr-0km.2` QMD lexical qualification
  - 📝 Coordinator approved one bounded repair attempt, preserving candidate2118ccf and original evidence. Minimal launcher heartbeat replaces repeated transcript polling.  /  User authorized one bounded lint/format cleanup after recovery cr-5apz; preserve c78d556 and require all gates.  /  User moving to another session. Resume handoff: scratchpad/execution/dws-qmd-qualification/HANDOFF-2026-09-15.md. Latest snapshot: attempt3 rootcr-9av3 activationcr-6zhw running; read cleanup-heartbeat.json first and do not duplicate launch. Handoff paths locally verified; optional external fresh-context check rejected by automatic approval review, not run.
- [x] `cr-0km.3` Lock and child-process qualification
  - 📝 At two-round cap: reviewer formatter-count MAJOR disproven by actual locked Ruff0.16.7 on22411a3:8formatted =7Python +README.md. Confirmed negative-control cleanup missing exit wait and safe-path duplicate wait. Signed abandon; one-entry maintenance successor authorized by coordinator under delegated triage authority, keeping code changes inside workflow. No manual source fixes.  /  Landed15de351b7415853d4e138f8963d5335b63f03b3b on wf/dws-lock-qualification via Terra high/Opus medium.6real-process qualification tests, parent-only negative control, inherited-lock lifetime, observed ext4 target. Host DWS acceptance exit0 after nodes and final bridge. No coordinator source fixes. Initial2rounds exhausted on evidence/cleanup findings; one bounded successor fixed real cleanup defect, reviewer count MAJOR adjudicated false with executed Ruff proof(7Python+README=8). FinalOpus accept0blocker0major. LocalLinux/ext4 Python-prototype only; actualQMD/deployed volume/G03 not claimed. Evidence scratchpad/execution/dws-lock-qualification/. Feedbackcr-02ze.15; nonblockingpolishcr-52h8.
- [ ] `cr-0km.4` Image, volume and browser egress qualification  ← ready
- [ ] `cr-0km.5` Pinned runtime manifest and distribution review  (blocked)
- [ ] `cr-0km.6` Delivery-order record in PRD and design  ← ready
- [ ] `cr-0km.7` Domain contracts, provider ports and policy  (blocked)
- [x] `cr-0km.8` Recover DWS package candidate through independent pointer review
  - 📝 Recovery successor for cr-0km.1. Original stage superseded, not successfully landed; historical phase bridge metadata/root cr-717 untouched. New stage must independently earn review/check/ship/landing receipt. Initial admission blocked by unfinished predecessor before any model dispatch.

## [P2] Evidence core
- [ ] `cr-42y.1` Schema, migrations and transaction ownership  (blocked)
- [ ] `cr-42y.2` Artifact publication and structure sidecar  (blocked)
- [ ] `cr-42y.3` Document, snapshot, acquisition and membership records  (blocked)
- [ ] `cr-42y.4` Bounded direct read  (blocked)
- [ ] `cr-42y.5` Metadata-plus-outbox commit  (blocked)
- [ ] `cr-42y.6` Publication crash recovery  (blocked)

## [P3] Command surface: daemon and CLI
- [ ] `cr-3ah.1` Local command API transport  (blocked)
- [ ] `cr-3ah.2` CLI parsing, output and exit classes  (blocked)
- [ ] `cr-3ah.3` Configuration discovery and local access policy  (blocked)
- [ ] `cr-3ah.4` Workspace and run administration  (blocked)
- [ ] `cr-3ah.5` Administrative DTO reservation and diagnostics  (blocked)
- [ ] `cr-3ah.6` Process entry points and bootstrap mode  (blocked)

## [P4] Runtime controls
- [ ] `cr-wxi.1` Cross-process acquisition slots  (blocked)
- [ ] `cr-wxi.2` Store-maintenance and index-lifecycle gates  (blocked)
- [ ] `cr-wxi.3` Supervised child execution  (blocked)
- [ ] `cr-wxi.4` Admission, backpressure and fairness  (blocked)
- [ ] `cr-wxi.5` Residual provider work reconciliation  (blocked)

## [P5] Static acquisition
- [ ] `cr-a9a.1` Outbound URL safety policy  (blocked)
- [ ] `cr-a9a.2` Static HTTP acquisition  (blocked)
- [ ] `cr-a9a.3` HTML extraction and line map  (blocked)
- [ ] `cr-a9a.4` PDF extraction and page map  (blocked)
- [ ] `cr-a9a.5` Freshness reuse and acquisition coalescing  (blocked)

## [P6] Rendered acquisition
- [ ] `cr-u0m.1` Crawl4AI adapter and escalation signals  (blocked)
- [ ] `cr-u0m.2` Browser egress and isolation enforcement  (blocked)
- [ ] `cr-u0m.3` Rendered acquisition under shared limits  (blocked)

## [P7] Discovery
- [ ] `cr-b7e.1` SearXNG adapter  (blocked)
- [ ] `cr-b7e.2` DDGS fallback and capability routing  (blocked)
- [ ] `cr-b7e.3` Outcome typing and search history  (blocked)
- [ ] `cr-b7e.4` Effective dependency recording  (blocked)

## [P8] Retrieval
- [ ] `cr-ggx.1` Indexer ownership and collection views  (blocked)
- [ ] `cr-ggx.2` Outbox batch algorithm and generations  (blocked)
- [ ] `cr-ggx.3` Restricted QMD adapter  (blocked)
- [ ] `cr-ggx.4` Per-path verification of index updates  (blocked)
- [ ] `cr-ggx.5` Index rebuild from canonical artifacts  (blocked)
- [ ] `cr-ggx.6` Scoped candidate resolution and passage construction  (blocked)
- [ ] `cr-ggx.7` Cursor and generation consistency  (blocked)
- [ ] `cr-ggx.8` Coverage and index-state honesty  (blocked)

## [P9] Durable crawl
- [ ] `cr-o71.1` Job records, submission and idempotency  (blocked)
- [ ] `cr-o71.2` Claiming, leases and fencing  (blocked)
- [ ] `cr-o71.3` Restart recovery scan  (blocked)
- [ ] `cr-o71.4` DWS-owned frontier and scope enforcement  (blocked)
- [ ] `cr-o71.5` Budgets and reconciling counters  (blocked)
- [ ] `cr-o71.6` Cancellation and deadline separation  (blocked)
- [ ] `cr-o71.7` Bounded crawl manifest  (blocked)
- [ ] `cr-o71.8` Crawl and indexing coexistence in one worker  (blocked)


<!-- BD:GENERATED END -->

<!-- Human notes below this line are preserved across renders. Everything above is bd-generated; do not hand-edit it. -->
