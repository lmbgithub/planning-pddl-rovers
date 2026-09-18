"""The models in this repository must keep saying what the README says they say."""

import pytest

from pddl import parse_domain_file, parse_plan_file, parse_problem_file, validate

DOMAINS = ["v1-battery", "v2-calibration-fix", "v3-towing"]
PROBLEMS = ["v1-battery", "v1-battery-harder", "v2-calibration-fix", "v3-towing"]


@pytest.mark.parametrize("name", DOMAINS)
def test_every_domain_parses(root, name):
    domain = parse_domain_file(root / f"domains/{name}.pddl")
    assert domain.actions


@pytest.mark.parametrize("name", PROBLEMS)
def test_every_problem_parses(root, name):
    assert parse_problem_file(root / f"problems/{name}.pddl").initial


def test_the_stored_plan_is_valid_against_the_model_that_produced_it(root):
    report = validate(
        parse_domain_file(root / "domains/v1-battery.pddl"),
        parse_problem_file(root / "problems/v1-battery.pddl"),
        parse_plan_file(root / "plans/v1-battery.plan"),
    )
    assert report.valid, report.summary()


def test_the_stored_plan_respects_the_battery_budget(root):
    # Four navigate steps on a b4 battery with one recharge available. If the
    # battery model were vacuous — a `lower` relation nothing constrains — the
    # plan would still validate, so this asserts the plan actually spends it.
    plan = parse_plan_file(root / "plans/v1-battery.plan")
    navigations = [s for s in plan.steps if s.name == "navigate-bat"]
    assert navigations
    levels = [s.arguments[-1] for s in navigations]
    assert levels == sorted(levels, reverse=True), (
        "battery level must not increase mid-plan"
    )


def test_v1_accepts_photographing_an_objective_the_camera_was_not_calibrated_for(root):
    # The finding. Domain v1 records `(calibrated ?camera ?rover)` and never
    # says what the camera was calibrated for.
    report = validate(
        parse_domain_file(root / "domains/v1-battery.pddl"),
        parse_problem_file(root / "problems/v1-battery.pddl"),
        parse_plan_file(root / "plans/uncalibrated-image.plan"),
    )
    assert all(step.applicable for step in report.steps)


def test_v2_rejects_the_same_plan(root):
    report = validate(
        parse_domain_file(root / "domains/v2-calibration-fix.pddl"),
        parse_problem_file(root / "problems/v2-calibration-fix.pddl"),
        parse_plan_file(root / "plans/uncalibrated-image.plan"),
    )
    failure = report.first_failure
    assert failure is not None
    assert failure.step.name == "take_image"
    assert "calibrated camera0 rover0 objective0" in failure.reason


def test_v2_carries_the_objective_in_the_calibration_predicate(root):
    v1 = parse_domain_file(root / "domains/v1-battery.pddl")
    v2 = parse_domain_file(root / "domains/v2-calibration-fix.pddl")
    assert v1.predicates["calibrated"] == 2
    assert v2.predicates["calibrated"] == 3


def test_the_towing_domain_declares_strips_while_using_more_than_strips(root):
    # Worth reporting rather than fixing silently: the domain tells a strict
    # planner one thing and a lenient one another, and the two disagree about
    # which plans exist.
    domain = parse_domain_file(root / "domains/v3-towing.pddl")
    assert ":strips" in domain.declared_requirements
    assert ":disjunctive-preconditions" in domain.undeclared_features()


def test_towing_is_only_for_a_rover_that_cannot_make_the_trip_itself(root):
    # The interesting half of the tow action: the negated precondition. Without
    # it, towing is always available and the planner uses it as a free ride.
    tow = parse_domain_file(root / "domains/v3-towing.pddl").action("tow")
    assert ":negative-preconditions" in tow.features()
