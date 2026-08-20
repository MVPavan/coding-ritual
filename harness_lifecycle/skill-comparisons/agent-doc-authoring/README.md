# Agent-Doc Authoring

Capability family: **agent-doc-authoring** — surfaces that write or rewrite
documents an agent consumes (CLAUDE.md / AGENTS.md, skills, rules, references).
Compared here: humanlayer's `improve-claude-md` against our
`authoring-for-agents`. The two upstream ancestors of ours
(superpowers `writing-skills`, mattpocock `writing-for-agents`) are already
ledgered as adopted-merged into `authoring-for-agents` (ledger 2026-08-12) and
are not re-read here; extend this folder if that set is ever reopened.

Upstream pin: `reference_harnesses/humanlayer_skills` @ `3c26291`.

## Level 1 — Placement

| Skill | Repo | Bucket | Triggers when |
|---|---|---|---|
| `improve-claude-md` | humanlayer | 11 Harness Routing & Agent-System Authoring | "When the user provides a CLAUDE.md file (or asks you to improve one)" (`SKILL.md:6`). Description (`SKILL.md:3`) names the mechanism (`<important if>` blocks), not the trigger — it would fire on "improve my CLAUDE.md" but not on "my agent keeps ignoring CLAUDE.md", which is the failure it actually addresses. Narrow: one file type, one transformation. |
| `authoring-for-agents` | ours | 11 (also 13) | "Creating or editing a document an agent consumes — a SKILL.md, AGENTS.md, CLAUDE.md, a rule or command file, or reference material" (`SKILL.md:3`). Broad: any agent-consumed doc; routes by failure type and surface (`SKILL.md:24-52`). |

Ledger: no entry for `improve-claude-md`. Relevant prior rulings: `writing-skills`
→ adopted-merged into `authoring-for-agents` (kept: match-form-to-failure,
description-never-summarises, rationalization tables, proportional testing;
rejected: Iron Law, docs cache, persuasion essay); `harness_learnings/harness-patterns-by-capability.md:7, 12-13`
(short root instruction file; trigger-style descriptions and progressive
disclosure; root shared guidance + subtree files near the code).

## Level 2 — Capability profiles

### `improve-claude-md` (humanlayer)

**Achieves** — a CLAUDE.md rewritten so each instruction carries an explicit
relevance condition, on the premise that Claude Code's own "may or may not be
relevant" wrapper makes the model discount un-scoped content.

**Can do**
- States the failure it fixes and cites the host's system-reminder text
  verbatim (`SKILL.md:8-14`). (Verified: the wrapper text quoted at
  `SKILL.md:12` is what Claude Code injects around CLAUDE.md content.)
- Mechanism: `<important if="condition">` XML blocks around conditionally
  relevant sections (`SKILL.md:16-18`).
- Five principles: foundational context bare / domain guidance wrapped with a
  90 % rule of thumb (`SKILL.md:22-28`); narrow conditions with bad/good
  examples (`:30-55`); keep it inline, shard only when verbose (`:57-63`);
  less is more — cut linter territory, discoverable patterns, code snippets
  (`:65-70`); keep all commands (`:72-74`).
- A fixed output structure (`SKILL.md:76-109`) and a nine-step procedure
  (`:111-123`).
- A full before/after worked example with "what was removed and why"
  (`SKILL.md:125-258`).

**Pros (vs ours)**
- Names a concrete, verifiable host behaviour and designs against it; ours
  reasons from pointer/attention principles without citing the wrapper.
- Gives a *conditional-loading mechanism that needs no file split*: the
  condition travels with the content. Our harness's only conditional
  mechanisms are the pointer (skill description, docs-index row) and the
  separate file behind it (`authoring-for-agents/references/writing-principles.md:7-20, 48-52`);
  Claude Code's path-scoped rules (`paths:` frontmatter) exist but no rule in
  `.claude/rules/` uses them. Their idea covers the middle ground — content
  that is too small to shard but not relevant to 90 % of tasks.
- "Delete linter territory / discoverable patterns / code snippets" is the
  same pruning our writing-principles prescribe (`writing-principles.md:131-145`),
  stated as an executable checklist with an example — lower freedom, which is
  right for a mechanical rewrite.

**Cons (vs ours)**
- The central claim — that `<important if>` tags measurably improve adherence
  — is asserted, not evidenced (`SKILL.md:18` "exploits the same XML tag
  pattern"). No baseline, no test. Our Verify ladder would demand a
  packaging/baseline test before shipping such a rule
  (`authoring-for-agents/SKILL.md:77-91`).
- Host-specific: the premise is Claude Code's wrapper; Codex reads AGENTS.md
  without it. Our harness ships one `CLAUDE.md`/`AGENTS.md` pair for both
  hosts; a tag dialect one host may ignore is a neutrality cost.
- "Keep it inline, avoid sharding" (`SKILL.md:57-63`) conflicts with our
  read-order architecture (lean root + `.claude/project/` overlay + rules +
  skills): our CLAUDE.md is a pointer file by design (`CLAUDE.md` header:
  "every line here costs context. Detail lives in the pointed-to docs").
  Adopting their output structure wholesale would reverse a settled decision.
- One transformation only; no failure-naming step for *other* doc types, no
  surface selection, no verification.
- Description names the mechanism, not the trigger (`SKILL.md:3`), so it
  would under-fire on the symptom the user actually reports.

### `authoring-for-agents` (ours)

**Achieves** — any agent-consumed document written or edited so it changes
behaviour predictably, with the form matched to the failure and the surface
matched to the moment.

**Can do**
- Name-the-failure gate; no failure → no document (`SKILL.md:13-22`).
- Match-the-form-to-the-failure table (`SKILL.md:24-37`).
- Pick-the-surface table: rule / CLAUDE.md / overlay / skill / command /
  reference / hook (`SKILL.md:39-52`).
- Write-by-branch with three references and four inline rules
  (`SKILL.md:54-75`).
- Proportional Verify ladder (`SKILL.md:77-91`); catalog-first and
  discoverability rules (`SKILL.md:93-102`).
- Writing principles: context pointers, the two loads, information hierarchy
  and progressive disclosure, completion criteria, degrees of freedom,
  leading words, negation, pruning (`references/writing-principles.md`).

**Pros** — covers the whole space, has a verification bar, and its surface
table already encodes where CLAUDE.md content should *go* instead of how to
tag it in place. **Cons** — high freedom for a CLAUDE.md rewrite (no
checklist, no worked example), and silent on in-file conditional scoping: an
agent following ours would split or prune, never scope in place.

### Verdict

Not substitutes. `improve-claude-md` is a narrow **recipe**; ours is the
**discipline**. The genuine overlap is the pruning checklist (both say cut
linter territory, discoverable patterns, stale snippets, no-ops). The genuinely
new component is **in-place conditional scoping** (`<important if>`), which
fills a hole in our surface table (between "inline" and "behind a pointer") —
but its effect is unmeasured and Claude-specific. Strongest for a one-shot
CLAUDE.md cleanup in a Claude-only repo: theirs. Strongest for everything
else, including deciding whether a CLAUDE.md should hold the content at all:
ours.

Routing recommendation (for `harness-evaluate`): **defer** — record the
conditional-scoping idea as a candidate *row* in the surface table of
`authoring-for-agents` ("content too small to shard, relevant to a minority of
tasks → scope in place"), to be added only after a packaging/baseline test on
this repo's CLAUDE.md shows a measurable difference and after checking Codex
does not choke on the tags. Do not import the output structure or the
inline-everything principle.
