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
Caller: `user request` | `<unit>, step <n>` | `delegated: <brief path>`, optional `(note)`.
Area and Topic classify the question, wherever the caller puts the file.
Run: fresh per run, `<session id>-<nonce>`; write to what `scripts/check_record.py --next
<path> --run <id>` prints. Add `**Revises:** <authority>` under Outcome only when the owner
or the caller named this path to revise.
Status and Source:
  established  code: <path>:<line>  |  outside: <source>, <version>, <date>  |  prototype: <report path>
               computed: <script path> -> <output path>  (a saved count, join or search)
               Confidence high, medium or low (how far the citation settles it)
  decided      owner: "<quote>" (YYYY-MM-DD)  |  owner: delegation <ref>
  routine      agent: routine, <basis>
  proposed     agent: <basis>, with the recommendation as the answer
  open         answer and source may be empty
Confidence stays empty on every row that is not established.
High only when the cited source shows the answer by itself. An answer put together from
several lines or a search that found nothing: medium or low, naming the rest and the inference.
A fact and a choice made on it go in separate rows; the choice stays proposed.
A computed answer names what it counts; compared counts cover one population. A consequence
of a proposed choice may be established, starting `If row <n> is chosen,`.
Then run `scripts/check_record.py <file>` and `scripts/check_record.py --index docs/discovery`.
-->
