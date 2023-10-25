from dataclasses import dataclass
from typing import Final, Literal, Union


@dataclass
class Config:
    GIT_MODE: Final[Literal["ssh", "https"]] = "ssh"
    VERBOSITY: Final[int] = 0
    DEBUG: Final[int] = 0
    