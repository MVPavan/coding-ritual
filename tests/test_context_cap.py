"""A role's activation context cap reaches Claude as `--autocompact`."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tests._foreman import DEFAULT_LAB_ROLES, ForemanLab
from tests._inspector import FrozenClock
from tests._profiles import INSTRUCTIONS, make_claude, make_codex, make_task
from workflow_interpreter.contracts.sessions import SessionMode
from workflow_interpreter.foreman.cases import startup_invocation
from workflow_interpreter.foreman.config import CrewBinding

AUTOCOMPACT = "--autocompact"
CODEX_WINDOW_KEYS = ("model_context_window", "model_auto_compact_token_limit")
REFUSED = "refused"
"""Config load refuses the cap by name; no argv is ever built."""
SESSION = "4f1c2d3e-0000-4000-8000-000000000001"
"""A UUID, the form claude's `--session-id` requires; codex takes it as-is."""


@pytest.mark.parametrize(
    ("profile", "model", "cap", "expected"),
    [
        ("claude", "claude-opus-5", 400000, (AUTOCOMPACT, "400000")),
        ("claude", "claude-opus-5", 100_000, (AUTOCOMPACT, "100000")),
        ("claude", "claude-opus-5", 1_000_000, (AUTOCOMPACT, "1000000")),
        ("claude", "claude-opus-5", 400, REFUSED),
        ("claude", "claude-opus-5", 1_000_001, REFUSED),
        ("claude", "claude-opus-5", None, None),
        ("codex", "gpt-5.6-sol", None, None),
    ],
)
def test_role_cap_reaches_launch_and_resume_argv(
    tmp_path: Path,
    profile: str,
    model: str,
    cap: int | None,
    expected: tuple[str, str] | str | None,
) -> None:
    """In-range claude cap passes unchanged on both argv; out of range is refused
    by role at config load; unset and codex emit none."""
    binding = CrewBinding(
        profile=profile, model=model, effort="high", context_cap_tokens=cap
    )
    roles = {**DEFAULT_LAB_ROLES, "implementer": binding}
    if expected == REFUSED:
        with pytest.raises(
            ValidationError,
            match=rf"role 'implementer' sets context_cap_tokens={cap}; "
            r"claude's --autocompact accepts 100000-1000000",
        ):
            ForemanLab(tmp_path, roles=roles)
        return
    lab = ForemanLab(tmp_path, roles=roles)
    root = lab.instantiate_resolved()
    view = startup_invocation(lab.composition, root, "implement")
    task = make_task(tmp_path, model=model).model_copy(
        update={"context_cap_tokens": view.context_cap_tokens}
    )
    crew = (
        make_claude(tmp_path, FrozenClock())
        if profile == "claude"
        else make_codex(tmp_path, FrozenClock())
    )
    for argv in (
        crew.build_command(task, SESSION).argv,
        crew.build_resume_command(SESSION, INSTRUCTIONS, task).argv,
    ):
        if expected is None:
            assert AUTOCOMPACT not in argv
        else:
            assert isinstance(expected, tuple)
            at = argv.index(AUTOCOMPACT)
            assert argv[at : at + 2] == expected
        assert not any(key in item for item in argv for key in CODEX_WINDOW_KEYS)


def test_codex_role_setting_the_cap_is_refused_by_name(tmp_path: Path) -> None:
    """A codex role cannot carry a claude-only cap; config load names the role."""
    critic = CrewBinding(
        profile="codex", model="gpt-5.6-sol", effort="high", context_cap_tokens=400000
    )

    with pytest.raises(ValidationError, match="role 'critic' binds profile 'codex'"):
        ForemanLab(tmp_path, roles={**DEFAULT_LAB_ROLES, "critic": critic})


def test_opencode_role_resuming_is_refused_by_name(tmp_path: Path) -> None:
    """opencode never registers a session, so a resume pin would run fresh forever."""
    critic = CrewBinding(
        profile="opencode", model="glm", effort="high", session_mode=SessionMode.RESUME
    )

    with pytest.raises(ValidationError, match="role 'critic' binds profile 'opencode'"):
        ForemanLab(tmp_path, roles={**DEFAULT_LAB_ROLES, "critic": critic})
