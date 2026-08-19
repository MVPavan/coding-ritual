---
name: code-review
description: Use when reviewing implemented changes — as a dispatched spec-compliance or code-quality reviewer, when re-reviewing a fix round, or when reviewing a diff inline before claiming completion. Trigger on review-the-code/review-the-diff phrases.
---

# Code Review

The review protocol for this repository. The spec-reviewer and code-reviewer
agents follow it when dispatched; a coordinator reviewing inline follows the
same sections. Spec compliance is judged before code quality, and the two
verdicts never blend in an initial review.

## Modes and inputs

Every dispatch states a **mode** and supplies its inputs:

| Mode | Who | Sections that bind | Inputs |
| --- | --- | --- | --- |
| `spec` | spec-reviewer | Evidence discipline, Do not trust the report, Spec compliance, Severity | brief path, report path, diff package path, global constraints |
| `quality` | code-reviewer | Evidence discipline, Do not trust the report, Code quality, Severity | same |
| `re-review` | code-reviewer | Re-review (role boundaries lift: verdict **every** finding, spec and quality alike) | findings list, brief path, report path, fix package path |
| `inline` | the coordinator itself | all sections, abbreviated to the changed surface | the diff package; BASE = the SCOPE_BASE recorded in the workspace ledger |

## Preflight — mechanical gates first

Initiators — the coordinator before dispatching, the inline reviewer before
reading the diff — check two facts before spending judgment effort: the base
resolves with a non-empty diff or package (ad-hoc, the base is the fixed
point the user named — ask if unspecified), and the mechanical gate
`.claude/project/verification.md` defines for the changed file types is
green in the implementer's report (or your own fresh run, inline). A red
gate bounces the work back as failed verification, not into a review round.

## Evidence discipline

- Work that reaches you failing preflight — an empty package, a base that
  does not resolve, a red mechanical gate in the reported output — returns
  `ISSUES_FOUND` (spec) or `BLOCK` (quality) with the preflight fact as the
  sole Critical finding: no judgment findings on top of a broken foundation.
- When the dispatch names a **diff package** (commit list + stat + `-U10`
  diff), read it once — its context lines ARE the changed files. Do not Read
  a changed file separately unless a hunk you must judge is cut off
  mid-function, and say so in your report. Do not re-run git commands. If no
  package was provided, fetch the diff yourself:
  `git diff --stat BASE..HEAD` and `git diff BASE..HEAD`.
- Do not crawl the broader codebase. Inspect code outside the diff only to
  evaluate a concrete risk you can name — one focused check per named risk,
  and name both the risk and what you checked. Cross-cutting changes are
  legitimate named risks: changed lock ordering, a changed function or API
  contract, shared mutable state — checking the call sites is the right method.
- The review is **read-only** on this checkout: never mutate the working
  tree, index, HEAD, or branch state. Need a working copy of another
  revision? Use the harness's isolated-worktree facility (Claude Code: the
  Agent tool's `isolation: worktree`, or `EnterWorktree`; Codex: a subagent
  in its own worktree), never raw `git worktree add`, which leaves worktree state the harness cannot see or
  clean up; either way, never move HEAD here. Before treating a checkout as
  already isolated, verify true isolation: a bare `GIT_DIR != GIT_COMMON`
  test also fires inside submodules (any vendored submodule directory) —
  confirm
  `git rev-parse --show-superproject-working-tree` returns nothing first.
- The implementer already ran the tests and reported the output. Do not
  re-run the suite to confirm their report. Run a test only when reading the
  code raises a specific doubt no existing run answers — then a focused
  test, never a package-wide suite, race detector, or repeated/high-count
  loop; if heavy validation seems warranted, recommend it in the report
  instead of running it. If you cannot run commands in this environment,
  name the test you would run. Warnings or noise in the reported test output
  are findings — output should be pristine.
- Every finding and every check you would otherwise answer with a bare "yes"
  carries a `file:line` reference.

## Do not trust the report

The implementer's report is unverified claims about the code — possibly
incomplete, inaccurate, or optimistic. Verify the claims against the diff.
Design rationales are claims too: "kept it simple per YAGNI" is the
implementer grading their own work. A stated rationale never downgrades a
finding's severity.

## Spec compliance review

Compare the diff against the brief/plan/requirements on three axes:

- **Missing** — requirements skipped, missed, or claimed without implementing.
- **Extra** — unrequested features, over-engineering, unneeded "nice to haves".
- **Misunderstood** — right feature built the wrong way, wrong problem solved.

Also check: file-scope compliance (owned files only), the relevant invariants
from `.claude/project/invariants.md` (run the concrete command when an
invariant has one), and required tests / verification evidence when the task
asked for them. Be strict about missing work and unrequested extras.

A requirement that cannot be verified from this diff alone (it lives in
unchanged code or spans tasks) is a **⚠️ Cannot verify from diff** item —
report it alongside the verdict with what the coordinator should check;
never broaden your own search instead.

**No brief supplied** (ad-hoc use): locate what "correct" means before
judging, in this order — the workspace brief under
`scratchpad/execution/<slug>/`, the bead tracking the work (`bd show`), the
plan under `docs/workstreams/`, a doc named in the range's commit messages,
then ask the user. None found → report `Verdict: ISSUES_FOUND` with the
single item "no spec available"; inline, continue with quality review only.
Never reconstruct the requirements from the diff itself.

## Code quality review

- **Correctness & design**: clean separation of concerns; proper error
  handling; DRY without premature abstraction; edge cases handled; hidden
  mutation or confusing state flow.
- **Tests**: judge the diff's tests before its implementation — they state
  the intent the code is measured against. New/changed tests verify real
  behaviour, not mocks; the task's edge cases are covered; no test asserts
  nothing. **A change that required editing existing tests to keep them
  passing changed behaviour** — flag it unless the task explicitly changed
  that behaviour.
- **Structure**: one clear responsibility per file with a defined interface;
  units understandable and testable independently; file structure follows
  the plan; flag files this change created large or grew significantly
  (ignore pre-existing size).
- **Dead code**: code this change orphaned — made unreachable but left in
  place — is a finding that names exactly what to delete; pre-existing dead
  code is at most a Minor note.
- **Dependencies** (diff touches `pyproject.toml`/`uv.lock`): a new
  dependency needs its gap named — what the existing stack cannot do; an
  upgrade is judged by its changelog, not its version delta; unrelated
  dependency changes bundled into one diff are a finding. Supply-chain
  doubts route to the security-skill lens below.
- **Production readiness**: a schema or persisted-data change names its
  migration strategy; a changed public interface stays backward compatible
  or the break is an explicit finding; docs and comments the change made
  stale are updated in the same diff.
- **Project risks**: apply `.claude/project/brief.md` and
  `.claude/project/invariants.md`.
- **Trust boundaries**: when the diff touches untrusted input, authn/authz,
  secrets, uploads/webhooks, external integrations, or LLM/agent features,
  run the **security skill's** review checklist as an additional lens —
  findings report under this skill's severity and output contract.
- **Python-first checks** when relevant: missing/weak tests for risky
  behaviour changes; missing type hints at important boundaries; mutable
  default arguments; bare `except`; swallowed exceptions or missing context
  managers; unsafe config or secret handling; blocking I/O in async code;
  unbounded retries or missing timeouts on external calls; path, shell, or
  deserialization hazards on untrusted input.

Report issues that could cause incorrect behaviour, safety or data-integrity
problems, missing verification, or brittle code at the changed boundary.
Findings are judgment content tooling cannot catch: skip stylistic noise
that affects neither correctness nor maintainability, and report nothing
this repo's configured formatter, linter, or type checker already enforces —
a tool's failure is a preflight fact, not a finding.

## Severity calibration

The bar is improvement, not perfection: a change that definitely improves
code health is approvable even when imperfect — "not how I would build it"
is not a finding.

Not everything is Critical. **Important** = the change cannot be trusted
until fixed: incorrect or fragile behaviour, a missed requirement, or
maintainability damage you would block a merge over (verbatim duplication of
a logic block, swallowed errors, tests that assert nothing). "Coverage could
be broader" and polish are **Minor**.

If the plan or brief explicitly mandates something this rubric calls a
defect, that IS a finding — report it as Important, labelled
**plan-mandated**. The plan's authorship does not grade its own work; the
human decides.

Within a severity bucket, lead with the structural finding.

Acknowledge what was done well before listing issues — accurate praise makes
the rest of the feedback trusted.

## Re-review (after a fix round)

Scope = the findings list + the fix diff, nothing else. Role boundaries do
not apply here: verdict every finding in the list, spec and quality alike,
**ADDRESSED** or **NOT ADDRESSED** with `file:line` evidence —
"attempted" is not addressed; the specific defect must no longer exist.
Confirm the fix report names the covering tests and shows their output.
Inspect the fix diff for new breakage (with severity). Issues entirely
outside the fix diff go under **Out-of-Scope Observations** — non-blocking,
they do not extend the loop.

## Output formats

The final message is the report itself: begin directly with the verdict.
Every line is a verdict, a finding with `file:line`, or a check you ran —
no preamble, no process narration.

**Spec review:**

```text
Verdict: COMPLIANT | ISSUES_FOUND
⚠️ Cannot verify from diff: <items + what the coordinator should check, or "none">
Requirements: / Scope: / Invariants: / Unexpected extras:
Issues:
1. [severity] file:line — what's wrong, why it matters
```

**Quality review:**

```text
Strengths: <specific>
Issues — Critical (must fix): / Important (should fix): / Minor (nice to have):
  each: file:line, what's wrong, why it matters, fix if not obvious
Verdict: APPROVE | WARNING | BLOCK — 1-2 sentence reasoning
```

**Re-review:**

```text
Finding verdicts: <each — ADDRESSED | NOT ADDRESSED, file:line evidence>
New breakage in fix diff: <severity + file:line, or "none">
Out-of-scope observations: <or "none">
Verdict: all addressed, no new Critical/Important | findings remain open — <list>
```
