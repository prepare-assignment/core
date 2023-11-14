import os
import sys

from pathlib import Path
from typing import Final

TASKS_PATH: Final[str] = "tasks"

__cache_path = None
__tasks_path = None


def get_cache_path() -> Path:
    """
    Get the path to the default cache location for applications
    :return: Path to the OS specific application cache
    :raises: AssertionError: if OS is not one of Linux, macOS or Windows
    """
    global __cache_path
    if __cache_path:
        return __cache_path
    if sys.platform == "linux":
        cache = os.environ.get("XDG_CACHE_HOME")
        if cache is None:
            cache = "~/.cache"
        __cache_path = Path(f"{cache}/prepare").expanduser()
    elif sys.platform == "darwin":
        __cache_path = Path("~/Library/Caches/prepare").expanduser()
    elif sys.platform == "win32":
        lad = f"{os.environ.get('LOCALAPPDATA')}"
        __cache_path = Path(os.path.join(lad, "prepare", "cache"))
    else:
        raise AssertionError("Unsupported OS")
    return __cache_path


def get_tasks_path() -> Path:
    global __tasks_path
    if __tasks_path:
        return __tasks_path
    cache_path = get_cache_path()
    __tasks_path = Path(os.path.join(cache_path, TASKS_PATH))
    return __tasks_path
