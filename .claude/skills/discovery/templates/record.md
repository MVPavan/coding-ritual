# Discovery record

**Question:** <the question this run settles>
**Area:** <area>
**Topic:** <topic>
**Date:** <YYYY-MM-DD>
**Run:** <run id>
**Caller:** <caller>
**Outcome:** <outcome>

| # | Question | Answer | Source | Confidence | Status |
|---|---|---|---|---|---|
| 1 | <question> | <answer> | <source> | <confidence> | <status> |

<!--
Fill every angle-bracket field; one row per open question; write `\|` for a pipe in a cell.
Run: fresh per run, `<session id>-<nonce>`; write to what `scripts/check_record.py --next
<path> --run <id>` prints. Add `**Revises:** <authority>` under Outcome only when the owner
or the caller named this path to revise.
Status and Source:
  established  code: <path>:<line>  |  outside: <source>, <version>, <date>  |  prototype: <report path>
               Confidence high, medium or low (how far the citation settles it)
  decided      owner: "<quote>" (YYYY-MM-DD)  |  owner: delegation <ref>
  routine      agent: routine, <basis>
  proposed     agent: <basis>, with the recommendation as the answer
  open         answer and source may be empty
Confidence stays empty on every row that is not established.
Then run `scripts/check_record.py <file>` and `scripts/check_record.py --index docs/discovery`.
-->
