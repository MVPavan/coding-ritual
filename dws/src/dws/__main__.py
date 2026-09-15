"""Support `python -m dws` alongside the installed console script."""

from __future__ import annotations

from dws.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
