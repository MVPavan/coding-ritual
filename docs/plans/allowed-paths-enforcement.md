# Decision document — real `allowed_paths` enforcement at the runner layer

Bead **cr-n2z (P1)**. Resolves ADR 0001 point 3 ("prevention is deferred, with
an explicit trigger"). Status: **proposal for the repo owner**; this document
does not edit ADR 0001. Probes run 2026-09-04 on the development host; every
CLI claim is quoted from `--help` run here or marked as an unprobed
documentation/repo-probe claim. Probe paths elided to `/tmp/probe/checkout`.

## 1. Trigger status

- **Automatic multi-tick execution (`foreman run`) landing — FIRED.**
  `workflow_interpreter/foreman/__main__.py:132` registers the subcommand
  (`run = commands.add_parser("run")`, with `--poll` and `--max-wall`); `:463`
  dispatches it (`if args.command == "run": result = foreman.run(args.root_id,
  poll_s=..., max_wall_s=...)`).
- **No human reads the complete diff before every transition — FIRED**,
  entailed by the first: `foreman run` polls and ticks with no per-transition
  diff read. ADR 0001 `:77-79` already records that even a single manual tick
  routes and dispatches without mandatory full-diff review.
- **Any write-capable runner not assumed cooperative — not yet** (ADR 0001 point 4).

Prevention is therefore blocking as of the phase-5 foreman landing.

## 2. What "prevention" must mean here

1. **The write cannot land on disk.** ADR 0001's "Rejected" section kills
   grading-time rejection — the edit already landed by the time it is caught.
   The bound is at the tool or OS layer, before the bytes.
2. **Per node, from `allowed_paths`.** Already plumbed to the runner layer as
   `TaskSpec.allowed_paths` (`supervisor/profile.py:149`); read today only by
   exit grading, so no new schema field. The schema already enforces the shape —
   `writes = false` ⇒ empty, `writes = true` ⇒ non-empty
   (`schema/messages.py:127-133`) — so every writer already declares a scope.
3. **The three §6 channels stay writable regardless of `writes`.**
   `$WF_OUTCOME_FILE`, `$WF_EFFECTS_FILE`, `$WF_ARTIFACT_DIR` (and
   `$WF_SCRATCH_DIR`) live under `channels/` (`supervisor/paths.py:264-290`); a
   reviewer with no writable outcome file grades `fail_code` for a missing
   marker (`profiles/codex.py:14-22`). The bound must carve `channels/` back in
   and must **not** grant the activation directory one level above it (receipt,
   exec ledger, exit file, completion evidence live there).
4. **`.git` cuts both ways.** Claude denies `Edit(<cwd>/.git)` and
   `Edit(<cwd>/.git/**)` (`profiles/claude.py:75-97`) because `.git/config` and
   `.git/hooks/` name programs the *wrapper's* git later runs — but §7.4 has the
   runner commit under a wrapper-assigned committer address
   (`supervisor/channels.py:224-226`), needing `.git` writable. See **O2**.
5. **Verifier scripts must be outside every writer's grant.** In
   `workflows/build-loop.toml` the `implement` node has
   `allowed_paths = ["workflow_interpreter/**", "tests/unit/**"]` (`:111-112`)
   while its checks are `scripts/checks/*.sh` (`:114-116`). `scripts/**` is in no
   node's `allowed_paths` in either shipped graph
   (`workflows/feature-delivery.toml:38` is `["src/**", "tests/**"]`), so a bound
   derived from `allowed_paths` excludes `scripts/**` for free.
6. **The ADR's residual gap.** Checks run in a detached `VerifyTree` at the
   artifact commit (`supervisor/exit.py:556`); provenance pins only `argv[0]`
   (`supervisor/channels.py:288`). `verify.py:256-268` refuses a check whose
   digest misses the pin, so a modified top-level script is caught; what that
   script reads or sources is not (helpers, `pyproject.toml`, pytest config, the
   tests). A write-layer bound closes this **only outside** the node's own
   `allowed_paths` — `implement` writing `tests/unit/**` still shapes what
   `tests-parse.sh` measures. Per-option verdicts below.

## 3. Options

### A. Per-profile tool / sandbox layer

**Mechanism.** Each profile turns `allowed_paths` into its own vendor bound at
`build_command` time.

- **claude** — narrow `_bounds` (`profiles/claude.py:251-282`). Today
  `writes = true` grants `Bash` plus `Edit(/<cwd>/**)` — the whole checkout.
  Enforcement replaces the tree rule with one `Edit` rule per `allowed_paths`
  entry plus the channel rules, and swaps the bare `Bash` for a prefix
  allow-list. Probed `--help` (claude 2.1.258) has every flag this needs:
  `--allowedTools/--allowed-tools` and `--disallowedTools/--disallowed-tools`
  (both "Comma or space-separated list of tool names ... (e.g. `Bash(git *)
  Edit`)"), `--permission-mode` (choices `acceptEdits, auto, bypassPermissions,
  manual, dontAsk, plan`), `--tools`, `--settings`, `--setting-sources`,
  `--add-dir`, `--restricted`. *Repo-probed, not re-probed here*
  (`profiles/claude.py:1-23`): `Write(path)` rules are inert, `Edit(path)`
  governs every file-editing tool, and an absolute path in a rule is `//` + it.
  **The hole is `Bash`**, and the profile says so itself
  (`profiles/claude.py:165-175`): "a bare `Bash` allow walks straight out of
  it: anything the model can phrase past three prefix deny-rules executes
  unconfined." A prefix allow-list is bypassed by `uv run python -c
  "open('x','w')"`, by `sh -c`, by a heredoc, by a `>` redirect inside an
  allowed command, and by any test the runner may write and then run.
  `--restricted` removes `Bash` outright, which a `writes = true` implementer
  cannot accept. → prevents file-tool writes outside the globs, nothing more.
- **codex** — the one vendor with an OS sandbox. `codex exec --help` (codex-cli
  0.151.0) shows `-s/--sandbox <SANDBOX_MODE>`
  `[possible values: read-only, workspace-write, danger-full-access]`,
  `--add-dir <DIR>` ("Additional directories that should be writable alongside
  the primary workspace"), `-C/--cd`, and `-c key=value`. The profile builds the
  box from `KEY_SANDBOX_MODE` / `KEY_WRITABLE_ROOTS`
  (`sandbox_workspace_write.writable_roots`) plus `network_access=false` and
  `exclude_slash_tmp=true` (`profiles/codex.py:125-128, 259-310`); enforcement
  only changes what goes into `writable_roots` — resolved allowed dirs **+**
  `channels/` instead of the checkout-wide root. The repo's own probes
  (`profiles/codex.py:14-30`, `tests/test_profiles_git_isolation.py`) establish
  "checkout unwritable, listed roots writable" and "`<root>/.git` read-only in
  both modes". → prevents every write outside the roots, shell included.
- **opencode** — nothing to use. `profiles/opencode.py:1-31`: no sandbox,
  permission or deny flag; resolved permission stack begins
  `{"permission":"*","action":"allow","pattern":"*"}` for every agent including
  `plan`; `build_command` (`:135`) already refuses to launch.

**Glob limits.** Both shipped graphs use directory-prefix globs only
(`tests/acceptance/**`, `workflow_interpreter/**`, `tests/unit/**`, `src/**`,
`tests/**`). Claude's rules are path patterns and take file-level patterns
natively. Codex's `writable_roots` are **directories**, so a file-level or
wildcard-segment pattern (`docs/*.md`, `**/*_test.py`) is inexpressible and must
be refused loudly — silently widening to the containing directory is worse than
no bound. **WSL2 feasibility:** no kernel dependency; works today.
**Cost.** `profiles/claude.py` (`_bounds` + a glob→rule mapper + a `Bash`
allow-list), `profiles/codex.py` (`_workspace_root`, `_sandbox_flags`),
`profiles/errors.py` (refusal for inexpressible globs), tests. No supervisor change.
**Surfacing.** Claude records refusals in `permission_denials`
(`profiles/claude.py:165-175`); codex emits `patch rejected: writing is blocked
by ...` on stderr, exit code 0 (`profiles/codex.py:14-18`). Both land in the run
log; neither produces a wrapper-side signal today.
**Residual:** closes for codex (`scripts/**` outside the roots); for claude only
against file tools, not `Bash`. Never closes inside the node's own grant.

### B. Wrapper-level mount sandbox, uniform across profiles

**Mechanism.** The supervisor wraps the runner argv before `os.execvpe`
(`supervisor/launch.py:462`): checkout bind-mounted read-only, each resolved
allowed directory and the activation's `channels/` bind-mounted read-write.
Vendor-independent — the bound holds for the shell, for `uv run python -c`, and
for any subprocess. Host probes:

```text
$ uname -a
Linux <host> 6.6.87.2-microsoft-standard-WSL2 #1 SMP PREEMPT_DYNAMIC Thu Jun  5 18:30:46 UTC 2025 x86_64 ... GNU/Linux
$ which bwrap unshare        -> /usr/bin/bwrap  /usr/bin/unshare
$ unshare --version          -> unshare from util-linux 2.39.3
$ unshare -rm true                          ; exit=0
$ unshare -rm mount --bind /tmp /tmp        ; bind-exit=0
$ bwrap --version            -> bubblewrap 0.9.0
$ bwrap --ro-bind / / --dev /dev --bind /tmp /tmp --unshare-user --unshare-pid /bin/true ; exit=0
$ apt-cache policy bubblewrap -> Installed: 0.9.0-1ubuntu0.1 / Candidate: 0.9.0-1ubuntu0.1
```

**Unprivileged user namespaces work under this WSL2 kernel and bubblewrap 0.9.0
is already installed** — nothing needed installing. Enforcement probe, form
`bwrap --dev-bind / / --ro-bind $CO $CO --bind $CO/tests/acceptance
$CO/tests/acceptance <cmd>`:

```text
B1 write outside allowed dir : /bin/sh: cannot create .../workflow_interpreter/foo.py: Read-only file system ; exit=2
B2 write inside allowed dir  : x ; exit=0
B3 chmod escape attempt      : chmod: changing permissions of '.../workflow_interpreter': Read-only file system ; chmod-exit=1
                               then: cannot create .../foo.py: Read-only file system ; exit=2
B4 write via python -c       : OSError: [Errno 30] Read-only file system: '.../workflow_interpreter/bar.py' ; exit=1
F1 file-level rw bind        : edited ; exit=0
F2 new sibling next to it    : cannot create .../other.py: Read-only file system ; exit=2
F3 bwrap nested inside bwrap : exit=0
```

**Prevents** every write outside the read-write binds, by any process, through
any interpreter. F3 shows codex's own sandbox still starts inside it, so B
composes with A. **Does not prevent** network (a separate `--unshare-net`
decision), writes inside the grant, or deletion of a granted dir.
**Glob limits.** Mounts are paths, not globs. A directory-prefix glob is one
`--bind`; a file-level pattern binds per file (F1 works) but then **new** files
matching it cannot be created (F2 fails) — the same build-time refusal as in A.
Allowed dirs that do not exist must be created before the bind.
**WSL2 feasibility.** Confirmed on this host for both `unshare -rm` and `bwrap`.
**Fallback where user namespaces are unavailable** (hardened kernels, some
containers, macOS, Windows-native): no equivalent exists, so the runner is
**refused** the way opencode is today unless policy says otherwise (**O1**).
Silent degradation is the failure mode to avoid.
**Cost.** New `supervisor/sandbox.py` (glob→bind plan, capability detection,
argv wrapping), a call site in `launch.py`, one key in `supervisor/config.py`,
tests. Profiles unchanged.
**Surfacing.** As `EROFS`/`Errno 30` in the runner's transcript — it sees the
failure and reports it like a failing test.
`AuditFlag.EFFECT_OUTSIDE_ALLOWED_PATHS` (`exit.py:657`) becomes a
should-never-fire invariant — a useful regression signal.
**Residual:** closes for every profile — `scripts/**` is read-only for every
writer; still open inside the node's own grant.

### C. Layered A + B

B is the bound; A is the same intent in vendor-native form, so denials arrive as
clean tool refusals instead of an `EROFS` mid-command. F3 confirms the two nest.

### D. chmod tripwire + detection (the floor)

`chmod -R a-w` the checkout except allowed dirs and `channels/`; diff after.

```text
D1 write outside allowed dir : sh: cannot create .../workflow_interpreter/foo.py: Permission denied ; exit=2
D2 write inside allowed dir  : exit=0
D3 same user chmods back     : chmod u+w ... && echo y > ... -> y ; exit=0
```

D3 is the verdict: the runner **owns** the files, so `chmod u+w` restores write
access and the write lands. A tripwire for accidents, not a bound against
anything deliberate; it also perturbs mode bits git tracks. **Residual: does not
close.** Near-zero cost, but not sufficient for the trigger that fired.

## 4. Recommendation

**Adopt C, phased: B first, then A.**

The trigger that fired is unattended multi-tick execution, and B is the only
option whose bound survives a granted shell (B1–B4). A alone leaves the claude
`writes = true` path — `build-loop`'s `write_tests` and `implement` nodes —
bounded by prefix deny-rules the model can phrase around, by the profile's own
admission. D bounds nothing (D3). B needs no profile change, and this host has
working bubblewrap and user namespaces.

1. **Phase 1 (blocking, ships first).** `supervisor/sandbox.py` + the
   `launch.py` wrap + capability detection + an `enforce_allowed_paths` config
   key. Refuse inexpressible globs; refuse dispatch when the host cannot sandbox
   and the mode is strict.
2. **Phase 2.** Profile-native expression: codex `writable_roots` from
   `allowed_paths`; claude per-glob `Edit` rules replacing the whole-checkout
   `_tree_rule`. Keep the bare `Bash` grant (under B it is no longer the hole)
   and the existing push and `.git` denials.
3. **Phase 3.** Treat `AuditFlag.EFFECT_OUTSIDE_ALLOWED_PATHS` as
   never-expected; add a §13 drill asserting a denied write is graded, not
   absorbed.

Files that would change: `supervisor/sandbox.py` (new), `supervisor/launch.py`,
`supervisor/config.py`, `profiles/claude.py`, `profiles/codex.py`,
`profiles/errors.py`, the graph JSON Schema description and
`schema/messages.py` prose (the field's meaning gains a second sentence:
exemption *and*, when enforcement is on, bound), spec §2/§6/§7.5,
`workflows/README.md`, a new §13 drill. ADR 0001 is not edited here.

## 5. Open questions for the owner

1. **O1 — unsupported host policy.** When user namespaces are unavailable:
   refuse dispatch (strict), or fall back to A with a recorded degradation
   flag?
2. **O2 — `.git` under a mount bound.** Does the runner keep committing the
   artifact (`.git` read-write minus `config`/`hooks`), or leave a dirty tree
   for `workspace.record_attribution`? Decides the bind plan; settle before
   phase 1.
3. **O3 — glob expressiveness.** Refuse file-level and wildcard-segment patterns
   loudly (recommended), or widen them to the containing directory? Yes =
   refuse.
4. **O4 — network.** Add `--unshare-net`, enforcing "no profile ever pushes"
   for claude too (codex has it via `network_access=false`)? It would also cut
   the claude CLI's own API access, so almost certainly no.
5. **O5 — rollout scope.** Both shipped graphs at once, or `build-loop` only —
   the graph whose `implement` node writes `workflow_interpreter/**` while its
   checks live in `scripts/**`?
