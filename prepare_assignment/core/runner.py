import json
import os.path
import re
import shlex
import subprocess
import sys
from typing import Any, Dict, List
import logging

from importlib_resources import files

# Get the logger
logger = logging.getLogger("prepare")


def run(prepare: Dict[str, Any]) -> None:
    logger.debug("========== Running prepare assignment")
    for step, actions in prepare["steps"].items():
        print(f"{step}:")
        print(f"{actions}")
    logger.debug("✓ Prepared :)")
