import json
import logging
import os.path
import shlex
import subprocess
import sys
from typing import Dict

from prepare_toolbox.command import DEMARCATION

from prepare_assignment.core.command import COMMAND_MAPPING
from prepare_assignment.core.subsituter import substitute_all, __substitute
from prepare_assignment.data.action_definition import ActionDefinition, PythonActionDefinition
from prepare_assignment.data.prepare import Prepare, Action
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
        actions_logger.trace(line)  # type: ignore


def __execute_action(environment: StepEnvironment) -> None:
    logger.debug(f"Executing action '{environment.current_action.name}'")  # type: ignore
    action: PythonActionDefinition = environment.current_action_definition   # type: ignore
    venv_path = os.path.join(action.path, "venv")
    main_path = os.path.join(action.path, "repo", action.main)
    executable: str
    if sys.platform == "win32":
        executable = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        executable = os.path.join(venv_path, "bin", "python")
    
    env = environment.environment.copy()
    env["VIRTUAL_ENV"] = venv_path
    for key, value in environment.current_action.with_.items():  # type: ignore
        sanitized = "PREPARE_" + key.replace(" ", "_").upper()
        env[sanitized] = json.dumps(value)
    with subprocess.Popen(
        [executable, main_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
        env=env
    ) as process:
        if process.stdout is None:
            return
        for line in process.stdout:
            __process_output_line(line, environment)
    if process.returncode != 0:
        print("Error code: 1")  # TODO: What to do if process fails?


def __execute_shell_command(command: str) -> None:
    logger.debug(f"Executing run '{command}'")  # type: ignore
    print(f"bash -c {shlex.quote(command)}")
    args = shlex.split(f"bash -c {shlex.quote(command)}")
    with subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True
    ) as process:
        if process.stdout is None:
            return
        for line in process.stdout:
            actions_logger.trace(line)  # type: ignore


def __handle_action(mapping: Dict[str, ActionDefinition],
                    action: Action,
                    environment: StepEnvironment) -> None:
    # Check what kind of actions it is
    if action.is_run:
        command = __substitute(action.run, environment)  # type: ignore
        __execute_shell_command(command)
    else:
        action_definition = mapping.get(action.uses)  # type: ignore
        substitute_all(action.with_, environment)  # type: ignore
        if action_definition.is_composite:  # type: ignore
            sub_env = environment.environment.copy()
            sub_environment = StepEnvironment(sub_env, outputs={}, inputs=action.with_)  # type: ignore
            for act in action_definition.steps:  # type: ignore
                act = Action.of(act)
                __handle_action(mapping, act, sub_environment)
        else:
            environment.current_action_definition = action_definition  # type: ignore
            environment.current_action = action
            environment.outputs[action.key] = {}
            __execute_action(environment)


def run(prepare: Prepare, mapping: Dict[str, ActionDefinition]) -> None:
    logger.debug("========== Running prepare_assignment assignment")
    for step, actions in prepare.steps.items():
        logger.debug(f"Running step: {step}")
        env = os.environ.copy()
        step_env = StepEnvironment(env, {}, {})
        for action in actions:
            __handle_action(mapping, action, step_env)

    logger.debug("✓ Prepared :)")
