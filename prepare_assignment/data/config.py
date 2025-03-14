from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal, Optional


class GitMode(str, Enum):
    ssh = "ssh"
    https = "https"


@dataclass
class Core:
    git_mode: GitMode = GitMode.ssh
    verbose: int = 0
    debug: int = 0


@dataclass
class Config:
    core: Core
