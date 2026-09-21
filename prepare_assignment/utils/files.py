import os
import shutil
import stat
import sys
from pathlib import Path
from typing import Any, Callable, Union


def _make_writable_and_retry(func: Callable[[str], Any], path: str, _: Any) -> None:
    """
    Git makes (object) files read-only, which cannot be removed on Windows. On other platforms a file cannot be
    removed if its directory is read-only. Make both writable and retry.
    """
    for target in (os.path.dirname(path), path):
        try:
            mode = os.stat(target).st_mode
            os.chmod(target, mode | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
        except OSError:
            pass
    func(path)


def remove_tree(path: Union[str, os.PathLike], ignore_errors: bool = False) -> None:
    """
    Remove a directory tree, also if it contains read-only files (e.g. a git repository on Windows)

    :param path: the directory to remove, nothing happens if it doesn't exist
    :param ignore_errors: if True, errors are ignored (best effort)
    :raises OSError: if the directory cannot be removed and ignore_errors is False
    """
    if not os.path.lexists(path):
        return
    try:
        if sys.version_info >= (3, 12):
            shutil.rmtree(Path(path), onexc=_make_writable_and_retry)
        else:
            shutil.rmtree(Path(path), onerror=_make_writable_and_retry)
    except OSError:
        if not ignore_errors:
            raise
