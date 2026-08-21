# Coding Discipline

Core discipline for every task in this project. Descended from the retired AK
guidelines ([Karpathy's observations](https://x.com/karpathy/status/2015883857489522876)
on LLM coding pitfalls); everything another surface now owns was removed —
simplification passes live in the execution engine's Simplification look,
verification in `.claude/project/verification.md`, testing in
`rules/python/testing.md`, conventions in `rules/python/coding-style.md`.

## Think before coding

- State your assumptions. If multiple interpretations exist, present them —
  don't pick silently. If something is unclear, stop and ask.
- If a simpler approach exists, say so. Push back when warranted.
- Read exports, immediate callers, and shared utilities before adding code;
  if unsure why code is structured a way, ask.
- Before coding against external data (API, database, file, config), run the
  command and read the actual field names and types — code against what you
  observed, not what docs or memory say.

## Simplicity, with its counterweight

- Minimum code that solves the problem: no speculative features, no
  unrequested configurability, no error handling for impossible scenarios.
- The counterweight: some abstractions exist for testability or
  extensibility — do not remove or refuse one just because it serves a single
  call site today, and never optimize for line count. Explicit-but-plain
  beats compact-but-clever when compact needs a mental pause.

## Surgical changes

- Touch only what the request requires; match existing conventions even where
  you disagree (surface a harmful convention, don't fork it silently). Don't
  "improve" adjacent code, comments, or formatting.
- Remove imports/variables/functions that YOUR change orphaned; leave
  pre-existing dead code alone.
- Report out-of-scope observations as
  `NOTICED BUT NOT TOUCHING: <what> — <why it matters>`.

## Judgment and honesty

- Use the model for judgment calls (classification, drafting, summarization,
  extraction). If code can answer deterministically (routing, retries,
  transforms), code answers.
- When two patterns conflict, pick one (more recent / better tested), say
  why, and flag the other for cleanup — never blend them.
- Fail loud: "completed" is wrong if anything was skipped silently; surface
  uncertainty instead of hiding it.
