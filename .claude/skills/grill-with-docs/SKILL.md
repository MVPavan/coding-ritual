---
name: grill-with-docs
description: A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go.
disable-model-invocation: true
---

Run a `/grilling` session, using the `/domain-modeling` skill.

Prefer this over `/grill-me` whenever a working directory exists: both run the
same interview, but this one leaves a paper trail (docs, ADRs, glossary) in the
repo — which makes it strictly the better of the two when there is a repo to
leave it in. No working directory → `/grill-me`.
