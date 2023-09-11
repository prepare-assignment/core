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
logger = logging.getLogger("prepare")


def __execute_action(file: str, inputs: Dict[str, str]) -> None:
    executable = sys.executable
    env = os.environ.copy()
    for key, value in inputs.items():
        sanitized = "PREPARE_" + key.replace(" ", "_").upper()
        env[sanitized] = value
    path = files().joinpath(f"../actions/{file}")
    result = subprocess.run([executable, path], capture_output=True, env=env)
    if result.returncode == 1:
        print(result.stderr)


def __execute_shell_command(command: str) -> None:
    args = shlex.split(f"bash -c {shlex.quote(command)}")
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode == 1:
        print(result.stderr)
    else:
        print(result)


def run(prepare: Dict[str, Any], mapping: Dict[str, ActionDefinition]) -> None:
    logger.debug("========== Running prepare assignment")
    for step, actions in prepare["steps"].items():
        logger.debug(f"Running step: {step}")
        for action in actions:
            # Check what kind of actions it is
            action_type = action.get("uses", None)
            if action_type is None:
                command = action.get("run")
                __execute_shell_command(command)
            else:
                uses = action.get("uses", None)
                action_definition = mapping.get(uses)
                inputs = action.get("with", {})
                for key, value in inputs.items():
                    inputs[key] = json.dumps(value)
                if isinstance(action_definition, PythonActionDefinition):
                    print("PythonAction")
                else:
                    print("CompositeAction")
    logger.debug("✓ Prepared :)")
