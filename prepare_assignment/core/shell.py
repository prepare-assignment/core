import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from typing import Dict, Final, Iterator, List, Optional, Tuple, Union

from prepare_assignment.data.errors import TaskExecutionError

# Make sure python can always print (non-ascii) output, regardless of the platform encoding (e.g. cp1252 on Windows)
PYTHON_UTF8_ENVIRONMENT: Final[Dict[str, str]] = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}

SHELLS: Final[Tuple[str, ...]] = ("bash", "sh", "pwsh", "powershell", "cmd", "python")
DEFAULT_SHELL: Final[str] = "bash"


def _find_bash() -> Optional[str]:
    """
    Try to retrieve the path to a bash executable

    :returns: the path to a bash executable or None if it cannot be found
    """
    if sys.platform != "win32":
        return shutil.which("bash")
    # See if bash is available
    path = shutil.which("bash.exe")
    # Check if it is not the placeholder (WSL) bash.exe
    if path is not None and path.lower() != "c:\\windows\\system32\\bash.exe":
        return path
    # If it is the placeholder, use the bash that comes with the git install
    git = shutil.which("git.exe")
    if git is None:
        return None
    git_path = os.path.dirname(git)
    # The default git install has bash.exe in both bin and cmd, but the cmd one doesn't work
    if git_path.lower().endswith("cmd"):
        git_path = git_path[:-3] + "bin"
    candidate = os.path.join(git_path, "bash.exe")
    return candidate if os.path.isfile(candidate) else None


def find_executable(shell: str) -> Optional[str]:
    """
    Find the executable for a shell

    :param shell: one of SHELLS
    :returns: path to the executable, or None if it isn't available on this system
    """
    if shell == "bash":
        return _find_bash()
    if shell == "python":
        return sys.executable
    if shell == "cmd":
        return shutil.which("cmd") or os.environ.get("COMSPEC")
    return shutil.which(shell)


def _missing_shell_message(shell: str) -> str:
    alternatives = ", ".join(s for s in SHELLS if s != shell)
    return f"{shell} not found; install it or set 'shell' to one of: {alternatives}"


# Same as the GitHub Actions runner: stop on the first error and exit with the exit code of the last
# native command (PowerShell doesn't fail on a failing native command by itself)
_POWERSHELL_PREFIX: Final[str] = "$ErrorActionPreference = 'stop'"
_POWERSHELL_SUFFIX: Final[str] = "if ((Test-Path -LiteralPath variable:\\LASTEXITCODE)) { exit $LASTEXITCODE }"

Command = Union[str, List[str]]


def _script(command: str, shell: str) -> Tuple[str, str, str, str]:
    """
    :returns: the script contents, file suffix, encoding and line ending for the shell
    """
    if shell in ("pwsh", "powershell"):
        # Windows PowerShell 5.1 only reads a UTF-8 script correctly if it has a BOM
        return f"{_POWERSHELL_PREFIX}\n{command}\n{_POWERSHELL_SUFFIX}\n", ".ps1", "utf-8-sig", "\n"
    if shell == "cmd":
        # cmd doesn't handle scripts with only LF line endings correctly
        return command, ".cmd", "utf-8", "\r\n"
    if shell == "python":
        return command, ".py", "utf-8", "\n"
    return command, ".sh", "utf-8", "\n"


def _arguments(shell: str, executable: str, path: str) -> Command:
    if shell == "bash":
        return [executable, "--noprofile", "--norc", "-eo", "pipefail", path]
    if shell == "sh":
        return [executable, "-e", path]
    if shell in ("pwsh", "powershell"):
        escaped = path.replace("'", "''")
        return [executable, "-NoProfile", "-NonInteractive", "-Command", f". '{escaped}'"]
    if shell == "cmd":
        # Passed as a string: the quoting of a list (subprocess.list2cmdline) breaks the nested quotes
        return f'"{executable}" /D /E:ON /V:OFF /S /C "CALL "{path}""'
    return [executable, path]


@contextmanager
def shell_command(shell: str, command: str) -> Iterator[Command]:
    """
    Build the command line to execute a script with the given shell.

    Like the GitHub Actions runner, the script is written to a temporary file which is executed by the shell,
    bash and sh stop on the first failing command (bash also if a command in a pipe fails).

    :param shell: one of SHELLS
    :param command: the command (script) to execute
    :returns: the arguments for subprocess (a string for cmd)
    :raises TaskExecutionError: if the shell is unknown or not available on this system
    """
    if shell not in SHELLS:
        raise TaskExecutionError(f"Unknown shell '{shell}', supported shells are: {', '.join(SHELLS)}")
    executable = find_executable(shell)
    if executable is None:
        raise TaskExecutionError(_missing_shell_message(shell))

    script, suffix, encoding, newline = _script(command, shell)
    handle, path = tempfile.mkstemp(suffix=suffix, prefix="prepare-")
    try:
        with os.fdopen(handle, "w", encoding=encoding, newline=newline) as file:
            file.write(script)
        yield _arguments(shell, executable, path)
    finally:
        os.remove(path)
