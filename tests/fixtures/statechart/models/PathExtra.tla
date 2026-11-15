---- MODULE PathExtra ----
\* The first run's graph stops at the constraint x <= 1; Low's path reaches
\* x = 2, y = 0 past it. Low's drawing run then fails evaluating x = 2, y = 1.
\* critic-92l probe.
EXTENDS Naturals
VARIABLES x,y
Init == x = 0 /\ y \in {0,1}
Next == x < 3 /\ x' = x+1 /\ UNCHANGED y
Bound == x <= 1
Low == IF x = 2 /\ y = 1 THEN 1 \div 0 = 0 ELSE x < 2+y
====
