import unittest

from ryutils.dict_util import add_item, recursive_replace


class TestRecursiveReplace(unittest.TestCase):

    def test_recursive_replace_in_dict(self) -> None:
        data = {"a": 1, "b": {"c": 2, "d": {"e": 3, "f": 4}}}
        expected = {"a": 1, "b": {"c": 2, "d": {"e": "new_value", "f": 4}}}
        result = recursive_replace(data, "e", "new_value")
        self.assertEqual(result, expected)

    def test_recursive_replace_in_list(self) -> None:
        data = [{"a": 1, "b": {"c": 2}}, {"a": 3, "b": {"c": 4}}]
        expected = [{"a": 1, "b": {"c": "new_value"}}, {"a": 3, "b": {"c": "new_value"}}]
        result = recursive_replace(data, "c", "new_value")
        self.assertEqual(result, expected)

    def test_recursive_replace_mixed(self) -> None:
        data = {"a": 1, "b": [{"c": 2, "d": {"e": 3}}, {"c": 4, "d": {"e": 5}}]}
        expected = {
            "a": 1,
            "b": [{"c": "new_value", "d": {"e": 3}}, {"c": "new_value", "d": {"e": 5}}],
        }
        result = recursive_replace(data, "c", "new_value")
        self.assertEqual(result, expected)

    def test_recursive_replace_no_match(self) -> None:
        data = {"a": 1, "b": {"c": 2, "d": {"e": 3, "f": 4}}}
        expected = data.copy()
        result = recursive_replace(data, "x", "new_value")
        self.assertEqual(result, expected)


class TestAddItem(unittest.TestCase):

    def test_add_item_to_empty_dict(self) -> None:
        data: dict = {}
        expected = {"a": "new_value"}
        result = add_item(data, "a", "new_value")
        self.assertEqual(result, expected)

    def test_add_item_to_nested_dict(self) -> None:
        data = {"a": {"b": {"c": 1}}}
        expected = {"a": {"b": {"c": 1, "d": "new_value"}}}
        result = add_item(data, "a.b.d", "new_value")
        self.assertEqual(result, expected)

    def test_add_item_creates_nested_dict(self) -> None:
        data: dict = {}
        expected = {"a": {"b": {"c": "new_value"}}}
        result = add_item(data, "a.b.c", "new_value")
        self.assertEqual(result, expected)

    def test_add_item_overwrites_existing_value(self) -> None:
        data = {"a": {"b": {"c": 1}}}
        expected = {"a": {"b": {"c": "new_value"}}}
        result = add_item(data, "a.b.c", "new_value")
        self.assertEqual(result, expected)
