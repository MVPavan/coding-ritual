---
name: model-council
description: Use only on an explicit request for a council of named models or agents with a judge, never by itself; a yes in words to one counts. It can also turn candidates into one artifact, picked and grafted. Usually one critic review is enough, and ordinary brainstorming needs no council; two options to weigh is `codebase-design`, and two to try is `prototype`.
---

# Model Council

Run the same task through user-selected independent members, then a selected
judge. Preserve every member's full report and the judge's consolidation.

Resolve members and judge from this request or its existing explicit selections;
ask only for missing choices or unreachable members. Inspect current runtime
configuration and the available permitted dispatch interfaces. Do not infer
cross-provider access from a model name, put effort only in prose when a runtime
control exists, or silently substitute a member. Dispatch members and the judge
through the `delegation` skill.

1. Write one common brief: question, relevant source pointers, constraints,
   acceptance and report format. Use a neutral brief without preferred conclusions.
2. Give each member that brief independently. Parallelism is useful but optional;
   isolation means members do not see one another's answers. Save full attributed
   reports under the supplied run directory or `scratchpad/council/<topic>/`.
3. Give a fresh judge the brief and all attributed reports. Request a synthesis
   of agreement, disputes, evidence, best-supported conclusion and uncovered gaps.
   Majority agreement is not proof; the judge may favor a supported minority view.
4. Deliver a concise consolidation, member-position summaries and paths to every
   full report. Include full text inline when requested, rather than discarding it.

**One artifact.** When the requester wants one built artifact from the members, not an
answer, follow `references/pick-and-graft.md` as well.

Record actual model identities where the runtime provides evidence. A failed
member gets bounded safe recovery; report any missing member and whether the
judge saw an incomplete council. Never backfill a member with your own answer.
A council-only request does not authorize implementing its recommendations.
