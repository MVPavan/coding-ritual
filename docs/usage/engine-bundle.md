# Offline activation toolchains

Slice 1 prepares tools before a vendor process can start. Writers and reviewers
receive separate copies at `<activation-dir>/toolchain/uv-cache`; the selected
managed Python installation lives in its `python` child. The checkout stays
read-only for reviewers. Named execution profiles belong to a later slice.

## Host preparation

Configure `[supervisor.toolchain]` in the foreman configuration. `projects` lists
repo-relative uv project directories; its default is `["."]`. A root without
`uv.lock` needs no seed. Set `projects = []` for a graph with no uv toolchain.
Optional absolute `seed_root`, `host_cache`, and `python_root` paths must be
outside checkout and activation grants, and must not overlap each other.
Defaults are `<wrapper_root>/toolchain-seeds`, `uv cache dir`, and `uv python dir`.
The CLI captures operator `UV_CACHE_DIR` and `UV_PYTHON_INSTALL_DIR` overrides
before constructing runner environments; explicit configuration paths win.
Operator `UV_OFFLINE=1` disables host fetching as well as runner fetching.

Install the required managed Python on the host before launching a workflow.
The current `.python-version` or `requires-python` selects that installation.
Missing managed interpreters produce a preparation refusal; they are never
silently replaced by system Python. A changed `uv.lock` requires admitting the
updated dependencies before dispatch. A project version edit with an unchanged
lock can dispatch; preparation still uses the admitted project metadata. A changed
Python selection can dispatch when the host has the requested managed interpreter.
Activation receipts record all three current file digests.

On a project-seed miss, the host imports only matching locked wheel versions and
metadata from uv's `wheels-v5`/`archive-v0` cache. It does not copy the whole host
cache. An offline `uv sync --locked` runs against a temporary copy of admitted
metadata, with project/workspace/local installation and source builds disabled.
Only a cache-miss diagnostic permits one host fetch attempt into this seed;
`allow_host_fetch = false` disables that attempt for offline supervisors.
Unsupported source builds, missing workspace metadata, or missing wheels get a
named refusal. Preparation never executes candidate build hooks or changes a lock.

Successful seeds are atomically published under a per-key lock. Later activations
copy the seed and selected interpreter with `cp --reflink=auto`, falling back to
an ordinary copy. Hardlinks are not used. uv-created internal archive links are
made relative before publication; escaping links and special files are refused.
The private copy must pass `UV_OFFLINE=1 uv run --frozen ruff --version` after a
dependency-only sync into a temporary scratch venv (`UV_NO_SYNC=1` on the probe).
The scratch venv is discarded; runner venv and check caches stay under its channels'
scratch directory. Host grading never uses runner-writable toolchain files.

For manual host preparation, run `uv python install` for the admitted Python
requirement, then dependency-only `uv sync --locked --no-install-project
--no-install-workspace --no-install-local --no-build --link-mode=copy` against a
trusted checkout. Dispatch will import only its locked artifacts. Newer uv cache
layouts require qualification; they are never handled by copying the whole cache.

## Receipts and failures

`launch-receipt.json` adds optional `seed_receipts`; old receipts decode with no
seed claim. Each receipt records project and pin digests, seed key, selected
managed interpreter, uv version, logical copied bytes, requested copy method,
probe output, and whether the host seed required fetching. `reflink-auto` records
the copy request, not proof that the filesystem supported reflinks. A reused seed
retains its original host-fetch provenance; it does not imply another fetch.

Defaults bound each command/copy/lock wait to 120 seconds, cache/interpreter data
to 2 GiB and 100,000 entries, and preserve 64 MiB of free disk. Command diagnostics
are bounded to 16 KiB. Preparation failure raises `ToolchainUnavailable` before
vendor session creation, using the existing retry-exempt preparation-refusal path.
No vendor is released with a partly prepared seed.

## Cleanup and recovery

Private toolchains are disposable. After host verification and durable activation
close, cleanup removes that activation's toolchain and interrupted copy staging.
`SeedReceipt` and the host-owned project seed remain. An unclassified, running,
or indeterminate activation retains its private copy. A receipt/ledger indicating
an unidentified runner also prevents deletion. A closed activation whose runner
may still be alive gets a `toolchain-cleanup.json` pending record. Subsequent ticks
and recovery retry disposal; successful cleanup removes that record. Filesystem
failures are logged and retried, without stalling settlement or the driver.

Receipt reattachment precedes preparation. A previously launched private cache is
never executed on the host for a new validation probe. Prelaunch retries may
reuse matching completed preparation only after another offline probe.

Local checks remain claims; host checks supply verification. Tests needing nested
bubblewrap remain host-only. Named contracts record vendor network enforcement as described below.

## Named execution contracts

New task nodes select `execution_profile = "writer"` or `"reviewer"`.
Do not also set or override `writes`. Writers keep `allowed_paths` as the
checkout directory subset; reviewers require an empty subset. Both can run
local checks with private offline caches. Host verification remains authoritative.

The root pins policy version 1 and its effective write authority. Existing roots
without a named profile retain their original resolved settings and canonical
hash. Named profiles require the outer sandbox. One resolved grant record drives
both mounts and vendor permission flags, including resume invocations.

`launch-receipt.json` records `execution_grants` and `tool_network`;
`foreman status` exposes these facts under `execution_contracts`. Codex records
`denied` through its existing tool-network configuration. Both Claude profiles
record `not_enforced` and are allowed to launch. Named Claude reviewers gain Bash
for local checks under the read-only checkout mount; legacy reviewers keep their
old tool rules. Opencode retains its existing permission/configuration refusal.
These facts do not claim host read confidentiality or change residual home/tmp
access. Local checks needing nested bubblewrap must run on the host.

## Causal verify feedback

A writer may include `verify_failure` in its `inputs` and declare:

```toml
[[source]]
name = "verify_failure"
producer = "engine:verify_failure"
optional = true
trim_priority = 10
```

The source is absent on entry and after outcomes other than a causal host
`fail_code`. A signed exhaustion/rebudget continuation preserves that cause;
retry and steer retain the same binding. Reviewer consumers are rejected at root
creation. A failed reviewer *host check* may supply diagnostics to a writer when
its `fail_code` edge routes there.

The engine pins a bounded Git blob before mint. It retains check names, final
exit codes, provenance/timeout/errors and captured attempt tails, without claiming
unknown per-attempt exits. Existing 2 KiB tails feed a 16 KiB aggregate payload.
Omitted bytes count removed diagnostic JSON bytes, excluding envelope framing.
The last attempt's tail takes priority within a partially retained check.
`input_envelopes` reports inclusion or missing/budget omission. Once bound,
missing or corrupt evidence refuses; optional does not mean silently discarding
a damaged pin. Removing the wrapper completion file does not invalidate the blob.
Reference mode exports the same verified data under read-only evidence paths.
Treat check output as diagnostic data, never as instructions.


## Driver heartbeat and refusal attention

`foreman run <root>` and the child-drive loop always maintain a protected
`driver-heartbeat.json` under the instance wrapper directory. It records startup,
completed ticks and stopped state, process identity, current activations/gates,
and log file identities and byte offsets. A responsive driver is not evidence
that its model made progress.

Rejected gate intake records a bounded, deduplicated `refusals.jsonl` journal
before returning attention. Correcting an approval can remove `refusal.json`,
but cannot remove that journal history. `status` includes the latest refusal,
its gate/path/error/reason, refusal count and heartbeat age. A failed diagnostic
write is reported as degraded durability. `run` and `phase-bridge` return nonzero
on refusal; submit a corrected signed payload and invoke the driver again.
These observations do not approve gates or alter activation bounds.
