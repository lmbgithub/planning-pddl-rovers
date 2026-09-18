"""Precondition formulas: atoms, and, or, not.

Effects in this repository's domains are conjunctions of literals, so they stay
as add/delete lists. Preconditions are not: one of the domains here uses `or`
and a nested `not` while declaring only `:strips`, and a validator that handled
only conjunctions would have to either reject that domain or silently ignore
half of each precondition. Ignoring part of a precondition means accepting plan
steps that are not actually applicable — the exact failure a validator exists
to prevent.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass

from pddl.sexpr import ParseError, Sexpr


@dataclass(frozen=True, slots=True)
class Atom:
    """A predicate applied to terms. Terms are `?variables` or object names."""

    name: str
    terms: tuple[str, ...] = ()

    def __str__(self) -> str:
        return f"({' '.join((self.name, *self.terms))})"

    def bind(self, binding: Mapping[str, str]) -> Atom:
        return Atom(self.name, tuple(binding.get(t, t) for t in self.terms))

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(t for t in self.terms if t.startswith("?"))


class Formula:
    """Base class. Subclasses implement `holds` and report their own atoms."""

    def holds(self, state: AbstractSet[Atom], binding: Mapping[str, str]) -> bool:
        raise NotImplementedError

    def atoms(self) -> tuple[Atom, ...]:
        raise NotImplementedError

    def features(self) -> frozenset[str]:
        """PDDL features this formula uses, for the requirements cross-check."""
        return frozenset()


@dataclass(frozen=True, slots=True)
class Literal(Formula):
    atom: Atom

    def holds(self, state, binding):
        return self.atom.bind(binding) in state

    def atoms(self):
        return (self.atom,)

    def __str__(self) -> str:
        return str(self.atom)


@dataclass(frozen=True, slots=True)
class Not(Formula):
    inner: Formula

    def holds(self, state, binding):
        return not self.inner.holds(state, binding)

    def atoms(self):
        return self.inner.atoms()

    def features(self):
        # A negated *atom* is `:negative-preconditions`; a negated compound
        # formula is beyond that and needs `:disjunctive-preconditions` too.
        own = {":negative-preconditions"}
        if not isinstance(self.inner, Literal):
            own.add(":disjunctive-preconditions")
        return frozenset(own) | self.inner.features()

    def __str__(self) -> str:
        return f"(not {self.inner})"


@dataclass(frozen=True, slots=True)
class And(Formula):
    parts: tuple[Formula, ...]

    def holds(self, state, binding):
        return all(part.holds(state, binding) for part in self.parts)

    def atoms(self):
        return tuple(a for part in self.parts for a in part.atoms())

    def features(self):
        return (
            frozenset().union(*(p.features() for p in self.parts))
            if self.parts
            else frozenset()
        )

    def __str__(self) -> str:
        return f"(and {' '.join(str(p) for p in self.parts)})"


@dataclass(frozen=True, slots=True)
class Or(Formula):
    parts: tuple[Formula, ...]

    def holds(self, state, binding):
        # An empty disjunction is false: `(or)` demands that one of no options
        # hold. Returning True — which `any([])` does not, but a hand-rolled
        # loop easily would — makes an impossible precondition satisfiable.
        return any(part.holds(state, binding) for part in self.parts)

    def atoms(self):
        return tuple(a for part in self.parts for a in part.atoms())

    def features(self):
        own = frozenset({":disjunctive-preconditions"})
        return own.union(*(p.features() for p in self.parts)) if self.parts else own

    def __str__(self) -> str:
        return f"(or {' '.join(str(p) for p in self.parts)})"


TRUE = And(())
"""The empty conjunction. An action with no precondition is always applicable."""


def parse_formula(node: Sexpr, context: str = "formula") -> Formula:
    """Build a formula tree from an s-expression."""
    if isinstance(node, str):
        return Literal(Atom(node))
    if not node:
        return TRUE

    keyword = node[0]
    if keyword == "and":
        return And(tuple(parse_formula(child, context) for child in node[1:]))
    if keyword == "or":
        return Or(tuple(parse_formula(child, context) for child in node[1:]))
    if keyword == "not":
        if len(node) != 2:
            raise ParseError(f"{context}: (not ...) takes exactly one formula")
        return Not(parse_formula(node[1], context))
    if keyword in ("forall", "exists", "when", "imply"):
        raise ParseError(
            f"{context}: {keyword!r} is not supported. Validating a plan against a "
            f"model whose quantifiers are ignored would accept steps that are not "
            f"applicable."
        )
    if not all(isinstance(term, str) for term in node[1:]):
        raise ParseError(f"{context}: malformed atom {node!r}")
    return Literal(Atom(keyword, tuple(node[1:])))


def literals(node: Sexpr, context: str) -> tuple[tuple[Atom, ...], tuple[Atom, ...]]:
    """Flatten an effect into (added, deleted) atoms, rejecting anything else."""
    added: list[Atom] = []
    deleted: list[Atom] = []

    def walk(current: Sexpr) -> None:
        if not current:
            return
        if isinstance(current, str):
            added.append(Atom(current))
            return
        keyword = current[0]
        if keyword == "and":
            for child in current[1:]:
                walk(child)
        elif keyword == "not":
            if len(current) != 2 or isinstance(current[1], str):
                raise ParseError(f"{context}: malformed (not ...) in an effect")
            deleted.append(Atom(current[1][0], tuple(current[1][1:])))
        elif keyword in ("or", "when", "forall", "exists"):
            raise ParseError(
                f"{context}: {keyword!r} in an effect is beyond STRIPS and is "
                f"not supported"
            )
        else:
            added.append(Atom(keyword, tuple(current[1:])))

    walk(node)
    return tuple(added), tuple(deleted)


def all_variables(
    formulas: Sequence[Formula], atom_groups: Sequence[Sequence[Atom]]
) -> set[str]:
    found: set[str] = set()
    for formula in formulas:
        for atom in formula.atoms():
            found.update(atom.variables)
    for group in atom_groups:
        for atom in group:
            found.update(atom.variables)
    return found
