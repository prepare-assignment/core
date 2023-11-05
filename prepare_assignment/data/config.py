from dataclasses import dataclass
from enum import Enum
from typing import Final, Literal


class GitMode(str, Enum):
    ssh = "ssh"
    https = "https"


@dataclass
class Config:
    GIT_MODE: Final[GitMode] = GitMode.ssh
    VERBOSITY: Final[int] = 0
    DEBUG: Final[int] = 0
