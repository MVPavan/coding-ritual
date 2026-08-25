"""Injected configuration for the bd transport and the §9 gate verifier.

Frozen models constructed by the caller and handed to `BdClient` /
`GateVerifier` at construction time. Deliberately NOT `pydantic-settings`
`BaseSettings` (the repo's default for config): `BaseSettings` reads the
process environment, and `rules/python/safety.md` forbids ambient environment
reads inside this boundary — the whole point of the typed wrapper is that
every bd invocation is fully determined by what the caller injected.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

CONFIG_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="forbid", arbitrary_types_allowed=False
)

DEFAULT_BD_BINARY: Final[str] = "bd"
DEFAULT_SSH_KEYGEN: Final[str] = "ssh-keygen"
DEFAULT_COMMAND_TIMEOUT_S: Final[float] = 60.0
DEFAULT_VERIFY_TIMEOUT_S: Final[float] = 15.0
PINNED_BD_VERSION: Final[str] = "1.1.0"
PINNED_BACKEND: Final[str] = "dolt"
PINNED_DOLT_MODE: Final[str] = "embedded"
GATE_SIGNATURE_NAMESPACE: Final[str] = "wf-gate"


class BdConfig(BaseModel):
    """Everything the bd transport needs; nothing is discovered from the process.

    `expected_*` pin the backend identity the §11 startup canary asserts — a
    fallback or skewed store must refuse dispatch loudly, not degrade.
    """

    model_config = CONFIG_MODEL

    workspace: Path
    actor: str = Field(min_length=1)
    binary: str = DEFAULT_BD_BINARY
    command_timeout_s: float = Field(default=DEFAULT_COMMAND_TIMEOUT_S, gt=0)
    expected_backend: str = PINNED_BACKEND
    expected_dolt_mode: str = PINNED_DOLT_MODE
    expected_bd_version: str = PINNED_BD_VERSION


class SigningConfig(BaseModel):
    """§9 gate-signature verification inputs.

    `allowed_signers_path` is the pinned allow-list — an OpenSSH
    `allowed_signers` file. It must live outside the bd workspace (and outside
    the repo): a foreman that can write its own allow-list can forge approvals,
    so `GateVerifier` refuses a path inside the workspace at construction.
    """

    model_config = CONFIG_MODEL

    allowed_signers_path: Path
    namespace: str = GATE_SIGNATURE_NAMESPACE
    ssh_keygen: str = DEFAULT_SSH_KEYGEN
    verify_timeout_s: float = Field(default=DEFAULT_VERIFY_TIMEOUT_S, gt=0)
