import logging
import re
from typing import Final

from prepare_assignment.data.config import Config
from prepare_assignment.utils.config import load_config

HAS_SUB_REGEX: Final[re.Pattern] = re.compile(r"(?P<exp>\${{\s*(?P<content>.*?)\s*}})")

LOG_LEVEL_TRACE: Final[int] = logging.DEBUG - 5

CONFIG: Config = load_config()
