# Council: lifecycle stage and sub-stage names (2026-10-06)

Four members reviewed a proposed list of ADLC stages and sub-stages and each
returned their own list. A judge consolidated the answers. The adopted
terminology is in `../../GUIDE.md` §1. The user made one change to the judge's
list: stage 3 "Construction" is renamed **Building**.

| File | Role | Model and effort |
|---|---|---|
| `brief.md` | Common brief: proposed list, naming rules, report format | — |
| `opus-5.5-high.md` | Member B | claude-opus-5-5, high |
| `fable-5.1-high.md` | Member D | claude-fable-5-1, high |
| `gpt-6.1-sol-high.md` | Member C | gpt-6.1-sol, high |
| `gpt-6-astra-high.md` | Member A | gpt-6-astra, high |
| `judge-brief.md` | Judge instructions; the four reports followed as Members A–D | — |
| `judge-opus-5.5-high.md` | Consolidation | claude-opus-5-5, high, no tools |

Model identities come from the runtime: `modelUsage` for Claude runs and the
Codex session header for GPT runs.

**Anonymization.** The judge saw only the labels A–D, in a shuffled order. The
member texts contained no model names, and the judge ran without tools, so it
could not read the attributed files.

**Known bias.** The judge and member B are the same model. In most disputes
the judge sided with B. Anonymization hides names, not writing style.

**Unverified by the judge.** The judge had no file access. The claim that
`GUIDE.md` gates merging (A-07) was checked afterwards: it is true.

**Later renames by the user.** Roadmapping became **Charting**, because the
repo already defines "Roadmap" as a workstream's phased plan. Closeout became
**Closure**, because "session closeout" already names the end-of-session
protocol.
