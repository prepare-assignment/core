import json
import logging

import pytest

from prepare_assignment.core.subsituter import substitute_all
from prepare_assignment.data.job_environment import JobEnvironment


def test_substitute_input() -> None:
    values = {
        'test': '${{ inputs.test }}'
    }
    env = JobEnvironment(inputs={'test': 'substituted'}, outputs={}, environment={})
    substitute_all(values, env)
    assert values["test"] == 'substituted'


def test_substitute_input_list() -> None:
    values = {
        'test': ['${{ inputs.test }}']
    }
    env = JobEnvironment(inputs={'test': 'substituted'}, outputs={}, environment={})
    substitute_all(values, env)
    assert values["test"] == ['substituted']


def test_substitute_output() -> None:
    values = {
        'test': '${{ tasks.step1.outputs.test }}'
    }
    env = JobEnvironment(inputs={}, outputs={'step1': {'test': 'substituted'}}, environment={})
    substitute_all(values, env)
    assert values["test"] == 'substituted'


def test_substitute_float() -> None:
    values = {
        'test': '${{ tasks.step1.outputs.test }}'
    }
    env = JobEnvironment(inputs={}, outputs={'step1': {'test': 7.2}}, environment={})
    substitute_all(values, env)
    assert values["test"] == '7.2'


def test_substitute_list() -> None:
    values = {
        'test': '${{ tasks.step1.outputs.test }}'
    }
    value = ['sub', 'sti', 'tuted']
    env = JobEnvironment(inputs={}, outputs={'step1': {'test': value}}, environment={})
    substitute_all(values, env)
    assert values["test"] == json.dumps(value)


def test_no_substitute() -> None:
    values = {
        'test': 'nothing to see here'
    }
    env = JobEnvironment(inputs={'test': 'substituted'}, outputs={}, environment={})
    substitute_all(values, env)
    assert values["test"] == 'nothing to see here'


def test_invalid_substitute(caplog: pytest.LogCaptureFixture) -> None:
    values = {
        'test': '${{ tasks.step1.outputs.test }}'
    }
    env = JobEnvironment(inputs={}, outputs={}, environment={})
    with caplog.at_level(logging.DEBUG):
        substitute_all(values, env)
    assert values["test"] == ''
    assert 'tasks.step1.outputs.test' in caplog.text
