"""Protected vendor state is intentional history, never a model writable root."""

import os
from pathlib import Path
from typing import Final

from workflow_interpreter.bdio import ActivationRecord, RootRecord
from workflow_interpreter.contracts.sessions import SessionReuse
from workflow_interpreter.profiles.errors import TaskRefused
from workflow_interpreter.supervisor.paths import WrapperPaths
from workflow_interpreter.supervisor.rpc_records import VENDOR_STATE

SESSION_STATES: Final[str] = "session-states"
MSG_STATE: Final[str] = "app-server vendor state is outside its protected owner"


def state_for(
    paths: WrapperPaths, root: RootRecord, activation: ActivationRecord
) -> Path:
    """Reuse only the source pinned at mint; otherwise start with private state."""
    source = activation.metadata.session_reuse_source
    if source is not None:
        state = Path(source.state_path)
    elif (
        root.index.nodes[activation.metadata.node].session_reuse
        is SessionReuse.SAME_NODE
    ):
        state = (
            paths.instance_dir
            / SESSION_STATES
            / activation.metadata.node
            / activation.activation_id
        )
    else:
        state = paths.activation_dir(activation.activation_id) / VENDOR_STATE
    if not state.is_relative_to(paths.instance_dir) or state.resolve() != state:
        raise TaskRefused(MSG_STATE)
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    stat = state.stat()
    if stat.st_uid != os.getuid() or stat.st_mode & 0o077:
        raise TaskRefused(MSG_STATE)
    return state
