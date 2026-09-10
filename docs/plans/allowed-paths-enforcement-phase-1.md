# Phase 1 — `allowed_paths` as a real mount bound (bead `cr-n2z.1`)

v2, after critic round 1 (two blockers: bind order re-opened the pins; a read-only checkout broke the node's own toolchain). Implements option **B** of `docs/plans/allowed-paths-enforcement.md` under the owner decisions of 2026-09-04, recorded verbatim in ADR 0001. Probes run on this host (`bubblewrap 0.9.0`, WSL2 6.6.87.2) under `/tmp`; results quoted, not recalled.

## 1. Decisions as applied

| id | decision | applied as |
| --- | --- | --- |
| O1 | `bwrap` is the bound; absent or self-test red ⇒ REFUSE to dispatch, every node, no fallback | `sandbox.probe()` once per wrapper process; refusal is a typed close (§3) |
| O2 | runner keeps committing; git dir writable except what makes git execute programs | ro pins `config`, `config.worktree`, `hooks/`, `info/`, `modules/*/config`, `refs/wf`; rw `objects`/`refs`/`logs`/`packed-refs`/worktree-gitdir |
| O3 | only `<dir>/**` accepted, refused at instantiation | one JSON-Schema `pattern` on a new `$defs/grant_glob` (§4) |
| O4 | no `--unshare-net`; codex keeps `network_access=false` | no `--unshare-*` beyond bwrap's implicit user+mount ns |
| O5 | on by default, both shipped graphs, every node | `SupervisorConfig.sandbox: SandboxMode = BWRAP`; `off` logged per dispatch + `AuditFlag.SANDBOX_OFF` on the close |

`RUNNER_PROTOCOL_WRITE_STEP` (`foreman/constants.py:84-87`) is unchanged — that is what O2 buys. A `writes = false` node gets the checkout read-only with only `channels/` writable; codex's own `workspace-write` box nests **inside** the mount bound (decision-doc probe F3), so the two compose.

## 2. The invocation

Bind order **is** mount order, and the fix for blocker 1 is that `wrap()` emits, unconditionally, in this order: **broad ro roots → git rw binds → grants → channels → ro pins LAST**. Probed: pins placed before a later rw bind of their parent are re-opened — `--ro-bind <M>` → `--bind <M>/.git` → `--ro-bind <M>/.git/hooks` → `--bind <M>/.git` lets a hook be written (`rc=0`); the same binds with the pin emitted last refuse it (`rc=1 Read-only file system`). Grants can never re-open a pin because `.`-leading segments are not valid grants (§4).

Worktree `writes = true` (`<M>`=`repo_root`, `<W>`=`wrapper_root`, `<C>`=checkout, `<G>`=`<M>/.git/worktrees/<name>`, `<A>`=activation dir, `<S>`=`<A>/channels/scratch`):

```text
bwrap --die-with-parent
      --dev-bind / /
      --ro-bind <M> <M>             --ro-bind <W> <W>        --ro-bind <C> <C>
      --bind <M>/.git/objects …     --bind <M>/.git/refs …   --bind <M>/.git/logs …
      --bind <M>/.git/packed-refs … --bind <G> <G>
      --bind <C>/tests/acceptance …    --bind <A>/channels <A>/channels
      --ro-bind <M>/.git/refs/wf …     --ro-bind <G>/config.worktree …  --ro-bind <G>/info …
      -- <inner argv…>
```

`--die-with-parent` makes the box a leaf of the supervisor's tree: if the wrapper is SIGKILLed the kernel tears the sandbox down instead of leaving an unreapable runner holding mounts. Worktree `writes = false`: the three `--ro-bind`s plus `--bind <A>/channels` only. In-repo `writes = true`: `<C> == <M>`, `<G> == <M>/.git` (a directory, rw as a *whole* because `index.lock` is created in it), pins then add `config`, `hooks`, `info`, `modules/*/config`.

| | W1b worktree rw | W2 worktree ro | I1 in-repo rw |
| --- | --- | --- | --- |
| write in grant / channels | `0` / `0` | `1 Read-only` / `0` | `0` / `0` |
| `git status` / `add` / `commit` | `0`/`0`/`0` | `0` / `128 Unable to create '…/index.lock': Read-only file system` | `0`/`0`/`0` |
| write outside grant (sh, `python -c`) | `Read-only file system` | `Read-only` | `Read-only file system` |
| `git config user.name` | `could not lock config file …: Read-only file system` | same | `rc=4 … Device or resource busy` |
| hook / `config.worktree` / `info/attributes` | all `Read-only` | all `Read-only` | `Read-only` / — / `Read-only` |
| write main repo tree | `Read-only` | `Read-only` | n/a |

`<M>/.git/logs` is load-bearing and was missed first: without it `git commit` dies `fatal: cannot update the ref 'refs/heads/probe-wt': unable to append to '…/.git/logs/refs/heads/probe-wt': Read-only file system`. `packed-refs`, `<G>/config.worktree` and `<G>/info` are **pre-created empty** when absent — that fixed set only; every other pin is emitted **only if the path exists** (§8); `<M>/.git/refs/wf` is therefore unpinned until the first evidence ref exists, so its test asserts the pin's PRESENCE in the plan once the ref exists, not only the refused write. A file ro-bind blocks the rename over it as `EBUSY`, not `EROFS`.

**Toolchain env (blocker 2).** A read-only checkout breaks the node's own `verify` command: `uv run` creates `.venv` in the checkout. The launcher already owns the child env (`RunnerChannels.env()`), so it points every cache at `$WF_SCRATCH_DIR`: `UV_PROJECT_ENVIRONMENT=<S>/venv`, `UV_FROZEN=1` (never rewrite `uv.lock` — a stated limitation: a writing node cannot `uv add` a dependency under the bound; it reports `fail_plan`), `RUFF_CACHE_DIR=<S>/ruff`, `MYPY_CACHE_DIR=<S>/mypy`, and `PYTEST_ADDOPTS` gaining `-o cache_dir=<S>/pytest` **appended** to any inherited value, never replacing it — the append lives in `profiles/_base.py:383-389` (the merge site that sees the inherited env), not in `RunnerChannels.env()`, which takes no env and is merged last. `-o cache_dir` is chosen over `-p no:cacheprovider` because the latter also disables `--lf`/`--ff`/`--sw`, which a `writes = true` implementer legitimately uses. uv's own download cache stays in `$HOME` (writable by design). Probed in a bwrap'd read-only checkout of THIS repo, cwd = the worktree:

| env | `uv run pytest -q tests/test_semantic_rules.py` | `uv run ruff check workflow_interpreter/` | `uv run mypy --strict …/foreman/errors.py` |
| --- | --- | --- | --- |
| none | `rc=2 error: failed to create directory '<C>/.venv': Read-only file system (os error 30)` | same | same |
| uv only | `rc=0`, `53 passed` + `PytestCacheWarning: could not create cache path <C>/.pytest_cache…` | `rc=2 error: Failed to initialize cache at <C>/.ruff_cache: Read-only file system (os error 30)` / `ruff failed` | `rc=2 INTERNAL ERROR` |
| all four | `rc=0`, `53 passed` | `rc=0`, `All checks passed!` | `rc=0` |

So `UV_PROJECT_ENVIRONMENT`/`UV_FROZEN`, `RUFF_CACHE_DIR` and `MYPY_CACHE_DIR` are load-bearing; `PYTEST_ADDOPTS` is a nicety — a runner that re-exports it costs a warning, not a run. The wrapper's own §7.3 verify step is unaffected: it runs OUTSIDE the sandbox, in the detached `VerifyTree` (`exit.py:548-556`).

**Untouched.** `cwd` (`launch.py:456` chdirs before exec; no `--chdir`), pgid (`setsid` precedes the exec; bwrap's fork stays in the group — probed `leader_pid == child_pgid`), exit code (probed `exit 42` ⇒ 42), stdout/stderr (fd 1/2 are dup'd from the log fd BEFORE exec, so the log lands even though `<A>` is read-only — probed directly), CLI home dirs (`~/.claude`, `~/.codex` — unbound; §8).

**Where it wraps.** In `ForkBarrierLauncher.__call__` (`launch.py:281`), the last transform before the receipt is written — not `Dispatcher._launch`. The launcher is the supervisor-owned exec §6 already proves a profile cannot bypass. `Dispatcher._launch` builds the `SandboxPlan` from the `TaskSpec` and injects it as `ForkBarrierLauncher(..., plan=plan)`. **The receipt records the WRAPPED argv**, because `handle.pid` names `bwrap`, not the runner (probed: bwrap forks) — the inner argv would describe a process the handle does not name, and the wrapped argv is the durable audit record of the exact bound. Liveness, identity and `terminate` are pgid/`/proc`-based and unaffected.

**Exit-127 sentinel.** bwrap makes `argv[0]` always exist, so a vanished vendor CLI would grade as a plain exit 1 and drill 22 would stop meaning anything. The launcher therefore resolves the vendor `argv[0]` (`shutil.which`, else `os.stat`) BEFORE wrapping and, when it is missing, exits `EXIT_EXEC_FAILED` (`launch.py:124`) **from the forked child in `_child`, before `execvpe`** (`launch.py:456-462`) — never from the parent path, where an `os._exit` would kill the wrapper mid-dispatch with the receipt already written.

## 3. `workflow_interpreter/supervisor/sandbox.py` (new)

- `SandboxMode(StrEnum)`: `BWRAP` | `OFF`; `SupervisorConfig.sandbox: SandboxMode = BWRAP` (`config.py:78`).
- `SandboxPlan(BaseModel, frozen)`: `ro_roots`, `git_rw`, `grants`, `channels`, `ro_pins` — absolute, emitted in that order by `wrap()`.
- `plan_for(task, *, repo_root, wrapper_root, channels_dir) -> SandboxPlan`, with **three** shapes keyed off the checkout, no subprocess: **no `.git`** ⇒ grants + channels only; **`.git` a directory** ⇒ in-repo; **`.git` a file** ⇒ parse `gitdir:`, common dir from `<G>/commondir` ⇒ worktree. `repo_root` and `wrapper_root` must exist (the lab creates them, §6).
- `wrap(argv, plan) -> tuple[str, ...]`; `probe(config) -> SandboxCapability` (`available`, `version`, `reason`): `bwrap --version` plus a one-shot self-test binding a temp dir that must allow a write inside and refuse one outside. Cached in a module-level slot, once per wrapper process; measured **2.3 ms** per `bwrap` startup (50 runs in 0.114 s).
- `supervisor/errors.py`: `SandboxUnavailable(SupervisorError)` and `SandboxPathRefused(SupervisorError)` (defence in depth behind §4).

**Refusal path.** `Dispatcher._launch` checks `probe()` before `profile.prepare`, so no session is minted for a launch that cannot happen. `supervise._run` gains an `except SandboxUnavailable` clause **before** the generic `(SupervisorError, OSError)` catch (`supervise.py:288`), closing `ERROR_TRANSPORT` with `Deviation(kind=DEVIATION_SANDBOX_UNAVAILABLE)` — the `InputsUnavailable` shape (`supervise.py:245-262`). A missing `bwrap` is permanent and must not burn §10.2 retries. Full inventory for the new `DeadEndKind.SANDBOX_UNAVAILABLE` — every one is required, the `cases.py` dict raises `KeyError` otherwise: `bdio/constants.py` (the deviation) · `bdio/bounds.py:40` (`_RETRY_EXEMPT_DEVIATIONS`) · `foreman/frontier.py:36` (enum member) and `:99-118` (`_dead_end`) · `foreman/cases.py:523-526` (the `{...}[kind]` map) · `foreman/constants.py` (`HALT_SANDBOX_UNAVAILABLE` + its `__all__:25-35` entry) · `foreman/events.py:142-146` (the skip set) · `foreman/supervise.py` (clause + import) · `tests/test_bdio_seams_bounds.py:19` (exempt-set parametrization).

**`sandbox = off` recording.** `LaunchReceipt` (`models.py:243-259`) gains `sandbox: SandboxMode`. `ExitObserver` already reads the activation's records while computing §7 evidence; it reads the receipt and appends `AuditFlag.SANDBOX_OFF` beside the other flags at `exit.py:652-663`. Evidence side, so it renders to the operator and blocks nothing. Test: a dispatch with `sandbox = off` closes carrying the flag; the same dispatch with `bwrap` does not.

## 4. Glob refusal and the grant mapping

Pattern `^(?:[A-Za-z0-9_-][A-Za-z0-9._-]*/)+\*\*$` — no segment may start with `.`. The JSON-Schema `pattern` on a **new** `$defs/grant_glob`, referenced only by `node.allowed_paths.items`, is the SOLE owner (the `node.runner` precedent, `graph_schema.json:182`, cr-0jd): no new `allowed_paths_well_formed` clause and no new message. Not on `$defs/relative_path` (`graph_schema.json:63`), which `verify.cmd`/`cwd` share. Probed: the round-1 pattern wrongly accepted `.git/**`, `.wf/**`, `.venv/**`, `./**`, `a/.git/**` — a `.git/**` grant would have re-opened every pin. This one rejects all of those and accepts all five shipped values (`tests/acceptance/**`, `workflow_interpreter/**`, `tests/unit/**`, `src/**`, `tests/**`). **Deliberate limitation:** a hidden directory can never be a grant, so `.claude/**` is refused too; a node needing one is a request to revisit this rule, not to widen the regex. A refusing constraint adds no content, so content hashes are unchanged.

Mapping: strip the trailing `/**` ⇒ repo-relative directory; join to the checkout, `realpath`, assert the result is still inside the checkout, `mkdir(parents=True, exist_ok=True)` when absent.

## 5. Prose edits (one line each, no rewrites)

- `docs/specs/workflow-interpreter.md:325-327` (§2 rule 6): after "a reporting exemption, not a bound" add "— and, with `sandbox = bwrap`, the node's writable mount set; entries must be `<dir>/**`".
- `:608-625` (§6 runner floor): the wrapper wraps every profile's argv in the mount bound before exec; profiles do not opt in and cannot opt out.
- `:679-686` (§7.5): replace "Real enforcement belongs at the runner layer and does not exist yet." with the mount bound + `effect_outside_allowed_paths` as a should-never-fire regression signal.
- `graph_schema.json:209`: second sentence naming the mount bound under `sandbox = bwrap`.
- `workflows/README.md`: entries must be `<dir>/**`, no hidden directories, and become the node's writable mounts.
- `.repo-context/verification.md`: a green run on a host without `bwrap` does not evidence the bound.
- ADR 0001: status, point 3 → decided, consequences (see the ADR diff).

## 6. Tests (red first)

Unit (`tests/test_supervisor_sandbox.py`): all three `plan_for` shapes incl. the no-`.git` case; `wrap()` emits pins last (assert the argv order, with the escape of §2 as a regression case); grant mapping incl. `mkdir` and symlink containment; `probe` caching; the missing-`argv[0]` sentinel. Schema: every reject class of §4 as a schema error; both shipped graphs load with unchanged content hashes. `proc`: write outside the grant ⇒ `EROFS` **and** the exit grades `fail_code`, not absorbed; write inside ⇒ ok and the runner's own commit is pinned as the artifact; `git config`, a hook write and a `refs/wf` update refused; `channels/` writable; `writes = false` cannot write anywhere in the checkout; the node's own `uv run` verify passes under the §2 env and fails without it; `sandbox = off` ⇒ `AuditFlag.SANDBOX_OFF`; `probe()` forced red ⇒ the §3 refusal, asserting the infra-retry count did not move.

**Skip policy.** The `plan_for`/`wrap` unit tests and the refusal-path test never skip — they use no real `bwrap`. Only the real-bwrap `proc` tests skip, loudly, via `pytest.skip(probe().reason)`.

**Rig.** `tests/_profiles.py:159-168` `make_supervisor_config` sets `repo_root = tmp_path/"repo"` and never creates it; `make_task` (`:191-200`) hands a checkout with no `.git`. Edits: `_profiles.py` — create `repo_root`/`wrapper_root`, add a `sandbox` override; `Lab` (same file) — thread the `sandbox` key and set the §2 cache env on its stubs; `_supervisor.py:299` `make_config` — accept and default `sandbox`; `_workspace.py` — no change beyond `make_repo` (`_supervisor.py:194`) already creating a real repo. Routed through them: `test_profiles_command.py`, `test_profiles_process.py`, `test_profiles_git_isolation.py`, `test_profiles_live.py`. Each CLI stub must write only into its grant or `channels/` — audit all of them.

## 7. Slices (disjoint files, ≤1 day each)

1. `supervisor/sandbox.py`, `errors.py`, `config.py` + unit tests. Gate: `uv run pytest tests/test_supervisor_sandbox.py`.
2. `schema/graph_schema.json` + schema tests. Gate: `uv run pytest tests/test_schema_*.py` + the content-hash assertions.
3. **Rig repair first** (§6, incl. the `Lab` `sandbox` key), then `supervisor/launch.py` (wrap site, receipt field, argv[0] sentinel), `foreman/supervise.py`, `bdio/constants.py`, `bdio/bounds.py`, `foreman/frontier.py`, `foreman/cases.py`, `foreman/constants.py`, `foreman/events.py`, `supervisor/models.py`, `supervisor/exit.py`, `profiles/_base.py` (the `PYTEST_ADDOPTS` append), `tests/test_bdio_seams_bounds.py`. Gate: `uv run pytest -m proc` and `-m bd`.
4. §5 prose + ADR 0001 only. Gate: `scripts/verify-feature.sh`, then `uv run pytest -m acceptance`.

**Out**: profile-native expression = `cr-n2z.3`; the §13 drill and the never-expected-flag invariant = `cr-n2z.4`; **hardening `packed-refs` and the instance branch against ref forgery** (§8) = a new bead.

## 8. Risks

- **`--dev-bind / /` leaves everything not explicitly bound writable.** Probed: writes to `/tmp` and `$HOME` from inside the box both succeed, and in-repo mode with only the checkout ro-bound left a sibling repo writable. The `--ro-bind <M>` + `--ro-bind <W>` pair is mandatory, not defensive: it covers the main repo's tree, this repo's agent worktrees (`<M>/.claude/worktrees/`) and the `.wf/` cache — probed protected (`receipt.json`, `exec.ledger`, a sibling activation dir all `Read-only`) with `channels/` still writable. `$HOME` and `/tmp` stay writable **by design**: an accepted residual.
- **Ref forgery survives O2.** `refs/` and `packed-refs` must be rw for the runner's own commit, so ro-pinning `<M>/.git/refs/wf` protects the wrapper's evidence refs only as LOOSE refs; a runner can still rewrite `packed-refs` or move the instance branch. Filed as a bead (§7 OUT). ADR 0001's residual therefore closes for the *examiner-editing* gap outside the grant, not for ref integrity.
- **`handle.pid` is bwrap's**, not the runner's — group termination and `/proc` identity are unaffected, but code reading `comm`, or assuming the pid names the vendor process, is wrong.
- **bwrap `rc=1` ambiguity**: pre-creation + `realpath` prevent the bad-bind-source case, but a bwrap setup failure and a runner exiting 1 are still indistinguishable from the exit code alone. Residual.
- **Cross-filesystem venv**: with the scratch dir on a different filesystem from uv's `$HOME` cache, uv logs `Failed to hardlink files; falling back to full copy` — correct but slower. `.wf/` sits beside the repo, so in production it usually shares a filesystem with `$HOME`.
- **`EBUSY` vs `EROFS`** on ro-pinned files: refused either way, but a test asserting the errno must accept both.
- **Submodules** (probed): `<M>/.git/modules/{reference_harnesses,reference_tools}` exist in the main repo; `mvp-harness` does not. A fresh worktree checkout has EMPTY submodule directories with no `.git` file, so worktree mode has nothing to pin — and `<M>` is ro-bound whole anyway. Only in-repo mode needs `modules/*/config` pins, and only for the ones that exist.
