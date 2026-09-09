# Claude Opus 5 — prompting best practices

Retrieved: 2026-09-09. Source: [Anthropic guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5). Paraphrased reference; not harness policy.

## Documented recommendations

- Supply the complete specification upfront. For broad bug discovery, collect findings before filtering severity. [Capabilities](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#capability-improvements).
- Explicitly set conversational length, update cadence, and document length separately. Effort does not reliably control visible verbosity. Positive style examples help. [Responses](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#response-length-and-verbosity), [updates](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#user-facing-progress-updates), [documents](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#written-deliverable-length).
- Constrain task scope; remove redundant verification and self-check prompting that compounds default checking. [Verification](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#task-scope-and-over-verification).
- Reserve delegation for substantial independent work; cap spawning. [Subagents](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#controlling-subagent-spawning).
- Narrate corrections when they affect user decisions. [Corrections](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#self-correction).

## Configuration, separately

Start at `high`, then evaluate lower efforts. Prefer thinking enabled with lower effort over disabling it: disabled thinking can produce textual, unexecuted tool calls or internal tags. Provide crop/zoom tools for vision and templates for documents. [Capabilities](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#capability-improvements), [thinking](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5#running-with-thinking-disabled).

## Local policy conflict

The recommendation to remove verification instructions conflicts with this repository's mandatory [verification gate](../../../.claude/project/verification.md). Recorded for future evaluation; no policy change is authorized by these notes. See [evidence limits](../README.md).
