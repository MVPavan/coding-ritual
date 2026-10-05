# Task

Design, from first principles, an **Autonomous Development Lifecycle** for AI coding agents:
the end-to-end process by which AI agents take a software change from an initial request to a
delivered, trustworthy result with as little human involvement as safely possible.

Think from scratch. Do not assume any particular product, framework, vendor, repository host,
issue tracker, code-review platform, or CI system. Describe capabilities, not tools.

## What to produce

1. **Principles** — the few first principles your lifecycle is derived from (what must be true
   for autonomous software work to be trustworthy), each with one line of reasoning.
2. **Lifecycle diagram** — a plain-text diagram of the stages, their order, loops/back-edges,
   and any cross-cutting concerns that apply to every stage.
3. **Stage table** — for every stage: goal; inputs; outputs; the capabilities (agent skills)
   needed for that stage to run autonomously; the exit criterion; and what happens on failure.
4. **Human involvement** — exactly where, if anywhere, a human must still decide or act, and why
   autonomy cannot or should not replace them there.
5. **Failure, safety and recovery** — how the lifecycle bounds cost and time, stops runaway
   loops, recovers from crashes or interruptions, and avoids irreversible mistakes.
6. **Capability catalogue** — a consolidated list of the distinct agent skills the lifecycle
   requires, grouped sensibly, each with a one-line purpose.
7. **Trade-offs and open questions** — the main tensions in your design and what you are least
   sure about.

Be concrete and opinionated. Prefer mechanisms over adjectives. Length: as long as needed,
but no padding.
