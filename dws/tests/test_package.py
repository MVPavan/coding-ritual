"""The package is importable from the installed distribution, not the source tree."""

from __future__ import annotations

from importlib.metadata import entry_points, version

import dws


def test_import_exposes_a_version_matching_the_distribution() -> None:
    assert dws.__version__ == version("dws")


def test_console_script_entry_point_targets_the_cli() -> None:
    scripts = entry_points(group="console_scripts")
    assert scripts["dws"].value == "dws.cli:main"


def test_runtime_package_depends_only_on_the_standard_library() -> None:
    from importlib.metadata import requires

    assert requires("dws") in (None, [])
