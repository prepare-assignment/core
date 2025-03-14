import os
import sys

from pathlib import Path
from typing import Final, Optional

TASKS_PATH: Final[str] = "tasks"

__cache_path = None
__tasks_path = None
__config_path: Optional[Path] = None


def get_config_path() -> Path:
    """
    Get the path to the default config location for applications
    :return: Path to the OS specific application config location
    :raises: AssertionError: if OS is not one of Linux, macOS or Windows
    """
    global __config_path
    if __config_path:
        return __config_path
    if sys.platform == "linux":
        config = os.environ.get("XDG_CONFIG_HOME")
        if config is None:
            config = "~/.config"
        __config_path = Path(os.path.join(config, "prepare")).expanduser()
    elif sys.platform == "darwin":
        __config_path = Path("~/Library/Application Support/prepare").expanduser()
    elif sys.platform == "win32":
        ad = f"{os.environ.get('APPDATA')}"
        __config_path = Path(os.path.join(ad, "prepare")).expanduser()
    else:
        raise AssertionError("Unsupported OS")
    return __config_path


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
