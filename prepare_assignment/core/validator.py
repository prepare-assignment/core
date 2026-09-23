from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Any, List

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from prepare_assignment.data.errors import ValidationError as VE
from prepare_assignment.data.task_definition import TaskDefinition
from prepare_assignment.data.types import is_of_type
from prepare_assignment.utils.default_validator import DefaultValidatingValidator
from prepare_assignment.utils.resources import load_schema
from prepare_assignment.utils.yml_loader import YAML_LOADER

logger = logging.getLogger("prepare_assignment")

def validate_prepare(prepare_file: str, prepare: Dict[str, Any]) -> None:
    """
    Validate that the prepare_assignment.y(a)ml file has the correct syntax
    NOTE: this does not validate all tasks, this is done in the
    validate_tasks function
    :param prepare_file: path/name of the prepare file
    :param prepare: The parsed yaml contents
    :return: None
    :raises: ValidationError: if schema is not valid
    """
    logger.debug("========== Validating config file")
    # Load the validation jsonschema
    schema = load_schema("prepare.schema.json")

    # Validate prepare_assignment.y(a)ml
    try:
        validate(prepare, schema, cls=DefaultValidatingValidator)
    except ValidationError as ve:
        message = f"Error in: {prepare_file}, unable to verify '{ve.json_path}'\n\t -> {ve.message}"
        raise VE(message)
    for job, steps in prepare["jobs"].items():
        validate_unique_ids(prepare_file, f"job '{job}'", steps)
    logger.debug("✓ Prepare file is valid")


def validate_unique_ids(file: str, where: str, steps: List[Dict[str, Any]]) -> None:
    """
    Validate that the ids of the steps are unique, the outputs of a step are stored under its id
    NOTE: steps without an id are not checked
    :param file: path/name of the file that contains the steps
    :param where: the job or composite task that contains the steps, used in the error message
    :param steps: the steps of the job or composite task
    :return: None
    :raises: ValidationError: if multiple steps have the same id
    """
    names: Dict[str, List[str]] = {}
    for step in steps:
        step_id = step.get("id", None)
        if step_id is not None:
            names.setdefault(step_id, []).append(step.get("name", ""))
    for step_id, step_names in names.items():
        if len(step_names) > 1:
            quoted = ", ".join(f"'{name}'" for name in step_names)
            raise VE(f"Error in: {file}, {where} has multiple steps with id '{step_id}': {quoted}")


def validate_tasks(file: str, task: Dict[str, Any], json_schema: Any) -> None:
    """
    Validate all tasks based on their respective json schemas
    NOTE: this assumes that all tasks are available and that it's json schema has been generated
    :param task The task definition
    :param json_schema the schema to validate against
    :param file the name/path of the task definition file
    :return: None
    :raises: ValidationError if a task cannot be validated against its respective schema
    """
    name = task["name"]
    task_name = task["uses"]
    logger.debug(f"Validating '{name}' ({task_name})")
    try:
        # If the yaml file doesn't contain with, the default validator doesn't trigger setting default values
        # So if the schema has 'with' property and the yaml misses, we can add it manually
        if json_schema.get("properties", {}).get("with", None) is not None and task.get("with", None) is None:
            task["with"] = {}
        DefaultValidatingValidator(json_schema).validate(task)
    except ValidationError as ve:
        message = (f"Error in: {file}, unable to verify task '{name}' ({task_name})\n\t "
                   f"-> {ve.json_path}: {ve.message}")
        raise VE(message)


def load_yaml(path: str | os.PathLike[str] | os.PathLike) -> Any:
    """
    Load yaml file from path

    :param path: the path to the yaml file
    :return: the loaded yaml file
    """
    path = Path(path)
    return YAML_LOADER.load(path)


def validate_task_definition(path: str | os.PathLike[str] | os.PathLike) -> Any:
    """
    Validate that the task definition follows the schema

    :param path: to the task definition file
    :return: the parsed yaml file
    """
    logger.debug("Validating task definition")

    # Load the validation jsonschema
    schema = load_schema("task.schema.json")

    task_definition = load_yaml(path)

    try:
        validate(task_definition, schema, cls=DefaultValidatingValidator)
        # Overwrite the task.yml file as we might have added default values
        with open(path, 'w') as handle:
            YAML_LOADER.dump(task_definition, handle)
    except ValidationError as ve:
        message = f"Unable to verify: {path}\n\t -> {ve.json_path}: {ve.message}"
        raise VE(message)

    return task_definition


def validate_default_values(task: TaskDefinition) -> None:
    """
    Validate that the default values are of the correct type.
    For a list this means that all default values should be of the 'item' type.

    :param task: for which to verify the default values
    :return: None
    :raises ValidationError if any of the default values is of the wrong type
    """
    for input in task.inputs:
        if input.default is None:
            continue

        # Check that the default type is of the type we expect
        if not is_of_type(input.default, input.type):
            raise VE(
                f"Unable to verify task '{task.name}', default value for input '{input.name}' is of the wrong type"
                f", expected '{input.type}', but got '{type(input.default)}'")

        # If we expect an array, validate that all elements are of the correct type
        if input.type == "array":
            # noinspection PyTypeChecker
            for item in input.default:  # type: ignore
                if not is_of_type(item, input.items):  # type: ignore
                    raise VE(f"Default item: {item}, for input: '{input.name}', should be of type: {input.items}, "
                             f"but is of type: {type(item)}")
