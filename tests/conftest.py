from pathlib import Path

import pytest

from tests.fixtures import TOY_DOMAIN, TOY_PROBLEM

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def root() -> Path:
    return ROOT


@pytest.fixture
def toy_domain():
    from pddl.domain import parse_domain

    return parse_domain(TOY_DOMAIN)


@pytest.fixture
def toy_problem():
    from pddl.problem import parse_problem

    return parse_problem(TOY_PROBLEM)
