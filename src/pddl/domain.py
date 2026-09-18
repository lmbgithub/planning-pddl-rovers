"""Domain parsing: types, predicates and action schemas."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from pddl.formula import Atom, Formula, all_variables, literals, parse_formula
from pddl.sexpr import ParseError, Sexpr, find, parse_one
from pddl.types import TypeHierarchy, build_hierarchy, parse_typed_list

#: Requirements this validator implements. Anything else is refused rather than
#: quietly ignored: validating against a fragment of a model is worse than not
#: validating at all, because it produces a confident "valid".
SUPPORTED_REQUIREMENTS = frozenset(
    {
        ":strips",
        ":typing",
        ":negative-preconditions",
        ":disjunctive-preconditions",
        ":equality",
    }
)


@dataclass(frozen=True, slots=True)
class Action:
    """A lifted action schema."""

    name: str
    parameters: tuple[tuple[str, str], ...]  # (?variable, type)
    precondition: Formula
    add_effects: tuple[Atom, ...]
    delete_effects: tuple[Atom, ...]

    @property
    def arity(self) -> int:
        return len(self.parameters)

    def bind(self, arguments: Sequence[str]) -> dict[str, str]:
        if len(arguments) != self.arity:
            raise ParseError(
                f"action {self.name} takes {self.arity} argument(s), got {len(arguments)}"
            )
        return {
            name: argument
            for (name, _), argument in zip(self.parameters, arguments, strict=True)
        }

    def features(self) -> frozenset[str]:
        return self.precondition.features()


@dataclass(frozen=True, slots=True)
class Domain:
    name: str
    types: TypeHierarchy
    predicates: Mapping[str, int]  # name -> arity
    actions: Mapping[str, Action]
    declared_requirements: tuple[str, ...]

    def action(self, name: str) -> Action:
        try:
            return self.actions[name]
        except KeyError:
            raise ParseError(
                f"domain {self.name!r} has no action {name!r}; "
                f"known actions: {', '.join(sorted(self.actions))}"
            ) from None

    def used_features(self) -> frozenset[str]:
        """PDDL features the action schemas actually use."""
        used: frozenset[str] = frozenset({":strips"})
        for action in self.actions.values():
            used |= action.features()
        if self.types.parents:
            used |= {":typing"}
        return used

    def undeclared_features(self) -> tuple[str, ...]:
        """Features used but not declared in `:requirements`.

        Not an error — most planners accept it — but worth reporting. A domain
        that declares `:strips` and then uses `(or ...)` is telling a strict
        planner one thing and a lenient one another, and the two will disagree
        about which plans exist.
        """
        return tuple(sorted(self.used_features() - set(self.declared_requirements)))


def parse_domain(text: str) -> Domain:
    form = parse_one(text)
    if not isinstance(form, list) or len(form) < 2 or form[0] != "define":
        raise ParseError("a domain file must be a single (define (domain ...) ...) form")

    header = form[1]
    if not isinstance(header, list) or header[0] != "domain":
        raise ParseError("the first form after 'define' must be (domain <name>)")
    name = header[1]

    requirement_section = find(form, ":requirements")
    requirements = tuple(requirement_section[1:]) if requirement_section else ()
    unsupported = set(requirements) - SUPPORTED_REQUIREMENTS
    if unsupported:
        raise ParseError(
            f"unsupported requirement(s): {', '.join(sorted(unsupported))}. "
            f"This validator implements {', '.join(sorted(SUPPORTED_REQUIREMENTS))}."
        )

    types_section = find(form, ":types")
    hierarchy = build_hierarchy(
        parse_typed_list(types_section[1:]) if types_section else []
    )

    predicates: dict[str, int] = {}
    predicate_section = find(form, ":predicates")
    if predicate_section:
        for declaration in predicate_section[1:]:
            if not isinstance(declaration, list) or not declaration:
                raise ParseError(f"malformed predicate declaration: {declaration!r}")
            if declaration[0] in predicates:
                raise ParseError(f"predicate {declaration[0]!r} is declared twice")
            predicates[declaration[0]] = len(parse_typed_list(declaration[1:]))

    actions: dict[str, Action] = {}
    for item in form[2:]:
        if isinstance(item, list) and item and item[0] == ":action":
            action = _parse_action(item, predicates, hierarchy)
            if action.name in actions:
                raise ParseError(f"action {action.name!r} is declared twice")
            actions[action.name] = action

    if not actions:
        raise ParseError(f"domain {name!r} declares no actions")

    return Domain(
        name=name,
        types=hierarchy,
        predicates=predicates,
        actions=actions,
        declared_requirements=requirements,
    )


def parse_domain_file(path: str | Path) -> Domain:
    return parse_domain(Path(path).read_text(encoding="utf-8"))


def _parse_action(
    form: Sexpr, predicates: Mapping[str, int], hierarchy: TypeHierarchy
) -> Action:
    name = form[1]
    sections = {form[i]: form[i + 1] for i in range(2, len(form) - 1, 2)}
    context = f"action {name!r}"

    parameters = tuple(parse_typed_list(sections.get(":parameters", [])))
    for _, type_name in parameters:
        if not hierarchy.known(type_name):
            raise ParseError(
                f"{context}: parameter declared with unknown type {type_name!r}"
            )

    precondition = parse_formula(sections.get(":precondition", []), context)
    add, delete = literals(sections.get(":effect", []), context)

    for atom in (*precondition.atoms(), *add, *delete):
        _check_atom(atom, predicates, context)

    declared = {variable for variable, _ in parameters}
    used = all_variables([precondition], [add, delete])
    undeclared = used - declared
    if undeclared:
        # A typo in a variable name is the most common PDDL bug there is: the
        # precondition refers to a fresh variable nothing binds, and the action
        # becomes either always or never applicable, with no error anywhere.
        raise ParseError(
            f"{context} uses undeclared variable(s): {', '.join(sorted(undeclared))}"
        )

    return Action(name, parameters, precondition, add, delete)


def _check_atom(atom: Atom, predicates: Mapping[str, int], context: str) -> None:
    if not predicates:
        return
    if atom.name not in predicates:
        raise ParseError(f"{context}: undeclared predicate {atom.name!r}")
    if predicates[atom.name] != len(atom.terms):
        # Arity mismatches are how a modelling change like `(calibrated ?c ?r)`
        # becoming `(calibrated ?c ?r ?o)` shows up if it is applied in only
        # half the places it needed to be.
        raise ParseError(
            f"{context}: predicate {atom.name!r} takes {predicates[atom.name]} "
            f"argument(s), used with {len(atom.terms)}"
        )
