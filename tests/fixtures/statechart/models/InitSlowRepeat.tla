---- MODULE InitSlowRepeat ----
\* Small is cheap in the check (the second initial state comes after one
\* distinct state) and endless in a level probe bounded at 0 distinct states.
EXTENDS Integers, FiniteSets, TLC
VARIABLE x
Init == x \in {0, 1}
Next == x' = 1 - x
Small == IF x = 0 \/ TLCGet("distinct") > 0
         THEN TRUE
         ELSE (\A s \in SUBSET (1..40) : s \subseteq (1..40))
====
