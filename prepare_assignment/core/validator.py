from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Type

from importlib_resources import files
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate
from ruamel.yaml import YAML

from prepare_assignment.data.action_definition import ActionDefinition
from prepare_assignment.data.errors import ValidationError as VE
from prepare_assignment.utils.default_validator import DefaultValidatingValidator

logger = logging.getLogger("prepare_assignment")
yaml = YAML(typ='safe')

type_map: Dict[str, Type] = {
    "string": type(''),
    "integer": type(1),
    "number": type(1.23),
    "array": type([]),
    "boolean": type(True)
}


def validate_prepare(prepare_file: str, prepare: Dict[str, Any]) -> None:
    """
    Validate that the prepare_assignment.y(a)ml file has the correct syntax
    NOTE: this does not validate all actions, this is done in the
    validate_actions function
    :param prepare: The parsed yaml
    :param prepare_file
    :return: None
    :raises: ValidationError: if schema is not valid
    """
    logger.debug("========== Validating config file")
    # Load the validation jsonschema
    schema_path = files().joinpath('../schemas/prepare.schema.json')
    schema: Dict[str, Any] = json.loads(schema_path.read_text())

    # Validate prepare_assignment.y(a)ml
    try:
        validate(prepare, schema, cls=DefaultValidatingValidator)
    except ValidationError as ve:
        message = f"Error in: {prepare_file}, unable to verify '{ve.json_path}'\n\t -> {ve.message}"
        raise VE(message)
    logger.debug("✓ Prepare file is valid")


def validate_action(file: str, action: Dict[str, Any], json_schema: Any) -> None:
    """
    Validate all actions based on their respective json schemas
    NOTE: this assumes that all actions are available and that it's json schema has been generated
    :param action The action definition
    :param json_schema
    :param file
    :return: None
    :raises: ValidationError if an action cannot be validated against its respective schema
    """
    name = action["uses"]
    logger.debug(f"Validating '{name}'")
    try:
        # validate(action, json_schema, cls=DefaultValidatingValidator)
        DefaultValidatingValidator(json_schema).validate(action)
    except ValidationError as ve:
        message = f"Error in: {file}, unable to verify action '{name}'\n\t -> {ve.json_path}: {ve.message}"
        raise VE(message)


def load_yaml(path: str | os.PathLike[str] | os.PathLike) -> Any:
    path = Path(path)
    return yaml.load(path)


def validate_action_definition(path: str | os.PathLike[str] | os.PathLike) -> Any:
    logger.debug("Validating action definition")

    # Load the validation jsonschema
    schema_path = files().joinpath('../schemas/action.schema.json')
    schema: Dict[str, Any] = json.loads(schema_path.read_text())

    action_definition = load_yaml(path)

    try:
        validate(action_definition, schema, cls=DefaultValidatingValidator)
        # Overwrite the action.yml file as we might have added default values
        with open(path, 'w') as handle:
            yaml.dump(action_definition, handle)
    except ValidationError as ve:
        message = f"Unable to verify: {path}\n\t -> {ve.json_path}: {ve.message}"
        raise VE(message)

    return action_definition


def validate_default_values(action: ActionDefinition) -> None:
    for input in action.inputs:
        if input.default is None:
            continue

        # Check that the default type is of the type we expect
        if not isinstance(input.default, type_map[input.type]):
            raise VE(
                f"Unable to verify action '{action.name}', default value for input '{input.name}' is of the wrong type"
                f", expected '{input.type}', but got '{type(input.default)}'")

        # If we expect an array, validate that all elements are of the correct type
        if input.type == "array":
            # we need to ignore the type here as both PyCharm and mypy don't know we validated the file already and
            # we know that there myst be option.items when the type is array
            item_type = type_map[input.items]  # type: ignore
            # noinspection PyTypeChecker
            for item in input.default:
                if item_type != type(item):
                    raise VE(f"Default item: {item}, should be of type: {item_type}, "
                             f"but is of type: {type(item)}")
