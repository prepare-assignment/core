import re
from typing import Any, Dict

from simpleeval import EvalWithCompoundTypes

from prepare_assignment.data.errors import ExpressionError
from prepare_assignment.data.job_environment import JobEnvironment

# Single pass tokenizer: quoted strings are matched first (and left untouched), so the rewrites below
# never apply inside string literals.
_TOKEN_RE = re.compile(
    r"""(?P<string>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")"""
    r"|(?P<and>&&)"
    r"|(?P<or>\|\|)"
    r"|(?P<not>!(?!=))"
    # Attribute access where the name contains hyphens (not valid Python identifiers)
    # e.g. .stripped-files → ["stripped-files"]
    r"|\.(?P<hyphen>[a-zA-Z_][a-zA-Z0-9_]*(?:-[a-zA-Z0-9_]+)+)"
    r"|(?P<bool>\b(?:true|false)\b)"
)
_STATUS_FUNCTION_RE = re.compile(r"\b(?:success|failure|always)\s*\(")


def _preprocess(expr: str) -> str:
    def replace(m: re.Match) -> str:  # type: ignore
        kind = m.lastgroup
        if kind == "and":
            return " and "
        if kind == "or":
            return " or "
        if kind == "not":
            return " not "
        if kind == "hyphen":
            return f'["{m.group("hyphen")}"]'
        if kind == "bool":
            return str(m.group("bool")).capitalize()
        return str(m.group(0))

    return _TOKEN_RE.sub(replace, expr).strip()


def _strip_wrapper(expr: str) -> str:
    stripped = expr.strip()
    m = re.fullmatch(r'\${{\s*(.*?)\s*}}', stripped, re.DOTALL)
    if m:
        stripped = m.group(1).strip()
    return stripped


def has_status_function(expr: str) -> bool:
    """
    Check whether an expression calls one of the status functions (success(), failure(), always()),
    ignoring occurrences inside string literals.
    """
    without_strings = _TOKEN_RE.sub(lambda m: "''" if m.lastgroup == "string" else m.group(0), expr)
    return _STATUS_FUNCTION_RE.search(without_strings) is not None


_MISSING = object()


class _Namespace:
    """
    Wraps a dict to allow attribute-style access (e.g. inputs.foo, tasks.step.outputs.bar).

    Accessing a missing key raises an error (to catch typos), unless `missing_ok` is set, in which case
    None is returned (used for environment variables, which are legitimately optional).
    """

    def __init__(self, d: Dict[str, Any], name: str, missing_ok: bool = False) -> None:
        object.__setattr__(self, "_d", d)
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_missing_ok", missing_ok)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    def __getitem__(self, key: str) -> Any:
        d: Dict[str, Any] = object.__getattribute__(self, "_d")
        prefix: str = object.__getattribute__(self, "_name")
        val = d.get(key, _MISSING)
        if val is _MISSING:
            if object.__getattribute__(self, "_missing_ok"):
                return None
            available = ", ".join(sorted(str(k) for k in d.keys())) or "none"
            raise KeyError(f"'{prefix}.{key}' is not defined (available: {available})")
        return _Namespace(val, f"{prefix}.{key}") if isinstance(val, dict) else val

    def __contains__(self, item: Any) -> bool:
        d: Dict[str, Any] = object.__getattribute__(self, "_d")
        return item in d


def _coerce_env(env: Dict[str, str]) -> Dict[str, Any]:
    """Convert string "true"/"false" env var values to Python booleans."""
    result: Dict[str, Any] = {}
    for k, v in env.items():
        if v.lower() == "true":
            result[k] = True
        elif v.lower() == "false":
            result[k] = False
        else:
            result[k] = v
    return result


def _build_names(environment: JobEnvironment) -> Dict[str, Any]:
    tasks_ctx = {
        step: {"outputs": outputs}
        for step, outputs in environment.outputs.items()
    }
    return {
        "inputs": _Namespace(environment.inputs, "inputs"),
        "env": _Namespace(_coerce_env(environment.process_environment), "env", missing_ok=True),
        "tasks": _Namespace(tasks_ctx, "tasks"),
    }


def _contains(collection: Any, item: Any) -> bool:
    return item in collection


def _starts_with(s: str, prefix: str) -> bool:
    return s.startswith(prefix)


def _ends_with(s: str, suffix: str) -> bool:
    return s.endswith(suffix)


def _build_functions(environment: JobEnvironment) -> Dict[str, Any]:
    return {
        "contains": _contains,
        "startsWith": _starts_with,
        "endsWith": _ends_with,
        "success": lambda: not environment.job_failed,
        "failure": lambda: environment.job_failed,
        "always": lambda: True,
        "never": lambda: False,
    }


def evaluate(expr: str, environment: JobEnvironment) -> Any:
    """
    Evaluate an expression, optionally wrapped in ${{ }}.
    Returns the typed result.

    :raises ExpressionError: if the expression cannot be evaluated
    """
    stripped = _strip_wrapper(expr)
    processed = _preprocess(stripped)
    names = _build_names(environment)
    evaluator = EvalWithCompoundTypes(names=names, functions=_build_functions(environment))
    try:
        return evaluator.eval(processed)
    except Exception as e:
        reason = (e.args[0] if isinstance(e, KeyError) and e.args else str(e)) or type(e).__name__
        raise ExpressionError(f"Cannot evaluate expression '{stripped}': {reason}") from e


def evaluate_condition(expr: str, environment: JobEnvironment) -> bool:
    """
    Evaluate an expression as a boolean condition (the 'if' of a step).

    Like GitHub Actions, if the expression doesn't contain a status function (success(), failure(), always()),
    it is implicitly combined with success(), i.e. `success() && (<expr>)`.

    :raises ExpressionError: if the expression cannot be evaluated
    """
    stripped = _strip_wrapper(expr)
    if not has_status_function(stripped) and environment.job_failed:
        return False
    return bool(evaluate(stripped, environment))
