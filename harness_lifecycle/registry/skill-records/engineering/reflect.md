---
skill: reflect
domain: engineering
stage: Improvement
substage: Retrospective
secondary: []
family:
aliases: []
status: active
---
# reflect

Review a session, or a sample of a delegated run's sessions, for changes to the agents' instructions, checks and tools that would have prevented its mistakes, and apply the ones the person approves. Use for /reflect; finding the cause of one failure is systematic-debugging, and reviewing a change is review.

**Boundary:** Reviews a session, or a sample of a delegated run's sessions, for changes to the agents' environment and applies the approved ones through their owners; the cause of one failure is systematic-debugging, and reviewing a change is review.

<!-- registry:generated traits -->
- `sampled-session-retros`: Retro a sample of about one in five delegated sessions, nested dispatches included, rather than every one.
- `failures-first-retro-sample`: Fill a retro sample with the sessions where something went wrong before any others.
- `environment-retro-categories`: Review a session for improvements to the agent's environment across fixed categories (navigation, automated checks, coding standards, steering files, tool economy, no-ops, information access).
- `read-existing-check-first`: Read the repo's own lint and check commands before proposing one, treating an unwired or broken check, or the absence of any guardrail, as itself the finding.
- `read-session-sources`: Read the primary sources (session logs) for the session under review, defaulting to the current one.
- `severity-ordered-proposals`: Present improvement candidates to the user in order of severity.
- `retro-in-reviewed-session`: Run a retrospective inside the session it reviews before clearing, or point it at that session's log afterwards.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/retro#environment-retro-categories** `skills/engineering/retro/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/retro#read-existing-check-first** `skills/engineering/retro/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/retro#read-session-sources** `skills/engineering/retro/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/retro#severity-ordered-proposals** `skills/engineering/retro/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/ask-matt#retro-in-reviewed-session** `skills/engineering/ask-matt/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/in-progress/chief-of-staff#sampled-session-retros** `skills/in-progress/chief-of-staff/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/in-progress/chief-of-staff#failures-first-retro-sample** `skills/in-progress/chief-of-staff/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-12` **adopt** (2026-11-12-reflect:009): Completes pending 2026-11-09-pocock-4ae2317:175: failures-first-retro-sample is written at .claude/skills/reflect/SKILL.md:20 in the ruled delivery wording, ve…
- `2026-11-12` **adopt** (2026-11-12-reflect:008): Completes pending 2026-11-09-pocock-4ae2317:174: sampled-session-retros is written at .claude/skills/reflect/SKILL.md:19 in the ruled delivery wording, verbati…
- `2026-11-12` **adopt-merged** (2026-11-12-reflect:007): Checkpoint at 5beb35b for the owner's trait rulings: 1 adopt (retro-in-reviewed-session into reflect, plan 64), 22 defer. Supersedes 2026-10-30-mattpocock_skil…
- `2026-11-12` **adopt** (2026-11-12-reflect:006): Owner ruling of 2026-11-05 §E (reflect: one skill combining retro's categories, reflect's lenses and approval, and chief-of-staff's worst-first sampling; appro…
- `2026-11-12` **adopt** (2026-11-12-reflect:005): Owner ruling of 2026-11-05 §E (reflect: one skill combining retro's categories, reflect's lenses and approval, and chief-of-staff's worst-first sampling; appro…
- `2026-11-12` **adopt** (2026-11-12-reflect:004): Owner ruling of 2026-11-05 §E (reflect: one skill combining retro's categories, reflect's lenses and approval, and chief-of-staff's worst-first sampling; appro…
- `2026-11-12` **adopt** (2026-11-12-reflect:003): Owner ruling of 2026-11-05 §E (reflect: one skill combining retro's categories, reflect's lenses and approval, and chief-of-staff's worst-first sampling; appro…
- `2026-11-12` **adopt** (2026-11-12-reflect:002): Owner ruling of 2026-11-05 §E (reflect: one skill combining retro's categories, reflect's lenses and approval, and chief-of-staff's worst-first sampling; appro…
- `2026-11-12` **add** (2026-11-12-reflect:001): Owner ruling of 2026-11-05 §E (reflect: one skill combining retro's categories, reflect's lenses and approval, and chief-of-staff's worst-first sampling; appro…
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:175) *(superseded)*: Owner ruling 2026-11-09: Prevents: A sample spent on smooth sessions while the ones that failed teach nothing. Lands in reflect, the new `reflect` skill of the…
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:174) *(superseded)*: Owner ruling 2026-11-09: Prevents: Every delegated session left unreviewed because retroing all of them costs too much. Lands in reflect, the new `reflect` ski…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-06-upstream-mattpocock_skills-4ae2317.md](../../reviews/2026-11-06-upstream-mattpocock_skills-4ae2317.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `environment-retro-categories`:
  - `mattpocock_skills:skill:skills/engineering/retro#environment-retro-categories` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `failures-first-retro-sample`:
  - `mattpocock_skills:skill:skills/in-progress/chief-of-staff#failures-first-retro-sample` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
- `read-existing-check-first`:
  - `mattpocock_skills:skill:skills/engineering/retro#read-existing-check-first` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `read-session-sources`:
  - `mattpocock_skills:skill:skills/engineering/retro#read-session-sources` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `retro-in-reviewed-session`:
  - `mattpocock_skills:skill:skills/engineering/ask-matt#retro-in-reviewed-session` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `sampled-session-retros`:
  - `mattpocock_skills:skill:skills/in-progress/chief-of-staff#sampled-session-retros` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
- `severity-ordered-proposals`:
  - `mattpocock_skills:skill:skills/engineering/retro#severity-ordered-proposals` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
