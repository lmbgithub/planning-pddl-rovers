"""Problem parsing: objects, initial state, goal."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from pddl.formula import Atom, Formula, parse_formula
from pddl.sexpr import ParseError, find, parse_one
from pddl.types import parse_typed_list


@dataclass(frozen=True, slots=True)
class Problem:
    name: str
    domain_name: str
    objects: Mapping[str, str]  # object -> type
    initial: frozenset[Atom]
    goal: Formula

    def type_of(self, obj: str) -> str:
        try:
            return self.objects[obj]
        except KeyError:
            raise ParseError(f"problem {self.name!r} has no object {obj!r}") from None


def parse_problem(text: str) -> Problem:
    form = parse_one(text)
    if not isinstance(form, list) or len(form) < 2 or form[0] != "define":
        raise ParseError(
            "a problem file must be a single (define (problem ...) ...) form"
        )

    header = form[1]
    if not isinstance(header, list) or header[0] != "problem":
        raise ParseError("the first form after 'define' must be (problem <name>)")
    name = header[1]

    domain_section = find(form, ":domain")
    if not domain_section or len(domain_section) < 2:
        raise ParseError(f"problem {name!r} does not say which domain it belongs to")
    domain_name = domain_section[1]

    object_section = find(form, ":objects")
    objects: dict[str, str] = {}
    for obj, type_name in parse_typed_list(object_section[1:] if object_section else []):
        if obj in objects:
            raise ParseError(f"object {obj!r} is declared twice")
        objects[obj] = type_name

    initial_section = find(form, ":init")
    initial = set()
    for item in initial_section[1:] if initial_section else []:
        if isinstance(item, str):
            initial.add(Atom(item))
            continue
        if item and item[0] in ("not", "and", "or"):
            # A closed-world initial state lists what is true. `(not ...)` in
            # `:init` is either redundant or a misunderstanding, and silently
            # accepting it would make the initial state ambiguous.
            raise ParseError(
                f"problem {name!r}: (:init ...) must be a list of atoms; "
                f"found {item[0]!r}"
            )
        initial.add(Atom(item[0], tuple(item[1:])))

    goal_section = find(form, ":goal")
    if not goal_section or len(goal_section) < 2:
        raise ParseError(f"problem {name!r} declares no goal")
    goal = parse_formula(goal_section[1], f"problem {name!r} goal")

    return Problem(
        name=name,
        domain_name=domain_name,
        objects=objects,
        initial=frozenset(initial),
        goal=goal,
    )


def parse_problem_file(path: str | Path) -> Problem:
    return parse_problem(Path(path).read_text(encoding="utf-8"))
