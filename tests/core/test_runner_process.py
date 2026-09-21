"""
Runner tests that execute real processes (using the python shell, so they work on every platform)
"""
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.core.runner import run
from prepare_assignment.data.errors import TaskExecutionError
from prepare_assignment.data.prepare import Prepare
from prepare_assignment.data.task_definition import CompositeTaskDefinition, TaskOutputDefinition
from prepare_assignment.utils.logger import add_logging_level
from prepare_assignment.data.constants import LOG_LEVEL_TRACE


@pytest.fixture(autouse=True)
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    add_logging_level("TRACE", LOG_LEVEL_TRACE, "trace")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def py(name: str, script: str, **kwargs: Any) -> Dict[str, Any]:
    return {"name": name, "shell": "python", "run": script, **kwargs}


def prepare(*steps: Dict[str, Any]) -> Prepare:
    return Prepare.of({"name": "test", "jobs": {"prepare": list(steps)}})


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── shells ───────────────────────────────────────────────────────────────────

def test_python_shell_multiline(project: Path) -> None:
    run(prepare(py("write", "lines = ['a', 'b']\nopen('out.txt', 'w').write(','.join(lines))\n")), {})
    assert read(project / "out.txt") == "a,b"


def test_default_shell_from_config(project: Path, mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.runner.CONFIG.core.shell", "python")
    run(prepare({"name": "write", "run": "open('out.txt', 'w').write('config')"}), {})
    assert read(project / "out.txt") == "config"


def test_missing_shell_fails_step(mocker: MockerFixture) -> None:
    mocker.patch("prepare_assignment.core.shell.find_executable", return_value=None)
    with pytest.raises(TaskExecutionError):
        run(prepare({"name": "x", "shell": "pwsh", "run": "echo hi"}), {})


# ── stdout / stderr ──────────────────────────────────────────────────────────

def test_stderr_is_not_parsed_as_command(project: Path) -> None:
    script = ("import sys\n"
              "sys.stderr.write(':PA:set-env:PA:FROM_STDERR:PA:\"1\"\\n')\n"
              "print(':PA:set-env:PA:FROM_STDOUT:PA:\"1\"')\n")
    check = "import os\nopen('out.txt', 'w').write(str(sorted(k for k in os.environ if k.startswith('FROM_'))))"
    run(prepare(py("emit", script), py("check", check)), {})
    assert read(project / "out.txt") == "['FROM_STDOUT']"


def test_stderr_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    logging.getLogger("tasks").setLevel(LOG_LEVEL_TRACE)
    with caplog.at_level(LOG_LEVEL_TRACE, logger="tasks"):
        run(prepare(py("emit", "import sys\nsys.stderr.write('warning from task\\n')")), {})
    assert "[stderr] warning from task" in caplog.text


def test_stderr_tail_in_error_message(caplog: pytest.LogCaptureFixture) -> None:
    script = "import sys\nfor i in range(30):\n    sys.stderr.write(f'line {i}\\n')\nsys.exit(3)\n"
    with caplog.at_level(logging.ERROR, logger="prepare_assignment"):
        with pytest.raises(TaskExecutionError):
            run(prepare(py("fail", script)), {})
    assert "exited with code 3" in caplog.text
    assert "line 29" in caplog.text
    assert "line 10" in caplog.text
    # Only the last 20 lines are included
    assert "line 9\n" not in caplog.text


def test_unicode_output() -> None:
    run(prepare(py("unicode", "print('✓ ünïcödé ✗')\nimport sys\nsys.stderr.write('→ ✓\\n')")), {})


# ── working-directory ────────────────────────────────────────────────────────

def test_working_directory(project: Path) -> None:
    (project / "sub").mkdir()
    run(prepare(py("write", "open('out.txt', 'w').write('x')", **{"working-directory": "sub"})), {})
    assert (project / "sub" / "out.txt").is_file()
    assert not (project / "out.txt").exists()


def test_working_directory_substitution(project: Path) -> None:
    (project / "dir-a").mkdir()
    run(prepare(py("write", "open('out.txt', 'w').write('x')",
                   **{"working-directory": "${{ env.TARGET }}"})), {}, env_vars={"TARGET": "dir-a"})
    assert (project / "dir-a" / "out.txt").is_file()


def test_working_directory_missing_fails(project: Path) -> None:
    with pytest.raises(TaskExecutionError):
        run(prepare(py("write", "open('out.txt', 'w').write('x')", **{"working-directory": "missing"})), {})
    assert not (project / "out.txt").exists()


def test_working_directory_does_not_leak(project: Path) -> None:
    (project / "sub").mkdir()
    run(prepare(py("a", "pass", **{"working-directory": "sub"}),
                py("b", "open('out.txt', 'w').write('x')")), {})
    assert (project / "out.txt").is_file()


# ── env ──────────────────────────────────────────────────────────────────────

def test_step_env(project: Path) -> None:
    script = "import os\nopen('out.txt', 'w').write(os.environ['GREETING'] + ' ' + os.environ.get('LEAK', '-'))"
    run(prepare(py("write", script, env={"GREETING": "hello ${{ env.NAME }}"})), {}, env_vars={"NAME": "world"})
    assert read(project / "out.txt") == "hello world -"


def test_step_env_available_in_expressions(project: Path) -> None:
    run(prepare(py("write", "open('out.txt', 'w').write('${{ env.GREETING }}')", env={"GREETING": "hi"})), {})
    assert read(project / "out.txt") == "hi"


def test_step_env_does_not_leak(project: Path) -> None:
    check = "import os\nopen('out.txt', 'w').write(os.environ.get('ONLY_A', '-'))"
    run(prepare(py("a", "pass", env={"ONLY_A": "a"}), py("b", check)), {})
    assert read(project / "out.txt") == "-"


def test_step_env_overrides_job_env(project: Path) -> None:
    check = "import os\nopen('out.txt', 'w').write(os.environ['VALUE'])"
    run(prepare(py("a", check, env={"VALUE": "step"})), {}, env_vars={"VALUE": "job"})
    assert read(project / "out.txt") == "step"


# ── continue-on-error ────────────────────────────────────────────────────────

def test_continue_on_error(project: Path) -> None:
    run(prepare(py("fail", "raise SystemExit(1)", **{"continue-on-error": True}),
                py("next", "open('out.txt', 'w').write('ran')")), {})
    assert read(project / "out.txt") == "ran"


def test_continue_on_error_false_fails_job(project: Path) -> None:
    with pytest.raises(TaskExecutionError):
        run(prepare(py("fail", "raise SystemExit(1)"),
                    py("next", "open('out.txt', 'w').write('ran')")), {})
    assert not (project / "out.txt").exists()


def test_continue_on_error_invalid_if(project: Path) -> None:
    run(prepare(py("bad-if", "pass", **{"if": "inputs.typo", "continue-on-error": True}),
                py("next", "open('out.txt', 'w').write('ran')")), {})
    assert read(project / "out.txt") == "ran"


# ── composite ────────────────────────────────────────────────────────────────

def _composite(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {"prepare-assignment/composite@latest": CompositeTaskDefinition(
        id="composite", name="c", description="c", inputs=[], path=Path(""),
        outputs={"value": TaskOutputDefinition(description="d", type="string", items=None,
                                               value="${{ env.SET_BY_SUB }}")},
        tasks=tasks)}


def test_composite_inherits_working_directory_and_env(project: Path) -> None:
    (project / "sub" / "inner").mkdir(parents=True)
    mapping = _composite([
        py("write", "import os\nopen('out.txt', 'w').write(os.environ['FROM_PARENT'])",
           **{"working-directory": "inner"}),
    ])
    step = {"name": "c", "uses": "composite", "with": {}, "working-directory": "sub", "env": {"FROM_PARENT": "p"}}
    run(prepare(step), mapping)
    assert read(project / "sub" / "inner" / "out.txt") == "p"


def test_composite_continue_on_error_in_sub_task(project: Path) -> None:
    mapping = _composite([
        py("fail", "raise SystemExit(1)", **{"continue-on-error": True}),
        py("set", "print(':PA:set-env:PA:SET_BY_SUB:PA:\"ok\"')"),
    ])
    run(prepare({"name": "c", "id": "c", "uses": "composite", "with": {}},
                py("check", "open('out.txt', 'w').write('${{ tasks.c.outputs.value }}')")), mapping)
    assert read(project / "out.txt") == "ok"


# ── shells (real execution, skipped if the shell is not available) ───────────

def _requires(shell_name: str) -> Any:
    from prepare_assignment.core.shell import find_executable
    available = find_executable(shell_name) is not None and (shell_name != "cmd" or sys.platform == "win32")
    return pytest.mark.skipif(not available, reason=f"{shell_name} is not available")


def sh(name: str, shell_name: str, script: str, **kwargs: Any) -> Dict[str, Any]:
    return {"name": name, "shell": shell_name, "run": script, **kwargs}


@_requires("bash")
def test_bash_stops_on_first_error(project: Path) -> None:
    with pytest.raises(TaskExecutionError):
        run(prepare(sh("fail", "bash", "false\necho ran > out.txt\n")), {})
    assert not (project / "out.txt").exists()


@_requires("bash")
def test_bash_pipefail(project: Path) -> None:
    with pytest.raises(TaskExecutionError):
        run(prepare(sh("fail", "bash", "false | cat\necho ran > out.txt\n")), {})
    assert not (project / "out.txt").exists()


@_requires("bash")
def test_bash_multiline_with_quotes(project: Path) -> None:
    run(prepare(sh("write", "bash", "A='it'\"'\"'s'\necho \"$A \\\"quoted\\\"\" > out.txt\n")), {})
    assert read(project / "out.txt").strip() == "it's \"quoted\""


@_requires("sh")
def test_sh_stops_on_first_error(project: Path) -> None:
    with pytest.raises(TaskExecutionError):
        run(prepare(sh("fail", "sh", "false\necho ran > out.txt\n")), {})
    assert not (project / "out.txt").exists()


@_requires("sh")
def test_sh_success(project: Path) -> None:
    run(prepare(sh("write", "sh", "echo one > out.txt\necho two >> out.txt\n")), {})
    assert read(project / "out.txt").split() == ["one", "two"]


@_requires("pwsh")
def test_pwsh_multiline_with_quotes(project: Path) -> None:
    script = "$a = \"it's\"\nSet-Content -Path out.txt -Value \"$a `\"quoted`\"\" -NoNewline\n"
    run(prepare(sh("write", "pwsh", script)), {})
    assert read(project / "out.txt") == "it's \"quoted\""


@_requires("pwsh")
def test_pwsh_failing_native_command_fails_step(project: Path) -> None:
    """Without the LASTEXITCODE suffix, a failing native command that isn't the last line is ignored"""
    script = f"& '{sys.executable}' -c 'import sys; sys.exit(3)'\nSet-Content -Path out.txt -Value ran\n"
    with pytest.raises(TaskExecutionError):
        run(prepare(sh("fail", "pwsh", script)), {})


@_requires("pwsh")
def test_pwsh_error_stops_script(project: Path) -> None:
    script = "Get-Item does-not-exist\nSet-Content -Path out.txt -Value ran\n"
    with pytest.raises(TaskExecutionError):
        run(prepare(sh("fail", "pwsh", script)), {})
    assert not (project / "out.txt").exists()


@_requires("powershell")
def test_windows_powershell_unicode(project: Path) -> None:
    """Windows PowerShell 5.1 needs a BOM to read the UTF-8 script correctly"""
    run(prepare(sh("write", "powershell", "Set-Content -Path out.txt -Value 'ünï' -Encoding UTF8\n")), {})
    assert read(project / "out.txt").lstrip("﻿").strip() == "ünï"


@_requires("cmd")
def test_cmd_multiline_with_quotes(project: Path) -> None:
    run(prepare(sh("write", "cmd", "set A=it's\necho %A% \"quoted\"> out.txt\n")), {})
    assert read(project / "out.txt").strip() == "it's \"quoted\""


@_requires("cmd")
def test_cmd_exit_code(project: Path) -> None:
    with pytest.raises(TaskExecutionError):
        run(prepare(sh("fail", "cmd", "echo before\nexit /b 3\n")), {})
