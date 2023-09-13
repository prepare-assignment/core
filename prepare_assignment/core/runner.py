import json
import logging
import os.path
import shlex
import subprocess
import sys
from typing import Any, Dict

from importlib_resources import files

from prepare_assignment.data.action_definition import ActionDefinition, PythonActionDefinition

# Get the logger
logger = logging.getLogger("prepare_assignment")


def __execute_action(action: PythonActionDefinition, inputs: Dict[str, str]) -> None:
    venv_path = os.path.join(action.path, "venv")
    main_path = os.path.join(action.path, "repo", action.main)
    executable = os.path.join(venv_path, "bin", "python")
    env = os.environ.copy()
    env["VIRTUAL_ENV"] = venv_path
    for key, value in inputs.items():
        sanitized = "PREPARE_" + key.replace(" ", "_").upper()
        env[sanitized] = value
    result = subprocess.run([executable, main_path], capture_output=True, env=env)
    if result.returncode == 1:
        logger.error(f"Failed to execute '{action.name}', action failed with status code {result.returncode}")
        if result.stderr:
            logger.error(result.stderr.decode("utf-8"))
        if not result.stderr and result.stdout:
            logger.error(result.stdout.decode("utf-8"))


def __execute_shell_command(command: str) -> None:
    args = shlex.split(f"bash -c {shlex.quote(command)}")
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 1:
        print(result.stderr)
    else:
        print(result)


def __handle_action(mapping: Dict[str, ActionDefinition], action: Any, inputs: Dict[str, Any]) -> None:
    # TODO: Command substitution
    for key, value in inputs.items():
        inputs[key] = json.dumps(value)
    # Check what kind of actions it is
    action_type = action.get("uses", None)
    if action_type is None:
        command = action.get("run")
        __execute_shell_command(command)
    else:
        uses = action.get("uses", None)
        action_definition = mapping.get(uses)

        if isinstance(action_definition, PythonActionDefinition):
            __execute_action(action_definition, inputs)
        else:
            for act in action_definition.steps:  # type: ignore
                __handle_action(mapping, act, inputs)


def run(prepare: Dict[str, Any], mapping: Dict[str, ActionDefinition]) -> None:
    logger.debug("========== Running prepare_assignment assignment")
    for step, actions in prepare["steps"].items():
        logger.debug(f"Running step: {step}")
        for action in actions:
            inputs = action.get("with", {})
            __handle_action(mapping, action, inputs)

    logger.debug("✓ Prepared :)")
