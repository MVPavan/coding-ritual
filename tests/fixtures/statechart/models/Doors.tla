---- MODULE Doors ----
\* Two parts that move apart: a door and its lock. The door opens only when
\* unlocked, and the lock turns only while the door is closed.
VARIABLES door, lock
Init == door = "closed" /\ lock = "locked"
Open   == door = "closed" /\ lock = "unlocked" /\ door' = "open" /\ UNCHANGED lock
Close  == door = "open" /\ door' = "closed" /\ UNCHANGED lock
Unlock == lock = "locked" /\ door = "closed" /\ lock' = "unlocked" /\ UNCHANGED door
Lock   == lock = "unlocked" /\ door = "closed" /\ lock' = "locked" /\ UNCHANGED door
Next == Open \/ Close \/ Unlock \/ Lock
Spec == Init /\ [][Next]_<<door, lock>>
====
