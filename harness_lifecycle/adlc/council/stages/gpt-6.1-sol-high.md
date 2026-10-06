## 1. Coverage verdict

**Revise: the proposal covers the main development flow, but not the entire lifecycle.** It lacks explicit release preparation, checks after deployment, incident recovery, validation of outcomes in use, and retirement. Its labels already satisfy word uniqueness and mostly use nouns; the larger naming problem is that **Intent** and **Evidence** name artifacts rather than activities. Planning is also underrepresented, approval appears too late for actions such as merging, and closeout is incorrectly tied to ongoing operations. Keep cross-stage concerns and a small miscellaneous bucket, but treat them as classification bands rather than phases. The lifecycle itself must support optional activities, repeated increments, and returns to earlier phases; strict one-pass ordering would misrepresent development.

## 2. Changes

| Change | Item | Reason |
|---|---|---|
| Redefine | Discovery | Distinguish exploration of opportunities from investigation needed to execute an accepted change; discovery is optional for incoming requests. |
| Rename | Decision → Selection | Names the activity of choosing a direction; “decision” can mean its resulting record. |
| Rename | Intake → Planning | Makes the phase recognisable against SDLC vocabulary and accommodates requirements and preparation. |
| Rename | Intent → Scoping | Names the activity of agreeing goals and boundaries rather than the resulting intent. |
| Move | Grounding → Planning | Relevant constraints and current behaviour should inform committed scope and requirements. |
| Split | Acceptance → Specification and Acceptance | Defining success before implementation differs from deciding whether the finished result is suitable for use. |
| Redefine | Design | Shapes the production change; exploratory code and prototypes may legitimately precede implementation. |
| Add | Prototyping | Provides an explicit home for testing uncertain design assumptions before committing to them. |
| Move | Slicing → Design, renamed Sequencing | Execution increments should reflect the chosen structure, dependencies, and verification strategy. |
| Redefine | Implementation | Includes tests, documentation, configuration, infrastructure, and migrations alongside application code. |
| Split | Diagnosis → Diagnosis and Optimization | Explaining and correcting failures differs from improving measured performance or resource use. |
| Redefine | Verification | Establish justified confidence within stated limits; finite checks do not prove universal correctness. |
| Rename | Evidence → Testing | Names the activity; recorded evidence is its output. Include applicable static checks and evaluations. |
| Redefine | Review | Retain independent critique, covering design, code, tests, and relevant release risks. |
| Rename | Delivery → Deployment | Gives the phase a direct SDLC counterpart. |
| Redefine | Integration | Incorporate verified changes under the applicable approval gate; disabled behaviour is a deployment technique, not a universal requirement. |
| Move | Authorization → cross-stage Governance | Approval can be required before integration, publishing, deletion, or other consequential actions. The repository’s [ADLC guide](harness_lifecycle/adlc/GUIDE.md) explicitly gates merging. |
| Add | Packaging, Readiness | Release artifacts, dependencies, migrations, operational ownership, and recovery arrangements need explicit preparation. |
| Rename | Rollout → Release | Covers deployment and activation, with gradual exposure where appropriate. |
| Add | Confirmation | Pre-release checks cannot establish that the actual deployment succeeded. |
| Rename | Operations → Maintenance | Matches common SDLC vocabulary and includes continuing upkeep. |
| Add | Response | Monitoring detects problems; containment, recovery, and incident handling are separate activities. |
| Add | Evaluation | Healthy software can still fail to deliver the intended user outcome; agent effectiveness also needs assessment. |
| Redefine | Improvement | Convert findings into proposed software or agent changes, then route those changes through the lifecycle and appropriate evaluations. |
| Move | Closeout → cross-stage band | Work can finish, be rejected, or stop without deployment; maintenance can continue after a work item closes. |
| Add | Retirement, Withdrawal, Disposal | An entire software lifecycle includes ending use and safely retiring its resources and retained data. |
| Rename | Across stages → Enablement | Uses a noun label while retaining a clearly separate band for supporting activities. |
| Rename | Guardrails → Governance | Clarifies authority, budgets, tracking, policy, and accountability rather than suggesting only prohibitions. |
| Add | Provisioning, Contextualization | Environment preparation and agent context management deserve explicit homes. |
| Move | Communication → Enablement | Writing, explanation, and human coordination support lifecycle work throughout. |
| Move | Housekeeping → Provisioning or Maintenance | Repository setup and upkeep are lifecycle work; classify them by their purpose. |
| Remove | Aliases | Redirects describe skill packaging, not lifecycle activities; resolve them to their targets. |
| Merge | Miscellaneous sub-stages → Assistance | Keep one explicit residual bucket for capabilities unrelated to development or agent improvement. Teaching about active work belongs under Communication. |

## 3. Final proposed list

All labels below are nouns, and no label word repeats. Phases **0–7** follow the normal forward path; activities can repeat, overlap, or be skipped when unnecessary. **X and M are classification bands**, so their entries have no chronological ordering.

| # | Stage | Sub-stage | One-line definition |
|---|---|---|---|
| 0 | **Discovery** | | Explore problems and opportunities before committing to a particular change. |
| | | Research | Gather evidence about needs, existing solutions, feasibility, and possible directions. |
| | | Selection | Compare opportunities and choose a direction worth pursuing. |
| 1 | **Planning** | | Turn a candidate request into understood, bounded, and accepted work. |
| | | Triage | Classify, prioritise, and route the request, including rejection or deferral when appropriate. |
| | | Grounding | Establish the relevant existing behaviour, code, dependencies, and constraints. |
| | | Scoping | Agree the intended outcome, boundaries, non-goals, and responsible stakeholders. |
| | | Specification | Define required behaviour, constraints, and observable criteria for success. |
| 2 | **Design** | | Shape the solution and its execution approach before production implementation. |
| | | Architecture | Define the necessary structure, interfaces, data model, and technical choices. |
| | | Prototyping | Test uncertain solution assumptions through bounded experiments or disposable implementations. |
| | | Sequencing | Divide the solution into ordered, verifiable increments with explicit dependencies. |
| 3 | **Construction** | | Produce the executable change and its supporting materials. |
| | | Implementation | Create code, tests, documentation, configuration, and migrations, using test-first methods where appropriate. |
| | | Diagnosis | Reproduce failures, identify their causes, and guide corrective changes. |
| | | Optimization | Improve measured performance or resource use while preserving required behaviour. |
| 4 | **Verification** | | Establish that the change meets its requirements with sufficient evidence for its intended use. |
| | | Testing | Run applicable checks and evaluations, recording results, coverage, and limitations. |
| | | Review | Independently challenge the solution, implementation, checks, and supporting claims. |
| | | Acceptance | Assess whether the result satisfies stakeholder needs and the agreed success criteria. |
| 5 | **Deployment** | | Incorporate, prepare, and introduce the verified change into its intended environment. |
| | | Integration | Incorporate verified increments into the shared codebase and resolve compatibility issues. |
| | | Packaging | Produce identifiable release artifacts and their required dependencies and documentation. |
| | | Readiness | Check release prerequisites, migration arrangements, operational ownership, and recovery procedures. |
| | | Release | Deploy and activate the change using an exposure strategy proportionate to its risk. |
| | | Confirmation | Check the actual deployed state and initial behaviour, invoking recovery when necessary. |
| 6 | **Maintenance** | | Sustain software in use and assess what it delivers over time. |
| | | Monitoring | Observe health, security, reliability, and usage to detect actionable findings. |
| | | Response | Contain incidents, restore service, and coordinate recovery and follow-up. |
| | | Evaluation | Assess user outcomes and agent effectiveness using operational evidence and feedback. |
| | | Improvement | Turn findings into prioritised software or agent changes that re-enter the appropriate lifecycle phase. |
| 7 | **Retirement** | | End use of software or a capability while meeting remaining obligations. |
| | | Withdrawal | Deprecate the capability, transition affected users, and cease its operation. |
| | | Disposal | Remove obsolete resources and access while retaining or deleting data according to applicable obligations. |
| X | **Enablement** | | Support and control work throughout the lifecycle rather than represent a sequential phase. |
| | | Provisioning | Prepare repositories, environments, tools, credentials, and infrastructure needed for the work. |
| | | Orchestration | Coordinate tasks, agents, dependencies, execution loops, and unattended progress. |
| | | Governance | Apply authority, permissions, budgets, policy checks, tracking, and decision accountability. |
| | | Contextualization | Select, preserve, and transfer the working context needed for reliable execution and resumption. |
| | | Communication | Explain findings, document decisions, and coordinate understanding with people and other agents. |
| | | Closeout | Reconcile completed, cancelled, or interrupted work, recording its outcome, evidence, lessons, and remaining obligations. |
| M | **Miscellaneous** | | Hold capabilities whose purpose lies outside software development and agent improvement. |
| | | Assistance | Perform unrelated tasks, including teaching or content creation unconnected to active lifecycle work. |

For skill mapping, classify by the **outcome the skill serves**, allowing multiple assignments when it genuinely serves several activities. Security, accessibility, documentation, and data handling belong throughout this structure; they are also useful independent tags. Resolve aliases before classification.

## 4. Open questions

1. Must every skill receive exactly one assignment, or can it have a primary assignment plus secondary ones? I recommend the latter; forcing exclusivity would create artificial boundaries.

No files were edited.