---
skill: prose-pass
domain: core
stage: X
substage: Communication
secondary: []
family: 
aliases: []
status: active
---
# prose-pass

Use to edit a reply or document a person will read, removing patterns that make it read as machine-written. Skip agent-facing text, which authoring-for-agents owns, and code, commands and quotations.

**Boundary:** Edits a reply or document a person will read, keeping its meaning; agent-facing text is authoring-for-agents, a standalone rendered page is html-artifact, shaping replies for an ADHD reader is i-have-adhd, and folding decisions into design documents is design-evolve.

<!-- registry:generated traits -->
- `meaning-preserved-edit`: Change wording only, never facts, citations or code.
- `confidence-language-kept`: Keep the tier words and hedges that mark uncertainty when editing a finished answer.
- `ing-phrase-cut`: Delete tacked-on present-participle phrases that claim significance, or back them with real sources.
- `vague-attribution-cut`: Name the source of any claim credited to unnamed groups, or delete the claim.
- `name-the-mechanism`: Rewrite a sentence that conveys an impression so that it states a mechanism or number, cutting it if it cannot become an instruction, fact or figure.
- `filler-phrase-cut`: Shorten wordy stock phrases and delete empty announcements of importance.
- `chatbot-phrase-cut`: Remove assistant pleasantries, offers of further help and excited discovery lines.
- `sycophancy-cut`: Remove praise and agreement openers and answer directly.
- `generic-conclusion-cut`: Replace optimistic sign-offs with specific plans or facts.
- `tell-vocabulary-swap`: Replace a fixed list of overused elevated words with plain ones.
- `plain-is-has`: Use is or has in place of grand verbs standing in for them.
- `plain-word`: Use the common word over a fancier synonym.
- `synonym-cycling-cut`: Keep one term for one referent instead of rotating through synonyms.
- `local-metaphor-noun-swap`: Replace figurative pseudo-technical nouns with concrete words, keeping those that name real things in this repository.
- `not-just-but-cut`: Replace the construction that denies one thing to promote another with a direct statement of the point.
- `forced-triplet-cut`: List as many items as naturally exist, never forcing a group of three.
- `false-range-cut`: Replace a from-to construction that has no real scale with a direct list.
- `hedge-stack-trim`: Reduce piled-up qualifiers to a single modal.
- `dense-sentence-split`: Split or trim any sentence the reader must reread to parse.
- `active-voice`: Name the actor in place of a passive, keeping passive only when the actor is unknown or does not matter.
- `adverb-cut`: Cut an adverb, using a stronger verb or the measured figure in its place.
- `mannered-prose-cut`: Replace aphorisms, rhetorical fragments, personified code, figurative verbs and stock framing with literal phrasing.
- `over-compression-fix`: Restore articles, verbs and whole sentences, and spell out arrows, symbols and abbreviations.
- `no-em-dash`: Use no em dashes, ending the sentence or using a comma or parentheses to separate a thought.
- `mid-sentence-colon-cut`: Keep colons for lists and examples, rewriting mid-sentence uses and the comparison framing around them.
- `bold-restraint`: Do not bold every proper noun or acronym.
- `inline-header-list-convert`: Turn bullets whose bold label merely restates the line into prose, keeping a period-ended label followed by new detail.
- `sentence-case-headings`: Write headings in sentence case.
- `no-decorative-emoji`: Remove ornamental emoji from headings and bullets.
- `straight-quotes`: Replace typographic quotation marks with straight ones.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **cursor_plugins:skill:pstack/skills/why#confidence-language-kept** `pstack/skills/why/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#meaning-and-tone-preserved** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#ing-phrase-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#vague-attribution-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#tell-vocabulary-swap** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#plain-is-has** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#not-just-but-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#forced-triplet-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#synonym-cycling-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#false-range-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#em-dash-ban** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#mid-sentence-colon-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#bold-restraint** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#inline-header-list-convert** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#sentence-case-headings** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#no-decorative-emoji** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#straight-quotes** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#chatbot-phrase-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#sycophancy-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#filler-phrase-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#hedge-stack-trim** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#generic-conclusion-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#metaphor-noun-swap** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#name-the-mechanism** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#dense-sentence-split** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#active-voice** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#adverb-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#plain-word** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#mannered-prose-cut** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/unslop#over-compression-fix** `pstack/skills/unslop/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **adopt** (2026-11-01-batch-1:233): Completes pending 2026-11-01-batch-1:188: over-compression-fix is written at .claude/skills/prose-pass/SKILL.md:49, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:232): Completes pending 2026-11-01-batch-1:187: mannered-prose-cut is written at .claude/skills/prose-pass/SKILL.md:48, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:231): Completes pending 2026-11-01-batch-1:186: plain-word is written at .claude/skills/prose-pass/SKILL.md:35, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:230): Completes pending 2026-11-01-batch-1:185: adverb-cut is written at .claude/skills/prose-pass/SKILL.md:47, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:229): Completes pending 2026-11-01-batch-1:184: active-voice is written at .claude/skills/prose-pass/SKILL.md:46, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:228): Completes pending 2026-11-01-batch-1:183: dense-sentence-split is written at .claude/skills/prose-pass/SKILL.md:45, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:227): Completes pending 2026-11-01-batch-1:181: name-the-mechanism is written at .claude/skills/prose-pass/SKILL.md:25, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:226): Completes pending 2026-11-01-batch-1:180: local-metaphor-noun-swap is written at .claude/skills/prose-pass/SKILL.md:37, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:225): Completes pending 2026-11-01-batch-1:179: generic-conclusion-cut is written at .claude/skills/prose-pass/SKILL.md:29, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:224): Completes pending 2026-11-01-batch-1:178: hedge-stack-trim is written at .claude/skills/prose-pass/SKILL.md:44, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:223): Completes pending 2026-11-01-batch-1:177: filler-phrase-cut is written at .claude/skills/prose-pass/SKILL.md:26, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:222): Completes pending 2026-11-01-batch-1:176: sycophancy-cut is written at .claude/skills/prose-pass/SKILL.md:28, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:221): Completes pending 2026-11-01-batch-1:175: chatbot-phrase-cut is written at .claude/skills/prose-pass/SKILL.md:27, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:220): Completes pending 2026-11-01-batch-1:174: straight-quotes is written at .claude/skills/prose-pass/SKILL.md:59, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:219): Completes pending 2026-11-01-batch-1:173: no-decorative-emoji is written at .claude/skills/prose-pass/SKILL.md:58, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:218): Completes pending 2026-11-01-batch-1:172: sentence-case-headings is written at .claude/skills/prose-pass/SKILL.md:57, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:217): Completes pending 2026-11-01-batch-1:171: inline-header-list-convert is written at .claude/skills/prose-pass/SKILL.md:56, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:216): Completes pending 2026-11-01-batch-1:170: bold-restraint is written at .claude/skills/prose-pass/SKILL.md:55, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:215): Completes pending 2026-11-01-batch-1:169: mid-sentence-colon-cut is written at .claude/skills/prose-pass/SKILL.md:54, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:214): Completes pending 2026-11-01-batch-1:168: no-em-dash is written at .claude/skills/prose-pass/SKILL.md:53, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:213): Completes pending 2026-11-01-batch-1:167: false-range-cut is written at .claude/skills/prose-pass/SKILL.md:43, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:212): Completes pending 2026-11-01-batch-1:166: synonym-cycling-cut is written at .claude/skills/prose-pass/SKILL.md:36, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:211): Completes pending 2026-11-01-batch-1:165: forced-triplet-cut is written at .claude/skills/prose-pass/SKILL.md:42, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:210): Completes pending 2026-11-01-batch-1:164: not-just-but-cut is written at .claude/skills/prose-pass/SKILL.md:41, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:209): Completes pending 2026-11-01-batch-1:163: plain-is-has is written at .claude/skills/prose-pass/SKILL.md:34, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:208): Completes pending 2026-11-01-batch-1:162: tell-vocabulary-swap is written at .claude/skills/prose-pass/SKILL.md:33, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:207): Completes pending 2026-11-01-batch-1:161: vague-attribution-cut is written at .claude/skills/prose-pass/SKILL.md:24, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:206): Completes pending 2026-11-01-batch-1:160: ing-phrase-cut is written at .claude/skills/prose-pass/SKILL.md:23, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:205): Completes pending 2026-11-01-batch-1:159: meaning-preserved-edit is written at .claude/skills/prose-pass/SKILL.md:15, read against its definition (T5).
- `2026-11-01` **adopt** (2026-11-01-batch-1:204): Completes pending 2026-11-01-batch-1:046: confidence-language-kept is written at .claude/skills/prose-pass/SKILL.md:16, read against its definition (T5).
- `2026-11-01` **adopt-merged** (2026-11-01-batch-1:194): Checkpoint at 4dd1d05 for the owner's trait rulings: 29 adopt, 2 reject.
- `2026-11-01` **adopt** (2026-11-01-batch-1:188) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:62.
- `2026-11-01` **adopt** (2026-11-01-batch-1:187) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:61.
- `2026-11-01` **adopt** (2026-11-01-batch-1:186) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:60.
- `2026-11-01` **adopt** (2026-11-01-batch-1:185) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:59.
- `2026-11-01` **adopt** (2026-11-01-batch-1:184) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:58.
- `2026-11-01` **adopt** (2026-11-01-batch-1:183) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:57.
- `2026-11-01` **adopt** (2026-11-01-batch-1:181) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:56.
- `2026-11-01` **adopt** (2026-11-01-batch-1:180) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md, into `local-metaphor-noun-swap`. Upstream: SKILL.md:52.
- `2026-11-01` **adopt** (2026-11-01-batch-1:179) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:48.
- `2026-11-01` **adopt** (2026-11-01-batch-1:178) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:47.
- `2026-11-01` **adopt** (2026-11-01-batch-1:177) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:46.
- `2026-11-01` **adopt** (2026-11-01-batch-1:176) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:42.
- `2026-11-01` **adopt** (2026-11-01-batch-1:175) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:41.
- `2026-11-01` **adopt** (2026-11-01-batch-1:174) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:37.
- `2026-11-01` **adopt** (2026-11-01-batch-1:173) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:36.
- `2026-11-01` **adopt** (2026-11-01-batch-1:172) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:35.
- `2026-11-01` **adopt** (2026-11-01-batch-1:171) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:34.
- `2026-11-01` **adopt** (2026-11-01-batch-1:170) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:33.
- `2026-11-01` **adopt** (2026-11-01-batch-1:169) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:32.
- `2026-11-01` **adopt** (2026-11-01-batch-1:168) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md, into `no-em-dash`. Upstream: SKILL.md:31.
- `2026-11-01` **adopt** (2026-11-01-batch-1:167) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:27.
- `2026-11-01` **adopt** (2026-11-01-batch-1:166) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:26.
- `2026-11-01` **adopt** (2026-11-01-batch-1:165) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:25.
- `2026-11-01` **adopt** (2026-11-01-batch-1:164) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:24.
- `2026-11-01` **adopt** (2026-11-01-batch-1:163) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:23.
- `2026-11-01` **adopt** (2026-11-01-batch-1:162) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:22.
- `2026-11-01` **adopt** (2026-11-01-batch-1:161) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:18.
- `2026-11-01` **adopt** (2026-11-01-batch-1:160) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:17.
- `2026-11-01` **adopt** (2026-11-01-batch-1:159) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md, into `meaning-preserved-edit`. Upstream: SKILL.md:9.
- `2026-11-01` **adopt** (2026-11-01-batch-1:046) *(superseded)*: Owner ruling 2026-11-01: Lands in prose-pass, SKILL.md. Upstream: SKILL.md:88.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `active-voice`:
  - `cursor_plugins:skill:pstack/skills/unslop#active-voice` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `adverb-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#adverb-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `bold-restraint`:
  - `cursor_plugins:skill:pstack/skills/unslop#bold-restraint` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `chatbot-phrase-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#chatbot-phrase-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `confidence-language-kept`:
  - `cursor_plugins:skill:pstack/skills/why#confidence-language-kept` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `dense-sentence-split`:
  - `cursor_plugins:skill:pstack/skills/unslop#dense-sentence-split` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `false-range-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#false-range-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `filler-phrase-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#filler-phrase-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `forced-triplet-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#forced-triplet-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `generic-conclusion-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#generic-conclusion-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `hedge-stack-trim`:
  - `cursor_plugins:skill:pstack/skills/unslop#hedge-stack-trim` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `ing-phrase-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#ing-phrase-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `inline-header-list-convert`:
  - `cursor_plugins:skill:pstack/skills/unslop#inline-header-list-convert` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `local-metaphor-noun-swap`:
  - `cursor_plugins:skill:pstack/skills/unslop#metaphor-noun-swap` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `mannered-prose-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#mannered-prose-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `meaning-preserved-edit`:
  - `cursor_plugins:skill:pstack/skills/unslop#meaning-and-tone-preserved` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `mid-sentence-colon-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#mid-sentence-colon-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `name-the-mechanism`:
  - `cursor_plugins:skill:pstack/skills/unslop#name-the-mechanism` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `no-decorative-emoji`:
  - `cursor_plugins:skill:pstack/skills/unslop#no-decorative-emoji` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `no-em-dash`:
  - `cursor_plugins:skill:pstack/skills/unslop#em-dash-ban` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `not-just-but-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#not-just-but-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `over-compression-fix`:
  - `cursor_plugins:skill:pstack/skills/unslop#over-compression-fix` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `plain-is-has`:
  - `cursor_plugins:skill:pstack/skills/unslop#plain-is-has` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `plain-word`:
  - `cursor_plugins:skill:pstack/skills/unslop#plain-word` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `sentence-case-headings`:
  - `cursor_plugins:skill:pstack/skills/unslop#sentence-case-headings` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `straight-quotes`:
  - `cursor_plugins:skill:pstack/skills/unslop#straight-quotes` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `sycophancy-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#sycophancy-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `synonym-cycling-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#synonym-cycling-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `tell-vocabulary-swap`:
  - `cursor_plugins:skill:pstack/skills/unslop#tell-vocabulary-swap` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `vague-attribution-cut`:
  - `cursor_plugins:skill:pstack/skills/unslop#vague-attribution-cut` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
