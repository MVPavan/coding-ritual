"""Private toolchains cannot form a write channel between activations."""

import json
import os
from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict

from tests._supervisor import _git as git_run
from workflow_interpreter.supervisor.config import SupervisorConfig
from workflow_interpreter.supervisor.profile import RunnerChannels, TaskSpec
from workflow_interpreter.supervisor.sandbox import plan_for
from workflow_interpreter.supervisor.toolchain import ToolchainSeeder
from workflow_interpreter.supervisor.toolchain_models import (
    ToolchainConfig,
    ToolchainUnavailable,
)


def test_two_reviewers_never_share_a_writable_toolchain(tmp_path: Path) -> None:
    """Two activation plans grant distinct caches outside their checkout."""
    repo = tmp_path / "repo"
    wrapper = tmp_path / "wrapper"
    repo.mkdir()
    wrapper.mkdir()
    caches: list[Path] = []
    for activation in ("first", "second"):
        channels = wrapper / activation / "channels"
        channels.mkdir(parents=True)
        task = TaskSpec(
            root_id="root",
            activation_id=activation,
            node="review",
            model="test-model",
            writes=False,
            cwd=str(repo),
            channels=RunnerChannels(
                outcome_file=str(channels / "outcome.json"),
                artifact_dir=str(channels / "artifacts"),
                effects_file=str(channels / "effects.json"),
                log_path=str(channels.parent / "run.jsonl"),
            ),
        )
        plan = plan_for(
            task, repo_root=repo, wrapper_root=wrapper, channels_dir=channels
        )
        caches.append(plan.toolchain_cache[0])
        assert not plan.grants
        assert not plan.git_rw
        assert not plan.toolchain_cache[0].is_relative_to(repo)
    assert caches[0] != caches[1]


class SeedLab(BaseModel):
    """Pinned project, host artifacts, and a recording uv process fixture."""

    # The process-local seeder is never serialized by this fixture model.
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    seeder: ToolchainSeeder
    repo: Path
    base: str
    host: Path
    interpreter: Path
    calls: Path
    config: SupervisorConfig


@pytest.fixture
def seed_lab(tmp_path: Path) -> SeedLab:
    """Build a trusted miniature host cache without external network access."""
    repo = tmp_path / "project"
    repo.mkdir()
    (repo / "uv.lock").write_text(
        'version = 1\n[[package]]\nname = "ruff"\nversion = "1.0"\n'
        '[package.source]\nregistry = "https://pypi.org/simple"\n'
    )
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "example"\nversion = "1.0"\nrequires-python = ">=3.13"\n'
    )
    git_run(repo, "init", "-q")
    git_run(repo, "add", "uv.lock", "pyproject.toml")
    git_run(
        repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.test",
        "commit",
        "-qm",
        "fixture",
    )
    base = git_run(repo, "rev-parse", "HEAD").strip()
    host = tmp_path / "host-cache"
    wheel = host / "wheels-v5" / "pypi" / "ruff"
    wheel.mkdir(parents=True)
    archive = host / "archive-v0" / "locked-wheel"
    archive.mkdir(parents=True)
    (archive / "ruff.py").write_text("trusted wheel")
    (wheel / "1.0-py3-none-any").symlink_to(archive)
    (host / "unrelated-large-file").write_text("must not be copied")
    python_home = tmp_path / "python"
    interpreter = python_home / "cpython-3.13.9-linux" / "bin" / "python3"
    interpreter.parent.mkdir(parents=True)
    interpreter.write_text("trusted interpreter")
    calls = tmp_path / "uv-calls.jsonl"
    uv = tmp_path / "fake-uv"
    uv.write_text(
        "#!/usr/bin/env python3\n"
        "import json, os, pathlib, sys\n"
        f"calls = pathlib.Path({str(calls)!r})\n"
        "args = sys.argv[1:]\n"
        'with calls.open("a") as f:\n'
        ' f.write(json.dumps([args, os.environ.get("UV_OFFLINE")]) + "\\n")\n'
        'if args == ["--version"]: print("uv fixture")\n'
        f'elif args[:2] == ["python", "find"]: print({str(interpreter)!r})\n'
        'elif args[:1] == ["sync"]:\n'
        ' assert "--locked" in args and "--no-build" in args\n'
        ' assert "--no-install-project" in args\n'
        ' cache = pathlib.Path(os.environ["UV_CACHE_DIR"])\n'
        ' assert (cache / "wheels-v5/pypi/ruff/1.0-py3-none-any/ruff.py").exists()\n'
        'elif args[:1] == ["run"]: print("ruff 1.0")\n'
        "else: sys.exit(2)\n"
    )
    uv.chmod(0o755)
    config = ToolchainConfig(
        seed_root=tmp_path / "seeds",
        host_cache=host,
        python_root=python_home,
        uv_binary=str(uv),
    )
    supervisor = SupervisorConfig(
        repo_root=repo, wrapper_root=tmp_path / "wrapper", host="test", toolchain=config
    )
    seeder = ToolchainSeeder(supervisor, {"PATH": os.environ["PATH"]})
    return SeedLab(
        seeder=seeder,
        repo=repo,
        base=base,
        host=host,
        interpreter=interpreter,
        calls=calls,
        config=supervisor,
    )


def test_seed_is_built_once_and_private_copies_are_independent(
    tmp_path: Path,
    seed_lab: SeedLab,
) -> None:
    """Warm host wheels seed only the lock's packages, then reuse the project seed."""
    seeder, repo, base = seed_lab.seeder, seed_lab.repo, seed_lab.base
    host, calls, supervisor = seed_lab.host, seed_lab.calls, seed_lab.config
    config = supervisor.toolchain
    archive = host / "archive-v0" / "locked-wheel"
    first = seeder.prepare(repo, base, tmp_path / "wrapper" / "first")
    second = seeder.prepare(repo, base, tmp_path / "wrapper" / "second")
    assert len(first.receipts) == 1
    assert first.receipts[0].lock_digest == second.receipts[0].lock_digest
    assert first.receipts[0].interpreter_version == "cpython-3.13.9-linux"
    assert first.receipts[0].copied_bytes > 0
    assert not first.receipts[0].host_fetch
    seed_cache = config.seed_root / first.receipts[0].seed_key / "uv-cache"
    assert not (seed_cache / "unrelated-large-file").exists()
    first_file = first.cache / "archive-v0" / "locked-wheel" / "ruff.py"
    second_file = second.cache / "archive-v0" / "locked-wheel" / "ruff.py"
    assert (
        len(
            {
                first_file.stat().st_ino,
                second_file.stat().st_ino,
                (archive / "ruff.py").stat().st_ino,
            }
        )
        == 3
    )
    first_file.write_text("poisoned")
    assert second_file.read_text() == "trusted wheel"
    assert (archive / "ruff.py").read_text() == "trusted wheel"
    assert (
        seed_cache / "archive-v0/locked-wheel/ruff.py"
    ).read_text() == "trusted wheel"
    events = [json.loads(line) for line in calls.read_text().splitlines()]
    # One seed sync plus a private-environment sync per activation, all offline.
    assert sum(event[0][0] == "sync" for event in events) == 3
    assert all(event[1] == "1" for event in events if event[0][0] in ("sync", "run"))


@pytest.mark.parametrize("kind", ["escape", "bytes", "disk"])
def test_unsafe_copy_is_refused_before_copy(tmp_path: Path, kind: str) -> None:
    """Escaping links and exhausted copy budgets never become writable grants."""
    from workflow_interpreter.supervisor.toolchain_files import copy_tree
    from workflow_interpreter.supervisor.toolchain_models import (
        ToolchainConfig,
        ToolchainUnavailable,
    )

    source = tmp_path / "source"
    source.mkdir()
    (source / "file").write_text("payload")
    config = ToolchainConfig()
    if kind == "escape":
        (source / "escape").symlink_to(tmp_path / "elsewhere")
    elif kind == "bytes":
        config = config.model_copy(update={"max_bytes": 1})
    else:
        config = config.model_copy(update={"reserve_bytes": 2**63})
    with pytest.raises(ToolchainUnavailable):
        copy_tree(source, tmp_path / "destination", config)
    assert (source / "file").read_text() == "payload"


def test_receipts_predating_seeding_still_load(tmp_path: Path) -> None:
    """Optional seed provenance preserves existing fork-barrier receipts."""
    from workflow_interpreter.supervisor.models import LaunchReceipt

    assert LaunchReceipt.model_fields["seed_receipts"].default == ()


@pytest.mark.parametrize("pin", ["uv.lock", "pyproject.toml", ".python-version"])
def test_changed_dependency_pins_never_invoke_uv(seed_lab: SeedLab, pin: str) -> None:
    """Candidate dependencies are refused before host preparation."""
    (seed_lab.repo / pin).write_text("candidate dependency input")
    with pytest.raises(ToolchainUnavailable, match="dependency pin changed"):
        seed_lab.seeder.prepare(
            seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "activation"
        )
    assert not seed_lab.calls.exists()


def test_launched_cache_is_never_probed_on_host(seed_lab: SeedLab) -> None:
    """A crashed runner's cache remains untrusted even if its receipt survived."""
    activation = seed_lab.config.wrapper_root / "activation"
    seeded = seed_lab.seeder.prepare(seed_lab.repo, seed_lab.base, activation)
    (activation / "exec.ledger").write_text("launched")
    before = seed_lab.calls.read_bytes()
    with pytest.raises(ToolchainUnavailable, match="launched private cache"):
        seed_lab.seeder.prepare(seed_lab.repo, seed_lab.base, activation)
    assert seed_lab.calls.read_bytes() == before
    assert seeded.cache.exists()


def test_prelaunch_copy_is_reused_only_after_offline_probe(seed_lab: SeedLab) -> None:
    """An interrupted prelaunch retry reuses intact inodes and probes offline."""
    activation = seed_lab.config.wrapper_root / "activation"
    first = seed_lab.seeder.prepare(seed_lab.repo, seed_lab.base, activation)
    inode = (first.cache / "archive-v0/locked-wheel/ruff.py").stat().st_ino
    before = len(seed_lab.calls.read_text().splitlines())
    second = seed_lab.seeder.prepare(seed_lab.repo, seed_lab.base, activation)
    assert second == first
    assert (second.cache / "archive-v0/locked-wheel/ruff.py").stat().st_ino == inode
    events = [
        json.loads(line) for line in seed_lab.calls.read_text().splitlines()[before:]
    ]
    assert any(
        args[:2] == ["run", "--frozen"] and offline == "1" for args, offline in events
    )


def test_missing_host_wheel_fetches_into_seed_once(seed_lab: SeedLab) -> None:
    """Only a host seed miss may fetch; another cold activation reuses that seed."""
    import shutil

    shutil.rmtree(seed_lab.host / "wheels-v5")
    uv = Path(seed_lab.config.toolchain.uv_binary)
    script = uv.read_text().replace(
        ' assert (cache / "wheels-v5/pypi/ruff/1.0-py3-none-any/ruff.py").exists()',
        ' wheel = cache / "wheels-v5/pypi/ruff/1.0-py3-none-any/ruff.py"\n'
        " if not wheel.exists():\n"
        '  if os.environ.get("UV_OFFLINE") == "1": '
        'print("not found in cache"); sys.exit(1)\n'
        '  wheel.parent.mkdir(parents=True); wheel.write_text("downloaded")',
    )
    uv.write_text(script)
    for name in ("first", "second"):
        result = seed_lab.seeder.prepare(
            seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / name
        )
        assert result.receipts[0].host_fetch
    events = [json.loads(line) for line in seed_lab.calls.read_text().splitlines()]
    assert sum(args[0] == "sync" and offline == "0" for args, offline in events) == 1


def test_copy_falls_back_to_plain_without_shared_inodes(tmp_path: Path) -> None:
    """A copier rejecting reflink-auto gets one ordinary-copy attempt."""
    from workflow_interpreter.supervisor.toolchain_files import copy_tree
    from workflow_interpreter.supervisor.toolchain_models import CopyMethod

    source = tmp_path / "source"
    source.mkdir()
    (source / "file").write_text("payload")
    copier = tmp_path / "cp-fixture"
    copier.write_text(
        '#!/bin/sh\ncase "$*" in *--reflink=auto*) exit 1;; esac\nexec cp "$@"\n'
    )
    copier.chmod(0o755)
    target = tmp_path / "target"
    method = copy_tree(source, target, ToolchainConfig(copy_binary=str(copier)))
    assert method is CopyMethod.PLAIN
    assert (target / "file").read_bytes() == (source / "file").read_bytes()
    assert (target / "file").stat().st_ino != (source / "file").stat().st_ino


def test_two_concurrent_activations_publish_one_seed(seed_lab: SeedLab) -> None:
    """Per-seed locking shares only the immutable seed across concurrent launches."""
    from concurrent.futures import ThreadPoolExecutor

    def prepare(name: str) -> Path:
        """Prepare one independent activation from the same admitted lock."""
        return seed_lab.seeder.prepare(
            seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / name
        ).cache

    with ThreadPoolExecutor(max_workers=2) as pool:
        paths = tuple(pool.map(prepare, ("first", "second")))
    assert paths[0] != paths[1]
    events = [json.loads(line) for line in seed_lab.calls.read_text().splitlines()]
    assert sum(args[0] == "sync" for args, _ in events) == 3


def test_lock_change_builds_a_new_seed(seed_lab: SeedLab) -> None:
    """A newly admitted lock gets a new seed without mutating the old one."""
    first = seed_lab.seeder.prepare(
        seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "first"
    )
    lock = seed_lab.repo / "uv.lock"
    lock.write_bytes(lock.read_bytes() + b"\n# newly admitted lock\n")
    git_run(seed_lab.repo, "add", "uv.lock")
    git_run(
        seed_lab.repo,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.test",
        "commit",
        "-qm",
        "new lock",
    )
    base = git_run(seed_lab.repo, "rev-parse", "HEAD")
    second = seed_lab.seeder.prepare(
        seed_lab.repo, base, seed_lab.config.wrapper_root / "second"
    )
    assert first.receipts[0].seed_key != second.receipts[0].seed_key
    assert first.cache.exists()


def test_private_cache_symlink_cannot_grant_another_activation(tmp_path: Path) -> None:
    """Planning must refuse a redirected private-cache path before creating it."""
    from workflow_interpreter.supervisor.errors import SandboxPathRefused
    from workflow_interpreter.supervisor.sandbox import toolchain_cache_for

    activation = tmp_path / "activation"
    activation.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    (activation / "toolchain").symlink_to(other, target_is_directory=True)
    with pytest.raises(SandboxPathRefused):
        toolchain_cache_for(activation)
    assert not (other / "uv-cache").exists()


def test_interrupted_private_copy_is_replaced_and_cleaned(seed_lab: SeedLab) -> None:
    """Unpublished staging files are not evidence and cannot become a seed."""
    activation = seed_lab.config.wrapper_root / "activation"
    partial = activation / ".toolchain-interrupted" / "uv-cache"
    partial.mkdir(parents=True)
    (partial / "poison").write_text("partial")
    result = seed_lab.seeder.prepare(seed_lab.repo, seed_lab.base, activation)
    assert not (result.cache / "poison").exists()
    assert not partial.parent.exists()


def test_no_project_does_not_discover_uv(seed_lab: SeedLab) -> None:
    """A graph declaring no uv project needs no host toolchain dependency."""
    config = seed_lab.config.model_copy(
        update={
            "toolchain": seed_lab.config.toolchain.model_copy(update={"projects": ()}),
        }
    )
    result = ToolchainSeeder(config, {}).prepare(
        seed_lab.repo, seed_lab.base, config.wrapper_root / "activation"
    )
    assert result.receipts == ()
    assert not seed_lab.calls.exists()


def test_host_fetch_can_be_disabled_for_offline_supervisors(seed_lab: SeedLab) -> None:
    """An offline host reports a missing wheel without attempting network access."""
    import shutil

    shutil.rmtree(seed_lab.host / "wheels-v5")
    uv = Path(seed_lab.config.toolchain.uv_binary)
    uv.write_text(
        uv.read_text().replace(
            ' assert (cache / "wheels-v5/pypi/ruff/1.0-py3-none-any/ruff.py").exists()',
            ' print("not found in cache"); sys.exit(1)',
        )
    )
    config = seed_lab.config.model_copy(
        update={
            "toolchain": ToolchainConfig(
                **{**seed_lab.config.toolchain.model_dump(), "allow_host_fetch": False},
            )
        }
    )
    with pytest.raises(ToolchainUnavailable, match="not found in cache"):
        ToolchainSeeder(config, {"PATH": os.environ["PATH"]}).prepare(
            seed_lab.repo,
            seed_lab.base,
            config.wrapper_root / "activation",
        )
    events = [json.loads(line) for line in seed_lab.calls.read_text().splitlines()]
    assert all(offline == "1" for args, offline in events if args[0] == "sync")


def test_timeout_never_publishes_private_toolchain(seed_lab: SeedLab) -> None:
    """A timed-out host command leaves no complete private cache or provenance."""
    uv = Path(seed_lab.config.toolchain.uv_binary)
    uv.write_text("#!/bin/sh\nexec sleep 2\n")
    config = seed_lab.config.model_copy(
        update={
            "toolchain": seed_lab.config.toolchain.model_copy(
                update={"timeout_s": 0.02}
            )
        }
    )
    activation = config.wrapper_root / "activation"
    with pytest.raises(ToolchainUnavailable, match="timed out"):
        ToolchainSeeder(config, {"PATH": os.environ["PATH"]}).prepare(
            seed_lab.repo,
            seed_lab.base,
            activation,
        )
    assert not (activation / "toolchain-seed.json").exists()
    assert not (activation / "toolchain").exists()


@pytest.mark.parametrize("location", ["seed", "host", "python"])
def test_overlapping_sources_refuse_before_uv(seed_lab: SeedLab, location: str) -> None:
    """A host cache inside the checkout cannot be reopened as a private grant."""
    field = {"seed": "seed_root", "host": "host_cache", "python": "python_root"}[
        location
    ]
    toolchain = seed_lab.config.toolchain.model_copy(
        update={field: seed_lab.repo / location}
    )
    config = seed_lab.config.model_copy(update={"toolchain": toolchain})
    with pytest.raises(ToolchainUnavailable, match="overlapping"):
        ToolchainSeeder(config, {"PATH": os.environ["PATH"]}).prepare(
            seed_lab.repo,
            seed_lab.base,
            config.wrapper_root / "activation",
        )
    assert not seed_lab.calls.exists()


def test_only_selected_interpreter_is_copied(seed_lab: SeedLab) -> None:
    """Other managed installations are not part of an activation's seed."""
    root = seed_lab.interpreter.parent.parent.parent
    other = root / "cpython-other"
    other.mkdir()
    (other / "large-unrelated-file").write_text("unrelated")
    result = seed_lab.seeder.prepare(
        seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "activation"
    )
    assert not (result.cache / "python" / other.name).exists()
    selected = (
        result.cache
        / "python"
        / seed_lab.interpreter.parent.parent.name
        / "bin/python3"
    )
    assert selected.read_bytes() == seed_lab.interpreter.read_bytes()
    assert selected.stat().st_ino != seed_lab.interpreter.stat().st_ino


def test_failed_sync_does_not_publish_a_partial_seed(seed_lab: SeedLab) -> None:
    """Build refusals preserve neither a completed seed nor launch provenance."""
    uv = Path(seed_lab.config.toolchain.uv_binary)
    uv.write_text(
        uv.read_text().replace(
            ' assert (cache / "wheels-v5/pypi/ruff/1.0-py3-none-any/ruff.py").exists()',
            ' print("source builds are disabled"); sys.exit(1)',
        )
    )
    activation = seed_lab.config.wrapper_root / "activation"
    with pytest.raises(ToolchainUnavailable, match="source builds are disabled"):
        seed_lab.seeder.prepare(seed_lab.repo, seed_lab.base, activation)
    assert not (activation / "toolchain-seed.json").exists()
    assert not list(seed_lab.config.toolchain.seed_root.glob("*/seed.json"))
    events = [json.loads(line) for line in seed_lab.calls.read_text().splitlines()]
    assert all(offline == "1" for args, offline in events if args[0] == "sync")


def test_candidate_fifo_is_refused_without_reading_it(
    seed_lab: SeedLab,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A candidate-controlled FIFO must not block the host's pin comparison."""
    lock = seed_lab.repo / "uv.lock"
    lock.unlink()
    os.mkfifo(lock)
    original = Path.read_bytes

    def read(path: Path) -> bytes:
        """Fail immediately if the implementation would block on the FIFO."""
        if path == lock:
            raise AssertionError("attempted to read candidate FIFO")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", read)
    with pytest.raises(ToolchainUnavailable, match="regular file"):
        seed_lab.seeder.prepare(
            seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "activation"
        )


def test_legacy_receipt_roundtrip_has_no_seed_claim(seed_lab: SeedLab) -> None:
    """Read a legacy serialized receipt without manufacturing seeding evidence."""
    from tests._supervisor import dead_pid, handle_for
    from workflow_interpreter.supervisor.models import LaunchReceipt

    receipt = LaunchReceipt(
        launch_id="old",
        root_id="root",
        activation_id="activation",
        argv=("runner",),
        cwd=str(seed_lab.repo),
        handle=handle_for(dead_pid()),
    )
    legacy = receipt.model_dump(mode="json", exclude={"seed_receipts"})
    assert LaunchReceipt.model_validate(legacy).seed_receipts == ()


def test_command_output_is_bounded_before_receipt(seed_lab: SeedLab) -> None:
    """Excessive preparation output is a diagnostic, not an oversized receipt."""
    uv = Path(seed_lab.config.toolchain.uv_binary)
    uv.write_text(uv.read_text().replace('print("uv fixture")', 'print("x" * 20000)'))
    with pytest.raises(ToolchainUnavailable, match="output exceeds"):
        seed_lab.seeder.prepare(
            seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "activation"
        )


def test_uv_created_internal_links_are_relocated_before_publication(
    seed_lab: SeedLab,
) -> None:
    """uv's own absolute archive pointers cannot retain a temporary seed path."""
    uv = Path(seed_lab.config.toolchain.uv_binary)
    uv.write_text(
        uv.read_text().replace(
            ' assert "--locked" in args and "--no-build" in args',
            ' cache = pathlib.Path(os.environ["UV_CACHE_DIR"])\n'
            ' link = cache / "uv-internal"\n'
            " if not link.exists(): "
            'link.symlink_to(cache / "archive-v0/locked-wheel")\n'
            ' assert "--locked" in args and "--no-build" in args',
        )
    )
    result = seed_lab.seeder.prepare(
        seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "activation"
    )
    link = result.cache / "uv-internal"
    assert not link.readlink().is_absolute()
    assert (link / "ruff.py").read_text() == "trusted wheel"


def test_host_cache_overrides_are_captured_before_runner_environment(
    tmp_path: Path,
) -> None:
    """Capture operator uv locations before rewriting the child environment."""
    configured = ToolchainConfig().with_host_env(
        {
            "UV_CACHE_DIR": str(tmp_path / "host-cache"),
            "UV_PYTHON_INSTALL_DIR": str(tmp_path / "managed-python"),
        }
    )
    assert configured.host_cache == tmp_path / "host-cache"
    assert configured.python_root == tmp_path / "managed-python"
    pinned = configured.with_host_env({"UV_CACHE_DIR": str(tmp_path / "other")})
    assert pinned == configured
    assert not configured.with_host_env({"UV_OFFLINE": "1"}).allow_host_fetch


def test_activation_lock_wait_is_bounded(seed_lab: SeedLab) -> None:
    """A concurrent preparation cannot leave a second wrapper waiting forever."""
    import fcntl

    activation = seed_lab.config.wrapper_root / "activation"
    activation.mkdir(parents=True)
    config = seed_lab.config.model_copy(
        update={
            "toolchain": seed_lab.config.toolchain.model_copy(
                update={"timeout_s": 0.02}
            )
        }
    )
    with (activation / "toolchain.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ToolchainUnavailable, match="lock timed out"):
            ToolchainSeeder(config, {}).prepare(
                seed_lab.repo, seed_lab.base, activation
            )
    assert not seed_lab.calls.exists()


def test_interrupted_seed_publication_is_not_reused(seed_lab: SeedLab) -> None:
    """A staged manifest without atomic publication cannot certify a reusable seed."""
    first = seed_lab.seeder.prepare(
        seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "first"
    )
    key = first.receipts[0].seed_key
    seeds = seed_lab.config.toolchain.seed_root
    assert seeds is not None
    interrupted = seeds / ("." + key + "-interrupted")
    (seeds / key).rename(interrupted)
    second = seed_lab.seeder.prepare(
        seed_lab.repo, seed_lab.base, seed_lab.config.wrapper_root / "second"
    )
    assert second.receipts[0].seed_key == key
    assert not interrupted.exists()
    assert (seeds / key / "seed.json").exists()
    events = [json.loads(line) for line in seed_lab.calls.read_text().splitlines()]
    assert sum(args[0] == "sync" for args, _ in events) == 4


@pytest.mark.proc
def test_host_sources_stay_read_only_under_the_outer_bound(seed_lab: SeedLab) -> None:
    """Even a direct shell cannot write host sources through their normal paths."""
    import subprocess

    from tests._profiles import make_task
    from workflow_interpreter.supervisor.sandbox import SandboxMode, wrap

    activation = seed_lab.config.wrapper_root / "activation"
    seeded = seed_lab.seeder.prepare(seed_lab.repo, seed_lab.base, activation)
    task = make_task(activation, writes=False, cwd=seed_lab.repo)
    channels = Path(task.channels.outcome_file).parent
    channels.mkdir(parents=True, exist_ok=True)
    plan = plan_for(
        task,
        repo_root=seed_lab.repo,
        wrapper_root=seed_lab.config.wrapper_root,
        channels_dir=channels,
    )
    plan = plan.model_copy(
        update={
            "toolchain_cache": (seeded.cache,),
            "ro_pins": (*plan.ro_pins, *seeded.protected_roots),
        }
    )
    command = (
        "/bin/sh",
        "-c",
        (
            'echo private > "$1/write-probe" || exit 2; shift; '
            'for source do if (echo poison > "$source/write-probe") 2>/dev/null; '
            "then exit 3; fi; done"
        ),
        "probe",
        str(seeded.cache),
        *(str(path) for path in seeded.protected_roots),
    )
    result = subprocess.run(
        wrap(command, plan, mode=SandboxMode.BWRAP),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (seeded.cache / "write-probe").read_text().strip() == "private"
    assert not any((root / "write-probe").exists() for root in seeded.protected_roots)
