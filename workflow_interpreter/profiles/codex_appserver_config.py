"""Supported 0.154.0 overrides shared by startup and both thread admission RPCs."""

import json
from typing import Final

from pydantic import JsonValue

DISABLED_FEATURES: Final[tuple[str, ...]] = (
    "apps",
    "browser_use",
    "browser_use_external",
    "computer_use",
    "image_generation",
    "multi_agent",
    "multi_agent_v2",
    "plugins",
    "remote_plugin",
    "skill_mcp_dependency_install",
    "tool_suggest",
)
KEY_NETWORK: Final[str] = "sandbox_workspace_write.network_access"
KEY_TMP: Final[str] = "sandbox_workspace_write.exclude_slash_tmp"
KEY_MCP: Final[str] = "mcp_servers"
KEY_WEB: Final[str] = "web_search"
WEB_DISABLED: Final[str] = "disabled"
CONFIG_FLAG: Final[str] = "-c"


def thread_config() -> dict[str, JsonValue]:
    """Deny optional tool integrations; retain sandboxed local shell/edit tools.

    An empty MCP map does not erase inherited entries. The private CODEX_HOME
    and untrusted project layers suppress those sources; this map expresses
    the engine's empty configuration on both thread/start and thread/resume.
    Dynamic client tools are never registered; incoming calls remain denied.
    """
    return {
        KEY_NETWORK: False,
        KEY_TMP: True,
        KEY_MCP: {},
        KEY_WEB: WEB_DISABLED,
        **{f"features.{name}": False for name in DISABLED_FEATURES},
    }


def config_argv() -> tuple[str, ...]:
    """Use the same supported values before any thread can restore configuration."""
    return tuple(
        word
        for key, value in thread_config().items()
        for word in (CONFIG_FLAG, f"{key}={json.dumps(value)}")
    )
