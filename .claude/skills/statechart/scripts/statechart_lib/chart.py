"""Lifting TLC's state graph to a chart: the view's labels, merged arrows,
hidden steps and their rules, regions and their fidelity, marks, classes
and a stable order."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from . import tlc
from .graph import Graph, parse_state
from .values import Decoder, order_key
from .view import Label, View, ViewError, check_nesting

BUDGET = 500  # model states drawn in full; above it, only the failing paths

Node = tuple[str, ...]  # a flat label, a nested path, or (region, label)
Needs = tuple[tuple[str, tuple[str, ...]], ...]  # (other region, labels it needs)


@dataclass
class Arrow:
    source: Node
    target: Node
    labels: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)  # model states it leaves
    # regions: label text -> (the view's label, other regions' labels it needs)
    when: dict[str, tuple[str, Needs]] = field(default_factory=dict)


@dataclass
class Path:
    rule: str
    kind: str
    steps: list[tuple[str | None, str]]  # (step label, state id); None at the start
    loop_from: int | None = None  # 1-based step the loop returns to
    back_action: str | None = None
    stutters: bool = False


@dataclass
class Chart:
    form: str
    title: str | None
    regions: tuple[str, ...] = ()
    nodes: list[Node] = field(default_factory=list)
    starts: list[Node] = field(default_factory=list)
    arrows: list[Arrow] = field(default_factory=list)
    marks: dict[Node, str] = field(default_factory=dict)  # breaks / mayBreak
    rules_at: dict[Node, set[str]] = field(default_factory=dict)
    classes: dict[Node, set[str]] = field(default_factory=dict)
    paths: list[Path] = field(default_factory=list)
    texts: dict[str, str] = field(default_factory=dict)  # state id -> reader words
    hidden: dict[str, int] = field(default_factory=dict)  # hidden action -> steps
    self_loops: int = 0
    notes: list[str] = field(default_factory=list)
    together: dict[str, bool] = field(default_factory=dict)  # regions: label -> at once
    node_of: dict[str, list[Node]] = field(default_factory=dict)
    legend: dict[str, str] = field(default_factory=dict)  # phase group -> colour
    model_states: int = 0
    model_steps: int = 0
    beyond: int = 0  # failing-path states TLC's graph does not hold
    over_budget: bool = False


def _add_traces(graph: Graph, verdicts: tlc.Verdicts, decoder: Decoder) -> list[Path]:
    paths: list[Path] = []
    known = {state: sid for sid, state in graph.states.items()}
    for rule, found in verdicts.broken.items():
        trace = found.trace
        path = Path(
            rule, found.kind, [], trace.back_to, trace.back_action, trace.stutters
        )
        previous: str | None = None
        for index, step in enumerate(found.trace.steps):
            state = parse_state(step.text, decoder)
            sid = known.get(state)
            if sid is None:  # past a constraint or the bound: drawn anyway
                sid = f"t{len(graph.extra)}"
                graph.states[sid], known[state] = state, sid
                graph.extra.append(sid)
                if previous is None:
                    graph.starts.append(sid)
            new = (previous or "", sid, step.action or "")
            if previous is not None and step.action and new not in graph.steps:
                graph.steps.append(new)
            path.steps.append((step.action if index else None, sid))
            previous = sid
        paths.append(path)
    return paths


def _breaking(graph: Graph, verdicts: tlc.Verdicts, paths: list[Path], constrained: bool,
              decoder: Decoder) -> dict[str, set[str]]:  # fmt: skip
    rules: dict[str, set[str]] = defaultdict(set)
    known = {state: sid for sid, state in graph.states.items()}
    for rule, texts in verdicts.violations.items():
        for text in texts:
            sid = known.get(parse_state(text, decoder))
            if sid is not None:
                rules[sid].add(rule)
    for path in paths:
        if path.kind in ("invariant", "deadlock", "initial"):
            rules[path.steps[-1][1]].add(path.rule)
    deadlock = verdicts.deadlock_rule
    # A state that no step leaves is a deadlock only in a graph that expanded
    # every state: no constraint, no bound, no run cut short.
    complete = not constrained and verdicts.graph_partial is None
    if deadlock and deadlock in verdicts.broken and complete:
        exits = graph.exits()
        for sid in graph.states:
            if sid not in graph.extra and not exits[sid]:
                rules[sid].add(deadlock)
    return rules


def _restrict(graph: Graph, paths: list[Path]) -> Graph:
    keep = {sid for path in paths for _, sid in path.steps}
    small = Graph({sid: graph.states[sid] for sid in graph.states if sid in keep})
    small.starts = [sid for sid in graph.starts if sid in keep]
    pairs = {(a[1], b[1], b[0]) for p in paths for a, b in zip(p.steps, p.steps[1:])}
    for path in paths:
        if path.loop_from:
            back = path.steps[path.loop_from - 1][1]
            pairs |= {(path.steps[-1][1], back, s[2]) for s in graph.steps
                      if s[0] == path.steps[-1][1] and s[1] == back}  # fmt: skip
    small.steps = [s for s in graph.steps if s in pairs]
    small.extra = [sid for sid in graph.extra if sid in keep]
    return small


def _nodes_of(label: Label, regions: tuple[str, ...]) -> list[Node]:
    if regions:
        return [(region, value) for region, value in zip(regions, label)]
    return [label]


def words(label: Label, regions: tuple[str, ...] = ()) -> str:
    """A label in the reader's words, for the report."""
    if regions:
        return ", ".join(f"{r}: {v}" for r, v in zip(regions, label))
    return " > ".join(label)


def build(graph: Graph, view: View, verdicts: tlc.Verdicts, constrained: bool,
          decoder: Decoder, budget: int = BUDGET) -> Chart:  # fmt: skip
    paths = _add_traces(graph, verdicts, decoder)
    rules = _breaking(graph, verdicts, paths, constrained, decoder)
    model_states, model_steps = len(graph.states), len(graph.steps)
    over = len(graph.states) - len(graph.extra) > budget
    # Marks count every model state, drawn or not: a label of the whole graph.
    whole = {sid: view.label(sid, state) for sid, state in graph.states.items()}
    if over:
        graph = _restrict(graph, paths)
    labels = {sid: whole[sid] for sid in graph.states}
    form = view.form or "flat"
    reason = None
    if form == "nested":
        check_nesting(labels, graph.states)
    chart = _lift(graph, view, labels, form, paths, rules, whole, over)
    if form == "regions" and over:
        if chart.nodes:
            chart.notes.append("Past the drawing budget the regions show the failing paths' "
                               "steps without the conditions under which they fire; the paths "
                               "above give their order.")  # fmt: skip
    elif form == "regions":
        reason = _regions_unfaithful(graph, view, labels, chart)
        if reason:

            def nest(of: dict[str, Label]) -> dict[str, Label]:
                return {
                    sid: tuple(f"{r}: {v}" for r, v in zip(view.regions, label))
                    for sid, label in of.items()
                }

            chart = _lift(graph, view, nest(labels), "nested", paths, rules,
                          nest(whole), over)  # fmt: skip
            chart.notes.append(f"Drawn as nested states, not regions: {reason}.")
    chart.model_states, chart.model_steps = model_states, model_steps
    chart.over_budget, chart.beyond = over, len(graph.extra)
    _check_loop_exits(chart, paths)
    return chart


def _lift(graph: Graph, view: View, labels: dict[str, Label], form: str,
          paths: list[Path], rules: dict[str, set[str]], whole: dict[str, Label],
          over: bool) -> Chart:  # fmt: skip
    """`labels` are the drawn states'; `whole` every model state's, for marks.
    Past the budget a region's step gets no condition: the drawn steps alone
    would name one the model need not have."""
    regions = view.regions if form == "regions" else ()
    chart = Chart(form, view.title, regions=regions)
    on_path = {(a[1], b[1], b[0]) for p in paths for a, b in zip(p.steps, p.steps[1:])}
    loops = {p.rule: _loop_states(p) for p in paths if p.kind == "property"}
    loop_exits = {
        s
        for s in graph.steps
        for states in loops.values()
        if s[0] in states and s[1] not in states
    }
    arrows: dict[tuple[Node, Node], Arrow] = {}
    hidden_at: dict[tuple[Node, Node], set[str]] = defaultdict(set)
    shown_at: set[tuple[Node, Node]] = set()
    together: dict[str, bool] = {}
    found: dict[tuple[tuple[Node, Node], str], set[str]] = defaultdict(set)
    for step in graph.steps:
        src, dst, action = step
        label = view.step(step, graph.states[src], graph.states[dst])
        moves = _moves(labels[src], labels[dst], regions)
        if not moves:
            chart.self_loops += 1
            continue
        if label is None:
            if step in on_path or step in loop_exits:
                where = "a failing path" if step in on_path else "a loop exit"
                raise ViewError(
                    f"step() hides {action} from {words(labels[src], regions)}, which is on {where}"
                )
            chart.hidden[action] = chart.hidden.get(action, 0) + 1
            for move in moves:
                hidden_at[move].add(src)
            continue
        if form == "regions":
            together[label] = together.get(label, False) or len(moves) > 1
        for move in moves:
            shown_at.add(move)
            found[(move, label)].add(src)
    for (move, label), sources in found.items():
        needs = (
            _needs(move, sources, labels, regions)
            if form == "regions" and "[" not in label and not over
            else ()
        )
        text = label + _when(needs)
        arrow = arrows.setdefault(move, Arrow(*move))
        arrow.labels.add(text)
        arrow.sources |= sources
        arrow.when[text] = (label, needs)
    for move in hidden_at:
        if move in shown_at:
            raise ViewError(f"step() hides some steps of the arrow {' > '.join(move[0])} to "
                            f"{' > '.join(move[1])} but not all")  # fmt: skip
    chart.together = together
    nodes_of = {sid: _nodes_of(label, regions) for sid, label in labels.items()}
    chart.node_of = nodes_of
    under: dict[Node, list[str]] = defaultdict(list)
    for sid, nodes in nodes_of.items():
        for node in nodes:
            under[node].append(sid)
    distance = graph.distances()
    for path in paths:  # states only a failing path reaches
        for index, (_, sid) in enumerate(path.steps):
            distance.setdefault(sid, index)
    far = max(distance.values(), default=0) + 1
    rank = {
        node: min(distance.get(s, far) for s in sids) for node, sids in under.items()
    }
    chart.nodes = sorted(under, key=lambda n: (rank[n], order_key(n)))
    position = {node: i for i, node in enumerate(chart.nodes)}
    chart.starts = sorted(
        {n for sid in graph.starts for n in nodes_of[sid]}, key=position.__getitem__
    )
    if form == "nested":
        _parent_arrows(arrows, chart.nodes)
    chart.arrows = sorted(
        arrows.values(),
        key=lambda a: (
            position.get(a.source, -1),
            position[a.target],
            sorted(a.labels),
        ),
    )
    _check_hiding(chart, hidden_at, under)
    every: dict[Node, list[str]] = defaultdict(list)
    for sid, whole_label in whole.items():
        for node in _nodes_of(whole_label, regions):
            every[node].append(sid)
    _mark(chart, every, whole, rules, regions)
    chart.marks = {n: m for n, m in chart.marks.items() if n in under}
    chart.rules_at = {n: r for n, r in chart.rules_at.items() if n in under}
    for node, sids in under.items():
        classes = chart.classes.setdefault(node, set())
        groups = {view.group(sid, graph.states[sid]) for sid in sids}
        if len(groups) == 1:
            group = groups.pop()
            if group is not None and group in view.colors:
                classes.add(f"phase_{view.colors[group]}")
                chart.legend[group] = view.colors[group]
        for path in paths:
            states = {sid for _, sid in path.steps}
            if path.kind == "property" and set(sids) & _loop_states(path):
                classes.add("repeats")
            elif path.kind != "property" and set(sids) & states:
                classes.add("onPath")
    chart.texts = {sid: words(label, regions) for sid, label in labels.items()}
    chart.paths = paths
    return chart


def _mark(chart: Chart, under: dict[Node, list[str]], labels: dict[str, Label],
          rules: dict[str, set[str]], regions: tuple[str, ...]) -> None:  # fmt: skip
    """Over every model state, drawn or not: `breaks` when every model state
    under a chart state breaks a rule, `mayBreak` when some do. In a regions
    chart a label is marked when every combination of labels it takes part in
    can break; then each breaking combination none of whose labels is marked
    gets all its labels marked."""

    def mark(node: Node, broke: list[str]) -> None:
        every = all(rules.get(sid) for sid in under[node])
        chart.marks[node] = "breaks" if every else "mayBreak"
        chart.rules_at.setdefault(node, set()).update(*(rules[s] for s in broke))

    if not regions:
        for node, sids in under.items():
            broke = [sid for sid in sids if rules.get(sid)]
            if broke:
                mark(node, broke)
        return
    combos: dict[Label, list[str]] = defaultdict(list)
    for sid, label in labels.items():
        combos[label].append(sid)
    breaking = {c for c, sids in combos.items() if any(rules.get(s) for s in sids)}
    for node, sids in under.items():
        if {labels[sid] for sid in sids} <= breaking:
            mark(node, [sid for sid in sids if rules.get(sid)])
    whole = set(chart.marks)
    for combo in sorted(breaking, key=order_key):
        nodes = _nodes_of(combo, regions)
        if not any(node in whole for node in nodes):
            for node in nodes:
                mark(node, [sid for sid in combos[combo] if rules.get(sid)])


def _loop_states(path: Path) -> set[str]:
    start = path.loop_from - 1 if path.loop_from else len(path.steps) - 1
    return {sid for _, sid in path.steps[start:]}


def _moves(
    before: Label, after: Label, regions: tuple[str, ...]
) -> list[tuple[Node, Node]]:
    if not regions:
        return [] if before == after else [(before, after)]
    moved = zip(regions, before, after)
    return [((r, a), (r, b)) for r, a, b in moved if a != b]


def _needs(
    move: tuple[Node, Node],
    sources: set[str],
    labels: dict[str, Label],
    regions: tuple[str, ...],
) -> Needs:
    """In a regions chart, the other regions' labels a step needs: those it
    leaves from, when that is fewer than the ones beside its source label."""
    region, value = move[0]
    at = {sid: dict(zip(regions, label)) for sid, label in labels.items()}
    needs = []
    for other in regions:
        if other == region:
            continue
        beside = {lb[other] for lb in at.values() if lb[region] == value}
        taken = {at[sid][other] for sid in sources}
        if taken != beside:
            needs.append((other, tuple(sorted(taken, key=order_key))))
    return tuple(needs)


def _when(needs: Needs) -> str:
    if not needs:
        return ""
    return " [when " + ", ".join(f"{r}: {' or '.join(v)}" for r, v in needs) + "]"


def _parent_arrows(arrows: dict[tuple[Node, Node], Arrow], nodes: list[Node]) -> None:
    """Draw once from a parent a step leaving every child of it with the same
    label and target."""
    parents = sorted({n[:cut] for n in nodes for cut in range(1, len(n))}, key=len)
    for parent in parents:
        leaves = [n for n in nodes if n[: len(parent)] == parent]
        targets = {
            (a.target, text)
            for a in arrows.values()
            if a.source in leaves
            for text in a.labels
        }
        for target, text in sorted(targets):
            if target[: len(parent)] == parent:
                continue
            if all(
                text in arrows.get((leaf, target), Arrow(leaf, target)).labels
                for leaf in leaves
            ):
                merged = arrows.setdefault((parent, target), Arrow(parent, target))
                merged.labels.add(text)
                for leaf in leaves:
                    arrow = arrows[(leaf, target)]
                    arrow.labels.discard(text)
                    merged.sources |= arrow.sources
                    if not arrow.labels:
                        del arrows[(leaf, target)]


def _check_hiding(
    chart: Chart,
    hidden_at: dict[tuple[Node, Node], set[str]],
    under: dict[Node, list[str]],
) -> None:
    """Hidden steps leave every state reachable and keep an exit wherever
    the model has one."""
    if not hidden_at:
        return

    def exits(node: Node) -> set[Node]:  # arrows from the node or a parent of it
        return {a.target for a in chart.arrows if node[: len(a.source)] == a.source}

    seen, todo = set(chart.starts), list(chart.starts)
    while todo:
        for nxt in exits(todo.pop()) - seen:
            seen.add(nxt)
            todo.append(nxt)
    for node in chart.nodes:
        if node not in seen:
            raise ViewError(
                f"hidden steps leave {' > '.join(node)} unreachable from a start"
            )
    for source, _ in hidden_at:
        drawn = any(a.source == source[: len(a.source)] for a in chart.arrows)
        if not drawn:
            raise ViewError(
                f"hidden steps leave {' > '.join(source)} with no arrow out, though the model has one"
            )


def _check_loop_exits(chart: Chart, paths: list[Path]) -> None:
    for path in paths:
        if path.kind != "property":
            continue
        loop = _loop_states(path)
        loop_nodes = {n for sid in loop for n in chart.node_of.get(sid, [])}
        for arrow in chart.arrows:
            if (
                arrow.source in loop_nodes
                and arrow.target not in loop_nodes
                and not arrow.sources & loop
            ):
                raise ViewError(
                    f"the arrow from {' > '.join(arrow.source)} to {' > '.join(arrow.target)} leaves the "
                    f"looping failure of {path.rule}, but the loop cannot take it; give the loop's states "
                    "a label that shows what stops it"
                )


def _regions_unfaithful(
    graph: Graph, view: View, labels: dict[str, Label], chart: Chart
) -> str | None:
    """None when the regions chart allows exactly the model's starts and
    moves; otherwise the first difference, in words."""
    tuples = labels
    regions = view.regions
    starts = {tuples[sid] for sid in graph.starts}
    per_region = [sorted({t[i] for t in starts}) for i in range(len(regions))]
    product: set[tuple[str, ...]] = {()}
    for options in per_region:
        product = {p + (o,) for p in product for o in options}
    if product != starts:
        extra = min(product - starts)
        return f"it would start at {_tuple_words(regions, extra)}, which the model never starts at"
    model: set[tuple[tuple[str, ...], str, tuple[str, ...]]] = set()
    for step in graph.steps:
        label = view.steps.get(step)
        if label is not None and tuples[step[0]] != tuples[step[1]]:
            model.add((tuples[step[0]], label, tuples[step[1]]))
    by_label: dict[str, list[Arrow]] = defaultdict(list)
    for arrow in chart.arrows:
        for base in {base for base, _ in arrow.when.values()}:
            by_label[base].append(arrow)
    seen, todo = set(starts), list(starts)
    allowed = set()
    while todo:
        current = todo.pop()
        for text, arrows in by_label.items():
            for nxt in _chart_moves(
                current, text, arrows, regions, chart.together.get(text, False)
            ):
                allowed.add((current, text, nxt))
                if nxt not in seen:
                    seen.add(nxt)
                    todo.append(nxt)
    for move in sorted(allowed - model):
        return f"it allows {move[1]} from {_tuple_words(regions, move[0])}, which the model does not"
    for move in sorted(model - allowed):
        return f"it misses {move[1]} from {_tuple_words(regions, move[0])}, which the model allows"
    return None


def _chart_moves(at: tuple[str, ...], text: str, arrows: list[Arrow], regions: tuple[str, ...],
                 together: bool) -> list[tuple[str, ...]]:  # fmt: skip
    fire = []
    for arrow in arrows:
        index = regions.index(arrow.source[0])
        for base, needs in arrow.when.values():
            if base != text or at[index] != arrow.source[1]:
                continue
            if all(at[regions.index(r)] in values for r, values in needs):
                fire.append((index, arrow.target[1]))
    if together and fire:
        moved = list(at)
        for index, value in fire:
            moved[index] = value
        return [tuple(moved)]
    return [
        tuple(value if i == index else x for i, x in enumerate(at))
        for index, value in fire
    ]


def _tuple_words(regions: tuple[str, ...], values: tuple[str, ...]) -> str:
    return ", ".join(f"{r}: {v}" for r, v in zip(regions, values))
