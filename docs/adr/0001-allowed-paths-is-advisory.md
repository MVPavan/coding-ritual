# ADR 0001 — `allowed_paths` is a disclosure exemption, not a containment bound

- **Status:** Accepted; points 1, 2 and 4 implemented 2026-09-03. Point 3 **decided
  2026-09-04** (trigger fired) and now under implementation — see
  `docs/plans/allowed-paths-enforcement.md` (options) and
  `docs/plans/allowed-paths-enforcement-phase-1.md` (the phase-1 plan, bead `cr-n2z.1`).
- **Date:** 2026-09-03; amended 2026-09-04
- **Deciders:** repo owner
- **Reviewed by:** Fable 5.1 (high), Sol (xhigh) — `scratchpad/probes/decisions-fable.md`, `scratchpad/probes/decisions-sol.md`
- **Supersedes wording in:** spec §2 (`:135`), §7.5 (`:649-654`), §6, §12, drill 24 in §13

## Context

`allowed_paths` reads throughout the spec, schema and fixtures as a *static
effect bound* — the set of paths a node may modify. It is not one.

`ExitObserver._undeclared_effects` computes:

```
observed − (runner_declared ∪ allowed_paths)
```

(`workflow_interpreter/supervisor/exit.py:706-733`). A runner may modify any
path, list that path in its own `$WF_EFFECTS_FILE` manifest, and be graded
`done` with no audit flag. This is asserted as correct behaviour at
`tests/test_supervisor_exit.py:299-310`. Spec §7.5 states the same union, so
the code is faithful to the spec; the *naming and surrounding prose* are what
mislead.

No runner profile consumes `allowed_paths` as a sandbox restriction. It reaches
`TaskSpec` (`workflow_interpreter/supervisor/profile.py:149`) and is read only
by exit grading (`supervise.py:155`). A write-enabled claude runner holds
unrestricted `Bash` (`workflow_interpreter/profiles/claude.py:155-180`).

Both reviewers independently confirmed this and added two qualifications:

- Containment is **isolation-dependent**. In `in-repo` mode, artifact
  attribution requires every committed path to appear in the runner's manifest
  (`workflow_interpreter/supervisor/artifact.py:204-228`); `allowed_paths` is
  not an alternative there. In worktree mode that check is skipped.
- `no_diff` rejects a commit but does not require a clean tree
  (`exit.py:684-704`); anti-drift checks commit identity, not scope
  (`exit.py:690-697`).

## Decision

**Keep the union semantics. Correct the language. Split detection from
prevention.**

1. **Rename the meaning, not the field.** Everywhere `allowed_paths` is
   described, it means: *paths whose changes are exempt from undeclared-effect
   reporting. A runner declaration outside this set is equally unflagged.
   Neither is authorization or containment.* Sites to correct: spec §2 `:135`,
   §7.5 `:649-654`, §6, §12, drill 24 in §13; `schema/messages.py:128-131`;
   `supervisor/exit.py:18`; `supervisor/profile.py:149`;
   `foreman/constants.py:77-80` (`RUNNER_PROTOCOL_NO_WRITE_STEP`, which is
   false under the union); `workflows/README.md`; the graph JSON Schema
   description; the `feature-delivery.toml:26` comment.

2. **Detection lands now.** `AuditFlag.EFFECT_OUTSIDE_ALLOWED_PATHS` records
   `observed ∖ allowed` — scope, ignoring what the runner declared — beside
   the existing §7.5 blocking set. Recorded, never raised: the transition is
   unaffected, but a node writing outside its declared scope is now visible
   instead of silent.

   Both computations share one `_observed_paths` helper, so they measure the
   same observation and differ only in what they subtract. Fixture TOML
   comments do not affect the content hash — `canonical_bytes` dumps the
   model (`schema/loader.py:153`) — so the prose corrections were free.

3. **Prevention is deferred, with an explicit trigger.** Real enforcement
   means the write cannot happen, at the runner/tool layer, and is per-profile.
   It becomes **blocking** at the first of:
   - automatic multi-tick execution (`foreman run`) landing, or
   - any run where a human does not read the complete diff before every
     transition, or
   - any write-capable runner not assumed cooperative.

   "First unattended loop" was the originally proposed trigger and is **wrong**
   — both reviewers rejected it. A single manual tick already routes and
   dispatches without mandatory full-diff review
   (`workflow_interpreter/foreman/tick.py:240-296`).

   **DECIDED 2026-09-04.** The first two triggers fired with the phase-5 foreman
   landing (`foreman/__main__.py:132,463`). `docs/plans/allowed-paths-enforcement.md`
   recommended option C phased B→A, and the owner ruled on its five open
   questions. Recorded verbatim:

   - **O1 — unsupported host.** bubblewrap (`bwrap`) is the bound. When it is
     absent or the self-test fails, the wrapper REFUSES to dispatch (every node,
     writing or not). No fallback mode.
   - **O2 — `.git`.** Least destructive to the existing protocol: the RUNNER
     keeps committing its artifact (`RUNNER_PROTOCOL_WRITE_STEP` stays), so the
     git directory stays writable, EXCEPT the parts that make git execute
     programs — `config`, `hooks/`, `info/attributes` are read-only binds
     (`.gitattributes` handling is already covered by the wrapper's own filter
     overrides). For a worktree checkout the gitdir is
     `<main>/.git/worktrees/<name>` plus `<main>/.git/objects`, `refs`,
     `packed-refs`; for in-repo mode it is `<checkout>/.git`.

     *Implementation note (phase-1 plan, 2026-09-05):* the read-only pins must be
     emitted LAST — after every read-write bind — because bind order is mount
     order and a pin placed before a later read-write bind of its parent is
     re-opened (probed). `<main>/.git/logs` joins the writable set (a commit
     cannot append its reflog without it), and `<main>/.git/refs/wf` joins the
     pins so a runner cannot forge the wrapper's own evidence refs as loose
     refs. The `info` pin is the whole directory (not `info/attributes` alone),
     and a worktree checkout also pins `<gitdir>/config.worktree`, in-repo mode
     `modules/*/config`. **Residual, accepted:** `refs/` and `packed-refs` stay
     writable, so `packed-refs` rewriting and moving the instance branch remain
     possible; hardening that is a separate bead.
   - **O3 — glob expressiveness.** Refuse inexpressible globs at instantiation.
     The only accepted `allowed_paths` shape is a directory-prefix glob
     `<relative dir>/**` (no `..`, no leading `/`, no wildcard segments, no
     file-level pattern), enforced as a JSON-Schema `pattern` on the items
     (precedent: cr-0jd did this for `node.runner`), and no segment may begin
     with `.` — so a hidden directory such as `.claude/**` can never be a grant
     and can never re-open a read-only pin. A refusing constraint does not
     change content hashes. A grant directory that does not exist in the
     checkout is created (empty) before the bind.
   - **O4 — network.** No `--unshare-net`. Codex keeps its
     `network_access=false`.
   - **O5 — rollout.** Both shipped graphs; enforcement is on by default for
     every node (a `writes = false` node gets the checkout read-only with only
     `channels/` writable). One `SupervisorConfig` key `sandbox` (enum: `bwrap`
     default | `off`); `off` is a deliberate unsafe switch, logged at every
     dispatch and recorded on the activation so a run without the bound is
     visible in bd.

   Phase 2 (profile-native expression) is `cr-n2z.3`; phase 3 (the §13 drill and
   the never-expected-flag invariant) is `cr-n2z.4`.

4. **Record today's safety envelope explicitly.** The system is currently safe
   because (a) runners are assumed cooperative, and (b) every writing artifact
   reaches a human gate that shows the cumulative diff. Both are assumptions,
   not mechanisms. The ADR states them so their loss is visible.

## Consequences

- Nothing bounds what any node writes today. That is now written down rather
  than implied otherwise. **Amended 2026-09-04:** true until point 3 ships; under
  `sandbox = bwrap` `allowed_paths` becomes the node's writable mount set as well
  as its reporting exemption, for every profile and through any interpreter.
- Reviewer nodes (`writes = false`) are told nothing about the reviewed
  writer's declared bound; build-loop has two writers before `slice_gate` with
  only non-writing reviewers between them.
- A residual gap survives even under prevention: verifier provenance pins only
  the executable (`supervisor/channels.py:286-289`), and checks run in a
  detached checkout of the artifact commit (`exit.py:548-554`), so a writing
  runner can edit what the examiner depends on. **Amended 2026-09-04:** the mount
  bound closes the *examiner-editing* half for everything outside the node's own
  grant — `scripts/**` is in no node's `allowed_paths` in either shipped graph, so
  no writer can reach its own examiner. Two parts stay open: inside the grant
  (`implement` writing `tests/**` still shapes what its own test check
  measures — and since cr-o85.34.21 widened that grant from `tests/unit/**`,
  `tests/acceptance/**` is inside it, so the acceptance tests are policed by
  the pinned `tests-untouched.sh` verifier rather than by the mount bound),
  and ref integrity (see the O2 residual — `packed-refs` and the
  instance branch remain writable).
- `AuditFlag.EFFECT_OUTSIDE_ALLOWED_PATHS` (point 2, `exit.py:657`) becomes a
  should-never-fire invariant once the bound is on: an observed write outside the
  grant means the sandbox did not hold. Asserting that is `cr-n2z.4`.

## Open

- `no_diff` must be defined as either "no committed artifact" (today) or "no
  observed change" (stricter, needs another invariant). Not decided here.
- Isolation-specific manifest semantics need a single stated rule covering both
  `in-repo` and worktree modes.

## Rejected

- **Hard-fail on undeclared paths at grading time.** Stops legitimate work
  (formatters, lockfiles, cache directories) without preventing anything — the
  edit already landed on disk by the time it is caught. Worst of both.
