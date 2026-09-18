import pytest

from pddl.formula import Atom
from pddl.problem import parse_problem
from pddl.sexpr import ParseError
from tests.fixtures import TOY_PROBLEM


def test_objects_carry_their_types(toy_problem):
    assert toy_problem.objects == {"r1": "robot", "a": "room", "b": "room"}


def test_initial_state_is_a_set_of_atoms(toy_problem):
    assert Atom("at", ("r1", "a")) in toy_problem.initial


def test_the_goal_is_a_formula(toy_problem):
    assert toy_problem.goal.holds(
        frozenset({Atom("at", ("r1", "b")), Atom("clean", ("b",))}), {}
    )


def test_type_of_an_unknown_object_names_it(toy_problem):
    with pytest.raises(ParseError, match="no object 'r9'"):
        toy_problem.type_of("r9")


def test_a_problem_without_a_domain_is_refused():
    text = TOY_PROBLEM.replace("(:domain toy)", "")
    with pytest.raises(ParseError, match="which domain"):
        parse_problem(text)


def test_a_problem_without_a_goal_is_refused():
    text = TOY_PROBLEM[: TOY_PROBLEM.index("(:goal")] + ")"
    with pytest.raises(ParseError, match="no goal"):
        parse_problem(text)


def test_a_negated_atom_in_init_is_refused():
    # The initial state is closed-world: it lists what is true. `(not ...)`
    # there is either redundant or a misunderstanding, and accepting it makes
    # the initial state ambiguous.
    text = TOY_PROBLEM.replace("(at r1 a)", "(not (at r1 b))")
    with pytest.raises(ParseError, match="list of atoms"):
        parse_problem(text)


def test_a_duplicate_object_is_refused():
    text = TOY_PROBLEM.replace(
        "(:objects r1 - robot a b - room)", "(:objects r1 r1 - robot a b - room)"
    )
    with pytest.raises(ParseError, match="declared twice"):
        parse_problem(text)


def test_a_problem_with_no_objects_parses():
    problem = parse_problem("(define (problem p) (:domain d) (:init (p)) (:goal (p)))")
    assert problem.objects == {}


def test_a_file_that_is_not_a_problem_is_refused():
    with pytest.raises(ParseError, match="define"):
        parse_problem("(problem p)")
