<!-- BD:GENERATED START -->
# Backlog (parked, vetted)
_generated from bd @ 2026-10-07T05:00:44Z — DO NOT EDIT (run: BD_RENDER=1 bash <beads-skill-dir>/scripts/bd-render-tracking.sh)_
- `cr-02ze` live run feedback
- `cr-o85.43` Discipline composition: Node has no method or discipline-set field, so mount-many has no mechanism
- `cr-8ji` Bind crew identity into LaunchReceipt so inspector reattachment cannot adopt a foreign vendor
- `cr-9uy` spike-then-harden is not expressible: no base-commit lineage primitive
- `cr-o85.34.29` Deferred phase-7 verify checks have prose triggers and no work items
- `cr-o85.38` launch abort follow-ups: torn abort-pending receipt orphans the stub child; recover.py docstring lists two pre-checks not three; mint-block test uses a duck-typed stub
- `cr-n2z.7` codex 0.153: sandbox surface drifted (codex sandbox needs --permission-profile; permission_profiles/profile_workspace_roots) — may express a read-only cwd and retire the writer exemption from phase 2
- `cr-n2z.5` allowed_paths residual: packed-refs and instance branch stay crew-writable (evidence-ref forgery)
- `cr-o85.34.11` Pinned verifier manifest hashes only argv[0] (inspector/channels.py:287)
- `cr-b1p` ADR 0003: shared method library (use: <name>, resolve-copy-freeze at create_root)
- `cr-6nl` Explain or mutation-prove the worktree HEAD assertion (inspector/gitio.py worktree_add)
- `cr-t5x` Git fault-injection spy tests: instance-branch CAS failure/CAS-lost and prereset update-ref failure → INFRA_RETRY (inspector/workspace.py)
- `cr-o85.30` Pre-reset snapshot correctness (inspector/gitsnapshot.py): hash-object TOCTOU and HEAD's cached gitlink for a moved submodule
- `cr-o85.26` phase-4/5: a replay that must recompute (completion.json absent) attributes a human edit to a DECLARED path to the runner
- `cr-o85.17` phase-5: run.jsonl is runner-writable by construction, and scan_log reads a session id and usage back out of it (R7)
- `cr-o85.16` Program-naming git keys other than filters remain unpinned (inspector/gitcmd.py)
- `cr-o85.12` phase-5: ProfileConfig is a frozen BaseModel, not pydantic-settings (flag 11)
- `cr-o85.1` bdio write guards: record_dispatch without recorded §3.2 precondition trio; repair_forward's unguarded second lifecycle merge
- `cr-a0n` bdio: package modules reach into BdClient._merge_metadata / _create_bead / _close_bead
- `cr-zaj` supervisor: ExitObserver reaches PinOutcome.REFUSED indirectly
- `cr-l17` supervisor: Monitor.watch holds on INDETERMINATE with no ceiling
- `cr-too` bdio: recorded_precondition raises a raw ValidationError on an out-of-band trio
- `cr-52h8` Polish DWS lock qualification diagnostics and deployment rerun evidence
<!-- BD:GENERATED END -->

<!-- Human notes below this line are preserved across renders. Everything above is bd-generated; do not hand-edit it. -->
