"""Admission-pinned repository checks and their observed execution evidence."""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import tempfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from workflow_interpreter.bridge.errors import BridgeRefusal
from workflow_interpreter.supervisor.gitio import Git


class CheckCommand(BaseModel):
    """An explicit argv, environment and finite deadline; never a shell string."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str = Field(min_length=1)
    argv: tuple[str, ...] = Field(min_length=1)
    timeout_s: float = Field(default=300, gt=0, le=3600, allow_inf_nan=False)
    environment: tuple[tuple[str, str], ...] = ()

    @model_validator(mode="after")
    def validate_environment(self) -> CheckCommand:
        """Disallow ambiguous environment values and malformed argv."""
        keys = [key for key, _ in self.environment]
        if len(set(keys)) != len(keys) or any(
            not key or "=" in key or "\0" in key for key in keys
        ):
            raise ValueError("invalid check environment")
        if any("\0" in value for _, value in self.environment):
            raise ValueError("invalid check environment")
        if not self.argv[0] or any("\0" in arg for arg in self.argv):
            raise ValueError("invalid check argv")
        return self


class PinnedCheck(BaseModel):
    """The executable bytes admitted for one declared command."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    command: CheckCommand
    executable_digest: str = Field(pattern=r"^[0-9a-f]{64}$")


class VerificationPolicy(BaseModel):
    """A complete ordered nonempty policy carried by the stage journal."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    checks: tuple[PinnedCheck, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_checks(self) -> VerificationPolicy:
        """One declared name identifies exactly one observed result."""
        names = [check.command.name for check in self.checks]
        if len(names) != len(set(names)):
            raise ValueError("duplicate verification check")
        return self

    @classmethod
    def pin(cls, commands: tuple[CheckCommand, ...], repo: Path) -> VerificationPolicy:
        """Resolve policy before any admission write or root creation."""
        if not commands:
            raise BridgeRefusal(
                "bridge verification policy must be nonempty; configure [[bridge_checks]] using config/foreman.example.toml and docs/usage/phase-bridge.md"
            )
        checks = []
        for command in commands:
            program = _program(repo, command.argv[0])
            checks.append(
                PinnedCheck(
                    command=command,
                    executable_digest=hashlib.sha256(program.read_bytes()).hexdigest(),
                )
            )
        return cls(checks=tuple(checks))

    @property
    def digest(self) -> str:
        """Stable identity includes argv, environment, timeout and program bytes."""
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()

    def matches(self, results: tuple[CheckResult, ...]) -> bool:
        """Require every observed success exactly once and in policy order."""
        return len(results) == len(self.checks) and all(
            result.name == check.command.name
            and result.command == check.command
            and result.executable_digest == check.executable_digest
            and result.exit_code == 0
            and not result.timed_out
            and result.source_unchanged
            for check, result in zip(self.checks, results, strict=True)
        )


class CheckResult(BaseModel):
    """Observed execution status and provenance, bound to an admitted command."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    name: str
    command: CheckCommand
    executable_digest: str
    exit_code: int
    timed_out: bool = False
    source_unchanged: bool


def _program(checkout: Path, argv0: str) -> Path:
    """Resolve relative programs within the candidate; absolute tools are explicit."""
    path = Path(argv0)
    resolved = (checkout / path).resolve()
    if not path.is_absolute() and not resolved.is_relative_to(checkout.resolve()):
        raise BridgeRefusal("verification executable escapes candidate")
    if not resolved.is_file():
        raise BridgeRefusal("verification executable missing")
    return resolved


def _source_digest(git: Git, checkout: Path, tree: str) -> str:
    """Read tracked source bytes directly, including assume-unchanged paths."""
    digest = hashlib.sha256()
    for name in git.tree_entries(tree, cwd=checkout):
        path = checkout / name
        digest.update(name.encode())
        if path.is_symlink():
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(path.read_bytes())
            digest.update(str(path.stat().st_mode).encode())
        elif path.is_dir():
            digest.update(b"directory")
        else:
            digest.update(b"missing")
    return digest.hexdigest()


def observe_checks(
    policy: VerificationPolicy, git: Git, checkout: Path, artifact_oid: str, tree: str
) -> tuple[CheckResult, ...]:
    """Execute fixed argv through the hashed descriptor, with bounded process lifetime."""
    baseline = _source_digest(git, checkout, tree)
    results = []
    for check in policy.checks:
        code, timed_out, observed_digest = 126, False, ""
        try:
            program = _program(checkout, check.command.argv[0])
            with program.open("rb") as executable:
                observed_digest = hashlib.file_digest(executable, "sha256").hexdigest()
                if observed_digest == check.executable_digest:
                    with tempfile.TemporaryDirectory(prefix="bridge-check-") as home:
                        env = {
                            "PATH": "/usr/bin:/bin",
                            "HOME": home,
                            "TMPDIR": home,
                            "LANG": "C.UTF-8",
                            **dict(check.command.environment),
                        }
                        process = subprocess.Popen(
                            (
                                f"/proc/self/fd/{executable.fileno()}",
                                *check.command.argv[1:],
                            ),
                            cwd=checkout,
                            env=env,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            pass_fds=(executable.fileno(),),
                            start_new_session=True,
                        )
                        try:
                            code = process.wait(timeout=check.command.timeout_s)
                        except subprocess.TimeoutExpired:
                            timed_out, code = True, 124
                        finally:
                            # Also terminate children left behind by a successful parent.
                            try:
                                os.killpg(process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass
                            process.wait()
        except (OSError, BridgeRefusal):
            code = 126
        unchanged = (
            git.head_commit(cwd=checkout) == artifact_oid
            and not git.status_paths(cwd=checkout)
            and _source_digest(git, checkout, tree) == baseline
        )
        results.append(
            CheckResult(
                name=check.command.name,
                command=check.command,
                executable_digest=observed_digest,
                exit_code=code,
                timed_out=timed_out,
                source_unchanged=unchanged,
            )
        )
        if not unchanged:
            break
    return tuple(results)
