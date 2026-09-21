import json
import logging
from json import JSONDecodeError
from typing import Any, List
from urllib.parse import unquote_plus

from prepare_assignment.data.job_environment import JobEnvironment
from prepare_assignment.data.types import is_of_type

logger = logging.getLogger("tasks")


def __handle_message(message: str) -> str:
    return unquote_plus(message).rstrip()


def handle_set_failed(environment: JobEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'set_failed'")
    message = __handle_message(params[0])
    logger.error(message)
    environment.task_errors.append(message)


def handle_set_output(environment: JobEnvironment, params: List[str]) -> None:
    if environment.current_task_definition is None:
        logger.warning("'set-output' is not supported for shell commands and will be ignored")
        return
    if len(params) < 2:
        raise AssertionError(f"Missing required params for 'set-output'")
    try:
        output = json.loads(params[1])
    except JSONDecodeError:
        raise AssertionError(f"'set_output' expects valid JSON params")
    if not isinstance(output, dict):
        raise AssertionError(f"'set_output' expects dictionary of key, value pairs")
    for key, value in output.items():
        definition = environment.current_task_definition.outputs.get(key, None)  # type: ignore
        if definition is None:
            logger.warning(f"Trying to set output '{key}', but is not defined in task. Skipping for now.")
            continue
        if not is_of_type(value, definition.type, definition.items):
            logger.warning(f"Output '{key}' is of type '{type(value)}', but expected '{definition.type}'")
            continue
        environment.outputs[environment.current_task.key][key] = value  # type: ignore


def handle_error(environment: JobEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'error'")
    logger.error(__handle_message(params[0]))


def handle_warning(environment: JobEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'warning'")
    logger.warning(__handle_message(params[0]))


def handle_info(environment: JobEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'info'")
    logger.info(__handle_message(params[0]))


def handle_debug(environment: JobEnvironment, params: List[str]) -> None:
    if len(params) < 1:
        raise AssertionError(f"Missing required message for 'debug'")
    logger.debug(__handle_message(params[0]))


def _env_value_to_string(value: Any) -> str:
    # Mirrors prepare_toolbox.utils.convert_to_string, so the task and subsequent steps see the same value
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return json.dumps(value)


def handle_set_env(environment: JobEnvironment, params: List[str]) -> None:
    """
    Set environment variables for all subsequent steps.

    Two formats are supported:
    - ``[name, json(value)]``: the value must be a JSON string
    - ``["", json({name: value, ...})]``: the format emitted by prepare-toolbox's ``set_env``,
      non-string values are converted to strings
    """
    if len(params) < 2:
        raise AssertionError(f"Missing required params for 'set-env'")
    name = unquote_plus(params[0]).strip()
    try:
        value = json.loads(params[1])
    except JSONDecodeError:
        raise AssertionError(f"'set-env' expects a JSON-encoded value as second param")
    if name:
        if not isinstance(value, str):
            raise AssertionError(f"'set-env' expects a string value")
        environment.environment[name] = value
        return
    if not isinstance(value, dict):
        raise AssertionError(f"'set-env' expects a variable name or a dictionary of key, value pairs")
    for key, val in value.items():
        if not isinstance(key, str) or not key:
            raise AssertionError(f"'set-env' expects non-empty variable names")
        environment.environment[key] = _env_value_to_string(val)


COMMAND_MAPPING = {
    "set-failed": handle_set_failed,
    "set-output": handle_set_output,
    "set-env": handle_set_env,
    "error": handle_error,
    "warning": handle_warning,
    "info": handle_info,
    "debug": handle_debug
}
