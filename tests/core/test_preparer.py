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
from prepare_assignment.data.errors import DependencyError
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
    class_mocker.patch("prepare_assignment.core.preparer.CONFIG.core.git_mode", git_mode)

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


def test_install_wrong_dependencies() -> None:
    with pytest.raises(DependencyError):
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_run([os.path.join(tmpdir, "venv")])
            repo_path = os.path.join(tmpdir, "repo")
            os.mkdir(repo_path)
            with open(os.path.join(repo_path, "requirements.txt"), "w") as handle:
                handle.write("prepare_toolbox==0.0.0")
            __task_install_dependencies(tmpdir)
