import json
import logging
import os.path
import shlex
import subprocess
from subprocess import Popen, PIPE
from typing import Any, Dict

from prepare_toolbox.command import DEMARCATION

from prepare_assignment.core.command import COMMAND_MAPPING
from prepare_assignment.data.action_definition import ActionDefinition, PythonActionDefinition
from prepare_assignment.data.prepare import Prepare, Action, ActionInput, UsesAction
from prepare_assignment.data.step_environment import StepEnvironment

# Get the logger
logger = logging.getLogger("prepare_assignment")
actions_logger = logging.getLogger("actions")


def __process_output_line(line: str, environment: StepEnvironment) -> None:
    if line.startswith(DEMARCATION):
        parts = line.split(DEMARCATION)
        if len(parts) <= 1:
            return
        command = parts[1]
        handler = COMMAND_MAPPING.get(command, None)
        if not handler:
            logger.warning(f"Found command '{command}', but this version of prepare assignment has no handler registered")
            return
        params = parts[2:]
        handler(environment, params)
    else:
        actions_logger.trace(line)


def __execute_action(inputs: Dict[str, str], environment: StepEnvironment) -> None:
    action = environment.current_action_definition
    venv_path = os.path.join(action.path, "venv")
    main_path = os.path.join(action.path, "repo", action.main)
    executable = os.path.join(venv_path, "bin", "python")
    env = environment.environment.copy()
    env["VIRTUAL_ENV"] = venv_path
    for key, value in inputs.items():
        sanitized = "PREPARE_" + key.replace(" ", "_").upper()
        env[sanitized] = value
    with Popen(
        [executable, main_path],
        stdout=PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
        env=env
    ) as process:
        for line in process.stdout:
            __process_output_line(line, environment)
    if process.returncode != 0:
        print("Error code: 1")  # TODO: What to do if process fails?


def __execute_shell_command(command: str) -> None:
    args = shlex.split(f"bash -c {shlex.quote(command)}")
    with Popen(
        args,
        stdout=PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True
    ) as process:
        for line in process.stdout:
            actions_logger.trace(line)


def __handle_action(mapping: Dict[str, ActionDefinition], action: Action, inputs: Dict[str, ActionInput], environment: StepEnvironment) -> None:
    # TODO: Command substitution
    for key, value in inputs.items():
        inputs[key] = json.dumps(value)
    # Check what kind of actions it is
    if action.is_run:
        __execute_shell_command(action.run)  # type: ignore
    else:
        action_definition = mapping.get(action.uses)  # type: ignore

        if action_definition.is_composite:
            for act in action_definition.steps:  # type: ignore
                __handle_action(mapping, act, inputs, environment)
        else:
            environment.current_action_definition = action_definition
            environment.current_action = action
            environment.output[action.key] = {}
            __execute_action(inputs, environment)


def run(prepare: Prepare, mapping: Dict[str, ActionDefinition]) -> None:
    logger.debug("========== Running prepare_assignment assignment")
    for step, actions in prepare.steps.items():
        logger.debug(f"Running step: {step}")
        env = os.environ.copy()
        output: Dict[str, str] = {}
        step_env = StepEnvironment(env, output)
        for action in actions:
            inputs = {} if action.is_run else action.with_  # type: ignore
            __handle_action(mapping, action, inputs, step_env)

    logger.debug("✓ Prepared :)")
