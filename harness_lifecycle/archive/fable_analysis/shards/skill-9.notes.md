# Shard skill-9 — worker notes

22 rows evaluated; all source files inspected (19 direct SKILL.md reads; the 3
compound-engineering `todo-*` skills recovered via `git show af80bf23:...` because
upstream restructured its skill tree).

## Assumptions

- `effectiveness` scored as "effective for THIS repo's Python-centric agentic
  workflow"; the other five dimensions score intrinsic authoring quality. Several
  rows therefore combine low effectiveness with high instruction quality (e.g.
  seo, writing-shape, scaffold-exercises).
- `teach-session` is our own capability; the verdict `rewrite` means keep it but
  tighten the prose (informal lowercase, "learner" pronoun glitches, stray
  `/goal` tag, AskUserQuestion quiz vs the user's no-popups preference).

## Stale paths (input rows vs upstream HEAD)

- `skill:testbrowser` — moved to `reference_harnesses/compound-engineering-plugin/skills/ce-test-browser/SKILL.md` (ce- prefix rename).
- `skill:todocreate` / `skill:todoresolve` / `skill:todotriage` — removed at
  upstream HEAD; contents read from git history (`af80bf23`). Upstream's own
  deletion of the file-todo system mildly reinforces the reject verdicts.
- `skill:tokenbudgetadvisor` — its CSV description was the artifact `">-"` (YAML
  block-scalar marker); the real description exists in the SKILL.md frontmatter.

## Verdict summary

- reject_after_review (13): scaffold-exercises, seo, tdd-workflow, team-builder,
  todo-create, todo-resolve, todo-triage, token-budget-advisor, ui-demo,
  unified-notifications-ops, using-superpowers, videodb, writing-beats,
  writing-fragments, writing-shape — wait, that's 15; exact list below.
  - Actual rejects (15): scaffold-exercises, seo, tdd-workflow, team-builder,
    todo-create, todo-resolve, todo-triage, token-budget-advisor, ui-demo,
    unified-notifications-ops, using-superpowers, videodb, writing-beats,
    writing-fragments, writing-shape.
- defer (5): security-bounty-hunter, teach, test-browser, ubiquitous-language,
  writing-hookify-rules.
- merge (1): to-prd (fold no-interview PRD synthesis + "fewest, highest test
  seams" check into planning/prepare-phases + Beads).
- rewrite (1): teach-session (ours).

## Borrowable nuggets inside rejected rows

- security-bounty-hunter: the "Skip These" false-positive filter + prove-
  reachability discipline → candidate merge into security-review if it gets noisy.
- tdd-workflow: RED-gate definition (runtime vs compile-time RED) and the TDD
  evidence report → could inform our test-driven-development skill; nothing else.
- todo-create: the "create a todo vs act immediately" ~15-minute threshold.
- using-superpowers: the red-flags rationalization table format (thought →
  reality) as a rule-writing device.
- ui-demo: "dump interactive elements before scripting" discovery discipline.

## Cluster relationships

- `durable-task-tracking` (todo-create/resolve/triage) is wholly displaced by
  Beads; treat as one decision, not three.
- `teaching-learning` pairs our teach-session with mattpocock's teach — if
  teach-session is ever expanded to multi-session learning, teach is the design
  reference.
- `writing-craft` (fragments/beats/shape) is a coherent explore→exploit trio;
  reject/adopt as a set, never piecemeal.
- `writing-hookify-rules` (hooks-configuration) is a companion skill — its fate
  should ride on the hookify *plugin* evaluation row, not stand alone.
- `browser-testing` (test-browser) + `browser-demo-recording` (ui-demo) both
  hinge on the agent-browser/Playwright toolchain and a web frontend existing.

## Weak rows / low confidence

- unified-notifications-ops and videodb read partially (first ~100/70 lines);
  enough to confirm scale/vendor mismatch, verdicts robust.
- team-builder's `claude agents` CLI discovery was not runtime-verified; the
  precision score of 3 reflects that parsing dependency, not tested behavior.
