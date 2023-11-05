from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaskProperties:
    organization: str
    name: str
    version: str

    def __str__(self):
        v = "" if self.version == "latest" else f"@{self.version}"
        o = "" if self.organization == "prepare-assignment" else f"/{self.organization}"
        return f"{o}{self.name}{v}"

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
