import logging
from typing import Dict

from prepare_assignment.data.constants import LOG_LEVEL_TRACE


class ColourFormatter(logging.Formatter):
    """
    Extend the default formatter to use colours.

    Adapted from: https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
    """

    light_blue = "\x1b[1;34m"
    grey = "\u001b[38;5;250m"
    white = "\u001b[37m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    black = "\u001b[30m"
    reset = "\033[39m"

    def __init__(self, prefix: str = "", debug_linenumbers: bool = True):
        """
        Create a new ColourLogger
        :param prefix: optional prefix for log message
        :param debug_linenumbers: show file + line numbers on debug message
        """
        super().__init__()
        self.prefix = prefix
        format_log_debug = f"{self.prefix}%(levelname)s - %(message)s"
        if debug_linenumbers:
            format_log_debug += " (%(filename)s:%(lineno)d)"
        format_log = f"{self.prefix}%(levelname)s - %(message)s"
        format_log_trace = f"{self.prefix}%(message)s"

        self.FORMATS: Dict[int, str] = {
            LOG_LEVEL_TRACE: self.grey + format_log_trace + self.reset,
            logging.DEBUG: self.white + format_log_debug + self.reset,
            logging.INFO: self.light_blue + format_log + self.reset,
            logging.WARNING: self.yellow + format_log + self.reset,
            logging.ERROR: self.red + format_log + self.reset,
            logging.CRITICAL: self.bold_red + format_log + self.reset
        }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def set_logger_level(
        logger: logging.Logger,
        verbosity: int = 0,
        add_colours: bool = True,
        debug_linenumbers: bool = True,
        prefix: str = ""
) -> None:
    """
    Set the properties of the logger.

    :param logger: the logger to use
    :param verbosity: set the output level
    :param add_colours: add colours to the logging
    :param debug_linenumbers: for debug level show file + line numbers (only works when colour formatting is used)
    :param prefix: set prefix for logger message
    :return: None
    """
    handler = logging.StreamHandler()
    if add_colours:
        handler.setFormatter(ColourFormatter(prefix, debug_linenumbers))
    if verbosity == 0:
        logger.setLevel(logging.ERROR)
        handler.setLevel(logging.ERROR)
    elif verbosity == 1:
        logger.setLevel(logging.WARNING)
        handler.setLevel(logging.WARNING)
    elif verbosity == 2:
        logger.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
    elif verbosity == 3:
        logger.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
    else:
        logger.setLevel(LOG_LEVEL_TRACE)
        handler.setLevel(LOG_LEVEL_TRACE)
    logger.addHandler(handler)
    logger.propagate = True


def add_logging_level(level_name: str, level_value: int, function_name: str) -> None:
    """
    Add an extra log level to the logging library.
    Adapted from: https://stackoverflow.com/a/35804945/1691778

    :param level_name: the name of the new logging level
    :param level_value: the value of the new logging level
    :param function_name: the name of the logging function
    :return: None
    """
    if hasattr(logging, level_name):
        raise AttributeError(f"Logging level '{level_name}' is already defined on logging")
    if hasattr(logging, function_name):
        raise AttributeError(f"Function '{function_name}' is already defined on logging")
    if hasattr(logging.getLoggerClass(), function_name):
        raise AttributeError(f"Function '{function_name}' is already defined on logger class")

    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_value):
            self._log(level_value, message.rstrip(), args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_value, message.rstrip(), args, kwargs)

    logging.addLevelName(level_value, level_name)
    setattr(logging, level_name, level_value)
    setattr(logging.getLoggerClass(), function_name, log_for_level)
    setattr(logging, function_name, log_to_root)
