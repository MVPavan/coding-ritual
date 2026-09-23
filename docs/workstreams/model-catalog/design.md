# Model catalog and live role bindings — cr-98c8

## 1. Goals and non-goals

**Goals.** Build and check a machine catalog at every foreman start; let a human
edit only flat TOML role bindings; use the binding current at each new activation;
pin the exact invocation in the activation ledger; resume by default; preserve
a crashed resumed writer's own session and tree on an eligible infra retry.

**Non-goals.** A model marketplace, automatic choice of a role's model, editing
the generated catalog, in-place model changes to a running activation, or a
`codex-appserver` migration. The app-server transport remains frozen and outside
this catalog; its pinned protocol and one-turn behavior are documented in
`docs/specs/workflow-interpreter.md:758-765`. Existing graphs are prototypes and
need no compatibility adapter, except a named refusal for legacy role `profile`.
Do not edit `profiles/codex_appserver*.py`, `contracts/codex.py`, or
`inspector/rpc_session.py` in this workstream.
`codex-appserver` and `opencode` remain available through direct graph
`crew = "codex-appserver" | "opencode"`, with graph model and project-config
node effort; neither is inferred from the catalog. Direct Opencode stays
explicitly `fresh` because it cannot register a resumable session
(`workflow_interpreter/schema/models.py:301-310`;
`workflow_interpreter/foreman/resolve.py:82-96`;
`workflow_interpreter/foreman/execution.py:186-193`;
`workflow_interpreter/foreman/config.py:54-63`).

**Verified baseline.** `CrewBinding` currently requires `profile`, `model`, and
`effort` in the main TOML config (`workflow_interpreter/foreman/config.py:84-99,221-238`).
Root creation resolves those role choices into immutable node settings
(`workflow_interpreter/foreman/resolve.py:452-528`), and mint checks model/crew
against those root pins (`workflow_interpreter/bdio/api.py:644-670`). Thus a
live TOML reread alone cannot implement mid-flight changes. This design makes
the *graph, static safety settings, policy version, and role name* root-pinned, but the *invocation
binding* activation-pinned. That is a deliberate change to the current root
contract, not an inference that it already works.

## 2. Catalog discovery, refresh, and failure policy

One `ModelCatalog.refresh()` interface accepts explicit binary paths and an
injected subprocess runner, and returns an immutable normalized snapshot plus
per-family diagnostics. The foreman invokes it before accepting work at every
**owner foreman** start. Worker/monitor restarts load that owner's qualified
snapshot and do not repeat paid probes. Serialize the snapshot to
`<wrapper_root>/model-catalog.json` by temp file, fsync, rename. No hand edits;
never accept the previous file as authority. It is useful only for diagnostics
and audit after a failed refresh. `wrapper_root` is a deterministic
per-repository path (`workflow_interpreter/foreman/config.py:69-81,158-161`).

**Codex, verified by read-only probe on 2026-09-23.** Installed `codex-cli
0.156.1` returns JSON from `codex debug models --bundled`: top-level `models`
array; 11 entries in this probe; each entry has `slug`, `context_window`, and
`supported_reasoning_levels` objects with an `effort` string. Entries also
have `visibility`; this probe has seven `list` and four `hide`. Normalize
visibility and exclude `hide` from binding choices (retain counts for
diagnostics). Ignore descriptive text and unknown extra fields. Do not infer
access from `--bundled`: it proves CLI recognition, not account entitlement.
Validate the selected pair with a bounded launch admission probe when needed.
Do not treat `max_context_window` as the ordinary window. Existing Codex argv
passes explicit model and effort (`workflow_interpreter/profiles/codex.py:341-348`).

**Claude, verified by read-only probe on 2026-09-23.** Installed `claude
2.1.258` help exposes `--model`, global `--effort` values `low, medium, high,
xhigh, max`, and `--autocompact` `100k–1M`. Its help lists no models command,
machine-readable model enumeration, or context-window query; `claude models
--help` displayed the general help. No model/window discovery has been verified.
Do not parse undocumented installed bundle internals or claim a global effort
list is per-model support. Use a small **checked-in Claude
seed** of full model IDs, context windows, and per-model efforts, sourced and
reviewed when maintained; the generated catalog still includes seed models the
user did not bind. At each owner start, check CLI version and help flags; a
self-update outside the seed's last known version is a warning, **not** family
disablement. Probe once per distinct **bound model** (one documented bound
effort as representative), outside every
instance band, before work is admitted. Use bounded transient retries with
backoff; persistent failure refuses that binding by role name. Probe via the
configured auth environment;
use `claude -p "Reply OK" --model <id> --effort <level> --tools ""
--output-format json --max-budget-usd <small-cap>` with a host timeout and
an aggregate startup cost cap. Record failures, duration, and cost if reported.
An unbound seed entry is listed as `seed-unprobed`, not as live-verified.
Documented per-model effort support comes from the seed's source; a successful
`--effort` invocation proves CLI acceptance, **not** that Claude honored the
requested effort. If support is undocumented, refuse the pair rather than infer it from
the global flag list. The seed cannot discover a newly released Claude
model absent from the seed; that is the honest limit of this CLI. If a later
supported machine-readable command appears, replace the seed adapter.

At each activation, re-read TOML but use the owner's qualified catalog/version
snapshot. This preserves the deliberate process-wide version cache
(`workflow_interpreter/profiles/registry.py:88-104`), avoiding subprocess cost
on every mint. Before exec, if binary identity/version differs from the pin,
re-run cheap `--version` qualification, bypassing that cache; do **no** paid
model probe. If the new version is in the adapter's qualified supported range,
warn and compare-and-set the **minted, not launched** activation's version pin;
reconcile its durable `WrapperLaunch` from that ledger pin before the fork
barrier. If a selected source ran the old version, clear its source/session IDs,
pin `VERSION_DRIFT`, and let fresh prepare assign a new ID; model/effort
stay pinned. Out-of-range version refuses by name;
the next owner start may qualify that range with its bound-model probe.

Failure policy: a missing CLI marks its family unavailable; malformed JSON,
empty/duplicate IDs, missing required fields, timeout, or persistent bound
Claude probe failure marks the affected binding unavailable. Record a named
readiness refusal for **new** work using it; keep the owner alive to replay or
settle existing activation pins, even if live TOML is malformed. An unused
unavailable family does not block the other. A failed activation-time
qualification refuses **before mint**. Never authorize from last-good JSON:
otherwise a removed model could be launched and its thread later mislabeled.
CLI version drift from a recorded source does **not** block a new activation;
it forces a fresh session with `VERSION_DRIFT` once the new catalog and role
choice pass admission. Source version recording already exists
(`workflow_interpreter/bdio/rpc_records.py:10-24`; `workflow_interpreter/bdio/sessions.py:141-163`).

## 3. Files and normalized formats

The human file is `roles.toml`, selected by absolute `role_bindings_path` in
`foreman.toml` (example path under the wrapper root). Foreman owns this path;
`tomllib` parses it at start and at every new activation, while unrelated
foreman settings remain the process's startup config. The current loader
already uses `tomllib` (`workflow_interpreter/foreman/config.py:221-235`).
No `profile` key is accepted. Example (model IDs are illustrative bindings,
subject to the local catalog):

```toml
[roles.implementer]
model = "claude-opus-5"
effort = "medium"
# context_cap_tokens = 400000

[roles.critic]
model = "gpt-5.6-sol"
effort = "high"
# session_mode = "fresh"  # only for deliberately independent reviews
```

The catalog decides `family = claude | codex` and hence `crew_profile`.
Exact model ID lookup must be unambiguous; refuse collisions by name and list
qualified choices rather than guessing a vendor. Refuse unknown model with
sorted valid model IDs; refuse unsupported effort with that model's sorted
efforts; refuse `profile` with “remove roles.<name>.profile; model determines
the crew”. `session_mode` accepts `resume | fresh`; absence means `resume`.
Only Claude accepts `context_cap_tokens`; reject invalid integers, values
outside Claude's CLI range, and values at/above the model's context window.

Generated JSON, schema version 1 (illustrative values, not a claim that the
example Claude model/window is installed):

```json
{
  "schema_version": 1,
  "generated_at": "2026-09-23T00:00:00Z",
  "families": {
    "codex": {"cli_version": "codex-cli 0.156.1", "source": "bundled-cli",
      "models": [{"id": "gpt-5.6-sol", "visibility": "list", "efforts": ["low", "medium", "high", "xhigh", "max", "ultra"], "context_window": 272000}]},
    "claude": {"cli_version": "2.1.258 (Claude Code)", "source": "checked-seed-and-probe",
      "models": [{"id": "claude-example", "verification": "seed-unprobed", "efforts": ["medium"], "context_window": 1000000}]}
  }
}
```

The checked-in seed is separate from this generated file and records, for each
entry, its source URL/date, verified CLI-version range, model ID, efforts, and
window (e.g. `{"id":"claude-example","efforts":["medium"],"context_window":1000000}`;
illustrative only). Canonicalize/sort normalized entries and hash the generated content
**without** `generated_at`; record that digest for activation audit. Reject
unknown schema versions and duplicate IDs. Do not include credentials, raw
probe output, or model descriptions in the catalog.

## 4. Activation resolution, reload, and audit pin

At owner start: refresh catalog, parse `roles.toml`, probe bound Claude models,
and record readiness; malformed bindings block new mints only. Under the
instance band derive the natural idempotency key
from root/route facts **first**; if an activation already has it, return its
pin without TOML parsing or validation. For a new key, read complete TOML
bytes. If a newly bound model needs a paid probe, release the band, probe once,
reacquire, recheck the key, and compare the file digest; restart preflight if
it changed. No provider probe runs under the band.
Current store lookup precedes mint checks (`workflow_interpreter/bdio/activation_writes.py:301-313`),
while route keys ignore model (`workflow_interpreter/bdio/mint.py:377-400`).

For a genuinely new entry/edge/infra mint, validate the current role and
construct one `ResolvedInvocation` before the ledger write. The constructors
currently read root values (`workflow_interpreter/foreman/cases.py:209-223,354-374,537-549`).
An intentional **steer continuation** instead inherits the predecessor's
entire invocation pin, including mode, model, effort, policy and version;
role edits take effect at the next ordinary mint. Remove the root rewrite in
`workflow_interpreter/inspector/steer.py:358-370` and derive the continuation
request from the recorded predecessor, not the root-based constructor at
`workflow_interpreter/foreman/tick.py:389-399`. Refuse by name if the pin is
incomplete; current selection otherwise raises a generic carrier error
(`workflow_interpreter/bdio/sessions.py:170-171`).
**OWNER RULING:** each role may set `apply = "now" | "next-task"` in
`roles.toml`; the default is `next-task`. With `next-task`, an edit takes effect
from the next task; every activation (steer, retry, next round) of the current
task keeps its pinned binding. With `now`, the crew's next activation
of any kind (steer, retry, or next round) takes the edited binding. A binding
change starts fresh with `MODEL_CHANGED` from the task's current tree; it never
interrupts a running turn. Leaving `now` set is harmless. Refuse an unknown
`apply` value by role name.

Remove role-bound crew/model/effort/mode/cap and role-derived policy from root
resolved config and decision-template identity. Keep graph role reference,
static node safety settings and policy version at root; move `tool_network` and
the complete `ExecutionPolicy` to the activation, derived from its **registered
crew**, then pin its digest for session eligibility. Claude declares
`NOT_ENFORCED`, Codex `DENIED` (`workflow_interpreter/profiles/claude.py:185-189`;
`workflow_interpreter/profiles/codex.py:185-189`); the current root policy
derives that capability from the creation crew
(`workflow_interpreter/bdio/roots.py:175-210`). Re-derive grants at each mint,
never reuse a stale root policy across families. Update root completeness and
same-`instance_key` comparison (`workflow_interpreter/bdio/roots.py:145-166,437-455`),
recursive decision template rendering (`workflow_interpreter/foreman/resolve.py:540-553`),
and child admission/revalidation (`workflow_interpreter/foreman/children.py:542-554,620-640`)
to compare static pins only. A child resolves its own live role at its mint.

Pin role, family/profile, model, effort, cap, mode, CLI version, catalog and
binding digests, and activation policy in `MintRequest`/`ActivationMetadata`;
metadata lacks effort/cap today (`workflow_interpreter/bdio/wire.py:388-431,581-607`).
Use an activation view for every invocation consumer: request reconstruction
(`workflow_interpreter/foreman/cases.py:144-160`;
`workflow_interpreter/foreman/inspector.py:137-159`), task argv/policy
(`workflow_interpreter/foreman/inspector.py:163-173,246-255`), dispatch
(`workflow_interpreter/foreman/inspector.py:290-305`), and settle/grade
(`workflow_interpreter/foreman/cases.py:401-411,424-431`). The registration
observer must take effort and policy digest from the activation pin; its root
lookup now yields stale values or `_UNREADABLE` after role pins leave the root
(`workflow_interpreter/inspector/profile.py:382-400`). It must also register
the activation's re-pinned CLI version, not the process cache (`workflow_interpreter/inspector/profile.py:385`).

S3 read inventory for **every** root lookup of crew/model/effort, policy, or
mode: `workflow_interpreter/foreman/execution.py:81-91,130-160`;
`workflow_interpreter/bdio/activation_writes.py:166-168` (called by
`workflow_interpreter/bdio/api.py:653-665` and
`workflow_interpreter/inspector/steer.py:358-370`);
`workflow_interpreter/bdio/sessions.py:74-105,194-207`;
`workflow_interpreter/inspector/profile.py:382-400`. Root construction and
validation also read those keys: `workflow_interpreter/foreman/resolve.py:441-477,480-528`;
`workflow_interpreter/bdio/roots.py:145-161,188-203`. Route invocation reads
to the activation pin; restrict remaining root reads to static/direct-crew
checks. Also inventory every `resolved_node(...).crew_profile/model/effort`
consumer in S3; leave static node topology/writes root-pinned. Already minted dispatches replay only their
ledger pin and durable `WrapperLaunch` (`workflow_interpreter/foreman/compose.py:57-64`).

## 5. Session choice and new fresh reason

For resumable Claude/Codex roles, effective mode is node declaration > role
declaration > `resume`. Explicit `fresh` means no source selection. A role may
change mode mid-flight only for future activations. The current resolution
defaults to `fresh` (`workflow_interpreter/foreman/resolve.py:462-477`), and
`resolved_session_mode` has a legacy fresh fallback
(`workflow_interpreter/bdio/sessions.py:194-207`); change both for new roots,
while preserving old pinned roots' explicitly recorded mode. More critically,
`choose_source` currently short-circuits on root mode and mint writes root mode
(`workflow_interpreter/bdio/sessions.py:66-73`;
`workflow_interpreter/bdio/activation_writes.py:313-320`). Both must use
`request.session_mode` from the new invocation, which is copied unchanged to
the activation. Root mode is historical only. Frozen app-server keeps its
legacy path.

Choose the newest same-root, same-node settled candidate, then compare its
recorded profile/model/effort to the new activation binding. A different model
**or effort** produces `MODEL_CHANGED` and a fresh turn; do not skip backwards
to an older matching session. A profile/family change is also a binding change
and gets `MODEL_CHANGED`. Current selection silently skips mismatches against
root settings (`workflow_interpreter/bdio/sessions.py:83-116`); compare the
candidate with the request's activation binding and record this reason. Keep
existing `VERSION_DRIFT`, `UNQUALIFIED_SOURCE`, and `NO_SOURCE` meanings
(`workflow_interpreter/contracts/sessions.py:54-70`). Only a selected source
supplies ID and tree OID; selection is durable at mint
(`docs/specs/workflow-interpreter.md:582-588`).
Move model/effort comparison and `MODEL_CHANGED` into the **same slice** that
first pins effort; current source tests compare both to the root
(`workflow_interpreter/bdio/sessions.py:91,104-105`). Compare source policy
digest with the request's activation policy, not the old root policy.

On **resumed non-writer tasks only** (`session_mode=resume`, selected source ID,
and effective `writes=false`), append a mandatory review delta: inspect the
whole current diff, verify fixes to prior findings, and check for regressions
or new defects elsewhere. Do not modify the shared `RESUME_FACT_FRAME`, which
applies to every crew (`workflow_interpreter/foreman/constants.py:121-128`;
`workflow_interpreter/foreman/inputs.py:549-555`). Preserve graph instructions;
current resume composition resends them and newly sent inputs
(`workflow_interpreter/foreman/inputs.py:508-555`),
and the pilot review currently describes its initial review task
(`workflows/dws-package-pilot.toml:63-110`). No tree reset is added for a
reviewer; non-writers observe the shared tree under §5.4
(`docs/specs/workflow-interpreter.md:636-660`).

## 6. Context cap defaults

| Case | Effective cap | Behavior |
| --- | ---: | --- |
| Claude window > 370,000, role cap absent | 370,000 | Emit `--autocompact 370000` on launch and resume. |
| Claude window <= 370,000, role cap absent | none | Leave vendor default. |
| Claude role cap set and valid | role value | Emit on launch and resume. |
| Codex | none | Leave vendor default; reject role cap. |
| Frozen app-server | existing behavior | No catalog or cap migration. |

Window comes from the checked catalog, never an ID heuristic. `370000` is
strictly below a larger window; an explicit cap must be below the window and
within the installed Claude flag's `100k–1M` range. `context_budget_bytes`
still limits the composed prompt, not vendor context
(`workflow_interpreter/foreman/inputs.py:452-461`). Claude's shared argv path
already emits an explicit cap on launch and resume
(`workflow_interpreter/profiles/claude.py:209-253`); Codex's shared argv has
only model/effort (`workflow_interpreter/profiles/codex.py:341-348`).

## 7. Crashed resumed writer: infra retry of its own thread

The cr-31ex.5 record in `.beads/issues.jsonl:556` describes a resumed writer
that crashes after partial edits: current selection reaches an older completed
source, whose expected tree no longer matches. Current code accepts only
successful outcomes or a steered ancestor (`workflow_interpreter/bdio/sessions.py:175-191`),
although infra retry ancestry is traced (`workflow_interpreter/bdio/sessions.py:210-239`).

For an `INFRA_RETRY` whose immediate predecessor was **resumed** and crashed:
after death proof and before closing it, pin its recovery snapshot and publish
that tree as its `session_tree_oid`. `preserve_interrupted` already creates a
producer-linked recovery record/ref (`workflow_interpreter/inspector/workspace.py:726-770,772-779,835-872`);
the steer path already publishes its recovered tree before close
(`workflow_interpreter/inspector/steer.py:317-355`). Generalize that operation
to the crash path. If no dirty state exists, pin the current proved full-tree
OID. Refuse if ownership, identity, or snapshot proof is missing; never copy
the prior successful turn's T1 as the failed turn's tree.

Source selection for this retry takes the **immediate crashed predecessor**
with its observed vendor registration and recovery tree, even though its
outcome is an infra error. It carries predecessor activation ID, same vendor
thread ID, and recovered expected tree into the same resume launch contract.
The resumed-writer precondition checks equality without reset
(`docs/specs/workflow-interpreter.md:646-654`). A second infra retry repeats
this against its own predecessor, bounded by the existing retry cap; no
unbounded recovery loop. If the binding or CLI version changed, enforce
`MODEL_CHANGED`/`VERSION_DRIFT` and start fresh **only after** preserving the
crash tree under `prereset`; if preservation fails, refuse before launch.
If the crashed turn never registered a vendor ID, use its **pinned source**
thread only when its proved recovery tree equals that turn's
non-null `expected_tree_oid`, a verified source session ID exists, and
model/effort/version/policy still match; no edits then
need recovery inside the unobserved turn. Otherwise refuse by name, leave the
checkout untouched, and do not select an older thread. Registration is the
current observed-identity gate (`workflow_interpreter/bdio/sessions.py:95-100`).
This rule does not change app-server transport files.

## 8. Migration

Replace inline `[roles.*]` in `config/foreman.example.toml:103-172` with
`role_bindings_path = "@WRAPPER_ROOT@/roles.toml"` and a short renderer/setup
instruction. Supply a checked-in `config/roles.example.toml`; render/copy it
once to the wrapper root, then let operators edit that file. The generator for
the machine-specific foreman config is `scripts/make-foreman-config.sh`
(`config/foreman.example.toml:1-11`). Reject the old `[roles.*] profile=` shape
at startup with the named migration message; no silent dual-source merge.

Update `workflows/dws-package-pilot.toml` to rely on resume-by-default for
implementer and critic, add an explicit `fresh` only to a genuinely independent
critical-review node, and add the full-diff/regression review instruction.
Its current implementer/critic role references and review text are at
`workflows/dws-package-pilot.toml:22-30,63-110`; its infra retry bound is zero
at `workflows/dws-package-pilot.toml:58-60`, so set a bounded retry allowance
if this pilot is used to demonstrate crash recovery. Keep model IDs in the
human role file, not duplicated in the graph. Migrate other prototype graphs
and test fixtures that assumed root-frozen role models; no back-compat shims
for their authored defaults are required.

## 9. Lean behavior tests and gate

Extend existing tests, not new files:

1. `tests/test_foreman_resolution.py`: bundled `hide` exclusion, Claude
   seed/version warning, one probe per bound model, retry bound, named invalid
   choice, and old `profile` refusal.
2. `tests/test_foreman_cases.py` and `tests/test_foreman_inspect.py`: change
   TOML between mints; duplicate key replays despite malformed TOML; dispatch,
   settle, grade and argv use the activation pin, including cross-family
   `tool_network` and unchanged root static policy version.
3. `tests/test_foreman_steer.py`: binding edit during steer retains the
   predecessor pin and session; incomplete pin refuses by name.
4. `tests/test_bdio_root_identity.py` and `tests/test_children_lifecycle.py`:
   same `instance_key` and child admission survive role edit while graph/static
   safety changes still conflict.
5. `tests/test_codex_appserver_sessions.py`: direct-crew legacy graph remains
   loadable; `tests/test_foreman_envelope.py`: only resumed non-writer gets
   whole-diff regression text; `tests/test_profiles_parse.py`: Claude
   `--resume` preserves the observed session ID or refuses a fork.
6. Existing session/crash tests: live mode overrides root mode; changed effort
   yields `MODEL_CHANGED` in S3; crash retry uses failed thread/recovery tree,
   or its source only when unregistered and tree unchanged.
7. `tests/test_foreman_inspect.py`: supported mid-run CLI update re-pins only
   minted activation and records `VERSION_DRIFT`; out-of-range update refuses.

Each slice runs the full workflow-interpreter gate in
`.claude/project/verification.md:40-64` and checks `git status`. A read-only
live CLI qualification is an additional admission probe, not a substitute for
the tests; never claim Claude context windows were CLI-discovered.

## 10. Independently green implementation slices

1. **S1 — catalog (~450 changed lines):** Codex visibility, Claude seed,
   owner-start bounded probes/version warning, generated JSON, existing tests.
2. **S2 — TOML/direct crews (~500):** role file and named refusals; adapt
   `tests/test_codex_appserver_sessions.py` to direct `crew`; keep old path green.
3. **S3 — activation carrier/view (~550):** pin effort/mode/policy, route
   registration/dispatch/settle/grade to the activation; compare source effort and
   model now, with `MODEL_CHANGED`; duplicate-mint replay test.
4. **S4 — stable root/children (~500):** remove role-derived identity from
   root and decision templates; update child admission and policy validation;
   same-key/child tests. Existing mints still use startup bindings.
5. **S5 — live mints/steer (~550):** reread roles at new mint, probe outside
   band, pin new bindings; steer inherits predecessor pin; tests for edits.
6. **S6 — crash retry (~500):** recovery-tree pin, exact failed source and
   unregistered unchanged-tree fallback; refusal and crash tests.
7. **S7 — defaults/review (~350):** resume default, non-writer review delta,
   pilot graph and prompt; focused history/envelope tests.
8. **S8 — authority/qualification (~300):** amend spec, guide, and
   `docs/workstreams/crew-sessions/design.md:38,60-63`; run live probes and
   full gate. The older design's fresh/root-source statements are superseded.

## 11. Risks and explicit evidence limits

- **Verified:** CLI probe output establishes Codex bundled metadata fields;
  it does not prove entitlement to every bundled model. Claude help establishes
  accepted flags, not a model list or per-model window/effort.
- **Inferred design tradeoff:** Claude seed + live probes costs startup time
  and provider tokens, and cannot notice models absent from the seed. Keep
  bounds explicit and report the source/verification status in catalog JSON.
- A live edit can race mint. Read/parse one complete file under the instance
  band, hash those bytes, and pin them before the ledger write. A partial edit
  refuses; it cannot mix fields from two versions.
- A prelaunch version re-pin is legal only before exec, with a durable ledger
  compare-and-set and request reconciliation; an already launched activation
  retains its original version. A resume across versions becomes `VERSION_DRIFT`.
- Claude `--resume` sends an ID but does not prove the resumed result reports
  that same ID (`workflow_interpreter/profiles/claude.py:221-233,302-315`).
  Compare the observed result ID with the pinned source; refuse a fork.
- Existing root-pinned model assumptions span mint, task construction, and
  source selection (`workflow_interpreter/bdio/api.py:644-670`;
  `workflow_interpreter/foreman/inspector.py:137-173`;
  `workflow_interpreter/bdio/sessions.py:83-116`). Missing even one call site
  would make replay disagree with the activation ledger; S3 needs a caller
  inventory and direct replay test.
