# Agent bridge and workflow coordination

Complete normal phase execution through the interpreter, then add bounded model decisions, independent child workflows, and serialized integration.

Approved behavior: [workflow coordination spec](../../specs/2026-09-11-workflow-coordination.md).
Execution sequence: [roadmap](roadmap.md). Durable work state is Beads; tracking files are generated.
The prior handoff in the coordinator checkout describes the paused sequential bridge. Implementation resumes that existing worktree and preserves its unfinished authority changes.

Implementation plans: [P1 sequential bridge](plans/P1.md), [P2 bounded decisions](plans/P2.md), [P3 child coordination](plans/P3.md), [P4 integration](plans/P4.md), [P5 normal execution and successors](plans/P5.md). A plan is not implementation evidence; consult Beads and the [handoff](state.md).

Verification evidence: [P1 repository gates and real-runtime execution](verification/P1.md).

Verified phase evidence: [P2 bounded model decisions](verification/P2.md).

Verified phase evidence: [P3 independent children](verification/P3.md).

Verified phase evidence: [P4 fresh integration](verification/P4.md).

Verified phase evidence: [P5 normal execution and real-runtime proof](verification/P5.md).
