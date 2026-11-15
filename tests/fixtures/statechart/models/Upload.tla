---- MODULE Upload ----
\* An upload the person can cancel from any busy phase; finished ends marked.
VARIABLE phase
Busy == {"picking", "sending", "verifying"}
Init == phase = "picking"
Pick   == phase = "picking" /\ phase' = "sending"
Send   == phase = "sending" /\ phase' = "verifying"
Verify == phase = "verifying" /\ phase' = "done"
Cancel == phase \in Busy /\ phase' = "cancelled"
Finished == phase \in {"done", "cancelled"} /\ UNCHANGED phase
Next == Pick \/ Send \/ Verify \/ Cancel \/ Finished
Spec == Init /\ [][Next]_phase
NeverCancelled == phase # "cancelled"
====
