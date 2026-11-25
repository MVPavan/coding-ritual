# Placing a skill

Every skill has one primary coordinate: domain · stage · sub-stage. Stages
and sub-stages are defined in `harness_lifecycle/adlc/GUIDE.md` §1; its mapping rules (§1,
"Mapping skills onto the lifecycle") decide placement.

1. Name the artifact the skill produces. The sub-stage that owns that
   artifact is the primary home. A skill that serves every stage belongs to X
   Crosscutting or U Utilities.
2. Check the definition and the boundary table in `harness_lifecycle/adlc/GUIDE.md` §1. A
   placement that needs a boundary exception is wrong.
3. Add at most two secondary tags, only for real spans.
4. List the other skills already in that domain · sub-stage (`harness_lifecycle/registry/INDEX.md`). Two
   active skills in one sub-stage each state their `boundary` in
   `harness_lifecycle/registry/skills.yaml`, or they are merge candidates (`skill-review.md`).
5. Write the placement and boundary in `harness_lifecycle/registry/skills.yaml`; what the skill
   does and when it fires is its `SKILL.md` description. Then list its traits
   in `harness_lifecycle/registry/traits/ours.yaml` by the procedure in `upstream-review.md` step 2 (extract
   blind, then map), with the folder's `tree_hash`, and run `registry.py
   build`.
