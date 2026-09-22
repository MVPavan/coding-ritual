# Crew sessions and budgets

## 1. Findings on G4

`codex exec resume <id>` is already implemented by the `codex` adapter
(`workflow_interpreter/profiles/codex.py:233-260`). In the captured real stream,
`thread.started` contains the thread ID on event 1 and the first tool call is event 4
(`tests/fixtures/profiles/codex/commands.jsonl:1-4`); the decoder extracts that ID
(`workflow_interpreter/profiles/codex.py:350-361`). A vendor guarantee that it will always precede
tool work: **not found**. Admission must probe this ordering for each supported Codex CLI version.
The event is durably capturable, but registration into activation metadata before work is not proven.

Crash safety does not require an engine-preassigned ID. Stdout and stderr are appended to the
activation log before exec (`workflow_interpreter/inspector/fork_launcher.py:496-498`). Registration
and recovery must both scan that log from byte zero for `thread.started`; thus a crash after the
event but before registration is recoverable. If the process dies before that event, the durable
launch has no vendor ID to resume: preserve any owned tree, record `session_id_missing`, and take a
fresh infra retry. Whether hidden vendor work can precede `thread.started`: **not found**. This
retires cr-o85.15; capturing the first durable vendor identity is sufficient, while inventing one is
not. The existing Codex profile already represents “not known yet” as an empty ID
(`workflow_interpreter/profiles/codex.py:197-209`).

App-server still gives pre-turn thread registration (`docs/specs/workflow-interpreter.md:598-605`),
one server process/one turn per activation (`docs/specs/workflow-interpreter.md:735-748`), and
bounded in-place steer (`docs/specs/workflow-interpreter.md:897-907`). It also uses private vendor
state and explicit untrusted project layers (`docs/specs/workflow-interpreter.md:744-764`); exec is
a one-shot process whose resume command reapplies cwd and sandbox overrides
(`workflow_interpreter/profiles/codex.py:233-260`).

**Recommendation: keep both crews, but use `codex` (exec) for this workstream.** Per R1,
`codex-appserver` remains registered, behaviorally untouched, and unmigrated; existing pinned roots
remain loadable. There is no alias, binding migration, in-place-steer removal, or retirement slice.

## 2. Session-mode model

- Canonical authoring has one enum, `session_mode = "fresh" | "resume"`. Add optional
  `CrewBinding.session_mode`; add optional `Node.session_mode`. Resolve once with precedence
  node > role binding > `fresh`, and pin `node.<name>.session_mode` beside profile/model/effort
  (`workflow_interpreter/foreman/resolve.py:423-463`). Foreman request construction carries that pin
  into the durable `MintRequest` before dispatch (`workflow_interpreter/foreman/cases.py:131-176`).
- `resolved_node()` already reconstructs effective node values from root-pinned settings
  (`workflow_interpreter/foreman/execution.py:111-165`). `choose_source()` must receive that resolved
  mode; it must stop reading the raw graph field, which it does today
  (`workflow_interpreter/bdio/sessions.py:39-49`). The foreman, not the inspector, selects once.
- For old pinned app-server graph bodies only, decode legacy `session_reuse="same-node"` as effective
  `session_mode="resume"` and `"fresh"` as `"fresh"`, without rewriting pinned bytes or hashes.
  New graphs cannot author `session_reuse`. This is schema compatibility, not a crew alias or an
  app-server migration; its current app-server-only semantics are documented at
  `docs/specs/workflow-interpreter.md:750-764`.
- A durable launch request carries `session_mode`, `session_source_activation_id`,
  `source_session_id`, and `expected_tree_oid`. `WrapperLaunch` already persists its `MintRequest`
  before spawning (`workflow_interpreter/foreman/compose.py:56-64`;
  `workflow_interpreter/foreman/cases.py:152-176`). For `fresh`, all source fields are null.
- `resume` means a new activation/turn using Claude `--resume <source_session_id>`
  (`workflow_interpreter/profiles/claude.py:220-232`) or Codex
  `codex exec resume <source_session_id>` (`workflow_interpreter/profiles/codex.py:233-260`). For
  legacy app-server roots, the compatibility mapping continues its existing `thread/resume`
  (`workflow_interpreter/inspector/rpc_session.py:269-280`); this workstream changes none of that
  crew's files or behavior.
- Generalize the same-node selection at `bdio/sessions.py:39-88`: newest completed eligible
  activation wins. A source is ineligible if it is another root/node; superseded; crashed or lacks
  successful turn completion; lacks an ID/tree proof required for its write mode; or changes
  crew/profile/version/model/effort/policy digest. “Superseded” means `superseded_by` is set or its
  outcome is `SUPERSEDED`, which also excludes it from `is_completed`
  (`workflow_interpreter/bdio/wire.py:435-472`).
- Fresh does not poison later reuse: if A resumes, F later runs fresh, and R later requests resume,
  newest-first selection makes R resume F's session, not A's. A resume with no eligible source
  launches fresh and records a reason; once a source is selected, launch may not silently switch.
- `SessionRegistration.crew_version` currently defaults every crew to `CODEX_VERSION`, and source
  selection compares it (`workflow_interpreter/bdio/rpc_records.py:11-24`;
  `workflow_interpreter/bdio/sessions.py:77-84`). The only current admission probe is app-server's
  hardcoded `CODEX_VERSION` check (`workflow_interpreter/contracts/codex.py:5`;
  `workflow_interpreter/profiles/codex_appserver.py:59-69`). S2 adds profile qualification in
  `ProfileRegistry.profile_for`: Claude runs `claude --version`, exec runs `codex --version`, and
  registration stores the normalized output. Only then does generalized source selection compare
  recorded versus qualified version. App-server keeps its existing comparison unchanged.
- Steer/infra retry selects only its exact ancestor using the existing lineage rule
  (`workflow_interpreter/bdio/sessions.py:91-118`), then emits the same four-field launch contract.
  Only the source selection differs; inspector launch and tree verification do not branch on steer.

## 3. Thorough resume

All activations in a root share `WrapperPaths.worktree`
(`workflow_interpreter/inspector/paths.py:198-200`). Today every activation receives `_precondition`,
which calls `Workspace.prepare` (`workflow_interpreter/inspector/run.py:218-230,332-346`); that path
does not consult `node.writes`, and for an off-repo checkout treats every dirty path as resettable
(`workflow_interpreter/inspector/workspace.py:238-287,342-366,404-420`). Change that exact call site
to choose one of three preconditions from node authority plus the durable launch request:

- After a successful vendor turn and before marking a writing source completed, record and pin a
  full working-tree snapshot commit; store its tree OID as `session_tree_oid`. Use the temporary-index
  mechanism, which captures the whole dirty state and pins before destructive reset
  (`workflow_interpreter/inspector/workspace.py:422-459`). A terminated steer source records the
  same expected-tree field from its pinned recovery snapshot. Both feed one launch contract.
- For `node.writes` plus `session_mode=resume`, require source ID and expected tree OID, compute the
  full current tree OID without mutation, and require equality before exec. On equality, do not
  reset, but do take ownership and record the §3.2 trio before exec: `pre_attempt_commit=current
  HEAD`, `reset_verified_commit=current HEAD` after OID equality is proven, and the current encoded
  dirty snapshot (or `None` off-repo). Factor `_finish_precondition` from `_prepare_owned`'s
  ownership/result tail: it calls `_write_record` and returns `PreconditionResult`; both reset and
  resume branches call it. `Dispatcher._prepare` then durably writes the trio, so later rework sees
  the resumed writer (`workflow_interpreter/inspector/workspace.py:264-287,647-667`;
  `workflow_interpreter/inspector/launch.py:451-468`; `workflow_interpreter/bdio/inspection.py:99-105`;
  `workflow_interpreter/bdio/mint.py:350-369`). Dead resumed writers then satisfy the ownership guard
  and pin their tree (`workflow_interpreter/inspector/workspace.py:548-572`).
- For `not node.writes` (`workflow_interpreter/schema/models.py:304`), session mode affects only the vendor session. Call `observe_shared_tree`, not
  `Workspace.prepare`: create the instance checkout at the intended base only if absent; otherwise
  neither move HEAD, reset, clean, nor transfer tree ownership. Record the full-tree OID immediately
  before launch and again after exit. Read-only sandbox grants remain in force, and the invariant is
  `observed_tree_oid_after == observed_tree_oid_before`; inequality raises owner-visible
  `ReadOnlyTreeMutation`. Fresh and resumed reviewers use this identical tree path.
- That after-exit check is best-effort on the normal `ExitObserver.observe` path only
  (`workflow_interpreter/inspector/exit.py:255-299`). Steer-pending returns before observation, and
  §5.6 recovery preserves directly (`workflow_interpreter/inspector/run.py:280-296`;
  `workflow_interpreter/inspector/recover.py:385-393`). After a steered/crashed reviewer, the next
  resumed writer's required `expected_tree_oid` probe supplies the check: equality proceeds;
  inequality refuses with `ResumeTreeMismatch`.
- On a missing writer snapshot or mismatch, raise named `ResumeTreeMismatch`, append an
  owner-visible attention/refusal containing expected and observed OIDs, do not reset, do not
  launch, and do not auto-retry fresh. A silent fresh fallback would discard the tree whose session
  was selected. The owner may explicitly mint fresh after inspecting/recovering it.
- A writer resolved as `fresh` never inherits the exemption. It takes the existing
  precondition: pin the complete dirty tree under `prereset`, reset to its own intended base, and
  prove clean (`workflow_interpreter/inspector/workspace.py:404-459`). A non-writer never does this,
  regardless of fresh/resume. Thus fresh-writer-after-resume preserves recoverability but starts
  clean; fresh-reviewer-after-resume observes the existing uncommitted tree.

Plain loop: **impl#1** (fresh writer) prepares clean, works, and pins OID `T1` → **review#1** (fresh
or resumed non-writer) observes `T1`, makes no reset, and proves before/after OIDs both `T1` →
**impl#2** (resumed writer) receives impl#1's session plus expected `T1`, observes the `T1` review
left, passes equality, and launches without reset. This cannot hold if a different writer/session
runs between impl#1 and impl#2: the current OID differs from `T1`, so impl#2 refuses by name with
`ResumeTreeMismatch(reason="intervening_writer")`; it never resumes against another writer's tree.

In `inspector/launch.py`, replace “`instructions is not None` means resume”
(`workflow_interpreter/inspector/launch.py:577-594`) with:
`resume = request.session_mode == resume and request.source_session_id is not None`.
`resume` calls `build_resume_command(source_session_id, prompt, task)`; plain graph resume uses the
complete current `task.brief`, while steer uses its persisted steer text. Fresh calls
`build_command`. Generalize `_assert_continuation` to validate this contract; today it both rejects
instructions on plain lineage and requires them on steer lineage
(`workflow_interpreter/inspector/launch.py:410-449`). This also prevents Claude plain resume from
falling into fresh `--session-id <existing-id>` (`workflow_interpreter/profiles/claude.py:208-218`).

## 4. Context cap

Add one optional role-binding field, `context_cap_tokens: int | None`; it has no node override and
is pinned with the role's invocation settings. Keep `context_budget_bytes` separate: it bounds the
composed envelope, not vendor context (`workflow_interpreter/foreman/inputs.py:462-473`).

For Claude only, a non-null value maps on both launch and resume to
`--autocompact <context_cap_tokens>`. Installed `claude --help` confirms explicit `100k-1M`; the
adapter's shared flags currently emit no compaction setting
(`workflow_interpreter/profiles/claude.py:238-249`). The DWS pilot sets `400000` on each
operator-designated 1M-window Claude role. The engine has no model-to-window table and does not
validate against one: the operator supplies the value and Claude receives it unchanged. Document
that Claude's own accepted floor is 100000. Unset emits no flag; Codex roles leave it unset.

Codex Sol/Terra remains at the owner-ruled vendor default: context window 272000 (872000 maximum,
95% effective). Do not emit `model_context_window` or `model_auto_compact_token_limit`. Codex exec
keeps the configured `CODEX_HOME` already admitted through its auth environment
(`workflow_interpreter/profiles/codex.py:185-194`); there is no private-home bootstrap. App-server
is untouched. Unset always means vendor default.

## 5. Slices

1. **S1 — resolved contract and source** (3h execution + 1h review). Files:
   `contracts/sessions.py`, `schema/{models.py,rules_nodes.py,graph_schema.json}`,
   `foreman/{config.py,resolve.py,execution.py,cases.py,compose.py}`, and
   `bdio/{wire.py,rpc_records.py,sessions.py,activation_writes.py,roots.py}`. Lean test: one table
   proves node > role > fresh, legacy app-server decode, newest source on non-version fields, and
   fresh-between-resumes; app-server's existing version check stays intact and generalized version
   eligibility waits for S2. Probe: inspect the durable request for all four session fields.
2. **S2 — durable identity and vendor resume** (4h + 90m). Files:
   `inspector/{launch.py,run.py,profile.py,rpc_records.py,paths.py}`, `profiles/registry.py`,
   `profiles/claude.py`, `profiles/codex.py`, `bdio/sessions.py`, and registration/inspection
   carriers. Lean tests: one
   plain-resume launch matrix proves Claude and exec take `build_resume_command` without steer
   lineage and compare captured CLI versions; one recovery case rescans the log.
   Probe: implementer → reviewer → implementer keeps one vendor ID and the second turn receives the
   new brief. Exit: live qualification permits retiring cr-o85.15.
3. **S3 — tree-faithful resume** (5h + 90m). Files:
   `inspector/{run.py,workspace.py,models.py,exit.py,recover.py,steer.py,paths.py}`,
   `foreman/{inspector.py,close.py}`, and `bdio/{wire.py,inspection.py}`. Lean tests:
   `resumed_writer_owns_and_records_trio`, `dead_resumed_writer_pins_tree`,
   `nonwriter_no_reset_oid_unchanged`, `reviewer_bypass_checked_by_next_writer`,
   `intervening_writer_refuses`, and `fresh_writer_resets`. Probe: impl#1 leaves a sentinel at `T1`;
   review#1 leaves `T1`; resumed impl#2 passes expected `T1`; repeat via steer. Exit: cr-o85.18.
4. **S4 — Claude cap and authority docs** (2h + 1h). Files: `foreman/config.py`,
   `foreman/resolve.py`, `foreman/execution.py`, `inspector/profile.py`, `profiles/claude.py`,
   `workflows/dws-package-pilot.toml`,
   `config/foreman.example.toml`, `docs/specs/workflow-interpreter.md` (§5.2, §5.4, §6, §8.1),
   and `docs/workflow-interpreter-guide/04-graph-and-nodes.md` (session and budget rows). Bead
   close/retirement is an exit
   action, not a generated-mirror edit. Lean test: one argv table proves explicit Claude 400000 is
   passed unchanged while unset Claude and Codex get no flag. Probe: capture pilot launch and resume
   argv. Exit: retire
   cr-e94f after docs and probe agree.

## 6. Risks / open rulings for the owner

- **Open rulings: none.** R1-R4 determine crew retention, plain-loop ownership, Codex home, and caps.
- Codex event ordering is version-qualified rather than guaranteed; an unqualified version refuses
  reuse, and a missing first event can only retry fresh.
- Full-tree snapshots include tracked, untracked, staged, and deletion state; snapshot failure must
  refuse resume rather than weaken the OID proof.
- Normal reviewer exits get best-effort before/after OID equality; bypassed checks defer to the next
  resumed writer's mandatory match rather than claiming `ReadOnlyTreeMutation` was observed.
- Tree mismatch is owner-visible and non-automatic, avoiding destruction of state the session remembers.
- Round-3 findings 1-3 are resolved in S3; none is refuted.
