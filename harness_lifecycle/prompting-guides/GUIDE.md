# Consolidated prompting guide

## 0. Precedence and use

Official vendor captures are authoritative; articles can add guidance only where no official source addresses the point. On the same point, Opus 5.5 replaces Opus 5, and the Astra model guide and blog replace GPT-5.6 guidance. Opus 5 patterns that 5.5 does not change remain a starting point. Fable 5.1 is a separate line: keep its behavior scoped to Fable. Where its general advice conflicts with Opus 5.5 or Astra, use publication dates only if evidenced in the captures; otherwise keep both scoped and see [LEDGER.md](LEDGER.md). Retrieval dates do not establish publication order. The rules below are source guidance for writing instructions, not an automatic change to this repository's operating policy.

| File (relative to this directory) | Vendor / model | Role | Supersedes what |
|---|---|---|---|
| `sources/anthropic/claude-opus-5-5.md` | Anthropic / Opus 5.5 | Authoritative, current Opus | Opus 5 on the same point |
| `sources/anthropic/claude-opus-5.md` | Anthropic / Opus 5 | Official, earlier | Retained only where 5.5 does not replace it |
| `sources/anthropic/claude-fable-5-1.md` | Anthropic / Fable and Mythos 5.1 | Authoritative for this model line | No Opus source |
| `sources/openai/gpt-6-astra-model-guide.md` | OpenAI / GPT-6 Astra | Authoritative, current Astra | GPT-5.6 on the same point |
| `sources/openai/gpt-6-astra-skills-and-prompts-blog.md` | OpenAI / GPT-6 Astra | Authoritative, current Astra | GPT-5.6 on the same point; Provencher article |
| `sources/openai/gpt-5.6-model-guide.md` | OpenAI / GPT-5.6 | Official, earlier | Retained only where Astra does not replace it |
| `sources/openai/gpt-5.6-prompt-guidance.md` | OpenAI / GPT-5.6 Sol | Official, earlier | Retained only where Astra does not replace it |
| `articles/wulfie_bain.txt` | Independent article | Corroborating only (no rule rests on it alone) | Nothing |
| `articles/eric-provencher.txt` | Independent article | Superseded, no rules adopted | Superseded by official Astra blog |
| `anthropic/claude-opus-5-best-practices.md` | Anthropic / Opus 5 | Historical paraphrase | Superseded by verbatim captures |
| `anthropic/claude-fable-5.1-best-practices.md` | Anthropic / Fable 5.1 | Historical paraphrase | Superseded by verbatim capture |
| `openai/gpt-5.6-best-practices.md` | OpenAI / GPT-5.6 | Historical paraphrase | Superseded by verbatim captures |
| `openai/gpt-6-astra-best-practices.md` | OpenAI / GPT-6 Astra | Historical paraphrase | Superseded by verbatim captures |
| `README.md` | This collection | Historical index | This guide governs current synthesis |

## 1. Universal rules

- **U-01** State the intended outcome, scope, constraints, evidence, completion condition, and any required output; let the model choose routine steps. [sources/openai/gpt-5.6-prompt-guidance.md:9-11] [sources/openai/gpt-5.6-prompt-guidance.md:27-39] [sources/anthropic/claude-opus-5.md:17-17] [sources/anthropic/claude-fable-5-1.md:822-830]
- **U-02** Treat a requested change as authority for in-scope reversible work; reserve questions for materially different readings and confirmation for risky, destructive, or genuinely new scope. Continue independent work while a blocking answer is pending. [sources/openai/gpt-6-astra-model-guide.md:64-75] [sources/anthropic/claude-fable-5-1.md:804-830] [sources/anthropic/claude-opus-5-5.md:71-76]
- **U-03** Set the work layer explicitly: a diagnostic question calls for an assessment, while a request to change, including “can you fix…?”, calls for implementation and relevant validation. [sources/openai/gpt-5.6-prompt-guidance.md:104-122] [sources/anthropic/claude-fable-5-1.md:810-815] [sources/openai/gpt-6-astra-model-guide.md:64-68]
- **U-04** Keep the requested scope intact; complete required behavior and report unrelated findings instead of silently adding fixes or narrowing the deliverable. [sources/anthropic/claude-opus-5.md:65-69] [sources/anthropic/claude-fable-5-1.md:822-846] [sources/openai/gpt-6-astra-model-guide.md:58-67]
- **U-05** Prompt for a proportionate, self-contained final answer and useful progress updates on long work; specify the cadence and information users need. [sources/anthropic/claude-opus-5-5.md:89-99] [sources/anthropic/claude-fable-5-1.md:42-59] [sources/openai/gpt-5.6-prompt-guidance.md:200-207]
- **U-06** State the audience, required facts, and concrete writing choices; preserve substance while trimming repetition and generic filler. [sources/openai/gpt-6-astra-model-guide.md:96-117] [sources/openai/gpt-5.6-model-guide.md:124-145] [sources/anthropic/claude-opus-5.md:25-59]
- **U-07** Match subagent delegation to independent work, model behavior, and workload; specify when delegation improves the result. [sources/anthropic/claude-opus-5.md:71-79] [sources/anthropic/claude-opus-5-5.md:115-123] [sources/openai/gpt-6-astra-model-guide.md:120-134]
- **U-08** Evaluate prompt changes on representative tasks; make targeted changes to observed failures and remove instructions whose benefit no longer holds. [sources/openai/gpt-5.6-prompt-guidance.md:287-299] [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:39-55]
- **U-09** Define the intended user experience through concrete personality and collaboration choices, including tone, formatting, initiative, and when to ask questions. [sources/openai/gpt-5.6-prompt-guidance.md:73-78] [articles/wulfie_bain.txt:36-44]

## 2. Instruction files and skills

- **S-01** Keep skill names and descriptions short and precise about when the skill applies; avoid broad triggers and competing descriptions that load irrelevant skills. [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:15-31]
- **S-02** Use skills for task-specific workflows or app guidance; for a multi-workflow skill, make the root a small router to supporting instructions and scripts. [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:13-15] [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:33-33]
- **S-03** Remove elaborate step recipes when they constrain judgment without improving the result; consider every model that may load a shared skill. [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:35-37]
- **S-04** Revisit every always-loaded `AGENTS.md` instruction; route reading to relevant documents by task instead of requiring a full document stack for each edit. [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:39-51]
- **S-05** Audit the combined instruction stack for contradictions, ambiguity, repeated rules, and unnecessary tools; remove one group at a time and compare representative results. [sources/openai/gpt-6-astra-model-guide.md:80-94] [sources/openai/gpt-5.6-prompt-guidance.md:15-35] [sources/openai/gpt-5.6-model-guide.md:82-92]
- **S-06** Define when an action is authorized and where approval is needed in one clear place; name known safe local workflows to prevent unnecessary pauses. [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:53-63] [sources/openai/gpt-5.6-model-guide.md:94-112]
- **S-07** For complex prompts, use short, identifiable sections for goal, constraints, tools, output, and stopping rules; add detail only where it changes behavior. [sources/openai/gpt-5.6-prompt-guidance.md:267-285] [articles/wulfie_bain.txt:45-69]
- **S-08** When drafting a task prompt, state the completion bar, evidence, constraints, and stop condition; avoid absolute rules for context-dependent choices. [sources/openai/gpt-5.6-prompt-guidance.md:37-65] [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:65-71]
- **S-09** Write tool descriptions with the purpose, expected return fields, and error behavior; identify prerequisites and keep irrelevant tools out of the task context. [sources/openai/gpt-5.6-prompt-guidance.md:124-136] [sources/openai/gpt-5.6-model-guide.md:88-92]
- **S-10** For bounded programmatic tool stages, name eligible tools, required output and evidence, concurrency, retry and stop limits, and the handoff back to direct judgment. [sources/openai/gpt-5.6-model-guide.md:177-228]

## 3. Claude-specific

### Opus 5.5

- **C-01** For unattended Opus 5.5 work, define completion and meaningful stopping conditions; treat a text-only turn as a progress report when work remains, and bound automatic continuations to two or three. [sources/anthropic/claude-opus-5-5.md:59-73]
- **C-02** If work Opus 5.5 started is still running, return its result before declaring completion. [sources/anthropic/claude-opus-5-5.md:69-69]
- **C-03** For human-in-the-loop work, ask for the desired progress cadence in the system prompt; for unattended work, word persistence instructions around specific premature stops while keeping risky-action confirmation. [sources/anthropic/claude-opus-5-5.md:71-76] [sources/anthropic/claude-opus-5-5.md:95-99]
- **C-04** In loosely specified multi-app work, instruct Opus 5.5 to inspect potentially relevant records before acting, and account for the added tool use and exposure to untrusted content. [sources/anthropic/claude-opus-5-5.md:105-113]
- **C-05** For Opus 5.5 multiagent tasks, supply an advisory elapsed-time signal or measured budget when useful; enforce any hard deadline in the harness and check quality under time pressure. [sources/anthropic/claude-opus-5-5.md:115-123]
- **C-06** Mark user-pasted outside content as such and instruct Opus 5.5 to follow its embedded directions only when the user's own request calls for them; treat text tags as one guardrail, not a security boundary. [sources/anthropic/claude-opus-5-5.md:137-155]
- **C-07** Remove instructions that demand the model reproduce private reasoning or tell it not to think; re-test Opus 5 workarounds written for disabled thinking. [sources/anthropic/claude-opus-5-5.md:50-56] [sources/anthropic/claude-opus-5-5.md:79-85]
- **C-08** If chat replies start slowly, consider removing blanket instructions to think carefully; keep later-answer re-examination enabled for agentic work where new evidence can expose an earlier error. [sources/anthropic/claude-opus-5-5.md:125-135]
- **C-09** For frontend work, name the particular design patterns to avoid and inspect the result before extending the exclusions; a generic request to avoid an AI look is insufficient. [sources/anthropic/claude-opus-5-5.md:161-166]
- **C-10** Control Opus response and written-deliverable length with explicit output instructions; effort primarily controls thinking. [sources/anthropic/claude-opus-5.md:25-59] [sources/anthropic/claude-opus-5-5.md:38-46]
- **C-11** For broad Opus code review, ask for all findings and filter severity in a separate pass; an instruction to report only high-severity issues may suppress findings. [sources/anthropic/claude-opus-5.md:18-18] [sources/anthropic/claude-opus-5-5.md:11-11]
- **C-12** Remove generic Opus instructions requiring a final verification step or a verification subagent. [sources/anthropic/claude-opus-5.md:63-63] [sources/anthropic/claude-opus-5-5.md:11-11]
- **C-13** Avoid prompting Opus to double-check or re-verify answers it already self-corrects. [sources/anthropic/claude-opus-5.md:83-83] [sources/anthropic/claude-opus-5-5.md:11-11]
- **C-14** For Opus, delegate only sizeable independent tasks; skip subagents for small tasks or verification, and set deterministic depth, concurrency, or spend caps where needed. [sources/anthropic/claude-opus-5.md:73-79] [sources/anthropic/claude-opus-5-5.md:11-11]
- **C-15** In unattended Opus 5.5 runs, track parts in a checklist or to-do tool; optionally use a smaller completion checker to return the unmet condition after a premature turn ending. [sources/anthropic/claude-opus-5-5.md:61-63]
- **C-16** If using the Opus 5.5 unattended persistence block, include it from the first request; adding it mid-session invalidates earlier thinking blocks, and it does not waive risky-action confirmation. [sources/anthropic/claude-opus-5-5.md:71-76]
- **C-17** With `thinking.display: "updates"` set, count Opus 5.5 tool-calling steps without visible text or progress-update text; after about five quiet steps, append a turn-scoped reminder after the latest tool results, and stop after two or three reminders. [sources/anthropic/claude-opus-5-5.md:99-102]

### Fable / Mythos 5.1 (this line only)

- **CF-01** If Fable goes quiet in a long tool chain, first expose its progress blocks and remove narration-suppressing instructions; then request brief status updates and a final recap. [sources/anthropic/claude-fable-5-1.md:42-59]
- **CF-02** In Fable coding or computer-use loops that serialize independent calls, nudge it to request all independent items together. [sources/anthropic/claude-fable-5-1.md:62-72]
- **CF-03** For Fable client-side compaction, preserve user constraints, decisions, failed approaches, current state, unresolved work, and hard-to-reconstruct details. [sources/anthropic/claude-fable-5-1.md:833-839]
- **CF-04** When Fable prose becomes dense or mannered, ask for literal, direct wording; remove blanket anti-formatting rules if they suppress useful structure. [sources/anthropic/claude-fable-5-1.md:764-784]
- **CF-05** If Fable copies retrieved wording without marking it, provide one complete correct example that distinguishes paraphrase from a short quotation. [sources/anthropic/claude-fable-5-1.md:786-802]
- **CF-06** For Fable, define autonomous completion within the user's scope, and keep permanent tests proportionate to stated behavior and repository convention. [sources/anthropic/claude-fable-5-1.md:804-846]
- **CF-07** At low Fable effort, explicitly trigger retrieval for unfamiliar or fast-changing names using the user's exact term. [sources/anthropic/claude-fable-5-1.md:849-857]
- **CF-08** If Fable rewrites whole files for small edits, ask for targeted edits when the result is equivalent. [sources/anthropic/claude-fable-5-1.md:867-873]
- **CF-09** Let the Fable lead continue independent work while subagents run, with results returned later and an explicit wait option. [sources/anthropic/claude-fable-5-1.md:888-896]
- **CF-10** If the interface hides tool output, tell Fable what users can see and ask it to include user-needed content in its reply. [sources/anthropic/claude-fable-5-1.md:56-59]
- **CF-11** Before a state-changing command, have Fable check that the evidence supports that specific action. [sources/anthropic/claude-fable-5-1.md:815-817]

## 4. OpenAI-specific: GPT-6 Astra

- **O-01** Prompt Astra to treat action requests phrased as questions or wishes as instructions to act and persist through the requested result; keep diagnostic questions as requests for assessment. [sources/openai/gpt-6-astra-model-guide.md:52-68] [sources/openai/gpt-5.6-prompt-guidance.md:104-115]
- **O-02** Have Astra prepare a concrete reviewable result before requesting approval for an action that still needs it; avoid hypothetical approval pauses. [sources/openai/gpt-6-astra-model-guide.md:70-76]
- **O-03** Make user-over-skill priority explicit, and have Astra identify the exact skill instruction when it pauses or diverts because of a skill. [sources/openai/gpt-6-astra-model-guide.md:80-94]
- **O-04** Specify when and how much Astra should delegate in a multiagent harness; make inter-agent messages legible. [sources/openai/gpt-6-astra-model-guide.md:120-134]
- **O-05** Calibrate Astra tests to change risk and required checks; broaden or repeat only after changed work, a failure, or unresolved concern. [sources/openai/gpt-6-astra-model-guide.md:136-144] [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:53-57]
- **O-06** Specify prose structure and level of detail when Astra's default lists, tables, or recurring phrases do not fit the audience. [sources/openai/gpt-6-astra-model-guide.md:96-117]
- **O-07** Audit inherited approval and first-implementation review instructions when moving to Astra; state the actual completion bar and safe workflows it may carry through. [sources/openai/gpt-6-astra-skills-and-prompts-blog.md:53-71]

## 5. Configuration (not prompting)

- **K-01** For Opus 5.5 start effort evaluation at `medium`, with thinking always on; use lower effort before prompt instructions to reduce thinking, and budget tokens for thinking plus reply. [sources/anthropic/claude-opus-5-5.md:38-57]
- **K-02** Expose Opus 5.5 progress-update thinking blocks with `thinking.display: "updates"` when the client needs them; use a dedicated message tool for verbatim mid-turn content. [sources/anthropic/claude-opus-5-5.md:89-99]
- **K-03** For Fable 5.1 start effort evaluation at `high`; preserve returned thinking blocks and append-only history, and budget thinking plus reply on long high-effort outputs. [sources/anthropic/claude-fable-5-1.md:34-40] [sources/anthropic/claude-fable-5-1.md:756-762] [sources/anthropic/claude-fable-5-1.md:875-885]
- **K-04** For Astra tool use, use Responses; Astra does not support `none` reasoning effort. Test supported effort levels on representative work. [sources/openai/gpt-6-astra-model-guide.md:158-166]
- **K-05** Set an OpenAI request's default output detail with `text.verbosity` where available; use the task prompt for required content and length. [sources/openai/gpt-5.6-model-guide.md:114-136]
- **K-06** When enabling GPT-6 asynchronous tools, let the application manage pending calls and return each result with its original `call_id` while the model continues independent work. [sources/openai/gpt-6-astra-model-guide.md:28-28]
- **K-07** Support GPT-6 mid-turn steering through the Responses WebSocket continuation when user corrections or new requirements arrive during work. [sources/openai/gpt-6-astra-model-guide.md:29-29]
