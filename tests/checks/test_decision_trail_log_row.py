"""`decision-trail/scripts/log_row.py`: what its guarantees promise a trail reader."""

from __future__ import annotations

import fcntl
import subprocess
import sys
import time
from pathlib import Path

import pytest

HELPER = Path(__file__).parents[2] / ".claude/skills/decision-trail/scripts/log_row.py"
HEADER = ["ts", "phase", "decision", "why", "evidence", "result"]
CELLS = ["phase=p", "decision=d", "why=w", "evidence=e", "result=r"]
WRITERS = 12
LOCK_HOLD_SECONDS = 0.5


def log_row(*args: str | Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HELPER), *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
    )


def rows(path: Path) -> list[list[str]]:
    return [
        line.split("\t") for line in path.read_text(encoding="utf-8").split("\n")[:-1]
    ]


def test_header_is_written_once(tmp_path: Path) -> None:
    trail = tmp_path / "new" / "parent" / "t.tsv"
    assert log_row(trail, *CELLS).returncode == 0
    assert log_row(trail, *CELLS).returncode == 0
    got = rows(trail)
    assert got[0] == HEADER
    assert [row[1:] for row in got[1:]] == [["p", "d", "w", "e", "r"]] * 2


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param([*CELLS[:-1]], id="missing cell"),
        pytest.param([*CELLS, "nope=1"], id="unknown cell"),
        pytest.param([*CELLS, "phase=again"], id="repeated cell"),
        pytest.param(
            [*CELLS, "--extra", "before,after", "before=1"], id="undeclared missing"
        ),
        pytest.param(
            [*CELLS, "--extra", "Bad name", "Bad name=1"], id="malformed extra"
        ),
        pytest.param([*CELLS, "--extra", "a,a", "a=1"], id="duplicate extra"),
        pytest.param([*CELLS, "--extra", "why", "why=1"], id="colliding extra"),
        pytest.param([*CELLS, "--extra", "", "=1"], id="empty extra"),
        pytest.param([*CELLS, "--extra", "delta", "delta=1"], id="changed extra"),
    ],
)
def test_refusal_writes_nothing(tmp_path: Path, bad: list[str]) -> None:
    fresh = tmp_path / "fresh.tsv"
    if "--extra" not in bad or "delta" not in bad:
        assert log_row(fresh, *bad).returncode != 0
        assert not fresh.exists()
    trail = tmp_path / "t.tsv"
    log_row(trail, *CELLS)
    before = trail.read_bytes()
    assert log_row(trail, *bad).returncode != 0
    assert trail.read_bytes() == before


def test_hostile_whitespace_stays_on_one_line(tmp_path: Path) -> None:
    trail = tmp_path / "t.tsv"
    assert (
        log_row(
            trail, "phase=p", "decision=a\tb\nc\rd", "why=w", "evidence=e", "result=r"
        ).returncode
        == 0
    )
    got = rows(trail)
    assert len(got) == 2
    assert got[1][2] == "a b c d"


@pytest.mark.parametrize(
    ("cell", "written"),
    [
        ("=cmd()", "'=cmd()"),
        ("@sum", "'@sum"),
        ("-rf x", "'-rf x"),
        ("-12%", "-12%"),
        ("+3.5", "+3.5"),
    ],
)
def test_formula_quoted_and_signed_number_kept(
    tmp_path: Path, cell: str, written: str
) -> None:
    trail = tmp_path / "t.tsv"
    args = [*CELLS, "--extra", "delta", f"delta={cell}"]
    assert log_row(trail, *args).returncode == 0
    assert rows(trail)[1][-1] == written


def test_simultaneous_first_writers_make_one_header_and_whole_rows(
    tmp_path: Path,
) -> None:
    trail = tmp_path / "t.tsv"
    with trail.open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        procs = [
            subprocess.Popen(
                [sys.executable, str(HELPER), str(trail), *CELLS[:-1], f"result={n}"]
            )
            for n in range(WRITERS)
        ]
        time.sleep(LOCK_HOLD_SECONDS)
        assert trail.stat().st_size == 0, "a writer did not wait for the lock"
    assert [proc.wait() for proc in procs] == [0] * WRITERS
    got = rows(trail)
    assert got[0] == HEADER
    assert sorted(int(row[-1]) for row in got[1:]) == list(range(WRITERS))
    assert all(len(row) == len(HEADER) for row in got)
