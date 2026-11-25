#!/usr/bin/env python3
"""Check a TLA+ spec with TLC and draw its state graph as a statechart.

    statechart.py SPEC.tla [--config FILE] [--view FILE] [--out DIR]
    statechart.py install [--remove RECORD]

Exit status: 0, all rules hold; 1, at least one rule is broken; 2, the input,
TLC or the output folder failed; 128+N, signal N interrupted the run. Statuses
0 and 1 alone fill the output folder: report.md, tlc.out, graph.dot, chart.mmd
with render.json, and tlc-<rule>.out or tlc-draw*.out where they apply.
"""

from __future__ import annotations

import sys

if sys.version_info < (3, 10):  # noqa: UP036 (the gate itself)
    sys.exit("statechart needs Python 3.10 or newer; this is " + sys.version.split()[0])

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from types import FrameType

sys.dont_write_bytecode = True  # this folder ships; leave no bytecode in it

from statechart_lib import chart, install, mermaid, publish, report, tlc
from statechart_lib.graph import parse_dot
from statechart_lib.values import Decoder, ValueRefused
from statechart_lib.view import ViewError, load

JAVA_MAJOR = 11  # TLC 1.7.4 runs on Java 11 or newer
NEEDS = (
    f"TLC {install.TLC_VERSION} (tla2tools.jar) on Java {JAVA_MAJOR} or newer "
    f"(pinned: Java {install.JAVA_PIN})"
)


class Interrupted(BaseException):  # not an Exception: no view refusal swallows it
    def __init__(self, signum: int) -> None:
        super().__init__(signum)
        self.signum = signum


def find_runtime() -> tuple[str, Path]:
    """JAVA and TLA2TOOLS when set, else the per-user install, else `java`
    on PATH; stops naming the versions it needs when one is missing."""
    home = Path.home()
    java = os.environ.get("JAVA") or (
        str(install.java_path(home))
        if install.java_path(home).exists()
        else shutil.which("java")
    )
    jar = Path(os.environ.get("TLA2TOOLS") or install.jar_path(home))
    missing = [] if java else ["java"]
    if not jar.is_file():
        missing.append(str(jar))
    if missing:
        raise tlc.CheckError(
            f"missing {' and '.join(missing)}: statechart needs {NEEDS}. With the person's "
            "approval run `statechart.py install` (references/install.md), or set JAVA and "
            "TLA2TOOLS to an existing install"
        )
    assert java is not None
    banner = subprocess.run(
        [java, "-version"], capture_output=True, text=True, check=False
    ).stderr
    version = re.search(r'version "(\d+)(?:\.(\d+))?', banner)
    major = (
        0
        if not version
        else int(version[1])
        if version[1] != "1"
        else int(version[2] or 0)
    )
    if major < JAVA_MAJOR:
        raise tlc.CheckError(
            f"{java} is Java {major or 'of unknown version'}: statechart needs {NEEDS}"
        )
    return java, jar


def arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="statechart.py", description=__doc__.split("\n\n")[0]
    )
    parser.add_argument("spec", type=Path, help="the TLA+ specification (SPEC.tla)")
    parser.add_argument(
        "--config",
        type=Path,
        help="the TLC configuration (default: SPEC.cfg beside it)",
    )
    parser.add_argument(
        "--view",
        type=Path,
        help="a Python view file: the reader's words, phases, colours",
    )
    parser.add_argument(
        "--out", type=Path, help="a new or empty folder (default: SPEC-chart beside it)"
    )
    args = parser.parse_args(argv)
    args.spec = args.spec.resolve()
    if args.spec.suffix != ".tla" or not args.spec.is_file():
        parser.error(f"{args.spec} is not a .tla file")
    args.config = (args.config or args.spec.with_suffix(".cfg")).resolve()
    if not args.config.is_file():
        parser.error(f"no configuration at {args.config}: pass --config FILE")
    args.out = (args.out or args.spec.with_name(f"{args.spec.stem}-chart")).resolve()
    return args


def run(args: argparse.Namespace) -> int:
    stage = work = None
    runner: tlc.JavaRunner | None = None

    def stop(signum: int, _frame: FrameType | None) -> None:
        if runner is not None:
            runner.stop()
        raise Interrupted(signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, stop)
    try:
        config = tlc.parse_config(args.config)
        view = load(args.view)
        stage, identity = publish.prepare(args.out)
        java, jar = find_runtime()
        work = Path(tempfile.mkdtemp(prefix="statechart-"))
        runner = tlc.JavaRunner(java, jar, args.spec, config, work)
        started = time.monotonic()
        verdicts = tlc.check(config, runner)
        limit = tlc.probe_limit(time.monotonic() - started)
        decoder = Decoder()
        drawn = chart.build(
            parse_dot(verdicts.dot, decoder),
            view,
            verdicts,
            config.constrained,
            decoder,
        )
        warnings = [
            f"PROPERTY {name} has no temporal operator, so TLC tests it against the initial "
            "states alone; to test it in every reachable state, move it under INVARIANT."
            if level == "initial"
            else f"TLC neither refused PROPERTY {name} as an invariant nor checked it as one, so "
            "statechart cannot tell whether it is temporal; if it is not, TLC tests it against "
            "the initial states alone."
            for name, level in tlc.property_levels(config, runner, limit).items()
        ]
        text = report.render(
            args.spec.stem, verdicts, drawn, view.steps, config, warnings
        )
        files = {
            "report.md": text,
            "tlc.out": verdicts.first_log,
            "graph.dot": verdicts.dot,
        }
        if drawn.nodes:
            files["chart.mmd"] = mermaid.render(drawn)
            files["render.json"] = json.dumps(mermaid.limits(files["chart.mmd"])) + "\n"
        for rule, found in verdicts.broken.items():
            if found.log != verdicts.first_log:  # the path's own run, not in tlc.out
                files[f"tlc-{rule}.out"] = found.log
        files.update(verdicts.logs)
        publish.publish(stage, args.out, identity, files)
        stage = None
        print(text)
        print(f"Wrote {args.out}: {', '.join(sorted(files))}")
        return 1 if verdicts.broken else 0
    except Interrupted as interrupted:
        name = signal.Signals(interrupted.signum).name
        print(
            f"statechart: {name} stopped the check; TLC stopped, nothing was written",
            file=sys.stderr,
        )
        return 128 + interrupted.signum
    except (
        tlc.InputError,
        tlc.CheckError,
        ViewError,
        ValueRefused,
        publish.OutputError,
    ) as error:
        print(f"statechart: {error}", file=sys.stderr)
        excerpt = getattr(error, "excerpt", "")
        if excerpt:
            print(excerpt, file=sys.stderr)
        print("Nothing was written.", file=sys.stderr)
        return 2
    finally:
        publish.discard(stage, work)


def main(argv: list[str]) -> int:
    if argv[:1] == ["install"]:
        try:
            if argv[1:2] == ["--remove"] and len(argv) == 3:
                print(*install.remove(Path(argv[2])), sep="\n")
            elif len(argv) == 1:
                print(*install.install(Path.home()), sep="\n")
            else:
                raise install.InstallError("use: install, or install --remove RECORD")
        except (install.InstallError, OSError, ValueError) as error:
            print(f"statechart install: {error}", file=sys.stderr)
            return 2
        return 0
    return run(arguments(argv))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
