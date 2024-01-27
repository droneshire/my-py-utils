import typing as T
import unittest

from ryutils.dict_util import (
    check_dict_keys_recursive,
    find_in_nested_dict,
    flatten_dict,
    patch_missing_keys_recursive,
    populate_typeddict_recursive,
    safe_get,
)


class NestedTypedDict(T.TypedDict):
    c: int
    d: str


class TestTypedDict(T.TypedDict):
    a: int
    b: str
    nested: NestedTypedDict


class UtilTest(unittest.TestCase):
    def setUp(self) -> None:
        pass

    def tearDown(self) -> None:
        pass

    def test_populate_typeddict(self) -> None:
        data = {
            "a": 1,
            "b": "2",
            "nested": {
                "c": 3,
                "d": "4",
            },
        }

        expected = TestTypedDict(
            a=1,
            b="2",
            nested=NestedTypedDict(
                c=3,
                d="4",
            ),
        )
        actual = populate_typeddict_recursive(data, TestTypedDict)
        self.assertEqual(expected, actual)

    def test_check_dict_keys_recursive(self) -> None:
        dict1 = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3,
            },
        }

        dict2 = {
            "a": 1,
            "b": {
                "c": 2,
            },
        }

        expected = ["d"]
        actual = check_dict_keys_recursive(dict1, dict2)
        self.assertEqual(expected, actual)

    def test_patch_missing_keys_recursive(self) -> None:
        dict1 = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3,
            },
        }

        dict2 = {
            "a": 1,
            "b": {
                "c": 2,
            },
        }

        expected = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3,
            },
        }
        actual = patch_missing_keys_recursive(dict1, dict2)
        self.assertEqual(expected, actual)

    def test_safe_get(self) -> None:
        dictionary = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3,
            },
        }

        expected = 2
        actual = safe_get(dictionary, ["b", "c"])
        self.assertEqual(expected, actual)

        expected2: T.Dict[T.Any, T.Any] = {}
        actual2 = safe_get(dictionary, ["b", "e"])
        self.assertEqual(expected2, actual2)

    def test_flatten_dict(self) -> None:
        dictionary = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3,
            },
        }

        expected = {
            "a": 1,
            "b.c": 2,
            "b.d": 3,
        }
        actual = flatten_dict(dictionary)
        self.assertEqual(expected, actual)

    def test_find_in_nested_dict(self) -> None:
        dictionary = {
            "a": 1,
            "b": {
                "c": 2,
                "d": 3,
            },
        }

        expected = 2
        actual = find_in_nested_dict(dictionary, "c")
        self.assertEqual(expected, actual)

        expected2 = None
        actual2 = find_in_nested_dict(dictionary, "e")
        self.assertEqual(expected2, actual2)
