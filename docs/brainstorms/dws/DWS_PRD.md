# Deep Web Search (DWS)
## Product Requirements Document, Architecture Baseline, and Decision Record

**Canonical filename:** `DWS_PRD.md`  
**Document version:** 1.0  
**Prepared:** 9 September 2026  
**Product owner:** The project owner / primary user  
**Product status:** Design-stage; this document does not assert that DWS has been implemented or benchmarked.  
**Scope:** Personal, local-first web discovery, acquisition, and evidence retrieval.  
**CLI name:** `dws`

> **Product definition:** DWS is a reusable, model-free-by-default web evidence acquisition and retrieval service. It searches the public web, fetches and crawls selected sources, preserves useful snapshots, and returns bounded, source-linked evidence. Research planning, interpretation, summarization, and report writing belong to the calling host’s agent and skills—not to DWS core.

---

## 0. How to use this document

This is the consolidated source of truth for **what DWS should do, why the current design was chosen, what was rejected or deferred, and what evidence would justify changing those decisions**. It consolidates the discussion; it is not a verbatim chat transcript or a claim that every earlier assistant statement was correct.

### 0.1 Decision and requirement status

| Label | Meaning |
|---|---|
| **Accepted** | Explicit user choice or established direction in the discussion. Do not reverse silently. |
| **Proposed baseline** | A concrete implementation recommendation added to make the PRD actionable. It is not represented as an already approved user instruction. |
| **Optional** | A supported extension that is not required for the default installation. |
| **Deferred** | Deliberately outside V1; revisit only when the stated trigger occurs. |
| **Rejected for V1** | Considered and not selected for this workload. This is not a universal judgment about the technology. |
| **Verification gate** | A version-, platform-, or behavior-sensitive question that must be tested before release. |

**Requirement notation:** `FR-*` identifies functional requirements, `NFR-*` non-functional requirements, `AT-*` acceptance tests, `ADR-*` architecture decisions, and `G-*` verification gates. “Must” defines required behavior of the proposed V1 baseline. Numeric defaults remain proposed until tested and configured.

### 0.2 Authority and change control

For DWS design intent, use this precedence: **new explicit owner decision → updated accepted ADR → requirements and contracts in this document → examples → historical discussion**. For external technical facts, verified upstream behavior takes precedence over previous chat explanations. A code implementation that deviates from a requirement must either be corrected or accompanied by an approved PRD/ADR update.

Keep this file in the DWS repository under version control. Record decision changes in Section 24 rather than rewriting history. Generated presentations, reports, or document exports are snapshots, not independent specifications.

### 0.3 Evidence boundaries

The linked primary sources were inspected for this consolidation. Some retrieved pages are cached, and `main` branches are mutable. They establish capabilities and risks; they are **not a dependency lockfile**. Exact versions, image digests, compatibility checks, and runtime build identities must be frozen during milestone M0.

Earlier conversation asserted several precise FastMCP releases and SDK behaviors. This PRD preserves the user’s **FastMCP choice and 4.x target**, but does not reuse inconsistent patch-version claims as installation instructions. Official installation material and retrieved release snapshots do not provide one consistently current view. Resolve the exact supported build through G-01. [S03] [S04]

The earlier deep-research requests are part of the discussion history, but their completed reports are not present in the supplied conversation. This PRD does not claim to incorporate findings from unavailable reports.

### Contents

1. [Executive baseline](#1-executive-baseline)
2. [User, workload, and problem statement](#2-user-workload-and-problem-statement)
3. [Goals, outcomes, and non-goals](#3-goals-outcomes-and-non-goals)
4. [Product boundaries and terminology](#4-product-boundaries-and-terminology)
5. [Primary user journeys](#5-primary-user-journeys)
6. [Architecture and ownership](#6-architecture-and-ownership)
7. [Functional requirements](#7-functional-requirements)
8. [Public interfaces and example contracts](#8-public-interfaces-and-example-contracts)
9. [Provider stack and fallback policy](#9-provider-stack-and-fallback-policy)
10. [Document pipeline and data model](#10-document-pipeline-and-data-model)
11. [Retention, cache, and indexing policy](#11-retention-cache-and-indexing-policy)
12. [QMD integration](#12-qmd-integration)
13. [Concurrency and database access](#13-concurrency-and-database-access)
14. [Durable jobs and failure handling](#14-durable-jobs-and-failure-handling)
15. [Single-Compose deployment](#15-single-compose-deployment)
16. [Local security and trust boundaries](#16-local-security-and-trust-boundaries)
17. [Non-functional requirements and metrics](#17-non-functional-requirements-and-metrics)
18. [Host-side agents, skills, and plugins](#18-host-side-agents-skills-and-plugins)
19. [Delivery milestones and acceptance tests](#19-delivery-milestones-and-acceptance-tests)
20. [Technology decision matrix](#20-technology-decision-matrix)
21. [Architecture decision records](#21-architecture-decision-records)
22. [Discussion chronology and superseded statements](#22-discussion-chronology-and-superseded-statements)
23. [Risks, open questions, and verification gates](#23-risks-open-questions-and-verification-gates)
24. [Change log and implementation handoff](#24-change-log-and-implementation-handoff)
25. [Primary-source ledger](#25-primary-source-ledger)

---

## 1. Executive baseline

### 1.1 The decisions that define DWS

| Area | Baseline | Status |
|---|---|---|
| Name | Deep Web Search; abbreviation DWS; command `dws` | Accepted |
| Audience | One person, many projects and concurrent agents; not enterprise SaaS | Accepted |
| Deployment | One top-level Docker Compose entry point on one machine | Accepted |
| MCP framework | Python FastMCP; target the compatible 4.x line and pin a tested build | Accepted; exact build gated |
| Core | Python services with no MCP, host, or research-agent dependency | Accepted |
| Research | Host-side agent + skill + optional structured profile | Accepted |
| Discovery | SearXNG as primary search provider | Accepted |
| Acquisition | Crawl4AI as primary browser-capable fetch/crawl component | Accepted |
| Search backup | DDGS as lightweight local-library fallback; TinyFish Search opt-in | Proposed baseline |
| Hard-page backup | TinyFish Fetch/Browser opt-in; Firecrawl self-hosted profile to evaluate | Proposed / optional |
| Retrieval | Original `tobi/qmd`, lexical FTS5/BM25 path only | Accepted |
| DWS state | DWS-owned SQLite file for metadata, jobs, provenance, and policies | Accepted |
| QMD state | Separate QMD-owned SQLite file; no DWS tables or direct schema dependence | Accepted |
| Artifacts | Retain normalized snapshots independently of QMD; original files selectively | Accepted direction; retention defaults proposed |
| Vectors and LLMs | No embeddings, reranking model, query-expansion model, or report model in default core | Accepted |
| Concurrency | Shared service, bounded QMD searches, one QMD updater, short SQLite transactions | Accepted direction; limits proposed |
| Turso | Do not migrate now; reconsider DWS metadata separately if measured contention warrants it | Accepted direction / deferred |
| Jobs | DWS-owned durable job model; MCP Tasks are an optional protocol projection | Accepted |

### 1.2 Recommended default installation

The proposed runtime has `dws-api`, `dws-worker`, `searxng`, and a `crawl4ai` service. API and worker may use the same DWS image. QMD runs as a dependency inside the DWS runtime, not as a separately exposed MCP server. DDGS is a library dependency. A lightweight HTTP fetch/extraction path is proposed inside DWS. Vendor-required supporting processes must be declared honestly; “no DWS Redis queue” does not mean an upstream image contains no Redis process.

Firecrawl and additional supporting services belong to an **optional Compose profile**, not automatically to every startup. TinyFish adapters require explicit configuration and may send queries or target URLs to a hosted service. The base product must still start and perform useful search, acquisition, and local retrieval without paid-provider credentials.

### 1.3 The central trade-off

DWS deliberately chooses **a small, dependable set of capabilities with recoverable evidence** over maximum feature count. It does not promise to access every website, understand every PDF, or eliminate all repeated work. It must be explicit about failed acquisition, stale content, unindexed documents, incomplete scope, and expired artifacts.

---

## 2. User, workload, and problem statement

### 2.1 Primary user

The primary user is an experienced Python/FastAPI developer who wants one reusable utility across projects. Examples include technical architecture research, learning about AI memory systems, general topic research, and Funda’s public-equity research. Funda is a consumer, not the schema or policy model for DWS.

Multiple agents may act on behalf of the same person. “Single user” must not be interpreted as “one sequential request.” Conversely, many agent identities do not by themselves justify distributed databases or a multi-tenant platform.

### 2.2 Expected workload

The expected pattern is intermittent, sometimes intensive research. A topic may be investigated once, but the same source may still be revisited several times within that investigation: after an excerpt, during comparison, to verify a quotation, or after a host context reset.

Cross-project cache reuse is unknown. No cache-hit percentage, document count, CPU requirement, or simultaneous-agent capacity has been measured on the user’s machine. These are instrumented properties, not product assumptions.

### 2.3 Problems to solve

- Repeated provider integrations across projects create inconsistent schemas, failures, and secrets handling.
- Search snippets are useful for discovery but insufficient as evidence of what a source actually says.
- Returning entire crawls or PDFs floods host context and wastes model tokens.
- Unbounded crawling, indexing, and subprocess creation can overwhelm a personal machine.
- A disposable search index alone does not preserve provenance or make interrupted work recoverable.
- A generic embedded research agent couples retrieval infrastructure to one methodology and model stack.

### 2.4 Product promise

A caller should be able to request a capability without knowing its provider, obtain compact and traceable results, read more only when necessary, and continue after a short-lived client disconnect without losing acknowledged durable work.

---

## 3. Goals, outcomes, and non-goals

### 3.1 Goals

| Goal | Observable outcome |
|---|---|
| Reuse | The same capability contracts work through MCP, CLI, and internal Python services. |
| Provider replacement | Add a provider through an adapter, configuration, and tests without changing the public contract. |
| Evidence preservation | A retained citation resolves to a specific captured snapshot and location, not silently to a changed live page. |
| Token discipline | Search returns metadata; fetch returns an excerpt and handle; crawl returns a job and manifest; retrieval returns bounded passages. |
| Local simplicity | One Compose invocation operates the baseline; state survives container replacement. |
| No hidden inference | Default operations execute with no model credentials and no model-weight downloads. |
| Recoverable jobs | Accepted long jobs are persisted before acknowledgement and can recover or fail explicitly after restart. |
| Honest degradation | Provider failures, missing coverage, index lag, and stale cache use are visible in machine-readable outputs. |
| Controlled parallelism | Agents may submit concurrently while local work is admitted according to measured capacity. |

### 3.2 V1 non-goals

DWS V1 does not include an autonomous research planner, investment recommendations, generic report synthesis, a vector database, always-on embedding generation, a general browser-control agent, a public API product, enterprise identity, distributed scheduling, a cluster manager, a knowledge graph, or full-web archival.

Authenticated private-site automation, login-cookie import, unrestricted browser scripts, interactive dashboards, OCR at scale, audio/video transcription, and arbitrary local-file search are outside the default public-web workflow. They require separate designs and explicit opt-in if added.

The product name does not imply dark-web access. “Deep” describes investigation beyond snippets and selected link traversal, not access to restricted sources.

### 3.3 Success is not “all research completed”

DWS is successful when acquisition and retrieval contracts are satisfied. Whether an investment thesis is persuasive or a technical report is complete belongs to the host workflow. DWS must not invent a research-completeness score to conceal this boundary.

---

## 4. Product boundaries and terminology

### 4.1 Five distinct operations

| Concept | Meaning | Owner |
|---|---|---|
| Search | Discover candidate URLs and lightweight records | DWS |
| Fetch | Acquire one selected URL and normalize a snapshot | DWS |
| Crawl | Traverse a bounded link graph and acquire selected pages | DWS |
| Retrieve / read | Find or read evidence from retained artifacts | DWS |
| Research | Define questions, judge adequacy, reconcile evidence, synthesize conclusions | Host agent and skill |

A crawl is conceptually built on page acquisition, but a native crawl provider need not call the public `fetch` tool repeatedly. Both paths must feed the same document pipeline.

### 4.2 “Deterministic” is an architectural constraint

Here, deterministic means **ordinary code and explicit policy control the default DWS workflow; a reasoning model is not required to decide how it runs**. It does not mean the internet is immutable or that browser execution, search ranking, extraction heuristics, timestamps, and provider responses are bit-for-bit reproducible.

For reproducibility, persist the inputs, configuration version, provider attempts, normalization version, and snapshot hashes. Deterministic extraction can still be incomplete or wrong; it must expose quality signals rather than claim certainty.

TinyFish’s Agent product is not interchangeable with its Search, Fetch, and Browser surfaces. The Agent product accepts natural-language goals; using it would introduce outsourced agent behavior. V1 may enable targeted hosted acquisition, but must not quietly route an ordinary fetch to an autonomous research agent. [S12]

### 4.3 Identifiers are not interchangeable

| Identifier | Meaning |
|---|---|
| `workspace_id` | Logical project/topic scope; an organizational boundary, not enterprise tenancy |
| `run_id` | Optional caller-provided correlation for a host research session; DWS does not execute its reasoning |
| `search_id` | One discovery request/result set |
| `document_id` | Logical source/document identity across captures |
| `snapshot_id` | Immutable captured/normalized version used for evidence |
| `crawl_id` | Crawl specification, membership, and manifest |
| `job_id` | Execution lifecycle and progress |
| `provider_job_id` | External provider’s execution handle, if any |
| QMD document key/path | Internal retrieval mapping; not DWS’s primary identifier |
| MCP task handle | Optional adapter-level representation of work |
| MCP continuation state | Protocol interaction continuation, not job progress or artifact storage |

The earlier `research_id` examples were useful while considering an internal research orchestrator. The final core uses workspaces, runs, documents, snapshots, crawls, and jobs. A host’s research identifier may be stored as opaque correlation metadata, not as evidence that DWS contains a ResearchService.

### 4.4 URI conventions

New interfaces use `dws://`, not the earlier illustrative `deepweb://` convention:

```text
dws://snapshot/{snapshot_id}/content
dws://snapshot/{snapshot_id}/metadata
dws://snapshot/{snapshot_id}/section/{section_id}
dws://crawl/{crawl_id}/manifest
```

The source URL is where information came from. A DWS URI identifies a view of the retained capture. A URI is not a persistence mechanism. Resource addresses also do not guarantee that a particular host makes them model-callable; bounded read tools provide a compatibility path. [S02]

---

## 5. Primary user journeys

### Journey A — One-off technical research

A host skill scopes “memory systems for AI agents,” generates queries, and calls DWS search. It selects several sources, fetches them, retrieves passages about persistence and retrieval, and reads exact sections for verification. The host writes the report and pins the snapshots it needs to preserve. DWS does not generate subquestions or summaries.

**Success:** all returned passages identify their captured source; the host never needs entire unrelated documents in context; default DWS work invokes no model.

### Journey B — Funda reuses the same infrastructure

A Funda skill prioritizes exchange filings and company material, passes source restrictions, and performs its own financial analysis. DWS applies those explicit filters, acquires sources, and returns evidence. It contains no special valuation, recommendation, or “credible company” logic.

**Success:** a generic technical host and Funda can use the same DWS deployment without a core fork.

### Journey C — Bounded documentation crawl

A caller submits a seed URL, host/path scope, depth, and page budget. DWS acknowledges a persisted crawl job. The caller disconnects and later checks status. Partial documents remain available; completion explains whether the frontier was exhausted or a limit stopped traversal.

**Success:** “completed” never silently means “the entire site was crawled” when a budget was reached.

### Journey D — Concurrent agents

Several agents share a workspace or use different workspaces. DWS coalesces equivalent in-flight acquisitions, queues QMD work, and returns index-lag signals when a newly captured snapshot is not yet searchable.

**Success:** no accidental cross-workspace result leakage, unbounded process spawning, or duplicate full crawl caused by repeated submission.

### Journey E — Revisit or recover

A caller requests an old snapshot after the original page changes. If retained, DWS serves that capture. If expired, it returns an explicit expiration/tombstone result rather than silently substituting current content. After index loss, retained normalized files can rebuild retrieval.

**Success:** provenance remains meaningful across updates, cleanup, and recovery.
## 6. Architecture and ownership

### 6.1 Logical architecture

```text
                       USER / HOST PROJECT
                Agent + skill + research profile
                 planning, judgment, report writing
                              |
                       MCP or DWS CLI
                              |
                    +---------v----------+
                    |     DWS API        |
                    | FastMCP adapter    |
                    | local command API  |
                    +---------+----------+
                              |
                    +---------v----------+
                    |   DWS services     |
                    | search / acquire   |
                    | crawl / retrieve   |
                    | read / jobs        |
                    +----+----+----+------+
                         |    |    |
           +-------------+    |    +------------------+
           |                  |                       |
     Provider ports      Document pipeline      Retrieval adapter
           |                  |                       |
   SearXNG / DDGS       normalize / validate     QMD lexical-only
   Crawl4AI / HTTP      hash / store / map       bounded CLI calls
   optional providers        |                       |
           |             Artifact files          QMD SQLite
           +------------------+
                              |
                        DWS SQLite
                provenance / metadata / jobs

              DWS worker: crawl execution + indexing
              Separate process, same application core
```

### 6.2 Dependency rules

1. `domain` and `services` must not import FastMCP, MCP protocol types, or host-agent libraries.
2. Provider-specific response objects are normalized at adapter boundaries.
3. The QMD adapter uses supported CLI or SDK interfaces; production code must not create, migrate, or join against QMD’s private tables.
4. The FastMCP adapter translates DWS contracts into negotiated MCP responses. It does not decide provider fallback or research strategy.
5. The CLI and MCP share service contracts. In normal shared-store mode, the CLI calls the running DWS service instead of independently writing shared databases or launching QMD updates.
6. Direct Python invocation remains useful for unit tests and an explicit exclusive standalone mode. It must not bypass concurrency controls on the live shared store.

### 6.3 Proposed repository layout

```text
dws/
  DWS_PRD.md                 # This document
  compose.yaml               # One deployment entry point
  .env.example               # Names and safe defaults, never secrets
  config/
    dws.example.yaml
    searxng/settings.yml
  src/dws/
    domain/                  # Models, errors, identifiers
    services/                # Search, fetch, crawl, retrieve, jobs
    ports/                   # Provider/store/index contracts
    adapters/
      search/                # SearXNG, DDGS, optional hosted search
      acquisition/           # HTTP, Crawl4AI, optional Firecrawl/TinyFish
      extraction/            # HTML, text, PDF
      retrieval/             # QMD implementation
      storage/               # SQLite and filesystem
      mcp/                   # FastMCP
      http/                  # Small local command/administration API
      cli/                   # dws commands
    worker/                  # Execution, leases, index update loop
    policies/                # Budgets, cache, retention, URL safety
  integrations/
    generic-research/
    technical-research/
    funda-research/
  tests/
    unit/
    contracts/
    fixtures/
    integration/
    concurrency/
```

This is a module layout, not a requirement to publish separate packages. Begin with one repository and one Python distribution unless packaging constraints justify a split.

### 6.4 Provider contracts

| Port | Required contract | Important distinction |
|---|---|---|
| `SearchProvider` | Search normalized queries; return ranked candidate records and attempts | Discovery is not page acquisition |
| `AcquisitionProvider` | Fetch a URL with explicit rendering mode, limits, and capabilities | A browser capability is not mandatory for every provider |
| `CrawlProvider` | Optional native traversal; return page events, continuation state, and termination reason | Must not become a second untracked frontier owner |
| `DocumentExtractor` | Convert bytes/provider output to normalized text, structure, and quality signals | Parsing is separate from downloading |
| `RetrievalIndex` | Index accepted artifacts, lexical search, status, and bounded document lookup | QMD is one implementation, not the public contract |
| `ArtifactStore` | Atomic content writes, reads, hashes, retention, and paths | Canonical evidence survives index replacement |
| `MetadataRepository` | Transactional metadata and job persistence | Does not contain QMD FTS tables |

Prefer one acquisition port with capabilities such as `http`, `rendered`, and `pdf_download` over a new public tool for every provider feature. A separate browser-session port is optional and not part of the default public API.

## 7. Functional requirements

**P0** means required for V1. **P1** means a useful follow-on or optional integration. Source-specific implementation choices remain subject to the gates in Section 23.

| ID | Priority | Requirement | Acceptance indicator |
|---|---|---|---|
| FR-001 | P0 | Expose provider-neutral search, fetch, crawl, retrieve, read, status, and cancel capabilities | Adding a provider does not rename public tools |
| FR-002 | P0 | Normalize search results with URL, title, snippet, rank, and nullable dates | No downloaded page bodies in ordinary search results |
| FR-003 | P0 | Preserve the requested query and explicit filters; do not use an internal LLM to rewrite them | No model call in search contract tests |
| FR-004 | P0 | Support configurable capability-level fallback with bounded attempts and visible outcomes | Primary failure can yield a successful fallback and an attempt record |
| FR-005 | P0 | Distinguish empty legitimate results from transport, parsing, and provider failures | Typed outcomes; no silent success on malformed responses |
| FR-006 | P0 | Fetch selected HTTP(S) URLs, detect content type, and enforce byte/time limits | Oversized or unsupported content stops safely |
| FR-007 | P0 | Produce stable document/snapshot IDs, metadata, bounded excerpt, and resource address | Excerpt is traceable to the stored normalized content |
| FR-008 | P0 | Attempt non-browser acquisition where suitable; escalate rendering only within policy | Browser not started for every plain text/HTML fixture |
| FR-009 | P0 | Handle text-bearing PDFs through an explicit parser path | PDF text includes page provenance when available |
| FR-010 | P0 | Report scanned/unsupported/poorly parsed content without pretending it is complete | Extraction warnings and `needs_ocr` or equivalent status |
| FR-011 | P0 | Crawl within explicit seed, host/path, depth, page, time, and request-attempt budgets | Out-of-scope links are not followed |
| FR-012 | P0 | Persist accepted crawl jobs before returning their IDs | Immediately polling an acknowledged job resolves it |
| FR-013 | P0 | Record per-URL outcomes and a crawl manifest with a stop reason | Page counts reconcile; limits are visible |
| FR-014 | P0 | Retry/resume safely after a worker restart using leases and checkpoints | Completed pages are not blindly re-enqueued |
| FR-015 | P0 | Use QMD lexical search only in the default retrieval path | No embed/vector/hybrid/model invocation |
| FR-016 | P0 | Scope retrieval to the requested workspace and optional run/crawl/document subset | Unrelated workspace documents never appear |
| FR-017 | P0 | Return bounded passages with snapshot, source, location, and index-state information | Host can verify the returned excerpt against its snapshot |
| FR-018 | P0 | Provide bounded direct reads independent of QMD index readiness | Just-saved or temporarily unindexed snapshots remain readable |
| FR-019 | P0 | Store useful normalized artifacts and update the index asynchronously in batches | Acquisition success does not depend on immediate indexing success |
| FR-020 | P0 | Surface pending/failed indexing and incomplete filter coverage | No claim that zero hits proves no relevant document exists |
| FR-021 | P0 | Keep DWS state and QMD state in separate owned database files | QMD rebuild leaves DWS jobs and provenance intact |
| FR-022 | P0 | Maintain source URL, redirects, capture timestamp, hashes, and normalization version | A retained snapshot can be audited after live content changes |
| FR-023 | P0 | Separate cache freshness from artifact retention | Stale-but-retained data is not mislabeled current |
| FR-024 | P0 | Offer pin, export, expire, and dry-run cleanup controls | Pinned artifacts are never silently evicted |
| FR-025 | P0 | Bound QMD query concurrency and serialize index updates | Load tests show admitted work stays within configured limits |
| FR-026 | P0 | Use short, retry-aware SQLite transactions and bootstrap migrations before traffic | No network or browser wait inside a write transaction |
| FR-027 | P0 | Enforce idempotency for eligible job submissions and acquisition coalescing | Same request key does not start duplicate crawls |
| FR-028 | P0 | Support job polling and cooperative cancellation | Cancellation state and residual work are explicit |
| FR-029 | P0 | Start the baseline from one Compose file and persist required state | Restart preserves jobs, retained artifacts, and configuration |
| FR-030 | P0 | Default to local access, protect secrets, and validate outgoing fetch targets | SSRF and secret-redaction tests pass |
| FR-031 | P0 | Use stable bounded response contracts, machine-readable errors, and truncation flags | Responses validate and respect configured output budgets |
| FR-032 | P0 | Operate with hosted providers disabled and no model credentials | Baseline end-to-end fixture suite succeeds |
| FR-033 | P0 | Record attempts, queue waits, index lag, cache events, and failures locally | Bottlenecks can be diagnosed without inspecting model reasoning |
| FR-034 | P0 | Supply a default host research integration template without embedding it in core | Core works without any agent/skill installation |
| FR-035 | P1 | Add self-hosted Firecrawl and/or Spider through optional adapters/profiles | Benefit and resource overhead demonstrated on the benchmark corpus |
| FR-036 | P1 | Expose native MCP Tasks or notifications where supported | Same DWS JobService; no second authoritative job system |

## 8. Public interfaces and example contracts

### 8.1 Proposed MCP tool catalog

The seven-tool baseline adds a bounded `read` operation to the earlier six-tool sketch. This is a **proposed compatibility refinement**, not a requirement to expose every storage operation to the model.

| Tool | Description presented to the host | Core inputs |
|---|---|---|
| `search` | Search the public web; return ranked URL metadata, not page bodies | query, workspace, result limit, optional explicit freshness/domain filters |
| `fetch` | Acquire one URL; store a snapshot; return metadata, excerpt, and handle | URL, workspace, freshness policy, optional run ID |
| `crawl` | Start bounded site traversal and acquisition | seed, workspace, scope, page/depth limits, optional run ID |
| `retrieve` | Search retained DWS artifacts; return relevant passages; do not search the live web | query, workspace, optional crawl/run/document filters, passage budget |
| `read` | Read a bounded range or section of a retained snapshot | snapshot ID, selector, output budget |
| `job_status` | Return execution status, progress, and result handles | job ID |
| `job_cancel` | Request cooperative cancellation of DWS work | job ID |

Workspace may come from a configured default, but explicit overrides must be supported. Advanced provider tuning stays in configuration/admin controls rather than inflating normal tool schemas.

MCP supports structured output and resource links. The adapter must use the actual negotiated protocol types rather than treating an arbitrary JSON field named `resource_links` as a standards-compliant content block. [S01]

### 8.2 Common contract rules

- Examples below are **illustrative DWS payloads**, not full MCP wire envelopes and not claims about live sources.
- `schema_version` versions the public DWS contract. Internal database schema versions are separate.
- Use ISO 8601 timestamps with timezone; persist UTC. Unknown source dates are `null`, never fabricated from fetch time.
- Rank/score is relevance information, not a calibrated probability of truth. Expose score kind when a score is returned.
- All arrays and text are bounded. `truncated`, `next_cursor`, `index_state`, and `warnings` disclose limitations.
- IDs are opaque. Public inputs never become unrestricted SQL, shell strings, or filesystem paths.
- Provider diagnostics are stored internally. The host sees only useful warnings by default.

### 8.3 Search result

Request: `search(query="episodic memory persistence", workspace_id="ws_ai_memory", limit=10)`.

```json
{
  "schema_version": "1.0",
  "request_id": "req_example_01",
  "search_id": "search_example_01",
  "query": "episodic memory persistence",
  "workspace_id": "ws_ai_memory",
  "returned_count": 2,
  "results": [
    {
      "result_id": "hit_01",
      "rank": 1,
      "title": "Memory persistence: design notes",
      "url": "https://example.org/notes/memory-persistence",
      "snippet": "Design notes covering durable records and retrieval of prior observations.",
      "published_at": null,
      "content_type_hint": "text/html"
    },
    {
      "result_id": "hit_02",
      "rank": 2,
      "title": "A guide to agent memory",
      "url": "https://example.org/guides/agent-memory.pdf",
      "snippet": "An illustrative guide discussing short-term context and retained observations.",
      "published_at": null,
      "content_type_hint": "application/pdf"
    }
  ],
  "ranking": {"method": "provider_rank", "score_kind": null},
  "cache": {"hit": false, "stale": false},
  "warnings": [],
  "truncated": false,
  "next_cursor": null
}
```

An unsuccessful provider may be retried or replaced internally. Missing result diversity alone must not reject an intentionally single-domain query. Search snippets remain discovery material, not verified quotations from an acquired document.

### 8.4 Fetch result

Request: `fetch(url="https://example.org/notes/memory-persistence", workspace_id="ws_ai_memory")`.

```json
{
  "schema_version": "1.0",
  "request_id": "req_example_02",
  "status": "success",
  "document_id": "doc_37",
  "snapshot_id": "snap_37_a",
  "workspace_id": "ws_ai_memory",
  "source_url": "https://example.org/notes/memory-persistence",
  "final_url": "https://example.org/notes/memory-persistence",
  "title": "Memory persistence: design notes",
  "content_type": "text/html",
  "published_at": null,
  "fetched_at": "2026-09-09T10:00:00Z",
  "excerpt": {
    "kind": "verbatim_normalized",
    "text": "Durable memory should remain available after the process that created it has stopped.",
    "selector": {"line_start": 12, "line_end": 12}
  },
  "resource_uri": "dws://snapshot/snap_37_a/content",
  "index_state": "pending",
  "retention": {"pinned": false, "expires_at": "2026-10-09T10:00:00Z"},
  "quality": {"status": "usable", "warnings": []},
  "cache": {"hit": false, "stale": false}
}
```

“Verbatim normalized” means copied from the normalized snapshot, not byte-identical HTML. Preserve a transformation record and original artifact when exact original presentation matters. A summary is not produced automatically.

### 8.5 Crawl submission, progress, and completion

Request: `crawl(seed_url="https://example.org/docs/", scope="same_path", max_pages=120, max_depth=2, workspace_id="ws_ai_memory")`.

```json
{
  "schema_version": "1.0",
  "request_id": "req_example_03",
  "job_id": "job_104",
  "crawl_id": "crawl_77",
  "status": "queued",
  "poll_after_ms": 10000,
  "manifest_uri": "dws://crawl/crawl_77/manifest",
  "scope": {"mode": "same_path", "max_pages": 120, "max_depth": 2}
}
```

Example running status:

```json
{
  "job_id": "job_104",
  "crawl_id": "crawl_77",
  "status": "running",
  "progress": {
    "scheduled_urls": 120,
    "queued": 40,
    "in_flight": 2,
    "succeeded": 72,
    "failed": 4,
    "skipped_after_scheduling": 2
  },
  "poll_after_ms": 10000
}
```

The states above are disjoint: `40 + 2 + 72 + 4 + 2 = 120`. Retry attempt counters are tracked separately from distinct URL counts.

Example final status:

```json
{
  "job_id": "job_104",
  "crawl_id": "crawl_77",
  "status": "completed",
  "outcome": "partial",
  "stop_reason": "page_limit",
  "progress": {
    "scheduled_urls": 120,
    "queued": 0,
    "in_flight": 0,
    "succeeded": 110,
    "failed": 8,
    "skipped_after_scheduling": 2,
    "new_snapshots": 106,
    "reused_snapshots": 4
  },
  "manifest_uri": "dws://crawl/crawl_77/manifest",
  "coverage_complete": false,
  "warnings": ["The page limit was reached; additional in-scope URLs remain."]
}
```

Completion is an execution state; outcome and coverage are separate. A paginated manifest lists URL outcomes and snapshot references, never every page body by default.

### 8.6 Retrieval result

Request: `retrieve(query="durable memory", workspace_id="ws_ai_memory", limit=5)`.

```json
{
  "schema_version": "1.0",
  "request_id": "req_example_04",
  "retrieval_mode": "lexical",
  "workspace_id": "ws_ai_memory",
  "returned_count": 1,
  "passages": [
    {
      "document_id": "doc_37",
      "snapshot_id": "snap_37_a",
      "title": "Memory persistence: design notes",
      "source_url": "https://example.org/notes/memory-persistence",
      "text": "Durable memory should remain available after the process that created it has stopped.",
      "selector": {"line_start": 12, "line_end": 12},
      "rank": 1,
      "resource_uri": "dws://snapshot/snap_37_a/content"
    }
  ],
  "index_state": "ready",
  "index_generation": 8,
  "coverage": {"filter_complete": true, "pending_snapshots": 0},
  "warnings": [],
  "truncated": false,
  "next_cursor": null
}
```

This is not a guarantee that the indexed source is factually correct. It is a traceable result from the retained corpus. A zero-result query must distinguish an empty index, pending updates, restrictive filters, and genuine lexical absence.

### 8.7 Errors

Use domain codes including `INVALID_INPUT`, `POLICY_DENIED`, `UNSAFE_URL`, `PROVIDER_UNAVAILABLE`, `RATE_LIMITED`, `TIMEOUT`, `CONTENT_TOO_LARGE`, `EXTRACTION_INCOMPLETE`, `INDEX_BUSY`, `INDEX_UNAVAILABLE`, `ARTIFACT_EXPIRED`, `NOT_FOUND`, and `CAPACITY_EXCEEDED`.

An error includes a safe message, retryability, optional retry delay, request ID, and any recoverable job or artifact handle. Do not leak credentials, raw exception stacks, cookie values, or internal paths. The MCP adapter maps domain failures to tool outcomes and protocol failures separately.

### 8.8 CLI and maintenance

```text
dws search "..." --workspace ... --json
dws fetch https://... --workspace ... --json
dws crawl https://... --max-pages 100 --max-depth 2 --json
dws retrieve "..." --workspace ... --json
dws read snap_... --from-line 10 --max-lines 40
dws jobs status job_...
dws jobs cancel job_...
dws artifacts pin snap_...
dws artifacts export snap_... --output ...
dws gc --dry-run
dws index status
dws index rebuild
dws doctor
```

These are proposed commands. Pinning, cleanup, configuration, and rebuild operations are local administrative capabilities; they do not need to enlarge the default model-visible tool catalog. JSON data goes to stdout; logs/progress go to stderr. A stdio MCP bridge similarly reserves stdout for protocol messages.
## 9. Provider stack and fallback policy

### 9.1 Capability matrix and selection

This matrix distinguishes **observed upstream capabilities** from **DWS’s proposed use of them**. Provider names are not interchangeable with capabilities, and a hosted product is not necessarily equivalent to its open-source counterpart.

| Component | Role in DWS | Benefit | Cost or limitation | Selection |
|---|---|---|---|---|
| SearXNG | Primary public-web discovery | Aggregates multiple search engines behind one interface | Upstream engines can fail, block, or share correlated outages; instance must enable the needed API output | Accepted primary [S07] [S08] |
| DDGS | Lightweight discovery fallback | Python/CLI integration without another persistent server | Not a guaranteed search index or independent SLA; overlaps with other engines and can be rate-limited | Proposed enabled backup [S13] |
| HTTPX + Trafilatura | Cheap HTTP acquisition and main-content extraction | Avoids browser startup for suitable pages | Does not replace rendering, traversal, PDF parsing, or access to blocked sites | Proposed baseline optimization [S15] [S30] |
| Crawl4AI | Browser-capable acquisition and primary crawl backend | Python-oriented crawling and content extraction | Browser dependencies, resource usage, extraction variability; pin and secure the chosen deployment | Accepted primary [S09] [S10] |
| Firecrawl self-hosted | Optional acquisition/crawl fallback | Another maintained acquisition pipeline and native crawl API | Overlap with Crawl4AI; several supporting services; open-source/cloud feature differences | Optional profile after evaluation [S11] [S37] |
| TinyFish Search / Fetch / Browser | Explicitly enabled hosted escape paths | Alternative discovery or remote acquisition for difficult sources | External service, credentials, variable cost/limits; each API requires its own adapter | Optional [S12] [S38] [S39] [S40] |
| Spider Rust engine | Candidate native crawl backend | Separate crawling implementation suitable for a provider adapter | Additional runtime/integration; not automatically the best choice without corpus tests | Deferred evaluation; distinguish from Spider Cloud [S14] |
| pypdf | Text-bearing PDF extraction | Local parser with no OCR model requirement | Reading order, tables and scanned pages require care; it is not OCR | Proposed baseline PDF adapter [S31] |
| QMD | Retained-document lexical retrieval | Ready-made indexing, collection, search, and document interfaces | Node/Bun/native dependency stack and lifecycle integration | Accepted text-only search subsystem [S16] [S20] |

A ranking such as “Spider is second best” or “Firecrawl is battle-tested enough to solve all hard pages” is **not a verified DWS finding**. The project will compare them on an explicit acquisition corpus, not reputation alone.

### 9.2 Search routing

Proposed sequence:

```text
Fresh search-cache entry matching all filters?
    yes → return compact cached results with age
    no  → SearXNG
              ↓ eligible failure or inadequate usable output
           DDGS
              ↓ still inadequate, and hosted search enabled
           TinyFish Search
```

An eligible failure includes transport timeout, upstream error, malformed output, or no usable URLs after validation. A legitimate zero-result response is distinct from a provider failure. A configurable second attempt may be useful for unexpectedly weak coverage, but the core does not invent new research questions. The host decides whether to reformulate a query.

Search aggregation and rank merging must preserve source attempts and remove duplicate URLs without inventing a calibrated cross-provider confidence score. If a provider cannot honor a requested freshness/domain filter, DWS must either reject that routing choice or disclose the unsupported filter.

**Independence matters:** Firecrawl’s configuration exposes a SearXNG endpoint setting. A Firecrawl search deployment using our own SearXNG instance is not an independent backup for that instance. DDGS and SearXNG can also depend on overlapping upstream engines. Record the effective dependency chain, not just the adapter name. [S32]

### 9.3 Acquisition routing

The route is based on content requirements and policy, not a mandatory sequence that always calls every provider:

```text
Retained snapshot sufficiently fresh for this request?
    yes → reuse snapshot; record new acquisition association if needed
    no  → cheap HTTP download where suitable
              ├── text/HTML → local extraction
              ├── PDF      → local parser
              └── requires rendering → Crawl4AI
                                          ↓ eligible failure
                                      Firecrawl, if enabled
                                          ↓ eligible failure and permission
                                      targeted TinyFish API
```

Signals for escalation include a JavaScript shell with little substantive text, a render requirement declared by the caller, extraction failure, or a provider-specific compatibility problem. Signals for stopping include an unsafe URL, an explicit access restriction, a robots/policy denial, unsupported credentials, or an exhausted budget. A fallback must never turn a policy denial into a bypass attempt.

A successful HTTP status is not sufficient evidence of successful extraction. Store signals such as extracted length, content type, challenge/login-page detection, parser warnings, and truncation. Heuristics must remain inspectable and must not turn every short page into a failure.

### 9.4 Crawl routing and ownership

For the first crawl integration, select **one frontier owner**: either DWS’s bounded traversal worker or the chosen provider’s native crawl implementation. Do not simultaneously maintain two competing notions of visited URLs, depth, and remaining budget.

A native backend must expose enough control and status to enforce DWS’s scope and limits. DWS retains its own job record, manifest, and canonical snapshot mappings. Provider job IDs are implementation details. Switching providers mid-crawl is allowed only if the adapter can translate the outstanding frontier safely; otherwise finish the current run as partial and start an explicit continuation.

Firecrawl and Spider are not mandatory deployments merely because their interfaces exist. Add them when tests show a meaningful increase in successful, accurate acquisition relative to the extra runtime cost and maintenance.

### 9.5 Common retry policy

Retries must be bounded by attempts, elapsed time, and provider budget. Use backoff with jitter for retryable failures. Do not retry invalid input, unsafe targets, unsupported authentication, or a known hard output limit as though they were transient errors.

Persist provider, effective backend if known, requested capability, duration, safe error code, and outcome. A degraded successful result is useful, but it must not erase the fact that some requested work failed. Hosted escalation is opt-in and has a separate expenditure ceiling.

## 10. Document pipeline and data model

### 10.1 Canonical pipeline

```text
Validated request
    → safe acquisition and redirects
    → staged original bytes, where retained
    → content-type-specific extraction
    → normalized text/Markdown with source locations
    → hashes, metadata, and extraction diagnostics
    → atomic artifact publication
    → short DWS metadata transaction + indexing outbox
    → asynchronous QMD update
    → searchable snapshot
```

All providers feed this pipeline. A crawler returning pre-cleaned Markdown still supplies provenance and extraction information; it does not bypass identity, retention, or output validation.

### 10.2 Document versus snapshot

A `document_id` represents a logical source identity. A `snapshot_id` represents a particular captured version. A new capture may reuse existing content bytes when hashes match, while still recording when and how it was acquired.

The source URL, final URL, canonicalization decision, and redirects are separately recorded. URL canonicalization must not indiscriminately remove query parameters: a parameter may select a document version, language, page, or download. A claimed HTML canonical URL is evidence to evaluate, not an unconditional instruction to merge unrelated documents.

Use separate hashes for original bytes and normalized content. Include a normalization-version identifier. Changing the normalizer can change extracted text without the source having changed. This must not masquerade as a new publisher update.

### 10.3 Proposed canonical snapshot fields

| Group | Fields and purpose |
|---|---|
| Identity | document ID, snapshot ID, workspace membership, optional run/crawl membership |
| Source | requested URL, final URL, canonical URL if accepted, redirect chain, content type |
| Time | capture timestamp, nullable publication/update dates, date source/quality |
| Content | original and normalized artifact references, byte counts, word count, language hint |
| Integrity | original hash, normalized hash, normalizer and extractor versions |
| Structure | stable line map, section markers, PDF page mapping where reliable, table/parse warnings |
| Acquisition | provider, acquisition mode, attempt ID, cache/revalidation information |
| Lifecycle | retention policy, expiry, pin references, indexing state/generation |

Do not fabricate dates, author names, confidence percentages, or page numbers when the extractor cannot establish them. Preserve unknown values explicitly.

### 10.4 Structure and passage integrity

The normalizer should retain headings, lists, hyperlinks, and simple tables when extraction supports them. PDF page boundaries should be preserved when possible. Complex layouts, figures, scanned PDFs, and malformed tables must carry warnings rather than flattened text being described as a complete representation.

A passage returned by retrieval must map back to normalized text and, where available, a source page/section. “Verbatim excerpt” means exact text from the retained normalized representation; normalization may have changed whitespace or removed navigation. Reports requiring exact original layout should reference the retained original as well.

### 10.5 Proposed DWS database model

The implementation may combine small tables, but ownership and invariants must remain:

| Entity | Responsibility |
|---|---|
| `workspaces`, `runs` | Scope, optional host correlation, policy defaults |
| `searches`, `search_hits` | Query/filter history and compact discovery records |
| `documents`, `snapshots` | Logical source and immutable capture metadata |
| `acquisitions`, `provider_attempts` | Fetch events, redirects, fallback and error history |
| `crawls`, `crawl_urls` | Scope, membership, per-URL state and manifest |
| `jobs` | Durable execution state, lease, attempt, cancellation, result handles |
| `index_outbox` | Pending QMD work and retry status |
| `artifact_pins`, `artifact_memberships` | Retention protection and references |
| `schema_migrations` | DWS-owned schema evolution |

The QMD database remains outside this schema. Do not create DWS tables, triggers, or migrations inside it. Do not put full duplicate normalized bodies into `dws.sqlite` merely because QMD also uses SQLite.

### 10.6 Atomicity across files and two databases

There is no cross-database/filesystem transaction that DWS can assume automatically. Use an explicit recoverable sequence:

1. Write a bounded artifact to a staging path, verify size/hash, and atomically publish it on the same filesystem.
2. Commit its DWS metadata and an indexing-outbox record in one short transaction.
3. Let the single indexer register/update the file through QMD’s public interface.
4. Mark the snapshot indexed only after the relevant update succeeds; expose pending/failed states meanwhile.

A crash between steps may leave an orphan staged/published file or a pending index request. Startup recovery must reconcile these states. An interrupted index update must not delete canonical evidence. Cleanup must likewise reconcile pins, memberships, files, and index state rather than assuming all operations succeed together.

### 10.7 Deduplication without losing provenance

Deduplicate bytes by content hash where practical, but do not collapse distinct source provenance or workspace membership. Two URLs serving the same content can share stored bytes while retaining their separate acquisition records. In-flight coalescing should include policy-sensitive inputs so that incompatible freshness or extraction requests are not silently merged.

## 11. Retention, cache, and indexing policy

### 11.1 Storage, caching, and indexing answer different questions

| Concern | Question |
|---|---|
| Retention | Do we still preserve this evidence? |
| Cache freshness | Is this capture recent enough to reuse without contacting the source? |
| Indexing | Can a query discover the retained content? |
| Pinning | Must this artifact survive normal cleanup because a report or project depends on it? |

One-time research does not imply zero retention value. Within one investigation, the host may reread a source, verify a passage, or resume after a context reset. Nevertheless, indefinite retention and global semantic indexing are not justified by an assumed future cache hit.

### 11.2 What is retained and indexed

**Default direction:** retain successful, useful normalized acquisitions and index them lexically in batches. Search hits alone are not downloaded or indexed. Failed responses, challenge pages, duplicate byte copies, and temporary browser assets are not automatically promoted into the useful corpus.

Original PDFs and selected original HTML snapshots may be retained for auditability. Large temporary assets and screenshots need separate explicit policies. Normalized evidence is the rebuildable input to QMD; QMD’s own stored text is a retrieval copy, not the only archive. QMD’s file-update and cleanup lifecycle can deactivate missing files and remove inactive content. [S18] [S41]

### 11.3 Proposed starting defaults—not final owner policy

| Item | Initial default to validate | Reason |
|---|---|---|
| Search-result cache | 5 minutes | Coalesce bursts without treating discovery as permanently current |
| Ordinary fetched-content freshness | 24 hours, overridden by explicit freshness policy | Avoid immediate refetches; not suitable for every changing source |
| Normalized accepted artifacts | 30 days after the run closes; ordinary use may renew an unpinned lease | Preserve investigation/revisit value without indefinite growth |
| Unpinned original HTML | 7 days unless an evidence profile retains it longer | Separate raw-page bulk from useful normalized text |
| Original PDFs | Align with normalized retention unless explicitly discarded | Original layout may be needed to verify extraction |
| Pinned evidence | Until explicit unpin/delete | Do not break a saved report’s evidence silently |
| Temporary downloads/browser files | Remove after successful publication or bounded failure cleanup | Avoid unmanaged accumulation |

An active job/run and an explicit pin protect required artifacts from garbage collection. When a caller does not close a run, use a documented inactivity policy rather than retaining everything forever. Exact TTLs, disk quota, and whether routine reads renew retention are G-10 decisions.

`force_refresh` or an explicit current-information request overrides normal freshness reuse. A retained but old capture may still be read as historical evidence; its age must be visible. Conditional HTTP revalidation may reduce transfers where supported, but the contract must not rely on every provider supporting it.

### 11.4 Garbage collection and disk pressure

Provide a dry-run plan before destructive cleanup. Deletion must honor pins and current references, preserve an expiry/tombstone record long enough to return `ARTIFACT_EXPIRED`, and update QMD through its supported lifecycle. Do not silently serve a different snapshot under an expired snapshot ID.

At a configured disk high-water mark, first stop or defer new bulk acquisition and report the condition. Do not delete pinned evidence to keep a crawl running. Proposed alert/pause thresholds are 80%/95% of the DWS quota, subject to testing; the quota is not the entire host disk capacity by implication.

### 11.5 Vector indexing is intentionally absent

The default corpus uses lexical retrieval. DWS does not run QMD embeddings, semantic search, query-expansion models, or reranking models. This avoids eager model computation and keeps the product usable without model credentials.

The trade-off is reduced recall for paraphrases, cross-language concepts, and passages that do not share query terms. The host can reformulate queries; DWS should also disclose when a lexical result set is sparse. Do not describe FTS as universally equivalent to semantic retrieval.

Reconsider optional semantic retrieval only after a representative query set shows meaningful misses and the corpus is reused enough to justify its cost. Corpus size alone is not the trigger. Browser rendering, PDF parsing, indexing, and embeddings have different cost profiles; no claim is made that vectors are always the largest cost.

### 11.6 Measure reuse rather than inventing it

Track same-run, same-workspace, and cross-workspace reuse separately; bytes avoided; artifact age at reuse; retained-but-never-read bytes; lexical query count; and index cost per accepted document. These measurements determine future TTL and indexing policy. The number of human users is not an adequate proxy for reuse or concurrency.

## 12. QMD integration

### 12.1 Exact product and text-only path

Use the original **`tobi/qmd` (Query Markup Documents)**. The CLI `qmd search` is the lexical path; in its SDK, `searchLex` is the explicit lexical API. The generic SDK `search` entry point supports hybrid/model-assisted behavior and must not be substituted merely because its name is convenient. Disabling reranking alone is not a sufficient lexical-only guarantee. [S16] [S17]

QMD stores indexed text and metadata in SQLite and has FTS tables. Its runtime also has native/model-related dependencies; lexical-only use avoids those inference operations, not necessarily their package footprint. Pin the runtime and native builds as part of the DWS image. [S18] [S20]

### 12.2 Adapter contract

Start with a bounded CLI adapter if it passes G-02/G-03. Invoke an argument array, never construct a shell command from a query. Parse a documented machine-readable result format. Enforce deadlines, output limits, collection scope, and process cleanup.

Permitted internal operations include collection registration, lexical search, bounded get, update, and controlled cleanup/rebuild. The host does not receive an arbitrary “run QMD command” tool. QMD’s own MCP surface is not exposed directly alongside DWS because that could bypass lexical-only policy, scope, and output budgets.

Use QMD’s public CLI/SDK interface, not direct SQL into its private tables. The implementation may later use a persistent wrapper to reduce startup overhead, but only after comparing it with the bounded CLI approach. An async wrapper around synchronous SQLite calls does not automatically create parallel execution.

### 12.3 Collection and scope design

**Proposed baseline:** one collection per workspace, using stable snapshot-derived paths under a controlled normalized-artifact directory. The DWS metadata store maps these paths to snapshot IDs and source records.

Optional run/crawl/document filters require special care. A global top-K search followed by filtering can omit relevant results that ranked below unrelated documents. The adapter must use supported scope controls, or bounded candidate expansion with explicit incomplete-coverage reporting. For an explicitly selected small snapshot set, a bounded direct-text scan is an acceptable fallback; it is not a second FTS database.

G-04 must establish that workspace isolation and requested subset semantics work on the pinned QMD build. If they cannot be satisfied adequately, revise the collection strategy before claiming the contract complete. Do not silently expand a request to all workspaces.

### 12.4 Passage production

QMD identifies relevant content; DWS is responsible for returning a bounded evidence envelope. Map a result to a retained snapshot, resolve line/section context, and include the source URL and extraction warnings. When precise QMD offsets are unavailable, derive bounded snippets from the retained normalized text and verify the excerpt against it.

Keep QMD relevance scores labeled as search scores, not source credibility. Preserve index generation and pending-document counts. Avoid returning an entire matching document as the default “passage.”

### 12.5 Index update ownership

One process owns updates for an index. Batch the outbox rather than calling update independently after every fetch. Initialize the collection/schema before admitting concurrent searches. Reads may still encounter startup or maintenance writes in a particular QMD build; test the actual release rather than assuming that a CLI command named search is entirely read-only.

QMD source includes WAL/busy handling and initialization contention work, but a fix on `main` is not proof that a deployed package contains it. Record the package/commit, underlying SQLite build, and tested environment. [S19] [S35]

### 12.6 Failure behavior

If indexing fails, acquisition can remain successful with `index_state=failed` or `pending`; the artifact stays readable through `read`. A search should return an explicit index error or incomplete-state warning, not zero matches pretending the corpus is empty.

Rebuilding QMD must be possible using retained normalized artifacts and DWS mappings. Losing QMD’s database must not destroy jobs, sources, or pinned evidence. Conversely, retained QMD text does not justify deleting its source files behind its normal update/cleanup lifecycle.
## 13. Concurrency and database access

### 13.1 Concurrency model

Agent count is not database capacity. Measure concurrent operations, query duration, transaction duration, indexing pressure, and hardware. DWS must accept concurrent callers while bounding actual local work.

SQLite WAL allows readers to use committed snapshots while a writer operates, but there is one active writer per database file. Long reads can delay checkpoints. WAL requires same-machine shared-memory coordination; the database files must not be used as a multi-machine network-share interface. [S23] [S24]

The DWS and QMD database files have independent locks. Their workloads can overlap, although they share CPU, RAM, and disk resources.

### 13.2 Proposed ownership model

```text
Many callers
    → one DWS API admission boundary
        ├── short metadata reads/writes → dws.sqlite
        ├── bounded lexical searches   → QMD database
        └── persisted jobs/outbox       → one DWS worker
                                             ├── acquisition work
                                             └── one QMD updater
```

Use one API process and one worker process initially, rather than several web workers multiplying in-memory semaphores. API and worker may each access DWS metadata, so a Python mutex alone is not a global database lock. SQLite transaction handling, busy/retry policy, job leases, and cross-process migration/maintenance coordination remain necessary.

A dedicated serialized metadata-write queue is an optional refinement, not a reason to introduce another database service. Regardless of connection structure, a logical transaction must have a clear owner from begin through commit. Do not allow unrelated coroutines to interleave their transaction steps on a shared connection.

`aiosqlite` can keep synchronous SQLite work off the API event loop through its per-connection worker queue; it does not make SQLite a multi-writer engine or automatically define application transaction boundaries. [S26]

### 13.3 Starting controls

| Control | Proposed initial setting | Reason |
|---|---|---|
| QMD lexical calls | 2 in flight | Conservative start; benchmark 4 before increasing |
| QMD updates | 1 per index | Avoid competing index writers and repeated startup work |
| QMD migration/cleanup/rebuild | Exclusive coordinated maintenance | Protect schema/index lifecycle |
| DWS acquisition workers | Bounded separately for HTTP and rendered pages | Browser demand differs from lightweight I/O |
| Database transactions | Short units of work | Do not hold write ownership through I/O |
| API backlog | Bounded; suggested 64 pending local operations | Backpressure instead of unbounded memory/process creation |

An illustrative DWS connection configuration is WAL plus a 5-second busy timeout, followed by bounded application retries for appropriate conflicts. Apply connection-local settings to each connection. The timeout is an initial policy, not a guarantee every lock conflict can be resolved by waiting. [S42]

QMD has its own busy configuration and startup behavior. DWS deadlines must account for those settings; an internal long busy wait must not make an interactive search appear hung indefinitely. Cancellation must clean up child processes without killing a separate indexing owner.

### 13.4 Global limits and CLI behavior

Normal CLI access to the shared store goes through the daemon’s API or an equally explicit cross-process coordinator. It must not independently launch arbitrary concurrent QMD updates. The Python core remains reusable; “shared core” does not require every CLI command to open shared files directly.

An offline maintenance mode may access the core directly only after verifying that the relevant daemon/worker is stopped or an exclusive maintenance lease has been acquired. Remote clients, if added later, call the service; they do not mount the database files.

### 13.5 Runtime validation

Test both the Python SQLite runtime and QMD’s bundled runtime, not only the system `sqlite3` executable. SQLite’s official WAL documentation records a rare multi-connection WAL-reset issue and fixed releases/backports. The selected builds must contain the applicable fixes; do not assume identical runtime versions inside two packages. [S23]

Concurrency acceptance is provisional until tested at 1, 5, 10, 20, and 50 simulated callers. “10–20 active agents” is a planning target, not a benchmark claim.

## 14. Durable jobs and failure handling

### 14.1 What constitutes a durable job

Persist the job and its recoverable inputs before returning an acknowledgement. Immediately polling an acknowledged ID must resolve a record. A task scheduled only on an API event loop is not crash-durable.

Proposed lifecycle:

```text
queued → running → completed
            │          └── outcome: success / partial
            ├──────→ failed
            └→ cancel_requested → cancelled

expired worker lease → recovery/requeue or explicit failed outcome
```

Job status describes execution. `crawl_id` describes the crawl and its artifacts. A retained snapshot is neither a job nor an MCP session. A completed job may have a partial result due to page limits or failed URLs; completion does not imply exhaustive source coverage.

### 14.2 Worker and recovery rules

The worker records lease owner/expiry, attempt number, progress checkpoints, and completed units. It must not hold a SQLite write transaction while a provider request or browser operation is running.

Recovery may re-execute some work; do not promise exactly-once execution across network services. Use idempotency keys where available, persist external job handles, reuse verified snapshots, and distinguish scheduled URLs from completed outcomes. A provider that lacks recovery/idempotency can incur duplicate work after a crash; report that limitation.

Job limits include total attempts and time, not only successfully stored pages. Otherwise repeated failures could bypass the intended crawl budget.

### 14.3 Cancellation and progress

Cancellation is cooperative. Stop scheduling new work, request cancellation of supported provider jobs, allow or time-bound safe in-flight cleanup, and record any residual activity. A cancelled job may still have useful acquired snapshots; deleting them is a separate retention choice.

Progress should prefer honest counts over fabricated percentages. A crawl with an unknown final frontier can report discovered, scheduled, active, succeeded, failed, skipped, and stored counts. If a percentage is shown, define its denominator and allow it to change visibly.

### 14.4 Polling, MCP Tasks, and continuation

Polling is the V1 baseline. Return a suggested delay, initially around 10 seconds for an active crawl and increasing for long operations. These are transport/workflow waits, not reasons to repeatedly invoke an LLM just to ask whether a job finished.

FastMCP Tasks may provide a convenient protocol projection, but their use is gated on the pinned framework and actual client. Do not introduce a second authoritative execution system or adopt Docket/Redis merely because the MCP framework can use it. Native Tasks must map onto DWS job state; ordinary `job_status` and `job_cancel` remain the compatibility path. [S06]

MRTR/elicitation is optional for client interaction, not the job queue. Approval for unusually large or paid work must be enforced by DWS policy even if the host does not support an interactive protocol extension. A host can resubmit within an owner-configured approved budget; untrusted parameters cannot raise hard deployment limits.

## 15. Single-Compose deployment

### 15.1 What “one Compose” means

The accepted requirement is one documented top-level Compose entry point, not one container, one process, or one database file. Package dependencies can be installed inside images while Compose manages lifecycle and connectivity.

Proposed default services:

| Service | Purpose | Exposure and state |
|---|---|---|
| `dws-api` | FastMCP endpoint, local CLI-facing API, admission and reads | Only owner-approved loopback host port; shared persistent state |
| `dws-worker` | Durable jobs, acquisition orchestration, QMD updates | No published port; same application image, worker entry point |
| `searxng` | Primary discovery | Internal Compose network; persistent/configured settings |
| `crawl4ai` | Browser-capable fetch/crawl backend | Internal Compose network; audited upstream runtime/configuration |

QMD is installed in the DWS image, not published as another independent MCP service. The API and worker share the controlled artifact/index layout and ownership protocol. Native dependency compatibility is tested during image construction.

### 15.2 Optional profiles

A `firecrawl` profile must enable the complete, pinned supporting stack it needs—not just its API container. Current upstream deployment materials describe a multi-service system including browser, queue/storage, and worker components; self-hosting is not a free equivalent of its hosted service. [S11] [S32] [S37]

The profile must not accidentally start its dependencies when disabled. Compose profiles support selective activation, but dependency/profile behavior needs an end-to-end startup test. [S27]

Spider remains a separate optional adapter/deployment decision. TinyFish is external, configured through secrets and outbound policy rather than an always-on local container.

### 15.3 Package versus service decision

| Component | Proposed packaging | Why |
|---|---|---|
| DWS Python core + FastMCP + CLI | Packages in DWS image | One codebase and reproducible dependency set |
| DDGS, HTTP client, text/PDF parsers | Packages in DWS image | No reason for separate daemon services |
| QMD | Pinned CLI/runtime in DWS image | Reuse public interface with minimal extra service wiring |
| SearXNG | Dedicated service | Clear search-engine lifecycle and configuration boundary |
| Crawl4AI | Dedicated service initially | Isolates browser dependencies and makes resource controls explicit |
| Firecrawl | Optional multi-service profile | Upstream architecture is service-oriented; do not embed its API package as if it were a full crawler |

Audit the selected SearXNG and Crawl4AI upstream Compose definitions rather than copying unverified service names, ports, or privileges. [S33] [S34]

A direct Crawl4AI Python-library integration remains an acceptable future adapter if it reduces overhead without harming isolation. It was not selected as the initial packaging because the owner prefers one reproducible Compose environment. Neither option changes the public capability contract.

### 15.4 Required deployment properties

- Pin package versions and image digests after G-01/G-05; do not deploy mutable `latest` tags as the baseline.
- Supply health/readiness checks that test useful capability, not just an open TCP port. Applications still retry dependencies; startup order alone is not resilience.
- Store SQLite files and artifacts on a local persistent volume with defined UID/GID permissions. Do not depend on container writable layers for evidence.
- Coordinate migrations before serving traffic. Replacing an API container must not silently rebuild/delete the corpus.
- Do not mount the Docker socket, host home directory, browser profiles, or unrelated credentials into crawler containers.
- Audit third-party supporting processes. Crawl4AI deployment documentation includes supervised supporting components; “one crawler container” must not be represented as one process or zero extra memory. [S10]

### 15.5 Binding and local reachability

Publish the DWS host port on `127.0.0.1` by default. The service inside its container may need to bind to `0.0.0.0` so the container network and port mapping can reach it. Do not confuse container binding with exposing a port on every host interface. Docker’s port-publishing rules distinguish these cases. [S28]

A cloud-hosted MCP client does not automatically reach a laptop’s loopback address. V1 targets local agents/hosts with actual local connectivity. A remote connector would require a separate, explicitly designed access path; this PRD does not silently add a public tunnel.

### 15.6 Persistent layout and backup

```text
/data/
├── dws.sqlite
├── qmd/
│   ├── index.sqlite
│   └── managed configuration/state
├── artifacts/
│   ├── normalized/{workspace}/{snapshot}.md
│   ├── originals/...
│   └── staging/...
└── exports/...
```

A backup must preserve DWS metadata, pinned/retained artifacts, configuration, and enough mapping to rebuild QMD. Use SQLite’s backup facilities or quiesce writers for a consistent filesystem backup. Copying only a live main database file while ignoring its WAL is not the specified backup procedure. [S25]

QMD may be backed up for fast recovery, but it must remain rebuildable. Test restore, not just backup creation. On Docker Desktop, use a supported local volume layout and verify permissions/performance; network-mounted database files are outside the baseline.

## 16. Local security and trust boundaries

### 16.1 Threat model

The system is personal, but untrusted web content and automated callers can still cause unwanted requests, disk growth, credential disclosure, or malicious parser input. Local deployment reduces public exposure; it does not make all inputs trusted.

### 16.2 Incoming access

Protect the published interface with loopback binding, Host/Origin validation appropriate to the transport, and a local token when compatible with the chosen host. Avoid unrestricted CORS. A stdio bridge still inherits process credentials and environment risks; it is not “security-free” because it has no port.

Enterprise OAuth, multi-tenant roles, and a public authorization server are not baseline requirements. Reassess them only if the service becomes remotely accessible.

### 16.3 Outbound URL policy

Only accept supported HTTP(S) targets. Validate hostnames, resolved addresses, redirects, and browser navigation/subrequests against loopback, private, link-local, metadata, multicast, and other prohibited destinations. Guard against DNS rebinding and equivalent encoded/address forms. Network egress controls may be needed to enforce these rules reliably for a third-party browser service. [S29]

Trusted internal provider endpoints are configuration, not arbitrary user fetch targets. The fact that Crawl4AI and SearXNG run on private container addresses must not cause the fetch policy to allow any caller-supplied private URL. Use distinct provider-connectivity and public-target allowlists.

### 16.4 Content, commands, and secrets

Fetched text is evidence, not an instruction to the host or DWS. Do not execute embedded commands, import browser cookies, or let a document modify provider configuration. Disable or avoid upstream arbitrary-script/hook surfaces for untrusted callers.

Enforce download, decompression, parsing, rendering, and output limits. Isolate crawlers and untrusted parsers where practical. Use generated paths and opaque IDs to prevent traversal. QMD subprocesses receive validated arguments, bounded stdin/stdout, and a minimal environment.

Provider keys stay in secret configuration, not tool inputs/results, resources, URLs, logs, or `_meta`. No metadata field is treated as a secure vault. Hosted escalation may send the query, target URL, or content to another provider; this must be opt-in and recorded.

### 16.5 Access restrictions and budget approval

Respect the configured robots/access policy. Do not introduce CAPTCHA evasion, paywall bypass, authenticated scraping, or content redistribution policies by implication. Those are separate product/legal decisions, not automatic features of “deep” search.

The host skill may ask for consent, but DWS enforces hard limits itself. A model-provided approval boolean alone does not authorize exceeding owner-configured cost, scope, or page ceilings.

## 17. Non-functional requirements and metrics

### 17.1 Required qualities

| ID | Requirement | Verification |
|---|---|---|
| NFR-001 | Model-free default execution | No inference/model download in the offline retrieval and baseline fixture tests |
| NFR-002 | Bounded resource usage | Concurrency, queue, download, crawl, and response limits enforced |
| NFR-003 | Recoverable acknowledged work | Restart/fault tests preserve jobs and retained evidence |
| NFR-004 | Traceable results | Every returned passage resolves to the intended snapshot/location |
| NFR-005 | Honest partiality | Truncation, pending indexing, failures, and uncertain extraction are explicit |
| NFR-006 | Local deployability | One documented Compose startup and tested local-host connection |
| NFR-007 | Replaceable integrations | Provider/retrieval contract tests do not require MCP imports in core |
| NFR-008 | Data ownership | QMD rebuild/upgrade cannot migrate or destroy DWS metadata |
| NFR-009 | Interface compatibility | MCP and CLI results conform to the same DWS payload schema |
| NFR-010 | Observable operations | Queue wait, execution time, retries, cache and index lag separately recorded |
| NFR-011 | Safe exposure | Local interface/SSRF/secret-redaction tests pass |
| NFR-012 | Reproducible builds | Lockfile, image digests, runtime report, and migration version captured |

### 17.2 Proposed budgets

These values make the design testable; they are **not measured capacity or already approved final settings**. The owner may tune them within tested limits.

| Budget | Proposed start |
|---|---|
| Search results | 10 default, 20 per response maximum |
| Fetch excerpt | About 800 characters; maximum 2,000 |
| Retrieval passages | 8 default, 20 maximum, within total response limit |
| Normal read/retrieve response | 20 KiB serialized payload target; paginate larger requests |
| Global ordinary tool-response ceiling | 64 KiB serialized payload unless explicitly using artifact export |
| Default crawl | 100 scheduled URLs, depth 2 |
| Hard ordinary crawl limit | 1,000 scheduled URLs unless owner configuration raises it |
| HTTP acquisition concurrency | 8 initially |
| Rendered acquisition concurrency | 2 initially |
| QMD lexical search concurrency | 2 initially |
| QMD index updates | 1 |
| Active crawl-job execution | 1 initially; individual pages can acquire concurrently |
| Initial job poll suggestion | 10 seconds; increase for long-running operations |
| Example download ceiling | 25 MiB per source, with explicit PDF/profile override |
| Capacity queue | 64 pending operations before backpressure, subject to benchmark |

Limits must yield valid structured results or explicit errors—not byte-truncated JSON. Token counts depend on the model tokenizer; byte/character budgets are enforcement mechanisms, not exact token predictions.

### 17.3 Test targets, not promises

The baseline local benchmark should use a documented machine and at least 1,000 controlled text documents, including duplicates, long documents, tables, and scope filters. A larger 10,000-document run is useful before increasing crawl defaults.

Provisional objectives are warm lexical retrieval p95 below 2 seconds at two active searches and job-status p95 below 250 milliseconds when the host is not resource-starved. Cold process startup and indexing contention must be reported separately. External network/search latency is excluded from these database targets.

Do not reject the architecture solely because an untuned laptop misses a provisional number; identify whether the bottleneck is QMD startup, parsing, index write time, disk, CPU, or queueing. Conversely, do not report success using only idle single-query latency.

### 17.4 Retrieval and evidence quality

Create a hand-checked fixture set of exact terms, phrase variants, synonyms, title-only matches, long-document passages, conflicting dates, and cross-workspace collisions. Measure relevant-result recall at a fixed K and verify every returned passage against its snapshot.

A lexical-only system is expected to miss some semantic variants. Record those misses and let the host reformulate; do not hide them with an undocumented model call. Set quality thresholds after the fixture corpus is agreed rather than inventing an accuracy percentage now.

### 17.5 Operational metrics

Record locally:

- Admission wait, provider latency, normalization time, QMD startup/search/update time, database busy/retry time, and checkpoint/maintenance time.
- Queue size, active jobs, outstanding URLs, failed attempts, recovered jobs, and cancellation delay.
- Artifact bytes by type, pinned bytes, expired bytes, index size, indexing lag, and retained-but-never-read content.
- Search-cache and document-cache hits separated by same-run, same-workspace, and cross-workspace reuse.
- Output bytes, number of passages/results, truncation, and hosted-provider usage.

An LLM-token dashboard is optional and can use estimates. The stronger V1 invariant is that DWS itself performs no default model inference, while its outputs are bounded and traceable.

## 18. Host-side agents, skills, and plugins

The integration package is separate from the engine:

```text
Default host agent + generic research skill + profile
Technical research agent + technical source/evidence profile
Funda agent + investment-specific methodology
                         │
                         ▼
                  Same DWS interface
```

The host owns question decomposition, query formulation, semantic source judgment, contradiction assessment, sufficiency, summarization, and report generation. DWS owns acquisition, extraction signals, source metadata, freshness, storage, and bounded retrieval.

A profile may describe preferred source types, query/acquisition budgets, evidence expectations, and output format. Instructions and machine-readable constraints should be versioned together, but hard deployment limits are enforced inside DWS. A generic “two sources per claim” rule is not universal: primary-source questions may need one authoritative record, while disputed claims need more investigation.

The default skill should teach the host to search first, acquire selected sources, retrieve/read relevant passages, acknowledge extraction or coverage gaps, and pin/export evidence cited in durable outputs. It should never treat search snippets alone as verified source content.

Plugin/agent/skill packaging differs across hosts. Supply a portable reference skill and per-host installation adapters only for tested hosts. MCP standardizes the server interface; it does not make every host’s sub-agent or skill format portable automatically.

`dws research ...` is not a core V1 command. A future launcher could invoke an external host workflow, but it must be clearly labeled and must not smuggle an internal research engine into the core package.
## 19. Delivery milestones and acceptance tests

### 19.1 Implementation sequence

| Milestone | Deliverable | Exit condition |
|---|---|---|
| **M0 — Verify and freeze** | Tested FastMCP/QMD/runtime pins, Compose topology audit, small fixture corpus, resolved critical gates | No unsupported version assumption; lexical-only QMD and local host connection demonstrated |
| **M1 — Acquisition foundation** | Domain models, safe URL policy, search adapters, lightweight fetch, Crawl4AI path, canonical artifact pipeline | Search/fetch fixtures pass; stored snapshots have provenance and bounded outputs |
| **M2 — Lexical retrieval** | QMD adapter, collection/snapshot mapping, indexing outbox, bounded retrieve/read | Scoped retrieval, index lag, rebuild and no-inference tests pass |
| **M3 — Durable crawl and concurrency** | Crawl jobs, limits, leases, checkpoints, cancellation, QMD admission control | Fault, burst, reconciliation, and maintenance tests pass |
| **M4 — Product integration** | FastMCP adapter, daemon-aware CLI, one Compose startup, security/configuration, pin/export/backup, default host skill | End-to-end user journeys work after restart and restore |
| **M5 — Optional capability expansion** | Firecrawl/Spider/TinyFish refinements, native MCP Tasks, measured tuning | Each addition proves benefit and preserves baseline contracts |

The sequence is a dependency order, not a delivery-time estimate. A prototype may combine steps, but it must not skip the data-integrity and security exit criteria.

### 19.2 Acceptance-test catalog

Tests should use local fixtures and fake provider responses for deterministic checks, plus a separately labeled live smoke suite. Unrelated internet failures must not make the core test suite nondeterministic.

| ID | Scenario and required result | Coverage |
|---|---|---|
| AT-001 | Start the baseline from the documented Compose invocation with hosted keys absent; useful fixture operations work | FR-029, FR-032, NFR-006 |
| AT-002 | Invoke equivalent MCP and CLI operations; payloads validate against the same DWS schemas | FR-001, FR-031, NFR-009 |
| AT-003 | Primary search times out; enabled fallback returns normalized results and records both attempts | FR-004 |
| AT-004 | Legitimate empty search, malformed output, unsupported filters and all-provider failure produce distinct outcomes | FR-002, FR-003, FR-005 |
| AT-005 | Fetch static HTML/text without a browser; browser-required fixture escalates within budget | FR-006, FR-008 |
| AT-006 | Fetch a text PDF with page mapping; scanned/complex PDF is warned or rejected without fabricated text | FR-009, FR-010 |
| AT-007 | Every fetch excerpt matches its normalized snapshot; hashes and source/fetch dates are correct or explicitly unknown | FR-007, FR-022, NFR-004 |
| AT-008 | Fetch the same bytes twice; reuse content safely while preserving acquisition history and memberships | FR-022, FR-027 |
| AT-009 | Source changes; the old snapshot URI still returns old retained content and the new capture gets a new snapshot identity | FR-022, FR-023 |
| AT-010 | Crawl contains cycles, off-scope URLs and failures; limits hold and all final counters reconcile | FR-011, FR-013 |
| AT-011 | Poll immediately after accepted submission; the job exists. Repeat its idempotency key; no duplicate crawl starts | FR-012, FR-027 |
| AT-012 | Kill/restart API while worker runs; acknowledged job remains queryable and worker ownership is unaffected | FR-012, FR-014, NFR-003 |
| AT-013 | Kill/restart worker at multiple checkpoints; recover or fail explicitly without blindly restarting completed pages | FR-014 |
| AT-014 | Request cancellation during acquisition; new work stops and residual/provider work is disclosed | FR-028 |
| AT-015 | Run lexical retrieval with model credentials absent and inference/download paths blocked; no embeddings, expansion or reranking occur | FR-015, FR-032, NFR-001 |
| AT-016 | Create colliding terms across workspaces and run/crawl subsets; retrieval scope is correct and coverage flags honest | FR-016, FR-020 |
| AT-017 | Return relevant passages from a long document; bounds, lines/sections and source mappings verify | FR-017, NFR-004 |
| AT-018 | Save a document while indexing is unavailable; direct read works and retrieval reports pending/failed index state | FR-018, FR-019, FR-020 |
| AT-019 | Delete/rebuild only QMD’s index; retained artifacts re-index and DWS metadata/jobs remain intact | FR-021, NFR-008 |
| AT-020 | Submit bursts of 1/5/10/20/50 callers while indexing; admission limits hold and busy/queue/latency metrics are captured | FR-025, FR-033, NFR-002 |
| AT-021 | Trace metadata transactions; none includes network/browser/QMD wait; logical operations do not interleave on one connection | FR-026 |
| AT-022 | Run multiple CLI callers; all shared-store updates obey the same global indexing and maintenance policy | FR-025, FR-026 |
| AT-023 | Pin, expire and clean artifacts; pins survive, expired URIs report expiry, and cleanup dry-run matches actual effects | FR-024 |
| AT-024 | Simulate disk pressure; bulk work pauses/fails safely without deleting pinned evidence | FR-024, NFR-002 |
| AT-025 | Back up and restore metadata/artifacts, rebuild QMD, and verify a known pinned citation | FR-021, FR-022, FR-029 |
| AT-026 | Try loopback/private/metadata targets, redirects, alternate IP forms and DNS changes; outbound policy blocks them | FR-030, NFR-011 |
| AT-027 | Inject secret-looking data, path traversal and shell metacharacters; no execution or secret leakage occurs | FR-030, NFR-011 |
| AT-028 | Oversized, malformed and decompression-heavy input stops within configured limits and leaves no uncontrolled staging growth | FR-006, FR-030 |
| AT-029 | Very large search/crawl/read/retrieve results remain valid JSON, bounded, paginated or explicitly truncated | FR-031, NFR-002 |
| AT-030 | Host skill performs search→fetch→retrieve→read and exports/pins cited evidence without DWS generating a report | FR-034 |
| AT-031 | Update or restart dependencies using pinned builds; migration/readiness gates prevent traffic against an unready index | NFR-006, NFR-012 |
| AT-032 | Enable an optional provider/profile; it improves identified failures without changing schemas or silently enabling paid/model behavior | FR-035, NFR-007 |
| AT-033 | Native Tasks-capable and ordinary clients observe the same underlying DWS job lifecycle, when the optional adapter is enabled | FR-036 |
| AT-034 | Install an added fake provider using only the provider interface/configuration; core and public interfaces do not import its details | FR-001, NFR-007 |
| AT-035 | Verify default port bindings and actual intended host connectivity; no unexpected upstream ports are published | FR-029, FR-030 |
| AT-036 | Inspect both SQLite runtimes, QMD/FastMCP identities and image digests; report the exact tested builds | NFR-012 |

### 19.3 V1 release boundary

All P0 requirements need passing acceptance evidence or an explicit owner-approved scope amendment. Firecrawl, Spider, native Tasks, vector retrieval, and hosted-service success are not prerequisites for the default V1 release. They must not delay a working local baseline without a demonstrated coverage need.

The implementation handoff should contain this PRD, a dependency/runtime manifest, contract schemas, the fixture corpus, test results, operational commands, and a restore demonstration. None of those results is implied to exist merely because this document lists them.

## 20. Technology decision matrix

This section records alternatives without claiming an exhaustive benchmark of the ecosystem. “Not selected” means not selected for this workload and phase.

### 20.1 Framework, deployment, and orchestration

| Option | Why it was attractive | Why selected or not selected | Revisit condition |
|---|---|---|---|
| **FastMCP** | Familiar declarative Python style and framework conveniences | **Selected by owner**, despite earlier recommendation for direct SDK minimalism; core isolation contains framework coupling | A required client/runtime cannot be supported or measured maintenance cost becomes unacceptable |
| Official Python MCP SDK directly | Fewer framework abstractions and direct protocol access | Not chosen after explicit owner preference; not treated as inferior or unsupported | A small adapter migration delivers a demonstrated compatibility advantage |
| Internal research orchestrator | Standalone research/report CLI; one centrally controlled workflow | Rejected for core: domain reasoning changes by project and duplicates host intelligence | Separate opt-in application package, not a silent expansion of core |
| Host agent + skill + profile | Domain-specific methodology with reusable retrieval infrastructure | Selected; host portability and token cost remain integration concerns | Need a tested standalone host launcher |
| Shared local HTTP daemon | One admission point, cache, job view and index lifecycle | Selected baseline | A specific host requires another transport |
| stdio-only independent servers | Simple subprocess installation | Not default for shared-state concurrency; optional thin bridge remains possible | The bridge can reach the same shared service without spawning competing index owners |
| Single Compose deployment | Reproducible lifecycle and explicit dependencies | Selected by owner | Only change through explicit owner decision |
| Host Python plus scattered manually installed services | Convenient early debugging | Not the product baseline; still possible in a developer environment | No impact on canonical deployment or storage ownership |
| Kubernetes / distributed services | Enterprise scaling features | Rejected for V1 workload and operational cost | Real multi-machine requirements, not hypothetical growth |

### 20.2 Retrieval and storage alternatives

| Option | Trade-off | Decision |
|---|---|---|
| **QMD lexical FTS5/BM25** | Ready-made document workflow, but another runtime and lifecycle boundary | Selected; model paths disabled and tested |
| Hand-written SQLite FTS5 | Small Python-native stack, full control, more indexing/retrieval code to own | Not selected as the primary index after QMD choice; do not implement both |
| No index, manifests/files only | Minimum indexing overhead, weak repeated cross-document lookup | Useful for temporary or tiny explicit sets, not the sole general retrieval path |
| ripgrep/direct text scan | Simple exact matching in bounded selected artifacts | Diagnostic/fallback utility, not a second primary search subsystem |
| QMD semantic/hybrid search | Potentially better conceptual recall, requires more model/runtime work | Deferred until query-quality evidence justifies it |
| Vector libraries/databases such as FAISS, LanceDB, Chroma or Qdrant | Additional semantic retrieval architecture and lifecycle to manage | Discussed alternatives, not benchmarked or selected; no embedding corpus requirement in V1 |
| Tantivy-based search, Meilisearch or Typesense | Alternative search-engine integration and operations | Not selected because QMD already covers the chosen lexical role; no claim of inferior speed |
| QMD SQLite as the entire DWS database | One physical file, but mixed schema/lifecycle ownership | Rejected for V1; storage simplification is illusory |
| Separate DWS SQLite + QMD SQLite + artifacts | Two files but no two database servers; clear ownership/rebuild path | Selected |
| Turso Rust engine for DWS metadata | Concurrent-write option with different integration/compatibility considerations | Deferred until measured write contention remains after transaction fixes |
| Turso as transparent QMD replacement | Would appear to unify engine choice | Not supported as a drop-in assumption: QMD’s FTS5 backend and Turso’s FTS differ [S21] |
| PostgreSQL for DWS metadata | A robust service database, additional deployment/backup operations | Not needed initially; reconsider only for a demonstrated workload/feature need |


**Turso scope clarification:** the alternative under discussion is the newer Rust database engine, not simply the older libSQL fork or the hosted Turso service. Its concurrent-write path uses opt-in MVCC and requires transaction-conflict handling; writing independent rows concurrently does not eliminate hot-row conflicts. For DWS, this is an option to benchmark against a measured metadata bottleneck, not a default performance upgrade. [S21] [S22]

QMD replacement is a separate issue: compatibility documentation distinguishes Turso’s full-text implementation from SQLite FTS, and does not support mixed SQLite/Turso multi-process access to the same file. A migration would require its own adapter/schema tests, not swapping a filename or Python package. [S21]

### 20.3 Acquisition and execution alternatives

| Option | Decision and rationale |
|---|---|
| Crawl4AI | Primary browser/crawl integration already agreed; verify deployed capabilities and resource profile |
| Firecrawl always on alongside Crawl4AI | Not default: potentially useful coverage but significant overlap and supporting services |
| Firecrawl optional self-host profile | Keep as the most direct self-hosted backup candidate; require benefit/resource measurements |
| Firecrawl hosted API | Not a baseline dependency; user prefers not to rely on its hosted limits/cost. No universal pricing judgment is asserted |
| TinyFish | Optional distinct APIs, not one undifferentiated agent tool; hosted escalation remains explicit |
| Spider Rust | Candidate backend, not an assumed “second-best” ranking; evaluate before adding runtime complexity |
| Raw Playwright/Scrapy traversal | Valid building blocks, but rebuilding a crawler is not V1’s objective; revisit for a concrete capability gap |
| Always use a browser | Rejected as a default; cheap acquisition is sufficient for many supported fixtures |
| Separate DWS Redis/Celery-style queue | Not required initially; SQLite-backed jobs and one worker fit the proposed workload |
| FastMCP task framework as the application database | Rejected: transport lifecycle must not own crawl state/provenance |
| Optional native MCP Tasks mapping | Allowed after compatibility tests, using the same DWS JobService |
| Permanent progress subscriptions | Deferred; polling satisfies the local baseline more simply |
| Automatic LLM summary of every page | Rejected: unwanted inference, cost, loss of source detail and unnecessary work |
## 21. Architecture decision records

The ADRs are the durable explanation of **why** DWS has this shape. Each records the cost accepted and the condition for reopening it. They supplement—not override—the requirement and verification status above.

### ADR-001 — Name the product Deep Web Search and the CLI `dws`
**Status:** Accepted, explicit owner decision.  
**Decision:** Use DWS consistently in product terminology, commands, resource schemes, examples, and documentation.  
**Why:** The name describes the reusable search utility better than the earlier DeepWeb shorthand.  
**Not chosen:** Continuing multiple names or exposing new `deepweb://` identifiers.  
**Consequence / revisit:** Rename illustrative legacy examples during implementation; compatibility aliases are needed only if an actual deployed client already used them.

### ADR-002 — Optimize for one owner and many concurrent callers
**Status:** Accepted.  
**Decision:** Run locally with one shared service, while supporting multiple host projects and agents.  
**Why:** The workload is personal but can burst; user count is not concurrency.  
**Not chosen:** Either an enterprise platform or a strictly sequential single-agent implementation.  
**Consequence / revisit:** Use admission control and workspace organization without enterprise tenancy. Revisit deployment/security only when real remote or multi-user requirements appear.

### ADR-003 — Remove research orchestration from core
**Status:** Accepted after comparing both architectures.  
**Decision:** DWS acquires/retrieves evidence; the host plans, interprets and writes reports.  
**Why:** Technical research and Funda research have different methods and change independently of web acquisition. The owner explicitly preferred this boundary.  
**Not chosen:** A generic autonomous planner/summarizer/report generator embedded in DWS.  
**Consequence / revisit:** A plain DWS CLI does not independently produce a research report. A future standalone research product must remain a separate consumer/package.

### ADR-004 — Ship a default host integration, not a mandatory agent runtime
**Status:** Accepted direction; packaging proposed.  
**Decision:** Provide a reference agent/skill/profile alongside the MCP/CLI, with specialized profiles outside core.  
**Why:** Avoid making every project invent the workflow while preserving domain-specific reasoning.  
**Not chosen:** Hard-coded model vendors, one investment methodology in DWS, or an assumption that all hosts share one plugin format.  
**Consequence / revisit:** Maintain tested host adapters; add a host only when its installation and tool behavior can be verified.

### ADR-005 — Use standalone Python FastMCP rather than the direct SDK
**Status:** Accepted, explicit owner preference.  
**Decision:** Target a verified compatible FastMCP 4.x build in the thin MCP adapter.  
**Why:** Familiar Python/FastAPI-style development is valuable to the owner. An earlier minimal-dependency argument for the official SDK did not outweigh that preference.  
**Not chosen:** Direct SDK as the default adapter; confusing Python FastMCP with the TypeScript project of similar name.  
**Consequence / revisit:** Pin carefully and keep core independent. A switch needs concrete compatibility or maintenance evidence, not stylistic disagreement.

### ADR-006 — Expose capabilities rather than providers
**Status:** Accepted.  
**Decision:** Small stable tool set with search, acquisition, retrieval and job semantics.  
**Why:** Models should not learn SearXNG/Firecrawl/Crawl4AI plumbing or choose low-level failover.  
**Not chosen:** Dozens of provider-named tools or an unrestricted generic command tool.  
**Consequence / revisit:** Advanced debugging belongs in admin controls. Split a tool only when distinct inputs/outcomes improve reliable selection.

### ADR-007 — Keep providers behind core interfaces
**Status:** Accepted.  
**Decision:** Normalize provider outputs through stable capability ports and a common document pipeline.  
**Why:** The owner wants to replace a weak backend without rewriting every caller.  
**Not chosen:** Provider calls and fallback logic inside MCP decorators.  
**Consequence / revisit:** Adapter work and contract tests are required. Introduce specialized interfaces only for real semantics that the current capability model cannot express safely.

### ADR-008 — Return handles and evidence, not entire artifacts
**Status:** Accepted.  
**Decision:** Compact structured metadata, bounded excerpts/passages, snapshot addresses and explicit pagination.  
**Why:** The host needs enough evidence to decide what to inspect, not every acquired byte.  
**Not chosen:** Full-page search results, embedded whole PDFs, or entire crawl manifests by default.  
**Consequence / revisit:** Some tasks require additional reads. Resource use is not automatically token-free; test the host’s actual handling.

### ADR-009 — Use deterministic excerpts instead of automatic summaries
**Status:** Accepted.  
**Decision:** Fetch returns text selected from the normalized snapshot; host inference is optional and external.  
**Why:** Many acquired sources are never important enough to justify a summary, and a summary is not primary evidence.  
**Not chosen:** One LLM call per fetched document.  
**Consequence / revisit:** Excerpts may be less semantically comprehensive. Add only an explicitly requested external workflow, not hidden summarization in fetch.

### ADR-010 — Distinguish discovery, acquisition and traversal
**Status:** Accepted.  
**Decision:** Search returns candidate records, fetch acquires a selected URL, and crawl explores a bounded graph.  
**Why:** They have different costs, failure modes and output sizes.  
**Not chosen:** Treating search hits as downloaded documents or forcing every native crawler through public fetch calls.  
**Consequence / revisit:** Maintain one frontier owner and common snapshot outcomes; revisit native-provider routing when resumability or budget controls are insufficient.

### ADR-011 — Use SearXNG as primary discovery
**Status:** Accepted.  
**Decision:** SearXNG is the default broad-search adapter.  
**Why:** It matches the original metasearch requirement while keeping the normal setup locally controlled.  
**Not chosen:** Treating it as a proprietary standalone web index or assuming guaranteed upstream availability.  
**Consequence / revisit:** Keep engine/API configuration and fallback diagnostics explicit. Reconsider primary ranking only using observed coverage and reliability.

### ADR-012 — Build capability-specific, dependency-aware fallbacks
**Status:** Accepted direction; exact sequence proposed.  
**Decision:** DDGS backs discovery; optional targeted hosted APIs and self-hosted acquisition backends serve the capabilities they actually provide.  
**Why:** A second product name may share the same failed upstream service. Fetch failure is not search failure.  
**Not chosen:** Blind provider fan-out or SearXNG→Firecrawl assumed independent without checking its backend.  
**Consequence / revisit:** Monitor shared failure points and test eligible escalation. Change ordering based on useful coverage per cost, not popularity.

### ADR-013 — Keep Crawl4AI as the primary browser/crawl component
**Status:** Accepted.  
**Decision:** Use Crawl4AI through an adapter; propose cheap HTTP/parser acquisition ahead of browser work where appropriate.  
**Why:** It was the owner’s original acquisition choice and keeps browser-oriented functionality reusable.  
**Not chosen:** Launching a browser for every supported static file, or rebuilding a general crawler immediately.  
**Consequence / revisit:** Browser resource/security controls and extraction tests are required. Replace or augment only for measured deficiencies.

### ADR-014 — Make self-hosted Firecrawl optional rather than mandatory
**Status:** Proposed baseline, not a final rejection of Firecrawl.  
**Decision:** Maintain an optional complete Compose profile after evaluation.  
**Why:** The owner wants a solid backup, but two broad crawlers can duplicate effort and increase supporting-service overhead.  
**Not chosen:** Requiring a hosted Firecrawl plan or promising self-host/cloud parity.  
**Consequence / revisit:** Some hard pages may remain unsupported in base V1. Promote Firecrawl when its measured coverage gain justifies its footprint and maintenance.

### ADR-015 — Defer Spider until a focused backend comparison
**Status:** Deferred.  
**Decision:** Preserve an adapter path for Spider’s Rust engine without deploying it by default.  
**Why:** It may be useful for traversal, but “next best crawler” has not been established for this corpus.  
**Not chosen:** Adding another runtime merely to maximize the list of supported libraries.  
**Consequence / revisit:** Benchmark scope control, recovery, output quality and local resource cost against the existing crawl path; distinguish the open-source engine from hosted services.

### ADR-016 — Use one top-level Compose deployment
**Status:** Accepted, explicit owner decision.  
**Decision:** One documented Compose entry point, default services, optional profiles and persistent volumes.  
**Why:** Reproducible personal operation is more valuable than scattered manual installation instructions.  
**Not chosen:** One container at all costs, a cluster, or blind concatenation of upstream Compose files.  
**Consequence / revisit:** Audit vendor support services and native dependencies. Developer shortcuts must not replace the supported product topology.

### ADR-017 — Treat packages and containers as complementary
**Status:** Proposed packaging baseline.  
**Decision:** Install Python/Node dependencies inside images; run service-oriented providers as services.  
**Why:** Package APIs determine integration style; Compose determines deployment lifecycle. They are not competing universal choices.  
**Not chosen:** Assuming `pip install` provides Firecrawl’s complete service stack or that a Docker image eliminates dependency cost.  
**Consequence / revisit:** A direct Crawl4AI library adapter remains possible if it materially simplifies the tested deployment.

### ADR-018 — Use QMD lexical retrieval instead of building another FTS layer
**Status:** Accepted.  
**Decision:** QMD is the sole primary document-search subsystem, through a supported lexical interface.  
**Why:** Reuses a ready-made document workflow and avoids owning every search/index feature.  
**Not chosen:** Parallel QMD plus hand-built FTS5 indexes for the same corpus.  
**Consequence / revisit:** Accept a Node/native dependency boundary. Reconsider only if scope, performance, model-free operation or maintenance cannot meet the gates.

### ADR-019 — Do not generate vectors for every acquired file
**Status:** Accepted.  
**Decision:** No default embeddings, semantic/hybrid search, model expansion or reranking.  
**Why:** The workload is mostly ad hoc and the benefit is unmeasured; indexing everything semantically adds unnecessary work.  
**Not chosen:** A vector database as a mandatory architectural component.  
**Consequence / revisit:** Lexical recall can miss synonyms and conceptual matches. Add optional semantic retrieval only when a judged query set demonstrates enough value.

### ADR-020 — Keep DWS and QMD database ownership separate
**Status:** Accepted after explicit comparison.  
**Decision:** `dws.sqlite` stores application state; QMD owns its SQLite file; normalized artifacts remain independent.  
**Why:** QMD index maintenance must not own jobs, provenance, retention or DWS schema migrations. Two files do not imply two database services.  
**Not chosen:** Putting DWS tables inside QMD’s database to achieve one physical file.  
**Consequence / revisit:** Maintain mappings and eventual-index consistency. Sharing a file requires a stronger benefit than aesthetic simplicity.

### ADR-021 — Preserve useful snapshots, not every response forever
**Status:** Accepted direction; TTLs proposed.  
**Decision:** Retain accepted normalized evidence, keep originals selectively, and provide pin/export/expiry controls.  
**Why:** One-off research still needs within-run verification and restart recovery, but indefinite raw archives can grow needlessly.  
**Not chosen:** Deleting source files after QMD indexing or permanently retaining every failed/challenge response.  
**Consequence / revisit:** A cited unpinned source may expire; host skills must pin/export durable evidence. Tune retention from measured usage.

### ADR-022 — Measure cache value rather than assume it
**Status:** Accepted.  
**Decision:** Distinguish freshness from retention and instrument several types of reuse.  
**Why:** One owner may reread sources frequently within a run, yet rarely revisit unrelated topics later.  
**Not chosen:** A promised cache-hit rate or a global “cache forever” strategy.  
**Consequence / revisit:** Keep inexpensive burst/in-flight coalescing, then tune longer caching only with evidence and source freshness needs.

### ADR-023 — Retain ordinary SQLite; defer Turso
**Status:** Accepted direction / deferred migration.  
**Decision:** Use short WAL-mode metadata transactions and fix ownership/scheduling first.  
**Why:** The expected small metadata writes do not yet justify another engine. Turso’s write-concurrency features do not fix QMD lifecycle or startup contention.  
**Not chosen:** A speculative migration because several agents might be active.  
**Consequence / revisit:** Prototype Turso for DWS metadata only if measured writer waiting remains material. Do not assume it transparently replaces QMD FTS5.

### ADR-024 — Bound QMD calls and serialize its updates
**Status:** Accepted direction; limits proposed.  
**Decision:** Central search admission, one updater, coordinated bootstrap/maintenance and release-specific tests.  
**Why:** Unrestricted CLI process startup can contend even when operations appear read-oriented.  
**Not chosen:** One independent QMD process/update per agent with no global limit.  
**Consequence / revisit:** Some calls queue briefly. Raise concurrency or adopt a persistent wrapper only after separating startup, query and indexing bottlenecks.

### ADR-025 — Make the shared daemon the normal CLI access path
**Status:** Proposed refinement preserving the accepted shared-core design.  
**Decision:** The normal CLI uses the daemon’s contracts; direct core access is controlled maintenance/development behavior.  
**Why:** Independent CLI processes would otherwise bypass global scheduling and index ownership.  
**Not chosen:** “Same Python core” interpreted as unrestricted multi-process writes to shared files.  
**Consequence / revisit:** The daemon must be running for ordinary shared-store operations; an offline mode must acquire exclusive coordination.

### ADR-026 — Own durable execution independently of MCP Tasks
**Status:** Accepted.  
**Decision:** DWS persists jobs, leases, checkpoints, cancellation and results; protocol Tasks are optional projections.  
**Why:** CLI, providers and MCP must observe the same recoverable execution state regardless of SDK changes.  
**Not chosen:** Using a framework Task object as the entire database schema or relying on `asyncio.create_task` for crash survival.  
**Consequence / revisit:** Some job infrastructure is owned by DWS. Adopt a worker framework only when it preserves these boundaries and demonstrably reduces complexity.

### ADR-027 — Start with polling, not permanent subscriptions
**Status:** Accepted.  
**Decision:** Use explicit status calls with wait/backoff hints.  
**Why:** Progress is occasional and local; a live notification subsystem is not needed for the stated workflow.  
**Not chosen:** Streaming every fetched page or holding a research-length request open.  
**Consequence / revisit:** Completion discovery has polling delay. Add notifications for a real interactive UI or supported host need, without making them authoritative storage.

### ADR-028 — Keep application state distinct from protocol continuation
**Status:** Accepted conceptual correction.  
**Decision:** Job progress, snapshot storage, resource addresses and MRTR continuation have different ownership.  
**Why:** Confusing them causes process/session coupling and invalid recovery assumptions.  
**Not chosen:** Storing research progress or hundreds of documents in protocol `requestState`.  
**Consequence / revisit:** Let the pinned framework implement protocol interaction; keep durable business handles explicit across all transports.

### ADR-029 — Preserve local security controls
**Status:** Accepted direction.  
**Decision:** Loopback publication, safe outgoing URL policy, secrets isolation, budgets and untrusted-content handling remain mandatory.  
**Why:** An agent-driven web fetcher can access sensitive local services even without public traffic.  
**Not chosen:** “Personal” as a reason to accept arbitrary URLs, scripts, file paths or provider keys in tool output.  
**Consequence / revisit:** Some targets require deliberate opt-in. Remote exposure triggers a new authentication/access review.

### ADR-030 — Do not add enterprise infrastructure by default
**Status:** Accepted direction.  
**Decision:** No DWS-owned Redis queue, service mesh, enterprise IAM or distributed database in V1.  
**Why:** They solve unstated workload requirements and increase operational burden.  
**Not chosen:** Pretending that upstream containers have no supporting services; required vendor components still count.  
**Consequence / revisit:** Revisit a specific component when measurement proves a limitation, not because “production” is used as a label.

### ADR-031 — Use immutable evidence identity and explicit partiality
**Status:** Proposed implementation baseline supporting accepted evidence goals.  
**Decision:** Stable snapshot IDs, hashes, provenance, location mapping and warning/coverage fields.  
**Why:** Cached content can change; retrieval can lag; parsers can lose information. A source-linked artifact must say exactly what it represents.  
**Not chosen:** Treating relevance as truth confidence, fetch time as publication time, or a completed crawl as complete web coverage.  
**Consequence / revisit:** More metadata than a raw scraper, but less ambiguity for every downstream research workflow.

### ADR-032 — Pin tested versions and preserve uncertainty honestly
**Status:** Required release practice.  
**Decision:** Resolve exact builds at M0; record source, version, digest, runtime and compatibility evidence.  
**Why:** Earlier conversation and mutable documentation contained inconsistent release claims. Intentional uncertainty is safer than installing an unverified historical version.  
**Not chosen:** Copying “latest stable” assertions from chat, using mutable image tags, or treating `main` as a release.  
**Consequence / revisit:** Upgrades require the contract/restore/concurrency suite and an explicit dependency record.

## 22. Discussion chronology and superseded statements

### 22.1 How the design evolved

| Stage | Discussion | Durable outcome |
|---|---|---|
| C-01 | Initial reusable MCP/CLI idea; SearXNG, Crawl4AI and backups | One provider-neutral search/acquisition utility for all projects |
| C-02 | MCP concepts explained through FastAPI | Host owns MCP client; MCP is an adapter, not the application engine |
| C-03 | Tools, resources and context size | Actions return compact results; retained artifacts are addressable and read on demand |
| C-04 | Excerpt versus summary | Default fetch uses deterministic text selection; no automatic page-summary model |
| C-05 | Long jobs and Tasks | Application job state is durable and separate from protocol Tasks and artifacts |
| C-06 | Statelessness, MRTR and subscriptions | Explicit IDs; continuation is not progress; polling selected for V1 |
| C-07 | Concrete search/fetch/crawl outputs | Separate discovery records, single snapshots, crawl jobs/manifests, and passage retrieval |
| C-08 | Internal research orchestrator proposed | Initially attractive for standalone reports, but introduced domain/model coupling |
| C-09 | Owner proposed host-side research agent/skill instead | Internal research orchestration removed; default/specialized host integrations retained |
| C-10 | FastMCP compared with direct official SDK | Earlier direct-SDK recommendation superseded by explicit owner FastMCP preference |
| C-11 | Broader crawler/search/retrieval research requested | Adapter candidates identified; unreceived deep-research reports not treated as evidence |
| C-12 | Renamed DeepWeb to Deep Web Search; questioned indexing costs | DWS name; no automatic semantic indexing of every download; measure reuse |
| C-13 | Package versus Docker and self-hosted backup discussion | One Compose deployment; Firecrawl evaluated as optional complete profile, not blindly always-on |
| C-14 | QMD text-only and “one database” question | QMD lexical-only accepted; separate DWS/QMD SQLite and retained files |
| C-15 | Concurrent agents and Turso investigation | Bounded scheduling, one QMD updater, short SQLite transactions; defer Turso migration |
| C-16 | Request for an authoritative PRD and decision history | This consolidated baseline, status labels, gates, tests and ADRs |

The learning questions were useful to establish boundaries, but they are not independent requirements. This document preserves their architectural conclusions rather than every conversational analogy.

### 22.2 Corrections and statements not to carry into implementation

| Earlier simplification or claim | Authoritative interpretation now |
|---|---|
| “The latest FastMCP is exactly 4.0.0/4.0.3” | User selected FastMCP and a 4.x target; exact current supported build must be verified and pinned. Do not confuse separate projects with the same name |
| “The SDK does/does not currently implement all modern Tasks behavior” | Runtime and host support are version-sensitive. DWS durability never depends on this claim |
| `research_id` is a special job or protocol state | Host research correlation, job lifecycle and retained artifacts are distinct; core has no research orchestrator |
| `requestState` is progress | It is protocol continuation, not durable job progress |
| “Async keeps the work alive when MCP dies” | Only independent/recoverable execution and persisted state satisfy crash durability |
| “Resources save tokens automatically” | Addressability enables lazy retrieval; the host can still load a huge resource. Bounds and explicit reads create the savings |
| “Structured JSON is automatically cheaper” | Predictable fields reduce reparsing ambiguity; actual token cost still depends on payload size and host injection |
| “Search returns complete contents” | Complete bounded search records, not every result’s webpage body |
| “Fetch is deterministic” | No default reasoning model; remote content and extraction output can still vary |
| “Source URL versus URI” | The relevant distinction is original source location versus retained snapshot address; a URL is itself a kind of URI |
| “All QMD text can be archived safely by deleting source files” | File-backed indexing/cleanup semantics can remove missing/inactive entries; keep independent canonical artifacts |
| “`store.search()` is necessarily text-only” | Use the verified lexical API/CLI; generic search may invoke hybrid/model paths |
| “SQLite allows only one client” | It serializes writers per file; concurrent reads and other work remain possible |
| “One Python lock enforces global concurrency” | Not across separate processes; shared-store ownership requires cross-process coordination |
| “Turso is a drop-in SQLite upgrade for QMD” | Distinguish Rust Turso, libSQL and cloud; QMD driver/FTS compatibility is a separate integration problem |
| “CLI shares core, so each invocation should access files directly” | Shared code is preserved; normal shared-state operations go through the common admission boundary |
| “One Compose means one process, and no Redis anywhere” | Several services/supporting processes may be required. No extra DWS queue is different from no vendor dependency |
| “Bind the app to 127.0.0.1 everywhere” | Publish on host loopback; container-internal binding must permit intended bridge/port access |
| “Any hosted MCP client can connect to localhost” | Only hosts with actual local connectivity can do so without an additional access design |
| “Local stdio has no security problem” | No listening port does not remove process, secret, filesystem or untrusted-input risks |
| “Firecrawl is automatically an independent search fallback” | Verify its backend; it may use the same SearXNG instance |
| “A score of 0.96 is evidence confidence” | Unless explicitly calibrated, it is a ranking/heuristic value, not truth probability |

## 23. Risks, open questions, and verification gates

### 23.1 Verification gates

**Release-blocking** gates must pass for the baseline capabilities they affect. An optional-provider gate blocks that provider’s promotion, not the entire product.

| ID | Question / risk | Evidence required | Disposition |
|---|---|---|---|
| G-01 | Which exact FastMCP/Python/SDK build supports the intended local hosts? | Authoritative package/tag identity, image build, tool/resource/schema/transport tests, locked dependencies | Release-blocking |
| G-02 | Is the selected QMD lexical path genuinely model-free in our image? | No inference, model download or semantic/expansion command in controlled search tests; runtime/dependency audit | Release-blocking |
| G-03 | Does pinned QMD handle concurrent searches, updates and initialization safely? | Stress/boot/maintenance tests; actual SQLite versions and applicable fixes verified | Release-blocking |
| G-04 | Can collection/snapshot/run/crawl scoping produce correct passages? | Known-corpus filter/line-mapping tests; incomplete-coverage behavior verified | Release-blocking |
| G-05 | What exactly runs in the selected Compose images? | Pinned upstream config, dependencies, ports, privileges, health endpoints, volumes and measured resource profile | Release-blocking |
| G-06 | What HTML/PDF extraction is reliable? | Fixture-based page/table/scan tests and honest unsupported/partial outcomes | Release-blocking for supported formats |
| G-07 | Are fallback engines truly useful and sufficiently independent? | Failure-injection tests, configured upstream identity where known, search filter support and limited live smoke tests | Baseline fallback quality gate |
| G-08 | Does Firecrawl or Spider justify becoming a default/optional production backend? | Incremental acquisition success, extraction fidelity, restart behavior, limits and resource cost | Optional-provider gate |
| G-09 | Can the actual local host and CLI use the deployed service securely? | Loopback/bridge/stdio tests, resource-read compatibility, local token/origin behavior and daemon-aware CLI | Release-blocking |
| G-10 | What limits fit the owner’s machine and retention preferences? | Hardware declaration, burst/query/index tests, disk measurement, agreed quota/TTLs | Required configuration sign-off |
| G-11 | Can evidence survive crash, cleanup, upgrade and restore? | Fault-injection, pinning, atomic publication, backup/restore and QMD rebuild demonstrations | Release-blocking |
| G-12 | Are dependencies and distributions acceptable? | License/notice review, native-runtime supply chain, hosted terms, image provenance and dependency inventory | Release-blocking distribution review |

FastMCP’s chosen versioning policy makes exact tested pins especially useful. The project’s official release policy should be consulted during upgrades rather than assuming every minor version is automatically non-breaking. [S05]

### 23.2 Risk register

| Risk | Mitigation | Residual limitation |
|---|---|---|
| R-01: Provider blocking or search gaps | Independent capability fallbacks, safe retries, explicit partial results | No promise of universal site access |
| R-02: Index/database corruption or startup contention | Pinned fixed runtimes, ownership, short transactions, rebuildable index, tested backup | Faults remain possible; restore must be operational |
| R-03: Prompt injection or SSRF | Untrusted-content boundary, target/egress policy, secrets separation, host skill guidance | Third-party browser enforcement must be validated |
| R-04: Lexical retrieval misses concepts | Host query reformulation, judged fixtures, coverage signals | Semantic recall is intentionally not guaranteed |
| R-05: Source expires before a report is revisited | Pin/export workflow, retention visibility, tombstones | Unpinned evidence may legitimately expire |
| R-06: QMD runtime heavier than expected | Measure native/image/startup costs; keep retrieval adapter replaceable | Framework convenience has a packaging cost |
| R-07: Token bloat through model-visible results | Output budgets, passage/read controls, no full manifests by default | Host can still request and inject more content |
| R-08: Duplicate work after crash | Idempotency, leases, provider handles, snapshot reuse | Exactly-once remote execution is not promised |
| R-09: Hidden Compose dependencies | Audit actual images and optional profiles | Upstream services may still require memory/storage beyond DWS itself |
| R-10: Scope creep toward a general agent platform | Non-goals, ADR-003/004, provider-neutral contracts | Separate integrations still need maintenance |
| R-11: Premature database migration | Attribute queue/CPU/write bottlenecks before engine changes | Future measured workloads may still justify Turso/PostgreSQL |
| R-12: Stale documentation/release assumptions | Source ledger, immutable pins at build time, explicit gates | A PRD is not a live dependency registry |

### 23.3 Decisions that are still intentionally open

The exact FastMCP/QMD/image pins, maximum supported local concurrency, hardware-specific queue limits, final artifact TTLs/quotas, detailed QMD subset-filter implementation, and Firecrawl/Spider promotion are not settled by this document. They have named owners and tests rather than being disguised as completed research.

Other deferred questions include authenticated browsing, multilingual semantic retrieval, OCR expansion, richer dashboards, remote exposure, and a standalone host research launcher. None is a reason to enlarge the default dependency set before the baseline works.

## 24. Change log and implementation handoff

### 24.1 Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 9 September 2026 | Consolidated conversation into product requirements, architecture, contracts, 32 ADRs, technology alternatives, verification gates and acceptance tests; preserved accepted owner choices and corrected superseded simplifications |

**Approval status:** Accepted choices reflect the conversation. New numeric defaults, exact topology details and interface refinements are explicitly proposed. This document is a design baseline; it is not a claim of final owner approval of every implementation detail.

### 24.2 Instructions for implementation agents and maintainers

Read Sections 0–8 and the applicable ADRs before changing architecture. Never infer that an earlier conversational example overrides this consolidated boundary. Do not add a model call, vector index, framework-owned job database, public endpoint, or always-on backup stack as an unnoticed “improvement.”

Before coding against version-sensitive behavior, resolve its gate and record the pinned evidence. Implement the smallest complete vertical slice first, preserving snapshot identity, safe output bounds and ownership. Link changes to requirement and acceptance-test IDs.

When a decision changes, append an ADR revision containing: status, date, owner, new evidence, alternatives evaluated, migration/data implications, tests affected, rollback path, and the superseded record. Preserve the reason for the old choice so future agents do not repeatedly rediscover the same trade-off.

### 24.3 Definition of readiness

| State | What this PRD establishes | What implementation must still prove |
|---|---|---|
| Product direction | User, boundaries, selected framework/search/retrieval/storage direction | Owner sign-off on proposed defaults where needed |
| Architecture | Interfaces, data ownership, jobs, deployment model | Exact dependency and host compatibility |
| Correctness | Invariants and test scenarios | Passing automated tests and failure recovery |
| Performance | Measurement plan and provisional targets | Results on the owner’s machine |
| Operations | Backup, cleanup, upgrade and security requirements | A working Compose installation and restore exercise |

**The invariant to preserve:** DWS remains reusable, bounded, locally operable evidence infrastructure. Host research can evolve rapidly without forcing a rewrite of acquisition, storage or retrieval.
## 25. Primary-source ledger

**Inspection date:** 9 September 2026. These are primary documentation, project repositories, configuration or source-code references consulted for the technical baseline. A retrieved page can be cached; a `main`/`master` path can change after inspection. The ledger is not an assurance of live availability or an immutable software bill of materials.

At M0, resolve relevant source links to released tags/commits and image digests, archive the selected configuration, and record test outcomes. A source explains upstream behavior; an ADR explains why DWS chooses to use—or not use—it. Product defaults and requirements in this PRD are original design decisions, not upstream guarantees.

| Reference | Primary source | What it supports / qualification |
|---|---|---|
| [S01] | MCP — Tools | Tool schemas, structured results, resource-link contract; not a hand-written wire implementation. |
| [S02] | MCP — Resources | Resource addressing, templates and host-controlled context behavior. |
| [S03] | Python FastMCP — Installation source | Correct Python project and installation guidance; exact package pin remains G-01. |
| [S04] | Python FastMCP — Releases | Release identity check; retrieved release snapshots had inconsistent freshness. |
| [S05] | FastMCP — Release/versioning policy | Upgrade and exact-pin policy; not an assertion about every future release. |
| [S06] | FastMCP — Tasks | Optional framework task capability; DWS job ownership is an independent design decision. |
| [S07] | SearXNG — Search API | Search request/output options and instance configuration. |
| [S08] | SearXNG — Docker installation | Container deployment and configuration context. |
| [S09] | Crawl4AI — Official repository | Project identity, acquisition/crawl capabilities and deployment references. |
| [S10] | Crawl4AI — Self-hosting | Server deployment and supporting components; actual image must be audited. |
| [S11] | Firecrawl — Self-hosting | Multi-service self-host deployment and documented limitations. |
| [S12] | TinyFish — API documentation | Distinct Search, Fetch, Browser and Agent surfaces. |
| [S13] | DDGS — Official repository | Maintained project identity, library/CLI integration and search-engine behavior. |
| [S14] | Spider — Rust engine repository | Open-source engine identity and crawling capabilities; not a DWS benchmark. |
| [S15] | Trafilatura — Documentation | Main-content extraction role; not browser rendering or all-format parsing. |
| [S16] | QMD — Original repository | CLI workflows and document-search product identity. |
| [S17] | QMD — SDK source | Explicit lexical API versus generic hybrid search entry point. |
| [S18] | QMD — Store source | Text storage, document/index ownership and retrieval internals. |
| [S19] | QMD — Database source | Runtime drivers, WAL/busy handling and initialization behavior. |
| [S20] | QMD — Package manifest | Runtime/native/model-related dependency footprint; not a final DWS lockfile. |
| [S21] | Turso — SQLite compatibility | Rust engine compatibility, FTS distinction and mixed-engine access restrictions. |
| [S22] | Turso — Concurrent writes | MVCC/concurrent transaction behavior and conflict handling. |
| [S23] | SQLite — WAL | Reader/writer behavior, same-machine constraint, checkpoints and runtime fix advisory. |
| [S24] | SQLite — Isolation | Transaction visibility and per-database write serialization. |
| [S25] | SQLite — Backup API | Supported live-backup approach; filesystem backup needs separate coordination. |
| [S26] | aiosqlite — Documentation | Async wrapper and per-connection worker/queue behavior. |
| [S27] | Docker Compose — Profiles | Selective service activation and dependency/profile behavior. |
| [S28] | Docker — Port publishing | Host-address binding and container network exposure. |
| [S29] | OWASP — SSRF prevention | Outbound target validation and defense-in-depth considerations. |
| [S30] | HTTPX — Async support | Async HTTP acquisition building block. |
| [S31] | pypdf — Text extraction | Text extraction boundaries and scanned/layout limitations. |
| [S32] | Firecrawl — Compose source | Supporting services and SearXNG configuration; pin an audited revision. |
| [S33] | SearXNG — Compose source | Deployment example for configuration/dependency review, not blindly merged YAML. |
| [S34] | Crawl4AI — Compose source | Runtime configuration, privileges and deployment review. |
| [S35] | QMD — Changelog | Initialization/concurrency change history; main-branch changes may precede releases. |
| [S36] | MCP — Protocol specification | Protocol-level background; exact support remains a framework/client test. |
| [S37] | Firecrawl — Open-source or cloud | Product/deployment differences; no cloud-parity assumption. |
| [S38] | TinyFish — Search API | Hosted discovery endpoint scope. |
| [S39] | TinyFish — Fetch API | Targeted fetch endpoint scope. |
| [S40] | TinyFish — Browser API | Browser endpoint scope, distinct from research orchestration. |
| [S41] | QMD — CLI implementation | Update, missing-file, cleanup and command lifecycle behavior. |
| [S42] | SQLite — PRAGMA reference | Journal/timeout configuration and connection-setting semantics. |

### Source-use limitations

No hardware benchmark, cache-hit rate, exact provider pricing/rate limit, universal crawler ranking or model-token saving percentage has been established here. Alternatives listed without a specific adopted integration were considered, not exhaustively benchmarked. License and redistribution approval is an explicit release gate, not implied by a repository being public.

The original user decisions and the discussion’s progression are sourced from the supplied conversation. Earlier precise-version or feature claims were not treated as evidence merely because an assistant stated them. Where verification remains inconclusive, this document records a gate instead of a fabricated answer.

---

**End of canonical PRD.** Implementation artifacts should reference this document’s requirement and decision IDs; derived summaries must not silently become a competing specification.

[S01]: https://modelcontextprotocol.io/specification/2026-07-28/server/tools "MCP — Tools"
[S02]: https://modelcontextprotocol.io/specification/2026-07-28/server/resources "MCP — Resources"
[S03]: https://github.com/PrefectHQ/fastmcp/blob/main/docs/getting-started/installation.mdx "Python FastMCP — Installation source"
[S04]: https://github.com/PrefectHQ/fastmcp/releases "Python FastMCP — Releases"
[S05]: https://gofastmcp.com/development/releases "FastMCP — Release/versioning policy"
[S06]: https://gofastmcp.com/servers/tasks "FastMCP — Tasks"
[S07]: https://docs.searxng.org/dev/search_api.html "SearXNG — Search API"
[S08]: https://docs.searxng.org/admin/installation-docker.html "SearXNG — Docker installation"
[S09]: https://github.com/unclecode/crawl4ai "Crawl4AI — Official repository"
[S10]: https://docs.crawl4ai.com/core/self-hosting/ "Crawl4AI — Self-hosting"
[S11]: https://docs.firecrawl.dev/contributing/self-host "Firecrawl — Self-hosting"
[S12]: https://docs.tinyfish.ai/ "TinyFish — API documentation"
[S13]: https://github.com/deedy5/ddgs "DDGS — Official repository"
[S14]: https://github.com/spider-rs/spider "Spider — Rust engine repository"
[S15]: https://trafilatura.readthedocs.io/en/latest/ "Trafilatura — Documentation"
[S16]: https://github.com/tobi/qmd "QMD — Original repository"
[S17]: https://raw.githubusercontent.com/tobi/qmd/main/src/index.ts "QMD — SDK source"
[S18]: https://raw.githubusercontent.com/tobi/qmd/main/src/store.ts "QMD — Store source"
[S19]: https://raw.githubusercontent.com/tobi/qmd/main/src/db.ts "QMD — Database source"
[S20]: https://raw.githubusercontent.com/tobi/qmd/main/package.json "QMD — Package manifest"
[S21]: https://raw.githubusercontent.com/tursodatabase/turso/main/COMPAT.md "Turso — SQLite compatibility"
[S22]: https://docs.turso.tech/tursodb/concurrent-writes "Turso — Concurrent writes"
[S23]: https://sqlite.org/wal.html "SQLite — WAL"
[S24]: https://www.sqlite.org/isolation.html "SQLite — Isolation"
[S25]: https://sqlite.org/backup.html "SQLite — Backup API"
[S26]: https://aiosqlite.omnilib.dev/en/stable/ "aiosqlite — Documentation"
[S27]: https://docs.docker.com/compose/how-tos/profiles/ "Docker Compose — Profiles"
[S28]: https://docs.docker.com/engine/network/port-publishing/ "Docker — Port publishing"
[S29]: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html "OWASP — SSRF prevention"
[S30]: https://www.python-httpx.org/async/ "HTTPX — Async support"
[S31]: https://pypdf.readthedocs.io/en/stable/user/extract-text.html "pypdf — Text extraction"
[S32]: https://raw.githubusercontent.com/firecrawl/firecrawl/main/docker-compose.yaml "Firecrawl — Compose source"
[S33]: https://raw.githubusercontent.com/searxng/searxng/master/container/docker-compose.yml "SearXNG — Compose source"
[S34]: https://raw.githubusercontent.com/unclecode/crawl4ai/main/docker-compose.yml "Crawl4AI — Compose source"
[S35]: https://raw.githubusercontent.com/tobi/qmd/main/CHANGELOG.md "QMD — Changelog"
[S36]: https://modelcontextprotocol.io/specification/2026-07-28 "MCP — Protocol specification"
[S37]: https://docs.firecrawl.dev/contributing/open-source-or-cloud "Firecrawl — Open-source or cloud"
[S38]: https://docs.tinyfish.ai/search-api "TinyFish — Search API"
[S39]: https://docs.tinyfish.ai/fetch-api "TinyFish — Fetch API"
[S40]: https://docs.tinyfish.ai/browser-api "TinyFish — Browser API"
[S41]: https://raw.githubusercontent.com/tobi/qmd/main/src/cli/qmd.ts "QMD — CLI implementation"
[S42]: https://sqlite.org/pragma.html "SQLite — PRAGMA reference"
