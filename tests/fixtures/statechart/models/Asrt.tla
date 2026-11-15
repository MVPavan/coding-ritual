---- MODULE Asrt ----
EXTENDS Naturals, TLC
VARIABLE x
Init == x = 0
Next == x < 3 /\ Assert(x < 2, "x got too big") /\ x' = x + 1
====
