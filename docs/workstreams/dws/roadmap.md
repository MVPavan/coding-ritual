# DWS Roadmap

**Spec:** `docs/plans/dws/cli-engine-implementation-plan.md`
**Baselines:** `docs/brainstorms/dws/DWS_PRD.md` v1.0 · `docs/brainstorms/dws/DWS_Design.md` v1.0
**Status:** Proposed phase structure. No implementation is authorized by this document.
**Revision:** r2 — independent critique applied (Codex `gpt-5.6-sol`, effort high, session `01a08ce3-c8b5`). Changes recorded in "Revision history".

Phases are components, not a schedule. Each has a demoable exit that can be
checked with real commands. Phase IDs `P1`–`P12` are the join key to Beads epics
(`[P1] Foundation …`). `Task N` references point at the governing spec's fourteen
tasks; this roadmap regroups them, it does not replace them.

Stage children are flat — no sub-tasks — but **not unordered**. Each phase
declares its internal `Stage edges`; those are seeded as real dependencies so a
merged phase cannot lose an edge the governing task DAG requires.

Planned code paths are ownership boundaries, not claims that files exist. `P1`
confirms the package location before any product file is created.

## Standing invariants

All fifteen from the technical design. Every phase is subject to all of them;
stages do not restate them.

| | Invariant |
|---|---|
| INV-01 | No default reasoning-model dependency |
| INV-02 | Public tools describe capabilities, not vendors |
| INV-03 | A retained snapshot ID never changes its content |
| INV-04 | Source location, acquisition event, and snapshot identity remain distinct |
| INV-05 | Every returned passage maps to its retained snapshot |
| INV-06 | Acknowledged durable jobs exist before their ID is returned |
| INV-07 | Successful acquisition does not require immediate indexing |
| INV-08 | QMD rebuild cannot delete DWS jobs or canonical evidence |
| INV-09 | Workspace scope is enforced before a result leaves DWS |
| INV-10 | No transaction spans network, browser, parser, or QMD work |
| INV-11 | Actual concurrent work and queued work are bounded |
| INV-12 | Policy denials never trigger bypass through another provider |
| INV-13 | Partial, stale, pending, expired, and unsupported outcomes are explicit |
| INV-14 | Normal CLI callers cannot bypass shared-state coordination |
| INV-15 | Pins and active references protect evidence during cleanup |

## Phase dependency graph

```text
P1 Foundation
 ├─► P2 Evidence core ──► P3 Command surface ──► P4 Runtime controls
 └─► P3                        │                      │
                               ├──────────────────────┤
                               ▼                      ▼
                        P5 Static acquisition    P7 Discovery
                               ├─► P6 Rendered acquisition
                               └─► P8 Retrieval ─┐
                                                 ├─► P9 Durable crawl
                                    P6 ──────────┘        │
                                                 P8 ──┬───┴─► P10 Operations
                                                      │            │
                                          P7 ─────────┴────► P11 Release ─► P12 MCP
```

| Edge | Reason |
|---|---|
| P1 → P2 | Storage implements the frozen contracts; a failed runtime probe changes them |
| P1 → P3 | Routes and CLI DTOs are the same frozen models |
| P2 → P3 | CLI acceptance requires real storage, not fixtures |
| P2 → P4 | Gates integrate with the publication and transaction boundaries |
| P3 → P4 | Gates integrate with daemon lifecycle and worker composition |
| P2 → P5 | Acquisition publishes through the evidence pipeline |
| P3 → P5 | Every slice is demonstrated through a real `dws fetch` |
| P4 → P5 | Acquisition slots must exist before concurrent acquisition |
| P3 → P7 | `dws search` needs the command surface |
| P4 → P7 | Discovery consumes the same permits and backpressure |
| P5 → P6 | Rendering is an escalation from the static path, not a parallel capability |
| P2 → P8 | The indexer drains outbox rows the evidence store commits |
| P4 → P8 | The exclusive index-lifecycle gate comes from runtime controls |
| P5 → P8 | Passages map to selectors the **static** pipeline produces; retrieval does not need the browser |
| P4 → P9 | Crawl execution depends on leases, permits and supervision |
| P5 → P9 | Crawl acquires pages through the acquisition pipeline |
| P6 → P9 | A crawl must be able to escalate a page to rendering |
| P8 → P9 | Crawled pages carry per-mapping index state and crawl-scoped retrieval |
| P8 → P10 | Retention interacts with index mappings and rebuild |
| P9 → P10 | Cleanup must honour crawl memberships and manifests |
| P7 → P11 | The release demonstration includes discovery |
| P10 → P11 | Release qualification runs against completed operations and recovery |
| P11 → P12 | Delivery B starts only after the engine passes its acceptance gate |

---

## P1 — Foundation: runtime qualification and frozen contracts

**Tasks 1–2.** Risk: deep. **Stage edges:** 5 ← 2, 3, 4 · 7 ← 1, 2, 3, 4, 5 (T1 → T2: contracts freeze only after the runtime is qualified).

**Goal:** A buildable engine-only `dws` distribution, recorded evidence that the
pinned runtime, QMD, browser and lock primitives can meet the design, and one
frozen contract and policy model that no transport or vendor type leaks into.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Package boundary and tooling | `dws/pyproject.toml`, `dws/uv.lock`, `dws/src/dws/`, `dws/tests/` | `uv sync --locked`; `uv run dws --help`; root `coding-ritual` package and its test collection unchanged |
| 2 | QMD lexical qualification | `dws/tests/qualification/`, `docs/verification/dws/runtime-qualification.md` | Cold init, lexical query/update/get, parseable output, concurrent search startup and interrupted update probed; no model download or inference on any accepted path (G-02) |
| 3 | Lock and child-process qualification | `dws/tests/qualification/` | Filesystem slot locks and lock lifetime across child processes on the target volume; parent death does not release ownership while a QMD child survives (G-03) |
| 4 | Image, volume and browser egress qualification | `dws/Dockerfile`, `dws/compose.yaml`, `docs/verification/dws/` | Recorded image contents, privileges, volumes and health; browser navigation and subrequest egress enforcement probed (G-05, G-09) |
| 5 | Pinned runtime manifest and distribution review | `docs/verification/dws/` machine-readable manifest | Python, QMD package/commit, Node/Bun, both SQLite runtimes, browser and parser builds and image digests recorded; no mutable `latest`; licence/notice review, native supply-chain and hosted-terms assessment recorded (NFR-012, G-12) |
| 6 | Delivery-order record | `docs/brainstorms/dws/DWS_PRD.md`, `docs/brainstorms/dws/DWS_Design.md` | CLI-first sequencing and the Delivery A release boundary recorded; MCP requirements retained for Delivery B; no accepted architectural history rewritten |
| 7 | Domain contracts, provider ports and policy | `dws/src/dws/domain/`, `ports/`, `policies/`, `dws/config/dws.example.yaml`, `docs/usage/dws/contracts.md` | `uv run pytest -q tests/contracts tests/unit/test_configuration.py`; unknown fields, elevated caller limits, invalid selectors, malformed cursors and fabricated dates rejected; core imports succeed with HTTP, MCP and provider adapters absent; **AT-034**: a fake provider is substituted through the interface alone with no core import of its vendor types |

**Exit (phase):** the package builds and `dws --help` runs; every essential
qualification probe has recorded evidence, or a recorded gate failure with an
explicit owner decision; contracts, capability descriptors and effective-policy
resolution are frozen and covered by tests. No product capability is claimed.
**Test focus:** characterization-first against real binaries and a fresh image
without model caches or credentials. Mock-only qualification does not count.

---

## P2 — Evidence core

**Task 3.** Risk: deep. **Stage edges:** 2 ← 1 · 3 ← 1 · 4 ← 2, 3 · 5 ← 1, 3 · 6 ← 2, 5.

**Goal:** A snapshot can be durably published and read back exactly, with source
history and workspace enforcement, while no search index exists at all.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Schema, migrations and transaction ownership | `dws/src/dws/adapters/storage/` | Bootstrap and migration gate; DWS schema version recorded; one owner per logical transaction; no transaction spans network, parser or subprocess work |
| 2 | Artifact publication and structure sidecar | `adapters/storage/`, evidence service | Staged hash validation, atomic same-filesystem publication, immutable bodies and sidecars; acquisition timestamps stay out of quoted text |
| 3 | Document, snapshot, acquisition and membership records | `adapters/storage/` | `AT-008`: equal-byte reuse preserves separate observations and memberships; a normalizer-version change stays distinguishable from a publisher update (INV-04) |
| 4 | Bounded direct read | evidence service | `tests/integration/test_evidence_store.py`: 1-based inclusive selectors; scope, retention, hash and selector validated; cross-workspace read fails; tombstone distinguished from integrity failure |
| 5 | Metadata-plus-outbox commit | `adapters/storage/` | The indexing-outbox row commits in the same short transaction as its evidence and membership change |
| 6 | Publication crash recovery | `adapters/storage/`, recovery path | `tests/integration/test_publication_recovery.py`: injected crashes before and after publication and commit leave acknowledged evidence or reconcilable orphans, never a successful missing body |

**Exit (phase):** an exact snapshot publishes and re-reads across a metadata
restart; `AT-009`: reads survive a change at the source and a new capture takes a
new identity; no snapshot is ever overwritten; a failed commit never
acknowledges a capture.
**Test focus:** integrity, membership and crash recovery, test-first, on real
temporary SQLite and filesystem with deterministic fault points.

---

## P3 — Command surface: daemon and CLI

**Task 4.** Risk: deep — it establishes the local trust boundary, the process
modes and every capability route. **Stage edges:** 2 ← 1 · 3 ← 1, 2 · 4 ← 1 · 5 ← 1 · 6 ← 3.

**Goal:** A real `dws` binary talking to one local command daemon over the
frozen contracts, with useful startup, scope management and diagnostics, before
any provider capability exists.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Local command API transport | `dws/src/dws/adapters/http/`, facade composition | FastAPI routes for the seven capabilities and `/v1/admin/...`; no FastMCP import anywhere in Delivery A |
| 2 | CLI parsing, output and exit classes | `dws/src/dws/adapters/cli/` | `tests/integration/test_cli_api.py` over a real subprocess: exit 0 valid result, 2 usage, 3 policy denial, 4 unavailable/capacity, 1 other; `--json` emits one schema-valid result on stdout, diagnostics on stderr; a failed historical job is data, not a failed transport call |
| 3 | Configuration discovery and local access policy | `adapters/cli/`, `adapters/http/` | `tests/integration/test_local_access.py`: Host/Origin/token policy enforced, secrets absent from output, daemon-absent failure explicit and never a silent second daemon (INV-14) |
| 4 | Workspace and run administration | facade, routes, CLI | Create/list/default workspace; optional run create/close; membership rules match the evidence model |
| 5 | Administrative DTO reservation and diagnostics | routes, facade | Manifest, pin/export, index, backup and doctor DTOs resolved ahead of their implementations; unavailable capabilities report capability status, never a fake success (INV-13) |
| 6 | Process entry points and bootstrap mode | `dws/src/dws/runtime/` | `dws init`, `serve`, `worker`, `restore`; online maintenance goes through the daemon; exclusive offline work is a distinct process mode |

**Exit (phase):** `dws --help`, scope commands and `doctor` work against a
temporary daemon, and CLI-decoded results are schema-identical to facade output.
**Test focus:** real CLI subprocess and loopback server with temporary
configuration; fakes only for capabilities not yet built.

---

## P4 — Runtime controls

**Task 5.** Risk: deep. **Stage edges:** 2 ← 1 · 3 ← 1 · 4 ← 1, 2 · 5 ← 1, 3.

**Goal:** API and worker obey one set of limits, one lock order, and survive
each other's death without inventing capacity.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Cross-process acquisition slots | `dws/src/dws/runtime/` | `tests/concurrency/test_runtime_controls.py`: two separate processes never multiply configured slots for HTTP, rendered, query or update classes (DD-006) |
| 2 | Store-maintenance and index-lifecycle gates | `runtime/`, storage integration | Lock order store-maintenance → index-lifecycle → short DB transaction; no transaction waits on a gate, provider or subprocess; the complete order is tested, not each lock alone |
| 3 | Supervised child execution | `runtime/`, worker composition | `tests/concurrency/test_child_ownership.py`: parent death cannot release a lock while its QMD child survives; child kills preserve ownership |
| 4 | Admission, backpressure and fairness | `runtime/`, daemon lifecycle | Saturated queues return typed capacity results with retry hints; a **synthetic long-running work class** saturates the rendered and query slots while the control path stays responsive; queue wait recorded separately from execution. *The real browser-plus-crawl integration of this property is verified in P11 stage 5, where both participants exist.* |
| 5 | Residual provider work reconciliation | `runtime/` | A provider handle that outlives its request is preserved and reconciled before its capacity is treated as free |

**Exit (phase):** concurrency tests using real processes and OS locks on the
target volume demonstrate that slot multiplication, lock inversion and orphaned
child ownership cannot occur.
**Test focus:** crash-injection-first. Unsupported lock semantics block release
and require another qualified coordinator, never per-process semaphores.

---

## P5 — Static acquisition

**Task 6.** Risk: deep. **Stage edges:** 2 ← 1 · 3 ← 2 · 4 ← 2 · 5 ← 3, 4.

**Goal:** `dws fetch` captures suitable public HTML, text and text-bearing PDFs
without a browser, and `dws read` returns the exact retained content with
indexing absent.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Outbound URL safety policy | `dws/src/dws/policies/` | `AT-026`: loopback, private, link-local, metadata and multicast targets, redirects, alternate encodings and DNS changes are blocked; validated targets bind to the actual connection so a second resolution cannot defeat policy; provider-connectivity and public-target allowlists stay separate (FR-030) |
| 2 | Static HTTP acquisition | `dws/src/dws/adapters/acquisition/` | `AT-028`: bounded bytes, deadlines, decompression and redirects; media inspected rather than filename suffix; oversized and malformed input stops without uncontrolled staging growth |
| 3 | HTML extraction and line map | `dws/src/dws/adapters/extraction/` | `AT-007`: normalized body with stable line numbering and a structure sidecar; code, headings and simple tables preserved where supported; a challenge page returning HTTP 200 is not a success (G-06) |
| 4 | PDF extraction and page map | `adapters/extraction/` | `AT-006`: text-bearing PDFs carry reliable page provenance; scanned or complex layouts are warned or refused, never fabricated (FR-009, FR-010) |
| 5 | Freshness reuse and acquisition coalescing | `services/`, `adapters/storage/` | A sufficiently fresh compatible capture satisfies fetch without contacting the source; conditional revalidation updates observations without changing capture time; **in-flight claims are keyed by workspace** and by freshness, render mode and policy version so incompatible requests never merge; a follower detaching does not cancel work another caller still needs |

**Exit (phase):** a fixture corpus of static HTML, text PDF and scanned PDF is
captured correctly or explicitly refused through real `dws fetch`, and every
returned excerpt matches its retained normalized body via `dws read`.
**Test focus:** local fixture servers under isolated test-network policy.
Production URL safety is never relaxed to accommodate a fixture.

---

## P6 — Rendered acquisition

**Task 8.** Risk: deep — externally constrained and gated on browser egress
enforcement. **Stage edges:** 2 ← 1 · 3 ← 1, 2.

**Goal:** Pages that genuinely need rendering are acquired through Crawl4AI
under the same policy, limits and evidence pipeline as the static path.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Crawl4AI adapter and escalation signals | `dws/src/dws/adapters/acquisition/` | `AT-005`: a browser-required fixture escalates within budget and a plain HTML or text fixture starts no browser (FR-008); escalation happens only on a declared signal or caller policy; provider-normalized output still passes through the same document pipeline |
| 2 | Browser egress and isolation enforcement | `dws/compose.yaml`, `config/`, `policies/` | Navigation and subrequests from the browser service obey the same outbound policy; the service holds no DWS volume, Docker socket, host home or credentials; no host port is published (G-05, G-09) |
| 3 | Rendered acquisition under shared limits | `adapters/acquisition/`, `runtime/` | Rendered work consumes the rendered slot class; a remote job that outlives its deadline is reconciled rather than assumed stopped; a policy denial is never retried through another provider (INV-12) |

**Exit (phase):** a JS-shell fixture that the static path cannot extract is
captured through the browser path, with egress enforcement demonstrated; the
static path remains the default and is untouched.
**Failure containment:** if the egress gate cannot be satisfied, this phase is
gated or disabled without blocking P8 retrieval, which depends only on P5.

---

## P7 — Discovery

**Task 7.** Risk: standard — uncertainty is contained behind frozen provider
contracts. **Stage edges:** 2 ← 1 · 3 ← 1, 2 · 4 ← 1, 2.

**Goal:** `dws search` returns bounded ranked candidates with honest filter and
fallback semantics, and never rewrites the caller's query.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | SearXNG adapter | `dws/src/dws/adapters/search/`, `dws/config/searxng/` | JSON output explicitly enabled; unsupported freshness or domain filters are declared, never silently dropped; no page bodies in results (FR-002) |
| 2 | DDGS fallback and capability routing | `adapters/search/`, `services/` | `AT-003`: a primary timeout yields a normalized fallback result with both attempts recorded (FR-004) |
| 3 | Outcome typing and search history | `services/`, `adapters/storage/` | `AT-004`: legitimate empty result, malformed output, unsupported filter and all-provider failure are four distinct outcomes; the requested query is preserved with no model rewrite (FR-003); cache key includes policy and filter identity; age disclosed |
| 4 | Effective dependency recording | `services/`, diagnostics | Shared upstream engines are recorded so a fallback is not represented as independent without evidence (G-07) |

**Exit (phase):** `dws search` returns compact records, the original query
preserved, and fallback attempts visible in the result.
**Test focus:** deterministic fixture providers plus a separately labelled live
smoke suite that cannot destabilise the core tests.

---

## P8 — Retrieval

**Tasks 9–10.** Risk: deep. **Stage edges:** 2 ← 1 · 3 ← 1 · 4 ← 2, 3 · 5 ← 4 · 6 ← 3, 4 (T9 → T10) · 7 ← 6 · 8 ← 6, 7.

**Goal:** Retained evidence becomes searchable asynchronously and returns
bounded, verified, correctly scoped passages with honest coverage.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Indexer ownership and collection views | `dws/src/dws/worker/`, `adapters/retrieval/` | One indexer owns collection mutations; a per-workspace view is materialised only after metadata commit, never the live canonical directory (DD-004) |
| 2 | Outbox batch algorithm and generations | `worker/` | Watermark selection and coalescing; `pending → applying → ready` per workspace/snapshot mapping; a partial QMD failure leaves a dirty, unready generation (DD-005, DD-007) |
| 3 | Restricted QMD adapter | `adapters/retrieval/` | `AT-015`: argument arrays only, allowlisted operations, controlled working directory, minimal environment, deadlines and bounded output; no vector, hybrid, expansion or rerank path with model credentials absent and downloads blocked (FR-015, G-02) |
| 4 | Per-path verification of index updates | `worker/` | Every intended path verified through supported lookup or status behaviour; a zero exit code alone is not proof of indexing |
| 5 | Index rebuild from canonical artifacts | `worker/`, admin routes | `AT-019`: deleting the QMD index and rebuilding from retained artifacts leaves DWS jobs, metadata and pins intact (INV-08) |
| 6 | Scoped candidate resolution and passage construction | `dws/src/dws/services/` | `AT-016`, `AT-017`: membership resolved from DWS metadata before results leave; exact passage text and selectors verified against the retained body; overlapping windows merged; title-only matches labelled rather than given invented body text; scoped emptiness never inferred from a tiny global top-K (G-04) |
| 7 | Cursor and generation consistency | `services/`, contracts | `AT-029`: cursors bind scope, query digest and index generation; a stale generation is rejected or explicitly restarted, never stitched across generations; file protection is held through response construction |
| 8 | Coverage and index-state honesty | `services/`, contracts | `AT-018`: a just-captured snapshot is readable while pending; empty index, pending updates, restrictive filters and genuine absence are four distinguishable outcomes; ordinary pending mappings are separated from a globally dirty index (FR-020, INV-13) |

**Exit (phase):** `dws retrieve` returns verified passages for the requested
scope and discloses index lag; `dws read` works with the index unavailable; a
deleted index rebuilds from artifacts alone.
**Test focus:** a hand-checked fixture corpus with cross-workspace term
collisions, long documents and title-only matches. G-04 is release-blocking.

---

## P9 — Durable crawl

**Tasks 11–12.** Risk: deep. **Stage edges:** 2 ← 1 · 3 ← 1, 2 · 4 ← 1, 2, 3 (T11 → T12) · 5 ← 4 · 6 ← 4 · 7 ← 4, 5 · 8 ← 4.

**Goal:** An acknowledged crawl survives restarts, respects every budget, and
reports counts that reconcile with its manifest.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Job records, submission and idempotency | `dws/src/dws/worker/`, `adapters/storage/` | `AT-011`: the job exists when polled immediately after acknowledgement (INV-06); a repeated key returns the same handle; a conflicting payload under the same key is rejected, not run twice |
| 2 | Claiming, leases and fencing | `worker/` | `AT-012`: a stale owner cannot overwrite newer job state; completion and checkpoint updates require the current owner and epoch; an API restart does not disturb worker ownership |
| 3 | Restart recovery scan | `worker/` | `AT-013`: queued work, expired claims and incomplete publication each recover or fail explicitly, without blindly re-running completed pages; failure history is preserved, not erased |
| 4 | DWS-owned frontier and scope enforcement | `services/`, `worker/` | `AT-010`: cycles and off-scope links are not followed; `same_domain` is not implicit subdomain permission; canonicalisation preserves meaningful query parameters and does not trust HTML canonical tags unconditionally (DD-002) |
| 5 | Budgets and reconciling counters | `worker/`, contracts | Distinct scheduled URLs counted including failures; separate attempt, byte, time and per-domain ceilings so retries cannot evade the page budget; `scheduled = queued + in_flight + succeeded + failed + skipped_after_scheduling` |
| 6 | Cancellation and deadline separation | `worker/`, facade | `AT-014`: new work stops, provider cancellation is requested, residual activity is disclosed, and acquired snapshots are not deleted as a side effect; request, job, provider and indexing deadlines stay distinct |
| 7 | Bounded crawl manifest | facade, routes, CLI | Cursor-based per-URL outcomes with an explicit stop reason; `completed` with `outcome=partial` never implies full coverage; no page bodies in a manifest by default |
| 8 | Crawl and indexing coexistence in one worker | `worker/`, `runtime/` | Crawl execution and index batches share the single worker fairly; a long crawl does not starve indexing and an index batch does not stall crawl checkpointing; queue delay measured separately for each class |

**Exit (phase):** a bounded crawl survives an API restart and a worker kill,
cancels cleanly with useful partial results, and its final counters reconcile
with a paginated manifest.
**Test focus:** fault injection at multiple checkpoints, test-first.

---

## P10 — Operations and recovery

**Task 13.** Risk: deep — the only phase that deletes anything. **Stage edges:** 2 ← 1 · 3 ← 1, 2 · 4 ← 1 · 5 ← 3, 4 · 6 ← 3, 4.

**Goal:** Evidence survives cleanup, upgrade and restore, and every destructive
operation is previewable and reversible in the ways the baselines promise.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Retention, freshness and expiry policy | `dws/src/dws/policies/`, `worker/` | Freshness, retention, pinning and index inclusion remain four independent decisions; a stale-but-retained capture is never labelled current; `force_refresh` overrides reuse (FR-023) |
| 2 | Pin, unpin and bounded export | facade, `/v1/admin/...`, CLI | Pinned artifacts are never silently evicted; export is explicit, bounded and recorded (FR-024, INV-15) |
| 3 | Garbage collection, tombstones and disk pressure | `worker/`, admin routes | `AT-023`, `AT-024`: dry-run matches actual effect; pins and active references are re-checked under the maintenance gate; an expired snapshot URI returns `ARTIFACT_EXPIRED` and never different content; disk pressure pauses bulk acquisition instead of deleting pinned evidence |
| 4 | Quiesced backup and verified restore | admin routes, `runtime/` | `AT-025`: backup captures a consistent metadata plus artifact set including WAL state; restore is demonstrated, QMD is rebuilt from artifacts, and a known pinned citation verifies (DD-009) |
| 5 | Maintenance interruption recovery | `worker/`, `runtime/` | An interrupted GC, backup, rebuild or migration leaves reconcilable state; startup recovery resolves dirty index generations and interrupted maintenance ownership without destroying canonical evidence |
| 6 | Upgrade, rollback and schema compatibility | `runtime/`, migrations, `docs/usage/dws/` | `AT-031`: dependency and image upgrade with pinned builds; migration and readiness gates prevent traffic against an unready index; replacing a container never silently rebuilds or deletes the corpus; rollback path recorded |

**Exit (phase):** pin, expire, clean, back up, restore and upgrade all execute
with pinned evidence intact and every destructive step previewable.
**Test focus:** GC-versus-read races, restore without QMD, interrupted
maintenance — test-first.

---

## P11 — Release qualification

**Task 14.** Risk: deep — this phase decides whether the engine ships.
**Stage edges:** 2 ← 1 · 3 ← 1 · 4 ← 1 · 5 ← 1 · 6 ← 1, 2, 3, 4, 5.

**Goal:** A fresh installation demonstrates the whole engine through `dws`
commands alone, with FastMCP, model credentials and hosted credentials absent.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | Compose bootstrap, readiness and restart | `dws/compose.yaml`, `dws/Dockerfile`, `dws/config/` | `AT-001`, `AT-035`: one-shot bootstrap runs migrations and collection initialisation before traffic (DD-008); readiness is capability-aware so stored reads work while discovery or indexing is unavailable; only the approved loopback port is published and no upstream ports are exposed |
| 2 | Sanitized diagnostics and structured logging | capability diagnostics, owning modules | `FR-033`: admission wait, provider latency, index lag, cache events, retries and failures recorded locally with secrets redacted; `dws doctor` reports actionable capability and runtime status |
| 3 | Adversarial input and bounded-output qualification | `dws/tests/acceptance/` | `AT-027`, `AT-029`: secret-looking data, path traversal and shell metacharacters cause no execution or leakage; very large search, crawl, read and retrieve results stay valid JSON — paginated or explicitly truncated, never byte-cut |
| 4 | Host CLI workflow template | `docs/usage/dws/host-cli-workflow.md`, `docs/usage/dws/getting-started.md` | `AT-030`, `FR-034`: a host workflow performs search → fetch → retrieve → read and pins/exports cited evidence using only `dws` commands, with query formulation and synthesis left to the host and DWS generating no report; core works with no such template installed |
| 5 | Measured concurrency qualification | `dws/tests/concurrency/`, `docs/verification/dws/` | `AT-020`, `AT-022`: bursts of 1, 5, 10, 20 and 50 callers with the fixture corpus; admission limits hold; job status and cancel stay responsive during real browser and crawl saturation; queue, SQLite, QMD and browser costs reported separately as measurements on declared hardware, never as capacity promises (G-10) |
| 6 | Release gate and acceptance matrix | `docs/verification/dws/cli-release-qualification.md`, `dws/tests/acceptance/`, `tests/live/` | `uv sync --locked`; `docker compose up -d --build` on a fresh fixture environment; `uv run pytest -q -m 'not live'` including `tests/acceptance`; `uv run ruff check src tests`; `uv run ruff format --check src tests`; `uv run mypy --strict src/dws`; `tests/live` only against permitted providers. Every Delivery A `AT-*` carries an explicit disposition — passed, skipped with reason, or not applicable — and the spec's seven release-evidence questions are answered with real command output. An unavailable required check is unverified, not passed. G-12 distribution acceptability signed off |

**Exit (phase):** a fresh Compose installation performs search → fetch → crawl →
retrieve → read → pin → export → backup → restore using only `dws` commands,
with FastMCP uninstalled, model downloads blocked and hosted credentials absent,
and every quality gate above recorded as run.
**Test focus:** observed behaviour. No gate is satisfied by a diagram, a
mock-only test, file presence or a healthy container.

---

## P12 — MCP adapter (Delivery B)

**Spec §8.** Risk: deep — it resolves release-blocking G-01 and touches host
compatibility, daemon lifespan, local access and protocol parity. "Thin"
describes code volume, not integration risk. Its file-level plan is written just
in time at `docs/plans/dws/mcp-wrapper-implementation-plan.md`; stage children
are seeded then, not now.

**Goal:** The same seven capabilities through MCP over the existing facade, with
the engine still fully usable when MCP is absent.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| 1 | FastMCP build and host qualification | optional dependency extra, `docs/verification/dws/` | G-01: the exact standalone FastMCP build and the actual intended MCP host are tested and pinned; prereleases declared |
| 2 | Adapter around the facade | `dws/src/dws/adapters/mcp/` | Lifespan composed with the existing daemon; MCP handlers spawn no second worker and open no unmanaged QMD index |
| 3 | Seven capability mappings | `adapters/mcp/` | Truthful capability descriptions and negotiated structured result types; no research, vendor-specific, shell or SQL tool added (INV-02) |
| 4 | Resource and manifest projection | `adapters/mcp/` | `dws://snapshot/...` and bounded manifests pass the same membership, retention, size and integrity checks; the direct `read` compatibility path is preserved |
| 5 | Error, busy and deadline translation | `adapters/mcp/` | Durable job lifetimes are unchanged; client disconnection does not cancel a crawl by implication |
| 6 | Parity and optionality proof | `dws/tests/` | `AT-002`, `AT-030`, `AT-035`, `AT-036`, NFR-009: identical payloads through CLI and MCP, mixed-load concurrency, real host reachability, and a re-run engine-only installation with MCP uninstalled |
| 7 | Host installation and integration guidance | `docs/usage/dws/` | A tested host MCP installation and a research-skill template that never treats search snippets as verified source content |

**Exit (phase):** the same evidence operation succeeds through CLI and MCP with
identical DWS semantics, and the engine release still works with MCP disabled.
Native MCP Tasks remain a separate optional extension over the same job state.

---

## Open decisions carried into execution

| Question | Resolve in | Continue-or-stop rule |
|---|---|---|
| Nested `dws/` package location in this repository | P1 s1 | Confirm against the live checkout; record a different location before creating files and update every owned path |
| QMD lexical path is genuinely model-free (G-02) | P1 s2, P8 s3 | A no-model failure blocks the retrieval baseline; investigate the pinned build before changing technology |
| QMD lifecycle and subprocess ownership (G-03) | P1 s3, P4, P8 | Reduce query concurrency to one if qualified; a persistent wrapper needs recorded evidence |
| Filesystem lock semantics on the target volume (DD-006) | P1 s3, P4 s1 | Unsupported semantics require another qualified coordinator, never independent in-process semaphores |
| Scope and per-path verification (G-04) | P1 s2, P8 s4–s8 | Bounded candidate expansion or a labelled direct scan may serve as fallback with explicit incomplete coverage; never a false complete result |
| HTML and PDF normalizer selection | P5 s3–s4 | Trafilatura and pypdf are candidates, not accepted choices; golden extraction fixtures and licence review decide (G-06, G-12) |
| Browser egress enforcement (G-05, G-09) | P1 s4, P6 s2 | An unverified egress path cannot ship as generally safe; gate or disable P6 — it must not block P8 |
| Hardware limits, quotas and retention durations (G-10) | P10 s1, P11 s5 | Begin with documented configurable limits, measure, report the supported workload; hard limits never come from callers |
| Optional providers: Firecrawl, TinyFish, Spider | Not scheduled | Requires an acquisition corpus the baseline stack demonstrably fails on (G-07, G-08); reputation is not evidence |

## Revision history

**r2** — independent critique (Codex `gpt-5.6-sol`, high) applied before seeding:

- Split the former P5 into **P5 static acquisition** and **P6 rendered
  acquisition**, so a failed browser-egress gate cannot block retrieval.
  Retrieval now depends on the static path only.
- Split the former P9 into **P10 operations and recovery** and **P11 release
  qualification**, making the T13 → T14 gate an explicit edge.
- Added **`Stage edges`** to every phase so the five task dependencies that the
  phase grouping would otherwise hide are seeded as real dependencies.
- Restored **INV-01…15** in place of the twelve-item excerpt.
- Added missing Delivery A acceptance: **AT-027, AT-029, AT-030/FR-034 with the
  host CLI workflow template, AT-031 upgrade and rollback, AT-034
  fake-provider substitution**, the full **G-12** licence and supply-chain
  review, **FR-033** sanitized diagnostics, and Task 14's exact command gates.
- Restored three compressed requirements: acquisition claims **keyed by
  workspace**, **cursor binding to scope/query/generation**, and **crawl versus
  indexing fairness** in the single worker.
- Moved integrated acceptance to the phase where all participants exist: the
  browser-saturation control-path check moved from P4 to P11 s5; interrupted
  maintenance recovery moved from the crawl phase to P10 s5.
- Raised **P3** and **P12** to `deep`.
- Corrected the charter's evidence-lifetime claim: retained snapshots are
  immutable, pinned evidence survives cleanup, unpinned evidence may expire.
