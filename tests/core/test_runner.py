import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core.runner import run
from prepare_assignment.data.errors import TaskExecutionError
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
    # First task fails; remaining tasks (no if:) are skipped; exception raised at end
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopenFail
    prepare = Prepare.of(yaml)
    with pytest.raises(TaskExecutionError):
        run(prepare, mapping)
    assert mock.call_count == 1


def test_runner_fail_always_still_runs(mocker: MockerFixture) -> None:
    # First task fails; second task has if: always() and should still run
    yaml_always = dict(name='Test', jobs={'prepare': [
        {'name': 'remove', 'uses': 'remove', 'id': 'remove',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
        {'name': 'cleanup', 'uses': 'remove', 'id': 'cleanup', 'if': 'always()',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
    ]})
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopenFail
    prepare = Prepare.of(yaml_always)
    with pytest.raises(TaskExecutionError):
        run(prepare, mapping)
    assert mock.call_count == 2


def test_runner_fail_failure_runs(mocker: MockerFixture) -> None:
    # First task fails; second task has if: failure() and should run
    yaml_failure = dict(name='Test', jobs={'prepare': [
        {'name': 'remove', 'uses': 'remove', 'id': 'remove',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
        {'name': 'on-fail', 'uses': 'remove', 'id': 'on-fail', 'if': 'failure()',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
    ]})
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    # First call fails, second succeeds
    mock.side_effect = [MockedPopenFail(None), MockedPopen(None)]
    prepare = Prepare.of(yaml_failure)
    with pytest.raises(TaskExecutionError):
        run(prepare, mapping)
    assert mock.call_count == 2


def test_runner_fail_success_skipped(mocker: MockerFixture) -> None:
    # First task fails; second task has if: success() and should be skipped
    yaml_success = dict(name='Test', jobs={'prepare': [
        {'name': 'remove', 'uses': 'remove', 'id': 'remove',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
        {'name': 'next', 'uses': 'remove', 'id': 'next', 'if': 'success()',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
    ]})
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopenFail
    prepare = Prepare.of(yaml_success)
    with pytest.raises(TaskExecutionError):
        run(prepare, mapping)
    assert mock.call_count == 1


def test_runner_if_condition_false_skips_task(mocker: MockerFixture) -> None:
    """A task with if: False should be skipped (Popen not called for it)."""
    yaml_with_if = dict(name='Test', jobs={'prepare': [
        {'name': 'remove', 'uses': 'remove', 'id': 'remove', 'if': 'False',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
    ]})
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopen
    prepare = Prepare.of(yaml_with_if)
    run(prepare, mapping)
    assert mock.call_count == 0


def test_runner_if_condition_true_runs_task(mocker: MockerFixture) -> None:
    """A task with if: True should execute normally."""
    yaml_with_if = dict(name='Test', jobs={'prepare': [
        {'name': 'remove', 'uses': 'remove', 'id': 'remove', 'if': 'True',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
    ]})
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopen
    prepare = Prepare.of(yaml_with_if)
    run(prepare, mapping)
    assert mock.call_count == 1
