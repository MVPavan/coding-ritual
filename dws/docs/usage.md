# Install and operate DWS

DWS is a standalone evidence tool. Work from this directory, the one containing
`pyproject.toml`, `compose.yaml`, and `src/dws/`. Its source, configuration,
dependency cache, temporary files, and retained evidence stay here.

## Start the local product

The default deployment requires Docker with Compose and outbound public-web
access. The setup script uses host Python 3 only to generate local secrets.
The application runs on the pinned Debian Python 3.13 image.

```bash
scripts/setup.sh start
docker compose --env-file .runtime/owner.env ps
curl --fail http://127.0.0.1:8765/ready
```

`scripts/setup.sh init` prepares directories and credentials without starting
containers. Repeating setup preserves existing secrets and evidence; `start`
briefly stops the API and worker before preparing their environment again.
Only the DWS API publishes a host port, bound to `127.0.0.1:8765`.
SearXNG and Crawl4AI are private services on the Compose network.

| Service | Responsibility |
|---|---|
| `prepare` | Finite job: install the locked environment with uv before serving |
| `dws-api` | Authenticated command API; optional MCP adapter |
| `dws-worker` | Durable crawl execution and restart recovery |
| `searxng` | Public-web discovery; its own pinned image |
| `crawl4ai` | Browser acquisition; its own pinned protective overlay |

The DWS image contains Linux, Python, and uv. **No Python application packages
are installed during its build.** `prepare` runs `uv sync --locked --no-dev`
against mounted source and the lockfile. API and worker use that environment
without running package installation themselves.
Process locks refuse preparation while either consumer is running.

| Local path | Contents |
|---|---|
| `.runtime/owner.env` | Local API/provider tokens and Compose settings; mode 0600 |
| `.runtime/uv-cache/` | Reusable uv downloads and build cache |
| `.runtime/container-env/` | Linux container environment shared by API and worker |
| `.runtime/cache/`, `.runtime/state/`, `.runtime/config/` | Product-local XDG cache, state, and configuration |
| `.runtime/tmp/` | Product-local temporary files |
| `.state/` | Management SQLite, evidence artifacts, index, and backups |
| `.venv/` | Optional host environment; separate from the container environment |

These paths are ignored by Git. The uv cache is not the runnable environment.
The mounted cache uses copy mode because linking across distinct mounts is not
portable. Replacing containers preserves the bind-mounted state. Providers
cannot mount the evidence archive. The earlier QMD qualification build is
preserved in `docker/qualification.Dockerfile`; it is not the runtime image.

## Use the same evidence contracts

Load the generated owner settings in a trusted shell. Do not print or share
the tokens.

```bash
set -a
source .runtime/owner.env
set +a
```

The API accepts a JSON object at `POST /v1/<operation>`. A basic research journey:

```bash
curl --fail-with-body http://127.0.0.1:8765/v1/search \
  -H "Authorization: Bearer $DWS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"query":"Python asyncio documentation","limit":5}'

curl --fail-with-body http://127.0.0.1:8765/v1/fetch \
  -H "Authorization: Bearer $DWS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"url":"https://docs.python.org/3/library/asyncio.html","render":"never"}'

curl --fail-with-body http://127.0.0.1:8765/v1/retrieve \
  -H "Authorization: Bearer $DWS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"query":"event loop","limit":3,"max_chars":4000}'
```

Copy the snapshot handle returned by `fetch` or `retrieve` into a `read`
request. The handle identifies captured evidence, not the current live page.

For static HTTP captures, `fetch` reuses a compatible snapshot within
`max_age_seconds`. When it is stale and has an ETag or Last-Modified validator,
DWS conditionally requests the source through the normal safe acquisition path.
A 304 returns the same snapshot with `cached: true`, `revalidated: true`, and
`observed_at`; it records a new observation and run membership without changing
the original capture time, hashes, or artifact bytes. A 200 creates a new
snapshot. `--refresh` always downloads again, and sources without validators
download again when stale. Browser-rendered Crawl4AI captures are never
conditionally revalidated. An unsolicited 304 or a 304 reached through a
different redirect chain returns a typed error instead of reusing evidence.

```bash
curl --fail-with-body http://127.0.0.1:8765/v1/read \
  -H "Authorization: Bearer $DWS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"snapshot_id":"REPLACE_WITH_SNAPSHOT_ID","line_start":1,"line_end":30}'
```

`retrieve` returns `next_cursor` when another page is available. Send that
opaque value as `cursor` with the same query, workspace, run, crawl, document
scope, limit, and character budget (CLI: `retrieve --cursor`). An index update
or rebuild invalidates it (`stale_cursor`); malformed or changed-scope cursors
return `invalid_cursor`. The cursor is base64url encoded JSON containing an index
generation UUID, result offset, and SHA-256 digest of the request fields. The
cursor is HMAC signed with a separate 0600 server-only key in the DWS state
directory. The key is created atomically on first cursor use and is never
derived from the API bearer token. Backups omit this key; restoring into a new
state directory invalidates old cursors. Direct store use follows the same rule.
Previously issued bearer-signed cursors are invalidated by this change.
API authentication and workspace checks remain the access boundary.

Search defaults to TinyFish when `DWS_TINYFISH_API_KEY` is configured, then
falls back to SearXNG and DDGS. Without a key, the existing SearXNG/DDGS route
remains available. **Privacy:** every search query and its domain filters go to
TinyFish by default with a key; eligible blocked-source URLs also go to TinyFish
Fetch. Ordinary successful local fetches do not contact TinyFish. Set
`DWS_TINYFISH_ENABLED=false` to disable both, or
`DWS_TINYFISH_FETCH_ESCALATION=false` to disable only fetch escalation.

| Owner setting (also optional Compose environment keys) | Default |
|---|---|
| `DWS_TINYFISH_API_KEY` | Unset; secret, excluded from serialized settings |
| `DWS_TINYFISH_ENABLED` | `true`, effective only with a key |
| `DWS_TINYFISH_FETCH_ESCALATION` | `true` |
| `DWS_TINYFISH_FETCH_TTL` | `3600` seconds; `0` prefers live acquisition, maximum `31536000` |
| `DWS_TINYFISH_SEARCH_URL` | `https://api.search.tinyfish.ai/` |
| `DWS_TINYFISH_FETCH_URL` | `https://api.fetch.tinyfish.ai/` |
| `DWS_TINYFISH_SEARCH_PER_MINUTE` / `DWS_TINYFISH_SEARCH_PER_HOUR` | `30` / `500` requests |
| `DWS_TINYFISH_FETCH_PER_MINUTE` / `DWS_TINYFISH_FETCH_PER_DAY` | `150` / `1000` URLs |

Endpoints allow only their respective product host over HTTPS on port 443,
plus HTTP loopback test endpoints. Provider redirects are refused with
credentials attached. Keep the key in owner secret
configuration, never tool inputs. Quotas use rolling windows and atomic
reservations shared by API and worker in `data_dir/tinyfish-quota.sqlite3`.
Reservations count before HTTP, including failed calls. Server zero-remaining
and 429 signals add bounded cooldowns; exceeding either local window sends no
request. The quota database is disposable operational state, omitted from
application backups and evidence exports. Deleting it resets local accounting;
it does not reset provider usage. Use one shared state directory per key: other
applications/state directories using the key are outside DWS's accounting.
If validation or reservation leaves too little hosted time to send a request,
DWS skips it without spending a unit; any unused reservation is released.

Search `engine_path.attempts` lists providers in order up to the serving provider,
with short `reason` codes: `served`, `quota_minute`, `quota_hour`,
`server_cooldown`, `rate_limited`, `unavailable`, `auth_failed`,
`invalid_response`, `disabled`, or `not_configured`. Existing fields remain:
`provider`, DDGS `backend: auto`, `upstream_engines`, and
`failed_primary_engines`. SearXNG failure still emits `searxng_unavailable`;
DDGS fallback emits `fallback_upstream_independence_unverified` because DDGS
cannot identify its upstream. TinyFish's `date` is an unverified provider claim,
not a source observation; search results remain non-evidence. TinyFish gets up
to one quarter of `request_timeout`, capped at five seconds, leaving time for
fallback within the unchanged whole-search deadline.

Local HTTPX/Crawl4AI acquisition stays primary. Hosted Fetch is eligible only
for a public URL after `challenge_page`, `render_failed`, source HTTP
401/403/429/451 (static or rendered), or required rendering without Crawl4AI.
For missing local rendering, a skipped/failed escalation preserves the original
`render_unavailable`/503; `render_required` identifies only the internal trigger
and successful escalation warning.
`render=never`, private/allowed-private hosts, credential URLs, policy/scope
denials, size/empty-content failures, and whole-local-request timeouts never
escalate. Local acquisition keeps its full `request_timeout`; an eligible
completed failure opens an additional budget of `min(request_timeout, 25)`
seconds, measured against one absolute monotonic deadline. After public-address
validation and quota reservation, TinyFish's per-URL timeout uses the remaining
time minus HTTP headroom: 20% of the initial budget (minimum 100ms, maximum 1s).
If fewer than 100ms remain for the provider after headroom, no request is sent
and `provider_timeout` is reported without spending quota.
Crawls allow this per-page budget plus the bounded acquisition-slot wait when
escalation is enabled, but still obey their total job deadline and shared daily
quota. Failure or skip preserves the original local code/message and adds
`error.escalation` (crawl manifest: `escalation`), with
`provider: tinyfish` and a typed reason, including `quota_day`, `ineligible`,
or `scope_denied`. A per-URL `timeout` becomes `provider_timeout` (also used when
the hosted budget expires); `target_http_error` becomes `target_blocked`, with
`target_status` only for an integer HTTP status from 100 to 599. Other per-URL
failures become `unavailable`. Failed URLs still spend quota. Provider error
text is never returned.

When escalation is enabled, the acquisition allowance is
`A = min(5, request_timeout) + request_timeout + min(request_timeout, 25)`,
including slot admission. An equivalent fetch waits up to `A` for the stripe
lock, then can spend another `A` acquiring its page. The worst case is about
`2 * A`: 120 seconds at the default 30-second request timeout, or 300 seconds
at the maximum 120-second setting, plus storage/response overhead. The CLI
allows 360 seconds for fetch responses. API execution and MCP tools impose no
shorter operation timer; configure external HTTP/MCP read/tool timeouts to at
least 360 seconds. The installed FastMCP HTTP client's 300-second default is
too short for this upper bound; use `Client(url, timeout=360)`.

Hosted captures use `provider: tinyfish`, `normalizer: tinyfish/fetch-markdown/1`,
and `content_type: text/vnd.tinyfish.markdown`. They are weaker evidence:
`source.bin` and its raw hash cover the exact UTF-8 provider text, **not original
source bytes**, which are unavailable. Warnings include
`provider_text_only_original_bytes_unavailable`, `hosted_provider_acquisition`,
and `escalated_from_<local_error_code>`. `--refresh` / `refresh=true` sends hosted
`ttl: 0`; otherwise an explicitly supplied `--max-age` / `max_age_seconds` sets
the TTL, or the owner `DWS_TINYFISH_FETCH_TTL` applies when omitted. A positive
TTL adds `provider_cache_permitted`: `captured_at` is DWS's acquisition time,
and the hosted text may be a provider-cached copy up to the requested TTL in age.
It is not an observation of when the origin served those bytes. Final URLs are
canonicalized, validated as public, and checked against crawl scope after remote
navigation; remote intermediate redirects/subrequests cannot be attested by
local egress policy.
Hosted snapshots can be reused for `auto`/`always` while enabled, never for
`never`; only HTTPX snapshots support conditional revalidation.

The CLI prints the same JSON as the API and uses these exit classes:

| Exit | Class | Error codes / status |
|---|---|---|
| 0 | Success | No error |
| 2 | Usage | Argument parser errors |
| 3 | Policy denial | `policy_denied`, `scope_denied`, `local_access_only`, `authentication_required`, `challenge_page`, `invalid_url`, `api_redirect_denied` |
| 4 | Unavailable or capacity | `busy`, `acquisition_busy`, `retrieval_busy`, `store_busy`, `queue_full`, `provider_unavailable`, `search_unavailable`, `render_unavailable`, `api_unavailable`, `source_unavailable`, `artifact_unavailable`, `backup_unavailable`, `dns_failed`, `source_timeout`, `provider_timeout`, `request_timeout`, `disk_pressure`, `storage_limit`; HTTP 429, 503, 507 |
| 1 | Other failure | All remaining errors, including not found, malformed input, and invalid or stale cursor |

For browser-rendered content, set `render` to `always`. With `auto`, acquisition
decides whether the static result needs browser fallback and reports its route.
`never` is useful for predictable direct HTTP acquisition.

```bash
curl --fail-with-body http://127.0.0.1:8765/v1/crawl \
  -H "Authorization: Bearer $DWS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"seed_url":"https://docs.python.org/3/library/asyncio.html","scope":"same_path","max_pages":10,"max_depth":1,"max_seconds":120,"idempotency_key":"asyncio-example"}'
```

Use the returned `job_id` in `job_status` and `job_cancel`. Crawl submission is
durable; request completion does not mean the worker has finished. Reusing the
same idempotency key with the same request returns the acknowledged job.
Cancellation preserves committed snapshots and reports unfinished work.

Each data operation defaults to workspace `default`. Use `workspace_create`
and `run_create`, then supply their returned IDs to keep projects and research
runs separate. Discovery results are source candidates; acquire a source before
citing its contents. DWS returns evidence; the caller judges and interprets it.

| Operations | Use |
|---|---|
| `search`, `fetch`, `crawl` | Discover and acquire public evidence |
| `retrieve`, `read` | Find passages and read exact retained captures |
| `job_status`, `job_cancel` | Inspect and control durable jobs |
| `workspace_create`, `workspace_list`, `run_create`, `run_list` | Organize and inspect project/run scope |
| `pin`, `export`, `expire`, `gc` | Retain, export, and explicitly remove evidence |
| `index_status`, `index_rebuild`, `diagnostics` | Inspect and repair local operation |
| `backup`, `restore` | Preserve and recover application data |

Requests are closed schemas: misspelled or unsupported fields are rejected.
An owner sets `DWS_*` resource limits; callers cannot raise those limits.
Use the installed `dws --help` for CLI commands and argument shapes.

For the standard Compose deployment, put owner settings in `.runtime/owner.env`
or export them before `scripts/setup.sh start`. Both API and worker receive
`DWS_MAX_BYTES`, `DWS_MAX_TEXT_CHARS`, `DWS_MAX_OUTPUT_CHARS`,
`DWS_MAX_RESPONSE_BYTES`, `DWS_REQUEST_TIMEOUT`, `DWS_MAX_PAGES`, `DWS_MAX_DEPTH`,
`DWS_MAX_CRAWL_SECONDS`, `DWS_MAX_JOBS`, `DWS_ACQUISITION_SLOTS`,
`DWS_MAX_STORAGE_BYTES`, `DWS_MIN_FREE_BYTES`, `DWS_RETENTION_SECONDS`,
`DWS_LEASE_SECONDS`, and optional `DWS_DDGS_ENABLED`. Unset controls use the
application's validated defaults; invalid values fail startup. Compose keeps
container paths, internal provider routing and private-target policy fixed.

Named sections use the exposed normalized Markdown title, including its literal
inline formatting or escapes. CommonMark block parsing identifies ATX and Setext
headings and fenced code; empty headings end sections without selectable names.
Line and character locations still refer to the exact retained text. Older
snapshots keep their original immutable maps; refresh a source for corrected
mapping behavior. Block mapping uses the locked
[markdown-it-py parser](https://markdown-it-py.readthedocs.io/en/latest/using.html).

## Host CLI or separate providers

The CLI does not require a host agent, the surrounding repository, Node, QMD,
or MCP. With uv installed, prepare an independent host environment:

```bash
scripts/setup.sh init
export UV_CACHE_DIR="$PWD/.runtime/uv-cache"
export UV_PYTHON_INSTALL_DIR="$PWD/.runtime/python"
export UV_PROJECT_ENVIRONMENT="$PWD/.venv"
export TMPDIR="$PWD/.runtime/tmp"
uv sync --locked --no-dev
uv run --no-sync dws --help
```

The host environment needs Python 3.13 or later; uv may download it into the
configured product-local Python directory. Use `uv run --no-sync` after
preparation to avoid changing an environment while a host service uses it.
Set `DWS_DATA_DIR` to a product-local directory when running a host API or worker.
`DWS_SEARXNG_URL`, `DWS_CRAWL4AI_URL`, and `DWS_CRAWL4AI_TOKEN` configure separate
providers. The standard Compose values use private service DNS names and are
not host URLs. Direct static/PDF acquisition works without the browser service;
browser-required pages report provider unavailability when it is absent.

## Optional MCP

Set `DWS_MCP_ENABLED=true` in `.runtime/owner.env`. Stop the API and worker,
prepare the locked `mcp` extra, and restart both as described below. The
authenticated Streamable HTTP endpoint is `http://127.0.0.1:8765/mcp/` with the
same bearer token. MCP is a thin adapter over the same engine and stored handles.
The default CLI works without the extra installed. Preparation and API startup
interpret the enable value consistently: `true`, `TRUE`, and `True` enable it;
`false` or an unset value leaves it disabled.

## Locked upgrades and restart

Changing source does not require rebuilding the generic image. Updating Python
dependencies requires updating the lockfile and preparing the shared environment
while its consumers are stopped. Do not run installation inside a serving API
or worker container.

```bash
docker compose --env-file .runtime/owner.env stop dws-api dws-worker
# Edit pyproject.toml if needed, then update a deliberate dependency selection.
UV_CACHE_DIR="$PWD/.runtime/uv-cache" \
  UV_PYTHON_INSTALL_DIR="$PWD/.runtime/python" \
  TMPDIR="$PWD/.runtime/tmp" uv lock --upgrade-package httpx
docker compose --env-file .runtime/owner.env run --rm --no-deps prepare
docker compose --env-file .runtime/owner.env up -d --no-deps dws-api dws-worker
```

To enable MCP without upgrading dependencies, skip the lock update; the optional
extra is already locked. If preparation fails, leave API and worker stopped,
correct the dependency problem, and rerun preparation. Changing Linux/Python/uv
or provider image versions requires rebuilding or pulling the relevant image
and checking actual acquisition again. Keep a backup before a material upgrade.

## Retention, maintenance, and recovery

Pin an important `snapshot_id` with `pin` (`pinned: true`) before its retention
window ends. `pinned: false` unpins it. `export` returns a portable retained
capture. `expire` is an explicit removal request; `gc` defaults to dry-run and
requires `dry_run: false` to apply cleanup. Expired handles return an explicit
unavailable result; they never silently fetch a newer live page.

`backup` creates an application backup beneath `.state/` and returns a backup
ID. Stop the worker before `restore` to avoid ongoing crawl work competing with
the administrative operation. Restore verifies the backup and refuses with
`409 restore_would_discard_state` if it would remove or change current captures,
pins, expiry, contexts, acknowledged jobs, or crawl progress. Even newer cache
events can make an older backup incompatible. There is no implicit rollback or
force option. Use a current matching backup for corruption repair, or recover
an older backup into a separate empty product-local state directory. Disposable
index state and transient job leases do not cause a conflict.
Send the returned `backup_id` to `restore` and check a known pinned citation
afterwards. For an additional filesystem copy,
stop both DWS consumers and keep the copy beneath this DWS directory. Keep
`.runtime/owner.env` separately from exported evidence; it contains credentials.

```bash
docker compose --env-file .runtime/owner.env logs --tail 100 dws-api dws-worker
docker compose --env-file .runtime/owner.env stop dws-api dws-worker
docker compose --env-file .runtime/owner.env up -d --no-deps dws-api dws-worker
```

Use `diagnostics` to inspect retained data, storage admission, and index health.
Provider operations report availability failures explicitly. Rebuild only the
index with `index_rebuild`; snapshot reads must continue
to work independently. Upstream search can be rate-limited or empty, acquisition
can fail, and crawls can finish partially. Inspect their machine-readable
failures, truncation signals, budgets, and manifests.

At the storage limit, new captures, jobs, and metadata writes fail explicitly
while retained reads and status remain available. Unpin/expire and explicit GC
permit recovery. Use diagnostics to inspect storage admission and available
space before changing retention.

If capture storage fails after admission, the attempted snapshot is rolled back.
No-space and filesystem-quota failures return `disk_pressure` (HTTP 507); other
artifact write or sync failures return `artifact_write_failed` (HTTP 500).
Unexpected API failures return a bounded `internal_error` (HTTP 500). Error
messages omit filesystem paths and raw exception details. Existing retained
reads remain available; resolve the storage problem before retrying acquisition.

## Supported scope and limitations

State belongs to the local service owner. A new state directory is private
(`0700`); an existing directory owned by that user with no write access for
others is tightened to that mode. Symlink roots, foreign ownership, and roots
writable by other users are rejected. These checks apply to explicit-token
API startup and worker startup as well as automatic-token startup. Choose a
dedicated state directory rather than a shared folder.
Configured retention must fit the supported UTC timestamp range; invalid
periods are rejected before API or worker state creation.

Public static HTML/text, rendered HTML, and text-bearing PDFs are the default
content types. Scanned PDFs and difficult layouts can produce limited extraction
and do not imply OCR support. Authentication automation, paywall bypass, arbitrary
browser scripting, video/audio transcription, and general local-file indexing
are outside the product contract.

Acquisition requires a complete HTTP representation. Unsupported range
responses (`206`) and delta responses (`226`) are rejected before interpretation
or snapshot publication, including provider transports and rendered main-page
status. Their errors remain visible in fetch/crawl results; configured search
fallback follows the existing provider-failure disclosure. Retained snapshots
stay immutable; request a refresh to reacquire a source under updated admission
rules. DWS requires a full source response from the upstream server. See
[HTTP partial content](https://www.rfc-editor.org/rfc/rfc9110.html#name-206-partial-content)
and [HTTP delta encoding](https://www.rfc-editor.org/rfc/rfc3229.html#section-10.4.1).

HTML decoding honors a recognized BOM before a supported HTTP charset. Known
rendered DOM strings use UTF-8. Decoding identity and limitations are retained
with the snapshot; unsupported labels and replacement decoding produce explicit
warnings. Charset support follows Python text codecs. Undeclared HTML uses the
existing BeautifulSoup inference, which does not implement every browser
encoding-sniffing rule. Earlier snapshots keep their original normalization;
request a refresh to capture a source with the updated decoder.

The browser image currently disables Chromium's renderer sandbox upstream;
the service uses a separate restricted container and protective outbound overlay.
Public-network policy still applies to redirects and browser subrequests.
Direct acquisition URL validation rejects known NAT64 translation prefixes,
including aliases for public IPv4 addresses. Browser subrequest policy checks
the embedded destination and can permit public IPv4 aliases. Deployment-specific
translation prefixes are not inferred.
Crawl scope applies to retained pages and static redirect destinations. Static
redirects outside scope are stopped before requesting the destination. Rendered
pages are checked after navigation and before retention; a public browser
navigation outside crawl scope may already have occurred. Browser assets remain
subject to public-network policy rather than the crawl path boundary.
Do not enable internal-target or insecure-TLS escape hatches. A provider failure
is an honest incomplete operation, not evidence that the source contains nothing.
The measured acceptance record is in `docs/verification/`; installation or green
health checks alone do not prove the entire [product vision](product-goal.md).
