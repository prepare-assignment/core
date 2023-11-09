import pytest

from jsonschema.exceptions import ValidationError

from prepare_assignment.utils.default_validator import DefaultValidatingValidator


def test_default_value() -> None:
    json_schema = {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'title': 'Test json schema',
        'type': 'object',
        'properties': {
            'default': {'type': 'string', 'default': 'default value'},
            'non-default': {'type': 'string'}
        }
    }
    yaml = {
        'non-default': 'test'
    }
    DefaultValidatingValidator(json_schema).validate(yaml)
    assert yaml["default"] == "default value"


def test_default_error() -> None:
    json_schema = {
        '$schema': 'http://json-schema.org/draft-07/schema#',
        'title': 'Test json schema',
        'type': 'object',
        'properties': {
            'default': {'type': 'string', 'default': 'default value'},
            'non-default': {'type': 'string'}
        }
    }
    yaml = {
        'non-default': 1
    }
    with pytest.raises(ValidationError):
        DefaultValidatingValidator(json_schema).validate(yaml)
