"""`wake/scripts/run_card.py`: what its exit codes and card promise a calling playbook."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HELPER = Path(__file__).parents[2] / ".claude/skills/wake/scripts/run_card.py"
RUN = "climb-20261103T220000Z"
NIGHT = "2026-11-03T22:00:00+00:00"
DEADLINE = "2026-11-04T06:00:00+00:00"


def card_cmd(
    cmd: str, card: Path, *args: str, at: str = NIGHT
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HELPER), cmd, str(card), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "CARD_NOW": at},
    )


def opened(tmp_path: Path, attempts: str = "2") -> Path:
    card = tmp_path / f"{RUN}.json"
    done = card_cmd(
        "open", card, "--run", RUN, "--deadline", DEADLINE, "--max-attempts", attempts
    )
    assert done.returncode == 0, done.stdout
    return card


def read(card: Path) -> dict:
    return json.loads(card.read_text())


def test_refused_open_leaves_no_card_and_an_existing_path_stays_untouched(
    tmp_path: Path,
) -> None:
    card = tmp_path / f"{RUN}.json"
    assert card_cmd("open", card, "--run", RUN, "--max-attempts", "1").returncode == 2
    assert card_cmd("open", card, "--run", RUN, "--deadline", DEADLINE).returncode == 2
    assert not card.exists()
    opened(tmp_path)
    before = card.read_bytes()
    assert (
        card_cmd(
            "open", card, "--run", RUN, "--deadline", DEADLINE, "--max-attempts", "1"
        ).returncode
        == 2
    )
    assert card.read_bytes() == before


def test_only_admit_consumes_and_a_limit_stops_starting(tmp_path: Path) -> None:
    card = opened(tmp_path)
    assert card_cmd("check", card, "--run", RUN).returncode == 0
    assert card_cmd("admit", card, "--run", RUN, at=DEADLINE).returncode == 3
    assert read(card)["attempts"] == 0
    assert card_cmd("admit", card, "--run", RUN).returncode == 0
    assert card_cmd("admit", card, "--run", RUN).returncode == 0
    assert card_cmd("admit", card, "--run", RUN).returncode == 3
    assert read(card)["attempts"] == 2


def test_under_a_second_left_is_a_limit_so_no_command_gets_a_zero_lifetime(
    tmp_path: Path,
) -> None:
    card = opened(tmp_path)
    near = "2026-11-04T05:59:59.750000+00:00"
    assert card_cmd("check", card, "--run", RUN, at=near).returncode == 3
    assert card_cmd("admit", card, "--run", RUN, at=near).returncode == 3
    assert read(card)["attempts"] == 0
    assert card_cmd(
        "admit", card, "--run", RUN, at="2026-11-04T05:59:59+00:00"
    ).stdout.startswith("seconds_left=1 ")


def test_closed_or_another_run_authorises_nothing_and_close_names_the_timer(
    tmp_path: Path,
) -> None:
    card = opened(tmp_path)
    assert (
        card_cmd(
            "timer",
            card,
            "--run",
            RUN,
            "--handle",
            "h1",
            "--evidence",
            "e",
            "--fires-at",
            DEADLINE,
        ).returncode
        == 0
    )
    assert card_cmd("admit", card, "--run", "another-run-id").returncode == 4
    assert card_cmd("close", card, "--run", RUN, "--reason", "met").stdout.startswith(
        "cancel=h1"
    )
    assert card_cmd("check", card, "--run", RUN).returncode == 4
    assert card_cmd("close", card, "--run", RUN, "--reason", "other").returncode == 0
    assert read(card)["reason"] == "met"


def test_one_timer_never_before_the_deadline(tmp_path: Path) -> None:
    card = opened(tmp_path)
    timer = ("--run", RUN, "--handle", "h1", "--evidence", "e", "--fires-at")
    assert card_cmd("timer", card, *timer, "2026-11-04T05:59:00+00:00").returncode == 2
    assert card_cmd("timer", card, *timer, "2026-11-04T06:01:00+00:00").returncode == 0
    assert card_cmd("timer", card, *timer, "2026-11-04T06:02:00+00:00").returncode == 2


def test_note_merges_and_refuses_a_missing_required_field(tmp_path: Path) -> None:
    card = opened(tmp_path)
    assert (
        card_cmd(
            "note", card, "--run", RUN, "--set", "row=0", "--set", "tree=t"
        ).returncode
        == 0
    )
    assert (
        card_cmd(
            "note", card, "--run", RUN, "--unset", "row", "--require", "row,tree"
        ).returncode
        == 2
    )
    assert read(card)["checkpoint"] == {"row": "0", "tree": "t"}
    assert (
        card_cmd(
            "note", card, "--run", RUN, "--set", "tree=u", "--phase", "climbing"
        ).returncode
        == 0
    )
    assert (read(card)["checkpoint"], read(card)["phase"]) == (
        {"row": "0", "tree": "u"},
        "climbing",
    )


def test_a_damaged_card_refuses(tmp_path: Path) -> None:
    card = opened(tmp_path)
    card.write_text(json.dumps({**read(card), "attempts": "1"}))
    assert card_cmd("admit", card, "--run", RUN).returncode == 2
