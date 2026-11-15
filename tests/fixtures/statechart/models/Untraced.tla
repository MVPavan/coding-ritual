---- MODULE Untraced ----
\* Low breaks at x = 1 from y = 0, then at x = 2 from the start y = 1. TLC
\* rebuilds a path by evaluating Init again, when TLCGet("distinct") is no
\* longer 0, so it cannot find the start y = 1: it names that break and
\* prints no path to it.
EXTENDS Naturals, TLC
VARIABLES x, y
Init == x = 0 /\ y \in {0, 1 + TLCGet("distinct")}
Next == x < 3 /\ x' = x + 1 /\ UNCHANGED y
Low == x < 1 + y
====
