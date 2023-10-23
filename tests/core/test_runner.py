import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core.runner import run
from prepare_assignment.data.action_definition import PythonActionDefinition, ActionInputDefinition, \
    ActionOutputDefinition, CompositeActionDefinition
from prepare_assignment.data.prepare import Prepare

yaml = dict(name='Test', steps={'prepare': [{'name': 'test composite', 'uses': 'composite', 'with': {'input': 'test'}},
                                            {'name': 'remove', 'uses': 'remove', 'id': 'remove',
                                             'with': {'input': ['out', '*.zip'], 'force': True, 'recursive': True}},
                                            {'name': 'run command',
                                             'run': "echo '${{ steps.remove.outputs.files }}' | jq"}]})

mapping = {
    'remove': PythonActionDefinition(id='remove', name='Remove files', description='Remove files', inputs=[ActionInputDefinition(name='force', description='Ignore nonexistent files and arguments', required=False, type='boolean', default=False, items=None), ActionInputDefinition(name='input', description='Files (glob) to remove', required=True, type='array', default=None, items='string'), ActionInputDefinition(name='recursive', description='Whether to recursively remove all subdirectories', required=False, type='boolean', default=False, items=None)], outputs={'files': ActionOutputDefinition(description='Matched globs that have been removed', type='array', items='string')}, path='', main='main.py'),
    'composite': CompositeActionDefinition(id='composite', name='Test composite action', description='Test composite action', inputs=[ActionInputDefinition(name='input', description='test input with substitution', required=True, type='string', default=None, items=None)], outputs={}, path='', steps=[{'name': 'Use other action', 'uses': 'remove', 'with': {'force': True, 'input': ['{{ inputs.input }}'], 'recursive': True}}])
}


def test_runner(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    # TODO: set the values on the mock
    prepare = Prepare.of(yaml)
    run(prepare, mapping)
    assert mock.call_count == 3
