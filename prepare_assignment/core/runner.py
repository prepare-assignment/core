import copy
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
from prepare_assignment.data.task_definition import TaskDefinition, PythonTaskDefinition
from prepare_assignment.data.constants import BASH_EXECUTABLE
from prepare_assignment.data.prepare import Prepare, Task
from prepare_assignment.data.job_environment import JobEnvironment
from prepare_assignment.data.task_properties import TaskProperties

# Get the logger
logger = logging.getLogger("prepare_assignment")
tasks_logger = logging.getLogger("tasks")


def __process_output_line(line: str, environment: JobEnvironment) -> None:
    if line.startswith(DEMARCATION):
        parts = line.split(DEMARCATION)
        if len(parts) <= 1:
            return
        command = parts[1]
        handler = COMMAND_MAPPING.get(command, None)
        if not handler:
            logger.warning(f"Found command '{command}', "
                           f"but this version of prepare assignment has no handler registered")
            return
        params = parts[2:]
        handler(environment, params)
    else:
        tasks_logger.trace(line)  # type: ignore


def __execute_task(environment: JobEnvironment) -> None:
    logger.debug(f"Executing task '{environment.current_task.name}'")  # type: ignore
    task: PythonTaskDefinition = environment.current_task_definition   # type: ignore
    venv_path = os.path.join(task.path, "venv")
    main_path = os.path.join(task.path, "repo", task.main)
    executable: str
    if sys.platform == "win32":
        executable = os.path.join(venv_path, "Scripts", "python.exe")
    else:
        executable = os.path.join(venv_path, "bin", "python")
    
    env = environment.environment.copy()
    env["VIRTUAL_ENV"] = venv_path
    for key, value in environment.current_task.with_.items():  # type: ignore
        sanitized = "PREPARE_" + key.replace(" ", "_").upper()
        env[sanitized] = json.dumps(value)
    for inp in task.inputs:
        if inp.default is not None and not inp.name in environment.current_task.with_.keys():  # type: ignore
            sanitized = "PREPARE_" + inp.name.replace(" ", "_").upper()
            env[sanitized] = json.dumps(inp.default)
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


def __execute_shell_command(command: str, env: Dict[str, str]) -> None:
    logger.debug(f"Executing run '{command}'")  # type: ignore
    args = shlex.split(f"-c {shlex.quote(command)}")
    args.insert(0, BASH_EXECUTABLE)
    with subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True,
        env=env
    ) as process:
        if process.stdout is None:
            return
        for line in process.stdout:
            tasks_logger.trace(line)  # type: ignore


def __handle_task(mapping: Dict[str, TaskDefinition],
                  task: Task,
                  environment: JobEnvironment) -> None:
    # Check what kind of task it is
    if task.is_run:
        command = __substitute(task.run, environment)  # type: ignore
        __execute_shell_command(command, environment.environment)  # type: ignore
    else:
        task_properties = TaskProperties.of(task.uses)  # type: ignore
        task_definition = mapping.get(str(task_properties))
        substitute_all(task.with_, environment)  # type: ignore
        if task_definition.is_composite:  # type: ignore
            sub_env = environment.environment.copy()
            sub_environment = JobEnvironment(sub_env, outputs={}, inputs=task.with_)  # type: ignore
            for subtask in task_definition.tasks:  # type: ignore
                subtask = copy.deepcopy(subtask)
                subtask = Task.of(subtask)
                __handle_task(mapping, subtask, sub_environment)
        else:
            environment.current_task_definition = task_definition  # type: ignore
            environment.current_task = task
            environment.outputs[task.key] = {}
            __execute_task(environment)


def run(prepare: Prepare, mapping: Dict[str, TaskDefinition]) -> None:
    logger.debug("========== Running prepare_assignment assignment")
    for job, tasks in prepare.jobs.items():
        logger.debug(f"Running job: {job}")
        env = os.environ.copy()
        step_env = JobEnvironment(env, {}, {})
        for task in tasks:
            __handle_task(mapping, task, step_env)

    logger.debug("✓ Prepared :)")
