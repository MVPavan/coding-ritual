# Pick and graft

Use this branch when the requester wants one built artifact from the members, not an
answer. It adds to the core steps of `SKILL.md`, which all still run.

1. **Frame.** Name the artifact every member will produce. Write three to six gradeable
   criteria for this task. Members see only the task, never the criteria.
2. **Candidates.** Each member writes only to its own location
   (`principle-separate-before-serializing-shared-state`). Each member returns its
   artifact and a short rationale saying what it weighed and turned down. A member
   produces nothing: go on and report it. Fewer than two left: no pick, and say so.
3. **Judge.** The judge gets core step 3 and read-only access. The judge comes from a
   family other than the coordinator's; if the user's choice does not, say so. If you
   cannot tell your own model, say the family check did not run. The judge receives the
   criteria. Give the judge every full attributed report, identified by its candidate
   path, as core step 3 requires. The judge scores every candidate on every criterion.
   The judge recommends a base and says why. No judge reachable after asking: no
   completed council, so stop, say so, and return the candidates with no pick.
4. **Pick.** The coordinator reads every candidate whole. It scores each one per
   criterion, not on overall feel. Only then compare with the judge; the same base
   confirms the pick. A different base means bias or a loose rubric: reread both
   rationales, then decide. The base is whichever a later maintainer extends most easily
   while invariants hold. A near-tie goes to the cleaner boundary or the smaller interface.
5. **Graft.** Go through each loser once more for what is worth carrying over. Expect one
   or two things from each, not most of it. Rewrite each by hand into one coherent result
   (`principle-redesign-from-first-principles`). Same shape everywhere: say so and graft
   nothing. Wild divergence: the frame was too loose, so reframe and rerun once, then stop
   and report.
6. **Verify.** If grafts change a previously checked behaviour, rerun its acceptance
   check; reuse evidence for unchanged parts and name what stays unchecked. A miss returns
   once to frame or graft, whichever was wrong; a second miss is reported.
7. **Deliver.** Deliver core step 4 plus the one artifact, left in its own location for
   the caller to move. Add a note: the base and why, each graft with its source, what was
   rejected and why. The note gives the judge's verdict. The note says where the members
   converged and who dropped out. The note gives the verification result.
