import json
import logging
import os
from pathlib import Path

from typing import Dict, Any, Optional
from importlib_resources import files
from jsonschema.validators import validate
from ruamel.yaml import YAML

from prepare_assignment.data.action_definition import CompositeActionDefinition, PythonActionDefinition, \
    ActionDefinition, PythonActionDefinitionInput
from prepare_assignment.utils.default_validator import DefaultValidatingValidator


logger = logging.getLogger("prepare")


def validate_prepare(prepare: Dict[str, Any]) -> None:
    """
    Validate that the prepare.y(a)ml file has the correct syntax
    NOTE: this does not validate all actions, this is done in the
    validate_actions function
    :param prepare: The parsed yaml
    :return: None
    :raises: ValidationError: if schema is not valid
    """
    # Load the validation jsonschema
    schema_path = files().joinpath('../schemas/prepare.schema.json')
    schema: Dict[str, Any] = json.loads(schema_path.read_text())

    # Validate prepare.y(a)ml
    validate(prepare, schema, cls=DefaultValidatingValidator)


def validate_actions(actions: Dict[str, Any]) -> None:
    """
    Validate all actions based on their respective json schemas
    NOTE: this assumes that all actions are available and that it's json schema has been generated
    :param actions:
    :return:
    :raises: ValidationError if an action cannot be validated against its respective schema
    """
    logger.debug("Validating actions")


def validate_action_definition(path: str | os.PathLike[str] | os.PathLike) -> ActionDefinition:
    logger.debug("Validating action definition")
    path = Path(path)
    # Load the validation jsonschema
    schema_path = files().joinpath('../schemas/action.schema.json')
    schema: Dict[str, Any] = json.loads(schema_path.read_text())

    yaml = YAML(typ='safe')
    action_definition = yaml.load(path)
    validate(action_definition, schema, cls=DefaultValidatingValidator)
    if action_definition["runs"]["using"] == "composite":
        return CompositeActionDefinition.of(action_definition)
    else:
        return PythonActionDefinition.of(action_definition)
