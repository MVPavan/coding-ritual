# Evidence Lenses

Use a lens to weigh what the sources show, not to pick an option or decorate a
report. Pick 1-3; the caller decides.

## Ecosystem Maturity

Use for SDKs, frameworks, databases, agent stacks, and infrastructure.

Find evidence for:
- Release cadence and breaking changes.
- Documentation quality.
- Issue velocity and maintainer responsiveness.
- Production references.
- Migration path and exit cost.
- Security posture and dependency footprint.

## Failure-Mode Analysis

Use for architecture, workflow engines, financial systems, compliance, and automation.

For each option the sources describe, find what they show about:
- What fails?
- How is it detected?
- Who is paged or notified?
- Can it retry safely?
- What state can corrupt?
- What human approval is required?

## Source Confidence Ladder

Use in every final report — the four levels (High / Medium / Low / Speculative) are defined in `synthesis-engine.md` § Confidence Calibration.
