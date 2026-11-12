---
name: no-comments
description: "Sweep a scope for comments that should go, judged by principle-no-comments, then fix what the sweep exposes and offer checks for real constraints. Use for /no-comments; reviewing a change for bugs or design is review."
disable-model-invocation: true
argument-hint: "Files, a diff or a path (default: this branch since it left main, with the working tree)"
---

# No comments

Read `principle-no-comments` first; it decides each comment. This skill runs
the sweep around it.

## Steps

1. **Scope.** Use the scope the person names when they give one. Otherwise
   take the branch from where it left the base branch (default `main`) through
   the working tree, untracked files included. Say the scope back before
   deleting anything.
2. **Comment pass.** Change only comments, and only inside the scope; code
   fixes wait for step 3.
   - Lint and type-checker suppressions are part of the sweep.
   - Before accepting a thinly justified keep or delete of a comment marked
     important (`IMPORTANT`, "do not remove" and the like), run `how` on its
     symbol's behaviour and `why` on its history.
   - Where a comment explained surprising behaviour in our own code, flag the
     exact symbol for a restructure that would make the behaviour obvious. A
     restructuring flag stays open until a fix inside the scope resolves it,
     otherwise the closing report lists it as open. What happens to its
     comment neither closes it nor is decided by it.
   - Never flag code that was kept on purpose as being at fault.
3. **Fixes**, after the comment pass and inside the same scope.
   - Resolve a simple accepted flag at once: remove an unused path or
     parameter, or call the real interface.
   - Remove every workaround the findings name, however many in-scope edits
     that takes. A named workaround that cannot be removed inside the scope or
     your authority is reported as incomplete, never left as a mere flag.
   - Other, larger restructuring suggestions stay flags in the report.
4. **Constraint comments.** For a constraint comment about something we
   control:
   - Offer the cheapest enforcement available in scope: a type, a runtime
     check, a test or a CI lint.
   - Apply one only with approval, through the route the person names, or
     given in advance for an unattended run.
   - Approved: add the enforcement, then delete the comment.
   - Not approved: keep the comment, report the constraint as open and sketch
     any work it needs outside the scope.
5. **Report.** List the comments deleted, those restored on proof, those kept
   and flagged, the fixes, the enforcements offered and those done, the
   constraints left unenforced, and the open items, including every open
   restructuring flag and any named workaround left incomplete.
