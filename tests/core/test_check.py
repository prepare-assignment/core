from pathlib import Path
import re
from typing import Callable, Dict, List, Optional

import pytest
from git import Git
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from prepare_assignment.cli.main import app
from prepare_assignment.core.check import check_task, tasks_in_prepare, check, TaskStatus
from prepare_assignment.data.task_properties import TaskProperties

PYTHON_TASK = """id: {name}
name: {name}
description: d
runs:
  using: python
  main: main.py
"""

COMPOSITE_TASK = """id: {name}
name: {name}
description: d
runs:
  using: composite
  tasks:
    - name: a
      uses: {sub}
    - name: b
      run: echo hi
"""


def _supported_ref_formats() -> List[str]:
    version = tuple(int(part) for part in re.findall(r"\d+", Git().version())[:2])
    # --ref-format is supported since git 2.45
    return ["files", "reftable"] if version >= (2, 45) else ["default"]


@pytest.fixture(autouse=True)
def tasks_dir(tmp_path: Path, mocker: MockerFixture) -> Path:
    mocker.patch("prepare_assignment.data.task_properties.tasks_path", tmp_path / "tasks")
    mocker.patch("prepare_assignment.utils.tasks.get_tasks_path", return_value=tmp_path / "tasks")
    mocker.patch("prepare_assignment.core.versions.CONFIG.core.git_mode", "https")
    return tmp_path


@pytest.fixture(params=_supported_ref_formats())
def install(request: pytest.FixtureRequest) -> Callable[..., str]:
    ref_format = str(request.param)

    def _install(task: str, content: Optional[str] = None) -> str:
        """Create an 'installed' task (a git repository with one commit), returns the commit hash"""
        props = TaskProperties.of(task)
        props.repo_path.mkdir(parents=True)
        props.definition_path.write_text(content or PYTHON_TASK.format(name=props.name))
        git = Git(str(props.repo_path))
        if ref_format == "default":
            git.init()
        else:
            git.init(f"--ref-format={ref_format}")
        git.add("task.yml")
        git.execute(["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-m", "init"])
        return str(git.rev_parse("HEAD")).strip()

    return _install


def mock_remote(mocker: MockerFixture, tags: Dict[str, str], head: Optional[str] = None) -> None:
    mocker.patch("prepare_assignment.core.check.list_remote_tags", return_value=tags)
    mocker.patch("prepare_assignment.core.check.remote_ref", return_value=head)


OTHER = "f" * 40


def test_not_installed() -> None:
    status = check_task(TaskProperties.of("remove"))
    assert status.installed is None
    assert str(status) == "prepare-assignment/remove@latest: not installed " \
                          "(use 'prepare task add prepare-assignment/remove@latest')"


def test_latest_update_available(mocker: MockerFixture, install: Callable[..., str]) -> None:
    head = install("remove")
    mock_remote(mocker, {"v1.0.0": head, "v1.1.0": OTHER})
    status = check_task(TaskProperties.of("remove"))
    assert (status.installed, status.update, status.newest) == ("v1.0.0", "v1.1.0", None)
    assert str(status) == ("prepare-assignment/remove@latest: v1.0.0 → v1.1.0 "
                           "https://github.com/prepare-assignment/remove/releases/tag/v1.1.0")


def test_latest_up_to_date(mocker: MockerFixture, install: Callable[..., str]) -> None:
    head = install("remove")
    mock_remote(mocker, {"v1.0.0": OTHER, "v1.1.0": head})
    status = check_task(TaskProperties.of("remove"))
    assert str(status) == "prepare-assignment/remove@latest: v1.1.0, up to date"


def test_prefix_pin_with_newer_major(mocker: MockerFixture, install: Callable[..., str]) -> None:
    head = install("copy@v1")
    mock_remote(mocker, {"v1.0.2": head, "v1.1.0": OTHER, "v2.0.0": "e" * 40})
    status = check_task(TaskProperties.of("copy@v1"))
    assert str(status) == ("prepare-assignment/copy@v1: v1.0.2 → v1.1.0 (newest: v2.0.0) "
                           "https://github.com/prepare-assignment/copy/releases/tag/v1.1.0")


def test_exact_pin_up_to_date_with_newer_release(mocker: MockerFixture, install: Callable[..., str]) -> None:
    head = install("copy@v1.0.2")
    mock_remote(mocker, {"v1.0.2": head, "v2.0.0": OTHER})
    status = check_task(TaskProperties.of("copy@v1.0.2"))
    assert status.update is None
    assert str(status) == ("prepare-assignment/copy@v1.0.2: v1.0.2, up to date (newest: v2.0.0) "
                           "https://github.com/prepare-assignment/copy/releases/tag/v2.0.0")


def test_main_behind(mocker: MockerFixture, install: Callable[..., str]) -> None:
    head = install("copy@main")
    mock_remote(mocker, {}, head=OTHER)
    status = check_task(TaskProperties.of("copy@main"))
    assert status.installed == head[:7]
    assert status.update == OTHER[:7]
    assert status.url == f"https://github.com/prepare-assignment/copy/compare/{head}...{OTHER}"


def test_main_up_to_date(mocker: MockerFixture, install: Callable[..., str]) -> None:
    head = install("copy@main")
    mock_remote(mocker, {}, head=head)
    assert str(check_task(TaskProperties.of("copy@main"))) == f"prepare-assignment/copy@main: {head[:7]}, up to date"


def test_latest_without_tags_uses_default_branch(mocker: MockerFixture, install: Callable[..., str]) -> None:
    install("copy")
    mock_remote(mocker, {}, head=OTHER)
    ref = mocker.patch("prepare_assignment.core.check.remote_ref", return_value=OTHER)
    status = check_task(TaskProperties.of("copy"))
    assert status.update == OTHER[:7]
    ref.assert_called_once_with("https://github.com/prepare-assignment/copy.git", "HEAD")


def test_commit_pin_reports_newest_only(mocker: MockerFixture, install: Callable[..., str]) -> None:
    head = install("copy@" + "a" * 40)
    mock_remote(mocker, {"v1.0.0": head, "v2.0.0": OTHER})
    status = check_task(TaskProperties.of("copy@" + "a" * 40))
    assert (status.installed, status.update, status.newest) == ("v1.0.0", None, "v2.0.0")


def test_remote_error(mocker: MockerFixture, install: Callable[..., str]) -> None:
    install("copy")
    mocker.patch("prepare_assignment.core.check.list_remote_tags", side_effect=RuntimeError("no network\nmore"))
    status = check_task(TaskProperties.of("copy"))
    assert str(status) == "prepare-assignment/copy@latest: unable to check (no network)"


def test_tasks_in_prepare_includes_sub_tasks(install: Callable[..., str]) -> None:
    install("alda@v1", COMPOSITE_TASK.format(name="alda", sub="remove@v1"))
    install("remove@v1")
    yaml = {"name": "x", "jobs": {
        "prepare": [{"name": "a", "uses": "alda@v1"}, {"name": "b", "uses": "prepare-assignment/alda@v1"},
                    {"name": "c", "run": "echo hi"}, {"name": "d", "uses": "other/copy"}],
        "other": [{"name": "e", "uses": "remove@v1"}]}}
    tasks = [str(t) for t in tasks_in_prepare(yaml)]
    assert tasks == ["prepare-assignment/alda@v1", "prepare-assignment/remove@v1", "other/copy@latest"]


def test_tasks_in_prepare_composite_with_missing_sub_task(install: Callable[..., str]) -> None:
    install("alda", COMPOSITE_TASK.format(name="alda", sub="missing"))
    tasks = [str(t) for t in tasks_in_prepare({"jobs": {"p": [{"name": "a", "uses": "alda"}]}})]
    assert tasks == ["prepare-assignment/alda@latest", "prepare-assignment/missing@latest"]


def test_check_deduplicates(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.check.check_task", side_effect=lambda p: TaskStatus(p))
    result = check([TaskProperties.of("remove"), TaskProperties.of("prepare-assignment/remove@latest")])
    assert len(result) == 1


# ── cli ──────────────────────────────────────────────────────────────────────

def test_cli_check(tmp_path: Path, mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "prepare.yml").write_text("name: x\njobs:\n  prepare:\n    - name: a\n      uses: remove\n")
    monkeypatch.chdir(tmp_path)
    mocker.patch("prepare_assignment.core.check.check_task",
                 side_effect=lambda p: TaskStatus(p, installed="v1.0.0", update="v1.1.0"))
    result = CliRunner().invoke(app, ["check", "--git", "https"])
    assert result.exit_code == 0
    assert "prepare-assignment/remove@latest: v1.0.0 → v1.1.0" in result.output


def test_cli_check_all(mocker: MockerFixture, install: Callable[..., str]) -> None:
    install("remove")
    install("copy@v1")
    mocker.patch("prepare_assignment.core.check.check_task", side_effect=lambda p: TaskStatus(p, installed="x"))
    result = CliRunner().invoke(app, ["check", "--all"])
    assert result.exit_code == 0
    assert result.output.splitlines() == ["prepare-assignment/copy@v1: x, up to date",
                                          "prepare-assignment/remove@latest: x, up to date"]


def test_cli_check_without_prepare_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["check"])
    assert result.exit_code == 1
    assert "No prepare.yml file found" in result.output
