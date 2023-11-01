import os
import shutil
import sys


def get_bash_path() -> str:
    """
    Try to retrieve the path to a bash executable

    :returns str: the path to a bash executable as string
    """
    if sys.platform == "win32":
        # See if bash is available
        path = shutil.which("bash.exe")
        # Check if it is not the placeholder bash.exe
        if path is None or path.lower() == "c:\\windows\\system32\\bash.exe":
            # If it is the placeholder, use the bash that comes with the git install
            git_path: str = os.path.dirname(shutil.which("git.exe"))
            # The default git install has bash.exe in both bin and cmd, but the cmd one doesn't work
            if git_path.endswith("cmd"):
                git_path = git_path[:-3] + "bin"
            return git_path + "\\bash.exe"
        return path
    return shutil.which("bash")  # type: ignore
