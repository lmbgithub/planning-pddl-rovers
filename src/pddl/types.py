"""The type hierarchy declared by a domain's `:types` section.

STRIPS with `:typing` is the only fragment handled here, and the hierarchy is
what makes a grounded action legal or not. Checking it is the difference
between validating a plan and merely replaying it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from pddl.errors import TypeError_
from pddl.sexpr import Sexpr

OBJECT = "object"


@dataclass(frozen=True, slots=True)
class TypeHierarchy:
    """Maps each type to its parent. Everything reaches `object`."""

    parents: dict[str, str] = field(default_factory=dict)

    def is_subtype(self, subtype: str, supertype: str) -> bool:
        """Is `subtype` the same as, or below, `supertype`?"""
        if supertype == OBJECT:
            return True
        seen: set[str] = set()
        current = subtype
        while current is not None:
            if current == supertype:
                return True
            if current in seen:
                # A cycle in the hierarchy would loop forever. It is a broken
                # domain, but a broken domain must produce an error, not a hang.
                raise TypeError_(f"cyclic type hierarchy at {current!r}")
            seen.add(current)
            current = self.parents.get(current)
        return False

    def known(self, name: str) -> bool:
        return name == OBJECT or name in self.parents


def parse_typed_list(
    items: Sequence[Sexpr], *, default: str = OBJECT
) -> list[tuple[str, str]]:
    """Parse `a b - type c - other d` into [(name, type), ...].

    This shape appears in `:types`, `:parameters`, `:objects` and `:predicates`,
    so it is parsed once. Names that appear before any `- type` take `default`,
    which is how untyped PDDL degrades gracefully to everything being `object`.
    """

    result: list[tuple[str, str]] = []
    pending: list[str] = []
    index = 0
    while index < len(items):
        item = items[index]
        if not isinstance(item, str):
            raise TypeError_(f"expected a name in a typed list, found {item!r}")
        if item == "-":
            index += 1
            if index >= len(items) or not isinstance(items[index], str):
                raise TypeError_("'-' at the end of a typed list has no type after it")
            if not pending:
                raise TypeError_("'-' in a typed list with no names before it")
            type_name = items[index]
            result.extend((name, type_name) for name in pending)
            pending = []
        else:
            pending.append(item)
        index += 1

    result.extend((name, default) for name in pending)
    return result


def build_hierarchy(declarations: Iterable[tuple[str, str]]) -> TypeHierarchy:
    hierarchy = TypeHierarchy()
    for name, parent in declarations:
        hierarchy.parents[name] = parent
    return hierarchy
