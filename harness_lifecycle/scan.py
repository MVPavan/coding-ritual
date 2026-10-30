#!/usr/bin/env python3
"""Capability scanner + differ for reference harnesses: thin entry.

The code lives in `curation/scan/` (stdlib only); see `curation/scan/cli.py`
for the subcommands (catalog, diff, drift).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from curation.scan.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
