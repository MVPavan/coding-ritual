"""statechart's view file: exports, answers and how often it is called."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True  # no bytecode beside the shipped scripts
sys.path.insert(0, str(ROOT / ".claude/skills/statechart/scripts"))

from statechart_lib.view import ViewError, load

from tests.checks.test_statechart_chart import draw


def _load(tmp_path: Path, source: str) -> None:
    path = tmp_path / "view.py"
    path.write_text(textwrap.dedent(source))
    load(path)


@pytest.mark.parametrize(
    ("source", "why"),
    [
        ("titel = 'x'\n", "unknown export 'titel'"),
        ("def states(v):\n    return 'x'\n", "unknown export 'states'"),
        ("state = 'x'\n", "state must be a function"),
        ("colors = {'a': 'red'}\n", "colour 'red' for 'a' is not one of blue"),
        ("colors = ['blue']\n", "colors must be a dict"),
        ("title = ' '\n", "title is empty"),
        ("raise RuntimeError('boom')\n", "RuntimeError: boom"),
    ],
)
def test_bad_exports_refused(tmp_path: Path, source: str, why: str) -> None:
    with pytest.raises(ViewError, match=why):
        _load(tmp_path, source)


def test_imports_and_private_helpers_are_allowed(tmp_path: Path) -> None:
    _load(
        tmp_path,
        """
        from __future__ import annotations
        import re
        from os.path import join

        _WORDS = {"red": "Stop"}

        def _word(v):
            return _WORDS.get(v["light"], "Go")

        def state(v):
            return _word(v)
        """,
    )


@pytest.mark.parametrize(
    ("case", "source", "why"),
    [
        (
            "Light",
            "def state(v):\n    return ''\n",
            r"state\(\) for light = red is empty",
        ),
        ("Light", "def state(v):\n    return 'a\\nb'\n", "control character"),
        ("Light", "def state(v):\n    return 3\n", "expected a string"),
        (
            "Light",
            "def state(v):\n    return 'red' if v['light'] == 'red' else ['go', v['light']]\n",
            "earlier states gave flat labels",
        ),
        (
            "Doors",
            "def state(v):\n    return {'Door': v['door']} if v['lock'] == 'locked' else {'Lock': v['lock']}\n",
            "gives regions",
        ),
        (
            "Light",
            "def state(v):\n    return ['on'] if v['light'] == 'red' else ['on', v['light']]\n",
            "is a leaf for one state and a parent",
        ),
        (
            "Light",
            "def step(action, before, after):\n    return 7\n",
            "step\\(\\) for Go",
        ),
    ],
)
def test_bad_answers_refused_naming_the_state(
    tmp_path: Path, case: str, source: str, why: str
) -> None:
    with pytest.raises(ViewError, match=why):
        draw(case, tmp_path, source)


def test_each_function_called_at_most_once_per_state_or_step(tmp_path: Path) -> None:
    source = """
        _calls = []

        def state(v):
            _calls.append(("state", v))
            return "x" if v["x"] < 2 else "y"

        def step(action, before, after):
            _calls.append(("step", action, before, after))
            return action

        def group(v):
            _calls.append(("group", v))
            return None
    """
    drawn, loaded, _, _ = draw("Counter", tmp_path, source)
    assert loaded.state_fn is not None
    calls = loaded.state_fn.__globals__["_calls"]
    assert len(calls) == len(set(calls))
    assert sum(1 for c in calls if c[0] == "state") == drawn.model_states == 16
    assert sum(1 for c in calls if c[0] == "step") == drawn.model_steps
