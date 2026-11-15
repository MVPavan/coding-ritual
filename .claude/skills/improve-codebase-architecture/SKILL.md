---
name: improve-codebase-architecture
description: Find evidence-backed architecture improvements within a named area or requested codebase survey.
disable-model-invocation: true
---

# Improve Codebase Architecture

Find architectural friction supported by current code, then recommend bounded
improvements. A review authorizes inspection and reporting, not refactoring or
glossary changes.

Read relevant domain terms and ADRs before exploring the code. Use the named module
or pain point. For a broad survey, use recent change history and actual
maintenance/test friction to choose areas; expand when evidence warrants. Evaluate
interfaces with the codebase-design vocabulary.

For each worthwhile candidate, identify affected files, the concrete friction,
a proposed direction, expected benefit, compatibility/migration cost and evidence.
Name each candidate and its friction in the project's domain terms. State each
benefit in codebase-design terms (depth, locality, seams), not generic claims such
as easier to maintain. Apply codebase-design's deletion test to each candidate. Distinguish a supported
recommendation from an untested hypothesis.

Present a concise comparison and strongest recommendation. Use an inline visual
when it clarifies structure. HTML is optional; `HTML-REPORT.md` points to the shared
artifact guidance. Do not create a report format merely to fill its components.

When an ADR conflicts, explain the new evidence that might justify revisiting it.
When the user rejects a candidate for a durable reason, offer an ADR through
domain-modeling so later reviews do not suggest it again; skip ephemeral or
self-evident reasons.
An interview, alternative-interface exercise or domain-document update happens
only when requested or already authorized, using the corresponding shared skill.
Do not automatically enter a grilling loop after delivering the review.
