---- MODULE Temporals ----
\* Temporal properties TLC refuses as invariants: a [] under a LET and an
\* operator whose body is temporal.
EXTENDS Naturals
VARIABLE x
Init == x = 0
Next == x' = 1 - x
Spec == Init /\ [][Next]_x /\ WF_x(Next)
Binary == [](x \in {0, 1})
LetBox == LET Inner == x \in {0, 1} IN []Inner
ViaOp == Binary
====
