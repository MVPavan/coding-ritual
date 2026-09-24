# Review of the shared skill audit

Date: 2026-09-10. Reviewed: [README.md](README.md) and [inventory.json](inventory.json)
in this folder, at working-tree state on branch `dws` (HEAD `4b53e6b`, uncommitted
instruction changes present). Review only: neither audit file nor any skill was edited.
Independent review by a different agent from the audit's author; no network access was
used, so external citations are marked unverified rather than checked.

## Verdict

**Accept with corrections.** The audit is source-grounded, its citations resolve, its
inventory arithmetic reproduces exactly, and its ten prioritized findings describe real
text in the skills. Two corrections are needed before it is used as a basis for changes:
finding 7 attributes a Codex-only plugin overlap to the shared library without naming the
harness, and the "not measured" limit on skill-use rates is wrong because local usage
counters exist and were not consulted. Everything else is minor.

## What was verified

| Check | Result |
|---|---|
| 33 `file:line` citations in the findings | 31 resolve to the quoted text; 2 are off by one (see MINOR 1) |
| `inventory.json` totals: 45 entries, 18 manual, 38,035 entrypoint words, 2,036 description words, 90 markdown files, 69,472 words | All reproduced with `jq` |
| Entrypoint SHA-256 and word count for `execution` | Match the working-tree file |
| `python3 .claude/scripts/skill-catalog.py --check` | Passes: 45 skills (27 model-invocable, 18 slash-only), 69 slash refs, 62 path refs, 45 sidecars |
| Codex exposure | `.codex/skills` holds 39 links; the six unlinked are exactly `harness-evaluate`, `harness-publish`, `harness-scan`, `harness-skill-compare`, `harness-status`, `show-me`. The 25/14 automatic/manual split follows (two of the six are model-invocable) |
| `.codex/README.md:5-8` | Excludes `harness-*` and `in-progress/` by design; `show-me` is indeed unexplained there |
| `git submodule status -- mvp-harness` | Uninitialized (`-196a3cee…`), as stated |
| Bead `cr-ygw` | Exists, closed, close reason matches the report's limits section |
| Relative links to `.claude/skills/*` and `prompting-guides/articles/eric-provencher.txt` | Resolve |
| Memory-policy contradiction (finding 9) | Confirmed: `beads/SKILL.md:47` and `.beads/beads.md:13` say `MEMORY.md`; the injected `bd prime` hook says the opposite |
| Review-surface claim (finding 10) | Confirmed: `code-review/SKILL.md:45` falls back to `git diff BASE..HEAD`, a commit range; `task-engine.md:191` packages without path arguments |
| Routing claims (findings 1 to 6) | Confirmed at `execution/SKILL.md:118-120`, `task-engine.md:186-196`, `:133`, `:176`, `verification-before-completion/SKILL.md:8`, `:29`, `brainstorming/SKILL.md:12`, `:31`, `research/SKILL.md:18`, `systematic-debugging/SKILL.md:10`, `:126`, `performance-optimization/SKILL.md:30` |

Not re-derived: the child-call arithmetic in finding 1 (2 / 3 / 5 / up to 17). The quoted
lines support the shape of the argument; the exact counts were not recomputed.

## Findings

### MAJOR 1. Finding 7 describes a Codex-only overlap as if it affected the shared library

`README.md:62` and `README.md:196-218`. The "installed `matt-skills-curated` package" is a
Codex plugin at `~/.codex/plugins/cache/openai-curated-remote/matt-skills-curated/1.1.0`
(42 `SKILL.md` files; the 13 exact name overlaps reproduce). No Matt Pocock plugin is
installed or enabled in Claude Code (`~/.claude/plugins/installed_plugins.json` has no
such entry, and the mattpocock-skills plugin is not in `enabledPlugins`). The semantic
competition the audit describes is therefore real for Codex sessions and absent for Claude
Code sessions in this repo.

Why it matters: the recommendation "disable overlapping plugin exposure for this workflow"
must target Codex plugin configuration, and the per-skill notes that cite plugin
counterparts (`code-review`, `systematic-debugging` vs `diagnosing-bugs`,
`test-driven-development` vs `tdd`) should say they apply to one harness. Fix: name the
harness in the "What is actually loaded" table row and in finding 7.

### MAJOR 2. Skill-use rates are available locally and were not used

`README.md:35` lists "historical skill-use rates" as not measured. Claude Code records
lifetime dispatch counts per skill in `~/.claude.json` (`skillUsage`, written on Skill-tool
or slash dispatch), and session transcripts under `~/.claude/projects/` record every
`Skill` tool call. Read on 2026-09-09 for the doctor report in the sibling folder, the
counters for this library's names are:

| Skill | Lifetime dispatches (Claude Code, all projects) | Last used |
|---|---|---|
| run-phases | 23 | 2026-07-07 |
| phase-execution | 15 | 2026-07-07 |
| i-have-adhd | 11 | 2026-09-03 |
| show-me | 11 | 2026-09-07 |
| html-artifact | 8 | 2026-08-03 |
| brainstorming | 4 | 2026-04-14 |
| planning | 4 | 2026-04-14 |
| model-council | 4 | 2026-08-24 |
| design-evolve | 2 | 2026-04-07 |
| grill-me | 2 | 2026-06-01 |
| teach-session | 2 | 2026-07-03 |
| authoring-for-agents, codebase-research, cost-estimate, document-review, harness-skill-compare, systematic-debugging | 1 each | 2026-04 to 2026-08 |
| All other 28 top-level skills | 0 | never via Skill tool or slash |

Never dispatched this way: `execution`, `code-review`, `receiving-code-review`,
`verification-before-completion`, `research`, `security`, `test-driven-development`,
`grilling`, `grill-with-docs`, `idea-refine`, `perspective-council`, `prototype`,
`wayfinder`, `beads`, `codebase-design`, `domain-modeling`, `performance-optimization`,
`resolving-merge-conflicts`, `skill-router`, `triage`, `teach`, `check-invariants`,
`improve-codebase-architecture`, `migrate-claude-to-codex`, and the five `harness-*` skills.

Caveats the audit should carry if it adopts these numbers: the counter records
Skill-tool and slash dispatch only, so a skill a subagent reads by file path inside the
execution engine (the normal route for `code-review`) is invisible to it; the counter is
global across every project on this machine, including the `coding-ritual` repo this one
descends from; and it says nothing about Codex sessions. Even so, it is direct evidence,
not inference. It supports the audit's two retire candidates (`cost-estimate` has one
lifetime use; `verification-before-completion` has none) and it weakens the "keep" case for
several automatic skills whose only recorded value is their description in the listing.
In the last 50 sessions (2026-09-02 to 2026-09-09) the only library skills dispatched were
`model-council` (5), `i-have-adhd` (3), `show-me` (3), `authoring-for-agents` (2),
`harness-skill-compare` (1), `teach-session` (1), and `codebase-research` (3 via slash).

### MINOR 1. Two citations are off by one line

- `README.md:113` cites `receiving-code-review/SKILL.md:15`; that line is blank. The
  fix-loop exception is at `:16-17`.
- `README.md:160` cites `research/SKILL.md:47` for source-count ranges; that line is the
  table separator. The ranges are at `:48-49`.

### MINOR 2. Finding 3's retire recommendation does not enumerate the callers it says to update

`README.md:134-138` and the disposition row at `README.md:315` say "update all callers
before removal" without listing them. They are: `execution/SKILL.md:120`,
`systematic-debugging/SKILL.md`, `performance-optimization/SKILL.md`,
`skill-router/SKILL.md`, and `authoring-for-agents/references/skill-anatomy.md`. The
catalog check would catch a dangling slash reference but not a prose mention, so the
list belongs in the report.

### MINOR 3. The memory-policy conflict is deliberate, and the audit reads it as drift

`README.md:264-268`. `beads/SKILL.md:47` does not merely differ from the `bd prime` hook;
it says to ignore the hook's memory guidance. The repo chose `MEMORY.md` over
`bd remember` on purpose. "Align both" is the wrong remedy. The choice is either to keep
the explicit override (and say so once, where agents will see it) or to change the
decision. The audit should present it as a decision to confirm, not an inconsistency to
smooth over. Its separate point stands: neither wording should imply automatic memory
writes, since `AGENTS.md` requires an explicit request.

### MINOR 4. External citations are unverified and one URL looks unusual

`README.md:67` cites `learn.chatgpt.com/docs/build-skills` for OpenAI skill
documentation; OpenAI's developer documentation normally lives under
`developers.openai.com`, which the sibling prompting-guides README uses. `README.md:74`
cites a `code.claude.com` anchor for the persistence-across-turns claim. Neither was
fetched for this review. The author should re-check both URLs and quote or paraphrase the
specific sentence relied on, since finding 7's "accidental loading is consequential"
argument leans on the second one.

### MINOR 5. Description measurement differs slightly from a direct read

`README.md:61` gives the `html-artifact` description as 992 characters; a direct read of
the frontmatter value gives 995. Immaterial to the finding.

## Assessment of the recommendations

- **Findings 1 to 3 are the audit's strongest and are correct on the text.** The
  execution skill explicitly routes inline-built work into a two-reviewer final review
  (`execution/SKILL.md:118-120`, `task-engine.md:186-196`), the fix loop defers
  adjudication to the cap by design (`task-engine.md:176`), and the verification skill
  ties evidence to the message rather than to changed state. These are the places where
  the library generates work the new `AGENTS.md` does not ask for.
- **Finding 4 is fair but understated in one respect.** `brainstorming/SKILL.md:31` has
  the small-explicit exit, yet the three grounding reads at `:12` precede it, so the exit
  is reached only after the cost it is meant to avoid. The audit says this; it could say
  plainly that the order of those two lines is the fix.
- **Findings 5 and 6 are judgment calls the audit argues well,** with the caveat the
  audit itself raises at `README.md:477-481`: some rigid rules encode past failures. The
  usage data above suggests these skills are rarely dispatched, which lowers the cost of
  testing trims on them first.
- **Finding 8 is correct and useful.** The `show-me` omission has no recorded reason.
- **Finding 10 is correct on git semantics** and fairly scoped: the engine always
  supplies a working-tree package, so the commit-range fallback bites only ad-hoc reviews.
- **The per-skill disposition tables are consistent with the summary** (2 retire, 5
  merge, the rest keep with trims). The candidate shorter descriptions at
  `README.md:413-423` are a good start; they should be evaluated with the routing cases
  at `README.md:381-402` as the audit proposes, not adopted on inspection.
- **Process limit, acknowledged by the audit:** this is a single-agent analysis whose
  planned independent review did not run. This document is that independent pass for the
  text; it is still not a behavioral evaluation.

## Recommended edits to the audit (not applied)

1. Name the harness in `README.md:62` and finding 7; retarget the plugin remedy at Codex
   plugin configuration.
2. Replace the "not measured" line at `README.md:35` with the usage table above and its
   caveats, or cite the sibling doctor report.
3. Correct the two line references in MINOR 1.
4. Add the five callers to finding 3 and the `verification-before-completion` row.
5. Reframe the memory-policy item as a decision to confirm.
6. Re-verify the two external URLs.
