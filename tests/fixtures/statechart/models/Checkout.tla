---- MODULE Checkout ----
\* Correct end states marked by an action that changes nothing: no deadlock.
VARIABLE phase
Init == phase = "cart"
Pay == phase = "cart" /\ phase' \in {"paid", "failed"}
Retry == phase = "failed" /\ phase' = "cart"
Done == phase = "paid" /\ UNCHANGED phase
Next == Pay \/ Retry \/ Done
Spec == Init /\ [][Next]_phase
====
