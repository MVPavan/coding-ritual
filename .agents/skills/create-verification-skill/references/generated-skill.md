# Writing a generated verify skill

The shared contract for a project skill that drives a real app, owned by
`create-verification-skill` and read by the other verification units. The skill
lives in the project's skills folder as `verify-<app>/`
(Claude Code: `.claude/skills/verify-<app>/`), with `features/` beside its `SKILL.md`.

## Frontmatter

Give it a `name` (`verify-<app>`) and a `description` that names the app, the
surface it drives and when to use it ("Use to launch and drive <app>'s command
line for proof of a change or a reproduction"), so the host registers it and an
agent working on that surface finds it. No other field is required.

## Writing rules

- The reader is an agent meeting the project cold, mid-task. Each section opens
  with what to run; background comes after, if at all.
- Use the real names from the code: commands, flags, routes, ports, environment
  variables, file paths, helper names. Never a placeholder such as `<your-app>`
  or `example.com` where the real value is known.
- Every command is literal and copyable; the run that wrote it ran it. The
  one exception is a feature entry marked not yet driven (`feature-map.md`,
  Layout).
- A rule here or in `feature-map.md` that opens "In the generated verification
  skill's …" names the section it lands in. Write it there as a direct rule in the terms of the
  surface the skill drives; drop a clause for a surface it does not drive, and
  say so in that section. Where `feature-map.md` carries the same rule, that
  file owns it and this one restates it for the section it lands in.
- Keep it to the fixed sections below, in this order. A section that does not
  apply says so in one line rather than disappearing.

## Launch

- The exact start command, and the concrete sign the product is ready to use: a
  page that renders its own content, a command that answers a real request, a
  sign-in that succeeds. A process that is up or a health check that answers
  while the app is still initialising is not ready.
- Launch from an empty data folder: migrations, seed data and sign-in setup are
  part of it, so the launch works on a fresh checkout.
- Pair the launch with its teardown, in the same section.
- For a short-lived command-line or terminal program, launch is one build or
  install, then an isolated session per drive (its own working folder, config
  and data, set by the helper). A command line that needs a long-lived service
  (a database, a queue) launches that service as the instance, with its
  teardown; each drive is an isolated session against it.

### Isolation (inside Launch)

Record the instance-isolation result the study found. The skill drives only an
instance its own run started; when the only instance is shared and cannot be
isolated (a shared staging server, the person's running app), it declines and
says so.

When the product uses a live service (a database, a queue, a vendor API),
every command the skill runs (launch, doctor, each drive, cleanup and every
helper) also:

- start each child process from a clean environment holding only the run's own
  values, so no inherited variable, credentials folder or default config can
  point it at someone else's service;
- refuse to run when a project env file (such as `.env`) would be read;
- before the first write, prove the endpoint is the run's own: its address, its
  data folder, a marker the run planted in it and a sign-in with credentials
  the run created;
- run only the commands the skill lists, refusing any other.

## Doctor

One read-only command that checks the instance is alive, is the right build,
owns its port, has valid sign-in, and matches the expected address, data folder
and revision. It changes nothing. Run it after launch, and first whenever
something looks wrong, before guessing at a cause.

## Drive

- Prefer durable handles: accessible roles and names, data attributes, prompt
  strings, routes, command names. Never screen positions, tab order or list
  position when a handle exists.
- In the generated verification skill's driving section, require for an interface that screen coordinates be used only when they come from a screenshot taken right before the action.
- Drive each feature as its file in `features/` says; the map's driving
  conventions apply (`feature-map.md`).

## Evidence

- Name what each proof captures and the folder it is kept in, one per run.
- Prove a feature through the path a real user takes; never through internal
  setters, test-only endpoints or direct database writes.
- Capture the action taken and the state that resulted, not only the final
  screen or the last line of output.
- Check side effects too: files written, rows inserted, messages sent.
- Never print, log or keep a credential, including one the run generated. Tool
  output that can hold one (resolved Compose config, container-inspect output,
  a connection string) is parsed inside the helper and never saved.
- Use test doubles only at system boundaries (external services, time, the file
  system); never stand in for a module the project owns.
- When the skill uses a dry-run or offline mode, record what the proof run
  observed that mode skip (no connection opened, no file written, no row
  changed); never trust the mode by its name. Observe it by running the drive
  where the network is unavailable (a network namespace, reaching the app's own
  services through a socket the helper relays) or by tracing its connections,
  and record the observation for each step.
- In the generated verification skill's evidence section, require for a reproduction a note of the steps and, on a visual surface with capture tools, a recording of the whole path that shows the broken final state; require that every captured screenshot and recording be looked at before it is cited; and, when the needed proof cannot be captured, a statement of what stays unverified.
- In the generated verification skill's evidence section, require for an interface a screenshot that shows enough of the app to identify it, kept with its path, capture time, app marker and what it should show.

## Cleanup

- Stop only the instances this run created, by the process id, container or
  project name it recorded; never by process name.
- Cleanup removes instances and scratch state; proof files survive in the
  evidence folder the skill names. Captures from earlier runs are removed only
  once past the retention window the skill names; this run's proof is never in
  that set. When the skill keeps no window, it says so and names who removes
  old runs.
- In the generated verification skill's cleanup section, require that cleanup stop the processes and sessions the driver created, remove the run's throwaway profiles, temporary workspaces and the fixtures it created, remove a capture only once it is past its retention window, report anything stopped, removed, kept or left, and never delete the person's own work.
- Run cleanup after a failed attempt too, before the next one.

## Helpers

Ship one control helper in `scripts/`, the single command every drive goes
through, plus any others the product needs. Each is executable, and the skill
body gives its exact invocation and what it prints.

## Use rules

The rules later work follows when it uses this skill:

- In the generated verification skill's use rules, require that the agent reproduce a reported interface bug itself, on the surface where it was seen, before any fix, handing that step to the person only when the surface needs something the agent cannot reach, such as their account or device, and saying which; the generator's own one-feature proof run needs no bug.
- In the generated verification skill's use rules, require that every change shipping behaviour on the surface it drives be exercised through that surface before it is called done.
- In the generated verification skill's use rules, require that before acting the agent confirm by stable markers suited to the driven surface that the target is the checked instance, workspace, account and data rather than a look-alike or production instance, and that the feature is in the expected state; when it drives a window, require it also to confirm by those markers, not window order or title, that the window belongs to that target.
- In the generated verification skill's use rules, require that before calling the environment a block the agent restate the defect without platform names and try a labelled stand-in that tests the same behaviour, treating hardware, permissions, device-only behaviour and account states as real blocks.
- In the generated verification skill's use rules, require that before any run relies on the driving tool, a harmless run of one mapped feature prove that it starts the app, drives that feature through real input, inspects without changing state, captures the evidence its surface allows and cleans up; require that the tool support every mapped feature through those capabilities, and that a missing capability be reported as incomplete and stop any work that needs it.
- In the generated verification skill's use rules and feature-map reference, require driving the app only through the feature map, kept where a refresh does not overwrite it, with each feature's entry giving its reset, the states that apply and its preconditions, and stopping to say so when the entry a run needs is missing rather than guessing the route.

A missing capability stops only the work that needs it: a command-line product
is not blocked for lacking a screen recorder.

## How other units recognise it

By content, not name: a `SKILL.md` with Launch, Doctor, Drive, Evidence and
Cleanup sections, beside a `features/README.md` index. maintain-verification-skill
and the setup and help units search every skills folder the project's hosts
read for that shape.
