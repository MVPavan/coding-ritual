"""TLC's printed values, decoded into the one shape a view file receives.

The shape (documented for view authors in references/view.md):
integer int, boolean bool, string str, model value the str of its name;
a sequence or tuple a tuple; a set a frozenset; a record or any other function
a Frozen (a read-only, hashable dict) keyed by its decoded domain values.
Every value is immutable and hashable, and `order_key` gives one total order
across all of them.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import NoReturn, Union

Value = Union[bool, int, str, tuple["Value", ...], frozenset["Value"], "Frozen"]

# The escapes TLC prints inside a string, as the jar printed them.
_ESCAPES = dict(zip('"\\ntrf', '"\\\n\t\r\f'))

# Names TLC prints bare for a set it never enumerated; never a model value here.
UNEVALUATED = frozenset({"Nat", "Int", "Real", "STRING", "BOOLEAN"})


class ValueRefused(Exception):
    """A printed value outside the documented shape."""


class Frozen(dict[Value, Value]):
    """A read-only, hashable mapping: a TLA+ record or function."""

    def __hash__(self) -> int:  # type: ignore[override]
        return hash(frozenset(self.items()))

    def _refuse(self, *_: object, **__: object) -> NoReturn:
        raise TypeError("a model value is read-only")

    __setitem__ = __delitem__ = clear = pop = popitem = setdefault = update = _refuse
    __ior__ = _refuse


def order_key(value: Value) -> tuple[object, ...]:
    """Type rank (bool, int, str, tuple, frozenset, Frozen), then the value."""
    if isinstance(value, bool):
        return (0, int(value))
    if isinstance(value, int):
        return (1, value)
    if isinstance(value, str):
        return (2, value)
    if isinstance(value, tuple):
        return (3, tuple(order_key(item) for item in value))
    if isinstance(value, frozenset):
        return (4, tuple(sorted(order_key(item) for item in value)))
    pairs = ((order_key(k), order_key(v)) for k, v in value.items())
    return (5, tuple(sorted(pairs)))


def show(value: Value) -> str:
    """Plain text for a default label: strings and model values unquoted."""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, str)):
        return str(value)
    if isinstance(value, tuple):
        return "<<" + ", ".join(show(v) for v in value) + ">>"
    if isinstance(value, frozenset):
        return "{" + ", ".join(show(v) for v in sorted(value, key=order_key)) + "}"
    keys = sorted(value, key=order_key)
    if all(isinstance(k, str) for k in keys):
        return "[" + ", ".join(f"{k} |-> {show(value[k])}" for k in keys) + "]"
    return "(" + " @@ ".join(f"{show(k)} :> {show(value[k])}" for k in keys) + ")"


def _mixes_bool_and_int(items: Iterable[Value]) -> bool:
    kinds = {type(v) for v in items}
    return bool in kinds and int in kinds


class Decoder:
    """Decodes value texts; remembers model values and strings across calls,
    so a model value and a string with the same text are refused wherever
    they meet in one run."""

    def __init__(self) -> None:
        self.model_values: set[str] = set()
        self.strings: set[str] = set()

    def decode(self, text: str) -> Value:
        parser = _Parser(text, self)
        value = parser.value()
        parser.skip()
        if parser.pos != len(text):
            parser.fail("unexpected text after the value")
        return value


class _Parser:
    def __init__(self, text: str, decoder: Decoder) -> None:
        self.text = text
        self.pos = 0
        self.decoder = decoder

    def fail(self, why: str) -> NoReturn:
        start = max(0, self.pos - 30)
        excerpt = self.text[start : self.pos + 30].replace("\n", " ")
        raise ValueRefused(f"{why} at {excerpt!r}")

    def skip(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos].isspace():
            self.pos += 1

    def peek(self, token: str) -> bool:
        self.skip()
        return self.text.startswith(token, self.pos)

    def take(self, token: str) -> bool:
        if self.peek(token):
            self.pos += len(token)
            return True
        return False

    def expect(self, token: str) -> None:
        if not self.take(token):
            self.fail(f"expected {token!r}")

    def items(self, close: str) -> list[Value]:
        found: list[Value] = []
        if self.take(close):
            return found
        while True:
            found.append(self.value())
            if self.take(close):
                return found
            self.expect(",")

    def value(self) -> Value:
        self.skip()
        if self.take("<<"):
            return tuple(self.items(">>"))
        if self.take("{"):
            members = self.items("}")
            if _mixes_bool_and_int(members):
                self.fail("a boolean beside an integer in one set")
            return frozenset(members)
        if self.take("["):
            return self.record()
        if self.take("("):
            return self.function()
        if self.peek('"'):
            return self.string()
        return self.atom()

    def record(self) -> Frozen:
        fields: dict[Value, Value] = {}
        while True:
            name = self.word()
            if not self.take("|->"):
                self.fail("an unevaluated function or record")
            fields[name] = self.value()
            if self.take("]"):
                return Frozen(fields)
            self.expect(",")

    def function(self) -> Frozen:
        pairs: list[tuple[Value, Value]] = []
        while True:
            key = self.value()
            if not self.take(":>"):
                self.fail("expected ':>' in a function")
            pairs.append((key, self.value()))
            if self.take(")"):
                break
            self.expect("@@")
        # Checked before building the dict, where True and 1 would collide.
        if _mixes_bool_and_int(key for key, _ in pairs):
            self.fail("a boolean beside an integer in one function domain")
        return Frozen(pairs)

    def string(self) -> str:
        self.pos += 1
        out: list[str] = []
        while self.pos < len(self.text):
            char = self.text[self.pos]
            if char == "\\":
                escaped = _ESCAPES.get(self.text[self.pos + 1 : self.pos + 2])
                if escaped is None:
                    self.fail("an escape TLC does not print in a string")
                out.append(escaped)
                self.pos += 2
            elif char == '"':
                self.pos += 1
                text = "".join(out)
                if text in self.decoder.model_values:
                    self.fail(f"the string {text!r} shares its text with a model value")
                self.decoder.strings.add(text)
                return text
            else:
                out.append(char)
                self.pos += 1
        self.fail("an unterminated string")

    def word(self) -> str:
        self.skip()
        start = self.pos
        while self.pos < len(self.text) and (
            self.text[self.pos].isalnum() or self.text[self.pos] == "_"
        ):
            self.pos += 1
        if start == self.pos:
            self.fail("not a value")
        return self.text[start : self.pos]

    def atom(self) -> Value:
        self.skip()
        negative = self.take("-")
        word = self.word()
        if word.isdigit():
            return -int(word) if negative else int(word)
        if negative:
            self.fail("not a number")
        if word in ("TRUE", "FALSE"):
            return word == "TRUE"
        if word in UNEVALUATED or word[0].isdigit():
            self.fail(f"the unevaluated value {word}")
        if word in self.decoder.strings:
            self.fail(f"the model value {word} shares its text with a string")
        self.decoder.model_values.add(word)
        return word
