# GPT-6 Astra — prompting best practices

Retrieved: 2026-09-09. Source: [OpenAI model guide](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#prompting-best-practices). Paraphrased reference; not harness policy.

## Documented recommendations

- **Autonomy:** explicitly authorize completing the requested work, making routine assumptions, and continuing independent work while questions remain. Prepare reviewable results before approval gates. [Follow-through](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#initiative-and-follow-through).
- **Instruction sensitivity:** audit skills and AGENTS.md for ambiguity or conflicts. Clarify user-versus-skill precedence; request the exact file and instruction behind unexpected pauses. [Instructions](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#instruction-following).
- **Writing:** define audience, length, prose versus lists, and concrete stylistic preferences. [Style](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#personality-and-writing-style).
- **Delegation:** specify when parallel agents should participate; require readable inter-agent messages. [Delegation](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#subagent-delegation).
- **Verification:** match checks to change risk; after required checks pass, repeat or broaden only for new evidence or unresolved concerns. [Testing](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#testing-and-verification).

## Configuration, separately

Astra does not support reasoning effort `none`; migration from `none` or `minimal` starts at `low`. Tool calling requires Responses. These are API constraints, not prompt instructions. [Migration](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra#update-api-and-model-parameters).

## Coverage

This source covers Astra, not every possible GPT-6 variant. No variant-specific extrapolation is established here. See the [comparison and evidence limits](../README.md).
