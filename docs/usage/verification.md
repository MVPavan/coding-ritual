# Verification inside a workflow task

The node verdict is a claim. Before returning it, complete the assigned source
or review work and run available supported local checks. The engine runs the
full declared HOST verification after return; it remains mandatory and gates
advancement. A local pass or reviewer `accept` cannot waive it. Host failure can
override an optimistic claim through the existing outcome/routing rules.

## Local evidence

Inspect the actual environment and task contract before choosing commands.
For each check, record the exact command, exit status/result, or a not-run reason
in an evidence file under `$WF_ARTIFACT_DIR`. Distinguish an assertion or source
failure from a command that could not execute. Preserve relevant error output;
when the cause is uncertain, say so rather than assuming an environment problem.

Run focused tests, lint, formatting, and strict types where supported. Respect
the task's local test scope. For interpreter tasks excluding live vendors, Beads,
and nested sandbox probes, use `-m "not live and not bd and not nested_sandbox"`
with the named focused tests. Do not run host-only nested sandbox checks from
inside a model sandbox. Do not retry dependency installation when sandbox DNS,
network, or tooling prevents it; record the limitation for host verification.
An unavailable check alone is not evidence of a source defect and must not alone
produce `fail_code` or reviewer `reject`. Real code/test failures must be reported
and never relabeled as environment limitations.

Writers report completion only when the assigned work is complete, committed,
and supported local checks pass, with unavailable checks explicitly recorded.
Reviewers decide against source/spec requirements and record concrete findings.
Neither role reports that the unrun host gate passed.

## Build-loop red evidence

`write_tests` must observe tests fail because the feature is absent and record
the command, result, and semantic reason. Import errors, unavailable dependencies,
or a test command not run do not prove a correct red. When required semantic
evidence cannot be obtained, use the existing `fail_plan` → `triage_tests` path.
The host parse check is mandatory but does not establish semantic red evidence.
Test review remains before implementation; implementers must not edit, weaken,
skip, or delete acceptance tests to make verification pass.

## Scratch and output channels

Consult the provided paths before using them. The runtime supplies
`$WF_SCRATCH_DIR` and sets the child's `$TMPDIR` to it. Temporary repositories,
work directories, and caches belong there. `$WF_ARTIFACT_DIR` holds deliverable
findings and evidence only: its contents are collected as outputs. Do not use
it as temporary storage. If a provided path is unavailable, record that limitation
rather than inventing a machine-specific path or changing sandbox permissions.
