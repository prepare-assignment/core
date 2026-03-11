import re
from typing import Any, Dict

from simpleeval import EvalWithCompoundTypes, InvalidExpression

from prepare_assignment.data.job_environment import JobEnvironment

_OP_RE = re.compile(r'&&|\|\||!(?!=)')
# Match attribute access where the name contains hyphens (not valid Python identifiers)
# e.g. .stripped-files → ["stripped-files"]
_HYPHEN_ATTR_RE = re.compile(r'\.([a-zA-Z_][a-zA-Z0-9_]*(?:-[a-zA-Z0-9_]+)+)')


def _preprocess(expr: str) -> str:
    def replace_op(m: re.Match) -> str:  # type: ignore
        token = m.group(0)
        if token == "&&":
            return " and "
        if token == "||":
            return " or "
        return "not "

    expr = _OP_RE.sub(replace_op, expr)
    expr = _HYPHEN_ATTR_RE.sub(lambda m: f'["{m.group(1)}"]', expr)
    return expr


class _Namespace:
    """Wraps a dict to allow attribute-style access (e.g. inputs.foo, tasks.step.outputs.bar)."""

    def __init__(self, d: Dict[str, Any]) -> None:
        object.__setattr__(self, "_d", d)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        d: Dict[str, Any] = object.__getattribute__(self, "_d")
        _MISSING = object()
        val = d.get(name, _MISSING)
        if val is _MISSING:
            raise AttributeError(name)
        return _Namespace(val) if isinstance(val, dict) else val

    def __getitem__(self, key: str) -> Any:
        d: Dict[str, Any] = object.__getattribute__(self, "_d")
        val = d[key]
        return _Namespace(val) if isinstance(val, dict) else val

    def __contains__(self, item: Any) -> bool:
        d: Dict[str, Any] = object.__getattribute__(self, "_d")
        return item in d


def _build_names(environment: JobEnvironment) -> Dict[str, Any]:
    tasks_ctx = {
        step: {"outputs": outputs}
        for step, outputs in environment.outputs.items()
    }
    return {
        "inputs": _Namespace(environment.inputs),
        "env": _Namespace(environment.env_vars),
        "tasks": _Namespace(tasks_ctx),
    }


def _contains(collection: Any, item: Any) -> bool:
    return item in collection


def _starts_with(s: str, prefix: str) -> bool:
    return s.startswith(prefix)


def _ends_with(s: str, suffix: str) -> bool:
    return s.endswith(suffix)


_FUNCTIONS = {
    "contains": _contains,
    "startsWith": _starts_with,
    "endsWith": _ends_with,
    "success": lambda: True,
    "failure": lambda: False,
    "always": lambda: True,
}


def evaluate(expr: str, environment: JobEnvironment) -> Any:
    """
    Evaluate an expression, optionally wrapped in ${{ }}.
    Returns the typed result.
    """
    stripped = expr.strip()
    m = re.fullmatch(r'\${{\s*(.*?)\s*}}', stripped, re.DOTALL)
    if m:
        stripped = m.group(1).strip()

    processed = _preprocess(stripped)
    names = _build_names(environment)
    evaluator = EvalWithCompoundTypes(names=names, functions=_FUNCTIONS)
    return evaluator.eval(processed)


def evaluate_condition(expr: str, environment: JobEnvironment) -> bool:
    """
    Evaluate an expression as a boolean condition.
    """
    try:
        result = evaluate(expr, environment)
        return bool(result)
    except (InvalidExpression, Exception):
        return False
