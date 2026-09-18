"""Bounded capture of runner-controlled output trees."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from workflow_interpreter.supervisor import channels
from workflow_interpreter.supervisor.channels import walk_outputs
from workflow_interpreter.supervisor.outputs import OutputsWalk, UnsafeKind


def _walk(root: Path, snapshot: Path, **overrides: int) -> OutputsWalk:
    """Walk a test output tree with the production defaults made small."""
    return walk_outputs(
        root,
        snapshot,
        max_files=overrides.get("max_files", 100),
        max_bytes=overrides.get("max_bytes", 100_000),
        max_walk_entries=overrides.get("max_walk_entries", 100),
        max_depth=overrides.get("max_depth", 32),
    )


def _unsafe(walk: OutputsWalk) -> set[tuple[str, UnsafeKind]]:
    """Render the stable unsafe entries for concise contract assertions."""
    return {(entry.path, entry.kind) for entry in walk.unsafe}


def test_walk_uses_sorted_preorder_when_file_cap_is_reached(tmp_path: Path) -> None:
    """A child directory precedes later root siblings in the capped listing."""
    root = tmp_path / "outputs"
    (root / "a").mkdir(parents=True)
    (root / "a" / "x.txt").write_text("x", encoding="utf-8")
    (root / "b.txt").write_text("b", encoding="utf-8")

    walk = walk_outputs(
        root,
        tmp_path / "snapshot",
        max_files=1,
        max_bytes=100,
        max_walk_entries=100,
        max_depth=10,
    )

    assert walk.paths == ("a/x.txt",)
    assert walk.truncated is True


def test_walk_refuses_a_symlinked_root_and_unsafe_entries(tmp_path: Path) -> None:
    """Links and FIFOs are reported but never read or followed."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(outside, target_is_directory=True)
    root = tmp_path / "outputs"
    root.mkdir()
    (root / "link.txt").symlink_to(outside / "secret.txt")
    os.mkfifo(root / "pipe")

    root_walk = _walk(linked_root, tmp_path / "root-snapshot")
    walk = _walk(root, tmp_path / "snapshot")

    assert _unsafe(root_walk) == {(".", UnsafeKind.ROOT)}
    assert walk.paths == ()
    assert _unsafe(walk) == {
        ("link.txt", UnsafeKind.SYMLINK),
        ("pipe", UnsafeKind.SPECIAL),
    }


def test_walk_enforces_file_and_byte_boundaries(tmp_path: Path) -> None:
    """Exact byte totals fit; the first byte over the cap does not."""
    root = tmp_path / "outputs"
    root.mkdir()
    (root / "a").write_bytes(b"aa")
    (root / "b").write_bytes(b"bb")
    (root / "c").write_bytes(b"cc")
    byte_root = tmp_path / "bytes"
    byte_root.mkdir()
    (byte_root / "a").write_bytes(b"aa")
    (byte_root / "b").write_bytes(b"bb")

    file_walk = _walk(root, tmp_path / "file-snapshot", max_files=2)
    exact_walk = _walk(byte_root, tmp_path / "exact-snapshot", max_bytes=4)
    over_walk = _walk(byte_root, tmp_path / "over-snapshot", max_bytes=3)

    assert file_walk.paths == ("a", "b")
    assert file_walk.truncated is True
    assert exact_walk.paths == ("a", "b")
    assert exact_walk.truncated is False
    assert over_walk.paths == ("a",)
    assert over_walk.total_bytes == 2
    assert over_walk.truncated is True


def test_a_file_beyond_the_remaining_byte_budget_is_dropped_not_partly_captured(
    tmp_path: Path,
) -> None:
    """N2 excludes an over-budget file before creating any snapshot bytes."""
    root = tmp_path / "outputs"
    root.mkdir()
    (root / "fits").write_bytes(b"aa")
    (root / "too-large").write_bytes(b"bb")
    snapshot = tmp_path / "snapshot"

    walk = _walk(root, snapshot, max_bytes=3)

    assert walk.paths == ("fits",)
    assert (snapshot / "fits").read_bytes() == b"aa"
    assert not (snapshot / "too-large").exists()


def test_a_runner_root_swap_after_open_cannot_change_captured_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N2 holds the root descriptor before a runner can replace its pathname."""
    root = tmp_path / "outputs"
    root.mkdir()
    (root / "result.txt").write_text("captured\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "result.txt").write_text("attacker\n", encoding="utf-8")
    opened = channels.fswalk.open_root

    def swap_after_open(path: Path) -> int:
        descriptor = opened(path)
        root.rename(tmp_path / "original")
        root.symlink_to(outside, target_is_directory=True)
        return descriptor

    monkeypatch.setattr(channels.fswalk, "open_root", swap_after_open)
    snapshot = tmp_path / "snapshot"
    walk = _walk(root, snapshot)

    assert walk.paths == ("result.txt",)
    assert (snapshot / "result.txt").read_text(encoding="utf-8") == "captured\n"


def test_a_runner_artifact_swap_after_walk_cannot_change_the_pinned_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """N2 pins the wrapper capture, never a runner name reopened after walking."""
    import json

    from tests._supervisor import blob_at
    from tests.test_supervisor_exit import DONE_MARKER, FEATURE_FILE, Lab

    lab = Lab(tmp_path)
    lab.commit_work(FEATURE_FILE)
    lab.marker(json.dumps(DONE_MARKER))
    lab.effects(FEATURE_FILE)
    artifacts = lab.paths.artifacts(lab.activation.activation_id)
    (artifacts / "result.txt").write_text("captured\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "result.txt").write_text("attacker\n", encoding="utf-8")
    pin_outputs = lab.workspace.pin_outputs

    def swap_then_pin(activation: object, paths: tuple[str, ...]):
        artifacts.rename(tmp_path / "original-artifacts")
        artifacts.symlink_to(outside, target_is_directory=True)
        return pin_outputs(activation, paths)

    monkeypatch.setattr(lab.workspace, "pin_outputs", swap_then_pin)
    observation = lab.observe()

    outputs_ref = observation.completion.evidence.outputs_ref
    assert outputs_ref is not None
    commit = lab.git.ref_target(outputs_ref, cwd=lab.repo)
    assert commit is not None
    assert blob_at(lab.repo, commit, "result.txt") == "captured\n"


def test_walk_does_not_depend_on_creation_order(tmp_path: Path) -> None:
    """A capped listing is a function of names, not scandir order."""
    walks = []
    for name, ordered_names in (
        ("first", ("c", "a", "b")),
        ("second", ("b", "c", "a")),
    ):
        root = tmp_path / name
        root.mkdir()
        for entry in ordered_names:
            (root / entry).write_text(entry, encoding="utf-8")
        walks.append(_walk(root, tmp_path / f"{name}-snapshot", max_files=2))

    assert [(walk.paths, walk.truncated) for walk in walks] == [
        (("a", "b"), True),
        (("a", "b"), True),
    ]


def test_wide_directories_stop_at_the_first_sorted_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One overflowing directory consumes the remaining global walk budget."""
    root = tmp_path / "outputs"
    for index in range(25):
        directory = f"d{index:02}"
        target = root / directory
        target.mkdir(parents=True)
        for index in range(26):
            (target / f"f{index:02}").write_text("x", encoding="utf-8")
    (root / "later.txt").write_text("later", encoding="utf-8")

    yielded = 0
    scandir = channels.os.scandir

    @contextmanager
    def counting_scandir(path: int) -> Iterator[Iterator[os.DirEntry[str]]]:
        nonlocal yielded
        with scandir(path) as entries:

            def counted_entries() -> Iterator[os.DirEntry[str]]:
                nonlocal yielded
                for entry in entries:
                    yielded += 1
                    yield entry

            yield counted_entries()

    monkeypatch.setattr(channels.os, "scandir", counting_scandir)

    walk = _walk(root, tmp_path / "snapshot", max_walk_entries=50)

    assert walk.paths == ()
    assert _unsafe(walk) == {("d00", UnsafeKind.TOO_WIDE)}
    assert walk.truncated is True
    assert yielded <= 51


def test_wide_walk_closes_queued_directory_descriptors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The 25-sibling overflow shape leaves no held directory descriptor."""
    root = tmp_path / "outputs"
    for index in range(25):
        child = root / f"d{index:02}"
        child.mkdir(parents=True)
        for child_index in range(26):
            (child / f"f{child_index:02}").write_text("x", encoding="utf-8")
    opened: list[int] = []
    open_child = channels.fswalk.open_child_dir

    def track_child(parent_fd: int, name: str) -> int:
        descriptor = open_child(parent_fd, name)
        opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(channels.fswalk, "open_child_dir", track_child)

    walk = _walk(root, tmp_path / "snapshot", max_walk_entries=50)

    assert _unsafe(walk) == {("d00", UnsafeKind.TOO_WIDE)}
    for descriptor in opened:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def test_capture_failure_closes_the_destination_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed `/proc` reopen cannot leak the snapshot destination fd."""
    source = tmp_path / "source"
    source.write_text("x", encoding="utf-8")
    source_fd = os.open(source, os.O_RDONLY)
    opened: list[int] = []
    real_open = os.open

    def fail_reopen(path: str | bytes | os.PathLike[str], *args: object) -> int:
        if str(path).startswith("/proc/self/fd/"):
            raise OSError("injected reopen failure")
        descriptor = real_open(path, *args)  # type: ignore[arg-type]
        opened.append(descriptor)
        return descriptor

    monkeypatch.setattr(channels.os, "open", fail_reopen)
    try:
        with pytest.raises(OSError, match="injected reopen failure"):
            channels._capture_file(source_fd, tmp_path / "snapshot", 1)
    finally:
        os.close(source_fd)

    assert not (tmp_path / "snapshot").exists()
    for descriptor in opened:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def test_directory_within_walk_budget_is_listed_whole_and_sorted(
    tmp_path: Path,
) -> None:
    """All children fit before sorting, so none are dropped by enumeration."""
    root = tmp_path / "outputs"
    root.mkdir()
    for index in range(39, -1, -1):
        (root / f"f{index:02}").write_text("x", encoding="utf-8")

    walk = _walk(root, tmp_path / "snapshot", max_walk_entries=50)

    assert walk.paths == tuple(f"f{index:02}" for index in range(40))
    assert walk.truncated is False


def test_deep_nesting_is_unsafe_without_recursing(tmp_path: Path) -> None:
    """Depth exhaustion reports the boundary rather than consuming Python stack."""
    root = tmp_path / "outputs"
    root.mkdir()
    current = root
    for index in range(200):
        current /= "child"
        current.mkdir()
    (current / "last").write_text("x", encoding="utf-8")

    walk = _walk(root, tmp_path / "snapshot", max_depth=32, max_walk_entries=500)

    assert ("/".join(("child",) * 32), UnsafeKind.TOO_DEEP) in _unsafe(walk)
    assert walk.truncated is True
    assert walk.paths == ()


def test_capture_failure_is_unsafe_and_listing_continues(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One snapshot-copy failure cannot turn the whole observation into an error."""
    root = tmp_path / "outputs"
    root.mkdir()
    for name in ("a", "broken", "c"):
        (root / name).write_text(name, encoding="utf-8")
    capture = channels._capture_file

    def fail_one(source_fd: int, destination: Path, size: int) -> None:
        if destination.name == "broken":
            raise OSError("injected capture failure")
        capture(source_fd, destination, size)

    monkeypatch.setattr(channels, "_capture_file", fail_one)

    walk = _walk(root, tmp_path / "snapshot")

    assert walk.paths == ("a", "c")
    assert _unsafe(walk) == {("broken", UnsafeKind.CAPTURE_FAILED)}
