import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Final, List, Optional, Set

from git import Repo
from virtualenv import cli_run

from prepare_assignment.core.versions import COMMIT_HASH_RE, get_git_url, resolve_version
from prepare_assignment.core.validator import validate_task_definition, validate_tasks, load_yaml, \
    validate_default_values, validate_unique_ids
from prepare_assignment.data.errors import DependencyError, ValidationError, PrepareTaskError
from prepare_assignment.data.task_definition import TaskDefinition, CompositeTaskDefinition, \
    PythonTaskDefinition, ValidableTask
from prepare_assignment.data.task_properties import TaskProperties
from prepare_assignment.utils.files import remove_tree
from prepare_assignment.utils.paths import get_cache_path, get_tasks_path

# Set the cache path
cache_path = get_cache_path()
tasks_path = get_tasks_path()
# Get the logger
logger = logging.getLogger("prepare_assignment")


# Properties that every step may have (next to 'uses' and 'with')
STEP_PROPERTIES: Final[List[str]] = ["name", "id", "if", "working-directory", "env", "continue-on-error"]

# Tasks that are currently being installed (to detect cyclic composite tasks)
_installing: Set[str] = set()

def __download_task(props: TaskProperties) -> Path:
    """
    Download the task (using git clone)

    :param props: task properties
    :returns Path: the path where the repo is checked out
    """
    props.repo_path.mkdir(parents=True, exist_ok=True)
    git_url = get_git_url(props)
    resolved = resolve_version(git_url, props.version)
    logger.debug(f"Cloning repository: {git_url} at ref '{resolved or 'HEAD'}'")

    if resolved is not None and COMMIT_HASH_RE.match(resolved):
        # Shallow clones cannot reach arbitrary commits; do a full clone then checkout
        with Repo.clone_from(git_url, props.repo_path) as repo:
            repo.git.checkout(resolved)
    else:
        clone_kwargs: Dict[str, Any] = {"depth": 1}
        if resolved is not None:
            clone_kwargs["branch"] = resolved
        Repo.clone_from(git_url, props.repo_path, **clone_kwargs)

    return props.repo_path


def __build_json_schema(props: TaskProperties, task: TaskDefinition) -> Dict[str, Any]:
    """
    Build the json schema that validates the usage of a task (the 'with' inputs) in a prepare.yml
    """
    logger.debug(f"Building json schema for '{task.id}'")
    schema: Dict[str, Any] = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"https://github.com/{props.organization}/{task.id}/{props.version}/{task.id}.schema.json",
        "additionalProperties": False,
        "title": task.name,
        "description": task.description,
        "type": "object",
        "properties": {
            # The generic step properties are validated by prepare.schema.json
            **{key: {} for key in STEP_PROPERTIES},
            "uses": {"const": str(props)},
        },
        "required": ["uses"],
    }
    # A task without inputs still accepts an empty 'with'
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for inp in task.inputs:
        properties[inp.name] = inp.to_schema_definition()
        if inp.required:
            required.append(inp.name)
    with_schema: Dict[str, Any] = {"type": "object", "additionalProperties": False, "properties": properties}
    if len(required) > 0:
        with_schema["required"] = required
        schema["required"].append("with")
    schema["properties"]["with"] = with_schema
    return schema


def __schema_path(props: TaskProperties) -> Path:
    return Path(os.path.join(props.task_path, f"{props.name}.schema.json"))


def __is_installed(props: TaskProperties) -> bool:
    """
    A task is only installed if its schema has been written, this is always the last step of preparing a task
    """
    return __schema_path(props).is_file()


def __write_schema(props: TaskProperties, schema: Dict[str, Any]) -> None:
    """
    Atomically write the schema, marking the task as completely installed
    """
    path = __schema_path(props)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(schema, handle, indent=2)
    os.replace(tmp_path, path)


def __task_install_dependencies(task_path: Path) -> None:
    if sys.platform == "win32":
        venv_path = os.path.join(task_path, "venv", "Scripts", "python.exe")
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

    if result is not None and result.returncode != 0:
        log_path = os.path.join(cache_path, "logs")
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file = os.path.join(log_path, f'{timestamp}-dependencies.log')
        Path(log_path).mkdir(parents=True, exist_ok=True)
        with open(file, 'wb') as handle:
            handle.write(result.stderr)
        raise DependencyError(f"Unable to install dependencies for '{repo_path}', see '{file}' for more info")


def __sub_tasks(task: TaskDefinition) -> List[Any]:
    if not isinstance(task, CompositeTaskDefinition):
        return []
    return [step for step in task.tasks if step.get("uses", None) is not None]


def __validate_sub_task_ids(props: TaskProperties, task: TaskDefinition) -> None:
    if isinstance(task, CompositeTaskDefinition):
        validate_unique_ids(str(props.definition_path), f"task '{task.name}'", task.tasks)


def __load_task_from_disk(props: TaskProperties, parsed: Dict[str, ValidableTask]) -> None:
    logger.debug(f"Task '{props}' is already available, loading from disk")
    task_yaml = load_yaml(props.definition_path)
    task = TaskDefinition.of(task_yaml, props.task_path)
    try:
        __validate_sub_task_ids(props, task)
    except ValidationError as e:
        raise PrepareTaskError(f"Unable to prepare task '{props}'", e) from e
    # Always rebuild the schema, so schemas generated by older versions of prepare are updated
    json_schema = __build_json_schema(props, task)
    with open(__schema_path(props), "r", encoding="utf-8") as handle:
        stored = json.load(handle)
    if stored != json_schema:
        logger.debug(f"Updating the schema of task '{props}'")
        __write_schema(props, json_schema)
    parsed[str(props)] = {"schema": json_schema, "task": task}
    # Sub-tasks might have been removed in the meantime, so make sure they are available (again)
    __prepare_tasks(__sub_tasks(task), parsed, check_inputs=False)


def __prepare_task(props: TaskProperties) -> ValidableTask:
    """
    Download, validate and install a task. The schema is NOT written yet, as that marks the task as installed.
    """
    try:
        # Download the task (clone the repository)
        __download_task(props)
        # Validate that the task.yml is valid
        task_yaml = validate_task_definition(props.definition_path)
        task: TaskDefinition = TaskDefinition.of(task_yaml, props.task_path)
        validate_default_values(task)
        __validate_sub_task_ids(props, task)
        if isinstance(task, PythonTaskDefinition):
            main_path = os.path.join(props.repo_path, Path(task.main))  # type: ignore
            if not Path(main_path).resolve().is_relative_to(props.repo_path.resolve()):
                raise ValidationError(f"Main path '{task.main}' must be within the repository")
            if not os.path.isfile(main_path):
                error_msg = f"Main file '{task.main}' does not exist for task '{task.name}'"  # type: ignore
                raise ValidationError(error_msg)
            # Create a virtualenv for this task
            cli_run([os.path.join(props.task_path, "venv")])
            # Install dependencies
            __task_install_dependencies(props.task_path)
        # Now we can build a schema for this task
        return {"schema": __build_json_schema(props, task), "task": task}
    except Exception as e:
        # If something went wrong in the previous steps,
        # that means the task is not valid and should be removed
        remove_tree(props.task_path, ignore_errors=True)
        # We need to raise an exception, because if it was part of a composite task,
        # then that task is also not valid
        raise PrepareTaskError(f"Unable to prepare task '{str(props)}'", e) from e


def __install_task(props: TaskProperties, parsed: Dict[str, ValidableTask]) -> None:
    if str(props) in _installing:
        raise PrepareTaskError(f"Unable to prepare task '{props}'",
                               DependencyError(f"Cyclic dependency detected for '{props}'"))
    _installing.add(str(props))
    try:
        __install_task_unchecked(props, parsed)
    finally:
        _installing.discard(str(props))


def __install_task_unchecked(props: TaskProperties, parsed: Dict[str, ValidableTask]) -> None:
    valid_task = __prepare_task(props)
    task = valid_task["task"]
    try:
        # Check if it is a composite task, in that case we might need to retrieve more tasks
        sub_tasks = __sub_tasks(task)
        if len(sub_tasks) > 0:
            logger.debug(f"Task '{props}' is a composite task, preparing sub-tasks")
            __prepare_tasks(sub_tasks, parsed, file=str(props.repo_path))
        # Writing the schema is the last step, only then the task is considered to be installed
        __write_schema(props, valid_task["schema"])
    except PrepareTaskError:
        # If any of the subtasks this composite task depend on fails,
        # we have to remove this task as well
        remove_tree(props.task_path, ignore_errors=True)
        raise
    except Exception as e:
        remove_tree(props.task_path, ignore_errors=True)
        raise PrepareTaskError(f"Unable to prepare task '{props}'", e) from e
    parsed[str(props)] = valid_task


def __prepare_tasks(tasks: List[Any], parsed: Optional[Dict[str, ValidableTask]] = None, *,
                    file: Optional[str] = None, check_inputs: bool = True) -> Dict[str, ValidableTask]:
    # Unfortunately we cannot do this as a default value, see:
    # https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments
    if parsed is None:
        parsed = {}
    for task_def in tasks:
        props = TaskProperties.of(task_def["uses"])

        # Make sure that we always talk about the same task/version, e.g. the following are all the same
        # remove, remove@latest, prepare-assignment/remove@latest
        task_def["uses"] = str(props)
        # Check if we have already loaded the task
        if parsed.get(str(props), None) is None:
            logger.debug(f"Task '{props}' has not been loaded in this run")
            if os.path.isdir(props.task_path) and not __is_installed(props):
                logger.warning(f"Task '{props}' was not completely installed, installing it again")
                remove_tree(props.task_path)
            # Check if task has already been installed in a previous run
            if __is_installed(props):
                __load_task_from_disk(props, parsed)
            else:
                logger.debug(f"Task '{props}' is not available on this system")
                __install_task(props, parsed)
        else:
            logger.debug(f"Task '{props}' has already been loaded in this run")
        if check_inputs and file is not None:
            validate_tasks(file, task_def, parsed[str(props)]["schema"])
    logger.debug("All (sub-)tasks prepared")
    return parsed


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
