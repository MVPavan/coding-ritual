"""Runner profiles — phase 4 of the workflow interpreter (spec v0.3 §6).

Three vendor adapters behind one invocation contract (§P4): `claude`, `codex`
and `opencode`. The §6 Protocol they satisfy is declared in
`supervisor/profile.py` and nothing here re-declares it.

Two rules hold across all three, and `_base.py` is where they are made
structural rather than remembered:

- **The exec is not delegable.** `launch` receives the supervisor's
  `ChildLauncher` and execs through it; the §5.2 fork barrier and the exec
  ledger are the crash-atomicity contract, and `launch.py` verifies the receipt
  afterwards.
- **The child environment is built once**, through `RunnerChannels.env()`, so
  the §7.4 committer identity is always stamped (§14, phase-3 ruling).

The danger default is inverted per vendor with whatever that vendor can
actually enforce — permission rules for claude, an OS sandbox plus a network
denial for codex, and for opencode a refusal, because it has no mechanism at
all (see `opencode.py`). Every flag was probed before it was written down;
the evidence is in `scratchpad/probes/phase4-cli-probes.md` and the captured
streams under `tests/fixtures/profiles/`.
"""

from workflow_interpreter.profiles._base import BaseProfile, fold_usage, parse_lines
from workflow_interpreter.profiles.claude import ClaudeProfile
from workflow_interpreter.profiles.codex import CodexProfile
from workflow_interpreter.profiles.config import (
    BASE_PASSTHROUGH_ENV,
    MODEL_VENDOR_DEFAULT,
    ProfileConfig,
    RunnerName,
)
from workflow_interpreter.profiles.errors import (
    ProfileError,
    TaskRefused,
    UnknownProfileError,
    UnsupportedOptionError,
)
from workflow_interpreter.profiles.opencode import OpencodeProfile
from workflow_interpreter.profiles.registry import ProfileRegistry, runner_name

__all__ = [
    "BASE_PASSTHROUGH_ENV",
    "MODEL_VENDOR_DEFAULT",
    "BaseProfile",
    "ClaudeProfile",
    "CodexProfile",
    "OpencodeProfile",
    "ProfileConfig",
    "ProfileError",
    "ProfileRegistry",
    "RunnerName",
    "TaskRefused",
    "UnknownProfileError",
    "UnsupportedOptionError",
    "fold_usage",
    "parse_lines",
    "runner_name",
]
