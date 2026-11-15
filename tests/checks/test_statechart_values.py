"""statechart's value decoder: TLC's printed values, read from text the real jar
printed for our fixture specs (tests/fixtures/statechart/values/)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True  # no bytecode beside the shipped scripts
sys.path.insert(0, str(ROOT / ".claude/skills/statechart/scripts"))

from statechart_lib.graph import parse_dot, parse_state
from statechart_lib.values import (
    Decoder,
    Frozen,
    ValueRefused,
    order_key,
    show,
)

FIXTURES = ROOT / "tests/fixtures/statechart/values"
RECORDED = ROOT / "tests/fixtures/statechart/recorded"


def _shapes() -> Frozen:
    text = (FIXTURES / "Shapes.dump").read_text().split("State 1:\n", 1)[1]
    return parse_state(text, Decoder())


def test_every_printed_kind_decodes_to_the_documented_shape() -> None:
    state = _shapes()
    assert state["seqfn"] == {(1,): 7, (2, 3): 8}
    assert state["recfn"] == {Frozen({"p": 1}): "one", Frozen({"p": 2}): "two"}
    assert state["setfn"] == {frozenset({1}): "v", frozenset({1, 2}): "v"}
    assert state["onen"] == (10, 20, 30)  # a function on 1..n is a sequence
    assert state["empties"] == (frozenset(), (), ())  # `<<>>` and `<< >>`
    assert state["mixed"] == frozenset({"a", "b", "x"})
    assert state["scalars"] == (-2, True, 'q "t"', "a")
    assert state["nested"] == {
        "r": frozenset({(1, "z")}),
        "t": {"p": frozenset()},
    }


def test_values_are_hashable_and_read_only() -> None:
    state = _shapes()
    assert len({state, state}) == 1
    record = state["nested"]
    assert isinstance(record, Frozen)
    with pytest.raises(TypeError):
        record["r"] = 1


def test_one_total_order_across_kinds() -> None:
    mixed: list[object] = [
        Frozen({"a": 1}),
        frozenset({2}),
        (1,),
        "s",
        3,
        True,
    ]
    ordered = sorted(mixed, key=order_key)  # type: ignore[arg-type]
    assert ordered == [True, 3, "s", (1,), frozenset({2}), Frozen({"a": 1})]
    assert show(frozenset({"x", "a"})) == "{a, x}"
    assert show(Frozen({(1,): 7})) == "(<<1>> :> 7)"


@pytest.mark.parametrize(
    "line",
    [
        "/\\ unevaluated = Nat",
        "/\\ infinite = [n \\in Nat |-> <expression line 7, col 56>]",
        '/\\ clash = {a, "a"}',
        "/\\ bad = {TRUE, 1}",
        "/\\ dom = (TRUE :> 1 @@ 1 :> 2)",
    ],
)
def test_refused_values_name_the_variable(line: str) -> None:
    with pytest.raises(ValueRefused, match=line.split()[1]):
        parse_state(line, Decoder())


def test_refused_lines_are_the_ones_tlc_printed() -> None:
    # The jar printed these three in its error report for Refused.tla.
    printed = (FIXTURES / "Refused.out").read_text()
    for name in ("unevaluated", "infinite", "clash"):
        line = next(x for x in printed.splitlines() if x.startswith(f"/\\ {name} "))
        with pytest.raises(ValueRefused):
            parse_state(line, Decoder())


def test_single_variable_state_prints_without_conjunction() -> None:
    assert parse_state('light = "red"', Decoder()) == {"light": "red"}
    assert parse_state("n = 0", Decoder()) == {"n": 0}


def test_tlc_string_escapes_decode_to_their_characters() -> None:
    # Escapes.tla: x = "q\"b\\c\td\ne\rf\fg", as the real jar printed it.
    recorded = json.loads((RECORDED / "Escapes.json").read_text())
    graph = parse_dot(recorded["runs"][0]["dot"], Decoder())
    [state] = graph.states.values()
    assert state["x"] == 'q"b\\c\td\ne\rf\x0cg'
    with pytest.raises(ValueRefused, match="escape"):
        Decoder().decode('"a\\qb"')


def test_state_text_ending_in_tlc_blank_separator_lines() -> None:
    recorded = json.loads((RECORDED / "Counter.json").read_text())
    output = recorded["runs"][0]["output"]
    step = output.split("@!@!@STARTMSG 2217:4 @!@!@\n", 1)[1].split("@!@!@ENDMSG")[0]
    state_text = step.partition("\n")[2]
    assert state_text.endswith("\n\n")  # TLC ends each state with a blank line
    assert parse_state(state_text, Decoder()) == {"x": 0, "y": 0}


def test_fixture_files_end_without_a_blank_line() -> None:
    root = ROOT / "tests/fixtures/statechart"
    ending = [
        str(path.relative_to(root))
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.read_bytes().endswith(b"\n\n")
    ]
    assert ending == []
