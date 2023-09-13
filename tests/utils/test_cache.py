import os
import sys
from pathlib import Path

import pytest

from prepare_assignment.utils import get_cache_path


def test_cache_xdg_home() -> None:
    old_cache_home = os.environ.get("XDG_CACHE_HOME", None)
    expected = Path("test/prepare_assignment")
    os.environ["XDG_CACHE_HOME"] = "test"
    cache_path = get_cache_path()
    if old_cache_home is not None:
        os.environ["XDG_CACHE_HOME"] = old_cache_home
    if sys.platform == "linux":
        same = cache_path == expected
    else:
        same = True
    assert same
