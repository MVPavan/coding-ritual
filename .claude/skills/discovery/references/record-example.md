# Discovery record

**Question:** How should this team keep past discovery decisions findable?
**Area:** general
**Topic:** decision-records
**Date:** 2026-11-11
**Run:** example-session-0001
**Caller:** user request
**Outcome:** One record per run under docs/discovery, with a generated index; research reports stay unindexed for now.

| # | Question | Answer | Source | Confidence | Status |
|---|---|---|---|---|---|
| 1 | Can the index be generated instead of kept by hand? | Yes: `--index <root>` rewrites `<root>/INDEX.md` from every record under it. | code: scripts/check_record.py:7 | high | established |
| 2 | Name the record file by date and slug? | Yes, `<YYYY-MM-DD>-<slug>.md`, as the template's Date field already requires. | agent: routine, matches templates/record.md | | routine |
| 3 | Where do records live by default? | `docs/discovery/<area>/<topic>/` | owner: "Keep them under docs/discovery, by area and topic." (2026-11-10) | | decided |
| 4 | Index research reports too? | Not yet: they share no header to index; revisit when new-format reports are common. | agent: no common header to read | | proposed |
| 5 | Who prunes records that later code changes make stale? | | | | open |

Illustrative only: the owner's words in row 3 are invented for the example. Rows cite this
skill's own files, so check it with `scripts/check_record.py references/record-example.md
--root .` from the skill's folder.
