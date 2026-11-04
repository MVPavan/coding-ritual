#!/usr/bin/env python3
"""One run's card: its limits on starting new work, its closed state, its checkpoint. Calls no model and
no scheduler. Every return decision is the caller's. Exits: 0 go on. 2 refused or damaged, nothing changed.
3 limit, start nothing new (under a second left counts). 4 ignore: closed, or another run. 5 unexpected failure. Only 0 authorises work.
  open <card> --run R --deadline ISO --max-attempts N [--allow-long]   a fresh path only
  timer <card> --run R --handle H --evidence TEXT --fires-at ISO   one, at or after the deadline
  check <card> --run R        changes nothing: open and within limits?
  admit <card> --run R        immediately before one unit of work: counts it, prints seconds left
  note <card> --run R [--phase P] [--set k=v ...] [--unset k ...] [--require k,k]   merges
  close <card> --run R --reason R     stops admission; idempotent; prints the timer still to cancel
  show <card>"""

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

GO, REFUSED, LIMIT, IGNORE, FAILED = 0, 2, 3, 4, 5
MAX_SPAN = timedelta(hours=24)
TEXT = ("handle", "evidence", "fires_at", "reason")


class Stop(Exception):
    def __init__(self, code, message):
        self.code, self.message = code, message


def now():
    return (
        datetime.fromisoformat(os.environ["CARD_NOW"])
        if "CARD_NOW" in os.environ
        else datetime.now(UTC)
    )


def when(text):
    try:
        moment = datetime.fromisoformat(text)
    except (TypeError, ValueError):
        raise Stop(REFUSED, f"refused: bad time {text}")
    if moment.tzinfo is None:
        raise Stop(REFUSED, f"refused: {text} has no timezone")
    return moment


def valid(card):
    if not isinstance(card, dict) or card.get("status") not in ("open", "closed"):
        raise ValueError("bad status")
    if (
        not isinstance(card.get("run"), str)
        or not card["run"]
        or not isinstance(card.get("phase"), str)
    ):
        raise ValueError("bad run or phase")
    when(card.get("deadline")), when(card.get("started"))
    if (
        type(card.get("attempts")) is not int
        or type(card.get("max_attempts")) is not int
        or card["attempts"] < 0
        or card["max_attempts"] < 1
    ):
        raise ValueError("bad attempts")
    for key in TEXT:
        if key not in card or not (card[key] is None or isinstance(card[key], str)):
            raise ValueError(f"bad {key}")
    if not isinstance(card.get("checkpoint"), dict) or not all(
        isinstance(v, str) for v in card["checkpoint"].values()
    ):
        raise ValueError("bad checkpoint")
    if (card["status"] == "closed") != (card["reason"] is not None):
        raise ValueError("close fields do not match status")
    return card


def load(path):
    try:
        return valid(json.loads(path.read_text()))
    except (OSError, ValueError) as err:
        raise Stop(REFUSED, f"refused: damaged or missing card {path}: {err}")
    except Stop as err:
        raise Stop(REFUSED, f"refused: damaged card {path}: {err.message}")


def save(path, card):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(card, indent=1))
    os.replace(tmp, path)


def open_card(a):
    if (
        not a.run
        or not re.fullmatch(r"[A-Za-z0-9._-]{8,}", a.run)
        or a.run not in a.card.name
    ):
        raise Stop(
            REFUSED,
            "refused: a run id of 8 or more plain characters, also in the card's file name",
        )
    if (
        a.max_attempts is None
        or not a.max_attempts.isdigit()
        or int(a.max_attempts) < 1
    ):
        raise Stop(REFUSED, "refused: a card needs an attempt limit")
    if a.deadline is None:
        raise Stop(REFUSED, "refused: a card needs a deadline")
    end = when(a.deadline)
    if end <= now():
        raise Stop(REFUSED, "refused: the deadline has passed")
    if end - now() > MAX_SPAN and not a.allow_long:
        raise Stop(REFUSED, "refused: over 24 hours needs the request's own words")
    a.card.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(a.card, "x") as out:
            json.dump(
                dict(
                    status="open",
                    run=a.run,
                    deadline=a.deadline,
                    started=now().isoformat(),
                    max_attempts=int(a.max_attempts),
                    attempts=0,
                    phase="opened",
                    checkpoint={},
                    **dict.fromkeys(TEXT),
                ),
                out,
                indent=1,
            )
    except FileExistsError:
        raise Stop(
            REFUSED, "refused: every run takes a fresh card path; this one exists"
        )
    return GO, f"run={a.run}"


def command(a):
    if a.cmd == "open":
        return open_card(a)
    card = load(a.card)
    if a.cmd == "show":
        return GO, json.dumps(card)
    if a.run != card["run"]:
        return IGNORE, f"ignore: another run ({a.run}, card holds {card['run']})"
    if a.cmd == "close":
        if card["status"] == "open":
            if not a.reason:
                raise Stop(REFUSED, "refused: closing needs a reason")
            card.update(status="closed", reason=a.reason)
            save(a.card, card)
        return (
            GO,
            f"cancel={card['handle']} attempts={card['attempts']} started={card['started']}",
        )
    if card["status"] == "closed":
        return IGNORE, "ignore: run closed"
    if a.cmd == "timer":
        if not (a.handle and a.evidence and a.fires_at):
            raise Stop(REFUSED, "refused: timer needs handle, evidence and fires-at")
        if card["handle"] is not None:
            raise Stop(REFUSED, "refused: a run has one timer")
        if when(a.fires_at) < when(card["deadline"]):
            raise Stop(REFUSED, "refused: the timer must fire at or after the deadline")
        card.update(handle=a.handle, evidence=a.evidence, fires_at=a.fires_at)
        save(a.card, card)
        return GO, f"timer at {a.fires_at}"
    if a.cmd == "note":
        pairs = [p.split("=", 1) for p in a.set or []]
        if any(len(p) != 2 for p in pairs):
            raise Stop(REFUSED, "refused: note takes k=v pairs")
        merged = {
            k: v
            for k, v in {**card["checkpoint"], **dict(pairs)}.items()
            if k not in (a.unset or [])
        }
        missing = [k for k in (a.require or "").split(",") if k and k not in merged]
        if missing:
            raise Stop(REFUSED, f"refused: this phase needs {','.join(missing)}")
        card.update(phase=a.phase or card["phase"], checkpoint=merged)
        save(a.card, card)
        return GO, f"phase={card['phase']}"
    left = (when(card["deadline"]) - now()).total_seconds()
    # Under a second would print as zero, and `timeout 0` disables a command's bound.
    if left < 1:
        return LIMIT, "limit: deadline"
    if card["attempts"] >= card["max_attempts"]:
        return LIMIT, "limit: attempts"
    if a.cmd == "admit":
        card["attempts"] += 1
        save(a.card, card)
    return (
        GO,
        f"seconds_left={int(left)} attempts={card['attempts']}/{card['max_attempts']}",
    )


def main():
    top = argparse.ArgumentParser()
    top.add_argument(
        "cmd", choices=["open", "timer", "check", "admit", "note", "close", "show"]
    )
    top.add_argument("card", type=Path)
    for flag in [
        "run",
        "deadline",
        "max-attempts",
        "handle",
        "evidence",
        "fires-at",
        "phase",
        "reason",
        "require",
    ]:
        top.add_argument(f"--{flag}")
    top.add_argument("--set", action="append")
    top.add_argument("--unset", action="append")
    top.add_argument("--allow-long", action="store_true")
    a = top.parse_args()  # bad usage exits 2, refused
    try:
        code, message = command(a)
    except Stop as stop:
        code, message = stop.code, stop.message
    except Exception as err:  # noqa: BLE001 - the exit-5 boundary: any failure must authorise nothing
        code, message = FAILED, f"failed: {type(err).__name__}: {err}"
    print(message)
    return code


sys.exit(main())
