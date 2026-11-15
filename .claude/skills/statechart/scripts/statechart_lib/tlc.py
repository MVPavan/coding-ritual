"""Running TLC: the configuration, pinned runs, tool-mode messages, traces,
and the loop that gives every rule its own verdict."""

from __future__ import annotations

import os
import re
import signal
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from itertools import chain, count
from pathlib import Path

BOUND = 100_000  # distinct states for each run after the first break
BOUND_OP = "StatechartWithinBound"
BOUND_MODULE = "StatechartBound"
JAVA_OPTIONS = ("-XX:+UseParallelGC",)
# One worker and a fixed fingerprint polynomial and seed: the same graph and
# the shortest trace on every run; liveness checked once, at the end.
TLC_OPTIONS = ("-tool", "-workers", "1", "-fp", "0", "-seed", "0", "-lncheck", "final")
EXCERPT_LINES = 40
# A property-level probe stops after PROBE_SECONDS, or sooner: the check's own
# time plus PROBE_MARGIN, since a probe should cost no more than one TLC start.
PROBE_SECONDS = 10.0
PROBE_MARGIN = 3.0

_RULE_SECTIONS = {"INVARIANT", "INVARIANTS", "PROPERTY", "PROPERTIES"}
_KEYWORDS = _RULE_SECTIONS | {
    "CONSTANT", "CONSTANTS", "INIT", "NEXT", "SPECIFICATION", "CONSTRAINT",
    "CONSTRAINTS", "ACTION_CONSTRAINT", "ACTION_CONSTRAINTS", "SYMMETRY", "VIEW",
    "CHECK_DEADLOCK", "POSTCONDITION", "ALIAS",
}  # fmt: skip
_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class InputError(Exception):
    """The specification or configuration is invalid; names file and line."""


class CheckError(Exception):
    """TLC stopped without a verdict; carries its own error text, cut short."""

    def __init__(self, message: str, excerpt: str = "") -> None:
        super().__init__(message)
        self.excerpt = excerpt


@dataclass(frozen=True)
class Config:
    path: Path
    invariants: tuple[str, ...]
    properties: tuple[str, ...]
    check_deadlock: bool
    constrained: bool  # CONSTRAINT or ACTION_CONSTRAINT
    representative: bool  # VIEW or SYMMETRY
    kept: str  # the text without rule sections and CHECK_DEADLOCK


def _lex(text: str) -> list[tuple[str, int, int]]:
    """Comments and strings as (kind, start, end), in TLA+'s and TLC's
    shared lexical rules: `(* *)` nests, `\\*` runs to the line end, and a
    backslash inside a string takes the next character with it. ValueError
    with the offset of a comment or string left open."""
    found: list[tuple[str, int, int]] = []
    at, size = 0, len(text)
    while at < size:
        if text.startswith("(*", at):
            depth, end = 1, at + 2
            while end < size and depth:
                step = text[end : end + 2]
                depth += {"(*": 1, "*)": -1}.get(step, 0)
                end += 2 if step in ("(*", "*)") else 1
            if depth:
                raise ValueError(at)
            found.append(("comment", at, end))
        elif text.startswith("\\*", at):
            end = text.find("\n", at)
            end = size if end < 0 else end
            found.append(("comment", at, end))
        elif text[at] == '"':
            end = at + 1
            while end < size and text[end] not in '"\n':
                end += 2 if text[end] == "\\" else 1
            if end >= size or text[end] != '"':
                raise ValueError(at)
            end += 1
            found.append(("string", at, end))
        else:
            at += 1
            continue
        at = end
    return found


def _blank(text: str) -> str:
    """The text with comments and string contents turned to spaces, lines kept."""
    out = list(text)
    for kind, start, end in _lex(text):
        first = start + 1 if kind == "string" else start
        last = end - 1 if kind == "string" else end
        for index in range(first, last):
            if out[index] != "\n":
                out[index] = " "
    return "".join(out)


def _config_tokens(path: Path, text: str) -> list[tuple[str, int, int]]:
    """(token, offset, line): words, whole strings and single characters,
    with comments skipped, so a keyword counts only outside strings."""
    try:
        spans = {start: end for kind, start, end in _lex(text) if kind == "string"}
        blank = _blank(text)
    except ValueError as error:
        line = text.count("\n", 0, error.args[0]) + 1
        raise InputError(
            f"{path}:{line}: a comment or string is never closed"
        ) from None
    tokens: list[tuple[str, int, int]] = []
    at = 0
    while at < len(text):
        if at in spans:
            end = spans[at]
        elif blank[at].isspace():
            at += 1
            continue
        else:
            word = _WORD.match(blank, at)
            end = word.end() if word else at + 1
        tokens.append((text[at:end], at, text.count("\n", 0, at) + 1))
        at = end
    return tokens


def parse_config(path: Path) -> Config:
    """Read a TLC configuration, refusing what it cannot use with file:line."""
    text = path.read_text()
    sections: list[tuple[str, int, int, list[tuple[str, int]]]] = []
    for token, start, line in _config_tokens(path, text):
        if token in _KEYWORDS:
            sections.append((token, start, line, []))
        elif not sections:
            raise InputError(f"{path}:{line}: expected a keyword, found {token!r}")
        else:
            sections[-1][3].append((token, line))
    invariants: list[str] = []
    properties: list[str] = []
    deadlock = True
    kept: list[str] = []
    for index, (word, start, line, body) in enumerate(sections):
        end = sections[index + 1][1] if index + 1 < len(sections) else len(text)
        if word == "ALIAS":
            raise InputError(
                f"{path}:{line}: ALIAS changes how TLC prints states, "
                "which the chart reads; remove it"
            )
        if word in _RULE_SECTIONS:
            for name, at in body:
                if not _NAME.match(name):
                    raise InputError(f"{path}:{at}: {name!r} is not a rule name")
            names = [name for name, _ in body]
            (invariants if word.startswith("INV") else properties).extend(names)
        elif word == "CHECK_DEADLOCK":
            if [t for t, _ in body] not in (["TRUE"], ["FALSE"]):
                raise InputError(f"{path}:{line}: CHECK_DEADLOCK takes TRUE or FALSE")
            deadlock = body[0][0] == "TRUE"
        else:
            if not body and word not in ("SYMMETRY", "VIEW"):
                raise InputError(f"{path}:{line}: {word} names nothing")
            kept.append(text[start:end])
    words = {word for word, _, _, _ in sections}
    return Config(
        path=path,
        invariants=tuple(dict.fromkeys(invariants)),
        properties=tuple(dict.fromkeys(properties)),
        check_deadlock=deadlock,
        constrained=bool(words & {"CONSTRAINT", "CONSTRAINTS", "ACTION_CONSTRAINT",
                                  "ACTION_CONSTRAINTS"}),
        representative=bool(words & {"VIEW", "SYMMETRY"}),
        kept="".join(kept),
    )  # fmt: skip


@dataclass(frozen=True)
class Request:
    """One TLC run: which rules it checks and how."""

    invariants: tuple[str, ...]
    properties: tuple[str, ...]
    deadlock: bool
    keep_going: bool = False  # -continue: every invariant violation, for marks
    bounded: bool = False
    as_written: bool = False  # the configuration file unchanged
    probe: bool = False  # bounded at 0 distinct states: TLC explores no state
    timeout: float | None = None  # seconds; past it the run is killed

    def describe(self) -> dict[str, object]:
        described: dict[str, object] = {
            "invariants": list(self.invariants),
            "properties": list(self.properties),
            "deadlock": self.deadlock,
            "keep_going": self.keep_going,
            "bounded": self.bounded,
            "as_written": self.as_written,
        }
        return described | ({"probe": True} if self.probe else {})


@dataclass(frozen=True)
class Result:
    code: int
    output: str
    dot: str


Runner = Callable[[Request], Result]


class JavaRunner:
    """Runs TLC as a child `java` in its own process group, so an interrupt
    can stop the whole group; every run gets a fresh folder under `work`."""

    def __init__(
        self, java: str, jar: Path, spec: Path, config: Config, work: Path,
        bound: int = BOUND,
    ) -> None:  # fmt: skip
        self.java, self.jar, self.spec, self.config = java, jar, spec, config
        self.work, self.bound, self.count = work, bound, 0
        self.process: subprocess.Popen[str] | None = None

    def rules_text(self, request: Request) -> str:
        text = self.config.kept.rstrip() + "\n"
        if request.invariants:
            text += "INVARIANTS " + " ".join(request.invariants) + "\n"
        if request.properties:
            text += "PROPERTIES " + " ".join(request.properties) + "\n"
        text += f"CHECK_DEADLOCK {'TRUE' if request.deadlock else 'FALSE'}\n"
        if request.bounded:
            text += f"CONSTRAINT {BOUND_OP}\n"
        return text

    def command(self, request: Request, folder: Path) -> list[str]:
        """The java command for one run, writing its configuration and, for a
        bounded run, the module that adds the bound, into `folder`."""
        module, config = self.spec, self.config.path
        if not request.as_written:
            config = folder / "rules.cfg"
            config.write_text(self.rules_text(request))
        if request.bounded:
            module = folder / f"{BOUND_MODULE}.tla"
            module.write_text(
                f"---- MODULE {BOUND_MODULE} ----\nEXTENDS {self.spec.stem}, Naturals, TLC\n"
                f'{BOUND_OP} == TLCGet("distinct") < {0 if request.probe else self.bound}\n'
                "====\n"
            )
        command = [
            self.java, *JAVA_OPTIONS, f"-DTLA-Library={self.spec.parent}",
            "-cp", str(self.jar), "tlc2.TLC", *TLC_OPTIONS,
            "-metadir", str(folder / "states"), "-config", str(config),
            "-dump", "dot,actionlabels", str(folder / "graph.dot"),
        ]  # fmt: skip
        if request.keep_going:
            command.append("-continue")
        if not request.as_written and not request.deadlock:
            command.append("-deadlock")
        return [*command, str(module)]

    def __call__(self, request: Request) -> Result:
        self.count += 1
        folder = self.work / f"run-{self.count}"
        folder.mkdir(parents=True)
        self.process = subprocess.Popen(
            self.command(request, folder), cwd=folder, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, start_new_session=True,
        )  # fmt: skip
        try:
            output, _ = self.process.communicate(timeout=request.timeout)
        except subprocess.TimeoutExpired:
            self.stop()
            output, _ = self.process.communicate()  # reaps it
        code = self.process.returncode
        self.process = None
        dot = folder / "graph.dot"
        return Result(code, output, dot.read_text() if dot.exists() else "")

    def stop(self) -> None:
        if self.process is not None and self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


@dataclass(frozen=True)
class Message:
    code: int  # -1 for text TLC printed outside any message (SANY's)
    severity: int
    text: str


def messages(output: str) -> list[Message]:
    found: list[Message] = []
    current: tuple[int, int, list[str]] | None = None
    loose: list[str] = []
    for line in output.splitlines():
        start = re.match(r"@!@!@STARTMSG (\d+):(\d+) @!@!@$", line)
        if start:
            if loose and any(x.strip() for x in loose):
                found.append(Message(-1, 0, "\n".join(loose)))
            loose = []
            current = (int(start.group(1)), int(start.group(2)), [])
        elif re.match(r"@!@!@ENDMSG \d+ @!@!@$", line):
            if current:
                found.append(Message(current[0], current[1], "\n".join(current[2])))
            current = None
        elif current:
            current[2].append(line)
        else:
            loose.append(line)
    if loose and any(x.strip() for x in loose):
        found.append(Message(-1, 0, "\n".join(loose)))
    return found


@dataclass(frozen=True)
class Step:
    action: str | None  # None for an initial state
    text: str


@dataclass
class Trace:
    steps: list[Step]
    back_to: int | None = None  # 1-based step a liveness loop returns to
    back_action: str | None = None
    stutters: bool = False  # a liveness counterexample that ends by stuttering


_STEP_HEAD = re.compile(r"^(\d+): <(.*?)(?: line \d+, col \d+ to line \d+, col \d+ of module \w+)?>$")  # fmt: skip


def _trace(found: list[Message], start: int) -> Trace:
    trace = Trace([])
    for message in found[start:]:
        if message.code in (2121, 2264):
            continue
        if message.code == 2217:
            head, _, state = message.text.partition("\n")
            match = _STEP_HEAD.match(head)
            action = match.group(2) if match else None
            trace.steps.append(
                Step(None if action == "Initial predicate" else action, state)
            )
        elif message.code == 2122:
            back = re.match(r"^(\d+): Back to state: <(\w+)", message.text)
            if back:
                trace.back_to, trace.back_action = int(back.group(1)), back.group(2)
        elif message.code == 2218:
            trace.stutters = True
        else:
            break
    return trace


@dataclass
class Outcome:
    kind: str  # holds, invariant, deadlock, property, input, unnamed, error
    rule: str | None = None
    trace: Trace | None = None
    distinct: int = 0
    generated: int = 0
    violations: dict[str, list[str]] = field(default_factory=dict)
    unprinted: dict[str, int] = field(default_factory=dict)  # breaks, no path printed
    excerpt: str = ""
    empty: str | None = None  # a completed run that explored no state, and why


def _excerpt(lines: list[str]) -> str:
    kept = [x for x in lines if x.strip()]
    if len(kept) > EXCERPT_LINES:
        kept = kept[:EXCERPT_LINES] + [f"... ({len(kept) - EXCERPT_LINES} more lines)"]
    return "\n".join(kept)


def judge(result: Result, request: Request) -> Outcome:
    found = messages(result.output)
    outcome = Outcome("holds")
    for message in found:
        counts = re.match(r"(\d+) states generated, (\d+) distinct", message.text)
        if message.code == 2199 and counts:
            outcome.generated, outcome.distinct = int(counts[1]), int(counts[2])
    # TLC's error text, without the breaks decoded below and their traces.
    skip = (2107, 2108, 2110, 2114, 2116, 2121, 2264)
    errors = [m for m in found if m.severity == 1 and m.code not in skip]
    outcome.excerpt = _excerpt([line for m in errors for line in m.text.splitlines()])
    for index, message in enumerate(found):
        named = re.match(r"Invariant (\w+) is violated", message.text)
        at_start = re.match(
            r"Property (\w+) is violated by the initial state", message.text
        )
        if message.code in (2107, 2110) and named:
            if message.code == 2107:
                state = message.text.partition("\n")[2]
                trace = Trace([Step(None, state)])
            else:
                trace = _trace(found, index + 1)
            if trace.steps:
                outcome.violations.setdefault(named[1], []).append(trace.steps[-1].text)
            else:  # TLC failed while printing the path: counted, no state invented
                outcome.unprinted[named[1]] = outcome.unprinted.get(named[1], 0) + 1
            if outcome.rule is None:
                outcome.kind, outcome.rule, outcome.trace = "invariant", named[1], trace
        elif message.code == 2108 and at_start and outcome.rule is None:
            trace = Trace([Step(None, message.text.partition("\n")[2])])
            outcome.kind, outcome.rule, outcome.trace = "initial", at_start[1], trace
        elif message.code == 2114 and outcome.rule is None:
            outcome.kind, outcome.trace = "deadlock", _trace(found, index + 1)
        elif message.code == 2116 and outcome.rule is None:
            outcome.kind, outcome.trace = "property", _trace(found, index + 1)
            if len(request.properties) == 1:
                outcome.rule = request.properties[0]
    expected = {"invariant": 12, "deadlock": 11, "property": 13, "initial": 13}.get(
        outcome.kind
    )
    if request.keep_going and result.code == 0:
        outcome.kind, outcome.rule, outcome.trace = "holds", None, None
    elif result.code in (150, 151):
        outcome.kind = "input"
    elif (
        result.code == 0
        and outcome.kind == "holds"
        or expected is not None
        and result.code == expected
    ):
        pass
    elif result.code in (11, 12, 13, 14):
        tail = result.output.splitlines()[-EXCERPT_LINES:]
        outcome.kind, outcome.rule, outcome.excerpt = "unnamed", None, "\n".join(tail)
    else:
        outcome.kind, outcome.rule = "error", None
    completed = any(m.code == 2193 for m in found)  # "No error has been found."
    if result.code == 0 and completed and outcome.distinct == 0:
        outcome.empty = (
            "every initial state lies outside the constraints"
            if outcome.generated else "no state satisfies the initial condition"
        )  # fmt: skip
    return outcome


@dataclass(frozen=True)
class Break:
    rule: str
    kind: str  # invariant, deadlock, property, initial (a property an initial state breaks)
    trace: Trace
    log: str  # TLC's output from the run that reported this break


@dataclass
class Verdicts:
    holds: list[str] = field(default_factory=list)
    broken: dict[str, Break] = field(default_factory=dict)
    unchecked: dict[str, str] = field(default_factory=dict)
    deadlock_rule: str | None = None
    first_log: str = ""
    dot: str = ""
    violations: dict[str, list[str]] = field(default_factory=dict)
    unprinted: dict[str, int] = field(default_factory=dict)  # breaks no mark can show
    marks_partial: dict[str, str] = field(default_factory=dict)  # rule: why it stopped
    distinct: int = 0
    generated: int = 0
    empty: str | None = None  # why no state was explored
    graph_partial: str | None = None  # why the drawn graph is not complete
    graph_from: str = "the first run"  # the run the drawn graph comes from
    logs: dict[str, str] = field(default_factory=dict)  # failed drawing runs' output


def _input_error(result: Result, outcome: Outcome, config: Config) -> InputError:
    text = "\n".join(
        m.text for m in messages(result.output) if m.code in (-1, 2229, 2230)
    )
    where = re.search(
        r"line (\d+), col(?:umn)? (\d+)(?: to line \d+, col \d+ of module (\w+))?", text
    )
    module = re.search(r"(?:In module|parse module) (\w+)", text)
    if where:
        name = where[3] or (module[1] if module else config.path.stem)
        place = f"{name}.tla:{where[1]}:{where[2]}"
    else:
        place = str(config.path)
        named = re.search(r"(?:invariant|property) (?:of )?(\w+)", text, re.IGNORECASE)
        if named:
            for number, line in enumerate(config.path.read_text().splitlines(), 1):
                if re.search(rf"\b{re.escape(named[1])}\b", line):
                    place = f"{config.path}:{number}"
                    break
    return InputError(
        f"{place}: TLC refused the input\n{outcome.excerpt or _excerpt(text.splitlines())}"
    )


def deadlock_name(config: Config) -> str:
    """The deadlock rule's name: the first of NoDeadlock, CheckDeadlock,
    NoDeadlock2, NoDeadlock3, ... that no configured rule has."""
    rules = set(config.invariants) | set(config.properties)
    names = chain(("NoDeadlock", "CheckDeadlock"), (f"NoDeadlock{n}" for n in count(2)))
    return next(name for name in names if name not in rules)


def check(config: Config, runner: Runner, bound: int = BOUND) -> Verdicts:
    """Check every rule once: run the configuration as written; on a break,
    drop the rule and rerun, bounded, until no remaining rule breaks; give
    each temporal property not yet decided a run of its own; then draw from
    a run that explored every state it could."""
    name = deadlock_name(config)
    verdicts = Verdicts(deadlock_rule=name if config.check_deadlock else None)
    at_bound = f"the run stopped at the bound of {bound:,} distinct states"
    invariants, properties = list(config.invariants), list(config.properties)
    deadlock = config.check_deadlock
    first_request = Request(
        tuple(invariants), tuple(properties), deadlock, as_written=True
    )
    first = runner(first_request)
    outcome = judge(first, first_request)
    verdicts.first_log = first.output
    if outcome.kind == "input":
        raise _input_error(first, outcome, config)
    if outcome.kind in ("unnamed", "error"):
        unchecked = invariants + properties + ([name] if deadlock else [])
        why = (
            "TLC stopped without naming a broken rule"
            if outcome.kind == "unnamed"
            else "TLC stopped on an error"
        )
        raise CheckError(
            f"{why}; unchecked: {', '.join(unchecked) or 'none'}", outcome.excerpt
        )

    whole = False  # the drawn graph's run expanded every state it found

    def draw_from(result: Result, found: Outcome, run: str, why: str | None) -> None:
        nonlocal whole
        verdicts.dot, verdicts.distinct = result.dot, found.distinct
        verdicts.generated, verdicts.empty = found.generated, found.empty
        verdicts.graph_from, verdicts.graph_partial = run, why
        whole = why is None

    def stopped(found: Outcome, run: str) -> str:
        return f"{run} stopped on an error: " + (found.excerpt.splitlines() or ["?"])[
            0
        ].rstrip(".")

    draw_from(first, outcome, "the first run", None)
    # A run that stopped at a break did not expand every state it found.
    complete = whole = outcome.kind in ("holds", "property")
    if outcome.kind == "holds":
        verdicts.holds = invariants + properties + ([name] if deadlock else [])
        return verdicts

    def rerun(request: Request) -> tuple[Result, Outcome]:
        result = runner(request)
        found = judge(result, request)
        if found.kind == "input":  # the rules or bound this tool wrote: never hide it
            raise CheckError(
                "TLC refused a rerun's own configuration or bound module", found.excerpt
            )
        return result, found

    def record(found: Outcome, result: Result) -> None:
        assert found.trace is not None
        rule = found.rule or name
        verdicts.broken[rule] = Break(rule, found.kind, found.trace, result.output)

    if outcome.kind == "property":
        # Liveness is checked at the end, after every state was explored, so
        # the safety rules held in this run.
        verdicts.holds += invariants + ([name] if deadlock else [])
        invariants, deadlock = [], False
        if outcome.rule:
            record(outcome, first)
            properties.remove(outcome.rule)
    else:
        record(outcome, first)
        if outcome.kind == "deadlock":
            deadlock = False
        # TLC checks the P of a PROPERTY []P as an invariant: "Invariant P is
        # violated" can name a property.
        for rules in (invariants, properties):
            if outcome.rule in rules:
                rules.remove(outcome.rule)
        while invariants or deadlock:
            request = Request(tuple(invariants), (), deadlock, bounded=True)
            result, found = rerun(request)
            pending = invariants + ([name] if deadlock else [])
            partial: str | None = None  # why this run's graph is not complete
            if found.kind == "holds" and found.distinct < bound:
                verdicts.holds += pending
                complete = True
            elif found.kind == "holds":
                partial = at_bound
                verdicts.unchecked.update(dict.fromkeys(pending, at_bound))
            elif found.kind in ("invariant", "deadlock"):
                record(found, result)
                if found.kind == "invariant":
                    invariants.remove(str(found.rule))
                else:
                    deadlock = False
                continue
            else:
                partial = stopped(found, "the run")
                verdicts.unchecked.update(dict.fromkeys(pending, partial))
            draw_from(result, found, "the rerun of the remaining rules", partial)
            break
    for prop in properties:
        request = Request((), (prop,), False, bounded=True)
        result, found = rerun(request)
        if found.distinct >= bound:
            verdicts.unchecked[prop] = at_bound
        elif found.kind == "holds":
            verdicts.holds.append(prop)
        elif found.kind in ("property", "initial", "invariant"):
            record(found, result)
        else:
            verdicts.unchecked[prop] = stopped(found, "the run")
    # TLC names one broken invariant per state, so each broken invariant gets
    # a run of its own that keeps going past every state breaking it. A
    # PROPERTY []P that TLC reported as an invariant stays a PROPERTY there:
    # TLC refuses a temporal formula as an INVARIANT.
    drawing = [r for r, b in verdicts.broken.items() if b.kind == "invariant"]
    for rule in drawing:
        invariant = rule in config.invariants
        request = Request((rule,) if invariant else (), () if invariant else (rule,),
                          False, keep_going=True, bounded=True)  # fmt: skip
        result, found = rerun(request)
        verdicts.violations[rule] = found.violations.get(rule, [])
        if found.unprinted.get(rule):
            verdicts.unprinted[rule] = found.unprinted[rule]
        run = f"the run drawing where {rule} breaks"
        if found.kind != "holds":  # -continue exits 0 unless the run failed
            # Its marks are partial; the graph only when no earlier run's is whole.
            verdicts.marks_partial[rule] = stopped(found, run)
            if not whole and verdicts.graph_partial is None:
                verdicts.graph_partial = verdicts.marks_partial[rule]
            verdicts.logs[f"tlc-draw-{rule}.out"] = result.output
            continue
        if result.dot:
            draw_from(result, found, run, at_bound if found.distinct >= bound else None)
        elif found.distinct >= bound:
            verdicts.graph_partial = at_bound
    if not drawing and not complete and verdicts.graph_partial is None:
        # Only a deadlock or an initial-state property broke: the drawn run
        # stopped there, so draw from one that checks nothing and goes on.
        result, found = rerun(Request((), (), False, bounded=True))
        if found.kind != "holds":
            verdicts.graph_partial = stopped(found, "the run drawing the graph")
            verdicts.logs["tlc-draw.out"] = result.output
        else:
            at = at_bound if found.distinct >= bound else None
            draw_from(result, found, "the run drawing the graph", at)
    return verdicts


def probe_limit(checked: float) -> float:
    """Seconds each probe may take, after a check that took `checked`."""
    return min(PROBE_SECONDS, checked + PROBE_MARGIN)


def property_levels(
    config: Config, runner: Runner, limit: float = PROBE_SECONDS
) -> dict[str, str]:
    """TLC's own judgement of each configured property: a run with it as the
    only invariant, bounded so no state is explored. TLC refuses a temporal
    formula as an invariant (message 2146, "not a state predicate"): left out.
    A verdict on the initial states (exit 0 or 12) means a state predicate,
    which TLC checks as a PROPERTY in the initial states only: "initial". Any
    other outcome, a run killed after `limit` seconds included: "unsure"."""
    levels: dict[str, str] = {}
    for prop in config.properties:
        probe = Request((prop,), (), False, bounded=True, probe=True, timeout=limit)
        result = runner(probe)
        if any(m.code == 2146 for m in messages(result.output)):
            continue
        levels[prop] = "initial" if result.code in (0, 12) else "unsure"
    return levels
