import os
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.utils.paths import get_cache_path, get_config_path


def test_cache_xdg_home(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__cache_path", None)
    mock.platform = "linux"
    mocker.patch.dict(os.environ, {"XDG_CACHE_HOME": "test"})
    expected = Path("test/prepare")
    cache_path = get_cache_path()
    assert cache_path == expected


def test_cache_linux(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__cache_path", None)
    mock.platform = "linux"
    expected = Path("~/.cache/prepare").expanduser()
    cache_path = get_cache_path()
    assert cache_path == expected


def test_cache_darwin(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__cache_path", None)
    mock.platform = "darwin"
    expected = Path("~/Library/Caches/prepare").expanduser()
    cache_path = get_cache_path()
    assert cache_path == expected


def test_cache_win32(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__cache_path", None)
    mock.platform = "win32"
    mocker.patch.dict(os.environ, {"LOCALAPPDATA": str(Path("AppData/Local"))})
    expected = Path("AppData/Local/prepare/cache")
    cache_path = get_cache_path()
    assert cache_path == expected


def test_cache_unsupported(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__cache_path", None)
    mock.platform = "unsupported"
    with pytest.raises(AssertionError):
        get_cache_path()

def test_config_xdg_home(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__config_path", None)
    mock.platform = "linux"
    mocker.patch.dict(os.environ, {"XDG_CONFIG_HOME": "test"})
    expected = Path("test/prepare")
    config_path = get_config_path()
    assert config_path == expected


def test_config_linux(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__config_path", None)
    mock.platform = "linux"
    expected = Path("~/.config/prepare").expanduser()
    config_path = get_config_path()
    assert config_path == expected


def test_config_darwin(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__config_path", None)
    mock.platform = "darwin"
    expected = Path("~/Library/Application Support/prepare").expanduser()
    config_path = get_config_path()
    assert config_path == expected


def test_config_win32(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__config_path", None)
    mock.platform = "win32"
    mocker.patch.dict(os.environ, {"APPDATA": str(Path("AppData/Roaming"))})
    expected = Path("AppData/Roaming/prepare")
    config_path = get_config_path()
    assert config_path == expected


def test_config_unsupported(mocker: MockerFixture) -> None:
    mock = mocker.patch("prepare_assignment.utils.paths.sys")
    mocker.patch("prepare_assignment.utils.paths.__config_path", None)
    mock.platform = "unsupported"
    with pytest.raises(AssertionError):
        get_config_path()