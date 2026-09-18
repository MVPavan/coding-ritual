# 10 — Assessment: vision versus what is built

An honest critique, written 2026-09-18. Opinion, clearly marked as such; the factual
claims underneath it carry citations.

## The vision, restated

From `docs/workflow-vision.md`. The motivating problem is named in its final section:
**supervisor context growth**. When every implement → review → fix exchange passes
through one model, its context fills with detail it does not need and it loses the
larger picture. The goal is that local detail stays local and supervisors receive only
outcomes and exceptions.

Everything else follows: deterministic routing so routine transitions cost no tokens;
bounded local loops so rework does not escalate; a small set of workflow families the
orchestrator picks from; roles assigned across vendors and models independently of
graph shape; parallel graphs; LLM judgment at exceptions and epic boundaries.

And one constraint, given its own section: *"Use the least custom machinery that
achieves these behaviors… implementation complexity must justify itself."*

## The verdict

**Not overengineered as a whole. Disproportionately engineered.**

About 52,000 lines of source and 67,000 lines of tests currently run one workflow
graph, one stage at a time, on one machine, triggered by hand.

The depth is nearly all in the *execution substrate* — crash recovery, process
identity, sandbox binds, evidence integrity, storage. The vision's actual subject
matter — workflow families, orchestrator assignment, parallelism, escalation — is where
the system is thin. The rigor is real and unusually high quality. It is spent at the
layer furthest from the point.

## The structural tension

The supervisor is detached: `start_new_session`, reparented to init, boot_id liveness
proofs, adopted children whose exit status is unknowable, seven recovery cases.

**And then the bridge blocks on `Foreman.run` for up to eight hours anyway.**

The concurrency that detachment buys is not being spent. Most of the hardest code in
the repository exists to handle failure modes created by a design choice whose benefit
is currently unrealized. It will pay off when graphs run concurrently. Today it is
foundation poured before the building was designed.

## Where complexity outran its justification

**The run ledger.** ADR 0005's three measured costs are real: 233 of 616 beads were
engine-written and unreadable through `bd`; each tick paid ~1.5 s across five `bd`
round trips; run knowledge was deleted unread. Tracker pollution genuinely needed
solving.

But the fix cost a second backend, 15 tables, a locator with three resolution sources,
permanent coexistence rules because claims stay in bd, export/import/verify/archive
with trust anchors, and a cross-task key-collision defect. And the latency argument is
weaker than it looks — ticks sleep 30 s while an agent works, so 1.5 s is about 5% of
an idle poll. A separate bd workspace for engine rows, or append-only JSONL per run,
would have solved pollution and unread-knowledge with a fraction of the machinery.

**The decision/children layer.** 2,242 lines, exercised by nothing. Well-designed and
anticipating real vision requirements, but built before the thing that needs it, so
none of its assumptions have met a real use.

## Where it is underengineered against the vision

1. **One graph family.** No family library, no selection mechanism.
2. **No parallelism.** Stages are strictly serial, enforced in
   `_refuse_other_admission`. The vision's central structural ask is the one thing the
   bridge forbids.
3. **The orchestrator cannot assign models.** The vision is emphatic that workflow
   shape and model assignment are separate choices. The bridge calls
   `instantiate(..., overrides={})` — it passes no overrides at all. Models come from
   role bindings in project config, fixed per graph.
4. **Gates cannot distinguish who may approve.** Authorization is by ssh key with no
   per-gate-kind policy, so "an LLM may approve triage but never ship" is
   inexpressible. Cryptographically rigorous, semantically blunt.
5. **No whole-effort review surface.** "Oversight across the whole effort" has no
   mechanism.

## What is genuinely good

The engineering judgment inside each module is excellent. The invariants are the right
ones — claim is not proof, refuse rather than guess, pin evidence before closing, two
out of three is not liveness. The comments record real incidents rather than
rationalizing them. That is rarer than good architecture and harder to retrofit.

The failure is sequencing, not skill. Each workstream deepened the substrate because
the substrate was what was in front of it, and each had a legitimate local
justification. The result is a system that could survive a datacenter losing power but
cannot yet run two stages at once or let its orchestrator pick a model.

## What to do about it

Freeze substrate work. No new backends, no deeper recovery, no extensions to
coordination.

Next increment: a second workflow family and per-stage model assignment through the
bridge — the two smallest things that make the vision's core claim testable. Then
parallel stages, which is where the existing children machinery finally earns its
2,242 lines.

## Caveat

This judgment comes from reading the code closely, not from watching the system run.
Which failure modes are over-insured is inference from structure, not operational
experience. Observed crashes should outweigh this reading.
