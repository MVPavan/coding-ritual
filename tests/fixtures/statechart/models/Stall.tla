---- MODULE Stall ----
\* Liveness breaks by stuttering: no fairness.
VARIABLE p
Init == p = "idle"
Start == p = "idle" /\ p' = "busy"
Back  == p = "busy" /\ p' = "idle"
Finish == p = "busy" /\ p' = "done"
Done == p = "done" /\ UNCHANGED p
Next == Start \/ Back \/ Finish \/ Done
Spec == Init /\ [][Next]_p
EventuallyDone == <>(p = "done")
====
