# GPT-5.6 family — prompting best practices

Retrieved: 2026-09-09. Source: [OpenAI model guide](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#prompting-best-practices). Paraphrased reference; not harness policy.

## Documented recommendations

- **Lean context:** remove duplicate rules, unnecessary examples, and irrelevant tools incrementally; rerun the same evaluations after each removal. Retain requirements and examples addressing measured failures. [Leaner prompts](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#favor-leaner-prompts).
- **Authority:** distinguish analysis from implementation requests; name authorized local actions and approval boundaries once. [Autonomy](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#define-autonomy-and-approval-boundaries).
- **Output:** preserve required facts, evidence, caveats, and next actions. Blanket brevity can overcompress already-concise replies. Specify observable tone choices. [Style](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#set-response-length-and-style).
- **Pro:** retain outcome-focused prompts: goal, context, constraints, evidence, success criteria, format. Enable pro through configuration, not requests to think harder. [Pro](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#pro-mode).
- **Programmatic tools:** identify the bounded processing stage, eligible tools, output/evidence schema, retry/concurrency limits, and stopping condition. Keep judgment, approvals, and artifact-sensitive work direct. Evaluate the final answer too. [PTC](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6#programmatic-tool-calling).

## Coverage and configuration

`gpt-5.6` aliases Sol; Terra and Luna are other family members. This guide does not provide separate prompting recipes for each. `text.verbosity` controls default detail. Benchmark reasoning effort and pro independently. [Guide](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.6).

See [evidence limits](../README.md).
