# Deep Web Search (DWS)
## Product Requirements, Architecture, and Decision Record

**Version:** 1.0 — consolidated design baseline  
**Prepared:** 9 September 2026  
**Product name:** Deep Web Search  
**CLI name:** `dws`  
**Deployment:** Personal, local-first, single-machine Docker Compose application  
**Status:** Requirements and architecture specification; not an implementation or benchmark report  
**Owner / primary user:** The project owner, using multiple AI hosts, projects, skills, and agents

> **Product definition:** DWS is a reusable evidence-acquisition and document-retrieval engine. It searches the public web, acquires and crawls permitted content, preserves useful evidence, and returns bounded, traceable results. Research planning, interpretation, contradiction analysis, summarization, and report writing belong to host-side agents and skills—not to DWS core.

---

## 0. How to use this document

This file is the single source of truth for **what DWS should do, how its major components fit together, why choices were made, which earlier ideas were superseded, and what still needs validation**. It consolidates the conversation rather than preserving every earlier proposal as a requirement.

### 0.1 Decision authority and status vocabulary

| Label | Meaning |
|---|---|
| **Settled** | Explicit user preference, or a conclusion accepted in the discussion. Implementation must preserve it unless this document is revised. |
| **Baseline** | A concrete engineering recommendation that makes the settled direction implementable. It is not a claim that the user explicitly approved every parameter. |
| **Optional** | Supported direction, disabled unless configured or enabled. It must not become a mandatory dependency accidentally. |
| **Deferred** | Not needed for V1. A reconsideration trigger is recorded. |
| **Superseded** | An earlier proposal replaced by a later decision. Do not implement it from old conversation excerpts. |
| **Validation gate** | An unresolved compatibility, quality, version, or operational question that must be tested before release. |

Within the requirements, **MUST** identifies a release requirement, **SHOULD** a preferred implementation, and **MAY** an optional extension. A proposed default is a starting configuration, not a measured capacity claim.

The order of authority is: **latest explicit user decision → settled requirements here → baseline decisions here → older discussion**. Upstream technical facts must be checked against the exact versions actually installed. A technical discrepancy does not authorize silently reversing a user choice; record and resolve it.

### 0.2 Scope of the consolidation

This document includes the search/fetch/crawl discussions, MCP lessons relevant to implementation, the research-agent boundary, FastMCP selection, Compose deployment, QMD lexical retrieval, storage and retention, concurrency, and Turso evaluation. Earlier research-tool requests are not treated as completed experimental reports: no missing report, unrun benchmark, or unavailable prototype is claimed as evidence.

Citations such as **[S01]** resolve to primary sources in Section 28. Conversation-derived preferences and the proposed DWS architecture are design decisions, not statements from those sources.

### 0.3 Version claims that must not become accidental requirements

Earlier messages confidently named FastMCP 4.0.0/4.0.3 as stable. During preparation, the primary installation documentation, GitHub release listing, and PyPI pages retrieved were not consistent with those claims: the visible upstream snapshots showed a 3.4.6 stable line and 4.0.0 beta releases. These retrieved pages can lag the date of this document. Consequently, **FastMCP is selected, and the v4 generation remains the intended direction, but a specific stable v4 pin is not established by this PRD**. Verify the actual release, package identity, runtime, and host compatibility at implementation; do not copy a version from earlier chat. [S01], [S02], [S03]

The same rule applies to QMD fixes, bundled SQLite versions, crawler images, hosted-provider limits, and protocol extensions. Mutable `main`-branch source is useful evidence, not an immutable dependency lock.

---

## Contents

1. [Product mission and intended workload](#1-product-mission-and-intended-workload)
2. [Settled direction at a glance](#2-settled-direction-at-a-glance)
3. [Scope, priorities, and non-goals](#3-scope-priorities-and-non-goals)
4. [User journeys and success outcomes](#4-user-journeys-and-success-outcomes)
5. [Responsibility boundaries](#5-responsibility-boundaries)
6. [Logical and runtime architecture](#6-logical-and-runtime-architecture)
7. [Technology stack and deployment decisions](#7-technology-stack-and-deployment-decisions)
8. [Canonical data model and identifiers](#8-canonical-data-model-and-identifiers)
9. [Acquisition and document pipeline](#9-acquisition-and-document-pipeline)
10. [Provider interfaces and capability contracts](#10-provider-interfaces-and-capability-contracts)
11. [Routing, fallbacks, and quality gates](#11-routing-fallbacks-and-quality-gates)
12. [MCP, CLI, and application API contracts](#12-mcp-cli-and-application-api-contracts)
13. [Durable jobs and crawl execution](#13-durable-jobs-and-crawl-execution)
14. [QMD lexical indexing and retrieval](#14-qmd-lexical-indexing-and-retrieval)
15. [Retention, caching, and evidence preservation](#15-retention-caching-and-evidence-preservation)
16. [Concurrency and database ownership](#16-concurrency-and-database-ownership)
17. [One Docker Compose deployment](#17-one-docker-compose-deployment)
18. [Security, privacy, and safe retrieval](#18-security-privacy-and-safe-retrieval)
19. [Token, compute, and cost budgets](#19-token-compute-and-cost-budgets)
20. [Functional requirements and traceability](#20-functional-requirements-and-traceability)
21. [Non-functional requirements and acceptance targets](#21-non-functional-requirements-and-acceptance-targets)
22. [Test strategy and operational verification](#22-test-strategy-and-operational-verification)
23. [Delivery phases and release gates](#23-delivery-phases-and-release-gates)
24. [Architecture decision records](#24-architecture-decision-records)
25. [Discussion evolution and corrections](#25-discussion-evolution-and-corrections)
26. [Risks, open questions, and reconsideration triggers](#26-risks-open-questions-and-reconsideration-triggers)
27. [Change control and implementation checklist](#27-change-control-and-implementation-checklist)
28. [Primary-source register](#28-primary-source-register)
29. [Final implementation brief](#29-final-implementation-brief)

---

## 1. Product mission and intended workload

### 1.1 Problem

The owner performs research across multiple projects and subjects: software architecture, AI memory systems, technical documentation, company fundamentals, and other ad hoc topics. Rebuilding search, scraping, retries, document handling, and source retrieval separately for every host or agent wastes effort and produces inconsistent behavior.

DWS will supply one shared implementation of those mechanical capabilities. Projects will keep their own research methods.

### 1.2 Intended workload

DWS serves **one person with multiple concurrent callers**, not a public multi-tenant service. A caller might be an interactive agent, a project-specific sub-agent, a CLI command, or a script. Research is often one-time or short-lived. Repeated reads within a research run may be useful even when the owner never revisits the topic months later.

The design must therefore support:

- Occasional bursts of search and acquisition without unbounded work.
- Several agents sharing one local artifact store and retrieval service.
- Short-lived corpora, selective preservation, and explicit pinning.
- New providers without changes to project-specific skills.
- Local operation without an embedding model, GPU, or DWS-owned LLM account.

“Deep web search” means thorough public-web discovery and evidence acquisition here. It does **not** imply darknet access, circumventing access controls, an Internet-wide index, or authenticated browsing by default.

### 1.3 Product goals

**G1 — Reuse:** MCP, CLI, and supported programmatic interfaces use the same services and canonical schemas.

**G2 — Useful evidence:** Return source locations, captured versions, and relevant passages—not merely opaque summaries.

**G3 — Low context cost:** Search metadata and bounded excerpts enter model context; complete corpora do not.

**G4 — Replaceability:** Providers and retrieval backends are behind explicit capability interfaces.

**G5 — Personal-scale reliability:** Accepted jobs, retained artifacts, and provenance survive ordinary service restarts.

**G6 — Controlled resource use:** CPU, browser work, indexing, output size, storage, and optional hosted spending have enforceable limits.

**G7 — Domain neutrality:** DWS works for Funda and unrelated technical projects without stock-analysis logic in its core.

### 1.4 What success looks like

A host agent can discover candidate URLs, fetch selected documents, crawl a bounded site section, retrieve cited passages from the resulting corpus, and continue after reconnecting. The agent does not need to choose scraping vendors, inspect database files, or orchestrate index maintenance.

A developer can add a new acquisition adapter without changing `search`, `fetch`, `crawl`, `retrieve`, or the host skill's research logic. The owner can start and stop the application through a single Compose project and understand why any optional service is running.

---

## 2. Settled direction at a glance

| Area | Direction | Status | Reason |
|---|---|---|---|
| Naming | Deep Web Search; CLI `dws` | Settled | Clear, reusable project identity. |
| Core scope | Search, fetch, crawl, normalize, store, retrieve, manage acquisition jobs | Settled | Common infrastructure across projects. |
| Research reasoning | Host-side agent + skill + optional research profile | Settled | Methodology changes by domain and project. |
| MCP framework | Standalone Python FastMCP project | Settled | User preference for familiar declarative Python/FastAPI-style ergonomics. |
| FastMCP version | v4 intended; exact tested release unresolved | Validation gate | Earlier release claims are not sufficient evidence. |
| Deployment | One owner-maintained Docker Compose entry point | Settled | Reproducible local operation. |
| MCP transport | Shared local Streamable HTTP service | Baseline | One service coordinates storage, work, and limits. |
| Search | SearXNG primary | Settled | Preferred broad discovery layer. |
| Lightweight search fallback | DDGS adapter | Baseline | Additional low-operations discovery path; not guaranteed independent upstream coverage. |
| Browser acquisition | Crawl4AI primary | Settled | Preferred browser/extraction component. |
| Static acquisition | Lightweight HTTP + deterministic extraction fast path | Baseline | Avoid browser work when it adds no value. |
| Additional crawler | Firecrawl self-hosted profile, off by default | Optional / validation gate | Useful backup candidate; operational cost and incremental benefit must be measured. |
| Rust crawler | Spider / spider-rs | Deferred | Keep adapter path; do not operate redundant crawlers without evidence. |
| Hosted fallback | TinyFish capability-specific APIs | Optional | Independent execution environment; explicit privacy and cost policy. |
| Local retrieval | Original `tobi/qmd`, lexical-only | Settled | Reuse document-search tooling without default vector inference. |
| Operational database | DWS-owned SQLite file | Settled | Small local metadata and job store. |
| Search database | QMD-owned SQLite file | Settled | QMD manages its schema and search lifecycle. |
| Vectors | No embeddings, hybrid expansion, or reranking by default | Settled | Ad hoc workload has not demonstrated the need. |
| Turso | Do not replace SQLite in V1 | Accepted baseline | No measured metadata write bottleneck; QMD is not a drop-in FTS migration. |
| Background execution | DWS-owned durable jobs | Settled | Correctness must not depend on MCP sessions or framework task workers. |
| Progress | Polling first | Settled | Simple, sufficient for personal use. |
| Output | Structured records + excerpts + artifact handles | Settled | Small context footprint and reproducible provenance. |

**Important:** “Settled” selects a direction, not an unsupported claim that the corresponding adapter is already implemented or that all provider capabilities are equivalent.

---

## 3. Scope, priorities, and non-goals

### 3.1 P0: required for the first usable release

| Capability | Required outcome |
|---|---|
| Broad search | SearXNG results normalized into compact records; a tested fallback path. |
| Single-URL fetch | Static and browser-backed acquisition, format detection, normalized text, provenance. |
| Bounded crawl | Durable frontier, explicit scope, page/depth/runtime limits, partial results. |
| Local retrieval | QMD keyword search over retained normalized documents. |
| Document reading | Bounded, snapshot-specific passage/line reads for tools and resources. |
| Artifacts | Stable IDs, source URLs, hashes, capture times, retention states. |
| Jobs | Submission, status, cancellation, retry/recovery, idempotency. |
| MCP + CLI | Shared behavior and schema contracts; no duplicated business logic. |
| Compose | One entry point, persistent local volumes, internal service networking. |
| Safety | URL/network policy, resource limits, hosted-provider opt-in, untrusted-content handling. |
| Concurrency | Central scheduling, controlled writes/index updates, tested concurrent reads. |
| Diagnostics | Provider attempts, queue wait, latency, index lag, errors, and installed-version inventory. |

### 3.2 P1: useful after the baseline works

Batch fetch; artifact import/export; a default host research skill; project-specific skill templates; an optional self-hosted Firecrawl profile; TinyFish Search/Fetch/Browser adapters after endpoint validation; richer document sections and tables; native MCP Tasks projection when it maps cleanly; more corpus management through the CLI.

These may be implemented earlier when inexpensive, but must not block a functioning default stack.

### 3.3 Explicit non-goals

DWS V1 will not include an autonomous research planner, automatic report writer, investment-thesis engine, domain-specific credibility scoring model, model provider router, multi-agent debate system, or per-document LLM summary pipeline.

It will not require a vector database, embedding service, GPU, Redis/Celery stack for DWS jobs, Kubernetes, distributed database, public authentication platform, or a multi-user permissions system.

It will not guarantee retrieval from every website, bypass paywalls or authorization, manufacture citations from search snippets, or preserve all downloaded data forever. Visual/OCR-heavy extraction is not a default requirement; an unreadable/scanned document must be reported honestly.

“No Redis/PostgreSQL required by DWS core” does not mean an optional vendor stack is forbidden from having its own dependencies. Firecrawl's self-hosted components are a separate operational decision.

---

## 4. User journeys and success outcomes

### J1 — One-time technical research

A host skill investigates AI memory systems. It decomposes the question and issues DWS searches. DWS returns URLs and short snippets. The host selects sources; DWS fetches and indexes accepted normalized documents. The host retrieves passages, identifies gaps, and writes its own report with DWS provenance.

**Outcome:** Useful evidence is available without every downloaded page entering model context. The report can pin its cited snapshots before transient material expires.

### J2 — Site-focused documentation review

A host asks DWS to crawl a specific documentation path, not the whole domain. DWS returns `job_id` and `crawl_id`, processes the frontier, and exposes bounded status. The host polls and retrieves passages scoped to that crawl.

**Outcome:** Scope and crawl budgets remain enforceable even when a provider discovers more links than expected.

### J3 — Provider failure

The primary search or acquisition adapter times out or returns unusable content. DWS applies capability-specific retry/fallback policy. It records every attempt and returns a usable result, a partial result, or a typed error.

**Outcome:** The host does not need vendor-specific recovery prompts. A lack of results is not mislabeled as a technical error, and a technical error is not mislabeled as successful research.

### J4 — Concurrent agents

Several host agents acquire and retrieve documents concurrently. The daemon owns scheduling. Duplicate compatible fetches coalesce, QMD search concurrency is bounded, and one index writer publishes updates.

**Outcome:** No agent can defeat global limits by spawning an independent CLI process against the shared store.

### J5 — Reconnection and restart

The MCP client disconnects during a crawl. The crawl continues if the backend worker remains healthy. If the worker or daemon also restarts, persisted work is recovered or retried according to recorded leases and checkpoints.

**Outcome:** An acknowledged job remains discoverable. “Survives restart” means recoverable execution, not a promise that every in-flight network request continues uninterrupted.

### J6 — Reuse and retention

The owner reopens a topic. DWS reports whether a document is retained, indexed, stale, pinned, expired, or removed. Re-fetching a changed source creates a new captured version rather than silently changing the text behind an old citation.

**Outcome:** Cached reuse and evidence preservation are explicit; absence of a high long-term cache hit rate does not invalidate within-run retrieval.

### J7 — Add a provider

A developer adds Spider or another fetch/crawl implementation behind the provider contract, runs conformance tests, and enables it in routing configuration.

**Outcome:** Host skills, public result schemas, storage ownership, and the retrieval layer remain unchanged.

---

## 5. Responsibility boundaries

### 5.1 Host versus DWS

| Responsibility | Host agent / skill | DWS core |
|---|---:|---:|
| Define research question and subquestions | Yes | No |
| Decide domain-specific source priorities | Yes | Apply supplied filters only |
| Generate semantic query variants | Yes | Execute supplied queries |
| Call search/fetch/crawl/retrieve | Yes | Implement operations |
| Select a working acquisition provider | No | Yes |
| URL/network validation and redirect checks | No | Yes |
| Normalize, deduplicate, retain, index | No | Yes |
| Judge whether evidence supports a claim | Yes | Supply evidence and provenance |
| Detect factual contradictions | Yes | No automatic interpretation |
| Decide whether research is complete | Yes | Enforce mechanical budgets only |
| Summarize and write a report | Yes | No |
| Manage crawl/index job progress | Poll/use handles | Yes |
| Pin evidence for a report | Request it | Enforce retention |

**Deterministic core** means the control logic and default processing do not require a generative model. It does not mean live websites, browser behavior, vendor results, or search ranking never change. Reproducibility comes from captured inputs, versions, settings, and snapshots.

### 5.2 MCP and CLI are interfaces, not owners of business logic

FastMCP tools translate validated arguments into service calls and project service results into MCP outputs. They MUST NOT contain provider fallback loops, crawl frontiers, SQL, retention policy, or research prompts.

The CLI uses the daemon for the shared store. A developer may use the Python core against an isolated test store or in an explicit exclusive maintenance mode. This preserves library reuse without allowing independent processes to bypass shared scheduling.

### 5.3 Optional provider intelligence is explicit

TinyFish exposes distinct Search, Fetch, Browser, and Agent surfaces. DWS must not conflate them. Programmatic Search/Fetch/Browser integration is different from delegating a natural-language research task to a hosted agent. [S20]

The default profile disallows DWS-owned generative inference. Any later adapter that invokes an agentic vendor feature must declare it, require explicit enablement, and expose usage/privacy implications. The presence of an optional hosted provider does not move the general research orchestrator back into DWS.

---

## 6. Logical and runtime architecture

### 6.1 Logical architecture

```text
HOST / PROJECT
  research agent + skill + domain profile
                   |
             MCP or DWS CLI
                   |
                   v
+------------------------------------------------------+
| DWS interfaces                                       |
| FastMCP adapter | local application API | CLI client   |
+--------------------------+---------------------------+
                           |
+--------------------------v---------------------------+
| DWS services                                         |
| Search | Fetch | Crawl | Retrieval | Artifact | Jobs  |
| Policy | Budget | Provider health | Cache | Retention |
+-------------+----------------------+-----------------+
              |                      |
              v                      v
      Provider adapters      Document / artifact pipeline
      SearXNG, DDGS          normalize -> snapshot -> retain
      HTTP, Crawl4AI                 -> QMD lexical index
      optional providers             -> bounded passages
              |                      |
              +-----------+----------+
                          |
           +--------------+----------------+
           |              |                |
       dws.sqlite     artifact files    QMD SQLite
       application    preserved text    QMD-owned
       metadata/jobs  and source bytes  search projection
```

### 6.2 Proposed runtime topology

```text
One Compose project, on one machine

  dws-api / coordinator
    - FastMCP + small local application/control API
    - application services and metadata owner
    - QMD CLI adapter and index scheduler
    - artifact publication, retention, diagnostics
             |
             +---- dws-worker
             |       bounded fetch/crawl execution
             |       leases/heartbeats via coordinator
             |       staged output, no independent index updates
             |
             +---- searxng
             |
             +---- crawl4ai
             |
             +---- optional Firecrawl profile
             |
             +---- optional hosted APIs
```

**Baseline design choice:** the coordinator is the sole live owner of DWS metadata writes and QMD scheduling. The worker runs independently of MCP request lifetimes and submits state changes through the coordinator's private control interface. This resolves the ambiguity in “one global writer” when API and worker are separate processes.

A simpler single backend process with a durable worker loop is an acceptable prototype, but it must not claim worker isolation from daemon crashes. Before release, either implement the proposed topology or record the alternative and prove equivalent recovery and scheduling guarantees.

### 6.3 Dependency rules

The core MUST NOT import FastMCP, host-agent libraries, or vendor-specific request models. Vendor packages belong in adapters. DWS-owned models may use a shared validation library such as Pydantic, but their fields are DWS concepts.

A provider SDK, a CLI subprocess, and an HTTP service can all implement the same capability. Choosing Docker for a provider does not change its logical role.

---

## 7. Technology stack and deployment decisions

### 7.1 Baseline component matrix

| Component | Role | Decision and rationale | Main cost / limitation |
|---|---|---|---|
| Python + typed models | Core services, adapters, policy | Settled language direction; matches owner expertise | Blocking/native work must not stall the event loop. |
| FastMCP | MCP surface | Selected for developer ergonomics and framework features [S01], [S02], [S03] | Pin and test; no assumption that newest documentation equals installed behavior. |
| FastAPI/ASGI + Uvicorn or compatible runner | Small local API/control surface and hosting | Baseline; share service methods, not a second business implementation | Keep routes local and narrow. |
| CLI framework, provisionally Typer | `dws` command parsing and output | Baseline, not an irreversible library choice | Client of daemon in shared-store mode. |
| SearXNG container | Primary metasearch | Selected; configure JSON output explicitly [S14], [S15] | Depends on external engines; not an independent web index. |
| DDGS Python adapter | Lightweight discovery fallback | Baseline; library also has a CLI [S16] | Shares external-engine risks; not guaranteed independent of SearXNG. |
| HTTPX + deterministic HTML extraction | Cheap static fetch path | Baseline candidate; asynchronous HTTP and main-content extraction [S17], [S18] | Not a browser; test extraction fidelity. |
| Crawl4AI service | Browser fetch/extraction and crawl capability | Selected primary browser component [S12], [S13] | Browser resources and version-specific service behavior. |
| PDF text parser, provisionally pypdf | Text-bearing PDF normalization | Baseline candidate [S19] | Scanned PDFs and complex layouts need other handling. |
| QMD CLI, original `tobi/qmd` | Lexical document search and indexed-text retrieval | Selected; use keyword path only [S06], [S07] | Node/Bun and native dependencies; process/index lifecycle needs coordination. |
| DWS SQLite + aiosqlite | Metadata, jobs, provenance, index outbox | Selected storage; async wrapper for event-loop integration [S09], [S11] | One writer per database; short transactions and controlled access. |
| Local filesystem / Compose volume | Normalized artifacts and selected originals | Selected | Retention and backups must be implemented. |
| Docker Compose | One deployment entry point | Settled [S23], [S24] | One file does not make browser/vendor components inexpensive. |
| pytest-style tests and load harness | Contract, recovery, and concurrency checks | Baseline | Hardware/corpus results must be recorded, not assumed. |

Package names beyond the explicitly selected projects are baseline suggestions. Freeze exact versions only after the compatibility spike and record them in lockfiles and image digests.

### 7.2 Optional and deferred components

| Component | Status | Why not mandatory |
|---|---|---|
| Firecrawl self-hosted | Optional profile | Overlaps acquisition; operates several supporting services. Add only for a measured fallback benefit. [S21], [S22] |
| Firecrawl hosted | Not preferred default | Owner preference against depending on its hosted limits/cost model. No fixed rate-limit claim is made here. |
| TinyFish Search / Fetch | Optional | Remote processing must be explicitly allowed; account capabilities need a smoke test. [S20] |
| TinyFish Browser | Optional escalation | Useful candidate for a distinct browser execution environment; not automatic spending. [S20] |
| TinyFish Agent | Outside the default core path | Goal-driven hosted automation must not become hidden research orchestration. |
| Spider / spider-rs | Deferred adapter candidate | Additional runtime/integration is justified only by a demonstrated gap. [S25] |
| QMD embeddings and hybrid search | Deferred | Lexical-first workload; no proven semantic-recall deficit yet. [S06], [S07] |
| Turso Rust engine | Deferred for metadata only | Concurrent-write benefits are real but not needed without measured contention. Not QMD FTS5-compatible. [S26], [S27] |
| Redis/Celery/Docket as DWS execution authority | Not selected for V1 | SQLite-backed jobs suffice as a baseline; framework tasks must not own domain correctness. |
| External vector/search server | Not selected for V1 | More dependencies without a demonstrated need. |

### 7.3 Package versus service

Crawl4AI provides Python APIs and Docker deployment material. Its Docker configuration includes browser/shared-memory settings and its own internal runtime choices; a container does not remove those costs. [S12], [S13]

For DWS, the baseline is to put browser-heavy Crawl4AI in a dedicated Compose service, and keep QMD's CLI in the DWS image initially. Static fetching, DDGS, metadata access, and normalization are Python-side components. This is a proposed isolation choice, not a claim that Crawl4AI cannot work as an in-process library.

Installing a Firecrawl **client SDK** is not equivalent to installing its self-hosted scraping engine. Its inspected Compose stack includes API/browser and supporting queue/storage components. Service dependencies, required external features, and persistence must be checked at the pinned revision. [S21], [S22]

### 7.4 Version and license inventory

Release artifacts MUST record Python, FastMCP, MCP SDK, QMD, Node/Bun, SQLite runtimes, browser, crawler images, parser versions, and enabled provider endpoints. Record both package pins and image digests where applicable.

Before distributing the plugin/image, inspect each pinned project's actual license and notices. Do not infer obligations from “open source,” from a similarly named project, or from an old README. No broad legal compatibility conclusion is made by this PRD.

---

## 8. Canonical data model and identifiers

### 8.1 Identity model

| Object | Example | Meaning |
|---|---|---|
| Project | `project_memory` | User/project grouping, not a security tenant by default. |
| Run | `run_01` | Mechanical grouping of related calls and artifacts. No autonomous research meaning. |
| Search | `search_01` | A recorded discovery operation and result set. |
| Document | `doc_37` | Stable logical source identity within acquisition/privacy policy. |
| Snapshot | `snap_05` | Immutable captured/normalized version, with hashes and extractor version. |
| Crawl | `crawl_09` | Crawl configuration, frontier, membership, and manifest. |
| Job | `job_101` | Execution lifecycle, lease, retries, progress, result references. |
| Passage | `passage_08` | Bounded text with snapshot-specific locators. |
| Provider attempt | `attempt_04` | One adapter invocation with outcome and timing. |
| Resource URI | `dws://documents/doc_37/snapshots/snap_05/content` | Address to a DWS representation, not the original web location. |

The old names `deepweb://...` and embedded DWS `research_id` examples are superseded for new public contracts. A host may attach its own external research identifier as correlation metadata; DWS does not need to interpret it.

### 8.2 Logical records in `dws.sqlite`

The following is a logical schema, not migration SQL:

```text
projects                 id, name, defaults, created_at
runs                     id, project_id, external_correlation, lifecycle
searches                 id, run_id, normalized_request, result_manifest, timestamps
sources                  document_id, requested_url, canonical_url, privacy_partition
snapshots                id, document_id, raw_hash, normalized_hash, media_type,
                         capture_time, parser_version, artifact_path, quality_state
source_observations      snapshot_id, requested_url, final_url, redirect_chain,
                         provider, observed_time, publication_date_evidence
memberships              project/run/crawl -> document/snapshot
jobs                     id, kind, state, request, lease, attempt_count,
                         cancellation_requested, result_refs, terminal_error
crawl_frontier           crawl_id, normalized_url_key, depth, parent,
                         state, attempt_count, snapshot_id
provider_attempts        id, operation_id, provider_id, outcome, timing,
                         upstream_request_id, cost/usage_when_known
index_outbox             snapshot_id, action, generation, state, retry_at
index_state              snapshot_id, qmd_collection, qmd_path, generation,
                         indexed_hash, readiness, indexed_at
retention                artifact_ref, pin_reason, expires_at, tombstone_state
idempotency              scoped_key, normalized_request_hash, operation_id, expires_at
```

These records MUST NOT duplicate an FTS corpus. Body text lives in retained artifacts and QMD's indexed representation. QMD's internal tables are not extended with these records.

### 8.3 Storage ownership

| Store | Authoritative for | Rebuildable? |
|---|---|---|
| `dws.sqlite` | Operational state, provenance, membership, retention, job ledger | Not merely a disposable index; back up. |
| Artifact files | Captured normalized text and retained source bytes | Re-extraction may be possible, but refetch cannot guarantee the same content. Back up pinned evidence. |
| QMD database/config | Search projection and QMD-managed indexed text | Rebuild from retained artifacts + DWS index mapping/config. |
| Logs | Diagnostic history within retention | Not the authoritative job or document store. |

QMD currently keeps indexed text and FTS structures in SQLite. Its supported document workflow does not make its database an appropriate home for every DWS table. [S06], [S08]

### 8.4 Provenance and score semantics

A document MUST distinguish source URL, final URL, asserted canonical URL, capture time, and publication time. Unknown publication dates remain null/absent. A date in a URL or a search snippet is evidence with a source, not automatically an authoritative publication timestamp.

Content hashes identify bytes or normalized content according to a named algorithm. A hash is not a source-credibility score. Equal normalized content does not erase distinct source observations.

Ranks, BM25 scores, provider scores, extraction signals, and host confidence are different fields. DWS MUST NOT invent a calibrated `confidence: 0.96` or compare uncalibrated vendor scores as if they were probabilities.

---

## 9. Acquisition and document pipeline

### 9.1 One canonical pipeline

```text
Request
  -> validate policy and budget
  -> inspect cache / coalesce compatible in-flight work
  -> acquire bytes or provider extraction
  -> inspect media type and extraction quality
  -> normalize with a named extractor version
  -> preserve source and normalized hashes
  -> publish immutable artifact
  -> commit metadata + index-outbox intent
  -> acknowledge document availability
  -> controlled QMD update
  -> mark snapshot searchable
```

Fetch and crawl outputs converge here. A native crawler must not invent a parallel artifact store that bypasses DWS provenance and retention.

### 9.2 Acquisition and normalization rules

**URL handling:** Permit supported HTTP(S) targets only. Preserve the original URL. Normalize safe equivalents; remove only known tracking parameters under a versioned policy. Do not strip arbitrary query strings, lowercase case-sensitive paths, or merge signed/authenticated URLs indiscriminately. Record redirects and treat publisher canonical tags as hints.

**Media detection:** Use response headers and content inspection. A `.pdf` suffix does not prove the body is a PDF. An HTML login or challenge page returned with status 200 is not a valid article.

**Static first:** When appropriate, fetch bytes without a browser and extract main content. Escalate if meaningful content depends on rendering, not merely because the text is short. Short pages can be legitimate.

**Browser path:** Use bounded browser contexts. Preserve enough extraction evidence to distinguish rendering failure, challenge content, and successful acquisition. Do not expose arbitrary user-supplied JavaScript through the public tool schema in V1.

**PDFs:** Extract text from text-bearing PDFs through a parser. Preserve page locators where possible. Record missing text or layout uncertainty; return `unsupported_extraction` or an explicit quality warning for scanned/image-only documents. Do not pretend an empty parse is a successful evidence capture. PDF extraction and OCR are separate capabilities. [S19]

**Excerpts:** Select bounded source text deterministically. A query-aware excerpt may be chosen with lexical matching; it must remain a faithful passage, not a generated summary. Identify omitted spans and normalize whitespace without silently changing substantive text.

**Structure:** Preserve headings, paragraphs, code blocks, lists, and simple tables when supported. Do not claim exact table reconstruction or visual understanding merely because Markdown was generated.

### 9.3 Snapshot publication and consistency

The artifact filesystem, DWS SQLite, and QMD database do not form one atomic transaction. DWS must implement an explicit, recoverable publication sequence:

1. Write to a staging file under a controlled directory.
2. Validate and hash the complete artifact; flush/publish it through atomic rename where supported.
3. Commit the snapshot metadata and index-outbox record together in DWS SQLite.
4. Acknowledge capture only after its durable metadata exists.
5. Process indexing asynchronously; record the indexed hash and generation.

A startup reconciler handles orphaned staged files, files published without metadata, pending index records, and missing artifacts. Failed indexing must not lose an otherwise valid capture. A row must not advertise a body that was never successfully published.

### 9.4 Quality is observable, not magical

Store named signals such as `challenge_detected`, `main_text_empty`, `parse_warnings`, `unexpected_media_type`, `truncated_at_byte_limit`, and `rendering_required`. A heuristic quality decision must include reasons and be overridable by policy for legitimate edge cases.

Source authority and truth are not inferred from these technical signals. A well-extracted page may be inaccurate; that is a host research concern.

---

## 10. Provider interfaces and capability contracts

### 10.1 Required interfaces

| Interface | Input/output responsibility | Examples |
|---|---|---|
| `SearchProvider` | Query/filter input → normalized candidate records + provider diagnostics | SearXNG, DDGS, optional hosted search |
| `FetchProvider` | URL + bounded acquisition options → raw/extracted acquisition result | Direct HTTP, Crawl4AI, optional Firecrawl/TinyFish |
| `CrawlProvider` | Optional native bounded traversal → page stream/manifests + external job handle | Crawl4AI/native capability, Firecrawl, future Spider |
| `DocumentNormalizer` | Bytes/provider output → normalized document + quality/provenance signals | HTML/PDF/text extractors |
| `RetrievalIndex` | Index lifecycle + lexical query/read operations | QMD adapter |
| `ArtifactStore` | Immutable body publication, reads, export, retention deletion | Local filesystem |
| `MetadataRepository` | DWS-owned records and atomic transitions | SQLite implementation |

Avoid inventing a separate interface for every vendor product. Browser rendering is initially a declared `FetchProvider` capability or mode; split a standalone browser-session interface only when a concrete workflow needs it.

### 10.2 Capability descriptor

Each adapter must advertise only verified capabilities for its actual deployment, for example:

```text
provider_id
supported_operations
supports_javascript
supports_pdf_acquisition
returns_raw_bytes
supports_partial_results
supports_cancellation
supports_scope_enforcement
supports_native_crawl
requires_network / requires_hosted_credentials
may_invoke_model
configured_cost_class
health / readiness
```

A cloud product and its open-source self-hosted deployment can have different descriptors. Do not copy cloud capability claims into the self-hosted adapter.

### 10.3 Conformance requirements

Adapters must obey deadlines and cancellation where possible, translate exceptions into typed errors, retain upstream request IDs when available, and distinguish partial results from complete results. They must never return credentials or unbounded raw logs to the caller.

Adapter configuration is versioned and included in reproducibility metadata. Routing may change without changing the public schema. Provider-specific controls remain administrative settings, not a growing list of model-facing tools.

### 10.4 Native crawl versus DWS-owned frontier

Conceptually, crawl is traversal built over page acquisition. Implementation need not force every native provider page through the public `fetch` tool.

**V1 baseline:** DWS owns the durable frontier and scope policy, and uses fetch capabilities to acquire pages. This makes checkpointing, cancellation, page limits, and partial reuse independent of vendor job semantics.

**Optional optimization:** Delegate bounded batches or traversal to a native crawler when conformance tests prove scope, page streaming, and cancellation behavior. Register every returned page through the same document pipeline. If native providers cannot resume across one another, retain completed snapshots and start only the remaining eligible work; do not claim transparent mid-job failover.

---

## 11. Routing, fallbacks, and quality gates

### 11.1 Default capability chains

| Operation | Baseline path | Optional escalation |
|---|---|---|
| Web search | Search cache → SearXNG → DDGS | Enabled TinyFish Search or independently configured search API |
| Static HTML/text | Artifact cache → direct HTTP + extraction | Crawl4AI when rendering/extraction warrants it |
| Browser-required page | Crawl4AI | Enabled Firecrawl self-hosted, then explicitly allowed hosted Fetch/Browser capability |
| PDF acquisition | Direct bytes → PDF normalizer | Alternate acquisition provider; extraction fallback is a separate issue |
| Site crawl | DWS frontier + configured fetch providers | Conformant native crawler adapter |
| Local retrieval | QMD lexical search → bounded DWS passage selection | Direct document reads if specific artifacts are known and indexing is pending |

This is a baseline ordering, not a mandatory full cascade on every error. Budgets, readiness, privacy, and failure type determine which eligible attempt comes next.

### 11.2 Why fallback must be capability-aware

Search discovers possible URLs. A crawler does not automatically replace a general web search index. Likewise, a different extraction parser can improve bad Markdown without acquiring a new page, and a new browser cannot fix an inherently image-only PDF's missing OCR.

SearXNG and DDGS both depend on external engines. Their failures can be correlated. The inspected Firecrawl Compose configuration supports a SearXNG endpoint; configuring Firecrawl search against the same SearXNG does not create an independent discovery backup. [S14], [S16], [S22]

### 11.3 Failure policy

| Condition | Required treatment |
|---|---|
| Timeout / transient upstream failure | Bounded retry or another eligible provider; record elapsed time. |
| Upstream throttling | Respect retry guidance; do not amplify bursts with unbounded fan-out. |
| Valid empty search response | Return empty or use one configured recall expansion/fallback; do not call it a transport failure. |
| Low diversity / duplicates | Deduplicate and record coverage signals; optional secondary search within budget. |
| Challenge/login/interstitial body | Mark unusable for the requested public content; do not index as the article. |
| DNS/private-address violation | Hard policy refusal; never use another vendor to evade the policy. |
| Robots/scope/access restriction | Stop or skip according to policy; not a reason to bypass restrictions. |
| Unsupported media or scanned PDF | Preserve metadata/bytes when allowed; expose extraction limitation. |
| Hosted service disabled | Skip it visibly in diagnostics; never enable or spend automatically. |
| All eligible paths fail | Typed error or partial result with attempted-provider summary. |

### 11.4 Global limits and backpressure

Per-operation limits are necessary but insufficient: all retries and provider cascades share a **single request deadline and budget**. DWS must cap queue size, attempts, bytes, browser concurrency, and crawl growth. A small circuit breaker can temporarily deprioritize a persistently failing provider.

Two agents requesting the same public URL with compatible freshness/extraction policies should share an in-flight acquisition where safe. Cancellation by one waiter must not terminate work still required by another without reference accounting.

---

## 12. MCP, CLI, and application API contracts

### 12.1 Stable model-facing tool surface

The earlier six-tool sketch gains a bounded `read` tool because resource handling varies by host. This is a justified baseline refinement, not an invitation to expose every internal function.

| Tool | Meaning | Primary output |
|---|---|---|
| `search` | Discover URLs on the public web | Ranked URL metadata and snippets |
| `fetch` | Acquire one URL and create/reuse a snapshot | IDs, metadata, excerpt, resource link |
| `crawl` | Start bounded multi-page acquisition | Durable job/crawl IDs |
| `retrieve` | Search retained indexed documents | Relevant passages with provenance |
| `read` | Read a bounded view of a known artifact | Text with stable locators |
| `job_status` | Inspect acquisition/index execution | State, counters, result references |
| `job_cancel` | Request cancellation | Acknowledgment and current state |

No `research`, `summarize_every_page`, vendor-specific search tool, arbitrary shell, arbitrary SQL, or unrestricted browser-evaluation tool belongs in the default catalog.

Tool descriptions must distinguish Internet discovery from corpus retrieval, and acquisition from reading stored content. Inputs and outputs are explicitly typed. Protocol tools and resources have different interaction roles; resource links do not by themselves force a host to retrieve less content. [S04], [S05]

### 12.2 Request fields and bounds

| Operation | Main fields | Proposed defaults / hard bounds |
|---|---|---|
| Search | `query`, `limit`, `project_id`, `run_id`, optional domains/language/freshness | 10 results by default; 30 max; snippet ≤600 characters each |
| Fetch | `url`, optional `freshness`, `render_mode`, project/run | Excerpt ≤800 characters; bounded deadline/bytes; no model summary |
| Crawl | `seed_url`, `scope`, `max_pages`, `max_depth`, `max_duration`, project/run | 100 pages, depth 2 default; hard cap configured separately |
| Retrieve | `query`, project/run/crawl/document scope, `limit`, text budget | 6 passages default; 20 max; aggregate text ≤12,000 characters by default |
| Read | `document_id`, `snapshot_id`, line/section selector, text budget | Bounded slice; explicit next selector; full export is a separate administrative operation |
| Job status/cancel | `job_id` | No document bodies or complete frontier dumps |

These are DWS policy defaults, not vendor limits. Character and byte budgets are enforceable without assuming a universal token-to-character ratio.

Fetch/crawl may also accept an owner-permitted retention class (`transient` or `pinned`), and a project/run may have an approved pinned-capture policy. Later pin/unpin operations use the administrative API/CLI. An MCP-only host that cannot access those operations must use an approved pinned workflow or explicitly surface the limitation; report citations do not magically cause pinning.

### 12.3 Resource URIs

```text
dws://documents/{document_id}/snapshots/{snapshot_id}/content
dws://documents/{document_id}/snapshots/{snapshot_id}/metadata
dws://documents/{document_id}/snapshots/{snapshot_id}/sections/{section_id}
dws://crawls/{crawl_id}/manifest/pages/{page_id}
dws://jobs/{job_id}/status
```

A convenience “latest snapshot” view may exist, but citations should use an immutable snapshot URI. A full large manifest must not be returned as an unbounded default resource read.

Dynamic resource links may be returned by tools without listing the entire corpus. Resource templates describe addresses; they are not persistence mechanisms. Embedded bodies are reserved for genuinely small results. [S04], [S05]

### 12.4 Proposed output examples

**All following payloads are illustrative DWS application schemas, not factual research results, vendor responses, or manually specified JSON-RPC envelopes.** Example titles and source content are fictional. FastMCP handles protocol framing and version negotiation.

#### Search response

```json
{
  "schema_version": "1.0",
  "request_id": "req_search_01",
  "search_id": "search_01",
  "status": "ok",
  "query": "episodic memory agent systems",
  "results": [
    {
      "result_id": "hit_01",
      "rank": 1,
      "title": "Example guide to agent memory",
      "url": "https://example.org/docs/agent-memory",
      "snippet": "This example guide distinguishes working memory from retained episodes.",
      "published_at": null,
      "content_type_hint": "text/html"
    },
    {
      "result_id": "hit_02",
      "rank": 2,
      "title": "Example memory evaluation note",
      "url": "https://example.org/papers/memory-evaluation.pdf",
      "snippet": "This example note describes a memory retrieval evaluation.",
      "published_at": null,
      "content_type_hint": "application/pdf"
    }
  ],
  "returned_count": 2,
  "page_bodies_included": false,
  "warnings": []
}
```

#### Fetch response

```json
{
  "schema_version": "1.0",
  "request_id": "req_fetch_01",
  "status": "ok",
  "document_id": "doc_37",
  "snapshot_id": "snap_05",
  "source_url": "https://example.org/docs/agent-memory",
  "final_url": "https://example.org/docs/agent-memory",
  "title": "Example guide to agent memory",
  "media_type": "text/html",
  "captured_at": "2026-09-09T10:00:00Z",
  "published_at": null,
  "excerpt": "This example guide distinguishes working memory from retained episodes.",
  "excerpt_kind": "source_text",
  "index_status": "pending",
  "retention": "transient",
  "resource_uri": "dws://documents/doc_37/snapshots/snap_05/content",
  "warnings": []
}
```

#### Crawl submission response

```json
{
  "schema_version": "1.0",
  "request_id": "req_crawl_01",
  "status": "accepted",
  "job_id": "job_101",
  "crawl_id": "crawl_09",
  "seed_url": "https://example.org/docs/",
  "scope": {
    "mode": "same_path",
    "max_pages": 100,
    "max_depth": 2
  },
  "job_state": "queued",
  "poll_after_ms": 10000
}
```

#### Crawl progress response

```json
{
  "job_id": "job_101",
  "crawl_id": "crawl_09",
  "job_state": "running",
  "progress": {
    "discovered_unique_urls": 70,
    "queued_urls": 20,
    "inflight_urls": 2,
    "stored_urls": 40,
    "failed_urls": 3,
    "skipped_urls": 5
  },
  "indexing": {
    "accepted_snapshots": 40,
    "indexed_snapshots": 35,
    "pending_snapshots": 5
  },
  "poll_after_ms": 10000
}
```

The six URL-state counters above partition 70 unique discovered URLs. Indexing counters are a separate dimension; do not add them to frontier totals.

#### Completed crawl response

```json
{
  "job_id": "job_101",
  "crawl_id": "crawl_09",
  "job_state": "succeeded",
  "result_status": "partial",
  "stop_reason": "frontier_exhausted",
  "counts": {
    "discovered_unique_urls": 100,
    "stored_urls": 85,
    "failed_urls": 5,
    "skipped_urls": 10
  },
  "index_status": "ready",
  "manifest_uri": "dws://crawls/crawl_09/manifest/pages/first",
  "warnings": ["Five eligible URLs could not be acquired."]
}
```

The job succeeded in completing its bounded workflow; content acquisition was partial. This distinction prevents “job completed” from being mistaken for “every page captured.”

#### Retrieval response

```json
{
  "schema_version": "1.0",
  "request_id": "req_retrieve_01",
  "status": "ok",
  "query": "episodic memory",
  "retrieval_mode": "lexical",
  "scope": {"crawl_id": "crawl_09"},
  "passages": [
    {
      "passage_id": "passage_08",
      "document_id": "doc_37",
      "snapshot_id": "snap_05",
      "source_url": "https://example.org/docs/agent-memory",
      "title": "Example guide to agent memory",
      "text": "An episode records a particular interaction and its outcome.",
      "locator": {"kind": "normalized_lines", "start": 42, "end": 42},
      "resource_uri": "dws://documents/doc_37/snapshots/snap_05/content"
    }
  ],
  "returned_count": 1,
  "truncated": false,
  "index_status": "ready"
}
```

A normalized-line locator is not automatically a PDF page number or a line number on the original webpage. Locator types must be named accurately.

### 12.5 Errors and partial outputs

Use stable DWS error codes such as:

```text
invalid_input           policy_denied          budget_exceeded
provider_unavailable    upstream_timeout       acquisition_blocked
unsupported_media       extraction_failed      partial_acquisition
index_pending           index_unavailable      artifact_expired
artifact_not_found      job_not_found          busy_retry_later
internal_error
```

A malformed protocol request and a valid tool whose acquisition failed are different cases. The MCP adapter maps DWS outcomes into the library's supported error/result forms. Do not leak raw stack traces, SQL, cookies, provider secrets, or full HTML errors.

### 12.6 CLI and programmatic usage

Proposed commands:

```bash
dws search "episodic memory agents" --json
dws fetch "https://example.org/docs/agent-memory" --project memory --json
dws crawl "https://example.org/docs/" --scope same-path --max-pages 100 --json
dws retrieve "episodic memory" --crawl crawl_09 --json
dws read doc_37 --snapshot snap_05 --from-line 40 --lines 20
dws jobs status job_101
dws jobs cancel job_101
dws artifacts pin doc_37 --snapshot snap_05 --reason "cited in project note"
dws doctor
dws backup create
```

These commands specify intended behavior; this PRD does not deliver an executable CLI. Administrative commands need not all become model-facing MCP tools. Direct offline access requires an explicit exclusive/maintenance mode and must refuse to race the running daemon.

---

## 13. Durable jobs and crawl execution

### 13.1 Lifecycle

```text
queued -> running -> succeeded
   |         |  \-> failed
   |         \----> cancelling -> cancelled
   \--------------> cancelled

running -- lease lost / crash --> recovery decision --> queued or failed
```

Job kind and result artifact are separate. A crawl job can produce `crawl_09`; an index job updates an index generation. Host research artifacts remain outside the job schema.

### 13.2 Durability requirements

DWS MUST persist a resolvable job before returning an accepted handle. An in-memory `asyncio.create_task()` alone is not sufficient. A worker lease, checkpoint, attempt counter, cancellation flag, and terminal state must be stored.

The worker may continue after client disconnection. If the coordinator is unavailable, it must not silently accept new unrecorded work or commit metadata independently. It may finish bounded in-flight work into staging, then pause/retry communication. Recovery validates leases and staged artifacts before publishing results.

Execution is **at least once where retries occur**, with idempotent publication and deduplication. Do not promise exactly-once external HTTP requests or hosted billing. Lost upstream responses can make retry cost uncertain.

### 13.3 Crawl frontier requirements

Persist normalized URL keys, parent/depth, scope decision, state, attempts, and resulting snapshot. Check scope and budget before enqueue and before acquisition. Pagination traps, calendars, query variants, and redirects must not expand the crawl indefinitely.

A page/depth budget is a policy limit, not an estimate that the site contains exactly that many pages. Stop reasons include frontier exhausted, page limit, time budget, cancellation, policy restriction, provider failure, and disk/resource pressure.

### 13.4 Tasks, MRTR, and subscriptions

FastMCP background Tasks are a possible protocol projection, not the DWS job database. Its task framework has its own execution integration; it must not be assumed to reuse DWS SQLite automatically. [S31]

The baseline remains explicit job/status/cancel tools. Enable native Tasks only when the pinned FastMCP release and selected hosts support the same extension and the mapping preserves existing job IDs/lifecycle. Do not wrap a job-submission function in a second background task and mistakenly claim that wrapper tracks the entire crawl.

MRTR is for additional client input, such as confirming an expensive bounded operation. It is not a crawl checkpoint or substitute for a job. `requestState` is short continuation state; `job_id` is execution identity. The modern MCP specification describes request-oriented continuation and optional discovery, but the framework—not hand-written protocol code—must implement those details. [S32]

Polling is the default. Start with a suggested 10-second interval, back off when useful, and expose `poll_after_ms`. Host software should poll without unnecessarily invoking an LLM for every status update. Subscriptions are deferred until a real UI/event need justifies them.

---

## 14. QMD lexical indexing and retrieval

### 14.1 Selected behavior

Use the original `tobi/qmd` project. Keyword retrieval is `qmd search`; the SDK's explicitly lexical entry point is `searchLex`. The generic SDK `search` path is hybrid, so naming similarity is not sufficient to guarantee lexical-only operation. [S06], [S07]

DWS MUST NOT call embedding generation, semantic query expansion, vector search, or LLM reranking in its default retrieval path. A fresh default deployment must be tested for unexpected model downloads or inference.

QMD's package still brings a JavaScript runtime and native/model-related dependencies. “No vector inference” is not the same as “only Python's standard SQLite library is installed.” [S40]

### 14.2 What gets indexed

Index retained, accepted normalized text—not every search hit, raw download, browser asset, screenshot, duplicate body, or rejected challenge page. Explicitly fetched usable documents are accepted by default; crawl documents pass acquisition/scope/quality gates first.

Automatic lexical indexing is scoped to DWS-managed artifact directories. Do not point QMD at the owner's entire home directory or include test fixtures and secrets accidentally. DWS metadata records `pending`, `ready`, `failed`, or `excluded` indexing state for each snapshot.

### 14.3 Collection and scope strategy

Start with project-scoped QMD collections backed by generated filesystem views. DWS maintains authoritative run/crawl/document membership. Within a project, index each retained snapshot once where possible, not once per agent.

Queries must respect scope before returning content. Where QMD cannot express a run/crawl constraint directly, use bounded candidate expansion and authoritative DWS filtering. Do not request a tiny global top-k, discard out-of-scope matches, and incorrectly report that the scoped corpus contains no evidence. If the adapter cannot meet scoped recall efficiently, materialize a scoped index view or revise the integration in a recorded decision.

Cross-project retrieval is explicit. Project boundaries are organizational in V1, not a claim of hardened multi-user isolation.

### 14.4 Update and query scheduling

Bootstrap and migrate the index before concurrent use. Batch new artifacts through one update worker; do not run `qmd update` once per document per agent. Keep only one updater per index, coordinate maintenance, and cap lexical-search subprocess concurrency.

The inspected QMD database-opening code enables WAL and busy-timeout handling, including contention during initial journal setup. That improves concurrency but does not remove startup/version-specific behavior. Test the exact build under simultaneous queries and updates. [S10]

The adapter must use argument-array subprocess execution, never shell interpolation; bound stdout/stderr, deadlines, and process count; validate JSON; and translate nonzero exit statuses into typed outcomes. Initialization must not happen implicitly on every untrusted request.

### 14.5 Passage extraction and citations

QMD supplies lexical candidates and available snippets/text. DWS maps those results to canonical snapshot IDs, retrieves the matching normalized body, and selects bounded source windows. Where exact offsets are not guaranteed by QMD output, DWS computes and verifies locators against its own retained artifact before returning citations.

Do not describe document-level keyword search as a ready-made perfect chunk-retrieval engine. Multi-passage retrieval, overlap suppression, stable line ranges, and text budgets are responsibilities of the DWS adapter/service.

### 14.6 Why not delete source files after indexing?

QMD's file-indexing lifecycle can mark removed files inactive, and its maintenance routines can remove inactive/unreferenced content. Therefore, QMD's stored text is useful for retrieval but must not be the only preservation copy under DWS retention policy. [S30]

Retain normalized artifacts for reproducible rebuilds. QMD cleanup and DWS retention are coordinated; DWS never edits QMD's private tables to simulate deletes.

### 14.7 Future semantic retrieval trigger

Vectors become a candidate when a representative test set shows meaningful lexical misses on conceptually relevant passages despite sensible host query reformulation. Other triggers include sustained cross-project reuse and a corpus whose vocabulary variation materially hurts the workflow.

Measure improvement against extra indexing time, disk use, model startup, hardware requirements, and output quality. Corpus size alone is not a sufficient trigger. Enable embeddings selectively for retained/pinned collections before considering a universal semantic index.

---

## 15. Retention, caching, and evidence preservation

### 15.1 Separate three decisions

```text
Acquire a document?
       !=
Retain the captured artifact?
       !=
Index it for search?
```

A failed parse can retain source bytes for diagnosis without entering the text index. A short-lived accepted page can be indexed during a run without being archived forever. A pinned cited PDF can be preserved even when its text extraction is incomplete.

### 15.2 Proposed retention defaults

These defaults are provisional operational policy, not user-approved exact durations:

| Material | Baseline policy |
|---|---|
| Search result records | Retain run history briefly; cache live search results for a short configurable TTL. |
| Accepted normalized snapshots | Retain for 30 days by default, subject to storage budget and active-run references. |
| Pinned/cited snapshots | Retain until explicit unpin/delete; include required original bytes when exact reproduction matters. |
| Raw HTML | Short diagnostic window, provisionally 7 days; longer when pinned or needed for re-extraction. |
| Downloaded PDFs | Retain alongside accepted snapshots by default within the same retention class. |
| Screenshots/browser traces | Off by default; short retention when explicitly captured. |
| Rejected/challenge bodies | Minimal metadata; optional short diagnostic quarantine, not searchable corpus. |
| Temporary/staged files | Reconcile after crashes; expire unreferenced leftovers. |
| QMD index | Follow the retained searchable artifact set; rebuildable. |

Deleting unpinned material must leave a bounded tombstone sufficient to distinguish “expired” from “never existed.” Sensitive deletion must also cover derived index content, caches, logs where applicable, and backups under their documented policy.

### 15.3 Garbage collection

GC must support a dry run, explain reasons, honor pins and active job references, and refuse deletion of files still being published/indexed. On low disk, first stop admitting large work and collect safe transient data. Never silently remove pinned evidence to satisfy a quota.

The report-writing host cannot assume that merely citing a source automatically pins it. The integration contract must explicitly pin referenced snapshots or export the evidence package.

### 15.4 Cache semantics

Use distinct caches for search responses, URL acquisition, extracted snapshots, and repeated retrieval. Cache keys include relevant query/filter parameters, extraction version, freshness policy, and privacy partition.

Search responses are not proof of current webpage content. A fetch cache returns its capture time and staleness. `force_refresh` obtains a new observation; it does not overwrite a cited snapshot. Conditional HTTP validation may avoid downloading unchanged content when supported.

### 15.5 Do not invent a hit rate

We do not know how often this owner will revisit the same source. Instrument in-run repeat reads, cross-run hits, coalesced acquisitions, stale refreshes, retained-but-never-read bytes, and index cost per useful retrieved passage.

Storage's value is not only caching: it preserves evidence, supports scoped retrieval during the current run, avoids repeated browser work, and lets a host revisit surrounding text after generating a claim.

---

## 16. Concurrency and database ownership

### 16.1 Supported model

Many callers may be active while a smaller number of backend operations execute. Agent count is not database capacity. Proposed acceptance loads are 1, 5, 10, 20, and 50 simultaneous callers, with workload and hardware documented; these are test levels, not guaranteed throughput.

SQLite supports concurrent read connections and serializes writes; WAL allows readers and a writer to overlap. Separate DWS and QMD database files have separate write-lock domains. [S35]

### 16.2 One coordinator, bounded workers

| Resource | Baseline policy |
|---|---|
| DWS metadata writes | One serialized writer path in the coordinator. |
| DWS metadata reads | Short-lived read transactions through controlled connections. |
| QMD lexical searches | Start with 2 simultaneous calls; benchmark 4 before raising. |
| QMD index updates | Exactly 1 active updater per index. |
| QMD maintenance | Coordinated exclusive maintenance window or generation rebuild. |
| Crawl job workers | Start with 1 worker process; bounded internal acquisition concurrency. |
| Browser pages | Start with 2 concurrent pages; adjust to measured memory/latency. |
| Static fetches | Start with 4 concurrent acquisitions, separately limited per domain. |

These are tunable DWS defaults. They are not hard limits of SQLite, QMD, or the providers.

Worker control calls do not become model-visible tools. Global limits live in the daemon, not in per-agent semaphores. Separate CLI clients must not independently start QMD commands against the live shared index.

### 16.3 Transaction discipline

Network, browser, parser, and QMD work occur **outside** DWS write transactions. Use transactional compare-and-set/state transitions for leases and jobs. Avoid frequent writes to one global counter; aggregate diagnostic counters where possible.

Baseline DWS database settings:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
```

Set connection-specific pragmas on every relevant connection and inspect their results. Busy timeout is bounded waiting, not a substitute for transaction design; some lock/snapshot errors require a new transaction. [S36], [S38]

Use a deliberate durability setting: default DWS metadata to `synchronous=FULL` unless a measured performance decision explicitly accepts weaker power-loss durability. Do not advertise acknowledged durable jobs while quietly assuming all power-loss cases behave like a graceful restart. [S09]

### 16.4 QMD-specific caution

Do not override QMD internals with DWS SQL. Its driver and runtime have their own settings. Establish index directories and schema before serving queries; coordinate the exact build's update and maintenance behavior through the adapter.

A long-lived JavaScript process can reduce startup cost, but synchronous SQLite calls do not become parallel CPU execution merely because a method returns a promise. Benchmark CLI process overhead separately from SQL execution before adding a QMD sidecar or worker pool.

### 16.5 Local disk, not shared network files

Database files remain on one machine's local persistent storage. Multiple remote clients, if later supported, must call DWS rather than open a SQLite file on a NAS. WAL relies on same-host coordination and is not supported over a network filesystem. [S09]

Two SQLite files do not imply two database-server services; SQLite runs embedded in its callers. [S37]

### 16.6 Why Turso is not selected

The Turso Rust engine and libSQL are different choices. The evaluated Rust engine supports opt-in concurrent writes through MVCC/`BEGIN CONCURRENT`, with conflicts requiring retry. Its compatibility document lists SQLite FTS5 as unsupported in favor of a different full-text implementation. [S26], [S27]

That makes Turso a possible future **DWS metadata** backend, not a transparent replacement for QMD's SQLite driver/schema. Migrate only if measured lock wait remains material after short transactions and proper scheduling. Never point ordinary SQLite and Turso writers at the same live file as an ad hoc experiment.

### 16.7 Bundled SQLite verification

Record the SQLite runtime actually used by Python and by QMD's selected driver. The official WAL documentation reports a rare reset-race fix in 3.51.3 and selected backports. Release qualification must prove the installed runtimes contain that fix or a later equivalent; checking only the host `sqlite3` executable is insufficient. [S09]

---

## 17. One Docker Compose deployment

### 17.1 Meaning of “single Compose”

The owner runs one DWS-managed Compose project. This does not mean one container, one database file, or every optional service running continuously.

A single root `compose.yaml` SHOULD describe the default services and optional profiles. Referenced Dockerfiles, configuration files, secrets, and lockfiles are expected. If upstream Compose material is imported or adapted, record its pinned revision and namespace its resources to avoid collisions.

Compose profiles allow optional services to remain disabled in the default invocation. They do not automatically solve application routing, persistence, or health validation. [S23]

### 17.2 Default and optional services

| Service | Default | Purpose |
|---|---:|---|
| `dws-api` | Yes | FastMCP/API, coordinator, metadata owner, QMD scheduling |
| `dws-worker` | Yes | Bounded acquisition/crawl execution |
| `searxng` | Yes | Discovery service |
| `crawl4ai` | Yes | Browser acquisition service |
| Firecrawl service group | No | Optional alternative acquisition profile |
| Standalone QMD server | No | CLI is bundled in DWS initially |
| Separate database server | No | SQLite files in local persistent volume |
| Embedding/GPU service | No | Lexical-only baseline |

Upstream Crawl4AI's container may include internal helpers; “four Compose services” is not a promise of only four operating-system processes. [S13]

### 17.3 Proposed operator commands

```bash
# Intended deployment workflow after implementation:
docker compose up -d --build
docker compose ps
docker compose logs --tail=100 dws-api dws-worker

# Optional, only after its profile has been integrated and tested:
docker compose --profile firecrawl up -d

# Stop services without deleting persistent evidence:
docker compose down
```

`docker compose down -v` is destructive to named volumes and must not appear as the normal stop instruction. Backup and reset commands require clear warnings.

### 17.4 Networking detail that supersedes earlier simplifications

Publish the DWS host port on loopback, for example `127.0.0.1:8765:8765`. Inside a bridged container, the application may need to listen on `0.0.0.0` for Docker networking to reach it. The security requirement is **host exposure restricted to loopback**, not blindly binding every container listener to its own loopback interface. Docker documents the distinction between container ports and host publication. [S24]

Provider services SHOULD be reachable only over the Compose network. The public URL-fetch policy must still block arbitrary requests to those private service addresses; configured internal provider connections are a separate trusted code path.

A cloud-hosted AI client cannot necessarily reach the owner's localhost. Only promise host integrations that have a supported local MCP client/bridge. Public tunnels and remote exposure are not silently part of V1.

### 17.5 Firecrawl integration conditions

The inspected self-hosting guide explicitly distinguishes its local stack from cloud-only/advanced features. The associated Compose source includes Redis, browser/API services, RabbitMQ, and PostgreSQL-related queue infrastructure, with optional backend variations. It is not “one more Python package.” [S21], [S22]

Before enabling its profile, verify a pinned deployment, functional scrape/crawl tests, persistence policy, privacy configuration, and a demonstrated success case that the default path misses. Keep its own dependencies under that profile. No claim is made that self-hosting guarantees the hosted service's anti-bot behavior or removes target-site restrictions.

### 17.6 Health, restart, and persistence

Liveness, readiness, and a functional end-to-end probe are separate. A healthy HTTP process does not prove a browser can acquire pages or QMD can search the index.

Persist DWS metadata, QMD configuration/index, and artifacts explicitly. Temporary browser state is disposable unless a later authenticated workflow requires otherwise. On startup: verify schema/runtime versions, acquire ownership locks, reconcile incomplete publication, recover jobs, initialize QMD, then report readiness.

### 17.7 Backup and restore

Use a coordinated snapshot/backup procedure, not an arbitrary copy of an active database file while ignoring WAL. SQLite provides an online backup API; an offline maintenance snapshot is also acceptable when writers are stopped correctly. [S29]

Backup metadata, retained artifact manifests and bodies, index mapping/configuration, and version inventory. The QMD index may be rebuilt rather than backed up if the source artifacts and configuration are complete. A restore test must prove pinned citations still resolve and incomplete jobs do not duplicate published artifacts.

---

## 18. Security, privacy, and safe retrieval

### 18.1 Local does not mean trusted content

DWS processes URLs and webpage bodies chosen partly by agents and external sources. Those inputs are untrusted even when the server runs on the owner's workstation.

DWS must distinguish trusted service configuration from untrusted fetch targets. An internal Crawl4AI endpoint is allowed because the operator configured it; that does not authorize an agent to fetch arbitrary Compose services or host-local ports.

### 18.2 URL and network policy

Reject unsupported schemes, embedded credentials by default, malformed hosts, and disallowed IP ranges. Validate resolved destinations, redirects, and browser subrequests as applicable. A first-hop URL check alone does not prevent a later redirect or DNS change from reaching a private endpoint. OWASP's SSRF guidance is the implementation reference. [S28]

Loopback, private-network, link-local, metadata-service, and internal Compose targets are denied for public-web acquisition by default. Any later allowlist is explicit and scoped. If a crawler service cannot enforce equivalent network policy, do not expose it unrestricted; use a validated egress control/proxy or disable the unsafe mode.

### 18.3 Local interface protection

Publish only required host ports. Validate Host/Origin where applicable; do not enable wildcard browser access casually. Keep the private worker-control interface authenticated with a local secret and unavailable through ordinary model tools. A simple local token may be required by the chosen host model; full OAuth infrastructure is not a baseline requirement.

Do not mount the Docker socket into DWS to let agents start optional services. Operator commands enable profiles. Do not mount arbitrary host directories or give browser containers unnecessary privileges.

### 18.4 Secrets and hosted services

Provider keys belong in local secrets/environment configuration, not tool schemas, artifacts, prompts, command output, or logs. Never pass incoming MCP bearer credentials downstream as provider credentials.

Hosted fallback is disabled without explicit configuration. A `local_only` policy must prohibit hosted processing even when a key exists. Before external transmission, record the provider and policy basis. Private documents, signed URLs, cookies, and authenticated sessions require a separate future design; they are not implicitly supported by the public-web baseline.

### 18.5 Untrusted content and citations

Webpage text must never become an instruction to alter system behavior. DWS returns it as attributed source data. Host research skills must not follow embedded instructions to reveal secrets, execute code, or change tools.

Do not use metadata labels such as “official” or “verified” without a defined meaning. Source provenance proves where and when DWS obtained content, not that the content is true. A search snippet is not a substitute for reading the underlying source when making a precise claim.

### 18.6 Input and resource bounds

Cap URL length, query length, downloaded/decompressed bytes, redirects, runtime, browser pages, parser input, output text, subprocess output, open files, and disk growth. Test archive/decompression bombs, huge documents, malicious HTML, path traversal, and subprocess-argument injection.

Retention deletion, report pinning, and host-supplied artifact IDs must resolve through DWS metadata. Never treat an arbitrary caller path or URI as permission to read the filesystem.

---

## 19. Token, compute, and cost budgets

### 19.1 Context efficiency requirements

DWS must expose a small, stable tool catalog with concise discriminative descriptions. Stable ordering and catalog caching can help host behavior, but output minimization remains DWS's responsibility. MCP structured content provides a predictable representation; it does not make model-visible JSON free. [S04], [S32]

Default outputs contain the minimum useful combination of IDs, URL/title, bounded source text, state, and provenance. Full provider debug records remain in diagnostics, not every model result. Do not duplicate complete JSON in both text and structured output without a demonstrated host-compatibility need.

Resources carry addresses and optional views. Token savings occur only when large content is not embedded/read indiscriminately. Provide bounded `read` and `retrieve` paths even when full artifacts are exportable.

### 19.2 Proposed budget profile

```yaml
# DWS-owned configuration proposal, not a vendor configuration schema.
profile: local-lexical

policy:
  hosted_providers_enabled: false
  generative_inference_enabled: false
  vector_search_enabled: false
  automatic_ocr_enabled: false

concurrency:
  metadata_write_workers: 1
  qmd_search_calls: 2
  qmd_index_updates: 1
  acquisition_workers: 1
  static_fetches: 4
  browser_pages: 2

outputs:
  search_default_results: 10
  search_max_results: 30
  search_snippet_max_chars: 600
  fetch_excerpt_max_chars: 800
  retrieve_default_passages: 6
  retrieve_max_passages: 20
  retrieve_text_budget_chars: 12000
  read_default_max_chars: 16000

crawl:
  default_max_pages: 100
  default_max_depth: 2
  default_scope: same_path
  default_max_duration_seconds: 600
  hard_max_pages: 1000

jobs:
  suggested_poll_interval_ms: 10000
  heartbeat_interval_seconds: 10
  lease_timeout_seconds: 60

retention:
  normalized_transient_days: 30
  raw_html_transient_days: 7
  pinned_expires_automatically: false
```

These values are proposed defaults to test. Hard limits may be changed only through owner-controlled policy, not by an agent overriding its request schema. Queue capacity, byte limits, storage ceilings, and hosted spending ceilings must be set during the deployment spike according to the reference machine.

A larger crawl is not approved just because the caller sets a larger number. The baseline returns `budget_exceeded` with the active limit. A future MRTR approval flow can permit a specific, scoped exception; it must not create a general bypass.

### 19.3 Compute accounting

Measure browser time, parse CPU time, QMD update time, query time, process-startup overhead, and storage amplification separately. Vector inference can add substantial model work, but it is not automatically the largest cost in every workload; browser rendering, PDFs, OCR, and huge corpora may dominate instead.

No claim of token, RAM, or latency savings is considered validated without an observed workload and baseline. Report generated-output characters/bytes and, where a host tokenizer is available, estimated tokens with the tokenizer identified.

---

## 20. Functional requirements and traceability

### 20.1 Interface and search requirements

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-01 | P0 | All interfaces use the same DWS services/models. | Equivalent MCP/CLI inputs yield equivalent canonical results in fixture tests. |
| FR-02 | P0 | FastMCP remains an adapter. | Core imports contain no FastMCP/host-agent dependency. |
| FR-03 | P0 | Search returns records, not page bodies. | Bounded result count/snippets; no implicit page acquisition. |
| FR-04 | P0 | Search supports a configured fallback. | Inject primary failure and verify alternate eligible path plus diagnostics. |
| FR-05 | P0 | Preserve original result provenance. | Search hit URL/title/provider observations survive normalization. |
| FR-06 | P0 | Distinguish empty, partial, and failed search. | Each case has a fixture and typed output. |
| FR-07 | P0 | Preserve request-level deadlines/budgets across fallbacks. | Cascade cannot exceed configured attempts/deadline without a bounded error. |
| FR-08 | P1 | Support optional independently configured hosted search. | Disabled/local-only profiles make no hosted calls. |

### 20.2 Acquisition and artifact requirements

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-09 | P0 | Fetch supports static and browser-backed paths. | Representative static and JS fixtures produce usable snapshots. |
| FR-10 | P0 | Normalize HTML/text and text-bearing PDFs. | Golden fixtures retain substantive text and declared locators. |
| FR-11 | P0 | Detect unusable/error/challenge responses. | Such bodies are not indexed as requested content. |
| FR-12 | P0 | Store immutable captured versions. | Refreshing changed content does not change the old snapshot read. |
| FR-13 | P0 | Keep source/final/canonical URL semantics distinct. | Redirect/canonical fixtures preserve all observations. |
| FR-14 | P0 | Publish metadata and index intent recoverably. | Crash injection at every publication step produces no lost accepted artifact. |
| FR-15 | P0 | Return excerpts rather than mandatory summaries. | Default path needs no model configuration or generation call. |
| FR-16 | P0 | Enforce artifact-size and parser limits. | Oversized/malicious inputs terminate predictably. |
| FR-17 | P1 | Support selected artifact import/export. | Imported material has explicit origin and scoped retention. |

### 20.3 Crawl and jobs requirements

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-18 | P0 | Persist jobs before acknowledging them. | Accepted ID remains resolvable after restart. |
| FR-19 | P0 | Persist frontier and enforce scope/depth/page/runtime limits. | Trap and redirect fixtures cannot escape configured scope. |
| FR-20 | P0 | Support cancellation. | Stop admission, cancel supported work, preserve completed artifacts. |
| FR-21 | P0 | Recover leases and retry idempotently. | Worker crash does not duplicate canonical snapshots or leave jobs permanently running. |
| FR-22 | P0 | Report partial crawl outcomes honestly. | Terminal job state and acquisition coverage are independently represented. |
| FR-23 | P0 | Expose bounded status/manifest reads. | No full page corpus or unbounded frontier in a status response. |
| FR-24 | P1 | Map to native MCP Tasks where supported. | Existing job semantics remain authoritative; no second inconsistent task lifecycle. |

### 20.4 Retrieval and storage requirements

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-25 | P0 | Use QMD lexical mode by default. | Fresh-run test sees no embedding, expansion, or reranking invocation. |
| FR-26 | P0 | Separate DWS and QMD database ownership. | No custom DWS tables or migrations in QMD database. |
| FR-27 | P0 | Index accepted normalized artifacts only. | Search hits, binary assets, secrets, fixtures, and challenge bodies stay excluded. |
| FR-28 | P0 | Expose indexing lag explicitly. | Captured-but-pending artifact can be read without falsely claiming full indexed coverage. |
| FR-29 | P0 | Enforce project/run/crawl/document scope. | Scoped retrieval never returns out-of-scope text. |
| FR-30 | P0 | Return faithful bounded passages with locators. | Every passage maps to the exact retained snapshot text. |
| FR-31 | P0 | Coordinate QMD updates and maintenance. | Mixed read/update load passes without unbounded process spawning or uncontrolled writer races. |
| FR-32 | P0 | Retain rebuildable normalized source files. | QMD rebuild from retained data reproduces searchable membership. |
| FR-33 | P0 | Pin, expire, and delete through retention policy. | GC dry run and real run agree; pinned content remains. |
| FR-34 | P0 | Cache/in-flight dedupe respects freshness and privacy. | Incompatible requests are not incorrectly coalesced. |

### 20.5 Operations and safety requirements

| ID | Priority | Requirement | Acceptance condition |
|---|---|---|---|
| FR-35 | P0 | One Compose entry point. | Default start works without optional provider/model credentials. |
| FR-36 | P0 | Shared-store CLI routes through the daemon. | Concurrent CLI processes cannot bypass global indexing/acquisition limits. |
| FR-37 | P0 | Restrict host exposure and provider endpoints. | Port audit shows only the intended loopback endpoint. |
| FR-38 | P0 | Enforce SSRF/redirect/browser-network policy. | Private-target attack fixtures are denied across enabled acquisition paths. |
| FR-39 | P0 | Protect secrets and sensitive logs. | Secret-canary tests find no leakage into outputs/artifacts/logs. |
| FR-40 | P0 | Bound queues and return backpressure. | Overload produces controlled waiting/refusal, not unbounded memory growth. |
| FR-41 | P0 | Provide readiness and diagnostic inventory. | `doctor` identifies missing provider, database, browser, index, and version issues. |
| FR-42 | P0 | Backup/restore retained evidence and job state. | Restore test resolves pinned snapshot locators and recovers incomplete jobs safely. |
| FR-43 | P1 | Optional Firecrawl profile remains isolated. | Default start succeeds without its dependencies; enabled profile passes conformance tests. |
| FR-44 | P1 | Default host skill template follows boundaries. | It plans/synthesizes outside DWS and cites/pins DWS evidence appropriately. |

---

## 21. Non-functional requirements and acceptance targets

### 21.1 Correctness and durability

Accepted jobs and committed artifact records must survive tested process/container restarts. Power-loss durability claims must match the chosen SQLite/filesystem settings. Partial provider failures must be visible without corrupting existing evidence.

**Release blockers:** lost acknowledged job; silent source-text mutation behind an immutable URI; out-of-scope/private retrieval; unbounded model output; model inference unexpectedly activated in lexical mode; corruption under the mixed-load test.

### 21.2 Performance targets—not benchmarks

| Measure | Provisional target / test method |
|---|---|
| Local job-status response | Target p95 under 250 ms when not deliberately overloaded. |
| Warm lexical retrieval | Target p95 under 2 seconds for a documented 10,000-document reference corpus. |
| Overload | Bounded queue and typed backpressure under a 50-caller burst. |
| Concurrency target | Qualify 10–20 active callers; report behavior at 1/5/10/20/50. |
| Index lag | Target first batch searchable within 30 seconds when the indexer is idle; report larger backlog explicitly. |
| New index bootstrap | Measure cold startup separately; do not mix it into warm-query claims. |
| Memory | Enforce a configured ceiling and measure browser/QMD peaks on the reference machine. |
| Output size | All default tools remain within their configured count/text/byte limits. |

These targets may be revised after measurement through the decision log. The reference machine's CPU, RAM, disk type, architecture, Docker runtime, corpus size, document length distribution, and software versions must accompany results.

### 21.3 Maintainability

Adapters must have shared conformance tests. Dependency updates require a reproducible lock and smoke-test run. Public schemas use explicit versioning; additive fields are preferred, breaking changes require a migration note. Default catalog changes must include token/host-selection review.

### 21.4 Observability

Record request/operation IDs, provider attempts, elapsed/queue time, acquisition bytes, cache decisions, index generation/lag, database busy events, job recovery, and retained storage. Logs are structured and bounded; a full tracing platform is unnecessary initially.

Measure SQL execution separately from writer queue wait, QMD query time separately from process startup, and acquisition separately from indexing. Otherwise, database migrations risk targeting the wrong bottleneck.

---

## 22. Test strategy and operational verification

### 22.1 Test layers

**Unit:** canonicalization, scope rules, error mapping, budgets, metadata merging, passage boundaries, score labeling, retention, idempotency.

**Adapter contract:** Search/Fetch/Crawl/Retrieval implementations must satisfy the same normalized schemas and safety/timeout rules. Mocked tests do not replace at least one real endpoint probe for each enabled integration.

**Local integration:** Real DWS SQLite, QMD index, artifact filesystem, coordinator, and worker against local HTTP fixtures. No paid services are required for core CI.

**Protocol/CLI:** MCP and CLI parity, supported host versions, resource-link behavior, bounded reading, cancellation/status, schemas, and tool errors.

**Recovery:** Kill API/worker/QMD at controlled publication/index/job steps; restart and reconcile. Test disk full, permission errors, interrupted migrations, stale leases, and backup restore.

**Live smoke tests:** A small explicitly allowed public-source set validates current external APIs, respecting limits and avoiding claims of universal scraping coverage.

### 22.2 Required fixture corpus

Static article; short valid page; JS-rendered page; redirected URL; tracking-query variants; duplicate body under two URLs; malformed HTML; login/challenge body with HTTP 200; text PDF; scanned PDF; large/code-heavy document; simple table; long unbroken text; multilingual text; crawl loop; calendar/query explosion; cross-domain link; private-address redirect; prompt-injection text; deleted/changed source; index-pending document; expired/pinned artifact.

All test fixtures must stay outside production QMD collection roots. Mark synthetic source text clearly.

### 22.3 Concurrency test matrix

For 1, 5, 10, 20, and 50 callers, test metadata-only reads, lexical-only searches, mixed searches and updates, capture bursts, job polls during a crawl, cancellation during update, and crash recovery while queries are waiting.

Report p50/p95/p99 where sample size supports them, completion/error counts, queue wait, busy/retry events, memory peak, index lag, and worker utilization. A missing benchmark is not filled with an estimated “agents supported” number.

### 22.4 Zero-model qualification

In a fresh image with no model credentials and an empty model cache, demonstrate: startup, search, static fetch, browser fetch, crawl, lexical index, lexical query, bounded read, and restart. Inspect network calls/processes to establish that DWS did not unexpectedly download a model or trigger embeddings/reranking.

If QMD initialization requires optional model-related setup even for lexical use in the pinned release, resolve it explicitly before shipping—not through a hidden install-time download.

### 22.5 Citation fidelity test

For every returned passage, confirm snapshot identity, exact normalized text match, valid locator range, correct source observation, no fabricated date, and no silently omitted negation/table unit. This is more important than generating a polished-looking snippet.

---

## 23. Delivery phases and release gates

No delivery dates or effort estimates are implied by these phases.

| Phase | Deliverable | Exit gate |
|---|---|---|
| P0 — Compatibility spike | Verified FastMCP/QMD/runtime pins, basic Compose topology, lexical-only probe | GATE-01 through GATE-04 below |
| P1 — Contracts and storage | Core models, artifact publication, metadata schema, one-owner coordinator | Crash-safe capture and scoped IDs |
| P2 — Acquisition | SearXNG + DDGS + static path + Crawl4AI, typed fallbacks | Provider conformance and SSRF tests |
| P3 — Retrieval | QMD lexical indexing, outbox, bounded read/retrieve, provenance | Scope, lag, no-model, and citation tests |
| P4 — Durable crawl | Frontier, worker leases, status/cancel, partial results | Restart/cancellation/limit tests |
| P5 — Interfaces | FastMCP tools/resources, daemon-backed CLI, health/doctor | Host/CLI parity and bounded output |
| P6 — Operations | Retention, backup/restore, concurrency qualification, documentation | Complete P0 acceptance suite |
| P7 — Optional integrations | Default host skill, Firecrawl/TinyFish/Spider as justified | Each optional adapter earns its place with a measured use case |

### Release gates

- **GATE-01 — Dependency identity:** Verify standalone Python FastMCP, original QMD, and intended crawler repositories. Avoid similarly named packages.
- **GATE-02 — Version/host compatibility:** Pick tested versions; state whether any are prereleases; verify actual host protocol/Tasks/resource behavior.
- **GATE-03 — Lexical-only QMD:** Search/update/get work without vector inference or unapproved model downloads.
- **GATE-04 — Storage/runtime safety:** Bundled SQLite fixes, local volume behavior, index startup/migration, and ownership locks pass.
- **GATE-05 — Acquisition completeness:** Default stack supports required fixture classes and a tested non-agentic fallback.
- **GATE-06 — Durability:** Crash/restart/restore tests pass with no lost acknowledged jobs or citations.
- **GATE-07 — Concurrency:** Measured mixed-load behavior meets the documented reference profile or revised accepted targets.
- **GATE-08 — Safety and privacy:** Network policy, provider opt-in, secret canaries, and untrusted-content handling pass.

---

## 24. Architecture decision records

Each record preserves the selected approach, alternatives, trade-off, and the condition that would justify reconsideration. These are decisions about DWS, not universal rankings of libraries.

### ADR-001 — Product name and scope

**Status:** Settled.  
**Decision:** Use Deep Web Search and `dws`; define the product as acquisition/retrieval infrastructure.  
**Alternative:** DeepWeb; a generic autonomous “research engine.”  
**Why:** The new name was explicitly requested and better reflects reusable capabilities. Research reasoning has a different owner.  
**Cost:** Older examples, paths, and resource schemes need migration.  
**Revisit:** Only by an explicit naming/scope decision; do not drift back to `deepweb` identifiers in new interfaces.

### ADR-002 — Host-side research, not an embedded orchestrator

**Status:** Settled; supersedes the earlier hybrid internal ResearchService.  
**Decision:** Ship optional host agent/skill templates alongside DWS. Keep planning, semantic relevance judgment, evidence interpretation, gap analysis, and synthesis outside core.  
**Alternatives:** Fully deterministic tools with no reusable skill; bounded LLM research workflow inside DWS; fully autonomous internal agent.  
**Why:** Funda and technical research need different methodologies; the host already supplies reasoning.  
**Cost:** Standalone `dws research` does not exist without a host/runner. Host integrations differ and need tests.  
**Revisit:** A genuine unattended research use case could justify a separate orchestration package that calls DWS, not a silent merger into core.

### ADR-003 — FastMCP over direct official SDK use

**Status:** Settled user choice.  
**Decision:** Use the standalone Python FastMCP framework.  
**Alternative:** Direct official MCP Python SDK, initially recommended because the MCP surface is small.  
**Why:** User familiarity with FastAPI-style decorators, schemas, lifecycle, and framework terminology outweighs minimizing one abstraction layer. Both routes can support a thin adapter; selecting FastMCP does not require coupling the core to it. [S01], [S02], [S03], [S39]  
**Cost:** Additional framework surface and upgrade testing; exact pins required.  
**Revisit:** A demonstrated framework limitation or maintenance problem—not a preference for fewer dependencies alone.

### ADR-004 — Version pins are release gates, not chat facts

**Status:** Baseline safeguard.  
**Decision:** Verify pins against project identity, primary release/package sources, and runtime probes.  
**Alternative:** Copy previously stated FastMCP 4.0.0/4.0.3 or other “latest” versions.  
**Why:** Primary snapshots retrieved during consolidation did not substantiate the earlier stable-v4 claims. [S01], [S02], [S03]  
**Cost:** A small compatibility spike precedes implementation.  
**Revisit:** Freeze verified pins in lockfiles; the decision to verify remains permanent.

### ADR-005 — Small semantic tool catalog

**Status:** Settled direction; seven-tool baseline.  
**Decision:** Expose search/fetch/crawl/retrieve/read/job-status/job-cancel.  
**Alternative:** Separate tools for every vendor and every internal operation; a giant OpenAPI-to-MCP export.  
**Why:** Hosts choose capabilities, not plumbing. Small schemas reduce selection ambiguity and repeated context.  
**Cost:** Advanced provider tuning requires configuration/diagnostics rather than public tool knobs.  
**Revisit:** Add a tool only when an existing capability cannot express a meaningful user action clearly.

### ADR-006 — One Compose entry point

**Status:** Settled.  
**Decision:** Operator-managed root Compose with default and optional services.  
**Alternatives:** Independent installation instructions per dependency; host-only runtime; always-on full vendor stacks.  
**Why:** The owner explicitly wants one working deployment. Profiles preserve optionality without manual multi-project startup. [S23]  
**Cost:** Container build, volume, and browser-resource configuration remain real work.  
**Revisit:** A desktop packaging requirement may change distribution; it must preserve reproducibility and storage guarantees.

### ADR-007 — Shared daemon instead of one independent MCP process per host

**Status:** Baseline.  
**Decision:** Local Streamable HTTP is canonical; stdio can be a bridge to the shared backend.  
**Alternative:** Each host launches an independent fully stateful DWS instance.  
**Why:** One daemon coordinates shared stores, limits, cache, and jobs. This is an ownership advantage, not a claim that stdio cannot share files.  
**Cost:** The daemon must be running; some hosts need a local bridge.  
**Revisit:** A portable standalone mode may be added for isolated stores, without bypassing shared ownership.

### ADR-008 — CLI uses shared-store coordination

**Status:** Baseline refinement of earlier direct-core CLI examples.  
**Decision:** Normal CLI commands call the daemon; direct Python use is for isolated stores or explicit exclusive mode.  
**Alternative:** Every CLI directly writes shared SQLite and launches QMD.  
**Why:** Per-process semaphores cannot enforce global limits. Reusing the core does not require every caller to own the storage lifecycle.  
**Cost:** A small local application API/client layer.  
**Revisit:** A proven cross-process coordinator could replace HTTP while retaining the same safety properties.

### ADR-009 — SearXNG primary with capability-aware discovery fallbacks

**Status:** Settled primary; fallback details baseline.  
**Decision:** SearXNG first, DDGS lightweight fallback, optional separately enabled hosted search.  
**Alternatives:** Treat crawlers as search engines; rely entirely on a paid search API; regard same-upstream wrappers as independent redundancy.  
**Why:** Matches user preference and keeps discovery replaceable. SearXNG's JSON API must be configured; DDGS is a metasearch library rather than a guaranteed DuckDuckGo-only independent index. [S14], [S16]  
**Cost:** External-engine restrictions and correlated failures remain.  
**Revisit:** Reliability measurements justify another independently operated search backend.

### ADR-010 — Cheap acquisition first, Crawl4AI for browser work

**Status:** Settled browser choice; static fast path baseline.  
**Decision:** Direct HTTP/deterministic extraction where sufficient; Crawl4AI when rendering or supported extraction adds value.  
**Alternatives:** Browser every URL; build all browser/extraction logic directly on Playwright; immediately adopt several crawlers.  
**Why:** Separate network acquisition, rendering, and parsing costs. Crawl4AI offers both traditional and model-backed extraction; only the non-generative paths belong in the default profile. [S12], [S17], [S18]  
**Cost:** Two acquisition paths need the same conformance tests.  
**Revisit:** Data may show a simpler uniform path has better reliability at acceptable cost.

### ADR-011 — Firecrawl is an optional self-hosted backup, not a default mandate

**Status:** Optional; exact integration unvalidated.  
**Decision:** Keep a Compose profile path, disabled initially. Prefer evaluating self-hosting over depending on hosted pricing as requested.  
**Alternatives:** Always run Firecrawl and Crawl4AI; choose hosted Firecrawl as mandatory; reject Firecrawl outright.  
**Why:** It may improve coverage, but inspected self-host material has multiple dependencies and does not provide every cloud capability. [S21], [S22]  
**Cost:** Optional profile maintenance; no promise that a backup is ready until its tests pass.  
**Revisit:** Enable when a representative hard case succeeds reliably and justifies idle/runtime resource cost.

### ADR-012 — Spider remains replaceable, not automatically second-best

**Status:** Deferred.  
**Decision:** Preserve the adapter interface for `spider-rs/spider`; do not rank it “next best” without benchmark evidence.  
**Alternatives:** Mandatory Rust crawler alongside Crawl4AI; replacing Crawl4AI immediately.  
**Why:** The user identified it as a candidate, not a completed comparative test. The original project must be distinguished from hosted services and similarly named wrappers. [S25]  
**Cost:** No immediate alternate local traversal implementation.  
**Revisit:** A crawl throughput, memory, robustness, or capability gap demonstrated on DWS workloads.

### ADR-013 — TinyFish by capability, with explicit remote policy

**Status:** Optional.  
**Decision:** Evaluate Search, Fetch, and programmatic Browser independently. Keep natural-language Agent usage out of the default acquisition path.  
**Alternative:** Treat all TinyFish functionality as a single interchangeable crawler or an internal research agent.  
**Why:** Different API surfaces imply different behavior and operational/privacy costs. [S20]  
**Cost:** Capability-specific adapters and account probes.  
**Revisit:** Enable each surface only when it fills a demonstrated gap and the owner accepts external processing.

### ADR-014 — QMD lexical retrieval over a custom FTS implementation

**Status:** Settled user preference.  
**Decision:** Use QMD as the sole document-search subsystem with its lexical path.  
**Alternative:** Build DWS's own FTS5 search/read/collection workflow.  
**Why:** Reuse existing CLI/document tooling and retain a future semantic option. QMD exposes keyword search separately from its hybrid path. [S06], [S07]  
**Cost:** JavaScript/native runtime footprint, adapter maintenance, and index lifecycle.  
**Revisit:** QMD integration overhead, scoped retrieval limitations, or concurrency behavior outweigh the reused functionality. A direct-FTS adapter would replace QMD—not run as a duplicate corpus by default.

### ADR-015 — No default vector index

**Status:** Settled.  
**Decision:** Do not embed every artifact or start an embedding/reranking service.  
**Alternatives:** QMD hybrid everywhere; a dedicated vector store; automatic summaries as a searchable substitute.  
**Why:** The workload is largely personal/ad hoc; lexical-first utility can be measured before adding model compute.  
**Cost:** Conceptually related passages with different vocabulary may be missed. Hosts may need query variants.  
**Revisit:** A representative relevance test shows enough semantic-recall improvement to justify selected-collection embeddings.

### ADR-016 — Two database files with clear ownership

**Status:** Settled.  
**Decision:** DWS SQLite owns operational metadata/jobs; QMD SQLite owns its search projection.  
**Alternative:** Add all DWS tables to QMD's file, or duplicate QMD's body/FTS corpus in DWS SQLite.  
**Why:** QMD maintenance/rebuild semantics differ from durable application state. Two embedded files do not require two database servers. [S08], [S30], [S37]  
**Cost:** Cross-store publication needs an outbox/reconciler; normalized text exists as an artifact and in QMD's stored/indexed representation.  
**Revisit:** Only if QMD offers a supported general storage extension with compatible lifecycle guarantees; physical file count alone is not a reason.

### ADR-017 — Ordinary SQLite before Turso

**Status:** Accepted baseline.  
**Decision:** Retain SQLite for DWS metadata; do not port QMD to Turso.  
**Alternative:** Use the Rust engine for concurrent writers now; mistake libSQL and Turso Rust as identical.  
**Why:** DWS writes can be brief and scheduled. Turso's concurrent-write mode requires its own transaction/conflict handling, and its full-text implementation does not match QMD's SQLite FTS5 dependency. [S26], [S27]  
**Cost:** SQLite writer contention remains something to monitor.  
**Revisit:** Measured metadata write wait remains material after transaction/scheduler fixes. Benchmark a repository implementation without rewriting the public API.

### ADR-018 — Retain useful artifacts, not everything forever

**Status:** Settled direction; TTLs baseline.  
**Decision:** Keep accepted normalized artifacts during a retention window, pin cited evidence, and retain raw material selectively.  
**Alternatives:** Never store; archive every response/browser asset forever; index every discovered URL.  
**Why:** Within-run retrieval and reproducibility matter even with low cross-project reuse. Unbounded retention is unnecessary.  
**Cost:** GC, pinning, tombstones, and storage metrics are required.  
**Revisit:** Observed revisit rates and retained-but-unused bytes justify different TTLs, not unsupported assumptions.

### ADR-019 — Source artifacts remain rebuildable

**Status:** Settled.  
**Decision:** Keep normalized files as the rebuild source and QMD as a derived search store.  
**Alternative:** Index once, delete the files, and use QMD as the only archive.  
**Why:** QMD's file-removal/cleanup lifecycle can deactivate or remove indexed content. [S30]  
**Cost:** Some text duplication and disk overhead.  
**Revisit:** A separate archive backend may reduce duplication if preservation and rebuild guarantees remain explicit.

### ADR-020 — Excerpts and evidence, not automatic summaries

**Status:** Settled.  
**Decision:** Return deterministic source excerpts; let the host synthesize when necessary.  
**Alternative:** Summarize every fetched page with an LLM.  
**Why:** Avoid unneeded model calls, omitted qualifications, and summary-as-evidence confusion.  
**Cost:** The host performs semantic synthesis and may request more context.  
**Revisit:** Optional cached summaries could be a separate host-side artifact; never replace original evidence or become mandatory fetch work.

### ADR-021 — Resource links and bounded reads

**Status:** Settled direction; `read` tool baseline.  
**Decision:** Large artifacts are addressable; default tool outputs remain small. A bounded read tool supplements resources for host compatibility.  
**Alternative:** Embed complete documents/manifests; assume resources automatically save tokens.  
**Why:** Addressability only enables lazy access; it does not force a host to avoid large reads. [S04], [S05]  
**Cost:** More deliberate retrieval steps and selector design.  
**Revisit:** Small objects may be embedded when useful; large corpora remain bounded.

### ADR-022 — DWS owns durable jobs, not MCP Tasks

**Status:** Settled.  
**Decision:** JobStore, worker recovery, and crawl checkpoints are independent of MCP.  
**Alternatives:** In-memory async tasks; using the MCP Task schema as the application database; letting FastMCP's task engine become the sole execution authority.  
**Why:** CLI, reconnects, restart recovery, and provider state outlive a protocol call. Framework Tasks can map onto this design but do not erase it. [S31]  
**Cost:** A small job lifecycle must be implemented.  
**Revisit:** A framework integration may implement part of the worker machinery if it preserves DWS semantics and storage requirements.

### ADR-023 — Polling first; MRTR and subscriptions are not job storage

**Status:** Settled.  
**Decision:** Use status polling with backoff. Keep approval continuation separate from job execution and defer notification streams.  
**Alternatives:** Stream every progress event; use `requestState` as research/job state; keep long operations attached to one request.  
**Why:** Simple personal operation with explicit identifiers.  
**Cost:** Bounded status traffic and non-instant UI updates.  
**Revisit:** A live dashboard or host notification requirement justifies subscriptions after testing.

### ADR-024 — Central scheduling before a database migration

**Status:** Accepted baseline.  
**Decision:** Single shared-store coordinator, brief metadata transactions, one QMD updater, bounded readers, measured overload.  
**Alternative:** Unlimited subprocesses, per-agent semaphores, or immediate Turso/PostgreSQL adoption.  
**Why:** Concurrency problems often concern initialization, index updates, worker ownership, or process overhead rather than the SQL engine alone.  
**Cost:** Queueing and coordinator availability are explicit concerns.  
**Revisit:** Load tests identify the coordinator or storage as an actual bottleneck and justify a documented topology change.

### ADR-025 — Crawl is traversal above acquisition

**Status:** Settled concept; DWS frontier baseline.  
**Decision:** Crawl manages scope/frontier/budget and creates many canonical documents. Native providers may optimize acquisition if they satisfy policy.  
**Alternatives:** Make crawl merely an alias for one-page fetch; force all vendor internals through public MCP calls; accept opaque native outputs without provenance.  
**Why:** Traversal and document acquisition have distinct responsibilities.  
**Cost:** Frontier persistence and vendor conformance work.  
**Revisit:** Delegate more traversal when measurements justify it without losing scope/recovery behavior.

### ADR-026 — No enterprise infrastructure by default

**Status:** Settled.  
**Decision:** Local Compose, embedded metadata, local artifacts, one worker, bounded diagnostics.  
**Alternatives:** Public service, OAuth server, Kubernetes, distributed queues/database, full tracing platform.  
**Why:** One owner and occasional research do not justify those defaults.  
**Cost:** Single-machine availability; no horizontal scaling promise.  
**Revisit:** Actual multi-user/remote/high-availability needs; do not enable by assumption. Optional vendor dependencies remain separate exceptions.

### ADR-027 — Local safety and hosted privacy remain mandatory

**Status:** Settled direction.  
**Decision:** Loopback host exposure, secrets isolation, SSRF defense, output/input limits, and hosted opt-in.  
**Alternative:** Assume local tools cannot be abused; silently send hard pages to any paid vendor.  
**Why:** Agents and websites provide untrusted inputs; local services and evidence can still be exposed. [S28]  
**Cost:** Some targets/modes are rejected rather than acquired unsafely.  
**Revisit:** Expand explicit allowlists only for documented workflows; never remove the policy boundary.

### ADR-028 — Domain profiles guide hosts; code enforces budgets

**Status:** Baseline from the research-agent discussion.  
**Decision:** Skills contain methodology, optional machine-readable profiles describe source/output preferences, and DWS enforces hard operational constraints.  
**Alternative:** Put everything in prompt prose or embed domain heuristics in the core.  
**Why:** Prompts are not enforcement mechanisms, and investing/technical research have different evidence standards.  
**Cost:** Profile/schema versioning and host adaptation.  
**Revisit:** Add profile fields only for demonstrated needs; no universal “two sources per claim” rule is mandated by DWS.

### ADR-029 — General search/vector systems are deferred, not falsely benchmark-rejected

**Status:** Deferred candidates.  
**Decision:** Do not add Meilisearch, Typesense, Qdrant, Chroma, LanceDB, FAISS, txtai, a standalone Tantivy stack, or another BM25 service to V1. `ripgrep`-style local scans may assist debugging, not form a second production retrieval engine.  
**Alternative:** Install several retrieval systems preemptively.  
**Why:** No comparative workload in this conversation establishes an unmet requirement that QMD lexical retrieval cannot address.  
**Cost:** No specialized alternative is immediately available.  
**Revisit:** Benchmark the specific candidate relevant to the measured gap. These projects were candidates mentioned for evaluation, not proven inferior products.

### ADR-030 — Benchmark and evidence quality over unsupported guarantees

**Status:** Baseline safeguard.  
**Decision:** Capacity, cache hit rate, extraction quality, and version support are measured or labeled unknown.  
**Alternative:** Promise a fixed number of agents, universal anti-bot success, automatic citation correctness, or vector savings from intuition.  
**Why:** Those properties depend on hardware, corpus, upstream services, and exact builds.  
**Cost:** Release qualification requires test artifacts and honest limitations.  
**Revisit:** Replace unknowns with recorded results, never with increasingly confident guesses.

---

## 25. Discussion evolution and corrections

### 25.1 Chronological decision summary

| Stage | What was explored | Final interpretation |
|---|---|---|
| Initial idea | “CRXNG” plus “Crawl for AI,” with Firecrawl/TinyFish/Spider backups | Names resolved to SearXNG and Crawl4AI; backup by capability, not by product name. |
| MCP learning | Host/client/server, tools/resources/prompts, protocol state | MCP is an interface; host owns the client; application data lives below protocol. |
| Tool/resource examples | Search records, fetched document bodies, crawl manifests | Search returns compact records; capture creates artifacts; retrieval/read selects bounded evidence. |
| Research orchestration | Internal bounded planner/evidence/gap/synthesis workflow | Superseded by host-side research agents and skills; core remains model-free by default. |
| Research specialization | Generic versus Funda/technical methodologies | Separate host skills/profiles reuse the same DWS capabilities. |
| Framework comparison | Direct official SDK initially favored for a small server | User chose FastMCP for familiarity and ergonomics; choice is preserved. |
| Deployment discussion | In-process packages, sidecars, separate upstream Compose setups | One DWS-owned Compose entry point; packaging chosen per component. |
| Naming | DeepWeb | Replaced by Deep Web Search / `dws`. |
| Corpus economics | Store/index everything versus one-time research | Retain useful normalized evidence with TTL/pins; lexical index accepted artifacts; no assumed high long-term hit rate. |
| QMD | Hybrid/semantic search versus keyword mode | QMD lexical-only chosen; no default embedding or model inference. |
| Single database idea | Reuse QMD's SQLite as all DWS storage | Rejected as unnecessary schema/lifecycle coupling; separate metadata and search databases. |
| Concurrency | Multiple agents and two SQLite files | Central scheduling, short transactions, one index writer, controlled QMD reads, benchmark actual capacity. |
| Turso | Rust SQLite-like engine and concurrent writers | Deferred for metadata; not a drop-in QMD FTS5 backend. |
| This PRD | Consolidate decisions and rationale | Stable requirements plus explicit baseline defaults, gates, and reconsideration triggers. |

### 25.2 Clarifications that override misleading earlier shorthand

1. **“Research is a kind of job” is incomplete.** A research execution may be a job in a host system, but an evidence/report artifact is not merely a job record. DWS itself no longer runs research jobs in V1.
2. **Async is not durable.** Persistence and recovery are necessary; a detached coroutine alone does not satisfy accepted-job survival.
3. **`requestState` is not job progress.** It belongs to request continuation, not the crawl database or document store.
4. **Resource is not storage.** A URI addresses a representation; the artifact and its database records have separate owners.
5. **A URL is also a URI.** The important distinction is source location versus DWS's captured representation.
6. **Structured output is not automatically token-cheap.** Large JSON can be as wasteful as large prose; result projection and bounds matter.
7. **Keyword retrieval is not semantic completeness.** Lexical misses remain possible and should be measured.
8. **No internal LLM does not imply every optional provider is deterministic.** Capabilities that may invoke a model must be declared and explicitly enabled.
9. **One Compose file is not one container or one process.** Nor do two SQLite files imply two database services.
10. **Crawl4AI/Firecrawl package names can refer to different layers.** A client SDK is not necessarily a self-hosted server or browser runtime.
11. **A backup is not automatically independent.** Shared search upstreams, outbound IPs, and browser failure modes can correlate.
12. **The CLI's shared-core goal does not justify uncontrolled shared-file access.** Default CLI uses the daemon; isolated core use remains possible.
13. **FastMCP's selected framework is settled; a claimed current version is not.** See Section 0.3 and GATE-02.
14. **No measured “N agents supported” result exists yet.** The concurrency numbers here are test targets and configuration starting points.
15. **Earlier example scores and page counts were illustrations.** They are not calibrated relevance probabilities, real source findings, or benchmark measurements.

### 25.3 Options mentioned without a completed comparative evaluation

Brave Search API, Scrapy, a bare Playwright implementation, readability-style extractors, alternative BM25 packages, Tantivy-based tools, Meilisearch, Typesense, Qdrant, Chroma, LanceDB, FAISS, txtai, and ripgrep-like scanning were mentioned as possible alternatives or research candidates.

This document does not fabricate a benchmark or a comprehensive rejection rationale for each. Their current status is **not selected for V1 because the settled baseline has no demonstrated requirement for them**. If a candidate solves a measured gap, evaluate it against that gap, rather than reopening the entire stack speculatively.

---

## 26. Risks, open questions, and reconsideration triggers

### 26.1 Risk register

| ID | Risk | Impact | Mitigation / decision trigger |
|---|---|---|---|
| R-01 | FastMCP docs/release/host behavior differ | Broken transport or task integration | Verify exact pins and test real hosts; explicit job tools remain baseline. |
| R-02 | QMD lexical path initializes model components unexpectedly | Hidden compute/download dependency | Fresh-image zero-model test is a release gate. |
| R-03 | QMD startup/update contention | Query failures or long stalls | Bootstrap first; one updater; bounded search pool; test pinned build. |
| R-04 | QMD cannot express desired scope efficiently | Poor recall or incorrect filtering | Scoped collections/views and adapter validation before broad rollout. |
| R-05 | Lexical search misses conceptually relevant evidence | Incomplete host research | Host query variants; measured semantic-retrieval trial if persistent. |
| R-06 | Crawl overfetches irrelevant material | Resource/storage waste | Scope, frontier dedupe, byte/page/time budgets, per-domain caps. |
| R-07 | Extraction drops code, tables, negations, or units | Incorrect downstream conclusions | Fidelity fixtures, original retention, explicit quality warnings. |
| R-08 | Search fallbacks share upstream failure | False sense of redundancy | Document backend provenance; add an independent provider only if needed. |
| R-09 | Firecrawl adds more dependencies than benefit | Operational overhead | Optional profile; incremental-success benchmark before enabling. |
| R-10 | Hosted fallback leaks sensitive URLs/content | Privacy loss | Local-only profile, explicit enablement, credential isolation. |
| R-11 | Shared CLI access bypasses limits | SQLite/QMD contention | Daemon-first CLI and exclusive offline mode. |
| R-12 | Worker retries duplicate remote work or billing | Extra cost/inconsistent state | Idempotent publication, upstream IDs, explicit unknown-outcome handling. |
| R-13 | Disk full or interrupted artifact publication | Lost/inconsistent evidence | Admission checks, staging/reconciler, durable metadata, backup tests. |
| R-14 | Retention removes cited content | Broken audit trail | Explicit pin/export workflow and retained locator verification. |
| R-15 | Coordinator becomes bottleneck | Queue growth | Separate queue/SQL/QMD measurements; optimize before engine migration. |
| R-16 | SQLite runtime lacks a relevant fix | Concurrency safety issue | Check Python and QMD embedded engines, not just system binary. |
| R-17 | Browser/network adapter bypasses SSRF policy | Exposure of local services | Cross-adapter redirect/subresource tests and verified egress controls. |
| R-18 | Root Compose diverges from upstream stacks | Upgrade breakage | Versioned integration notes, conformance probes, exact image revisions. |
| R-19 | ARM64/native dependency mismatch | Failed local image build | Qualify actual target architecture; no assumed cross-platform parity. |
| R-20 | Host cannot reach localhost or handle resources | Unusable integration | Explicit host compatibility matrix; local bridge where supported; bounded read tool. |

### 26.2 Open decisions with safe defaults

| Question | Safe default now | Resolution owner / evidence |
|---|---|---|
| Exact FastMCP release and protocol set | Framework selected; no unverified stable-v4 pin | Implementation compatibility spike + owner acceptance if prerelease needed |
| Exact Python/Node/QMD/browser image versions | Lock only after native/runtime tests | Build/CI qualification |
| Crawl4AI sidecar API coverage | Sidecar baseline; in-process adapter remains possible | Representative fetch/crawl tests |
| HTML/PDF normalizer selection | HTTPX + Trafilatura / pypdf candidates | Golden extraction fixtures and licensing review |
| Firecrawl in first usable release | Off by default | Demonstrated incremental success and acceptable resource profile |
| TinyFish endpoints enabled | None without configuration | Account-specific smoke tests and privacy/cost consent |
| QMD CLI versus persistent wrapper | Bounded CLI first | Separate process-startup and search benchmarks |
| One collection per project versus materialized run views | Project collections + authoritative scope validation | Scoped recall and index-update benchmarks |
| Hardware/storage ceilings | Explicit configuration required | Actual workstation resources and load test |
| Retention durations | Proposed 30-day normalized / 7-day raw HTML | Observed reuse and storage metrics |
| Native MCP Tasks | Optional projection only | Pin/host support and clean JobService mapping |
| Host pinning access | CLI/API pin; approved pinned capture/run profile for MCP-only workflows | Host integration tests; optional narrow pin tool if needed |
| Need for vectors | Disabled | Relevant-query evaluation, not corpus size alone |
| Need for Turso or another metadata DB | Ordinary SQLite | Persistent measured writer contention after scheduling fixes |

### 26.3 Conditions that justify revisiting a major choice

Revisit QMD when its runtime, update cost, scoped retrieval, or maintenance complexity becomes a demonstrated obstacle. Revisit lexical-only retrieval when relevant-evidence recall is measurably insufficient. Revisit SQLite when metadata write contention is a sustained bottleneck rather than a misuse of transactions. Revisit the provider set when required content cannot be obtained by an existing conformant path. Revisit a local-only deployment only when the owner's actual host/network requirements demand it.

Do not revisit the architecture because a new library has an attractive release announcement. Start with a documented problem, test the smallest alternative that addresses it, and record migration and rollback implications.

---

## 27. Change control and implementation checklist

### 27.1 Required change record

Every significant change should state:

```text
Decision ID:
Previous status / decision:
New decision:
Problem observed:
Evidence / benchmark / issue:
Alternatives considered:
Consequences for core, adapters, storage, and hosts:
Migration and rollback plan:
Affected requirements and tests:
Owner acceptance where required:
Date:
```

Do not delete superseded records; change their status and point to the replacement. The PRD is authoritative for intent; lockfiles/configuration are authoritative for the exact shipped build. Implementation differences must update this document rather than becoming undocumented folklore.

### 27.2 Implementation checklist

- [ ] Repository and CLI naming use DWS consistently.
- [ ] No research agent, report synthesizer, or mandatory LLM dependency exists in core.
- [ ] FastMCP/package identity and exact version are verified and pinned.
- [ ] Shared-store ownership and worker communication are implemented explicitly.
- [ ] Public tools remain small, typed, bounded, and provider-neutral.
- [ ] A bounded `read` path works for hosts with limited resource support.
- [ ] SearXNG JSON API and DDGS fallback pass conformance tests.
- [ ] Static and Crawl4AI acquisition paths publish the same Document/Snapshot schema.
- [ ] Crawling enforces scope and durable checkpoints.
- [ ] Source URLs, capture times, publication evidence, and hashes are preserved.
- [ ] DWS metadata and QMD databases remain separate and correctly owned.
- [ ] QMD uses lexical-only search; no unexpected model downloads/inference.
- [ ] Publication/outbox/index state can recover after crashes.
- [ ] Scoped retrieval and passage citations are verified against retained text.
- [ ] QMD update/query/maintenance concurrency is bounded and tested.
- [ ] SQLite runtime fixes/settings are checked inside both relevant runtimes.
- [ ] Retention, pinning, dry-run GC, backup, and restore work.
- [ ] Optional provider profiles are not required for default startup.
- [ ] Hosted APIs are disabled unless explicitly configured and permitted.
- [ ] Local port exposure, secret handling, and SSRF defenses pass tests.
- [ ] Load test reports distinguish caller count, queue wait, SQL, QMD, and browser costs.
- [ ] A host research skill can complete the evidence workflow without vendor-specific logic.
- [ ] Documentation states what is unsupported and which limits are provisional.

### 27.3 Definition of done

DWS V1 is ready when the P0 requirements pass, the exact default Compose deployment starts on the reference machine without model/hosted credentials, at least one real host and the CLI can complete the primary user journeys, and the release includes the measured limitations and restore procedure.

A polished interface without recovery, scope correctness, bounded output, or evidence fidelity is not done. An oversized architecture with unused optional systems is not a substitute for those guarantees.

---

## 28. Primary-source register

**Reviewed during this consolidation on 9 September 2026.** Some retrieved pages expose older crawl snapshots or mutable development branches. They support the stated technical observations, not a claim that every “latest” release was conclusively identified. Recheck at version pinning. No benchmark was run against these projects for this PRD.

| ID | Primary source | Used for |
|---|---|---|
| S01 | [FastMCP installation documentation](https://gofastmcp.com/getting-started/installation) | Standalone framework identity, installation, release/pinning caveat. |
| S02 | [PrefectHQ/FastMCP releases](https://github.com/PrefectHQ/fastmcp/releases) | Visible v4 prerelease history and framework/protocol direction. |
| S03 | [FastMCP on PyPI](https://pypi.org/project/fastmcp/) | Package identity and retrieved release history. |
| S04 | [MCP tools, 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/server/tools) | Tools, schemas, structured output, content/resource links. |
| S05 | [MCP resources, 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/server/resources) | URI-addressed resources, templates, host-driven access. |
| S06 | [Original QMD README](https://raw.githubusercontent.com/tobi/qmd/main/README.md) | QMD identity, keyword search, collections, retrieval modes. |
| S07 | [QMD public SDK source](https://raw.githubusercontent.com/tobi/qmd/main/src/index.ts) | Explicit lexical versus generic/hybrid API distinction. |
| S08 | [QMD store implementation](https://raw.githubusercontent.com/tobi/qmd/main/src/store.ts) | Indexed text, document records, FTS schema, storage behavior. |
| S09 | [SQLite WAL documentation](https://sqlite.org/wal.html) | WAL, local filesystem requirement, durability and documented reset-race fix. |
| S10 | [QMD database-opening implementation](https://raw.githubusercontent.com/tobi/qmd/main/src/db.ts) | SQLite drivers, busy timeout, WAL initialization behavior. |
| S11 | [aiosqlite documentation](https://aiosqlite.omnilib.dev/en/stable/) | Async interface and per-connection worker queue. |
| S12 | [Crawl4AI quick start](https://docs.crawl4ai.com/core/quickstart/) | Browser acquisition, Markdown, traditional versus LLM extraction. |
| S13 | [Crawl4AI Compose source](https://raw.githubusercontent.com/unclecode/crawl4ai/main/docker-compose.yml) | Container runtime, browser shared memory, internal service details. |
| S14 | [SearXNG Search API](https://docs.searxng.org/dev/search_api.html) | Query formats and configured machine-readable search output. |
| S15 | [SearXNG container installation](https://docs.searxng.org/admin/installation-docker.html) | Container deployment baseline. |
| S16 | [DDGS repository](https://github.com/deedy5/ddgs) | Metasearch library and CLI identity. |
| S17 | [HTTPX asynchronous support](https://www.python-httpx.org/async/) | Async HTTP client baseline. |
| S18 | [Trafilatura documentation](https://trafilatura.readthedocs.io/en/latest/) | Deterministic web-text extraction candidate. |
| S19 | [pypdf text extraction documentation](https://pypdf.readthedocs.io/en/stable/user/extract-text.html) | PDF text extraction limitations and OCR distinction. |
| S20 | [TinyFish API overview](https://docs.tinyfish.ai/) | Distinct Search, Fetch, Browser, and Agent surfaces. |
| S21 | [Firecrawl self-hosting guide](https://docs.firecrawl.dev/contributing/self-host) | Local deployment, dependency/feature limitations, cloud distinction. |
| S22 | [Firecrawl Compose source](https://raw.githubusercontent.com/firecrawl/firecrawl/main/docker-compose.yaml) | Supporting services and SearXNG search configuration. |
| S23 | [Docker Compose profiles](https://docs.docker.com/compose/how-tos/profiles/) | Optional service groups under one deployment. |
| S24 | [Docker port publication](https://docs.docker.com/engine/network/port-publishing/) | Host loopback publication versus container listener. |
| S25 | [Spider repository](https://github.com/spider-rs/spider) | Identity of the deferred Rust crawler candidate. |
| S26 | [Turso concurrent writes](https://docs.turso.tech/tursodb/concurrent-writes) | MVCC/BEGIN CONCURRENT and retry/conflict behavior. |
| S27 | [Turso compatibility document](https://raw.githubusercontent.com/tursodatabase/turso/main/COMPAT.md) | SQLite compatibility and FTS5 mismatch. |
| S28 | [OWASP SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html) | URL, DNS, network, and redirect safety implementation reference. |
| S29 | [SQLite backup API](https://sqlite.org/backup.html) | Supported database backup approach. |
| S30 | [QMD CLI implementation](https://raw.githubusercontent.com/tobi/qmd/main/src/cli/qmd.ts) | File indexing/deactivation and maintenance lifecycle. |
| S31 | [FastMCP background tasks](https://gofastmcp.com/servers/tasks) | Framework task integration versus DWS job ownership. |
| S32 | [Official MCP 2026-07-28 release](https://blog.modelcontextprotocol.io/posts/2026-07-28/) | Request-oriented protocol, continuation, catalog/extension direction. |
| S33 | [SQLite FTS5 documentation](https://sqlite.org/fts5.html) | Underlying lexical-search facility and direct-FTS alternative. |
| S34 | [QMD changelog](https://raw.githubusercontent.com/tobi/qmd/main/CHANGELOG.md) | Release review input; not a substitute for pinned-build verification. |
| S35 | [SQLite isolation](https://sqlite.org/isolation.html) | Readers, serialized writers, and transaction visibility. |
| S36 | [SQLite pragmas](https://sqlite.org/pragma.html) | Connection settings and durability configuration. |
| S37 | [SQLite is serverless](https://sqlite.org/serverless.html) | Embedded file database versus database service. |
| S38 | [SQLite transactions](https://sqlite.org/lang_transaction.html) | Transaction/lock behavior. |
| S39 | [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Framework alternative and upstream identity. |
| S40 | [QMD package manifest](https://raw.githubusercontent.com/tobi/qmd/main/package.json) | Runtime/native dependency footprint. |

### Reference definitions

[S01]: https://gofastmcp.com/getting-started/installation
[S02]: https://github.com/PrefectHQ/fastmcp/releases
[S03]: https://pypi.org/project/fastmcp/
[S04]: https://modelcontextprotocol.io/specification/2026-07-28/server/tools
[S05]: https://modelcontextprotocol.io/specification/2026-07-28/server/resources
[S06]: https://raw.githubusercontent.com/tobi/qmd/main/README.md
[S07]: https://raw.githubusercontent.com/tobi/qmd/main/src/index.ts
[S08]: https://raw.githubusercontent.com/tobi/qmd/main/src/store.ts
[S09]: https://sqlite.org/wal.html
[S10]: https://raw.githubusercontent.com/tobi/qmd/main/src/db.ts
[S11]: https://aiosqlite.omnilib.dev/en/stable/
[S12]: https://docs.crawl4ai.com/core/quickstart/
[S13]: https://raw.githubusercontent.com/unclecode/crawl4ai/main/docker-compose.yml
[S14]: https://docs.searxng.org/dev/search_api.html
[S15]: https://docs.searxng.org/admin/installation-docker.html
[S16]: https://github.com/deedy5/ddgs
[S17]: https://www.python-httpx.org/async/
[S18]: https://trafilatura.readthedocs.io/en/latest/
[S19]: https://pypdf.readthedocs.io/en/stable/user/extract-text.html
[S20]: https://docs.tinyfish.ai/
[S21]: https://docs.firecrawl.dev/contributing/self-host
[S22]: https://raw.githubusercontent.com/firecrawl/firecrawl/main/docker-compose.yaml
[S23]: https://docs.docker.com/compose/how-tos/profiles/
[S24]: https://docs.docker.com/engine/network/port-publishing/
[S25]: https://github.com/spider-rs/spider
[S26]: https://docs.turso.tech/tursodb/concurrent-writes
[S27]: https://raw.githubusercontent.com/tursodatabase/turso/main/COMPAT.md
[S28]: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html
[S29]: https://sqlite.org/backup.html
[S30]: https://raw.githubusercontent.com/tobi/qmd/main/src/cli/qmd.ts
[S31]: https://gofastmcp.com/servers/tasks
[S32]: https://blog.modelcontextprotocol.io/posts/2026-07-28/
[S33]: https://sqlite.org/fts5.html
[S34]: https://raw.githubusercontent.com/tobi/qmd/main/CHANGELOG.md
[S35]: https://sqlite.org/isolation.html
[S36]: https://sqlite.org/pragma.html
[S37]: https://sqlite.org/serverless.html
[S38]: https://sqlite.org/lang_transaction.html
[S39]: https://github.com/modelcontextprotocol/python-sdk
[S40]: https://raw.githubusercontent.com/tobi/qmd/main/package.json

---

## 29. Final implementation brief

Build **Deep Web Search (DWS)** as a personal local evidence-acquisition and retrieval service, delivered through **one Docker Compose project**. Use **FastMCP** for the MCP adapter, with the exact release verified rather than assumed. Expose a small provider-neutral capability surface and a daemon-backed CLI.

Use **SearXNG** for primary discovery, a tested **DDGS** fallback, a cheap deterministic acquisition path, and **Crawl4AI** for browser work. Keep **Firecrawl self-hosted**, **TinyFish**, and **Spider** optional until each demonstrates a specific benefit and satisfies policy.

Use **DWS-owned SQLite** for jobs, metadata, provenance, retention, and publication/index coordination; **normalized artifact files** as preserved evidence and rebuild input; and **QMD's own SQLite/FTS-backed lexical search** as the only document-search subsystem. Do not add DWS tables to QMD, generate default embeddings, or migrate to Turso without a measured reason.

Centralize shared-store ownership. Bound concurrent reads and browser work, serialize QMD updates, keep metadata transactions short, and make jobs recoverable. Distinguish capture availability from index readiness. Return small structured results, source excerpts, and immutable artifact references; do not inject whole crawls into model context.

Keep research planning, interpretation, synthesis, and report writing in **host agents and skills**, with project-specific methodology. DWS supplies evidence and enforces operational policy; it does not decide what a company is worth, whether a research thesis is complete, or what conclusion a report should reach.

**The design succeeds when the owner can reuse reliable, inexpensive, traceable web capabilities everywhere—without inheriting an agent framework, a permanent vector-indexing workload, or an enterprise operations stack.**

---

*End of DWS PRD v1.0. Update the decision records when the implementation or accepted requirements change.*
