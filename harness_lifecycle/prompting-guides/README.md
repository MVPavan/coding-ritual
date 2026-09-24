# Prompting Guides

Retrieved: 2026-09-09. Question: how should prompting differ across the four requested model guides?

These are concise, paraphrased reference notes with links to the official sections, not full webpage archives or executable harness instructions. The user-requested location is `harness_lifecycle/prompting-guides/`.

## Models and biggest adjustments

| Vendor | Saved guide | Main emphasis |
|---|---|---|
| OpenAI | [GPT-6 Astra](openai/gpt-6-astra-best-practices.md) | Autonomy, instruction conflicts, calibrated delegation. [Source](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#prompting-best-practices) |
| OpenAI | [GPT-5.6 family](openai/gpt-5.6-best-practices.md) | Lean prompts and outcome contracts. [Source](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#prompting-best-practices) |
| Anthropic | [Claude Fable 5.1](anthropic/claude-fable-5.1-best-practices.md) | Completion, progress visibility, history integrity. [Source](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1) |
| Anthropic | [Claude Opus 5](anthropic/claude-opus-5-best-practices.md) | Reduce excess narration, verification, and delegation. [Source](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5) |

## Synthesis — interpretation, not a benchmark result

A useful design hypothesis is a shared task contract plus small model-specific adjustments. The contract states the deliverable, scope, evidence, action authority, and output requirements. Add an adjustment when observed behavior warrants it; avoid combining every vendor's remedy into one universal prompt.

The table highlights differences within vendors as well as between them. Vendor identity alone is too coarse a basis for selecting a prompt. These sources also mix prompt advice with API and orchestration requirements: a sentence cannot implement a missing client capability.

## Method and confidence

All four exact supplied URLs were opened and their relevant sections read. The two OpenAI query parameters returned different model guidance. Research depth: focused official-document comparison. Source owners: OpenAI and Anthropic. Publication/update dates were not established; the date above is retrieval time.

- **High confidence:** the linked vendors publish the summarized recommendations.
- **Unverified locally:** resulting quality, latency, cost, and completion improvements in this harness. No model experiments were run.
- **Inference:** the shared-contract approach above is a proposed synthesis, not a vendor guarantee.

Strongest counterargument: vendor observations may depend on private evaluations and different tool environments. A useful default elsewhere may harm this repo's workflows. Compare representative tasks before adopting changes; retain required correctness checks while testing reductions in redundant prompting.

## Boundaries and future reference

These notes cover the requested four guides, not a complete model catalog. They establish neither universal behavior across variants nor which API controls a particular Codex or Claude Code installation exposes. Availability and API details need fresh verification before implementation.

The Opus note records a source-versus-repository verification conflict. This collection does not amend AGENTS.md, skills, approval policy, or test requirements. Future adoption must resolve that conflict explicitly.

When refreshing, reopen the exact model URL, compare its relevant sections, and update the retrieval date and affected claims together. Preserve model query parameters; a moving latest-model page is not an immutable source.
