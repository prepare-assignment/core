import pytest

from prepare_assignment.core.expression import evaluate, evaluate_condition
from prepare_assignment.data.job_environment import JobEnvironment


def env(**kwargs) -> JobEnvironment:  # type: ignore
    defaults = dict(environment={}, outputs={}, inputs={})
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
    e = env(environment={"MY_VAR": "hello"})
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


def test_evaluate_success_when_no_failure() -> None:
    e = env()
    assert evaluate("success()", e) is True


def test_evaluate_success_when_failed() -> None:
    e = env(job_failed=True)
    assert evaluate("success()", e) is False


def test_evaluate_failure_when_no_failure() -> None:
    e = env()
    assert evaluate("failure()", e) is False


def test_evaluate_failure_when_failed() -> None:
    e = env(job_failed=True)
    assert evaluate("failure()", e) is True


def test_evaluate_always() -> None:
    e = env()
    assert evaluate("always()", e) is True


def test_evaluate_always_when_failed() -> None:
    e = env(job_failed=True)
    assert evaluate("always()", e) is True


def test_evaluate_never() -> None:
    e = env()
    assert evaluate("never()", e) is False


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


# ── boolean coercion for env vars ─────────────────────────────────────────────

def test_evaluate_env_true_string_coerced_to_bool() -> None:
    """env var with value "true" is coerced to bool True."""
    e = env(environment={"release": "true"})
    assert evaluate_condition("env.release", e) is True


def test_evaluate_env_false_string_coerced_to_bool() -> None:
    """env var with value "false" is coerced to bool False."""
    e = env(environment={"release": "false"})
    assert evaluate_condition("env.release", e) is False


def test_evaluate_env_true_uppercase_coerced() -> None:
    """env var with value "True" (Python-style) is also coerced."""
    e = env(environment={"release": "True"})
    assert evaluate_condition("env.release", e) is True


def test_evaluate_env_bool_equals_true_literal() -> None:
    """env.release == true (lowercase literal) evaluates correctly."""
    e = env(environment={"release": "true"})
    assert evaluate_condition("env.release == true", e) is True


def test_evaluate_env_bool_equals_True_literal() -> None:
    """env.release == True (Python literal) evaluates correctly."""
    e = env(environment={"release": "true"})
    assert evaluate_condition("env.release == True", e) is True


def test_evaluate_env_false_not_equals_true_literal() -> None:
    """env.release == true is False when release is "false"."""
    e = env(environment={"release": "false"})
    assert evaluate_condition("env.release == true", e) is False


def test_evaluate_quoted_true_string_unchanged() -> None:
    """'true' inside quotes is not rewritten to Python True.
    For non-boolean env vars the quoted string comparison works as expected.
    For boolean-coerced env vars use the unquoted literal: env.flag == true."""
    # Non-boolean env var: 'true' literal is preserved, comparison works normally
    e = env(environment={"flag": "other"})
    assert evaluate_condition("env.flag == 'true'", e) is False
    # Boolean env var is coerced to True (bool); compare with unquoted true, not 'true'
    e2 = env(environment={"flag": "true"})
    assert evaluate_condition("env.flag == true", e2) is True
    assert evaluate_condition("env.flag == 'true'", e2) is False
