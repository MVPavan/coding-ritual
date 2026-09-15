# Engine bundle — implementation plan

Status: proposed; Phase 1 only. Coordinator review precedes implementation.
Origin: coordinator brief; `docs/specs/workflow-interpreter.md` §§5, 6, 8–10.
Baseline: `wf/engine-bundle`, `add0f008f57457950a83d7542286d1ca1c5ccea8`.
Goal: make activation permissions, offline tools, rework evidence, wake delivery,
and Codex control explicit without weakening host verification or crash recovery.

This is one plan for cr-02ze.6, cr-02ze.20, cr-02ze.19, cr-02ze.21,
cr-02ze.4, cr-o85.15, cr-o85.10, and the measurement concern in cr-o85.34.30.
`bd show` failed while opening the database lock on a read-only filesystem.
Task descriptions, acceptance criteria, and notes were read from the committed
`.beads/issues.jsonl` mirror; their live status was not verified. No Beads writes.
All implementation paths below are proposed, not changes made in Phase 1.

## 1. Observed guarantees today

These are source-verified facts at the baseline, not fresh live qualifications.
Older explanatory comments sometimes describe a broader or older boundary than
the executable code. The project brief's “no first-party code” statement is also
stale; the interpreter-specific verification section is the applicable gate.

### Filesystem, network, and temporary files

| Surface | Observed behavior and evidence |
|---|---|
| Outer bwrap | Starts with `--dev-bind / /`, then read-only repo root, wrapper root, and checkout; writable Git stores, allowed directories, channels, and toolchain cache; read-only pins last. It is a workspace mount bound, not complete host isolation. `workflow_interpreter/supervisor/sandbox.py:577`, `workflow_interpreter/supervisor/sandbox.py:634`. |
| Writer Git | Linked-worktree writers get their Git directory, shared objects, and this instance's candidate branch/ref-log directories. Config, info, and Git pointer files are pinned back. The branch grant is checked against trusted root identity; detached checkouts receive no shared branch grant. `workflow_interpreter/supervisor/sandbox.py:407`, `workflow_interpreter/supervisor/sandbox.py:495`. |
| Protected state | Main/sibling workspace data and wrapper evidence are covered by the read-only roots; channel grants exclude the wrapper's receipt and ledger. Grant paths reject hidden segments, traversal shapes, and symlinked directory segments. This is not a claim that arbitrary host credentials or paths outside those roots are inaccessible. `workflow_interpreter/supervisor/sandbox.py:288`, `workflow_interpreter/supervisor/sandbox.py:326`, `workflow_interpreter/profiles/codex.py:274`. |
| Network | Outer bwrap does **not** unshare network. ADR 0001 decision O4 explicitly chose that. Codex tool sandbox configuration sets `network_access=false`; Claude shell permissions do not provide an equivalent OS network boundary. Denying the entire vendor process would also deny its model transport. `workflow_interpreter/supervisor/sandbox.py:634`, `workflow_interpreter/profiles/codex.py:317`, `workflow_interpreter/profiles/claude.py:270`. |
| Temporary files/home | Outer bwrap leaves host home and `/tmp` writable unless covered by an explicit bind. Codex excludes ambient `/tmp`; all profiles receive `TMPDIR` pointing at channel scratch. This env setting does not hide host `/tmp` from Claude Bash. `workflow_interpreter/supervisor/sandbox.py:18`, `workflow_interpreter/profiles/codex.py:302`, `workflow_interpreter/profiles/_base.py:475`. |
| Unsafe mode | `sandbox=off` bypasses wrapping, with an explicit audit posture. Normal dispatch probes bwrap and refuses an unavailable bound. Named profiles must not silently opt into this escape hatch. `workflow_interpreter/supervisor/sandbox.py:632`, `workflow_interpreter/supervisor/launch.py:969`, `workflow_interpreter/foreman/supervise.py:359`. |

### Vendor write roots and cache wiring

- **Codex writer:** `workspace-write`, checkout as cwd, channels plus linked
  Git write directories plus the supervisor's cache as additional writable roots.
  Vendor cwd is wider than `allowed_paths`; outer bwrap enforces the narrower
  checkout subset. In-repo Codex writers are refused. Both launch and resume use
  the same root calculation. Evidence: `workflow_interpreter/profiles/codex.py:221`,
  `workflow_interpreter/profiles/codex.py:274`,
  `workflow_interpreter/profiles/codex.py:424`.
- **Codex reviewer:** cwd is channels, using `workspace-write` to permit reporting.
  `_writable_roots` returns before adding Git or toolchain cache. The checkout is
  readable but not a vendor write root. `TaskSpec` carries only `cwd`, without an
  explicit checkout read-root contract: cr-o85.10 remains relevant.
  Evidence: `workflow_interpreter/profiles/codex.py:298`,
  `workflow_interpreter/profiles/codex.py:430`,
  `workflow_interpreter/supervisor/profile.py:127`.
- **Claude:** keeps checkout cwd. Uses `dontAsk`, restricted setting sources,
  strict MCP configuration, tool allow/deny rules. Writers have Bash and path
  rules for declared directories/channels; outer mounts contain shell writes in
  the workspace. Reviewers have read tools and channel write rules, with Bash
  denied. A cache alone therefore does not enable Claude reviewer checks.
  Evidence: `workflow_interpreter/profiles/claude.py:58`,
  `workflow_interpreter/profiles/claude.py:129`,
  `workflow_interpreter/profiles/claude.py:235`,
  `workflow_interpreter/profiles/claude.py:248`.
- **Opencode:** parsing exists, but launch is deliberately refused because its
  permission/configuration surface was not boundable. A new execution-profile
  name is not evidence that this changed. `workflow_interpreter/profiles/opencode.py:1`.
- **Cache creation:** `toolchain_cache_for(wrapper_root)` creates one empty
  `wrapper_root/uv-cache`, shared across activations. Outer plans grant it even
  to readers; the Codex inner reader policy blocks it. `_launch` injects that
  path into `TaskSpec`; the fork launcher overrides `UV_CACHE_DIR` and
  `UV_PYTHON_INSTALL_DIR=<cache>/python`. No seed/import step exists.
  Evidence: `workflow_interpreter/supervisor/sandbox.py:584`,
  `workflow_interpreter/supervisor/sandbox.py:605`,
  `workflow_interpreter/supervisor/launch.py:364`,
  `workflow_interpreter/supervisor/launch.py:915`.
- **Other tool directories:** profile env places the virtualenv, Ruff, mypy,
  pytest cache, and temp data in scratch; `UV_FROZEN=1` is set, but not
  `UV_OFFLINE=1`. `workflow_interpreter/profiles/_base.py:125`.
  `LaunchReceipt` has no seed provenance. `workflow_interpreter/supervisor/models.py:280`.

### Dispatch, steering, polling, and evidence

- The fork barrier writes a receipt before release, appends an exec ledger line,
  and only then execs. Current child stdin is `/dev/null`; stdout and stderr
  share `run.jsonl`. An RPC runner cannot use that stream as both an interactive
  transport and an ordinary log. `workflow_interpreter/supervisor/launch.py:584`.
- Codex `prepare()` returns the existing session ID, empty on a fresh activation.
  Its header records the preassignment deviation; the real thread is learned
  from output and reported in the terminal envelope, without durable registration
  into the live handle. Resume has no `-s`/`-C`; config overrides and process cwd
  restate its bounds. `workflow_interpreter/profiles/codex.py:59`,
  `workflow_interpreter/profiles/codex.py:205`,
  `workflow_interpreter/profiles/codex.py:241`.
- `Steerer` requires a resumable ID before recording intent or killing anything.
  It persists intent, proves termination, closes `steered`, and mints a
  continuation. Fresh Codex runs are consequently unsteerable through this path.
  `workflow_interpreter/supervisor/steer.py:108`,
  `workflow_interpreter/supervisor/steer.py:186`.
- `Foreman.run` repeats ticks, stops on gate/halt/terminal/stall/wall expiry, and
  sleeps only for blocked/contended reports. The bridge uses this same driver.
  CLI `run` emits its aggregate result after the loop. `supervise` launches the
  detached activation wrapper, which owns liveness and time enforcement.
  `workflow_interpreter/foreman/tick.py:558`,
  `workflow_interpreter/bridge/command.py:376`,
  `workflow_interpreter/foreman/__main__.py:584`,
  `workflow_interpreter/foreman/__main__.py:617`,
  `workflow_interpreter/foreman/compose.py:100`.
- **Refusals are partly surfaced, not wholly absent:** gate intake writes
  `refusal.json` and returns its reason; `tick` includes `refusals`. However,
  status does not read those files, and `run` neither stops nor sleeps solely
  because a report contains refusals. Repeated invalid approval can spin until
  another stop condition. File-write errors are swallowed by intake. Evidence:
  `workflow_interpreter/foreman/gates.py:233`,
  `workflow_interpreter/foreman/tick.py:424`,
  `workflow_interpreter/foreman/tick.py:574`,
  `workflow_interpreter/foreman/__main__.py:639`.
- Re-entry binds only the node's declared `inputs`. Instance inputs come from
  pinned root metadata; node inputs choose the latest completed producer (same
  round preferred within a region) and materialize a pinned diff/output tree.
  There is no engine verifier source. A self-loop therefore gets task inputs
  and any available review findings, not the failure that caused rework.
  `workflow_interpreter/foreman/inputs.py:62`,
  `workflow_interpreter/foreman/inputs.py:160`.
- Host verification already stores combined stdout/stderr tails: **2 KiB per
  attempt**, not 16 KiB. The final exit code and all attempt tails are retained;
  earlier attempts' individual exit codes are not. `inspect` renders red tails
  from completion evidence. `workflow_interpreter/supervisor/verify.py:105`,
  `workflow_interpreter/supervisor/models.py:735`,
  `workflow_interpreter/foreman/tick.py:177`.
- Envelope accounting counts UTF-8 bytes and framing, drops optional sections
  by descending `trim_priority` then source name, and refuses if mandatory
  content still exceeds the bound. `workflow_interpreter/foreman/envelope.py:64`.

## 2. Design

### A. Named execution profiles and private offline toolchains

**Decision.** Separate **runner** (vendor/protocol) from **execution profile**
(filesystem/tool policy). Use two names initially: `writer` and `reviewer`.
Both permit local checks; writer additionally permits the checkout subset and
candidate commit. A third `verifier` profile would imply authority that a model
activation does not have. Host verification remains `ExitObserver`/`run_checks`;
a test-authoring node is a writer. A check-only model node is a reviewer.

Introduce `ExecutionProfileName` and frozen `ExecutionPolicy`, plus a frozen
resolved `ExecutionGrants` model under `supervisor/execution.py`. Policy is
closed engine data, not a graph-authored permission object. Grants carry explicit
checkout read root, process cwd, writable directory tuple, channels, scratch,
private cache, Git directories, final read-only pins, and policy version.
`TaskSpec` gains `execution_profile` and `checkout_read_root`; one resolved grant
object feeds outer mounts and vendor translations. Vendors retain different
flag spellings, not separate authority calculations. Validate that reviewer
channels/cache/scratch are outside the checkout and outside protected records.
This addresses cr-o85.10 without claiming read confidentiality for the whole host.

| Named profile | Checkout | Git | Channels/scratch/cache | Local checks |
|---|---|---|---|---|
| writer | Readable; only `allowed_paths` directory prefixes writable through outer mounts | Existing instance-scoped commit grants and final pins | Private and writable | Yes, offline |
| reviewer | Explicit read root; no checkout write root | Read-only | Private and writable | Yes, offline, subject to runner qualification |

**Network settled (Q1).** Network enforcement is best-effort and never a
blocking requirement. Named profiles carry `tool_network = "denied" |
"not_enforced"` as a recorded fact, not an admission predicate. Codex records
`denied` through its existing `network_access=false`; Claude writer and Claude
reviewer are both allowed under named profiles and record `not_enforced`.
Expose the fact in `LaunchReceipt` and status. Missing tool-network enforcement
must never refuse either Claude profile. Do not implement `--unshare-net` around
the entire vendor; its model transport still needs network access.

Vendor mappings: Codex keeps `workspace-write`, reviewer cwd=channels,
`exclude_slash_tmp=true`, network=false, and the existing ambient-config
suppression. Cache grants now precede the reviewer return. Writer's broader
vendor cwd is still intersected with outer mounts. Claude keeps its writer path
rules; named reviewers gain Bash for local checks, with the checkout read-only
under outer bwrap and channels/scratch/private cache writable. Record
`not_enforced` for both Claude profiles rather than claiming shell-network denial.
Legacy pinned reviewer behavior remains unchanged. Opencode continues to refuse
for its existing unboundable permission/configuration reason only; the network
fact adds no new refusal. Keep host `/tmp`/home residuals explicit; no container
migration, broad home remapping, or claims of full host isolation in this bundle.

**Migration.** Add optional `node.execution_profile`, omitted from canonical
serialization when absent. For new named nodes, reject authored or override
`writes` authority and reject nonempty `allowed_paths` on reviewers. Derive the
internal effective `writes` boolean from policy for existing consumers, including
base-commit derivation and grading. Resolve policy once at root creation and pin
its version and effective meaning. Legacy pinned roots retain their historical
resolved `writes`; reading them must not change their canonical hash. New named
profiles cannot dispatch with `sandbox=off`. Update shipped graphs and their
fixture twins with the recorded network fact for their configured runner; never
substitute a vendor or model silently. Keep ADR 0001's disclosure/effect reporting
semantics separate from physical grants; amend its network/profile discussion explicitly.

**Cache first, independently of profile migration.** Use two levels. Level 1
is a host-owned per-project seed cache under supervisor configuration, keyed by
project identity and lock digest. Build it once with `uv sync --locked`
(dependency-only, builds disabled), then reuse it until the lock changes. The
configured host cache reported by `uv cache dir` is 24 GB on this host
(coordinator-supplied fact); it is never copied wholesale. The project seed
contains only that project's locked dependency cache, not the whole host cache.

Level 2 replaces the wrapper-wide writable cache with
`<activation-dir>/toolchain/uv-cache` and its `python` child, outside channels and
the checkout. Only that subtree is granted, not its parent. Every activation,
including retry and resumed activation, receives a fresh private dependency-cache
copy from the project seed, never from `uv cache dir` or a previous activation.
Copy the selected interpreter separately from the host uv-managed Python
directory discovered by `uv python dir`. Never retain the wrapper-wide writer
cache. Bind the host seed, configured host uv cache, and managed Python source
directories read-only in the outer plan, last, so Claude cannot bypass the private
path through their normal host paths. Refuse overlapping source, checkout,
grant, or destination layouts. This closes the named cache channel; it does not
erase the outer sandbox's other host-path residuals.

Host configuration declares repo-relative toolchain project directories (default
root when it has `uv.lock`), rather than recursively discovering projects from
writable grants. Pin lock, `pyproject.toml`, and interpreter-selection digests
from the admitted base; record the actual managed interpreter version. `.python-version`
and project Python requirements select the interpreter; a lock alone need not
select an exact patch version. A graph without a declared uv project needs no
uv seed. Local edits requiring new dependencies produce an actionable refusal;
the toolchain path does not refresh the host lock or fetch dependencies from
an activation; `UV_OFFLINE=1` applies even where tool network is not enforced.

A host-owned `ToolchainSeeder` consumes those pins, the configured project-seed
root, and injected host paths discovered through `uv cache dir` and `uv python dir`.
It produces `SeedReceipt` (project seed key, project/pin digests, interpreter
version, uv version, copied logical bytes, copy method, offline probe result,
whether host fetching was needed). Include
that receipt in `LaunchReceipt`; partial preparation gets a distinct diagnostic,
not a false successful launch. The wrapper runs seeding after worktree preparation
but before the fork barrier releases any vendor, with explicit timeout/byte/free
space bounds from supervisor config.

Build a missing project seed in a temporary sibling under a per-seed-key lock;
validate, fsync, and atomically publish it before any activation copies it. An
existing complete seed with the same lock digest skips `uv sync --locked`. For
each activation, copy its dependency seed and selected interpreter into a
temporary sibling with `cp --reflink=auto` and ordinary-copy fallback, validate,
fsync, then rename into place. Never use host-to-private hardlinks or symlink
mounts. Internal relative symlinks must resolve inside the
copied tree; reject escaping links and special files. Measure the project seed
and selected interpreter, enforce configured size limits, and report bytes.
The 24 GB whole-host cache is never the activation copy source.
Serialize preparation per activation; a completed prelaunch seed with matching
pins is reused only after its offline probe passes. A copy interrupted by a crash
is not a seed. No cleanup may touch host sources or another activation.

Probe with the private cache/interpreter, scratch venv, and `UV_OFFLINE=1`;
for the declared Python development toolchain the acceptance probe is
`uv run --frozen ruff --version`. Set `UV_OFFLINE=1` on dispatched child env too.
On a project seed miss, run the bounded host `uv sync --locked` preparation
against admitted pins with `UV_CACHE_DIR` directed to the project seed. Reuse
already cached required artifacts from the configured host cache through a
dependency-scoped import; never copy that cache wholesale or use it as the
activation source. Only the host fetches genuinely missing artifacts. Do not
rebuild a completed seed or fetch again merely because an activation destination
is empty. Do not run arbitrary project build hooks while preparing the seed:
use dependency-only installation with builds disabled; missing wheels or required
project builds get a named preparation refusal. Exact uv options must be checked
against installed help before implementation. Never execute a previously runner-writable seed on the
host to “validate” it after launch; receipt reattachment takes precedence.
Host grading uses its own trusted environment, never this private mutable cache.

**Private-copy lifecycle.** Private toolchains are disposable, not evidence.
After host verification and durable activation close, remove only that activation's
private toolchain and retain `SeedReceipt` as its toolchain provenance. Keep the
host-owned project seed for reuse. Cleanup is idempotent and does not run while
an activation may still be executing: retain the private copy across crashes
until recovery classifies the activation and proves any runner is dead. Recovery
then completes verification/close as applicable and retries cleanup, including
crashes after close but before deletion. Report cleanup failure and retry on
recovery; do not delete another activation's directory or host sources.

The copy lands for both writer and reviewer in slice 1. Codex reviewers gain only
the external private cache grant; named Claude reviewer checks land with the
profile mapping in slice 2, recording `not_enforced` without a network gate. Keep
venv, Ruff, mypy, pytest caches in scratch. Acceptance does not require nested bwrap
inside a sandbox: the coordinator's NETLINK_ROUTE failure is a supplied host
constraint, not something to repair. Local checks remain claims; host checks
supply proof.

**Rejected alternatives.**

- Shared writable cache: lets one activation poison another and the host.
- Read-only shared cache alone: uv still needs mutable cache/runtime locations.
- Hardlinks/symlinked copies: inode/path sharing defeats private ownership.
- Copying the whole host cache: duplicates 24 GB instead of the project dependency set.
- Retaining closed activations' private caches as evidence: receipts preserve provenance without disposable toolchain data.
- Mandatory network enforcement: contradicts the settled best-effort, nonblocking contract.
- Third model “verifier”: duplicates reviewer permissions and confuses evidence authority.
- Full disposable container migration: changes authentication and transport scope without qualification.

**Files touched.** Create `supervisor/toolchain.py`, `supervisor/execution.py`
under `workflow_interpreter/`; modify its
`supervisor/{sandbox,launch,models,profile,config,paths,recover}.py`,
`profiles/{_base,codex,claude,opencode}.py`, `schema/{models,rules_references}.py`,
`schema/graph_schema.json`,
`foreman/{resolve,execution,inputs,config,__main__,close}.py`, and
`bdio/{roots,mint,wire,carriers}.py` for pinned contract compatibility as needed.
Update `config/foreman.example.toml`, `workflows/README.md`, the affected workflow
TOMLs and fixture twins, `docs/specs/workflow-interpreter.md`, ADR 0001, and add
`docs/usage/engine-bundle.md` with seed diagnostics/manual host preparation.

**Tests to add.** Stub-uv cold/warm/missing-host paths; build the project seed once
per lock digest; reuse it across activations; rebuild on lock change; never copy
the whole host cache; copy only the selected managed interpreter; concurrent and
interrupted seed publication; reflink/plain-copy fallback;
byte-identical contents with distinct host/private and cross-activation inodes;
mutation isolation; interrupted copy recovery; pin mismatch; timeout/disk limit;
escaping symlink refusal; host-cache direct writes denied; no host fetch on warm
cache; Codex network denial retained; named Claude writer/reviewer launch with
`not_enforced` visible in receipt/status; reviewer offline probe with checkout-write,
Git-write, wrapper-record-write attempts denied; private-copy cleanup after host
verification and close; `SeedReceipt` and project seed retained; idempotent cleanup;
crash retention until recovery classification/death proof; recovery cleanup after
a crash between close and deletion. Extend
`tests/test_codex_writer_qualification.py::test_a_reviewer_can_write_its_channels_and_nothing_of_the_checkout`
and the sandbox/launch/profile process tests. Add named-profile compatibility,
legacy canonical-hash, effective-writes override/base-commit, unsupported-runner,
and launch/resume grant parity tests. New files: `tests/test_toolchain_seeding.py`
and `tests/test_execution_profiles.py`.

**Risk.** Cache copying is trusted host execution over filesystem data; avoid
running candidate build code or reusing tainted private copies there. Disk cost
scales with project seed keys and live/unclassified private copies, rather than
all historical activations. Optional receipts preserve old record readability;
old roots remain legacy rather than silently acquiring stronger guarantees.
Claude tool-network access remains unenforced and visible as a recorded fact.

### B. Host verify feedback as an engine source

**Decision.** Add the exact source producer `engine:verify_failure`, always
optional, with ordinary `trim_priority`. Only writer consumers may declare it;
shipped graphs attach it to their implementer inputs, never reviewer inputs.
Do not hardcode the literal node name `implement` in the engine.

Bind against the **causal predecessor**, not the latest failed node in the whole
history: a writer re-entry whose taken edge is `fail_code`, with closed host
completion evidence containing a failed check. Follow a verified exhaustion /
rebudget gate's `source_activation_id` when it represents that same failure.
The predecessor can be the same implementer or another node whose failed host
check routes to it; eligibility is the actual edge and host evidence, not a
hardcoded producer role.
Infra retry or steer of this rework inherits its bound source; it does not search
for a newer failure. Other entry outcomes, including reviewer rejection, get no
verify-failure source. A marker-only fail_code with no failed host check has no
such source. A declared reviewer consumer is rejected at root creation.

At mint, produce `VerifyFailureBinding` identifying root, source activation,
completion evidence digest, and a canonical bounded payload digest. Persist it
with the input bindings; materialization verifies its identity. Read protected
host completion evidence, not `run.jsonl`, a candidate path, or a caller-supplied
instance input. Introduce a typed engine-source branch in schema validation,
producer classification, binding validation, bounded materialization, and
reference-mode export so `producer_node() == None` no longer means all producers
are instance inputs. Before mint, store the canonical payload as a Git blob pinned
under the engine's protected `refs/wf` namespace, with its SHA-256 alongside the
object ID. Materialize by object ID and verify the digest; do not depend on a
mutable file path or retain a runtime dependency on `completion.json`. Reference
mode exports a read-only copy using the existing evidence-export boundary.
Retain the pin for the instance evidence lifetime. A binding that was recorded but
is missing/tampered is a refusal; it is not silently omitted as optional.

Use the existing **2 KiB per-attempt evidence cap** initially; 16 KiB cannot be
recovered from today's records. Render each finally failed check's `cmd` as its
name, final exit code, timeout/provenance/error fields, and retained attempt tails,
with a **16 KiB total payload cap** and explicit omitted-check/byte counts.
Do not invent per-attempt exit codes. Prefer the last attempt's tail when the
aggregate cap cuts a check. Stable check ordering makes the payload deterministic.
Large-output capture improvements are outside this feedback change.

Label output as host-observed diagnostic data, not instructions. Feed the source
through the existing composer so UTF-8 bytes, headings, mandatory facts, omissions,
and descending trim priorities retain their meaning. Report the source under
`input_envelopes.included`, or a missing/budget omission. Pointer inputs still
point to immutable engine evidence with the same provenance and size limits.
No changes to grading, rounds, no-progress behavior, or signed gates.

**Rejected alternatives.**

- Append tail text directly to the brief: bypasses provenance and budget accounting.
- Search latest same-node failure: can attach unrelated or stale evidence.
- Use `node:implement`: currently means a candidate artifact, not host evidence.
- Increase all durable tails to 16 KiB now: storage expansion is unnecessary to fix missing feedback.

**Files touched.** `workflow_interpreter/schema/{models,graph_index,rules_references,rules_flow}.py`,
`schema/graph_schema.json`, `foreman/{inputs,cases,supervise,evidence_export}.py`,
`bdio/{carriers,mint,wire}.py`; create `foreman/verify_feedback.py`. Amend spec
§2/§5.5 and the implementer source declarations in shipped graphs/fixture twins.

**Tests to add.** Extend `tests/test_foreman_inputs.py`,
`tests/test_foreman_fail_code_routing.py`, `tests/test_foreman_envelope.py`, and
pointer-input tests: two-round failure feedback; absence initially/after non-fail
outcomes; cross-node fail_code into a writer; rebudget lineage; retry inheritance;
unrelated failure excluded;
reviewer rejected; missing/tampered bound evidence refused; UTF-8/aggregate caps,
stable trimming, legacy evidence, and status inclusion. Exercise real mint →
composition with fake runners, rather than only testing a formatter.

**Risk.** Failure output can contain attacker-controlled text; provenance means
“the host captured this,” not that its content is trusted instruction. Binding
must survive a wrapper restart and cleanup without depending on a mutable log.

### C. Durable monitor, wake events, and visible refusals

**Decision.** Use the QM comparison's cursor/fire pattern, not its infrastructure.
The read-only reference is the orchestrators checkout's
`docs/research/agent-systems/comparison/qm-vs-workflow-interpreter.md` (QM
`e0b8686`). Its table's blanket claim that our network is denied is corrected by
section 1 above.

Add a shared `DriverObserver` used by `Foreman.run` and the child-drive loop.
The bridge already calls `Foreman.run`. After each completed tick atomically write
`<instance-dir>/driver-heartbeat.json`: schema version, instance/root identity,
driver generation and identity (host/boot/PID/start time), tick count, timestamp,
root state, current activation/gate IDs, refusal count, last condition, and
per-active-log identity plus `run.jsonl` byte offset. Write starting and stopped
records too; a hanging tick leaves a stale heartbeat. Heartbeat says the driver
is responsive, not that the model made progress. Refusal count counts distinct
refusal identities, not repeated writes of the same failed signature.
Gate intake durably appends each distinct refusal identity and bounded detail to
an instance condition journal before returning the refusal. The monitor consumes
that journal by offset; a later corrected approval may remove `refusal.json` but
cannot erase an unseen condition. Journal write failure is reported as degraded
durability, never hidden behind a healthy heartbeat.

Monitoring is **opt-in**. The driver always writes its heartbeat and refusal
journal, whether or not a monitor is running. Add the separate host command
`foreman monitor <root>` with injected clock and bounded polling: the driver
cannot detect its own SIGKILL or stale heartbeat. Ordinary `run` and
`phase-bridge` do not start a monitor or refuse startup when one is missing.
Only an explicit `--monitored` flag requires an independently started monitor
with an identity-proven handle and startup acknowledgment before work starts;
refuse that explicitly monitored startup if the check fails. It must not share
the driver's kill group or die-with-parent setting. A per-instance local lock prevents two local monitors;
this is not a multi-replica lease system. An operator can restart the monitor
command after machine/monitor failure; no claim of detection while the whole host
is down. On restart, reconcile durable events and current state before polling.

Conditions and stable cursors:

| Condition | Cursor identity |
|---|---|
| gate opened | Gate's immutable gate key; discover from durable gate records even after a crash |
| root terminal | Root terminal identity/state, once per instance |
| refusal | Gate key + payload/signature digest + bounded refusal digest; repeated identical intake does not create a new condition |
| driver exit/loss | Driver generation + identity + stopped record or proven process loss |
| heartbeat stale | Driver generation + last advancing tick; one fire per stale episode until heartbeat advances |

Use log identity (activation plus file generation) alongside offsets so truncation
or activation change cannot look like forward progress. No transcript reads are
needed for the named wake conditions. Metadata-only polls suffice. Raw output and
quiet-heartbeat notifications from QM are not extra wake triggers in this bundle.
A normal stop at a gate still records driver exit; it is a separate event with
an expected reason, rather than a duplicate gate key.

`WakeCursor`, `DriverHeartbeat`, `WakeEvent`, and `WakeDelivery` are frozen typed
records. Fire key is a domain-separated hash of instance key, condition, and
cursor. Add `WorkflowStore.append_wake_event`, re-find by key, verify identical
payload, and return the existing event after an ambiguous write. Extend bd event
encoding with a distinct wake discriminator while preserving existing transition
event decoding/backfill. Wake events never count as activations or satisfy a
transition, approval, or rebudget. Audit/readers must understand both event shapes;
do not fake `from/outcome/to` to fit `EventPayload`.

Persist observed/pending cursors before delivery; only advance delivered state
after the bd event is confirmed. Minimum fire interval defaults to 30 seconds,
monitor poll to 5 seconds, stale threshold to 120 seconds, and a lifetime cap to
100 distinct events per instance. Bound the condition journal and pending set to
that lifetime allowance, with 8 KiB per condition record; reserve a small fixed
status record for saturation rather than appending unlimited overflow events.
Validate positive bounds and stale threshold
above normal poll spacing. Pending distinct conditions survive throttling and
restart; they are not discarded by advancing a cursor early. Reconcile cap usage
from durable events. After cap exhaustion, publish `wake_cap_exhausted` in local
status/log and stop firing; event guarantees are explicitly within that cap.
Refusal repetitions cannot burn it down by changing only file mtime.

After durable event creation, run optional trusted-config `hook_argv` without a
shell, with a compact JSON status including fire key on stdin (8 KiB cap), a
10-second timeout, bounded stdout/stderr, and no model call. Config owns hook argv;
refusal text and runner output cannot select an executable. Delivery is
**at-least-once**, with the receiver deduplicating fire key: a crash after hook
execution but before acknowledgment can repeat the hook. Journal attempts and
allow at most three per fire with bounded backoff; expose exhausted delivery.
Exactly-once external side effects are not promised. The hook may enqueue a NEW
coordinator turn; it never injects into the current activation.

Status includes refusal gate/path/error/reason, heartbeat age, monitor health,
pending fires, last delivery error, and cap state. Log each new refusal at error
level with gate identity; repeated failures remain visible without repeated full
payloads. Make `run` return an attention report on refusal, with CLI nonzero status,
rather than busy-spin. A corrected signed payload can be consumed on the next
invocation under the existing gate verification. Preserve refusal history in wake
events even when successful intake removes `refusal.json`. Report failure to write
that file rather than swallowing it; never claim durable delivery when bd is down.

**Rejected alternatives.**

- Driver-only monitor: cannot observe its own death or a stuck tick.
- LLM/log polling: spends judgment on deterministic activity detection.
- Hook before bd event: loses the durable explanation and replay key.
- Exactly-once hook claim: impossible across an arbitrary subprocess side effect and local acknowledgment.
- Fire every tick/mtime: duplicates refusals and defeats rate limits.

**Files touched.** Create `workflow_interpreter/foreman/{heartbeat,wake,monitor}.py`
and `workflow_interpreter/bdio/wake.py`; modify
`foreman/{tick,children,__main__,config,compose,gates}.py`,
`supervisor/paths.py`, and `bdio/{api,keys,wire,records,reads}.py` plus exports.
Update `bridge/command.py` for monitored startup/error propagation,
`config/foreman.example.toml`, spec §8.2, and `docs/usage/engine-bundle.md`.

**Tests to add.** `tests/test_foreman_wake.py`, `tests/test_bdio_wake.py`, plus
run/status/gate/bridge tests: heartbeat and refusal journal without a monitor;
ordinary startup succeeds with no monitor; `--monitored` requires a healthy
monitor; driver stub exits or hangs; separate monitor survives
its termination; cursor reset; gate recovery between polls; refusal dedupe;
stale episodes and recovery; rate-limit pending delivery; lifetime cap across
restart; crash before/after bd write and hook acknowledgment; hook timeout/error;
no shell expansion; no model invocation; wake events excluded from routing and
activation bounds. Real bd tests use isolated test databases, never task records.

**Risk.** The monitor is another host process with a lifecycle to own; it needs a
restart command and health reporting. A durable event is not proof that an external
coordinator received it. Monitored execution promises no wake when its host and
monitor are both unavailable.

### D. Codex app-server as a second runner, last and fixture-qualified

**Decision.** Add `RunnerName.CODEX_APPSERVER = "codex-appserver"` behind the
existing task/profile dispatch contract; keep `codex` exec as the default and
explicit fallback choice. No automatic fallback after an ambiguous launch or
turn submission. Pin app-server to codex-cli **0.154.0** initially. Local
`codex --version` returned that version; its `app-server --help` identifies an
experimental stdio service. Neither command qualifies actual model execution.

The official [Codex App Server documentation](https://learn.chatgpt.com/docs/app-server)
describes `initialize` → `initialized`, `thread/start` or `thread/resume`, then
`turn/start`; completion is a `turn/completed` notification. `turn/steer` appends
input to the active turn using `expectedTurnId`; `turn/interrupt` requests
cancellation. These are protocol facts, not our engine's recovery semantics.
The QM `src/harness/codex-app-server.ts:142`–`:201` client illustrates separate
stdio pipes and initialization; use it only as protocol-shape reference. The
installed version's generated schema is the implementation authority; commit
only the exercised fixture/schema subset with version provenance in slice 4.

**Transport ownership.** One app-server process per activation, inside the same
bwrap plan, one model turn per activation. Extend launcher I/O with a closed
`RunnerTransport` enum (`event-log`, `stdio-rpc`) and host-owned pipe endpoints.
The existing exec path keeps its current stdio. The wrapper owns the RPC client,
request IDs, bounded frames, stderr drain, deadlines, normalized `run.jsonl`, and
shutdown; the runner gets no bd handle or host-hook execution capability.
Drive RPC and runtime enforcement together with bounded polling/nonblocking I/O,
so a blocked request never postpones `max_wall` or stale termination.

Do not put a trusted Python adapter inside the runner's writable environment and
let it rewrite launch evidence. The outer receipt/ledger still identifies the
bwrap/app-server process before exec. After handshake, correlate the
`thread/start` response ID and atomically register `{launch_id, activation_id,
process identity, thread_id}` in a protected `session.json`; mirror it through a
typed identity-checked bdio registration before sending `turn/start`. Repeating
registration with the same identity is a no-op; a different thread or launch is
an integrity error. Preserve the original process identity and receipt. Recovery,
steer lookup, and status consult the registration, rather than trusting arbitrary
log text. Ordinary tool output saying `thread.started` is never registration.

This fixes durable early thread registration for **the new runner**, not for
legacy `codex exec`. It does **not** literally satisfy today's §5.2 “session ID
before process exec”: app-server must already be running to create a thread.
Amend §5.2 explicitly to distinguish process identity before exec from vendor
session identity before the first model turn. Process crash atomicity remains;
thread/turn RPC introduces additional crash windows that need explicit evidence.

Persist turn-start intent before submission and its returned turn ID when known.
Never resend an ambiguous `turn/start` to an adopted process. If the wrapper dies,
use existing identity/death proof and transport-error recovery, preserve any
artifact, and start a bounded retry activation; do not reconnect to an orphaned
stdio pipe or assert an unknown turn never ran. A wrapper crash before registration
may leave an unused vendor thread, but no turn was authorized. Between turn
submission and acknowledgment the outcome is unknown and must be reported as such.
On `turn/completed`, flush telemetry, close stdin/request shutdown, wait boundedly,
then TERM/KILL if required. A server exit alone is not successful model completion;
require successful turn status, process termination, and existing outcome/artifact/
host-check grading. Interrupt acknowledgment alone is not proof of process death.

**Control semantics.** Preserve default §8.1 `steer` as persist → terminate →
continuation for all runners. Add explicit experimental `steer --in-place` for
app-server: durable intent keyed by activation/control sequence, bounded text,
identity/expected-turn check, RPC acknowledgment, no new activation or review
round. Count both modes against `max_steers`, including persisted ambiguous
requests, so the new path cannot bypass the cap. Do not replay an unacknowledged
in-place steer after wrapper failure; mark uncertain, expose attention via C,
and require a subsequent deliberate control action. Termination uses RPC interrupt
as a courtesy before existing bounded group death proof. The wrapper receives
control through a host-owned bounded inbox outside channels; it validates target
identity and writes acknowledgments. This is separate from the monitor, which
never steers. Amend §8.1's “none supports mid-turn input” claim for this runner.

**Resume across rounds.** Add graph-pinned `session_reuse = "fresh" | "same-node"`,
default fresh and app-server-only. Choose the latest eligible registered thread
of the same root and node, with a completed prior turn and matching execution
policy, runner version, model, and effort. Bind its source activation durably at
mint. Never share writer/reviewer threads or resume an ambiguous live turn.
Every new process reapplies grants, current cwd, channels, tool configuration,
and the complete bounded current envelope before its single turn. Use a
host-owned session-state directory per root/node for intentional history reuse;
keep it read-only to model tools, distinct from mutable toolchain caches. Pin
its path/ownership in the launch state and qualify that vendor state can persist
without giving tool commands authority over it. No ambient user-config/MCP
inheritance or restored dynamic tools may widen policy on resume.

Fresh reviewer sessions remain the default: remembered verdicts create anchoring
risk. Resume is a cost hypothesis, not a fix for cr-o85.34.30. Record per-turn and
cumulative input, cached input, output, and unknown fields separately; derive
activation deltas without summing cumulative notifications. Keep envelope bytes
visible alongside token usage. Comparing a second live run with the earlier
baseline is outside this bundle, so that bead's measurement acceptance stays open.

**Protocol strictness.** Validate request/response IDs, thread/turn IDs, frame
size and types with frozen models. Pin a closed set of recognized notifications,
including explicitly ignored informational ones. Unknown notifications or server
requests fail loudly with bounded diagnostics and terminate the activation;
never silently drop permission-relevant events. Dynamic tools are disabled;
`item/tool/call` is answered with a bounded unsupported-tool error, never executed
on the host. Reject approval/escalation requests; no unattended permission
promotion. Separate stderr from protocol frames and avoid logging credentials.

**Rejected alternatives.**

- Replace exec now: makes every workflow depend on an experimental protocol.
- Bare `codex app-server` argv swap: stdin is currently null and no client would start a turn.
- Spawn server in `prepare()`: escapes the established launch barrier and sandbox owner.
- Register from merged `run.jsonl`: runner-controlled text becomes session authority.
- Reuse one server across activations: changes process ownership and recovery scope.
- Automatic reviewer resume or promised token savings: biases review and lacks measurement.

**Files touched.** Create `workflow_interpreter/profiles/{codex_appserver,codex_rpc}.py`
and `supervisor/{rpc_session,control}.py`; modify
`profiles/{config,registry}.py`, `supervisor/{profile,launch,run,monitor,recover,steer,models,paths}.py`,
`bdio/{api,supervision,mint,wire,carriers}.py`,
`foreman/{__main__,config,resolve,execution,inputs}.py`, `schema/models.py`,
`schema/graph_schema.json`, example config, spec §§5/6/8.1, and usage doc.
New fixtures: `tests/fixtures/codex_appserver/` (fake executable and bounded
versioned protocol messages). New tests: `tests/test_codex_appserver.py` and
`tests/test_codex_appserver_recovery.py`; extend dispatch/steer/usage tests.

**Tests to add.** Fake process handshake; correlated registration before turn;
fragmented/oversized/invalid frames; interleaved stderr; unknown notifications;
server requests denied; wrong identity; duplicate responses; usage deltas;
turn success followed by shutdown; exit without terminal notification; hung
shutdown; crash before/after receipt, registration, and turn send/ack; no duplicate
vendor exec on re-tick; in-place cap and ambiguous delivery; default steer death
proof; per-node resume with refreshed permissions and channels; reviewer history
not inherited by writer; version mismatch refusal; same sandbox writer/reviewer
contract as exec. No live model qualification or token-cost benchmark in this slice.

**Risk.** This is the largest slice: RPC lifecycle, durable session state, and
control semantics cross the existing one-shot seam. Keep it opt-in and last.
Fixture-green means protocol/recovery behavior against the fixture, not a
production-qualified app-server or a fulfilled cost-reduction claim.

## 3. Slice plan

All implementation is test-first, solo, only after “implement slice N.” Each
slice owns its code, tests, spec amendments, and usage changes in one independently
landable conventional commit. No pushes. No Beads writes by this session.
Later slices use the earlier contracts; no earlier slice requires app-server.

### Slice 1 — private cache seeding (lands first)

- Serves cr-02ze.20 and the first safe increment of cr-02ze.6.
- Consumes existing `TaskSpec`, activation identity, admitted dependency pins,
  injected host uv locations, and supervisor configuration.
- Produces reusable project seeds keyed by lock digest, `SeedReceipt`,
  activation-private cache paths and close/recovery cleanup, read-only host source
  pins, offline child env, and matching Codex launch/resume cache grants.
- Owns A's toolchain module and cache-specific launch/sandbox/model/profile/test
  changes. Does not require the named-profile schema; Q1 is settled.
- Exit criterion: build each project seed once per lock digest; a cold activation
  destination copies only that seed and the selected managed interpreter and runs
  offline, with no whole-host cache copy or redundant fetch. Private mutation
  cannot affect another copy/seed/host; Codex reviewer runs the probe and cannot
  write checkout, Git, or wrapper records. Private toolchains are deleted after
  host verification and close, with receipts retained; crash copies survive until
  recovery classification and death proof, then cleanup is retried. Old receipts
  still load. Preparation failures do not release the fork barrier.
- Risk focus: copy ownership, symlinks, tainted-cache host execution, crash cleanup.
- Proposed commit: `feat(supervisor): seed private offline activation toolchains`.

### Slice 2 — named execution contracts and causal rework feedback

- Serves cr-02ze.6, cr-o85.10, cr-02ze.19. Depends on slice 1; Q1 is settled.
- Consumes private seed/grant paths; produces pinned `ExecutionPolicy`/
  `ExecutionGrants`, explicit checkout read root, derived effective writes,
  recorded `tool_network` in receipt/status, and `VerifyFailureBinding` with
  bounded engine evidence.
- Owns A's remaining schema/migration work and B's entire input path. These form
  one usable loop: a qualified writer re-enters with the check evidence and tools
  needed to act, while reviewers retain zero checkout writes.
- Exit criterion: two-round fake-runner workflow exposes failed host check data
  in rework and status; Codex records `denied`, and both named Claude profiles
  launch and run local checks with `not_enforced` in receipt/status, without a
  network-enforcement refusal. Profile conflicts fail early; opencode retains
  only its existing refusal. Legacy pins still decode unchanged; reviewer inputs
  never receive this engine source.
- Risk focus: graph/config pinning and causal binding, not vendor string naming.
- Proposed commit: `feat(foreman): pin execution profiles and bind verify rework evidence`.

### Slice 3 — durable wake and refusal reporting

- Serves cr-02ze.21; lands on slices 1–2's explicit activation/status contracts.
- Consumes driver tick reports, protected records, instance identity, and pinned
  execution/evidence metadata. Produces heartbeat, monitor handle, wake events,
  durable cursor/delivery state, and compact status for host hooks.
- Owns C, including the separate monitor lifecycle and typed bd event reader
  compatibility. The monitor remains useful with legacy exec runners.
- Exit criterion: ordinary runs write heartbeat/refusal journal without requiring
  a monitor; only `--monitored` gates startup on monitor health. With the separate
  monitor running, walk away from a stub-driven run; gate, refusal, terminal,
  proven driver exit, and stale heartbeat each produce a deduplicated durable
  event within configured bounds. Restart replays pending delivery without
  duplicate events; invalid approval stops the driver visibly.
- Risk focus: event-vs-hook delivery guarantees, local lock ownership, monitor death.
- Proposed commit: `feat(foreman): add durable wake events and driver heartbeats`.

### Slice 4 — experimental app-server runner

- Serves cr-02ze.4/cr-o85.15 for the new runner and supplies measurement plumbing
  for cr-o85.34.30. Depends on A's grants, B's fresh rework envelopes, and C's
  attention/wake reporting for ambiguous control and transport failure.
- Consumes `TaskSpec` and resolved execution grants; produces early registered
  session identity, one-turn RPC execution, explicit in-place control, optional
  same-node resume, and normalized usage through the existing runner envelope.
- Owns D, including launcher pipe support, supervisor recovery integration,
  specification amendments, strict protocol fixture, and tests.
- Exit criterion: fake-process end-to-end dispatch, control, completion, resume,
  and crash-window tests pass under the same outer bounds; exec regression tests
  pass. No shipped role silently switches to app-server.
- Risk focus: exactly-once process launch versus ambiguous RPC delivery; vendor
  state persistence and strict schema drift. Live qualification remains separate.
- Proposed commit: `feat(profiles): add fixture-qualified codex app-server runner`.

### Verification and handoff for every implementation slice

Run from repo root, record output, exit status, and skips:

1. `uv run pytest -q -m "not bd and not live"`
2. `uv run pytest -q -m proc`
3. `uv run pytest -q -m bd`
4. `uv run pytest -q -m acceptance`
5. `uv run ruff check workflow_interpreter/ tests/`
6. `uv run ruff format --check workflow_interpreter/ tests/`
7. `MYPYPATH=. uv run mypy --strict --explicit-package-bases workflow_interpreter/`
8. `git diff --check` and `git status --short`.

The proc/nested-sandbox gate must run on the host where bwrap works; a skipped
physical-bound test is not its qualification. No marker exclusions beyond the
commands above, no weakened verifier pins, and no live model run implied by a
fixture test. Real bd tests require an isolated writable test database; the
read-only task database failure does not justify touching coordinator task state.
Do not commit a slice until required gates are green; report actual red/blocked
checks and preserve the work if the environment prevents them. Stage explicit
slice files only. Handoff names changes, exact validation, remaining failures,
commit, and unperformed live qualification. cr-o85.34.30 cannot be closed by this
bundle because its acceptance requires a second live measurement.

Phase 1 validation is a source/requirements self-review, path/format checks, and
Git scope check. No implementation suite or independent-agent review is claimed;
the coordinator supplies the independent review after this document is delivered.

## 4. Coordinator rulings — settled

No open questions remain from Phase 1.

1. **Q1 — network:** best-effort and never blocking. Record `tool_network` as
   `denied` for Codex and `not_enforced` for Claude writer/reviewer, visible in
   receipt and status. Both named Claude profiles are allowed; opencode retains
   its existing refusal only.
2. **Toolchain seed:** build a host-owned per-project seed once per lock digest
   with dependency-only, builds-disabled `uv sync --locked`. Private activation
   copies come from that seed, never the 24 GB whole-host cache. Copy the selected
   interpreter separately from the host uv-managed Python directory.
3. **Cleanup:** delete private toolchains after host verification and activation
   close; retain `SeedReceipt`. Crash copies stay until recovery classification
   and death proof permit close/cleanup; project seeds remain reusable.
4. **Monitor:** heartbeat and refusal journal are always written. The separate
   `foreman monitor <root>` command is opt-in; only explicit `--monitored` makes
   monitor availability a startup requirement.
5. **Slice 4:** remains in the bundle, last and fixture-qualified only.

Other choices remain as written: two execution names; 2 KiB retained attempt
tails with a 16 KiB feedback payload cap; deduplicated durable events and
at-least-once hooks; unchanged default §8.1 steer plus explicit experimental
in-place control; fresh sessions by default. These rulings do not authorize
implementation before a slice instruction.
