from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.data.errors import ValidationError
from prepare_assignment.utils.config import load_config


def _write(tmp_path: Path, mocker: MockerFixture, content: str) -> None:
    (tmp_path / "config.yml").write_text(content)
    mocker.patch("prepare_assignment.utils.config.get_config_path", return_value=tmp_path)


def test_default_shell(tmp_path: Path, mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.utils.config.get_config_path", return_value=tmp_path)
    assert load_config().core.shell == "bash"


def test_shell_from_config(tmp_path: Path, mocker: MockerFixture) -> None:
    _write(tmp_path, mocker, "core:\n  shell: pwsh\n  git-mode: https\n")
    config = load_config()
    assert config.core.shell == "pwsh"
    assert config.core.git_mode == "https"


def test_invalid_shell_in_config(tmp_path: Path, mocker: MockerFixture) -> None:
    _write(tmp_path, mocker, "core:\n  shell: fish\n")
    with pytest.raises(ValidationError):
        load_config()
