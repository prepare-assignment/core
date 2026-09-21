from __future__ import annotations

import re

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
from typing import Dict, Optional, Union, Any, List

TaskInput = Union[str, float, int, list]


@dataclass
class Task(ABC):
    name: str
    id: Optional[str]
    if_: Optional[str]
    working_directory: Optional[str] = field(default=None, kw_only=True)
    env: Dict[str, str] = field(default_factory=dict, kw_only=True)
    continue_on_error: bool = field(default=False, kw_only=True)

    @property
    @abstractmethod
    def is_run(self) -> bool:
        ...

    @staticmethod
    def of(yaml: Dict[str, Any]) -> Task:
        return RunTask.of(yaml) if "run" in yaml else UsesTask.of(yaml)

    @staticmethod
    def _common(yaml: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": yaml["name"],
            "id": yaml.get("id", None),
            "if_": yaml.get("if", None),
            "working_directory": yaml.get("working-directory", None),
            "env": dict(yaml.get("env", None) or {}),
            "continue_on_error": yaml.get("continue-on-error", False),
        }

    @cached_property
    def key(self) -> str:
        if self.id is None:
            key = self.name.lower().replace("_", "-")
            return re.sub(r"\s+", "-", key)
        return self.id


@dataclass
class RunTask(Task):
    run: str
    shell: Optional[str] = field(default=None, kw_only=True)

    @classmethod
    def of(cls, yaml: Dict[str, Any]) -> RunTask:
        return cls(
            run=yaml["run"],
            shell=yaml.get("shell", None),
            **Task._common(yaml)
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
            uses=yaml["uses"],
            with_=yaml.get("with", {}),
            **Task._common(yaml)
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
