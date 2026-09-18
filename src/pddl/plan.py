"""Reading plan files, in the two shapes planners emit.

    0.00000: (navigate-bat rover0 waypoint3 waypoint1 bat0 b4 b4 b3)
    (navigate-bat rover0 waypoint3 waypoint1 bat0 b4 b4 b3)

Trailing `; Makespan:` comments are dropped by the tokenizer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pddl.sexpr import ParseError, parse

_TIMESTAMP = re.compile(r"^\s*[-+]?\d+(\.\d+)?\s*:\s*")


@dataclass(frozen=True, slots=True)
class Step:
    """One grounded action instance, with the time the planner gave it."""

    name: str
    arguments: tuple[str, ...]
    time: float | None = None

    def __str__(self) -> str:
        return f"({' '.join((self.name, *self.arguments))})"


@dataclass(frozen=True, slots=True)
class Plan:
    steps: tuple[Step, ...]

    def __len__(self) -> int:
        return len(self.steps)

    @property
    def makespan(self) -> float | None:
        """The last timestamp, or None for an untimed plan.

        Deliberately *not* the plan length: for a sequential plan they are
        proportional and confusing them is harmless, but the moment a planner
        emits concurrent steps they are different numbers answering different
        questions.
        """
        times = [s.time for s in self.steps if s.time is not None]
        return max(times) if times else None


def parse_plan(text: str) -> Plan:
    steps: list[Step] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.split(";", 1)[0].strip()
        if not stripped:
            continue

        time: float | None = None
        match = _TIMESTAMP.match(stripped)
        if match:
            time = float(match.group(0).rstrip(": ").strip())
            stripped = stripped[match.end() :]

        forms = parse(stripped)
        if len(forms) != 1 or not isinstance(forms[0], list) or not forms[0]:
            raise ParseError(
                f"line {line_number}: expected one grounded action, got {line!r}"
            )
        name, *arguments = forms[0]
        if not all(isinstance(a, str) for a in arguments):
            raise ParseError(f"line {line_number}: action arguments must be object names")
        steps.append(Step(name=name, arguments=tuple(arguments), time=time))

    return Plan(tuple(steps))


def parse_plan_file(path: str | Path) -> Plan:
    return parse_plan(Path(path).read_text(encoding="utf-8"))
