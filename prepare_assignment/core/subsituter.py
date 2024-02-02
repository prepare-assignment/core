import json
import logging
from typing import Dict, Any, Union, List

from prepare_assignment.data.constants import HAS_SUB_REGEX, SUB_REGEX
from prepare_assignment.data.job_environment import JobEnvironment

tasks_logger = logging.getLogger("tasks")


def __to_string(value: Any) -> str:
    """
    Convert a value to string for substitution.
    We assume we only have the types that are valid in our yaml files, for more info see the schemas.
    The following conversions happen:
    - string -> keep as is
    - int, float, bool -> use built in toString
    - list -> 'json.dumps'


    :param value: the value to convert
    :return: the value as a string
    """
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value)


def __substitute(value: str, environment: JobEnvironment, is_list: bool = False) -> Union[str, List[str]]:
    """
    Substitute commands in a string with the matching values from the environment.
    ${{ inputs.<name> }} -> replace with the matching input
    ${{ tasks.<task>.outputs.<name>}} -> replace with the matching output of the correct task

    :param value: the string to substitute on
    :param environment: the environment to take the values from
    :return: the substituted string, or the original in case there is no command present
    """
    # Find all ${{ }}
    substitutions = []
    for expression in HAS_SUB_REGEX.finditer(value):
        replacement = {"start": expression.start("exp"), "end": expression.end("exp"), "sub": ""}
        substitutions.append(replacement)
        # See what command substitution we need: "inputs", "outputs"
        for sub in SUB_REGEX.finditer(expression.group("content")):
            # lastgroup contains the name of the matched group
            sub_type = sub.lastgroup
            substitution = None
            if sub_type == "inputs":
                substitution_name = sub.group(sub_type)
                substitution = environment.inputs.get(substitution_name, None)
            elif sub_type == "outputs":
                step = sub.group("step")
                output = sub.group("output")
                substitution = environment.outputs.get(step, {}).get(output, None)
            if substitution is None:
                tasks_logger.warning(f"Cannot substitute '{sub.string}'")
                continue
            # TODO: check the type
            if is_list and isinstance(substitution, list) and replacement["end"] - replacement["start"] == len(value):  # type: ignore
                return substitution
            replacement["sub"] = __to_string(substitution)

    if len(substitutions) == 0:
        return value

    substitutions.append({
        "start": substitutions[-1]["end"],
        "end": len(value),
        "sub": value[substitutions[-1]["end"]:]  # type: ignore
    })
    previous = 0
    result = ""
    for sub in substitutions:
        result += value[previous:sub["start"]] + sub["sub"]
        previous = sub["end"]
    return result


def substitute_all(values: Dict[str, Any], environment: JobEnvironment) -> None:
    """
    Substitute (in-place) all commands with the matching values.

    :param values: the inputs to check for commands and substitute
    :param environment: the environment containing the substitutions
    :return: None
    """
    for key, value in values.items():
        # For now, we only support it on string type
        if isinstance(value, str):
            values[key] = __substitute(value, environment)  # type: ignore
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], str):
            replacement = []
            for idx, val in enumerate(value):
                substituted = __substitute(val, environment, is_list=True)
                if isinstance(substituted, list):
                    replacement.extend(substituted)
                else:
                    replacement.append(substituted)
            values[key] = replacement
