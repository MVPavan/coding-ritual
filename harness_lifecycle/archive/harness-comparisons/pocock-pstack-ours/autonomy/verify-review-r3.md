Round-2 findings

1. ADDRESSED — §5, index.html:1390,1455. “Combine parallel work” is now both +P. Pstack’s arena picks a base and grafts useful parts of other candidates (arena/SKILL.md:24-33,53-57). I counted all 83 chips and table rows: 28 pstack-only, 29 ours-only, 23 both, 3 Pocock-only. The author’s arithmetic is correct; my round-2 tally recommendation was wrong.

2. ADDRESSED — introduction and footer, index.html:116,1562. They now allow inline primary-source citations, and the relevant claims are present in the corrected data files, including ours.md:279,286,310,318 and pstack.md:31,394,440.

3. ADDRESSED — §6 L9, index.html:1532. The ADR requirement now applies to a changed ship-authority model, not to scheduling existing human reviews together. This matches workflow-coordination.md:36 and workflow-interpreter.md:1058-1095.

4. ADDRESSED — §2c, index.html:780,817. The TDD seam rule now cites tdd/SKILL.md:22, the correct line.

I checked 10 corrected data claims against primary sources: pstack’s bot inputs, verifier-family scope, landing modes and arena graft; Pocock’s TDD seam rule and implement-spec flow; ours’ red-test evidence, debrief scope, monitor delivery and signed ship gate. I also checked nine shifted ours.md citations, including index.html:1189,1447,1464-1467,1479,1527,1532-1533; they point to the intended current lines.

New breakage

MINOR — §4 P16 and §5 debrief row, index.html:1356,1473; data/ours.md:286. The claim that the basic graph has no debrief cites workflows/basic.toml:1-28, but that range does not cover the graph’s remaining nodes. The claim is true on inspection of the full file. Fix: cite workflows/basic.toml:1-83.

Verdict: APPROVE.