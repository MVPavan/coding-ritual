# Fixture concurrency qualification — 2026-10-04

## Method and environment

Run from `dws/`:

```bash
UV_CACHE_DIR="$PWD/.runtime/uv-cache" TMPDIR="$PWD/.runtime/tmp" \
  .venv/bin/python tests/e2e/verify_concurrency.py \
  --output-dir .runtime/verification/qualification-final2-20261004
```

The repeatable script starts separate API and worker processes with isolated
SQLite/artifact state and a loopback HTTP fixture. It does not contact public
websites or replace the owner's Compose services. Each burst has *N* concurrent
callers and four queued operations per caller: distinct static `fetch`, `read`,
scoped `retrieve`, and search through the fixture SearXNG response. A real worker
crawl holds one fixture acquisition during each burst. The fixture delays each
static source response by 350 ms. Five `job_status` and one `job_cancel` calls
run while the crawl and burst are active. Percentiles use the nearest-rank
method and include both successful and typed capacity responses.

This run used Python 3.13.9 on Linux 6.6.87.2 WSL2. API admission was six
requests, with one place reserved for job controls; the cross-process
acquisition limit was four. The qualification sampled occupied acquisition
lock slots and independently counted simultaneous fixture source requests.
Bounds: neither peak may exceed four, all errors must be typed 429 capacity
responses with `Retry-After: 1` and `retry_after_seconds: 1`, and status/cancel
p95 must remain below 2,500 ms with at least one success each.

## Measured results

The full run passed from 17:03:43 to 17:04:14 UTC. Values below are milliseconds.
`S/429/other` counts successful responses, typed capacity responses, and other
errors. The complete machine-readable receipt is
`.runtime/verification/qualification-final2-20261004/concurrency.json`.

| Callers | Peak held slots / fixture requests (limit 4) | All S / 429 / other | Status p95 | Cancel p95 |
|---:|---:|---:|---:|---:|
| 1 | 2 / 2 | 10 / 0 / 0 | 4.3 | 5.5 |
| 5 | 4 / 4 | 26 / 0 / 0 | 15.8 | 5.5 |
| 10 | 4 / 3 | 20 / 26 / 0 | 24.9 | 5.7 |
| 20 | 4 / 4 | 20 / 66 / 0 | 24.6 | 5.0 |
| 50 | 4 / 4 | 19 / 187 / 0 | 82.7 | 63.1 |

| Callers | Operation | Calls | p50 | p95 | Max | S | 429 | Other |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | fetch | 1 | 496.4 | 496.4 | 496.4 | 1 | 0 | 0 |
| 1 | read | 1 | 1.7 | 1.7 | 1.7 | 1 | 0 | 0 |
| 1 | retrieve | 1 | 1.9 | 1.9 | 1.9 | 1 | 0 | 0 |
| 1 | search | 1 | 2.3 | 2.3 | 2.3 | 1 | 0 | 0 |
| 1 | job_status | 5 | 1.7 | 4.3 | 4.3 | 5 | 0 | 0 |
| 1 | job_cancel | 1 | 5.5 | 5.5 | 5.5 | 1 | 0 | 0 |
| 5 | fetch | 5 | 538.4 | 1000.8 | 1000.8 | 5 | 0 | 0 |
| 5 | read | 5 | 5.5 | 16.0 | 16.0 | 5 | 0 | 0 |
| 5 | retrieve | 5 | 5.9 | 22.0 | 22.0 | 5 | 0 | 0 |
| 5 | search | 5 | 6.0 | 509.7 | 509.7 | 5 | 0 | 0 |
| 5 | job_status | 5 | 2.3 | 15.8 | 15.8 | 5 | 0 | 0 |
| 5 | job_cancel | 1 | 5.5 | 5.5 | 5.5 | 1 | 0 | 0 |
| 10 | fetch | 10 | 6.1 | 527.1 | 527.1 | 2 | 8 | 0 |
| 10 | read | 10 | 11.3 | 27.7 | 27.7 | 4 | 6 | 0 |
| 10 | retrieve | 10 | 13.7 | 28.8 | 28.8 | 5 | 5 | 0 |
| 10 | search | 10 | 5.9 | 32.8 | 32.8 | 3 | 7 | 0 |
| 10 | job_status | 5 | 2.1 | 24.9 | 24.9 | 5 | 0 | 0 |
| 10 | job_cancel | 1 | 5.7 | 5.7 | 5.7 | 1 | 0 | 0 |
| 20 | fetch | 20 | 11.3 | 551.5 | 555.1 | 3 | 17 | 0 |
| 20 | read | 20 | 10.6 | 28.3 | 41.5 | 3 | 17 | 0 |
| 20 | retrieve | 20 | 10.5 | 42.9 | 43.2 | 5 | 15 | 0 |
| 20 | search | 20 | 10.3 | 32.4 | 61.3 | 3 | 17 | 0 |
| 20 | job_status | 5 | 1.6 | 24.6 | 24.6 | 5 | 0 | 0 |
| 20 | job_cancel | 1 | 5.0 | 5.0 | 5.0 | 1 | 0 | 0 |
| 50 | fetch | 50 | 22.9 | 667.4 | 1165.4 | 5 | 45 | 0 |
| 50 | read | 50 | 22.1 | 72.7 | 82.9 | 4 | 46 | 0 |
| 50 | retrieve | 50 | 23.9 | 77.8 | 85.3 | 2 | 48 | 0 |
| 50 | search | 50 | 23.0 | 79.0 | 134.0 | 2 | 48 | 0 |
| 50 | job_status | 5 | 1.8 | 82.7 | 82.7 | 5 | 0 | 0 |
| 50 | job_cancel | 1 | 63.1 | 63.1 | 63.1 | 1 | 0 | 0 |

The separate browser phase reused the isolated public/private Docker networks,
runtime API container, fixture source and protected Crawl4AI container from
`verify_rendered_fixture.py`. A two-second fixture delay held actual browser
navigation while five job-status calls and one cancel completed. Their p95s
were 184.2 ms and 178.2 ms, respectively; all six succeeded. The browser
captured rendered text, the private subrequest remained blocked, and the
isolated containers and networks were removed. The browser receipt is at
`.runtime/verification/qualification-final2-20261004/browser/receipt.json`.

## Limits

This measures one fixture delay, one host, one admission configuration and a
short burst envelope; it is not a production throughput, sustained-load or
public-website capacity claim. At 50 callers, 187 of 206 requests were typed
capacity responses. The browser phase measured control responsiveness during
one rendered fetch; the 1/5/10/20/50 mixed bursts used static fixture fetches.
The first trial before reserving control admission returned 429 for all five
job-status probes at 50 callers; its failed receipt is retained under
`.runtime/verification/20261004T165317Z-concurrency/`.
