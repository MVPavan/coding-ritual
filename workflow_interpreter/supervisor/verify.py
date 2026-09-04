"""§7.3 evidence: the pinned checks, run against the artifact commit's own tree.

Three properties, each of which was a hole:

1. **The tree under test is the ARTIFACT, not the workspace.** The checks run
   in a throwaway detached checkout of the commit the evidence names, created
   here and asserted clean before a single check runs. Grading the live working
   tree let a runner commit a broken tree, leave a good one uncommitted, and
   collect a `done` whose evidence named the broken commit (probed). §7.4 says
   the recorded identity is the commit; §7.3's checks have to be about the same
   object.

2. **One resolution decides which file runs, and the exec uses the OPEN
   DESCRIPTOR that was hashed.** `ResolvedCheck` computes the run directory,
   the canonical program path and the argv in a single step; the program is
   then opened once, hashed through that descriptor, and exec'd through
   `/proc/self/fd/<n>` — so the file that is HASHED and the file that is
   EXECUTED are the same INODE, not merely the same path. The path version
   could be two files: the digest was taken at `tree/argv[0]` while
   `subprocess` resolved a relative `argv[0]` against `check.cwd`, so
   `cwd = "sub"` hashed the honest script and ran `sub/scripts/verify.sh`
   instead (probed). Resolving once closed that; the descriptor closes the
   remaining window in which something replaces the path between the two.

2b. **A check cannot reach outside the tree at all.** `cwd` is authored in the
   pinned graph, and `..`, an absolute path or a symlink out of the checkout
   would put the check back on the live working tree that property 1 exists to
   avoid. `run_dir` and `program` are canonicalized and must both stay inside
   the detached tree; anything else is refused, not run. Defense in depth: the
   digest already has to match, and this makes the escape unexpressible.

3. **A check that cannot RUN is a result, not an exception.** Only
   `TimeoutExpired` was caught, so a non-executable script raised
   `PermissionError` out of `observe()`, no exit record was ever written, and
   the activation repeated as `error_transport` until the §10.2 infra cap
   burned. Every `OSError` is now exit code 126 with an audit flag.

The refusal order is deliberate and unchanged: provenance is decided BEFORE
execution, and a mismatch does not run the check at all (§7.3, drill 13).
"""

from __future__ import annotations

import hashlib
import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path
from types import TracebackType
from typing import Final

import structlog

from workflow_interpreter.schema.graph_index import duration_seconds
from workflow_interpreter.schema.models import Node, VerifyCheck
from workflow_interpreter.supervisor.channels import verifier_digest_key
from workflow_interpreter.supervisor.errors import VerifyTreeError
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.models import VerifyResult
from workflow_interpreter.supervisor.paths import ENCODING, WrapperPaths

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

PROC_FD_TEMPLATE: Final[str] = "/proc/self/fd/{descriptor}"
"""How the hashed descriptor is exec'd. Linux-only, like the rest of the
package (§5.3), and the only argv[0] that cannot name a different file from
the one the digest was taken from."""

BASE_COMMIT_ENV: Final[str] = "WF_BASE_COMMIT"
"""The one `WF_*` variable a §7.3 check is given: the activation's
`intended_base_commit`.

A check runs in a detached checkout whose HEAD is the artifact commit and which
has no branch, no upstream and no reflog of its own — so a check that must ask
what THIS round changed (`tests-untouched.sh`, `mutate.sh`) has no other way to
name where the round started. It is injected for every check, not only the ones
that read it, so the environment a check sees does not depend on the node.

For a non-writing node the base equals the verified head (phase 7, D5), which
makes a diff-based check empty there by design rather than by accident."""

READ_CHUNK: Final[int] = 65536

REFUSED_EXIT_CODE: Final[int] = 126
"""A check whose provenance failed is REFUSED, not run — recorded as 126
(POSIX 'found but not executable'), so evidence never contains a pass from an
examiner the runner could have rewritten. A check that could not be started at
all lands on the same code for the same reason: it did not pass."""
TIMEOUT_EXIT_CODE: Final[int] = 124

RED_CHECK_RERUNS: Final[int] = 1
"""How many extra times a check that RAN and came back non-zero is run again.

One rerun is what tells a flaky check from a red artifact (cr-o85.34.14). A
racy test graded the activation `fail_code`, the graph routed it to the
implementer, who had nothing to change, re-committed an identical tree, and
§10.5's no-progress breaker sent the run to a human gate. A check that is red
TWICE at the same commit, with the same descriptor and the same timeout, is the
artifact's problem and grades `fail_code` exactly as before. Deliberately not
configurable: a graph that could raise this could re-roll a red check until it
passed, and §7.3 evidence would stop meaning anything."""

VERIFY_OUTPUT_TAIL_BYTES: Final[int] = 2048
"""How many bytes of one attempt's combined output are kept as evidence.

A `fail_code` that names only an exit code makes a human infer the cause: live,
`scripts/review-checks.sh` exited 1 and neither `completion.json` nor the bead
held a byte of what it printed (cr-o85.34.12). The tail is that byte record.

Bounded PER ATTEMPT rather than per check so `completion.json` stays small and
a chatty check cannot bloat a durable record: the tail is for a human reading a
verdict after the fact, not a full transcript, and the failing lines of a check
are the last ones it prints."""

STDERR_SEPARATOR: Final[bytes] = b"\n--- stderr ---\n"
"""Marks where a captured stdout ends and its stderr begins in one tail.

The two streams are captured separately, so a tail that just concatenated them
would read as one stream and put a diagnostic line in the wrong place."""

_MSG_TREE_DIRTY: Final[str] = (
    "the §7.3 verify checkout at {path} is not a clean {commit} (HEAD {head}, "
    "{dirty} dirty path(s)); evidence computed there would not be about the "
    "artifact commit"
)
_MSG_EMPTY_CMD: Final[str] = "verify cmd {cmd!r} has no program to run"
_MSG_UNRUNNABLE: Final[str] = "{program} could not be executed: {error}"
_MSG_ESCAPES: Final[str] = (
    "verify check {cmd!r} resolves to {resolved}, outside the §7.3 checkout at "
    "{tree}; a check that reaches out of the artifact's own tree is grading "
    "something else and is refused, never run"
)


class VerifyTree:
    """A throwaway detached checkout of one commit, asserted clean.

    A context manager because the guarantee is only worth anything while it
    holds: the tree is created, proven to be exactly `commit` with nothing
    modified, used, and removed. It lives under the wrapper dir rather than
    beside the runner's workspace, so nothing the runner can still write
    reaches it.
    """

    def __init__(self, git: Git, paths: WrapperPaths, commit: str) -> None:
        self._git = git
        self._paths = paths
        self._commit = commit
        self._repo = paths.config.repo_root

    def __enter__(self) -> Path:
        """Create the checkout and prove it is a clean `commit`."""
        path = self._paths.verify_tree
        self._clear(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._git.worktree_add_detached(path, self._commit, cwd=self._repo)
        head = self._git.head_commit(cwd=path)
        dirty = self._git.status_paths(cwd=path)
        if head != self._commit or dirty:
            raise VerifyTreeError(
                _MSG_TREE_DIRTY.format(
                    path=path, commit=self._commit, head=head, dirty=len(dirty)
                )
            )
        return path

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Remove the checkout, whatever the checks did."""
        self._clear(self._paths.verify_tree)

    def _clear(self, path: Path) -> None:
        """Leave nothing at `path` and no stale worktree registration for it.

        Best effort in both steps: a previous run killed mid-check leaves both
        a directory and a registration behind, and neither is a reason to
        refuse to compute this run's evidence.
        """
        self._git.worktree_remove(path, cwd=self._repo, check=False)
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        self._git.worktree_prune(cwd=self._repo)


class ResolvedCheck:
    """Where one check runs and exactly which file it runs — resolved once."""

    def __init__(self, tree: Path, check: VerifyCheck) -> None:
        argv = shlex.split(check.cmd)
        if not argv:
            raise VerifyTreeError(_MSG_EMPTY_CMD.format(cmd=check.cmd))
        self.cmd = check.cmd
        self.cwd = check.cwd
        self.pin_name = argv[0]
        """The declared program; the §7.3 digest is pinned under `cwd / this`."""
        root = _canonical(tree)
        self.run_dir = _canonical(tree / (check.cwd or ""))
        self.program = _canonical(self.run_dir / argv[0])
        """The one file this check hashes AND executes."""
        self.escapes = _escape_reason(check, root, self.run_dir, self.program)
        """Why this check reaches outside the checkout, or `None` when it does
        not. Recorded rather than raised: §7.3 makes an unusable check a
        REFUSED verdict, and raising here would skip the exit record §7.1
        depends on."""
        self.argv_tail = argv[1:]
        self.timeout_s = duration_seconds(check.timeout)


def _canonical(path: Path) -> Path:
    """Fully resolved: `..` folded, symlinks followed, absolute.

    Both of those matter for containment. `..` is what a pinned graph can spell
    directly; a symlink is what a repository can COMMIT, so the escape survives
    the clean-checkout assertion `VerifyTree` makes.
    """
    return Path(os.path.realpath(path))


def _escape_reason(
    check: VerifyCheck, root: Path, run_dir: Path, program: Path
) -> str | None:
    """Whether the resolved run dir and program both stay inside the checkout."""
    for resolved in (run_dir, program):
        if not resolved.is_relative_to(root):
            return _MSG_ESCAPES.format(cmd=check.cmd, resolved=resolved, tree=root)
    return None


def run_checks(
    node: Node,
    tree: Path,
    pinned_digests: dict[str, str],
    *,
    base_commit: str,
) -> tuple[VerifyResult, ...]:
    """Execute the PINNED graph's checks in `tree`: provenance first, no shell.

    `base_commit` is the activation's `intended_base_commit`, passed to every
    check as `BASE_COMMIT_ENV`.
    """
    results: list[VerifyResult] = []
    for check in node.verify or ():
        resolved = ResolvedCheck(tree, check)
        if resolved.escapes is not None:
            _LOG.error("wf.verify.escapes_tree", node=node.name, cmd=check.cmd)
            results.append(_refused(resolved, "", None, error=resolved.escapes))
            continue
        descriptor = _open_program(resolved.program)
        try:
            digest = "" if descriptor is None else _digest_of(descriptor)
            key = verifier_digest_key(node.name, resolved.cwd, resolved.pin_name)
            pinned = pinned_digests.get(key)
            if descriptor is None or not pinned or pinned != digest:
                _LOG.error(
                    "wf.verify.provenance",
                    node=node.name,
                    cmd=check.cmd,
                    program=str(resolved.program),
                    pinned=pinned,
                    actual=digest,
                )
                results.append(_refused(resolved, digest, pinned))
                continue
            results.append(_execute(resolved, descriptor, digest, pinned, base_commit))
        finally:
            if descriptor is not None:
                os.close(descriptor)
    return tuple(results)


def _refused(
    resolved: ResolvedCheck,
    digest: str,
    pinned: str | None,
    *,
    error: str | None = None,
) -> VerifyResult:
    """A check that was NOT run, and the evidence saying so."""
    return VerifyResult(
        cmd=resolved.cmd,
        exit_code=REFUSED_EXIT_CODE,
        script_digest=digest,
        pinned_digest=pinned,
        provenance_ok=False,
        program=str(resolved.program),
        error=error,
    )


def _open_program(path: Path) -> int | None:
    """Open the check's program once, or `None` when there is nothing to open.

    This descriptor is the check's identity from here on: it is what the digest
    is taken from and what the exec runs. A program that is not there yields
    `None`, which hashes to `""`, which no pin matches — §7.3's own answer for
    a verifier whose provenance cannot be established.

    The descriptor must name a REGULAR FILE, and that is checked through the
    descriptor itself rather than through the path. `os.open` on a directory
    succeeds; `os.pread` on the result then raises `IsADirectoryError` from
    inside `_digest_of`, which is not where §7.3 answers questions — it escaped
    `observe()` entirely, and a directory committed at a verifier's path is
    something the runner being graded can arrange (Sol#17).

    `O_NONBLOCK` is what makes the check REACHABLE for the other non-regular
    kinds. A FIFO at the verifier's path blocks in `os.open` itself until some
    writer appears, so an fstat guard behind a blocking open never runs — the
    §7 computation simply stops, forever, and the wrapper's own `max_wall` does
    not cover its post-exit work (found while covering this fix). On a regular
    file the flag changes nothing, and the exec re-opens the inode through
    `/proc/self/fd/<n>` regardless.
    """
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    except OSError as exc:
        _LOG.error("wf.verify.unopenable", program=str(path), error=str(exc))
        return None
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            _LOG.error("wf.verify.not_a_regular_file", program=str(path))
            os.close(descriptor)
            return None
    except OSError as exc:  # pragma: no cover - fstat on an open fd
        _LOG.error("wf.verify.unstattable", program=str(path), error=str(exc))
        os.close(descriptor)
        return None
    return descriptor


def _digest_of(descriptor: int) -> str:
    """sha256 of an OPEN descriptor, read positionally so the offset never moves."""
    hasher = hashlib.sha256()
    offset = 0
    while True:
        chunk = os.pread(descriptor, READ_CHUNK, offset)
        if not chunk:
            return hasher.hexdigest()
        hasher.update(chunk)
        offset += len(chunk)


def _execute(
    resolved: ResolvedCheck,
    descriptor: int,
    digest: str,
    pinned: str,
    base_commit: str,
) -> VerifyResult:
    """Run the check, re-running a RED one `RED_CHECK_RERUNS` times.

    Only a check that ran to completion and came back non-zero is re-run — a
    timeout and a program that could not be started are results about the
    check itself, and repeating them buys nothing but the timeout again. The
    rerun is the same tree, the same already-hashed descriptor and the same
    timeout, so the final attempt's exit code is evidence about the same
    object the first attempt was.
    """
    attempt = 1
    tails: list[str] = []
    while True:
        result = _run_once(resolved, descriptor, digest, pinned, attempt, base_commit)
        # Every attempt's tail is kept, not just the surviving result's: when a
        # rerun turns the check green, the RED attempt's output is the one a
        # human wants to read (cr-o85.34.12).
        tails.extend(result.output_tails)
        rerunnable = (
            result.exit_code != 0 and not result.timed_out and result.error is None
        )
        if not rerunnable or attempt >= 1 + RED_CHECK_RERUNS:
            return result.model_copy(update={"output_tails": tuple(tails)})
        attempt += 1
        _LOG.warning(
            "wf.verify.rerun",
            cmd=resolved.cmd,
            exit_code=result.exit_code,
            attempt=attempt,
        )


def _run_once(
    resolved: ResolvedCheck,
    descriptor: int,
    digest: str,
    pinned: str,
    attempts: int,
    base_commit: str,
) -> VerifyResult:
    """Run the HASHED descriptor with its declared timeout, argv only, no shell.

    `argv[0]` is `/proc/self/fd/<n>` rather than the program's path, and the
    descriptor is passed through to the child. The path could be rewritten
    between the hash and the exec — an editor or a `git checkout` renames a new
    inode over the old name, and a path-based exec would then run bytes nobody
    vouched for. The descriptor cannot: it names the inode that was hashed,
    even once nothing links to it any more.

    Output is captured as BYTES, not text: `text=True` decodes strictly, so a
    check that printed a single non-UTF-8 byte would raise `UnicodeDecodeError`
    out of `subprocess.run` — an exception neither handler below catches, from
    a check that ran perfectly well. The tail decodes leniently instead.
    """
    try:
        completed = subprocess.run(
            [PROC_FD_TEMPLATE.format(descriptor=descriptor), *resolved.argv_tail],
            cwd=resolved.run_dir,
            capture_output=True,
            text=False,
            timeout=resolved.timeout_s,
            check=False,
            pass_fds=(descriptor,),
            env={**os.environ, BASE_COMMIT_ENV: base_commit},
        )
    except subprocess.TimeoutExpired as expired:
        return VerifyResult(
            cmd=resolved.cmd,
            exit_code=TIMEOUT_EXIT_CODE,
            script_digest=digest,
            pinned_digest=pinned,
            provenance_ok=True,
            timed_out=True,
            program=str(resolved.program),
            attempts=attempts,
            # Whatever the check printed before the kill is the only evidence
            # of WHERE it hung; both streams are `None` when it printed nothing.
            output_tails=(_output_tail(expired.stdout, expired.stderr),),
        )
    except OSError as exc:
        # Not executable, no interpreter, a run_dir that is not a directory:
        # the check did not pass and the wrapper still owes an exit record.
        _LOG.error("wf.verify.unrunnable", cmd=resolved.cmd, error=str(exc))
        return VerifyResult(
            cmd=resolved.cmd,
            exit_code=REFUSED_EXIT_CODE,
            script_digest=digest,
            pinned_digest=pinned,
            provenance_ok=True,
            program=str(resolved.program),
            error=_MSG_UNRUNNABLE.format(program=resolved.program, error=exc),
            attempts=attempts,
            # Nothing was started, so there is no output to keep — the `error`
            # above is the whole story of this result.
        )
    return VerifyResult(
        cmd=resolved.cmd,
        exit_code=completed.returncode,
        script_digest=digest,
        pinned_digest=pinned,
        provenance_ok=True,
        program=str(resolved.program),
        attempts=attempts,
        output_tails=(_output_tail(completed.stdout, completed.stderr),),
    )


def _output_tail(stdout: bytes | None, stderr: bytes | None) -> str:
    """The last `VERIFY_OUTPUT_TAIL_BYTES` of one attempt's combined output.

    Decoded leniently, like every other tail in the wrapper: the cut lands on
    an arbitrary byte, so a partial UTF-8 sequence at the front is expected and
    is never a reason to lose the evidence.
    """
    combined = stdout or b""
    if stderr:
        combined = combined + STDERR_SEPARATOR + stderr
    return combined[-VERIFY_OUTPUT_TAIL_BYTES:].decode(ENCODING, errors="replace")


__all__ = [
    "BASE_COMMIT_ENV",
    "RED_CHECK_RERUNS",
    "REFUSED_EXIT_CODE",
    "TIMEOUT_EXIT_CODE",
    "VERIFY_OUTPUT_TAIL_BYTES",
    "ResolvedCheck",
    "VerifyTree",
    "run_checks",
]
