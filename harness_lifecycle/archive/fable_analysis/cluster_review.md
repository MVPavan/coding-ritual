# Cluster Review — Fable analysis

One entry per primary cluster: composition, worker-verdict mix, and the
coordinator's decision with reasoning. Decisions and priorities are mirrored
in `final_synthesis.md`; every source row remains traceable via `clusters.json`.

## C01 — Code review lenses & change quality

- **n:** 29 · **kinds:** agent:15, command:5, plugin:3, rule:2, skill:4 · **avg score:** 3.74
- **worker verdicts:** adopt 1, merge 17, rewrite 1, defer 3, reject_after_review 7
- **strongest members:** agent:codereviewer, agent:performancereviewer, agent:apicontractreviewer
- **decision:** `merge` · **priority:** P0

Largest quality cluster. The lens agents (correctness-reviewer 4.83 avg, reliability-reviewer 4.83, maintainability-reviewer 4.67) are excellent but duplicate one another and our own reviewer; the santa-loop convergence idea is worth a note in the review skill. Python-specific reviewers overlap our rules.

## C02 — PR feedback resolution & triage

- **n:** 5 · **kinds:** agent:2, command:1, skill:2 · **avg score:** 3.93
- **worker verdicts:** merge 1, rewrite 1, defer 3
- **strongest members:** agent:prcommentresolver, agent:previouscommentsreviewer, skill:receivingcodereview
- **decision:** `defer` · **priority:** P2

Small, high-quality, low current relevance.

## C03 — Code simplification & cleanup

- **n:** 5 · **kinds:** agent:3, command:1, plugin:1 · **avg score:** 2.97
- **worker verdicts:** rewrite 2, reject_after_review 3
- **strongest members:** agent:codesimplicityreviewer, command:refactorclean, plugin:codesimplifier
- **decision:** `merge` · **priority:** P2

Redundant surfaces; keep ours, absorb boundary language.

## C04 — Planning, requirements & product discovery

- **n:** 24 · **kinds:** agent:6, command:7, skill:11 · **avg score:** 3.47
- **worker verdicts:** adopt 3, merge 10, defer 1, reject_after_review 10
- **strongest members:** skill:brainstorming, skill:planning, agent:codearchitect
- **decision:** `merge` · **priority:** P1

Solid cluster with real ideas; most rejects are prp/rpi duplicates of workflows we already run via phase-execution.

## C05 — Plan / spec / design document review

- **n:** 17 · **kinds:** agent:9, command:1, skill:7 · **avg score:** 4.05
- **worker verdicts:** adopt 3, merge 8, rewrite 1, defer 1, reject_after_review 4
- **strongest members:** agent:specreviewer, agent:feasibilityreviewer, agent:projectstandardsreviewer
- **decision:** `merge` · **priority:** P1

The single richest source of borrowable review IP in the survey.

## C06 — Implementation execution workflows

- **n:** 13 · **kinds:** agent:2, command:5, plugin:1, rule:2, skill:3 · **avg score:** 3.38
- **worker verdicts:** adopt 1, merge 4, reject_after_review 8
- **strongest members:** agent:implementer, command:codeximplement, skill:executingplans
- **decision:** `reject_after_review` · **priority:** P3

Confirms our existing execution stack; nothing here beats it.

## C07 — Workstreams, tasks & issue tracking

- **n:** 22 · **kinds:** agent:1, command:5, hook:1, plugin:2, skill:13 · **avg score:** 3.74
- **worker verdicts:** adopt 7, merge 1, rewrite 1, defer 3, reject_after_review 10
- **strongest members:** skill:runphases, skill:beads, command:runphases
- **decision:** `adopt_as_is` · **priority:** P1

Self-audit outcome: our Beads-based stack scored highest in its own cluster.

## C08 — Debugging & root-cause analysis

- **n:** 9 · **kinds:** agent:2, command:2, skill:5 · **avg score:** 3.7
- **worker verdicts:** adopt 1, merge 6, defer 1, reject_after_review 1
- **strongest members:** skill:systematicdebugging, command:codexdiagnose, skill:agentintrospectiondebugging
- **decision:** `merge` · **priority:** P1

Coherent cluster, clear local owner.

## C09 — Testing, TDD & regression

- **n:** 16 · **kinds:** agent:5, command:2, rule:3, skill:6 · **avg score:** 3.3
- **worker verdicts:** adopt 1, merge 5, rewrite 1, reject_after_review 9
- **strongest members:** skill:testdrivendevelopment, agent:testengineer, agent:testingreviewer
- **decision:** `merge` · **priority:** P2

Mostly redundant with ours; the review-of-tests lenses are the durable bit.

## C10 — Verification before completion

- **n:** 7 · **kinds:** command:2, hook:1, skill:4 · **avg score:** 4.05
- **worker verdicts:** adopt 3, merge 1, reject_after_review 3
- **strongest members:** skill:verificationbeforecompletion, command:checkinvariants, skill:checkinvariants
- **decision:** `adopt_as_is` · **priority:** P1

Self-audit: our verification doctrine is confirmed best-of-cluster.

## C11 — Browser automation & E2E QA

- **n:** 9 · **kinds:** agent:1, command:1, mcp:1, plugin:1, skill:5 · **avg score:** 3.63
- **worker verdicts:** adopt 1, rewrite 1, defer 3, reject_after_review 4
- **strongest members:** skill:agentbrowser, skill:browserqa, mcp:playwright
- **decision:** `defer` · **priority:** P2

Good tools, wrong time.

## C12 — Security review & baselines

- **n:** 26 · **kinds:** agent:3, command:2, hook:11, plugin:1, rule:6, skill:3 · **avg score:** 3.36
- **worker verdicts:** adopt 2, merge 9, rewrite 2, defer 6, reject_after_review 7
- **strongest members:** rule:pythonsafety, agent:securitylensreviewer, agent:securityauditor
- **decision:** `merge` · **priority:** P0

Highest-leverage adoption target in the whole analysis.

## C13 — Safety guardrails (destructive actions & data)

- **n:** 11 · **kinds:** hook:10, skill:1 · **avg score:** 3.45
- **worker verdicts:** adopt 1, merge 2, rewrite 4, reject_after_review 4
- **strongest members:** hook:blockgeneratededitssh, hook:blockgeneratededitspy, hook:blockdangerouscommandssh
- **decision:** `adapt` · **priority:** P1

Classic 'borrow the pattern, not the file' cluster.

## C14 — Edit/commit-time quality gates

- **n:** 12 · **kinds:** command:1, hook:10, skill:1 · **avg score:** 3.31
- **worker verdicts:** merge 4, rewrite 3, reject_after_review 5
- **strongest members:** command:qualitygate, hook:prewritedocwarnjs, hook:posteditaccumulatorjs
- **decision:** `adapt` · **priority:** P2

Cheap wins if kept tiny.

## C15 — Hook infrastructure & authoring

- **n:** 24 · **kinds:** command:6, hook:10, plugin:1, rule:3, skill:4 · **avg score:** 3.31
- **worker verdicts:** rewrite 3, defer 8, reject_after_review 13
- **strongest members:** command:configure, command:hookifylist, command:hookifyhelp
- **decision:** `defer` · **priority:** P3

Over-engineering relative to our five hooks.

## C16 — Observability & notifications

- **n:** 19 · **kinds:** hook:14, plugin:2, skill:3 · **avg score:** 3.05
- **worker verdicts:** adopt 1, defer 2, reject_after_review 16
- **strongest members:** skill:sessionreport, hook:aftershellexecutionjs, hook:autotmuxdevjs
- **decision:** `reject_after_review` · **priority:** P3

Session-report (5.0, ours) is the one keeper — already local.

## C17 — Context, cost & model routing

- **n:** 13 · **kinds:** command:3, hook:2, rule:2, skill:6 · **avg score:** 3.12
- **worker verdicts:** merge 2, rewrite 2, defer 3, reject_after_review 6
- **strongest members:** skill:strategiccompact, command:contextbudget, hook:suggestcompactjs
- **decision:** `defer` · **priority:** P3

Mostly solved a platform level.

## C18 — Memory, learning & knowledge continuity

- **n:** 26 · **kinds:** agent:3, command:10, hook:3, mcp:2, plugin:1, skill:7 · **avg score:** 3.12
- **worker verdicts:** adopt 1, merge 6, defer 3, reject_after_review 16
- **strongest members:** hook:sessionendmarkerjs, command:projects, command:instinctimport
- **decision:** `merge` · **priority:** P2

Our two-layer setup (learnings.md + bd) survives contact with 26 alternatives.

## C19 — Session continuity & handoff

- **n:** 9 · **kinds:** agent:1, command:3, hook:3, skill:2 · **avg score:** 3.31
- **worker verdicts:** merge 1, rewrite 1, defer 1, reject_after_review 6
- **strongest members:** agent:sessionhistorian, skill:cesessions, skill:handoff
- **decision:** `reject_after_review` · **priority:** P3

Historical pattern, superseded.

## C20 — Subagent orchestration & delegation

- **n:** 20 · **kinds:** agent:3, command:5, mcp:1, rule:3, skill:8 · **avg score:** 3.42
- **worker verdicts:** adopt 4, merge 3, rewrite 2, reject_after_review 11
- **strongest members:** rule:core01delegation, skill:subagentdrivendevelopment, agent:fablexhigh
- **decision:** `adopt_as_is` · **priority:** P1

Confirms the earlier lifecycle finding: candidate A is still the only actionable upstream delta.

## C21 — Autonomous loops & pipelines

- **n:** 17 · **kinds:** agent:3, command:6, hook:1, plugin:1, skill:6 · **avg score:** 3.03
- **worker verdicts:** merge 1, rewrite 1, defer 2, reject_after_review 13
- **strongest members:** command:cancelralph, command:loopstatus, skill:lfg
- **decision:** `reject_after_review` · **priority:** P3

Philosophically incompatible; deliberately not adopted.

## C22 — Codex / second-model delegation

- **n:** 8 · **kinds:** command:4, plugin:1, skill:3 · **avg score:** 4.4
- **worker verdicts:** adopt 6, merge 1, reject_after_review 1
- **strongest members:** plugin:codexadapter, command:codexcheck, skill:usecodex
- **decision:** `adopt_as_is` · **priority:** P1

Self-audit: strongest ours-owned cluster in the survey.

## C23 — Compatibility shims

- **n:** 4 · **kinds:** command:3, skill:1 · **avg score:** 3.62
- **worker verdicts:** reject_after_review 4
- **strongest members:** command:orchestrate, command:promptoptimize, command:claw
- **decision:** `reject_after_review` · **priority:** P3

Noise.

## C24 — Harness lifecycle & curation

- **n:** 40 · **kinds:** agent:7, command:13, hook:1, plugin:5, rule:1, skill:13 · **avg score:** 3.57
- **worker verdicts:** adopt 11, merge 12, rewrite 1, reject_after_review 16
- **strongest members:** rule:harnesslifecyclecuration, command:harnessstatus, skill:harnessevaluate
- **decision:** `adopt_as_is` · **priority:** P0

Ours validated; one genuinely new idea (periodic portfolio stocktake) worth absorbing.

## C25 — Harness authoring & skill quality

- **n:** 32 · **kinds:** agent:5, command:5, plugin:4, rule:2, skill:16 · **avg score:** 3.24
- **worker verdicts:** adopt 2, merge 9, rewrite 4, defer 3, reject_after_review 14
- **strongest members:** skill:writinggreatskills, plugin:skillcreator, skill:skillcreator
- **decision:** `merge` · **priority:** P1

writing-great-skills is the single best external authoring doc surveyed.

## C26 — Agent-native readiness

- **n:** 5 · **kinds:** agent:3, skill:2 · **avg score:** 3.67
- **worker verdicts:** merge 3, defer 1, reject_after_review 1
- **strongest members:** agent:clireadinessreviewer, agent:cliagentreadinessreviewer, skill:agentnativearchitecture
- **decision:** `merge` · **priority:** P2

Small but new.

## C27 — Docs & research lookup

- **n:** 18 · **kinds:** agent:5, command:2, mcp:3, plugin:1, skill:7 · **avg score:** 3.83
- **worker verdicts:** adopt 4, merge 6, defer 3, reject_after_review 5
- **strongest members:** skill:deepresearch, mcp:context7, agent:docsresearcher
- **decision:** `adopt_as_is` · **priority:** P1

Ours confirmed; hygiene line worth one sentence.

## C28 — Documentation maintenance

- **n:** 8 · **kinds:** agent:2, command:2, rule:2, skill:2 · **avg score:** 3.29
- **worker verdicts:** adopt 1, rewrite 1, defer 1, reject_after_review 5
- **strongest members:** rule:core02knowledgediscoverability, skill:codetour, command:synctutorials
- **decision:** `defer` · **priority:** P3

Low value at current doc volume.

## C29 — Teaching & onboarding people

- **n:** 7 · **kinds:** command:2, plugin:1, skill:4 · **avg score:** 3.14
- **worker verdicts:** merge 3, rewrite 1, defer 1, reject_after_review 2
- **strongest members:** skill:teach, skill:scaffoldexercises, skill:teachsession
- **decision:** `merge` · **priority:** P2

Nice-to-have, tiny merge.

## C30 — Architecture & codebase understanding

- **n:** 21 · **kinds:** agent:7, command:2, skill:12 · **avg score:** 3.54
- **worker verdicts:** adopt 3, merge 8, rewrite 4, defer 1, reject_after_review 5
- **strongest members:** agent:codeexplorer, agent:architecturecritic, agent:githistoryanalyzer
- **decision:** `merge` · **priority:** P1

Substantive, actionable, bounded.

## C31 — Code intelligence indexing

- **n:** 8 · **kinds:** command:3, hook:1, mcp:1, plugin:2, skill:1 · **avg score:** 4.25
- **worker verdicts:** adopt 7, reject_after_review 1
- **strongest members:** plugin:codeintel, command:disableforproject, mcp:serena
- **decision:** `adopt_as_is` · **priority:** P1

Self-audit pass.

## C32 — Git, GitHub & release workflows

- **n:** 25 · **kinds:** agent:3, command:5, mcp:1, plugin:3, rule:2, skill:11 · **avg score:** 2.97
- **worker verdicts:** merge 4, rewrite 5, reject_after_review 16
- **strongest members:** command:prppr, mcp:github, rule:commongitworkflow
- **decision:** `reject_after_review` · **priority:** P3

Doctrine conflict resolved in favor of our explicit-staging rules.

## C33 — Legacy modernization

- **n:** 13 · **kinds:** agent:4, command:8, plugin:1 · **avg score:** 4.23
- **worker verdicts:** adopt 1, merge 3, rewrite 4, defer 3, reject_after_review 2
- **strongest members:** agent:businessrulesextractor, command:modernizestatus, agent:legacyanalyst
- **decision:** `defer` · **priority:** P2

Best 'wrong-time' cluster; explicitly parked, not rejected.

## C34 — Data & database safety

- **n:** 10 · **kinds:** agent:5, command:1, skill:4 · **avg score:** 3.13
- **worker verdicts:** merge 2, rewrite 7, reject_after_review 1
- **strongest members:** agent:datamigrationexpert, agent:datamigrationsreviewer, agent:dataintegrityguardian
- **decision:** `adapt` · **priority:** P2

Consistent rewrite signal across both evaluators.

## C35 — Coding discipline & standards

- **n:** 15 · **kinds:** rule:7, skill:8 · **avg score:** 3.32
- **worker verdicts:** adopt 3, rewrite 2, reject_after_review 10
- **strongest members:** skill:akguide, skill:prototype, rule:core03akguidelines
- **decision:** `adopt_as_is` · **priority:** P1

Self-audit pass; ak-guide is best-in-class.

## C36 — Deployment & DevOps

- **n:** 6 · **kinds:** plugin:2, skill:4 · **avg score:** 3.08
- **worker verdicts:** merge 2, reject_after_review 4
- **strongest members:** plugin:terraform, plugin:firebase, skill:rclone
- **decision:** `defer` · **priority:** P3

Out of scope.

## C37 — External integrations & media tools

- **n:** 13 · **kinds:** agent:1, plugin:1, skill:11 · **avg score:** 3.45
- **worker verdicts:** defer 3, reject_after_review 10
- **strongest members:** skill:cardputerbuddy, skill:m5onboard, agent:seospecialist
- **decision:** `reject_after_review` · **priority:** P3

Off-domain.

## C38 — Domain-specific packs

- **n:** 15 · **kinds:** agent:1, skill:14 · **avg score:** 2.82
- **worker verdicts:** rewrite 2, reject_after_review 13
- **strongest members:** skill:llmtradingagentsecurity, skill:productionscheduling, skill:qualitynonconformance
- **decision:** `reject_after_review` · **priority:** P3

Cleanly out of scope.

## C39 — Writing craft

- **n:** 7 · **kinds:** skill:7 · **avg score:** 3.67
- **worker verdicts:** defer 2, reject_after_review 5
- **strongest members:** skill:articlewriting, skill:brandvoice, skill:writingshape
- **decision:** `defer` · **priority:** P3

Not engineering surface.

## C40 — HTML artifacts, frontend & reporting

- **n:** 23 · **kinds:** agent:4, plugin:2, rule:7, skill:10 · **avg score:** 3.54
- **worker verdicts:** adopt 3, merge 3, rewrite 1, defer 3, reject_after_review 13
- **strongest members:** skill:htmlartifact, skill:playground, skill:dashboardbuilder
- **decision:** `merge` · **priority:** P2

Ours validated; one concrete borrow identified.

## C41 — MCP & plugin development

- **n:** 18 · **kinds:** agent:2, command:4, plugin:5, skill:7 · **avg score:** 3.22
- **worker verdicts:** adopt 2, merge 1, rewrite 4, defer 7, reject_after_review 4
- **strongest members:** plugin:mcpserverdev, skill:buildmcpb, plugin:plugindev
- **decision:** `defer` · **priority:** P2

Good reference material, no active demand.
