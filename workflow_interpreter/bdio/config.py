"""Injected configuration for the §9 gate verifier.

A frozen model constructed by the caller and handed to `GateVerifier` at
construction time. Deliberately NOT `pydantic-settings` `BaseSettings` (the
repo's default for config): `BaseSettings` reads the process environment, and
`rules/python/safety.md` forbids ambient environment reads inside this
boundary — verification authority is fully determined by what was injected.

The bd transport's own config left with the transport in S6
(`tracker/bd_transport.py`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field

CONFIG_MODEL: Final[ConfigDict] = ConfigDict(
    frozen=True, extra="forbid", arbitrary_types_allowed=False
)

DEFAULT_SSH_KEYGEN: Final[str] = "ssh-keygen"
DEFAULT_VERIFY_TIMEOUT_S: Final[float] = 15.0
GATE_SIGNATURE_NAMESPACE: Final[str] = "wf-gate"


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
