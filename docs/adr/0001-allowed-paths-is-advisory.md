# ADR 0001 — `allowed_paths` is a disclosure exemption, not a containment bound

- **Status:** Accepted; points 1, 2 and 4 implemented 2026-09-03, point 3 open
- **Date:** 2026-09-03
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

4. **Record today's safety envelope explicitly.** The system is currently safe
   because (a) runners are assumed cooperative, and (b) every writing artifact
   reaches a human gate that shows the cumulative diff. Both are assumptions,
   not mechanisms. The ADR states them so their loss is visible.

## Consequences

- Nothing bounds what any node writes today. That is now written down rather
  than implied otherwise.
- Reviewer nodes (`writes = false`) are told nothing about the reviewed
  writer's declared bound; build-loop has two writers before `slice_gate` with
  only non-writing reviewers between them.
- A residual gap survives even under prevention: verifier provenance pins only
  the executable (`supervisor/channels.py:286-289`), and checks run in a
  detached checkout of the artifact commit (`exit.py:548-554`), so a writing
  runner can edit what the examiner depends on.

## Open

- `no_diff` must be defined as either "no committed artifact" (today) or "no
  observed change" (stricter, needs another invariant). Not decided here.
- Isolation-specific manifest semantics need a single stated rule covering both
  `in-repo` and worktree modes.

## Rejected

- **Hard-fail on undeclared paths at grading time.** Stops legitimate work
  (formatters, lockfiles, cache directories) without preventing anything — the
  edit already landed on disk by the time it is caught. Worst of both.
