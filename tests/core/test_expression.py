import pytest

from prepare_assignment.core.expression import evaluate, evaluate_condition
from prepare_assignment.data.job_environment import JobEnvironment


def env(**kwargs) -> JobEnvironment:  # type: ignore
    defaults = dict(environment={}, outputs={}, inputs={}, env_vars={})
    defaults.update(kwargs)
    return JobEnvironment(**defaults)  # type: ignore


# ── evaluate ─────────────────────────────────────────────────────────────────

def test_evaluate_input() -> None:
    e = env(inputs={"name": "Alice"})
    assert evaluate("inputs.name", e) == "Alice"


def test_evaluate_input_wrapped() -> None:
    e = env(inputs={"name": "Alice"})
    assert evaluate("${{ inputs.name }}", e) == "Alice"


def test_evaluate_env_var() -> None:
    e = env(env_vars={"MY_VAR": "hello"})
    assert evaluate("env.MY_VAR", e) == "hello"


def test_evaluate_task_output() -> None:
    e = env(outputs={"step1": {"count": 3}})
    assert evaluate("tasks.step1.outputs.count", e) == 3


def test_evaluate_task_output_hyphenated() -> None:
    e = env(outputs={"codestripper": {"stripped-files": ["a.java", "b.java"]}})
    result = evaluate("tasks.codestripper.outputs.stripped-files", e)
    assert result == ["a.java", "b.java"]


def test_evaluate_comparison_equal() -> None:
    e = env(inputs={"x": 5})
    assert evaluate("inputs.x == 5", e) is True


def test_evaluate_comparison_not_equal() -> None:
    e = env(inputs={"x": 5})
    assert evaluate("inputs.x != 3", e) is True


def test_evaluate_logical_and() -> None:
    e = env(inputs={"a": True, "b": True})
    assert evaluate("inputs.a && inputs.b", e) is True


def test_evaluate_logical_and_false() -> None:
    e = env(inputs={"a": True, "b": False})
    assert evaluate("inputs.a && inputs.b", e) is False


def test_evaluate_logical_or() -> None:
    e = env(inputs={"a": False, "b": True})
    assert evaluate("inputs.a || inputs.b", e) is True


def test_evaluate_logical_not() -> None:
    e = env(inputs={"flag": False})
    assert evaluate("!inputs.flag", e) is True


def test_evaluate_not_equal_operator_not_broken() -> None:
    """!= must not be converted to 'not ='"""
    e = env(inputs={"x": 5})
    assert evaluate("inputs.x != 3", e) is True


def test_evaluate_contains_function() -> None:
    e = env(inputs={"files": ["a.java", "b.java"]})
    assert evaluate("contains(inputs.files, 'a.java')", e) is True


def test_evaluate_contains_function_false() -> None:
    e = env(inputs={"files": ["a.java", "b.java"]})
    assert evaluate("contains(inputs.files, 'c.java')", e) is False


def test_evaluate_starts_with() -> None:
    e = env(inputs={"name": "hello world"})
    assert evaluate("startsWith(inputs.name, 'hello')", e) is True


def test_evaluate_ends_with() -> None:
    e = env(inputs={"name": "hello world"})
    assert evaluate("endsWith(inputs.name, 'world')", e) is True


def test_evaluate_success() -> None:
    e = env()
    assert evaluate("success()", e) is True


def test_evaluate_failure() -> None:
    e = env()
    assert evaluate("failure()", e) is False


def test_evaluate_always() -> None:
    e = env()
    assert evaluate("always()", e) is True


def test_evaluate_literal_string() -> None:
    e = env()
    assert evaluate("'hello'", e) == "hello"


def test_evaluate_literal_number() -> None:
    e = env()
    assert evaluate("42", e) == 42


# ── evaluate_condition ────────────────────────────────────────────────────────

def test_evaluate_condition_true() -> None:
    e = env(inputs={"x": 1})
    assert evaluate_condition("inputs.x == 1", e) is True


def test_evaluate_condition_false() -> None:
    e = env(inputs={"x": 1})
    assert evaluate_condition("inputs.x == 2", e) is False


def test_evaluate_condition_invalid_returns_false() -> None:
    e = env()
    assert evaluate_condition("nonexistent.variable", e) is False


def test_evaluate_condition_wrapped() -> None:
    e = env(inputs={"flag": True})
    assert evaluate_condition("${{ inputs.flag }}", e) is True
