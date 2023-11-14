import os
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.utils.cache import get_cache_path


def test_cache_xdg_home(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.cache.sys")
    mocker.patch("prepare_assignment.utils.cache.__cache_path", None)
    mock.platform = "linux"
    mocker.patch.dict(os.environ, {"XDG_CACHE_HOME": "test"})
    expected = Path("test/prepare")
    cache_path = get_cache_path()
    assert cache_path == expected


def test_cache_linux(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.cache.sys")
    mocker.patch("prepare_assignment.utils.cache.__cache_path", None)
    mock.platform = "linux"
    expected = Path("~/.cache/prepare").expanduser()
    cache_path = get_cache_path()
    assert cache_path == expected


def test_cache_darwin(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.cache.sys")
    mocker.patch("prepare_assignment.utils.cache.__cache_path", None)
    mock.platform = "darwin"
    expected = Path("~/Library/Caches/prepare").expanduser()
    cache_path = get_cache_path()
    assert cache_path == expected


def test_cache_win32(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.cache.sys")
    mocker.patch("prepare_assignment.utils.cache.__cache_path", None)
    mock.platform = "win32"
    mocker.patch.dict(os.environ, {"LOCALAPPDATA": str(Path("AppData/Local"))})
    expected = Path("AppData/Local/prepare/cache")
    cache_path = get_cache_path()
    assert cache_path == expected


def test_cache_unsupported(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.cache.sys")
    mocker.patch("prepare_assignment.utils.cache.__cache_path", None)
    mock.platform = "unsupported"
    with pytest.raises(AssertionError):
        get_cache_path()
