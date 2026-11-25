---
name: grilling
description: Use when the user explicitly requests a grilling interview to resolve or challenge material decisions. For a written critique, review the artifact directly.
---

# Grilling

Interview the user about a plan, decision or idea when they explicitly request
that interaction. A request for written critique does not itself request an interview.

Map material decisions and their prerequisites. Ask a manageable batch of
independent questions whose prerequisites are settled; defer dependent questions
until their answers can use the earlier decisions. Wait for the answers to the
current round before asking the next round. Include a recommendation and its
assumptions where useful, allowing the user to disagree. Word each question so a
plain yes accepts the recommendation. A question after a fact, with no
recommendation to offer, stays an ordinary question.

Look up available facts yourself. Ordinary local or documentation lookups stay
inline; delegate only bounded work that benefits from it. Decisions requiring a
live participant remain pending; do not answer on that participant's behalf.

Recompute the unresolved choices after each answer. Stop when the decisions
needed for the requested outcome are settled, explicitly deferred or identified
as blocked; by default do not exhaust every branch. Then offer to continue
through every remaining branch until none is left and nothing is silently
assumed, and do so only if the user says yes. Summarize material agreements,
remaining uncertainty, and deferred and blocked decisions; carry authorization
forward for any next step already requested, without treating the interview
itself as implementation authority.

If the necessary respondent is absent, prepare a questionnaire for their role and
knowledge gap: cover every needed decision or fact with at least one single-idea
question, most important first, laid out as `references/questionnaire.md`
describes. Ask the present user only for missing recipient context and desired
outcome; do not force two exchanges when these were supplied. Drafting a
questionnaire does not authorize sending it.

Save the closing summary and any drafted questionnaire to files unless the user
asks not to: a saved file survives a lost context. Use `docs/interviews/`, or the
folder the project's `.repo-context/` names for interview outputs, with the name
`YYYY-MM-DD-HHMM-<slug>-<kind>.md`, where kind is `grilling` or `questionnaire`,
and report each path. Saving is not sending.

Glossary and ADR documentation is optional and separate from those files. When
requested, use domain-modeling for settled terms and qualifying ADRs; a
repository's existence alone does not authorize these writes.
