# Filesystem slot-lock qualification

## Verdict and scope

The local Linux `fcntl.flock` prototype is qualified on the filesystem used by
this run for the narrow behavior below. It is a characterization of Python
process and descriptor lifetime, not production DWS runtime code.

The tested target was Linux `6.6.87.2-microsoft-standard-WSL2` on an `ext4`
filesystem. Tests use pytest's isolated temporary directory by default. The
target directory can instead be selected with `DWS_LOCK_QUALIFICATION_DIR` to
repeat the probe on an intended container volume.

This result does **not** complete G-03 or establish actual QMD inheritance,
QMD startup/update behavior, container filesystem semantics, or the deployed
volume's behavior. Those remain separate qualification work.

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
  competing contender denied. After the test terminates that exact announced
  child PID, a contender acquires the slot.
- The negative control starts the same child without the descriptor. Killing
  the supervisor then lets a competing contender acquire the slot while the
  child is still alive. This is an observed early-release failure, not a safe
  ownership pattern.

The probe has readiness handshakes, five-second process/selector deadlines, a
15-second maximum helper lifetime, and `finally` cleanup. It targets only PIDs
created and announced by the probe; it never signals a process group or scans
for a process to kill.

## Test-first evidence and observed commands

Before descriptor inheritance was implemented, the lifecycle test was run as:

```sh
cd dws
python3 -m pytest -q \
  tests/qualification/test_slot_lock_lifecycle.py::test_parent_crash_does_not_release_a_lock_held_by_surviving_child
```

It failed as intended: one failure reported `assert 0 == 75` after the parent
was killed, because the competing process printed `ACQUIRED`. That is the
unsafe parent-only control the final suite retains explicitly.

After passing the locked descriptor into the child, the same focused command
reported `1 passed in 0.09s`. The final local run reported:

```text
python3 -m pytest -q tests/qualification                         5 passed in 0.30s
ruff check tests/qualification                                    All checks passed!
ruff format --check tests/qualification                           2 files already formatted
python3 -m py_compile tests/qualification/lock_probe.py \
  tests/qualification/test_slot_lock_lifecycle.py                 exit 0
```

The locked `uv` command could not be exercised in this model sandbox: its
injected frozen environment conflicted with `--locked`; after unsetting that
flag, uv attempted to download its managed Python and DNS was unavailable.
No dependency installation was retried. The declared host gate remains the
authority for `uv sync --locked` and `scripts/verify-dws-pilot.py`.

## Deployment-volume rerun

Create or select an empty, writable parent directory on the intended local
container volume, then run:

```sh
cd dws
DWS_LOCK_QUALIFICATION_DIR=/path/on/intended-volume/lock-qualification \
  uv run --locked pytest -q tests/qualification
```

The suite creates a UUID-named child directory beneath that parent and removes
only that child during fixture cleanup. A failure on the intended target is a
qualification failure: do not silently fall back to per-process semaphores or
a different filesystem. Record the target's platform, mount type, command
output, and the resulting coordination decision before using this mechanism.

## Remaining limitations

- This uses Python fixture children, not the pinned QMD executable. A future
  QMD adapter must prove its own descriptor inheritance and process-group
  supervision behavior.
- `flock` behavior is qualified only for the observed local Linux filesystem.
  Network filesystems, Docker/Compose mounts, overlay configurations, and the
  deployment volume are unverified until rerun there.
- Descriptor lifetime protects local admission only. It does not prove a
  remote provider stopped when a client or supervisor dies; later runtime work
  must retain and reconcile remote handles conservatively.
- This qualification does not add a runtime slot-lock implementation or claim
  that all QMD query/update/maintenance concurrency requirements have passed.
