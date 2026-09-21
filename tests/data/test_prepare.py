from typing import Any, Dict

import pytest

from prepare_assignment.core.validator import validate_prepare
from prepare_assignment.data.errors import ValidationError
from prepare_assignment.data.prepare import Task, RunTask, UsesTask


def test_run_task_defaults() -> None:
    task = Task.of({"name": "Echo it", "run": "echo hi"})
    assert isinstance(task, RunTask)
    assert task.shell is None
    assert task.working_directory is None
    assert task.env == {}
    assert task.continue_on_error is False
    assert task.key == "echo-it"


def test_run_task_all_properties() -> None:
    task = Task.of({"name": "x", "id": "x-id", "if": "always()", "run": "echo hi", "shell": "pwsh",
                    "working-directory": "sub", "env": {"A": "b"}, "continue-on-error": True})
    assert isinstance(task, RunTask)
    assert task.shell == "pwsh"
    assert task.working_directory == "sub"
    assert task.env == {"A": "b"}
    assert task.continue_on_error is True
    assert task.if_ == "always()"
    assert task.key == "x-id"


def test_uses_task_all_properties() -> None:
    task = Task.of({"name": "x", "uses": "remove", "with": {"input": ["a"]},
                    "working-directory": "sub", "env": {"A": "b"}, "continue-on-error": True})
    assert isinstance(task, UsesTask)
    assert task.with_ == {"input": ["a"]}
    assert task.working_directory == "sub"
    assert task.env == {"A": "b"}
    assert task.continue_on_error is True


def _prepare(step: Dict[str, Any]) -> Dict[str, Any]:
    return {"name": "test", "jobs": {"prepare": [step]}}


@pytest.mark.parametrize("step", [
    {"name": "x", "run": "echo", "shell": "python", "working-directory": "a", "env": {"A": "b"},
     "continue-on-error": True, "if": "always()", "id": "x"},
    {"name": "x", "uses": "remove", "with": {}, "working-directory": "a", "env": {"A": "b"},
     "continue-on-error": False},
])
def test_prepare_schema_valid_steps(step: Dict[str, Any]) -> None:
    validate_prepare("prepare.yml", _prepare(step))


@pytest.mark.parametrize("step", [
    {"name": "x", "run": "echo", "shell": "fish"},
    {"name": "x", "uses": "remove", "shell": "bash"},
    {"name": "x", "run": "echo", "shel": "bash"},
    {"name": "x", "run": "echo", "env": {"A": 1}},
    {"name": "x", "run": "echo", "continue-on-error": "yes"},
    {"name": "x", "run": "echo", "with": {}},
])
def test_prepare_schema_invalid_steps(step: Dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        validate_prepare("prepare.yml", _prepare(step))
