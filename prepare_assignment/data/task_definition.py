from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional, List, TypedDict


@dataclass
class TaskInputDefinition:
    name: str
    description: str
    required: bool
    type: str
    default: str | List[Any] | bool | int | float | None = None
    items: Optional[str] = None

    @classmethod
    def of(cls, name: str, yaml: Dict[str, Any]) -> TaskInputDefinition:
        default = yaml.get("default", None)
        items = yaml.get("items", None)
        return cls(
            name=name,
            description=yaml["description"],
            required=yaml["required"],
            type=yaml["type"],
            default=default,
            items=items
        )

    def to_schema_definition(self) -> str:

        properties = [f'"type": "{self.type}"']
        if self.type == "array":
            properties.append(f'"items": {{ "type": "{self.items}" }}')
        if self.default is not None:
            properties.append(f'"default": {json.dumps(self.default)}')
        joined = ",\n  ".join(properties)
        return f'"{self.name}": {{\n  {joined}\n}}'


@dataclass
class TaskOutputDefinition:
    description: str
    type: str
    items: Optional[str]

    @classmethod
    def of(cls, yaml: Dict[str, Any]) -> TaskOutputDefinition:
        items = yaml.get("items", None)
        return cls(
            description=yaml["description"],
            type=yaml["type"],
            items=items
        )


@dataclass
class TaskDefinition(ABC):
    id: str
    name: str
    description: str
    inputs: List[TaskInputDefinition]
    outputs: Dict[str, TaskOutputDefinition]
    path: str

    @property
    @abstractmethod
    def is_composite(self) -> bool:
        ...

    @staticmethod
    def _dict_to_inputs(dictionary: Dict[str, Any]) -> List[TaskInputDefinition]:
        return [TaskInputDefinition.of(key, value) for key, value in dictionary.items()]

    @staticmethod
    def _yaml_to_outputs(yaml: Dict[str, Any]) -> Dict[str, TaskOutputDefinition]:
        return {key: TaskOutputDefinition.of(value) for key, value in yaml.items()}


@dataclass
class PythonTaskDefinition(TaskDefinition):
    main: str

    @classmethod
    def of(cls, yaml: Dict[str, Any], path: str) -> PythonTaskDefinition:
        inputs = yaml.get("inputs", {})
        outputs = yaml.get("outputs", {})
        return cls(
            id=yaml["id"],
            name=yaml["name"],
            description=yaml["description"],
            inputs=TaskDefinition._dict_to_inputs(inputs),
            outputs=TaskDefinition._yaml_to_outputs(outputs),
            main=yaml["runs"]["main"],
            path=path
        )

    @property
    def is_composite(self) -> bool:
        return False


@dataclass
class CompositeTaskDefinition(TaskDefinition):
    tasks: List[Any]

    @classmethod
    def of(cls, yaml: Dict[str, Any], path: str) -> CompositeTaskDefinition:
        inputs = yaml.get("inputs", {})
        outputs = yaml.get("outputs", {})
        return cls(
            id=yaml["id"],
            name=yaml["name"],
            description=yaml["description"],
            tasks=yaml["runs"]["tasks"],
            inputs=TaskDefinition._dict_to_inputs(inputs),
            outputs=TaskDefinition._yaml_to_outputs(outputs),
            path=path
        )

    @property
    def is_composite(self) -> bool:
        return True


class ValidTask(TypedDict):
    schema: Any
    task: TaskDefinition