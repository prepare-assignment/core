import json
import logging
import shlex
from typing import Dict, Any

from prepare_assignment.data.constants import HAS_SUB_REGEX, SUB_REGEX
from prepare_assignment.data.step_environment import StepEnvironment

actions_logger = logging.getLogger("actions")


def __to_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value)


def __substitute(value: str, environment: StepEnvironment) -> str:
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
                substitution = environment.inputs.get(sub.group(sub_type), None)
            elif sub_type == "outputs":
                step = sub.group("step")
                output = sub.group("output")
                substitution = environment.outputs.get(step, {}).get(output, None)
            if substitution is None:
                actions_logger.warning(f"Cannot substitute '{sub.string}'")
                continue
            # TODO: check the type
            replacement["sub"] = __to_string(substitution)

    if len(substitutions) == 0:
        return value

    substitutions.append({
        "start": substitutions[-1]["end"],
        "end": len(value),
        "sub": value[substitutions[-1]["end"]:]
    })
    previous = 0
    result = ""
    for sub in substitutions:
        result += value[previous:sub["start"]] + sub["sub"]
        previous = sub["end"]
    return result


def substitute_all(values: Dict[str, Any], environment: StepEnvironment) -> None:
    for key, value in values.items():
        # For now, we only support it on string type
        if isinstance(value, str):
            values[key] = __substitute(value, environment)  # type: ignore
        elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], str):
            for idx, val in enumerate(value):
                value[idx] = __substitute(val, environment)
