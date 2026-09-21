import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Final, Dict, Any

import git
import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core.preparer import prepare_tasks, __task_install_dependencies
from prepare_assignment.data.errors import DependencyError, PrepareTaskError
from virtualenv import cli_run  # type: ignore

from prepare_assignment.utils.paths import get_cache_path

PREPARE: Final[Dict[str, Any]] = {
    'prepare': [
        {'name': 'test composite', 'uses': 'composite2', 'with': {'input': 'test'}},
        {'name': 'codestripper', 'uses': 'codestripper', 'with': {'include': ['**/*.java', 'pom.xml'],
                                                                  'working-directory': 'solution', 'verbosity': 5}},
        {'name': 'remove', 'uses': 'remove', 'id': 'remove', 'with': {'input': ['out', '*.zip'], 'force': True,
                                                                      'recursive': True}},
        {'name': 'run command', 'run': "echo '${{ tasks.remove.outputs.files }}' | jq"}
    ]
}

CACHE_PATH: Final[str] = os.path.join(tempfile.gettempdir(), "prepare")
TASKS_PATH: Final[str] = os.path.join(CACHE_PATH, "tasks")


@pytest.fixture(scope="class", autouse=True)
def set_cache(class_mocker) -> None:
    git_mode = os.environ.get("PREPARE_TEST_GIT_MODE", "ssh")
    class_mocker.patch("prepare_assignment.core.versions.CONFIG.core.git_mode", git_mode)

    class_mocker.patch("prepare_assignment.core.preparer.cache_path", CACHE_PATH)
    class_mocker.patch("prepare_assignment.data.task_properties.tasks_path", TASKS_PATH)
    class_mocker.patch("prepare_assignment.core.preparer.tasks_path", TASKS_PATH)


def __clean_cache() -> None:

    if not os.path.exists(CACHE_PATH):
        return

    # We need to fix the readonly git directory on windows
    def onerror(func, path, exec_info):
        import stat
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IWUSR)
            func(path)

    if sys.platform == "win32":
        shutil.rmtree(CACHE_PATH, onerror=onerror)
    else:
        shutil.rmtree(CACHE_PATH, ignore_errors=True)

    Path(CACHE_PATH).mkdir(parents=True, exist_ok=True)


def test_prepare_run_task() -> None:
    prepare = {
        'prepare': [
            {'name': 'run command', 'run': "echo '${{ tasks.remove.outputs.files }}' | jq"}
        ]
    }
    __clean_cache()
    mapping = prepare_tasks("prepare.yml", prepare)
    assert len(mapping) == 0


def test_prepare_python_task() -> None:
    prepare = {
        'prepare': [
            {'name': 'remove', 'uses': 'remove', 'with': {'input': ['out', '*.zip'], 'force': True}}
        ]
    }
    __clean_cache()

    mapping = prepare_tasks("prepare.yml", prepare)
    assert len(mapping) == 1


def test_prepare_already_available(mocker: MockerFixture) -> None:
    prepare = {
        'prepare': [
            {'name': 'remove', 'uses': 'remove', 'with': {'input': ['out', '*.zip'], 'force': True}}
        ]
    }
    __clean_cache()
    spy = mocker.spy(git.Repo, "clone_from")
    prepare_tasks("prepare.yml", prepare)
    mapping = prepare_tasks("prepare.yml", prepare)
    assert len(mapping) == 1
    spy.assert_called_once()


def test_prepare_specific_version() -> None:
    prepare = {
        'prepare': [
            {'name': 'remove', 'uses': 'remove@v1.0.0', 'with': {'input': ['out', '*.zip'], 'force': True}}
        ]
    }
    __clean_cache()

    mapping = prepare_tasks("prepare.yml", prepare)
    assert len(mapping) == 1


def test_prepare_composite_task(mocker: MockerFixture) -> None:
    prepare = {
        'prepare': [
            {'name': 'composite', 'uses': 'composite', 'with': {'input': 'test'}}
        ]
    }
    __clean_cache()
    spy = mocker.spy(git.Repo, "clone_from")
    mapping = prepare_tasks("prepare.yml", prepare)
    assert len(mapping) == 2
    assert spy.call_count == 2
    mapping = prepare_tasks("prepare.yml", prepare)
    assert len(mapping) == 2
    # Should load from disk, not clone again
    assert spy.call_count == 2


def test_prepare_task_main_outside_repo(mocker: MockerFixture) -> None:
    task_yaml_evil = {
        'id': 'evil',
        'name': 'Evil task',
        'description': 'Evil',
        'runs': {
            'using': 'python',
            'main': '../../evil.py'
        }
    }
    __clean_cache()
    mocker.patch("prepare_assignment.core.preparer.__download_task")
    mocker.patch("prepare_assignment.core.preparer.validate_task_definition", return_value=task_yaml_evil)
    mocker.patch("prepare_assignment.core.preparer.validate_default_values")
    mocker.patch("prepare_assignment.core.preparer.shutil.rmtree")
    prepare = {'prepare': [{'name': 'evil task', 'uses': 'evil', 'with': {}}]}
    with pytest.raises(PrepareTaskError) as exc_info:
        prepare_tasks("prepare.yml", prepare)
    assert isinstance(exc_info.value.cause, Exception)
    assert "outside" in str(exc_info.value.cause).lower() or "within" in str(exc_info.value.cause).lower()


def test_install_wrong_dependencies() -> None:
    with pytest.raises(DependencyError):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_run([os.path.join(tmpdir, "venv")])
            repo_path = os.path.join(tmpdir, "repo")
            os.mkdir(repo_path)
            with open(os.path.join(repo_path, "requirements.txt"), "w") as handle:
                handle.write("prepare_toolbox==0.0.0")
            __task_install_dependencies(tmpdir)


# ── schema generation ─────────────────────────────────────────────────────────

def _build_schema(task: Any) -> Dict[str, Any]:
    from prepare_assignment.core import preparer
    from prepare_assignment.data.task_properties import TaskProperties
    return preparer.__build_json_schema(TaskProperties.of(task.id), task)  # type: ignore[attr-defined]


def _python_task(inputs: Any, description: str = "desc") -> Any:
    from prepare_assignment.data.task_definition import PythonTaskDefinition
    return PythonTaskDefinition(id="remove", name="Remove", description=description, inputs=inputs,
                                outputs={}, path=Path(""), main="main.py")


def test_schema_without_inputs_is_valid() -> None:
    """Previously the template placeholders were not replaced for tasks without inputs → invalid JSON."""
    from prepare_assignment.core.validator import validate_tasks
    schema = _build_schema(_python_task([]))
    validate_tasks("prepare.yml", {"name": "x", "uses": "prepare-assignment/remove@latest"}, schema)


def test_schema_escapes_quotes() -> None:
    import json
    schema = _build_schema(_python_task([], description='Uses "quotes" and \\ backslashes'))
    assert json.loads(json.dumps(schema))["description"] == 'Uses "quotes" and \\ backslashes'


def test_schema_allows_step_properties() -> None:
    """'if' on a 'uses' step used to be rejected by the generated schema."""
    from prepare_assignment.core.validator import validate_tasks
    schema = _build_schema(_python_task([]))
    validate_tasks("prepare.yml", {"name": "x", "id": "x", "if": "always()",
                                   "uses": "prepare-assignment/remove@latest"}, schema)


def test_schema_rejects_unknown_step_property() -> None:
    from prepare_assignment.core.validator import validate_tasks
    from prepare_assignment.data.errors import ValidationError
    schema = _build_schema(_python_task([]))
    with pytest.raises(ValidationError):
        validate_tasks("prepare.yml", {"name": "x", "whit": {}, "uses": "prepare-assignment/remove@latest"}, schema)


def test_schema_required_inputs_and_defaults() -> None:
    from prepare_assignment.core.validator import validate_tasks
    from prepare_assignment.data.errors import ValidationError
    from prepare_assignment.data.task_definition import TaskInputDefinition
    schema = _build_schema(_python_task([
        TaskInputDefinition(name="input", description="d", required=True, type="array", items="string"),
        TaskInputDefinition(name="force", description="d", required=False, type="boolean", default=False),
    ]))
    assert schema["required"] == ["uses", "with"]
    assert schema["properties"]["with"]["required"] == ["input"]
    step: Dict[str, Any] = {"name": "x", "uses": "prepare-assignment/remove@latest", "with": {"input": ["a"]}}
    validate_tasks("prepare.yml", step, schema)
    assert step["with"]["force"] is False
    with pytest.raises(ValidationError):
        validate_tasks("prepare.yml", {"name": "x", "uses": "prepare-assignment/remove@latest", "with": {}}, schema)


# ── cache integrity ───────────────────────────────────────────────────────────

def test_incomplete_install_is_reinstalled(mocker: MockerFixture) -> None:
    prepare = {'prepare': [{'name': 'remove', 'uses': 'remove', 'with': {'input': ['out'], 'force': True}}]}
    __clean_cache()
    spy = mocker.spy(git.Repo, "clone_from")
    prepare_tasks("prepare.yml", prepare)
    schema_file = os.path.join(TASKS_PATH, "prepare-assignment", "remove", "latest", "remove.schema.json")
    assert os.path.isfile(schema_file)
    # Simulate an interrupted install: the directory exists, but the schema was never written
    os.remove(schema_file)
    mapping = prepare_tasks("prepare.yml", prepare)
    assert len(mapping) == 1
    assert spy.call_count == 2
    assert os.path.isfile(schema_file)


def test_missing_sub_task_of_cached_composite_is_installed(mocker: MockerFixture) -> None:
    prepare = {'prepare': [{'name': 'composite', 'uses': 'composite', 'with': {'input': 'test'}}]}
    __clean_cache()
    spy = mocker.spy(git.Repo, "clone_from")
    mapping = prepare_tasks("prepare.yml", prepare)
    sub_task = next(k for k in mapping if not k.startswith("prepare-assignment/composite@"))
    org, rest = sub_task.split("/")
    name, version = rest.split("@")
    shutil.rmtree(os.path.join(TASKS_PATH, org, name, version), ignore_errors=True)
    mapping = prepare_tasks("prepare.yml", prepare)
    assert sub_task in mapping
    assert spy.call_count == 3


def test_failed_prepare_writes_no_schema(mocker: MockerFixture) -> None:
    __clean_cache()
    mocker.patch("prepare_assignment.core.preparer.__download_task", side_effect=RuntimeError("network down"))
    prepare = {'prepare': [{'name': 'remove', 'uses': 'remove', 'with': {}}]}
    with pytest.raises(PrepareTaskError):
        prepare_tasks("prepare.yml", prepare)
    assert not os.path.exists(os.path.join(TASKS_PATH, "prepare-assignment", "remove", "latest"))


def test_cyclic_composite_is_detected(mocker: MockerFixture) -> None:
    from prepare_assignment.data.task_definition import CompositeTaskDefinition
    __clean_cache()
    cyclic = CompositeTaskDefinition(id="cyclic", name="cyclic", description="d", inputs=[], outputs={},
                                     path=Path(""), tasks=[{"name": "self", "uses": "cyclic"}])
    mocker.patch("prepare_assignment.core.preparer.__prepare_task",
                 return_value={"schema": {}, "task": cyclic})
    prepare = {'prepare': [{'name': 'cyclic', 'uses': 'cyclic', 'with': {}}]}
    with pytest.raises(PrepareTaskError) as exc:
        prepare_tasks("prepare.yml", prepare)
    assert "Cyclic" in str(exc.value.cause)


def test_schema_allows_new_step_properties() -> None:
    from prepare_assignment.core.validator import validate_tasks
    schema = _build_schema(_python_task([]))
    validate_tasks("prepare.yml", {"name": "x", "uses": "prepare-assignment/remove@latest",
                                   "working-directory": "a", "env": {"A": "b"}, "continue-on-error": True},
                   schema)


def test_outdated_schema_is_updated_on_load(mocker: MockerFixture) -> None:
    """Schemas generated by an older version of prepare didn't allow 'if' on steps."""
    import json
    prepare = {'prepare': [{'name': 'remove', 'uses': 'remove', 'with': {'input': ['out'], 'force': True}}]}
    __clean_cache()
    prepare_tasks("prepare.yml", prepare)
    schema_file = os.path.join(TASKS_PATH, "prepare-assignment", "remove", "latest", "remove.schema.json")
    with open(schema_file) as handle:
        schema = json.load(handle)
    del schema["properties"]["if"]
    with open(schema_file, "w") as handle:
        json.dump(schema, handle)
    spy = mocker.spy(git.Repo, "clone_from")
    prepare_with_if = {'prepare': [{'name': 'remove', 'uses': 'remove', 'if': 'always()',
                                    'with': {'input': ['out'], 'force': True}}]}
    prepare_tasks("prepare.yml", prepare_with_if)
    spy.assert_not_called()
    with open(schema_file) as handle:
        assert "if" in json.load(handle)["properties"]
