import pytest

from pddl.domain import parse_domain
from pddl.sexpr import ParseError
from tests.fixtures import TOY_DOMAIN


def test_actions_and_predicates_are_read(toy_domain):
    assert set(toy_domain.actions) == {"move", "tidy"}
    assert toy_domain.predicates["at"] == 2


def test_parameters_carry_their_types(toy_domain):
    assert toy_domain.action("move").parameters == (
        ("?r", "robot"),
        ("?from", "room"),
        ("?to", "room"),
    )


def test_effects_are_split(toy_domain):
    move = toy_domain.action("move")
    assert [str(a) for a in move.add_effects] == ["(at ?r ?to)"]
    assert [str(a) for a in move.delete_effects] == ["(at ?r ?from)"]


def test_an_unknown_action_lists_what_exists(toy_domain):
    with pytest.raises(ParseError, match="known actions: move, tidy"):
        toy_domain.action("teleport")


def test_binding_rejects_the_wrong_number_of_arguments(toy_domain):
    with pytest.raises(ParseError, match="takes 3 argument"):
        toy_domain.action("move").bind(["r1", "a"])


def test_an_undeclared_variable_is_refused():
    # The most common PDDL bug there is: the precondition names a variable
    # nothing binds, so the action is either always or never applicable.
    text = TOY_DOMAIN.replace("(at ?r ?from) (connected ?from ?to)", "(at ?r ?form)")
    with pytest.raises(ParseError, match="undeclared variable"):
        parse_domain(text)


def test_an_undeclared_predicate_is_refused():
    text = TOY_DOMAIN.replace("(clean ?x)))", "(sparkling ?x)))")
    with pytest.raises(ParseError, match="undeclared predicate"):
        parse_domain(text)


def test_a_predicate_used_with_the_wrong_arity_is_refused():
    # This is how a change like (calibrated ?c ?r) -> (calibrated ?c ?r ?o)
    # shows up when it is applied in only half the places it was needed.
    text = TOY_DOMAIN.replace(":effect (clean ?x)))", ":effect (clean ?x ?r)))")
    with pytest.raises(ParseError, match="takes 1 argument"):
        parse_domain(text)


def test_a_parameter_with_an_unknown_type_is_refused():
    text = TOY_DOMAIN.replace("(?r - robot ?x - room)", "(?r - android ?x - room)")
    with pytest.raises(ParseError, match="unknown type"):
        parse_domain(text)


def test_a_duplicate_action_is_refused():
    text = TOY_DOMAIN.replace(
        "(:action tidy",
        "(:action move\n    :parameters ()\n    :effect ())\n  (:action tidy",
    )
    with pytest.raises(ParseError, match="declared twice"):
        parse_domain(text)


def test_a_duplicate_predicate_is_refused():
    text = TOY_DOMAIN.replace(
        "(clean ?x - room))", "(clean ?x - room) (clean ?y - room))"
    )
    with pytest.raises(ParseError, match="declared twice"):
        parse_domain(text)


def test_a_domain_with_no_actions_is_refused():
    with pytest.raises(ParseError, match="no actions"):
        parse_domain("(define (domain empty) (:requirements :strips) (:predicates (p)))")


def test_an_unsupported_requirement_is_refused_up_front():
    # Validating against a fragment of a model produces a confident "valid".
    text = TOY_DOMAIN.replace(
        ":requirements :strips :typing", ":requirements :strips :fluents"
    )
    with pytest.raises(ParseError, match=":fluents"):
        parse_domain(text)


def test_a_file_that_is_not_a_define_form_is_refused():
    with pytest.raises(ParseError, match="define"):
        parse_domain("(domain toy)")


def test_used_features_include_typing_when_types_are_declared(toy_domain):
    assert ":typing" in toy_domain.used_features()


def test_negative_preconditions_are_detected(toy_domain):
    assert ":negative-preconditions" in toy_domain.used_features()


def test_undeclared_features_are_reported_not_raised(toy_domain):
    # The toy domain declares :strips :typing but `tidy` uses (not ...).
    assert ":negative-preconditions" in toy_domain.undeclared_features()


def test_a_domain_that_declares_what_it_uses_reports_nothing():
    text = TOY_DOMAIN.replace(
        ":requirements :strips :typing",
        ":requirements :strips :typing :negative-preconditions",
    )
    assert parse_domain(text).undeclared_features() == ()
