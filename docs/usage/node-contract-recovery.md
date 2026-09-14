# Node execution contracts and interrupted-work recovery

Ordinary task nodes receive a mandatory cooperative leaf contract on initial
launch, resume, and retry of a continuation. They perform their assigned work
and tests directly. The enclosing engine owns independent review, delegation,
routing, and approval gates. Generic repository delegation instructions, task
prose, and coordination membership do not grant that authority to a leaf.
Explicit coordinator child-workflow admission and collection APIs are unchanged.

This is an instruction contract, not a hard isolation guarantee or a ban enforced
against every shell-launched agent. No native delegation flags were added.
Claude's existing tool restrictions and the existing sandbox configuration still
apply. Unsupported OpenCode launch/resume remains refused.

The engine composes the node facts, protocol, contract, current node instructions,
original task inputs, and persisted steer advice before recording the envelope.
Claude and Codex receive that exact composed payload on continuation, including
retry. Recorded UTF-8 byte count and SHA-256 describe the delivered payload.
Optional inputs can be omitted under the existing budget rules; mandatory content
cannot. If required content exceeds the budget, dispatch refuses. Missing or
malformed original steer intent still refuses even when a task prompt could be
composed without it.

## Interrupted writer content

After confirmed process death, the supervisor preserves dirty content from the
writer's owned workspace before grading, closing, or replaying cached completion.
This includes ordinary error and timeout exits, dead-without-exit recovery, and
steer before the continuation is minted. Preservation and workspace ownership
transfer use the existing repository execution band. A prior producer cannot
snapshot a successor's checkout, including another root's in-repo writer.

Recovery snapshots use the existing Git snapshot machinery and are pinned at:

```text
refs/wf/<root-id>/recovery/<activation-id>
```

The producer's wrapper directory contains `recovery.json`, outside runner channel
grants. It records root and activation identity, intended base, observed HEAD,
snapshot commit/tree, previous commit, ref, and pending/pinned state. Inspection
validates the producer, observed HEAD against the snapshot parent, tree, and pin.
Existing activation records without recovery evidence remain readable.

A repeated observation of the same tree retains the original pinned identity.
Divergent content chains the previous snapshot as a parent, so older snapshots
remain reachable. A failed pin keeps the prior ref intact. Pending evidence allows
a later attempt to finish the pin from the recorded object, without relabelling
successor bytes. Failure to persist either recovery record state, or to pin and
read back the ref, remains an error: settlement stays open and retryable. Correct
the underlying storage/ref failure and run another tick; do not delete the pending
record to force advancement. A missing legacy ownership record is reported as
unavailable, rather than attributing today's checkout to an old activation.

Clean and read-only exits create no unnecessary snapshots. Existing pre-reset
snapshot chains and terminal dirty-worktree retention remain in place.

## Read-only inspection

Use the same configuration as the running instance:

```sh
python -m workflow_interpreter.foreman --config workflow-config.yaml inspect ROOT_ID ACTIVATION_ID
```

The JSON `recovery` field is null when no record exists. A successful preservation
has `pinned: true` and commit/tree/ref identities. A pending record has
`pinned: false`; `unavailable` explains when ownership or process identity could
not be established. Inspection does not repair pending pins or restore files.

From the repository holding the objects, substitute the actual IDs and path:

```sh
git ls-tree -r 'refs/wf/ROOT_ID/recovery/ACTIVATION_ID'
git show 'refs/wf/ROOT_ID/recovery/ACTIVATION_ID:src/example.py'
git log --format='%H %P %s' 'refs/wf/ROOT_ID/recovery/ACTIVATION_ID'
```

These commands read the pinned tree and its history without changing a checkout.
Use the recorded commit OID to inspect a particular version if the ref has since
chained another snapshot. Recovery refs are local Git refs; ordinary clone/fetch
settings do not automatically distribute them.

## Scope and limits

Recovery covers tracked worktree content and non-ignored untracked files under
existing snapshot semantics. It does not reconstruct separate staged and
unstaged states, preserve ignored files or special-file contents, or recurse into
nested repositories and gitlinks. A snapshot may retain a base gitlink pointer;
that does not preserve the nested checkout's edits.

Recovery evidence is never a verified artifact, a success outcome, trusted writer
lineage, or a retry base. Without a committed candidate, verification still uses
the original intended base. There is no automatic restore, promotion, or change
to signed approval gates. Unknown interrupted or nested token usage remains
unknown; recovery adds no inferred cost telemetry.
