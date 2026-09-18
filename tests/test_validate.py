"""Replaying plans, including every way a plan can be wrong."""

from pddl.domain import parse_domain
from pddl.formula import Atom
from pddl.plan import parse_plan
from pddl.problem import parse_problem
from pddl.validate import validate
from tests.fixtures import TOY_DOMAIN, TOY_PROBLEM

GOOD = "(move r1 a b)\n(tidy r1 b)\n"


def run(plan_text, domain_text=TOY_DOMAIN, problem_text=TOY_PROBLEM):
    return validate(
        parse_domain(domain_text), parse_problem(problem_text), parse_plan(plan_text)
    )


def test_a_correct_plan_is_valid():
    report = run(GOOD)
    assert report.valid
    assert all(s.applicable for s in report.steps)
    assert report.first_failure is None
    assert "VALID" in report.summary()


def test_an_inapplicable_step_names_the_missing_atom():
    report = run("(move r1 b a)\n")  # the robot starts at a, not b
    assert not report.valid
    assert report.first_failure.index == 1
    assert "(at r1 b)" in report.first_failure.reason


def test_replay_stops_at_the_first_failure():
    # Continuing past a failure would report cascading nonsense.
    report = run("(move r1 b a)\n(tidy r1 a)\n")
    assert len(report.steps) == 1


def test_a_plan_that_applies_but_misses_the_goal_is_invalid():
    # Every step is fine; the plan simply stops short. This is what a truncated
    # or wrong-problem plan looks like, and step-by-step it is perfect.
    report = run("(move r1 a b)\n")
    assert all(s.applicable for s in report.steps)
    assert not report.goal_reached
    assert not report.valid
    assert "goal is not reached" in report.summary()


def test_unmet_goals_are_named():
    report = run("(move r1 a b)\n")
    assert Atom("clean", ("b",)) in report.unmet_goals


def test_an_empty_plan_is_valid_only_if_the_goal_already_holds():
    assert not run("").valid
    already = TOY_PROBLEM.replace(
        "(:goal (and (at r1 b) (clean b)))", "(:goal (at r1 a))"
    )
    assert run("", problem_text=already).valid


def test_an_unknown_action_is_reported_at_its_step():
    report = run("(teleport r1 b)\n")
    assert "no action 'teleport'" in report.first_failure.reason


def test_the_wrong_number_of_arguments_is_reported():
    report = run("(move r1 a)\n")
    assert "takes 3 argument" in report.first_failure.reason


def test_arguments_are_type_checked():
    # Without this the replay accepts (move a r1 b): the preconditions are just
    # atom lookups, and a symmetric initial state can make them succeed.
    report = run("(move a r1 b)\n")
    assert "expects type 'robot'" in report.first_failure.reason


def test_an_argument_that_is_not_an_object_is_reported():
    report = run("(move r1 a z)\n")
    assert "not an object" in report.first_failure.reason


def test_a_negative_precondition_is_enforced():
    carrying = TOY_PROBLEM.replace(
        "(init (at r1 a)", "(init (carrying r1) (at r1 a)"
    ).replace("(:init (at r1 a)", "(:init (carrying r1) (at r1 a)")
    report = run("(move r1 a b)\n(tidy r1 b)\n", problem_text=carrying)
    assert not report.valid
    assert report.first_failure.index == 2


def test_delete_happens_before_add():
    # An action with the same atom in both lists must leave it true. Adding
    # first would delete it.
    domain = TOY_DOMAIN.replace(
        ":effect (and (not (at ?r ?from)) (at ?r ?to))",
        ":effect (and (not (at ?r ?to)) (at ?r ?to))",
    )
    report = run("(move r1 a b)\n", domain_text=domain)
    assert Atom("at", ("r1", "b")) in report.final_state


def test_effects_are_recorded_per_step():
    report = run(GOOD)
    assert Atom("at", ("r1", "b")) in report.steps[0].added
    assert Atom("at", ("r1", "a")) in report.steps[0].deleted


def test_a_domain_mismatch_is_a_warning_not_an_error():
    problem = TOY_PROBLEM.replace("(:domain toy)", "(:domain other)")
    report = run(GOOD, problem_text=problem)
    assert report.valid
    assert any("declares domain" in w for w in report.warnings)


def test_undeclared_requirements_are_warned_about():
    # The toy domain declares :strips :typing and uses (not ...).
    assert any(":negative-preconditions" in w for w in run(GOOD).warnings)


def test_the_final_state_is_returned():
    report = run(GOOD)
    assert Atom("clean", ("b",)) in report.final_state


def test_step_reports_render_readably():
    report = run("(move r1 b a)\n")
    assert "FAIL" in str(report.steps[0])
    assert "ok" in str(
        validate(
            parse_domain(TOY_DOMAIN), parse_problem(TOY_PROBLEM), parse_plan(GOOD)
        ).steps[0]
    )
