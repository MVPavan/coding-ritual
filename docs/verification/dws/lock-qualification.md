# Filesystem slot-lock qualification

## Verdict and scope

The local Linux `fcntl.flock` prototype is qualified on the filesystem observed
by this run for the narrow behavior below. It is a characterization of Python
process and descriptor lifetime, not production DWS runtime code.

The latest local run used Linux `6.6.87.2-microsoft-standard-WSL2` on
`x86_64 GNU/Linux` (from `uname -srmo`). Its pytest temporary lock directory
emitted `FILESYSTEM=ext4` after the probe read `/proc/self/mountinfo`. The
dynamic target and mount paths are deliberately not copied into this committed
record: they are machine-local. Tests use pytest's isolated temporary directory
by default. Select a deployment-volume parent with
`DWS_LOCK_QUALIFICATION_DIR` to qualify that particular mount.

This result does **not** complete G-03 or establish actual QMD inheritance,
QMD startup/update behavior, container filesystem semantics, or deployed-volume
behavior. Those remain separate qualification work.

## Mechanism characterized

The probe uses one `flock(LOCK_EX)` file per capacity slot and has independent
Python subprocesses contend with `LOCK_NB`.

- A single occupied slot rejects a second independent contender.
- Two occupied slots reject a third independent contender.
- Once the holder exits and closes its descriptor, an independent contender
  can acquire the released slot.
- In the safe lifecycle pattern, the supervisor passes the already-locked file
  descriptor to its child with `subprocess.Popen(..., pass_fds=(fd,))`.
  Killing the supervisor with `SIGKILL` while that child survives leaves a
  competing contender denied. After the test terminates the exact announced
  child PID and confirms its exit, a contender acquires the slot.
- The negative control starts the same child without the descriptor. Killing
  the supervisor then lets a competing contender acquire the slot while the
  child is still alive. This is an observed early-release failure, not a safe
  ownership pattern. Its cleanup confirms the signalled child exits.

The probe has readiness handshakes, test-side five-second process/selector
deadlines, a three-second supervisor child-readiness deadline, a 15-second
maximum helper lifetime, and `finally` cleanup. It targets only PIDs created
and announced by the probe; it never signals a process group or scans for a
process to kill.

## Test-first evidence and local commands

The filesystem-observation test was added before the probe role. Its focused
RED run failed with exit status 1 because `filesystem` was not a recognized
probe role. After adding the `/proc/self/mountinfo` reader, its focused GREEN
run passed and emitted an `ext4` target record.

The lifecycle suite retains a real-process negative control: parent-only
descriptor ownership allows a contender to print `ACQUIRED` after the parent
dies, whereas the inherited-descriptor test requires `BUSY` until the child
dies. Thus an omitted descriptor transfer fails the safe-lifecycle assertion.

The following commands were run against the committed qualification source:

```text
cd dws
python3 -m pytest -q -s tests/qualification
  TARGET=<dynamic pytest directory> FILESYSTEM=ext4 MOUNT=<local mount path>
  6 passed in 0.38s

ruff check .
  All checks passed!

ruff format --check .
  8 files already formatted

python3 -m py_compile tests/qualification/lock_probe.py \
  tests/qualification/test_slot_lock_lifecycle.py
  exit 0

mypy --strict src/dws
  Success: no issues found in 3 source files
```

`python3 -m pytest -q` was also attempted, but is not an equivalent package
check in this sandbox: collection stopped at `tests/test_package.py` because
the current interpreter has not installed the `dws` distribution
(`ModuleNotFoundError: No module named 'dws'`). That is recorded as an
environment limitation, not a passing suite. The declared HOST gate remains
the authority for `uv sync --locked` and `scripts/verify-dws-pilot.py`; neither
host-only command was run here.

## Deployment-volume rerun

Create or select an empty, writable parent directory on the intended local
container volume, then run:

```sh
cd dws
DWS_LOCK_QUALIFICATION_DIR=/path/on/intended-volume/lock-qualification \
  uv run --locked pytest -q -s tests/qualification
```

The suite creates a UUID-named child directory beneath that parent and removes
only that child during fixture cleanup. The emitted `TARGET`, `FILESYSTEM`, and
`MOUNT` record is the evidence of the precise mount tested. Preserve that output
with the platform command output and resulting coordination decision. A failure
on the intended target is a qualification failure: do not silently fall back to
per-process semaphores or a different filesystem.

## Remaining limitations

- This uses Python fixture children, not the pinned QMD executable. A future
  QMD adapter must prove its own descriptor inheritance and process-supervision
  behavior.
- `flock` behavior is qualified only for the observed local Linux filesystem.
  Network filesystems, Docker/Compose mounts, overlay configurations, and the
  deployment volume are unverified until rerun there.
- Descriptor lifetime protects local admission only. It does not prove a
  remote provider stopped when a client or supervisor dies; later runtime work
  must retain and reconcile remote handles conservatively.
- This qualification does not add a runtime slot-lock implementation or claim
  that all QMD query/update/maintenance concurrency requirements have passed.
