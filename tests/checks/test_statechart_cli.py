"""statechart.py as a command: exit codes, output folder, interrupts, runtime
gate and install. Replayed runs need no Java; the end-to-end tests at the
bottom run the real jar and skip, saying why, when it is absent."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".claude/skills/statechart/scripts"
sys.dont_write_bytecode = True  # no bytecode beside the shipped scripts
sys.path.insert(0, str(SCRIPTS))

from statechart_lib import install, tlc

from tests.checks.test_statechart_tlc import MODELS, Replay


def _command() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "statechart_command", SCRIPTS / "statechart.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Hooked(Replay):
    """A replay the command can stop, running `during` before each run."""

    def __init__(self, case: str, during: Callable[[], object] | None) -> None:
        super().__init__(case)
        self.during = during

    def __call__(self, request: tlc.Request) -> tlc.Result:
        if self.during:
            self.during()
        return super().__call__(request)

    def stop(self) -> None:
        pass


def replaying(
    monkeypatch: pytest.MonkeyPatch,
    case: str,
    during: Callable[[], object] | None = None,
) -> ModuleType:
    command = _command()
    monkeypatch.setattr(
        command, "find_runtime", lambda: ("java", Path("tla2tools.jar"))
    )
    monkeypatch.setattr(command.tlc, "JavaRunner", lambda *_: Hooked(case, during))
    return command


def test_exit_codes_and_files_for_hold_and_break(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command = replaying(monkeypatch, "Light")
    assert command.main([str(MODELS / "Light.tla"), "--out", str(tmp_path / "a")]) == 0
    assert sorted(p.name for p in (tmp_path / "a").iterdir()) == [
        "chart.mmd", "graph.dot", "render.json", "report.md", "tlc.out",
    ]  # fmt: skip
    assert "PROPERTY" not in (tmp_path / "a/report.md").read_text()  # temporal
    printed = capsys.readouterr().out
    assert printed.startswith("# Light\n") and f"Wrote {tmp_path / 'a'}" in printed
    command = replaying(monkeypatch, "Counter")
    assert (
        command.main([str(MODELS / "Counter.tla"), "--out", str(tmp_path / "b")]) == 1
    )
    assert (
        tmp_path / "b/tlc-SumSmall.out"
    ).is_file()  # found by a rerun, not in tlc.out
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a", "b"]


@pytest.mark.parametrize(
    ("case", "says"), [("Bad", "Bad.tla:5:20"), ("DivZero", "div is 0")]
)
def test_errors_exit_two_and_write_nothing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    case: str,
    says: str,
) -> None:
    command = replaying(monkeypatch, case)
    assert (
        command.main([str(MODELS / f"{case}.tla"), "--out", str(tmp_path / "out")]) == 2
    )
    error = capsys.readouterr().err
    assert says in error and "Nothing was written." in error
    assert list(tmp_path.iterdir()) == []


def test_state_predicate_property_is_warned_about(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    command = replaying(monkeypatch, "InitOnly")
    assert (
        command.main([str(MODELS / "InitOnly.tla"), "--out", str(tmp_path / "o")]) == 1
    )
    words = (tmp_path / "o/report.md").read_text()
    assert (
        "- PROPERTY Small has no temporal operator, so TLC tests it against the initial"
        in words
    )
    assert "PROPERTY Wrapped" not in words  # temporal through the definition it names


def test_output_folder_must_be_new_or_empty_and_unchanged(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out"
    out.mkdir()
    (out / "keep.txt").write_text("mine")
    command = replaying(monkeypatch, "Light")
    assert command.main([str(MODELS / "Light.tla"), "--out", str(out)]) == 2
    assert "choose another folder with --out" in capsys.readouterr().err
    assert [p.name for p in out.iterdir()] == ["keep.txt"]
    later = tmp_path / "later"
    command = replaying(monkeypatch, "Light", during=lambda: later.mkdir(exist_ok=True))
    assert command.main([str(MODELS / "Light.tla"), "--out", str(later)]) == 2
    assert "changed while the check ran" in capsys.readouterr().err
    assert list(later.iterdir()) == [] and sorted(
        p.name for p in tmp_path.iterdir()
    ) == ["later", "out"]


def test_defaults_derive_from_the_spec(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for suffix in (".tla", ".cfg"):
        shutil.copy(MODELS / f"Light{suffix}", tmp_path / f"Light{suffix}")
    command = replaying(monkeypatch, "Light")
    assert command.main([str(tmp_path / "Light.tla")]) == 0
    assert (tmp_path / "Light-chart/report.md").is_file()
    (tmp_path / "Light.cfg").unlink()
    with pytest.raises(SystemExit) as stopped:
        command.main([str(tmp_path / "Light.tla"), "--out", str(tmp_path / "x")])
    assert stopped.value.code == 2 and "pass --config FILE" in capsys.readouterr().err


def test_interrupt_stops_and_leaves_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    command = replaying(
        monkeypatch, "Counter", during=lambda: os.kill(os.getpid(), signal.SIGINT)
    )
    previous = signal.getsignal(signal.SIGINT)
    try:
        code = command.main(
            [str(MODELS / "Counter.tla"), "--out", str(tmp_path / "out")]
        )
    finally:
        signal.signal(signal.SIGINT, previous)
    assert code == 128 + signal.SIGINT
    assert "SIGINT stopped the check" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []  # no output, no staging folder


def test_missing_runtime_stops_naming_versions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("JAVA", "")
    monkeypatch.setenv("TLA2TOOLS", str(tmp_path / "no.jar"))
    monkeypatch.setenv("PATH", str(tmp_path))
    with pytest.raises(
        tlc.CheckError,
        match=r"missing java and .*no\.jar.*TLC 1\.7\.4.*Java 11 or newer",
    ):
        _command().find_runtime()


def test_install_pointed_installs_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("JAVA", "/opt/java")
    monkeypatch.setenv("TLA2TOOLS", "/opt/tla2tools.jar")

    def no_fetch(url: str, target: Path) -> None:
        raise AssertionError(f"fetched {url}")

    done = install.install(
        tmp_path, fetch=no_fetch, run=lambda c: f"TLC2 {install.TLC_BANNER}"
    )
    assert done[0].startswith("JAVA and TLA2TOOLS are set: nothing installed")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(
    sys.platform != "linux" or os.uname().machine != "x86_64",
    reason="pins are for Linux x86-64",
)
def test_install_stops_on_a_digest_that_is_not_the_pin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("JAVA", raising=False)
    monkeypatch.delenv("TLA2TOOLS", raising=False)

    def tampered(url: str, target: Path) -> None:
        target.write_bytes(b"not the release")

    with pytest.raises(install.InstallError, match="is not the pinned"):
        install.install(tmp_path, fetch=tampered, run=lambda c: "")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("view", "says"),
    [
        (
            "def state(v):\n    return v['missing']\n",
            "state() for light = red raised KeyError: 'missing'",
        ),
        (
            "def step(a, b, c):\n    return 1 // 0\n",
            "step() for Go from light = red raised ZeroDivisionError",
        ),
        (
            "def group(v):\n    raise ValueError('no')\n",
            "group() for light = red raised ValueError: no",
        ),
    ],
)
def test_view_function_failure_is_a_refusal_naming_the_state(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    view: str, says: str,
) -> None:  # fmt: skip
    (tmp_path / "view.py").write_text(view)
    command = replaying(monkeypatch, "Light")
    spec = str(MODELS / "Light.tla")
    out = tmp_path / "out"
    assert (
        command.main([spec, "--out", str(out), "--view", str(tmp_path / "view.py")])
        == 2
    )
    error = capsys.readouterr().err
    assert says in error and "Nothing was written." in error, error
    assert sorted(p.name for p in tmp_path.iterdir()) == ["view.py"]


def test_breaks_found_in_drawing_and_initial_runs_reach_the_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    command = replaying(monkeypatch, "AfterError")
    assert (
        command.main([str(MODELS / "AfterError.tla"), "--out", str(tmp_path / "a")])
        == 1
    )
    assert "\\div is 0" in (tmp_path / "a/tlc-draw-Small.out").read_text()
    words = (tmp_path / "a/report.md").read_text()
    assert "The drawn graph is not complete" in words
    command = replaying(monkeypatch, "InitialProperty")
    out = tmp_path / "b"
    assert command.main([str(MODELS / "InitialProperty.tla"), "--out", str(out)]) == 1
    assert "PROPERTY Small" in (out / "report.md").read_text()
    limits = json.loads((out / "render.json").read_text())
    assert limits["maxEdges"] == max(
        500, (out / "chart.mmd").read_text().count(" --> ")
    )
    command = replaying(monkeypatch, "InitialWarning")
    out = tmp_path / "c"
    assert command.main([str(MODELS / "InitialWarning.tla"), "--out", str(out)]) == 0
    words = (out / "report.md").read_text()
    assert "PROPERTY Small" in words and "PROPERTY Indented" in words
    for case in ("UnusedTemporal", "TrailingTheorem", "UnusedArgument", "TopArgument",
                 "CompactInfix", "MultilineHead", "SameLine"):  # fmt: skip
        command = replaying(monkeypatch, case)  # Small holds in real TLC
        out = tmp_path / case
        assert command.main([str(MODELS / f"{case}.tla"), "--out", str(out)]) == 0
        words = (out / "report.md").read_text()
        assert "- PROPERTY Small has no temporal operator" in words
        assert "initial states alone" in words
    command = replaying(monkeypatch, "Temporals")
    out = tmp_path / "Temporals"
    assert command.main([str(MODELS / "Temporals.tla"), "--out", str(out)]) == 0
    assert "PROPERTY" not in (out / "report.md").read_text()  # TLC: temporal


def test_replaced_empty_output_folder_is_detected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out, other = tmp_path / "out", tmp_path / "other"
    out.mkdir()

    def swap() -> None:
        if out.exists() and not other.exists():
            other.mkdir()
            out.rmdir()
            other.rename(out)

    command = replaying(monkeypatch, "Light", during=swap)
    assert command.main([str(MODELS / "Light.tla"), "--out", str(out)]) == 2
    assert "changed while the check ran" in capsys.readouterr().err
    assert list(out.iterdir()) == []


# End to end, on the real jar.

JAVA = os.environ.get("JAVA") or str(install.java_path(Path.home()))
JAR = Path(os.environ.get("TLA2TOOLS") or install.jar_path(Path.home()))
needs_tlc = pytest.mark.skipif(
    not (shutil.which(JAVA) and JAR.is_file()),
    reason=f"end-to-end: needs java ({JAVA}) and TLC's jar ({JAR}); see statechart/references/install.md",
)


def _real(
    spec: Path, out: Path, *extra: str, timeout: float = 300
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ, JAVA=JAVA, TLA2TOOLS=str(JAR), PYTHONDONTWRITEBYTECODE="1")
    command = [
        sys.executable,
        str(SCRIPTS / "statechart.py"),
        str(spec),
        "--out",
        str(out),
        *extra,
    ]
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        env=env,
        cwd=out.parent,
        timeout=timeout,
        check=False,
    )


@needs_tlc
def test_real_runs_match_the_recordings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for case, code in (
        ("Light", 0),
        ("Counter", 1),
        ("Bad", 2),
        ("Loop", 1),
        ("Quoted", 1),
    ):
        done = _real(MODELS / f"{case}.tla", tmp_path / case)
        assert done.returncode == code, done.stderr
        if code < 2:
            command = replaying(monkeypatch, case)
            assert (
                command.main(
                    [
                        str(MODELS / f"{case}.tla"),
                        "--out",
                        str(tmp_path / f"{case}-replayed"),
                    ]
                )
                == code
            )
            assert (tmp_path / case / "chart.mmd").read_text() == (
                tmp_path / f"{case}-replayed" / "chart.mmd"
            ).read_text()


@needs_tlc
def test_real_property_levels_come_from_tlc(tmp_path: Path) -> None:
    for case in ("CompactInfix", "MultilineHead", "SameLine", "Temporals"):
        done = _real(MODELS / f"{case}.tla", tmp_path / case)
        assert done.returncode == 0, done.stderr
        words = (tmp_path / case / "report.md").read_text()
        warned = "- PROPERTY Small has no temporal operator" in words
        assert warned == (case != "Temporals") and ("PROPERTY" in words) == warned


@needs_tlc
def test_real_probe_past_its_time_limit_leaves_the_check_published(
    tmp_path: Path,
) -> None:
    started = time.monotonic()
    done = _real(MODELS / "InitSlowRepeat.tla", tmp_path / "out", timeout=60)
    assert time.monotonic() - started < 60
    assert done.returncode == 0, done.stderr
    words = (tmp_path / "out/report.md").read_text()
    assert "## Rules that hold\n\n- Small\n- NoDeadlock" in words
    assert "- TLC neither refused PROPERTY Small as an invariant" in words
    running = subprocess.run(
        ["pgrep", "-f", "InitSlowRepeat"], capture_output=True, text=True, check=False
    )
    assert running.stdout == ""


@needs_tlc
def test_real_box_property_breaks_without_a_traceback(tmp_path: Path) -> None:
    for case in ("BoxFirst", "BoxLater"):
        done = _real(MODELS / f"{case}.tla", tmp_path / case)
        assert done.returncode == 1, done.stderr
        assert "Traceback" not in done.stderr
        assert "### Small" in (tmp_path / case / "report.md").read_text()


@needs_tlc
def test_real_box_property_marks_every_state_breaking_it(tmp_path: Path) -> None:
    spec = MODELS / "BoxManySolo.tla"
    done = _real(spec, tmp_path / "plain")
    assert done.returncode == 1, done.stderr
    words = (tmp_path / "plain/report.md").read_text()
    assert "- x = 2: Small\n- x = 3: Small" in words
    view = tmp_path / "view.py"
    view.write_text("def state(v):\n    return 'bad' if v['x'] >= 2 else 'good'\n")
    done = _real(spec, tmp_path / "merged", "--view", str(view))
    assert done.returncode == 1, done.stderr
    words = (tmp_path / "merged/report.md").read_text()
    assert "- `breaks`: every model state" in words and "mayBreak" not in words
    marked = [x.split()[-1] for x in (tmp_path / "merged/chart.mmd").read_text().splitlines()
              if x.strip().startswith("class ") and "onPath" not in x]  # fmt: skip
    assert marked == ["breaks"]


@needs_tlc
def test_real_sibling_module_found_from_another_folder(tmp_path: Path) -> None:
    done = _real(MODELS / "sib/UsesHelper.tla", tmp_path / "out")
    assert done.returncode == 0, done.stderr


@needs_tlc
def test_real_interrupt_kills_tlc_and_writes_nothing(tmp_path: Path) -> None:
    env = dict(os.environ, JAVA=JAVA, TLA2TOOLS=str(JAR), PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, str(SCRIPTS / "statechart.py"), str(MODELS / "Endless.tla"),
               "--out", str(tmp_path / "out")]  # fmt: skip
    process = subprocess.Popen(command, env=env, stderr=subprocess.PIPE, text=True)
    time.sleep(3)
    process.send_signal(signal.SIGTERM)
    _, err = process.communicate(timeout=60)
    assert process.returncode == 128 + signal.SIGTERM, err
    assert list(tmp_path.iterdir()) == []
    running = subprocess.run(
        ["pgrep", "-f", "Endless.tla"], capture_output=True, text=True, check=False
    )
    assert running.stdout == ""
