from __future__ import annotations

import os.path
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from prepare_assignment.utils.cache import get_tasks_path

tasks_path = get_tasks_path()


@dataclass(frozen=True)
class TaskProperties:
    organization: str
    name: str
    version: str

    @cached_property
    def task_path(self) -> Path:
        return Path(os.path.join(tasks_path, self.organization, self.name, self.version))

    @cached_property
    def repo_path(self) -> Path:
        return Path(os.path.join(self.task_path, "repo"))

    @cached_property
    def definition_path(self) -> Path:
        return Path(os.path.join(self.repo_path, "task.yml"))

    def __str__(self):
        return f"{self.organization}/{self.name}@{self.version}"

    def __eq__(self, other):
        if not isinstance(other, TaskProperties):
            return False
        return self.organization == other.organization and self.name == other.name and self.version == other.version

    @classmethod
    def of(cls, task: str) -> TaskProperties:
        parts = task.split("/")
        if len(parts) > 2:
            raise AssertionError("Tasks cannot have more than one slash")
        elif len(parts) == 1:
            parts.insert(0, "prepare-assignment")
        organization: str = parts[0]
        name = parts[1]
        split = name.split("@")
        version: str = "latest"
        task_name: str = name
        if len(split) > 2:
            raise AssertionError("Cannot have multiple '@' symbols in the name")
        elif len(split) == 2:
            task_name = split[0]
            version = split[1]
        return cls(organization, task_name, version)
