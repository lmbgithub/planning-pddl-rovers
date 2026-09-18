import pytest

from pddl.sexpr import ParseError, find, head, parse, parse_one, tokenize


def test_nested_forms():
    assert parse_one("(a (b c) d)") == ["a", ["b", "c"], "d"]


def test_symbols_are_lowercased():
    # PDDL is case-insensitive; normalising here means no comparison downstream
    # can silently fail because a problem wrote ROVER0 and a plan wrote rover0.
    assert parse_one("(At ROVER0 Waypoint1)") == ["at", "rover0", "waypoint1"]


def test_comments_run_to_the_end_of_the_line():
    assert parse_one("(a ; ignored (b c)\n d)") == ["a", "d"]


def test_a_comment_only_file_has_no_forms():
    assert parse("; nothing here\n; nor here\n") == []


def test_tokens_carry_line_numbers():
    tokens = tokenize("(a\n b)")
    assert [t.line for t in tokens] == [1, 1, 2, 2]


def test_multiple_top_level_forms():
    assert len(parse("(a) (b)")) == 2


def test_parse_one_rejects_a_second_form():
    # A domain file with two (define ...) forms would otherwise silently use
    # the first and ignore the rest.
    with pytest.raises(ParseError, match="exactly one"):
        parse_one("(a) (b)")


def test_parse_one_rejects_an_empty_file():
    with pytest.raises(ParseError, match="exactly one"):
        parse_one("")


def test_unclosed_paren_names_its_line():
    with pytest.raises(ParseError, match="line 2"):
        parse("(a\n(b c")


def test_unexpected_close_paren_names_its_line():
    with pytest.raises(ParseError, match="line 1"):
        parse("(a))")


def test_empty_list_is_a_form():
    assert parse_one("()") == []


def test_find_returns_the_named_section():
    form = parse_one("(define (domain d) (:types a b) (:predicates (p)))")
    assert find(form, ":types") == [":types", "a", "b"]


def test_find_returns_none_for_a_missing_section():
    assert find(parse_one("(define)"), ":types") is None


def test_find_on_an_atom_is_none():
    assert find("atom", ":types") is None


def test_head_of_an_atom_is_itself():
    assert head("atom") == "atom"
    assert head(["and", "x"]) == "and"
    assert head([]) == "<list>"
