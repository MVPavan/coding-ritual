# SearXNG image qualification — P1 / cr-0km.4

**2026-09-22 — Fix round 1 ready for fresh Sol high review; coordinator acceptance pending.**
This qualifies one upstream image and private-service configuration. It does not
implement a production DWS service or search adapter, close cr-0km.4, or satisfy
all P1 requirements. Scope follows [P1](../../workstreams/dws/roadmap.md#p1--foundation-runtime-qualification-and-frozen-contracts),
the [goal](../../plans/dws/implementation-goal.md), PRD provider/deployment sections
9/15, and design sections 6.1/13. The browser and application image workers own
their separate boundaries.

## Identity and source evidence

Selected official image:
`ghcr.io/searxng/searxng@sha256:a93b665d10ce0675e8d2124187943111399ba69f384228c51b4cd21fdceda0bc`.
Version `2026.9.11-61d660276`, source revision
`61d660276f1288e7d512e8d8da46cb8442728454`, created
`2026-09-11T15:01:39.101889467Z`. Actual pulled manifest/image ID matches the
selected digest (unchanged in fix round 1); platform **linux/amd64**, image size 381,785,923 bytes. No other
architecture was tested. Candidate selection used the official
[GHCR package](https://github.com/searxng/searxng/pkgs/container/searxng).

The [machine-readable manifest](searxng-image-manifest.json) records actual image
metadata, complete installed Python package inventory, native versions, config
keys, API examples and candidate file hashes. Inspection found Void Linux,
Python 3.14.7, Granian 2.8.2, Flask 3.1.3, glibc 2.41, Python OpenSSL 3.6.4,
SQLite 3.53.4, lxml 6.1.2/libxml2 2.14.6/libxslt 1.1.43 and curl_cffi 0.16.1
with libcurl 8.21.0-IMPERSONATE/BoringSSL. The native curl TLS stack differs
from Python's OpenSSL stack. Runtime inspection, not host package versions,
supplied these values.

Pinned upstream sources inspected:

- [Builder](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/container/builder.dockerfile)
  installs requirements with uv and compiles/compresses packaged resources.
- [Distribution image](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/container/dist.dockerfile)
  copies the venv, application, entrypoint and frozen version into an upstream
  base; defines port 8080 and config/cache volumes. Upstream base references
  are mutable tags; this qualification pins the final artifact, not a verified
  reproducible source rebuild. No local image rebuild was performed.
- [Entrypoint](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/container/entrypoint.sh)
  checks config/cache directories, generates settings only when absent, performs
  ownership/CA changes only as root, then execs Granian. The actual image has
  no configured default user or built-in healthcheck.
- [License](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/LICENSE):
  GNU AGPL v3 text; OCI label and source SPDX identify AGPL-3.0-or-later.
  Preserve upstream attribution/source/license information in distribution.
  Complete transitive notices, network-use obligations, hosted-provider terms,
  vulnerability assessment, signatures and attestations remain P1 .5 review
  work; this report is not distribution approval or a clean security audit.

## Candidate configuration and isolation

[settings.yml](../../../dws/docker/searxng/settings.yml) explicitly enables JSON
alongside HTML, disables autocomplete/image proxy/public-instance mode/limiter,
sets `valkey.url: false`, sets request/max timeouts to 3/5 seconds, and retains
only DuckDuckGo and Wikipedia from the pinned defaults. This small credential-free
candidate bounds engine fan-out; it is not a claim about broad-search coverage.
`/config` confirmed exactly those two engines. DuckDuckGo advertises time-range
support; Wikipedia does not. These declarations do not prove filter enforcement;
P7 must handle capability disclosure, fallback, URL validation and filters.

The central `plugins` mapping now retains the other ten pinned default plugins
and **omits** `tracker_url_remover`. This is significant: the pinned
[settings loader](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/searx/settings_loader.py)
replaces the default plugin map with the supplied map, while
[plugin initialization](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/searx/plugins/_core.py)
calls every configured plugin's `init`, even with `active: false`.
The [tracker initializer](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/searx/plugins/tracker_url_remover.py)
loads mutable external rules. Omitting it prevents both initialization and later
user selection. No rules are vendored and no provider implementation is changed.
The other ten plugins retain their pinned upstream active/inactive settings.
Eight appear in the effective `/config` list: `ahmia_filter` removes itself when
Tor is unused and `hostnames` removes itself without hostname-rewrite settings
(per their pinned `init` methods). The final local checker initially assumed
all ten would remain registered; source inspection corrected that checker
expectation, with no runtime candidate change or extra service rerun.

[service.yaml](../../../dws/docker/searxng/service.yaml) is a coordinator integration
fragment, **not a new top-level deployment**. It carries the immutable digest,
platform, UID/GID 977, `cap_drop: ALL`, `no-new-privileges`, read-only rootfs,
one Granian worker, 1 CPU, 512 MiB memory with no extra swap allowance, and 128
PIDs. It has no published ports. Mount only the dedicated config directory and
healthcheck read-only. `/tmp` and `/var/cache/searxng` are bounded 32 MiB tmpfs
mounts; no archive, home, Docker socket or unrelated credential is exposed.
Provide a random deployment-specific `DWS_SEARXNG_SECRET` to the fragment; its
`SEARXNG_SECRET` runtime mapping avoids committing a shared signing secret.
Do not put unrelated files/secrets into the mounted config directory.

The probe used equivalent Docker flags, with isolated DWS-prefixed names and an
**internal** Docker network. Container inspection and `/proc/1/status` recorded
nonroot UID 977, zero capability sets and `NoNewPrivs: 1`. Inspect records show
no port bindings, read-only config, tmpfs, resource limits and no DWS data mount.
The private production bridge needs outbound provider access; an internal-only
network is suitable for these fixtures but cannot perform public discovery.
This does not qualify general browser/URL egress enforcement.

Config files must exist and be readable before startup. The entrypoint warns
about the host-owned read-only config directory, but both candidate and fixture
services started successfully without chown or added capabilities. The existing
CA bundle works without root-only CA refresh. Replacement discards cache/tmp
contents; no persistent volume was required for these searches.

**Redis/Valkey is optional for this private configuration.** No Redis/Valkey
container or server process was started. The installed `valkey` Python client is
not a server. [valkeydb.py](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/searx/valkeydb.py)
returns without a connection when no URL is configured; `redis.url` is deprecated
in favor of `valkey.url`. [limiter.py](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/searx/limiter.py)
requires Valkey for rate limiting; missing Valkey logs an error and leaves the
private limiter uninstalled, while public-instance mode exits. The tested
`/config` response reported limiter disabled and public-instance false. Enabling
either feature requires a separately qualified supporting service.

## Actual API and failure evidence

Run from repository root with Docker access and the pinned image available:

```sh
docker pull ghcr.io/searxng/searxng@sha256:a93b665d10ce0675e8d2124187943111399ba69f384228c51b4cd21fdceda0bc
python3 dws/tests/qualification/image_searxng_probe.py
```

The stdlib-only [probe](../../../dws/tests/qualification/image_searxng_probe.py)
runs the real Granian/SearXNG service and its **unmodified upstream
[json_engine](https://github.com/searxng/searxng/blob/61d660276f1288e7d512e8d8da46cb8442728454/searx/engines/json_engine.py)**.
Only test settings point that generic engine at a synthetic HTTP upstream on the
owned network. No public engine was replaced or counted as live coverage. A
separate candidate service verifies actual default-engine registration without
querying those engines. Requests originate in a separate container through
Docker DNS/networking, not Flask's test client or host-published ports.

Successful request: `GET /search?q=success&format=json&engines=dws-fixture`.
Response keys: `query`, `results`, `answers`, `corrections`, `infoboxes`,
`suggestions`, `unresponsive_engines`. The result includes `url`, `title`,
`content` (snippet), `engine`, `engines`, `positions`, `score`, `category`,
`publishedDate: null` and display fields. No `number_of_results` field appeared
in this fixture response: do not assume it is mandatory. Exact example is in
the manifest. Result links were not fetched.

| Case | Observed real response |
|---|---|
| Fixture success | HTTP 200; one expected result; no unresponsive engines |
| Genuine fixture empty | HTTP 200; empty results and empty unresponsive engines |
| Malformed upstream JSON | HTTP 200; empty results; `[["dws-fixture", "parsing error"]]` |
| Upstream exceeds 0.5 s fixture timeout | HTTP 200; empty results; `[["dws-fixture", "timeout"]]` |
| Upstream HTTP 503 | HTTP 200; empty results; `[["dws-fixture", "HTTP error"]]` |
| Missing query with JSON enabled | HTTP 400; `{"error": "No query"}` |
| JSON removed from formats | HTTP 403, HTML error body |
| Service stopped | Client transport error: Docker DNS resolution failure, not empty JSON |

Engine failure cases restart the same service between selected cases to clear
upstream suspension state, not to retry a failed qualification. SearXNG can mask
engine failures behind HTTP 200, so a later adapter must inspect the payload.
The probe now asserts the exact singleton `[engine, reason]` pair for each
failure, separately from legitimate empty and transport failure. Mutating each
actual failure response to `wrong category` is rejected by the same assertion.
No DWS fallback or filter behavior is tested here.

[healthcheck.py](../../../dws/docker/searxng/healthcheck.py) verifies the missing-query
JSON response. Unlike the upstream `/healthz` constant `OK`, it exercises JSON
format enablement and a real search route without upstream requests. It passed
on both configured services. It does **not** prove public engines are reachable
or returning results; later diagnostics must distinguish those states.

## Runs, checks and limitations

Raw evidence (gitignored): original `scratchpad/dws/searxng-image/run-9b357658`
and `run-7a9343ad` remain unchanged, along with original source/inventory/review
artifacts. Their prior success is **superseded for the three review findings**:
mutable plugin startup traffic, insufficient category assertions and fallible
cleanup. Pre-fix report/manifest copies are in
`scratchpad/dws/searxng-image/fix1/pre-fix1-searxng-image-{qualification.md,manifest.json}`;
the current manifest also retains historical hashes and evidence separately.

Fix round 1 commands (repository root):

```sh
python3 dws/tests/qualification/image_searxng_probe.py
python3 dws/tests/qualification/image_searxng_probe.py --inject-finalization-failures
```

The first command exited **0**, `fix1/run-e3a5be16`, all real API cases passed.
The second deliberately exited **1**, `fix1/run-9fc0685b`, after passing the same
real API checks and injecting finalization failures. These are two planned
controls for one fix candidate, not infrastructure retries. No correction run
was needed. Full stdout/stderr, source excerpts, results, startup logs,
container inspections and finalization reports are under `fix1/`.

| Sol Important finding | Fix and evidence |
|---|---|
| Mutable tracker startup downloads | Explicit plugin map omits tracker. Fresh candidate, fixture and no-JSON services have no tracker in `/config` and no tracker/rules-fetch log markers, including fixture restarts. A separate internal-network control adds tracker with `active: false`: `/config` reports disabled but logs reproduce `TRACKER_PATTERNS` and all three public rules endpoints. This positive detection control demonstrates why merely making it inactive is insufficient. Actual downloads remain blocked on the internal network. |
| Failure category assertions too weak | Exact `dws-fixture` plus `parsing error`, `timeout`, and `HTTP error` assertions pass. All three wrong-category mutations of observed responses are rejected. Empty and transport cases remain separately asserted. |
| Evidence/removal failure skips cleanup | Each log/inspect/write has independent error handling; cleanup runs in the outer `finally` and attempts every owned container plus network independently. Original primary error is retained first in an exception group alongside finalization errors; any such error makes the command fail. |

The integration injection raises a primary operation error after actual API
checks, fails the first log collection, and simulates a lost removal success
acknowledgement after the first real container removal. It still collects all
five inspections and four later container logs, attempts all five container
removals plus network removal, and reports all **three** errors with original
tracebacks in primary-first order. The acknowledged-removal simulation proves
continuation when a removal call reports an error without deliberately leaking
a resource; it does not prove that removal can succeed if Docker is unavailable.
A real removal failure remains reported and may require exact-resource operator
cleanup; the probe does not claim success or broadly discover/delete resources.

`fix1/cleanup-proof.json` records subsequent **exact-name** Docker inspections:
all ten containers and both networks from the normal and injection runs were
absent. All expected cleanup commands were recorded in order. No persistent
volume was created. Cached image retained; no prune/unrelated cleanup occurred.
`finalization.json` and process exit status, not a partial `results.json` alone,
are authoritative for overall probe success.

Public search queries sent: **zero**. Live provider availability, coverage,
rate limits/CAPTCHAs and correlated outages remain unqualified. Default engines
still register as DuckDuckGo/Wikipedia and the JSON health route works. Remaining
startup warnings concern the host-owned read-only config, absent `limiter.toml`
and proxy client-IP headers; these did not prevent the private API checks.
The revised candidate snapshot used 76.07 MiB and 8 tasks; fixture service
77.9 MiB and 10 tasks, under 512 MiB limits. These are tiny-workload observations,
not sustained-load evidence. No immutable image pin, mount, privilege or resource
constraint changed.

Validation: `python3 -m py_compile` on both Python files; scoped Ruff check and
format check; strict mypy on both files; `python3 -m json.tool` on manifest;
`DWS_SEARXNG_SECRET=qualification-config-validation-only docker compose -p
dws-searxng-config -f dws/docker/searxng/service.yaml config --quiet`;
`git diff --check`; local documentation link check. All passed. Root application,
Compose, package dependencies, existing tests and other workers' files were not
edited. Fresh independent Sol high re-review, coordinator integration and P1 .5 supply-chain /
distribution disposition remain outstanding.
