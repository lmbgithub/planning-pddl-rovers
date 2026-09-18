import pytest

from pddl.types import TypeError_, build_hierarchy, parse_typed_list


def test_untyped_names_default_to_object():
    assert parse_typed_list(["a", "b"]) == [("a", "object"), ("b", "object")]


def test_a_shared_type_applies_to_every_name_before_it():
    assert parse_typed_list(["a", "b", "-", "room"]) == [("a", "room"), ("b", "room")]


def test_several_groups():
    assert parse_typed_list(["a", "-", "x", "b", "c", "-", "y"]) == [
        ("a", "x"),
        ("b", "y"),
        ("c", "y"),
    ]


def test_trailing_names_after_a_group_are_objects():
    assert parse_typed_list(["a", "-", "x", "b"]) == [("a", "x"), ("b", "object")]


def test_a_dash_with_no_type_after_it_is_an_error():
    with pytest.raises(TypeError_, match="no type after"):
        parse_typed_list(["a", "-"])


def test_a_dash_with_no_names_before_it_is_an_error():
    with pytest.raises(TypeError_, match="no names before"):
        parse_typed_list(["-", "room"])


def test_an_empty_list_is_empty():
    assert parse_typed_list([]) == []


def test_everything_is_a_subtype_of_object():
    hierarchy = build_hierarchy([("rover", "vehicle")])
    assert hierarchy.is_subtype("rover", "object")
    assert hierarchy.is_subtype("anything-at-all", "object")


def test_a_type_is_a_subtype_of_itself():
    assert build_hierarchy([]).is_subtype("rover", "rover")


def test_subtyping_follows_the_chain():
    hierarchy = build_hierarchy([("rover", "vehicle"), ("vehicle", "object")])
    assert hierarchy.is_subtype("rover", "vehicle")
    assert not hierarchy.is_subtype("vehicle", "rover")


def test_unrelated_types_are_not_subtypes():
    hierarchy = build_hierarchy([("rover", "vehicle"), ("camera", "device")])
    assert not hierarchy.is_subtype("rover", "device")


def test_a_cyclic_hierarchy_raises_instead_of_hanging():
    hierarchy = build_hierarchy([("a", "b"), ("b", "a")])
    with pytest.raises(TypeError_, match="cyclic"):
        hierarchy.is_subtype("a", "c")
