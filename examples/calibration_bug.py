"""The finding: a model can accept a plan the real system would refuse.

Domain v1 records calibration as `(calibrated ?camera ?rover)`. It never says
*what* the camera was calibrated for. So a rover can calibrate camera0 against
objective1 and then photograph objective0 with it, and every precondition in
the model is satisfied.

A planner cannot find this. VAL cannot find this. The plan is valid — against a
model that is wrong. The only thing that finds it is reading the predicate and
asking what it means.

Domain v2 changes the predicate to `(calibrated ?camera ?rover ?objective)` and
the same plan is rejected at the step that takes the image.

    python examples/calibration_bug.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pddl import (  # noqa: E402
    parse_domain_file,
    parse_plan_file,
    parse_problem_file,
    validate,
)

PLAN = ROOT / "plans/uncalibrated-image.plan"
CASES = [
    ("v1-battery", "v1-battery", "calibrated ?camera ?rover"),
    ("v2-calibration-fix", "v2-calibration-fix", "calibrated ?camera ?rover ?objective"),
]


def main() -> int:
    plan = parse_plan_file(PLAN)
    print("plan under test:")
    for step in plan.steps:
        print(f"   {step}")
    print()

    for domain_name, problem_name, predicate in CASES:
        domain = parse_domain_file(ROOT / f"domains/{domain_name}.pddl")
        problem = parse_problem_file(ROOT / f"problems/{problem_name}.pddl")
        report = validate(domain, problem, plan)

        image_step = report.steps[-1] if len(report.steps) == len(plan) else None
        verdict = (
            "accepted — the model is happy to photograph an uncalibrated objective"
            if image_step and image_step.applicable
            else f"rejected — {report.first_failure.reason}"
        )
        print(f"{domain_name:<22}({predicate})")
        print(f"   take_image: {verdict}")
        print()

    print(
        "Neither run is a complete plan for the problem goal, and that is not the\n"
        "point: the question is whether the take_image step is applicable at all.\n"
        "Under v1 it is."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
