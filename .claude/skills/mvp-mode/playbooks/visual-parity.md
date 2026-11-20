---
trigger: A user-interface migration whose components must look the same afterwards, proven by image diff against a baseline.
traits: [frozen-baseline-no-shortcuts, visual-pass-predicate]
steps:
  - id: visual-parity#1
    when: always, before any component changes
    actions: [{trait: harness-with-pre-change-baseline}]
    calls: [{to: "skill:build-a-lever", when: the project has no harness that captures each component's states on one surface}]
  - id: visual-parity#2
    when: visual-parity#1 holds a baseline for every component in scope, and the migration changes shared primitives
    actions: [{trait: shared-primitives-first}]
  - id: visual-parity#3
    when: once per component, after visual-parity#2 or once the baseline holds when no shared primitive changes
    actions: [{trait: one-component-at-a-time}, {trait: baseline-surface-image-diff}, {trait: parallel-components-on-request}]   # the third only when the owner asks for parallel work
    calls: [{to: "skill:systematic-debugging", when: a failing diff's cause is not clear from the delta}, {to: "skill:delegation", when: the owner asked for components to run in parallel}]
  - id: visual-parity#4
    when: a component or a batch of them passed visual-parity#3
    actions: [{trait: integrated-tree-rediff}, {trait: publish-requested-pr}]   # the second only when the request authorizes a pull request
    calls: [{to: "skill:land"}, {to: "skill:pr", when: the request asks for a pull request}]
  - id: visual-parity#5
    when: every exit
    actions: [{trait: visual-migration-closeout}]
---

# Visual parity

For moving user-interface components to a new implementation (a framework,
a styling system, a component library) when they must look exactly as they
did, proven by image diff. A UI idea to try out is `prototype`; a structure
change with nothing visible at stake is the refactoring playbook. A project
with no user interface has no use for this playbook.

**The gates:**

- **The baseline is the specification.** Once captured, the harness and the
  baseline images are frozen. Never edit them, or restructure a component, to
  make a diff pass. A baseline that looks wrong is a stop: show it to the
  owner, ask, and leave it as it is.
- **One pass predicate.** By default a diff passes only on exact equality. When
  the request gives a metric and a limit (pixels, a percentage, a region), that
  is the predicate instead. Steps 2, 3 and 4 all judge by it, and every result
  reports the measured delta beside the limit. Judging by eye proves nothing.

1. **Baseline.** Before any migration, capture every component in scope across
   its states (and the target implementation when two are being matched) with
   a harness that screenshots them on one surface: a browser, a device, a
   viewport. Use the project's own visual harness or verify skill when it has
   one. With none, invoke `build-a-lever` to build the harness first; that is
   the first deliverable, not a follow-up. No baseline, no parity claim.
2. **Shared primitives first.** When the migration changes primitives other
   components use (tokens, typography, layout or base controls), migrate those
   and show every dependent component passing before any other component
   moves. This step blocks the rest.
3. **One component at a time.** Migrate one component, then diff its images
   against its baseline on the surface the baseline was taken on. On a failing
   diff, find what the changed pixels come from, invoking
   `systematic-debugging` when the delta does not show it, fix the migration
   and diff again until it passes.
   Parallel work, one owner per component in its own worktree, runs only when
   the owner asks for it: hand it out through `delegation`, and apply
   `principle-separate-before-serializing-shared-state` so no two owners write
   the same file or baseline.
4. **Integrate and land.** Components pass one at a time, but a later one can
   still change an earlier one (a global style, a shared selector). On the
   exact tree to be committed, rerun every state the batch could affect, or
   every in-scope state when that set is unclear, and judge it by the pass
   predicate. Only then invoke `land`. When the request asks for a pull
   request, invoke `pr` for its body; when the request also authorizes
   publishing, push the branch and open the pull request (`gh pr create
   --body-file <file>`) after the commits.
5. **Close out**, on every exit. Keep the harness, the baseline images, and
   each failing diff's images or the exact command that reproduces them.
   Remove the run's other scratch captures. Record each component's measured
   delta and limit, and which components are left.

## Reply

- **Migrated:** each component with its measured delta and the limit, the
  integrated rerun's result, where the harness and baseline live and how to
  rerun them, `land`'s commits or plan, the pull request's URL or the exact
  reason it was not published, and what is left.
- **Stopped, partial proof:** the components that passed, with their deltas;
  the one that did not, with its delta, the kept images or command, and what
  was found about its cause; and whether anything landed.
- **Stopped, baseline:** the baseline that looks wrong, what looks wrong about
  it, and the owner's decision needed; nothing migrated past it.
- **Stopped, no harness:** why a harness could not be built, and that no parity
  is claimed.
