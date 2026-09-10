# Shared AGENTS.md structure proposal

Date and retrieval date: 2026-09-09. Status: historical proposal and rationale.

Activation, 2026-09-09: the user-edited candidate is now installed in `AGENTS.md`,
with conditional pointers to `.claude/project/coding-style.md` and
`.claude/project/delegation.md`. The root now requests useful bounded delegation
within runtime limits. Superseded Markdown rules and their Codex symlinks were
removed; native command enforcement remains unchanged. The draft file is an
archived input; `AGENTS.md` and its project pointers are authoritative.

Revision, 2026-09-09: the user requested a shorter draft. The current candidate
has 549 words across 78 lines, down from 1,020 words across 121 lines (46% fewer
words; no tokenizer measurement). Implementation and effort now share a section.
Repeated boundaries, generic advice, examples, and procedural detail were removed;
Beads tracking is one line. The research and initial validation below describe
the original proposal and remain its rationale, not the current file's inventory.
The shortened draft passed pointer, whitespace, and single-Beads-line checks.
A fresh Sol/medium session applied it to the same six simulated scenarios;
outputs are in gitignored `scratchpad/agents-trim/`. The hostile-content response
rejected disclosure and bypassing but suggested asking about them if blocking
completion: this is a limitation of the probe, not evidence of an enforceable
security boundary. Native enforcement remains necessary.

## Decision

Use one AGENTS.md for retained general behavioral policy, with CLAUDE.md importing
it. Keep conditional pointers to project facts, commands, and specific workflows;
keep native enforcement in harness configuration. Do not consolidate by copying
every existing rule into the root file.

Draft: `harness_lifecycle/prompting-updates/drafts/AGENTS.proposed.md` (paths inside
the draft are relative to the repository root, where it would be installed).

The proposed structure is a design recommendation, not a measured optimum for
GPT-5.6, Astra, Opus, or Fable. No vendor specifies a universally best outline.

## Scope and method

Reviewed eight primary pages from OpenAI, Anthropic, and AGENTS.md, plus the
user-supplied minimal-code excerpt and local Eric Provencher article. Compared
their recommendations against the user's single-policy requirement and current
repository safeguards. Vendor engineering articles describe their experience;
they do not establish cross-model benchmark results. No model pricing or latency
claims are made. Memory search returned no directly useful guidance for this task.

## Evidence and implications

| Finding | Evidence | Implication and confidence |
| --- | --- | --- |
| The format has no mandatory headings. | [AGENTS.md specification site](https://agents.md/) | Organize around decisions rather than cargo-culting a template. High. |
| Always-loaded instructions should be short and contain information the agent cannot readily infer. | [Claude Code best practices](https://code.claude.com/docs/en/best-practices#write-an-effective-claude-md) | Keep concrete constraints and contextual pointers; remove generic tutorials. High. |
| A large root manual can obscure priorities and accumulate stale instructions. | [OpenAI harness engineering](https://openai.com/index/harness-engineering/) | One policy source need not contain the complete knowledge base. High for reported experience; medium for this repository's optimal size. |
| Relevant context is more useful than exhaustive context; retrieval and compaction are design choices. | [Anthropic context engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) | Scope reads and preserve evidence provenance during handoff. High for general guidance. |
| Additional agent orchestration trades cost and latency against potential quality gains. | [Anthropic effective agents](https://www.anthropic.com/engineering/building-effective-agents) | Avoid mandatory delegation and review chains on every task. Medium when applying the application-design guidance to coding harnesses. |
| Codex discovers AGENTS instructions through a hierarchy and a configured size budget. | [OpenAI AGENTS.md documentation](https://learn.chatgpt.com/docs/agent-configuration/agents-md) | Native loading is a harness concern; merely creating a file does not prove every harness loaded it. High. |
| Claude imports expand context; instructions are not enforced configuration. | [Claude memory documentation](https://code.claude.com/docs/en/memory) | Keep CLAUDE.md as the import shim, but retain permission and hook configuration. High. |
| Untrusted content can redirect agents and leak private data; prompt guidance alone is imperfect. | [OpenAI agent safety guidance](https://developers.openai.com/api/docs/guides/agent-builder-safety) | Include a data-versus-authority boundary and maintain external enforcement. High. |

The local `harness_lifecycle/prompting-guides/articles/eric-provencher.txt` reinforces
conditional context loading, pruning, explicit completion, and continuity of safe
authorization. It is user-supplied commentary, not an independently benchmarked
source for model-specific effects.

## Structure and coverage

| Section | Decision it governs | Requested concerns |
| --- | --- | --- |
| Scope and authority | What outcome is authorized and when to ask | Governance, quality |
| Context and evidence | What to read, trust, verify, and retain | Bloat, poisoning, quality, cost |
| Implementation choices | Whether and how much to build | Quality, efficiency, cost |
| Effort and coordination | How much planning, tooling, and delegation to use | Cost, speed, efficiency |
| Verification and completion | What proves the task is finished | Quality, efficiency, speed |
| Safety and work preservation | Which protections survive optimization | Safety, governance |
| Repository context | Where task-specific facts and procedures live | Context efficiency, governance |

Alternative: eight sections matching the user's eight concerns are easy to audit,
but repeat the same instructions under cost, speed, efficiency, and context. A
minimal orientation-only router would be shorter, but would leave behavioral
policy in separate files or implicit defaults. The selected structure balances
the user's centralization preference with selective context loading.

## Evaluation of the supplied excerpt

| Element | Recommendation | Reason |
| --- | --- | --- |
| Efficient senior developer / best code never written | Keep the intent, omit the persona | State the desired engineering outcome without inviting under-delivery. |
| Reuse ladder and understanding before coding | Keep, with suitability checks | Prevent duplication without forcing reuse of unsuitable code or libraries. |
| Root cause and caller inspection | Keep, scope to affected contracts | A common helper is not always the correct layer; callers can have legitimate differences. |
| One line / fewest files / shortest diff | Drop as optimization targets | Obscures readability, module boundaries, and behavioral risk. |
| No unrequested abstractions | Replace with present-need justification | A well-scoped abstraction can be necessary to implement the requested behavior safely. |
| Avoid dependencies and boilerplate | Keep as a preference | Custom crypto or protocol code can cost more and be riskier than a suitable dependency. |
| Challenge complex requests | Keep material assumption checks | Avoid turning every clear request into a new approval round. |
| `ponytail:` comments | Keep useful limitation documentation, omit the prefix | The project-specific marker adds no shared meaning. Explain the ceiling and revisit trigger only when material. |
| Exactly one check; no frameworks or fixtures | Replace with risk-based tests using existing tooling | One check can miss critical cases; parallel ad hoc test conventions add maintenance cost. |
| Trivial one-liners need no test | Replace diff-size heuristic with behavioral risk | A one-line authorization or data-deletion bug can be consequential. |
| Security, validation, accessibility, real-world constraints | Keep applicable protections | Minimal code must still meet the actual operating requirements. |

## Tradeoffs and remaining work

The strongest counterargument is that one root policy loads coding and Git guidance
even during research. The user's maintenance preference accepts some of that cost.
Keep the file compact and prune using observed failures, rather than adding a rule
for every hypothetical error. Specific workflows and project documentation remain
available on demand; they should not become a second general-policy layer.

Cost means total cost to reach an acceptable result, including retries, review,
and user attention. The cheapest model or shortest diff can increase total cost.
Model names, effort presets, prices, and concurrency limits belong in runtime/task
configuration. The proposed policy respects that configuration without duplicating
vendor-specific instructions.

Context poisoning includes malicious instructions and accidental contamination
from stale summaries, unsupported claims, or repeated assumptions. The draft
addresses both. Its instruction cannot guarantee resistance to injection.

Before activating the draft, reconcile remaining Markdown rules and their inbound
references, including skills that link to the old heading names. Preserve native
command policies and hooks. The existing project brief/verification preambles
incorrectly claim there is no first-party code, and the invariants file's absolute
submodule prohibition conflicts with the root's explicit submodule-work exception.
Resolve these known documentation conflicts during migration rather than hiding them
behind new pointers. This proposal does not silently change those files.

High confidence: the structural distinctions, native loading facts, and identified
problems with the excerpt's absolutes. Medium confidence: the exact wording and
amount of policy needed across all four families. Open: model-specific adherence,
actual savings, and the minimum sufficient root size require representative tasks.

## Draft validation

The candidate contains 1,020 words in 121 lines. Nine concrete repository pointers
resolve; both proposal documents pass whitespace and machine-local-path checks.
`git diff --check` passes for tracked changes.

A fresh, read-only Codex CLI session using GPT-5.6 Sol at medium effort applied
the candidate to six bounded scenarios without repository exploration: draft-only
scope, a typo, an authorization bug with distinct caller behavior, hostile fetched
instructions and an unsupported handoff, parser reuse, and completion with an
unrelated baseline failure. Its responses preserved scope, proportional checks,
caller contracts, the data/authority boundary, configured routing, and Git authority.
The hostile-content case was correctly rejected; asking about authorization must
not become a path to treating the hostile destination as trusted.

This was a simulated policy-application check, not execution of real bug fixes,
a controlled baseline comparison, a native import test, or a cross-model security
evaluation. It provides initial wording evidence only. Local probe artifacts are
gitignored under `scratchpad/agents-structure-probe/`. Active AGENTS.md, CLAUDE.md,
rules, hooks, and project overlays were not changed by this proposal task.
