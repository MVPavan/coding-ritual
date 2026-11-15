---- MODULE Retry ----
\* Liveness breaks through a loop of failures: busy and failed repeat forever.
VARIABLE p
Init == p = "idle"
Start == p = "idle" /\ p' = "busy"
Skip  == p = "idle" /\ p' = "done"
Fail  == p = "busy" /\ p' = "failed"
Again == p = "failed" /\ p' = "busy"
Done  == p = "done" /\ UNCHANGED p
Next == Start \/ Skip \/ Fail \/ Again \/ Done
Spec == Init /\ [][Next]_p /\ WF_p(Next)
EventuallyDone == <>(p = "done")
====
