import logging
from typing import Dict


class ColourFormatter(logging.Formatter):
    """
    Custom logger that adds color based on level
    Taken from: https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
    """

    light_blue = "\x1b[1;34m"
    grey = "\u001b[38;5;250m"
    white = "\u001b[37m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    black = "\u001b[30m"
    reset = "\033[39m"

    def __init__(self, prefix: str = ""):
        super().__init__()
        self.prefix = prefix
        format_log_debug = f"{self.prefix}%(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
        format_log = f"{self.prefix}%(levelname)s - %(message)s"
        format_log_trace = f"{self.prefix}%(message)s"

        self.FORMATS: Dict[int, str] = {
            logging.DEBUG - 5: self.grey + format_log_trace + self.reset,
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
        new_lines: bool = True,
        prefix: str = ""
) -> None:
    handler = logging.StreamHandler()
    if not new_lines:
        handler.terminator = ""
    if add_colours:
        handler.setFormatter(ColourFormatter(prefix))
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
        logger.setLevel(logging.DEBUG - 5)
        handler.setLevel(logging.DEBUG - 5)
    logger.addHandler(handler)
    logger.propagate = False


# Adapted from: https://stackoverflow.com/a/35804945/1691778
def add_logging_level(level_name: str, level_value: int, function_name: str) -> None:
    if hasattr(logging, level_name):
        raise AttributeError(f"Logging level '{level_name}' is already defined on logging")
    if hasattr(logging, function_name):
        raise AttributeError(f"Function '{function_name}' is already defined on logging")
    if hasattr(logging.getLoggerClass(), function_name):
        raise AttributeError(f"Function '{function_name}' is already defined on logger class")

    def log_for_level(self, message, *args, **kwargs):
        if self.isEnabledFor(level_value):
            self._log(level_value, message, args, **kwargs)

    def log_to_root(message, *args, **kwargs):
        logging.log(level_value, message, args, kwargs)

    logging.addLevelName(level_value, level_name)
    setattr(logging, level_name, level_value)
    setattr(logging.getLoggerClass(), function_name, log_for_level)
    setattr(logging, function_name, log_to_root)
