import logging
import os
import re
import shutil
import sys
from typing import Final, Dict, Type, List

from ruamel.yaml import YAML

from prepare_assignment.data.config import Config
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

CONFIG: Config = Config()

BASH_EXECUTABLE: Final[str] = get_bash_path()

YAML_LOADER = YAML(typ='safe')
YAML_LOADER.brace_single_entry_mapping_in_flow_sequence = False
YAML_LOADER.default_flow_style = True
