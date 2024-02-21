import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

from git import Repo
from importlib_resources import files
from virtualenv import cli_run

from prepare_assignment.data.constants import CONFIG
from prepare_assignment.core.validator import validate_task_definition, validate_tasks, load_yaml, \
    validate_default_values
from prepare_assignment.data.errors import DependencyError, ValidationError, PrepareTaskError
from prepare_assignment.data.task_definition import TaskDefinition, CompositeTaskDefinition, \
    PythonTaskDefinition, ValidableTask
from prepare_assignment.data.task_properties import TaskProperties
from prepare_assignment.utils.cache import get_cache_path, get_tasks_path

# Set the cache path
cache_path = get_cache_path()
tasks_path = get_tasks_path()
# Get the logger
logger = logging.getLogger("prepare_assignment")
# Load the task template file
template_file = files().joinpath('../schemas/task.schema.json_template')
template: str = template_file.read_text()


def __download_task(props: TaskProperties) -> Path:
    """
    Download the task (using git clone)

    :param props: task properties
    :returns Path: the path where the repo is checked out
    """
    props.repo_path.mkdir(parents=True, exist_ok=True)
    git_url: str
    if CONFIG.GIT_MODE == "https":
        git_url = f"https://github.com/{props.organization}/{props.name}.git"
    else:
        git_url = f"git@github.com:{props.organization}/{props.name}.git"
    logger.debug(f"Cloning repository: {git_url}")
    with Repo.clone_from(git_url, props.repo_path) as repo:
        if props.version != "latest":
            logger.debug(f"Checking out correct version of repository: {props.version}")
            repo.git.checkout(props.version)
    return props.repo_path


def __build_json_schema(props: TaskProperties, task: TaskDefinition) -> str:
    logger.debug(f"Building json schema for '{task.id}'")
    schema = template.replace("{{task-id}}", task.id)
    schema = schema.replace("{{task-version}}", props.version)
    schema = schema.replace("{{organization}}", props.organization)
    schema = schema.replace("{{task}}", str(props))
    schema = schema.replace("{{task-name}}", task.name)
    schema = schema.replace("{{task-description}}", task.description)
    required: List[str] = []
    properties: List[str] = []
    for inp in task.inputs:
        properties.append(inp.to_schema_definition())
        if inp.required:
            required.append(inp.name)
    if len(properties) > 0:
        output = (',    \n"with": {\n      "type": "object",\n      "additionalProperties": false,\n '
                  '     "properties": {\n')
        output += ",\n".join(properties) + "\n    }"
        if len(required) > 0:
            schema = schema.replace("{{required}}", ', "with"')
            output += ',\n    "required": [' + ", ".join(map(lambda x: f'"{x}"', required)) + ']\n    }'
        else:
            schema = schema.replace("{{required}}", "")
            output += "\n}"
        schema = schema.replace("{{with}}", output)
    return schema


def __task_install_dependencies(task_path: Path) -> None:
    if sys.platform == "win32":
        venv_path = os.path.join(task_path, "venv", "scripts", "python.exe")
    else:
        venv_path = os.path.join(task_path, "venv", "bin", "python")
    repo_path = os.path.join(task_path, "repo")
    requirements_path = os.path.join(repo_path, "requirements.txt")
    pyproject_path = os.path.join(repo_path, "pyproject.toml")
    has_requirements = os.path.isfile(requirements_path)
    has_pyproject = os.path.isfile(pyproject_path)

    if not has_requirements and not has_pyproject:
        return

    result: Optional[subprocess.CompletedProcess[Any]] = None
    if has_requirements:
        logger.debug(f"Installing dependencies from '{requirements_path}'")
        args = [venv_path] + f"-m pip install -r {requirements_path}".split(" ")
        result = subprocess.run(args, capture_output=True)
    elif has_pyproject:
        logger.debug(f"Installing dependencies from '{pyproject_path}'")
        args = [venv_path] + f"-m pip install .".split()
        result = subprocess.run(args, capture_output=True, cwd=repo_path)

    if result is not None and result.returncode == 1:
        log_path = os.path.join(cache_path, "logs")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file = os.path.join(log_path, f'{timestamp}-dependencies.log')
        Path(log_path).mkdir(parents=True, exist_ok=True)
        with open(file, 'wb') as handle:
            handle.write(result.stderr)
        raise DependencyError(f"Unable to install dependencies for '{repo_path}', see '{file}' for more info")


def __load_task_from_disk(props: TaskProperties, parsed: Dict[str, ValidableTask]) -> None:
    logger.debug(f"Task '{props}' is already available, loading from disk")
    with open(os.path.join(props.task_path, f"{props.name}.schema.json"), "r") as handle:
        json_schema = json.load(handle)
    task_yaml = load_yaml(props.definition_path)
    task = TaskDefinition.of(task_yaml, props.task_path)
    parsed[str(props)] = {"schema": json_schema, "task": task}
    if isinstance(task, CompositeTaskDefinition):
        for sub_task in task.tasks:
            sub_task_name = sub_task.get("uses", None)
            if sub_task_name is None:
                continue
            sub_props = TaskProperties.of(sub_task_name)
            __load_task_from_disk(sub_props, parsed)


def __prepare_task(props: TaskProperties) -> ValidableTask:
    try:
        # Download the task (clone the repository)
        __download_task(props)
        # Validate that the task.yml is valid
        task_yaml = validate_task_definition(props.definition_path)
        task: TaskDefinition = TaskDefinition.of(task_yaml, props.task_path)
        validate_default_values(task)
        if isinstance(task, PythonTaskDefinition):
            main_path = os.path.join(props.repo_path, Path(task.main))  # type: ignore
            if not os.path.isfile(main_path):
                error_msg = f"Main file '{task.main}' does not exist for task '{task.name}'"  # type: ignore
                raise ValidationError(error_msg)
            # Create a virtualenv for this task
            cli_run([os.path.join(props.task_path, "venv")])
            # Install dependencies
            __task_install_dependencies(props.task_path)
        # Now we can build a schema for this task
        schema = __build_json_schema(props, task)
        json_schema = json.loads(schema)
        with open(os.path.join(props.task_path, f"{props.name}.schema.json"), 'w') as handle:
            handle.write(schema)
        return {"schema": json_schema, "task": task}
    except Exception as e:
        # If something went wrong in the previous steps,
        # that means the task is not valid and should be removed
        shutil.rmtree(props.task_path)
        # We need to raise an exception, because if it was part of a composite task,
        # then that task is also not valid
        raise PrepareTaskError(f"Unable to prepare task '{str(props)}'", e)


def __prepare_tasks(tasks: List[Any], parsed: Optional[Dict[str, ValidableTask]] = None, *,
                    file: Optional[str] = None, check_inputs: bool = True) -> Dict[str, ValidableTask]:
    # Unfortunately we cannot do this as a default value, see:
    # https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments
    if parsed is None:
        parsed = {}
    if len(tasks) == 0:
        logger.debug("All (sub-)tasks prepared")
        return parsed

    task_def = tasks.pop()
    props = TaskProperties.of(task_def["uses"])

    # Make sure that we always talk about the same task/version, e.g. the following are all the same
    # remove, remove@latest, prepare-assignment/remove@latest
    task_def["uses"] = str(props)
    # Check if we have already loaded the task
    if parsed.get(str(props), None) is None:
        logger.debug(f"Task '{props}' has not been loaded in this run")
        # Check if task (therefore the path) has already been downloaded in previous run
        task_path = props.task_path
        if os.path.isdir(task_path):
            __load_task_from_disk(props, parsed)
        else:
            logger.debug(f"Task '{props}' is not available on this system")
            valid_task = __prepare_task(props)
            # Check if it is a composite task, in that case we might need to retrieve more tasks
            task = valid_task["task"]
            if isinstance(task, CompositeTaskDefinition):
                logger.debug(f"Task '{props}' is a composite task, preparing sub-tasks")
                all_tasks: List[Any] = []
                for step in task.tasks:
                    name = step.get("uses", None)
                    if name is not None:
                        all_tasks.append(step)
                try:
                    parsed = __prepare_tasks(all_tasks, parsed, file=str(props.repo_path))
                except PrepareTaskError as PE:
                    # If any of the subtasks this composite task depend on fails,
                    # we have to remove this task as well
                    shutil.rmtree(task_path)
                    raise PE
                except Exception as e:
                    shutil.rmtree(task_path)
                    raise PrepareTaskError(f"Unable to prepare task '{props}'", e)
            parsed[str(props)] = valid_task
            if task_def.get("with", None) is None:
                task_def["with"] = {}
    else:
        logger.debug(f"Task '{props}' has already been loaded in this run")
    if check_inputs and file is not None:
        validate_tasks(file, task_def, parsed[str(props)]["schema"])
    return __prepare_tasks(tasks, parsed, file=file)


def prepare_tasks(prepare_file: str, jobs: Dict[str, Any]) -> Dict[str, TaskDefinition]:
    """
    Make sure that the tasks are available for the runner.

    If a task is not available:
    1. Clone the repository
    2. Checkout the correct version
    3. Generate json schema for validation
    4. Validate task

    :param prepare_file the name/path to the prepare file
    :param jobs: The jobs of the prepare file
    :return: None
    """
    logger.debug("========== Preparing tasks")
    all_tasks: List[Any] = []
    # Iterate through all the tasks to make sure that they are available
    for step, tasks in jobs.items():
        for task in tasks:
            # If the task is a run command, we don't need to do anything
            if task.get("uses", None) is not None:
                all_tasks.append(task)
    mapping = __prepare_tasks(all_tasks, file=prepare_file)
    logger.debug("✓ All tasks downloaded and valid")
    return {k: v["task"] for k, v in mapping.items()}
