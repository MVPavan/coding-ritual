"""A role's activation context cap reaches Claude as `--autocompact`."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from tests._foreman import DEFAULT_LAB_ROLES, ForemanLab
from tests._inspector import FrozenClock
from tests._profiles import INSTRUCTIONS, make_claude, make_codex, make_task
from workflow_interpreter.bdio.wire import activation_binding_digest
from workflow_interpreter.contracts.execution import CrewName
from workflow_interpreter.foreman.cases import mint_entry, startup_invocation
from workflow_interpreter.foreman.config import CrewBinding
from workflow_interpreter.foreman.errors import ResolutionError
from workflow_interpreter.foreman.model_catalog import (
    CatalogModel,
    CatalogProvenance,
    CatalogSnapshot,
    FamilySnapshot,
    VerificationStatus,
)

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
        ("claude", "claude-opus-5", None, (AUTOCOMPACT, "370000")),
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
    binding = CrewBinding(model=model, effort="high", context_cap_tokens=cap)
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
    """A codex role cannot carry a Claude-only cap at catalog qualification."""
    critic = CrewBinding(model="gpt-5.6-sol", effort="high", context_cap_tokens=400000)

    lab = ForemanLab(tmp_path, roles={**DEFAULT_LAB_ROLES, "critic": critic})
    root = lab.instantiate_resolved()
    with pytest.raises(
        ResolutionError,
        match="role 'critic': context_cap_tokens is only supported by claude",
    ):
        startup_invocation(lab.composition, root, "review")


@pytest.mark.parametrize(
    ("family", "window", "expected"),
    [
        (CrewName.CLAUDE, 1_000_000, 370_000),
        (CrewName.CODEX, 1_000_000, None),
    ],
)
def test_catalog_default_cap_is_pinned_at_mint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    family: CrewName,
    window: int,
    expected: int | None,
) -> None:
    model = "claude-a" if family is CrewName.CLAUDE else "codex-a"
    role_path = tmp_path / "roles.toml"
    role_path.write_text(
        f'[roles.implementer]\nmodel = "{model}"\neffort = "high"\n',
        encoding="utf-8",
    )
    snapshot = CatalogSnapshot(
        generated_at="2026-09-23T00:00:00Z",
        digest="cap-at-mint",
        families={
            family: FamilySnapshot(
                source="checked-seed-and-probe"
                if family is CrewName.CLAUDE
                else "bundled-cli",
                available=True,
                models=(
                    CatalogModel(
                        id=model,
                        efforts=("high",),
                        context_window=window,
                        verification=(
                            VerificationStatus.PROBE_OK
                            if family is CrewName.CLAUDE
                            else None
                        ),
                    ),
                ),
            )
        },
    )
    lab = ForemanLab(tmp_path)
    lab.profiles.accepted = lab.profiles.accepted | {family.value}
    lab.config = lab.config.model_copy(update={"role_bindings_path": role_path})
    lab.composition = replace(
        lab.composition,
        config=lab.config,
        catalog=snapshot,
        catalog_provenance=CatalogProvenance.REFRESHED,
    )
    monkeypatch.setattr(lab.spawner, "launch", lambda *_args, **_kwargs: None)
    root = lab.instantiate()

    minted = mint_entry(lab.composition, lab.wiring(), root)

    assert minted.dispatched is not None
    metadata = lab.store.reads.load_activation(minted.dispatched).metadata
    assert metadata.context_cap_tokens == expected
    assert metadata.binding_digest == activation_binding_digest(metadata)
    changed = metadata.model_copy(
        update={"context_cap_tokens": 370_000 if expected is None else None}
    )
    assert metadata.binding_digest != activation_binding_digest(changed)
