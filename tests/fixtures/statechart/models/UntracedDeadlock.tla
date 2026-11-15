---- MODULE UntracedDeadlock ----
\* Low breaks at x = 1 from y = 0, then at x = 2 from the start y = 1. TLC
\* rebuilds a path by evaluating Init again, when TLCGet("distinct") is no
\* longer 0, so it cannot find the start y = 1: it names that break and
\* prints no path to it.
\* With deadlock checked too, the drawn graph comes from a rerun that
\* expands all 8 states: both x = 3 states are deadlocks.
EXTENDS Naturals, TLC
VARIABLES x, y
Init == x = 0 /\ y \in {0, 1 + TLCGet("distinct")}
Next == x < 3 /\ x' = x + 1 /\ UNCHANGED y
Low == x < 1 + y
TypeOK == x \in 0..3 /\ y \in 0..1
====
