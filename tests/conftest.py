"""Shared fixtures: a throwaway bd workspace and a throwaway signing key.

The bd workspace is created per test SESSION under `tmp_path_factory` — never
this repo's own `.beads`. It is deliberately outside the repo tree: a bd
workspace nested inside another repo's workspace leaks the outer project's
beads into read paths (probed 2026-08-25), which would make "count the
instance's beads" assertions meaningless. Every assertion still selects by
`wf_root_id`, as the spec's §11 lab note requires.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Final

import pytest

from tests._fake_bd import FakeBd
from workflow_interpreter.bdio import BdConfig, GateVerifier, SigningConfig
from workflow_interpreter.bdio.api import WorkflowStore
from workflow_interpreter.bdio.client import BdClient

BD_BINARY: Final[str] = "bd"
SSH_KEYGEN: Final[str] = "ssh-keygen"
TEST_ACTOR: Final[str] = "wf-test-foreman"
TEST_PRINCIPAL: Final[str] = "gatekeeper@wf-test"
INIT_TIMEOUT_S: Final[float] = 180.0
KEYGEN_TIMEOUT_S: Final[float] = 30.0
BRANCH_HEAD: Final[str] = "b" * 40
"""The instance branch head every test's injected reader reports (§3.2)."""

_SKIP_NO_BD: Final[str] = "the bd binary is not on PATH"
_SKIP_NO_SSH_KEYGEN: Final[str] = "ssh-keygen is not on PATH"

FAKE_WORKSPACE: Final[Path] = Path("/tmp/wf-fake-lab")

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
def gate_verifier(signing_config: SigningConfig, bd_workspace: Path) -> GateVerifier:
    """A verifier whose allow-list lives outside the bd workspace (§9)."""
    return GateVerifier(signing_config, bd_workspace)


@pytest.fixture
def store(bd_client: BdClient, gate_verifier: GateVerifier) -> WorkflowStore:
    """The typed write API wired to real bd and a real §9 verifier."""
    return WorkflowStore(bd_client, gate_verifier, branch_head_reader=branch_head)


@pytest.fixture
def documents() -> Documents:
    """The mutable gate document, as approved (§9 artifact reader)."""
    return Documents({PLAN_REF: APPROVED_TEXT})


@pytest.fixture
def gate_store(
    fake_client: BdClient, gate_verifier: GateVerifier, documents: Documents
) -> WorkflowStore:
    """A store that can verify §9 approvals and re-hash mutable artifacts."""
    return WorkflowStore(
        fake_client,
        gate_verifier,
        artifact_reader=documents,
        branch_head_reader=branch_head,
    )


@pytest.fixture
def fake_bd() -> FakeBd:
    """An in-memory bd workspace with crash injection and scheduling hooks."""
    return FakeBd(str(FAKE_WORKSPACE))


@pytest.fixture
def fake_client(fake_bd: FakeBd) -> BdClient:
    """The real transport driving the in-memory workspace."""
    return BdClient(BdConfig(workspace=FAKE_WORKSPACE, actor=TEST_ACTOR), fake_bd)


@pytest.fixture
def fake_store(fake_client: BdClient) -> WorkflowStore:
    """The typed write API over the in-memory workspace, no §9 verifier."""
    return WorkflowStore(fake_client, branch_head_reader=branch_head)


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
