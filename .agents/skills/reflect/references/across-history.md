# Across history

Read only when the person asks to review the project's history rather than
sessions (`SKILL.md` step 1). This scope looks for mistakes that recur across
the project's record. Each section below replaces the session parts of its step;
the rest of that step holds as written.

## Steps 1-2: scope and evidence

Say the scope back: the window (recent history unless the person names one)
and the sources read. Read them, read-only:

- version-control history, reverts and fix-up commits;
- review and critic findings;
- tracker comments and close reasons;
- the project's lessons file, wherever its instructions send lessons;
- the instruction files, for rules added after a mistake;
- workaround comments in the code.

A source the project does not have is a gap reported in the reply.

## Step 3: review

Give the history to one fresh reviewer through `delegation`, briefed with
`references/reviewer-brief.md` followed by this section, and with the sources
and the window in place of a log location. In that brief, "the session" and
"the log" mean the history in scope, and the reviewer returns classes instead
of single findings:

- Group the mistakes into classes: one class is one kind of mistake, however
  many places it appears.
- Keep a class only when it has at least two occurrences; one occurrence is a
  one-off, not a lesson.
- For each class give its occurrences with pointers (commit, finding, comment),
  the enforcement level chosen and why no stronger level works. Choose the
  strongest level that works: a check before a test before a written rule (the
  full order is in `authoring-for-agents`).

## Step 4: merge and check

Check each class against the record: open every cited occurrence and confirm it
shows that mistake. Drop an occurrence the record does not bear out, and a class
left with fewer than two. Mark each remaining class accepted, rejected with its
reason, or backlog, with its destination. A class a check could enforce goes to
`build-a-lever`, one a test could catch goes to `tdd`, and only a judgement call
becomes a written rule.

## Step 5: present

Present the classes most frequent first, in place of worst first. Each class
shows its confirmed occurrences, the level chosen, why no stronger level works,
and its destination. Wait for the person to approve a subset; never apply a class
without approval.

## Step 6: apply

Apply the approved subset in that order, most frequent first, so this pass fixes
the most frequent classes. Each goes through its owner as in step 6; an approved
test goes through `tdd`, following the project's test conventions.

## Step 7: reply

Report as in step 7, but give as coverage the window, the sources checked and
the sources the project lacks, in place of the sessions reviewed and the logs
not found.
