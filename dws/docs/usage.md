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

```bash
curl --fail-with-body http://127.0.0.1:8765/v1/read \
  -H "Authorization: Bearer $DWS_TOKEN" -H 'Content-Type: application/json' \
  -d '{"snapshot_id":"REPLACE_WITH_SNAPSHOT_ID","line_start":1,"line_end":30}'
```

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
