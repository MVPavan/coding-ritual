# Agent-Doc Authoring — Level 3 Components

| Key | Surface |
|---|---|
| `ICM` | humanlayer — `plugins/improve-claude-md/skills/improve-claude-md/SKILL.md` (258 lines, no references) |
| `AFA` | ours — `.claude/skills/authoring-for-agents/` (SKILL.md + `references/writing-principles.md`, `skill-anatomy.md`, `testing-docs.md`) |

## Component inventory

### `ICM` — improve-claude-md (humanlayer)

| Component | Citation |
|---|---|
| Failure statement grounded in the host's CLAUDE.md wrapper text | `SKILL.md:8-14` |
| `<important if="condition">` in-place conditional scoping | `SKILL.md:16-18` |
| Bare-vs-wrapped rule with 90 % threshold (identity, map, stack stay bare) | `SKILL.md:22-28` |
| Narrow-condition rule with bad/good examples; never group unrelated rules under one broad condition | `SKILL.md:30-55, 119` |
| Inline over sharding unless verbose | `SKILL.md:57-63` |
| Pruning checklist: linter-enforceable, discoverable-from-code, code snippets → path references, vague "best practices" | `SKILL.md:65-70, 121-123` |
| Keep-all-commands invariant, commands in one block | `SKILL.md:72-74, 118` |
| Fixed output structure | `SKILL.md:76-109` |
| Nine-step rewrite procedure | `SKILL.md:111-123` |
| Worked before/after example with removal rationale | `SKILL.md:125-258` |

### `AFA` — authoring-for-agents (ours)

| Component | Citation |
|---|---|
| Name-the-failure gate; observed baseline required for discipline rules; no failure → no document | `SKILL.md:13-22` |
| Match-the-form-to-the-failure table; no nuance clauses | `SKILL.md:24-37` |
| Pick-the-surface table (rule / CLAUDE.md / overlay / skill / command / reference / hook) | `SKILL.md:39-52` |
| Route-by-branch reading of references | `SKILL.md:54-63` |
| Four inline rules: triggers-only description, positive target, one source of truth, every sentence changes behaviour | `SKILL.md:65-75` |
| Proportional Verify ladder with done-criterion | `SKILL.md:77-91` |
| Catalog-first; discoverability on own surface; match the host harness's conventions | `SKILL.md:93-102` |
| Context pointers — wording decides reach; pruning of pointers | `references/writing-principles.md:5-20` |
| The two loads (context vs cognitive) | `references/writing-principles.md:22-32` |
| Information hierarchy + progressive disclosure as a variance lever; co-location; sprawl | `references/writing-principles.md:34-62` |
| Completion criteria (clarity, demand) | `references/writing-principles.md:64-80` |
| Degrees of freedom | `references/writing-principles.md:82-95` |
| Leading words | `references/writing-principles.md:97-114` |
| Negation — state the target, prohibition only as guardrail | `references/writing-principles.md:116-127` |
| Pruning — single source of truth, environment as source of truth, relevance/sediment, no-ops test | `references/writing-principles.md:129-145` |
| Skill layout / frontmatter / invocation mechanics | `references/skill-anatomy.md` |
| Testing methods per rung | `references/testing-docs.md` |

## Cross-skill matrix

| Component | ICM | AFA |
|---|---|---|
| Names the failure the document fixes | ✓ (one fixed failure, host-cited) | ✓ (required per document) |
| In-place conditional scoping of content | ✓ | — |
| Conditional reach via pointer + separate file | ~ (discouraged unless verbose) | ✓ |
| Foundational-vs-conditional split | ✓ (90 % rule) | ~ (branch test: inline what every branch needs) |
| Narrow trigger conditions | ✓ | ~ (conditional keyed to observable predicate; for descriptions, front-loaded trigger) |
| Pruning: linter territory / discoverable / snippets / vague | ✓ | ✓ (environment-as-source-of-truth, no-ops, relevance) |
| Keep commands invariant | ✓ | ~ (CLAUDE.md holds "verification commands" per surface table) |
| Fixed output structure for CLAUDE.md | ✓ | — |
| Step-by-step rewrite procedure | ✓ | — |
| Worked example | ✓ | — |
| Surface selection (where should this content live) | — | ✓ |
| Form selection by failure type | — | ✓ |
| Verification ladder / baseline test | — | ✓ |
| Host-neutrality consideration | — | ✓ (match the harness you write into) |
| Description-states-triggers rule | — | ✓ |
| Negation / positive phrasing | — | ✓ |
| Degrees of freedom | — | ✓ |
| Leading words | — | ✓ |
| Completion criteria for steps | — | ✓ |
| Covers skills, rules, commands, references | — | ✓ |

## Shared-component differences

**Failure naming.** `ICM` names one failure for all users and grounds it in
the host wrapper (`SKILL.md:8-14`); `AFA` makes the author name the failure
per document and, for discipline rules, observe a baseline first
(`SKILL.md:13-22`). Stronger as a general method: AFA. Stronger as a
ready-to-run recipe: ICM — but its failure is asserted for the mechanism's
*fix* only, never demonstrated.

**Conditional relevance.** `ICM` scopes in place with a tag the content
carries (`SKILL.md:16-18`); `AFA` scopes by moving content behind a pointer
whose wording is the condition (`writing-principles.md:7-20, 48-52`). ICM's
mechanism has lower context-load *benefit* (the content is still loaded) but
lower *fragmentation* cost; AFA's removes the load entirely at the price of a
pointer line and a tool call. Which is stronger depends on the size of the
conditional content — AFA has no answer for the small-but-conditional case,
ICM has no answer for the large one. A complete method needs both rows.

**Pruning.** Same list, different form. `ICM` is an imperative checklist with
an example of each cut (`SKILL.md:65-70, 252-258`); `AFA` is the principle
("the environment is a source of truth", `writing-principles.md:134-137`; no-op
test `:142-145`). ICM's is stronger for a one-shot mechanical pass (low freedom
matches a mechanical task — by AFA's own degrees-of-freedom rule,
`writing-principles.md:87-89`); AFA's is stronger for deciding new cases.

**Sharding stance.** `ICM`: "do not shard … unless incredibly verbose"
(`SKILL.md:59`); `AFA`: disclose reference behind pointers, inline only what
every branch needs (`writing-principles.md:48-52`). Direct conflict. AFA's is
the settled position for this harness (lean root + overlay + rules); ICM's
would reverse it.
