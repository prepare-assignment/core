import logging
from typing import Iterator

import pytest

# Loggers that prepare() configures (level, handlers), see prepare_assignment/core/main.py
_LOGGERS = ("prepare_assignment", "tasks")


@pytest.fixture(autouse=True)
def reset_loggers() -> Iterator[None]:
    """
    Restore the prepare loggers after every test. prepare() sets their level (e.g. ERROR for verbosity 0), which made
    tests that check log output with caplog fail when they ran after a test that calls prepare().
    """
    saved = {}
    for name in _LOGGERS:
        logger = logging.getLogger(name)
        saved[name] = (logger.level, list(logger.handlers), logger.propagate)
    yield
    for name, (level, handlers, propagate) in saved.items():
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers[:] = handlers
        logger.propagate = propagate
