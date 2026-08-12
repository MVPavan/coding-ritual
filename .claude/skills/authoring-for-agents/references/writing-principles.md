# Writing principles

What makes any agent-consumed document bind behaviour, whatever its
packaging.

## Context pointers

A pointer is a line held in context that names out-of-context material and the
condition for reaching it — a skill description, a docs-index row, an
AGENTS.md read-order line. The pointer's *wording*, not its target, decides
whether the material is ever reached. A must-read doc behind a weak pointer is
a variance bug: sharpen the wording first; inline the material only if
sharpening fails.

A pointer costs its tokens on every turn, so it earns harder pruning than the
body it guards:

- Front-load the trigger word — that is where it does its work.
- One trigger per distinct branch. Synonyms renaming the same branch are one
  branch written twice; collapse them.
- Cut identity the body already carries.

## The two loads

Every document and pointer spends one of two budgets:

- **Context load** — always-loaded material (an AGENTS.md line, a skill
  description) costing tokens and attention every turn, whether or not it fires.
- **Cognitive load** — the human remembering what exists and when to reach for
  it. Not a cost to minimise to zero: it is the price of human agency. Spend it
  where human judgement matters; remove it where it does not.

Material behind a pointer escapes context load for the price of the pointer's
own line. Material with no pointer at all rides entirely on the human's memory.

## Information hierarchy

A document mixes two content types — **steps** (ordered actions the agent
performs) and **reference** (rules and facts consulted on demand) — across
three tiers, ranked by how immediately the agent needs the material:

1. **In-file step** — what the agent does, in order. The primary tier.
2. **In-file reference** — consulted on demand; a flat peer-set of rules is a
   fine arrangement, not a smell.
3. **Disclosed reference** — a separate file behind a pointer, loaded only
   when the pointer fires.

**Progressive disclosure** is the move down the ladder. It is not primarily a
token optimisation: reference sitting on top of steps buries them and turns
attending to them into a coin flip — a variance lever, not just a legibility
one. The branch test decides: inline what every branch needs; push behind a
pointer what only some branches reach.

**Co-location** decides what sits beside a piece once its tier is chosen: keep
a concept's definition, rules, and caveats under one heading. Scattering
fragments one meaning across many places (distinct from duplication, which
repeats it).

**Sprawl** is the failure mode even when every line is live: attention thins
across the excess, and every extra line is one more to keep current. The cure
is the ladder — disclose reference, and split by branch or sequence so each
path carries only what it needs.

## Completion criteria

Every step ends on the condition that tells the agent the work is done. Two
levers:

- **Clarity** — can the agent tell done from not-done? A fuzzy bound
  ("understanding reached") invites finishing early, pulled forward by the
  visible steps still ahead. Sharpen the bound first — it is local and cheap.
  Split the sequence across a real context boundary (a hand-off, a subagent
  dispatch) only when the bound is irreducibly fuzzy *and* you observe the
  rush; an inline split clears nothing.
- **Demand** — how much the criterion requires. "Every modified module
  accounted for" forces digging that "produce a change list" does not. Demand
  binds flat reference too: "every rule applied" is an exhaustiveness bar with
  no steps at all.

The strongest criteria are both checkable and exhaustive.

## Degrees of freedom

Independent of form: how prescriptive should the document be? Match the
tightness to the task's fragility, not to how much you happen to know:

- **Low freedom** — a fragile or deterministic operation where one wrong step
  breaks things: exact steps, exact commands, or a script the agent runs
  rather than prose it interprets.
- **High freedom** — a judgment call whose right answer depends on context:
  principles and heuristics, not steps. A recipe here forces wrong moves and
  teaches the agent to ignore the document.

Most documents mix both; the smell is a mismatch — pseudo-precision wrapped
around a judgment call, or vague advice guarding a fragile sequence.

## Leading words

A leading word is a compact concept already in the model's pretraining that
the agent thinks with while running the document — *tracer bullet*,
*characterization test*, *sediment*. Repeated as a token, never as a sentence,
it anchors a region of behaviour in almost no tokens by recruiting priors the
model already holds.

It anchors twice: in a body, execution — the agent reaches for the same
behaviour wherever the word appears; in a pointer, invocation — when the same
word lives in your prompts and your docs, the agent links them and reaches the
material more reliably.

Prefer existing words: a coined term recruits no priors and costs its whole
definition. Hunt for restatements begging to collapse — "fast, deterministic,
low-overhead" is one word (*tight*). A word too weak to beat the default
("be thorough" to an already thorough-ish agent) is a no-op; the fix is a
stronger word, not more words.

## Negation

Steering by prohibition drags the forbidden behaviour into context and makes
it *more* available — the ban half-reads as an instruction to do the thing.
State the target behaviour instead: "write one-line comments", not "don't
write long comments". A prohibition earns its place only as a hard guardrail
with no positive phrasing, paired with the positive target so attention lands
on what to do.

(A discipline rule the agent knows and skips under pressure is a different
failure than shaping: there, the explicit prohibition plus its rationalization
counters is the right form.)

## Pruning

- **Single source of truth** — one authoritative place per meaning, so a
  behaviour change is a one-place edit. Duplication costs maintenance and
  inflates a meaning's apparent rank on the ladder.
- **The environment is a source of truth** — package scripts, configs,
  `--help` output, the directory layout. A document restating them is a cache
  that goes stale. Cache only what no lookup answers: the unwritten
  convention, the reason behind a choice, the gotcha no config confesses.
- **Relevance** — a line loses it by never bearing on the task, or by going
  stale as the world changes. Without a pruning discipline the default fate is
  *sediment*: stale layers that settle because adding feels safe and removing
  feels risky.
- **No-ops** — an instruction the model already obeys by default pays load to
  say nothing. The test — does it change behaviour versus the default? — is
  model-relative: two people disagreeing about a no-op disagree about the
  default, and settle it by running the document, not by debate.
