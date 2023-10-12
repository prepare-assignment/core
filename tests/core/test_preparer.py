import os
import shutil
from pathlib import Path
from typing import Final, Dict, Any

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core.preparer import prepare_actions
from prepare_assignment.utils import get_cache_path

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


def __clean_cache() -> None:
    cache_path = get_cache_path()
    shutil.rmtree(cache_path, ignore_errors=True)
    os.mkdir(cache_path)


def test_prepare_run_action() -> None:
    prepare = {
        'prepare': [
            {'name': 'run command', 'run': "echo '${{ steps.remove.outputs.files }}' | jq"}
        ]
    }
    __clean_cache()
    mapping = prepare_actions("prepare.yml", prepare)
    assert len(mapping) == 0


def test_prepare_composite_action() -> None:
    prepare = {
        'prepare': [
            {'name': 'codestripper', 'uses': 'codestripper', 'with': {'include': ['**/*.java']}}
        ]
    }
    __clean_cache()

    mapping = prepare_actions("prepare.yml", prepare)
    assert len(mapping) == 1
