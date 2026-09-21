import os
import sys
from typing import List, Union

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core import shell
from prepare_assignment.core.shell import shell_command, find_executable, SHELLS
from prepare_assignment.data.errors import TaskExecutionError


@pytest.mark.parametrize("name, expected", [
    ("bash", ["/bin/x", "--noprofile", "--norc", "-eo", "pipefail", "{path}"]),
    ("sh", ["/bin/x", "-e", "{path}"]),
    ("pwsh", ["/bin/x", "-NoProfile", "-NonInteractive", "-Command", ". '{path}'"]),
    ("powershell", ["/bin/x", "-NoProfile", "-NonInteractive", "-Command", ". '{path}'"]),
    ("python", ["/bin/x", "{path}"]),
])
def test_shell_arguments(name: str, expected: List[str], mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.shell.find_executable", return_value="/bin/x")
    with shell_command(name, "echo hi") as args:
        path = _script_path(args)
        assert args == [arg.replace("{path}", path) for arg in expected]
        assert os.path.isfile(path)
    assert not os.path.exists(path)


def _script_path(args: Union[str, List[str]]) -> str:
    if isinstance(args, str):
        return args.split('"CALL "')[1][:-2]
    last = args[-1]
    return last[3:-1] if last.startswith(". '") else last


def test_cmd_arguments_are_a_string(mocker: MockerFixture) -> None:
    """A list would be quoted by subprocess.list2cmdline, which breaks the nested quotes"""
    mocker.patch("prepare_assignment.core.shell.find_executable", return_value="C:\\cmd.exe")
    with shell_command("cmd", "echo hi") as args:
        assert isinstance(args, str)
        path = _script_path(args)
        assert args == f'"C:\\cmd.exe" /D /E:ON /V:OFF /S /C "CALL "{path}""'
        assert path.endswith(".cmd")


@pytest.mark.parametrize("name, suffix, content", [
    ("bash", ".sh", b"a\nb\n"),
    ("sh", ".sh", b"a\nb\n"),
    ("python", ".py", b"a\nb\n"),
    ("cmd", ".cmd", b"a\r\nb\r\n"),
    ("pwsh", ".ps1", b"\xef\xbb\xbf$ErrorActionPreference = 'stop'\na\nb\n\n"
                     b"if ((Test-Path -LiteralPath variable:\\LASTEXITCODE)) { exit $LASTEXITCODE }\n"),
])
def test_script_file(name: str, suffix: str, content: bytes, mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.shell.find_executable", return_value="/bin/x")
    with shell_command(name, "a\nb\n") as args:
        path = _script_path(args)
        assert path.endswith(suffix)
        with open(path, "rb") as handle:
            assert handle.read() == content


def test_script_file_removed_on_error(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.shell.find_executable", return_value="/bin/x")
    with pytest.raises(RuntimeError):
        with shell_command("bash", "echo hi") as args:
            path = _script_path(args)
            raise RuntimeError("process failed")
    assert not os.path.exists(path)


def test_powershell_path_with_quote_is_escaped(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.shell.find_executable", return_value="/bin/x")
    mocker.patch("prepare_assignment.core.shell.tempfile.mkstemp",
                 side_effect=lambda **kwargs: (os.open(os.devnull, os.O_WRONLY), "/tmp/it's.ps1"))
    mocker.patch("prepare_assignment.core.shell.os.remove")
    with shell_command("pwsh", "echo hi") as args:
        assert args[-1] == ". '/tmp/it''s.ps1'"


def test_unknown_shell() -> None:
    with pytest.raises(TaskExecutionError) as exc:
        with shell_command("fish", "echo hi"):
            pass
    assert "Unknown shell 'fish'" in exc.value.message


def test_missing_shell(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.shell.find_executable", return_value=None)
    with pytest.raises(TaskExecutionError) as exc:
        with shell_command("bash", "echo hi"):
            pass
    assert exc.value.message.startswith("bash not found; install it or set 'shell' to one of:")
    assert "python" in exc.value.message


def test_find_python_is_current_interpreter() -> None:
    assert find_executable("python") == sys.executable


def test_find_cmd_falls_back_to_comspec(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    mocker.patch("prepare_assignment.core.shell.shutil.which", return_value=None)
    monkeypatch.setenv("COMSPEC", "C:\\Windows\\system32\\cmd.exe")
    assert find_executable("cmd") == "C:\\Windows\\system32\\cmd.exe"


def test_find_bash_posix(mocker: MockerFixture) -> None:
    mocker.patch.object(shell.sys, "platform", "linux")
    mocker.patch("prepare_assignment.core.shell.shutil.which", return_value="/usr/bin/bash")
    assert find_executable("bash") == "/usr/bin/bash"


def test_find_bash_windows_on_path(mocker: MockerFixture) -> None:
    mocker.patch.object(shell.sys, "platform", "win32")
    mocker.patch("prepare_assignment.core.shell.shutil.which", return_value="C:\\msys\\bash.exe")
    assert find_executable("bash") == "C:\\msys\\bash.exe"


def test_find_bash_windows_git_bash(mocker: MockerFixture) -> None:
    mocker.patch.object(shell.sys, "platform", "win32")
    git_cmd = os.path.join("C:", "Git", "cmd")

    def which(name: str) -> str:
        return "c:\\windows\\system32\\bash.exe" if name == "bash.exe" else os.path.join(git_cmd, "git.exe")

    mocker.patch("prepare_assignment.core.shell.shutil.which", side_effect=which)
    mocker.patch("prepare_assignment.core.shell.os.path.isfile", return_value=True)
    assert find_executable("bash") == os.path.join(os.path.join("C:", "Git", "bin"), "bash.exe")


def test_find_bash_windows_without_git(mocker: MockerFixture) -> None:
    """Used to crash with TypeError (os.path.dirname(None))."""
    mocker.patch.object(shell.sys, "platform", "win32")
    mocker.patch("prepare_assignment.core.shell.shutil.which", return_value=None)
    assert find_executable("bash") is None


def test_all_shells_supported_in_schemas() -> None:
    from prepare_assignment.utils.resources import load_schema
    prepare = load_schema("prepare.schema.json")
    items = prepare["properties"]["jobs"]["patternProperties"]["^[_a-zA-Z][a-zA-Z0-9_-]*$"]["items"]
    run_step = next(option for option in items["anyOf"] if "run" in option["properties"])
    assert tuple(run_step["properties"]["shell"]["enum"]) == SHELLS
    config = load_schema("config.schema.json")
    assert tuple(config["properties"]["core"]["properties"]["shell"]["enum"]) == SHELLS
