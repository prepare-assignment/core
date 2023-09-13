import os
import sys

from pathlib import Path


def get_cache_path() -> Path:
    """
    Get the path to the default cache location for applications
    :return: Path to the OS specific application cache
    :raises: AssertionError: if OS is not one of Linux, macOS or Windows
    """
    if sys.platform == "linux":
        cache = os.environ.get("XDG_CACHE_HOME")
        if cache is None:
            cache = "~/.cache"
        return Path(f"{cache}/prepare").expanduser()
    elif sys.platform == "darwin":
        return Path("~/Library/Caches/prepare").expanduser()
    elif sys.platform == "win32":
        lad = f"{os.environ.get('LOCALAPPDATA')}"
        return Path(os.path.join(lad, "prepare", "cache"))
    raise AssertionError("Unsupported OS")