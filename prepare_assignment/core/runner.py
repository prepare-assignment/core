import json
import os.path
import re
import shlex
import subprocess
import sys
from typing import Any, Dict, List

from importlib_resources import files


def run(prepare: Dict[str, Any]) -> None:
    for step, actions in prepare["steps"].items():
        print(f"{step}:")
        print(f"{actions}")
