# Beads → GitHub mirror: roadmap

Status: approved by the owner on 2026-11-20. Seeded in Beads under `cr-k88k`.
Spec: `docs/specs/2026-11-20-beads-github-mirror.md` (approved, revision 5). Epic: `cr-k88k`.
The spec orders this work after Visual parity, Babysit and Shipping, which are closed, and before
Autopilot-stack and Autopilot-full.

## Shape

There are four phases, and each one ends at a check that needs nothing from the phases after it.
The command is built and tested offline first: outbound, then the digest and the pull-request
check. Next it is wired into the hooks and the skills. The live trial comes last and is the only
phase that touches GitHub.

| Phase | Goal | Risk | Stages |
|---|---|---|---|
| M1 Outbound command | Beads reach GitHub as issues, safely, tested against a fake `gh` | deep | 3 |
| M2 Digest and pull-request check | GitHub's state comes back as a digest, and a pull request needs a reference | deep | 2 |
| M3 Hooks and skill guidance | Session start runs the mirror in the writer clone and stays silent everywhere else; skills act on it | standard | 2 |
| M4 Live trial and activation guide | The trial confirms the behaviour on a real repository and the owner gets activation steps | deep | 3 |

Everything is built in the canonical harness in this repository. The plugin template copy, and the
plugin `doctor` check the spec describes, wait for the end-of-project sync (`cr-e0a`).

### Decisions this roadmap makes

- **Where the command lives.** `.claude/hooks/bead-mirror.py`, a single standard-library file. The
  residue the plugin carries covers `.claude/hooks` and `.codex/hooks`, but not `.claude/scripts`,
  so a residue command has to live under the hooks. Each tool gets its own launcher:
  `.claude/hooks/bead-mirror-session.sh` and `.codex/hooks/bead-mirror-session.sh`.
- **Fixtures before the trial.** The spec says the fake `gh` replays responses recorded in the live
  trial, but the trial needs a working command. M1 and M2 therefore build against hand-written
  fixtures, marked provisional and modelled on GitHub's documented responses. M4 records the real
  responses, swaps them in, and fixes whatever no longer passes. The alternative is an early recording
  probe, which would need the owner's go-ahead before M1 starts.
- **The check's script and the shared grammar.** The workflow cannot check out code, so its
  reference check is an inline step. The command holds the workflow text, writes it with
  `install-check`, and keeps the inline step's grammar in the same source as the digest's parser.
  The tests run both against the one fixture table.
- **The plugin `doctor` check** goes with the `cr-e0a` sync, as plugin work. When the roadmap is
  seeded, a note on `cr-e0a` will record it.
- **"Not opted in" after `adopt` and `update`** is checked in this repository in M3 (no switch and no
  workflow means a silent session start and no mirror files). The `adopt`/`update` run itself
  happens at the `cr-e0a` sync.
- **Activation in this repository** is outside this workstream. The settings and the switch are the
  owner's actions. M4 hands over the steps, which matches the epic's acceptance.

## M1 Outbound command

**Goal.** The command creates, links, updates, closes and retires issues for enrolled beads, and
never writes unless every authority check passes. It is proven against a fake `gh` and a real
temporary Beads store.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| M1.1 | Test seam, skeleton, authority and lock: fake `gh` on `PATH` (replay plus fault injection), a temporary Beads store fixture, provisional fixtures; the command's subcommand parser, switch, explicit store resolution, `gh` account and node-ID checks, writes by node ID, the state file bound to store, repository and account, `reset-state`, the clone-wide lock, a dry-run mode (activation step 4) | `.claude/hooks/bead-mirror.py`, `tests/mirror/` (`_fake_gh.py`, `conftest.py`, `fixtures/`), `.repo-context/verification.md` (a `tests/mirror` row) | Spec criteria Authority, Rename, Failures (manual runs exit non-zero with the cause), Lock (two manual runs) pass; the fake `gh` fails any unrecorded call, so no test reaches the network |
| M1.2 | Create and link: eligibility, scope and status, `mirror=never`, `pr` enrolment under the switch, the private-material screen, mention code spans, banner with store identity, listing-based adoption, pending attempts, `resolve`, the `external_ref` write, the `link` subcommand | `.claude/hooks/bead-mirror.py`, `tests/mirror/` | Criteria Outbound (create, link, background creates nothing), Only the link, Private, Create, Store change, Link race, Lost state (no duplicate) pass; carried cases pass: deferred and excluded beads through `pr` with out-of-scope types allowed |
| M1.3 | Update, close and retire: text and `bead-type:` label converge on canonical forms, not-storable, the open-or-closed hold table, `overwrite`, the keyed closing comment, `retire`, the map | `.claude/hooks/bead-mirror.py`, `tests/mirror/` | Criteria Outbound (second run makes no writes), Converge, Close, Open-or-closed held, Retire, Lost state (holds) pass; carried cases pass: a GitHub-only text edit repaired on the next incremental run, two distinct closes with the same stored time and reason |

Spec references: Project states; Authority and activation; Scope, enrolment and links; Outbound;
Packaging (the command); Testing Decisions.
Exit (phase): `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q tests/mirror` passes every
criterion named above, using provisional fixtures and without network access.
Test focus: fault injection at the `gh` seam (lost create response, lagging listing, copied banner,
dropped write, interrupted read-back, collaborator change between write and read-back, failed page,
renamed repository); after each run, the Beads store has changed only in `external_ref`.
Risk: deep. Crash-safe creation and the hold table implement the spec's no-duplicate and
no-silent-overwrite guarantees.

## M2 Digest and pull-request check

**Goal.** Inbound compares GitHub with Beads and writes an identifiers-only digest. The check
workflow fails any pull request with no reference, and it reads the same grammar as the digest.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| M2.1 | Reference grammar and check workflow: the shared fixture table; the workflow text held in the command (`pull_request_target`, no checkout, read-only pull-request permission, fixed job name, the four triggers, a per-pull-request concurrency group, the exempt-authors variable, the body read through the API at run time, fail closed); `install-check` | `.claude/hooks/bead-mirror.py`, `tests/mirror/fixtures/references.*`, `tests/mirror/` | Criterion References passes in both the digest parser and the workflow's inline step; the offline part of Check passes (no reference fails with the fix in the message, a reference passes, an exempt author passes, an empty or malformed body fails); a static test asserts the trigger, permissions, concurrency and absence of checkout in the written workflow |
| M2.2 | Inbound digest: every row of the inbound table, the field allow-list, open-row re-evaluation, Beads-side re-check, both checkpoints and the digest in one atomic state replacement, `dismiss`, the weekly full comparison bounded by its starting high-water mark, the `inbound` and `both` subcommands | `.claude/hooks/bead-mirror.py`, `tests/mirror/` | Criteria Merge reported, Untracked, Beads-side change, Digest safety (no title text in an entry) pass; carried case passes: a manual re-close after an earlier merge close is not attributed to the old pull request; a run that cannot finish inbound leaves the previous digest and checkpoints unchanged |

Spec references: Inbound (GitHub → digest); Pull-request check; Packaging (the check's workflow).
Exit (phase): the `tests/mirror` suite passes M1's and M2's criteria; the same fixture table gives
the same answer in the check and in the digest.
Test focus: atomicity of the state replacement, the allow-list against instruction-like text from
GitHub, and grammar edge cases (`Refs #42abc`, keyword case, colon, full URL).
Risk: deep. The digest is the only inbound path, so a missed row means a merge never reaches the
tracker.

## M3 Hooks and skill guidance

**Goal.** A session start in the writer clone shows the digest summary and starts the background
run without waiting. In any other clone it prints nothing. The skills follow the project states.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| M3.1 | Supervisor and session-start hooks: the background supervisor and worker (own process group, log, worker-held lock and deadline, supervisor deadline and reaping), the capped summary, the fifteen-minute relaunch rule, a launcher and session-start entry for each tool | `.claude/hooks/bead-mirror.py`, `.claude/hooks/bead-mirror-session.sh`, `.codex/hooks/bead-mirror-session.sh`, `.claude/settings.json`, `.codex/hooks.json`, `tests/mirror/` | Criteria Hook, Lock (`pr` path and manual run during a background run; supervisor killed mid-run), Failures (hook prints the last digest and exits 0), Digest safety (output cap) pass for both launchers; with no switch in this repository, session start prints nothing new, creates no mirror file, and the Beads context output is byte-identical; `bash -n`, `shellcheck` and `json.tool` pass |
| M3.2 | Skill guidance for each project state: `tracker` (acting on the digest; outbound after closing or seeding), `pr` (nearest issue-bearing ancestor, `Refs` by default, the writer-clone stop line), `triage` (untracked issues and pull requests, `link`, `dismiss`), Babysit and Shipping (close the bead after reading a merge back) | `.claude/skills/{tracker,pr,triage}/SKILL.md` and their references, `.claude/skills/mvp-mode/playbooks/{babysit,shipping}.md` | `uv run python .claude/scripts/skill-catalog.py --check` and `uv run python harness_lifecycle/registry/registry.py check` pass; each project state in the spec's table maps to one instruction in each skill, checked item by item; carried case: `pr` writes `Refs` to an ancestor whose work remains open; text stays provider-neutral with no machine paths |

Spec references: Project states; Triggers; Packaging (residue, skill guidance); Constraints.
Exit (phase): hook tests pass for both tools' real launchers; the skill and registry checks pass;
this repository, with no switch, starts sessions exactly as before.
Test focus: hook return time, deadline cleanup of a slow child, lock contention, and an unchanged
Beads context output.
Risk: standard. The behaviour is bounded, but the hooks run in every adopted project.

## M4 Live trial and activation guide

**Goal.** The trial confirms the spec's behaviour on a real repository, the recorded responses
replace the provisional fixtures, and the owner has the activation steps.

| # | Stage | Create/modify paths | Verify |
|---|---|---|---|
| M4.1 | Trial checklist and owner gate: a checklist of every trial case in the spec, each with the evidence that settles it; the owner's go-ahead; the owner creates the throwaway repository with the supported protection, Actions policy, three merge methods, and a second account for fork pull requests | `docs/workstreams/beads-github-mirror/trial.md` | The checklist covers every case in the spec's live-trial paragraph; the owner's go-ahead is recorded on the stage bead before any network call |
| M4.2 | Run the trial: issue create, edit, label, close with read-back; the title, CRLF and 60,000-character round trips; lost-response recovery; closing events for squash, merge and rebase; every merge-decision case, including the same-name workflow from a fork; enforcing (not evaluating) `pull_request_target` policy; one real session start per tool after the hook entry is installed | `docs/workstreams/beads-github-mirror/trial.md`, `tests/mirror/fixtures/recorded/` | Each checklist case has its observed result and evidence link; recorded responses are saved as fixtures; any hook-trust prompt is noted |
| M4.3 | Replay and hand-over: switch the fake `gh` to the recorded fixtures, fix divergences, retire the provisional ones; write the owner's activation steps in the spec's order | `tests/mirror/`, `.claude/hooks/bead-mirror.py`, `docs/usage/bead-mirror.md` | `tests/mirror` passes on recorded fixtures only; the remaining live parts of the Check criterion are evidenced in `trial.md`; the activation guide lists the spec's eight steps in order and marks each as the owner's |

Spec references: Activation; Testing Decisions (live trial); Out of Scope (repository settings).
Exit (phase): `trial.md` shows every case passed, the suite passes on recorded fixtures, and the
activation guide exists. The spec's prerequisite to activation is then met.
Test focus: whatever the real GitHub responses do differently from the provisional fixtures.
Risk: deep. It depends on outside services and on owner actions and settings.

## Dependencies

| Edge | Reason |
|---|---|
| M1 → M2 | The digest reads the state, links and lock that M1 builds |
| M2 → M3 | The hooks run inbound and summarise its digest; the skills act on digest rows and on `install-check` |
| M3 → M4 | The trial runs real session starts and the hook entry |
| M1.1 → M1.2 → M1.3 | Create needs the seam, authority and lock; update and close need enrolled issues |
| M1.3 → M2.1 | Phase order. M2.1 itself needs only M1.1 and could start earlier if the owner prefers |
| M2.1 → M2.2 | The digest's pull-request rows use the shared grammar |
| M2.2 → M3.1, M2.2 → M3.2 | Phase order. M3.1 and M3.2 are independent of each other |
| M3.1, M3.2 → M4.1 | Phase order |
| M4.1 → M4.2 → M4.3 | Owner go-ahead before any network call; replay needs the recordings |

## Owner rulings (2026-11-20)

1. **Fixture order.** Provisional fixtures first; M4 replaces them with recorded responses.
2. **Second GitHub account.** Not available yet. The fork cases in M4.2 are deferred until one is; every
   other trial case proceeds.
3. **Command location.** `.claude/hooks/bead-mirror.py` is kept.
