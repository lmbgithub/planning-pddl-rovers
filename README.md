# planning-pddl-rovers — a plan can be valid and still be wrong

PDDL models of a rovers planning task, refined across three variants, with a
**plan validator** written to check them.

The finding the repository is built around: domain v1 accepts a plan in which a
rover photographs an objective its camera was never calibrated for. Every
precondition is satisfied. A planner cannot detect this, and neither can a plan
validator — the plan is valid *against a model that is wrong*.

**Zero dependencies. 131 tests.**

## Skills demonstrated

**Symbolic AI / planning** — PDDL domain and problem modelling, STRIPS
semantics implemented as a step-by-step replay, resource consumption expressed
as a level ladder to stay inside the fragment classical planners support,
negated preconditions used to constrain an action rather than enable it

**Language tooling** — an s-expression reader with line-tracked errors, typed
parameter lists, a formula tree over and/or/not, and feature detection that
reports what a domain uses against what it declares

**Verification** — arguments type-checked against the declared hierarchy, not
just looked up; delete-before-add effect ordering; "every step applied" and
"the goal holds" kept as separate claims; unsupported constructs refused rather
than silently ignored

**Software engineering** — zero dependencies, 131 tests covering malformed
headers, cyclic type hierarchies, arity mismatches, undeclared variables and
truncated plans; CI exit code 1 on an invalid plan so a model change fails a
build

**Tooling** — ruff, pre-commit, CI matrix on 3.10/3.11/3.12 with a lint job

## What the run looks like

```
$ python examples/calibration_bug.py
plan under test:
   (navigate-bat rover0 waypoint3 waypoint1 bat0 b4 b4 b3)
   (calibrate rover0 camera0 objective1 waypoint1)
   (take_image rover0 waypoint1 objective0 camera0 high_res)

v1-battery            (calibrated ?camera ?rover)
   take_image: accepted — the model is happy to photograph an uncalibrated objective

v2-calibration-fix    (calibrated ?camera ?rover ?objective)
   take_image: rejected — unsatisfied: (calibrated camera0 rover0 objective0)

Neither run is a complete plan for the problem goal, and that is not the
point: the question is whether the take_image step is applicable at all.
Under v1 it is.
```

The camera's only `calibration_target` is `objective1`. In v1 the calibration
predicate does not record *what* the camera was calibrated for, so the
calibration transfers to every objective in the problem.

Validating the real planner output:

```
$ python -m pddl domains/v1-battery.pddl problems/v1-battery.pddl plans/v1-battery.plan --steps
domain rover-battery   problem roverprob1234   12 steps
  VALID: every step applied and the goal holds
  makespan 0.011   plan length 12

  1. ok  (navigate-bat rover0 waypoint3 waypoint1 bat0 b4 b4 b3)
  2. ok  (calibrate rover0 camera0 objective1 waypoint1)
  ...
 12. ok  (communicate_rock_data rover0 general waypoint3 waypoint3 waypoint0)
```

## The five decisions worth discussing

**1. A battery modelled as a level ladder, not a number.** `:fluents` would make
the battery arithmetic and lock the domain out of most classical planners.
Instead the battery is a `blevel` type with a `(lower ?a ?b)` relation listed in
the problem, and `navigate-bat` moves one rung down. The cost is that the
problem file has to enumerate the ladder; the benefit is that the model stays in
the fragment every planner supports. `test_the_stored_plan_respects_the_battery_budget`
checks the level never increases mid-plan — without it, a `lower` relation that
nothing constrains would validate just as happily.

**2. The towing precondition is a negation, not a flag.** `tow` requires that
the towed rover *cannot* make the crossing itself. Without that, towing is
always available and a planner treats it as a free ride for two rovers at the
cost of one battery — which is a cheaper plan and not the intended behaviour.

**3. The validator refuses what it cannot check.** `forall`, `exists`, `when`
and numeric fluents raise rather than being skipped. A validator that quietly
ignores a conditional effect accepts steps that are not applicable and reports
"valid" — worse than not validating, because it is confident.

**4. Arguments are type-checked, not just looked up.** Preconditions are atom
lookups, so a replay with no type check happily accepts
`(move waypoint1 rover0 waypoint2)` whenever the initial state happens to be
symmetric. The type hierarchy is what separates validating a plan from replaying
one.

**5. "Every step applied" and "the plan is valid" are different claims.** A plan
whose steps all apply but that stops short of the goal looks perfect step by
step; it is what a truncated plan, or a plan validated against the wrong
problem, produces. `ValidationReport.valid` requires both, and the summary says
which of the two failed.

### A finding the validator reports but does not fix

`domains/v3-towing.pddl` declares `:requirements :typing :strips` and then uses
`(or ...)` and a negated conjunction in its preconditions. Most planners accept
it. A strict one will not, and the two disagree about which plans exist — so the
validator prints it as a warning rather than repairing the file:

```
warning: domain uses :disjunctive-preconditions, :negative-preconditions
         without declaring them in :requirements
```

## Design

```
src/pddl/
  sexpr.py     tokenizer and reader (PDDL is Lisp without the evaluation)
  types.py     typed-list parsing and the subtype relation
  formula.py   atoms, and/or/not, and the feature set each formula uses
  domain.py    predicates and action schemas, with the model-level checks
  problem.py   objects, initial state, goal
  plan.py      timed and untimed plan files
  validate.py  step-by-step replay, typing, and the goal test
  cli.py       argument parsing, exit codes
```

The reader is written out rather than pulled from a PDDL library because the
subject of this repository is what the model *says*, and a parser you did not
write is a layer between you and that. It is also what makes the model-level
errors possible: an undeclared variable, a predicate used at the wrong arity, a
duplicate action. Those are the bugs that produce plausible plans.

## Usage

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

```bash
pytest -q
python examples/calibration_bug.py
python -m pddl domains/v1-battery.pddl problems/v1-battery.pddl plans/v1-battery.plan --steps
```

Exit code is 1 for an invalid plan, so it works in CI: a model change that
invalidates a stored plan fails the build instead of scrolling past. The CI
workflow in this repository does exactly that.

As a library:

```python
from pddl import parse_domain_file, parse_problem_file, parse_plan_file, validate

report = validate(
    parse_domain_file("domains/v1-battery.pddl"),
    parse_problem_file("problems/v1-battery.pddl"),
    parse_plan_file("plans/v1-battery.plan"),
)
print(report.summary())
print(report.first_failure)
```

## Dataset

### The models

| File | What it adds | What it is for |
|---|---|---|
| `domains/v1-battery.pddl` | A discrete battery: `navigate-bat` steps the level down through `(lower ?next ?current)`, `recharge` restores it at the lander | Resource consumption without numeric fluents, so the domain stays in STRIPS |
| `domains/v2-calibration-fix.pddl` | `(calibrated ?camera ?rover ?objective)` | Fixes the finding above |
| `domains/v3-towing.pddl` | Terrain types (`is_road_up`, `is_flat`, …), locomotion (`use_wheels`, `use_legs`), and a `tow` action | A rover that cannot cross a stretch itself gets towed by one that can |

Problems and stored planner output sit in `problems/` and `planner-output/`
under matching names. `plans/uncalibrated-image.plan` is hand-written, and says
so in its header: no planner produced it, it exists to demonstrate the bug.


None. The models are the data.

To *produce* plans rather than check them you need a planner:
<https://editor.planning.domains> runs these files directly in a browser (paste a
domain and a problem, press Solve), or build [Fast
Downward](https://www.fast-downward.org/) locally. The output in
`planner-output/` came from the `dual-bfws-ffparser` and `lama-first` solvers on
that service.

## Scope

- **No planner.** This validates plans; it does not search for them. Writing a
  planner is a different project, and a bad one would say nothing about the
  models.
- **No grounding of the full domain.** Only the actions that appear in the plan
  are instantiated. Reachability analysis and mutex detection are planner work.
- **No numeric fluents, durative actions or ADL.** Deliberately: the models are
  written to stay inside the fragment every classical planner supports, and the
  validator refuses anything it cannot check exactly.
- **No plan-quality comparison across planners.** `planner-output/` keeps the
  raw logs, but comparing search effort across solvers on one problem instance
  would be a benchmark, not a measurement — see the sibling
  `08.28.planning-planner-benchmark` repository.

## License

MIT — see [LICENSE](LICENSE).
