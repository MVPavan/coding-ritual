"""The view file: the reader's words for states and steps, phases, colours and
title. Each function is called at most once per state or step, and every
answer is checked before the chart uses it."""

from __future__ import annotations
import __future__

import importlib.util
import inspect
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType

from .values import Frozen, show

PALETTE = ("blue", "green", "yellow", "orange", "purple", "teal", "pink", "gray")
EXPORTS = {"state", "step", "group", "colors", "title"}
MAX_LABEL = 120

# A chart label: a flat label is a 1-tuple, a nested one a path of parents to
# the leaf, a regions one each region's label in the order of `View.regions`.
Label = tuple[str, ...]


class ViewError(Exception):
    """The view file or one of its answers is refused; names the state."""


def _text(value: object, what: str) -> str:
    if not isinstance(value, str):
        raise ViewError(f"{what} is {value!r}, not a string")
    if not value.strip() or value != value.strip():
        raise ViewError(f"{what} is empty or has spaces at its ends: {value!r}")
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ViewError(f"{what} has a control character: {value!r}")
    if len(value) > MAX_LABEL:
        raise ViewError(
            f"{what} is longer than {MAX_LABEL} characters: {value[:40]!r}..."
        )
    return value


def _call(where: str, function: Callable[..., object], *args: object) -> object:
    """Run one of the view's functions; its own failure is a refusal that
    names the state, not a crash."""
    try:
        return function(*args)
    except Exception as error:  # noqa: BLE001 (any failure of the view's own code is input)
        raise ViewError(f"{where} raised {type(error).__name__}: {error}") from None


def default_label(state: Frozen) -> str:
    return ", ".join(f"{name} = {show(state[name])}" for name in sorted(state, key=str))


@dataclass
class View:
    state_fn: Callable[[Frozen], object] | None = None
    step_fn: Callable[[str, Frozen, Frozen], object] | None = None
    group_fn: Callable[[Frozen], object] | None = None
    colors: dict[str, str] = field(default_factory=dict)
    title: str | None = None
    form: str | None = None  # flat, nested or regions, from the first answer
    regions: tuple[str, ...] = ()
    labels: dict[str, Label] = field(default_factory=dict)
    groups: dict[str, str | None] = field(default_factory=dict)
    steps: dict[tuple[str, str, str], str | None] = field(default_factory=dict)

    def label(self, sid: str, state: Frozen) -> Label:
        if sid in self.labels:
            return self.labels[sid]
        where = f"state() for {default_label(state)}"
        answer = (
            _call(where, self.state_fn, state)
            if self.state_fn
            else default_label(state)
        )
        label: Label
        if isinstance(answer, str):
            form, label = "flat", (_text(answer, where),)
        elif isinstance(answer, (list, tuple)) and answer:
            form = "nested"
            label = tuple(
                _text(part, f"{where}, part {i + 1}") for i, part in enumerate(answer)
            )
        elif isinstance(answer, dict) and answer:
            form = "regions"
            pairs = [
                (_text(k, f"{where}, region"), _text(v, f"{where}, region {k}"))
                for k, v in answer.items()
            ]
            names = tuple(name for name, _ in pairs)
            if self.form == "regions" and set(names) != set(self.regions):
                raise ViewError(
                    f"{where} gives regions {sorted(names)}, others gave {sorted(self.regions)}"
                )
            self.regions = self.regions or names
            found = dict(pairs)
            label = tuple(found[name] for name in self.regions)
        else:
            raise ViewError(
                f"{where} returned {answer!r}: expected a string, a non-empty list or a non-empty dict"
            )
        if self.form and form != self.form:
            raise ViewError(
                f"{where} returned a {form} label; earlier states gave {self.form} labels"
            )
        self.form = form
        self.labels[sid] = label
        return label

    def step(
        self, key: tuple[str, str, str], before: Frozen, after: Frozen
    ) -> str | None:
        if key in self.steps:
            return self.steps[key]
        where = f"step() for {key[2]} from {default_label(before)}"
        answer = (
            _call(where, self.step_fn, key[2], before, after)
            if self.step_fn
            else key[2]
        )
        self.steps[key] = None if answer is None else _text(answer, where)
        return self.steps[key]

    def group(self, sid: str, state: Frozen) -> str | None:
        if sid not in self.groups:
            where = f"group() for {default_label(state)}"
            answer = _call(where, self.group_fn, state) if self.group_fn else None
            self.groups[sid] = None if answer is None else _text(answer, where)
        return self.groups[sid]


def check_nesting(labels: dict[str, Label], states: dict[str, Frozen]) -> None:
    """A nested label may not be both a leaf and a parent."""
    paths = {label: sid for sid, label in labels.items()}
    for path, sid in paths.items():
        for cut in range(1, len(path)):
            if path[:cut] in paths:
                raise ViewError(
                    f"state() for {default_label(states[sid])}: {' > '.join(map(str, path[:cut]))} "
                    "is a leaf for one state and a parent for this one"
                )


def _load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("statechart_view", path)
    if spec is None or spec.loader is None:
        raise ViewError(f"{path}: not a Python file")
    module = importlib.util.module_from_spec(spec)
    writes = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    except Exception as error:  # noqa: BLE001 (any failure of the view's own code is input)
        raise ViewError(f"{path}: {type(error).__name__}: {error}") from None
    finally:
        sys.dont_write_bytecode = writes
    return module


def load(path: Path | None) -> View:
    """Load a view file, refusing unknown or mistyped exports; no file gives
    the default view (variable values as labels, action names on arrows)."""
    if path is None:
        return View()
    module = _load_module(path)
    for name, value in vars(module).items():
        if name.startswith("_") or name in EXPORTS:
            continue
        if inspect.ismodule(value) or isinstance(value, __future__._Feature):
            continue
        imported = getattr(value, "__module__", None) != module.__name__
        if (inspect.isroutine(value) or inspect.isclass(value)) and imported:
            continue  # a function or class imported from elsewhere
        raise ViewError(
            f"{path}: unknown export {name!r}; exports are {sorted(EXPORTS)}, helpers start with _"
        )
    view = View()
    for name in ("state", "step", "group"):
        value = getattr(module, name, None)
        if value is not None and not callable(value):
            raise ViewError(f"{path}: {name} must be a function")
    view.state_fn = getattr(module, "state", None)
    view.step_fn = getattr(module, "step", None)
    view.group_fn = getattr(module, "group", None)
    colors = getattr(module, "colors", {})
    if not isinstance(colors, dict):
        raise ViewError(f"{path}: colors must be a dict of group to colour")
    for group, color in colors.items():
        _text(group, f"{path}: colors key")
        if color not in PALETTE:
            raise ViewError(
                f"{path}: colour {color!r} for {group!r} is not one of {', '.join(PALETTE)}"
            )
    view.colors = dict(colors)
    title = getattr(module, "title", None)
    view.title = None if title is None else _text(title, f"{path}: title")
    return view
