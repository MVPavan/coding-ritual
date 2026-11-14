---- MODULE CompactInfix ----
\* A compact infix definition follows Small; Small itself has no temporal
\* operator, so TLC tests it against the initial states alone.
EXTENDS Integers
VARIABLE x
Init == x = 0
Next == x' = 1 - x
Small == x = 0
a++b == []TRUE
====
