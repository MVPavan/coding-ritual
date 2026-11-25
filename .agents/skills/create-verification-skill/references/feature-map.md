# Feature map contract

The map a generated verify skill drives through: `verify-<app>/features/`, an
index (`README.md`) and one file per user-facing feature. Shared by
`create-verification-skill`, which seeds it, and maintain-verification-skill,
which keeps it current. A worked example is in `feature-map-example/`.

## Layout

- The map lives in the skill's own `features/` folder, which a later
  regeneration never overwrites: a rerun of `create-verification-skill` that
  finds a map stops and points to maintain-verification-skill.
- Seed it with an index line and a file for each of the top three to five
  user-facing features, taken from routes, commands, menus or docs.
- A seeded feature the proof run did not drive is written from the code and
  marked "not yet driven" in its file and on its index line. Its results name
  what to assert, never a value nobody observed.
- In the generated verification skill's feature-map reference, require that before reproductions rely on the map it hold an entry for every user-facing feature a reproduction may drive.
- In the generated verification skill's use rules and feature-map reference, require driving the app only through the feature map, kept where a refresh does not overwrite it, with each feature's entry giving its reset, the states that apply and its preconditions, and stopping to say so when the entry a run needs is missing rather than guessing the route.

## Index (`README.md`)

It opens by telling the reader to read the index first, then open the one
feature file that matches the task and follow it as the recipe. Then the
baseline block, then one line per feature: its file and a one-line user-side
summary.

## Baseline

The index opens with the preconditions every recipe shares: the launch address
or command, the seed data loaded, the sign-in used, and the tools that must be
on the path. Each run gets its own throwaway data folder keyed by a run id
(for example a temporary folder `<app>-verify-<run-id>/`), so two runs never share state.
Check the folder against the product's own path-safety rules (some refuse a
store under a world-writable parent such as the system temporary folder) and
record what works.

## Driving conventions

- Every recipe starts from the baseline unless it says otherwise. When an
  earlier step changed the state a later case needs, return to that state before
  proving the next case.
- Commands are literal: keep quoted names, flags and their order unchanged.
- Every browser and terminal action goes through the skill's one control
  command; no recipe calls a driver directly.
- Put seeded data back after any change to it.
- In the generated verification skill's driving section, require for an interface that screen coordinates be used only when they come from a screenshot taken right before the action.
- Wait for a concrete result (an element, a status line, a file) rather than a
  fixed delay.
- On a command line, assert against the program's machine-readable output (a
  JSON or tab-separated option) when it has one.

## Proof by surface

- **Interface:** a screenshot that shows the product's identity, plus an
  accessibility snapshot when the surface and the available tools provide one.
- In the generated verification skill's evidence section, require for an interface a screenshot that shows enough of the app to identify it, kept with its path, capture time, app marker and what it should show.
- **Command line:** the command, its standard output, its standard error and its
  exit code.
- **A saved change** is proven by reading it back through a separate read-only
  view (reopening the item from the list, a second product query that shows the
  saved item), never by its save confirmation.
- **No read view:** when the product offers no read-only way to read a change
  back, the feature file says so and the run reports that change as unverified.
- **Displayed value:** assert what the product showed, not what was typed; the
  product may normalise input.
- **No results:** tell a true empty result from an unavailable feature by waiting
  for the finished state; on a command line, assert the exact exit code and the
  empty output.
- **Cancel:** a feature with a cancel action gets a journey that cancels and
  checks what the product specifies a cancel leaves, such as no saved item.
- Label every proof file with the feature, entry point, product, input used and
  expected item.

## Skip reporting

A feature or entry point is reported unreachable only with the route tried and
the prerequisite that was missing. A skipped entry point is never claimed
through another route.

## Feature file template

Written from the user's side: what the feature does, how to reach it, how to
drive it and the visible end state that proves it. Implementation detail stays
out; name only the user's routes, durable handles, needed state, commands and
visible proof. "How to reach it" lists every way a user reaches the feature,
found in the code (each page, menu, command, shortcut and direct route), since
coverage is judged against that list.

```markdown
# <Feature name>

<One paragraph of what the user sees the feature do.>

## Sub-features
- `<short-id>`: <one line each>

## How to reach it
- <every way a user can reach the feature: page, menu, command, shortcut>

## Driving it
- action: <what the user does>
  command: <the literal control command>
  result: <the visible proof to assert>

## Gotchas
- <a trap that could waste a run or make its result invalid>
```

## Coverage

The map defines what must be proven. Proof through one entry point falls short
while the file lists more.

## Gotchas

Keep each feature's gotchas for traps that could waste a verification run or
make its result invalid, not for general notes. When the seed data lacks a
precondition a journey needs, record the missing precondition there.
