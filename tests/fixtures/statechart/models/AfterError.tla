---- MODULE AfterError ----
\* Small breaks at x = 1; the step out of x = 1 divides by zero.
EXTENDS Naturals
VARIABLE x
Init == x = 0
Inc == x = 0 /\ x' = 1
Oops == x = 1 /\ x' = 1 \div 0
Next == Inc \/ Oops
Small == x = 0
====
