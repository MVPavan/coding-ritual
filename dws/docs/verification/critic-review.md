# Whole-product critic audit — 2 October 2026

## Review scope and current verdict

The owner requested fresh independent GPT-6.1 reviews at `xhigh`, covering
every product layer and reporting every confirmed Important and Minor issue.
Each completed review was followed by corrections, applicable verification,
and a new critic. The loop finished with the **tenth complete critic: CLEAN=true,
zero Important and zero Minor findings**. All **forty-eight findings** from
rounds 1–9 have corrections and evidence below. The final five-group
qualification passed against the same reviewed and deployed product.

**Current verdict: vision achieved at the documented product scope.** Earlier
rounds and their pending/blocked verdicts below describe historical candidates.
Final result annotations were added after the clean review; runtime, active
tests, build and deployment inputs remain unchanged.

Review includes untracked runtime source, contracts, CLI/API/MCP, providers,
outbound policy, evidence and location mappings, scopes, retrieval and index
recovery, durable jobs, concurrency, storage/retention, backup/restore, startup,
Docker/Compose, dependency preparation, packaging, user documentation, tests,
and actual verification receipts. Documented product limits remain part of the
[goal](../product-goal.md).

Two Codex CLI launches failed before a model session initialized. They are
infrastructure failures, not reviews. Fresh native critics use the requested
`gpt-6.1-sol` model and `xhigh` reasoning. Startup evidence is under
`.runtime/critic-review/round-1/`.

## Round 1: all eleven findings

The complete condensed report is `.runtime/critic-review/round-1/review.md`.
The critic returned **issues found**, with five Important and six Minor defects.

| ID | Severity | Confirmed defect | Correction exercised in product scenarios |
|---|---|---|---|
| FC1 | Important | Interrupted FTS replacement can leave an empty index falsely ready | Commit pending/outbox intent before index mutation; kill, restart, inspect pending state, recover exact scoped hits |
| FC2 | Important | Truncated link discovery can report an exhausted successful crawl | Persist discovery limitation with captures; continue admitted work and report partial outcomes; migrate and restore legacy jobs |
| FC3 | Minor | HTML base URLs ignored | Resolve valid HTML bases and retain policy checks; actual relative/absolute/private-base fixtures |
| FC4 | Minor | Equivalent fetch aliases miss cache | Validate one canonical fetch identity before lock, cache and acquisition; concurrent aliases share a capture |
| FC5 | Minor | Accepted offsets overflow SQLite integers | Bound pagination inputs to signed 64-bit offsets; API/CLI rejection before effects |
| FC6 | Important | Interrupted capture files consume quota but evade GC | Reconcile strictly owned unreferenced capture/staging trees; real interruption, dry-run/apply accounting and pinned-evidence preservation |
| FC7 | Important | Canonical expansion can persist invalid jobs and poison the queue | Validate before acknowledgement; isolate malformed persisted jobs, preserve progress and continue healthy work |
| FC8 | Important | Interrupted automatic token publication can admit an empty credential | Fully write/fsync private staging, atomically publish, validate existing tokens and fail closed; actual interrupted/concurrent host starts |
| FC9 | Minor | Padded and spaced HTML links silently disappear | Normalize HTML URL values before strict validation; acquire the encoded PDF URL and verify exact evidence |
| FC10 | Minor | Deep bounded JSON escapes structured admission | Normalize decoder recursion failures before dispatch; actual protected HTTP rejection and healthy subsequent request |
| FC11 | Minor | Concurrent status reads can contradict the manifest and end pagination early | Read counts, pages and pagination from one SQLite transaction; actual paged polling during job progress |

## Round 2: all thirteen findings

This critic completed the entire review and returned **issues found**: nine
Important and four Minor defects. Six corrections had source and primary
execution evidence during the review; the other seven required subsequent
verification. Its complete condensed report is
`.runtime/critic-review/round-2/review.md`. All thirteen findings are listed.

| ID | Severity | Confirmed defect | Owning correction and verification scope |
|---|---|---|---|
| R2-1 | Important | Crawl admission source-validation timeout escapes as raw 500 | Structured source timeout before admission, preserving a concurrently durable acknowledgement; actual protected HTTP/replay journey |
| R2-2 | Important | A dotted directory seed broadens same-path crawl scope | Preserve the explicit directory slash; actual versioned-directory fixture with an off-scope observer |
| R2-3 | Minor | Historical QMD helper builds a bare generic image as an application | Retire that helper with explicit exit 2 and route installation to the current setup command |
| R2-4 | Important | Isolated build backend is unconstrained by the runtime lock | Pin the backend and its build dependency closure through uv build constraints; fresh empty-cache wheel resolution |
| R2-5 | Important | Known NAT64 aliases bypass direct HTTP address policy | Reject known translation prefixes; real fetch/crawl rejection and no admission; no live-translator exploit claim |
| R2-6 | Important | Crawl redirects can acquire and retain documents outside scope | Check static redirects before destination requests and rendered final URLs before retention; public browser navigation may already have occurred |
| R2-7 | Important | Unescaped SQLite file URIs misinterpret legal state paths | Encode path URIs consistently; actual state paths containing query/fragment/percent characters with exact retrieval and restore |
| R2-8 | Important | Host and worker state can be readable by other local users | Central owner-state validation and private root permissions for every startup route; actual explicit-token/worker/concurrent starts |
| R2-9 | Minor | Missing original artifacts escape export/backup as unstructured errors | Validate raw artifacts through the owning loader; structured unavailable/integrity errors, output cleanup and repair through a verified backup |
| R2-10 | Important | Copied artifacts are not all fsynced before backup/restore acknowledgement | Durable tree copy with file/directory/parent sync ordering; failure injection and pinned restoration into empty state |
| R2-11 | Minor | Large JSON integers raise unhandled decoder ValueError | Normalize only JSON decoder failures; authenticated/unauthenticated actual HTTP and CLI rejection with healthy subsequent reads |
| R2-12 | Minor | Arbitrary Page headings invent PDF locations or overflow integer conversion | Explicit generated PDF page offsets; real HTML long headings and genuine multipage-PDF mappings |
| R2-13 | Important | Heading mapping allocates quadratic suffix lists | Linear heading stack; large real source capture, exact section locations and bounded scaling evidence |

## Round 3: all six findings

The third fresh critic completed the full audit and returned **issues found**:
two Important and four Minor defects. Its complete condensed report is
`.runtime/critic-review/round-3/review.md`, anchored to the fourteen independently
checked hashes in `.runtime/critic-review/round-3-baseline.json`.

| ID | Severity | Confirmed defect | Correction and acceptance scope |
|---|---|---|---|
| R3-1 | Important | Heading regex backtracking grows about eightfold when internal whitespace doubles | Linear prefix/title parsing; real whitespace-heavy plaintext capture within deadline, exact reads and subsequent ordinary operation |
| R3-2 | Important | Twenty failed index events permanently starve a healthy later capture | Rotate only the matching failed durable event behind waiting work; actual worker indexes the healthy capture while damaged events remain |
| R3-3 | Minor | Valid JSON with malformed backup-manifest shapes escapes as AttributeError | Validate objects, file keys and digests before mutation; actual invalid-backup cases preserve pins, jobs and state |
| R3-4 | Minor | Deep provider JSON escapes as RecursionError | Structured provider decoder failure; actual HTTP renderer/search fixture and retained reads afterwards |
| R3-5 | Minor | Accepted retrieval terms after the thirty-second are silently omitted | Search every term within the existing 512-character budget; actual scoped API/CLI/MCP late-term checks |
| R3-6 | Minor | NAT64 wording overstates browser prefix policy | Explain direct URL prefix denial and browser public-alias behavior accurately; no private reachability defect established and browser code unchanged |

The expanded **16:55:19–16:57:31 UTC** full run was **failed**, with nine core
passes and one failure; the rendered, live/MCP, and operations groups passed.
The new dense-document fixture sought a section beyond its configured retained
text limit. The fixture's owner text budget was corrected, and its targeted
scenario then passed. A failed run is preserved as failed in
`.runtime/verification/20261002T165519Z-3270150/summary.json`; it is not final
product acceptance. Its installed-source snapshot remains valid baseline
evidence for this review.

## Round 4: all six findings

The fourth fresh critic completed the entire review and returned **issues found**:
one Important and five Minor defects. Its complete condensed report is
`.runtime/critic-review/round-4/review.md`, tied to the forty-five frozen inputs
in `.runtime/critic-review/round-4-candidate.json` and the installed wheel below.
The subsequent corrections are outside that verdict.

| ID | Severity | Confirmed defect | Correction and actual regression scope |
|---|---|---|---|
| R4-1 | Important | Discarded HTTP charset silently corrupts normalized evidence | BOM/validated HTTP charset/inference precedence with decoder provenance; real UTF-8/meta, BOM, Latin-1, unknown-label and rendered-DOM fixtures verify exact text, hashes and cited reads |
| R4-2 | Minor | Rendered HTML fallback reports raw-Markdown provenance | Select identity from the adopted transformation; actual missing-Markdown fallback and ordinary Markdown paths, exact raw retention and export |
| R4-3 | Minor | Invalid UTF-8 token files escape CLI JSON errors | Bounded nonsecret authentication failure; installed console script, no request, restored credential and exact pinned reads |
| R4-4 | Minor | Malformed API ports escape CLI URL validation | Validate parsed ports including zero; installed CLI rejects four bad port cases without HTTP traffic and then reads healthy evidence |
| R4-5 | Minor | Deep API JSON escapes CLI response decoding | Normalize decoder recursion failure; actual 28 KB response fixture returns structured error and ordinary reads remain exact |
| R4-6 | Minor | Accepted retention exceeds UTC timestamp serialization limits | Validate Settings before startup and expiry before publication; actual API/worker invalid-start rejection before state, normal startup and pinned evidence |

Charset scenarios reproduced the original corruption against unchanged pre-fix
sources and passed after correction. Their two actual research/provider journeys
passed in **25.961 seconds**; `.runtime/source-charsets/summary.json` records
both outcomes. The installed CLI/startup journey passed in **10.87 seconds**,
with primary receipt `.runtime/host-startup-tests/journey-g5wvtq9p/receipt.json`.
The current corrected candidate is frozen in
`.runtime/critic-review/round-5-candidate.json`. The fresh four-group run below
passed. The fifth independent critic found two additional mapping defects below;
final acceptance remains pending.

## Round 5: all two findings

The fifth fresh critic completed every product level and returned **issues
found**: one Important and one Minor defect. Its complete condensed report is
`.runtime/critic-review/round-5/review.md`, bound to the forty-five-input
round 5 manifest and independently verified installed wheel.

| ID | Severity | Confirmed defect | Correction and regression scope |
|---|---|---|---|
| R5-1 | Important | Fenced shell comments become section headings and silently omit instructions from named reads | Track backtick/tilde fence type and length, preserving offsets and hierarchy; actual HTML/Markdown named reads with code, subsequent instructions and real boundaries |
| R5-2 | Minor | Literal or escaped trailing hashes disappear from section titles | Strip only a whitespace-separated optional closing hash delimiter; actual C#, escaped terminal hash and optional delimiter reads |

Failures were reproduced through the actual API using the unchanged round 5
installed package. The Install assertion failed because its response contained
only the heading and opening fence. The fixed full research journey passed in
**28.521 seconds**, including representative short/mismatched/content-trailing
fences and exact scoped retrieval. Before/after primary receipts are in
`.runtime/source-section-boundaries/summary.json`. The owning changes follow
the [CommonMark fence and heading delimiter rules](https://spec.commonmark.org/0.31.2/)
for these cases; representative checks do not prove full parser conformance.
Both corrections are implemented. Current inputs are frozen in
`.runtime/critic-review/round-6-candidate.json`; renewed four-group qualification
passed below. The sixth fresh critic found the six additional defects recorded
next.

## Round 6: all six findings

The sixth fresh critic completed all product levels and returned **issues
found**: four Important and two Minor defects. Complete condensed report:
`.runtime/critic-review/round-6/review.md`. Formatted title unescaping was
considered and excluded because the contract exposes raw normalized Markdown
names; all six confirmed findings are retained.

| ID | Severity | Confirmed defect | Owning correction and actual verification |
|---|---|---|---|
| R6-1 | Important | Direct and browser classifiers accept site-local/reserved IPv6; browser also admits multicast | Explicit classifications in both predicates, preserving recognized public aliases; safe literal-only before proofs, deployed pure predicate checks, real protected fetch/crawl denials, fresh browser transport qualification pending |
| R6-2 | Important | Compose silently omits owner resource/retention controls | Optional forwarding of fourteen bounds plus DDGS to both consumers without duplicating defaults; real shell/env-file rendered configuration before/after, selected runtime environment proof in operations |
| R6-3 | Important | Empty headings leak another section or invent a phantom name | Real Markdown block boundaries independent of selectable titles; actual empty-heading exact reads and no phantom sections |
| R6-4 | Important | Ordinary Setext headings lack names and boundaries | Locked markdown-it-py block parser, retaining original text/offsets and raw title spelling; actual single/multiline Setext hierarchy and fenced-code cases |
| R6-5 | Minor | Malformed CLI hosts/control characters escape structured errors | Early raw URL validation plus InvalidURL handling; real installed CLI failure/recovery journey |
| R6-6 | Minor | Standalone ignores rely on parent repository | Local environment/bytecode/scratch patterns; isolated Git repository confirms product-only ignores |

The research/access pair passed in **36.413 seconds** after an actual unchanged
source Setext failure; `.runtime/source-setext-boundaries/summary.json` records
both. Old unsafe IPv6 acceptance was proven with literal validation only, without
HTTP/TCP/DNS calls. Fixed API fetch/crawl deny all four IPv6 targets and both
multicast targets while preserving state and exact healthy reads.
`.runtime/ipv6-policy-fix/deployed-browser-after.json` records the actual rebuilt
classifier and legitimate alias controls; internal reachability is not claimed.
The broker SHA-256 changed to
`d6594b6a639b5f857fedb88af06f78a691cf9a9597f2c42a59d5bbf158e365eb`;
manager hash and Crawl4AI/Playwright versions remain unchanged. Historical
transport receipts no longer establish this broker's complete qualification;
the expanded real matrix is being rerun. Current full verification adds its
`browser_policy` group to the previous four groups.

Compose before/after records are in `.runtime/compose-owner-limits/`;
standalone ignore proof is `.runtime/standalone-ignore-fix/receipt.json`.
Corrections are implemented. The installed CLI host journey passed in **10.21
seconds**, with sixteen check groups and primary receipt
`.runtime/host-startup-tests/journey-ouau8dfi/receipt.json`. All twenty-five
active runtime/test/overlay Python files passed Ruff lint/format and strict mypy;
shell syntax and whitespace passed. The corrected forty-nine-input candidate is
frozen in `.runtime/critic-review/round-7-candidate.json`. Its complete five-group
qualification and seventh fresh independent critic are running; acceptance
remains pending.

## Round 7: all one finding

The seventh fresh GPT-6.1/xhigh critic completed its whole-product scan and
returned **BLOCK, CLEAN=false**: one Important finding and no additional
confirmed Minor finding. Complete report:
`.runtime/critic-review/round-7/review.md`. Independent wheel, candidate and
browser-source binding is in its `independent-binding.json`.

| ID | Severity | Confirmed defect | Owning correction and required qualification |
|---|---|---|---|
| R7-I1 | Important | Browser plain-HTTP proxy loses IPv6 brackets in broker validation and forwarded Host | Extend the exact source-hash/context-bound overlay to the audited proxy; preserve brackets in both authorities, policy and pinning; unchanged mapped-public plus actual global HTTP/global HTTPS/mapped HTTPS controls in the 86-case matrix |

This correction is implemented. All forty-five findings across seven full
critics now have source corrections; fresh five-group execution and a new
independent whole-product verdict are required before final acceptance.
The proxy's audited original SHA-256 is
`2a3ddbef47289dcf4d093cb8f87cf142a6da81e9496b81e545d5e4346727d987`.
The original failed case remains recorded below.

## Round 8: all two findings

The eighth fresh GPT-6.1/xhigh critic completed the exhaustive scan and
returned **BLOCK, CLEAN=false**: one Important and one Minor finding.
Complete report and independent bindings:
`.runtime/critic-review/round-8/review.md` and
`.runtime/critic-review/round-8/qualification-extraction.json`.

| ID | Severity | Confirmed defect | Owning correction and real regression scope |
|---|---|---|---|
| R8-I1 | Important | Unsupported HTTP 206 range fragments and HTTP 226 delta representations are accepted as full sources/provider responses; crawling can falsely succeed and discovery can appear empty | One explicit rejection at direct-source, provider-transport and rendered-main status admission, before decoding/retention; real static formats/delta patches, provider and renderer cases, API/CLI, durable failed/mixed crawls, no rejected snapshots and healthy reads |
| R8-M1 | Minor | Preparation only enables the MCP extra for lowercase true while API accepts case variants | Normalize the preparation flag exactly as API does; five fresh locked generic-image environments for true/TRUE/True/false/unset, actual API/MCP or optional-package absence |

Both source corrections are implemented. Across eight full critics, all
forty-seven findings have source corrections. The expanded real access/provider
journey passed in **11.008 seconds**. Its primary receipt is
`.runtime/product-tests/journey-2jd86g71/partial-response-receipt.json`;
before/fixed bindings are in `.runtime/partial-response-regression/summary.json`.
Static, provider and rendered HTTP 206/226 fail before publication. The mixed
crawl retains its healthy seed, returns a partial outcome with two failed pages,
and publishes neither fragment; incomplete discovery fails explicitly.

All five actual fresh MCP preparation/startup cases passed. Primary receipt:
`.runtime/mcp-prepare-regression/fixed-all-five/receipt.json`. Enabled cases list
all seven tools; false/unset omit FastMCP and return MCP 404 with healthy API.
Copied cache links stay within owned state, all five containers are removed,
and the main manifest/lock are unchanged. Ruff lint/format, strict mypy across
all twenty-five Python files, shell syntax and Git whitespace pass.

The corrected candidate is ready for renewed five-group qualification and a
fresh ninth critic. The prior passing full run remains baseline evidence rather
than current final acceptance.

The Important finding was independently reproduced against real local HTTP
fixtures and real Engine/jobs. HTTP 206 retained a prefix, HTTP 226 retained an
actual GNU diff-e patch, and provider HTTP 206 returned a valid nested JSON
fragment that silently removed a discovery result. No Range, A-IM or conditional
base request was made. Protocol references:
[RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#name-206-partial-content)
and [RFC 3229](https://www.rfc-editor.org/rfc/rfc3229.html#section-10.4.1).
Independent receipts and probes are preserved under the round 8 report directory;
author API/CLI/worker proofs are under `.runtime/partial-response-regression/`.
Actual offline generic-image preparation/startup before-fix and lowercase control
proofs are under `.runtime/mcp-prepare-regression/`.

## Round 9: all one finding

The ninth fresh GPT-6.1/xhigh critic completed the whole-product audit and
returned **BLOCK, CLEAN=false**: zero Important findings and one Minor finding.
Complete report and independent bindings:
`.runtime/critic-review/round-9/review.md` and
`.runtime/critic-review/round-9/primary-binding.json`.

| ID | Severity | Confirmed defect | Owning correction and real regression scope |
|---|---|---|---|
| R9-M1 | Minor | Capture write or fsync failure rolls back correctly but escapes the shared structured error envelope as plain-text HTTP 500 | Preserve rollback and classify publication OSError at Store: no-space/quota disk_pressure507, other artifact_write_failed500; sanitized API internal_error500 fallback; four real API/installed CLI failure phases, clean metadata/artifacts, preserved pinned reads and healthy recovery |

All forty-eight findings across nine complete critics have source corrections.
The original independent ENOSPC probe is preserved under the round 9 directory.
The author's original real API/installed CLI failures are in
`.runtime/capture-io-regression/before-product.json`: ENOSPC during write, EIO
at file fsync, EDQUOT after rename at artifact-parent fsync, and an unclassified
RuntimeError. All returned plain-text500 and CLI invalid_response; cleanup and
retained evidence were intact. The corrected actual access/provider journey
passed in **12.723 seconds**. Primary receipt:
`.runtime/product-tests/journey-q62dpn64/capture-io-receipt.json`;
before/fixed binding: `.runtime/capture-io-regression/final-summary.json`.
All four API/installed CLI phases returned the expected sanitized JSON code,
left metadata and artifact trees unchanged, preserved pinned exact reads, and
recovered with exact artifact hashes after faults were removed. All twenty-five
Python files pass Ruff lint/format and strict mypy; shell syntax also passes.
Production contains no test fault hook. A fresh whole-product critic and full
five-group qualification are still required; current acceptance is withheld.

## Round 10: no findings — review loop complete

The tenth fresh independent GPT-6.1/xhigh critic completed the entire audit and
returned **CLEAN=true: Important 0, Minor 0**. It found no deferred confirmed
issue and used no top-N cutoff. Complete report:
`.runtime/critic-review/round-10/review.md`; final content-hash binding:
`.runtime/critic-review/round-10/final-binding.json`.

All production layers, current tests/helpers, deployment, packaging, documents
and retained qualification tooling were inspected. The critic independently
bound all **fifty-nine frozen inputs**, all fifteen source/wheel/installed
payloads, every wheel RECORD row, both deployed consumers, and actual protected
browser module identities. It recalculated the raw five-group receipts,
browser assertions and twelve mutations, DNS/observer/QUIC/launch controls,
rendered hashes, five prepared MCP cases, and fresh capture-I/O recovery hashes.

An independent bounded synthetic probe exercised actual Store, shared Engine
and in-memory FastMCP Client. ENOSPC, EIO, post-rename EDQUOT and unclassified
failures preserved metadata/artifact trees and exact pinned reads, masked
private error details, and recovered after fault removal. A rejected
transactional callback rolled back metadata and its published tree. Receipt:
`.runtime/critic-review/round-10/publication-probe-receipt.json`. A stdlib control
isolated an initial sandbox local-IPC stall; the permitted bounded probe passed,
and owned stalled processes were stopped. No production source or service was
changed by the critic. The transport/extraction/platform/power-loss limits below
remain explicit; the clean verdict does not extend the documented scope.

## Actual verification evidence

### Round 10 final reviewed build — qualification and review passed

The complete five-group command ran at **20:14:25–20:20:54 UTC** on 2 October
2026 and passed every selected group. Primary summary:
`.runtime/verification/20261002T201425Z-4079616/summary.json`.

| Group | Actual result |
|---|---|
| Core integration | **10 passed**, zero failures/errors/skips; 119.927 seconds |
| Browser traffic policy | **86 of 86 passed**, all twelve malformed-receipt mutations rejected; zero forbidden traffic, DNS receipt or cleanup errors |
| Protected rendered fixture | Passed; retained artifacts/hashes and calibrated observer checked |
| Live public sources/MCP | Passed; all seven capabilities, retained resource and exact API/CLI/MCP parity |
| Installation and operation | Passed; independent wheel, locked upgrade, fifteen owner controls, consumer replacement, all five fresh MCP preparation/startup cases and no leftovers |

All fifty-one runtime/test/build/deployment inputs and eight reviewed document
hashes were unchanged through the final review. All fifteen source, independent
wheel, installed and deployed-consumer payloads match. Wheel SHA-256:
`865ec85ba073525d37f234a703f5b986ba373932deb7793e25a851f99038e712`.
Root extraction: `.runtime/critic-review/round-10-verification.json`;
independent binding: `.runtime/critic-review/round-10/primary-binding.json`.
Fresh full-run capture-I/O receipt:
`.runtime/product-tests/journey-ws3xrq2k/capture-io-receipt.json`.
The clean critic report completed at **20:40:39 UTC**. Only these final result
annotations follow that verdict; the qualified product inputs remain unchanged.

### Round 9 reviewed build — qualification passed, review blocked

The complete five-group command ran at **19:38:39–19:45:27 UTC** and passed all
selected groups. Primary summary:
`.runtime/verification/20261002T193839Z-3255142/summary.json`.

| Group | Actual result |
|---|---|
| Core integration | **10 passed**, zero failures/errors/skips; 122.592 seconds |
| Browser traffic policy | **86 of 86 passed**, twelve malformed-receipt mutations rejected; zero forbidden traffic, DNS receipt or cleanup errors |
| Protected rendered fixture | Passed |
| Live public sources/MCP | Passed; all seven operations and resource/API parity |
| Installation and operation | Passed; independent wheel, locked upgrade, owner controls, actual consumer replacement and all five fresh MCP preparation/startup cases |

All fifty runtime/test/build/deployment hashes and eight review document hashes
were unchanged. All fifteen source/wheel/installed payloads and every wheel
RECORD hash/size match. Wheel SHA-256:
`86726d3bddbb7c25e286c0903cb4f9316dfa2bda2a72fe0ef90277ec81879f7c`.
Root extraction: `.runtime/critic-review/round-9-verification.json`.
The critic independently recalculated the primary records, browser cases and
controls, module identities, candidate and package bindings. Its R9-M1 above
blocks acceptance despite this passing qualification. The subsequent correction
is outside that frozen verdict and requires renewed qualification and review.

### Round 8 reviewed build — qualification passed, review blocked

The complete five-group command ran at **18:54:50–19:01:06 UTC** and passed all
selected groups. Primary summary:
`.runtime/verification/20261002T185450Z-1887500/summary.json`.

| Group | Actual result |
|---|---|
| Core integration | **10 passed**, zero failures/errors/skips; 113.248 seconds |
| Browser traffic policy | **86 of 86 passed**, twelve malformed-receipt mutations rejected; zero forbidden traffic, DNS receipt or cleanup errors |
| Protected rendered fixture | Passed |
| Live public sources/MCP | Passed; all seven operations and resource/API parity |
| Installation and operation | Passed; independent wheel, locked upgrade, owner controls and actual consumer replacement |

All fifty runtime/test/build/deployment hashes and eight reviewed document hashes
were unchanged. All fifteen installed package payloads match. Wheel SHA-256:
`171cdee6ba65114278d63c995e7766a6df94124b91dcb03dd900cb26f8fccbbc`.
Browser broker/manager hashes match the previous run; the corrected proxy is
`4c00953a8406dd078fdac20c7d968e123a4bc8e4f4ab9f5f78629b90473c31ae`.
Root extraction is `.runtime/critic-review/round-8-verification.json`; the critic
independently reopened and recalculated the primary receipts, all case/sensitivity
assertions, module identities and package payloads. Its two further findings
above block acceptance despite this passing qualification.

### Round 7 reviewed build — qualification failed

The expanded complete entrypoint ran at **18:32:13–18:38:05 UTC**. Its five
selected groups recorded **four passes and one failure**; overall qualification
is **failed**. The primary summary is
`.runtime/verification/20261002T183213Z-1371312/summary.json`.

| Group | Actual result |
|---|---|
| Core integration | Passed |
| Browser traffic policy | **82 of 83 cases passed**; the public mapped-IPv4 literal HTTP control failed with HTTP 500; all denial controls passed and no forbidden traffic was recorded |
| Protected rendered fixture | Passed |
| Live public sources and MCP | Passed |
| Installation and operation | Passed, including all fifteen owner controls in both rendered Compose routes and actual consumer omission of unset values |

The browser receipt records eleven rejected receipt mutations, no DNS receipt
failures, and complete cleanup. Its broker SHA-256 is
`d6594b6a639b5f857fedb88af06f78a691cf9a9597f2c42a59d5bbf158e365eb`;
browser-manager SHA-256 is
`6f44b845b33553fe5640796c5e8a873647b7d4f9afedd7e120e49c7e7b6de9b6`.
The subsequent audit traced the public control failure to lost IPv6 brackets
in the plain-HTTP proxy. This run does not qualify that path.

All fifteen installed package members match the frozen forty-nine-input
round 7 candidate. Wheel SHA-256:
`171cdee6ba65114278d63c995e7766a6df94124b91dcb03dd900cb26f8fccbbc`.
The extraction `.runtime/critic-review/round-7-verification.json` explicitly
records two subsequent browser-helper changes, excluded from the frozen
verdict. Runtime and build inputs remained unchanged. The new helper controls
need fresh execution against the corrected proxy.

### Round 6 reviewed build

The complete command passed all four groups at **18:00:30–18:03:11 UTC**:
`.runtime/verification/20261002T180030Z-447611/summary.json`.

| Group | Actual result |
|---|---|
| Core integration | **10 passed**, zero failures/errors/skips; 107.973 seconds, including renewed charset, CLI and named-section scenarios |
| Protected rendered fixture | Passed; exact evidence, calibrated private-target observer and cleanup |
| Live public sources/MCP | Passed; static/PDF/rendered, installed CLI, all seven tools/resources, late-term query, exact read/offset parity and jobs |
| Installation/operation | Passed; isolated wheel, stopped-consumer locked dependency upgrade preserving pins/jobs, live preparation refusal and actual Compose replacement |

All forty-five candidate inputs remain unchanged; all fifteen installed package
members match `.runtime/critic-review/round-6-candidate.json`. The wheel SHA-256:
`19e8ded712d86cf7d5ab01d53efb3c03269a141c4daace04ffda92d9198bf881`.
Its installed sources are preserved under
`.runtime/verification/20261002T180030Z-447611/operations/run-3a380020c4dd/installed/source-not-required/dws/`.
Binding extraction: `.runtime/critic-review/round-6-verification.json`.
Ruff lint/format, strict mypy across all twenty-one Python files, shell syntax,
local Markdown links and Git whitespace passed. The sixth critic then found
the six defects above; this receipt binds the earlier reviewed baseline.

### Round 5 reviewed build

The complete entrypoint ran at **17:44:32–17:47:08 UTC** and **passed all four
groups**. Primary summary:
`.runtime/verification/20261002T174432Z-260962/summary.json`.

| Group | Actual result |
|---|---|
| Core integration | **10 passed**, zero failures/errors/skips; 103.265 seconds |
| Protected rendered fixture | Passed; exact evidence, private-target denial and calibrated observer, fixture cleanup |
| Live public sources and MCP | Passed; public static/PDF/rendered acquisition, installed CLI, all seven MCP tools/resources, late-term query and exact read parity |
| Installed product and operations | Passed; independent wheel without repository source/MCP, stopped-consumer locked dependency upgrade, preserved pin/job, live-prepare refusal and actual Compose replacement |

All forty-five runtime/test/build/deployment inputs matched at qualification
`.runtime/critic-review/round-5-candidate.json`; all fifteen installed package
members match its source hashes. The installed wheel SHA-256 is
`7dc37734c19deb739ed2a6c2c87f3f97f83219c34922f4a0c78f5a67ab53470f`.
Its preserved source is under
`.runtime/verification/20261002T174432Z-260962/operations/run-893e6e1342e9/installed/source-not-required/dws/`.
Qualification extraction is `.runtime/critic-review/round-5-verification.json`;
the critic independently reopened the primary receipts and verified the same
binding. Ruff lint/format and strict mypy across twenty-one Python files,
shell syntax, local documentation links and Git whitespace checks passed.
The fifth critic subsequently found the two mapping defects above. This
qualification binds its reviewed baseline, not later corrections.

### Round 4 reviewed build

The complete entrypoint ran at **17:15:51–17:18:12 UTC** and **passed all four
groups**. The authoritative receipt is
`.runtime/verification/20261002T171551Z-3417649/summary.json`:

| Group | Current result |
|---|---|
| Core integration | **10 passed**, zero failures/errors/skips; 88.636 seconds |
| Protected rendered fixture | Passed, including exact artifacts and calibrated private-network observer |
| Live public sources and MCP | Passed; static/PDF/rendered, installed CLI, all seven tools, exact resource/offset parity and the thirty-third query term |
| Installed product and operations | Passed; independent wheel, stopped-consumer dependency upgrade, exact retained pin/job, live-preparation refusal and actual Compose consumer replacement |

The round 4 installed wheel SHA-256 is
`bf3c3fa08092906dc4ce0db8b4271e458fb23047728f6ab7eea5949771158b85`.
Its preserved installed source is under
`.runtime/verification/20261002T171551Z-3417649/operations/run-15e992f35a9b/installed/source-not-required/dws/`.
All 45 frozen runtime/test/build/deployment input hashes matched at qualification
`.runtime/critic-review/round-4-candidate.json`; extracted qualification is in
`.runtime/critic-review/round-4-verification.json`.

Ruff lint/format, strict mypy across all 21 runtime/integration/E2E Python
files, shell syntax and Git whitespace checks passed. The fourth fresh critic
subsequently found the six defects above. This receipt qualifies its baseline;
the later corrected build requires fresh verification and independent review.

### Earlier reviewed build

The first expanded full entrypoint ran at **16:35:17–16:37:09 UTC** and passed
all four selected groups. Its receipt is
`.runtime/verification/20261002T163517Z-2678981/summary.json`:

- Core integration: **9 passed**, zero failures/errors/skips, 65.456 seconds.
- Actual protected rendered fixture: passed.
- Live public sources, installed CLI and all seven MCP tools: passed.
- Installed wheel, stopped-consumer dependency upgrade, retained pin/job,
  live-preparation refusal and Compose consumer replacement: passed.

That build precedes R2-7 through R2-13 corrections. It proves the reviewed
baseline and earlier corrections; it is not final qualification of later code.
Its installed wheel SHA-256 is
`7bcfeb85fbe8f97aa0f9c2425692002ce6492f7d2d3e5be7bd548a3503f551e7`.
The before/after crash and targeted scenario receipts are under
`.runtime/critic-fixes/`, with reproducible tests in `tests/integration/`.

All 21 runtime/integration/E2E Python files passed Ruff lint/format and strict
mypy before those later changes. The current-build checks above follow the
last source change.

Fresh empty-cache build evidence is
`.runtime/build-constraints-proof/receipt.json`. It resolved Hatchling 1.27.0,
packaging 26.3, pathspec 1.1.1, pluggy 1.6.0 and trove-classifiers
2026.9.21.13. The configuration uses the documented
[uv build constraints setting](https://docs.astral.sh/uv/reference/settings/#build-constraint-dependencies).

## Evidence limits

The original acceptance reused the historical 62-case transport matrix after
source/image checks. The round 7 run executed the expanded 83-case matrix
against the changed broker, preserving its failed public control explicitly.
The round 8 matrix then passed all 86 cases against the corrected proxy. This
proves the observed transport cases; further product corrections still require
qualification and fresh review. Rendered fixture
and private-subrequest scenarios are separate actual runs. Public browser navigation is checked against crawl scope
after navigation and before retention; pre-navigation path containment is not
claimed. Known NAT64 policy checks do not establish a live translator exploit.
Fsync ordering and injected failures are evidence of the implemented durability
protocol; SIGKILL does not simulate host power loss.

The original development window ended at **16:35:36 UTC**. This later audit
continues under the owner's subsequent explicit instruction to repeat fresh
reviews until a full critic reports no issues. All audit-controlled writes
remain inside this standalone product. Parent tracking state and unrelated
changes are preserved; no commit or push is authorized by this report.
