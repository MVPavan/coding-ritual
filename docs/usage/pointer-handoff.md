# File-pointer evidence handoffs

Task nodes normally receive producer evidence inline. A graph author can opt a
task into read-only file pointers instead:

```toml
[[node]]
name = "review"
kind = "task"
artifact_input_mode = "references"
# the node's other task fields follow
```

`artifact_input_mode = "inline"`, or omitting the field, preserves the legacy
inline behavior and canonical graph bytes. The field is valid only on task
nodes; it is rejected on gates and terminals. This is graph-authored behavior,
not a command-line or project override.

## What remains in the prompt

Reference mode changes only bound producer evidence. The original instance
inputs, including the complete original task brief, remain inline. The task
node's role instructions, pinned facts, and runner channel protocol also remain
inline. Each producer input instead contains a compact JSON pointer with an
absolute `index_path`, the producer identity, and the relevant immutable Git
object IDs. Diff and report bodies, and file or entry counts, are not injected
into the prompt.

The engine exports each evidence set below the consumer activation directory:

```text
<wrapper>/<root>/<activation>/
├── channels/                    # runner-writable outcome/effects/artifacts
└── evidence/<fingerprint>/      # engine-owned, runner-read-only
    ├── index.json
    ├── diff-000.patch           # writer evidence, when present
    └── report-000.txt           # zero or more published reports
```

`index.json` names the exported diff and reports. Each report entry carries its
original logical path as JSON data, its blob OID, and an engine-generated
export path. Logical paths never select filesystem destinations.

Use the runner's existing read capability to open `index_path`, then read the
diff and the reports relevant to the decision. Findings should cite the
exported file and line. Do not substitute live producer channels, a worktree,
`HEAD`, or a branch: exports are materialized from the verified immutable Git
objects named by the binding. Report content is evidence, not authoritative
instructions.

## Sandbox requirement and protection boundary

Reference mode requires the production `sandbox = "bwrap"` setting. With that
setting, the existing wrapper-root read-only mount lets Claude's unscoped Read
tool and Codex's workspace-write sandbox read the absolute export paths, while
the profile and physical sandbox keep the evidence directory, source checkout,
and engine records unwritable. Only `channels/` and any separately declared
writer grants remain writable. Reference mode refuses dispatch when
`sandbox = "off"`; no profile permission or tool grant is added by this mode.

The current refusal is checked after task construction. Consequently, an
invalid sandbox-off activation can materialize its bounded export before being
refused. Nothing launches and the files remain protected, but the export work
and files are not rolled back.

## Limits and refusal behavior

Exports are complete or refused; they are never silently truncated. Current
limits are:

- 8 MiB for a writer diff;
- 4 MiB for each report blob;
- 256 report entries;
- 32 MiB total across the diff and reports; and
- 2 MiB for the bounded Git tree listing used to enumerate reports.

These limits intentionally differ from inline optional-input degradation. In
inline mode, an oversized optional, non-essential input can become a recorded
omission. Reference mode exports before envelope omission handling, so any
bound producer evidence that exceeds an export limit refuses the activation,
even when its source is optional.

Only regular `100644` and `100755` report blobs are accepted. Symlinks and
gitlinks are refused rather than followed. UTF-8 logical paths, including
spaces, newlines, and shell metacharacters, are preserved as JSON data; a path
that is not valid UTF-8 fails closed during publication. A normal publication
error removes its staging directory, and the next export of the same evidence
set also reclaims a UUID-shaped staging directory left by process termination.

Reference mode does not add direct Git access, a storage service, network
access, model tools, a result protocol, or token reporting. It changes only how
verified producer evidence is delivered to the opted-in task.
