from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal, Optional


class GitMode(str, Enum):
    ssh = "ssh"
    https = "https"

@dataclass
class Core:
    git_mode: Optional[GitMode] = GitMode.ssh
    verbose: Optional[int] = 0
    debug: Optional[bool] = False

@dataclass
class Config:
    core: Core
