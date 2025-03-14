import logging
import re
from typing import Final, Dict, Type, List

from prepare_assignment.data.config import Config
from prepare_assignment.utils.config import load_config
from prepare_assignment.utils.executables import get_bash_path

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
    # ${{ tasks.<step>.outputs.<output> }}
    r"tasks\.(?P<outputs>(?P<step>[_a-zA-Z][a-zA-Z0-9_-]*)\.outputs\.(?P<output>[_a-zA-Z][a-zA-Z0-9_-]*))"
]

SUB_REGEX: Final[re.Pattern] = re.compile("|".join(SUBSTITUTIONS))

LOG_LEVEL_TRACE: Final[int] = logging.DEBUG - 5

CONFIG: Config = load_config()

BASH_EXECUTABLE: Final[str] = get_bash_path()
