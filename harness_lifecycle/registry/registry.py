#!/usr/bin/env python3
"""Skill + capability registry: thin entry.

The code lives in `curation/registry/`; see `curation/registry/cli.py` and
README.md §6 for the commands (gap, ours, round, record, build, check).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from curation.registry.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
