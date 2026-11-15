> Optional material, not a required sequence or numerical quota.
> Illustrative market claims are examples to verify before relying on them.

# Decision toolkit

Pick the one section that fits the question: an ideation lens to open options, a
judgment framework to compare them, or a decision sequence for a decision in a
known domain. Never run every section.

## Ideation lenses

Use these lenses selectively. Pick the lens that fits the idea — don't mechanically run every framework. The goal is to unlock thinking, not to follow a checklist.

### SCAMPER

A structured way to transform an existing idea by applying seven different operations:

- **Substitute:** What component, material, or process could you swap out? What if you replaced the core technology? The target audience? The business model?
- **Combine:** What if you merged this with another product, service, or idea? What two things that don't usually go together would create something new?
- **Adapt:** What else is like this? What ideas from other industries, domains, or time periods could you borrow? What parallel exists in nature?
- **Modify (Magnify/Minimize):** What if you made it 10x bigger? 10x smaller? What if you exaggerated one feature? What if you stripped it to the absolute minimum?
- **Put to other uses:** Who else could use this? What other problems could it solve? What happens if you use it in a completely different context?
- **Eliminate:** What happens if you remove a feature entirely? What's the version with zero configuration? What would it look like with half the steps?
- **Reverse/Rearrange:** What if you did the steps in the opposite order? What if the user did the work instead of the system (or vice versa)? What if you reversed the value chain?

**Best for:** Improving or reimagining existing products/features. Less useful for greenfield ideas.

### How Might We (HMW)

Reframe problems as opportunities using the "How Might We..." format:

- Start with an observation or pain point
- Reframe it as "How might we [desired outcome] for [specific user] without [key constraint]?"
- Generate multiple HMW framings of the same problem — different framings unlock different solutions

**Good HMW qualities:**
- Narrow enough to be actionable ("...help new users find relevant content in their first 5 minutes")
- Broad enough to allow creative solutions (not "...add a recommendation sidebar")
- Contains a tension or constraint that forces creativity

**Bad HMW qualities:**
- Too broad: "How might we make users happy?"
- Too narrow: "How might we add a button to the settings page?"
- Solution-embedded: "How might we build a chatbot for support?"

**Best for:** Reframing stuck thinking. When someone is anchored on a solution, pull them back to the problem.

### First Principles Thinking

Break the idea down to its fundamental truths, then rebuild from there:

1. **What do we know is true?** (not assumed, not conventional — actually true)
2. **What are we assuming?** List every assumption, even the ones that feel obvious
3. **Which assumptions can we challenge?** For each, ask: "Is this actually a law of physics, or just how it's been done?"
4. **Rebuild from the truths.** If you only had the fundamental truths, what would you build?

**Best for:** Breaking out of incremental thinking. When every idea feels like a small improvement on the status quo.

### Jobs to Be Done (JTBD)

Focus on what the user is trying to accomplish, not what they say they want:

- **Functional job:** What task are they trying to complete?
- **Emotional job:** How do they want to feel?
- **Social job:** How do they want to be perceived?

Format: "When I [situation], I want to [motivation], so I can [expected outcome]."

**Key insight:** People don't buy products — they hire them to do a job. The competing product isn't always in the same category. (Netflix competes with sleep, not just other streaming services.)

Include the competing alternatives, and doing nothing, as options the job could hire.

**Best for:** Understanding the real problem. When you're not sure if you're solving the right thing.

### Constraint-Based Ideation

Deliberately impose constraints to force creative solutions:

- **Time constraint:** "What if you only had 1 day to build this?"
- **Feature constraint:** "What if it could only have one feature?"
- **Tech constraint:** "What if you couldn't use [the obvious technology]?"
- **Cost constraint:** "What if it had to be free forever?"
- **Audience constraint:** "What if your user had never used a computer before?"
- **Scale constraint:** "What if it needed to work for 1 billion users? What about just 10?"

**Best for:** Cutting through complexity. When the idea is growing too large or too vague.

### Pre-mortem

Imagine the idea has already failed. Work backwards:

1. It's 12 months from now. The project shipped and flopped. What went wrong?
2. List every plausible reason for failure — technical, market, team, timing
3. For each failure mode: Is this preventable? Is this a signal the idea needs to change?
4. Which failure modes are you willing to accept? Which ones would kill the project?

**Best for:** Phase 2 evaluation. Stress-testing ideas that feel good but haven't been pressure-tested.

### Analogous Inspiration

Look at how other domains solved similar problems:

- What industry has already solved a version of this problem?
- What would this look like if [specific company/product] built it?
- What natural system works this way?
- What historical precedent exists?

The key is finding *structural* similarities, not surface-level ones. "Uber for X" is surface-level. "A two-sided marketplace that solves a trust problem between strangers" is structural.

**Best for:** Phase 1 expansion. Generating variations that feel genuinely different from the obvious approach.

## Judgment frameworks

Use one to three to sharpen a choice between options, not to decorate the record.

### Decision Matrix

Use for tool, product, architecture, or vendor choices.

Minimum columns: option, best fit, sacrifices, integration cost, operating cost, lock-in, risk, confidence.

Rules:
- Weight criteria by the user's constraints.
- Explain why the winner wins.
- Include "do not choose if" for each serious option.

### Build vs Buy vs Compose

Use for architecture, tooling, platform, and workflow decisions.

Ask:
- What is core product behavior vs commodity plumbing?
- What must be customized?
- What failure modes become ours if we build?
- What lock-in or missing control do we accept if we buy?
- Can composition preserve control with less maintenance?

### Root Cause Analysis

Use for operational or product problems.

Start with the observed problem. Ask why until reaching a changeable cause. If multiple causes exist, group them by people, process, technology, policy, incentives, and external constraints.

Jobs to Be Done, for product, feature and market choices, is under Ideation lenses.

## Decision sequences

Pick one sequence matched to the decision's domain; pull from a second only when the
decision truly spans domains. Steps marked **(research)** are fact-finding: call
`research` for them, or read the code when this project holds the answer. A
"recommend" step yields your recommended answer: a `proposed` row, or the
recommendation in the owner's question, never a decision by itself.

### 1. Technology or tooling decision

Use for: frameworks, SDKs, databases, queues, workflow engines, observability, hosting, LLM infrastructure.

1. Define the decision and non-negotiables.
2. List viable options and explicit exclusions.
3. **(research)** Compare current capabilities from official docs.
4. **(research)** Check integration fit, operational burden, failure modes, pricing, ecosystem maturity, and migration cost.
5. **(research)** Find practitioner evidence for real-world pain.
6. Recommend one option, a fallback, and upgrade triggers.

Frameworks: decision matrix, build vs buy vs compose, a risk register; `research` weighs ecosystem maturity and failure modes.

### 2. Developer tooling or architecture

Use for: orchestration architecture, agent harnesses, code tools, infra design, platform tradeoffs.

1. Define the workflow and correctness requirements.
2. Separate control plane, execution plane, data plane, tool plane, and human approval plane.
3. Compare build vs adopt vs compose.
4. Evaluate reliability, debuggability, security, extensibility, and operator burden.
5. **(research)** Check official docs and live source before trusting examples.
6. Recommend the smallest architecture that satisfies the real workflows.

Frameworks: build vs buy vs compose, an architecture responsibility map, a dependency budget, upgrade triggers; `research` weighs failure modes.

### 3. Problem-solving or operations

Use for: diagnosing failures, reducing cost, improving conversion, fixing workflow bottlenecks.

1. Define the measurable problem.
2. Identify symptoms vs causes.
3. **(research)** Find analogous problems and case studies.
4. Compare solution classes by evidence, cost, time, risk, and prerequisites.
5. Identify quick wins, strategic bets, and false fixes.
6. Recommend a staged path and validation metrics.

Frameworks: root cause analysis, a solution matrix; analogous inspiration under Ideation lenses.
