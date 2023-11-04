from __future__ import annotations

import re

from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import cached_property
from typing import Dict, Optional, Union, Any, List

TaskInput = Union[str, float, int, list]


@dataclass
class Task(ABC):
    name: str
    id: Optional[str]

    @property
    @abstractmethod
    def is_run(self) -> bool:
        ...

    @staticmethod
    def of(yaml: Dict[str, Any]) -> Task:
        return RunTask.of(yaml) if "run" in yaml else UsesTask.of(yaml)

    @cached_property
    def key(self) -> str:
        if self.id is None:
            key = self.name.lower().replace("_", "-")
            return re.sub(r"\s+", "-", key)
        return self.id


@dataclass
class RunTask(Task):
    run: str

    @classmethod
    def of(cls, yaml: Dict[str, Any]) -> RunTask:
        return cls(
            name=yaml["name"],
            run=yaml["run"],
            id=yaml.get("id", None)
        )

    @property
    def is_run(self) -> bool:
        return True


@dataclass
class UsesTask(Task):
    uses: str
    with_: Dict[str, TaskInput]

    @classmethod
    def of(cls, yaml: Dict[str, Any]) -> UsesTask:
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
    jobs: Dict[str, List[Task]]

    @classmethod
    def of(cls, yaml: Dict[str, Any]) -> Prepare:
        jobs_dict = yaml.get("jobs", {})
        jobs = {key: [Task.of(value) for value in values] for key, values in jobs_dict.items()}
        return cls(
            name=yaml["name"],
            jobs=jobs
        )
