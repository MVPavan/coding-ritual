---- MODULE Loop ----
\* Liveness breaks through a loop: Start and Back can repeat forever.
VARIABLE p
Init == p = "idle"
Start == p = "idle" /\ p' = "busy"
Back  == p = "busy" /\ p' = "idle"
Finish == p = "busy" /\ p' = "done"
Done == p = "done" /\ UNCHANGED p
Next == Start \/ Back \/ Finish \/ Done
Spec == Init /\ [][Next]_p /\ WF_p(Next)
EventuallyDone == <>(p = "done")
====
