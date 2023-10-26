import copy
from typing import Any, Dict, Final

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core.validator import (validate_prepare, validate_action, load_yaml,
                                               validate_action_definition, validate_default_values)
from prepare_assignment.data.action_definition import PythonActionDefinition
from prepare_assignment.data.errors import ValidationError

VALID_PREPARE_YAML: Final[Dict[str, Any]] = {
    'name': 'Valid',
    'steps': {
        'step1': [{'name': 'test step', 'uses': 'test', 'with': {'input': 'test'}}]
    }
}

INVALID_PREPARE_YAML: Final[Dict[str, Any]] = {
    'name': 'Valid'
}

ACTION_SCHEMA: Final[Dict[str, Any]] = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    '$id': 'https://github.com/prepare-assignment/test/test.schema.json',
    'additionalProperties': False,
    'title': 'Test action',
    'description': 'Test action',
    'type': 'object',
    'properties': {
        'name': {'type': 'string'},
        'id': {'type': 'string'},
        'uses': {'const': 'test'},
        'with': {
            'type': 'object',
            'additionalProperties': False,
            'properties': {'fail': {'type': 'boolean'}},
            'required': ['fail']
        }
    },
    'required': ['uses', 'with']
}

ACTION_DEFINITION: Final[Dict[str, Any]] = {
    'id': 'test',
    'name': 'test',
    'description': 'test',
    'inputs': {
        "test": {
            'description': 'test default',
            "type": "string",
            'default': "test",
            'required': False
        },
        'test2': {
            'description': 'test 2',
            'type': 'string',
            'required': False
        },
        'list': {
            'description': 'test list default',
            'type': 'array',
            'items': 'string',
            'default': ['test1', 'test2'],
            'required': False
        }
    },
    'runs': {
        'using': 'python',
        'main': 'main.py'
    }
}

VALID_ACTION: Final[Dict[str, Any]] = {'id': 'valid', 'name': 'valid action', 'uses': 'test', 'with': {'fail': False}}
INVALID_ACTION: Final[Dict[str, Any]] = {'id': 'valid', 'name': 'valid action', 'uses': 'test'}


def test_validate_prepare_valid() -> None:
    validate_prepare("prepare.yml", VALID_PREPARE_YAML)


def test_validate_prepare_invalid() -> None:
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_prepare("prepare.yml", INVALID_PREPARE_YAML)


def test_validate_action_valid() -> None:
    validate_action("action.yml", VALID_ACTION, ACTION_SCHEMA)


def test_validate_action_invalid() -> None:
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_action("action.yml", INVALID_ACTION, ACTION_SCHEMA)


def test_load_yaml(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.validator.yaml.load", return_value="test")
    load_yaml("test.yml")


def test_validate_action_definition_valid(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.validator.load_yaml", return_value=ACTION_DEFINITION)
    mocked_yaml_dump = mocker.patch("prepare_assignment.core.validator.yaml.dump")
    mocked_open = mocker.mock_open()
    mocker.patch("builtins.open", mocked_open)
    validate_action_definition("action.yml")
    mocked_yaml_dump.assert_called_once()


def test_validate_action_definition_invalid(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.validator.load_yaml", return_value={})
    mocked_yaml_dump = mocker.patch("prepare_assignment.core.validator.yaml.dump")
    mocked_open = mocker.mock_open()
    mocker.patch("builtins.open", mocked_open)
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_action_definition("action.yml")
    mocked_yaml_dump.assert_not_called()


def test_validate_default_values_invalid() -> None:
    action_copy = copy.deepcopy(ACTION_DEFINITION)
    action_copy["inputs"]["test"]["default"] = 5
    action = PythonActionDefinition.of(action_copy, "test.yml")
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_default_values(action)
    assert "test" in str(pytest_wrapped_e.value)


def test_validate_default_values_invalid_array() -> None:
    action_copy = copy.deepcopy(ACTION_DEFINITION)
    action_copy["inputs"]["list"]["default"] = ["test", 1]
    action = PythonActionDefinition.of(action_copy, "test.yml")
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_default_values(action)
    assert "list" in str(pytest_wrapped_e.value)


def test_validate_default_values_valid() -> None:
    action = PythonActionDefinition.of(ACTION_DEFINITION, "test.yml")
    validate_default_values(action)
