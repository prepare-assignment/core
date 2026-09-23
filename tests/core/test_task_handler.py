from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core import task_handler
from prepare_assignment.data.task_properties import TaskProperties

TASK_YML = """id: remove
name: Remove
description: Remove files
inputs:
  input:
    description: files
    type: array
    items: string
    required: true
runs:
  using: python
  main: main.py
"""


@pytest.fixture
def tasks_dir(tmp_path: Path, mocker: MockerFixture) -> Path:
    mocker.patch("prepare_assignment.data.task_properties.tasks_path", tmp_path)
    # Only exact tags (v1.0.0) are fixed in these tests
    mocker.patch("prepare_assignment.core.task_handler.is_fixed_version",
                 side_effect=lambda url, version: version == "v1.0.0")
    return tmp_path


def _install_fake(props: TaskProperties, marker: str) -> None:
    props.repo_path.mkdir(parents=True, exist_ok=True)
    props.definition_path.write_text(TASK_YML)
    (props.task_path / "marker").write_text(marker)


def test_update_restores_previous_version_on_failure(tasks_dir: Path, mocker: MockerFixture) -> None:
    props = TaskProperties.of("remove")
    _install_fake(props, "old")

    def failing_add(task: str) -> None:
        # Simulate a partial install before failing
        props.task_path.mkdir(parents=True)
        raise RuntimeError("network down")

    mocker.patch("prepare_assignment.core.task_handler.add", side_effect=failing_add)
    with pytest.raises(RuntimeError):
        task_handler.update("remove", recursive=False)
    assert (props.task_path / "marker").read_text() == "old"
    assert not Path(f"{props.task_path}.backup").exists()


def test_update_replaces_version_on_success(tasks_dir: Path, mocker: MockerFixture) -> None:
    props = TaskProperties.of("remove")
    _install_fake(props, "old")
    mocker.patch("prepare_assignment.core.task_handler.add", side_effect=lambda task: _install_fake(props, "new"))
    task_handler.update("remove", recursive=False)
    assert (props.task_path / "marker").read_text() == "new"
    assert not Path(f"{props.task_path}.backup").exists()


def test_update_not_installed_adds(tasks_dir: Path, mocker: MockerFixture) -> None:
    add = mocker.patch("prepare_assignment.core.task_handler.add")
    mocker.patch("prepare_assignment.core.task_handler.get_dependencies",
                 return_value={TaskProperties.of("remove")})
    task_handler.update("remove", recursive=True)
    add.assert_called_once_with("prepare-assignment/remove@latest")


def test_update_fixed_version_is_skipped(tasks_dir: Path, mocker: MockerFixture) -> None:
    add = mocker.patch("prepare_assignment.core.task_handler.add")
    task_handler.update("remove@v1.0.0", recursive=False)
    add.assert_not_called()


def test_update_moving_version_prefix_is_updated(tasks_dir: Path, mocker: MockerFixture) -> None:
    add = mocker.patch("prepare_assignment.core.task_handler.add")
    task_handler.update("remove@v1", recursive=False)
    add.assert_called_once_with("prepare-assignment/remove@v1")


def test_info_uses_task_path(tasks_dir: Path, capsys: pytest.CaptureFixture) -> None:
    props = TaskProperties.of("remove")
    _install_fake(props, "x")
    task_handler.info("remove")
    assert "id: remove" in capsys.readouterr().out


def test_load_task_uses_task_path(tasks_dir: Path) -> None:
    from prepare_assignment.utils.tasks import load_task
    props = TaskProperties.of("remove")
    _install_fake(props, "x")
    assert load_task(props).path == props.task_path


def test_version_with_slash(tasks_dir: Path, mocker: MockerFixture, capsys: pytest.CaptureFixture) -> None:
    from prepare_assignment.utils.tasks import get_all_tasks
    mocker.patch("prepare_assignment.utils.tasks.get_tasks_path", return_value=tasks_dir)
    mocker.patch("prepare_assignment.core.task_handler.tasks_path", tasks_dir)
    props = TaskProperties.of("remove@fix/something")
    _install_fake(props, "branch")
    assert get_all_tasks() == [props]
    task_handler.ls()
    assert "fix/something" in capsys.readouterr().out
