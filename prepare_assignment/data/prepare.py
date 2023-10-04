from __future__ import annotations

import re

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import Dict, Optional, Union, Any, List

ActionInput = Union[str, float, int, list]


@dataclass
class Action(ABC):
    name: str
    id: Optional[str]

    @property
    @abstractmethod
    def is_run(self) -> bool:
        ...

    @staticmethod
    def of(yaml: Dict[str, Any]) -> Action:
        return RunAction.of(yaml) if "run" in yaml else UsesAction.of(yaml)

    @cached_property
    def key(self) -> str:
        if self.id is None:
            key = self.name.lower().replace("_", "-")
            return re.sub(r"\s+", "-", key)
        return self.id


@dataclass
class RunAction(Action):
    run: str

    @classmethod
    def of(cls, yaml: Dict[str, Any]) -> RunAction:
        return cls(
            name=yaml["name"],
            run=yaml["run"],
            id=yaml.get("id", None)
        )

    @property
    def is_run(self) -> bool:
        return True


@dataclass
class UsesAction(Action):
    uses: str
    with_: Dict[str, ActionInput]

    @classmethod
    def of(cls, yaml: Dict[str, Any]) -> UsesAction:
        return cls(
            name=yaml["name"],
            uses=yaml["uses"],
            with_=yaml.get("with", {}),
            id=yaml.get("id", None)
        )

    @property
    def is_run(self) -> bool:
        return False


@dataclass
class Prepare:
    name: str
    steps: Dict[str, List[Action]]

    @classmethod
    def of(cls, yaml: Dict[str, Any]) -> Prepare:
        steps_dict = yaml.get("steps", {})
        steps = {key: [Action.of(value) for value in values] for key, values in steps_dict.items()}
        return cls(
            name=yaml["name"],
            steps=steps
        )
