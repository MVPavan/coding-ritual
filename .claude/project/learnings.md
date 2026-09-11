# Learnings

Durable, verified, likely-to-recur patterns for **this** repo. Capture only
after a verified fix or a repeated pattern — not speculation. Keep each entry
short: what was observed, why it matters, how to apply it.

Format per entry:

```
## <short title>  (<YYYY-MM-DD>)
- Observed: <what happened / the pattern>
- Why it matters: <consequence>
- Apply: <concrete guidance>
- Source: <bead id / task / session that verified it>   (optional)
```

## Codex CLI silently swallows bad `-c` config values  (2026-07-10)

- Observed: `codex exec -c model_reasoning_effort=bogus` runs fine (exit 0, no
  warning) and silently falls back to the config default; same for any
  unrecognized `-c` key/value. Verified on codex-cli 0.144.1.
- Why it matters: wrapper-side typos in effort/sandbox/config overrides fail
  open, not closed — on a machine whose `config.toml` defaults to
  `workspace-write`, a typo'd sandbox value silently yields a writable run.
- Apply: any wrapper around `codex exec` must validate safety-critical values
  itself (hard-fail for sandbox, warn-and-forward for the rest). Prefer the
  native `-s` flag on plain `codex exec` — it outranks all config overrides,
  including `default_permissions` profile keys that supersede `sandbox_mode`;
  note `exec resume`/`exec review` don't accept `-s` (config override only).

## Codex CLI accepts hidden flags its --help doesn't list  (2026-07-10)

- Observed: `--yolo` and `--full-auto` are accepted by `codex exec` 0.144.1
  (probed via `-h` short-circuit: exit 0 vs exit 2 for a bogus flag) but absent
  from `--help`. Both escalate the sandbox.
- Why it matters: flag allowlists or deny-checks built from `--help` output are
  incomplete; pass-through wrappers can smuggle escalations.
- Apply: when guarding a pass-through surface, probe suspected hidden flags
  with `<cmd> <flag> -h` and deny by pattern, not by the documented list. Always
  emit a `--` before a positional prompt so dash-prefixed text can't be parsed
  as a flag by the child CLI.

## `bd init` commits, and sweeps untracked files at its known paths  (2026-08-19)

- Observed: `bd init --non-interactive --skip-agents` (bd 1.1.0 and 1.2.2)
  always makes one git commit — its own `.beads/` + `.gitignore` — and also
  stages any *untracked* `CLAUDE.md`, `AGENTS.md`, `.claude/settings.json`,
  `.codex/*` it finds (not other untracked files). No flag suppresses the
  commit. With `--skip-agents` it does not edit CLAUDE.md/AGENTS.md, add a
  skill, or touch global config; it sets `core.hooksPath=.beads/hooks` and
  chains pre-existing hooks. Without `--skip-agents` it appends BEADS
  INTEGRATION blocks to both files, adds `.agents/skills/beads/`, and edits
  `.claude/settings.json` + `.codex/hooks.json`.
- Why it matters: an installer that lays files and then runs `bd init` ships a
  half-committed harness; a teammate's clone inherits the half. Found by the
  plugin's live install matrix (cell 8), not by unit tests.
- Apply: run `bd init` before laying any residue; always pass `--skip-agents`;
  tell the user bd made a commit; keep the residue uncommitted for review.

## Plugin scope facts that bite install tooling  (2026-08-19)

- Observed: `claude plugin list --json` lists project-scope rows for every repo
  on the machine (with `projectPath`); `claude plugin install --scope project`
  pre-creates `.claude/settings.json` and later rewrites it dropping unknown
  keys (hook `description`); `claude plugin marketplace remove` uninstalls the
  plugin from every scope silently. Codex has user scope only; repo hooks run
  only after per-hook approvals (`hooks.state."<repo>/.codex/hooks.json:*"`
  in `~/.codex/config.toml`), which only the interactive prompt writes.
- Why it matters: status checks that take the first list row, file-merge on
  settings.json, or `trust_level`-only checks all misreport.
- Apply: filter plugin rows by `projectPath`; JSON-merge settings.json; check
  `hooks.state` counts; test install flows in a clean container with real
  CLIs (`mvp-harness/plugins/mvp-plugin/test/` + a long-lived lab container).

## `ForemanLab` timing and rebuild traps in crash/staleness drills  (2026-09-02)

- Observed, three independent traps, each cost a worker a failing run:
  (1) `ForemanLab` wires a `FrozenClock` whose `sleep()` advances virtual time
  for free, so a real-fork staleness test gets NO stale-but-alive window — the
  wrapper's poll loop races through the node's `stale_after` AND its 45m
  `max_wall` in an eyeblink and kills its own child before the test can steer
  it (`LifecycleConflictError`). (2) Dispatch and settle are SEPARATE ticks
  even in the synchronous `InlineSpawner` lab, so `crash_on("update", n)`
  armed one tick late silently never fires (`DID NOT RAISE`). (3)
  `lab.rebuild()` discards `_Profiles` and any queued `ChildScript`, so a
  script queued before a rebuild is lost and the relaunch runs the stale
  default.
- Why it matters: each trap produces a *green or plausibly-red* test that is
  not testing what it claims — the exact failure mode the §5 drill inventory
  overclaim (S1) was about.
- Apply: set `lab.clock.real_sleep_s = 0.05` before forking in any real-fork
  timing test (the only precedent is
  `tests/test_supervisor_run.py::test_a_stale_child_raises_the_flag_on_disk_and_in_bd`,
  invisible from `tests/_foreman.py`); arm a crash BEFORE the dispatch attempt
  it must land in, not after; requeue the next `ChildScript` AFTER the rebuild
  that consumes it.
- Source: S1 batches 4a/4b, `scratchpad/probes/s1-triage.md`.

## A liveness assertion placed after a barrier proves nothing  (2026-09-02)

- Observed: `assert not _runner_alive(pid)` sat after
  `ProcSpawner.await_barrier(timeout_s=15.0)` while the child slept 6s. A
  mutant aiming `terminate` at a bogus pid SURVIVED — the assertion was
  satisfied by the child timing out on its own and could not tell a real kill
  from a natural exit. Moving the same assertion to immediately after
  `steer()` returns passes clean and kills the mutant.
- Why it matters: the one assertion whose whole job was proving a live child
  got killed proved nothing, and only mutation exposed it.
- Apply: assert a process died at the earliest point the product guarantees it
  (here: `steer()` terminates with proof before returning), never after a wait
  long enough for the process to end by itself. Same rule for any timeout-
  bounded barrier.
- Source: S1 batch 4b mutant B4B-M4, `tests/test_foreman_steer.py`.

## `model_copy(update=)` silently skips `model_validator(mode="after")`  (2026-09-02)

- Observed: `foreman/cases.py` built an infra-retry `MintRequest` with
  `_request(...).model_copy(update={…})`. Pydantic's `model_copy` does NOT
  re-run validation, so the copy carried a stale `predecessor_gate_id`
  alongside a `predecessor_activation_id` — a combination `MintRequest`'s own
  `_validate_predecessors` (`bdio/wire.py:523`) exists to forbid. `mint.py`
  then raised `CarrierIntegrityError` uncaught inside `Foreman.tick()`,
  permanently: a stranded instance with no human escape (P1, `cr-o85.33.8`).
- Why it matters: the invariant was written, tested, and correct — and simply
  not run. A guard one level above the check is invisible to every test that
  only exercises the constructor.
- Apply: never `model_copy(update=…)` a model that carries an after-validator
  unless the updated fields are provably disjoint from everything the
  validator reads. Prefer field-by-field construction, which forces the
  validator to run and makes the invariant *enforced* rather than *assumed*.
  AUDITED the other five sites in this repo after the fix
  (`supervisor/steer.py:145`, `foreman/config.py:75`,
  `supervisor/workspace.py:480`, `bdio/transitions.py:220`,
  `bdio/roots.py:207`): none is a live defect — THREE target models with no
  after-validator at all (`RootMetadata`, `ActivationMetadata`, `PinResult`)
  and TWO that update a field the validator never reads
  (`MintRequest.session_id`, `ForemanConfig.config_path`). Note WHY the latter
  two are safe: field-disjointness, which nothing enforces and any later edit
  can break — `steer.py:145` is the identical construct on the identical model
  that caused the P1, separated from it only by which field is updated.
  (Classification corrected 2026-09-02 after a sign-off caught the counts
  reversed; the safety conclusion was unchanged.)
- Source: S1 batch 2 + the Fable 5.1 high sign-off (MINOR 8),
  `scratchpad/probes/s1-triage.md`.

## `bd` resolves its workspace by walking UP — a test rig inside this repo binds to the repo's own beads  (2026-09-02)

- Observed: building the DRILL-27 live rig under `scratchpad/live-drill/beads`
  and running `bd init` there answered "This workspace is already initialized"
  with the directory empty — `bd` had resolved upward to
  `/data/codes/coding-ritual/.beads`. The same `bd init` in `/tmp` created its
  own workspace immediately.
- Why it matters: the standing rule is that test labs must never touch this
  repo's own `.beads/`. A rig sited anywhere under the project silently
  violates it, and `bd` reports success rather than refusing — the failure is
  invisible until something writes.
- Apply: site any rig that runs real `bd` OUTSIDE `/data/codes/coding-ritual`
  (the session scratchpad under `/tmp` works). `bd init` printing "already
  initialized" in a directory you just created is the tell. Verify with
  `git status` on `.beads/` afterwards either way.
- Source: cr-o85.32 live acceptance run.

## A test double that satisfies a protocol hides whether anything TEACHES the protocol  (2026-09-02)

- Observed: every lab test of the foreman drove `ShellProfile`, whose child
  script the test itself authored — so the child always wrote
  `$WF_OUTCOME_FILE` and `$WF_EFFECTS_FILE`. The first live run with a real
  `claude` did the task correctly, passed verify, and then exited 0 without
  writing either file or committing, because nothing in the composed brief ever
  mentions them (`foreman/inputs.py::DefaultComposer` joins inputs and stops).
  Graded `fail_code`; 980 green lab tests had said nothing.
- Why it matters: this is a whole class, not one bug. Wherever a double is
  built to satisfy a contract, the tests cannot see whether the production path
  COMMUNICATES that contract to a real participant. The double's compliance is
  authored, not earned.
- Apply: when a component's job includes instructing an external agent, at
  least one test must exercise a participant that was NOT told the protocol by
  the test author — or the gap ships. Ask of any double: "what does this know
  that a real one would have to be told?"
- Source: cr-0zc, found by the cr-o85.32 live run.

## A probe that measures the wrong code path proves nothing

**Verified 2026-09-03.** Phase-0 probe 2 recorded "70KB metadata value
round-trips byte-identical" and was cited in the spec (§11) and by three
separate reviews as the evidence that pinned graph bodies fit. It used
`bd --metadata=@file.json`. Production passes canonical JSON inline as one
argv element (`bdio/client.py:334-335`), which caps at the kernel's
`MAX_ARG_STRLEN` (32 x page size = 131,072 bytes) and fails with
`OSError: [Errno 7] Argument list too long` before bd is reached.

Re-probed on the production path: 130,818 chars verified, 131,329 fails.
On `@file`: 4 MB verified. The recorded number was real; the path was not.

**Rule:** a probe's argv/API shape must match the production call site, and
the probe record must name that call site by `file:line`. A number without
the path it measured is not evidence. Same species as "a test double that
satisfies a protocol hides whether anything TEACHES the protocol" — both are
harnesses proving a property of themselves.

## `claude -p` exits 0 when the API call itself failed  (2026-09-03)

- Observed: a `claude -p ... --model claude-fable-5-1` run that hit an API 500
  returned exit status 0 with a 161-byte error body on stdout. Nothing in the
  exit status distinguishes it from a completed run.
- Why it matters: any wrapper, drill, or orchestrator step that treats
  `exit == 0` as "the model answered" will accept an error line as the answer
  and route on it.
- Apply: judge a `claude -p` run by its output — size and first line — never
  by exit status alone; pre-assign `--session-id <uuid>` so a failed run can be
  resumed rather than re-prompted from scratch. (`codex exec` is unaffected.)

## Verify scripts run as `/proc/self/fd/<n>` — `$0`-relative paths do not exist  (2026-09-03)

- Observed: `supervisor/verify.py` executes a pinned verifier through an open
  descriptor, so inside the script `$0` is `/proc/self/fd/<n>` and
  `dirname "$0"` is `/proc/self/fd`. The process gets no `$WF_*` variables and
  no arguments (`verify.py:302`); only `argv[0]` is hashed.
- Why it matters: the usual `cd "$(dirname "$0")/.."` idiom silently runs
  every check from the wrong directory, and sibling-script calls by relative
  path fail.
- Apply: a verify script anchors on `git rev-parse --show-toplevel` (cwd is the
  §7.3 checkout) and derives everything else from git in that cwd; it calls
  siblings by repo-relative path from that root. See `scripts/verify-feature.sh`.
- Source: cr-o85.34.3

## `_emit` bounds only `tail` and `stalled` — every other report field must arrive bounded  (2026-09-03)

- Observed: `foreman/__main__.py:_emit` fits a report to `MAX_TRANSCRIPT_BYTES`
  by shrinking the `tail` / `stalled` strings alone; an oversized value in any
  other field is emitted as-is (or, if the budget is already blown by them,
  cannot be recovered by `_emit` at all).
- Why it matters: a new rendered field that can grow with the run (a diff stat,
  a findings listing, a gate list) is unbounded output unless its producer
  caps it.
- Apply: cap at render time (`MAX_GATE_DIFF_BYTES` for `diff_stat`) rather than
  extending `_emit`'s field list; keep `_emit`'s two-field contract a
  documented invariant.
- Source: cr-o85.34.4

## A codex-profile writer cannot commit — reviewers on codex, writers on claude  (2026-09-03)

- Observed: the codex sandbox makes `<root>/.git` read-only in both `writes`
  modes, including the `gitdir:` file a worktree carries
  (`tests/test_profiles_git_isolation.py`, probes P2.2/P2.3). A node bound to a
  codex profile can edit files but its commit fails, so it can never produce a
  committed artifact — `no_diff` at best.
- Why it matters: a graph that binds an implementing node to `profile:codex`
  is a dead-end by construction; nothing in resolution rejects it.
- Apply: bind writers (`writes = true`) to claude profiles and reviewers to
  codex; `config/foreman.example.toml` encodes this default. Treat a
  codex-bound writer as a graph authoring error at plan time.
- Source: phase-6 plan §0 D5

## Agent worktrees can start behind the orchestrator's HEAD  (2026-09-04)

- Observed: an implementer dispatched with `isolation: worktree` right after
  three fresh commits found its worktree checked out at the commit three
  behind; the brief named the intended base, so it fast-forwarded
  (`git merge --ff-only <base>`) before editing. Its patch then applied cleanly.
- Why it matters: a patch built on a stale base fails `git apply --check` at
  landing, or worse applies with silently reverted context on files the newer
  commits touched (cases.py was changed by both waves here).
- Apply: every worktree brief names the base commit and asks the worker to
  confirm `git log --oneline -1` matches (fast-forward if not) before editing;
  the orchestrator lands only patches whose report confirms the base.
- Source: followups-p1-p2 session, beads cr-o85.4 / cr-o85.34.9

## A last-line-only gate recipe destroys the identity of a failure  (2026-09-11)

- Observed: the seven-gate recipe compressed each command to
  `echo "[$st] $(echo "$out"|tail -1)"`. When acceptance returned
  `1 failed, 65 passed`, the failing test's name had already been thrown away,
  and the failure never reproduced in 25+ replays — so it could not be
  diagnosed at all, only filed (`cr-l4a`).
- Why it matters: a gate's summary line proves red/green but carries no
  identity. A flake is exactly the case where the evidence exists once.
- Apply: write each gate's full output to its own log file, print the summary
  line, then `grep -h '^FAILED' <logs>` so a red gate names its tests. Keep the
  logs until the slice is committed.

## A file-scoped pytest run is not the marked gate that covers that file  (2026-09-11)

- Observed: a worker was briefed to verify with `pytest tests/test_foreman_main.py`
  and reported 34 passed; the same tree then failed the `-m acceptance` gate.
  That path selects 34 tests, exactly one of which is acceptance-marked
  (`tests/test_foreman_main.py:93`); the gate selects 66 across the suite, in a
  different order and process shape. Ten files carry a module-level
  `pytestmark` that a path-scoped brief silently ignores — verified with
  `grep -ln '^pytestmark' tests/*.py tests/acceptance/*.py`.
- Why it matters: green on a path is not evidence for the marker gate the
  orchestrator must pass, and the orchestrator is the one who finds out.
- Apply: brief workers with the marker expression from
  `.claude/project/verification.md`, never a file path, whenever the change
  touches a marked test. A worker's green is a signal, never the gate.
- Source: Slice 1c, bead cr-l4a

## Assembling a brief by text extraction silently drops the sections above the anchor  (2026-09-11)

- Observed: a worker brief was rebuilt across dispatches with
  `sed -n '/^--- ITEM 1/,$p' previous-brief.md`, which starts the extract at the
  first item and drops everything above it. Two design rulings the orchestrator
  had already made (where the CLI gets its graph, which bead field carries the
  task brief) lived in that header and vanished. The worker blocked on exactly
  those two questions a second time, costing a full dispatch.
- Why it matters: the worker sees only the assembled artifact. A section the
  orchestrator "already decided" does not exist unless it is in the bytes sent,
  and re-answering looks like worker failure rather than orchestrator error.
- Apply: after assembling any brief from parts, grep the finished file for one
  distinctive string per required section and print the counts BEFORE
  dispatching. Treat the assembled file, not the intent, as the specification.
- Source: Slice 2b, dispatches 3-5
