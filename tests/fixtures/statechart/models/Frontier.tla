---- MODULE Frontier ----
\* 0 branches to 1 and 2; 1 has no step out, 2 walks on to 3, which stays.
EXTENDS Naturals
VARIABLE n
Init == n = 0
Branch == n = 0 /\ n' \in {1, 2}
Walk == n = 2 /\ n' = 3
Stay == n = 3 /\ UNCHANGED n
Next == Branch \/ Walk \/ Stay
====
