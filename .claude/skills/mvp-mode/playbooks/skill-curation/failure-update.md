# Updating from our own failure

1. Record the failure before changing anything: the task, what the agent did,
   and what it should have done.
2. Find the owning skill by its coordinate (`placing.md`). Fix it there, not in a
   neighbour.
3. Pick the form that fixes the failure (`authoring-for-agents`, "Match the
   form to the failure").
4. Re-run the task, or a fresh-context test of it, and keep both results as
   the `update` event's evidence.
5. Update the skill's traits in `harness_lifecycle/registry/traits/ours.yaml` and its
   `tree_hash`.
   If the fix drops a trait we adopted from upstream, the `update` event
   lists that upstream trait in `withdraws`; an upstream ruling never removes
   it for us. A playbook has no `traits/ours.yaml` entry: its frontmatter is
   its trait list, and `record` stores its hash on an `update` of
   `doc:<its path>` (`harness_lifecycle/registry/README.md` §4b).
