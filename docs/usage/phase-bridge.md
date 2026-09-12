# Operating the sequential phase bridge

Select one direct stage of the phase, then run:

```sh
uv run python -m workflow_interpreter.foreman --config <foreman-config.toml> phase-bridge <epic-id> <stage-id>
```

The coordinator must be clean and attached to the intended target branch. The bridge pins the stage's policy before admission, runs its workflow, consumes the authenticated immutable ship approval, verifies the candidate, lands it, and closes the stage with a durable receipt. A waiting workflow returns its run result; `completed` or `recovered` means a validated stage closure. The LLM selects stages; the bridge does not choose the next stage.

## Required check policy

Generate a local config with `scripts/make-foreman-config.sh`, then adapt and uncomment the `[[bridge_checks]]` example in `config/foreman.example.toml`. Select the complete required check set for the repository. There is no automatic default; missing or empty policy refuses before stage/root writes and points here.

Each check declares `name`, `argv`, `timeout_s` (positive, at most 3600 seconds), and optional `environment` as an array of `[key, value]` pairs. Names and environment keys must be unique. The example calls `scripts/verify-feature.sh`, which has its own documented exclusions; it does not replace the parent's seven milestone gates.

Executable and environment rules:

- `argv[0]` resolves as a repository-relative executable inside the detached checkout, or as an explicit absolute host executable. Bare `uv` does not search PATH at admission. Use the tracked script example with an explicitly provisioned uv on its child PATH, or specify the host executable's absolute path.
- Admission pins executable bytes, argv, environment and timeout. Execution hashes and uses the same open executable descriptor via `/proc/self/fd/N`. A check script must use the checkout working directory, not derive the repository from `$0`. Host tools must support descriptor-based invocation; tools which depend on their launch path need a suitable tracked entry script.
- Default PATH is `/usr/bin:/bin`, LANG is `C.UTF-8`, and HOME/TMPDIR are a new temporary scratch directory per check. Ambient variables, credentials and developer HOME are not inherited. Explicit environment entries override these defaults and are stored in the policy and receipt: **do not put secrets in them**.
- The working directory is a detached candidate checkout. It has no borrowed development `.venv`, Beads workspace, populated submodules, or inherited tool cache. Provision tools and Python explicitly (the example supplies PATH and UV_PYTHON_INSTALL_DIR), and ensure checks can build their dependencies without changing tracked source. Ignored build output may remain during verification; tracked byte/mode changes, HEAD changes and dirty source refuse.
- Every declared check must produce a successful observed exit status with matching provenance and unchanged source. Labels, partial/duplicate results, failures and timeouts cannot authorize landing. Reconfiguring a later invocation never replaces an already admitted policy; legacy journals without policy need operator migration, not automatic invention.

Checks retain the disclosed T1 trust boundary: they execute trusted candidate-controlled code on the host. These controls do not claim OS containment of malicious checks.

## Pending intents and recovery

Rerunning the same command reads durable state first. Default recovery **never moves a ref**. If an intent exists while the target equals the original base, the report says `disposition: pending` and `next_action: --retry-landing`. That observation does not prove whether an earlier CAS occurred; do not delete the intent file.

To explicitly retry that retained landing intent:

```sh
uv run python -m workflow_interpreter.foreman --config <foreman-config.toml> phase-bridge <epic-id> <stage-id> --retry-landing
```

This operation revalidates the same stage/root/attempt, intent, authenticated ship authority, policy, exact target base, and clean attached coordinator; it reruns checks and attempts the same CAS. It never runs agents or creates a root. It refuses existing receipts, already-landed states, moved targets, or combinations with `--retry` or `--trace`. Repeating it after completion refuses without moving a ref; the ordinary command returns validated historical completion.

`--retry` is a different operation: for an uncoordinated ordinary stage it creates a new workflow attempt only for an eligible terminal declared by the graph. A coordinated ordinary stage refuses this legacy retry because it would reset the owner budget; use the original-owner `children replace` operation instead. Integration retains its separate same-pins retry path. It cannot bypass an admitted shipped artifact waiting for landing. `--trace` reads current evidence without executing work.

## Checkout and historical completion

A branch switch or staged, unstaged, or untracked change is preserved, including changes during a run. Fresh landing checks coordinator identity before CAS and again after verification. If CAS succeeded before an interruption, recovery only synchronizes an attached coordinator still holding the clean original index/tree. Refusal reports retain the reason, intent identity, and relevant observed target. Preserve local changes outside the coordinator, return to the admitted branch, and rerun ordinary recovery; never use a blind reset or delete recovery evidence.

A closed stage's replay validates its closed relation, receipt digest, intent, admitted policy and authenticated artifact correspondence. It does not execute historical host tools again. Historical completion reports what landed previously, not a promise that the target has never moved since. Missing, corrupt or mismatched receipts still refuse.


## Explicit integration of child results

Collect the required child results first. Write an integration request with `owner_id`, `epic_id`, `stage_id`, a stable `request_key`, and `sources` containing exact `[slot, generation, receipt_digest]` triples. Every source belongs to that owner. Then run:

```sh
uv run python -m workflow_interpreter.foreman --config <config.toml> integration prepare --request <request.json>
uv run python -m workflow_interpreter.foreman --config <config.toml> integration status <epic-id> <stage-id>
uv run python -m workflow_interpreter.foreman --config <config.toml> phase-bridge <epic-id> <stage-id>
```

Preparation pins the selected sources, target base and integration admission, and reserves capacity from the original owner. The integration workflow produces a combined candidate with fresh review, checks and authenticated ship approval. Existing child approvals cannot authorize that candidate. Source receipt collection does not change a Git target.

Use `integration retry <epic-id> <stage-id>` only for an eligible same-pins integration retry; it takes a fresh target base and requires new evidence. A pending landing intent instead uses the existing `phase-bridge --retry-landing` contract above. Status and durable records distinguish these states; preserve them when recovery is pending.
