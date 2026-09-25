# Dispatched review contract

## Critic review

A critic is an independent reviewer, never the author; the user chooses its model.
Give a thorough opinion, then every finding with its severity and supporting
evidence; for code, cite `file:line`. The coordinator filters by severity afterward.
`APPROVE` means no open BLOCKER or MAJOR; otherwise `REVISE`.

## Inputs

Inputs: mode, brief/requirements path, implementation report, scoped diff package,
binding constraints, output path. For re-review also include the finding list and
fix-delta package. Follow the code-review entrypoint's evidence and scope rules.

Initial spec and quality verdicts remain distinct when those roles are dispatched
separately. A combined reviewer covers both explicitly. Re-review covers every
listed finding regardless of its original role.

## Spec output

```text
Verdict: APPROVE | REVISE
Unverified requirements: <items and needed evidence, or none>
Issues: <severity, file:line, missing/extra/misunderstood requirement and impact>
Checks and limitations: <actual evidence>
```

A missing brief limits compliance claims; an unrelated failed check is not an
automatic BLOCKER. Report each limitation at its actual consequence.

## Quality output

```text
Verdict: APPROVE | REVISE — <reason>
Issues: <BLOCKER / MAJOR / MINOR; file:line, trigger and impact>
Checks and limitations: <actual evidence>
```

## Re-review output

```text
Finding verdicts: <ID — ADDRESSED | NOT ADDRESSED; file:line evidence>
New breakage in fix diff: <severity and evidence, or none>
Out-of-scope observations: <nonblocking follow-ups, or none>
Verdict: APPROVE | REVISE
Checks and limitations: <actual evidence>
```

A reviewer may report that a finding was incorrect; the coordinator records that
ruling and its evidence separately from an implemented fix. Uncertain findings
remain explicitly unresolved. Do not demand edits solely to make a verdict green.
