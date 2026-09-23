"""DWS — an engine-only distribution that currently contains no product capability.

This package exists to fix the ownership boundary and the tooling around it.
Everything else in the DWS design is unimplemented.
"""

from __future__ import annotations

from importlib.metadata import version

__all__ = ["__version__"]

__version__ = version("dws")
