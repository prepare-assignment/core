from pytest_mock import MockerFixture

from prepare_assignment.core.runner import run
from prepare_assignment.data.task_definition import PythonTaskDefinition, TaskInputDefinition, \
    TaskOutputDefinition, CompositeTaskDefinition
from prepare_assignment.data.prepare import Prepare

yaml = dict(name='Test', jobs={'prepare': [{'name': 'test composite', 'uses': 'composite', 'with': {'input': 'test'}},
                                            {'name': 'remove', 'uses': 'remove', 'id': 'remove',
                                             'with': {'input': ['out', '*.zip'], 'force': True, 'recursive': True}},
                                            {'name': 'run command',
                                             'run': "echo '${{ jobs.remove.outputs.files }}' | jq"}]})

mapping = {
    'prepare-assignment/remove@latest': PythonTaskDefinition(id='remove', name='Remove files', description='Remove files', inputs=[TaskInputDefinition(name='force', description='Ignore nonexistent files and arguments', required=False, type='boolean', default=False, items=None), TaskInputDefinition(name='input', description='Files (glob) to remove', required=True, type='array', default=None, items='string'), TaskInputDefinition(name='recursive', description='Whether to recursively remove all subdirectories', required=False, type='boolean', default=False, items=None)], outputs={'files': TaskOutputDefinition(description='Matched globs that have been removed', type='array', items='string')}, path='', main='main.py'),
    'prepare-assignment/composite@latest': CompositeTaskDefinition(id='composite', name='Test composite task', description='Test composite task', inputs=[TaskInputDefinition(name='input', description='test input with substitution', required=True, type='string', default=None, items=None)], outputs={}, path='', tasks=[{'name': 'Use other task', 'uses': 'remove', 'with': {'force': True, 'input': ['{{ inputs.input }}'], 'recursive': True}}])
}


class MockedPopen:

    def __init__(self, args, **kwargs):
        self.args = args
        self.returncode = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        pass

    @property
    def stdout(self):
        return [":PA:error:PA:error message\n"]


class MockedPopenFail(MockedPopen):
    def __init__(self, args, **kwargs):
        super().__init__(args, **kwargs)
        self.returncode = 1


def test_runner(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopen
    prepare = Prepare.of(yaml)
    run(prepare, mapping)
    assert mock.call_count == 3


def test_runner_fail(mocker: MockerFixture) -> None:
    # TODO: update test when we are handling failed command execution
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopenFail
    prepare = Prepare.of(yaml)
    run(prepare, mapping)
    assert mock.call_count == 3
