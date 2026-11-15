# Fix root causes

A failure shows where a wrong state became visible, which is rarely where the
system first went wrong.

- Keep asking why at each link until the answer is a wrong decision in the
  code, not a consequence of an earlier one.
- Before naming the place a symptom surfaced as the cause, decide whether the
  state that triggered it is legitimate. If the system may be in that state,
  the code that broke on it is the cause and handling the state there is the
  fix; if not, a guard there would hide the fault, so trace the state to what
  produced it.
- A failure that appears only after a restart points first at persisted
  state: configuration files, caches, lock files, serialized state.
