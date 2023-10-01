import json
import logging
from typing import List
from urllib.parse import unquote_plus

from prepare_assignment.data.step_environment import StepEnvironment

logger = logging.getLogger("actions")


def handle_set_failed(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'set_failed'")
    logger.error(unquote_plus(params[0]))


def handle_set_output(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 2:
        raise AssertionError(f"Missing required params for 'set_failed'")
    message = params[1]
    output = json.loads(params[1])


def handle_error(environment: StepEnvironment, params: List[str]) -> None:
    handle_set_failed(environment, params)


def handle_warning(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'warning'")
    logger.error(unquote_plus(params[0]))


def handle_info(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'info'")
    logger.error(unquote_plus(params[0]))


def handle_debug(environment: StepEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'debug'")
    logger.error(unquote_plus(params[0]))


COMMAND_MAPPING = {
    "set-failed": handle_set_failed,
    "set-output": handle_set_output,
}
