---- MODULE Shapes ----
\* Every value kind the decoder reads, printed by TLC into Shapes.dump.
EXTENDS Integers, Sequences, TLC
CONSTANTS a, b
VARIABLES seqfn, recfn, setfn, onen, empties, mixed, scalars, nested
Init ==
  /\ seqfn = (<<1>> :> 7) @@ (<<2, 3>> :> 8)
  /\ recfn = ([p |-> 1] :> "one") @@ ([p |-> 2] :> "two")
  /\ setfn = [q \in {{1}, {1, 2}} |-> "v"]
  /\ onen = [i \in 1..3 |-> i * 10]
  /\ empties = <<{}, <<>>, [i \in {} |-> 0]>>
  /\ mixed = {a, "x", b}
  /\ scalars = <<-2, TRUE, "q \"t\"", a>>
  /\ nested = [r |-> {<<1, "z">>}, t |-> [u \in {"p"} |-> {}]]
Next == UNCHANGED <<seqfn, recfn, setfn, onen, empties, mixed, scalars, nested>>
====
