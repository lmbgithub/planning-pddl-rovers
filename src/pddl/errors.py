"""The package's error hierarchy.

One base class, so a caller catches everything this package raises with a
single `except` and can still discriminate. `PddlError` derives from
`ValueError` so handlers written for bad input keep working.
"""

from __future__ import annotations


class PddlError(ValueError):
    """Anything this package refuses to do."""


class ParseError(PddlError):
    """The text is not well-formed PDDL."""


class TypeError_(PddlError):
    """A typed declaration that does not make sense.

    Named with a trailing underscore so it cannot shadow the builtin
    `TypeError` at a call site that imports it directly.
    """
