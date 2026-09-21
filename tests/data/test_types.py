from typing import Any, Optional

import pytest

from prepare_assignment.data.types import is_of_type


@pytest.mark.parametrize("value, type_name, items, expected", [
    ("a", "string", None, True),
    (1, "string", None, False),
    (1, "integer", None, True),
    (True, "integer", None, False),
    (1.5, "integer", None, False),
    (1, "number", None, True),
    (1.5, "number", None, True),
    (False, "number", None, False),
    (True, "boolean", None, True),
    (0, "boolean", None, False),
    (["a"], "array", None, True),
    (["a"], "array", "string", True),
    (["a", 1], "array", "string", False),
    ([1, 2.5], "array", "number", True),
    ("a", "array", None, False),
    ("a", "unknown", None, False),
])
def test_is_of_type(value: Any, type_name: str, items: Optional[str], expected: bool) -> None:
    assert is_of_type(value, type_name, items) is expected
