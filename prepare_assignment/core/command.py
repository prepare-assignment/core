import ast
import json
import logging
import re
from json import JSONDecodeError
from typing import List
from urllib.parse import unquote_plus

from prepare_assignment.data.constants import TYPE_MAPPING
from prepare_assignment.data.step_environment import StepEnvironment

logger = logging.getLogger("actions")


def __handle_message(message: str) -> str:
    return unquote_plus(message).rstrip()


def handle_set_failed(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'set_failed'")
    logger.error(__handle_message(params[0]))


def handle_set_output(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 2:
        raise AssertionError(f"Missing required params for 'set_failed'")
    message = params[0]
    try:
        output = json.loads(params[1])
    except JSONDecodeError as e:
        raise AssertionError(f"'set_output' expects valid JSON params")
    if not isinstance(output, dict):
        raise AssertionError(f"'set_output' expects dictionary of key, value pairs")
    for key, value in output.items():
        definition = environment.current_action_definition.outputs.get(key, None)  # type: ignore
        if definition is None:
            logger.warning(f"Trying to set output '{key}', but is not defined in action. Skipping for now.")
            break
        expected_type = TYPE_MAPPING.get(definition.type, None)
        if expected_type is None or not isinstance(value, expected_type):
            logger.warning(f"Output '{key}' is of type '{type(value)}', but expected '{definition.type}'")
            break
        environment.outputs[environment.current_action.key][key] = value  # type: ignore


def handle_error(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'warning'")
    logger.error(__handle_message(params[0]))


def handle_warning(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'warning'")
    logger.warning(__handle_message(params[0]))


def handle_info(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'info'")
    logger.info(__handle_message(params[0]))


def handle_debug(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'debug'")
    logger.debug(__handle_message(params[0]))


COMMAND_MAPPING = {
    "set-failed": handle_set_failed,
    "set-output": handle_set_output,
    "error": handle_error,
    "warning": handle_warning,
    "info": handle_info,
    "debug": handle_debug
}
