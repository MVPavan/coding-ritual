# QMD stdin-carrier lifetime qualification — cr-0km.13

2026-09-22: **the measured stdin-carrier ownership mechanism passed**; fresh
independent Sol xhigh review is pending. This does not complete G-03, P1 or release
qualification. The earlier extra-fd candidate remains failed and budget-stopped;
its evidence was not replayed or reclassified.

Exact application image:
`sha256:eb1475855045015fd0aa47e32605dcb5dcb68275d04f70be2386c9322694b616`.
The application label still matched this ID at closeout. Installed QMD **2.8.3**,
Node **v22.22.0**, QMD SQLite **3.53.4**, linux/amd64. See the
[application qualification](application-image-qualification.md) and
[evidence manifest](qmd-child-manifest.json).

## Contract and scope

Reserve stdin for a flocked regular-file descriptor on DWS's internal,
noninteractive QMD subprocess allowlist: `collection add`, `update`, `status`,
`search`, `get`. These commands receive data through arguments/files. DWS CLI
stdin is a separate, unaffected interface. Arbitrary, interactive, MCP and model
commands are excluded. This is an authorized engine implementation detail, not a
new caller-visible restriction. No production supervisor, guardian, daemon or
upstream-source change was introduced.

Always invoke public `qmd`; its launcher forwards stdin to the actual worker.
The probe observes the internal worker path solely to verify process identity;
it never invokes that path directly. Requalify on image, QMD, Node, launcher,
allowlist or relevant filesystem changes. Other commands have only successful
carrier smoke coverage here; parent/launcher-death lifetime proof uses `get`.

## Measured lifecycle and false control

Passing run: `dws-qmd-stdin-b6e23094ec1a`, volume
`dws-qmd-stdin-b6e23094ec1a-state`. `/state` was a local Docker named volume on
**ext4**, `/dev/sdd`, device **8:48**. Eight independent competitor containers
opened the same case-specific lock inode and checked exclusive nonblocking
`fcntl.flock`. Outcomes and counters are assertions, not expected-value metadata.

| Transition | Stdin carrier | Parent-only negative control |
| --- | --- | --- |
| Worker initialized, real fixture output emitted, then SIGSTOP | BUSY; counter 0 | BUSY; counter 0 |
| Controller SIGKILL and reaped; same worker remains stopped | BUSY; counter 0 | ACQUIRED; counter 1 |
| Launcher SIGKILL and reaped; same worker reparented to PID 1 | BUSY; counter 0 | ACQUIRED; counter 2 |
| Worker SIGCONT, complete genuine get, exit 0 and reaped | ACQUIRED; counter 1 | ACQUIRED; counter 3 |

Each case had controller PID 82, public launcher PID 83, actual worker PID 90
in its own namespace. Worker start ticks were **51761477** (carrier) and
**51761783** (negative). Exact PID/start ticks, PPID, executable and full command
were checked at lifecycle transitions; zombie/exited states were rejected.
Carrier worker fd0 targeted `/state/stdin-carrier/slot.lock`, inode **1341720**,
with kernel `FLOCK ADVISORY WRITE` ownership, including after both ancestors were
reaped. Negative worker fd0 was `/dev/null` and no descriptor referenced its lock
(inode **1341881**). Raw descriptor and process identities are in the manifest's
referenced result JSON.

PID 1 was an independent observer that stayed alive throughout. Its bounded
control channel was never QMD stdin, and its output reader remained open after
controller death. Control flags stayed blocking. Worker discovery required a
real child of the launcher with the exact worker command; no launcher fallback.
Thus neither PID-1 teardown nor broken-output-pipe termination explains success.
The observer reaped both killed ancestors and the normally completed worker,
asserted `/proc/PID` absence after each reap, and verified no children remained.

A 2,200,035-byte synthetic fixture produced **2,889,002 output bytes**, with all
**100,004 numbered body lines** compared exactly in both cases. Real lexical
search returned `qmd://fixture/fixture.md`; get content was observed before
SIGSTOP. Output exceeded the 65,536-byte pipe capacity, providing real-operation
backpressure. Collection add, update, status and search also completed through
the public launcher with locked stdin. Empty cache/HOME were asserted after
both completed runs, with cache empty before initialization; no models appeared.

## Reproduction, attempts and cleanup

From the repository root, with the existing image and installed tools:

```bash
DWS_QMD_CHILD_DOCKER=1 dws/.venv/bin/pytest -q -s \
  dws/tests/qualification/test_qmd_child_docker.py
```

New budget consumed: one implementation and one evidence-driven correction.
Initial run `dws-qmd-stdin-7eb60a9aab6e` proved the carrier's three BUSY states,
but its output expectation omitted QMD's numbered terminal empty line. The
correction preserves that line and retains exact full-body equality. Corrected
run: **1 passed in 7.24 seconds**. Both run directories retain immutable mounted
probe and host-test snapshots, result JSON, stderr and command arrays. The prior
failed candidate/report/manifest were preserved in `stdin-carrier/previous-source/`;
all historical raw evidence remains intact.

Containers used UID/GID 1000, ALL capabilities dropped, no-new-privileges,
read-only root, network none, 1 CPU, 1 GiB memory/swap ceiling, 128 PIDs and a
64 MiB noexec/nosuid tmpfs. Only the unique new volume and read-only probe snapshot
were mounted. Network none still exposes loopback: only `lo` was observed. This
is lexical execution under network denial, not proof of no attempted networking.

All **14 containers and 2 volumes** created across these new attempts were
removed by exact name. Both filtered inventories were empty; cleanup failures
were empty. Primary failures and cleanup failures have separate evidence fields,
and every cleanup step is attempted. No packages/builds, owner corpus, shared
volumes, privileges, Beads, branches, worktrees, commits or delegation were used.

Focused Docker E2E, Ruff lint/format, strict mypy, Python compilation, manifest
JSON and whitespace checks passed. No broad suite ran. This is one pinned
Linux/Docker-local-volume mechanism proof, not production supervision, complete
scheduling/lock-order/concurrency qualification, power-loss durability or a
promise covering all upstream commands. Independent acceptance remains pending.
