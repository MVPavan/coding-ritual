# Review: pstack's Claude Code adapter

Type `skill` (README §5a). Date 2026-11-14. Bead `cr-r2pa.2.26`. Serves two of our skills, `delegation` and `reflect`; named after the adapter rather than one skill, which the owner accepted on 2026-11-14.

## Source

- Harness `cursor_plugins`, pin `2776ddd` (`2776ddd2355d6d6c8747d3964600f28daf62f049`).
- The adapter: `pstack/docs/harness/claude-code.md` (67 lines), git blob `bf154e6464a6cca96a9627bbe10a628092e8c09e` at the pin. Its copy in the generated tree, `harness/pstack/claude-code/docs/harness/claude-code.md`, is blob `bf154e6464a6cca96a9627bbe10a628092e8c09e`, the same bytes. Three rows also cite `harness/pstack/README.md`, the note on how the tree is built.
- Not a catalog capability: the scanner classifies no kind for the adapter, so its traits have no trait records, analysis or report. This review is where they are kept (option D).
- Line citations below are of the adapter at the pin unless another file is named.

## Verdict

The owner ruled every row as recommended on 2026-11-14 ("All as recommended"). 27 traits: 2 adopt, 5 already have, 1 already ruled (delivery pending), 7 defer, 12 reject, 0 out of scope.

- Our harness writes each unit once in wording that fits both hosts, and publishing fails on a line that fits only one. That choice is why most rows are rejects.
- The two adopts are not delivered. Each is delivered by an ours-side `update` on its target (`delegation`, `reflect`) whose `evidence` cites this review, so `build` lists the review in both skill records. The `reflect` edit is delivered together with the pending layout-probe edit to the same file (2026-11-13-batch-p2:159).
- The `delegation` check covers every helper whose only read-only control is its brief, Claude CLI reviewers with Bash included.
- `role-model-rule-file` was ruled before (2026-11-13-batch-p3:147) and is not delivered; it is not counted as held.

## What this review keeps, and what it does not

It keeps the evidence for every row, rejects and defers included, with each row's upstream lines, our holder and each defer's revisit condition. It gives no per-trait registry state: `status` and `TRAITS.md` do not list these rows, `gap` does not track them, and nothing brings a defer back by itself. Reconsidering a defer depends on reading this review. The new trait IDs below are defined only here, not in `trait-definitions.yaml`.

## Revisit conditions (defers)

- `search-tool-shell-fallback`: A shipped unit names a search tool for a host or worker that does not grant it.
- `resume-by-pasted-result`: A vendor we dispatch through cannot resume a worker's session.
- `local-copy-over-fetch`: A shipped unit or document links one of the harness's own files by URL.
- `host-only-step-skip-line`: A run on one host stops, asks or retries at a step that needs a feature only another host has.
- `skip-placeholder-named`: The same as host-only-step-skip-line, which this depends on.
- `bot-comments-as-forge-threads`: The babysit playbook reopens (deferred because we have no pull requests, CI or review bots, 2026-11-01-pstack-playbooks:019), as for bot-comment-three-way-triage (2026-11-13-batch-p3:060).
- `absent-review-bot-steps-skipped`: The babysit playbook reopens (2026-11-01-pstack-playbooks:019), as for review-bot-tracking (2026-11-13-batch-p3:094).

## The ruled sheet

### Adopt (2)

| Trait | What it means | What we have | Recommendation |
|---|---|---|---|
| Read-only worker: check the checkout afterward | When a helper meant to only read could still edit files, tell it not to, and afterward check the checkout against a record made before it started. | Our briefs tell read-only helpers not to edit, and our T3 and Claude CLI notes say when the brief is the only control. Nothing checks afterward. | **Adopt into `delegation`**, in two places. Before dispatch, the coordinator records `git status --short` and a checksum of every file already modified or untracked (the same record our read-only playbooks keep). After collecting, any difference outside the helper's report file is a *discrepancy pending attribution*: inspect it, report it as a breach if the helper made it, and leave alone any change that may be someone else's. If other writers shared the checkout, say the check could not attribute the change. Prevents an edit by an explorer or reviewer from slipping into the next commit. |
| Where Claude Code keeps session logs | Session logs live in a per-workspace folder whose name is the workspace path with every `/` and `.` turned into `-`. | `reflect`'s note says only `/` is turned into `-`, which is wrong for any workspace under a dotted folder (for example `.claude/worktrees/`). | **Adopt into `reflect`**: correct that line. Prevents reflect failing to find a log for such a workspace. Deliver it together with the pending layout-probe edit to the same file. |

### Already have (5)

| Trait | What it means | What we have | Recommendation |
|---|---|---|---|
| Build the shipped tree by script | Produce each install tree from one source by a script run, never as a second hand-kept copy. (From pstack's tree readme, not the adapter.) | Our plugin's skills and agents are copied from this repository by the publish script, driven by its manifest. | Already have. |
| Never hand-edit the built tree | Do not edit the generated install folder by hand. (From pstack's tree readme.) | `harness-publish` says the shipped skills and agents are build output, never edited by hand. Existing trait. | Already have. |
| Model lines kept out of the shared policy files | Never put the model-per-role lines in the shared root policy documents (`CLAUDE.md`, `AGENTS.md`); a dedicated model file is fine. | Our roster is its own untracked file, and `AGENTS.md` leaves model settings to configuration. | Already have. |
| Name the starting point of a separate checkout | A helper working in its own checkout is told which branch or commit to start from. | Recorded in our learnings after an earlier incident: name and verify the base. | Already have. |
| Read only this project's logs | Never search other projects' session logs. | `reflect` says this. | Already have. |

### Already ruled, delivery pending (1)

| Trait | What it means | Where it stands | Recommendation |
|---|---|---|---|
| Model-per-role file written by setup | Setup writes one file holding a model for each role, rewritten whole each run. | Ruled on 2026-11-13 into the planned `setup-mvp-stack`, which does not exist yet. The ruling changes the delivery: it writes our roster file and records no budget line. | Nothing new to rule. The adapter's Claude Code folder for it does not carry over, because our roster is read at each handoff. |

### Defer (7)

| Trait | What it means | What we have | Recommendation |
|---|---|---|---|
| Resume by pasting the earlier result | Where a helper cannot be resumed, start a new one with the old result pasted in. | Every vendor we use can resume a helper's own session. | Defer until a vendor we use cannot resume. |
| Read the local copy, never fetch it | If a skill links one of its own pack's files by web address and the file is installed, read the installed copy. | Our skills cite their own files by relative path; none links by web address. | Defer until one of our units links its own files by web address. |
| One-line notice for a skipped host-only step | When a step needs a feature this host lacks, say so in one line and carry on without stopping or asking. | A step that will not run stays in the todo list marked `skip: <reason>`. | Defer until a run stalls at a step needing a feature only the other host has. |
| Placeholder for what a skipped step would have made | Leave a named placeholder when a later step needs a skipped step's output. | Nothing. | Defer with the row above; it only matters once that exists. |
| Search with the shell when search tools are missing | Without the file and content search tools, search through the shell. | Shipped text may name the search tools (publishing does not block them), but every helper that names them is also given them. | Defer until a shipped unit names a search tool for a helper or host that lacks it. |
| Review-bot comments as ordinary threads | Read and answer a review bot's comments on a pull request with the forge's own commands. | Nothing; we do not drive pull requests. | Defer with the babysit playbook, like the bot rows ruled on 2026-11-13. |
| Skip bot steps when no bot is present | Skip starting, waiting for or configuring a review bot when the pull request shows no sign of it. | Nothing. | Defer with the babysit playbook. |

### Reject (12)

| Trait | What it means | What we have | Recommendation |
|---|---|---|---|
| Translation page per host | Write skills in one host's names and ship a translation page, read once per session, for each other host. | One text for both hosts, checked when we publish. | Reject: we chose the other design on purpose, and ours is checked on the text itself. |
| Pointer to the translation page in each built skill | The build adds a line to each skill pointing at its host's translation page. | No translation page exists. | Reject, with the row above. |
| Drop a setting the host lacks, and say so | Leave out a setting with no counterpart and mention it. | A model or setting the vendor does not offer stops the handoff. | Reject: dropping it would run a setup the owner did not choose. |
| Never pass a value the tool refuses | Do not send a tool a setting its definition rejects. | We check the model and settings before every handoff, which is stricter. | Reject: covered already; the tool itself refuses the rest. |
| Unknown model: use the session's model | When a model cannot run here, run the helper on the current session's model and say so. | We stop, or route the model through its own vendor, and ask the owner when the roster has nothing. | Reject: it swaps the model, which our rules forbid. |
| "inherit" means the session's model | A role marked `auto` or `inherit-parent` runs on the session's model. | We ask the owner when a role has no roster entry. | Reject. |
| Model line with a built-in default | Read a role's model from a rule file, falling back to the skill's default. | Ruled before (2026-11-03, 2026-11-13): models come from the owner's roster. | Reject, as already ruled. |
| Detect models from the tool's own list | Setup finds the usable models from what the helper tool accepts. | Ruled before (2026-11-13): models come from each vendor's own list. | Reject, as already ruled. |
| Run another skill by reading its file | Follow another skill by opening its file. | We start skills through the platform's own skill mechanism. | Reject, as already ruled. |
| Ask in plain text when the question tool is missing | Without the structured question tool, ask in the reply. | Our skills say "ask" and never name the tool; publishing enforces it. | Reject: nothing of ours depends on that tool. |
| Keep the todo list in the reply when there is no todo tool | Without a todo tool, keep and update the list in the reply. | Our skills say "the todo list" and never name a tool; publishing enforces it. | Reject: each host keeps the list with what it has. |
| Newest log is the current session | Take the newest log file in the folder as this session's. | `reflect` identifies the session by its id and never by file age. | Reject: parallel sessions share a folder, so the newest file can be another session's. |

## Row detail

### Adopt (2)

#### `unenforced-read-only-brief-and-status-check` (new ID)

- Definition: When a read-only worker's tool access still lets it write, say in its brief not to edit files and, after it returns, check the checkout against a baseline the coordinator recorded before dispatch.
- Distinct from: `enforced-read-only`, `brief-only-read-only`, `read-only-closeout`. enforced-read-only picks the vendor control and says when the brief is the only one; brief-only-read-only is only the brief; read-only-closeout is the read-only run checking itself. This adds the coordinator's check afterward, and reuses read-only-closeout's baseline (status plus a checksum per already dirty path).
- Upstream: `pstack/docs/harness/claude-code.md:21`
- Ours: Brief half held: .claude/skills/delegation/roles/explorer.md:8, roles/reviewer.md:9, roles/critic.md:8; vendors/t3/dispatch.md:18-19 and vendors/claude-cli/dispatch.md:33-36 say when the brief is the only control. Baseline form held by read-only-closeout: .claude/skills/mvp-mode/playbooks/session-pickup.md:33-34, plan.md:57-60. Check half missing: SKILL.md:65-69 (Collect) opens what a worker changed, but nothing asks for a check when a read-only worker should have changed nothing.
- Ruling: adopt, into `delegation`. Prevents: an explorer, reviewer or critic on T3, or a claude-cli reviewer with Bash, editing files unnoticed, so the edit rides into the coordinator's next commit. A status-only comparison misses a second edit to a path already ` M` or `??` (its status line does not change), and would blame the worker for a parallel writer's change; the checksum baseline and 'pending attribution' wording close both, and leaving unattributed changes in place preserves others' work (AGENTS.md:50).
- Wording at delivery: Two edits. (1) Step 4 (Dispatch), before dispatching: 'For a read-only role whose only control is its brief, first record the baseline the read-only closeout uses (`mvp-mode/playbooks/session-pickup.md` step 1): `git status --short`, plus a checksum of each path already modified or untracked.' (2) Step 6 (Collect), after 'Open what the worker changed or produced': 'For such a worker, compare with that baseline: a new or changed status line, or a changed checksum, outside its report file is a discrepancy pending attribution. Inspect it. A change the worker made is a breach to report, never kept; leave a change you cannot attribute in place, since it may be another writer's. When other writers shared the checkout during the run and the check cannot attribute a change, say so and claim only that the worker was not seen to write.'

#### `transcript-location-convention` (existing ID)

- Definition (registry): Locate past chats in a per-workspace folder of line-per-message files named from the workspace path.
- Note: Coordinate with the pending reflect adopt of transcript-located-by-layout-probe (2026-11-13-batch-p2:159), which rewrites the same reference file.
- Upstream: `pstack/docs/harness/claude-code.md:56` (~/.claude/projects/<slug>/<session>.jsonl; slug = workspace path with each `/` and `.` changed to `-`; <session>/subagents/ holds subagent transcripts)
- Ours: .claude/skills/reflect/references/session-logs.md:14-16 (path and subagents folder; says only '/' is replaced)
- Ruling: adopt, into `reflect`. Prevents: reflect failing to find a log for a workspace whose path has a dot, such as a worktree under `.claude/worktrees/` or `~/.t3/worktrees/`. This machine's Claude Code project folders show it: a workspace under a dotted folder has `--` where `/.` was. Reflect's ruling was 'take everything'; the earlier out-of-scope ruling on this trait (2026-11-06-batch-p1:174) was for recall, which keeps no path.
- Wording at delivery: session-logs.md:14: 'workspace path with each "/" and "." replaced by "-"'; reflect's traits/ours.yaml entry then lists transcript-location-convention.

### Already have (5)

#### `scripted-install-tree` (new ID)

- Definition: Build the shipped install tree from the one canonical source by a script run, never keeping it as a second hand-maintained copy.
- Distinct from: `never-edit-build-output`, `plugin-subset-invariant`. never-edit-build-output is the bar on hand edits to the built tree; plugin-subset-invariant limits what the tree may contain. This is the generation step itself.
- Upstream: `harness/pstack/README.md:3` (the tree is generated from named pstack sources); `harness/pstack/README.md:7` (run the generator script after editing the sources, then commit)
- Ours: mvp-harness/plugins/mvp-plugin/publish-manifest.txt:1-4 (what /harness-publish copies, read by scripts/publish-plugin.sh), :20-21 (`source .claude/skills -> skills`, `source .claude/agents -> agents`)
- Ruling: already have. Our plugin's skills and agents are produced by the publish script from this repository, never maintained as a second copy.

#### `never-edit-build-output` (existing ID)

- Definition (registry): Never hand-edit the shipped plugin's skills or agents, which are build output; edit plugin-owned skills and scripts in the plugin itself.
- Upstream: `harness/pstack/README.md:3` (Do not edit it by hand)
- Ours: .claude/skills/harness-publish/SKILL.md:88-90 (never edit mvp-plugin/skills/ or agents/ by hand; they are build output)
- Ruling: already have. The existing definition already covers the upstream rule for our shipped tree; no new variant is needed.

#### `roster-outside-instruction-files` (new ID)

- Definition: Keep the per-role model lines out of the shared root policy documents, in a dedicated model rule or configuration file.
- Distinct from: `role-model-rule-file`. role-model-rule-file is the whole-file writer and its file; this is only the bar on putting the lines in the shared root policy documents (upstream: CLAUDE.md and AGENTS.md). A dedicated always-loaded rule file, as the adapter itself writes, satisfies it.
- Upstream: `pstack/docs/harness/claude-code.md:42` (setup writes its own rule file in the always-loaded rules folder); `pstack/docs/harness/claude-code.md:46` (never put the role lines in CLAUDE.md or AGENTS.md)
- Ours: .claude/skills/delegation/SKILL.md:28-29 (the roster is .delegation/roster.toml, untracked); AGENTS.md:81 (runtime configuration owns model settings)
- Ruling: already have. Ours keeps the roster in its own untracked file, and the shared instructions only point at configuration.

#### `isolated-worker-named-base` (new ID)

- Definition: Name, in the brief of a worker given its own checkout, the branch or commit that checkout must start from.
- Distinct from: `worktree-base-verify`. worktree-base-verify has the worker confirm its base; this has the coordinator name it.
- Upstream: `pstack/docs/harness/claude-code.md:23`; `pstack/docs/harness/claude-code.md:25`
- Ours: .repo-context/learnings.md:20 (worker worktrees: name and verify the intended base before editing or landing)
- Ruling: already have. Ours records the same rule as a learning from an earlier incident, and it covers verification too.

#### `no-cross-project-transcript-search` (existing ID)

- Definition (registry): Never search across project transcript folders during an audit, because that exposes unrelated private conversations.
- Upstream: `pstack/docs/harness/claude-code.md:56` (read only this workspace's folder)
- Ours: .claude/skills/reflect/SKILL.md:22-23
- Ruling: already have. Adopted into reflect (2026-11-13-batch-p2:474).

### Already ruled, delivery pending (1)

#### `role-model-rule-file` (existing ID)

- Definition (registry): Write one always-loaded rule file that records a budget line and one model per role, overwritten whole on each run.
- Upstream: `pstack/docs/harness/claude-code.md:40-46` (setup-pstack writes ~/.claude/rules/pstack-models.md, no frontmatter, overwritten whole)
- Ours: Not held. Ruled adopt into setup-mvp-stack, delivery pending (2026-11-13-batch-p3:147, `pending: cr-r2pa.2.13.3`); setup-mvp-stack does not exist yet.
- Ruling: already ruled, delivery pending. Already ruled through setup-pstack, with a modified delivery: 'Write the delegation roster (`.delegation/roster.toml`) in the shape of `roster.example.toml`, one entry per role ..., rewriting the whole file from the confirmed values on each run; record no budget line' (2026-11-13-batch-p3:147). That replaces the definition's always-loaded rule file and budget line, so the source definition is not what we will hold. The adapter only adds the Claude Code location (an always-loaded rules folder), which does not carry over, because ours reads the roster at each dispatch (P3 rejected new-sessions-notice for the same reason, 2026-11-13-batch-p3:158).

### Defer (7)

#### `search-tool-shell-fallback` (new ID)

- Definition: When the host's file and content search tools are unavailable, search through the shell instead.
- Distinct from: `unreachable-data-is-gap`. unreachable-data-is-gap reports a missing tool's data as a gap; this substitutes for the search tools.
- Upstream: `pstack/docs/harness/claude-code.md:13` (no Grep/Glob: Bash with rg)
- Ours: Partly: the search tools are not audit patterns (publish-manifest.txt:39-52), so shipped text may name them; today the agents that name them also grant them (.claude/agents/docs-researcher.md:4 grants Read, Grep, Glob and :18 names them; code-reviewer.md:4, spec-reviewer.md:4, implementer.md:4 grant them).
- Ruling: defer. Unlike the question and todo tools, nothing stops a shipped unit naming the search tools, so this one could matter. Today every unit that names them also grants them, so no run can miss them.
- Revisit when: A shipped unit names a search tool for a host or worker that does not grant it.

#### `resume-by-pasted-result` (new ID)

- Definition: Where a host cannot resume a worker, start a new worker with the earlier worker's result pasted into its brief.
- Distinct from: `session-resume-followup`. session-resume-followup resumes the worker's own session.
- Upstream: `pstack/docs/harness/claude-code.md:27`
- Ours: .claude/skills/delegation/SKILL.md:53-54 (session-resume-followup); vendors/claude-cli/dispatch.md:22-23, vendors/codex-cli/dispatch.md:18-21, vendors/t3/dispatch.md:3-6 (each gives a resume path or owns follow-ups)
- Ruling: defer. Every vendor we use can resume a worker's own session, which keeps its full context. A pasted result is the fallback only for a vendor that cannot.
- Revisit when: A vendor we dispatch through cannot resume a worker's session.

#### `local-copy-over-fetch` (new ID)

- Definition: When a unit links to its own pack's file by URL and the installed pack holds that file, read the local copy and never fetch it, giving the person the URL only when they need a link.
- Upstream: `pstack/docs/harness/claude-code.md:55`
- Ours: None needed today: shipped units cite their own files by relative path (AGENTS.md:116, plain-path-references); a search of .claude/skills, .claude/agents and AGENTS.md for repository URLs finds none.
- Ruling: defer. The failure it prevents (reading a fetched upstream version that differs from the installed one) needs a URL self-link, and ours has none.
- Revisit when: A shipped unit or document links one of the harness's own files by URL.

#### `host-only-step-skip-line` (new ID)

- Definition: When a step needs a feature the host lacks, write one reply line naming the step and the reason and go on without stopping, asking or retrying; a substitute that does the step's job is not a skip and gets no line.
- Distinct from: `recorded-step-skip`. recorded-step-skip keeps the skipped step in the todo list with its reason; this adds a reply line and the no-stop rule for host gaps.
- Upstream: `pstack/docs/harness/claude-code.md:58-60`; `pstack/docs/harness/claude-code.md:64`; `pstack/docs/harness/claude-code.md:66`; `pstack/docs/harness/claude-code.md:67` (a forge command for the PR tool is not a skip)
- Ours: .claude/skills/mvp-mode/SKILL.md:48 (recorded-step-skip: 'skip: <reason>' in the todo list)
- Ruling: defer. Our units are written for both hosts, so a host-only step is rare, and the todo-list skip already keeps it visible. No run is recorded stalling on one.
- Revisit when: A run on one host stops, asks or retries at a step that needs a feature only another host has.

#### `skip-placeholder-named` (new ID)

- Definition: When a later step needs what a skipped step would have made, leave a placeholder and name it in the skip line.
- Distinct from: `real-id-wiring`. real-id-wiring forbids placeholders in tracker wiring; this allows one only for an output a host could not produce, and names it.
- Upstream: `pstack/docs/harness/claude-code.md:60`
- Ours: nothing
- Ruling: defer. It only matters once a skip line exists.
- Revisit when: The same as host-only-step-skip-line, which this depends on.

#### `bot-comments-as-forge-threads` (new ID)

- Definition: Read and answer a review bot's existing pull-request comments as ordinary review threads through the forge's own commands, not the bot's integration.
- Distinct from: `bot-comment-three-way-triage`. bot-comment-three-way-triage decides fix, dismiss or ask for each thread; this says which commands read and answer the threads when the bot's own integration is absent.
- Upstream: `pstack/docs/harness/claude-code.md:65`
- Ours: nothing
- Ruling: defer. It only serves pull-request driving, which we do not do today. The same flow's triage rows are deferred on the same condition.
- Revisit when: The babysit playbook reopens (deferred because we have no pull requests, CI or review bots, 2026-11-01-pstack-playbooks:019), as for bot-comment-three-way-triage (2026-11-13-batch-p3:060).

#### `absent-review-bot-steps-skipped` (new ID)

- Definition: Skip steps that start, wait for or configure a review bot when the pull request shows none of its checks or comments.
- Distinct from: `review-bot-tracking`. review-bot-tracking counts a present bot's passes and waits while its check is pending; this drops the bot's steps when no sign of the bot exists.
- Upstream: `pstack/docs/harness/claude-code.md:65`
- Ours: nothing
- Ruling: defer. Ruled separately from the triage row because one could triage existing comments while still waiting for a bot that is merely slow. Nothing of ours waits on a bot today.
- Revisit when: The babysit playbook reopens (2026-11-01-pstack-playbooks:019), as for review-bot-tracking (2026-11-13-batch-p3:094).

### Reject (12)

#### `host-name-adapter` (new ID)

- Definition: Write units in one host's tool, field, path and model names and ship, for each other host, one adapter file read once per session that maps every such name to that host's equivalent.
- Upstream: `pstack/docs/harness/claude-code.md:1-3`; `pstack/docs/harness/claude-code.md:5-13` tools table; `pstack/docs/harness/claude-code.md:15-28` subagent-field table; `pstack/docs/harness/claude-code.md:30-38` model table; `pstack/docs/harness/claude-code.md:50-56` paths table; `harness/pstack/claude-code/skills/*/SKILL.md` added pointer line (74/added-lines.txt)
- Ours: Provider-neutral unit text, enforced at publish: mvp-harness/plugins/mvp-plugin/publish-manifest.txt:37-56 (audit patterns and two-branch `neutral` phrases); .claude/skills/harness-publish/SKILL.md:82 (NOT NEUTRAL failure)
- Ruling: reject. Ours chose the other design on purpose. Each shipped line is written for both hosts (a neutral action, or a 'Claude Code: ... / Codex: ...' two-branch phrase), and the publish fails on a host-only name. A table read once per session must be remembered for the rest of it, while our check runs on the text itself before it ships.

#### `adapter-pointer-injected` (new ID)

- Definition: Insert into each generated unit a line pointing at its host's adapter document.
- Distinct from: `scripted-install-tree`. scripted-install-tree builds the tree; this adds a host-specific line to the units while building it.
- Upstream: `harness/pstack/claude-code/skills/*/SKILL.md` added pointer line, 23 copies (74/added-lines.txt)
- Ours: Nothing to point at: no adapter exists (host-name-adapter, rejected); shipped text is provider-neutral, publish-manifest.txt:37-56.
- Ruling: reject. It only serves an adapter, and we rejected the adapter design. Ours ships one text for both hosts, so there is no host page for a unit to point at.

#### `unmapped-field-dropped-and-said` (new ID)

- Definition: When a tool-call field or value a unit names has no counterpart on the running host, leave it out of the call and say in the reply that it was left out.
- Distinct from: `validate-selection`. validate-selection refuses an undeclared model or setting and stops the spawn; this drops the field and carries on.
- Upstream: `pstack/docs/harness/claude-code.md:3`; `pstack/docs/harness/claude-code.md:24`; `pstack/docs/harness/claude-code.md:26`; `pstack/docs/harness/claude-code.md:34` (drop -fast)
- Ours: .claude/skills/delegation/SKILL.md:40-42 (a value not on the vendor's list stops the dispatch); SKILL.md:54-55 (background dispatch phrased as a condition, not a field)
- Ruling: reject. For a model or setting, ours stops and reports, because a dropped value runs a configuration the owner did not choose. Other fields do not arise, since neutral text names the condition ('in the background when the runtime allows') and never the field.

#### `schema-valid-values-only` (new ID)

- Definition: Never pass a tool a field or value its declared schema rejects.
- Distinct from: `validate-selection`. validate-selection checks the chosen spawn values against the vendor's catalog deterministically before spawning; this is a general rule over any tool call, with no check named.
- Upstream: `pstack/docs/harness/claude-code.md:3`; `pstack/docs/harness/claude-code.md:34` (`model` takes only opus, sonnet, haiku, fable)
- Ours: .claude/skills/delegation/SKILL.md:39-42 (validate-selection, for the values we choose)
- Ruling: reject. The values we choose (model, effort, options) are already checked before dispatch, and more strictly, by validate-selection. For any other field the host refuses the invalid call and says so, so the rule would add a sentence that prevents no failure we would miss.

#### `unrunnable-model-to-session-model` (new ID)

- Definition: When a requested model is not one the host can run, leave the model unset so the worker runs on the session's model, and say so.
- Distinct from: `inherit-defaults`, `owner-roster`. inherit-defaults applies when no model was requested; owner-roster asks the owner. This replaces a requested model with the session's model.
- Upstream: `pstack/docs/harness/claude-code.md:35`
- Ours: .claude/skills/delegation/SKILL.md:29-31 (no entry and no named model: ask the owner), :40-42 (a value not on the list stops the dispatch, never a substitute), :74-80 (a model from another vendor goes through that vendor's file)
- Ruling: reject. It substitutes a model, which ours forbids. Ours routes a model from another vendor through that vendor and stops on one nobody offers; running the session's model instead would hide that the configured model never ran.

#### `inherit-defaults` (existing ID)

- Definition (registry): Inherit the session model and effort defaults when none is requested.
- Upstream: `pstack/docs/harness/claude-code.md:36` (`auto` or `inherit-parent`: omit `model`)
- Ours: .claude/skills/delegation/SKILL.md:28-31 (owner-roster)
- Ruling: reject. Ours asks the owner when a role has no roster entry and no named model; the trait files keep inherit-defaults distinct from owner-roster for this reason.

#### `role-model-config-line` (existing ID)

- Definition (registry): Read each spawned role's model from a named line of a shared configuration, falling back to a fixed default and leaving the field unset for an alias.
- Upstream: `pstack/docs/harness/claude-code.md:37` (role lines read from an always-loaded rule file; the skill's default slug when the file or line is missing)
- Ours: .claude/skills/delegation/SKILL.md:28-31
- Ruling: reject. Already ruled on this trait (2026-11-13-batch-p3:033 and 2026-11-13-batch-p2:163). Model choice goes through delegation and the owner's roster, never through a config line with a fixed default.

#### `detect-selectable-models` (existing ID)

- Definition (registry): Take the selectable models from what the helper tool accepts this session, preferring a full models list, and ask the person to paste them when none can be found.
- Upstream: `pstack/docs/harness/claude-code.md:44` (detected models are the `model` values the Agent tool schema lists)
- Ours: .claude/skills/delegation/SKILL.md:76-80 (vendor-model-list)
- Ruling: reject. Already ruled (2026-11-13-batch-p3:148). Ours takes models from each vendor's own source, falling back to a reviewed seed.

#### `sibling-skill-by-relative-path` (existing ID)

- Definition (registry): Run another skill's procedure by reading its instruction file at a path relative to the current skill and following it.
- Upstream: `pstack/docs/harness/claude-code.md:12` (Read `<pstack>/skills/<name>/SKILL.md` and follow it; the Skill tool refuses most pstack skills)
- Ours: .claude/skills/mvp-mode/SKILL.md:30-31 (platform-skill-invocation)
- Ruling: reject. Already ruled (2026-11-09-pocock-4ae2317:173, and P3). Ours invokes a skill through the platform's skill mechanism, never by reading its file.

#### `question-tool-text-fallback` (new ID)

- Definition: When the host's structured question tool is unavailable, ask the question in plain text in the reply.
- Distinct from: `unreachable-data-is-gap`. unreachable-data-is-gap reports what a missing tool could not reach; this substitutes for the tool.
- Upstream: `pstack/docs/harness/claude-code.md:10` (no AskUserQuestion in -p mode: ask in plain text)
- Ours: mvp-harness/plugins/mvp-plugin/publish-manifest.txt:45 (a shipped line naming AskUserQuestion fails without a two-branch phrase), so shipped units say 'ask' and never name the tool.
- Ruling: reject. Our units name the action, and the publish audit enforces it, so no unit depends on the question tool and there is nothing to fall back from.

#### `todo-tool-reply-list-fallback` (new ID)

- Definition: When the host has no todo tool, keep the task list in the reply and update it at each phase.
- Distinct from: `recorded-step-skip`. recorded-step-skip says what a skipped step looks like in the todo list; this says where the list lives when no todo tool exists.
- Upstream: `pstack/docs/harness/claude-code.md:11` (no TodoWrite: keep the list in the reply, update it at each phase)
- Ours: publish-manifest.txt:46 (TodoWrite is an audit pattern); .claude/skills/mvp-mode/SKILL.md:47 ('the todo list', no tool named).
- Ruling: reject. Ours says 'the todo list' without naming a tool, and the audit enforces that, so each host keeps the list with whatever it has; a stated fallback location adds nothing a run could miss.

#### `newest-log-is-current-session` (new ID)

- Definition: Take the newest session log in the workspace's log folder as the current session's.
- Distinct from: `transcript-located-by-layout-probe`. transcript-located-by-layout-probe lists the newest candidates and matches the first line to the chat's opening prompt; this takes the newest file.
- Upstream: `pstack/docs/harness/claude-code.md:56` (the newest .jsonl directly in that folder is the current session)
- Ours: .claude/skills/reflect/references/session-logs.md:8-10 (the id from CLAUDE_CODE_SESSION_ID or CODEX_THREAD_ID; modification time never identifies it)
- Ruling: reject. Ours identifies the session by its id on purpose. Several sessions often share one workspace (this repository runs parallel sessions and delegated workers), so the newest file can belong to another session.

### Not traits

- Adapter lines 1, 58 (headings and the Cursor-only list intro): no mechanism.
- Adapter lines 64 (Cursor Automations: skip with the line) and 66 (cloud agents: map to a worktree, skip dashboard steps): instances of host-only-step-skip-line and the name table, not separate traits.

## Provenance

- Mapping and sheet: `scratchpad/mvp-stack/74/adapter-mapping.yaml`, `adapter-ruling-sheet.md`, `report.md` (gitignored).
- Critics: critic-74b REVISE (five majors, three minors, all fixed in round 2), critic-74d PASS.
- Owner rulings 2026-11-14: `scratchpad/mvp-stack/owner-rulings-2026-11-13.md`, last section.
