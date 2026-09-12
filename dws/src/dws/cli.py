"""The `dws` console entry point.

The command is deliberately almost empty: it reports what the distribution is
and what it is not. Subcommands arrive with the stages that implement them, so
that `dws --help` never advertises a capability that does not exist.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from dws import __version__

_DESCRIPTION = """\
DWS is a scaffold. This distribution currently provides its own package
boundary, tooling and this entry point, and nothing else.

No storage, acquisition, retrieval or service capability is implemented, and
no command here stands in for one.
"""

_EPILOG = "Run `dws --version` to report the installed version."


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level parser."""
    parser = argparse.ArgumentParser(
        prog="dws",
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="print the installed version and exit",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line. Returns the process exit code.

    With no arguments there is no work to do, so the help text is the honest
    answer; argparse still rejects anything it does not recognise with its
    usage error, exit code 2.
    """
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0
