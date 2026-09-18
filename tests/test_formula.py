import pytest

from pddl.formula import TRUE, And, Atom, Literal, Not, Or, literals, parse_formula
from pddl.sexpr import ParseError, parse_one

STATE = frozenset({Atom("at", ("r1", "a")), Atom("clean", ("a",))})


def holds(text, binding=None):
    return parse_formula(parse_one(text)).holds(STATE, binding or {})


def test_an_atom_in_the_state_holds():
    assert holds("(at r1 a)")


def test_an_atom_not_in_the_state_does_not():
    assert not holds("(at r1 b)")


def test_variables_are_bound_before_lookup():
    assert parse_formula(parse_one("(at ?r ?x)")).holds(STATE, {"?r": "r1", "?x": "a"})


def test_conjunction():
    assert holds("(and (at r1 a) (clean a))")
    assert not holds("(and (at r1 a) (clean b))")


def test_disjunction():
    assert holds("(or (at r1 b) (clean a))")
    assert not holds("(or (at r1 b) (clean b))")


def test_negation():
    assert holds("(not (at r1 b))")
    assert not holds("(not (at r1 a))")


def test_nested_negation_of_a_conjunction():
    assert holds("(not (and (at r1 a) (clean b)))")


def test_an_empty_conjunction_is_true():
    # An action with no precondition is always applicable.
    assert TRUE.holds(STATE, {})
    assert holds("()")


def test_an_empty_disjunction_is_false():
    # `(or)` asks that one of no options hold. True here would make an
    # impossible precondition satisfiable.
    assert not Or(()).holds(STATE, {})


def test_features_are_reported_for_the_requirements_cross_check():
    assert (
        ":disjunctive-preconditions"
        in parse_formula(parse_one("(or (a) (b))")).features()
    )
    assert ":negative-preconditions" in parse_formula(parse_one("(not (a))")).features()


def test_negating_a_compound_needs_disjunctive_preconditions_too():
    features = parse_formula(parse_one("(not (and (a) (b)))")).features()
    assert {":negative-preconditions", ":disjunctive-preconditions"} <= features


def test_a_plain_conjunction_needs_nothing_extra():
    assert parse_formula(parse_one("(and (a) (b))")).features() == frozenset()


@pytest.mark.parametrize("keyword", ["forall", "exists", "when", "imply"])
def test_unsupported_quantifiers_are_refused(keyword):
    # Silently ignoring a quantifier means accepting steps that are not
    # applicable — a confident wrong answer.
    with pytest.raises(ParseError, match=keyword):
        parse_formula(parse_one(f"({keyword} (?x) (p ?x))"))


def test_malformed_negation_is_refused():
    with pytest.raises(ParseError, match="exactly one"):
        parse_formula(parse_one("(not (a) (b))"))


def test_atoms_are_collected_through_the_whole_tree():
    formula = parse_formula(parse_one("(and (a) (or (b) (not (c))))"))
    assert {atom.name for atom in formula.atoms()} == {"a", "b", "c"}


def test_effects_split_into_added_and_deleted():
    added, deleted = literals(parse_one("(and (at r1 b) (not (at r1 a)))"), "test")
    assert added == (Atom("at", ("r1", "b")),)
    assert deleted == (Atom("at", ("r1", "a")),)


def test_an_effect_may_be_a_single_atom():
    added, deleted = literals(parse_one("(clean a)"), "test")
    assert added == (Atom("clean", ("a",)),) and deleted == ()


@pytest.mark.parametrize("keyword", ["or", "when", "forall", "exists"])
def test_non_strips_effects_are_refused(keyword):
    with pytest.raises(ParseError, match="beyond STRIPS"):
        literals(parse_one(f"({keyword} (a) (b))"), "test")


def test_atoms_render_as_pddl():
    assert str(Atom("at", ("r1", "a"))) == "(at r1 a)"
    assert str(Not(Literal(Atom("p")))) == "(not (p))"
    assert str(And((Literal(Atom("p")),))) == "(and (p))"
