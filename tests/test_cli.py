import pytest

from pddl.cli import build_parser, main


def paths(root, domain, problem, plan):
    return [
        str(root / f"domains/{domain}.pddl"),
        str(root / f"problems/{problem}.pddl"),
        str(root / f"plans/{plan}.plan"),
    ]


def test_parser_requires_three_files():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["domain.pddl"])


def test_a_valid_plan_exits_zero(root, capsys):
    assert main(paths(root, "v1-battery", "v1-battery", "v1-battery")) == 0
    assert "VALID" in capsys.readouterr().out


def test_an_invalid_plan_exits_one(root, capsys):
    # Usable in CI: a model change that invalidates a stored plan fails a build.
    assert (
        main(
            paths(root, "v2-calibration-fix", "v2-calibration-fix", "uncalibrated-image")
        )
        == 1
    )
    assert "INVALID" in capsys.readouterr().out


def test_steps_are_printed_on_request(root, capsys):
    main([*paths(root, "v1-battery", "v1-battery", "v1-battery"), "--steps"])
    out = capsys.readouterr().out
    assert "1. ok" in out


def test_the_final_state_is_printed_on_request(root, capsys):
    main([*paths(root, "v1-battery", "v1-battery", "v1-battery"), "--final-state"])
    assert "final state:" in capsys.readouterr().out


def test_makespan_is_reported_for_a_timed_plan(root, capsys):
    main(paths(root, "v1-battery", "v1-battery", "v1-battery"))
    assert "makespan" in capsys.readouterr().out


def test_a_missing_file_is_a_usage_error(root, tmp_path, capsys):
    args = paths(root, "v1-battery", "v1-battery", "v1-battery")
    args[2] = str(tmp_path / "absent.plan")
    assert main(args) == 2
    assert "file not found" in capsys.readouterr().err


def test_a_malformed_file_is_a_usage_error(root, tmp_path, capsys):
    bad = tmp_path / "bad.pddl"
    bad.write_text("(define (domain broken)")
    args = paths(root, "v1-battery", "v1-battery", "v1-battery")
    args[0] = str(bad)
    assert main(args) == 2
    assert "parse error" in capsys.readouterr().err
