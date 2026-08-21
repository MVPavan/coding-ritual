# The-Claude-Protocol — discipline / memory / delegation layers

Subject pin: `af754ef63535a416af4894223edda1b2c730d3c2` (2026-02-06, "feat: quick-fix escape hatch,
investigation constraints, memory writes"). All upstream paths below are relative to
`/data/codes/coding-ritual/reference_harnesses/The-Claude-Protocol/`.

Ledger status check: `harness_lifecycle/ledger.json` currently holds **zero** entries for
`The-Claude-Protocol` (repos present: agent-skills 45, mattpocock_skills 33, superpowers 16,
humanlayer_skills 10, diagram-design 6, html-artifacts 1). Nothing here has been ruled on yet
except the `react-best-practices` out-of-scope note recorded in
`harness_lifecycle/inventory/skill-buckets.md:31-33` (round-002 ruling), which is not in the ledger.

**Framing fact that colours everything below:** TCP is not a peer harness to ours. It is an
enforcement-first *orchestration product* — npm package `beads-orchestration`, distributed via
`npx skills add` (`README.md:5-17`), with a Kanban UI (`README.md:24`). Its skills are written for a
world where the main thread is forbidden to write code (`templates/CLAUDE.md`, "Your Identity":
"**Never write code**") and all implementation happens in `*-supervisor` subagents inside git
worktrees. Every mechanism below assumes that architecture. We do not have it.

---

## 1. subagents-discipline — deep dive

### 1.1 What it enforces

One logical skill, two files. Both are invoked at the start of an *implementation* task, not at
completion (`skills/subagents-discipline/SKILL.md:3`). Its thesis is stated in one line: "Test the
FEATURE, not just the component you built" (`skills/subagents-discipline/SKILL.md:8`).

Components of the root variant (158 lines):

| Component | Lines | What it does |
|---|---|---|
| Rule 1 — Look Before You Code | `:14-35` | Before coding against any external data (API/DB/file/config), run the command and read the *actual* field names/types; code against what you observed. Worked example: `information_schema` query revealing `reference_image_url` vs assumed `reference_images`. |
| Rule 2 — Test Both Levels | `:37-55` | Component test AND feature test are both required; a per-artifact table (`:44-49`) maps "API endpoint / DB change / frontend component / full-stack" to what each level means. |
| Rule 3 — Use Your Tools | `:57-65` | Before claiming you can't test: enumerate available MCP servers, use any that can verify. "I couldn't test" is valid only after exhausting options. |
| DEMO block (required) | `:69-82` | A fixed output format — COMPONENT{Command, Result} + FEATURE{Steps, Result} — that must accompany every completion. |
| PARTIAL escape | `:84-110` | A structured way to declare incomplete verification (Verified / Needs human check / Why), plus an explicit whitelist: acceptable = no browser automation, rate-limited external API, job > 5 min, unmockable prod data (`:106-110`); **not** acceptable = "server wasn't running", "no test data", "would take too long" (`:101-104`). |
| Epic-child contract | `:113-121` | If BEAD_ID contains a dot, fetch the epic's design doc via `bd show {EPIC_ID} --json \| jq -r '.[0].design'` and match it exactly. |
| Completion checklist | `:125-133` | 5 boxes: looked at real data, component test, feature test or valid PARTIAL, DEMO block, used available tools. |
| Red flags | `:137-147` | "This should work…", "I assume the field is…", "I'll test it later", "It's too simple to break", and the pre-announcement flags "Done! / Fixed! / Should work now!". |
| Bottom line | `:150-158` | "Component test passing ≠ feature works; curl 200 ≠ UI displays correctly; TypeScript compiles ≠ user can use it." |

### 1.2 Variant diff (root vs templates)

`skills/subagents-discipline/SKILL.md` (158 lines) vs `templates/skills/subagents-discipline/SKILL.md`
(127 lines). Same `name:` frontmatter, different `description:` — "Invoke at the start of any
implementation task to enforce verification-first development" (`skills/…:3`) vs "Core engineering
principles for implementation tasks" (`templates/…:3`).

**Templates-only content:**
- **Rule 0 — Read the Bead First** (`templates/…:8-25`): run `bd show {BEAD_ID}` and `bd comments
  {BEAD_ID}`; the orchestrator's dispatch prompt is auto-logged as a DISPATCH comment carrying
  investigation findings, root cause with file/function/line, related files, gotchas. "Don't
  re-investigate" (`:23`). If no context comment exists, **ask the orchestrator before proceeding**
  (`:25`).
- **Rule 4 — Log Your Approach (Optional)** (`:94-107`): `bd comment {BEAD_ID} "APPROACH: …"` when
  you deviated from the suggested fix or picked among valid solutions. Explicitly "not enforced"
  (`:107`).
- **Rule 2 reframed** as "Test Functionally (Close the Loop)" (`:50-84`): the organising principle
  becomes *fastest way to verify*, with a fast-vs-slow table (`:54-60`) that ranks `curl`/run-the-CLI
  above writing tests, two named strategies (User Journey Tests `:64-74`, Component Tests as
  regression supplement `:76-79`), and a good/bad pair: "Curled endpoint with invalid auth, got 401
  as expected" vs "Wrote tests, they compile" (`:83-84`).

**Root-only content (dropped in templates):** the entire DEMO block section (`skills/…:69-82`), the
PARTIAL policy with its acceptable/unacceptable lists (`:84-110`), the completion checklist
(`:125-133`), the "Bottom line" (`:150-158`), the "This catches:" line after Rule 1 (`:22`), and the
sentence "Design docs ensure all pieces fit together. If you deviate, integration fails."
(`:121`). Rules 1 and 3 are byte-identical in substance; Red Flags are identical minus the
"about to say Done!/Fixed!" clause, which the templates variant drops (`skills/…:145-147` has no
counterpart).

**Which is newer:** the templates copy, by 11 days. Git history for the two paths:
- root: last touched `5221da3` 2026-01-20 "refactor: slim down subagents-discipline skill (870 → 158 lines)".
- templates: last touched `a0bc7f7` 2026-01-31 "feat: v2.0 — co-pilot architect, voluntary knowledge, dispatch auto-logging"; the two share `5221da3` as a common ancestor.

**Which is stronger — my judgment, and it splits.** The newer templates variant is stronger on
*orchestration wiring* (Rule 0 makes the worker consume the coordinator's investigation instead of
redoing it; Rule 4 records the deviation) and stronger on *verification philosophy* (close-the-loop
beats DEMO-block bureaucracy, and the "wrote tests, they compile" anti-example is sharp). It is
**materially weaker on evidence discipline**: it deleted the only artefact that made the claim
checkable (the DEMO block), the only structured way to declare partial verification, and the
completion checklist. The upstream author appears to have moved enforcement from skill text into
hooks — `templates/settings.json:52-58` wires `validate-completion.sh` on `SubagentStop`, and
`templates/hooks/inject-discipline-reminder.sh:19-25` injects "invoke `/subagents-discipline`" only
for `*-supervisor` dispatches.

**That migration is incomplete, and it is the skill's biggest hole.** Read
`templates/hooks/validate-completion.sh`: it blocks on completion-report *format* (`:54-59`),
presence of a `bd comment` (`:66-73`), worktree existence (`:75-84`), uncommitted changes
(`:86-93`), branch pushed (`:95-106`), bead status == `inreview` (`:108-117`), and response
verbosity ≤ 15 lines / 800 chars (`:119-129`). It never checks for a DEMO block, test output, or any
evidence that the feature was exercised. So the root variant's claim "Every completion must include
evidence. Code reviewer will verify this." (`skills/…:71`) is, at this pin, mechanically unenforced —
the hook enforces git hygiene, not verification.

### 1.3 Head-to-head vs `.claude/rules/core/03-coding-discipline.md` + `verification-before-completion`

**What they have that we lack (mechanism level):**

1. **Pre-coding empiricism (Rule 1).** Our discipline rule's nearest line is "Read exports, immediate
   callers, and shared utilities before adding code" (`.claude/rules/core/03-coding-discipline.md`,
   §Think before coding) — that is *static* code reading. TCP demands you *execute* something to
   observe the real shape of external data before writing code against it. Our
   `verification-before-completion` is a post-hoc gate: it proves the claim after the fact and would
   never catch an assumed-column-name bug earlier than the failing test. Genuine gap; small but real.
2. **A feature/integration level that is mandatory, not implied.** Our claim→evidence table
   (`.claude/skills/verification-before-completion/SKILL.md:29-39`) is keyed by *claim* ("Tests pass",
   "Bug fixed"), and every row can be satisfied by unit-level evidence. Nothing in our gate says "the
   integrated feature must have been exercised the way a user would". TCP's Rule 2 says exactly that
   and gives a per-artifact table for what it means (`skills/…:44-49`). Our `systematic-debugging`
   Phase 1 ladder (`.claude/skills/systematic-debugging/SKILL.md:39-48`) has the same spirit — build a
   loop at whatever seam reaches the bug, curl/CLI/scripted-client — but that only fires on a *bug*,
   not on new feature work.
3. **A named format for partial verification.** TCP's `FEATURE: PARTIAL` with Verified / Needs human
   check / Why, plus a whitelist of acceptable excuses (`skills/…:88-110`). Our rule says "Fail loud:
   'completed' is wrong if anything was skipped silently" (`03-coding-discipline.md`, §Judgment and
   honesty) but gives no shape for the honest partial report. Format beats exhortation.
4. **"Check your tools before claiming you can't test" (Rule 3, `skills/…:57-65`).** We have no
   equivalent anywhere; our gate implicitly assumes a runnable command exists.
5. **Rule 0's "don't re-investigate, consume the dispatch context"** (`templates/…:8-25`) — a
   worker-side counterpart to our coordinator-side `.claude/rules/core/01-delegation.md` ("Pass the
   exact task, files, invariants, and verification commands they need"). We state the coordinator's
   obligation; TCP also states the worker's obligation to use it and to *stop and ask* when context is
   missing (`templates/…:25`).

**What we have that they lack:**

- Commands come from a declared source of truth, never invented
  (`verification-before-completion/SKILL.md:15-16` → `verification.md` / `invariants.md`). TCP's DEMO
  block accepts whatever command the agent felt like running.
- Read the **exit status** and **count the failures**; "a skim is a skip" (`:19-20`). TCP's DEMO block
  asks only for "Result: [what you observed]".
- Freshness: the claim must live in the same message as the run that proves it (`:8-10`) — TCP has no
  freshness rule.
- `git status` before presenting completion (`:22-23`).
- A "Not sufficient" column that names the near-miss for each claim (`:29-39`).
- **Red-green proof** for fixes: fails with the fix reverted, passes restored (`:36`, `:41-44`). TCP
  has nothing like it.
- **"The agent said success" → the diff is the evidence** (`:37`, `:51`, `:61`). TCP's whole model is
  the orchestrator trusting supervisor reports plus a git-hygiene hook.
- Binding by *meaning*, not wording, and a rationalizations table (`:8-10`, `:54-64`).
- Trigger breadth: our gate also fires before committing, opening a PR, or closing a bead (`:3`);
  TCP's fires at the end of an implementation task only.

**Is it a substitute?** No. `harness_lifecycle/inventory/skill-buckets.md:148-149,258` places it in
family `completion-gate` with relation **substitutes** against `verification-before-completion`. On
the evidence, that relation is **too generous and should be corrected to `complements` (or
`overlaps`)**. Reasons: (a) it fires at task *start* and governs how you build
(`skills/…:3`), which is why the same file also lists it in bucket 4 (`skill-buckets.md:149` "Also in
4"); (b) its evidence model is strictly weaker than ours on every axis that matters — freshness, exit
status, declared commands, git status, red-green, agent-report skepticism; (c) it is welded to
beads/worktree/supervisor mechanics (`templates/…:8-25`, `skills/…:113-121`) that do not transfer.
The correct call is reject-as-a-skill, borrow 2–3 mechanisms into files we already own.

**Quality gripes (mine):** the PARTIAL policy leaves a 2–5 minute grey zone — "if < 2 minutes, do it"
(`skills/…:104`) vs "Job takes > 5 minutes" as acceptable (`:108`); "Code reviewer will verify this"
(`:71`) is unbacked at this pin; and the templates variant's Rule 2 table (`templates/…:54-60`) ranks
`curl` above writing a test in a way that, absent our red-green rule, licenses "I ran it once and it
looked right" as proof of a fix.

---

## 2. Memory architecture — what the scripts actually do

### 2.1 Write path (cited from the hook, not the doc)

`templates/hooks/memory-capture.sh`, wired as `PostToolUse` on `Bash` with `timeout: 10`
(`templates/settings.json:45-50`):

- Bails unless `tool_name == "Bash"` (`:13`), the command matches `bd\s+comment\s+` (`:20`) **and**
  contains the literal `LEARNED:` (`:21`).
- Extracts BEAD_ID by `sed` on the command string with char class `[A-Za-z0-9._-]` (`:24`); extracts
  the comment body by stripping a leading quote after the ID and a trailing quote (`:28`), capped at
  4096 chars, then content capped at 2048 (`:36`).
- `key` = `learned-` + slug of the first 60 chars of content (`:42-43`).
- `source` = `supervisor` if the hook's `cwd` contains `.worktrees/`, else `orchestrator` (`:46-51`).
- `tags` = the type plus any match from a **hardcoded** keyword list: `swift swiftui appkit menubar
  api security test database networking ui layout performance crash bug fix workaround gotcha
  pattern convention architecture auth middleware async concurrency model protocol adapter scanner
  engine` (`:57-60`).
- Appends one JSON line to `${CLAUDE_PROJECT_DIR}/.beads/memory/knowledge.jsonl` (`:88-93`); rotates
  when > 1000 lines by moving the oldest 500 into `knowledge.archive.jsonl` (`:96-102`).

**Fragility, in fact form.** The capture is a regex parse of a *command string*, so it only fires for
one narrow spelling. `bd comment "$ID" "LEARNED: …"` fails the `[A-Za-z0-9._-]` class at `:24` and is
dropped by the guard at `:25`. A heredoc body, a `-m`-flag form, or a multi-line comment defeats the
quote-stripping at `:28`. Writes are append-only with no dedupe (dedupe is read-side only,
`recall.sh:116-119`). And the whole thing is voluntary: the doc says so explicitly, and confirms the
`SubagentStop` hook does **not** check for knowledge contributions
(`docs/memory-architecture.md:82-84`).

**Doc-vs-implementation drift (fact).** `recall.sh:21` tells the user entries come from "INVESTIGATION:
or LEARNED: prefixes", `recall.sh:51` advertises `--type learned|investigation`, and `recall.sh:65`
counts `"type":"investigation"` entries — but `memory-capture.sh:32-37` can only ever set
`TYPE="learned"`. The investigation path is dead. `docs/memory-architecture.md:27-29` lists only
`LEARNED:`, so the doc and the script disagree with each other's sibling.

The hardcoded tag list including `swift swiftui appkit menubar` (`memory-capture.sh:57`) is direct
evidence this was extracted from one Swift/macOS project and never generalised. Tags are therefore
noise in any non-Swift repo.

### 2.2 Read path

`templates/hooks/session-start.sh` (`SessionStart`, `templates/settings.json:59-64`) is only ~15%
memory. In order it: warns if the main working tree is dirty, on the premise that "Agents should only
work in .worktrees/" (`:22-30`); scans `.worktrees/bd-*` and prints cleanup commands for branches
merged into main (`:35-48`); lists the user's open PRs via `gh` (`:53-60`); prints `bd list --status
in_progress` / `bd ready` / `bd blocked` / `bd stale --days 3`, each head-limited (`:67-96`); and only
then reads `knowledge.jsonl` — `tail -20` piped to `jq -s` that groups by key, takes `max_by(.ts)`,
sorts desc, and prints the top 5 with a `recall.sh` hint (`:106-119`). Note the dedupe window is the
last 20 lines only (`:113`), which the doc describes loosely as "the 5 most recent deduplicated
entries" (`docs/memory-architecture.md:62`).

`templates/memory/recall.sh` is a grep-over-JSONL search: `--stats` (`:62-77`), `--recent N`
(`:80-87`), and default keyword search via `grep -i "$QUERY"` over the raw JSON lines (`:102`),
optional `--type` filter by literal JSON substring (`:106`), then jq dedupe by key with latest-ts
winning (`:116-119`). Because the grep runs over the raw line, a query also matches `key`, `tags`,
`source` and `bead` fields, and metacharacters are interpreted as a BRE (no `-F`). Requires `jq`.

### 2.3 Versus ours

Ours is two-surface and manual. `.claude/project/learnings.md:1-14` defines a strict entry shape —
`## <short title> (<YYYY-MM-DD>)` with `Observed:` / `Why it matters:` / `Apply:` — and a hard capture
bar: "Capture only after a verified fix or a repeated pattern — not speculation." The file is 72
lines today. Durable non-work knowledge lives in `MEMORY.md`, and `.beads/beads.md:13-16` explicitly
**bans** `bd remember` / `bd memories`, drawing the line "bd = work items only; MEMORY.md = durable
knowledge". Our `SessionStart` surface is `.claude/hooks/bd-prime.sh:25` (`bd prime --hook-json`) plus
`harness-staleness-nudge.sh` (`.claude/settings.json:25-39`).

**Comparison, my judgment.** Their system optimises for *zero-friction capture at volume* and pays for
it in quality: no bar on what gets written, no structure beyond one free-text `content` field, and
auto-tagging that is wrong outside Swift. Ours optimises for *quality per entry* and pays for it in
recall: nothing surfaces a learning unless an agent chooses to open the file. At 72 lines that trade
is currently correct — a JSONL store with grep search is machinery for hundreds of entries we do not
have, and adopting it would collide head-on with the `MEMORY.md`-only ruling in `.beads/beads.md:13-16`.

**Worth stealing:** one thing, and it is small — **provenance fields**. Their entries carry `source`
(which agent wrote it) and `bead` (which work item produced it)
(`docs/memory-architecture.md:50-54`). Our learnings entries carry a date and nothing else
(`learnings.md:8-13`), so a reader cannot trace an entry back to the task that verified it. Adding one
optional `Source:` line to the format is a two-line edit with real durable value. Everything else here
— the capture hook, the JSONL store, `recall.sh`, the session-start knowledge block — I would reject.

---

## 3. mcp-provider-delegator

### 3.1 What it is (fact)

A Python MCP stdio server (`mcp>=1.0.0`, `pyyaml`, `requires-python >=3.11`, version 0.1.0 —
`pyproject.toml:5-13`) exposing **exactly one tool**, `invoke_agent`, with an enum of five agents:
`scout, scribe, code-reviewer, detective, architect` (`src/mcp_provider_delegator/server.py:30-59`).

Flow: `AGENT_TEMPLATES_PATH` (default `.claude/agents`) is read at import time (`server.py:20-22`);
`AgentLoader.load_agent` reads `<name>.md`, splits YAML frontmatter from body via regex, and returns
`name/model/description/tools/skills/system_prompt` (`agent_loader.py:51-79`). The system prompt and
the task prompt are concatenated with an optional `TASK_ID:` header (`provider_client.py:241-243`) and
sent down a two-provider chain (`provider_client.py:296-322`):

- **Codex** — subprocess `codex exec -m <model> --sandbox workspace-write <prompt>`
  (`provider_client.py:92-100`), with model mapping haiku→`gpt-5.1-codex-mini`,
  sonnet→`gpt-5.2-codex`, opus→`gpt-5.1-codex-max` (`:78-82`).
- **Gemini** — subprocess `gemini -p <prompt> -m gemini-3-flash-preview -y`, where `-y` is
  "Auto-approve tool calls for agentic execution" (`:138-145`).

Rate limits are detected by substring-matching stderr against `["rate limit", "429", "too many
requests", "usage limit", "quota exceeded"]` (`:59-69`). If both fail: for `code-reviewer` only, the
chain returns `success=True` with the body `"SKIPPED: All providers rate limited. Task skipped."`
(`:266-272`, allow_skip set at `:314-315`); for every other agent it returns a
`PROVIDER_FALLBACK_REQUIRED` text blob containing a suggested `Task(subagent_type=…, model=…,
prompt="PROVIDER_FALLBACK: …")` call (`:276-293`, `:32-36`). A companion hook
`enforce-codex-delegation.sh` normally *blocks* direct `Task()` calls for read-only agents and lets
them through only when the prompt contains the literal `PROVIDER_FALLBACK` (`README.md:101-116`) —
note that hook is described in the README but is **not present** in `templates/hooks/` at this pin.

### 3.2 Maturity — poor

- **Tests:** 4 files, 150 lines total (`test_agent_loader.py` 26, `test_integration.py` 38,
  `test_provider_client.py` 58, `test_server.py` 28). Of those, 4 tests are
  `@pytest.mark.integration` requiring live Codex/Gemini CLIs
  (`test_provider_client.py:35,48`; `test_integration.py:6,23`). Real offline coverage is: model
  mapping (`test_provider_client.py:13-18`), the `allow_skip` boolean (`:21-32`), template load +
  missing-file (`test_agent_loader.py:10-26`), tool registration, and a smoke test whose assertions
  are `result[0].text` is truthy and `isinstance(..., str)` (`test_server.py:14-28`).
- **The central logic is untested.** `ProviderChain.invoke` — the fallback ordering, rate-limit
  branch, skip branch, and hint construction, i.e. the entire reason this package exists — has no
  test with mocked providers.
- **No config discipline:** `pyproject.toml` has no `[tool.pytest.ini_options]`, so the
  `integration` marker is unregistered; no ruff/mypy config; no lockfile-verified CI. The only
  workflow is `.github/workflows/release.yml`, tag-triggered, which creates a GitHub release and
  publishes to npm — **nothing runs these tests in CI**.
- Dataclasses throughout rather than validated models (`agent_loader.py:12-21`,
  `provider_client.py:18-46`); `frontmatter["name"]`/`["model"]` are unguarded KeyErrors
  (`agent_loader.py:73-75`) despite the docstring promising `ValueError` for invalid frontmatter.
- README calls the setup "configurable" but `create_provider_chain` hardcodes both providers
  (`provider_client.py:309-312`), and the fallback subagent map hardcodes another harness's names,
  including `"code-reviewer": "superpowers:code-reviewer"` (`:179-185`).

**Two findings I would call blocking if this were ours:**

1. **Declared tool restrictions are parsed and then discarded.** `AgentTemplate.tools` is populated
   (`agent_loader.py:76`) and never read again anywhere in `server.py` or `provider_client.py`. The
   test fixture `tests/fixtures/scout.md:5-8` declares `tools: [Read, Glob, Grep]` — a read-only
   agent — yet every invocation runs `codex exec … --sandbox workspace-write`
   (`provider_client.py:98`), i.e. with write access to the workspace. A read-only agent contract is
   silently upgraded to read-write.
2. **Review can silently evaporate.** `allow_skip` is true only for `code-reviewer`
   (`provider_client.py:314-315`), and the skip returns `success=True` (`:266-272`). Under provider
   rate limits, the one agent whose job is to catch defects is the one agent the system is willing to
   skip while reporting success.

### 3.3 Place in our harness — none

`CLAUDE.md` §Independent critique and `.claude/project/tools.md:11,17-26` retire Codex in this repo
(2026-08-14 ruling, low quota) and route critique to a **spawned critic subagent**, fresh context,
separate from the implementer, model chosen by the user, findings returned numbered
BLOCKER/MAJOR/MINOR with `file:line`. A Codex-primary provider router is a direct contradiction of
that ruling. Secondary blockers: it targets agent names we do not have (`server.py:44` vs our
implementer / code-reviewer / spec-reviewer / docs-researcher roster in `tools.md:30-38`); it depends
on a `gemini` CLI we do not use; it requires an MCP server, a Python package, and a companion
enforcement hook that is not even shipped at this pin; and `tools.md:13-14` records that this repo has
no package-install step at all. **Reject, unconditionally.** The only idea with any transfer value —
"declare a fallback when the preferred critique route is unavailable" — is one sentence of policy, and
our policy already says it (ask the user which model serves as critic).

---

## 4. react-best-practices — out-of-scope call confirmed

Confirmed, with one qualification. The skill is 487 lines across 8 numbered sections, sourced from
Vercel Engineering / `vercel-labs/agent-skills` (`templates/skills/react-best-practices/SKILL.md:9`),
and its own priority order is "Eliminating Waterfalls > Bundle Size > Server-Side > Client-Side >
Re-renders > Rendering > JS Perf > Advanced" (`:25`). Sections 1–6 and 8 are irreducibly
React/Next-specific — Suspense boundaries (`:81`), RSC serialization (`:187`), `React.cache()`
(`:238`), `after()` (`:250`), SWR (`:274`), `useEffectEvent` (`:452`), CSS `content-visibility`
(`:362`). The **only** UI-independent residue is §7 "JavaScript Performance", explicitly marked
"Impact: LOW-MEDIUM" (`:402`): build Set/Map index maps instead of `Array.includes` in a filter
(`:404-413`), prefer `toSorted()` over mutating `sort()` (`:415-423`), and early-return from
validation loops (`:425-443`). All three are elementary, all three are JavaScript/TypeScript, and this
repo has no first-party JS/TS application code — `tools.md:9` lists Node only for the private,
unpublished `codex-adapter`. So there is nothing here worth extracting even from the UI-independent
slice. The `out-of-scope` marking in `skill-buckets.md:31-33,113` stands, and it should get an
explicit ledger entry (it currently has none) so `gap.py` stops re-surfacing it.

---

## 5. Borrow candidates — ranked, smallest first

Default is reject/defer; these are the only four I would even argue for.

| # | What exactly | Effort | Attach point | Risk |
|---|---|---|---|---|
| **B1** | **A `FEATURE` / integration row and a PARTIAL escape in our claim→evidence table.** One row — "Feature works end-to-end" → requires the integrated path exercised the way a user hits it, *not sufficient*: component/unit test green — plus a 3-line PARTIAL format (Verified / Needs human check / Why) with the acceptable-vs-unacceptable reason lists compressed to one line each. Source: `skills/subagents-discipline/SKILL.md:37-55,84-110`. | ~12 lines | `.claude/skills/verification-before-completion/SKILL.md`, table at `:29-39` + a short section after `:44` | Low. Closes a real hole (our gate is satisfiable by unit evidence alone) without touching the gate's structure. Main risk is table bloat — keep it to one row. |
| **B2** | **Provenance line in the learnings format.** Add an optional `Source: <bead-id / task / session>` line to the entry template. Source: `docs/memory-architecture.md:50-54` (`bead`, `source` fields). | ~2 lines | `.claude/project/learnings.md:8-13` header block | Very low. Purely additive; does not touch the `MEMORY.md`-only ruling in `.beads/beads.md:13-16`. |
| **B3** | **"Look before you code" as one bullet in our discipline rule.** "Before coding against external data (API, DB, file, config), run the command and read the actual field names and types — code against what you observed, not what the docs or your memory say." Source: `skills/subagents-discipline/SKILL.md:14-22`. | 1 bullet | `.claude/rules/core/03-coding-discipline.md`, §Think before coding | Low, but note this rule is always-loaded context — every line costs. Justifiable only as a single bullet; do not import the worked example. |
| **B4** *(defer)* | **Worker-side context obligation:** a worker that receives a dispatch with no investigation context must stop and ask rather than re-investigate. Source: `templates/skills/subagents-discipline/SKILL.md:8-25`. | 1 bullet | `.claude/rules/core/01-delegation.md` (currently states only the coordinator's obligation) | Low value today — our execution skill already curates dispatch context — but it is the one asymmetry in our delegation rule. Defer until a real case shows workers re-investigating. |

Explicitly **not** borrowing: the DEMO block format (our claim→evidence table is strictly stronger and
adding a second required format creates two competing completion rituals); `bd comment "LEARNED:"`
capture plus the JSONL/recall machinery (collides with `.beads/beads.md:13-16`, and 72 lines of
learnings do not need grep-over-JSONL); `session-start.sh`'s knowledge block (our SessionStart already
runs `bd prime`); `validate-completion.sh` (enforces worktree/push/bead-status hygiene we deliberately
do not automate — see `CLAUDE.md` §Git Safety and `.beads/beads.md` "Conservative git authority");
Rule 3's MCP-enumeration advice (we have a documented routing table in `tools.md:28-40`).

---

## 6. Verdict recommendation per capability

| Capability | Verdict | One-sentence reasoning |
|---|---|---|
| `subagents-discipline` (both variants, one logical skill) | **adopt-in-part** (skill rejected; borrow B1, B3) | Its completion evidence model is strictly weaker than `verification-before-completion` on freshness, exit status, declared commands, `git status`, red-green, and agent-report skepticism, and it is welded to bead/worktree/supervisor mechanics we do not run — but its mandatory feature-level test, its PARTIAL format, and its look-at-the-real-data rule fill genuine holes in our two files. |
| `react-best-practices` | **out-of-scope** (record in ledger) | Seven of eight sections are React/Next-specific and the eighth (`:400-444`) is three elementary JS tips for a repo with no first-party JS/TS code, so the round-002 UI ruling (`skill-buckets.md:31-33`) is correct and just needs a ledger entry. |
| `templates/hooks/memory-capture.sh` | **reject** | Voluntary, string-parse-fragile capture (breaks on `"$ID"`, heredocs, `-m` forms) with a Swift-specific hardcoded tag vocabulary (`:57`), writing a free-text store that our `MEMORY.md` + `learnings.md` split already covers with a higher quality bar. |
| `templates/memory/recall.sh` | **reject** | grep-over-JSONL search is machinery for hundreds of entries; `learnings.md` is 72 lines and greppable as-is, and the script advertises an `investigation` type the capture hook can never produce (`recall.sh:21,51,65` vs `memory-capture.sh:32-37`). |
| `templates/hooks/session-start.sh` | **reject** (borrow nothing; B2 is from the doc, not this script) | 85% of it is worktree/PR/bead status that `bd prime --hook-json` (`.claude/hooks/bd-prime.sh:25`) and our staleness nudge already cover, and the remaining knowledge block depends on the rejected capture pipeline. |
| `mcp-provider-delegator` | **reject** | It is a Codex-primary router in a repo that formally retired Codex (`tools.md:11,17-26`), it is immature (central `ProviderChain.invoke` untested, no CI running its tests), it discards declared agent tool restrictions while forcing `--sandbox workspace-write` (`provider_client.py:98` vs `agent_loader.py:76`), and it treats a skipped code review as success (`:266-272`). |

**Overall grade on this layer of TCP: C-.** The discipline skill has three good ideas and one
unenforced ritual; the memory system is a plausible design whose implementation drifted from its own
documentation and never left its origin project; the delegator is a prototype that contradicts our
standing ruling and ships two safety defects. Net extractable value from ~900 lines of upstream
material: roughly 15 lines of edits to two files we already own.
