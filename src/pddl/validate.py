"""Replay a plan against a domain and problem, step by step.

A planner returning a plan is not evidence that the plan works. Planners are
complex, and more to the point the *model* is usually the thing that is wrong:
a missing delete effect, a predicate whose arity changed in one place, a
precondition referring to a variable nothing binds. All of those produce a plan
that a planner is happy with. This replays the plan against the model and says
which step fails and why.

What it cannot do is check the model against reality. That distinction is the
whole point of the calibration finding in this repository's README.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from pddl.domain import Action, Domain
from pddl.formula import Atom
from pddl.plan import Plan, Step
from pddl.problem import Problem
from pddl.sexpr import ParseError


@dataclass(frozen=True, slots=True)
class StepReport:
    """What happened at one step."""

    index: int
    step: Step
    applicable: bool
    reason: str = ""
    added: tuple[Atom, ...] = ()
    deleted: tuple[Atom, ...] = ()

    def __str__(self) -> str:
        mark = "ok " if self.applicable else "FAIL"
        line = f"{self.index:>3}. {mark} {self.step}"
        return line if self.applicable else f"{line}\n      {self.reason}"


@dataclass(frozen=True, slots=True)
class ValidationReport:
    domain: str
    problem: str
    steps: tuple[StepReport, ...]
    goal_reached: bool
    final_state: frozenset[Atom]
    unmet_goals: tuple[Atom, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def valid(self) -> bool:
        """A plan is valid only if every step applied *and* the goal holds.

        Both halves are needed. A plan whose steps all apply but that stops
        short of the goal is the failure mode of a truncated or a
        wrong-problem plan, and it looks perfect step by step.
        """
        return all(s.applicable for s in self.steps) and self.goal_reached

    @property
    def first_failure(self) -> StepReport | None:
        return next((s for s in self.steps if not s.applicable), None)

    def summary(self) -> str:
        lines = [
            f"domain {self.domain}   problem {self.problem}   {len(self.steps)} steps"
        ]
        for warning in self.warnings:
            lines.append(f"  warning: {warning}")
        failure = self.first_failure
        if failure:
            lines.append(f"  INVALID at step {failure.index}: {failure.reason}")
        elif not self.goal_reached:
            unmet = ", ".join(str(a) for a in self.unmet_goals) or "goal formula is false"
            lines.append(
                f"  INVALID: every step applied but the goal is not reached ({unmet})"
            )
        else:
            lines.append("  VALID: every step applied and the goal holds")
        return "\n".join(lines)


def validate(domain: Domain, problem: Problem, plan: Plan) -> ValidationReport:
    """Replay `plan`, stopping at the first inapplicable step."""

    warnings: list[str] = []
    if problem.domain_name != domain.name:
        # Not fatal — the file names are the user's business — but validating a
        # plan against the wrong domain is a way to get a confident, meaningless
        # answer, so it is said out loud.
        warnings.append(
            f"problem declares domain {problem.domain_name!r} "
            f"but the domain is {domain.name!r}"
        )
    undeclared = domain.undeclared_features()
    if undeclared:
        warnings.append(
            f"domain uses {', '.join(undeclared)} without declaring them in :requirements"
        )

    state = set(problem.initial)
    reports: list[StepReport] = []
    failed = False

    for index, step in enumerate(plan.steps, start=1):
        if failed:
            break
        try:
            action = domain.action(step.name)
            binding = action.bind(step.arguments)
        except ParseError as exc:
            reports.append(StepReport(index, step, False, str(exc)))
            failed = True
            continue

        type_error = _check_types(action, binding, problem, domain)
        if type_error:
            reports.append(StepReport(index, step, False, type_error))
            failed = True
            continue

        if not action.precondition.holds(state, binding):
            reports.append(
                StepReport(index, step, False, _explain(action, binding, state))
            )
            failed = True
            continue

        deleted = tuple(a.bind(binding) for a in action.delete_effects)
        added = tuple(a.bind(binding) for a in action.add_effects)
        # Delete before add, which is the PDDL rule and not a detail: an action
        # with the same atom in both lists must leave it true. Adding first
        # would delete it.
        state.difference_update(deleted)
        state.update(added)
        reports.append(StepReport(index, step, True, added=added, deleted=deleted))

    frozen = frozenset(state)
    goal_reached = not failed and problem.goal.holds(frozen, {})
    return ValidationReport(
        domain=domain.name,
        problem=problem.name,
        steps=tuple(reports),
        goal_reached=goal_reached,
        final_state=frozen,
        unmet_goals=tuple(a for a in problem.goal.atoms() if a not in frozen)
        if not goal_reached
        else (),
        warnings=tuple(warnings),
    )


def _check_types(
    action: Action, binding: dict[str, str], problem: Problem, domain: Domain
) -> str:
    """Every argument must be an object of the declared parameter type.

    Skipping this is the difference between validating a plan and replaying it:
    an untyped replay happily accepts `(navigate-bat waypoint1 rover0 ...)`,
    because the preconditions are just atom lookups and the atoms happen to
    exist in a symmetric initial state.
    """
    for (variable, declared), argument in zip(
        action.parameters, binding.values(), strict=True
    ):
        try:
            actual = problem.type_of(argument)
        except ParseError:
            return f"{argument!r} is not an object declared in the problem"
        if not domain.types.is_subtype(actual, declared):
            return f"{variable} expects type {declared!r} but {argument!r} is {actual!r}"
    return ""


def _explain(action: Action, binding: dict[str, str], state: Iterable[Atom]) -> str:
    """Name the unsatisfied atoms rather than saying "precondition failed".

    For a conjunction this is exact. For a disjunction it lists the atoms that
    were false, which is the information a modeller needs to see anyway.
    """
    state = set(state)
    missing = [
        atom.bind(binding)
        for atom in action.precondition.atoms()
        if atom.bind(binding) not in state
    ]
    if not missing:
        return f"precondition {action.precondition} is false under this binding"
    return (
        "unsatisfied: "
        + ", ".join(str(a) for a in missing[:6])
        + (f" (+{len(missing) - 6} more)" if len(missing) > 6 else "")
    )
