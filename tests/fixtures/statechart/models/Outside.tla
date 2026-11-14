---- MODULE Outside ----
\* The only initial state lies outside the constraint.
EXTENDS Naturals
VARIABLE x
Init == x = 5
Next == x' = x + 1
Small == x < 3
====
