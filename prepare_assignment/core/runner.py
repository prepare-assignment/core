import copy
import json
import logging
import os.path
import subprocess
import sys
import threading
from collections import deque
from typing import Any, Deque, Dict, Final, Iterable, List, Optional

from prepare_toolbox.command import DEMARCATION

from prepare_assignment.core.command import COMMAND_MAPPING
from prepare_assignment.core.expression import evaluate_condition, evaluate
from prepare_assignment.core.shell import Command, shell_command
from prepare_assignment.core.subsituter import substitute_all, __substitute
from prepare_assignment.data.task_definition import TaskDefinition, PythonTaskDefinition, CompositeTaskDefinition
from prepare_assignment.data.constants import CONFIG
from prepare_assignment.data.prepare import Prepare, Task, RunTask
from prepare_assignment.data.job_environment import JobEnvironment
from prepare_assignment.data.errors import TaskExecutionError, ExpressionError
from prepare_assignment.data.task_properties import TaskProperties

# Get the logger
logger = logging.getLogger("prepare_assignment")
tasks_logger = logging.getLogger("tasks")

# Number of stderr lines that are included in the error message when a process fails
STDERR_TAIL_LINES: Final[int] = 20


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
        try:
            handler(environment, params)
        except AssertionError as e:
            logger.error(f"Invalid command '{command}': {e}")
            environment.task_errors.append(f"Invalid command '{command}': {e}")
    else:
        tasks_logger.trace(line)  # type: ignore


def __read_stderr(stream: Iterable[str], tail: Deque[str]) -> None:
    for line in stream:
        tasks_logger.trace(f"[stderr] {line}")  # type: ignore
        tail.append(line.rstrip())


def __run_process(args: Command, environment: JobEnvironment, env: Dict[str, str], description: str) -> None:
    """
    Run a process, stdout is parsed for commands, stderr is only logged (and reported if the process fails)

    :raises TaskExecutionError: if the process fails or reports errors
    """
    cwd = environment.working_directory
    if cwd is not None and not os.path.isdir(cwd):
        raise TaskExecutionError(f"{description} failed: working directory '{cwd}' doesn't exist")
    stderr_tail: Deque[str] = deque(maxlen=STDERR_TAIL_LINES)
    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=1,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=cwd
        )
    except OSError as e:
        raise TaskExecutionError(f"{description} could not be started: {e}") from e
    with process:
        reader: Optional[threading.Thread] = None
        if process.stderr is not None:
            reader = threading.Thread(target=__read_stderr, args=(process.stderr, stderr_tail), daemon=True)
            reader.start()
        if process.stdout is not None:
            # Commands are handled on this thread, so the environment is only modified from one thread
            for line in process.stdout:
                __process_output_line(line, environment)
        if reader is not None:
            reader.join()
    if process.returncode != 0:
        message = f"{description} exited with code {process.returncode}"
        if len(stderr_tail) > 0:
            message += "\n\t" + "\n\t".join(stderr_tail)
        raise TaskExecutionError(message)
    if environment.task_errors:
        raise TaskExecutionError(f"{description} failed: " + "; ".join(environment.task_errors))


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

    env = environment.process_environment
    env["VIRTUAL_ENV"] = venv_path
    # Make sure the task can always print (non-ascii) output, regardless of the platform encoding
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    for key, value in environment.current_task.with_.items():  # type: ignore
        sanitized = "PREPARE_" + key.replace(" ", "_").upper()
        env[sanitized] = json.dumps(value)
    for inp in task.inputs:
        if inp.default is not None and not inp.name in environment.current_task.with_.keys():  # type: ignore
            sanitized = "PREPARE_" + inp.name.replace(" ", "_").upper()
            env[sanitized] = json.dumps(inp.default)
    __run_process([executable, main_path], environment, env, f"Task '{environment.current_task.name}'")  # type: ignore


def __execute_shell_command(command: str, shell: str, environment: JobEnvironment) -> None:
    logger.debug(f"Executing run ({shell}) '{command}'")
    with shell_command(shell, command) as args:
        __run_process(args, environment, environment.process_environment, f"Shell command '{command}'")


def __should_skip(task: Task, environment: JobEnvironment) -> bool:
    """
    :raises TaskExecutionError: if the 'if' expression cannot be evaluated
    """
    if task.if_ is None:
        if environment.job_failed:
            logger.debug(f"Skipping task '{task.name}' (previous task failed)")
            return True
        return False
    try:
        if not evaluate_condition(task.if_, environment):
            logger.debug(f"Skipping task '{task.name}' (if condition is false)")
            return True
    except ExpressionError as e:
        raise TaskExecutionError(f"Invalid 'if' for task '{task.name}': {e.message}") from e
    return False


def __handle_task(mapping: Dict[str, TaskDefinition],
                  task: Task,
                  environment: JobEnvironment) -> None:
    # The step's 'env' and 'working-directory' only apply to this step
    previous_overlay = environment.env_overlay
    previous_working_directory = environment.working_directory
    try:
        env_overlay = {key: str(__substitute(value, environment)) for key, value in task.env.items()}
        environment.env_overlay = {**previous_overlay, **env_overlay}
        if task.working_directory is not None:
            working_directory = str(__substitute(task.working_directory, environment))
            environment.working_directory = os.path.join(previous_working_directory or os.getcwd(),
                                                         working_directory)
        __handle_task_unchecked(mapping, task, environment)
    except ExpressionError as e:
        raise TaskExecutionError(f"Task '{task.name}' failed: {e.message}") from e
    finally:
        environment.env_overlay = previous_overlay
        environment.working_directory = previous_working_directory


def __handle_task_unchecked(mapping: Dict[str, TaskDefinition],
                            task: Task,
                            environment: JobEnvironment) -> None:
    environment.task_errors = []
    # Check what kind of task it is
    if isinstance(task, RunTask):
        command = str(__substitute(task.run, environment))
        __execute_shell_command(command, task.shell or CONFIG.core.shell, environment)
        return
    task_properties = TaskProperties.of(task.uses)  # type: ignore
    task_definition = mapping.get(str(task_properties))
    substitute_all(task.with_, environment)  # type: ignore
    if isinstance(task_definition, CompositeTaskDefinition):
        # Declared inputs that are not supplied (and have no default) are available as None,
        # so only undeclared inputs (typos) raise an error
        inputs = {inp.name: None for inp in task_definition.inputs}
        inputs.update(task.with_)  # type: ignore
        # The environment is shared, so environment variables set by sub-tasks are available afterwards
        sub_environment = JobEnvironment(environment.environment, outputs={}, inputs=inputs,
                                         env_overlay=environment.env_overlay,
                                         working_directory=environment.working_directory)
        subtasks = [Task.of(copy.deepcopy(subtask)) for subtask in task_definition.tasks]
        __run_steps(mapping, subtasks, sub_environment)
        if sub_environment.job_failed:
            environment.outputs[task.key] = {name: None for name in task_definition.outputs}
            raise TaskExecutionError(f"Composite action '{task.name}' failed")
        outputs: Dict[str, Any] = {}
        for name, definition in task_definition.outputs.items():
            outputs[name] = None if definition.value is None else evaluate(definition.value, sub_environment)
        environment.outputs[task.key] = outputs
    else:
        environment.current_task_definition = task_definition  # type: ignore
        environment.current_task = task
        # Declared outputs that are not set by the task are available as None
        environment.outputs[task.key] = {name: None for name in task_definition.outputs}  # type: ignore
        __execute_task(environment)


def __run_steps(mapping: Dict[str, TaskDefinition], tasks: List[Task], environment: JobEnvironment) -> None:
    for task in tasks:
        try:
            if __should_skip(task, environment):
                continue
            __handle_task(mapping, task, environment)
        except TaskExecutionError as e:
            if task.continue_on_error:
                logger.warning(f"{e} (ignored, 'continue-on-error' is set)")
            else:
                logger.error(str(e))
                environment.job_failed = True


def run(prepare: Prepare, mapping: Dict[str, TaskDefinition], env_vars: Optional[Dict[str, str]] = None) -> None:
    env_vars = env_vars or {}
    logger.debug("========== Running prepare_assignment assignment")
    for job, tasks in prepare.jobs.items():
        logger.debug(f"Running job: {job}")
        env = {**os.environ.copy(), **env_vars}
        step_env = JobEnvironment(env, {}, {})
        __run_steps(mapping, tasks, step_env)
        if step_env.job_failed:
            raise TaskExecutionError(f"Job '{job}' failed")

    logger.debug("✓ Prepared :)")
