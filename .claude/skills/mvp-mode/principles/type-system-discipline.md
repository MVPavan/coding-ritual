# Type-system discipline

Let the checker carry the rules the code would otherwise test at runtime.

- Shape types so the checker rejects impossible states; define special cases
  out of existence instead of handling them.
- Handle every variant of a closed type so the checker reports a variant left
  unhandled.
- Give a value its own type only where a raw value of the same primitive could
  really be passed in its place; validate it once when created and trust it
  afterwards.
- Keep a loose type while every operation on it stays defined for all inputs.
  Tighten it only where the looseness forces an assertion, a cast or an
  impossible-case throw. Returning a possibly absent result is the other way to
  make a signature total; pick whichever leaves callers simpler.
- Let one schema own both validation and the static type. Do not keep a schema,
  a parallel type and a hand-written check that can disagree.
- A function claiming to prove a type must really check it; a false claim is
  worse than an open cast, because the name says it is safe.
- Where raw input becomes typed values is `principle-boundary-discipline`'s
  rule.
