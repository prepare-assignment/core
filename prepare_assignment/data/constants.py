import logging
import re
from typing import Final, Dict, Type, List

from prepare_assignment.data.config import Config

TYPE_MAPPING: Final[Dict[str, Type]] = {
    "string": str,
    "array": list,
    "number": float,
    "integer": int,
    "boolean": bool
}

HAS_SUB_REGEX: Final[re.Pattern] = re.compile(r"(?P<exp>\${{\s*(?P<content>.*?)\s*}})")

SUBSTITUTIONS: Final[List[str]] = [
    # ${{ inputs.<input> }}
    r"inputs\.(?P<inputs>[_a-zA-Z][a-zA-Z0-9_-]*)",
    # ${{ steps.<step>.outputs.<output> }}
    r"steps\.(?P<outputs>(?P<step>[_a-zA-Z][a-zA-Z0-9_-]*)\.outputs\.(?P<output>[_a-zA-Z][a-zA-Z0-9_-]*))"
]

SUB_REGEX: Final[re.Pattern] = re.compile("|".join(SUBSTITUTIONS))

LOG_LEVEL_TRACE: Final[int] = logging.DEBUG - 5

CONFIG: Config = Config()
