# The view file

The view holds the judgment in a chart: the reader's words for states and
steps, phases, their colours, the title. It is a Python module passed with
`--view`, kept apart from the model so the model stays a plain TLA+ check.

## Exports

| Name | Kind | Returns |
|---|---|---|
| `state(v)` | function | The chart state for model state `v`: a `str` (flat chart), a non-empty `list` of parents then the leaf (nested chart), or a non-empty `dict` of region to label (regions chart) |
| `step(action, before, after)` | function | The arrow's label, or `None` to hide the step |
| `group(v)` | function | The phase of `v` as a `str`, or `None` |
| `colors` | dict | Phase name to a palette colour: `blue`, `green`, `yellow`, `orange`, `purple`, `teal`, `pink`, `gray` |
| `title` | str | The chart's title (default: the spec's name) |

Each export is optional. Any other public name is refused; helpers start with
`_`, and imported modules, functions and classes are allowed. The first answer
of `state` fixes the form, and every later answer must have the same form; in a
regions chart every state gives the same region names. A nested label cannot be
a leaf for one state and a parent for another.

`state` and `group` run no more than once for each model state, `step` no more
than once for each step, and the chart and the report share those answers. Write each
function so its answer depends on its arguments alone.

## Values

`v`, `before` and `after` are read-only mappings from variable name to value, in
one shape:

| TLA+ | Python |
|---|---|
| integer | `int` |
| `TRUE`, `FALSE` | `bool` |
| string | `str` |
| model value | `str`, its name |
| sequence or tuple `<<a, b>>` | `tuple` `(a, b)` |
| set | `frozenset` |
| record or any other function | a read-only `dict` keyed by its decoded domain values |

Every value is immutable and hashable, so any value can be a set member or a
key: `(<<1>> :> 7)` is `{(1,): 7}`. TLC prints a function on `1..n` as a
sequence, so the view sees a `tuple` there, indexed from 0. One order is used
for every label, merge and draw: booleans, then integers, strings, tuples, sets
and functions, each compared by value and its members by the same order.

A string holds the characters TLC's escapes stand for: `\"`, `\\`, `\n`, `\t`,
`\r` and `\f`. The tool refuses (exit 2, naming the variable and an excerpt of
the text) any other escape; a value TLC printed without evaluating, such as
`Nat` or an operator; a model value named exactly like a string in the same
run; and a boolean beside an integer in one set or function domain, which
Python would treat as equal.

## Labels

Every label is a non-empty string of at most 120 characters, with no control
characters and no spaces at either end. A bad answer, or an exception raised
inside `state`, `step` or `group`, is refused (exit 2) naming the state it came
from.

- **States.** Name each by what the reader sees or cares about ("Paying",
  "Lease held, write pending"), never by a variable name.
- **Steps.** Name each as the user meets it ("you press pay", "the card is
  declined"), never by the action or the code behind it. Steps with the same
  visible effect get the same label, so they share an arrow; different labels
  between two states are joined with "or".
- **Conditions.** When a step can happen only under a condition, close its
  label with that condition inside square brackets, in plain reader words:
  "you press pay [while the cart loads]". For a regions chart, leave out what
  the other regions must show: the tool adds it (`[when Network: Offline]`),
  and a `[` in your label replaces what it would add. Past the drawing budget
  it adds none: the failing paths alone cannot show the condition.
- **Hidden outcomes.** When the target of a step hinges on a value no label
  displays, put the outcome in the label: "the refund call fails".
- A step that stays inside one chart state is not drawn and is counted in the
  report. Split the label when the reader needs to see it.

## Phases and regions

`group` puts a state in a phase and `colors` gives the phase its colour. A chart
state whose model states sit in different phases gets no colour. In a regions
chart the tool checks that the regions allow exactly the model's starts and
moves; when they do not, it draws nested states instead and the report says
why. A step that moves several regions at once fires all their arrows together,
and the report notes per label whether it moves one region or several. When a step
takes every child of one parent to the same target under the same label, it is
drawn once, from the parent.

## Fewer arrows

Aim for about twenty arrows. First make `state` coarser: one label for values
that behave alike, dropping a detail the reader has no use for. Every state on a
failing path and every mark survives a merge; never merge states whose broken
rules differ, and know that a merge can turn a `breaks` mark into `mayBreak`.
Only then return `None` from `step` for steps the reader does not need, under
the hiding rules in `SKILL.md` ("Hand off"); the tool refuses a view that breaks
them, naming the step.

The tool refuses an arrow out of a looping failure that the loop cannot take,
since the chart would show an escape the model lacks; give the loop's states a
label that shows what keeps them in.

## Example

```python
def state(v):
    return {"Cart": "Paid" if v["phase"] == "paid" else "Open",
            "Network": "Online" if v["net"] else "Offline"}

def step(action, before, after):
    return {"Pay": "you press pay", "Drop": "the connection drops"}.get(action, action)

title = "Checkout"
```
