# Claude Fable 5.1 — prompting best practices

Retrieved: 2026-09-09. Source: [Anthropic guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1). Paraphrased reference; not harness policy.

## Documented recommendations

- Request progress updates and a self-contained final response; check client visibility first. [Updates](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#ask-for-user-facing-progress-updates).
- Nudge batching of independent calls; keep the lead productive during delegation. [Batching](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#batch-independent-tool-calls-in-agent-loops).
- Prefer literal prose, useful formatting, and a worked example distinguishing quotations from paraphrases. [Writing](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#writing-density).
- Require full completion within scope, targeted edits, and proportionate permanent tests. [Completion](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#finish-the-whole-task).
- Preserve decisions, exact constraints, rejected approaches, current state, unresolved work, and hard-to-recover details during compaction. [Summaries](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#tell-the-model-what-to-preserve-in-compaction-summaries).
- At low effort, explicitly trigger retrieval for unfamiliar or changing names. [Search](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#search-triggering-at-low-effort).

## Harness and configuration

Start at `high`; evaluate other efforts. Budget thinking plus final output at `xhigh`/`max`; discourage duplicate drafting. Keep replay history append-only, including thinking blocks. Provide crop/zoom tools for dense images. For benign coding false refusals, supply language documentation, use bug-focused wording, and avoid base64 tool payloads. [Effort](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#consider-all-effort-levels), [history](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#keep-the-conversation-history-append-only), [refusals](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#reduce-safeguard-false-positives), [long outputs](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#leave-room-for-long-outputs-at-xhigh-and-max-effort), [vision](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1#give-vision-work-tools-to-crop-and-zoom).

See [evidence limits](../README.md); scope is Fable 5.1.
