"""The ruff-zero loop's sensor and controller: what they measure and what they choose."""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

LOOP = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(
        f"ruff_zero_{name}", LOOP / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sensor = load("sensor")
controller = load("controller")


def finding(root, path, code):
    return {"filename": str(root / path), "code": code}


def test_sensor_counts_findings_per_file_and_rule(tmp_path):
    findings = [
        finding(tmp_path, "b/two.py", "C408"),
        finding(tmp_path, "a/one.py", "I001"),
        finding(tmp_path, "b/two.py", "C408"),
        finding(tmp_path, "b/two.py", None),
    ]
    files, total = sensor.summarize(findings, tmp_path)
    assert files == [
        {"path": "a/one.py", "count": 1, "rules": {"I001": 1}},
        {"path": "b/two.py", "count": 3, "rules": {"C408": 2, "syntax-error": 1}},
    ]
    assert total == 4


def settings(codes, target="3.13"):
    rules = "\n".join(f"\tsome-rule ({c})," for c in codes)
    return (
        f"linter.rules.enabled = [\n{rules}\n]\n"
        f"linter.unresolved_target_version = {target}\n"
    )


def test_sensor_pin_moves_with_the_rule_set_or_target_version():
    base = sensor.ruleset(settings(["C408", "F401"]))
    assert (base["count"], base["target"]) == (2, "3.13")
    assert sensor.ruleset(settings(["F401", "C408"]))["sha"] == base["sha"]
    assert sensor.ruleset(settings(["C408"]))["sha"] != base["sha"]
    assert (
        sensor.ruleset(settings(["C408", "F401"], target="3.12"))["sha"] != base["sha"]
    )


def test_sensor_reads_real_ruff_output_in_a_repository(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("X = dict()\nY = list()\n")
    (tmp_path / "other.py").write_text("Z = dict()\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    env = {**os.environ, "RUFF": f"{sys.executable} -m ruff"}
    out = subprocess.run(
        [
            sys.executable,
            str(LOOP / "sensor.py"),
            "--root",
            str(tmp_path),
            "--roots",
            "pkg",
        ],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout
    data = json.loads(out)
    assert data["files_scanned"] == 1
    assert data["files"] == [{"path": "pkg/mod.py", "count": 2, "rules": {"C408": 2}}]
    assert data["total"] == 2


def sensed(*files):
    entries = [{"path": p, "count": n, "rules": {"C408": n}} for p, n in files]
    return {"loop": "ruff-zero", "total": sum(n for _, n in files), "files": entries}


def pick(sensor_out, notes="", tests=(), read=lambda p: ""):
    return controller.choose(
        sensor_out, controller.read_notes(notes, "ruff-zero"), list(tests), read
    )


def test_controller_picks_the_file_with_fewest_findings_then_by_path():
    code, out = pick(sensed(("z.py", 1), ("big.py", 9), ("a.py", 1)))
    assert (code, out["target"], out["selectable"]) == (0, "a.py", 3)


@pytest.mark.parametrize(
    ("notes", "expected"),
    [
        ("ruff-zero done a.py https://example.invalid/pull/1", "b.py"),
        ("ruff-zero skipped a.py needs a person", "b.py"),
        ("ruff-zero failed a.py tests fail (run 1)", "a.py"),
        ("ruff-zero failed a.py x\nruff-zero failed a.py y", "b.py"),
        ("ruff-zero done a.py url\nruff-zero reopened a.py", "a.py"),
        ("other-loop done a.py url", "a.py"),
    ],
)
def test_controller_passes_over_files_by_their_notes(notes, expected):
    code, out = pick(sensed(("a.py", 1), ("b.py", 2)), notes)
    assert (code, out["target"]) == (0, expected)


def test_controller_reports_set_point_and_nothing_selectable():
    assert pick(sensed())[0] == 3
    code, out = pick(sensed(("a.py", 1)), "ruff-zero skipped a.py why")
    assert code == 4
    assert out["excluded"] == [{"path": "a.py", "count": 1, "reason": "noted skipped"}]


def test_controller_never_picks_a_path_the_allowlist_cannot_carry():
    code, out = pick(sensed(("a b.py", 1), ("c.py", 3)))
    assert (code, out["target"]) == (0, "c.py")


def test_controller_names_the_tests_that_exercise_the_target():
    texts = {
        "tests/test_gen.py": "import generate_synthesis\n",
        "tests/test_other.py": "import synthesis_tools\n",
        "tests/test_self.py": "",
    }
    _, out = pick(
        sensed(("tools/generate_synthesis.py", 1)), tests=texts, read=texts.__getitem__
    )
    assert out["tests"] == ["tests/test_gen.py"]
    _, out = pick(
        sensed(("tests/test_self.py", 1)), tests=texts, read=texts.__getitem__
    )
    assert out["tests"] == ["tests/test_self.py"]
