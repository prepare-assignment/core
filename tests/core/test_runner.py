from typing import Any, Dict, List

import pytest
from prepare_toolbox.command import DEMARCATION
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


# ── composite if: expressions ─────────────────────────────────────────────────

_composite_yaml = dict(name='Test', jobs={'prepare': [
    {'name': 'test composite', 'uses': 'composite', 'with': {'input': 'test'}},
]})


def test_runner_composite_if_false_skips_subtask(mocker: MockerFixture) -> None:
    """A composite subtask with if: False is skipped."""
    composite_with_if = {
        'prepare-assignment/composite@latest': CompositeTaskDefinition(
            id='composite', name='Composite', description='',
            inputs=[TaskInputDefinition(name='input', description='', required=True, type='string', default=None, items=None)],
            outputs={}, path='',
            tasks=[
                {'name': 'always runs', 'uses': 'remove', 'with': {'input': ['out'], 'force': True, 'recursive': True}},
                {'name': 'never runs', 'if': 'False', 'uses': 'remove', 'with': {'input': ['out'], 'force': True, 'recursive': True}},
            ]
        ),
        'prepare-assignment/remove@latest': mapping['prepare-assignment/remove@latest'],
    }
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopen
    run(Prepare.of(_composite_yaml), composite_with_if)
    assert mock.call_count == 1


def test_runner_composite_if_always_runs_after_failure(mocker: MockerFixture) -> None:
    """A composite subtask with if: always() runs even after a failing subtask."""
    composite_with_always = {
        'prepare-assignment/composite@latest': CompositeTaskDefinition(
            id='composite', name='Composite', description='',
            inputs=[TaskInputDefinition(name='input', description='', required=True, type='string', default=None, items=None)],
            outputs={}, path='',
            tasks=[
                {'name': 'fails', 'uses': 'remove', 'with': {'input': ['out'], 'force': True, 'recursive': True}},
                {'name': 'always', 'if': 'always()', 'uses': 'remove', 'with': {'input': ['out'], 'force': True, 'recursive': True}},
            ]
        ),
        'prepare-assignment/remove@latest': mapping['prepare-assignment/remove@latest'],
    }
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = [MockedPopenFail(None), MockedPopen(None)]
    with pytest.raises(TaskExecutionError):
        run(Prepare.of(_composite_yaml), composite_with_always)
    assert mock.call_count == 2


def test_runner_composite_if_failure_runs_on_failure(mocker: MockerFixture) -> None:
    """A composite subtask with if: failure() runs when a prior subtask failed."""
    composite_with_failure = {
        'prepare-assignment/composite@latest': CompositeTaskDefinition(
            id='composite', name='Composite', description='',
            inputs=[TaskInputDefinition(name='input', description='', required=True, type='string', default=None, items=None)],
            outputs={}, path='',
            tasks=[
                {'name': 'fails', 'uses': 'remove', 'with': {'input': ['out'], 'force': True, 'recursive': True}},
                {'name': 'on-fail', 'if': 'failure()', 'uses': 'remove', 'with': {'input': ['out'], 'force': True, 'recursive': True}},
            ]
        ),
        'prepare-assignment/remove@latest': mapping['prepare-assignment/remove@latest'],
    }
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = [MockedPopenFail(None), MockedPopen(None)]
    with pytest.raises(TaskExecutionError):
        run(Prepare.of(_composite_yaml), composite_with_failure)
    assert mock.call_count == 2


def test_runner_composite_if_success_skipped_after_failure(mocker: MockerFixture) -> None:
    """A composite subtask with if: success() is skipped after a prior subtask failed."""
    composite_with_success = {
        'prepare-assignment/composite@latest': CompositeTaskDefinition(
            id='composite', name='Composite', description='',
            inputs=[TaskInputDefinition(name='input', description='', required=True, type='string', default=None, items=None)],
            outputs={}, path='',
            tasks=[
                {'name': 'fails', 'uses': 'remove', 'with': {'input': ['out'], 'force': True, 'recursive': True}},
                {'name': 'skipped', 'if': 'success()', 'uses': 'remove', 'with': {'input': ['out'], 'force': True, 'recursive': True}},
            ]
        ),
        'prepare-assignment/remove@latest': mapping['prepare-assignment/remove@latest'],
    }
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopenFail
    with pytest.raises(TaskExecutionError):
        run(Prepare.of(_composite_yaml), composite_with_success)
    assert mock.call_count == 1


# ── set-env propagation ───────────────────────────────────────────────────────

_SET_ENV_LINE = f"{DEMARCATION}set-env{DEMARCATION}MY_VAR{DEMARCATION}\"hello\"\n"
_SET_ENV_COMPOSITE_LINE = f"{DEMARCATION}set-env{DEMARCATION}COMPOSITE_VAR{DEMARCATION}\"from-composite\"\n"

_two_tasks_yaml = dict(name='Test', jobs={'prepare': [
    {'name': 'setter', 'uses': 'remove', 'id': 'setter',
     'with': {'input': ['out'], 'force': True, 'recursive': True}},
    {'name': 'reader', 'uses': 'remove', 'id': 'reader',
     'with': {'input': ['out'], 'force': True, 'recursive': True}},
]})

_composite_then_task_yaml = dict(name='Test', jobs={'prepare': [
    {'name': 'test composite', 'uses': 'composite', 'with': {'input': 'test'}},
    {'name': 'reader', 'uses': 'remove', 'id': 'reader',
     'with': {'input': ['out'], 'force': True, 'recursive': True}},
]})


def _make_popen_factory(outputs: List[List[str]]) -> Any:
    """Return a Popen factory that cycles through the given stdout line lists and records env kwargs."""
    call_envs: List[Dict[str, str]] = []
    call_index = [0]

    class _Popen(MockedPopen):
        def __init__(self, args: Any, **kwargs: Any) -> None:
            super().__init__(args, **kwargs)
            call_envs.append(dict(kwargs.get("env") or {}))
            self._lines = outputs[min(call_index[0], len(outputs) - 1)]
            call_index[0] += 1

        @property
        def stdout(self) -> List[str]:
            return self._lines

    _Popen.captured = call_envs  # type: ignore
    return _Popen


def test_set_env_available_in_next_task_subprocess(mocker: MockerFixture) -> None:
    """Env var written by task A via set-env appears in task B's subprocess environment."""
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    factory = _make_popen_factory([[_SET_ENV_LINE], []])
    mock.side_effect = factory
    run(Prepare.of(_two_tasks_yaml), mapping)
    assert mock.call_count == 2
    assert factory.captured[1].get("MY_VAR") == "hello"  # type: ignore


def test_set_env_available_in_next_task_expression(mocker: MockerFixture) -> None:
    """Env var written by task A via set-env is accessible in task B's if: expression."""
    yaml = dict(name='Test', jobs={'prepare': [
        {'name': 'setter', 'uses': 'remove', 'id': 'setter',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
        {'name': 'reader', 'uses': 'remove', 'id': 'reader', 'if': "env.MY_VAR == 'hello'",
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
    ]})
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    factory = _make_popen_factory([[_SET_ENV_LINE], []])
    mock.side_effect = factory
    run(Prepare.of(yaml), mapping)
    # reader's if: condition is true → both tasks ran
    assert mock.call_count == 2


def test_set_env_not_set_expression_skips_task(mocker: MockerFixture) -> None:
    """If set-env was never called, an if: expression checking that var evaluates false → task skipped."""
    yaml = dict(name='Test', jobs={'prepare': [
        {'name': 'reader', 'uses': 'remove', 'id': 'reader', 'if': "env.MY_VAR == 'hello'",
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
    ]})
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    mock.side_effect = MockedPopen
    run(Prepare.of(yaml), mapping)
    assert mock.call_count == 0


def test_run_task_set_env(mocker: MockerFixture) -> None:
    """Env var written by a run: task via set-env appears in the next task's subprocess environment."""
    yaml_run_set_env = dict(name='Test', jobs={'prepare': [
        {'name': 'setter', 'run': 'echo something'},
        {'name': 'reader', 'uses': 'remove', 'id': 'reader',
         'with': {'input': ['out'], 'force': True, 'recursive': True}},
    ]})
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    factory = _make_popen_factory([[_SET_ENV_LINE], []])
    mock.side_effect = factory
    run(Prepare.of(yaml_run_set_env), mapping)
    assert mock.call_count == 2
    assert factory.captured[1].get("MY_VAR") == "hello"  # type: ignore


def test_set_env_inside_composite_propagates_to_next_task(mocker: MockerFixture) -> None:
    """Env var set inside a composite subtask is visible to subsequent top-level tasks."""
    mocker.patch("prepare_assignment.core.runner.tasks_logger")
    mock = mocker.patch("prepare_assignment.core.runner.subprocess.Popen")
    # First call = composite's subtask (outputs set-env), second call = top-level reader
    factory = _make_popen_factory([[_SET_ENV_COMPOSITE_LINE], []])
    mock.side_effect = factory
    run(Prepare.of(_composite_then_task_yaml), mapping)
    assert mock.call_count == 2
    assert factory.captured[1].get("COMPOSITE_VAR") == "from-composite"  # type: ignore
