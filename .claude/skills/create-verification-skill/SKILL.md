---
name: create-verification-skill
description: "Use for /create-verification-skill when a project has no scripted way to drive its real app; updating an existing verify skill is maintain-verification-skill, and proving one change on its surface needs no new skill. Generates a project skill that launches the real app, drives a feature as a user would and keeps proof, with a starter feature map, then runs it once end to end."
disable-model-invocation: true
argument-hint: "Optional: the app or surface to cover (default: the primary surface found in the code)"
---

# Create Verification Skill

Writes a project skill, kept in the product's repository, that launches the real
product, drives a feature the way a user reaches it and keeps proof. Its reader
is a later agent, not you: it arrives cold, mid-task, knowing nothing this run
learned. The skill lands in the project's skills folder as `verify-<app>/`
(Claude Code: `.claude/skills/verify-<app>/`), beside a starter feature map.

**Scope.** First search every skills folder the project's hosts read (a project
can have one per host) for an existing verify skill, recognised by its shape
(`references/generated-skill.md`, "How other units recognise it"). If one
exists, or a feature map already exists, stop: keeping it current is
maintain-verification-skill, and a rerun here would overwrite the map.
This skill edits only the new skill folder and any scaffolding it labels; a fix
to product code needs the person's authority.

## 1. Study the project

Answer every setup question from the code, its docs and its config. Ask the
person only what none of them can show (a sign-in only they hold, which of two
equal surfaces matters more), and say why the code could not answer it.

- **Surfaces.** List every surface a user touches: web page, command line,
  terminal app, desktop window, API, mobile, library. Choose the primary one,
  or the one the argument names, and record the others as not covered.
- **Start command.** Prefer the project's own documented development command
  (README, `Makefile`, `package.json` scripts, compose files) over one you
  assemble.
- **Prerequisites.** Record what a local run needs: ports, environment
  variables, seed data, sign-in, services it calls.
- **Driver.** Use a driving harness the project already has (its end-to-end
  tests, expect scripts, HTTP fixtures); only when it has none, pick a generic
  recipe for the surface (browser control, a terminal multiplexer, plain HTTP).
  Installing a missing driving tool needs the person's approval first, and then
  goes per project or per user, never system-wide.
- **Evidence.** List the kinds of proof the product can give: screenshots,
  terminal transcripts, response bodies, logs, exit codes, stored state.
- **Isolation.** Find out whether two instances can run side by side, through
  separate ports, data folders or profiles, and record the answer in the
  generated skill; it decides whether a run may ever share an instance.

## 2. Working base

Before generating anything, make sure the checkout builds and starts. For a
command line, a harmless command answering (its help or version) counts as
starting; note any files it writes. A service the product needs starts in the
generated Launch, not here. Syncing the project's own dependencies is part of
the base and needs the person's approval when it was not already given. When
the checkout does not build or start, report the failure exactly: the command,
its output and the step that broke. Fix it only within the authority the person
gave; a broken base is not permission to repair their product.

A run may create an unrelated asset that blocks startup (an empty config file, a
placeholder certificate) only when it is labelled as verification scaffolding
and the generated cleanup removes it.

## 3. Write the skill

Write `verify-<app>/SKILL.md` by `references/generated-skill.md`: its
frontmatter and writing rules, then its fixed sections Launch, Doctor, Drive,
Evidence, Cleanup, Helpers and Use rules. Every command, path, port, route and
helper name is one you found in the code or ran. Write for an agent that meets
the project cold, in the middle of another task: lead each section with what to
run, not with background.

## 4. Seed the feature map

Write `verify-<app>/features/` by `references/feature-map.md`: an index, then
one file for each of the top three to five user-facing features, found in
routes, commands, menus or docs. `references/feature-map-example/` shows the
shape on a small product. The map defines what must be proven: a feature is
proven only through every entry point its file lists, and an entry point that
was skipped is never claimed through another route.

## 5. Prove it once

A generated skill nobody has run is a draft. Runs made while writing it are
development runs: clean each up and report it, but none is the proof. The proof
is a fresh run from step 1 once the text is final, made as its next reader
would, reading only what it says:

1. Launch from empty data, as the skill's Launch section says.
2. Run the doctor.
3. Drive one mapped feature through every entry point its file lists, capturing
   the evidence the skill names. One feature proven end to end is enough for
   the handover; the rest of the map is for later runs.
4. Clean up, then confirm every evidence file is still where the skill says it
   is. A missing one fails this step.

When a step fails, clean up before the next attempt too, so no process or port is
left stranded, then fix the skill (not the product) and rerun from step 1. When
the skill's check fails on the product itself, report the failure; never weaken
the journey, its check or its expected value to make it pass.

When the proof ran somewhere other than the real target (a stand-in database,
a fake service, a substitute account), list each setup step it did that the real
target will not get, and keep those steps marked unverified in the skill and the
reply.

## 6. Hand over

The generated skill and map stay uncommitted unless the person asks for a commit;
`land` makes it. Tell the person that keeping the skill current as the product
changes is maintain-verification-skill.

## Reply

- **Skill:** its path, the surface it covers and the surfaces it does not.
- **Map:** the features seeded, one line each.
- **Proof run:** the feature, each entry point driven, the evidence paths, and
  the doctor and cleanup results.
- **Unverified:** stand-in steps, surfaces not covered, questions still open.
- **Blocked or draft:** when the base or the proof run failed, the exact failure,
  and that the skill is a draft.
