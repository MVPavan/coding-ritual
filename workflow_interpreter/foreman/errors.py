"""Typed refusals shared by resolution and the resolved execution view.

Their own module so `execution.py` — which every input, brief, mint and task
path now reads a node through — stays below `resolve.py` and its composition
import, and no lower-level caller has to reach up through it.
"""


class ResolutionError(ValueError):
    """A caller supplied a setting that has no declared configuration home."""


class UnresolvedRunnerError(ResolutionError):
    """A root pins a role-bound node without the resolution of its runner."""


class UnusableResolutionError(ResolutionError):
    """A root pins an effective node that fails field or semantic validation.

    `resolve()` refuses these before a root is written, so reaching this at
    execution is tamper or a root written by an older, laxer resolver — either
    way it is a typed refusal, never a bare `ValidationError` out of the tick
    loop.
    """
