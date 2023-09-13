import os
from pathlib import Path

import pytest

from prepare.utils import get_cache_path


def test_cache() -> None:
    old_cache_home = os.environ.get("XDG_CACHE_HOME", None)
    expected = Path("test/prepare")
    os.environ["XDG_CACHE_HOME"] = "test"
    cache_path = get_cache_path()
    if old_cache_home is not None:
        os.environ["XDG_CACHE_HOME"] = old_cache_home
    assert cache_path == expected
