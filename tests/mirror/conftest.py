"""Fixtures for the Beads -> GitHub mirror tests; the harness itself is in ``_harness.py``."""

from __future__ import annotations

import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.mirror._harness import (
    FAKE_GH,
    Fake,
    Mirror,
    initial_fake_state,
    make_store,
    real_tool,
)


@pytest.fixture(scope="session")
def store_templates(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, tuple[Path, str]]:
    base = tmp_path_factory.mktemp("stores")
    return {name: (base / name, make_store(base / name, name)) for name in ("ma", "mb")}


@pytest.fixture
def mirror(
    tmp_path: Path, store_templates: dict[str, tuple[Path, str]]
) -> Iterator[Mirror]:
    template, project_id = store_templates["ma"]
    clone = tmp_path / "clone"
    shutil.copytree(template, clone, symlinks=True)

    state_path = tmp_path / "fake-gh.json"
    fake = Fake(state_path)
    fake.save(initial_fake_state())
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    wrapper = bin_dir / "gh"
    wrapper.write_text(
        f'#!/bin/sh\nFAKE_GH_STATE="{state_path}" exec "{sys.executable}" "{FAKE_GH}" "$@"\n'
    )
    wrapper.chmod(0o755)

    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    (tools_dir / "git").symlink_to(real_tool("git"))
    bd_shim = tools_dir / "bd"
    count_beads_env = f'"{real_tool("env")}" | "{real_tool("grep")}" -c "^BEADS_"'
    bd_shim.write_text(
        "#!/bin/sh\n"
        f'printf "%s beads_env=%s\\n" "$*" "$({count_beads_env})" >> "$MIRROR_TEST_BD_LOG"\n'
        f'exec "{real_tool("bd")}" "$@"\n'
    )
    bd_shim.chmod(0o755)

    m = Mirror(clone, project_id, fake, bin_dir, tools_dir, tmp_path / "bd-calls.log")
    yield m
    assert fake.load()["unrecognised"] == [], "the fake gh saw calls it does not serve"


@pytest.fixture
def other_store(store_templates: dict[str, tuple[Path, str]]) -> tuple[Path, str]:
    return store_templates["mb"]
