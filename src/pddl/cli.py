"""Validate a plan against a domain and problem."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pddl.domain import parse_domain_file
from pddl.plan import parse_plan_file
from pddl.problem import parse_problem_file
from pddl.sexpr import ParseError
from pddl.validate import validate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pddl-validate",
        description="Replay a plan against a PDDL domain and problem, step by step.",
    )
    parser.add_argument("domain", type=Path)
    parser.add_argument("problem", type=Path)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--steps", action="store_true", help="print every step")
    parser.add_argument(
        "--final-state",
        action="store_true",
        help="print the state reached at the end of the plan",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        domain = parse_domain_file(args.domain)
        problem = parse_problem_file(args.problem)
        plan = parse_plan_file(args.plan)
    except FileNotFoundError as exc:
        print(f"file not found: {exc.filename}", file=sys.stderr)
        return 2
    except ParseError as exc:
        print(f"parse error: {exc}", file=sys.stderr)
        return 2

    report = validate(domain, problem, plan)
    print(report.summary())
    if plan.makespan is not None:
        print(f"  makespan {plan.makespan:g}   plan length {len(plan)}")

    if args.steps:
        print()
        for step in report.steps:
            print(step)

    if args.final_state:
        print("\nfinal state:")
        for atom in sorted(report.final_state, key=str):
            print(f"  {atom}")

    # Exit code 1 for an invalid plan: this is meant to be usable in CI, where
    # "the model changed and the stored plan no longer applies" should fail a
    # build rather than scroll past.
    return 0 if report.valid else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
