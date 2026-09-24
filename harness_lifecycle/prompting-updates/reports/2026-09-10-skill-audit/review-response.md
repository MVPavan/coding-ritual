# Skill audit review response

Date: 2026-09-10. Beads: `cr-2iq`. Review: [review.md](review.md).
Revised analysis: [README.md](README.md). No repository skills were changed.

The review supports the main recommendations: remove compulsory workflow
overhead, narrow automatic triggers, and retain specialized capabilities with
clear boundaries. Its corrections improve the evidence and migration detail;
they do not justify retiring skills merely because a usage counter is absent.

| Review finding | Disposition |
|---|---|
| Major 1: analysis scope | Removed account-installed plugin comparisons entirely, as requested by the user. |
| Major 2: missing usage evidence | Read Claude Code's current local aggregate counters and added the 17 matching entries, with a minimal [snapshot](claude-usage-snapshot.json). The other 28 names have no entry; this does not prove no use. |
| Minor 1: line citations | Corrected the receiving-review citation to line 16 and the research source-count citation to line 48. |
| Minor 2: verification-skill callers | Enumerated the five caller files, including the reference document, that require migration before removal. |
| Minor 3: Beads memory policy | Reframed the conflict as a deliberate repository override. Preserve that decision unless explicitly changed; automatic memory writes remain unauthorized. Higher-priority runtime instructions still govern destination. |
| Minor 4: external documentation | Reopened official documentation. OpenAI's developer skill URL redirects to its learn.chatgpt.com documentation. Claude's skill-content lifecycle section explicitly documents persistence across turns and compaction limits. |
| Minor 5: description size | Kept the reproducible parsed value: 992 Unicode characters, 994 UTF-8 bytes. The review's 995-character measurement was not reproduced. |

The aggregate counters are machine-local and span projects; direct file reads
and Codex use are outside their coverage. The review's recent-session sample
was not independently recomputed. Its five recent `model-council` dispatches
versus four in the aggregate are a reason to avoid describing the aggregate as
a complete lifetime record. Low observed use supports prioritizing evaluation,
not deleting a skill without examining its purpose and callers.

The review also strengthens the proposed brainstorming fix: move the small,
explicit-task exit before compulsory grounding reads. The recommendations to
remove completion-verification as a separate workflow and replace unsupported
cost-estimation heuristics still stand. Neither has been implemented here.

Documentation rechecked on 2026-09-10:

- [OpenAI skills](https://learn.chatgpt.com/docs/build-skills): discovery and progressive loading.
- [Claude invocation control](https://code.claude.com/docs/en/skills#control-who-invokes-a-skill): manual versus automatic invocation.
- [Claude skill-content lifecycle](https://code.claude.com/docs/en/skills#skill-content-lifecycle): loaded instructions remain in conversation context, subject to compaction.

Validation covered report links, inventory hashes, description measurement,
the repository skill catalog, and whitespace checks. This is a source review,
not a measured comparison of model quality, latency, or invocation behavior.
