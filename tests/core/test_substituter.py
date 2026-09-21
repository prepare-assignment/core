import json
import logging

import pytest

from prepare_assignment.core.subsituter import substitute_all
from prepare_assignment.data.errors import ExpressionError
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


def test_invalid_substitute_raises() -> None:
    values = {
        'test': '${{ tasks.step1.outputs.test }}'
    }
    env = JobEnvironment(inputs={}, outputs={}, environment={})
    with pytest.raises(ExpressionError) as exc:
        substitute_all(values, env)
    assert 'tasks.step1' in exc.value.message


def test_invalid_substitute_in_mixed_string_raises() -> None:
    """A typo must never silently become an empty string (e.g. `rm -rf ${{ typo }}/x`)."""
    values = {'test': 'rm -rf ${{ inputs.typo }}/x'}
    env = JobEnvironment(inputs={"dir": "out"}, outputs={}, environment={})
    with pytest.raises(ExpressionError) as exc:
        substitute_all(values, env)
    assert "'inputs.typo' is not defined" in exc.value.message
    assert "dir" in exc.value.message


def test_substitute_missing_env_is_empty() -> None:
    values = {'test': 'value: ${{ env.NOT_SET }}'}
    env = JobEnvironment(inputs={}, outputs={}, environment={})
    substitute_all(values, env)
    assert values['test'] == 'value: '


def test_substitute_declared_but_unset_output_is_empty() -> None:
    values = {'test': '${{ tasks.step1.outputs.files }}'}
    env = JobEnvironment(inputs={}, outputs={"step1": {"files": None}}, environment={})
    substitute_all(values, env)
    assert values['test'] == ''


def test_substitute_none_in_list_is_dropped() -> None:
    values = {'test': ['a', '${{ inputs.extra }}']}
    env = JobEnvironment(inputs={"extra": None}, outputs={}, environment={})
    substitute_all(values, env)
    assert values['test'] == ['a']


def test_substitute_env_var() -> None:
    values = {'test': '${{ env.MY_VAR }}'}
    env = JobEnvironment(inputs={}, outputs={}, environment={'MY_VAR': 'secret'})
    substitute_all(values, env)
    assert values["test"] == 'secret'


def test_substitute_expression_comparison() -> None:
    values = {'test': '${{ inputs.x == 5 }}'}
    env = JobEnvironment(inputs={'x': 5}, outputs={}, environment={})
    substitute_all(values, env)
    assert values["test"] == 'True'


def test_substitute_hyphenated_output() -> None:
    values = {'test': '${{ tasks.step1.outputs.stripped-files }}'}
    env = JobEnvironment(inputs={}, outputs={'step1': {'stripped-files': ['a.java']}}, environment={})
    substitute_all(values, env)
    assert values["test"] == '["a.java"]'


def test_substitute_mixed_string() -> None:
    values = {'test': 'hello ${{ inputs.name }}!'}
    env = JobEnvironment(inputs={'name': 'world'}, outputs={}, environment={})
    substitute_all(values, env)
    assert values["test"] == 'hello world!'
