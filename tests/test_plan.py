import pytest

from pddl.plan import Step, parse_plan
from pddl.sexpr import ParseError


def test_a_timed_plan():
    plan = parse_plan("0.00000: (move r1 a b)\n0.00100: (tidy r1 b)\n")
    assert len(plan) == 2
    assert plan.steps[0] == Step("move", ("r1", "a", "b"), 0.0)
    assert plan.steps[1].time == 0.001


def test_an_untimed_plan():
    plan = parse_plan("(move r1 a b)\n")
    assert plan.steps[0].time is None
    assert plan.makespan is None


def test_makespan_is_the_last_timestamp_not_the_step_count():
    # For a sequential plan the two are proportional; the moment a planner
    # emits concurrent steps they answer different questions.
    plan = parse_plan("0.0: (a)\n0.5: (b)\n0.5: (c)\n")
    assert plan.makespan == 0.5
    assert len(plan) == 3


def test_comments_and_blank_lines_are_ignored():
    plan = parse_plan(";;!domain: rover\n\n(move r1 a b)\n; Makespan: 0.011\n")
    assert len(plan) == 1


def test_an_empty_plan_is_a_plan():
    plan = parse_plan("")
    assert len(plan) == 0
    assert plan.makespan is None


def test_a_zero_argument_action():
    assert parse_plan("(wait)\n").steps[0].arguments == ()


def test_symbols_are_lowercased():
    assert parse_plan("(MOVE R1 A B)\n").steps[0] == Step("move", ("r1", "a", "b"), None)


def test_a_line_with_two_actions_is_refused():
    with pytest.raises(ParseError, match="line 1"):
        parse_plan("(move r1 a b) (tidy r1 b)\n")


def test_a_nested_argument_is_refused():
    with pytest.raises(ParseError, match="object names"):
        parse_plan("(move r1 (a b))\n")


def test_a_bare_symbol_line_is_refused():
    with pytest.raises(ParseError, match="line 1"):
        parse_plan("move\n")


def test_steps_render_as_pddl():
    assert str(Step("move", ("r1", "a"))) == "(move r1 a)"


def test_negative_timestamps_parse():
    assert parse_plan("-1.5: (a)\n").steps[0].time == -1.5
