import logging
from typing import Dict


class ColourFormatter(logging.Formatter):
    """
    Custom logger that adds color based on level
    Taken from: https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
    """

    light_blue = "\x1b[1;34m"
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_log_debug = "%(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    format_log = "%(levelname)s - %(message)s"

    FORMATS: Dict[int, str] = {
        logging.DEBUG: grey + format_log_debug + reset,
        logging.INFO: light_blue + format_log + reset,
        logging.WARNING: yellow + format_log + reset,
        logging.ERROR: red + format_log + reset,
        logging.CRITICAL: bold_red + format_log + reset
    }

    def format(self, record: logging.LogRecord) -> str:
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def set_logger_level(logger: logging.Logger, verbosity: int = 0, add_colours: bool = True) -> None:
    handler = logging.StreamHandler()
    if add_colours:
        handler.setFormatter(ColourFormatter())
    if verbosity == 0:
        logger.setLevel(logging.ERROR)
        handler.setLevel(logging.ERROR)
    elif verbosity == 1:
        logger.setLevel(logging.WARNING)
        handler.setLevel(logging.WARNING)
    elif verbosity == 2:
        logger.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
    elif verbosity >= 3:
        logger.setLevel(logging.DEBUG)
        handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.propagate = False
