---- MODULE UnusedTemporal ----
\* Small's temporal operator sits in a LET definition it never uses, so TLC
\* tests Small against the initial states alone.
EXTENDS Integers
VARIABLE x
Init == x = 0
Next == x' = 1 - x
Small == LET NeverUsed == []TRUE IN x = 0
====
