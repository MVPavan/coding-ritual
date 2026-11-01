---
skill: systematic-debugging
domain: engineering
stage: Building
substage: Diagnosis
secondary: []
family: debugging
aliases: []
status: active
---
# systematic-debugging

Use to find the cause of a failure when it is unclear, after a fix did not hold, or for a flaky or production-only failure; it reports a diagnosis and changes no production code. To fix a reported bug end to end, run the bug-fix playbook instead; it calls this skill.

**Boundary:** Finds the cause of an unclear failure, a failed fix or flaky behaviour; slowness or resource use against a target is performance-optimization.

<!-- registry:generated traits -->
- `reproduction-preferred`: Seek a reproduction that shows the reported failure, not a nearby one, before diagnosing, but when none is obtainable confirm a cause by independent evidence such as traces instead. (Reuses an existing failing test or command first, otherwise builds the smallest useful reproduction.)
- `unproven-without-reproduction`: When no reproduction is obtainable, continue safe source analysis and qualify any resulting fix as unproven.
- `loop-construction`: Build the reproduction in the form that fits the failure: a focused test, CLI fixture, captured trace or isolated scratch harness.
- `minimize-to-discriminate`: Minimize a reproduction only as far as needed to distinguish the candidate causes.
- `flake-reproduction`: For a flaky or production-only failure, diagnose its flake class and raise the reproduction rate until the loop is debuggable, using an order-dependent-test finder for test pollution.
- `environmental-cause-unresolved`: Claim an environmental root cause only after every hypothesis is falsified, report it as an unresolved finding with the investigation attached, and never present a mitigation as the fix.
- `hypotheses`: Form explicit hypotheses about the cause before probing any of them.
- `discriminating-observation`: Choose an observation that discriminates between the live hypotheses instead of generating a fixed number of them.
- `localized-probing`: Probe the suspected boundary or variable and repeat only while new evidence appears, using cross-layer tracing, working-versus-broken comparison or bisection to find the failing layer.
- `critic-escalation`: When hypotheses run out, get a critic review and pass it artifacts — the reproduction, its output and the attempts — rather than conclusions.
- `diagnosis-only`: Change no production code beyond temporary instrumentation, so the deliverable is a diagnosis and not a fix.
- `diagnosis-status`: Return one diagnosis with one status: confirmed (the cause, the evidence that confirms it and the verification limit), provisional (any unconfirmed cause that is not unresolved, reproducible or not, with the reproduction if any, the analysis, the remaining hypotheses, the discriminating evidence requested and any proposed fix labelled unproven) or unresolved (an environmental or external cause, with its investigation and no mitigation offered as the fix).
- `caller-deferrable-cleanup`: Before answering, remove the temporary instrumentation you added, unless the caller says its own closeout removes it; then leave it in place and list it.
- `preserve-reproducers`: Keep useful reproducers and user artifacts when cleaning up after a fix.
- `tagged-debug-logs`: Tag every debug log with a unique prefix so cleanup is a single search.
- `suspect-the-observation`: When a check fails unexpectedly, test the observation method before concluding the system is wrong.
- `why-chain`: Ask why at each step of a failure until the answer is a wrong decision in the code rather than a consequence of an earlier one.
- `legitimate-state-test`: Before guarding where a symptom surfaced, decide whether the triggering state is legitimate: handle a legitimate state there, and trace an illegitimate one to what produced it.
- `persisted-state-suspect`: When a failure appears only after a restart, suspect persisted state (configuration, caches, lock files, serialized state) first.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/debugging-and-error-recovery** `skills/debugging-and-error-recovery/SKILL.md` @ 7676817
- **superpowers:skill:skills/systematic-debugging** `skills/systematic-debugging/SKILL.md` @ 44c9b2d
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#reproduction-first** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#tighten-loop** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#reproduce-and-minimize** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#one-variable-at-a-time** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.9)
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#tagged-debug-logs** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#baseline** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.9)
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#perf-bisection** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#prove-the-red** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.9)
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#regression-check** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#missing-seam-finding** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.9)
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#closeout** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#falsifiable-hypotheses** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.9)
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#placeholder-sensitive-data-redaction** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.9)
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#credential-env-indirection** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.9)
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#loop-construction** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/diagnosing-bugs#preferred-reproduction-order** `skills/engineering/diagnosing-bugs/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **cursor_plugins:skill:pstack/skills/principle-fix-root-causes#owning-layer-fix** `pstack/skills/principle-fix-root-causes/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-fix-root-causes#why-chain** `pstack/skills/principle-fix-root-causes/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-fix-root-causes#legitimate-state-test** `pstack/skills/principle-fix-root-causes/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-fix-root-causes#persisted-state-suspect** `pstack/skills/principle-fix-root-causes/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
- **cursor_plugins:skill:pstack/skills/principle-prove-it-works#suspect-the-observation** `pstack/skills/principle-prove-it-works/SKILL.md` @ 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-01` **update** (2026-11-01-principles-fixes:001): The restart heuristic (persisted-state-suspect, delivered by 2026-11-01-cursor_plugins-pstack-principles:217) moves from references/localization.md into the sk…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:218): Completes pending 2026-11-01-cursor_plugins-pstack-principles:098: the principles build (cr-r2pa.1.2) delivered suspect-the-observation in systematic-debugging…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:217): Completes pending 2026-11-01-cursor_plugins-pstack-principles:044: the principles build (cr-r2pa.1.2) delivered persisted-state-suspect in systematic-debugging…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:216): Completes pending 2026-11-01-cursor_plugins-pstack-principles:043: the principles build (cr-r2pa.1.2) delivered legitimate-state-test in systematic-debugging, …
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:215): Completes pending 2026-11-01-cursor_plugins-pstack-principles:041: the principles build (cr-r2pa.1.2) delivered why-chain in systematic-debugging, checked whol…
- `2026-11-01` **update** (2026-11-01-cursor_plugins-pstack-principles:139): Withdraws the owning-layer-fix adoption that :039 recorded into this skill by mistake; AGENTS.md provides the trait (:137). The skill never listed it.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:098) *(superseded)*: Lands as a skill or playbook trait. No holder; it matters when a check fails unexpectedly, which is debugging's entry. One clause in systematic-debugging's rep…
- `2026-11-01` **defer** (2026-11-01-cursor_plugins-pstack-principles:046): Lands as a skill or playbook trait. A review heuristic more than a debugging step; our owning-fix rule already rejects workarounds that hide symptoms.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:044) *(superseded)*: Lands as a skill or playbook trait. No holder; a cheap, high-yield heuristic. Fits systematic-debugging's references/localization.md rather than the skill body.
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:043) *(superseded)*: Lands as a skill or playbook trait. The bug-fix gate says a change that hides the symptom is not a fix, but gives no test for when a guard is the real fix. The…
- `2026-11-01` **reject** (2026-11-01-cursor_plugins-pstack-principles:042): Lands as a skill or playbook trait. Not listed by any holder, so not covered. systematic-debugging labels hypotheses as provisional, chooses a discriminating o…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:041) *(superseded)*: Lands as a skill or playbook trait. Ours probes until evidence stops; it never states when the causal chain ends (a wrong decision, not a consequence). One cla…
- `2026-11-01` **reject** (2026-11-01-cursor_plugins-pstack-principles:040): Lands as a skill or playbook trait. Variant via reproduction-preferred. systematic-debugging seeks a reproduction first, but when none is obtainable it continu…
- `2026-11-01` **adopt** (2026-11-01-cursor_plugins-pstack-principles:039) *(superseded)*: Lands as covered. AGENTS.md: fix at the owning layer and inspect callers.
- `2026-10-31` **update** (2026-10-31-mvp-mode:012): Restates 2026-10-31-mvp-mode:011 without its evidence path to an ignored scratch file. Trait list corrected: reproduction-first (adopted from diagnosing-bugs, …
- `2026-10-31` **update** (2026-10-31-mvp-mode:011) *(superseded)*: Trait list corrected: reproduction-first (adopted from diagnosing-bugs, 2026-10-30-mattpocock_skills-5beb35b:216) is replaced by its conditional variant reprod…
- `2026-10-31` **update** (2026-10-31-mvp-mode:006): Restates 2026-10-31-mvp-mode:003 with durable evidence: its pilot record was an ignored scratch file, now docs/workstreams/skill-curation/bug-fix-pilot.md (cri…
- `2026-10-31` **update** (2026-10-31-mvp-mode:003) *(superseded)*: Bug-fix pilot: the skill now reports a diagnosis and changes no production code beyond temporary instrumentation; fixing, its proof and hardening moved to the …
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:570): Checkpoint at 5beb35b for the owner's trait rulings: 17 adopt, 13 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:245): Same mechanism, looser and deliberate: SKILL.md:14-17 lists candidate forms by fit rather than order, which suits the failure at hand (S-03).
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:244): Ours builds the reproduction as a focused test, CLI fixture, captured trace or scratch harness to fit the failure.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:243): Ours keeps secrets out of reports (SKILL.md:51) but never says how to keep credentials out of commands it shows; environment-variable indirection closes that, …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:242): Ours keeps secrets out of reports (SKILL.md:51) but leaves out personal data, saved artifacts and the masking technique; placeholders for secrets and personal …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:238): Ours labels hypotheses (SKILL.md:19-20) but does not require each to name what would confirm or refute it, which is what makes the discriminating observation c…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:237): Owner deferred the report's reject recommendation, to review the set later: Ours already requests missing evidence when it cannot diagnose (SKILL.md:35-36), an…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:235): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:234): Owner deferred the report's reject recommendation, to review the set later: Ours states the observable condition for skipping the extended investigation (an ob…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:233): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours continues safe source analysis without a reproduction, where …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:231): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours deliberately preserves useful reproducers and user artifacts …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:230): Ours removes temporary instrumentation and records cause, proving check and remaining limits.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:229): Ours makes the regression check conditional on feasibility (SKILL.md:29) and records remaining limits (SKILL.md:54), but never names an unreachable seam as an …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:228): Ours turns the failure into a durable regression check, shows failure before and success after, then reruns the original scenario.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:227): Ours shows failure before the fix (SKILL.md:29-30) but has no guard against a forced red that never took effect; one sentence closes a real false-proof failure…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:226): Owner deferred the report's reject recommendation, to review the set later: An absolute tool preference fixes a context-dependent routine choice (U-01, S-08); …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:225): Same mechanism, looser and deliberate (SKILL.md:38-40); bisection stays available in localization.md:71-85.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:224): Ours asks for comparable timing evidence for a performance regression (SKILL.md:38) without saying the baseline is taken before the fix; one clause makes the o…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:223): Ours tags every instrumentation line with a unique prefix and finds it again with one grep.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:222): Ours probes the suspected boundary or variable (SKILL.md:21) but never limits a probe to one change, so a probe that moves two things cannot attribute the resu…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:221): Owner deferred the report's reject recommendation, to review the set later: Ours keeps no ranked hypothesis list to show (SKILL.md:19-20), and a mid-investigat…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:220): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours chooses a discriminating observation instead of generating a …
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:219): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours deliberately continues safe source analysis or instrumentatio…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:218): Same mechanism, looser and deliberate (SKILL.md:17): extra shrinking past discrimination costs time without changing the diagnosis.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:217): Same purpose, looser: flake-rate raising is in non-reproducible-bugs.md:30-35, and SKILL.md:17 bounds minimisation effort to what discriminates causes.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:216): Ours reuses or builds the smallest reproduction and confirms it shows the reported failure, not a nearby one.
- `2026-08-14` **adopt** (2026-10-14-migration:157): Adopted-absorbed into the rebuilt systematic-debugging skill (2026-08-14, evidence: skill-comparisons/debugging-loop/, per casebook bucket-06 round-001 absorb …
- `2026-08-14` **adopt-merged** (2026-10-14-migration:136): Adopted as the SPINE of the rebuilt systematic-debugging skill (2026-08-14, evidence: skill-comparisons/debugging-loop/, implementing casebook bucket-06 round-…
- `2026-08-14` **adopt** (2026-10-14-migration:126): Re-recorded 2026-08-14, superseding the stale 2026-07-15 'covered by our workflow' claim which held only at step-name level (evidence: skill-comparisons/debugg…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:052) *(superseded)*: The only skill that makes building a reliable reproduction the skill itself, with a checkable phase-one exit: one command, already run at least once, that show…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/debugging-loop](../../../archive/skill-comparisons/debugging-loop/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `closeout`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#closeout` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-10-31)
- `flake-reproduction`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#tighten-loop` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `legitimate-state-test`:
  - `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#legitimate-state-test` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `localized-probing`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#perf-bisection` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `loop-construction`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#loop-construction` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#preferred-reproduction-order` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `minimize-to-discriminate`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#reproduce-and-minimize` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `owning-layer-fix`:
  - `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#owning-layer-fix` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe; withdrawn 2026-11-01)
- `persisted-state-suspect`:
  - `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#persisted-state-suspect` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `regression-check`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#regression-check` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-10-31)
- `reproduction-first`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#reproduction-first` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-10-31)
- `suspect-the-observation`:
  - `cursor_plugins:skill:pstack/skills/principle-prove-it-works#suspect-the-observation` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
- `tagged-debug-logs`:
  - `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#tagged-debug-logs` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `why-chain`:
  - `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#why-chain` (adopted at 4dd1d05818d19792e7cd6e818f1667f95f7e1dbe)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#observe-not-guess` (reject): Lands as a skill or playbook trait. Not listed by any holder, so not covered. systematic-debugging labels hypotheses as provisional, chooses a discriminating o…
- `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#reproduction-first` (reject): Lands as a skill or playbook trait. Variant via reproduction-preferred. systematic-debugging seeks a reproduction first, but when none is obtainable it continu…
- `cursor_plugins:skill:pstack/skills/principle-fix-root-causes#workaround-comment-smell` (defer): Lands as a skill or playbook trait. A review heuristic more than a debugging step; our owning-fix rule already rejects workarounds that hide symptoms.
- `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#ask-when-redaction-blinds` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours already requests missing evidence when it cannot diagnose (SKILL.md:35-36), an…
- `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#debugger-first` (defer): Owner deferred the report's reject recommendation, to review the set later: An absolute tool preference fixes a context-dependent routine choice (U-01, S-08); …
- `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#delete-debug-prototypes` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours deliberately preserves useful reproducers and user artifacts …
- `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#escalate-unreproducible` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours continues safe source analysis without a reproduction, where …
- `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#fixed-hypothesis-count` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours chooses a discriminating observation instead of generating a …
- `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#hypothesis-ranking-presentation` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours keeps no ranked hypothesis list to show (SKILL.md:19-20), and a mid-investigat…
- `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#justified-phase-skip` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours states the observable condition for skipping the extended investigation (an ob…
- `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#phase1-completion-criterion` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours deliberately continues safe source analysis or instrumentatio…
- `mattpocock_skills:skill:skills/engineering/diagnosing-bugs#read-domain-docs-first` (defer): Owner deferred the report's reject recommendation, to review the set later: ROUTED: AGENTS.md:93-94 routes domain terminology and ADRs, and AGENTS.md:26 surfac…
<!-- /registry:generated declined -->
