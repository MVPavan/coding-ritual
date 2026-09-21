"""Typed failures of the §6 crew profiles.

Flat, like `bdio.errors` and `inspector.errors`: a caller routes on the class,
never on a message. Every one of these is a REFUSAL to build or run an
invocation the profile cannot bound — §6's "unsupported option = loud error"
is the whole point, because the alternative is a child that quietly holds more
authority than the node declared.
"""

from __future__ import annotations

from workflow_interpreter.contracts.execution import UnregisteredCrewError


class ProfileError(Exception):
    """Base class for every failure raised by a crew profile."""


class UnsupportedOptionError(ProfileError):
    """§6: the crew cannot express a bound the task requires.

    Raised where a CLI has no mechanism at all for what was asked — not where
    the wrapper simply chose not to use one. The message names the option and
    what the vendor CAN bound, so the refusal is actionable rather than a wall.
    """


class UnknownProfileError(ProfileError, UnregisteredCrewError):
    """A crew name absent from the registry (`registry.profile_for`)."""


class TaskRefused(ProfileError):
    """The `TaskSpec` cannot be turned into an invocation at all.

    Distinct from `UnsupportedOptionError`: the vendor is capable, the task is
    incomplete (an empty brief, a relative path where an absolute one is
    required, a resume with no launch to continue).
    """
