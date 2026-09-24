"""P1 filesystem characterization only; this is not a DWS service entrypoint."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sqlite3
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["write", "read", "hold", "contend"])
    args = parser.parse_args()
    root = Path("/state")
    if args.mode in ("hold", "contend"):
        with (root / "slot.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                if args.mode != "contend":
                    raise
                print("CONTENTION_CONFIRMED", flush=True)
                return
            if args.mode == "contend":
                raise RuntimeError("expected another container to hold the slot")
            print("LOCK_HELD", flush=True)
            time.sleep(20)
        return
    with sqlite3.connect(root / "evidence.sqlite") as db:
        mode = db.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if args.mode == "write":
            db.execute("CREATE TABLE IF NOT EXISTS evidence (value TEXT)")
            db.execute("INSERT INTO evidence VALUES ('synthetic-image-volume')")
            temporary = root / "artifact.tmp"
            with temporary.open("w") as stream:
                stream.write("synthetic-image-volume\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(root / "artifact.txt")
            descriptor = os.open(root, os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        values = db.execute("SELECT value FROM evidence").fetchall()
        assert values == [("synthetic-image-volume",)]
        assert (root / "artifact.txt").read_text() == "synthetic-image-volume\n"
        print(
            json.dumps(
                {
                    "mode": args.mode,
                    "uid": os.getuid(),
                    "gid": os.getgid(),
                    "sqlite": sqlite3.sqlite_version,
                    "journal_mode": mode,
                    "rows": values,
                    "device": root.stat().st_dev,
                }
            )
        )


if __name__ == "__main__":
    main()
