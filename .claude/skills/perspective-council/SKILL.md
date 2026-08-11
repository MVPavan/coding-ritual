---
name: perspective-council
description: "Use ONLY when the user explicitly asks for the council: 'council this', 'run the council', 'perspective council', 'war room this', 'pressure-test this', 'stress-test this', 'debate this'. Never trigger on ordinary decision questions — 'should I X or Y', 'which option', 'is this the right move', 'I'm torn between' — answer those directly; the user will invoke the council themselves if they want it. If the user names specific council members and a judge, use model-council instead."
---

# Perspective Council

Five sub-agents analyze one framed question through five clashing lenses, anonymously peer-review each other, and a chairman synthesizes a verdict. Adapted from Karpathy's LLM Council — thinking lenses inside one model instead of different models. For distinct user-named models with a judge, use `model-council`.

Use only where uncertainty is genuine and a wrong call is expensive. One-right-answer questions, creation tasks, and summaries get answered directly — no council.

## The five lenses

| Advisor | Lens |
|---|---|
| Contrarian | Assumes a fatal flaw exists and hunts for it. Asks the questions being avoided. |
| First Principles | Ignores the surface question: "what are we actually solving?" May rule the question itself wrong. |
| Expansionist | Ignores risk; hunts undervalued upside and adjacent opportunity. |
| Outsider | Zero context on the user or field. Catches curse-of-knowledge blind spots. |
| Executor | Only feasibility and the fastest path: "what do you do Monday morning?" |

Built-in tensions: Contrarian↔Expansionist (downside/upside), First Principles↔Executor (rethink/just do), Outsider keeps both honest.

## Process

1. **Frame.** Spend ≤30s finding the 2–3 workspace files that ground the question (CLAUDE.md, memory/, files the user referenced). Write one neutral framed question: the decision, key context and numbers, constraints, stakes. No opinion, no steering. If too vague, ask exactly one clarifying question, then proceed.
2. **Convene — 5 sub-agents in parallel.** Each gets its lens description, the framed question, and: "Respond only from your lens. Be direct and specific; do not hedge or balance — other advisors cover the other angles. 150–300 words, no preamble."
3. **Peer review — 5 fresh sub-agents in parallel.** Anonymize the responses as A–E with randomized mapping. Each reviewer sees all five and answers in ≤200 words: (1) strongest response and why, (2) biggest blind spot and what it misses, (3) what ALL five missed.
4. **Chairman synthesis.** One agent gets the framed question, de-anonymized responses, and all reviews. It may side with a lone dissenter when that reasoning is strongest.
5. **Deliver in chat** — markdown:

```
## Council Verdict: {topic}
### Where the Council Agrees      — independent convergences (high-confidence signals)
### Where the Council Clashes     — genuine disagreements, both sides stated
### Blind Spots the Council Caught — surfaced only by peer review
### The Recommendation            — a real answer with reasoning, never "it depends"
### The One Thing to Do First     — a single concrete step, not a list
```

## Rules

- Spawn each round in parallel — sequential spawning lets responses bleed.
- Always anonymize peer review — attribution causes lens-deference instead of merit judgment.
- Save a transcript to docs/research/perspective-council/{topic}.md unless the user asks not to.

