"""Shared fixtures, plus the opt-in gate that keeps token-spending tests off.

The bd workspace is created per test SESSION under `tmp_path_factory` — never
this repo's own `.beads`. It is deliberately outside the repo tree: a bd
workspace nested inside another repo's workspace leaks the outer project's
beads into read paths (probed 2026-08-25), which would make "count the
instance's beads" assertions meaningless. Every assertion still selects by
`wf_root_id`, as the spec's §11 lab note requires.

**`live` tests are deselected unless `--run-live` is passed**, and that is a
collection hook rather than a marker expression on purpose. `addopts =
-m 'not live'` looked equivalent and was not: any `-m` on the command line
REPLACES it, so the gate recipe every earlier phase used
(`pytest -q -m "not bd"`) selected the four real-CLI tests and spent tokens.
An option gate cannot be overridden by an `-m` the way a default marker
expression can, and deselecting rather than skipping is what makes
`--collect-only` show the truth about what a run would execute.
"""

from __future__ import annotations

import shutil
import statistics
import subprocess
import time
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Final

import pytest

from tests._fake_bd import FakeBd
from tests._helpers import (
    AUTHORING_FIXTURE,
    BUILD_LOOP_GRAPH,
    LEGACY_BUILD_LOOP_GRAPH,
    VALID_FIXTURE,
)
from tests._profiles import Lab
from workflow_interpreter.bdio import GateVerifier, SigningConfig
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.contracts.codex import CODEX_VERSION
from workflow_interpreter.foreman.model_catalog import ModelCatalog
from workflow_interpreter.ledger.claims import LedgerClaims
from workflow_interpreter.ledger.database import LedgerDatabase, open_ledger
from workflow_interpreter.ledger.store import LedgerStore
from workflow_interpreter.tracker.bd_transport import BdClient, BdConfig

BD_BINARY: Final[str] = "bd"
CODEX_BINARY: Final[str] = "codex"
SSH_KEYGEN: Final[str] = "ssh-keygen"
TEST_ACTOR: Final[str] = "wf-test-foreman"
TEST_PRINCIPAL: Final[str] = "gatekeeper@wf-test"
INIT_TIMEOUT_S: Final[float] = 180.0
LIST_TIMEOUT_S: Final[float] = 60.0
LATENCY_SAMPLES: Final[int] = 3
KEYGEN_TIMEOUT_S: Final[float] = 30.0
CODEX_VERSION_TIMEOUT_S: Final[float] = 5.0
BRANCH_HEAD: Final[str] = "b" * 40
"""The instance branch head every test's injected reader reports (§3.2)."""

_SKIP_NO_BD: Final[str] = "the bd binary is not on PATH"
_SKIP_NO_SSH_KEYGEN: Final[str] = "ssh-keygen is not on PATH"

FAKE_WORKSPACE: Final[Path] = Path("/tmp/wf-fake-lab")

RUN_LIVE_OPTION: Final[str] = "--run-live"
LIVE_MARKER: Final[str] = "live"
_RUN_LIVE_HELP: Final[str] = (
    "run the `live` tests, which invoke a real vendor CLI, need working auth "
    "and spend tokens; without it they are deselected at collection"
)


@pytest.fixture(autouse=True)
def block_real_catalog_clis(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Require an injected CLI boundary for catalog work in non-live tests."""
    if request.node.get_closest_marker(LIVE_MARKER) is not None:
        return
    original = ModelCatalog._run

    def guarded(
        catalog: ModelCatalog, argv: list[str], timeout: float
    ) -> subprocess.CompletedProcess[str]:
        """Fail before a default catalog runner can reach a vendor binary."""
        if catalog._runner is None:
            pytest.fail(f"non-live catalog test used real {Path(argv[0]).name} CLI")
        return original(catalog, argv, timeout)

    monkeypatch.setattr(ModelCatalog, "_run", guarded)


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register the explicit opt-in the `live` family requires."""
    parser.addoption(
        RUN_LIVE_OPTION, action="store_true", default=False, help=_RUN_LIVE_HELP
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Drop every `live`-marked test from the run unless `--run-live` was given.

    Deselected, not skipped: a skip still shows up in `--collect-only`, so
    nobody can read the output and tell whether a recipe is about to spend
    money. This is the only gate — the marker alone never was one.
    """
    if config.getoption(RUN_LIVE_OPTION):
        return
    deselected = [item for item in items if item.get_closest_marker(LIVE_MARKER)]
    if not deselected:
        return
    config.hook.pytest_deselected(items=deselected)
    items[:] = [item for item in items if item not in deselected]


PLAN_REF: Final[str] = "docs/plan.md"
APPROVED_TEXT: Final[bytes] = b"the plan as approved\n"
EDITED_TEXT: Final[bytes] = b"the plan, quietly edited\n"


class Documents:
    """A workspace-scoped artifact reader over an in-memory document set (§9)."""

    def __init__(self, contents: dict[str, bytes]) -> None:
        self.contents = contents

    def __call__(self, artifact_ref: str) -> bytes:
        return self.contents[artifact_ref]


Signer = Callable[[bytes, Path | None], bytes]


def branch_head() -> str:
    """A deterministic stand-in for the phase-3 git head reader."""
    return BRANCH_HEAD


def _require(binary: str, reason: str) -> str:
    """Resolve a required binary, or skip the test that asked for it."""
    found = shutil.which(binary)
    if found is None:
        pytest.skip(reason)
    return found


@pytest.fixture(scope="session")
def pinned_codex_appserver_cli() -> tuple[str, str]:
    """Require the installed CLI version frozen by the app-server crew."""
    binary = _require(
        CODEX_BINARY,
        f"codex binary absent; pinned codex-cli version is {CODEX_VERSION}",
    )
    version = subprocess.run(
        [binary, "--version"],
        capture_output=True,
        text=True,
        timeout=CODEX_VERSION_TIMEOUT_S,
        check=True,
    )
    version_output = version.stdout.strip()
    installed = version_output.removeprefix("codex-cli ")
    if installed != CODEX_VERSION:
        pytest.skip(
            f"installed codex-cli {installed} differs from pinned codex-cli "
            f"{CODEX_VERSION}"
        )
    return binary, version_output


@pytest.fixture(scope="session")
def bd_workspace(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A throwaway git repo with its own `.beads`, created once per session."""
    _require(BD_BINARY, _SKIP_NO_BD)
    workspace = tmp_path_factory.mktemp("bd-lab")
    subprocess.run(
        ["git", "init", "--quiet", str(workspace)],
        check=True,
        capture_output=True,
        timeout=INIT_TIMEOUT_S,
    )
    subprocess.run(
        [BD_BINARY, "init", "--prefix", "wf", "--non-interactive"],
        cwd=workspace,
        check=True,
        capture_output=True,
        timeout=INIT_TIMEOUT_S,
    )
    return workspace


@pytest.fixture(scope="session")
def bd_latency_s(bd_workspace: Path) -> float:
    """Median wall seconds of ONE `bd` round trip against the session workspace.

    Wall budgets in bd-marked tests are call counts times this, never a fixed
    number of seconds: a `bd` invocation costs ~50 ms on one host and ~290 ms on
    another, which is the whole of `cr-xu34`. Measured once per session, and
    with the same subcommand (`list --json`) the engine's reads use.
    """
    samples: list[float] = []
    for _ in range(LATENCY_SAMPLES):
        started = time.monotonic()
        subprocess.run(
            [BD_BINARY, "list", "--json"],
            cwd=bd_workspace,
            check=True,
            capture_output=True,
            timeout=LIST_TIMEOUT_S,
        )
        samples.append(time.monotonic() - started)
    return statistics.median(samples)


@pytest.fixture
def bd_config(bd_workspace: Path) -> BdConfig:
    """Injected transport config pointing at the throwaway workspace."""
    return BdConfig(workspace=bd_workspace, actor=TEST_ACTOR)


@pytest.fixture
def bd_client(bd_config: BdConfig) -> BdClient:
    """A real bd transport against the throwaway workspace."""
    return BdClient(bd_config)


@pytest.fixture(scope="session")
def signing_key(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An ed25519 key plus an `allowed_signers` file, outside any bd workspace."""
    _require(SSH_KEYGEN, _SKIP_NO_SSH_KEYGEN)
    key_dir = tmp_path_factory.mktemp("wf-signers")
    key_path = key_dir / "gate_key"
    subprocess.run(
        [
            SSH_KEYGEN,
            "-t",
            "ed25519",
            "-N",
            "",
            "-C",
            TEST_PRINCIPAL,
            "-f",
            str(key_path),
        ],
        check=True,
        capture_output=True,
        timeout=KEYGEN_TIMEOUT_S,
    )
    public = (key_dir / "gate_key.pub").read_text(encoding="utf-8").strip()
    (key_dir / "allowed_signers").write_text(
        f"{TEST_PRINCIPAL} {public}\n", encoding="utf-8"
    )
    return key_path


@pytest.fixture
def signing_config(signing_key: Path) -> SigningConfig:
    """§9 verification config pointing at the throwaway allow-list."""
    return SigningConfig(allowed_signers_path=signing_key.parent / "allowed_signers")


@pytest.fixture
def gate_verifier(
    signing_config: SigningConfig, ledger_repo: tuple[Path, Path]
) -> GateVerifier:
    """A verifier whose allow-list lives outside what the engine writes (§9)."""
    return GateVerifier(signing_config, ledger_repo[0])


LAB_TASK: Final[str] = "cr-3411.2"
LAB_EPIC: Final[str] = "cr-3411"
"""The task and epic every ledger-backed fixture store is scoped to.

One task per store is the ledger's own shape (§3.3): its rows are keyed by
`task_id`, and the epic is an INPUT at mint (§3.7), never a parse of the id."""


@pytest.fixture
def ledger_repo(tmp_path: Path) -> tuple[Path, Path]:
    """A repository and a wrapper root, with the in-repo `.git` shape.

    `.git` as a DIRECTORY is its own git common directory, which is all the
    fence resolver reads — so a store fixture needs no `git` binary.
    """
    repo_root = tmp_path / "fixture-repo"
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    wrapper_root = tmp_path / "fixture-wrapper"
    wrapper_root.mkdir(exist_ok=True)
    return repo_root, wrapper_root


@pytest.fixture
def ledger(ledger_repo: tuple[Path, Path]) -> Iterator[LedgerDatabase]:
    """This test's own ledger, fenced and migrated exactly as production's is."""
    repo_root, wrapper_root = ledger_repo
    with open_ledger(repo_root, wrapper_root) as database:
        yield database


@pytest.fixture
def documents() -> Documents:
    """The mutable gate document, as approved (§9 artifact reader)."""
    return Documents({PLAN_REF: APPROVED_TEXT})


@pytest.fixture
def gate_store(
    fake_client: LedgerStore,
    ledger: LedgerDatabase,
    gate_verifier: GateVerifier,
    documents: Documents,
) -> WorkflowStore:
    """A store that can verify §9 approvals and re-hash mutable artifacts."""
    return WorkflowStore(
        fake_client,
        gate_verifier,
        artifact_reader=documents,
        branch_head_reader=branch_head,
        claims=LedgerClaims(ledger),
    )


@pytest.fixture
def fake_bd() -> FakeBd:
    """An in-memory bd workspace with crash injection and scheduling hooks."""
    return FakeBd(str(FAKE_WORKSPACE))


@pytest.fixture
def fake_bd_client(fake_bd: FakeBd) -> BdClient:
    """The bd TRANSPORT over the in-memory workspace — tracker traffic only.

    Distinct from `fake_client` since S6: that one is the record store, and bd
    is no longer one (R1). What is left here is what a tracker asks.
    """
    return BdClient(BdConfig(workspace=FAKE_WORKSPACE, actor=TEST_ACTOR), fake_bd)


@pytest.fixture
def fake_client(ledger: LedgerDatabase) -> LedgerStore:
    """The record store itself, for the tests that write rows directly."""
    return LedgerStore(ledger, task_id=LAB_TASK, epic_id=LAB_EPIC)


@pytest.fixture
def fake_store(fake_client: LedgerStore, ledger: LedgerDatabase) -> WorkflowStore:
    """The typed write API over this test's ledger, no §9 verifier."""
    return WorkflowStore(
        fake_client, branch_head_reader=branch_head, claims=LedgerClaims(ledger)
    )


@pytest.fixture
def sign_payload(signing_key: Path, tmp_path: Path) -> Signer:
    """A callable that signs canonical payload bytes as the allow-listed key."""

    def _sign(payload_bytes: bytes, key_path: Path | None = None) -> bytes:
        message = tmp_path / "payload.json"
        message.write_bytes(payload_bytes)
        subprocess.run(
            [
                SSH_KEYGEN,
                "-Y",
                "sign",
                "-f",
                str(key_path or signing_key),
                "-n",
                "wf-gate",
                str(message),
            ],
            check=True,
            capture_output=True,
            timeout=KEYGEN_TIMEOUT_S,
        )
        signature = message.with_suffix(".json.sig").read_bytes()
        message.with_suffix(".json.sig").unlink()
        return signature

    return _sign


@pytest.fixture
def lab(tmp_path: Path) -> Iterator[Lab]:
    """An inspector over a throwaway repo, ready to exec a stub vendor CLI.

    Here rather than in a `test_profiles_*` module because two of them now drive
    the same `Lab` (`tests/_profiles.py`), and a fixture imported into a test
    module reads as an unused import to every linter that looks at it.
    """
    built = Lab(tmp_path)
    try:
        yield built
    finally:
        built.cleanup()


@pytest.fixture(params=["shipped", "legacy"])
def feature_graph(request: pytest.FixtureRequest) -> Path:
    """Exercise the shipped graph first and its immutable legacy predecessor."""
    return AUTHORING_FIXTURE if request.param == "shipped" else VALID_FIXTURE


@pytest.fixture(params=["shipped", "legacy"])
def build_loop_graph(request: pytest.FixtureRequest) -> Path:
    """Run build-loop behavior against both execution-contract generations."""
    return BUILD_LOOP_GRAPH if request.param == "shipped" else LEGACY_BUILD_LOOP_GRAPH
