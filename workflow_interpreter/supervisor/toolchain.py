"""Prepare pinned offline activation tools without executing candidate build hooks."""

import fcntl
import hashlib
import shutil
import subprocess
import tempfile
import time
import tomllib
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Final

from pydantic import BaseModel

from workflow_interpreter.supervisor import toolchain_constants as tc
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.gitcmd import GitSubcommand
from workflow_interpreter.supervisor.gitio import Git
from workflow_interpreter.supervisor.paths import (
    LEDGER_FILE,
    fsync_dir,
    read_record,
    write_record,
)
from workflow_interpreter.supervisor.toolchain_files import (
    copy_tree,
    import_wheels,
    measure,
    read_regular,
    relocate_links,
    sync_tree,
)
from workflow_interpreter.supervisor.toolchain_models import (
    MODEL,
    CopyMethod,
    SeedPreparation,
    SeedReceipt,
    ToolchainUnavailable,
)

PIN_LIMIT: Final[int] = 8 * 1024 * 1024
SYNC: Final[tuple[str, ...]] = (
    "sync",
    "--locked",
    "--no-install-project",
    "--no-install-workspace",
    "--no-install-local",
    "--no-build",
    "--no-python-downloads",
    "--link-mode=copy",
)


class ProjectPins(BaseModel):
    """Admitted metadata copied into host-owned preparation directories."""

    model_config = MODEL
    project: str
    lock: bytes
    pyproject: bytes
    python: bytes | None = None

    def write(self, directory: Path) -> None:
        """Materialize only admitted metadata, never candidate project code."""
        directory.mkdir(parents=True, exist_ok=True)
        (directory / tc.LOCK_FILE).write_bytes(self.lock)
        (directory / tc.PROJECT_FILE).write_bytes(self.pyproject)
        if self.python is not None:
            (directory / tc.PYTHON_FILE).write_bytes(self.python)


def digest(value: bytes) -> str:
    """Use content identity rather than mtime for reusable seeds."""
    return hashlib.sha256(value).hexdigest()


class ToolchainSeeder:
    """Prepare offline tools before the supervisor releases the vendor process."""

    def __init__(self, config: SupervisorConfig, env: Mapping[str, str]) -> None:
        """Keep host authority separate from activation-supplied environment."""
        self._supervisor = config
        self._config = config.toolchain
        self._env = {
            key: value
            for key, value in env.items()
            if key in ("PATH", "HOME", "LANG", "LC_ALL", "SSL_CERT_FILE")
        }

    def prepare(
        self, checkout: Path, base: str | None, activation_dir: Path
    ) -> SeedPreparation:
        """Publish complete private copies; preparation errors never launch a vendor."""
        try:
            return self._prepare(checkout, base, activation_dir)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            raise ToolchainUnavailable(tc.MSG_PREPARATION.format(error=exc)) from exc

    def _prepare(
        self, checkout: Path, base: str | None, activation: Path
    ) -> SeedPreparation:
        """Serialize private publication and keep launched caches out of host probes."""
        if activation.is_symlink() or activation.resolve() != activation:
            raise ToolchainUnavailable(tc.MSG_ACTIVATION_LINK)
        if not activation.is_relative_to(self._supervisor.wrapper_root):
            raise ToolchainUnavailable(tc.MSG_OUTSIDE_WRAPPER)
        activation.mkdir(parents=True, exist_ok=True)
        with self._lock(activation / "toolchain.lock"):
            # The dispatcher checks receipts first. This guard also protects direct use.
            if (activation / LEDGER_FILE).exists():
                raise ToolchainUnavailable(tc.MSG_TAINTED)
            for interrupted in activation.glob(".toolchain-*"):
                if interrupted.is_symlink():
                    raise ToolchainUnavailable(tc.MSG_INTERRUPTED_LINK)
                shutil.rmtree(interrupted)
            private_path = activation / tc.TOOLCHAIN / tc.CACHE
            if private_path.resolve() != private_path:
                raise ToolchainUnavailable(tc.MSG_PRIVATE_LINK)
            if base is None:
                if any(
                    (checkout / project / tc.LOCK_FILE).exists()
                    for project in self._config.projects
                ):
                    raise ToolchainUnavailable(tc.MSG_NO_BASE)
                cache = activation / tc.TOOLCHAIN / tc.CACHE
                cache.mkdir(parents=True, exist_ok=True)
                return SeedPreparation(cache=cache)
            pins = tuple(
                pin
                for project in self._config.projects
                if (pin := self._pins(checkout, base, project)) is not None
            )
            cache = activation / tc.TOOLCHAIN / tc.CACHE
            if not pins:
                cache.mkdir(parents=True, exist_ok=True)
                return SeedPreparation(cache=cache)
            host = self._host_path(self._config.host_cache, ("cache", "dir"))
            python = self._host_path(self._config.python_root, (tc.PYTHON, "dir"))
            seeds = (
                self._config.seed_root
                or self._supervisor.wrapper_root / tc.SEED_DIRECTORY
            )
            roots = (seeds, host, python)
            for source in roots:
                for destination in (checkout, activation, self._supervisor.repo_root):
                    if source.is_relative_to(destination) or destination.is_relative_to(
                        source
                    ):
                        raise ToolchainUnavailable(tc.MSG_OVERLAP)
                if source.resolve() != source:
                    raise ToolchainUnavailable(tc.MSG_SOURCE_LINK)
            for left, right in ((seeds, host), (seeds, python), (host, python)):
                if left.is_relative_to(right) or right.is_relative_to(left):
                    raise ToolchainUnavailable(tc.MSG_HOST_OVERLAP)
            seeds.mkdir(parents=True, exist_ok=True)
            host.mkdir(parents=True, exist_ok=True)
            version = self._run(("--version",), seeds, self._env)
            prepared = read_record(activation / tc.PREPARED, SeedPreparation)
            expected = tuple(digest(pin.lock) for pin in pins)
            if (
                prepared is not None
                and tuple(r.lock_digest for r in prepared.receipts) == expected
            ):
                if tuple(
                    (r.project_digest, r.python_digest) for r in prepared.receipts
                ) != tuple(
                    (digest(pin.pyproject), digest(pin.python) if pin.python else None)
                    for pin in pins
                ):
                    raise ToolchainUnavailable(tc.MSG_PRIVATE_PINS)
                if prepared.protected_roots != roots:
                    raise ToolchainUnavailable(tc.MSG_RECEIPT_PATH)
                if prepared.cache != cache:
                    raise ToolchainUnavailable(tc.MSG_RECEIPT_PATH)
                for pin in pins:
                    self._probe(pin, cache, activation, python=None)
                return prepared
            if cache.parent.is_symlink():
                raise ToolchainUnavailable(tc.MSG_PRIVATE_ROOT_LINK)
            stage = Path(tempfile.mkdtemp(prefix=tc.STAGING_PREFIX, dir=activation))
            try:
                private = stage / tc.CACHE
                private.mkdir()
                receipts: list[SeedReceipt] = []
                for pin in pins:
                    interpreter = self._interpreter(pin, python, seeds)
                    seed, receipt = self._seed(pin, seeds, host, interpreter, version)
                    total_bytes = sum(
                        measure(path, self._config)
                        for path in (
                            seed / tc.CACHE,
                            interpreter,
                            private,
                        )
                    )
                    if total_bytes > self._config.max_bytes:
                        raise ToolchainUnavailable(tc.MSG_BOUNDS)
                    method = copy_tree(seed / tc.CACHE, private, self._config)
                    python_method = copy_tree(
                        interpreter,
                        private / tc.PYTHON / interpreter.name,
                        self._config,
                    )
                    probe = self._probe(
                        pin, private, activation, python=interpreter.name
                    )
                    receipts.append(
                        receipt.model_copy(
                            update={
                                "copy_method": (
                                    CopyMethod.PLAIN
                                    if python_method is CopyMethod.PLAIN
                                    else method
                                ),
                                "copied_bytes": measure(private, self._config),
                                "offline_probe": probe,
                                "interpreter_version": interpreter.name,
                                "uv_version": version,
                            }
                        )
                    )
                sync_tree(stage)
                if cache.parent.exists():
                    shutil.rmtree(cache.parent)
                stage.rename(cache.parent)
                fsync_dir(activation)
                result = SeedPreparation(
                    cache=cache, protected_roots=roots, receipts=tuple(receipts)
                )
                write_record(activation / tc.PREPARED, result)
                return result
            finally:
                if stage.exists():
                    shutil.rmtree(stage)

    def _pins(self, checkout: Path, base: str, project: str) -> ProjectPins | None:
        """Compare dependency inputs with regular-file blobs at admitted base."""
        git = Git(self._supervisor)
        values: dict[str, bytes | None] = {}
        for name in (tc.LOCK_FILE, tc.PROJECT_FILE, tc.PYTHON_FILE):
            relative = (Path(project) / name).as_posix()
            listing = git.run(
                GitSubcommand.LS_TREE,
                base,
                "--",
                relative,
                cwd=self._supervisor.repo_root,
            ).text
            value = None
            if listing:
                if not listing.startswith(("100644 ", "100755 ")):
                    raise ToolchainUnavailable(tc.MSG_PIN_REGULAR.format(path=relative))
                value = git.bounded_bytes(
                    GitSubcommand.CAT_FILE,
                    "blob",
                    f"{base}:{relative}",
                    cwd=self._supervisor.repo_root,
                    limit=PIN_LIMIT,
                )
            current = checkout / relative
            if current.resolve() != current or current.is_symlink():
                raise ToolchainUnavailable(tc.MSG_PIN_LINK.format(path=relative))
            if current.exists() and current.stat().st_size > PIN_LIMIT:
                raise ToolchainUnavailable(tc.MSG_PIN_SIZE.format(path=relative))
            actual = read_regular(current, PIN_LIMIT)
            if actual != value:
                raise ToolchainUnavailable(tc.MSG_PIN_CHANGED.format(path=relative))
            values[name] = value
            if name == tc.LOCK_FILE and value is None:
                return None
        lock, project_bytes = values[tc.LOCK_FILE], values[tc.PROJECT_FILE]
        if lock is None:
            return None
        if project_bytes is None:
            raise ToolchainUnavailable(tc.MSG_NO_PROJECT)
        return ProjectPins(
            project=project,
            lock=lock,
            pyproject=project_bytes,
            python=values[tc.PYTHON_FILE],
        )

    def _host_path(self, configured: Path | None, args: tuple[str, ...]) -> Path:
        """Discover host paths through injected uv, never from candidate settings."""
        value = configured or Path(
            self._run(args, self._supervisor.repo_root, self._env)
        )
        if not value.is_absolute():
            raise ToolchainUnavailable(tc.MSG_RELATIVE_HOST)
        return value

    def _interpreter(self, pin: ProjectPins, root: Path, cwd: Path) -> Path:
        """Select a managed interpreter matching admitted Python requirements."""
        data = tomllib.loads(pin.pyproject.decode())
        project = data.get("project", {})
        request = (
            pin.python.decode().strip()
            if pin.python
            else str(project.get("requires-python", ""))
        )
        args: tuple[str, ...] = (
            tc.PYTHON,
            "find",
            "--no-project",
            "--managed-python",
            "--no-python-downloads",
        )
        if request:
            args += (request,)
        executable = Path(
            self._run(
                args,
                cwd,
                {**self._env, tc.ENV_PYTHON: str(root), tc.ENV_OFFLINE: "1"},
            )
        )
        if not executable.resolve().is_relative_to(root):
            raise ToolchainUnavailable(tc.MSG_UNMANAGED)
        relative = executable.relative_to(root)
        selected = root / relative.parts[0]
        measure(selected, self._config)
        return selected

    def _seed(
        self, pin: ProjectPins, seeds: Path, host: Path, interpreter: Path, version: str
    ) -> tuple[Path, SeedReceipt]:
        """Build once under a seed-key lock, then atomically publish a complete seed."""
        key = (
            digest(
                str(self._supervisor.repo_root).encode() + b"\0" + pin.project.encode()
            )[:16]
            + "-"
            + digest(pin.lock)
        )
        seed = seeds / key
        with self._lock(seeds / (key + ".lock")):
            if seed.resolve() != seed:
                raise ToolchainUnavailable(tc.MSG_SEED_LINK)
            existing = read_record(seed / tc.MANIFEST, SeedReceipt)
            if existing is not None:
                if existing.project_digest != digest(
                    pin.pyproject
                ) or existing.python_digest != (
                    digest(pin.python) if pin.python else None
                ):
                    raise ToolchainUnavailable(tc.MSG_SEED_PINS)
                return seed, existing
            for interrupted in seeds.glob(f".{key}-*"):
                if interrupted.is_symlink():
                    raise ToolchainUnavailable(tc.MSG_SEED_LINK)
                shutil.rmtree(interrupted)
            stage = Path(tempfile.mkdtemp(prefix=f".{key}-", dir=seeds))
            try:
                cache = stage / tc.CACHE
                cache.mkdir()
                data = tomllib.loads(pin.lock.decode())
                packages = tuple(
                    (str(p["name"]).replace("_", "-"), str(p["version"]))
                    for p in data.get("package", [])
                    if "version" in p
                )
                import_wheels(host, cache, packages, self._config)
                project = stage / "project"
                pin.write(project)
                env = self._uv_env(cache, stage / "venv", interpreter.parent)
                sync_args = (*SYNC, "--python", str(interpreter / "bin" / "python3"))
                fetched = False
                try:
                    self._run(sync_args, project, env)
                except ToolchainUnavailable as exc:
                    if not self._config.allow_host_fetch or not any(
                        message in str(exc).lower()
                        for message in (
                            "not found in cache",
                            "not available in the cache",
                            "network connectivity is disabled",
                        )
                    ):
                        raise
                    self._run(sync_args, project, {**env, tc.ENV_OFFLINE: "0"})
                    fetched = True
                relocate_links(cache, self._config)
                shutil.rmtree(stage / "venv", ignore_errors=True)
                shutil.rmtree(project)
                receipt = SeedReceipt(
                    project=pin.project,
                    seed_key=key,
                    lock_digest=digest(pin.lock),
                    project_digest=digest(pin.pyproject),
                    python_digest=digest(pin.python) if pin.python else None,
                    interpreter_version=interpreter.name,
                    uv_version=version,
                    copied_bytes=measure(cache, self._config),
                    copy_method=CopyMethod.AUTO,
                    offline_probe="pending private probe",
                    host_fetch=fetched,
                )
                write_record(stage / tc.MANIFEST, receipt)
                sync_tree(stage)
                if seed.exists():
                    shutil.rmtree(seed)
                stage.rename(seed)
                fsync_dir(seeds)
                return seed, receipt
            finally:
                if stage.exists():
                    shutil.rmtree(stage)

    def _probe(
        self, pin: ProjectPins, cache: Path, activation: Path, python: str | None
    ) -> str:
        """Probe only prelaunch tools, using admitted metadata and a scratch venv."""
        with tempfile.TemporaryDirectory(
            prefix=tc.PROBE_PREFIX, dir=cache.parent
        ) as directory:
            project = Path(directory)
            pin.write(project)
            env = self._uv_env(cache, project / "venv", cache / tc.PYTHON)
            args = SYNC
            if python is not None:
                args += (
                    "--python",
                    str(cache / tc.PYTHON / python / "bin" / "python3"),
                )
            self._run(args, project, env)
            relocate_links(cache, self._config)
            return self._run(
                ("run", "--frozen", "ruff", "--version"),
                project,
                {**env, tc.ENV_NO_SYNC: "1"},
            )

    def _uv_env(self, cache: Path, venv: Path, python: Path) -> dict[str, str]:
        """Force copy installation and offline resolution in isolated environments."""
        return {
            **self._env,
            tc.ENV_CACHE: str(cache),
            tc.ENV_VENV: str(venv),
            tc.ENV_PYTHON: str(python),
            tc.ENV_OFFLINE: "1",
            tc.ENV_DOWNLOADS: "never",
            tc.ENV_LINK_MODE: "copy",
            tc.ENV_NO_CONFIG: "1",
        }

    def _run(self, args: tuple[str, ...], cwd: Path, env: Mapping[str, str]) -> str:
        """Run one bounded host operation before any vendor has launched."""
        from workflow_interpreter.supervisor.toolchain_process import run_uv

        return run_uv(self._config, args, cwd, env)

    @contextmanager
    def _lock(self, path: Path) -> Iterator[None]:
        """Serialize publication with a bounded wait, including across processes."""
        with path.open("a") as stream:
            deadline = time.monotonic() + self._config.timeout_s
            while True:
                try:
                    fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise ToolchainUnavailable(tc.MSG_LOCK_TIMEOUT) from None
                    time.sleep(0.01)
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)
