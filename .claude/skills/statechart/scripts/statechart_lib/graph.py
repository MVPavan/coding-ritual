"""TLC's state graph: the dot dump, its states decoded, and walks over it."""

from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field

from .values import Decoder, Frozen, Value, ValueRefused

_NODE = re.compile(r'^(-?\d+) \[label="((?:[^"\\]|\\.)*)"(,style = filled)?\]')
_EDGE = re.compile(r"^(-?\d+) -> (-?\d+) \[(.*)\];?$")
_EDGE_LABEL = re.compile(r'label="((?:[^"\\]|\\.)*)"')
_CONJUNCT = re.compile(r"^/\\ (\w+) = ", re.MULTILINE)
_SINGLE = re.compile(r"^(\w+) = ")


def parse_state(text: str, decoder: Decoder) -> Frozen:
    """One state as TLC prints it: `/\\ var = value` lines, or `var = value`
    alone when the model has one variable. Keyed by name, as TLC prints the
    variables in an order of its own."""
    text = text.strip()
    found: dict[Value, Value] = {}
    starts = list(_CONJUNCT.finditer(text))
    if not starts:
        single = _SINGLE.match(text)
        if not single:
            raise ValueRefused(f"not a state: {text[:60]!r}")
        starts_at = [(single.group(1), single.end(), len(text))]
    else:
        ends = [m.start() for m in starts[1:]] + [len(text)]
        starts_at = [(m.group(1), m.end(), end) for m, end in zip(starts, ends)]
    for name, begin, end in starts_at:
        try:
            found[name] = decoder.decode(text[begin:end].strip())
        except ValueRefused as refused:
            raise ValueRefused(f"variable {name}: {refused}") from None
    return Frozen(found)


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)", lambda m: "\n" if m.group(1) == "n" else m.group(1), text)


@dataclass
class Graph:
    """Model states by id, start ids, and steps (source, target, action).
    TLC's dashed stuttering loops are left out; an action that changes
    nothing stays as a labelled self-loop, so it counts as an exit."""

    states: dict[str, Frozen] = field(default_factory=dict)
    starts: list[str] = field(default_factory=list)
    steps: list[tuple[str, str, str]] = field(default_factory=list)
    extra: list[str] = field(default_factory=list)  # added from traces

    def find(self, state: Frozen) -> str | None:
        return {known: sid for sid, known in self.states.items()}.get(state)

    def exits(self) -> dict[str, list[tuple[str, str]]]:
        out: dict[str, list[tuple[str, str]]] = {sid: [] for sid in self.states}
        for src, dst, action in self.steps:
            out[src].append((dst, action))
        return out

    def distances(self) -> dict[str, int]:
        exits = self.exits()
        seen = {sid: 0 for sid in self.starts}
        queue = deque(self.starts)
        while queue:
            sid = queue.popleft()
            for dst, _ in exits[sid]:
                if dst not in seen:
                    seen[dst] = seen[sid] + 1
                    queue.append(dst)
        return seen


def parse_dot(text: str, decoder: Decoder) -> Graph:
    """Read `-dump dot,actionlabels`: nodes are fingerprints labelled with the
    state, the initial ones filled; edges carry the action name."""
    graph = Graph()
    for line in text.splitlines():
        node = _NODE.match(line)
        if node:
            sid = node.group(1)
            try:
                graph.states[sid] = parse_state(_unescape(node.group(2)), decoder)
            except ValueRefused as refused:
                raise ValueRefused(f"state {sid}: {refused}") from None
            if node.group(3):
                graph.starts.append(sid)
            continue
        edge = _EDGE.match(line)
        if edge and "dashed" not in edge.group(3):
            label = _EDGE_LABEL.search(edge.group(3))
            action = _unescape(label.group(1)) if label else "?"
            graph.steps.append((edge.group(1), edge.group(2), action))
    return graph
