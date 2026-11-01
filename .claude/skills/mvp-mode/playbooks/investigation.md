---
trigger: A question about how this repository's code works, why it has its shape, or which design to pick.
traits: [read-only-answer-gate]   # new; variant of no-fix-handback, for a question about code
steps:
  - id: investigation#1
    when: always
    calls: [{to: "skill:explain-code"}]
  - id: investigation#2
    when: an answer was drafted
    calls: [{to: "skill:prose-pass"}]
  - id: investigation#3
    when: every exit
    actions: [{trait: read-only-closeout}]   # new
---

# Investigation

For a question about how this repository's code works, why it has its shape or
which design to pick, answered from source and history. A failure's cause is
`systematic-debugging` or the bug-fix playbook, a number to measure is
`performance-optimization`, and a captured artifact is the trace-forensics
playbook. An external codebase is `/codebase-research`.

**The gate:** the run ends at the answer and changes nothing. When a change is
wanted, name it as the next request and do not start it. The one file this run may
write is a saved copy of the reply, when asked to keep it: at the path named, or at
a gitignored scratch path when none is. Before step 1, note `git status --short` and
a checksum of each path already dirty.

1. **Explain.** Invoke `explain-code`. Its history branch takes a question about
   motivation or a regression, and its decision branch a choice between
   alternatives. When the question's premise is wrong, say so in the answer.
2. **Edit the answer.** When an answer was drafted, invoke `prose-pass` on it.
   Citations, tradeoffs tables, confidence tiers and the sources line all stay.
3. **Close out**, on every exit. Compare `git status --short` with the start: only a
   reply you were explicitly asked to save may differ. For a path already dirty at the
   start, compare its checksum with the one you noted, because its status cannot show
   whether this run touched it. Name any other difference in the reply, and name the
   scratch files kept.

## Reply

- **Answered:** the explanation, the recommendation with its table, or the history
  with its tiers and sources line. Asked "are we sure?", give your real judgement
  with reasons.
- **Stopped:** what was searched and what is still unknown.
- **Change wanted:** the answer, with the change named as the next request through
  the router.

Every reply also names the scratch files kept and any reply saved.
