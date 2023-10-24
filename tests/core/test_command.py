import json
import logging
from typing import Callable, List

import pytest

from prepare_assignment.core.command import handle_set_failed, handle_debug, handle_info, handle_warning, handle_error, \
    handle_set_output
from prepare_assignment.data.action_definition import PythonActionDefinition, ActionOutputDefinition
from prepare_assignment.data.prepare import Action, UsesAction
from prepare_assignment.data.step_environment import StepEnvironment


output = ActionOutputDefinition(description="test", items=None, type="string")
action_definition = PythonActionDefinition(outputs={'test': output},
                                           description="test",
                                           inputs=[],
                                           id="test",
                                           name="test",
                                           path="path",
                                           main="main.py")
action = UsesAction(name="test", id="id", with_={}, uses="test")
env = StepEnvironment(environment={},
                      outputs={'id': {}},
                      inputs={},
                      current_action_definition=action_definition,
                      current_action=action)


@pytest.mark.parametrize(
    "function, level", [
        (handle_set_failed, logging.ERROR),
        (handle_error, logging.ERROR),
        (handle_warning, logging.WARNING),
        (handle_info, logging.INFO),
        (handle_debug, logging.DEBUG),
    ]
)
def test_handle_functions(function: Callable[[StepEnvironment, List[str]], None],
                          level: int,
                          caplog: pytest.LogCaptureFixture) -> None:
    message = "message"
    with caplog.at_level(level):
        function(env, [message])
    assert message in caplog.text
    for record in caplog.records:
        assert record.levelno == level


@pytest.mark.parametrize(
    "function", [
        handle_set_failed,
        handle_error,
        handle_warning,
        handle_info,
        handle_debug,
        handle_set_output
    ]
)
def test_handle_functions_fail(function: Callable[[StepEnvironment, List[str]], None]) -> None:
    with pytest.raises(AssertionError) as pytest_wrapped_e:
        function(env, [])


def test_handle_set_output_no_json() -> None:
    with pytest.raises(AssertionError) as pytest_wrapped_e:
        handle_set_output(env, ["message", "not a dict"])
    assert "JSON" in str(pytest_wrapped_e.value)


def test_handle_set_output_no_dict() -> None:
    with pytest.raises(AssertionError) as pytest_wrapped_e:
        handle_set_output(env, ["message", json.dumps("not a dict")])
    assert "dictionary" in str(pytest_wrapped_e.value)


def test_handle_set_output_non_key(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        handle_set_output(env, ["test", json.dumps({"testkey": "test"})])
    assert "testkey" in caplog.text


def test_handle_set_output_wrong_type(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        handle_set_output(env, ["test", json.dumps({"test": 1})])
    assert "type" in caplog.text


def test_handle_set_output_success() -> None:
    handle_set_output(env, ["test", json.dumps({"test": "asd"})])
    assert env.outputs['id']['test'] == "asd"