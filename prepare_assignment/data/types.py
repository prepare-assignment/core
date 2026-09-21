from typing import Any, Optional


def is_of_type(value: Any, type_name: str, items: Optional[str] = None) -> bool:
    """
    Check if a value matches one of the task input/output types (json schema semantics)

    :param value: the value to check
    :param type_name: one of 'string', 'number', 'integer', 'boolean' or 'array'
    :param items: for arrays, the type of the items (optional)
    :return: True if the value is of the given type
    """
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "boolean":
        return isinstance(value, bool)
    # bool is a subclass of int in python, but not a number in json schema
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if type_name == "array":
        if not isinstance(value, list):
            return False
        return items is None or all(is_of_type(item, items) for item in value)
    return False
