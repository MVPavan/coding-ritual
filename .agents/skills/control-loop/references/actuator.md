# Actuator instructions: template

Read at step 4 of `control-loop`, to write the loop's actuator instructions: a
file in the loop folder that the run script puts first in the agent's prompt,
before the controller's selected work and the steering file. It is the one
home of the golden pattern, the outcomes and the body format. Fill every
`<...>`; keep it to what changes the agent's work on one target.

```markdown
# <Loop name>: actuator instructions

You are one run of the <loop name> control loop in this repository. The
selected work below names one target. Change only that target's paths; the run
script refuses anything else. Nobody answers questions during a run: when you
cannot finish within these rules, skip the target and say why.

## The change

<The golden pattern: what a good change looks like here, with the paths of one
or two existing examples to follow. The smallest change that clears the
target's measured gap, with no behaviour change unless the set point is a
behaviour.>

Never clear the target by silencing the measurement (an ignore entry, a
suppression comment, a changed tool configuration): skip it instead. The run
script refuses any added or changed line carrying a directive of the tool, and
counts with suppressions ignored, so no other finding may rise either.

## Commands you may run

<Exactly the commands the allowlist grants, for example the sensor's tool on
the target and its formatter. The run script runs the full validation itself
after you finish.>

## Outcome

Make the first line of your final message one of:

- `OUTCOME: fixed`
- `OUTCOME: skipped - <why this target needs a person>`

Then, for `fixed`, the pull request's middle section in this form:

### What changed
- <each kind of finding or change, how many, and how it was fixed>

### Risk
<low, medium or high, with the reason; for medium or high, how a reviewer can
check it by hand>

### Notes
<anything the reviewer should know: a finding fixed by hand rather than by the
tool, a pattern the steering file might want>
```

The run script builds the rest of the body around that section: the target,
the measurement before and after, each validation it ran and its result, the
manual checks the commit gate printed, the run's task bead and the
`Refs #<loop issue>` line.
