"""Vendor-neutral machinery every §6 profile shares.

Four things live here because getting any of them wrong in one adapter would
be invisible until production:

- **The child environment is built in ONE place**, and it routes through
  `RunnerChannels.env()`. That call is what stamps the §7.4 committer identity
  onto the child; a profile that assembled its own `dict` would leave every
  in-repo commit unattributable, `pin_artifact` would refuse it, and a `done`
  claim on a writing node would grade `fail_code` with nothing to point at
  (§14, phase-3 ruling). `command()` is therefore the only constructor of a
  `RunnerCommand` in this package, so no adapter can skip it.
- **`launch` execs through the injected `ChildLauncher` and does nothing else.**
  The §5.2 fork barrier and the exec ledger are the crash-atomicity contract;
  `launch.py` verifies the receipt afterwards, so an adapter that forked its own
  child is caught rather than trusted.
- **The push backstop is set for EVERY vendor**, in the child env rather than
  in one vendor's flags (`push_backstop`). Two of the three CLIs cannot deny a
  push at all, and the third could only deny the spellings somebody thought of.
- **`parse_output` never raises.** The launcher dup2s the runner log onto BOTH
  fd 1 and fd 2 (`launch.py::_child`), so the "machine event stream" is
  guaranteed to carry non-JSON vendor chatter — every CLI probed writes a stdin
  complaint to stderr — on top of the torn final line a crash leaves. A parser
  that threw on either would turn a recoverable dispatch into a crash loop
  (drill 18). Unparseable lines become `EventType.ERROR` events with the raw
  text, which is conservative and lossless; nothing in the wrapper ROUTES on
  these events (`exit.py` reads the reserved channel itself, `monitor.py`
  measures byte growth), so a misclassified stderr line costs nothing.

`usage: unknown` is legal (§6): it disables only the best-effort token ceiling,
and `max_wall` always holds.
"""

from __future__ import annotations

import json
import shlex
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import ClassVar, Final

import structlog
from pydantic import BaseModel, ConfigDict

from workflow_interpreter.bdio import ProcessHandle, Usage
from workflow_interpreter.profiles.config import ProfileConfig, RunnerName
from workflow_interpreter.profiles.errors import TaskRefused
from workflow_interpreter.supervisor import procfs
from workflow_interpreter.supervisor.clock import Clock, elapsed_seconds
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.models import Liveness, TerminationProof
from workflow_interpreter.supervisor.profile import (
    Capabilities,
    ChildLauncher,
    EventType,
    InspectResult,
    ProcessStatus,
    RunnerChannels,
    RunnerCommand,
    RunnerEvent,
    TaskSpec,
    TerminalEnvelope,
)
from workflow_interpreter.supervisor.sandbox import (
    ENV_MYPY_CACHE_DIR,
    ENV_PYTEST_ADDOPTS,
    ENV_RUFF_CACHE_DIR,
    ENV_UV_FROZEN,
    ENV_UV_PROJECT_ENVIRONMENT,
    PYTEST_CACHE_OPTION,
    UV_FROZEN_VALUE,
)

_LOG: Final[structlog.stdlib.BoundLogger] = structlog.get_logger(__name__)

SCAN_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="forbid", arbitrary_types_allowed=False
)

ENV_TMPDIR: Final[str] = "TMPDIR"
"""Pointed at `$WF_SCRATCH_DIR` in every child (see `BaseProfile.child_env`)."""

PUSH_SINK: Final[str] = "wf-no-push://blocked/"
"""Where every remote a child could push to is rewritten (see `push_backstop`).

An unknown transport rather than an unreachable host: git answers it with
`'remote-wf-no-push' is not a git command` immediately and offline, so the
refusal costs no DNS lookup, no timeout, and cannot be defeated by a network
that happens to work."""

PUSH_URL_PREFIX: Final[str] = ""
"""The prefix every remote URL starts with, which is the point.

`pushInsteadOf` is a LONGEST-PREFIX match over the URL as written, so the empty
string matches every one of them and one entry covers the whole space. An
enumeration cannot: it was five prefixes claiming to be "every URL form a
`git push` can name a remote with", and probed against real `git remote get-url
--push`, three common spellings walked straight through it —
`deploy@host:wf/repo.git` (scp-style with any user other than `git`, the usual CI
form), `ftp://…` (whose helper is installed on this host), and a plain local path.
`ext::sh -c …` did too, and only git's default protocol allowlist stopped it.

With the empty prefix all nine probed forms rewrite, `ext::` included. The
backstop is COOPERATIVE by construction (§0.3), and in two ways, not one: a
child can unset the variables, and — because the match is longest-prefix — a
child can add its own LONGER-prefix `pushInsteadOf` (`git -c url.<x>.pushInsteadOf=https://`
or a `GIT_CONFIG_COUNT=2` entry of its own) and that entry wins over this one
(probed, git 2.43). What this removes is every accidental push and every push
phrased around a prefix rule; a hostile child is bounded only by the OS
network sandbox (codex) or by nothing (claude, which reports
`denies_network=False` for exactly this reason)."""

UV_VENV_DIR: Final[str] = "venv"
RUFF_CACHE_DIR: Final[str] = "ruff"
MYPY_CACHE_DIR: Final[str] = "mypy"
PYTEST_CACHE_DIR: Final[str] = "pytest"
"""Subdirectories of `$WF_SCRATCH_DIR` the §2 toolchain env names."""

ENV_GIT_CONFIG_COUNT: Final[str] = "GIT_CONFIG_COUNT"
ENV_GIT_CONFIG_KEY: Final[str] = "GIT_CONFIG_KEY_{index}"
ENV_GIT_CONFIG_VALUE: Final[str] = "GIT_CONFIG_VALUE_{index}"
PUSH_INSTEAD_OF: Final[str] = "url.{sink}.pushInsteadOf"


def toolchain_env(scratch_dir: str) -> dict[str, str]:
    """Point every toolchain cache at `$WF_SCRATCH_DIR` (plan §2, blocker 2).

    A read-only checkout breaks the node's OWN `verify` command: `uv run`
    creates `.venv` in the checkout, and ruff and mypy create their caches
    there. Probed under a bwrap'd read-only checkout of this repo: with none of
    these, `uv run pytest` dies `failed to create directory '<C>/.venv':
    Read-only file system`; with `UV_PROJECT_ENVIRONMENT` alone, ruff and mypy
    still die on their own caches; with all four, all three tools pass.

    `PYTEST_ADDOPTS` is SET, not appended: `child_env` copies only
    `passthrough_env` keys and `PYTEST_ADDOPTS` is not one of them, so there is
    never an inherited value to preserve and an append branch would be code that
    can never run. Its path is `shlex.quote`d because pytest shlex-SPLITS the
    variable — an unquoted cache dir containing a space arrives as two arguments
    and the run dies on an unrecognised one. That one is a nicety rather than
    load-bearing (pytest degrades to a warning when it cannot write its cache),
    but a nicety that breaks the gate is not a nicety.

    Applied for every profile and in every mode. The bound is not the only
    reason it is right, and a cache location that changed with the sandbox
    setting would make an `off` run stop reproducing a `bwrap` one.
    """
    scratch = Path(scratch_dir)
    return {
        ENV_UV_PROJECT_ENVIRONMENT: str(scratch / UV_VENV_DIR),
        ENV_UV_FROZEN: UV_FROZEN_VALUE,
        ENV_RUFF_CACHE_DIR: str(scratch / RUFF_CACHE_DIR),
        ENV_MYPY_CACHE_DIR: str(scratch / MYPY_CACHE_DIR),
        ENV_PYTEST_ADDOPTS: PYTEST_CACHE_OPTION.format(
            path=shlex.quote(str(scratch / PYTEST_CACHE_DIR))
        ),
    }


def push_backstop() -> dict[str, str]:
    """Child env that rewrites every pushable remote to a dead transport (§6).

    "No profile ever pushes" was three claude deny-rules matching one spelling
    of one command, in one vendor. This is the vendor-neutral half: git reads
    `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n` from the
    ENVIRONMENT, so the rewrite applies to every git any process in the child's
    tree runs, whatever tool spawned it and however the command was phrased.

    It is a backstop, not the policy, and §0.3's semi-trusted runner can unset
    the variables — which is precisely why codex's `network_access = false` and
    the supervisor's own closed subcommand set both still exist. What it removes
    is every ACCIDENTAL push, and every push phrased around a prefix rule.

    ONE entry, keyed on the empty prefix (`PUSH_URL_PREFIX`): the rewrite is a
    longest-prefix match, so enumerating transports could only ever be as
    complete as the enumerator was, and it was not.
    """
    return {
        ENV_GIT_CONFIG_COUNT: "1",
        ENV_GIT_CONFIG_KEY.format(index=0): PUSH_INSTEAD_OF.format(sink=PUSH_SINK),
        ENV_GIT_CONFIG_VALUE.format(index=0): PUSH_URL_PREFIX,
    }


ENCODING: Final[str] = "utf-8"
DECODE_ERRORS: Final[str] = "replace"
"""A JSONL tail is routinely a partial UTF-8 sequence (§8.2). Decoding
leniently keeps a torn byte from becoming an exception in a reader whose whole
contract is that it does not raise."""

_MSG_UNDECODABLE: Final[str] = (
    "{runner}: could not decode a vendor event ({error}): {line}"
)

_MSG_EMPTY_BRIEF: Final[str] = (
    "{runner}: the task for node {node} has an empty brief; a runner CLI given "
    "no prompt argument reads its instructions from stdin, which the launcher "
    "does not redirect"
)
_MSG_RELATIVE: Final[str] = (
    "{runner}: {label} must be an absolute path, got {value!r}; a relative path "
    "in a sandbox rule silently anchors somewhere else"
)


class LogScan(BaseModel):
    """One pass over a runner log: the session it names and what it spent."""

    model_config = SCAN_MODEL

    session: str | None = None
    usage: Usage = Usage(known=False)


def json_object(line: str) -> Mapping[str, object] | None:
    """The JSON object a line holds, or `None` when it is not one.

    `None` covers every way a line can fail to be a vendor event: torn JSON, a
    stderr sentence, an empty line, and valid JSON that is not an object.
    """
    stripped = line.strip()
    if not stripped:
        return None
    try:
        parsed = json.loads(stripped)
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_lines(
    stream: Iterable[str],
    decode: Callable[[Mapping[str, object]], RunnerEvent | None],
    runner: str = "",
) -> Iterator[RunnerEvent]:
    """Drive a vendor decoder over a stream, tolerating everything else.

    Blank lines are dropped (they carry nothing). Anything that is not a JSON
    object becomes an `ERROR` event holding the raw line, so a caller can see
    exactly what the wrapper could not read.

    So does anything the DECODER cannot turn into an event. Guarding only the
    JSON parse was half a guard: a well-formed line whose numbers are outside
    `bdio`'s carrier bounds — a token count bd's JSON path would silently round —
    raises `ValidationError` out of `Usage`, and `collect_terminal_envelope`
    re-reads the log after every exit, so the same line would have crashed every
    subsequent tick (drill 18's crash-loop, reached by a different door).
    `ValidationError` is a `ValueError` in pydantic v2, so one clause covers
    both it and a decoder's own arithmetic.
    """
    for line in stream:
        payload = json_object(line)
        if payload is None:
            text = line.strip()
            if not text:
                continue
            yield RunnerEvent(type=EventType.ERROR, text=text, is_error=True)
            continue
        try:
            event = decode(payload)
        except ValueError as error:
            _LOG.warning("wf.profile.undecodable", runner=runner, error=str(error))
            yield RunnerEvent(
                type=EventType.ERROR,
                text=_MSG_UNDECODABLE.format(
                    runner=runner, error=type(error).__name__, line=line.strip()
                ),
                is_error=True,
            )
            continue
        if event is not None:
            yield event


def mapping_at(payload: Mapping[str, object], key: str) -> Mapping[str, object]:
    """A nested object, or an empty one when the key is absent or wrong-typed."""
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def text_at(payload: Mapping[str, object], key: str) -> str:
    """A string field, or `""` when it is absent or not a string."""
    value = payload.get(key)
    return value if isinstance(value, str) else ""


def optional_text_at(payload: Mapping[str, object], key: str) -> str | None:
    """A string field, or `None` when it is absent, empty or not a string."""
    return text_at(payload, key) or None


def int_at(payload: Mapping[str, object], key: str) -> int | None:
    """An integer field, or `None` when it is absent or not an integer.

    `bool` is excluded deliberately: it is an `int` subclass in Python, and a
    `true` in a token field is a defect, not a count of one.
    """
    value = payload.get(key)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def decimal_at(payload: Mapping[str, object], key: str) -> Decimal | None:
    """A money field as an exact decimal, or `None` when it is unusable.

    Vendors report cost as a JSON float; `bdio.Usage` stores money as a decimal
    STRING because JSON floats are not exact. Going through `str()` keeps the
    vendor's own repr rather than inventing precision.
    """
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def fold_usage(events: Iterable[RunnerEvent]) -> Usage:
    """Normalize a stream's usage events into one §6 `Usage`.

    Cost is read from `RunnerEvent.cost_usd` and from nowhere else. §6's event
    carries `usage?` and `cost?` as separate fields, so a vendor decoder puts
    money on the event and tokens in the usage — two carriers for one number
    would be two things to keep in step.

    Tokens are SUMMED rather than last-wins: opencode reports per-step counts
    that are not cumulative (probed), and every step's input tokens are really
    billed, so a sum is what a token ceiling should be measuring. claude and
    codex each report one terminal total per exec, for which a sum is that
    total. `known = False` when no event carried usage at all — legal, and it
    disables only the best-effort ceiling (§6).
    """
    seen = False
    input_tokens = 0
    output_tokens = 0
    cost: Decimal | None = None
    for event in events:
        if event.usage is not None and event.usage.known:
            seen = True
            input_tokens += event.usage.input_tokens or 0
            output_tokens += event.usage.output_tokens or 0
        if event.cost_usd is not None:
            try:
                cost = (cost or Decimal(0)) + Decimal(event.cost_usd)
            except InvalidOperation:  # pragma: no cover - decimal_at guards this
                continue
    if not seen and cost is None:
        return Usage(known=False)
    return Usage(
        known=True,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=None if cost is None else str(cost),
    )


def require_absolute(runner: RunnerName, label: str, value: str) -> str:
    """Refuse a relative path where a bound depends on it being absolute."""
    if not Path(value).is_absolute():
        raise TaskRefused(
            _MSG_RELATIVE.format(runner=runner.value, label=label, value=value)
        )
    return value


class BaseProfile:
    """The shared half of a §6 profile; the vendor half is three subclasses."""

    runner: ClassVar[RunnerName]
    auth_env: ClassVar[tuple[str, ...]] = ()
    """Vendor credential keys copied from the host env when present. Named
    explicitly rather than pattern-matched: a prefix rule would hand a runner
    whatever new secret a future release happens to name."""
    sandboxed: ClassVar[bool] = False
    """Whether the vendor enforces the wrapper's write bound itself, rather than
    the wrapper merely asking it to. Reported through `capabilities()`."""
    denies_network: ClassVar[bool] = False
    reports_cost: ClassVar[bool] = False
    live_usage: ClassVar[bool] = False
    supports_resume: ClassVar[bool] = False

    def __init__(
        self,
        config: ProfileConfig,
        supervisor_config: SupervisorConfig,
        clock: Clock,
        host_env: Mapping[str, str],
    ) -> None:
        self._config = config
        self._supervisor_config = supervisor_config
        self._clock = clock
        self._host_env = dict(host_env)

    # -- identity ---------------------------------------------------------

    def name(self) -> str:
        """The profile's stable identifier (`runner = "profile:<name>"`)."""
        return self.runner.value

    def binary(self) -> str:
        """The executable this profile execs."""
        return self._config.binary_for(self.runner)

    def capabilities(self) -> Capabilities:
        """Declared capabilities; `live_usage = False` disables only the ceiling."""
        return Capabilities(
            live_usage=self.live_usage,
            resume=self.supports_resume,
            sandboxed=self.sandboxed,
            denies_network=self.denies_network,
            reports_cost=self.reports_cost,
        )

    # -- command construction --------------------------------------------

    def child_env(self, channels: RunnerChannels) -> dict[str, str]:
        """The child's COMPLETE environment: passthrough keys, then the channels.

        Complete because `launch.py` execs with `dict(command.env)` and nothing
        else — the child inherits none of the wrapper's environment. The §6
        channels and the §7.4 committer identity come from `channels.env()` and
        are written LAST, so no passthrough key can shadow them.

        `TMPDIR` points at `$WF_SCRATCH_DIR` for every vendor. The child's
        toolchain needs somewhere to write and the codex sandbox no longer
        grants `/tmp` (probe 12a), so the wrapper hands it one inside the box
        rather than leaving `TMPDIR` to whatever the host had — which is also
        why the codex profile no longer excludes `$TMPDIR` from the writable
        set: the variable is now the wrapper's own, and it names a directory
        already inside the grant.

        `toolchain_env` rides on the same channel and for the same reason: this
        is the merge that sees the INHERITED environment, which is what the
        `PYTEST_ADDOPTS` append needs and what `RunnerChannels.env()` — merged
        last, and taking no env at all — cannot have.
        """
        env = {
            key: self._host_env[key]
            for key in (*self._config.passthrough_env, *self.auth_env)
            if key in self._host_env
        }
        if channels.scratch_dir:
            env[ENV_TMPDIR] = channels.scratch_dir
            env.update(toolchain_env(channels.scratch_dir))
        return {**env, **push_backstop(), **channels.env()}

    def command(
        self,
        argv: Sequence[str],
        task: TaskSpec,
        session_id: str,
        *,
        cwd: str | None = None,
    ) -> RunnerCommand:
        """The one place a `RunnerCommand` is built (see the module docstring).

        `argv` is executed without a shell, so every element is a literal — no
        quoting, no metacharacters, no interpreter prefix.
        """
        return RunnerCommand(
            argv=tuple(argv),
            env=self.child_env(task.channels),
            cwd=cwd or task.cwd,
            log_path=task.channels.log_path,
            session_id=session_id,
        )

    def require_brief(self, task: TaskSpec) -> str:
        """The prompt argument, refusing the empty one.

        Every CLI probed falls back to READING STDIN when it has no prompt
        argument, and `launch.py::_child` redirects fd 1 and fd 2 but not fd 0 —
        so an empty brief does not produce an empty run, it produces a child
        blocked on the wrapper's own stdin.
        """
        if not task.brief.strip():
            raise TaskRefused(
                _MSG_EMPTY_BRIEF.format(runner=self.runner.value, node=task.node)
            )
        return task.brief

    # -- process lifecycle ------------------------------------------------

    def launch(self, command: RunnerCommand, launcher: ChildLauncher) -> ProcessHandle:
        """Exec THROUGH the supervisor's launcher; the barrier is not optional."""
        _LOG.info(
            "wf.profile.launch",
            runner=self.runner.value,
            session_id=command.session_id,
            program=command.argv[0],
        )
        return launcher(command)

    def inspect(self, handle: ProcessHandle) -> InspectResult:
        """Alive or dead, proven by the §5.3 handle identity rather than the pid.

        An INDETERMINATE `/proc` read reports ALIVE. `InspectResult` has no third
        state, and the conservative direction is the only safe one: calling an
        unreadable `/proc` DEAD is what let a retry run concurrently with a
        survivor (`procfs`). The exit code stays `None` — reading it means
        reaping, and reaping is `ExitObserver`'s, not a vendor adapter's.
        """
        proof = procfs.prove_liveness(self._supervisor_config, handle)
        alive = proof.alive or proof.status is Liveness.INDETERMINATE
        return InspectResult(
            status=ProcessStatus.ALIVE if alive else ProcessStatus.DEAD
        )

    def terminate(self, handle: ProcessHandle) -> TerminationProof:
        """TERM → bounded wait → KILL, with proof of death (§8.1)."""
        return procfs.terminate(self._supervisor_config, handle, self._clock)

    def collect_terminal_envelope(self, handle: ProcessHandle) -> TerminalEnvelope:
        """The runner's terminal facts, read from its own log (§6).

        No marker: §7.2's claim is `exit.py`'s to parse from the reserved
        channel with the node's declared outcome set, and a profile reporting a
        second one meant guessing the channel's path from `handle.log_path` —
        see `TerminalEnvelope`.
        """
        scan = self.scan_log(Path(handle.log_path))
        return TerminalEnvelope(
            usage=scan.usage,
            session_id=self._session_of(scan.session, handle.session_id),
            duration_s=elapsed_seconds(handle.started_at, self._clock.now()),
        )

    def _session_of(self, observed: str | None, assigned: str) -> str | None:
        """Reconcile the session the STREAM named with the one §5.2 assigned.

        They must agree wherever both exist: claude's is pre-assigned and echoed
        back, so a difference means the CLI ignored `--session-id` and the
        wrapper's recorded handle now names a session nobody can resume. Codex
        and opencode assign their own, so `assigned` is empty and the stream is
        the only source (§5.2 deviation, `CodexProfile.prepare`).

        The observed id still wins: it is the session that actually exists, and
        a resume hint naming a session the vendor never created helps nobody.
        The disagreement is LOGGED rather than swallowed, which it used to be —
        `scan.session or handle.session_id` never compared them at all.
        """
        if observed and assigned and observed != assigned:
            _LOG.warning(
                "wf.profile.session_mismatch",
                runner=self.runner.value,
                assigned=assigned,
                observed=observed,
            )
        return observed or assigned or None

    # -- stream parsing ---------------------------------------------------

    def decode_event(self, payload: Mapping[str, object]) -> RunnerEvent | None:
        """Map one vendor event object onto the normalized §6 event."""
        raise NotImplementedError  # pragma: no cover - vendor subclasses override

    def parse_output(self, stream: Iterable[str]) -> Iterator[RunnerEvent]:
        """Normalize the runner's machine event stream (§6), never raising."""
        return parse_lines(stream, self.decode_event, self.runner.value)

    def scan_log(self, log_path: Path) -> LogScan:
        """One pass over a runner log: the session it names and what it spent.

        The session is the FIRST one any event carries — the id of the session
        this exec belongs to (§5.2) — which for codex and opencode is the only
        place it exists at all.
        """
        try:
            with log_path.open(encoding=ENCODING, errors=DECODE_ERRORS) as handle:
                session: str | None = None
                events: list[RunnerEvent] = []
                for event in self.parse_output(handle):
                    if session is None and event.session:
                        session = event.session
                    events.append(event)
        except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
            return LogScan()
        except OSError as error:
            _LOG.warning(
                "wf.profile.log_unreadable", path=str(log_path), error=str(error)
            )
            return LogScan()
        return LogScan(session=session, usage=fold_usage(events))
