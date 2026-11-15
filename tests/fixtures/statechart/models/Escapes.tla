---- MODULE Escapes ----
\* One string with every escape TLA+ allows.
VARIABLE x
Init == x = "q\"b\\c\td\ne\rf\fg"
Next == UNCHANGED x
====
