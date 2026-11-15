---- MODULE UntracedStart ----
\* Low breaks at x = 2. TLC rebuilds a path by evaluating Init again, when
\* TLCGet("distinct") is no longer 0, so it cannot find the start: even the
\* first run names the break and prints no path to it.
EXTENDS Naturals, TLC
VARIABLES x, y
Init == x = 0 /\ y = TLCGet("distinct")
Next == x < 4 /\ x' = x + 1 /\ UNCHANGED y
Low == x < 2
====
