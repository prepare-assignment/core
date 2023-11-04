import copy
from typing import Any, Dict, Final

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core.validator import (validate_prepare, validate_tasks, load_yaml,
                                               validate_task_definition, validate_default_values)
from prepare_assignment.data.task_definition import PythonTaskDefinition
from prepare_assignment.data.errors import ValidationError

VALID_PREPARE_YAML: Final[Dict[str, Any]] = {
    'name': 'Valid',
    'jobs': {
        'step1': [{'name': 'test step', 'uses': 'test', 'with': {'input': 'test'}}]
    }
}

INVALID_PREPARE_YAML: Final[Dict[str, Any]] = {
    'name': 'Valid'
}

TASK_SCHEMA: Final[Dict[str, Any]] = {
    '$schema': 'http://json-schema.org/draft-07/schema#',
    '$id': 'https://github.com/prepare-assignment/test/test.schema.json',
    'additionalProperties': False,
    'title': 'Test task',
    'description': 'Test task',
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

TASK_DEFINITION: Final[Dict[str, Any]] = {
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

VALID_TASK: Final[Dict[str, Any]] = {'id': 'valid', 'name': 'valid task', 'uses': 'test', 'with': {'fail': False}}
INVALID_TASK: Final[Dict[str, Any]] = {'id': 'valid', 'name': 'invalid task', 'uses': 'test'}


def test_validate_prepare_valid() -> None:
    validate_prepare("prepare.yml", VALID_PREPARE_YAML)


def test_validate_prepare_invalid() -> None:
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_prepare("prepare.yml", INVALID_PREPARE_YAML)


def test_validate_task_valid() -> None:
    validate_tasks("task.yml", VALID_TASK, TASK_SCHEMA)


def test_validate_task_invalid() -> None:
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_tasks("task.yml", INVALID_TASK, TASK_SCHEMA)


def test_load_yaml(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.validator.yaml.load", return_value="test")
    load_yaml("test.yml")


def test_validate_task_definition_valid(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.validator.load_yaml", return_value=TASK_DEFINITION)
    mocked_yaml_dump = mocker.patch("prepare_assignment.core.validator.yaml.dump")
    mocked_open = mocker.mock_open()
    mocker.patch("builtins.open", mocked_open)
    validate_task_definition("task.yml")
    mocked_yaml_dump.assert_called_once()


def test_validate_task_definition_invalid(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.validator.load_yaml", return_value={})
    mocked_yaml_dump = mocker.patch("prepare_assignment.core.validator.yaml.dump")
    mocked_open = mocker.mock_open()
    mocker.patch("builtins.open", mocked_open)
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_task_definition("task.yml")
    mocked_yaml_dump.assert_not_called()


def test_validate_default_values_invalid() -> None:
    task_copy = copy.deepcopy(TASK_DEFINITION)
    task_copy["inputs"]["test"]["default"] = 5
    task = PythonTaskDefinition.of(task_copy, "test.yml")
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_default_values(task)
    assert "test" in str(pytest_wrapped_e.value)


def test_validate_default_values_invalid_array() -> None:
    task_copy = copy.deepcopy(TASK_DEFINITION)
    task_copy["inputs"]["list"]["default"] = ["test", 1]
    task = PythonTaskDefinition.of(task_copy, "test.yml")
    with pytest.raises(ValidationError) as pytest_wrapped_e:
        validate_default_values(task)
    assert "list" in str(pytest_wrapped_e.value)


def test_validate_default_values_valid() -> None:
    task = PythonTaskDefinition.of(TASK_DEFINITION, "test.yml")
    validate_default_values(task)
