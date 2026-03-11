import json
import logging
from typing import Dict, Any, Union, List

from simpleeval import InvalidExpression

from prepare_assignment.core.expression import evaluate
from prepare_assignment.data.constants import HAS_SUB_REGEX
from prepare_assignment.data.job_environment import JobEnvironment

tasks_logger = logging.getLogger("tasks")


def _to_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value)


def __substitute(value: str, environment: JobEnvironment, is_list: bool = False) -> Union[str, List[str]]:
    """
    Substitute ${{ }} expressions in a string with evaluated results.

    :param value: the string to substitute on
    :param environment: the environment to evaluate expressions against
    :param is_list: if True and the entire value is a single expression yielding a list, return the list
    :return: the substituted string, or the typed result if the whole string is one expression
    """
    blocks = list(HAS_SUB_REGEX.finditer(value))
    if not blocks:
        return value

    # If the entire value is exactly one ${{ }} block, return the typed result directly
    if len(blocks) == 1 and blocks[0].group("exp") == value.strip():
        content = blocks[0].group("content")
        try:
            result = evaluate(content, environment)
        except (InvalidExpression, Exception):
            tasks_logger.warning(f"Cannot evaluate expression '{content}'")
            return ""
        if is_list and isinstance(result, list):
            return result
        return _to_string(result)

    # Mixed string: interpolate each block as a string
    result_str = value
    offset = 0
    for block in blocks:
        content = block.group("content")
        try:
            replacement = evaluate(content, environment)
            repl_str = _to_string(replacement)
        except (InvalidExpression, Exception):
            tasks_logger.warning(f"Cannot evaluate expression '{content}'")
            repl_str = ""
        start = block.start("exp") + offset
        end = block.end("exp") + offset
        result_str = result_str[:start] + repl_str + result_str[end:]
        offset += len(repl_str) - (block.end("exp") - block.start("exp"))
    return result_str


def substitute_all(values: Dict[str, Any], environment: JobEnvironment) -> None:
    """
    Substitute (in-place) all ${{ }} expressions with the matching values.

    :param values: the inputs to check for expressions and substitute
    :param environment: the environment containing the substitutions
    :return: None
    """
    for key, value in values.items():
        if isinstance(value, str):
            values[key] = __substitute(value, environment)  # type: ignore
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], str):
            replacement = []
            for val in value:
                substituted = __substitute(val, environment, is_list=True)
                if isinstance(substituted, list):
                    replacement.extend(substituted)
                else:
                    replacement.append(substituted)
            values[key] = replacement
