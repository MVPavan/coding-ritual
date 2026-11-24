# Steering file: template

Read at step 4 of `control-loop`, to start the loop's steering file: the
owner's standing guidance, version-controlled in the loop folder and placed in
the agent's prompt after the controller's selected work on every run, so an
edit changes every later run, not one pull request.

Keep in it only what should change future runs: a scope exclusion, a known
false positive, a pattern a review corrected. Not a one-off instruction or a
run's log (those go in the run's task bead). A rule that already lives in the
actuator instructions or the controller stays there. Selection itself
(exclusions by target) is the controller's, through the loop bead's notes.

```markdown
# <Loop name>: steering

Standing guidance from the owner, read after the selected work on every run.
Edit it to change what later runs do.

## Guidance

- <a scope exclusion, a false positive, or a review lesson, with the date it
  was added>
```
