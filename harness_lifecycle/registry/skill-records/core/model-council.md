---
skill: model-council
domain: core
stage: X
substage: Coordination
secondary: []
family: 
aliases: []
status: active
---
# model-council

Use only on an explicit request for a council of named models or agents with a judge, never by itself; a yes in words to one counts. It can also turn candidates into one artifact, picked and grafted. Usually one critic review is enough, and ordinary `discovery` needs no council; two options to weigh is `codebase-design`, and two to try is `prototype`.

**Boundary:** Runs an explicitly requested council of named models or agents with a judge; a council of perspectives or roles is perspective-council, and dispatching each member is delegation; on request it also turns candidates into one artifact, which a build's playbook then uses.

<!-- registry:generated traits -->
- `member-resolution`: Resolve the members and judge from the request's explicit selections, asking only for missing choices or unreachable members.
- `runtime-capability-check`: Verify actual runtime dispatch interfaces before assuming cross-provider access from a model name or placing effort only in prose when a runtime control exists.
- `neutral-framing`: Frame one neutral shared brief for every member, stating the question, constraints and uncertainty with no preferred conclusion.
- `member-isolation`: Give each member the shared brief in isolation so none sees another's response; sequential dispatch is allowed.
- `report-preservation`: Save every member's full attributed report under the run directory rather than discarding it after synthesis.
- `independent-synthesis`: A fresh synthesizer that did not participate receives every member's full report and produces agreement, disputes, blind spots and a best-supported recommendation, treating agreement as no proof.
- `consolidated-delivery`: Deliver a concise consolidation with member-position summaries and paths to every full report, inlining full text only on request.
- `identity-recording`: Record the actual model identities wherever the runtime provides evidence of them.
- `failed-member-recovery`: Give a failed member bounded safe recovery before treating it as missing.
- `no-silent-substitution`: Never backfill a missing member with your own answer or a silent substitute; report the gap and whether the synthesizer saw an incomplete set.
- `artifact-named-up-front`: State exactly what artifact each candidate must produce before any candidate starts.
- `task-rubric-criteria`: Write three to six concrete, gradeable success criteria specific to this task.
- `rubric-withheld-from-candidates`: Keep the success criteria from the candidates, who see only the task.
- `own-output-location`: Give every candidate or adversary a separate output location, so they share no writable state.
- `rationale-names-rejected`: Have each candidate deliver, with its artifact, a short rationale naming the alternatives it weighed and what it rejected.
- `dropout-proceeds-noted`: Go on with the remaining candidates or adversaries when one produces nothing, and record the dropout.
- `read-only-judge`: Give the judge read-only access.
- `judge-other-family-or-stated`: Take the judge from a model family other than the coordinator's, and say so when the user's choice shares that family or the coordinator cannot tell its own.
- `rubric-given-to-judge`: Give the judge the success criteria to score against.
- `path-labelled-candidates`: Show the judge each candidate under its path label.
- `judge-criterion-scores`: Have the judge score each candidate on each criterion.
- `judge-recommends-base`: Have the judge recommend a base and justify the recommendation.
- `full-read-before-pick`: Read every candidate in full before choosing a base.
- `picker-criterion-scores`: Score each candidate on each criterion instead of by overall impression.
- `pick-compared-with-judge`: Compare your scored pick with the judge's, treating the same choice as confirmation.
- `disagreement-rereads-rationales`: Treat a disagreement with the judge as a sign of bias or an unclear rubric, and read both rationales before deciding.
- `base-chosen-for-extensibility`: Choose the base a later maintainer could extend most easily while keeping invariants intact.
- `near-tie-smaller-surface`: Break a near-tie in favour of the cleaner boundary or the smaller interface.
- `loser-graft-pass`: Go through each losing candidate once more for parts worth carrying over.
- `sparse-grafts`: Expect only one or two grafts from a losing candidate, not the bulk of it.
- `hand-folded-grafts`: Rewrite each graft into the base by hand, so the result keeps one coherent design rather than pasted fragments.
- `converged-shape-no-graft`: When candidates reach one shape, record the agreement and ship that shape with no graft.
- `divergence-reframes-once`: When candidates differ wildly, treat the frame as too loose, reframe and rerun at most once, then stop and report instead of blending them.
- `graft-change-rerun`: After grafting, rerun the acceptance check of any previously checked behaviour the graft changed, reuse evidence for the rest and name what stays unchecked.
- `verify-miss-returns-once`: Send a verification problem back once to reframing or to grafting, whichever caused it, then report any further miss rather than hiding it.
- `single-synthesized-artifact`: End with one merged artifact rather than a set of alternatives.
- `synthesis-decision-record`: Record the chosen base candidate with its reason, what was grafted from the rest and why each was rejected.
- `note-judge-status`: Record in the synthesis note the judge's verdict or that the judge was skipped.
- `note-convergence-dropouts`: Record any convergence or dropped candidates in the synthesis note.
- `note-verification-result`: Record the verification result in the synthesis note.
- `no-judge-no-pick`: With no judge reachable, count no completed council: stop, say so and return the candidates with no pick.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/arena#artifact-named-up-front** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#task-rubric-criteria** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#rubric-withheld-from-candidates** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#own-output-location** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#rationale-names-rejected** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#dropout-proceeds-noted** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#read-only-judge** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#judge-outside-lead-family** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#family-check-unrun-disclosed** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#rubric-given-to-judge** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#path-labelled-candidates** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#judge-criterion-scores** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#judge-recommends-base** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#full-read-before-pick** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#picker-criterion-scores** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#pick-compared-with-judge** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#disagreement-rereads-rationales** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#base-chosen-for-extensibility** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#near-tie-smaller-surface** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#loser-graft-pass** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#sparse-grafts** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#hand-folded-grafts** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#converged-shape-no-graft** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#divergence-reframes** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#synthesized-artifact-verified** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#verify-miss-routes-back** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#single-synthesized-artifact** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#synthesis-decision-record** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#note-judge-status** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#note-convergence-dropouts** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/arena#note-verification-result** `pstack/skills/arena/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-11` **update** (2026-11-11-discovery:008): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D1. Its description's routing clause names `discovery` (plan 20 De…
- `2026-11-03` **update** (2026-11-03-batch-3:148): A branch that turns candidates into one artifact, picked and grafted, in references/pick-and-graft.md and loaded only on the branch. The description now says e…
- `2026-11-03` **adopt** (2026-11-03-batch-3:147): Completes pending 2026-11-03-batch-3:049: note-verification-result is written at .claude/skills/model-council/references/pick-and-graft.md:35, read against its…
- `2026-11-03` **adopt** (2026-11-03-batch-3:146): Completes pending 2026-11-03-batch-3:048: note-convergence-dropouts is written at .claude/skills/model-council/references/pick-and-graft.md:34-35, read against…
- `2026-11-03` **adopt** (2026-11-03-batch-3:145): Completes pending 2026-11-03-batch-3:047: note-judge-status is written at .claude/skills/model-council/references/pick-and-graft.md:34, read against its defini…
- `2026-11-03` **adopt** (2026-11-03-batch-3:144): Completes pending 2026-11-03-batch-3:046: synthesis-decision-record is written at .claude/skills/model-council/references/pick-and-graft.md:33-34, read against…
- `2026-11-03` **adopt** (2026-11-03-batch-3:143): Completes pending 2026-11-03-batch-3:045: single-synthesized-artifact is written at .claude/skills/model-council/references/pick-and-graft.md:32-33, read again…
- `2026-11-03` **adopt** (2026-11-03-batch-3:142): Completes pending 2026-11-03-batch-3:044: verify-miss-returns-once is written at .claude/skills/model-council/references/pick-and-graft.md:30-31, read against …
- `2026-11-03` **adopt** (2026-11-03-batch-3:141): Completes pending 2026-11-03-batch-3:043: graft-change-rerun is written at .claude/skills/model-council/references/pick-and-graft.md:29-30, read against its de…
- `2026-11-03` **adopt** (2026-11-03-batch-3:140): Completes pending 2026-11-03-batch-3:042: divergence-reframes-once is written at .claude/skills/model-council/references/pick-and-graft.md:27-28, read against …
- `2026-11-03` **adopt** (2026-11-03-batch-3:139): Completes pending 2026-11-03-batch-3:041: converged-shape-no-graft is written at .claude/skills/model-council/references/pick-and-graft.md:26-27, read against …
- `2026-11-03` **adopt** (2026-11-03-batch-3:138): Completes pending 2026-11-03-batch-3:040: hand-folded-grafts is written at .claude/skills/model-council/references/pick-and-graft.md:25-26, read against its de…
- `2026-11-03` **adopt** (2026-11-03-batch-3:137): Completes pending 2026-11-03-batch-3:039: sparse-grafts is written at .claude/skills/model-council/references/pick-and-graft.md:24-25, read against its definit…
- `2026-11-03` **adopt** (2026-11-03-batch-3:136): Completes pending 2026-11-03-batch-3:038: loser-graft-pass is written at .claude/skills/model-council/references/pick-and-graft.md:24, read against its definit…
- `2026-11-03` **adopt** (2026-11-03-batch-3:135): Completes pending 2026-11-03-batch-3:037: near-tie-smaller-surface is written at .claude/skills/model-council/references/pick-and-graft.md:23, read against its…
- `2026-11-03` **adopt** (2026-11-03-batch-3:134): Completes pending 2026-11-03-batch-3:036: base-chosen-for-extensibility is written at .claude/skills/model-council/references/pick-and-graft.md:22-23, read aga…
- `2026-11-03` **adopt** (2026-11-03-batch-3:133): Completes pending 2026-11-03-batch-3:035: disagreement-rereads-rationales is written at .claude/skills/model-council/references/pick-and-graft.md:21-22, read a…
- `2026-11-03` **adopt** (2026-11-03-batch-3:132): Completes pending 2026-11-03-batch-3:034: pick-compared-with-judge is written at .claude/skills/model-council/references/pick-and-graft.md:20-21, read against …
- `2026-11-03` **adopt** (2026-11-03-batch-3:131): Completes pending 2026-11-03-batch-3:033: picker-criterion-scores is written at .claude/skills/model-council/references/pick-and-graft.md:19-20, read against i…
- `2026-11-03` **adopt** (2026-11-03-batch-3:130): Completes pending 2026-11-03-batch-3:032: full-read-before-pick is written at .claude/skills/model-council/references/pick-and-graft.md:19, read against its de…
- `2026-11-03` **adopt** (2026-11-03-batch-3:129): Completes pending 2026-11-03-batch-3:030: judge-recommends-base is written at .claude/skills/model-council/references/pick-and-graft.md:17, read against its de…
- `2026-11-03` **adopt** (2026-11-03-batch-3:128): Completes pending 2026-11-03-batch-3:029: judge-criterion-scores is written at .claude/skills/model-council/references/pick-and-graft.md:16, read against its d…
- `2026-11-03` **adopt** (2026-11-03-batch-3:127): Completes pending 2026-11-03-batch-3:028: path-labelled-candidates is written at .claude/skills/model-council/references/pick-and-graft.md:15-16, read against …
- `2026-11-03` **adopt** (2026-11-03-batch-3:126): Completes pending 2026-11-03-batch-3:027: rubric-given-to-judge is written at .claude/skills/model-council/references/pick-and-graft.md:14-15, read against its…
- `2026-11-03` **adopt** (2026-11-03-batch-3:125): Completes pending 2026-11-03-batch-3:026: judge-other-family-or-stated is written at .claude/skills/model-council/references/pick-and-graft.md:13-14, read agai…
- `2026-11-03` **adopt** (2026-11-03-batch-3:124): Completes pending 2026-11-03-batch-3:023: judge-other-family-or-stated is written at .claude/skills/model-council/references/pick-and-graft.md:12-13, read agai…
- `2026-11-03` **adopt** (2026-11-03-batch-3:123): Completes pending 2026-11-03-batch-3:022: read-only-judge is written at .claude/skills/model-council/references/pick-and-graft.md:12, read against its definiti…
- `2026-11-03` **adopt** (2026-11-03-batch-3:122): Completes pending 2026-11-03-batch-3:019: dropout-proceeds-noted is written at .claude/skills/model-council/references/pick-and-graft.md:10-11, read against it…
- `2026-11-03` **adopt** (2026-11-03-batch-3:121): Completes pending 2026-11-03-batch-3:018: rationale-names-rejected is written at .claude/skills/model-council/references/pick-and-graft.md:9-10, read against i…
- `2026-11-03` **adopt** (2026-11-03-batch-3:120): Completes pending 2026-11-03-batch-3:014: own-output-location is written at .claude/skills/model-council/references/pick-and-graft.md:8-9, read against its def…
- `2026-11-03` **adopt** (2026-11-03-batch-3:119): Completes pending 2026-11-03-batch-3:005: rubric-withheld-from-candidates is written at .claude/skills/model-council/references/pick-and-graft.md:7, read again…
- `2026-11-03` **adopt** (2026-11-03-batch-3:118): Completes pending 2026-11-03-batch-3:004: task-rubric-criteria is written at .claude/skills/model-council/references/pick-and-graft.md:6-7, read against its de…
- `2026-11-03` **adopt** (2026-11-03-batch-3:117): Completes pending 2026-11-03-batch-3:003: artifact-named-up-front is written at .claude/skills/model-council/references/pick-and-graft.md:6, read against its d…
- `2026-11-03` **adopt-merged** (2026-11-03-batch-3:050): Checkpoint at 4dd1d05 for the owner's trait rulings: 31 adopt, 18 reject.
- `2026-11-03` **adopt** (2026-11-03-batch-3:049) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:48.
- `2026-11-03` **adopt** (2026-11-03-batch-3:048) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:48.
- `2026-11-03` **adopt** (2026-11-03-batch-3:047) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:48.
- `2026-11-03` **adopt** (2026-11-03-batch-3:046) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:48.
- `2026-11-03` **adopt** (2026-11-03-batch-3:045) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:48.
- `2026-11-03` **adopt** (2026-11-03-batch-3:044) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md, into `verify-miss-returns-once`. Upstream: SKILL.md:44.
- `2026-11-03` **adopt** (2026-11-03-batch-3:043) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md, into `graft-change-rerun`. Upstream: SKILL.md:44.
- `2026-11-03` **adopt** (2026-11-03-batch-3:042) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md, into `divergence-reframes-once`. Upstream: SKILL.md:40.
- `2026-11-03` **adopt** (2026-11-03-batch-3:041) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:40.
- `2026-11-03` **adopt** (2026-11-03-batch-3:040) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:38.
- `2026-11-03` **adopt** (2026-11-03-batch-3:039) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:38.
- `2026-11-03` **adopt** (2026-11-03-batch-3:038) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:38.
- `2026-11-03` **adopt** (2026-11-03-batch-3:037) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:34.
- `2026-11-03` **adopt** (2026-11-03-batch-3:036) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:34.
- `2026-11-03` **adopt** (2026-11-03-batch-3:035) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:32.
- `2026-11-03` **adopt** (2026-11-03-batch-3:034) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:32.
- `2026-11-03` **adopt** (2026-11-03-batch-3:033) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:32.
- `2026-11-03` **adopt** (2026-11-03-batch-3:032) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:32.
- `2026-11-03` **adopt** (2026-11-03-batch-3:030) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:28.
- `2026-11-03` **adopt** (2026-11-03-batch-3:029) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:28.
- `2026-11-03` **adopt** (2026-11-03-batch-3:028) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:28.
- `2026-11-03` **adopt** (2026-11-03-batch-3:027) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:28.
- `2026-11-03` **adopt** (2026-11-03-batch-3:026) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md, into `judge-other-family-or-stated`. Upstream: SKILL.md:28.
- `2026-11-03` **adopt** (2026-11-03-batch-3:023) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md, into `judge-other-family-or-stated`. Upstream: SKILL.md:28.
- `2026-11-03` **adopt** (2026-11-03-batch-3:022) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:28.
- `2026-11-03` **adopt** (2026-11-03-batch-3:019) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:24.
- `2026-11-03` **adopt** (2026-11-03-batch-3:018) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:22.
- `2026-11-03` **adopt** (2026-11-03-batch-3:014) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:18.
- `2026-11-03` **adopt** (2026-11-03-batch-3:005) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:16.
- `2026-11-03` **adopt** (2026-11-03-batch-3:004) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:16.
- `2026-11-03` **adopt** (2026-11-03-batch-3:003) *(superseded)*: Owner ruling 2026-11-03: Lands in model-council, references/pick-and-graft.md. Upstream: SKILL.md:15.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-03-upstream-cursor_plugins-4dd1d05-batch-3.md](../../reviews/2026-11-03-upstream-cursor_plugins-4dd1d05-batch-3.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `artifact-named-up-front`:
  - `cursor_plugins:skill:pstack/skills/arena#artifact-named-up-front` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `base-chosen-for-extensibility`:
  - `cursor_plugins:skill:pstack/skills/arena#base-chosen-for-extensibility` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `converged-shape-no-graft`:
  - `cursor_plugins:skill:pstack/skills/arena#converged-shape-no-graft` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `disagreement-rereads-rationales`:
  - `cursor_plugins:skill:pstack/skills/arena#disagreement-rereads-rationales` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `divergence-reframes-once`:
  - `cursor_plugins:skill:pstack/skills/arena#divergence-reframes` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `dropout-proceeds-noted`:
  - `cursor_plugins:skill:pstack/skills/arena#dropout-proceeds-noted` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `full-read-before-pick`:
  - `cursor_plugins:skill:pstack/skills/arena#full-read-before-pick` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `graft-change-rerun`:
  - `cursor_plugins:skill:pstack/skills/arena#synthesized-artifact-verified` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `hand-folded-grafts`:
  - `cursor_plugins:skill:pstack/skills/arena#hand-folded-grafts` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `judge-criterion-scores`:
  - `cursor_plugins:skill:pstack/skills/arena#judge-criterion-scores` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `judge-other-family-or-stated`:
  - `cursor_plugins:skill:pstack/skills/arena#family-check-unrun-disclosed` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
  - `cursor_plugins:skill:pstack/skills/arena#judge-outside-lead-family` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `judge-recommends-base`:
  - `cursor_plugins:skill:pstack/skills/arena#judge-recommends-base` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `loser-graft-pass`:
  - `cursor_plugins:skill:pstack/skills/arena#loser-graft-pass` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `near-tie-smaller-surface`:
  - `cursor_plugins:skill:pstack/skills/arena#near-tie-smaller-surface` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `note-convergence-dropouts`:
  - `cursor_plugins:skill:pstack/skills/arena#note-convergence-dropouts` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `note-judge-status`:
  - `cursor_plugins:skill:pstack/skills/arena#note-judge-status` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `note-verification-result`:
  - `cursor_plugins:skill:pstack/skills/arena#note-verification-result` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `own-output-location`:
  - `cursor_plugins:skill:pstack/skills/arena#own-output-location` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `path-labelled-candidates`:
  - `cursor_plugins:skill:pstack/skills/arena#path-labelled-candidates` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `pick-compared-with-judge`:
  - `cursor_plugins:skill:pstack/skills/arena#pick-compared-with-judge` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `picker-criterion-scores`:
  - `cursor_plugins:skill:pstack/skills/arena#picker-criterion-scores` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `rationale-names-rejected`:
  - `cursor_plugins:skill:pstack/skills/arena#rationale-names-rejected` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `read-only-judge`:
  - `cursor_plugins:skill:pstack/skills/arena#read-only-judge` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `rubric-given-to-judge`:
  - `cursor_plugins:skill:pstack/skills/arena#rubric-given-to-judge` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `rubric-withheld-from-candidates`:
  - `cursor_plugins:skill:pstack/skills/arena#rubric-withheld-from-candidates` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `single-synthesized-artifact`:
  - `cursor_plugins:skill:pstack/skills/arena#single-synthesized-artifact` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `sparse-grafts`:
  - `cursor_plugins:skill:pstack/skills/arena#sparse-grafts` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `synthesis-decision-record`:
  - `cursor_plugins:skill:pstack/skills/arena#synthesis-decision-record` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `task-rubric-criteria`:
  - `cursor_plugins:skill:pstack/skills/arena#task-rubric-criteria` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `verify-miss-returns-once`:
  - `cursor_plugins:skill:pstack/skills/arena#verify-miss-routes-back` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
