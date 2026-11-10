---
name: why
description: "Use to answer why something in this project is the way it is (code, a document, a decision, config, a tracker record): what was decided about it, what motivated it, or which change brought a regression and for what reason, from the project's own record, cited at the strength the evidence has. How it works now is how; evidence from outside the project is research; a failure whose cause is unknown is systematic-debugging. At top level, a question that should end in that answer is the investigation playbook."
---

# Why

The deliverable is one cited answer about why something in this project has its
shape: its code, documents, decisions, configuration or tracker records. A question
about what was decided, when the outcome itself is wanted, is answered the same way.
Code and files show what the project does; the reason lives in what people wrote about it,
and that record is partial. Report it at the strength it has.

Change nothing: no edit, no commit, not even a temporary print or probe. A delegate
you use works under the same limit. If a change is wanted, name it as the next
request and do not start it.

If a target is ambiguous but each reading would give much the same answer, state
the reading you took and carry on.

This skill reads the project's own record. Evidence from outside the project
(vendor documentation, papers, other codebases) is `research`'s. Past agent
sessions are `recall`'s, once that skill exists; until then, a past decision is
answered from the project's own record here, and sessions are listed in the
sources line as not searched.

## Gather

Collect everything below before you settle on an answer: form no conclusion and
pick no side while gathering.

1. **Anchor.** Before any search, fix the target's files, lines, symbols and last
   commits with `git blame -L` and a rename-following `git log --follow`.
2. **Records named there.** Fetch what those commits name (a bead, an ADR), with
   its comments, before you search by keyword.
3. **Search terms.** Build them from the target's feature or business term, its
   symbols, its author, its error strings and its path. Try several wordings.
4. **Sources.** Search for motivation in commit messages (always), Beads, decision
   records, docs, inline markers, changelogs, tests and co-changed files. Add another
   source only if it is available. When a commit you trace links a pull request,
   read `references/pull-requests.md` and follow it.
5. **Strings in history.** Find commits whose diffs add, remove or match a string or
   pattern with `git log -S` and `git log -G`.
6. **Whole records.** Before relying on an anchor or an excerpt, read the complete
   commit message and diff, and the decision or bead discussion behind it.
7. **Lineage.** From a record, follow its parent and duplicate links to the item
   that carries the motive.
8. **Past the latest commit.** The newest commit is not authoritative. Trace back to
   the earlier decisions that produced the current shape.

If a guess sits inside the question ("I assume it's for speed"), it is one candidate.
Test it independently, then confirm or refute it with citations.

## Judge

Put each claim in one tier, by its evidence:

| Tier | Evidence | Phrasing |
|---|---|---|
| Direct | An author's written words state the reason | Confident, cited |
| Supported | Several indirect items converge | Confident, citing each item |
| Inferred | A reasonable reading with no explicit support | Hedged, with the chain of reasoning shown |
| Speculative | Other explanations fit equally well | Stated as a guess |

Words that assert cause, intent, achieved effect or a group decision ("because",
"was designed to", "fixes", "the team decided") go only on Direct or Supported
claims, with a specific citation right beside them.

Four readings do not count as evidence:

- Code or a diff, as proof of what its author intended. Never cite it for that.
- A tidy justification laid over messy history, or an assumption that the author
  chose correctly followed by reasoning backward. Do neither.
- A repeated pattern, as a deliberate choice. It may be copying.
- A lack of mention, as proof that something was no concern.

## Answer

- **Conflict:** show the conflicting sources side by side with citations, and leave
  the call to the user.
- **Several stories:** when the record fits more than one, give each its evidence for
  and against, and force no winner.
- **Unknown:** report it with exactly what was searched, where and with which terms.
- **Out of reach:** data you could not get, through a missing tool, denied access,
  retention or deletion, is a coverage gap. Report it as that, never as a null result.
- **Sources line:** list each source searched, empty or skipped, with the reason.
- **Change to follow:** if one does, turn the findings into four lists: preserve,
  change, avoid and risk.
