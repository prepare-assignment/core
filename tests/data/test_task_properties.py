import os

import pytest

from prepare_assignment.data.task_properties import TaskProperties, directory_to_version, version_to_directory


@pytest.mark.parametrize("task, expected", [
    ("remove", TaskProperties("prepare-assignment", "remove", "latest")),
    ("remove@v1", TaskProperties("prepare-assignment", "remove", "v1")),
    ("prepare-assignment/remove", TaskProperties("prepare-assignment", "remove", "latest")),
    ("org/remove@v1.0.0", TaskProperties("org", "remove", "v1.0.0")),
    ("prc2-assignment@fix/tasks-and-shell", TaskProperties("prepare-assignment", "prc2-assignment",
                                                           "fix/tasks-and-shell")),
    ("prepare-assignment/remove@fix/something", TaskProperties("prepare-assignment", "remove", "fix/something")),
    ("remove@feat/a@b", TaskProperties("prepare-assignment", "remove", "feat/a@b")),
])
def test_of(task: str, expected: TaskProperties) -> None:
    assert TaskProperties.of(task) == expected


def test_of_more_than_one_slash_in_name() -> None:
    with pytest.raises(ValueError):
        TaskProperties.of("a/b/c@v1")


def test_str_keeps_slash_in_version() -> None:
    assert str(TaskProperties.of("remove@fix/something")) == "prepare-assignment/remove@fix/something"


def test_task_path_is_single_directory_for_version() -> None:
    props = TaskProperties.of("remove@fix/something")
    assert props.task_path.name == "fix%2Fsomething"
    assert props.task_path.parent.name == "remove"


def test_task_path_unchanged_for_plain_version() -> None:
    assert TaskProperties.of("remove@v1.0.0").task_path.name == "v1.0.0"


@pytest.mark.parametrize("version", ["v1", "fix/something", "a/b/c", "100%", "%2F", "a%2F/b%25"])
def test_version_directory_round_trip(version: str) -> None:
    directory = version_to_directory(version)
    assert os.sep not in directory
    assert directory_to_version(directory) == version
