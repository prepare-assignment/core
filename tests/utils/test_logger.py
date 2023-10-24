import logging

import pytest
from pytest_mock import MockerFixture

from prepare_assignment.data.constants import LOG_LEVEL_TRACE
from prepare_assignment.utils import set_logger_level
from prepare_assignment.utils.logger import ColourFormatter, add_logging_level


def test_set_colour(mocker: MockerFixture) -> None:
    logger = logging.getLogger("test_set_colour")
    set_logger_level(logger, verbosity=0, add_colours=True, prefix="TEST", debug_linenumbers=True)
    assert logger.hasHandlers()
    handler = logger.handlers[-1]
    formatter = handler.formatter
    assert isinstance(formatter, ColourFormatter)


def test_no_colour(mocker: MockerFixture) -> None:
    logger = logging.getLogger("test_set_colour")
    set_logger_level(logger, verbosity=0, add_colours=False, prefix="TEST", debug_linenumbers=True)
    assert logger.hasHandlers()
    handler = logger.handlers[-1]
    formatter = handler.formatter
    assert not isinstance(formatter, ColourFormatter)


@pytest.mark.parametrize(
    "verbosity, level",
    [
        (0, logging.ERROR),
        (1, logging.WARNING),
        (2, logging.INFO),
        (3, logging.DEBUG),
        (4, LOG_LEVEL_TRACE),
        (10, LOG_LEVEL_TRACE),
        (-1, LOG_LEVEL_TRACE),
    ]
)
def test_levels(verbosity: int, level: int) -> None:
    logger = logging.getLogger("test_levels")
    set_logger_level(logger, verbosity=verbosity)
    assert logger.hasHandlers()
    handler = logger.handlers[-1]
    assert handler.level == level
    assert logger.level == level


def test_add_logging_level(caplog: pytest.LogCaptureFixture) -> None:
    add_logging_level("test", 1, "test_fun")
    assert logging.getLevelName("test") == 1
    assert logging.getLevelName(1) == "test"

    with pytest.raises(AttributeError) as pytest_wrapped_e:
        add_logging_level("test", 2, "other_fun")

    with pytest.raises(AttributeError) as pytest_wrapped_e:
        add_logging_level("asd", 2, "test_fun")

    logger = logging.getLogger("test_add_logging_level")
    with caplog.at_level(logging.DEBUG):
        logger.error("test error")

    assert "test error" in caplog.text


@pytest.mark.parametrize(
    "level, name, control", [
        (0, "", False),
        (10, "DEBUG", True),
        (20, "INFO", True),
        (30, "WARNING", True),
        (40, "ERROR", True),
        (50, "CRITICAL", True)
    ]
)
def test_colour_formatter(level: int, name: str, control: bool):
    formatter = ColourFormatter()
    record = logging.LogRecord(
        name="test",
        level=level,
        pathname="testpath",
        lineno=0,
        msg="Test message",
        args=None,
        exc_info=None)
    formatted = formatter.format(record)
    contains_name = name in formatted
    contains_control = '\x1b[' in formatted
    control_correct = contains_control if control else not contains_control
    assert (contains_name and control_correct), "Colour formatter should format correctly"
