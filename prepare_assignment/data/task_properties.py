from __future__ import annotations

import os.path
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

from prepare_assignment.utils.paths import get_tasks_path

tasks_path = get_tasks_path()


@dataclass(frozen=True)
class TaskProperties:
    organization: str
    name: str
    version: str

    @cached_property
    def task_path(self) -> Path:
        return Path(os.path.join(tasks_path, self.organization, self.name, self.version_directory))

    @property
    def version_directory(self) -> str:
        """
        The version as a single directory name, a branch can contain a slash (e.g. fix/something)
        """
        return version_to_directory(self.version)

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
        # Everything after the first '@' is the version, a branch can contain a slash
        name, separator, version = task.partition("@")
        if not separator:
            version = "latest"
        parts = name.split("/")
        if len(parts) > 2:
            raise ValueError("Tasks cannot have more than one slash")
        elif len(parts) == 1:
            parts.insert(0, "prepare-assignment")
        return cls(parts[0], parts[1], version)


def version_to_directory(version: str) -> str:
    return version.replace("%", "%25").replace("/", "%2F")


def directory_to_version(directory: str) -> str:
    return directory.replace("%2F", "/").replace("%25", "%")
