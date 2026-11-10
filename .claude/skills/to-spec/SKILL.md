---
name: to-spec
description: Use when decisions already settled should be written up as a durable spec for planning or another session. Skip choices still open or being compared, which are brainstorming.
---

# To spec

Write decisions already reached into a durable spec that a later reader can act on.

## Gather

Take the decisions from the conversation, the documents it names or the tracker
record, and write them down without reopening them. A material choice that is
still open goes back to `brainstorming`; do not settle it inside the spec.
Read only the code, docs and constraints the spec has to describe.

## Write

Use `references/spec-template.md`; the default path is
`docs/specs/YYYY-MM-DD-<topic>.md`. Record the sources, assumptions and excluded
alternatives the next reader needs.

## Approve

A new spec is `Status: draft`. Set `Status: approved` only when actual
authorization covers its direction and scope, and record that evidence. Approval
names the chosen direction; re-ask vague assent as a choice between two concrete
options. Resolve each blocking question, or move it explicitly to Out of Scope,
before approval. Check consistency, scope and verifiability; a spec with material
risk gets a critic review (review skill) before approval. Report a direction still
unresolved as a blocker to whoever asked for the spec.

## Hand off

This skill's output is a spec. Continue into `planning` or `implement` when
already authorized; a request for a spec alone does not authorize code changes.
