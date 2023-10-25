import os
import shutil
import tempfile
from pathlib import Path
from typing import Final, Dict, Any

import git
import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core.preparer import prepare_actions, __action_install_dependencies
from prepare_assignment.data.errors import DependencyError
from prepare_assignment.utils import get_cache_path
from virtualenv import cli_run  # type: ignore

PREPARE: Final[Dict[str, Any]] = {
    'prepare': [
        {'name': 'test composite', 'uses': 'composite2', 'with': {'input': 'test'}},
        {'name': 'codestripper', 'uses': 'codestripper', 'with': {'include': ['**/*.java', 'pom.xml'], 'working-directory': 'solution', 'verbosity': 5}},
        {'name': 'remove', 'uses': 'remove', 'id': 'remove', 'with': {'input': ['out', '*.zip'], 'force': True, 'recursive': True}},
        {'name': 'run command', 'run': "echo '${{ steps.remove.outputs.files }}' | jq"}
    ]
}


@pytest.fixture(scope="class", autouse=True)
def set_cache(class_mocker) -> None:
    class_mocker.patch.dict(os.environ, {
        "XDG_CACHE_HOME": str(Path("/tmp")),
        "LOCALAPPDATA": str(Path(os.environ.get("Temp", "c:/temp")))
    })
    cache_path = get_cache_path()
    class_mocker.patch("prepare_assignment.core.preparer.cache_path", cache_path)


def __clean_cache() -> None:
    cache_path = get_cache_path()
    # We need to fix the readonly git directory on windows
    def onerror(func, path, exec_info):
        import stat
        if not os.access(path, os.W_OK):
            os.chmod(path, stat.S_IWUSR)
            func(path)
    shutil.rmtree(cache_path, onerror=onerror)
    Path(cache_path).mkdir(parents=True, exist_ok=True)


def test_prepare_run_action() -> None:
    prepare = {
        'prepare': [
            {'name': 'run command', 'run': "echo '${{ steps.remove.outputs.files }}' | jq"}
        ]
    }
    __clean_cache()
    mapping = prepare_actions("prepare.yml", prepare)
    assert len(mapping) == 0


def test_prepare_python_action(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.preparer.CONFIG.GIT_MODE", return_value="ssh")
    prepare = {
        'prepare': [
            {'name': 'remove', 'uses': 'remove', 'with': {'input': ['out', '*.zip'], 'force': True}}
        ]
    }
    __clean_cache()

    mapping = prepare_actions("prepare.yml", prepare)
    assert len(mapping) == 1


def test_prepare_already_available(mocker: MockerFixture) -> None:
    prepare = {
        'prepare': [
            {'name': 'remove', 'uses': 'remove', 'with': {'input': ['out', '*.zip'], 'force': True}}
        ]
    }
    __clean_cache()
    spy = mocker.spy(git.Repo, "clone_from")
    prepare_actions("prepare.yml", prepare)
    mapping = prepare_actions("prepare.yml", prepare)
    assert len(mapping) == 1
    spy.assert_called_once()


def test_prepare_specific_version() -> None:
    prepare = {
        'prepare': [
            {'name': 'remove', 'uses': 'remove@v1.0.0', 'with': {'input': ['out', '*.zip'], 'force': True}}
        ]
    }
    __clean_cache()

    mapping = prepare_actions("prepare.yml", prepare)
    assert len(mapping) == 1


def test_prepare_composite_action(mocker: MockerFixture) -> None:
    prepare = {
        'prepare': [
            {'name': 'composite', 'uses': 'composite', 'with': {'input': 'test'}}
        ]
    }
    __clean_cache()
    spy = mocker.spy(git.Repo, "clone_from")
    mapping = prepare_actions("prepare.yml", prepare)
    assert len(mapping) == 2
    assert spy.call_count == 2
    mapping = prepare_actions("prepare.yml", prepare)
    assert len(mapping) == 2
    # Should load from disk, not clone again
    assert spy.call_count == 2


def test_install_wrong_dependencies() -> None:
    with pytest.raises(DependencyError) as pytest_wrapped_e:
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_run([os.path.join(tmpdir, "venv")])
            repo_path = os.path.join(tmpdir, "repo")
            os.mkdir(repo_path)
            with open(os.path.join(repo_path, "requirements.txt"), "w") as handle:
                handle.write("prepare_toolbox==0.0.0")
            __action_install_dependencies(tmpdir)
